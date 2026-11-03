from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.migrations.legacy_notes import (
    apply_manifest,
    approve_manifest,
    build_manifest,
    snapshot_source,
    verify_receipt,
)


class LegacyNotesPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.source = root / "notes"
        self.target = root / "mindflow"
        for path in (
            self.source / "PaperNotes/VLA",
            self.source / "PaperNotes/_authors",
            self.source / "PaperNotes/_concepts",
            self.source / "PaperNotes/_code",
            self.source / "DailyPapers",
            self.source / "GitHubTrending",
            self.source / "ResearchSources/Sources",
            self.source / "ResearchSources/Insights",
            self.source / "ResearchNotes",
            self.target / "Papers",
        ):
            path.mkdir(parents=True, exist_ok=True)
        (self.source / "PaperNotes/VLA/Novel.md").write_text(
            "---\ntitle: Novel\narxiv_html: https://arxiv.org/html/2601.00001v2\n---\nBody\n",
            encoding="utf-8",
        )
        (self.source / "PaperNotes/VLA/ExistingReport.md").write_text(
            "---\ntitle: Existing Report\n---\n"
            "[PDF](https://example.org/report.pdf)\n",
            encoding="utf-8",
        )
        (self.target / "Papers/2601-ExistingReport.md").write_text(
            "---\ntype: paper\ntitle: Existing Report\n"
            "paper: https://example.org/report.pdf\n---\nTarget\n",
            encoding="utf-8",
        )
        (self.source / "PaperNotes/VLA/GR00T-Series-Survey.md").write_text(
            "---\ntitle: GR00T Series\ntype: survey\n---\nSurvey\n",
            encoding="utf-8",
        )
        (self.source / "PaperNotes/VLA/Pi06 Base Model.md").write_text(
            "---\ntype: concept\ntitle: Pi06 Base Model\n---\nConcept\n",
            encoding="utf-8",
        )
        (self.source / "PaperNotes/_authors/A.md").write_text("# Author\n", encoding="utf-8")
        (self.source / "PaperNotes/_concepts/C.md").write_text("# Concept\n", encoding="utf-8")
        (self.source / "PaperNotes/_code/code.md").write_text("# Code\n", encoding="utf-8")
        (self.source / "PaperNotes/PaperNotes.md").write_text("# Navigation\n", encoding="utf-8")
        (self.source / "DailyPapers/2026-10-28-论文推荐.md").write_text("daily\n", encoding="utf-8")
        (self.source / "GitHubTrending/2026-W44 GitHub周榜.md").write_text("trend\n", encoding="utf-8")
        (self.source / "ResearchSources/Sources/Post.md").write_text("source\n", encoding="utf-8")
        (self.source / "ResearchSources/Insights/Insight.md").write_text("insight\n", encoding="utf-8")
        (self.source / "ResearchNotes/KnowHow.md").write_text("know-how\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def freeze_manifest(self) -> tuple[Path, Path]:
        manifest_path = self.target / "Workbench/migrations/manifest.json"
        receipt_path = self.target / "Workbench/migrations/approval.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_bytes(build_manifest(self.source, self.target).to_json_bytes())
        approve_manifest(
            manifest_path,
            receipt_path,
            "user directive 2026-11-03: 按你推荐的做，不问我",
            target=self.target,
        )
        return manifest_path, receipt_path

    def test_manifest_is_stable_and_source_is_unchanged(self) -> None:
        before = snapshot_source(self.source)
        first = build_manifest(self.source, self.target).to_json_bytes()
        second = build_manifest(self.source, self.target).to_json_bytes()
        self.assertEqual(first, second)
        self.assertEqual(before, snapshot_source(self.source))

    def test_auxiliary_routes_are_exact(self) -> None:
        routes = {
            item.source_path: item.destination_path
            for item in build_manifest(self.source, self.target).items
        }
        self.assertEqual(
            routes["DailyPapers/2026-10-28-论文推荐.md"],
            "Workbench/daily/2026-10-28-论文推荐.md",
        )
        self.assertEqual(
            routes["GitHubTrending/2026-W44 GitHub周榜.md"],
            "Workbench/trending/2026-W44 GitHub周榜.md",
        )

    def test_scope_excludes_entities_navigation_and_code(self) -> None:
        paths = {item.source_path for item in build_manifest(self.source, self.target).items}
        self.assertNotIn("PaperNotes/_authors/A.md", paths)
        self.assertNotIn("PaperNotes/_concepts/C.md", paths)
        self.assertNotIn("PaperNotes/_code/code.md", paths)
        self.assertNotIn("PaperNotes/PaperNotes.md", paths)
        self.assertIn("PaperNotes/VLA/Pi06 Base Model.md", paths)
        blocked = next(item for item in build_manifest(self.source, self.target).items if item.source_path.endswith("Pi06 Base Model.md"))
        self.assertEqual((blocked.decision, blocked.status), ("blocked", "blocked"))

    def test_exact_official_url_and_title_routes_to_reviewed_merge(self) -> None:
        item = next(
            item
            for item in build_manifest(self.source, self.target).items
            if item.source_path.endswith("ExistingReport.md")
        )
        self.assertEqual(item.identity_confidence, "review")
        self.assertEqual(item.decision, "merge-paper")
        self.assertEqual(item.destination_path, "Papers/2601-ExistingReport.md")

    def test_apply_rejects_source_hash_drift(self) -> None:
        manifest, receipt = self.freeze_manifest()
        source_note = self.source / "DailyPapers/2026-10-28-论文推荐.md"
        source_note.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash drift"):
            apply_manifest(
                manifest,
                receipt,
                self.source,
                self.target,
                {"import-daily"},
            )

    def test_apply_never_overwrites_existing_target(self) -> None:
        manifest, receipt = self.freeze_manifest()
        destination = self.target / "Workbench/daily/2026-10-28-论文推荐.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("user content\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "target exists"):
            apply_manifest(
                manifest,
                receipt,
                self.source,
                self.target,
                {"import-daily"},
            )
        self.assertEqual(destination.read_text(encoding="utf-8"), "user content\n")

    def test_receipt_is_bound_to_manifest_bytes(self) -> None:
        manifest, receipt = self.freeze_manifest()
        verify_receipt(manifest, receipt, target=self.target)
        manifest.write_bytes(manifest.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "manifest SHA-256"):
            verify_receipt(manifest, receipt, target=self.target)


if __name__ == "__main__":
    unittest.main()
