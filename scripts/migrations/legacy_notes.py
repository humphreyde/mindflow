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
EMBED_RE = re.compile(r"!\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


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


@dataclass(frozen=True)
class ApprovalReceipt:
    approval_version: int
    approval_status: str
    manifest_path: str
    manifest_sha256: str
    approval_basis: str

    def to_json_bytes(self) -> bytes:
        return (
            json.dumps(asdict(self), sort_keys=True, ensure_ascii=False, indent=2)
            + "\n"
        ).encode("utf-8")


@dataclass(frozen=True)
class AssetResult:
    destination_name: str
    reuse_existing: bool


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
        if relative.as_posix() == "DailyPapers/.history.json":
            return False
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


def _resolve_source_asset(source: Path, note: Path, reference: str) -> Path | None:
    reference_path = Path(reference)
    if reference_path.suffix.lower() in {"", ".md"} or reference_path.is_absolute():
        return None
    candidates = (
        (source / reference_path,)
        if reference.startswith("PaperNotes/")
        else (note.parent / reference_path, source / reference_path)
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(source)
        except ValueError:
            continue
        if resolved.is_file():
            return resolved
    matches = [path.resolve() for path in source.rglob(reference_path.name) if path.is_file()]
    return matches[0] if len(matches) == 1 else None


def _raw_asset_references(
    source: Path, note: Path
) -> tuple[tuple[str, Path | None], ...]:
    text = note.read_text(encoding="utf-8", errors="replace")
    return tuple(
        (reference, _resolve_source_asset(source, note, reference))
        for reference in dict.fromkeys(EMBED_RE.findall(text))
        if not reference.casefold().startswith(("http://", "https://"))
        and Path(reference).suffix.lower() not in {"", ".md"}
    )


def _snapshot_files(source: Path) -> tuple[Path, ...]:
    files = set(_iter_included_files(source))
    for note in tuple(files):
        if note.suffix.lower() != ".md":
            continue
        for _, asset in _raw_asset_references(source, note):
            if asset is not None:
                files.add(asset)
    return tuple(sorted(files, key=lambda path: path.relative_to(source).as_posix()))


def snapshot_source(source: Path) -> SourceSnapshot:
    source = source.resolve()
    files = tuple(
        (path.relative_to(source).as_posix(), _sha256(path.read_bytes()))
        for path in _snapshot_files(source)
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


def _publication_prefix(path: Path, identity: Mapping[str, str | None]) -> str:
    arxiv_id = identity.get("arxiv_id")
    if arxiv_id:
        return arxiv_id[:4]
    text = path.read_text(encoding="utf-8", errors="replace")
    date_row = re.search(r"\|\s*日期\s*\|([^|]+)\|", text)
    date_text = date_row.group(1).strip() if date_row else ""
    numeric = re.search(r"(20\d{2})[-/](\d{1,2})", date_text)
    if numeric:
        return f"{int(numeric.group(1)) % 100:02d}{int(numeric.group(2)):02d}"
    month_names = {
        name.casefold(): index
        for index, name in enumerate(
            (
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December",
            ),
            start=1,
        )
    }
    english = re.search(r"([A-Za-z]+)\s+\d{1,2},\s*(20\d{2})", date_text)
    if english and english.group(1).casefold() in month_names:
        return (
            f"{int(english.group(2)) % 100:02d}"
            f"{month_names[english.group(1).casefold()]:02d}"
        )
    raise ValueError(f"cannot derive YYMM publication prefix for {path}")


def _paper_destination(path: Path, identity: Mapping[str, str | None]) -> str:
    prefix = _publication_prefix(path, identity)
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


def _link_rewrites(
    path: Path,
    legacy_destinations: Mapping[str, str],
    asset_rewrites: Sequence[tuple[str, str]] = (),
) -> tuple[tuple[str, str], ...]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rewrites = list(asset_rewrites)
    rewrites.extend(
        (old, new)
        for old, new in sorted(legacy_destinations.items())
        if old in text
    )
    unresolved_pattern = re.compile(
        r"\[\[(PaperNotes/[^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]"
    )
    for match in unresolved_pattern.finditer(text):
        old_path = match.group(1)
        if old_path in legacy_destinations or any(
            old_path == old for old, _ in asset_rewrites
        ):
            continue
        readable = match.group(2) or Path(old_path).name
        rewrites.append((match.group(0), readable))
    return tuple(sorted(set(rewrites)))


def _asset_folder(destination: str) -> str:
    path = Path(destination)
    stem = re.sub(r"^\d{4}-", "", path.stem)
    if path.parts[0] == "Papers":
        return f"Papers/assets/{stem}"
    if path.parts[0] == "Topics":
        return f"Topics/assets/{stem}"
    raise ValueError(f"assets are unsupported for destination: {destination}")


def _plan_item_assets(
    source: Path,
    target: Path,
    note: Path,
    destination: str | None,
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...]]:
    if destination is None or not destination.startswith(("Papers/", "Topics/")):
        return (), (), ()
    references: list[str] = []
    rewrites: list[tuple[str, str]] = []
    missing: list[str] = []
    for old_reference, asset in _raw_asset_references(source, note):
        if asset is None:
            missing.append(old_reference)
            continue
        raw = asset.read_bytes()
        original_destination = f"{_asset_folder(destination)}/{asset.name}"
        existing_path = target / original_destination
        existing = existing_path.read_bytes() if existing_path.is_file() else None
        result = plan_asset_copy(asset.name, raw, existing=existing)
        destination_reference = f"{_asset_folder(destination)}/{result.destination_name}"
        references.append(asset.relative_to(source).as_posix())
        rewrites.append((old_reference, destination_reference))
    return (
        tuple(sorted(set(references))),
        tuple(sorted(set(rewrites))),
        tuple(sorted(set(missing))),
    )


def build_manifest(source: Path, target: Path) -> MigrationManifest:
    source = source.resolve()
    target = target.resolve()
    target_identities = _target_identities(target)
    included_files = _iter_included_files(source)
    candidates: list[tuple[Path, dict[str, str | None]]] = []
    for path in included_files:
        relative = path.relative_to(source)
        if relative.parts[0] == "PaperNotes" and relative.name not in TOPIC_NAMES and relative.name not in BLOCKED_CONCEPTS:
            candidates.append((path, _source_identity(path)))
    duplicate_counts: dict[str, int] = {}
    for _, identity in candidates:
        key = identity.get("key")
        if key:
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1

    legacy_destinations: dict[str, str] = {}
    for path in included_files:
        relative = path.relative_to(source)
        if relative.parts[0] != "PaperNotes" or relative.name in BLOCKED_CONCEPTS:
            continue
        if relative.name in TOPIC_NAMES:
            destination = f"Topics/{relative.name}"
        else:
            identity = _source_identity(path)
            key = identity.get("key")
            if identity["kind"] == "missing":
                continue
            destination = target_identities.get(key or "") or _paper_destination(
                path, identity
            )
        legacy_destinations[relative.with_suffix("").as_posix()] = Path(
            destination
        ).with_suffix("").as_posix()

    items: list[MigrationItem] = []
    for path in included_files:
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
        referenced_assets: tuple[str, ...] = ()
        asset_rewrites: tuple[tuple[str, str], ...] = ()
        missing_assets: tuple[str, ...] = ()
        if relative.parts[0] != "PaperNotes":
            decision, destination = _route_auxiliary(relative)
            is_history = relative.as_posix() == "DailyPapers/.history.json"
            status = (
                "ready"
                if is_history or not (target / destination).exists()
                else "blocked"
            )
            reason = (
                "merge deterministic history"
                if is_history
                else "approved auxiliary route"
                if status == "ready"
                else "target exists"
            )
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
            if identity["kind"] == "missing":
                decision = "import-paper"
                destination = None
                status = "blocked"
                reason = "missing paper identity"
            elif key in target_identities:
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
                if (target / destination).exists():
                    status = "blocked"
                    reason = "target exists without high-confidence identity match"
                else:
                    status = "ready"
                    reason = "old-only paper candidate"
        if decision in {"import-paper", "import-topic"}:
            referenced_assets, asset_rewrites, missing_assets = _plan_item_assets(
                source, target, path, destination
            )
            if missing_assets:
                status = "blocked"
                reason = "missing referenced assets: " + ", ".join(missing_assets)
        link_rewrites = _link_rewrites(path, legacy_destinations, asset_rewrites)
        if relative.parts[0] != "PaperNotes" and destination is not None:
            destination_path = target / destination
            if destination_path.is_file():
                source_raw = path.read_bytes()
                if relative.as_posix() == "DailyPapers/.history.json":
                    source_history = json.loads(source_raw)
                    target_history = json.loads(destination_path.read_bytes())
                    expected = (
                        json.dumps(
                            merge_history(source_history, target_history),
                            sort_keys=True,
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n"
                    ).encode("utf-8")
                else:
                    expected = _apply_rewrites(source_raw, link_rewrites)
                if destination_path.read_bytes() == expected:
                    status = "applied"
                    reason = "target matches deterministic migration output"
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
                referenced_assets=referenced_assets,
                link_rewrites=link_rewrites,
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


def _manifest_from_bytes(raw: bytes) -> MigrationManifest:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid migration manifest JSON") from exc
    if not isinstance(payload, dict) or payload.get("manifest_version") != 1:
        raise ValueError("unsupported migration manifest version")
    try:
        snapshot_raw = payload["source_snapshot"]
        snapshot = SourceSnapshot(
            git_head=snapshot_raw["git_head"],
            git_status=tuple(snapshot_raw["git_status"]),
            files=tuple(tuple(pair) for pair in snapshot_raw["files"]),
        )
        items = tuple(
            MigrationItem(
                source_path=item["source_path"],
                source_sha256=item["source_sha256"],
                source_kind=item["source_kind"],
                identity=dict(item["identity"]),
                identity_confidence=item["identity_confidence"],
                decision=item["decision"],
                destination_path=item["destination_path"],
                duplicate_group=item["duplicate_group"],
                referenced_assets=tuple(item["referenced_assets"]),
                link_rewrites=tuple(tuple(pair) for pair in item["link_rewrites"]),
                status=item["status"],
                reason=item["reason"],
            )
            for item in payload["items"]
        )
        return MigrationManifest(
            manifest_version=1,
            source_root=payload["source_root"],
            target_root=payload["target_root"],
            source_snapshot=snapshot,
            items=items,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("malformed migration manifest") from exc


def _relative_to_target(path: Path, target: Path) -> str:
    try:
        return path.resolve().relative_to(target.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("manifest and receipt must be inside target vault") from exc


def approve_manifest(
    manifest_path: Path,
    receipt_path: Path,
    basis: str,
    *,
    target: Path,
) -> ApprovalReceipt:
    manifest_absolute = manifest_path.resolve()
    _manifest_from_bytes(manifest_absolute.read_bytes())
    receipt = ApprovalReceipt(
        approval_version=1,
        approval_status="confirmed",
        manifest_path=_relative_to_target(manifest_absolute, target),
        manifest_sha256=_sha256(manifest_absolute.read_bytes()),
        approval_basis=basis,
    )
    _guard_output(Path("/nonexistent-source-root"), receipt_path)
    _atomic_write(receipt_path.resolve(), receipt.to_json_bytes())
    return receipt


def _load_receipt(receipt_path: Path) -> ApprovalReceipt:
    try:
        payload = json.loads(receipt_path.read_bytes())
        receipt = ApprovalReceipt(**payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("invalid migration approval receipt") from exc
    if receipt.approval_version != 1 or receipt.approval_status != "confirmed":
        raise ValueError("migration approval receipt is not confirmed")
    return receipt


def verify_receipt(
    manifest_path: Path, receipt_path: Path, *, target: Path
) -> ApprovalReceipt:
    receipt = _load_receipt(receipt_path)
    expected_path = _relative_to_target(manifest_path, target)
    if receipt.manifest_path != expected_path:
        raise ValueError("approval manifest path mismatch")
    if receipt.manifest_sha256 != _sha256(manifest_path.read_bytes()):
        raise ValueError("manifest SHA-256 mismatch")
    return receipt


def _safe_destination(target: Path, relative: str) -> Path:
    candidate = (target / relative).resolve()
    try:
        candidate.relative_to(target.resolve())
    except ValueError as exc:
        raise ValueError(f"destination escapes target: {relative}") from exc
    return candidate


def _exclusive_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _history_key(item: Mapping[str, object]) -> str:
    arxiv = normalize_arxiv_id(str(item.get("id") or item.get("arxiv_id") or ""))
    if arxiv:
        return f"arxiv:{arxiv}"
    doi = normalize_doi(str(item.get("doi") or ""))
    if doi:
        return f"doi:{doi}"
    return f"title:{normalize_title(str(item.get('title') or ''))}"


def merge_history(
    source: list[dict[str, object]], target: list[dict[str, object]]
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in (*source, *target):
        key = _history_key(item)
        if key in seen:
            continue
        seen.add(key)
        merged.append(dict(item))
    return merged


def _apply_rewrites(raw: bytes, rewrites: Sequence[tuple[str, str]]) -> bytes:
    for old, new in rewrites:
        raw = raw.replace(old.encode("utf-8"), new.encode("utf-8"))
    return raw


def plan_asset_copy(
    name: str, source: bytes, *, existing: bytes | None = None
) -> AssetResult:
    if existing is None:
        return AssetResult(name, False)
    if existing == source:
        return AssetResult(name, True)
    path = Path(name)
    suffix = _sha256(source)[:12]
    return AssetResult(f"{path.stem}-{suffix}{path.suffix}", False)


def _frontmatter_keys(raw: bytes, newline: bytes) -> set[str]:
    closing = raw.find(newline + b"---" + newline, len(b"---") + len(newline))
    if closing < 0:
        raise ValueError("legacy note has malformed frontmatter")
    frontmatter = raw[len(b"---") + len(newline) : closing]
    keys: set[str] = set()
    for line in frontmatter.split(newline):
        match = re.match(rb"([A-Za-z_][A-Za-z0-9_-]*):", line)
        if match:
            keys.add(match.group(1).decode("ascii"))
    return keys


def _render_imported_note(
    item: MigrationItem,
    source_bytes: bytes,
    rewrites: Sequence[tuple[str, str]],
    *,
    paper: bool,
) -> bytes:
    if source_bytes.startswith(b"---\r\n"):
        newline = b"\r\n"
    elif source_bytes.startswith(b"---\n"):
        newline = b"\n"
    else:
        raise ValueError("legacy Paper must have YAML frontmatter")
    keys = _frontmatter_keys(source_bytes, newline)
    additions: list[bytes] = []
    fields: list[tuple[str, str | None]] = []
    if paper:
        fields.extend(
            [
                ("type", "paper"),
                ("arxiv_id", item.identity.get("arxiv_id")),
                ("doi", item.identity.get("doi")),
            ]
        )
    fields.extend(
        [
        ("source_vault", "notes"),
        ("source_path", item.source_path),
        ("date_migrated", "2026-11-03"),
        ]
    )
    for key, value in fields:
        if key not in keys and value:
            additions.append(f"{key}: {value}".encode("utf-8") + newline)
    insertion = len(b"---") + len(newline)
    rendered = source_bytes[:insertion] + b"".join(additions) + source_bytes[insertion:]
    return _apply_rewrites(rendered, rewrites)


def render_imported_paper(
    item: MigrationItem,
    source_bytes: bytes,
    rewrites: Sequence[tuple[str, str]],
) -> bytes:
    return _render_imported_note(item, source_bytes, rewrites, paper=True)


def render_imported_topic(
    item: MigrationItem,
    source_bytes: bytes,
    rewrites: Sequence[tuple[str, str]],
) -> bytes:
    return _render_imported_note(item, source_bytes, rewrites, paper=False)


def _planned_asset_destination(
    item: MigrationItem, source_asset: Path, target: Path
) -> tuple[Path, bool]:
    if item.destination_path is None:
        raise ValueError(f"asset item has no destination: {item.source_path}")
    original = target / _asset_folder(item.destination_path) / source_asset.name
    existing = original.read_bytes() if original.is_file() else None
    result = plan_asset_copy(source_asset.name, source_asset.read_bytes(), existing=existing)
    return original.with_name(result.destination_name), result.reuse_existing


def apply_manifest(
    manifest_path: Path,
    receipt_path: Path,
    source: Path,
    target: Path,
    decisions: set[str],
) -> tuple[str, ...]:
    source = source.resolve()
    target = target.resolve()
    verify_receipt(manifest_path, receipt_path, target=target)
    manifest = _manifest_from_bytes(manifest_path.read_bytes())
    if Path(manifest.source_root).resolve() != source:
        raise ValueError("source root differs from frozen manifest")
    if Path(manifest.target_root).resolve() != target:
        raise ValueError("target root differs from frozen manifest")
    current_snapshot = snapshot_source(source)
    if current_snapshot != manifest.source_snapshot:
        raise ValueError("source hash drift from frozen manifest")
    selected = [
        item
        for item in manifest.items
        if item.decision in decisions and item.status == "ready"
    ]
    prepared: list[tuple[Path, bytes, bytes | None]] = []
    for item in selected:
        if item.destination_path is None:
            raise ValueError(f"ready item has no destination: {item.source_path}")
        source_path = source / item.source_path
        source_raw = source_path.read_bytes()
        if _sha256(source_raw) != item.source_sha256:
            raise ValueError(f"source hash drift: {item.source_path}")
        destination = _safe_destination(target, item.destination_path)
        is_history = item.source_path == "DailyPapers/.history.json"
        if (destination.exists() or destination.is_symlink()) and not is_history:
            raise ValueError(f"target exists: {item.destination_path}")
        if item.decision == "import-paper":
            raw = render_imported_paper(item, source_raw, item.link_rewrites)
        elif item.decision == "import-topic":
            raw = render_imported_topic(item, source_raw, item.link_rewrites)
        else:
            raw = _apply_rewrites(source_raw, item.link_rewrites)
        previous = destination.read_bytes() if destination.is_file() else None
        if is_history:
            try:
                source_history = json.loads(source_raw)
                target_history = json.loads(previous) if previous is not None else []
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("invalid daily history JSON") from exc
            if not isinstance(source_history, list) or not isinstance(target_history, list):
                raise ValueError("daily history must be a JSON list")
            raw = (
                json.dumps(
                    merge_history(source_history, target_history),
                    sort_keys=True,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ).encode("utf-8")
        prepared.append((destination, raw, previous))
        for asset_relative in item.referenced_assets:
            source_asset = (source / asset_relative).resolve()
            try:
                source_asset.relative_to(source)
            except ValueError as exc:
                raise ValueError(f"asset escapes source: {asset_relative}") from exc
            if not source_asset.is_file():
                raise ValueError(f"missing referenced asset: {asset_relative}")
            asset_destination, reuse_existing = _planned_asset_destination(
                item, source_asset, target
            )
            if reuse_existing:
                continue
            if asset_destination.exists() or asset_destination.is_symlink():
                raise ValueError(
                    f"target exists: {asset_destination.relative_to(target).as_posix()}"
                )
            prepared.append((asset_destination, source_asset.read_bytes(), None))
    created: list[Path] = []
    replaced: list[tuple[Path, bytes]] = []
    try:
        for destination, raw, previous in prepared:
            if previous is None:
                _exclusive_write(destination, raw)
                created.append(destination)
            else:
                _atomic_write(destination, raw)
                replaced.append((destination, previous))
    except BaseException:
        for path, previous in reversed(replaced):
            _atomic_write(path, previous)
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    if snapshot_source(source) != manifest.source_snapshot:
        raise ValueError("source hash drift during apply")
    return tuple(
        path.relative_to(target).as_posix()
        for path in (*created, *(path for path, _ in replaced))
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--source", required=True, type=Path)
    plan.add_argument("--target", required=True, type=Path)
    plan.add_argument("--json", required=True, type=Path)
    plan.add_argument("--markdown", required=True, type=Path)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--manifest", required=True, type=Path)
    approve.add_argument("--receipt", required=True, type=Path)
    approve.add_argument("--basis", required=True)
    approve.add_argument("--target", type=Path, default=Path("."))
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--manifest", required=True, type=Path)
    apply_parser.add_argument("--receipt", required=True, type=Path)
    apply_parser.add_argument("--source", type=Path)
    apply_parser.add_argument("--target", required=True, type=Path)
    apply_parser.add_argument("--decisions", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "plan":
        manifest = build_manifest(args.source, args.target)
        write_plan(manifest, args.source, args.json, args.markdown)
        return 0
    if args.command == "approve":
        approve_manifest(
            args.manifest,
            args.receipt,
            args.basis,
            target=args.target,
        )
        return 0
    if args.command == "apply":
        manifest = _manifest_from_bytes(args.manifest.read_bytes())
        source = args.source or Path(manifest.source_root)
        created = apply_manifest(
            args.manifest,
            args.receipt,
            source,
            args.target,
            {value for value in args.decisions.split(",") if value},
        )
        for path in created:
            print(path)
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
