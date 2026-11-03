#!/usr/bin/env python3
"""Plan, apply, and roll back allowlisted Codex skill links for MindFlow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.mindflow_paths import resolve_vault_root  # noqa: E402


MANAGED_LINKS = {
    "paper-digest": "skills/1-literature/paper-digest",
    "daily-papers": "skills/1-literature/daily-papers",
    "github-trending": "skills/1-literature/github-trending",
    "research-insights": "skills/1-literature/research-insights",
    "mindflow-context": "skills/6-orchestration/mindflow-context",
}
RETIRE_ONLY = (
    "paper-reader",
    "daily-papers-fetch",
    "daily-papers-review",
    "daily-papers-notes",
    "author-graph",
    "generate-mocs",
)
ALLOWLIST = frozenset((*MANAGED_LINKS, *RETIRE_ONLY))


class PlanEntry(NamedTuple):
    name: str
    action: str
    active_path: Path
    target: Path | None


def _lexists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _require_contained(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} escapes Codex home: {path}") from exc
    return resolved


def _roots(vault: Path, codex_home: Path) -> tuple[Path, Path, Path, Path]:
    vault_root = resolve_vault_root(vault)
    home = codex_home.resolve()
    skills = home / "skills"
    archive = home / "skills-legacy"
    if _lexists(skills):
        _require_contained(skills, home, "skills root")
        if not skills.is_dir():
            raise ValueError(f"Codex skills root is not a directory: {skills}")
    if _lexists(archive):
        _require_contained(archive, home, "archive root")
        if not archive.is_dir():
            raise ValueError(f"Codex archive root is not a directory: {archive}")
    return vault_root, home, skills, archive


def plan_bootstrap(vault: Path, codex_home: Path) -> dict[str, PlanEntry]:
    vault_root, _, skills_root, _ = _roots(vault, codex_home)
    plan: dict[str, PlanEntry] = {}
    for name, relative in MANAGED_LINKS.items():
        source = (vault_root / relative).resolve()
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            raise ValueError(f"canonical skill source is missing: {source}")
        active = skills_root / name
        if not _lexists(active):
            action = "link"
        elif active.is_symlink():
            action = "noop" if active.resolve() == source else "archive-and-link"
        elif active.is_dir():
            action = "archive-and-link"
        else:
            raise ValueError(f"ordinary file conflict at allowlisted skill: {active}")
        plan[name] = PlanEntry(name, action, active, source)

    for name in RETIRE_ONLY:
        active = skills_root / name
        if not _lexists(active):
            action = "noop"
        elif active.is_symlink() or active.is_dir():
            action = "archive-only"
        else:
            raise ValueError(f"ordinary file conflict at allowlisted skill: {active}")
        plan[name] = PlanEntry(name, action, active, None)
    return plan


def tree_hash(path: Path) -> str:
    if not _lexists(path):
        raise ValueError(f"cannot hash missing path: {path}")
    digest = hashlib.sha256()

    def visit(current: Path, relative: str) -> None:
        encoded = relative.encode("utf-8", errors="surrogateescape")
        if current.is_symlink():
            digest.update(b"L\0" + encoded + b"\0")
            digest.update(os.readlink(current).encode("utf-8", errors="surrogateescape"))
        elif current.is_file():
            digest.update(b"F\0" + encoded + b"\0")
            with current.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif current.is_dir():
            digest.update(b"D\0" + encoded + b"\0")
            for child in sorted(current.iterdir(), key=lambda value: value.name):
                child_relative = f"{relative}/{child.name}" if relative else child.name
                visit(child, child_relative)
        else:
            raise ValueError(f"unsupported filesystem entry in skill tree: {current}")

    visit(path, "")
    return digest.hexdigest()


def _install_link(path: Path, target: Path) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.symlink_to(target)
        os.replace(temporary, path)
    finally:
        if _lexists(temporary):
            temporary.unlink()


def _remove_expected_link(path: Path, target: Path) -> None:
    if not path.is_symlink() or path.resolve() != target.resolve():
        raise ValueError(f"link drift prevents recovery: {path}")
    path.unlink()


def _reverse_partial(states: list[dict[str, object]]) -> None:
    for state in reversed(states):
        active = Path(str(state["active_path"]))
        target = Path(str(state["new_target"])) if state.get("new_target") else None
        archive = Path(str(state["archive_path"])) if state.get("archive_path") else None
        if state.get("linked"):
            if target is None:
                raise RuntimeError("internal recovery state omitted link target")
            _remove_expected_link(active, target)
        if state.get("archived"):
            if archive is None or not _lexists(archive):
                raise RuntimeError(f"internal recovery archive is missing: {archive}")
            if _lexists(active):
                raise RuntimeError(f"internal recovery target is occupied: {active}")
            os.replace(archive, active)


def _archive_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError(f"archive date must use YYYY-MM-DD: {value}")
    return value


def apply_bootstrap(vault: Path, codex_home: Path, archive_date: str) -> Path:
    archive_date = _archive_date(archive_date)
    vault_root, home, skills_root, archive_root = _roots(vault, codex_home)
    if ".worktrees" in vault_root.parts:
        raise ValueError(f"refusing global skill links to a worktree: {vault_root}")
    plan = plan_bootstrap(vault_root, home)
    dated_archive = archive_root / archive_date
    manifest = dated_archive / "manifest.json"
    actions = [entry for entry in plan.values() if entry.action != "noop"]

    if manifest.exists():
        if not actions:
            return manifest
        raise FileExistsError(f"archive manifest already exists: {manifest}")

    for entry in actions:
        if entry.action.startswith("archive"):
            archive_path = dated_archive / entry.name
            if _lexists(archive_path):
                raise FileExistsError(f"archive path already exists: {archive_path}")

    skills_root.mkdir(parents=True, exist_ok=True)
    dated_archive.mkdir(parents=True, exist_ok=True)
    states: list[dict[str, object]] = []
    operations: list[dict[str, object]] = []
    try:
        for entry in actions:
            archive_path = (
                dated_archive / entry.name if entry.action.startswith("archive") else None
            )
            state: dict[str, object] = {
                "active_path": str(entry.active_path),
                "archive_path": str(archive_path) if archive_path else "",
                "new_target": str(entry.target) if entry.target else "",
                "archived": False,
                "linked": False,
            }
            states.append(state)
            operation: dict[str, object] = {
                "name": entry.name,
                "action": entry.action,
                "active": f"skills/{entry.name}",
                "archive": (
                    f"skills-legacy/{archive_date}/{entry.name}" if archive_path else ""
                ),
                "archive_hash": "",
                "new_target": str(entry.target) if entry.target else "",
            }
            if archive_path is not None:
                operation["archive_hash"] = tree_hash(entry.active_path)
                os.replace(entry.active_path, archive_path)
                state["archived"] = True
            if entry.action in {"link", "archive-and-link"}:
                if entry.target is None:
                    raise RuntimeError(f"managed link has no target: {entry.name}")
                _install_link(entry.active_path, entry.target)
                state["linked"] = True
            operations.append(operation)

        payload = {
            "version": 1,
            "created_at": datetime.now().astimezone().isoformat(),
            "vault_root": str(vault_root),
            "codex_home": str(home),
            "archive_date": archive_date,
            "operations": operations,
        }
        with manifest.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        _reverse_partial(states)
        if manifest.exists():
            manifest.unlink()
        raise
    return manifest


def _manifest_path(value: object, home: Path, prefix: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"manifest has invalid {label}")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"manifest {label} escapes Codex home")
    if not relative.parts or relative.parts[0] != prefix:
        raise ValueError(f"manifest {label} escapes expected {prefix} root")
    candidate = home / relative
    try:
        candidate.parent.resolve().relative_to(home)
    except ValueError as exc:
        raise ValueError(f"manifest {label} escapes Codex home") from exc
    return candidate


def rollback(manifest: Path, codex_home: Path) -> None:
    home = codex_home.resolve()
    archive_root = home / "skills-legacy"
    if not manifest.is_file():
        raise ValueError(f"rollback manifest is missing: {manifest}")
    try:
        manifest.resolve().relative_to(archive_root.resolve())
    except ValueError as exc:
        raise ValueError(f"manifest escapes Codex skill archive: {manifest}") from exc

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or payload.get("codex_home") != str(home):
        raise ValueError("manifest does not match this Codex home")
    archive_date = _archive_date(str(payload.get("archive_date", "")))
    vault_value = payload.get("vault_root")
    if not isinstance(vault_value, str) or not Path(vault_value).is_absolute():
        raise ValueError("manifest has invalid vault root")
    vault_root = Path(vault_value).resolve()
    if manifest.resolve().parent != (archive_root / archive_date).resolve():
        raise ValueError("manifest path does not match its archive date")
    operations = payload.get("operations")
    if not isinstance(operations, list):
        raise ValueError("manifest operations must be an array")

    checked: list[tuple[dict[str, object], Path, Path | None, Path | None]] = []
    for raw in operations:
        if not isinstance(raw, dict):
            raise ValueError("manifest operation must be an object")
        name = raw.get("name")
        action = raw.get("action")
        if name not in ALLOWLIST or action not in {"link", "archive-and-link", "archive-only"}:
            raise ValueError("manifest contains a non-allowlisted operation")
        if raw.get("active") != f"skills/{name}":
            raise ValueError("manifest active path does not match its allowlisted name")
        expected_archive = (
            f"skills-legacy/{archive_date}/{name}" if str(action).startswith("archive") else ""
        )
        if raw.get("archive") != expected_archive:
            raise ValueError("manifest archive path does not match its allowlisted name")
        active = _manifest_path(raw.get("active"), home, "skills", "active path")
        archive = (
            _manifest_path(raw.get("archive"), home, "skills-legacy", "archive path")
            if raw.get("archive")
            else None
        )
        target = Path(str(raw["new_target"])) if raw.get("new_target") else None

        if action in {"link", "archive-and-link"}:
            expected_target = (vault_root / MANAGED_LINKS[str(name)]).resolve()
            if target is None or target.resolve() != expected_target:
                raise ValueError(f"manifest target drift prevents rollback: {name}")
            if not active.is_symlink() or active.resolve() != expected_target:
                raise ValueError(f"link drift prevents rollback: {active}")
        elif target is not None:
            raise ValueError(f"retire-only manifest has an unexpected target: {name}")
        elif _lexists(active):
            raise ValueError(f"active path drift prevents rollback: {active}")
        if archive is not None:
            if not _lexists(archive) or tree_hash(archive) != raw.get("archive_hash"):
                raise ValueError(f"archive drift prevents rollback: {archive}")
        checked.append((raw, active, archive, target))

    for raw, active, archive, target in reversed(checked):
        action = raw["action"]
        if action in {"link", "archive-and-link"}:
            if target is None:
                raise RuntimeError("validated rollback target unexpectedly missing")
            _remove_expected_link(active, target)
        if archive is not None:
            if _lexists(active):
                raise RuntimeError(f"rollback target became occupied: {active}")
            os.replace(archive, active)


def _plan_json(plan: dict[str, PlanEntry]) -> str:
    return json.dumps(
        {
            name: {
                "action": entry.action,
                "active": str(entry.active_path),
                "target": str(entry.target) if entry.target else None,
            }
            for name, entry in plan.items()
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)
    for command in ("plan", "apply"):
        child = subparsers.add_parser(command)
        child.add_argument("--codex-home", required=True, type=Path)
        if command == "apply":
            child.add_argument("--archive-date", required=True)
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--codex-home", required=True, type=Path)
    rollback_parser.add_argument("--manifest", required=True, type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    vault = resolve_vault_root(Path(__file__))
    if args.command == "plan":
        print(_plan_json(plan_bootstrap(vault, args.codex_home)))
    elif args.command == "apply":
        print(apply_bootstrap(vault, args.codex_home, args.archive_date))
    else:
        rollback(args.manifest, args.codex_home)
        print(f"rolled back: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
