from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.migrations.legacy_notes import (
    apply_manifest,
    approve_manifest,
    build_manifest,
    merge_history,
    plan_asset_copy,
    render_imported_paper,
    snapshot_source,
    verify_migration,
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
        (self.source / "PaperNotes/VLA/URLOnly.md").write_text(
            "---\ntitle: URL Only\nyear: 2026\n---\n"
            "| 日期 | March 9, 2026 |\n"
            "[PDF](https://example.org/url-only.pdf)\n",
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
        (self.source / "DailyPapers/2026-10-28-论文推荐.md").write_text(
            "daily [[PaperNotes/VLA/Novel|Novel]] and "
            "[[PaperNotes/_code/Companion|Code Companion]]\n",
            encoding="utf-8",
        )
        (self.source / "DailyPapers/.history.json").write_text(
            '[{"id":"2601.00001","date":"2026-10-01","title":"A"},'
            '{"id":"2601.00002","date":"2026-10-03","title":"B"}]\n',
            encoding="utf-8",
        )
        (self.target / "Workbench/daily").mkdir(parents=True)
        (self.target / "Workbench/daily/.history.json").write_text(
            '[{"id":"2601.00001","date":"2026-10-02","title":"A"}]\n',
            encoding="utf-8",
        )
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

    def test_url_only_paper_uses_explicit_publication_month(self) -> None:
        item = next(
            item
            for item in build_manifest(self.source, self.target).items
            if item.source_path.endswith("URLOnly.md")
        )
        self.assertEqual(item.destination_path, "Papers/2603-URLOnly.md")

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
        destination.parent.mkdir(parents=True, exist_ok=True)
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

    def test_history_merge_preserves_both_sides_and_deduplicates(self) -> None:
        merged = merge_history(
            [{"id": "2601.00001", "date": "2026-10-01", "title": "A"}],
            [
                {"id": "2601.00001", "date": "2026-10-02", "title": "A"},
                {"id": "2601.00002", "date": "2026-10-03", "title": "B"},
            ],
        )
        self.assertEqual([item["id"] for item in merged], ["2601.00001", "2601.00002"])
        self.assertEqual(merged[0]["date"], "2026-10-01")

    def test_auxiliary_apply_merges_history_and_rewrites_old_links(self) -> None:
        manifest, receipt = self.freeze_manifest()
        created = apply_manifest(
            manifest,
            receipt,
            self.source,
            self.target,
            {"import-daily"},
        )
        self.assertIn("Workbench/daily/2026-10-28-论文推荐.md", created)
        note = (self.target / "Workbench/daily/2026-10-28-论文推荐.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("[[Papers/2601-Novel|Novel]]", note)
        self.assertIn("and Code Companion", note)
        self.assertNotIn("PaperNotes/", note)
        history = json.loads(
            (self.target / "Workbench/daily/.history.json").read_text(encoding="utf-8")
        )
        self.assertEqual([item["id"] for item in history], ["2601.00001", "2601.00002"])

    def test_import_preserves_body_and_adds_only_migration_fields(self) -> None:
        item = next(
            item
            for item in build_manifest(self.source, self.target).items
            if item.source_path.endswith("Novel.md")
        )
        source_bytes = (self.source / item.source_path).read_bytes()
        body = source_bytes[source_bytes.index(b"---\nBody\n") + 4 :]
        rendered = render_imported_paper(item, source_bytes, item.link_rewrites)
        self.assertIn(b"type: paper\n", rendered)
        self.assertIn(b"source_vault: notes\n", rendered)
        self.assertIn(b"source_path: PaperNotes/VLA/Novel.md\n", rendered)
        self.assertIn(b"date_migrated: 2026-11-03\n", rendered)
        self.assertIn(b"arxiv_id: 2601.00001\n", rendered)
        self.assertTrue(rendered.endswith(body))

    def test_asset_collision_uses_hash_suffix(self) -> None:
        result = plan_asset_copy("figure.png", b"source", existing=b"different")
        self.assertRegex(result.destination_name, r"^figure-[0-9a-f]{12}\.png$")
        self.assertFalse(result.reuse_existing)


class LegacyNotesVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.source = root / "notes"
        self.target = root / "mindflow"
        (self.source / "PaperNotes/VLA").mkdir(parents=True)
        (self.source / "DailyPapers").mkdir(parents=True)
        (self.target / "Papers").mkdir(parents=True)
        (self.source / "PaperNotes/VLA/Novel.md").write_text(
            "---\ntitle: Novel\narxiv_id: 2601.00001\n---\n"
            "Body ![[figure.png]]\n",
            encoding="utf-8",
        )
        (self.source / "PaperNotes/VLA/figure.png").write_bytes(b"image-bytes")
        (self.source / "DailyPapers/2026-11-03.md").write_text(
            "Daily [[PaperNotes/VLA/Novel|Novel]]\n",
            encoding="utf-8",
        )
        self.manifest = self.target / "Workbench/migrations/manifest.json"
        self.receipt = self.target / "Workbench/migrations/approval.json"
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_bytes(
            build_manifest(self.source, self.target).to_json_bytes()
        )
        approve_manifest(
            self.manifest,
            self.receipt,
            "verification fixture",
            target=self.target,
        )
        apply_manifest(
            self.manifest,
            self.receipt,
            self.source,
            self.target,
            {"import-paper", "import-daily"},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def verify(self) -> dict[str, int]:
        return verify_migration(
            self.manifest,
            source=self.source,
            target=self.target,
        )

    def rewrite_manifest(self, mutate) -> None:
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        mutate(payload)
        self.manifest.write_text(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_verify_accepts_complete_materialized_manifest(self) -> None:
        summary = self.verify()
        self.assertEqual(summary["items"], 2)
        self.assertEqual(summary["errors"], 0)

    def test_verify_rejects_source_snapshot_drift(self) -> None:
        (self.source / "DailyPapers/2026-11-03.md").write_text(
            "changed\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "source snapshot drift"):
            self.verify()

    def test_verify_rejects_duplicate_paper_identity(self) -> None:
        (self.target / "Papers/2601-Duplicate.md").write_text(
            "---\ntype: paper\ntitle: Duplicate\narxiv_id: 2601.00001\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "duplicate Paper identity"):
            self.verify()

    def test_verify_rejects_missing_copied_asset(self) -> None:
        (self.target / "Papers/assets/Novel/figure.png").unlink()
        with self.assertRaisesRegex(ValueError, "missing copied asset"):
            self.verify()

    def test_verify_rejects_legacy_wikilink_and_absolute_path(self) -> None:
        destination = self.target / "Workbench/daily/2026-11-03.md"
        destination.write_text(
            "[[PaperNotes/VLA/Novel|Novel]] /Users/limx/notes\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            ValueError, "legacy PaperNotes wikilink.*legacy absolute path"
        ):
            self.verify()

    def test_verify_rejects_unknown_status(self) -> None:
        self.rewrite_manifest(
            lambda payload: payload["items"][0].__setitem__("status", "mystery")
        )
        with self.assertRaisesRegex(ValueError, "unknown status"):
            self.verify()

    def test_verify_rejects_manifest_count_mismatch(self) -> None:
        self.rewrite_manifest(lambda payload: payload["items"].pop())
        with self.assertRaisesRegex(ValueError, "manifest accounting mismatch"):
            self.verify()

    def test_verify_rejects_target_hash_drift(self) -> None:
        destination = self.target / "Papers/2601-Novel.md"
        destination.write_text(
            destination.read_text(encoding="utf-8") + "drift\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "target hash drift"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
