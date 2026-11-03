#!/usr/bin/env python3
"""Workspace containment tests for MindFlow repository profiles."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_profiles import (
    Profile,
    load_profile,
    resolve_workspace_entrypoint,
    resolve_workspace_root,
    workspace_context_paths,
)


class WorkspaceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.vault = root / "vault"
        self.workspace = self.vault / "Projects/pi"
        self.workspace.mkdir(parents=True)
        (self.workspace / "main.md").write_text("# Main\n", encoding="utf-8")
        (self.workspace / "engineering.md").write_text("# Engineering\n", encoding="utf-8")
        (self.workspace / "experiments").mkdir()
        (self.workspace / "experiments/approved.md").write_text(
            "# Approved\n", encoding="utf-8"
        )
        (self.workspace / "discussions").mkdir()
        (self.workspace / "discussions/unlisted.md").write_text(
            "# Unlisted\n", encoding="utf-8"
        )
        self.profile = Profile(
            path=self.vault / "Workbench/RepositoryProfiles/pi.md",
            repo_key="pi",
            repo_roots=(),
            aliases=(),
            domains=(),
            entrypoints=(),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=self.workspace.resolve(),
            workspace_entrypoint_values=("experiments/approved.md",),
        )

    def test_workspace_root_rejects_invalid_paths(self) -> None:
        invalid_roots = (
            "/tmp/external",
            "Projects/../escape",
            "Missing/pi",
            "Projects/pi/main.md",
            "Other/pi",
        )
        for value in invalid_roots:
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_workspace_root(self.vault, value)

    def test_workspace_root_rejects_directory_symlink(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside"
        outside.mkdir()
        link = self.vault / "Projects/linked"
        link.symlink_to(outside, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "symlink"):
            resolve_workspace_root(self.vault, "Projects/linked")

    def test_context_is_fixed_defaults_plus_explicit_files(self) -> None:
        self.assertEqual(
            workspace_context_paths(self.profile),
            (
                self.workspace.resolve() / "main.md",
                self.workspace.resolve() / "engineering.md",
                self.workspace.resolve() / "experiments/approved.md",
            ),
        )
        self.assertNotIn(
            self.workspace.resolve() / "discussions/unlisted.md",
            workspace_context_paths(self.profile),
        )

    def test_entrypoint_rejects_forbidden_directories_and_escape(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        escape = self.workspace / "experiments/escape.md"
        escape.symlink_to(outside)
        for value in (
            "/tmp/external.md",
            "../outside.md",
            "code/repo/README.md",
            "worklog/task.md",
            ".git/config.md",
            "experiments/escape.md",
            "discussions",
            "missing.md",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_workspace_entrypoint(self.workspace.resolve(), value)

    def test_missing_default_is_rejected(self) -> None:
        (self.workspace / "engineering.md").unlink()

        with self.assertRaisesRegex(ValueError, "does not exist"):
            workspace_context_paths(self.profile)

    def test_entrypoints_require_workspace_root(self) -> None:
        repo = Path(self.temporary_directory.name) / "repo"
        repo.mkdir()
        profile_path = self.vault / "Workbench/RepositoryProfiles/missing-root.md"
        profile_path.parent.mkdir(parents=True)
        (self.vault / "DomainMaps").mkdir()
        (self.vault / "DomainMaps/VLA.md").write_text("# VLA\n", encoding="utf-8")
        profile_path.write_text(
            "---\n"
            "type: repository-profile\n"
            "repo_key: missing-root\n"
            "repo_roots:\n"
            f"  - {repo}\n"
            "aliases: []\n"
            "domains:\n  - VLA\n"
            "entrypoints:\n  - DomainMaps/VLA.md\n"
            "keywords:\n  - ACP\n"
            "workspace_entrypoints:\n  - experiments/approved.md\n"
            "verified_at: 2026-11-03\n"
            "---\n",
            encoding="utf-8",
        )

        profile, errors = load_profile(profile_path, self.vault)

        self.assertIsNone(profile)
        self.assertIn("workspace_entrypoints requires workspace_root", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
