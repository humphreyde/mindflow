#!/usr/bin/env python3
"""Area, Resource, and typed archive validation tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_profiles import (
    load_archived_area,
    load_archived_resource,
    load_area,
    load_resource,
)


class ParaAssetValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.vault = Path(self.temporary_directory.name) / "vault"
        (self.vault / "DomainMaps").mkdir(parents=True)
        (self.vault / "DomainMaps/VLA.md").write_text("# VLA\n", encoding="utf-8")

    def write_note(self, relative: str, frontmatter: str) -> Path:
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{frontmatter}---\n", encoding="utf-8")
        return path

    def test_valid_area_and_resource_load(self) -> None:
        area = self.write_note(
            "Workbench/PARA/Areas/Research.md",
            "type: area\narea_key: research\nowner: hum\n"
            "responsibility: Maintain research\nstandard: Evidence first\n"
            "status: active\nreview_cadence: monthly\nlast_reviewed:\n"
            "domains:\n  - VLA\n",
        )
        resource = self.write_note(
            "Workbench/PARA/Resources/VLA.md",
            "type: resource\nresource_key: vla\nscope: VLA knowledge\n"
            "entrypoints:\n  - DomainMaps/VLA.md\nquery:\n"
            "review_cadence: quarterly\nlast_reviewed:\n",
        )
        self.assertEqual(load_area(area, self.vault)[1], [])
        self.assertEqual(load_resource(resource, self.vault)[1], [])

    def test_resource_entrypoints_must_be_contained_files(self) -> None:
        outside = Path(self.temporary_directory.name) / "outside.md"
        outside.write_text("secret\n", encoding="utf-8")
        link = self.vault / "DomainMaps/link.md"
        link.symlink_to(outside)
        for index, value in enumerate(
            ("../outside.md", "/absolute.md", "DomainMaps/missing.md", "DomainMaps", "DomainMaps/link.md")
        ):
            path = self.write_note(
                f"Workbench/PARA/Resources/bad-{index}.md",
                "type: resource\nresource_key: bad\nscope: Invalid\n"
                f"entrypoints:\n  - {value}\nquery:\n"
                "review_cadence: quarterly\nlast_reviewed:\n",
            )
            loaded, errors = load_resource(path, self.vault)
            self.assertIsNone(loaded, value)
            self.assertTrue(errors, value)

    def test_area_rejects_bad_values(self) -> None:
        path = self.write_note(
            "Workbench/PARA/Areas/Bad.md",
            "type: area\narea_key: Not Valid\nowner: hum\nresponsibility:\n"
            "standard: Evidence first\nstatus: retired\nreview_cadence: sometimes\n"
            "last_reviewed: 03/11/2026\ndomains: []\n",
        )
        loaded, errors = load_area(path, self.vault)
        joined = "\n".join(errors)
        self.assertIsNone(loaded)
        self.assertIn("lowercase kebab-case", joined)
        self.assertIn("responsibility must be non-empty", joined)
        self.assertIn("invalid area status", joined)
        self.assertIn("invalid review cadence", joined)
        self.assertIn("ISO date", joined)

    def test_archived_types_require_final_fields(self) -> None:
        area = self.write_note(
            "Workbench/PARA/Archives/Areas/Research.md",
            "type: area\narea_key: research\nowner: hum\nresponsibility: Old\n"
            "standard: Evidence first\nstatus: active\nreview_cadence: monthly\n"
            "last_reviewed:\ndomains: []\narchived_at: 2026-11-03\n"
            "archive_reason: Retired\n",
        )
        loaded, errors = load_archived_area(area, self.vault)
        self.assertIsNone(loaded)
        self.assertIn("status must be retired", "\n".join(errors))
        self.assertIn("missing required field 'final_outcome'", "\n".join(errors))

        resource = self.write_note(
            "Workbench/PARA/Archives/Resources/VLA.md",
            "type: resource\nresource_key: vla\nscope: Old\n"
            "entrypoints:\n  - DomainMaps/VLA.md\nquery:\n"
            "review_cadence: quarterly\nlast_reviewed:\n"
            "archived_at: 2026-11-03\narchive_reason: Retired\n",
        )
        loaded, errors = load_archived_resource(resource, self.vault)
        self.assertIsNone(loaded)
        self.assertIn("missing required field 'final_outcome'", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
