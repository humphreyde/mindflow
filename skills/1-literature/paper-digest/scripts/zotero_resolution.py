#!/usr/bin/env python3
"""Pure, read-only Zotero resolution policy used by paper-digest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, Sequence

from paper_schema import (
    normalize_arxiv_id,
    normalize_doi,
    normalize_official_url,
    normalize_title,
)


class ZoteroUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class ZoteroCandidate:
    item_key: str
    title: str


@dataclass(frozen=True)
class ZoteroAttachment:
    attachment_key: str
    title: str
    content_type: str
    is_pdf: bool


@dataclass(frozen=True)
class OfficialSource:
    kind: Literal["paper", "website", "github"]
    url: str


@dataclass(frozen=True)
class ZoteroResolution:
    status: Literal["exact", "ambiguous", "not_found", "unavailable"]
    candidate: ZoteroCandidate | None
    candidate_keys: tuple[str, ...]


class ZoteroBackend(Protocol):
    def by_item_key(self, item_key: str) -> Sequence[ZoteroCandidate]: ...

    def by_doi(self, doi: str) -> Sequence[ZoteroCandidate]: ...

    def by_arxiv_id(self, arxiv_id: str) -> Sequence[ZoteroCandidate]: ...

    def by_title(self, title: str) -> Sequence[ZoteroCandidate]: ...

    def list_attachments(self, item_key: str) -> Sequence[ZoteroAttachment]: ...


def _select(candidates: Sequence[ZoteroCandidate]) -> ZoteroResolution | None:
    by_key = {candidate.item_key: candidate for candidate in candidates}
    ordered = tuple(sorted(by_key))
    if not ordered:
        return None
    if len(ordered) > 1:
        return ZoteroResolution("ambiguous", None, ordered)
    candidate = by_key[ordered[0]]
    return ZoteroResolution("exact", candidate, ordered)


def resolve_zotero_reference(
    backend: ZoteroBackend,
    *,
    item_key: str | None,
    doi: str | None,
    arxiv_id: str | None,
    title: str,
) -> ZoteroResolution:
    try:
        if item_key and item_key.strip():
            if result := _select(backend.by_item_key(item_key.strip())):
                return result
        if normalized_doi := normalize_doi(doi or ""):
            if result := _select(backend.by_doi(normalized_doi)):
                return result
        if normalized_arxiv := normalize_arxiv_id(arxiv_id or ""):
            if result := _select(backend.by_arxiv_id(normalized_arxiv)):
                return result
        normalized_title = normalize_title(title)
        if normalized_title:
            candidates = tuple(
                candidate
                for candidate in backend.by_title(normalized_title)
                if normalize_title(candidate.title) == normalized_title
            )
            if result := _select(candidates):
                return result
    except ZoteroUnavailableError:
        return ZoteroResolution("unavailable", None, ())
    return ZoteroResolution("not_found", None, ())


def choose_read_source(
    resolution: ZoteroResolution,
    official_sources: Sequence[OfficialSource],
) -> OfficialSource | None:
    del resolution  # Zotero membership never supplies paper body or claims.
    priority = {"paper": 0, "website": 1, "github": 2}
    normalized: list[OfficialSource] = []
    for source in official_sources:
        if url := normalize_official_url(source.url):
            normalized.append(OfficialSource(source.kind, url))
    return min(normalized, key=lambda source: priority[source.kind], default=None)


def list_attachment_metadata(
    backend: ZoteroBackend, item_key: str
) -> tuple[ZoteroAttachment, ...]:
    return tuple(backend.list_attachments(item_key))


__all__ = [
    "OfficialSource",
    "ZoteroAttachment",
    "ZoteroBackend",
    "ZoteroCandidate",
    "ZoteroResolution",
    "ZoteroUnavailableError",
    "choose_read_source",
    "list_attachment_metadata",
    "resolve_zotero_reference",
]
