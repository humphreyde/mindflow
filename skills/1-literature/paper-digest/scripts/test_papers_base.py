from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from paper_schema import parse_frontmatter
from papers_base_contract import (
    EXPECTED_FILTERS,
    has_low_confidence_identity,
    is_vla,
    is_wam,
    needs_review,
)


REQUIRED_VIEWS = {
    "All Papers",
    "By Primary Domain",
    "Cross-domain",
    "VLA",
    "WAM",
    "Needs Review",
    "Foundation",
    "Recent",
}


class PapersBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vault = Path(__file__).resolve().parents[4]
        cls.base_path = cls.vault / "Workbench/PARA/Resources/Papers.base"
        cls.data = yaml.safe_load(cls.base_path.read_text(encoding="utf-8"))

    def test_base_exposes_exact_required_views(self) -> None:
        self.assertEqual({view["name"] for view in self.data["views"]}, REQUIRED_VIEWS)

    def test_global_scope_is_root_papers_markdown(self) -> None:
        self.assertEqual(
            self.data["filters"],
            {"and": ['file.folder == "Papers"', 'file.ext == "md"']},
        )

    def test_base_formulas_match_executable_contract(self) -> None:
        formulas = self.data["formulas"]
        for name, expression in EXPECTED_FILTERS.items():
            with self.subTest(name=name):
                self.assertEqual(formulas[name], expression)

    def test_view_filters_and_recent_sort_match_contract(self) -> None:
        views = {view["name"]: view for view in self.data["views"]}
        self.assertEqual(views["WAM"]["filters"], "formula.is_wam")
        self.assertEqual(views["Needs Review"]["filters"], "formula.needs_review")
        self.assertEqual(views["Foundation"]["filters"], "rating == 3")
        self.assertEqual(
            views["Recent"]["sort"],
            [{"property": "date_added", "direction": "DESC"}],
        )

    def test_live_vault_acceptance_counts(self) -> None:
        frontmatters = [
            parse_frontmatter(path).frontmatter
            for path in sorted((self.vault / "Papers").glob("*.md"))
        ]
        counts = {
            "All Papers": len(frontmatters),
            "VLA": sum(is_vla(frontmatter) for frontmatter in frontmatters),
            "WAM": sum(is_wam(frontmatter) for frontmatter in frontmatters),
            "Foundation": sum(frontmatter.get("rating") == 3 for frontmatter in frontmatters),
            "Needs Review": sum(needs_review(frontmatter) for frontmatter in frontmatters),
        }
        self.assertEqual(
            counts,
            {
                "All Papers": 204,
                "VLA": 70,
                "WAM": 16,
                "Foundation": 45,
                "Needs Review": 204,
            },
        )

    def test_low_confidence_is_computed_not_persisted(self) -> None:
        self.assertTrue(has_low_confidence_identity({"paper": "https://example.org/p"}))
        self.assertFalse(has_low_confidence_identity({"arxiv_id": "2603.03596"}))
        self.assertFalse(has_low_confidence_identity({"doi": "10.1000/test"}))


if __name__ == "__main__":
    unittest.main()
