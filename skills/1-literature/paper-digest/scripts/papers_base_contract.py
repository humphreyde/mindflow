#!/usr/bin/env python3
"""Executable predicates mirroring the Papers Base formulas."""

from __future__ import annotations

from typing import Mapping

from paper_schema import CONTROLLED_TAGS


EXPECTED_FILTERS = {
    "is_cross_domain": 'list(domains).length > 1',
    "is_vla": 'list(tags).contains("VLA")',
    "is_wam": 'list(tags).contains("world-action-model") || (list(tags).contains("world-model") && list(tags).contains("VLA"))',
    "low_confidence_identity": '(!file.hasProperty("arxiv_id") || arxiv_id.isEmpty()) && (!file.hasProperty("doi") || doi.isEmpty())',
    "missing_identity": '(!file.hasProperty("arxiv_id") || arxiv_id.isEmpty()) && (!file.hasProperty("doi") || doi.isEmpty()) && (!file.hasProperty("paper") || paper.isEmpty()) && (!file.hasProperty("website") || website.isEmpty()) && (!file.hasProperty("github") || github.isEmpty())',
    "missing_classification": '!file.hasProperty("primary_domain") || primary_domain.isEmpty() || !file.hasProperty("domains") || list(domains).isEmpty()',
    "has_unknown_tag": 'list(tags).filter(!"VLM|video-LLM|video-understanding|agentic-RL|computer-use|gui-agent|web-agent|auto-research|manipulation|navigation|mobile-manipulation|VLA|imitation-learning|diffusion-policy|flow-matching|VLN|3D-representation|spatial-reasoning|spatial-memory|scene-understanding|semantic-map|SLAM|cross-embodiment|legged|world-action-model|LLM|world-model|embodied-reasoning|RL|task-planning|instruction-following".split("|").contains(value)).length > 0',
    "needs_review": 'formula.missing_identity || formula.low_confidence_identity || formula.missing_classification || formula.has_unknown_tag || !file.hasProperty("review_status") || review_status != "reviewed"',
}


def _list(frontmatter: Mapping[str, object], key: str) -> list[object]:
    value = frontmatter.get(key)
    return value if isinstance(value, list) else []


def _missing(frontmatter: Mapping[str, object], key: str) -> bool:
    value = frontmatter.get(key)
    return value is None or value == "" or value == []


def is_cross_domain(frontmatter: Mapping[str, object]) -> bool:
    return len(_list(frontmatter, "domains")) > 1


def is_vla(frontmatter: Mapping[str, object]) -> bool:
    return "VLA" in _list(frontmatter, "tags")


def is_wam(frontmatter: Mapping[str, object]) -> bool:
    tags = _list(frontmatter, "tags")
    return "world-action-model" in tags or ("world-model" in tags and "VLA" in tags)


def has_unknown_tag(frontmatter: Mapping[str, object]) -> bool:
    return any(not isinstance(tag, str) or tag not in CONTROLLED_TAGS for tag in _list(frontmatter, "tags"))


def has_low_confidence_identity(frontmatter: Mapping[str, object]) -> bool:
    return _missing(frontmatter, "arxiv_id") and _missing(frontmatter, "doi")


def _missing_identity(frontmatter: Mapping[str, object]) -> bool:
    return all(
        _missing(frontmatter, field)
        for field in ("arxiv_id", "doi", "paper", "website", "github")
    )


def _missing_classification(frontmatter: Mapping[str, object]) -> bool:
    return _missing(frontmatter, "primary_domain") or _missing(frontmatter, "domains")


def needs_review(frontmatter: Mapping[str, object]) -> bool:
    return (
        _missing_identity(frontmatter)
        or has_low_confidence_identity(frontmatter)
        or _missing_classification(frontmatter)
        or has_unknown_tag(frontmatter)
        or frontmatter.get("review_status") != "reviewed"
    )


__all__ = [
    "EXPECTED_FILTERS",
    "has_low_confidence_identity",
    "has_unknown_tag",
    "is_cross_domain",
    "is_vla",
    "is_wam",
    "needs_review",
]
