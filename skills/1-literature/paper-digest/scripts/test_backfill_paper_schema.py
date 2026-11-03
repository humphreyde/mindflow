from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from backfill_paper_schema import (
    ApprovalExpectation,
    ApprovalValidationError,
    ManifestDriftError,
    ManifestValidationError,
    apply_manifest,
    main,
    parse_approved_manifest,
)
from paper_schema import parse_frontmatter, render_deterministic_updates, resolve_identity


BYTE_CASES = (
    b"---\ntitle: ASCII\n---\nBody\n",
    b"---\r\ntitle: CRLF\r\n---\r\nBody\r\n",
    b"---\ntitle: no-eof\n---\nBody",
    "---\ntitle: 机器人\n---\n正文\n".encode("utf-8"),
)

CLI_MODES = (
    ("dry-run", ()),
    ("apply", ("--apply",)),
    ("emit-paper-pathspec", ("--emit-paper-pathspec",)),
    ("verify-index", ("--verify-index",)),
)

PIN_MISMATCHES = (
    ("manifest_commit", "0" * 40),
    ("manifest_sha256", "0" * 64),
    ("pending_approval_commit", "0" * 40),
    ("pending_approval_sha256", "0" * 64),
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(vault: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(vault), *args],
        text=True,
    ).strip()


class BackfillPaperSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name)
        self.papers = self.vault / "Papers"
        self.migrations = self.vault / "Workbench/migrations"
        self.scripts = self.vault / "skills/1-literature/paper-digest/scripts"
        self.papers.mkdir(parents=True)
        self.migrations.mkdir(parents=True)
        self.scripts.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.vault)], check=True)
        git(self.vault, "config", "user.email", "test@example.com")
        git(self.vault, "config", "user.name", "Test")

        self.paper_paths: list[Path] = []
        items = []
        for index in range(182):
            path = self.papers / f"2603-Test{index:03d}.md"
            if index < 175:
                arxiv_id = f"2603.{index:05d}"
                raw = (
                    f"---\ntitle: Test {index}\npaper: https://arxiv.org/abs/{arxiv_id}\n---\nBody\n"
                ).encode()
                updates = {"type": "paper", "arxiv_id": arxiv_id}
            else:
                raw = (
                    f"---\ntitle: Test {index}\nwebsite: https://example.org/paper-{index}\n---\nBody\n"
                ).encode()
                updates = {"type": "paper"}
            path.write_bytes(raw)
            document = parse_frontmatter(path)
            post = render_deterministic_updates(document, updates)
            identity = resolve_identity(document)
            items.append(
                {
                    "path": path.relative_to(self.vault).as_posix(),
                    "source_sha256": sha256(raw),
                    "expected_post_sha256": sha256(post),
                    "identity": {
                        "kind": identity.kind,
                        "key": identity.key,
                        "arxiv_id": identity.arxiv_id,
                        "doi": identity.doi,
                        "official_url": identity.official_url,
                        "normalized_title": identity.normalized_title,
                        "confidence": identity.confidence,
                    },
                    "confidence": identity.confidence,
                    "classification_candidates": [],
                    "issues": [],
                    "deterministic_updates": updates,
                }
            )
            self.paper_paths.append(path)

        self.manifest_path = self.migrations / "audit.json"
        manifest = {
            "manifest_version": 1,
            "items": items,
            "duplicate_groups": [],
            "summary": {
                "total": 182,
                "arxiv_identity": 175,
                "url_title_review": 7,
                "duplicate_identity_groups": 0,
                "errors": 0,
                "needs_review": 182,
            },
        }
        self.manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.scripts / "backfill_paper_schema.py").write_text("tool\n", encoding="utf-8")
        (self.scripts / "test_backfill_paper_schema.py").write_text("tests\n", encoding="utf-8")
        git(self.vault, "add", ".")
        git(self.vault, "commit", "-qm", "audit manifest")
        self.manifest_commit = git(self.vault, "rev-parse", "HEAD")
        self.manifest_sha256 = sha256(self.manifest_path.read_bytes())

        self.approval_path = self.migrations / "approval.json"
        receipt = {
            "approval_version": 1,
            "approval_status": "pending",
            "manifest_path": self.manifest_path.relative_to(self.vault).as_posix(),
            "manifest_commit": self.manifest_commit,
            "manifest_sha256": self.manifest_sha256,
            "approved_type_additions": 182,
            "approved_arxiv_additions": 175,
            "approved_other_fields": 0,
        }
        self.approval_path.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        git(self.vault, "add", str(self.approval_path))
        git(self.vault, "commit", "-qm", "pending approval")
        self.pending_approval_commit = git(self.vault, "rev-parse", "HEAD")
        self.pending_approval_sha256 = sha256(self.approval_path.read_bytes())
        receipt["approval_status"] = "confirmed"
        self.approval_path.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        git(self.vault, "add", str(self.approval_path))
        git(self.vault, "commit", "-qm", "confirm approval")
        self.expectation = ApprovalExpectation(
            manifest_commit=self.manifest_commit,
            manifest_sha256=self.manifest_sha256,
            pending_approval_commit=self.pending_approval_commit,
            pending_approval_sha256=self.pending_approval_sha256,
        )
        self.note = self.paper_paths[0]
        self.expected_post_bytes = render_deterministic_updates(
            parse_frontmatter(self.note),
            {"type": "paper", "arxiv_id": "2603.00000"},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _expectation_with(self, **changes: str) -> ApprovalExpectation:
        values = {
            "manifest_commit": self.expectation.manifest_commit,
            "manifest_sha256": self.expectation.manifest_sha256,
            "pending_approval_commit": self.expectation.pending_approval_commit,
            "pending_approval_sha256": self.expectation.pending_approval_sha256,
        }
        values.update(changes)
        return ApprovalExpectation(**values)

    def _cli_args(self, expectation: ApprovalExpectation, *mode_args: str) -> list[str]:
        return [
            "--vault", str(self.vault),
            "--manifest", self.manifest_path.relative_to(self.vault).as_posix(),
            "--approval", self.approval_path.relative_to(self.vault).as_posix(),
            "--expected-manifest-commit", expectation.manifest_commit,
            "--expected-manifest-sha256", expectation.manifest_sha256,
            "--expected-pending-approval-commit", expectation.pending_approval_commit,
            "--expected-pending-approval-sha256", expectation.pending_approval_sha256,
            *mode_args,
        ]

    def test_renderer_preserves_every_existing_byte(self) -> None:
        for raw in BYTE_CASES:
            with self.subTest(raw=raw):
                path = self.vault / "byte-case.md"
                path.write_bytes(raw)
                document = parse_frontmatter(path)
                rendered = render_deterministic_updates(
                    document, {"type": "paper", "arxiv_id": "2603.03596"}
                )
                inserted = (
                    b"type: paper" + document.newline
                    + b"arxiv_id: 2603.03596" + document.newline
                )
                split = document.opening_delimiter_end
                self.assertEqual(rendered, raw[:split] + inserted + raw[split:])

    def test_dry_run_reports_all_pending_and_writes_nothing(self) -> None:
        before = {path: path.read_bytes() for path in self.paper_paths}
        report = apply_manifest(
            self.vault,
            self.manifest_path,
            self.approval_path,
            expectation=self.expectation,
            apply=False,
        )
        self.assertEqual((report.pending, report.applied, report.noop, report.blocked), (182, 0, 0, 0))
        self.assertEqual(before, {path: path.read_bytes() for path in self.paper_paths})

    def test_apply_preserves_mode_and_is_idempotent(self) -> None:
        self.note.chmod(0o644)
        first = apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=True,
        )
        self.assertEqual((first.applied, first.blocked), (182, 0))
        self.assertEqual(stat.S_IMODE(self.note.stat().st_mode), 0o644)
        self.assertEqual(self.note.read_bytes(), self.expected_post_bytes)
        second = apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=True,
        )
        self.assertEqual((second.noop, second.applied), (182, 0))

    def test_blocked_dry_run_and_apply_return_complete_report_and_write_nothing(self) -> None:
        self.note.write_bytes(b"---\ntitle: user edit\n---\n")
        before = {path: path.read_bytes() for path in self.paper_paths}
        reports = []
        for should_apply in (False, True):
            with self.subTest(apply=should_apply):
                with self.assertRaisesRegex(ManifestDriftError, "blocked") as caught:
                    apply_manifest(
                        self.vault, self.manifest_path, self.approval_path,
                        expectation=self.expectation, apply=should_apply,
                    )
                reports.append(caught.exception.report)
                self.assertEqual(caught.exception.report.blocked, 1)
                self.assertEqual(before, {path: path.read_bytes() for path in self.paper_paths})
        self.assertEqual(reports[0], reports[1])
        self.assertEqual(len(reports[0].items), 182)

    def test_pending_receipt_is_rejected_before_paper_evaluation(self) -> None:
        git(self.vault, "reset", "--hard", "HEAD^")
        with self.assertRaisesRegex(ApprovalValidationError, "not confirmed") as caught:
            apply_manifest(
                self.vault, self.manifest_path, self.approval_path,
                expectation=self.expectation, apply=False,
            )
        self.assertFalse(hasattr(caught.exception, "report"))

    def test_external_human_confirmed_pins_are_required(self) -> None:
        for field, bad_value in PIN_MISMATCHES:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ApprovalValidationError, "human-confirmed") as caught:
                    apply_manifest(
                        self.vault, self.manifest_path, self.approval_path,
                        expectation=self._expectation_with(**{field: bad_value}),
                        apply=False,
                    )
                self.assertFalse(hasattr(caught.exception, "report"))

    def test_dirty_or_recommitted_receipt_is_rejected(self) -> None:
        self.approval_path.write_text(
            self.approval_path.read_text().replace(
                '"approved_type_additions": 182', '"approved_type_additions": 181'
            )
        )
        with self.assertRaises(ApprovalValidationError):
            apply_manifest(
                self.vault, self.manifest_path, self.approval_path,
                expectation=self.expectation, apply=False,
            )
        git(self.vault, "add", str(self.approval_path))
        git(self.vault, "commit", "-qm", "tamper receipt")
        with self.assertRaisesRegex(ApprovalValidationError, "exactly two receipt commits"):
            apply_manifest(
                self.vault, self.manifest_path, self.approval_path,
                expectation=self.expectation, apply=False,
            )

    def test_malformed_manifest_raises_report_free_validation_error(self) -> None:
        for raw in (b"{", b'{"manifest_version": 2, "items": "not-a-list"}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ManifestValidationError) as caught:
                    parse_approved_manifest(raw)
                self.assertFalse(hasattr(caught.exception, "report"))

    def test_every_cli_mode_rejects_each_single_pin_mismatch_without_stdout(self) -> None:
        before = {path: path.read_bytes() for path in self.paper_paths}
        for mode_name, mode_args in CLI_MODES:
            for field, bad_value in PIN_MISMATCHES:
                stdout = StringIO()
                stderr = StringIO()
                with self.subTest(mode=mode_name, field=field):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        exit_code = main(
                            self._cli_args(
                                self._expectation_with(**{field: bad_value}),
                                *mode_args,
                            )
                        )
                    self.assertEqual(exit_code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn("human-confirmed", stderr.getvalue())
                    self.assertEqual(before, {path: path.read_bytes() for path in self.paper_paths})


if __name__ == "__main__":
    unittest.main()
