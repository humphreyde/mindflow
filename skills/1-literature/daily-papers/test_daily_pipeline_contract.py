from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent
MODULE_PATH = SKILL_DIR / "fetch_and_score.py"
SPEC = importlib.util.spec_from_file_location("daily_fetch_and_score", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
run_fixture_pipeline = MODULE.run_fixture_pipeline
score_paper = MODULE.score_paper


class DailyPipelineContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = (Path(self.temp_dir.name) / "mindflow").resolve()
        for name in ("skills", "Papers", "Workbench"):
            (self.vault / name).mkdir(parents=True)
        (self.vault / "AGENTS.md").write_text("# test\n", encoding="utf-8")
        self.fixture = SKILL_DIR / "fixtures/candidates.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_fixture_pipeline_accounts_for_six_artifact_classes(self) -> None:
        result = run_fixture_pipeline(self.vault, self.fixture)

        self.assertTrue(
            (self.vault / "Workbench/daily/.candidates.json").is_file()
        )
        self.assertTrue((self.vault / "Workbench/daily/.history.json").is_file())
        self.assertEqual(len(list((self.vault / "Papers").glob("*.md"))), 1)
        daily = self.vault / "Workbench/daily/2026-11-03.md"
        self.assertTrue(daily.is_file())
        self.assertIn("3 - Foundation", daily.read_text(encoding="utf-8"))

        log = (self.vault / "Workbench/logs/2026-11-03.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("paper-digest", log)
        self.assertIn("daily-papers", log)
        self.assertEqual(result.fetched, result.read + result.skipped)
        self.assertEqual((result.fetched, result.read, result.skipped), (2, 1, 1))

    def test_whole_body_and_robot_self_improvement_match_research_profile(self) -> None:
        whole_body = {
            "title": "Scalable Whole-Body Tracking for Humanoid Robots",
            "abstract": "A motion imitation system for loco-manipulation.",
        }
        self_improvement = {
            "title": "Robot Self-Improvement from Real-World Failures",
            "abstract": "Online policy improvement with human feedback.",
        }

        self.assertGreaterEqual(score_paper(whole_body), 3)
        self.assertGreaterEqual(score_paper(self_improvement), 3)


if __name__ == "__main__":
    unittest.main()
