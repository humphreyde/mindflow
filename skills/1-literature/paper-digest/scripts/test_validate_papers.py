from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from validate_papers import (
    MANIFEST_VERSION,
    audit_vault,
    main,
    report_json_bytes,
    write_approval_candidate,
    write_report,
)


def sha256_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ValidatePapersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name)
        self.papers = self.vault / "Papers"
        self.papers.mkdir()
        self.note = self.papers / "2603-Test.md"
        self.note.write_text(
            "---\n"
            "title: Test Paper\n"
            "tags: [VLA, world-model]\n"
            "paper: https://arxiv.org/abs/2603.03596v2\n"
            "rating: 2\n"
            "---\n"
            "Body\n",
            encoding="utf-8",
        )
        self.review_note = self.papers / "project-note.md"
        self.review_note.write_text(
            "---\n"
            "title: Project Paper\n"
            "tags: [world-model]\n"
            "website: https://example.org/project\n"
            "rating: 1\n"
            "---\n",
            encoding="utf-8",
        )
        self.out_json = self.vault / "audit.json"
        self.out_md = self.vault / "audit.md"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_audit_is_stable_and_does_not_modify_notes(self) -> None:
        before = sha256_tree(self.papers)
        first = report_json_bytes(audit_vault(self.vault))
        second = report_json_bytes(audit_vault(self.vault))
        self.assertEqual(first, second)
        self.assertEqual(before, sha256_tree(self.papers))

    def test_audit_only_proposes_deterministic_fields(self) -> None:
        report = audit_vault(self.vault)
        item = next(item for item in report.items if item.path == "Papers/2603-Test.md")
        self.assertEqual(
            item.deterministic_updates,
            {"type": "paper", "arxiv_id": "2603.03596"},
        )
        self.assertNotIn("primary_domain", item.deterministic_updates)
        self.assertNotIn("review_status", item.deterministic_updates)
        self.assertNotEqual(item.source_sha256, item.expected_post_sha256)

    def test_summary_counts_errors_separately_from_review(self) -> None:
        summary = audit_vault(self.vault).summary
        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.arxiv_identity, 1)
        self.assertEqual(summary.url_title_review, 1)
        self.assertEqual(summary.errors, 0)
        self.assertEqual(summary.needs_review, 2)

    def test_duplicate_strong_identity_is_hard_error(self) -> None:
        duplicate = self.papers / "2603-Duplicate.md"
        duplicate.write_text(
            "---\ntitle: Duplicate\ntags: [VLA]\narxiv_id: 2603.03596\n---\n",
            encoding="utf-8",
        )
        report = audit_vault(self.vault)
        self.assertEqual(report.summary.duplicate_identity_groups, 1)
        self.assertEqual(report.summary.errors, 2)
        duplicate_issues = [
            issue
            for item in report.items
            for issue in item.issues
            if issue.code == "duplicate-identity"
        ]
        self.assertEqual(len(duplicate_issues), 2)
        self.assertTrue(all(issue.severity == "error" for issue in duplicate_issues))

    def test_outputs_cannot_alias_paper_inputs(self) -> None:
        report = audit_vault(self.vault)
        paper_alias = self.vault / "paper-alias"
        paper_alias.symlink_to(self.papers, target_is_directory=True)
        for output in (
            self.note,
            self.papers / "audit.json",
            paper_alias / "audit.json",
        ):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "Papers"):
                    write_report(report, json_path=output, markdown_path=self.out_md)

    def test_markdown_output_cannot_be_inside_papers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Papers"):
            write_report(
                audit_vault(self.vault),
                json_path=self.out_json,
                markdown_path=self.papers / "audit.md",
            )

    def test_output_pair_cannot_alias_each_other(self) -> None:
        self.out_json.write_bytes(b"old\n")
        out_alias = self.vault / "out-alias.md"
        out_alias.symlink_to(self.out_json)
        with self.assertRaisesRegex(ValueError, "distinct"):
            write_report(
                audit_vault(self.vault),
                json_path=self.out_json,
                markdown_path=out_alias,
            )

    def test_atomic_failure_preserves_existing_output(self) -> None:
        self.out_json.write_bytes(b"old-json\n")
        with mock.patch("validate_papers.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "JSON"):
                write_report(
                    audit_vault(self.vault),
                    json_path=self.out_json,
                    markdown_path=self.out_md,
                )
        self.assertEqual(self.out_json.read_bytes(), b"old-json\n")
        self.assertFalse(self.out_md.exists())

    def test_second_replace_failure_never_exposes_partial_markdown(self) -> None:
        self.out_json.write_bytes(b"old-json\n")
        self.out_md.write_bytes(b"old-md\n")
        real_replace = os.replace
        calls = 0

        def fail_second(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("second replace failed")
            real_replace(source, target)

        with mock.patch("validate_papers.os.replace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "Markdown"):
                write_report(
                    audit_vault(self.vault),
                    json_path=self.out_json,
                    markdown_path=self.out_md,
                )
        self.assertIn(self.out_json.read_bytes(), {b"old-json\n", report_json_bytes(audit_vault(self.vault))})
        self.assertEqual(self.out_md.read_bytes(), b"old-md\n")

    def test_report_top_level_contract_and_manifest_version(self) -> None:
        payload = json.loads(report_json_bytes(audit_vault(self.vault)))
        self.assertEqual(set(payload), {"manifest_version", "items", "duplicate_groups", "summary"})
        self.assertEqual(payload["manifest_version"], MANIFEST_VERSION)

    def test_cli_exit_codes_distinguish_review_from_hard_error(self) -> None:
        self.assertEqual(
            main(
                [
                    "--vault",
                    str(self.vault),
                    "--mode",
                    "audit",
                    "--json",
                    str(self.out_json),
                    "--markdown",
                    str(self.out_md),
                ]
            ),
            0,
        )
        self.note.write_text(
            "---\ntitle: Conflict\narxiv_id: 2603.00001\npaper: https://arxiv.org/abs/2603.00002\n---\n",
            encoding="utf-8",
        )
        self.assertEqual(
            main(
                [
                    "--vault",
                    str(self.vault),
                    "--mode",
                    "audit",
                    "--json",
                    str(self.out_json),
                    "--markdown",
                    str(self.out_md),
                ]
            ),
            1,
        )

    def test_approval_candidate_reads_committed_manifest_blob(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.vault, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.vault, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.vault, check=True)
        manifest = self.vault / "manifest.json"
        items = []
        for index in range(182):
            updates = {"type": "paper"}
            if index < 175:
                updates["arxiv_id"] = f"2603.{index:05d}"
            items.append({"deterministic_updates": updates})
        manifest.write_text(
            json.dumps(
                {
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
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "manifest.json"], cwd=self.vault, check=True)
        subprocess.run(["git", "commit", "-qm", "manifest"], cwd=self.vault, check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.vault, text=True).strip()
        manifest.write_text("uncommitted bytes\n", encoding="utf-8")
        approval = self.vault / "approval.json"
        receipt = write_approval_candidate(manifest, commit, approval)
        committed = subprocess.check_output(
            ["git", "show", f"{commit}:manifest.json"], cwd=self.vault
        )
        self.assertEqual(receipt.approval_status, "pending")
        self.assertEqual(receipt.manifest_sha256, hashlib.sha256(committed).hexdigest())
        self.assertEqual(receipt.approved_type_additions, 182)
        self.assertEqual(receipt.approved_arxiv_additions, 175)
        self.assertEqual(receipt.approved_other_fields, 0)


if __name__ == "__main__":
    unittest.main()
