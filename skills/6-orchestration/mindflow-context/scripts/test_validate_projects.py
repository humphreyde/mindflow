#!/usr/bin/env python3
"""Outcome Project and context-channel validation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_profiles import (
    Area,
    Profile,
    load_archived_project,
    load_project,
    resolve_context,
)


class ProjectValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.vault = root / "vault"
        self.repo = root / "repo"
        self.repo.mkdir()
        self.workspace = self.vault / "Projects/pi"
        self.workspace.mkdir(parents=True)
        (self.workspace / "main.md").write_text("# Main\n", encoding="utf-8")
        (self.workspace / "engineering.md").write_text("# Engineering\n", encoding="utf-8")
        (self.workspace / "experiments").mkdir()
        (self.workspace / "experiments/profile-approved.md").write_text(
            "# Profile approved\n", encoding="utf-8"
        )
        (self.vault / "Experiments").mkdir()
        (self.vault / "Experiments/recap.md").write_text("# RECAP\n", encoding="utf-8")
        (self.vault / "DomainMaps").mkdir()
        self.domain_map = self.vault / "DomainMaps/VLA.md"
        self.domain_map.write_text("# VLA\n", encoding="utf-8")
        self.profile_path = self._write_profile()
        self.profile = Profile(
            path=self.profile_path,
            repo_key="pi",
            repo_roots=(self.repo.resolve(),),
            aliases=(),
            domains=("VLA",),
            entrypoints=(self.domain_map.resolve(),),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=self.workspace.resolve(),
            workspace_entrypoint_values=("experiments/profile-approved.md",),
        )
        area_path = self._write_area()
        self.area = Area(
            path=area_path,
            area_key="research",
            owner="hum",
            responsibility="Maintain research",
            standard="Evidence first",
            status="active",
            review_cadence="monthly",
            last_reviewed=None,
            domains=(),
        )
        self.first_project_path = self.write_project("pi-recap")
        self.second_project_path = self.write_project("pi-tron2")

    def _write_profile(self) -> Path:
        path = self.vault / "Workbench/RepositoryProfiles/pi.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\ntype: repository-profile\nrepo_key: pi\nrepo_roots:\n"
            f"  - {self.repo}\naliases: []\ndomains:\n  - VLA\n"
            "entrypoints:\n  - DomainMaps/VLA.md\nkeywords:\n  - ACP\n"
            "workspace_root: Projects/pi\nworkspace_entrypoints:\n"
            "  - experiments/profile-approved.md\nverified_at: 2026-11-03\n---\n",
            encoding="utf-8",
        )
        return path.resolve()

    def _write_area(self) -> Path:
        path = self.vault / "Workbench/PARA/Areas/Research.md"
        path.parent.mkdir(parents=True)
        path.write_text(
            "---\ntype: area\narea_key: research\nowner: hum\n"
            "responsibility: Maintain research\nstandard: Evidence first\n"
            "status: active\nreview_cadence: monthly\nlast_reviewed:\n"
            "domains: []\n---\n",
            encoding="utf-8",
        )
        return path.resolve()

    def write_project(self, key: str) -> Path:
        path = self.vault / f"Workbench/PARA/Projects/{key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\ntype: project\n"
            f"project_key: {key}\noutcome: Deliver {key}\n"
            "completion_criteria:\n  - Verified result\nstatus: active\n"
            "target_date:\nworkspace_root: Projects/pi\nrepo_refs:\n  - pi\n"
            "area_refs:\n  - research\nknowledge_entrypoints:\n"
            "  - Experiments/recap.md\n---\n",
            encoding="utf-8",
        )
        return path.resolve()

    def write_archive(self, status: str = "completed", final: bool = True) -> Path:
        path = self.vault / "Workbench/PARA/Archives/Projects/pi-old.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        final_line = "final_outcome: Verified\n" if final else ""
        path.write_text(
            "---\ntype: project\nproject_key: pi-old\noutcome: Old result\n"
            "completion_criteria:\n  - Done\n"
            f"status: {status}\ntarget_date:\nworkspace_root: Projects/pi\n"
            "repo_refs:\n  - pi\narea_refs: []\nknowledge_entrypoints: []\n"
            "archived_at: 2026-11-03\narchive_reason: Finished\n"
            f"{final_line}code_provenance:\n  - pi@deadbeef\n---\n",
            encoding="utf-8",
        )
        return path.resolve()

    def test_multiple_projects_require_explicit_selection(self) -> None:
        result = resolve_context(self.vault, self.repo)
        self.assertEqual(result.status, "project_selection_required")
        self.assertEqual(result.project_keys, ("pi-recap", "pi-tron2"))
        self.assertIsNone(result.project_path)

    def test_context_channels_stay_separate(self) -> None:
        result = resolve_context(self.vault, self.repo, project_key="pi-recap")
        self.assertEqual(result.status, "matched")
        self.assertEqual(result.project_path, self.first_project_path)
        self.assertEqual(result.vault_entrypoints, (self.domain_map.resolve(),))
        self.assertEqual(
            result.workspace_context,
            (
                self.workspace.resolve() / "main.md",
                self.workspace.resolve() / "engineering.md",
                self.workspace.resolve() / "experiments/profile-approved.md",
            ),
        )
        self.assertEqual(
            result.project_workspace_context,
            (
                self.workspace.resolve() / "main.md",
                self.workspace.resolve() / "engineering.md",
            ),
        )
        self.assertEqual(
            result.project_knowledge_entrypoints,
            ((self.vault / "Experiments/recap.md").resolve(),),
        )

    def test_unknown_references_and_escape_are_rejected(self) -> None:
        path = self.write_project("bad")
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("  - pi\n", "  - missing\n", 1), encoding="utf-8")
        project, errors = load_project(
            path, self.vault, {"pi": self.profile}, {"research": self.area}
        )
        self.assertIsNone(project)
        self.assertIn("unknown repo_ref", "\n".join(errors))

        path = self.write_project("escape")
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("  - Experiments/recap.md", "  - ../outside.md"),
            encoding="utf-8",
        )
        project, errors = load_project(
            path, self.vault, {"pi": self.profile}, {"research": self.area}
        )
        self.assertIsNone(project)
        self.assertIn("entrypoint", "\n".join(errors))

    def test_archived_project_requires_final_fields_and_terminal_status(self) -> None:
        archived, errors = load_archived_project(
            self.write_archive(final=False),
            self.vault,
            {"pi": self.profile},
            {"research": self.area},
        )
        self.assertIsNone(archived)
        self.assertIn("missing required field 'final_outcome'", "\n".join(errors))

        archived, errors = load_archived_project(
            self.write_archive(status="active"),
            self.vault,
            {"pi": self.profile},
            {"research": self.area},
        )
        self.assertIsNone(archived)
        self.assertIn("archived status must be completed or cancelled", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
