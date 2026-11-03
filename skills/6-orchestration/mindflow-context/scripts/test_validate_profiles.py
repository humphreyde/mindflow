#!/usr/bin/env python3
"""Focused regressions for filesystem failures in validate_profiles.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_profiles import (
    _prepare_fixture,
    _write_fixture_profile,
    load_profile,
    validate_vault,
)


PATH_FAILURES = (OSError, RuntimeError, ValueError)


class ProfileSeparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.vault = Path(self.temporary_directory.name) / "vault"
        _prepare_fixture(self.vault)
        self.repo = Path(self.temporary_directory.name) / "repo"
        self.repo.mkdir()
        profile_directory = self.vault / "Workbench/RepositoryProfiles"
        profile_directory.mkdir(parents=True)
        self.profile_path = profile_directory / "pi.md"
        self._write_profile(self.profile_path, "repository-profile")

    def _write_profile(self, path: Path, profile_type: str) -> None:
        path.write_text(
            "---\n"
            f"type: {profile_type}\n"
            "repo_key: pi\n"
            "repo_roots:\n"
            f"  - {self.repo}\n"
            "aliases: []\n"
            "domains:\n"
            "  - VLA\n"
            "entrypoints:\n"
            "  - DomainMaps/VLA.md\n"
            "keywords:\n"
            "  - ACP\n"
            "verified_at: 2026-11-03\n"
            "---\n",
            encoding="utf-8",
        )

    def test_profiles_load_only_from_repository_profiles(self) -> None:
        legacy_directory = self.vault / "Workbench/PARA/Projects"
        legacy_directory.mkdir(parents=True)
        self._write_profile(legacy_directory / "legacy.md", "repository-profile")

        profiles, errors = validate_vault(self.vault)

        self.assertEqual(errors, [])
        self.assertEqual([profile.repo_key for profile in profiles], ["pi"])
        self.assertEqual(profiles[0].path, self.profile_path.resolve())

    def test_wrong_profile_type_is_rejected(self) -> None:
        wrong_path = self.vault / "Workbench/RepositoryProfiles/wrong.md"
        self._write_profile(wrong_path, "project")

        profile, errors = load_profile(wrong_path, self.vault)

        self.assertIsNone(profile)
        self.assertIn("type must be 'repository-profile'", "\n".join(errors))


class FilesystemFailureTests(unittest.TestCase):
    def test_repository_root_nul_returns_path_qualified_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory) / "vault"
            _prepare_fixture(vault)
            profile_path = _write_fixture_profile(vault, "pi.md", repo_root="bad\0root")

            try:
                profile, errors = load_profile(profile_path, vault)
            except PATH_FAILURES as exc:
                self.fail(f"repository-root failure escaped validation: {exc}")

            self.assertIsNone(profile)
            self.assertTrue(
                any(
                    error.startswith(f"{profile_path}: cannot resolve repo root 'bad\\x00root':")
                    for error in errors
                ),
                errors,
            )

    def test_repository_root_permission_denied_returns_path_qualified_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            vault = base / "vault"
            _prepare_fixture(vault)
            blocked = base / "blocked"
            blocked.mkdir()
            profile_path = _write_fixture_profile(
                vault, "pi.md", repo_root=str(blocked / "repo")
            )
            blocked.chmod(0)
            try:
                try:
                    profile, errors = load_profile(profile_path, vault)
                except PATH_FAILURES as exc:
                    self.fail(f"repository-root failure escaped validation: {exc}")
            finally:
                blocked.chmod(0o700)

            self.assertIsNone(profile)
            self.assertTrue(
                any(
                    error.startswith(f"{profile_path}: cannot inspect repo root ")
                    and "Permission denied" in error
                    for error in errors
                ),
                errors,
            )

    def test_entrypoint_nul_returns_path_qualified_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            vault = base / "vault"
            _prepare_fixture(vault)
            repo = base / "repo"
            repo.mkdir()
            profile_path = _write_fixture_profile(
                vault,
                "pi.md",
                repo_root=str(repo),
                entrypoint="DomainMaps/bad\0entry.md",
            )

            try:
                profile, errors = load_profile(profile_path, vault)
            except PATH_FAILURES as exc:
                self.fail(f"entrypoint failure escaped validation: {exc}")

            self.assertIsNone(profile)
            self.assertTrue(
                any(
                    error.startswith(
                        f"{profile_path}: cannot resolve entrypoint 'DomainMaps/bad\\x00entry.md':"
                    )
                    for error in errors
                ),
                errors,
            )

    def test_entrypoint_permission_denied_returns_path_qualified_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            vault = base / "vault"
            _prepare_fixture(vault)
            repo = base / "repo"
            repo.mkdir()
            blocked = vault / "DomainMaps/blocked"
            blocked.mkdir()
            profile_path = _write_fixture_profile(
                vault,
                "pi.md",
                repo_root=str(repo),
                entrypoint="DomainMaps/blocked/entry.md",
            )
            blocked.chmod(0)
            try:
                try:
                    profile, errors = load_profile(profile_path, vault)
                except PATH_FAILURES as exc:
                    self.fail(f"entrypoint failure escaped validation: {exc}")
            finally:
                blocked.chmod(0o700)

            self.assertIsNone(profile)
            self.assertTrue(
                any(
                    error.startswith(f"{profile_path}: cannot inspect entrypoint ")
                    and "Permission denied" in error
                    for error in errors
                ),
                errors,
            )

    def test_malformed_vault_path_returns_path_qualified_error(self) -> None:
        vault = Path("bad\0vault")

        try:
            profiles, errors = validate_vault(vault)
        except PATH_FAILURES as exc:
            self.fail(f"vault-root failure escaped validation: {exc}")

        self.assertEqual(profiles, [])
        self.assertTrue(
            any(error.startswith(f"{vault}: cannot resolve vault root:") for error in errors),
            errors,
        )

    def test_profile_directory_permission_denied_returns_path_qualified_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory) / "vault"
            profile_directory = vault / "Workbench/RepositoryProfiles"
            profile_directory.mkdir(parents=True)
            profile_directory.chmod(0)
            try:
                try:
                    profiles, errors = validate_vault(vault)
                except PATH_FAILURES as exc:
                    self.fail(f"profile-directory failure escaped validation: {exc}")
            finally:
                profile_directory.chmod(0o700)

            self.assertEqual(profiles, [])
            self.assertTrue(
                any(
                    error.startswith(f"{profile_directory.resolve()}: cannot list profile directory:")
                    and "Permission denied" in error
                    for error in errors
                ),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
