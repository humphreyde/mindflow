#!/usr/bin/env python3
"""Pure parsing, identity, validation, and rendering primitives for Paper notes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Mapping
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

import yaml


Severity = Literal["error", "review", "warning"]
IdentityKind = Literal["arxiv", "doi", "url-title", "missing"]
IdentityConfidence = Literal["high", "low", "review"]
ValidationMode = Literal["audit", "strict"]

DOMAINS = {
    "multimodal-understanding",
    "ai-agent",
    "embodied-ai",
    "general-ai",
}
REVIEW_STATUSES = {"inbox", "digested", "reviewed"}
RATINGS = {1, 2, 3}

DOMAIN_TAGS = {
    "multimodal-understanding": {"VLM", "video-LLM", "video-understanding"},
    "ai-agent": {
        "agentic-RL",
        "computer-use",
        "gui-agent",
        "web-agent",
        "auto-research",
    },
    "embodied-ai": {
        "manipulation",
        "navigation",
        "mobile-manipulation",
        "VLA",
        "imitation-learning",
        "diffusion-policy",
        "flow-matching",
        "VLN",
        "3D-representation",
        "spatial-reasoning",
        "spatial-memory",
        "scene-understanding",
        "semantic-map",
        "SLAM",
        "cross-embodiment",
        "legged",
        "world-action-model",
    },
    "general-ai": set(),
}
SHARED_TAGS = {
    "LLM",
    "world-model",
    "embodied-reasoning",
    "RL",
    "task-planning",
    "instruction-following",
}
CONTROLLED_TAGS = frozenset(SHARED_TAGS).union(*DOMAIN_TAGS.values())

_ARXIV_ID_RE = re.compile(
    r"(?i)(?:arxiv\s*:\s*|arxiv\.org/(?:abs|html|pdf)/)?"
    r"(?P<id>(?:\d{4}\.\d{4,6}|[a-z][a-z.\-]+/\d{7}))(?:v\d+)?(?:\.pdf)?(?:\s|$|[?#/])"
)
_DOI_RE = re.compile(r"(?i)^10\.\d{4,9}/[-._;()/:a-z0-9]+$")
_UNRESERVED = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class PaperIdentity:
    kind: IdentityKind
    key: str | None
    arxiv_id: str | None
    doi: str | None
    official_url: str | None
    normalized_title: str
    confidence: IdentityConfidence


@dataclass(frozen=True)
class PaperDocument:
    path: Path
    raw_bytes: bytes
    frontmatter: Mapping[str, object]
    opening_delimiter_end: int
    frontmatter_end: int
    newline: bytes


class UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key {key!r}")
        if key == "arxiv_id" and isinstance(value_node, yaml.ScalarNode):
            mapping[key] = value_node.value
        else:
            mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeySafeLoader.yaml_implicit_resolvers = {
    initial: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for initial, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def parse_frontmatter(path: Path) -> PaperDocument:
    raw = path.read_bytes()
    if raw.startswith(b"---\r\n"):
        newline = b"\r\n"
        opening_end = 5
    elif raw.startswith(b"---\n"):
        newline = b"\n"
        opening_end = 4
    else:
        raise ValueError(f"{path}: missing YAML frontmatter opening delimiter")

    closing_marker = newline + b"---" + newline
    closing_start = raw.find(closing_marker, opening_end - len(newline))
    if closing_start < 0:
        raise ValueError(f"{path}: missing YAML frontmatter closing delimiter")
    yaml_end = closing_start
    frontmatter_end = closing_start + len(closing_marker)
    yaml_bytes = raw[opening_end:yaml_end]
    try:
        yaml_text = yaml_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: frontmatter is not UTF-8") from exc
    try:
        loaded = yaml.load(yaml_text, Loader=UniqueKeySafeLoader)
    except ValueError:
        raise
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        raise ValueError(f"{path}: frontmatter must be a string-keyed mapping")
    return PaperDocument(
        path=path,
        raw_bytes=raw,
        frontmatter=loaded,
        opening_delimiter_end=opening_end,
        frontmatter_end=frontmatter_end,
        newline=newline,
    )


def normalize_arxiv_id(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    match = _ARXIV_ID_RE.search(candidate + " ")
    if not match:
        return None
    return match.group("id").lower()


def normalize_doi(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    candidate = re.sub(r"(?i)^doi\s*:\s*", "", candidate)
    candidate = re.sub(r"(?i)^https?://(?:dx\.)?doi\.org/", "", candidate)
    candidate = unquote(candidate).strip().rstrip(".,;").lower()
    return candidate if _DOI_RE.fullmatch(candidate) else None


def normalize_title(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def _normalize_percent_path(path: str) -> str:
    decoded = unquote(path, errors="strict")
    return quote(decoded, safe="/!$&'()*+,;=:@" + "".join(_UNRESERVED))


def normalize_official_url(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    try:
        parts = urlsplit(candidate)
        if parts.scheme.casefold() not in {"http", "https"}:
            return None
        if not parts.hostname or parts.username is not None or parts.password is not None:
            return None
        scheme = parts.scheme.casefold()
        host = parts.hostname.encode("idna").decode("ascii").casefold()
        try:
            port = parts.port
        except ValueError:
            return None
        if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
            host = f"{host}:{port}"
        path = _normalize_percent_path(parts.path or "/")
        if path != "/":
            path = path.rstrip("/")
        pairs = []
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
            folded = key.casefold()
            if folded.startswith("utm_") or folded in {"gclid", "fbclid"}:
                continue
            pairs.append((key, item_value))
        query = urlencode(sorted(pairs), doseq=True)
        return urlunsplit((scheme, host, path, query, ""))
    except (UnicodeError, ValueError):
        return None


def _string(frontmatter: Mapping[str, object], key: str) -> str | None:
    value = frontmatter.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _paper_arxiv(frontmatter: Mapping[str, object]) -> str | None:
    paper = _string(frontmatter, "paper")
    if paper and "arxiv.org/" in paper.casefold():
        return normalize_arxiv_id(paper)
    return None


def _paper_doi(frontmatter: Mapping[str, object]) -> str | None:
    paper = _string(frontmatter, "paper")
    if paper and "doi.org/" in paper.casefold():
        return normalize_doi(paper)
    return None


def _identity_conflicts(document: PaperDocument) -> list[ValidationIssue]:
    fm = document.frontmatter
    explicit_arxiv = normalize_arxiv_id(_string(fm, "arxiv_id") or "")
    paper_arxiv = _paper_arxiv(fm)
    explicit_doi = normalize_doi(_string(fm, "doi") or "")
    paper_doi = _paper_doi(fm)
    issues: list[ValidationIssue] = []
    if explicit_arxiv and paper_arxiv and explicit_arxiv != paper_arxiv:
        issues.append(
            ValidationIssue(
                "identity-conflict",
                "error",
                f"explicit arXiv {explicit_arxiv} conflicts with paper URL {paper_arxiv}",
            )
        )
    if explicit_doi and paper_doi and explicit_doi != paper_doi:
        issues.append(
            ValidationIssue(
                "identity-conflict",
                "error",
                f"explicit DOI {explicit_doi} conflicts with paper URL {paper_doi}",
            )
        )
    return issues


def resolve_identity(document: PaperDocument) -> PaperIdentity:
    fm = document.frontmatter
    arxiv_id = normalize_arxiv_id(_string(fm, "arxiv_id") or "") or _paper_arxiv(fm)
    doi = normalize_doi(_string(fm, "doi") or "") or _paper_doi(fm)
    title = normalize_title(_string(fm, "title") or "")
    official_url = None
    for field in ("paper", "website", "github"):
        raw_url = _string(fm, field)
        if raw_url and (normalized := normalize_official_url(raw_url)):
            official_url = normalized
            break
    if arxiv_id:
        return PaperIdentity("arxiv", f"arxiv:{arxiv_id}", arxiv_id, doi, official_url, title, "high")
    if doi:
        return PaperIdentity("doi", f"doi:{doi}", None, doi, official_url, title, "high")
    if official_url and title:
        return PaperIdentity(
            "url-title",
            f"url-title:{official_url}#{title}",
            None,
            None,
            official_url,
            title,
            "review",
        )
    return PaperIdentity("missing", None, None, None, official_url, title, "low")


def _tags(document: PaperDocument) -> list[str]:
    value = document.frontmatter.get("tags")
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(tag, str) for tag in value):
        return []
    return value


def classification_candidates(document: PaperDocument) -> tuple[tuple[str, ...], str | None]:
    tags = _tags(document)
    candidates = tuple(
        sorted(
            domain
            for domain, owned_tags in DOMAIN_TAGS.items()
            if any(tag in owned_tags for tag in tags)
        )
    )
    if not candidates:
        return (), "no-domain-candidate"
    if tags and tags[0] in SHARED_TAGS:
        return candidates, "shared-first"
    if len(candidates) > 1:
        return candidates, "multi-domain-candidate"
    return candidates, None


def _issue(code: str, severity: Severity, message: str) -> ValidationIssue:
    return ValidationIssue(code, severity, message)


def validate_paper(document: PaperDocument, mode: ValidationMode) -> list[ValidationIssue]:
    if mode not in {"audit", "strict"}:
        raise ValueError(f"unsupported validation mode: {mode}")
    fm = document.frontmatter
    issues = _identity_conflicts(document)
    identity = resolve_identity(document)
    tags_value = fm.get("tags")
    tags = _tags(document)

    if identity.kind == "url-title":
        issues.append(_issue("url-title-identity", "review", "official URL plus title requires review"))
    elif identity.kind == "missing":
        issues.append(_issue("missing-identity", "review" if mode == "audit" else "error", "paper has no usable identity"))

    if tags_value is not None and (not isinstance(tags_value, list) or not all(isinstance(tag, str) for tag in tags_value)):
        issues.append(_issue("invalid-tags", "review" if mode == "audit" else "error", "tags must be a list of strings"))
    for tag in sorted(set(tags) - CONTROLLED_TAGS):
        issues.append(_issue("unknown-tag", "review" if mode == "audit" else "error", f"unknown tag: {tag}"))
    if len(tags) > 4:
        issues.append(_issue("too-many-tags", "warning" if mode == "audit" else "error", f"paper has {len(tags)} tags; expected at most 4"))

    candidates, classification_issue = classification_candidates(document)
    if classification_issue:
        issues.append(
            _issue(
                classification_issue,
                "review" if mode == "audit" else "error",
                f"classification requires review; candidates={list(candidates)}",
            )
        )

    identity_prefix = identity.arxiv_id.split(".", 1)[0] if identity.arxiv_id and "." in identity.arxiv_id else None
    filename_prefix_match = re.match(r"^(\d{4})-", document.path.name)
    if identity_prefix and filename_prefix_match and filename_prefix_match.group(1) != identity_prefix:
        issues.append(
            _issue(
                "filename-identity-mismatch",
                "review",
                f"filename prefix {filename_prefix_match.group(1)} differs from arXiv prefix {identity_prefix}",
            )
        )

    if mode == "strict":
        if fm.get("type") != "paper":
            issues.append(_issue("missing-type", "error", "type must be paper"))
        primary_domain = fm.get("primary_domain")
        domains = fm.get("domains")
        if not isinstance(primary_domain, str) or not primary_domain:
            issues.append(_issue("missing-primary-domain", "error", "primary_domain is required"))
        elif primary_domain not in DOMAINS:
            issues.append(_issue("unknown-domain", "error", f"unknown primary_domain: {primary_domain}"))
        if not isinstance(domains, list) or not domains or not all(isinstance(value, str) for value in domains):
            issues.append(_issue("missing-domains", "error", "domains must be a non-empty string list"))
            domain_values: list[str] = []
        else:
            domain_values = domains
            for domain in sorted(set(domain_values) - DOMAINS):
                issues.append(_issue("unknown-domain", "error", f"unknown domain: {domain}"))
        if isinstance(primary_domain, str) and primary_domain and primary_domain not in domain_values:
            issues.append(_issue("primary-domain-not-in-domains", "error", "primary_domain must be present in domains"))
        if not 1 <= len(tags) <= 4:
            issues.append(_issue("invalid-tag-count", "error", "strict notes require 1-4 tags"))
        if fm.get("review_status") not in REVIEW_STATUSES:
            code = "missing-review-status" if fm.get("review_status") is None else "invalid-review-status"
            issues.append(_issue(code, "error", "review_status must be inbox, digested, or reviewed"))
        rating = fm.get("rating")
        if rating is not None and rating not in RATINGS:
            issues.append(_issue("invalid-rating", "error", "rating must be 1, 2, or 3"))
    else:
        primary_domain = fm.get("primary_domain")
        domains = fm.get("domains")
        if primary_domain is None or domains is None:
            issues.append(
                _issue(
                    "missing-classification",
                    "review",
                    "primary_domain and domains require review",
                )
            )
        if primary_domain is not None and primary_domain not in DOMAINS:
            issues.append(_issue("unknown-domain", "review", f"unknown primary_domain: {primary_domain}"))
        if isinstance(domains, list):
            for domain in sorted({value for value in domains if isinstance(value, str)} - DOMAINS):
                issues.append(_issue("unknown-domain", "review", f"unknown domain: {domain}"))

    return issues


def find_duplicate_groups(
    documents: Iterable[PaperDocument],
) -> list[tuple[str, tuple[Path, ...]]]:
    by_key: dict[str, list[Path]] = {}
    for document in documents:
        identity = resolve_identity(document)
        if identity.confidence != "high" or identity.key is None:
            continue
        by_key.setdefault(identity.key, []).append(document.path)
    return [
        (key, tuple(sorted(paths)))
        for key, paths in sorted(by_key.items())
        if len(paths) > 1
    ]


def render_deterministic_updates(
    document: PaperDocument, updates: Mapping[str, str]
) -> bytes:
    allowed = {"type", "arxiv_id"}
    unsupported = set(updates) - allowed
    if unsupported:
        raise ValueError(f"unsupported deterministic field: {sorted(unsupported)[0]}")
    insertions: list[bytes] = []
    for field in ("type", "arxiv_id"):
        if field not in updates:
            continue
        value = updates[field]
        if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
            raise ValueError(f"invalid deterministic value for {field}")
        existing = document.frontmatter.get(field)
        if existing is not None:
            if str(existing) != value:
                raise ValueError(f"existing {field} conflicts with deterministic update")
            continue
        insertions.append(f"{field}: {value}".encode("utf-8") + document.newline)
    split = document.opening_delimiter_end
    return document.raw_bytes[:split] + b"".join(insertions) + document.raw_bytes[split:]


__all__ = [
    "CONTROLLED_TAGS",
    "DOMAIN_TAGS",
    "DOMAINS",
    "PaperDocument",
    "PaperIdentity",
    "SHARED_TAGS",
    "ValidationIssue",
    "classification_candidates",
    "find_duplicate_groups",
    "normalize_arxiv_id",
    "normalize_doi",
    "normalize_official_url",
    "normalize_title",
    "parse_frontmatter",
    "render_deterministic_updates",
    "resolve_identity",
    "validate_paper",
]
