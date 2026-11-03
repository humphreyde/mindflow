#!/usr/bin/env python3
"""Plan and apply a deterministic, read-only legacy notes migration."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence


PAPER_SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "skills/1-literature/paper-digest/scripts"
)
if str(PAPER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PAPER_SCRIPTS))

from paper_schema import (  # noqa: E402
    normalize_arxiv_id,
    normalize_doi,
    normalize_official_url,
    normalize_title,
    parse_frontmatter,
    resolve_identity,
)


MANIFEST_VERSION = 1
APPROVED_ROOTS = (
    "PaperNotes",
    "DailyPapers",
    "GitHubTrending",
    "ResearchSources",
    "ResearchNotes",
)
TOPIC_NAMES = {"GR00T-Series-Survey.md", "Pi-Series-Survey.md"}
BLOCKED_CONCEPTS = {"Pi06 Base Model.md"}
NAVIGATION_NAMES = {
    "PaperNotes.md",
    "_inbox.md",
    "VLA.md",
    "world model.md",
    "Sources.md",
    "Insights.md",
    "assets.md",
}
ARXIV_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|html|pdf)/|arxiv:\s*)(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
DOI_RE = re.compile(r"(?:doi\.org/|doi:\s*)(10\.\d{4,9}/[^\s)\]}>,]+)", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s)\]}>,]+", re.IGNORECASE)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SourceSnapshot:
    git_head: str
    git_status: tuple[str, ...]
    files: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MigrationItem:
    source_path: str
    source_sha256: str
    source_kind: str
    identity: Mapping[str, str | None]
    identity_confidence: str
    decision: str
    destination_path: str | None
    duplicate_group: str | None
    referenced_assets: tuple[str, ...]
    link_rewrites: tuple[tuple[str, str], ...]
    status: str
    reason: str


@dataclass(frozen=True)
class MigrationManifest:
    manifest_version: int
    source_root: str
    target_root: str
    source_snapshot: SourceSnapshot
    items: tuple[MigrationItem, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json_bytes(self) -> bytes:
        return (
            json.dumps(
                self.to_dict(), sort_keys=True, ensure_ascii=False, indent=2
            )
            + "\n"
        ).encode("utf-8")


def _git(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(source), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _is_excluded(relative: Path) -> bool:
    parts = relative.parts
    if not parts:
        return True
    if parts[0] == "PaperNotes":
        if any(part in {"_authors", "_concepts", "_code", "assets"} for part in parts[1:-1]):
            return True
        if relative.name in NAVIGATION_NAMES:
            return True
        return relative.suffix.lower() != ".md"
    if parts[0] == "ResearchSources":
        if relative.name in NAVIGATION_NAMES or relative.name.startswith("."):
            return True
        return relative.suffix.lower() != ".md"
    if parts[0] in {"DailyPapers", "GitHubTrending", "ResearchNotes"}:
        if relative.name.startswith("."):
            return True
        return relative.suffix.lower() != ".md"
    return True


def _iter_included_files(source: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for root_name in APPROVED_ROOTS:
        root = source / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and not _is_excluded(path.relative_to(source)):
                paths.append(path)
    return tuple(sorted(paths, key=lambda path: path.relative_to(source).as_posix()))


def snapshot_source(source: Path) -> SourceSnapshot:
    source = source.resolve()
    files = tuple(
        (path.relative_to(source).as_posix(), _sha256(path.read_bytes()))
        for path in _iter_included_files(source)
    )
    status = tuple(
        sorted(line for line in _git(source, "status", "--short").splitlines() if line)
    )
    return SourceSnapshot(
        git_head=_git(source, "rev-parse", "HEAD"),
        git_status=status,
        files=files,
    )


def _read_frontmatter(path: Path) -> Mapping[str, object]:
    try:
        return parse_frontmatter(path).frontmatter
    except ValueError:
        return {}


def _first_scalar(mapping: Mapping[str, object], names: Sequence[str]) -> str | None:
    for name in names:
        value = mapping.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _source_identity(path: Path) -> dict[str, str | None]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    frontmatter = _read_frontmatter(path)
    title = _first_scalar(frontmatter, ("title", "method_name")) or path.stem
    arxiv = normalize_arxiv_id(_first_scalar(frontmatter, ("arxiv_id", "arxiv")) or "")
    if arxiv is None:
        for value in frontmatter.values():
            if isinstance(value, str):
                match = ARXIV_RE.search(value)
                if match:
                    arxiv = normalize_arxiv_id(match.group(1))
                    break
    if arxiv is None:
        match = ARXIV_RE.search(text)
        if match:
            arxiv = normalize_arxiv_id(match.group(1))
    if arxiv is None:
        match = re.search(
            r"arxiv[^0-9]{0,30}(\d{4}\.\d{4,5})(?:v\d+)?",
            text,
            re.IGNORECASE,
        )
        if match:
            arxiv = normalize_arxiv_id(match.group(1))
    doi = normalize_doi(_first_scalar(frontmatter, ("doi",)) or "")
    if doi is None:
        match = DOI_RE.search(text)
        if match:
            doi = normalize_doi(match.group(1))
    official_url = None
    for key in ("paper", "website", "project_page", "arxiv_html", "code_url"):
        value = frontmatter.get(key)
        if isinstance(value, str):
            official_url = normalize_official_url(value)
            if official_url:
                break
    if official_url is None:
        normalized_urls = [
            normalized
            for raw_url in URL_RE.findall(text)
            if (normalized := normalize_official_url(raw_url)) is not None
        ]
        official_url = next(
            (url for url in normalized_urls if url.casefold().endswith(".pdf")),
            next(
                (url for url in normalized_urls if "github.com" not in url.casefold()),
                normalized_urls[0] if normalized_urls else None,
            ),
        )
    normalized = normalize_title(title)
    if arxiv:
        return {
            "kind": "arxiv",
            "key": f"arxiv:{arxiv}",
            "arxiv_id": arxiv,
            "doi": doi,
            "official_url": official_url,
            "normalized_title": normalized,
        }
    if doi:
        return {
            "kind": "doi",
            "key": f"doi:{doi}",
            "arxiv_id": None,
            "doi": doi,
            "official_url": official_url,
            "normalized_title": normalized,
        }
    if official_url and normalized:
        return {
            "kind": "url-title",
            "key": f"url-title:{official_url}#{normalized}",
            "arxiv_id": None,
            "doi": None,
            "official_url": official_url,
            "normalized_title": normalized,
        }
    return {
        "kind": "missing",
        "key": None,
        "arxiv_id": None,
        "doi": None,
        "official_url": official_url,
        "normalized_title": normalized,
    }


def _target_identities(target: Path) -> dict[str, str]:
    identities: dict[str, str] = {}
    for path in sorted((target / "Papers").glob("*.md")):
        try:
            identity = resolve_identity(parse_frontmatter(path))
        except ValueError:
            continue
        if identity.key and identity.confidence == "high":
            identities[identity.key] = path.relative_to(target).as_posix()
        frontmatter = _read_frontmatter(path)
        title = frontmatter.get("title")
        if isinstance(title, str):
            normalized_title = normalize_title(title)
            for field in ("paper", "website", "github"):
                value = frontmatter.get(field)
                if isinstance(value, str):
                    normalized_url = normalize_official_url(value)
                    if normalized_url:
                        identities[
                            f"url-title:{normalized_url}#{normalized_title}"
                        ] = path.relative_to(target).as_posix()
    return identities


def _safe_stem(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(words) or "LegacyPaper"


def _paper_destination(path: Path, identity: Mapping[str, str | None]) -> str:
    prefix = (identity.get("arxiv_id") or "legacy")[:4]
    return f"Papers/{prefix}-{_safe_stem(path.stem)}.md"


def _route_auxiliary(relative: Path) -> tuple[str, str]:
    if relative.parts[0] == "DailyPapers":
        return "import-daily", f"Workbench/daily/{relative.name}"
    if relative.parts[0] == "GitHubTrending":
        return "import-trending", f"Workbench/trending/{relative.name}"
    if relative.parts[:2] == ("ResearchSources", "Sources"):
        return "import-source", f"ResearchSources/Sources/{relative.name}"
    if relative.parts[:2] == ("ResearchSources", "Insights"):
        return "import-insight", f"ResearchSources/Insights/{relative.name}"
    if relative.parts[0] == "ResearchNotes":
        return "import-insight", f"ResearchSources/Insights/{relative.name}"
    raise ValueError(f"unsupported auxiliary path: {relative}")


def build_manifest(source: Path, target: Path) -> MigrationManifest:
    source = source.resolve()
    target = target.resolve()
    target_identities = _target_identities(target)
    candidates: list[tuple[Path, dict[str, str | None]]] = []
    for path in _iter_included_files(source):
        relative = path.relative_to(source)
        if relative.parts[0] == "PaperNotes" and relative.name not in TOPIC_NAMES and relative.name not in BLOCKED_CONCEPTS:
            candidates.append((path, _source_identity(path)))
    duplicate_counts: dict[str, int] = {}
    for _, identity in candidates:
        key = identity.get("key")
        if key:
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1

    items: list[MigrationItem] = []
    for path in _iter_included_files(source):
        relative = path.relative_to(source)
        source_path = relative.as_posix()
        identity: dict[str, str | None] = {
            "kind": "missing",
            "key": None,
            "arxiv_id": None,
            "doi": None,
            "official_url": None,
            "normalized_title": "",
        }
        duplicate_group = None
        if relative.parts[0] != "PaperNotes":
            decision, destination = _route_auxiliary(relative)
            status = "ready" if not (target / destination).exists() else "blocked"
            reason = "approved auxiliary route" if status == "ready" else "target exists"
            confidence = "review"
        elif relative.name in BLOCKED_CONCEPTS:
            decision, destination, status = "blocked", None, "blocked"
            reason = "misfiled concept requires semantic absorption"
            confidence = "review"
        elif relative.name in TOPIC_NAMES:
            decision = "import-topic"
            destination = f"Topics/{relative.name}"
            status = "ready" if not (target / destination).exists() else "blocked"
            reason = "approved series survey" if status == "ready" else "target exists"
            confidence = "review"
        else:
            identity = _source_identity(path)
            key = identity.get("key")
            confidence = "high" if identity["kind"] in {"arxiv", "doi"} else "review"
            if key and duplicate_counts.get(key, 0) > 1:
                duplicate_group = key
            if key in target_identities:
                decision = "merge-paper"
                destination = target_identities[key]
                status = "ready"
                reason = (
                    "high-confidence identity match"
                    if confidence == "high"
                    else "exact official URL and normalized title match"
                )
            else:
                decision = "import-paper"
                destination = _paper_destination(path, identity)
                if identity["kind"] == "missing":
                    status = "blocked"
                    reason = "missing paper identity"
                elif (target / destination).exists():
                    status = "blocked"
                    reason = "target exists without high-confidence identity match"
                else:
                    status = "ready"
                    reason = "old-only paper candidate"
        items.append(
            MigrationItem(
                source_path=source_path,
                source_sha256=_sha256(path.read_bytes()),
                source_kind=(
                    "paper" if relative.parts[0] == "PaperNotes" else relative.parts[0]
                ),
                identity=identity,
                identity_confidence=confidence,
                decision=decision,
                destination_path=destination,
                duplicate_group=duplicate_group,
                referenced_assets=(),
                link_rewrites=(),
                status=status,
                reason=reason,
            )
        )
    return MigrationManifest(
        manifest_version=MANIFEST_VERSION,
        source_root=str(source),
        target_root=str(target),
        source_snapshot=snapshot_source(source),
        items=tuple(sorted(items, key=lambda item: item.source_path)),
    )


def _markdown_report(manifest: MigrationManifest) -> bytes:
    counts: dict[str, int] = {}
    for item in manifest.items:
        key = f"{item.decision}:{item.status}"
        counts[key] = counts.get(key, 0) + 1
    lines = [
        "# Legacy notes migration plan",
        "",
        f"- Source HEAD: `{manifest.source_snapshot.git_head or 'untracked fixture'}`",
        f"- Included items: {len(manifest.items)}",
        "",
        "## Counts",
        "",
    ]
    lines.extend(f"- `{key}`: {counts[key]}" for key in sorted(counts))
    lines.extend(["", "## Items", ""])
    for item in manifest.items:
        lines.append(
            f"- `{item.source_path}` → `{item.destination_path or '-'}`: "
            f"**{item.decision}/{item.status}** — {item.reason}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _guard_output(source: Path, path: Path) -> Path:
    absolute = path.resolve()
    try:
        absolute.relative_to(source.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("migration output must not be inside source root")
    if "Papers" in absolute.parts:
        raise ValueError("migration reports must not be inside Papers")
    return absolute


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False)
    temporary = Path(handle.name)
    try:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temporary, path)
    except BaseException:
        handle.close()
        temporary.unlink(missing_ok=True)
        raise


def write_plan(
    manifest: MigrationManifest, source: Path, json_path: Path, markdown_path: Path
) -> None:
    json_path = _guard_output(source, json_path)
    markdown_path = _guard_output(source, markdown_path)
    if json_path == markdown_path:
        raise ValueError("JSON and Markdown outputs must be distinct")
    _atomic_write(json_path, manifest.to_json_bytes())
    _atomic_write(markdown_path, _markdown_report(manifest))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--source", required=True, type=Path)
    plan.add_argument("--target", required=True, type=Path)
    plan.add_argument("--json", required=True, type=Path)
    plan.add_argument("--markdown", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "plan":
        manifest = build_manifest(args.source, args.target)
        write_plan(manifest, args.source, args.json, args.markdown)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
