from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "write_trending_note.py"
SPEC = importlib.util.spec_from_file_location("write_trending_note", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
write_note = MODULE.write_note


class GitHubTrendingWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = (Path(self.temp_dir.name) / "mindflow").resolve()
        for name in ("skills", "Papers", "Workbench"):
            (self.vault / name).mkdir(parents=True)
        (self.vault / "AGENTS.md").write_text("# test\n", encoding="utf-8")
        self.repositories = [
            {
                "rank": 1,
                "repo": "org/repo",
                "url": "https://github.com/org/repo",
                "description": "robot learning toolkit",
                "language": "Python",
                "stars_total": 100,
                "forks_total": 10,
                "stars_period": 25,
                "period": "weekly",
                "score": 3,
                "matched_keywords": ["robot learning"],
                "relevant": True,
            }
        ]

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_writer_uses_mindflow_trending_directory(self) -> None:
        output = write_note(self.vault, date(2026, 11, 3), self.repositories)
        self.assertEqual(
            output,
            self.vault / "Workbench/trending/2026-W45 GitHub周榜.md",
        )
        self.assertIn("org/repo", output.read_text(encoding="utf-8"))

    def test_existing_week_is_not_overwritten(self) -> None:
        output = self.vault / "Workbench/trending/2026-W45 GitHub周榜.md"
        output.parent.mkdir(parents=True)
        output.write_text("handwritten\n", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            write_note(self.vault, date(2026, 11, 3), self.repositories)
        self.assertEqual(output.read_text(encoding="utf-8"), "handwritten\n")


if __name__ == "__main__":
    unittest.main()
