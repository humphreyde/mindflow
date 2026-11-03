from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "capture_source.py"
SPEC = importlib.util.spec_from_file_location("capture_source", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_source_note = MODULE.build_source_note
save_insight = MODULE.save_insight
save_source = MODULE.save_source


class CaptureSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = (Path(self.temp_dir.name) / "mindflow").resolve()
        for name in ("skills", "Papers", "Workbench"):
            (self.vault / name).mkdir(parents=True)
        (self.vault / "AGENTS.md").write_text("# test\n", encoding="utf-8")
        self.record = {
            "title": "Post",
            "source_url": "https://example.org/post",
            "accessed": "2026-11-03",
            "content": "A source-backed observation.",
        }
        self.note = build_source_note(self.record)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_source_note_records_url_and_access_date(self) -> None:
        self.assertIn('source_url: "https://example.org/post"', self.note)
        self.assertIn("accessed: 2026-11-03", self.note)
        self.assertIn("A source-backed observation.", self.note)

    def test_capture_does_not_overwrite_existing_source(self) -> None:
        destination = self.vault / "ResearchSources/Sources/Post.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("existing\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            save_source(self.vault, "Post", self.note)
        self.assertEqual(destination.read_text(encoding="utf-8"), "existing\n")

    def test_optional_insight_uses_separate_directory(self) -> None:
        output = save_insight(self.vault, "Reusable / insight", "# Insight\n")
        self.assertEqual(
            output,
            self.vault / "ResearchSources/Insights/Reusable - insight.md",
        )
        self.assertEqual(output.read_text(encoding="utf-8"), "# Insight\n")


if __name__ == "__main__":
    unittest.main()
