#!/usr/bin/env python3
"""Read-only Paper audit and frozen approval-candidate generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from paper_schema import (
    IdentityConfidence,
    PaperIdentity,
    ValidationIssue,
    classification_candidates,
    find_duplicate_groups,
    parse_frontmatter,
    render_deterministic_updates,
    resolve_identity,
    validate_paper,
)


MANIFEST_VERSION = 1


@dataclass(frozen=True)
class AuditItem:
    path: str
    source_sha256: str
    expected_post_sha256: str
    identity: PaperIdentity
    confidence: IdentityConfidence
    classification_candidates: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]
    deterministic_updates: Mapping[str, str]


@dataclass(frozen=True)
class AuditSummary:
    total: int
    arxiv_identity: int
    url_title_review: int
    duplicate_identity_groups: int
    errors: int
    needs_review: int


@dataclass(frozen=True)
class AuditReport:
    manifest_version: int
    items: tuple[AuditItem, ...]
    duplicate_groups: tuple[tuple[str, tuple[str, ...]], ...]
    summary: AuditSummary
    _vault_root: Path = field(compare=False, repr=False)


@dataclass(frozen=True)
class ApprovalReceipt:
    approval_version: int
    approval_status: str
    manifest_path: str
    manifest_commit: str
    manifest_sha256: str
    approved_type_additions: int
    approved_arxiv_additions: int
    approved_other_fields: int


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _issue_sort_key(issue: ValidationIssue) -> tuple[str, str, str]:
    return issue.severity, issue.code, issue.message


def audit_vault(vault: Path) -> AuditReport:
    vault = vault.resolve()
    papers_dir = vault / "Papers"
    if not papers_dir.is_dir():
        raise ValueError(f"missing Papers directory: {papers_dir}")

    documents = []
    parsed: dict[Path, object] = {}
    parse_failures: dict[Path, str] = {}
    for path in sorted(papers_dir.glob("*.md")):
        try:
            document = parse_frontmatter(path)
        except (OSError, ValueError) as exc:
            parse_failures[path] = str(exc)
        else:
            documents.append(document)
            parsed[path] = document

    duplicate_groups_raw = find_duplicate_groups(documents)
    duplicate_by_path: dict[Path, str] = {}
    duplicate_groups: list[tuple[str, tuple[str, ...]]] = []
    for key, paths in duplicate_groups_raw:
        relative_paths = tuple(path.relative_to(vault).as_posix() for path in paths)
        duplicate_groups.append((key, relative_paths))
        for path in paths:
            duplicate_by_path[path] = key

    items: list[AuditItem] = []
    for path in sorted(papers_dir.glob("*.md")):
        raw = path.read_bytes()
        source_sha = _sha256(raw)
        relative = path.relative_to(vault).as_posix()
        if path in parse_failures:
            identity = PaperIdentity("missing", None, None, None, None, "", "low")
            issues = (
                ValidationIssue("parse-error", "error", parse_failures[path]),
            )
            items.append(
                AuditItem(
                    path=relative,
                    source_sha256=source_sha,
                    expected_post_sha256=source_sha,
                    identity=identity,
                    confidence=identity.confidence,
                    classification_candidates=(),
                    issues=issues,
                    deterministic_updates={},
                )
            )
            continue

        document = parsed[path]
        identity = resolve_identity(document)  # type: ignore[arg-type]
        issues = list(validate_paper(document, mode="audit"))  # type: ignore[arg-type]
        if path in duplicate_by_path:
            issues.append(
                ValidationIssue(
                    "duplicate-identity",
                    "error",
                    f"strong identity appears in multiple notes: {duplicate_by_path[path]}",
                )
            )
        candidates, _ = classification_candidates(document)  # type: ignore[arg-type]
        updates: dict[str, str] = {}
        if document.frontmatter.get("type") is None:  # type: ignore[union-attr]
            updates["type"] = "paper"
        if identity.kind == "arxiv" and document.frontmatter.get("arxiv_id") is None:  # type: ignore[union-attr]
            assert identity.arxiv_id is not None
            updates["arxiv_id"] = identity.arxiv_id
        rendered = render_deterministic_updates(document, updates)  # type: ignore[arg-type]
        items.append(
            AuditItem(
                path=relative,
                source_sha256=source_sha,
                expected_post_sha256=_sha256(rendered),
                identity=identity,
                confidence=identity.confidence,
                classification_candidates=candidates,
                issues=tuple(sorted(issues, key=_issue_sort_key)),
                deterministic_updates=updates,
            )
        )

    errors = sum(
        1
        for item in items
        for issue in item.issues
        if issue.severity == "error"
    )
    needs_review = sum(
        1
        for item in items
        if any(issue.severity != "error" for issue in item.issues)
        or item.confidence != "high"
    )
    summary = AuditSummary(
        total=len(items),
        arxiv_identity=sum(item.identity.kind == "arxiv" for item in items),
        url_title_review=sum(item.identity.kind in {"url-title", "missing"} for item in items),
        duplicate_identity_groups=len(duplicate_groups),
        errors=errors,
        needs_review=needs_review,
    )
    return AuditReport(
        manifest_version=MANIFEST_VERSION,
        items=tuple(items),
        duplicate_groups=tuple(sorted(duplicate_groups)),
        summary=summary,
        _vault_root=vault,
    )


def _identity_json(identity: PaperIdentity) -> dict[str, object]:
    return asdict(identity)


def _issue_json(issue: ValidationIssue) -> dict[str, object]:
    return asdict(issue)


def report_to_dict(report: AuditReport) -> dict[str, object]:
    return {
        "manifest_version": report.manifest_version,
        "items": [
            {
                "path": item.path,
                "source_sha256": item.source_sha256,
                "expected_post_sha256": item.expected_post_sha256,
                "identity": _identity_json(item.identity),
                "confidence": item.confidence,
                "classification_candidates": list(item.classification_candidates),
                "issues": [_issue_json(issue) for issue in item.issues],
                "deterministic_updates": dict(item.deterministic_updates),
            }
            for item in report.items
        ],
        "duplicate_groups": [
            {"identity": key, "paths": list(paths)}
            for key, paths in report.duplicate_groups
        ],
        "summary": asdict(report.summary),
    }


def report_json_bytes(report: AuditReport) -> bytes:
    return (
        json.dumps(
            report_to_dict(report),
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def report_markdown_bytes(report: AuditReport) -> bytes:
    lines = [
        "# Paper classification and identity audit",
        "",
        f"- Manifest version: {report.manifest_version}",
        f"- Total: {report.summary.total}",
        f"- arXiv identities: {report.summary.arxiv_identity}",
        f"- URL/title review: {report.summary.url_title_review}",
        f"- Duplicate identity groups: {report.summary.duplicate_identity_groups}",
        f"- Hard errors: {report.summary.errors}",
        f"- Needs review: {report.summary.needs_review}",
        "",
        "## Review items",
        "",
    ]
    for item in report.items:
        if not item.issues:
            continue
        lines.append(f"### `{item.path}`")
        lines.append("")
        lines.append(f"- Identity: `{item.identity.key or 'missing'}`")
        lines.append(
            "- Classification candidates: "
            + (", ".join(item.classification_candidates) or "none")
        )
        for issue in item.issues:
            lines.append(f"- `{issue.severity}` `{issue.code}`: {issue.message}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _resolved_with_missing(path: Path) -> Path:
    path = path.absolute()
    missing: list[str] = []
    cursor = path
    while not cursor.exists() and cursor.parent != cursor:
        missing.append(cursor.name)
        cursor = cursor.parent
    resolved = cursor.resolve()
    for component in reversed(missing):
        resolved /= component
    return resolved


def _guard_output(path: Path, vault: Path) -> Path:
    papers_lexical = (vault / "Papers").absolute()
    papers_resolved = (vault / "Papers").resolve()
    lexical = path.absolute()
    resolved = _resolved_with_missing(path)
    if lexical.is_relative_to(papers_lexical) or resolved.is_relative_to(papers_resolved):
        raise ValueError(f"output must not be inside or alias Papers: {path}")
    return resolved


def _temporary_for(target: Path, data: bytes) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{target.name}.",
        dir=target.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    finally:
        handle.close()
    return temp_path


def write_report(report: AuditReport, *, json_path: Path, markdown_path: Path) -> None:
    json_resolved = _guard_output(json_path, report._vault_root)
    markdown_resolved = _guard_output(markdown_path, report._vault_root)
    if json_resolved == markdown_resolved:
        raise ValueError("JSON and Markdown outputs must resolve to distinct paths")
    json_temp: Path | None = None
    markdown_temp: Path | None = None
    try:
        json_temp = _temporary_for(json_path, report_json_bytes(report))
        markdown_temp = _temporary_for(markdown_path, report_markdown_bytes(report))
        try:
            os.replace(json_temp, json_path)
            json_temp = None
        except OSError as exc:
            raise OSError(f"failed to replace JSON output {json_path}: {exc}") from exc
        try:
            os.replace(markdown_temp, markdown_path)
            markdown_temp = None
        except OSError as exc:
            raise OSError(f"failed to replace Markdown output {markdown_path}: {exc}") from exc
    finally:
        for temp_path in (json_temp, markdown_temp):
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


def _git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def _write_atomic_single(path: Path, data: bytes) -> None:
    temp = _temporary_for(path, data)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def write_approval_candidate(
    manifest_path: Path, manifest_commit: str, output_path: Path
) -> ApprovalReceipt:
    if not re.fullmatch(r"[0-9a-f]{40}", manifest_commit):
        raise ValueError("manifest commit must be 40 lowercase hex characters")
    repo = _git_root(manifest_path.parent)
    manifest_absolute = manifest_path.resolve()
    try:
        manifest_relative = manifest_absolute.relative_to(repo).as_posix()
    except ValueError as exc:
        raise ValueError("manifest must be inside its Git repository") from exc
    _guard_output(output_path, repo)
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"{manifest_commit}:{manifest_relative}"]
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("manifest blob does not exist at supplied commit") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("committed manifest is not valid JSON") from exc
    if payload.get("manifest_version") != MANIFEST_VERSION or not isinstance(payload.get("items"), list):
        raise ValueError("committed manifest must use manifest version 1")
    type_additions = 0
    arxiv_additions = 0
    other_fields = 0
    for item in payload["items"]:
        updates = item.get("deterministic_updates", {}) if isinstance(item, dict) else {}
        if not isinstance(updates, dict):
            raise ValueError("manifest deterministic_updates must be mappings")
        type_additions += "type" in updates
        arxiv_additions += "arxiv_id" in updates
        other_fields += len(set(updates) - {"type", "arxiv_id"})
    if (len(payload["items"]), type_additions, arxiv_additions, other_fields) != (182, 182, 175, 0):
        raise ValueError("manifest does not match the approved 182/175/0 scope")
    receipt = ApprovalReceipt(
        approval_version=1,
        approval_status="pending",
        manifest_path=manifest_relative,
        manifest_commit=manifest_commit,
        manifest_sha256=_sha256(raw),
        approved_type_additions=type_additions,
        approved_arxiv_additions=arxiv_additions,
        approved_other_fields=other_fields,
    )
    data = (json.dumps(asdict(receipt), sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _write_atomic_single(output_path, data)
    return receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--mode", choices=("audit",), default="audit")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--write-approval-candidate", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--manifest-commit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        if args.write_approval_candidate is not None:
            if args.manifest is None or args.manifest_commit is None:
                raise ValueError("approval candidate requires --manifest and --manifest-commit")
            write_approval_candidate(
                args.manifest,
                args.manifest_commit,
                args.write_approval_candidate,
            )
            return 0
        if args.vault is None or args.json is None or args.markdown is None:
            raise ValueError("audit requires --vault, --json, and --markdown")
        report = audit_vault(args.vault)
        write_report(report, json_path=args.json, markdown_path=args.markdown)
        return 1 if report.summary.errors else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
