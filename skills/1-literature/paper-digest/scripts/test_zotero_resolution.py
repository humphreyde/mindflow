from __future__ import annotations

import unittest

from zotero_resolution import (
    OfficialSource,
    ZoteroAttachment,
    ZoteroCandidate,
    ZoteroUnavailableError,
    choose_read_source,
    list_attachment_metadata,
    resolve_zotero_reference,
)


class FakeBackend:
    def __init__(self) -> None:
        self.item_key: list[ZoteroCandidate] = []
        self.doi: list[ZoteroCandidate] = []
        self.arxiv: list[ZoteroCandidate] = []
        self.title: list[ZoteroCandidate] = []
        self.attachments: list[ZoteroAttachment] = []
        self.calls: list[tuple[str, str]] = []

    def by_item_key(self, item_key: str):
        self.calls.append(("item_key", item_key))
        return self.item_key

    def by_doi(self, doi: str):
        self.calls.append(("doi", doi))
        return self.doi

    def by_arxiv_id(self, arxiv_id: str):
        self.calls.append(("arxiv", arxiv_id))
        return self.arxiv

    def by_title(self, title: str):
        self.calls.append(("title", title))
        return self.title

    def list_attachments(self, item_key: str):
        self.calls.append(("attachments", item_key))
        return self.attachments


class UnavailableBackend(FakeBackend):
    def by_item_key(self, item_key: str):
        raise ZoteroUnavailableError("desktop unavailable")


class ZoteroResolutionTests(unittest.TestCase):
    def test_exact_item_key_match_returns_exact_without_weaker_queries(self) -> None:
        backend = FakeBackend()
        backend.item_key = [ZoteroCandidate("ITEM1", "Paper")]
        result = resolve_zotero_reference(
            backend,
            item_key="ITEM1",
            doi="10.1000/test",
            arxiv_id="2603.03596",
            title="Paper",
        )
        self.assertEqual(result.status, "exact")
        self.assertEqual(result.candidate.item_key, "ITEM1")
        self.assertEqual(backend.calls, [("item_key", "ITEM1")])

    def test_doi_wins_over_arxiv_and_title(self) -> None:
        backend = FakeBackend()
        backend.doi = [ZoteroCandidate("DOI1", "DOI Paper")]
        backend.arxiv = [ZoteroCandidate("ARXIV1", "Arxiv Paper")]
        result = resolve_zotero_reference(
            backend,
            item_key=None,
            doi="https://doi.org/10.1000/ABC",
            arxiv_id="2603.03596",
            title="Paper",
        )
        self.assertEqual(result.candidate.item_key, "DOI1")
        self.assertEqual(backend.calls, [("doi", "10.1000/abc")])

    def test_arxiv_wins_over_title(self) -> None:
        backend = FakeBackend()
        backend.arxiv = [ZoteroCandidate("ARXIV1", "Arxiv Paper")]
        backend.title = [ZoteroCandidate("TITLE1", "Arxiv Paper")]
        result = resolve_zotero_reference(
            backend,
            item_key=None,
            doi=None,
            arxiv_id="arXiv:2603.03596v2",
            title="Arxiv Paper",
        )
        self.assertEqual(result.candidate.item_key, "ARXIV1")
        self.assertEqual(backend.calls, [("arxiv", "2603.03596")])

    def test_multiple_normalized_title_matches_are_ambiguous(self) -> None:
        backend = FakeBackend()
        backend.title = [
            ZoteroCandidate("B", "Paper: One"),
            ZoteroCandidate("A", "Paper One"),
            ZoteroCandidate("IGNORED", "Different"),
        ]
        result = resolve_zotero_reference(
            backend,
            item_key=None,
            doi=None,
            arxiv_id=None,
            title=" paper—one ",
        )
        self.assertEqual(result.status, "ambiguous")
        self.assertIsNone(result.candidate)
        self.assertEqual(result.candidate_keys, ("A", "B"))

    def test_ambiguous_strong_stage_never_falls_through(self) -> None:
        backend = FakeBackend()
        backend.doi = [ZoteroCandidate("B", "B"), ZoteroCandidate("A", "A")]
        backend.arxiv = [ZoteroCandidate("ARXIV", "Paper")]
        result = resolve_zotero_reference(
            backend,
            item_key=None,
            doi="10.1000/test",
            arxiv_id="2603.03596",
            title="Paper",
        )
        self.assertEqual((result.status, result.candidate_keys), ("ambiguous", ("A", "B")))
        self.assertEqual(backend.calls, [("doi", "10.1000/test")])

    def test_unavailable_returns_unavailable_and_official_source_fallback(self) -> None:
        result = resolve_zotero_reference(
            UnavailableBackend(),
            item_key="ITEM",
            doi=None,
            arxiv_id=None,
            title="Paper",
        )
        self.assertEqual(result.status, "unavailable")
        source = choose_read_source(
            result,
            (
                OfficialSource("github", "https://github.com/example/repo/"),
                OfficialSource("website", "https://user:secret@example.org/bad"),
                OfficialSource("paper", "HTTPS://ARXIV.ORG/abs/2603.03596#x"),
            ),
        )
        self.assertEqual(
            source,
            OfficialSource("paper", "https://arxiv.org/abs/2603.03596"),
        )

    def test_not_found_uses_kind_priority_for_valid_sources(self) -> None:
        backend = FakeBackend()
        result = resolve_zotero_reference(
            backend,
            item_key=None,
            doi=None,
            arxiv_id=None,
            title="Missing",
        )
        source = choose_read_source(
            result,
            (
                OfficialSource("github", "https://github.com/example/repo"),
                OfficialSource("website", "https://example.org/project"),
            ),
        )
        self.assertEqual(source.kind, "website")

    def test_attachment_listing_is_explicit_and_metadata_only(self) -> None:
        backend = FakeBackend()
        backend.attachments = [
            ZoteroAttachment("ATT1", "PDF", "application/pdf", True)
        ]
        attachments = list_attachment_metadata(backend, "ITEM1")
        self.assertEqual(attachments, tuple(backend.attachments))
        self.assertEqual(backend.calls, [("attachments", "ITEM1")])
        self.assertFalse(any(hasattr(attachments[0], name) for name in ("path", "body", "fulltext")))

    def test_backend_contract_has_no_mutation_methods(self) -> None:
        backend = FakeBackend()
        self.assertFalse(
            any(hasattr(backend, method) for method in ("add", "move", "remove", "save"))
        )


if __name__ == "__main__":
    unittest.main()
