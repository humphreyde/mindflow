#!/usr/bin/env python3
"""Apply a human-pinned, deterministic Paper frontmatter backfill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from paper_schema import (
    PaperIdentity,
    ValidationIssue,
    parse_frontmatter,
    render_deterministic_updates,
    resolve_identity,
)
from validate_papers import AuditItem, AuditReport, AuditSummary


ApplyState = Literal["pending", "applied", "noop", "blocked"]


@dataclass(frozen=True)
class ApprovalExpectation:
    manifest_commit: str
    manifest_sha256: str
    pending_approval_commit: str
    pending_approval_sha256: str


class BackfillValidationError(RuntimeError):
    """Base class caught by the CLI boundary."""


class ApprovalValidationError(BackfillValidationError):
    """Receipt, history, external-pin, or pinned-object validation failed."""


class ManifestValidationError(BackfillValidationError):
    """The approved manifest schema or semantics are invalid."""


class ManifestDriftError(BackfillValidationError):
    """A complete item preflight found one or more blocked Paper states."""

    def __init__(self, message: str, report: "ApplyReport") -> None:
        super().__init__(message)
        self.report = report


@dataclass(frozen=True)
class ApplyItem:
    path: str
    state: ApplyState
    updates: Mapping[str, str]
    current_sha256: str


@dataclass(frozen=True)
class ApplyReport:
    manifest_version: int
    items: tuple[ApplyItem, ...]
    pending: int
    applied: int
    noop: int
    blocked: int


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _manifest_error(message: str) -> ManifestValidationError:
    return ManifestValidationError(message)


def parse_approved_manifest(raw: bytes) -> AuditReport:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _manifest_error(f"invalid manifest JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("manifest_version") != 1:
        raise _manifest_error("manifest_version must be 1")
    if set(payload) != {"manifest_version", "items", "duplicate_groups", "summary"}:
        raise _manifest_error("manifest top-level fields are invalid")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise _manifest_error("manifest items must be a list")
    if payload.get("duplicate_groups") != []:
        raise _manifest_error("approved manifest must contain zero duplicate groups")
    summary_raw = payload.get("summary")
    if not isinstance(summary_raw, dict):
        raise _manifest_error("manifest summary must be an object")
    required_summary = {
        "total": 182,
        "arxiv_identity": 175,
        "url_title_review": 7,
        "duplicate_identity_groups": 0,
        "errors": 0,
        "needs_review": 182,
    }
    if summary_raw != required_summary:
        raise _manifest_error("manifest summary does not match approved baseline")

    items: list[AuditItem] = []
    seen_paths: set[str] = set()
    type_additions = 0
    arxiv_additions = 0
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            raise _manifest_error("manifest item must be an object")
        required_fields = {
            "path",
            "source_sha256",
            "expected_post_sha256",
            "identity",
            "confidence",
            "classification_candidates",
            "issues",
            "deterministic_updates",
        }
        if set(raw_item) != required_fields:
            raise _manifest_error("manifest item fields are invalid")
        path = raw_item["path"]
        if (
            not isinstance(path, str)
            or not re.fullmatch(r"Papers/[^/]+\.md", path)
            or path in seen_paths
        ):
            raise _manifest_error(f"invalid or duplicate Paper path: {path!r}")
        seen_paths.add(path)
        source_sha = raw_item["source_sha256"]
        post_sha = raw_item["expected_post_sha256"]
        if not isinstance(source_sha, str) or not _SHA256_RE.fullmatch(source_sha):
            raise _manifest_error(f"invalid source hash for {path}")
        if not isinstance(post_sha, str) or not _SHA256_RE.fullmatch(post_sha):
            raise _manifest_error(f"invalid post hash for {path}")
        identity_raw = raw_item["identity"]
        if not isinstance(identity_raw, dict):
            raise _manifest_error(f"invalid identity for {path}")
        try:
            identity = PaperIdentity(**identity_raw)
        except TypeError as exc:
            raise _manifest_error(f"invalid identity fields for {path}") from exc
        confidence = raw_item["confidence"]
        if confidence not in {"high", "low", "review"} or confidence != identity.confidence:
            raise _manifest_error(f"invalid confidence for {path}")
        candidates = raw_item["classification_candidates"]
        if not isinstance(candidates, list) or not all(isinstance(value, str) for value in candidates):
            raise _manifest_error(f"invalid classification candidates for {path}")
        issues_raw = raw_item["issues"]
        if not isinstance(issues_raw, list):
            raise _manifest_error(f"invalid issues for {path}")
        try:
            issues = tuple(ValidationIssue(**issue) for issue in issues_raw)
        except (TypeError, AttributeError) as exc:
            raise _manifest_error(f"invalid issue fields for {path}") from exc
        updates = raw_item["deterministic_updates"]
        if not isinstance(updates, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in updates.items()
        ):
            raise _manifest_error(f"invalid deterministic updates for {path}")
        if set(updates) - {"type", "arxiv_id"}:
            raise _manifest_error(f"unsupported deterministic update for {path}")
        if updates.get("type") != "paper":
            raise _manifest_error(f"missing type update for {path}")
        type_additions += 1
        if "arxiv_id" in updates:
            if identity.arxiv_id != updates["arxiv_id"]:
                raise _manifest_error(f"arXiv update does not match identity for {path}")
            arxiv_additions += 1
        items.append(
            AuditItem(
                path=path,
                source_sha256=source_sha,
                expected_post_sha256=post_sha,
                identity=identity,
                confidence=confidence,
                classification_candidates=tuple(candidates),
                issues=issues,
                deterministic_updates=dict(updates),
            )
        )
    if (len(items), type_additions, arxiv_additions) != (182, 182, 175):
        raise _manifest_error("manifest updates do not match approved 182/175 scope")
    items.sort(key=lambda item: item.path)
    summary = AuditSummary(**summary_raw)
    return AuditReport(1, tuple(items), (), summary, Path("."))


def _git(vault: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(vault), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout.strip() if text else result.stdout


def _relative_inside(vault: Path, path: Path, label: str) -> tuple[Path, str]:
    absolute = path if path.is_absolute() else vault / path
    # Resolve both macOS' /var -> /private/var alias and any symlink before the
    # containment check.  ``vault`` is already canonical at every call site.
    absolute = absolute.resolve()
    try:
        relative = absolute.relative_to(vault).as_posix()
    except ValueError as exc:
        raise ApprovalValidationError(f"{label} must be inside vault") from exc
    return absolute, relative


def _git_blob(vault: Path, commit: str, relative: str) -> bytes:
    try:
        return _git(vault, "show", f"{commit}:{relative}", text=False)  # type: ignore[return-value]
    except subprocess.CalledProcessError as exc:
        raise ApprovalValidationError(
            f"human-confirmed Git object is unavailable: {commit}:{relative}"
        ) from exc


def _load_json_object(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApprovalValidationError(f"invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ApprovalValidationError(f"invalid {label} object")
    return value


def _validate_approval_and_manifest(
    vault: Path,
    manifest_path: Path,
    approval_path: Path,
    expectation: ApprovalExpectation,
) -> AuditReport:
    vault = vault.resolve()
    for value, pattern, label in (
        (expectation.manifest_commit, _COMMIT_RE, "manifest commit"),
        (expectation.manifest_sha256, _SHA256_RE, "manifest sha256"),
        (expectation.pending_approval_commit, _COMMIT_RE, "pending approval commit"),
        (expectation.pending_approval_sha256, _SHA256_RE, "pending approval sha256"),
    ):
        if not pattern.fullmatch(value):
            raise ApprovalValidationError(f"human-confirmed {label} has invalid format")

    approval_absolute, approval_relative = _relative_inside(vault, approval_path, "approval")
    manifest_absolute, manifest_relative = _relative_inside(vault, manifest_path, "manifest")
    try:
        _git(vault, "ls-files", "--error-unmatch", "--", approval_relative)
    except subprocess.CalledProcessError as exc:
        raise ApprovalValidationError("approval receipt is untracked") from exc
    if _git(vault, "status", "--porcelain", "--untracked-files=all", "--", approval_relative):
        raise ApprovalValidationError("approval receipt is dirty")
    history_text = _git(vault, "log", "--format=%H", "--", approval_relative)
    history = history_text.splitlines() if isinstance(history_text, str) and history_text else []
    if not history:
        raise ApprovalValidationError("approval receipt has no committed history")
    latest_approval_commit = history[0]
    working_approval = approval_absolute.read_bytes()
    latest_approval_blob = _git_blob(vault, latest_approval_commit, approval_relative)
    if working_approval != latest_approval_blob:
        raise ApprovalValidationError("approval receipt does not match latest committed blob")
    receipt = _load_json_object(working_approval, "approval receipt")
    if receipt.get("approval_version") != 1:
        raise ApprovalValidationError("unsupported approval receipt version")
    status_value = receipt.get("approval_status")
    if status_value == "pending":
        if (
            latest_approval_commit != expectation.pending_approval_commit
            or _sha256(latest_approval_blob) != expectation.pending_approval_sha256
        ):
            raise ApprovalValidationError("pending receipt differs from human-confirmed pins")
        raise ApprovalValidationError("approval receipt is not confirmed")
    if status_value != "confirmed":
        raise ApprovalValidationError("approval receipt has invalid status")
    if len(history) != 2:
        raise ApprovalValidationError("approval path must have exactly two receipt commits")
    pending_commit = history[1]
    pending_blob = _git_blob(vault, pending_commit, approval_relative)
    if (
        pending_commit != expectation.pending_approval_commit
        or _sha256(pending_blob) != expectation.pending_approval_sha256
    ):
        raise ApprovalValidationError("pending receipt differs from human-confirmed pins")
    try:
        _git(vault, "merge-base", "--is-ancestor", pending_commit, latest_approval_commit)
    except subprocess.CalledProcessError as exc:
        raise ApprovalValidationError("pending receipt is not an ancestor of confirmation") from exc
    pending_receipt = _load_json_object(pending_blob, "pending approval receipt")
    if pending_receipt.get("approval_status") != "pending":
        raise ApprovalValidationError("earlier receipt is not pending")
    pending_without_status = {key: value for key, value in pending_receipt.items() if key != "approval_status"}
    confirmed_without_status = {key: value for key, value in receipt.items() if key != "approval_status"}
    if pending_without_status != confirmed_without_status:
        raise ApprovalValidationError("receipt confirmation changed fields beyond approval_status")
    expected_confirmed_blob = pending_blob.replace(
        b'"approval_status": "pending"',
        b'"approval_status": "confirmed"',
        1,
    )
    if expected_confirmed_blob != working_approval:
        raise ApprovalValidationError("receipt confirmation is not the one-line status transition")

    if receipt.get("manifest_path") != manifest_relative:
        raise ApprovalValidationError("manifest path differs from human-confirmed receipt")
    if (
        receipt.get("manifest_commit") != expectation.manifest_commit
        or receipt.get("manifest_sha256") != expectation.manifest_sha256
    ):
        raise ApprovalValidationError("manifest differs from human-confirmed pins")
    if (
        receipt.get("approved_type_additions") != 182
        or receipt.get("approved_arxiv_additions") != 175
        or receipt.get("approved_other_fields") != 0
    ):
        raise ApprovalValidationError("approval receipt has unexpected write counts")

    try:
        _git(vault, "ls-files", "--error-unmatch", "--", manifest_relative)
    except subprocess.CalledProcessError as exc:
        raise ApprovalValidationError("approved manifest is untracked") from exc
    if _git(vault, "status", "--porcelain", "--untracked-files=all", "--", manifest_relative):
        raise ApprovalValidationError("approved manifest is dirty")
    latest_manifest_commit = _git(vault, "log", "-1", "--format=%H", "--", manifest_relative)
    if latest_manifest_commit != expectation.manifest_commit:
        raise ApprovalValidationError("manifest latest commit differs from human-confirmed commit")
    pinned_manifest = _git_blob(vault, expectation.manifest_commit, manifest_relative)
    current_manifest = manifest_absolute.read_bytes()
    if (
        _sha256(pinned_manifest) != expectation.manifest_sha256
        or current_manifest != pinned_manifest
        or _sha256(current_manifest) != expectation.manifest_sha256
    ):
        raise ApprovalValidationError("manifest bytes differ from human-confirmed sha256")
    return parse_approved_manifest(pinned_manifest)


def _report(items: Sequence[ApplyItem]) -> ApplyReport:
    return ApplyReport(
        manifest_version=1,
        items=tuple(items),
        pending=sum(item.state == "pending" for item in items),
        applied=sum(item.state == "applied" for item in items),
        noop=sum(item.state == "noop" for item in items),
        blocked=sum(item.state == "blocked" for item in items),
    )


def _write_note_atomic(path: Path, raw: bytes, mode: int) -> None:
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        dir=path.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        os.fchmod(handle.fileno(), mode)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temp_path, path)
    except BaseException:
        handle.close()
        temp_path.unlink(missing_ok=True)
        raise


def apply_manifest(
    vault: Path,
    manifest_path: Path,
    approval_path: Path,
    *,
    expectation: ApprovalExpectation,
    apply: bool,
) -> ApplyReport:
    vault = vault.resolve()
    manifest = _validate_approval_and_manifest(
        vault, manifest_path, approval_path, expectation
    )
    preflight: list[ApplyItem] = []
    pending_bytes: dict[str, tuple[bytes, int]] = {}
    for manifest_item in manifest.items:
        path = vault / manifest_item.path
        if not path.is_file():
            preflight.append(ApplyItem(manifest_item.path, "blocked", dict(manifest_item.deterministic_updates), ""))
            continue
        current = path.read_bytes()
        current_sha = _sha256(current)
        if current_sha == manifest_item.source_sha256:
            document = parse_frontmatter(path)
            identity = resolve_identity(document)
            if identity.key != manifest_item.identity.key:
                raise ManifestValidationError(
                    f"identity no longer matches approved manifest for {manifest_item.path}"
                )
            rendered = render_deterministic_updates(
                document, manifest_item.deterministic_updates
            )
            if _sha256(rendered) != manifest_item.expected_post_sha256:
                raise ManifestValidationError(
                    f"renderer hash mismatch for {manifest_item.path}"
                )
            preflight.append(
                ApplyItem(
                    manifest_item.path,
                    "pending",
                    dict(manifest_item.deterministic_updates),
                    current_sha,
                )
            )
            pending_bytes[manifest_item.path] = (
                rendered,
                stat.S_IMODE(path.stat().st_mode),
            )
        elif current_sha == manifest_item.expected_post_sha256:
            document = parse_frontmatter(path)
            if resolve_identity(document).key != manifest_item.identity.key:
                raise ManifestValidationError(
                    f"post-write identity mismatch for {manifest_item.path}"
                )
            preflight.append(
                ApplyItem(
                    manifest_item.path,
                    "noop",
                    dict(manifest_item.deterministic_updates),
                    current_sha,
                )
            )
        else:
            preflight.append(
                ApplyItem(
                    manifest_item.path,
                    "blocked",
                    dict(manifest_item.deterministic_updates),
                    current_sha,
                )
            )
    report = _report(preflight)
    if report.blocked:
        raise ManifestDriftError(
            f"manifest preflight blocked {report.blocked} Paper item(s)", report
        )
    if not apply:
        return report
    applied_items: list[ApplyItem] = []
    for item in preflight:
        if item.state == "pending":
            raw, mode = pending_bytes[item.path]
            path = vault / item.path
            _write_note_atomic(path, raw, mode)
            if _sha256(path.read_bytes()) != next(
                manifest_item.expected_post_sha256
                for manifest_item in manifest.items
                if manifest_item.path == item.path
            ):
                raise ManifestValidationError(f"post-write hash mismatch for {item.path}")
            applied_items.append(
                ApplyItem(item.path, "applied", item.updates, _sha256(path.read_bytes()))
            )
        else:
            applied_items.append(item)
    return _report(applied_items)


def _report_json(report: ApplyReport) -> str:
    return json.dumps(asdict(report), sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _emit_paper_pathspec(report: AuditReport) -> None:
    for item in report.items:
        sys.stdout.buffer.write(item.path.encode("utf-8") + b"\0")


def _verify_index(vault: Path, manifest: AuditReport) -> None:
    paper_paths = {item.path for item in manifest.items}
    tool_paths = {
        "skills/1-literature/paper-digest/scripts/backfill_paper_schema.py",
        "skills/1-literature/paper-digest/scripts/test_backfill_paper_schema.py",
    }
    staged_raw = _git(vault, "diff", "--cached", "--name-only", "-z", text=False)
    staged = {
        value.decode("utf-8")
        for value in staged_raw.split(b"\0")  # type: ignore[union-attr]
        if value
    }
    if staged != paper_paths | tool_paths:
        raise ManifestValidationError("staged path set does not match approved Papers plus tool files")
    expected_by_path = {item.path: item for item in manifest.items}
    for path in sorted(paper_paths):
        staged_bytes = _git(vault, "show", f":{path}", text=False)
        if _sha256(staged_bytes) != expected_by_path[path].expected_post_sha256:  # type: ignore[arg-type]
            raise ManifestValidationError(f"staged hash mismatch for {path}")
    patch = _git(vault, "diff", "--cached", "--unified=0", "--", "Papers", text=True)
    additions = []
    deletions = []
    for line in patch.splitlines():  # type: ignore[union-attr]
        if line.startswith("+") and not line.startswith("+++"):
            additions.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            deletions.append(line[1:])
    if deletions:
        raise ManifestValidationError("staged Paper patch contains deletions")
    type_lines = sum(line == "type: paper" for line in additions)
    arxiv_lines = sum(bool(re.fullmatch(r"arxiv_id: \S+", line)) for line in additions)
    if len(additions) != 357 or type_lines != 182 or arxiv_lines != 175:
        raise ManifestValidationError("staged Paper additions do not match 182 type and 175 arXiv lines")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--expected-manifest-commit", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-pending-approval-commit", required=True)
    parser.add_argument("--expected-pending-approval-sha256", required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--emit-paper-pathspec", action="store_true")
    modes.add_argument("--verify-index", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        vault = args.vault.resolve()
        expectation = ApprovalExpectation(
            manifest_commit=args.expected_manifest_commit,
            manifest_sha256=args.expected_manifest_sha256,
            pending_approval_commit=args.expected_pending_approval_commit,
            pending_approval_sha256=args.expected_pending_approval_sha256,
        )
        manifest_path = args.manifest if args.manifest.is_absolute() else vault / args.manifest
        approval_path = args.approval if args.approval.is_absolute() else vault / args.approval
        if args.emit_paper_pathspec:
            manifest = _validate_approval_and_manifest(
                vault, manifest_path, approval_path, expectation
            )
            apply_manifest(
                vault, manifest_path, approval_path,
                expectation=expectation, apply=False,
            )
            _emit_paper_pathspec(manifest)
            return 0
        if args.verify_index:
            manifest = _validate_approval_and_manifest(
                vault, manifest_path, approval_path, expectation
            )
            apply_manifest(
                vault, manifest_path, approval_path,
                expectation=expectation, apply=False,
            )
            _verify_index(vault, manifest)
            return 0
        report = apply_manifest(
            vault,
            manifest_path,
            approval_path,
            expectation=expectation,
            apply=args.apply,
        )
        sys.stdout.write(_report_json(report))
        return 0
    except BackfillValidationError as exc:
        print(str(exc), file=sys.stderr)
        if isinstance(exc, ManifestDriftError):
            print(_report_json(exc.report), file=sys.stderr, end="")
        return 2
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
