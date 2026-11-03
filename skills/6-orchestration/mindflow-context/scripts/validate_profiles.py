#!/usr/bin/env python3
"""Validate MindFlow project profiles without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Sequence


PROFILE_DIRECTORY = Path("Workbench/RepositoryProfiles")
PROJECT_DIRECTORY = Path("Workbench/PARA/Projects")
REPOSITORY_PROFILE_TYPE = "repository-profile"
REQUIRED_FIELDS = (
    "type",
    "repo_key",
    "repo_roots",
    "aliases",
    "domains",
    "entrypoints",
    "keywords",
    "verified_at",
)
LIST_FIELDS = {
    "repo_roots",
    "aliases",
    "domains",
    "entrypoints",
    "keywords",
    "workspace_entrypoints",
}
PATH_ERRORS = (OSError, RuntimeError, ValueError)
FORBIDDEN_WORKSPACE_PARTS = {"code", "worklog", ".git"}


@dataclass(frozen=True)
class Profile:
    path: Path
    repo_key: str
    repo_roots: tuple[Path, ...]
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    entrypoints: tuple[Path, ...]
    keywords: tuple[str, ...]
    verified_at: str
    workspace_root: Path | None
    workspace_entrypoint_values: tuple[str, ...]


MatchStatus = Literal["matched", "ambiguous", "not_found", "invalid"]


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    profile: Profile | None
    errors: tuple[str, ...]


PROJECT_STATUSES = {"planning", "active", "paused", "completed", "cancelled"}
ARCHIVED_PROJECT_STATUSES = {"completed", "cancelled"}
AREA_STATUSES = {"active", "paused"}
ARCHIVED_AREA_STATUS = "retired"
REVIEW_CADENCES = {"weekly", "monthly", "quarterly", "annual"}


@dataclass(frozen=True)
class Area:
    path: Path
    area_key: str
    owner: str
    responsibility: str
    standard: str
    status: str
    review_cadence: str
    last_reviewed: str | None
    domains: tuple[str, ...]


@dataclass(frozen=True)
class Resource:
    path: Path
    resource_key: str
    scope: str
    entrypoints: tuple[Path, ...]
    query: str | None
    review_cadence: str
    last_reviewed: str | None


@dataclass(frozen=True)
class ArchivedArea(Area):
    archived_at: str
    archive_reason: str
    final_outcome: str


@dataclass(frozen=True)
class ArchivedResource(Resource):
    archived_at: str
    archive_reason: str
    final_outcome: str


@dataclass(frozen=True)
class Project:
    path: Path
    project_key: str
    outcome: str
    completion_criteria: tuple[str, ...]
    status: str
    target_date: str | None
    workspace_root: Path
    repo_refs: tuple[str, ...]
    area_refs: tuple[str, ...]
    knowledge_entrypoints: tuple[Path, ...]


@dataclass(frozen=True)
class ArchivedProject(Project):
    archived_at: str
    archive_reason: str
    final_outcome: str
    code_provenance: tuple[str, ...]


@dataclass(frozen=True)
class ControlPlaneValidation:
    profiles: tuple[Profile, ...]
    projects: tuple[Project, ...]
    archived_projects: tuple[ArchivedProject, ...]
    areas: tuple[Area, ...]
    resources: tuple[Resource, ...]
    archived_areas: tuple[ArchivedArea, ...]
    archived_resources: tuple[ArchivedResource, ...]
    errors: tuple[str, ...]


ContextStatus = Literal[
    "matched", "ambiguous", "not_found", "invalid", "project_selection_required"
]


@dataclass(frozen=True)
class ContextResult:
    status: ContextStatus
    profile_key: str | None
    project_key: str | None
    project_keys: tuple[str, ...]
    project_path: Path | None
    vault_entrypoints: tuple[Path, ...]
    workspace_context: tuple[Path, ...]
    project_workspace_context: tuple[Path, ...]
    project_knowledge_entrypoints: tuple[Path, ...]
    errors: tuple[str, ...]


def _error(path: Path, message: str) -> ValueError:
    return ValueError(f"{path}: {message}")


def _strip_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote == '"':
            escaped = True
            continue
        if quote:
            if character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def _parse_scalar(value: str, path: Path, line_number: int) -> str | list[str]:
    value = _strip_comment(value).strip()
    if value == "[]":
        return []
    if value.startswith("[") or value.startswith("{"):
        raise _error(path, f"line {line_number}: unsupported inline collection")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, str | list[str]]:
    """Parse the supported, deliberately small YAML frontmatter subset."""

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise _error(path, "missing opening frontmatter delimiter")

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise _error(path, "missing closing frontmatter delimiter") from exc

    result: dict[str, str | list[str]] = {}
    list_parent: str | None = None
    for index, raw_line in enumerate(lines[1:closing_index], start=2):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        stripped = raw_line.strip()
        if stripped.startswith("-"):
            if not raw_line[0].isspace() or not stripped.startswith("- "):
                raise _error(path, f"line {index}: list item without a parent key")
            if list_parent is None or not (
                result[list_parent] == "" or isinstance(result[list_parent], list)
            ):
                raise _error(path, f"line {index}: list item without a parent key")
            if result[list_parent] == "":
                result[list_parent] = []
            raw_item = _strip_comment(stripped[2:]).strip()
            quoted_item = (
                len(raw_item) >= 2
                and raw_item[0] == raw_item[-1]
                and raw_item[0] in {"'", '"'}
            )
            if not quoted_item and re.match(r"^[^:]+:(?:\s|$)", raw_item):
                raise _error(path, f"line {index}: nested mappings are not supported")
            item = _parse_scalar(stripped[2:], path, index)
            if isinstance(item, list):
                raise _error(path, f"line {index}: unsupported inline collection")
            assert isinstance(result[list_parent], list)
            result[list_parent].append(item)
            continue

        if raw_line[0].isspace():
            raise _error(path, f"line {index}: nested mappings are not supported")
        if ":" not in raw_line:
            raise _error(path, f"line {index}: expected a top-level key/value pair")

        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        if not key:
            raise _error(path, f"line {index}: empty key")
        if key in result:
            raise _error(path, f"line {index}: duplicate key {key!r}")
        result[key] = _parse_scalar(raw_value, path, index)
        list_parent = key if result[key] == "" else None

    return result


def resolve_repo_root(vault: Path, value: str) -> Path:
    expanded = Path(value).expanduser()
    if not expanded.is_absolute():
        expanded = vault / expanded
    return expanded.resolve()


def resolve_workspace_root(vault: Path, value: str) -> Path:
    raw = Path(value)
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or len(raw.parts) != 2
        or raw.parts[0] != "Projects"
    ):
        raise ValueError("workspace_root must be Projects/<workspace>")
    resolved_vault = vault.resolve()
    projects_path = vault / "Projects"
    if projects_path.is_symlink():
        raise ValueError("Projects must not be a symlink")
    candidate = vault / raw
    if candidate.is_symlink():
        raise ValueError("workspace_root must not be a symlink")
    if not candidate.is_dir():
        raise ValueError("workspace_root must be an existing directory")
    projects_root = projects_path.resolve()
    resolved = candidate.resolve()
    if not projects_root.is_relative_to(resolved_vault):
        raise ValueError("Projects escapes the vault")
    if not resolved.is_relative_to(projects_root):
        raise ValueError("workspace_root escapes Projects")
    return resolved


def resolve_workspace_entrypoint(workspace_root: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or raw.suffix != ".md":
        raise ValueError("workspace entrypoint must be a relative Markdown file")
    if any(part in FORBIDDEN_WORKSPACE_PARTS for part in raw.parts):
        raise ValueError("workspace entrypoint enters a forbidden directory")
    candidate = workspace_root / raw
    if candidate.is_symlink():
        raise ValueError("workspace entrypoint must not be a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(workspace_root):
        raise ValueError("workspace entrypoint escapes workspace_root")
    if not resolved.is_file():
        raise ValueError("workspace entrypoint does not exist")
    relative = resolved.relative_to(workspace_root)
    if any(part in FORBIDDEN_WORKSPACE_PARTS for part in relative.parts):
        raise ValueError("workspace entrypoint resolves into a forbidden directory")
    return resolved


def workspace_context_paths(profile: Profile) -> tuple[Path, ...]:
    if profile.workspace_root is None:
        return ()
    values = ("main.md", "engineering.md", *profile.workspace_entrypoint_values)
    resolved = tuple(
        resolve_workspace_entrypoint(profile.workspace_root, value) for value in values
    )
    return tuple(dict.fromkeys(resolved))


def load_profile(path: Path, vault: Path) -> tuple[Profile | None, list[str]]:
    errors: list[str] = []
    try:
        data = parse_frontmatter(path)
    except PATH_ERRORS as exc:
        message = str(exc)
        if not message.startswith(f"{path}:"):
            message = f"{path}: cannot read or parse profile: {exc}"
        return None, [message]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"{path}: missing required field {field!r}")

    profile_type = data.get("type")
    if profile_type is not None and profile_type != REPOSITORY_PROFILE_TYPE:
        errors.append(f"{path}: type must be {REPOSITORY_PROFILE_TYPE!r}")

    repo_key_value = data.get("repo_key")
    repo_key = repo_key_value if isinstance(repo_key_value, str) else ""
    if repo_key_value is not None and (
        not isinstance(repo_key_value, str)
        or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", repo_key_value)
    ):
        errors.append(f"{path}: repo_key must be lowercase kebab-case")

    list_values: dict[str, list[str]] = {}
    for field in LIST_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(f"{path}: {field} must be a list of non-empty strings")
            continue
        list_values[field] = value

    for field in ("repo_roots", "domains", "entrypoints", "keywords"):
        if field in list_values and not list_values[field]:
            errors.append(f"{path}: {field} must contain at least one value")

    resolved_roots: list[Path] = []
    for value in list_values.get("repo_roots", []):
        try:
            root = resolve_repo_root(vault, value)
        except PATH_ERRORS as exc:
            errors.append(f"{path}: cannot resolve repo root {value!r}: {exc}")
            continue
        resolved_roots.append(root)
        try:
            root_is_directory = root.is_dir()
        except PATH_ERRORS as exc:
            errors.append(f"{path}: cannot inspect repo root {root}: {exc}")
            continue
        if not root_is_directory:
            errors.append(f"{path}: repo root does not exist: {root}")

    try:
        resolved_vault = vault.resolve()
    except PATH_ERRORS as exc:
        errors.append(f"{path}: cannot resolve vault root {vault}: {exc}")
        resolved_vault = None
    resolved_entrypoints: list[Path] = []
    for value in list_values.get("entrypoints", []):
        try:
            entrypoint = Path(value)
        except PATH_ERRORS as exc:
            errors.append(f"{path}: cannot interpret entrypoint {value!r}: {exc}")
            continue
        if entrypoint.is_absolute() or ".." in entrypoint.parts:
            errors.append(f"{path}: entrypoint must be a vault-relative path without '..': {value}")
            continue
        if resolved_vault is None:
            continue
        try:
            resolved = (resolved_vault / entrypoint).resolve()
        except PATH_ERRORS as exc:
            errors.append(f"{path}: cannot resolve entrypoint {value!r}: {exc}")
            continue
        if not resolved.is_relative_to(resolved_vault):
            errors.append(f"{path}: entrypoint escapes the vault: {value}")
            continue
        resolved_entrypoints.append(resolved)
        try:
            entrypoint_is_file = resolved.is_file()
        except PATH_ERRORS as exc:
            errors.append(f"{path}: cannot inspect entrypoint {value!r}: {exc}")
            continue
        if not entrypoint_is_file:
            errors.append(f"{path}: entrypoint does not exist: {resolved}")

    verified_at_value = data.get("verified_at")
    verified_at = verified_at_value if isinstance(verified_at_value, str) else ""
    if verified_at_value is not None:
        if not isinstance(verified_at_value, str):
            errors.append(f"{path}: verified_at must be an ISO date")
        else:
            try:
                date.fromisoformat(verified_at_value)
            except ValueError:
                errors.append(f"{path}: verified_at must be an ISO date")

    workspace_root_value = data.get("workspace_root")
    workspace_root: Path | None = None
    if workspace_root_value not in (None, ""):
        if not isinstance(workspace_root_value, str):
            errors.append(f"{path}: workspace_root must be a string")
        else:
            try:
                workspace_root = resolve_workspace_root(vault, workspace_root_value)
            except PATH_ERRORS as exc:
                errors.append(f"{path}: invalid workspace_root: {exc}")

    workspace_entrypoint_values = tuple(list_values.get("workspace_entrypoints", []))
    if workspace_entrypoint_values and workspace_root_value in (None, ""):
        errors.append(f"{path}: workspace_entrypoints requires workspace_root")

    if errors:
        return None, errors

    profile = Profile(
        path=path,
        repo_key=repo_key,
        repo_roots=tuple(resolved_roots),
        aliases=tuple(list_values["aliases"]),
        domains=tuple(list_values["domains"]),
        entrypoints=tuple(resolved_entrypoints),
        keywords=tuple(list_values["keywords"]),
        verified_at=verified_at,
        workspace_root=workspace_root,
        workspace_entrypoint_values=workspace_entrypoint_values,
    )
    try:
        workspace_context_paths(profile)
    except PATH_ERRORS as exc:
        return None, [f"{path}: invalid workspace context: {exc}"]
    return profile, []


def validate_vault(vault: Path) -> tuple[list[Profile], list[str]]:
    try:
        vault = vault.resolve()
    except PATH_ERRORS as exc:
        return [], [f"{vault}: cannot resolve vault root: {exc}"]
    profile_directory = vault / PROFILE_DIRECTORY
    try:
        profile_directory_is_directory = profile_directory.is_dir()
    except PATH_ERRORS as exc:
        return [], [f"{profile_directory}: cannot inspect profile directory: {exc}"]
    if not profile_directory_is_directory:
        return [], [f"{profile_directory}: profile directory does not exist"]

    try:
        profile_paths = sorted(
            path for path in profile_directory.iterdir() if path.match("*.md")
        )
    except PATH_ERRORS as exc:
        return [], [f"{profile_directory}: cannot list profile directory: {exc}"]

    profiles: list[Profile] = []
    errors: list[str] = []
    for path in profile_paths:
        profile, profile_errors = load_profile(path, vault)
        errors.extend(profile_errors)
        if profile is not None:
            profiles.append(profile)

    repo_keys: dict[str, list[Profile]] = {}
    identities: dict[str, list[Profile]] = {}
    roots: dict[Path, list[Profile]] = {}
    for profile in profiles:
        repo_keys.setdefault(profile.repo_key, []).append(profile)
        for identity in {profile.repo_key.casefold(), *(alias.casefold() for alias in profile.aliases)}:
            identities.setdefault(identity, []).append(profile)
        for root in set(profile.repo_roots):
            roots.setdefault(root, []).append(profile)

    for repo_key, claimants in sorted(repo_keys.items()):
        if len(claimants) > 1:
            paths = ", ".join(str(profile.path) for profile in claimants)
            errors.append(f"duplicate repo_key {repo_key!r}: {paths}")
    for identity, claimants in sorted(identities.items()):
        unique_claimants = {profile.path: profile for profile in claimants}
        if len(unique_claimants) > 1:
            paths = ", ".join(str(path) for path in sorted(unique_claimants))
            errors.append(f"ambiguous identity {identity!r}: {paths}")
    for root, claimants in sorted(roots.items(), key=lambda item: str(item[0])):
        if len(claimants) > 1:
            paths = ", ".join(str(profile.path) for profile in claimants)
            errors.append(f"ambiguous repo root {root}: {paths}")

    return profiles, errors


def match_profile(
    profiles: Sequence[Profile],
    repo_root: Path,
    repository_name: str | None = None,
) -> MatchResult:
    try:
        canonical_root = repo_root.resolve()
    except PATH_ERRORS as exc:
        return MatchResult("invalid", None, (f"cannot resolve repository root: {exc}",))

    root_claimants = [
        profile
        for profile in profiles
        if canonical_root in {root.resolve() for root in profile.repo_roots}
    ]
    if len(root_claimants) == 1:
        return MatchResult("matched", root_claimants[0], ())
    if len(root_claimants) > 1:
        paths = ", ".join(str(profile.path) for profile in root_claimants)
        return MatchResult(
            "ambiguous",
            None,
            (f"multiple profiles claim canonical root {canonical_root}: {paths}",),
        )

    if repository_name:
        identity = repository_name.casefold()
        identity_claimants = [
            profile
            for profile in profiles
            if identity
            in {profile.repo_key.casefold(), *(alias.casefold() for alias in profile.aliases)}
        ]
        if len(identity_claimants) == 1:
            return MatchResult("matched", identity_claimants[0], ())
        if len(identity_claimants) > 1:
            paths = ", ".join(str(profile.path) for profile in identity_claimants)
            return MatchResult(
                "ambiguous",
                None,
                (f"multiple profiles claim identity {repository_name!r}: {paths}",),
            )

    return MatchResult(
        "not_found",
        None,
        (f"no repository profile matches {canonical_root}",),
    )


def _missing_fields(
    data: dict[str, str | list[str]], path: Path, fields: tuple[str, ...]
) -> list[str]:
    return [f"{path}: missing required field {field!r}" for field in fields if field not in data]


def _string_value(
    data: dict[str, str | list[str]],
    path: Path,
    field: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> str:
    value = data.get(field)
    if not isinstance(value, str):
        if value is not None:
            errors.append(f"{path}: {field} must be a string")
        return ""
    if not allow_empty and not value.strip():
        errors.append(f"{path}: {field} must be non-empty")
    return value.strip()


def _list_value(
    data: dict[str, str | list[str]],
    path: Path,
    field: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    value = data.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        if value is not None:
            errors.append(f"{path}: {field} must be a list of non-empty strings")
        return ()
    if not allow_empty and not value:
        errors.append(f"{path}: {field} must contain at least one value")
    return tuple(item.strip() for item in value)


def _optional_date(
    data: dict[str, str | list[str]], path: Path, field: str, errors: list[str]
) -> str | None:
    value = data.get(field)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(f"{path}: {field} must be an ISO date")
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"{path}: {field} must be an ISO date")
    return value


def resolve_vault_entrypoint(vault: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("entrypoint must be a vault-relative path without '..'")
    resolved_vault = vault.resolve()
    resolved = (resolved_vault / raw).resolve()
    if not resolved.is_relative_to(resolved_vault):
        raise ValueError("entrypoint escapes the vault")
    if not resolved.exists():
        raise ValueError("entrypoint does not exist")
    if not resolved.is_file():
        raise ValueError("entrypoint must be a file")
    return resolved


def _parse_note(path: Path) -> tuple[dict[str, str | list[str]] | None, list[str]]:
    try:
        return parse_frontmatter(path), []
    except PATH_ERRORS as exc:
        message = str(exc)
        if not message.startswith(f"{path}:"):
            message = f"{path}: cannot read or parse note: {exc}"
        return None, [message]


def _validate_key(path: Path, field: str, value: str, errors: list[str]) -> None:
    if value and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        errors.append(f"{path}: {field} must be lowercase kebab-case")


def _load_area(path: Path, vault: Path, *, archived: bool) -> tuple[Area | ArchivedArea | None, list[str]]:
    data, errors = _parse_note(path)
    if data is None:
        return None, errors
    fields = (
        "type", "area_key", "owner", "responsibility", "standard", "status",
        "review_cadence", "last_reviewed", "domains",
    )
    archive_fields = ("archived_at", "archive_reason", "final_outcome")
    errors.extend(_missing_fields(data, path, fields + (archive_fields if archived else ())))
    note_type = _string_value(data, path, "type", errors)
    if note_type and note_type != "area":
        errors.append(f"{path}: type must be 'area'")
    area_key = _string_value(data, path, "area_key", errors)
    _validate_key(path, "area_key", area_key, errors)
    owner = _string_value(data, path, "owner", errors)
    responsibility = _string_value(data, path, "responsibility", errors)
    standard = _string_value(data, path, "standard", errors)
    status = _string_value(data, path, "status", errors)
    if archived:
        if status and status != ARCHIVED_AREA_STATUS:
            errors.append(f"{path}: archived area status must be retired")
    elif status and status not in AREA_STATUSES:
        errors.append(f"{path}: invalid area status {status!r}")
    cadence = _string_value(data, path, "review_cadence", errors)
    if cadence and cadence not in REVIEW_CADENCES:
        errors.append(f"{path}: invalid review cadence {cadence!r}")
    last_reviewed = _optional_date(data, path, "last_reviewed", errors)
    domains = _list_value(data, path, "domains", errors)
    if archived:
        archived_at = _optional_date(data, path, "archived_at", errors) or ""
        archive_reason = _string_value(data, path, "archive_reason", errors)
        final_outcome = _string_value(data, path, "final_outcome", errors)
    if errors:
        return None, errors
    common = dict(
        path=path.resolve(), area_key=area_key, owner=owner,
        responsibility=responsibility, standard=standard, status=status,
        review_cadence=cadence, last_reviewed=last_reviewed, domains=domains,
    )
    if archived:
        return ArchivedArea(
            **common, archived_at=archived_at, archive_reason=archive_reason,
            final_outcome=final_outcome,
        ), []
    return Area(**common), []


def load_area(path: Path, vault: Path) -> tuple[Area | None, list[str]]:
    area, errors = _load_area(path, vault, archived=False)
    return area if isinstance(area, Area) and not isinstance(area, ArchivedArea) else None, errors


def load_archived_area(path: Path, vault: Path) -> tuple[ArchivedArea | None, list[str]]:
    area, errors = _load_area(path, vault, archived=True)
    return area if isinstance(area, ArchivedArea) else None, errors


def _load_resource(
    path: Path, vault: Path, *, archived: bool
) -> tuple[Resource | ArchivedResource | None, list[str]]:
    data, errors = _parse_note(path)
    if data is None:
        return None, errors
    fields = (
        "type", "resource_key", "scope", "entrypoints", "query",
        "review_cadence", "last_reviewed",
    )
    archive_fields = ("archived_at", "archive_reason", "final_outcome")
    errors.extend(_missing_fields(data, path, fields + (archive_fields if archived else ())))
    note_type = _string_value(data, path, "type", errors)
    if note_type and note_type != "resource":
        errors.append(f"{path}: type must be 'resource'")
    resource_key = _string_value(data, path, "resource_key", errors)
    _validate_key(path, "resource_key", resource_key, errors)
    scope = _string_value(data, path, "scope", errors)
    entrypoint_values = _list_value(data, path, "entrypoints", errors)
    query_value = data.get("query")
    query = query_value.strip() if isinstance(query_value, str) and query_value.strip() else None
    if query_value is not None and not isinstance(query_value, str):
        errors.append(f"{path}: query must be a string")
    entrypoints: list[Path] = []
    for value in entrypoint_values:
        try:
            entrypoints.append(resolve_vault_entrypoint(vault, value))
        except PATH_ERRORS as exc:
            errors.append(f"{path}: invalid entrypoint {value!r}: {exc}")
    if not entrypoint_values and query is None:
        errors.append(f"{path}: resource requires an entrypoint or query")
    cadence = _string_value(data, path, "review_cadence", errors)
    if cadence and cadence not in REVIEW_CADENCES:
        errors.append(f"{path}: invalid review cadence {cadence!r}")
    last_reviewed = _optional_date(data, path, "last_reviewed", errors)
    if archived:
        archived_at = _optional_date(data, path, "archived_at", errors) or ""
        archive_reason = _string_value(data, path, "archive_reason", errors)
        final_outcome = _string_value(data, path, "final_outcome", errors)
    if errors:
        return None, errors
    common = dict(
        path=path.resolve(), resource_key=resource_key, scope=scope,
        entrypoints=tuple(entrypoints), query=query, review_cadence=cadence,
        last_reviewed=last_reviewed,
    )
    if archived:
        return ArchivedResource(
            **common, archived_at=archived_at, archive_reason=archive_reason,
            final_outcome=final_outcome,
        ), []
    return Resource(**common), []


def load_resource(path: Path, vault: Path) -> tuple[Resource | None, list[str]]:
    resource, errors = _load_resource(path, vault, archived=False)
    return resource if isinstance(resource, Resource) and not isinstance(resource, ArchivedResource) else None, errors


def load_archived_resource(
    path: Path, vault: Path
) -> tuple[ArchivedResource | None, list[str]]:
    resource, errors = _load_resource(path, vault, archived=True)
    return resource if isinstance(resource, ArchivedResource) else None, errors


def _load_project(
    path: Path,
    vault: Path,
    profiles_by_key: dict[str, Profile],
    areas_by_key: dict[str, Area],
    *,
    archived: bool,
) -> tuple[Project | ArchivedProject | None, list[str]]:
    data, errors = _parse_note(path)
    if data is None:
        return None, errors
    fields = (
        "type", "project_key", "outcome", "completion_criteria", "status",
        "target_date", "workspace_root", "repo_refs", "area_refs",
        "knowledge_entrypoints",
    )
    archive_fields = ("archived_at", "archive_reason", "final_outcome", "code_provenance")
    errors.extend(_missing_fields(data, path, fields + (archive_fields if archived else ())))
    note_type = _string_value(data, path, "type", errors)
    if note_type and note_type != "project":
        errors.append(f"{path}: type must be 'project'")
    project_key = _string_value(data, path, "project_key", errors)
    _validate_key(path, "project_key", project_key, errors)
    outcome = _string_value(data, path, "outcome", errors)
    completion = _list_value(data, path, "completion_criteria", errors, allow_empty=False)
    status = _string_value(data, path, "status", errors)
    if archived:
        if status and status not in ARCHIVED_PROJECT_STATUSES:
            errors.append(f"{path}: archived status must be completed or cancelled")
    elif status and status not in PROJECT_STATUSES:
        errors.append(f"{path}: invalid status {status!r}")
    target_date = _optional_date(data, path, "target_date", errors)
    workspace_value = _string_value(data, path, "workspace_root", errors)
    workspace_root: Path | None = None
    if workspace_value:
        try:
            workspace_root = resolve_workspace_root(vault, workspace_value)
        except PATH_ERRORS as exc:
            errors.append(f"{path}: invalid workspace_root: {exc}")
    repo_refs = _list_value(data, path, "repo_refs", errors, allow_empty=False)
    area_refs = _list_value(data, path, "area_refs", errors)
    knowledge_values = _list_value(data, path, "knowledge_entrypoints", errors)
    for value in repo_refs:
        if value not in profiles_by_key:
            errors.append(f"{path}: unknown repo_ref {value!r}")
    for value in area_refs:
        if value not in areas_by_key:
            errors.append(f"{path}: unknown area_ref {value!r}")
    knowledge: list[Path] = []
    for value in knowledge_values:
        try:
            knowledge.append(resolve_vault_entrypoint(vault, value))
        except PATH_ERRORS as exc:
            errors.append(f"{path}: invalid knowledge entrypoint {value!r}: {exc}")
    if archived:
        archived_at = _optional_date(data, path, "archived_at", errors) or ""
        archive_reason = _string_value(data, path, "archive_reason", errors)
        final_outcome = _string_value(data, path, "final_outcome", errors)
        code_provenance = _list_value(data, path, "code_provenance", errors, allow_empty=False)
    if errors or workspace_root is None:
        return None, errors
    common = dict(
        path=path.resolve(), project_key=project_key, outcome=outcome,
        completion_criteria=completion, status=status, target_date=target_date,
        workspace_root=workspace_root, repo_refs=repo_refs, area_refs=area_refs,
        knowledge_entrypoints=tuple(knowledge),
    )
    if archived:
        return ArchivedProject(
            **common, archived_at=archived_at, archive_reason=archive_reason,
            final_outcome=final_outcome, code_provenance=code_provenance,
        ), []
    return Project(**common), []


def load_project(
    path: Path, vault: Path, profiles_by_key: dict[str, Profile], areas_by_key: dict[str, Area]
) -> tuple[Project | None, list[str]]:
    project, errors = _load_project(
        path, vault, profiles_by_key, areas_by_key, archived=False
    )
    return project if isinstance(project, Project) and not isinstance(project, ArchivedProject) else None, errors


def load_archived_project(
    path: Path, vault: Path, profiles_by_key: dict[str, Profile], areas_by_key: dict[str, Area]
) -> tuple[ArchivedProject | None, list[str]]:
    project, errors = _load_project(
        path, vault, profiles_by_key, areas_by_key, archived=True
    )
    return project if isinstance(project, ArchivedProject) else None, errors


def project_workspace_context_paths(project: Project) -> tuple[Path, ...]:
    return tuple(
        resolve_workspace_entrypoint(project.workspace_root, value)
        for value in ("main.md", "engineering.md")
    )


def _scan_notes(directory: Path, *, exclude: set[str] | None = None) -> list[Path]:
    if not directory.is_dir():
        return []
    excluded = exclude or set()
    return sorted(
        path for path in directory.iterdir() if path.suffix == ".md" and path.name not in excluded
    )


def validate_para_assets(
    vault: Path,
) -> tuple[list[Area], list[Resource], list[ArchivedArea], list[ArchivedResource], list[str]]:
    areas: list[Area] = []
    resources: list[Resource] = []
    archived_areas: list[ArchivedArea] = []
    archived_resources: list[ArchivedResource] = []
    errors: list[str] = []
    for path in _scan_notes(vault / "Workbench/PARA/Areas"):
        item, item_errors = load_area(path, vault)
        errors.extend(item_errors)
        if item is not None:
            areas.append(item)
    for path in _scan_notes(vault / "Workbench/PARA/Resources", exclude={"_index.md"}):
        item, item_errors = load_resource(path, vault)
        errors.extend(item_errors)
        if item is not None:
            resources.append(item)
    for path in _scan_notes(vault / "Workbench/PARA/Archives/Areas"):
        item, item_errors = load_archived_area(path, vault)
        errors.extend(item_errors)
        if item is not None:
            archived_areas.append(item)
    for path in _scan_notes(vault / "Workbench/PARA/Archives/Resources"):
        item, item_errors = load_archived_resource(path, vault)
        errors.extend(item_errors)
        if item is not None:
            archived_resources.append(item)
    for label, items, key_name in (
        ("area", areas, "area_key"), ("resource", resources, "resource_key")
    ):
        seen: dict[str, Path] = {}
        for item in items:
            key = getattr(item, key_name)
            if key in seen:
                errors.append(f"duplicate {label} key {key!r}: {seen[key]}, {item.path}")
            seen[key] = item.path
    return areas, resources, archived_areas, archived_resources, errors


def validate_projects(
    vault: Path, profiles_by_key: dict[str, Profile], areas_by_key: dict[str, Area]
) -> tuple[list[Project], list[ArchivedProject], list[str]]:
    projects: list[Project] = []
    archived: list[ArchivedProject] = []
    errors: list[str] = []
    for path in _scan_notes(vault / PROJECT_DIRECTORY):
        item, item_errors = load_project(path, vault, profiles_by_key, areas_by_key)
        errors.extend(item_errors)
        if item is not None:
            projects.append(item)
    for path in _scan_notes(vault / "Workbench/PARA/Archives/Projects"):
        item, item_errors = load_archived_project(path, vault, profiles_by_key, areas_by_key)
        errors.extend(item_errors)
        if item is not None:
            archived.append(item)
    seen: dict[str, Path] = {}
    for item in (*projects, *archived):
        if item.project_key in seen:
            errors.append(
                f"duplicate project_key {item.project_key!r}: {seen[item.project_key]}, {item.path}"
            )
        seen[item.project_key] = item.path
    return projects, archived, errors


def validate_control_plane(vault: Path) -> ControlPlaneValidation:
    profiles, profile_errors = validate_vault(vault)
    areas, resources, archived_areas, archived_resources, asset_errors = validate_para_assets(vault)
    profiles_by_key = {profile.repo_key: profile for profile in profiles}
    areas_by_key = {area.area_key: area for area in areas}
    projects, archived_projects, project_errors = validate_projects(
        vault, profiles_by_key, areas_by_key
    )
    errors = tuple(dict.fromkeys((*profile_errors, *asset_errors, *project_errors)))
    return ControlPlaneValidation(
        profiles=tuple(profiles), projects=tuple(projects),
        archived_projects=tuple(archived_projects), areas=tuple(areas),
        resources=tuple(resources), archived_areas=tuple(archived_areas),
        archived_resources=tuple(archived_resources), errors=errors,
    )


def resolve_context(
    vault: Path, repo_root: Path, project_key: str | None = None
) -> ContextResult:
    control = validate_control_plane(vault)
    if control.errors:
        return ContextResult(
            "invalid", None, None, (), None, (), (), (), (), control.errors
        )
    matched = match_profile(control.profiles, repo_root, repo_root.name)
    if matched.status != "matched" or matched.profile is None:
        return ContextResult(
            matched.status, None, None, (), None, (), (), (), (), matched.errors
        )
    profile = matched.profile
    matching_projects = sorted(
        (project for project in control.projects if profile.repo_key in project.repo_refs),
        key=lambda project: project.project_key,
    )
    project_keys = tuple(project.project_key for project in matching_projects)
    if project_key is None and project_keys:
        return ContextResult(
            "project_selection_required", profile.repo_key, None, project_keys,
            None, profile.entrypoints, workspace_context_paths(profile), (), (),
            ("explicit project_key required",),
        )
    selected = next(
        (project for project in matching_projects if project.project_key == project_key), None
    )
    if project_key is not None and selected is None:
        return ContextResult(
            "invalid", profile.repo_key, None, project_keys, None,
            profile.entrypoints, workspace_context_paths(profile), (), (),
            (f"project {project_key!r} does not reference profile {profile.repo_key!r}",),
        )
    return ContextResult(
        "matched", profile.repo_key, selected.project_key if selected else None,
        project_keys, selected.path if selected else None, profile.entrypoints,
        workspace_context_paths(profile),
        project_workspace_context_paths(selected) if selected else (),
        selected.knowledge_entrypoints if selected else (), (),
    )


def _write_fixture_profile(
    vault: Path,
    filename: str,
    *,
    repo_key: str = "pi",
    repo_root: str,
    entrypoint: str = "DomainMaps/VLA.md",
    include_keywords: bool = True,
    profile_type: str = REPOSITORY_PROFILE_TYPE,
) -> Path:
    profile_directory = vault / PROFILE_DIRECTORY
    profile_directory.mkdir(parents=True, exist_ok=True)
    keywords = "keywords:\n  - ACP\n" if include_keywords else ""
    profile = profile_directory / filename
    profile.write_text(
        "---\n"
        f"type: {profile_type}\n"
        f"repo_key: {repo_key}\n"
        "repo_roots:\n"
        f"  - {repo_root}\n"
        "aliases: []\n"
        "domains:\n"
        "  - VLA\n"
        "entrypoints:\n"
        f"  - {entrypoint}\n"
        f"{keywords}"
        "verified_at: 2026-10-28\n"
        "---\n",
        encoding="utf-8",
    )
    return profile


def _prepare_fixture(vault: Path) -> None:
    (vault / "DomainMaps").mkdir(parents=True, exist_ok=True)
    (vault / "DomainMaps/VLA.md").write_text("# VLA\n", encoding="utf-8")


def run_self_tests() -> int:
    results: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory() as temporary_directory:
        base = Path(temporary_directory)

        valid_vault = base / "valid"
        _prepare_fixture(valid_vault)
        valid_repo = base / "valid-repo"
        valid_repo.mkdir()
        _write_fixture_profile(valid_vault, "pi.md", repo_root=str(valid_repo))
        _, valid_errors = validate_vault(valid_vault)
        results.append(("valid", not valid_errors, "; ".join(valid_errors)))

        missing_field_vault = base / "missing-field"
        _prepare_fixture(missing_field_vault)
        _write_fixture_profile(
            missing_field_vault,
            "pi.md",
            repo_root=str(valid_repo),
            include_keywords=False,
        )
        _, missing_field_errors = validate_vault(missing_field_vault)
        results.append(
            (
                "missing field",
                any("keywords" in error for error in missing_field_errors),
                "; ".join(missing_field_errors),
            )
        )

        stale_root_vault = base / "stale-root"
        _prepare_fixture(stale_root_vault)
        _write_fixture_profile(stale_root_vault, "pi.md", repo_root=str(base / "missing-repo"))
        _, stale_root_errors = validate_vault(stale_root_vault)
        results.append(
            (
                "stale root",
                any("repo root does not exist" in error for error in stale_root_errors),
                "; ".join(stale_root_errors),
            )
        )

        missing_entrypoint_vault = base / "missing-entrypoint"
        _prepare_fixture(missing_entrypoint_vault)
        _write_fixture_profile(
            missing_entrypoint_vault,
            "pi.md",
            repo_root=str(valid_repo),
            entrypoint="DomainMaps/Missing.md",
        )
        _, missing_entrypoint_errors = validate_vault(missing_entrypoint_vault)
        results.append(
            (
                "missing entrypoint",
                any("entrypoint does not exist" in error for error in missing_entrypoint_errors),
                "; ".join(missing_entrypoint_errors),
            )
        )

        ambiguous_vault = base / "ambiguous"
        _prepare_fixture(ambiguous_vault)
        first = _write_fixture_profile(
            ambiguous_vault, "first.md", repo_key="first", repo_root=str(valid_repo)
        )
        second = _write_fixture_profile(
            ambiguous_vault, "second.md", repo_key="second", repo_root=str(valid_repo)
        )
        _, ambiguous_errors = validate_vault(ambiguous_vault)
        results.append(
            (
                "ambiguous match",
                any(
                    "ambiguous repo root" in error and str(first) in error and str(second) in error
                    for error in ambiguous_errors
                ),
                "; ".join(ambiguous_errors),
            )
        )

        relative_vault = base / "relative-root"
        _prepare_fixture(relative_vault)
        relative_repo = relative_vault / "repos/pi"
        relative_repo.mkdir(parents=True)
        relative_profile_path = _write_fixture_profile(
            relative_vault, "pi.md", repo_root="repos/pi"
        )
        relative_profile, relative_load_errors = load_profile(relative_profile_path, relative_vault)
        _, relative_validation_errors = validate_vault(relative_vault)
        relative_errors = relative_load_errors + relative_validation_errors
        results.append(
            (
                "relative-root resolution",
                not relative_errors
                and relative_profile is not None
                and relative_profile.repo_roots == (relative_repo.resolve(),),
                "; ".join(relative_errors),
            )
        )

    passed = 0
    for name, success, detail in results:
        if success:
            passed += 1
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: {detail or 'assertion failed'}")
    if passed == len(results):
        print("self-test: 6/6 passed")
        return 0
    print(f"self-test: {passed}/6 passed")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--repository-name")
    parser.add_argument("--project-key")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()

    if arguments.self_test:
        return run_self_tests()

    control = validate_control_plane(arguments.vault)
    if control.errors:
        for error in control.errors:
            print(f"ERROR {error}")
        return 1

    if arguments.repo_root is not None:
        result = resolve_context(
            arguments.vault, arguments.repo_root, project_key=arguments.project_key
        )

        def relative(path: Path | None) -> str | None:
            if path is None:
                return None
            try:
                return str(path.resolve().relative_to(arguments.vault.resolve()))
            except PATH_ERRORS:
                return str(path)

        profile_path = None
        if result.profile_key is not None:
            profile = next(
                profile for profile in control.profiles if profile.repo_key == result.profile_key
            )
            profile_path = relative(profile.path)
        payload = {
            "status": result.status,
            "profile_key": result.profile_key,
            "profile_path": profile_path,
            "project_key": result.project_key,
            "project_keys": list(result.project_keys),
            "project_path": relative(result.project_path),
            "vault_entrypoints": [relative(path) for path in result.vault_entrypoints],
            "workspace_context": [relative(path) for path in result.workspace_context],
            "project_workspace_context": [
                relative(path) for path in result.project_workspace_context
            ],
            "project_knowledge_entrypoints": [
                relative(path) for path in result.project_knowledge_entrypoints
            ],
            "errors": list(result.errors),
        }
        if arguments.json:
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        elif result.status == "matched":
            print(f"matched {result.profile_key}: {profile_path}")
        else:
            for error in result.errors:
                print(f"ERROR {error}")
        return 0 if result.status == "matched" else 1

    unique_roots = {root for profile in control.profiles for root in profile.repo_roots}
    print(
        f"validated {len(control.profiles)} profile(s); "
        f"{len(unique_roots)} unique repo root(s); 0 errors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
