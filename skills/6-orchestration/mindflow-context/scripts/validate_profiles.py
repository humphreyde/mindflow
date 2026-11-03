#!/usr/bin/env python3
"""Validate MindFlow project profiles without third-party dependencies."""

from __future__ import annotations

import argparse
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path


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
LIST_FIELDS = {"repo_roots", "aliases", "domains", "entrypoints", "keywords"}
PATH_ERRORS = (OSError, RuntimeError, ValueError)


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

    if errors:
        return None, errors

    return (
        Profile(
            path=path,
            repo_key=repo_key,
            repo_roots=tuple(resolved_roots),
            aliases=tuple(list_values["aliases"]),
            domains=tuple(list_values["domains"]),
            entrypoints=tuple(resolved_entrypoints),
            keywords=tuple(list_values["keywords"]),
            verified_at=verified_at,
        ),
        [],
    )


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
    arguments = parser.parse_args()

    if arguments.self_test:
        return run_self_tests()

    profiles, errors = validate_vault(arguments.vault)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    unique_roots = {root for profile in profiles for root in profile.repo_roots}
    print(
        f"validated {len(profiles)} profile(s); "
        f"{len(unique_roots)} unique repo root(s); 0 errors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
