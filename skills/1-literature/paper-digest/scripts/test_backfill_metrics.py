from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backfill_metrics import parse_paper


class BackfillMetricsIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def note(self, frontmatter: str, body: str = "") -> Path:
        path = self.root / "2603-Test.md"
        path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")
        return path

    def test_explicit_arxiv_id_wins_when_it_matches_url(self) -> None:
        paper = parse_paper(
            self.note(
                "arxiv_id: 2603.03596\n"
                "paper: https://arxiv.org/abs/2603.03596v2\n"
            )
        )
        self.assertEqual(paper.arxiv_id, "2603.03596")

    def test_conflicting_explicit_and_url_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "identity conflict"):
            parse_paper(
                self.note(
                    "arxiv_id: 2603.00001\n"
                    "paper: https://arxiv.org/abs/2603.00002\n"
                )
            )

    def test_explicit_arxiv_id_works_without_arxiv_url(self) -> None:
        paper = parse_paper(
            self.note(
                "arxiv_id: 2603.03596v3\n"
                "paper: https://publisher.example/paper\n"
            )
        )
        self.assertEqual(paper.arxiv_id, "2603.03596")

    def test_body_citation_is_not_used_as_identity(self) -> None:
        paper = parse_paper(
            self.note(
                "title: GEN-1\n"
                "paper:\n",
                "Related work cites https://arxiv.org/abs/2005.14165\n",
            )
        )
        self.assertIsNone(paper.arxiv_id)


if __name__ == "__main__":
    unittest.main()
