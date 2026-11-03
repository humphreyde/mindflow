from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from paper_schema import (
    PaperDocument,
    classification_candidates,
    find_duplicate_groups,
    normalize_arxiv_id,
    normalize_doi,
    normalize_official_url,
    normalize_title,
    parse_frontmatter,
    render_deterministic_updates,
    resolve_identity,
    validate_paper,
)


class PaperSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_note(self, text: str, name: str = "2603-Test.md") -> Path:
        path = self.root / name
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def document(self, **frontmatter: object) -> PaperDocument:
        lines = ["---"]
        lines.extend(
            yaml.safe_dump(
                frontmatter,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            ).rstrip().splitlines()
        )
        lines.extend(("---", "Body", ""))
        return parse_frontmatter(self.write_note("\n".join(lines)))

    def test_duplicate_frontmatter_key_is_rejected(self) -> None:
        path = self.write_note("---\ntitle: One\ntitle: Two\n---\nBody\n")
        with self.assertRaisesRegex(ValueError, "duplicate key 'title'"):
            parse_frontmatter(path)

    def test_malformed_yaml_is_rejected(self) -> None:
        path = self.write_note("---\ntitle: [unterminated\n---\nBody\n")
        with self.assertRaisesRegex(ValueError, "invalid YAML"):
            parse_frontmatter(path)

    def test_missing_frontmatter_is_rejected(self) -> None:
        path = self.write_note("# Plain note\n")
        with self.assertRaisesRegex(ValueError, "frontmatter"):
            parse_frontmatter(path)

    def test_yaml_timestamps_remain_strings_without_global_mutation(self) -> None:
        path = self.write_note(
            "---\ndate_publish: 2026-03-03\ndate_added: 2026-11-03\n---\n"
        )
        document = parse_frontmatter(path)
        self.assertEqual(document.frontmatter["date_publish"], "2026-03-03")
        self.assertEqual(document.frontmatter["date_added"], "2026-11-03")
        self.assertEqual(type(yaml.safe_load("value: 2026-03-03")["value"]).__name__, "date")

    def test_crlf_parser_records_byte_offsets_and_newline(self) -> None:
        path = self.root / "crlf.md"
        raw = b"---\r\ntitle: Test\r\n---\r\nBody\r\n"
        path.write_bytes(raw)
        document = parse_frontmatter(path)
        self.assertEqual(document.newline, b"\r\n")
        self.assertEqual(raw[: document.opening_delimiter_end], b"---\r\n")
        self.assertEqual(raw[document.frontmatter_end :], b"Body\r\n")

    def test_arxiv_version_suffix_is_removed(self) -> None:
        self.assertEqual(normalize_arxiv_id("arXiv:2603.03596v2"), "2603.03596")
        self.assertEqual(
            normalize_arxiv_id("https://arxiv.org/pdf/2401.12345v3.pdf"),
            "2401.12345",
        )
        self.assertIsNone(normalize_arxiv_id("not-an-arxiv-id"))

    def test_doi_normalization_removes_common_prefixes(self) -> None:
        self.assertEqual(normalize_doi(" https://doi.org/10.1000/ABC.123 "), "10.1000/abc.123")
        self.assertEqual(normalize_doi("doi:10.5555/Test_Value"), "10.5555/test_value")
        self.assertIsNone(normalize_doi("https://example.org/not-a-doi"))

    def test_title_normalization_is_case_and_whitespace_stable(self) -> None:
        self.assertEqual(normalize_title("  GR00T—N1.5:  A Robot! "), "gr00t n1 5 a robot")

    def test_official_url_normalization_is_stable(self) -> None:
        self.assertEqual(
            normalize_official_url(" HTTPS://Example.org/paper/?utm_source=x#results "),
            "https://example.org/paper",
        )
        self.assertIsNone(normalize_official_url("https://user:secret@example.org/paper"))
        self.assertEqual(
            normalize_official_url("https://example.org"),
            normalize_official_url("https://example.org/"),
        )

    def test_official_url_sorts_query_and_removes_tracking(self) -> None:
        first = "https://EXAMPLE.org:443/paper/?b=2&utm_medium=x&a=1&gclid=y"
        second = "https://example.org/paper?a=1&b=2"
        self.assertEqual(normalize_official_url(first), normalize_official_url(second))

    def test_official_url_rejects_invalid_scheme_and_credentials(self) -> None:
        self.assertIsNone(normalize_official_url("file:///tmp/paper.pdf"))
        self.assertIsNone(normalize_official_url("https://token@example.org/paper"))
        self.assertIsNone(normalize_official_url("https:///missing-host"))

    def test_official_url_normalizes_percent_encoded_unreserved_path(self) -> None:
        self.assertEqual(
            normalize_official_url("https://example.org/%7Epaper/%41/"),
            "https://example.org/~paper/A",
        )

    def test_explicit_arxiv_conflict_with_paper_url_is_blocked(self) -> None:
        document = self.document(
            title="Conflict",
            arxiv_id="2603.00001",
            paper="https://arxiv.org/abs/2603.00002",
        )
        issues = validate_paper(document, mode="audit")
        self.assertTrue(
            any(issue.code == "identity-conflict" and issue.severity == "error" for issue in issues)
        )

    def test_identity_priority_is_arxiv_then_doi_then_url_title(self) -> None:
        document = self.document(
            title="Priority",
            arxiv_id="2603.03596v2",
            doi="10.1000/lower-priority",
            website="https://example.org/project",
        )
        identity = resolve_identity(document)
        self.assertEqual(identity.key, "arxiv:2603.03596")
        self.assertEqual(identity.confidence, "high")

    def test_doi_identity_is_high_confidence(self) -> None:
        identity = resolve_identity(self.document(title="DOI", doi="10.1000/ABC"))
        self.assertEqual(identity.key, "doi:10.1000/abc")
        self.assertEqual(identity.confidence, "high")

    def test_url_title_identity_needs_review(self) -> None:
        identity = resolve_identity(
            self.document(title="Project Paper", website="https://example.org/paper")
        )
        self.assertEqual(identity.kind, "url-title")
        self.assertEqual(identity.confidence, "review")
        self.assertEqual(identity.key, "url-title:https://example.org/paper#project paper")

    def test_missing_identity_is_low_confidence(self) -> None:
        identity = resolve_identity(self.document(title="No source"))
        self.assertEqual((identity.kind, identity.key, identity.confidence), ("missing", None, "low"))

    def test_official_url_priority_is_paper_then_website_then_github(self) -> None:
        identity = resolve_identity(
            self.document(
                title="Sources",
                paper="https://publisher.example/paper",
                website="https://project.example",
                github="https://github.com/example/repo",
            )
        )
        self.assertEqual(identity.official_url, "https://publisher.example/paper")

    def test_distinct_urls_with_same_title_remain_distinct(self) -> None:
        first = resolve_identity(self.document(title="Shared", website="https://one.example/p"))
        second = resolve_identity(self.document(title="Shared", website="https://two.example/p"))
        self.assertNotEqual(first.key, second.key)

    def test_primary_domain_must_be_in_domains(self) -> None:
        document = self.document(
            type="paper",
            title="Domains",
            primary_domain="embodied-ai",
            domains=["ai-agent"],
            tags=["VLA"],
            review_status="reviewed",
            rating=2,
            arxiv_id="2603.03596",
        )
        self.assertIn(
            "primary-domain-not-in-domains",
            {issue.code for issue in validate_paper(document, mode="strict")},
        )

    def test_strict_mode_rejects_unknown_domains_tags_status_and_rating(self) -> None:
        document = self.document(
            type="paper",
            title="Invalid",
            primary_domain="robotics",
            domains=["robotics"],
            tags=["unknown-tag"],
            review_status="done",
            rating=4,
            arxiv_id="2603.03596",
        )
        issues = validate_paper(document, mode="strict")
        codes = {issue.code for issue in issues if issue.severity == "error"}
        self.assertTrue(
            {"unknown-domain", "unknown-tag", "invalid-review-status", "invalid-rating"}.issubset(codes)
        )

    def test_strict_mode_requires_canonical_fields_and_one_to_four_tags(self) -> None:
        document = self.document(title="Incomplete", tags=[])
        codes = {issue.code for issue in validate_paper(document, mode="strict")}
        self.assertTrue(
            {"missing-type", "missing-primary-domain", "missing-domains", "invalid-tag-count", "missing-review-status"}.issubset(codes)
        )

    def test_audit_warns_for_more_than_four_legacy_tags(self) -> None:
        document = self.document(
            title="Legacy",
            tags=["VLA", "world-model", "RL", "task-planning", "manipulation"],
            paper="https://arxiv.org/abs/2603.03596",
        )
        issues = validate_paper(document, mode="audit")
        self.assertTrue(
            any(issue.code == "too-many-tags" and issue.severity == "warning" for issue in issues)
        )

    def test_audit_unknown_tag_is_review_not_error(self) -> None:
        issues = validate_paper(
            self.document(title="Unknown", tags=["mystery"], paper="https://example.org/p"),
            mode="audit",
        )
        self.assertTrue(any(issue.code == "unknown-tag" and issue.severity == "review" for issue in issues))

    def test_classification_selects_only_one_owned_domain(self) -> None:
        document = self.document(title="VLA", tags=["VLA", "world-model"])
        self.assertEqual(classification_candidates(document), (("embodied-ai",), None))

    def test_classification_shared_first_and_multi_domain_need_review(self) -> None:
        shared = self.document(title="Shared", tags=["world-model", "VLA"])
        multi = self.document(title="Multi", tags=["VLA", "computer-use"])
        self.assertEqual(classification_candidates(shared), (("embodied-ai",), "shared-first"))
        self.assertEqual(
            classification_candidates(multi),
            (("ai-agent", "embodied-ai"), "multi-domain-candidate"),
        )

    def test_classification_without_owned_tag_needs_review(self) -> None:
        document = self.document(title="Shared only", tags=["RL"])
        self.assertEqual(classification_candidates(document), ((), "no-domain-candidate"))

    def test_duplicate_groups_use_only_strong_identities(self) -> None:
        a = self.document(title="One", arxiv_id="2603.03596")
        b_path = self.write_note(
            "---\ntitle: Two\npaper: https://arxiv.org/abs/2603.03596v3\n---\n",
            "second.md",
        )
        b = parse_frontmatter(b_path)
        weak_path = self.write_note(
            "---\ntitle: Weak\nwebsite: https://example.org/weak\n---\n",
            "weak.md",
        )
        weak = parse_frontmatter(weak_path)
        groups = find_duplicate_groups((weak, b, a))
        self.assertEqual(groups, [("arxiv:2603.03596", tuple(sorted((a.path, b.path))))])

    def test_same_title_with_distinct_strong_ids_is_not_duplicate(self) -> None:
        first = self.document(title="GR00T N1", arxiv_id="2503.14734")
        second = parse_frontmatter(
            self.write_note(
                "---\ntitle: GR00T N1\narxiv_id: 2512.00001\n---\n",
                "groot-n15.md",
            )
        )
        self.assertEqual(find_duplicate_groups((first, second)), [])

    def test_groot_versions_remain_separate(self) -> None:
        documents = []
        for name, arxiv_id in (
            ("GR00T N1", "2503.14734"),
            ("GR00T N1.5", "2512.00001"),
            ("GR00T N1.6", "2601.00001"),
        ):
            documents.append(
                parse_frontmatter(
                    self.write_note(
                        f"---\ntitle: {name}\narxiv_id: {arxiv_id}\n---\n",
                        f"{arxiv_id}.md",
                    )
                )
            )
        self.assertEqual(find_duplicate_groups(documents), [])

    def test_renderer_inserts_only_allowed_fields_in_fixed_order(self) -> None:
        raw = b"---\ntitle: Test\n---\nBody"
        path = self.root / "raw.md"
        path.write_bytes(raw)
        document = parse_frontmatter(path)
        rendered = render_deterministic_updates(
            document,
            {"arxiv_id": "2603.03596", "type": "paper"},
        )
        self.assertEqual(
            rendered,
            b"---\ntype: paper\narxiv_id: 2603.03596\ntitle: Test\n---\nBody",
        )
        with self.assertRaisesRegex(ValueError, "unsupported deterministic field"):
            render_deterministic_updates(document, {"review_status": "reviewed"})


if __name__ == "__main__":
    unittest.main()
