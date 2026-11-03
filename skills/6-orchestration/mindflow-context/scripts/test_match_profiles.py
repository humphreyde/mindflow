#!/usr/bin/env python3
"""Canonical repository matching tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_profiles import Profile, match_profile


class MatchProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.repo_symlink = root / "repo-link"
        self.repo_symlink.symlink_to(self.repo, target_is_directory=True)
        self.profiles = [self.make_profile("pi", (self.repo,))]

    def make_profile(
        self, key: str, roots: tuple[Path, ...], aliases: tuple[str, ...] = ()
    ) -> Profile:
        return Profile(
            path=Path("Workbench/RepositoryProfiles") / f"{key}.md",
            repo_key=key,
            repo_roots=tuple(root.resolve() for root in roots),
            aliases=aliases,
            domains=(),
            entrypoints=(),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=None,
            workspace_entrypoint_values=(),
        )

    def test_original_and_symlink_paths_match_one_profile(self) -> None:
        original = match_profile(self.profiles, self.repo)
        linked = match_profile(self.profiles, self.repo_symlink)

        self.assertEqual(original.status, "matched")
        self.assertEqual(linked.status, "matched")
        self.assertEqual(original.errors + linked.errors, ())
        self.assertEqual(original.profile.repo_key, "pi")
        self.assertEqual(linked.profile.repo_key, "pi")

    def test_duplicate_canonical_claim_is_ambiguous(self) -> None:
        profiles = [
            self.make_profile("pi-a", (self.repo,)),
            self.make_profile("pi-b", (self.repo_symlink,)),
        ]

        result = match_profile(profiles, self.repo)

        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.profile)
        self.assertEqual(len(result.errors), 1)

    def test_identity_fallback_runs_only_without_root_claimant(self) -> None:
        other = Path(self.temporary_directory.name) / "other"
        other.mkdir()
        identity_profile = self.make_profile("identity", (other,), aliases=("openpi",))
        exact_profile = self.make_profile("exact", (self.repo,), aliases=("different",))

        result = match_profile(
            [identity_profile, exact_profile], self.repo, repository_name="openpi"
        )

        self.assertEqual(result.status, "matched")
        self.assertEqual(result.profile.repo_key, "exact")

    def test_identity_fallback_is_casefolded(self) -> None:
        other = Path(self.temporary_directory.name) / "other"
        other.mkdir()
        profile = self.make_profile("pi", (other,), aliases=("OpenPI",))

        result = match_profile([profile], self.repo, repository_name="openpi")

        self.assertEqual(result.status, "matched")
        self.assertEqual(result.profile.repo_key, "pi")

    def test_unknown_root_and_identity_is_not_found(self) -> None:
        missing = Path(self.temporary_directory.name) / "missing"

        result = match_profile(self.profiles, missing, repository_name="unknown")

        self.assertEqual(result.status, "not_found")
        self.assertIsNone(result.profile)
        self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
