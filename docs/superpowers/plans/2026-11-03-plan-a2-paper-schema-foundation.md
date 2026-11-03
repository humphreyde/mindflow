# Plan A2 Paper Schema Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one validated Paper schema, produce a read-only identity/classification audit, and apply only deterministic frontmatter additions without rewriting research content.

**Architecture:** A pure `paper_schema.py` library owns YAML parsing, taxonomy validation, identity normalization, and duplicate grouping. A read-only audit CLI emits stable JSON/Markdown reports; a separate opt-in backfill CLI performs narrow line insertions and cannot classify papers. Obsidian Bases consumes the same field contract, while existing notes retain legacy `Archived` text until individually edited.

**Tech Stack:** Python 3.12, PyYAML 6.0.3+, `unittest`, Markdown/YAML frontmatter, JSON audit reports, Obsidian Bases, `uv` lockfile.

**Spec:** `docs/superpowers/specs/2026-10-29-para-notes-migration-design.md`

## Global Constraints

- `skills/1-literature/paper-digest/references/paper-note-template.md` is the only canonical Paper template. Do not recreate `Templates/Paper.md`.
- The current baseline is 182 root-level Paper notes: 175 high-confidence arXiv identities, 7 URL/title review items, and 0 exact duplicate identity groups. Stop and report if execution-time counts differ before any apply step.
- Run a read-only audit and obtain review of the ambiguous list before deterministic backfill.
- Deterministic backfill may add only `type: paper` to 182 notes and canonical `arxiv_id` to the 175 high-confidence notes from the approved audit.
- Do not automatically add `primary_domain`, `domains`, `review_status`, `doi`, `world-action-model`, or Zotero fields. Do not remove any tag.
- Do not rename Paper files. Filename/date mismatches remain warnings because path stability is a design requirement.
- Existing `1 - Archived` prose is valid legacy text. New output uses `1 - Peripheral`; never run a global string replacement over `Papers/`.
- `world-model` plus `VLA` is the WAM transition view; it does not authorize writing `world-action-model` into existing notes.
- Preserve every existing frontmatter line, quote, inline list, body byte, wikilink, and asset reference. Do not serialize existing notes with `yaml.safe_dump()`.
- The audit CLI is always read-only. Network calls, Zotero writes, author sync, global skill cutover, merge, and push are outside this plan.
- A2 starts after A1 has created `Workbench/PARA/Resources/`; execute the two plans sequentially to avoid README/SPEC conflicts.
- The frozen audit is manifest version `1`. Every item records both the exact pre-write byte hash and the expected post-write byte hash; apply accepts only those two states.
- Do not modify root `AGENTS.md` on this branch. The canonical checkout has user-owned uncommitted edits; repository-local routing lives in the two skills and documentation until an authorized integration reconciliation.
- Repository-local `daily-papers` wording is not a global cutover. The same-name global skill conflict remains an explicit blocker after this plan.
- Local task commits inside the approved A1/A2 scope do not require per-commit confirmation. The one backfill content gate and the final local-merge gate remain explicit.

---

### Task 1: Build the Pure Paper Schema and Identity Library

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `references/paper-schema.md`
- Create: `skills/1-literature/paper-digest/scripts/paper_schema.py`
- Create: `skills/1-literature/paper-digest/scripts/test_paper_schema.py`

**Interfaces:**
- Produces: `PaperDocument`, `PaperIdentity`, and `ValidationIssue` dataclasses
- Produces: `parse_frontmatter(path: Path) -> PaperDocument`
- Produces: `normalize_arxiv_id(value: str) -> str | None`
- Produces: `normalize_doi(value: str) -> str | None`
- Produces: `normalize_title(value: str) -> str`
- Produces: `normalize_official_url(value: str) -> str | None`
- Produces: `resolve_identity(document: PaperDocument) -> PaperIdentity`
- Produces: `validate_paper(document: PaperDocument, mode: Literal["audit", "strict"]) -> list[ValidationIssue]`
- Produces: `find_duplicate_groups(documents: Iterable[PaperDocument]) -> list[tuple[str, tuple[Path, ...]]]`
- Produces: `render_deterministic_updates(document: PaperDocument, updates: Mapping[str, str]) -> bytes`

Use these complete public contracts:

```python
Severity = Literal["error", "review", "warning"]
IdentityKind = Literal["arxiv", "doi", "url-title", "missing"]
IdentityConfidence = Literal["high", "low", "review"]
ValidationMode = Literal["audit", "strict"]

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
```

`key` is `arxiv:<id>`, `doi:<doi>`, or
`url-title:<normalized-url>#<normalized-title>`; missing identity has `key=None`.
All JSON-facing enum values are the exact lowercase strings above.

Classification candidates are audit-only and never become deterministic updates:
map every controlled non-shared tag to the domain section that owns it in
`references/tags.md`; `world-action-model` maps to `embodied-ai`. If exactly one
domain is supported, report it as a single-domain candidate. If no owned tag is
present, or any Shared tag is the first tag, or owned tags support multiple domains,
emit a review item (`no-domain-candidate`, `shared-first`, or
`multi-domain-candidate`) and report candidates without selecting `primary_domain`.
`render_deterministic_updates()` accepts only `type` and `arxiv_id`, inserts them
in that fixed order after the opening frontmatter delimiter, and returns bytes
without writing. The auditor and backfill tool must share this one renderer so
`expected_post_sha256` cannot drift from apply behavior.

Use this exact taxonomy projection; `SHARED_TAGS` never selects a domain:

```python
DOMAIN_TAGS = {
    "multimodal-understanding": {
        "VLM", "video-LLM", "video-understanding",
    },
    "ai-agent": {
        "agentic-RL", "computer-use", "gui-agent", "web-agent", "auto-research",
    },
    "embodied-ai": {
        "manipulation", "navigation", "mobile-manipulation", "VLA",
        "imitation-learning", "diffusion-policy", "flow-matching", "VLN",
        "3D-representation", "spatial-reasoning", "spatial-memory",
        "scene-understanding", "semantic-map", "SLAM", "cross-embodiment",
        "legged", "world-action-model",
    },
    "general-ai": set(),
}
SHARED_TAGS = {
    "LLM", "world-model", "embodied-reasoning", "RL", "task-planning",
    "instruction-following",
}
```

- [ ] **Step 1: Add PyYAML as a direct dependency**

Run:

```bash
uv add 'pyyaml>=6.0.3'
uv lock --check
```

Expected: `pyproject.toml` declares PyYAML directly and the lockfile remains consistent.

- [ ] **Step 2: Write parsing and duplicate-key tests**

Use a unique-key loader instead of accepting PyYAML's last-key-wins behavior.

```python
def test_duplicate_frontmatter_key_is_rejected(self) -> None:
    path = self.write_note("---\ntitle: One\ntitle: Two\n---\nBody\n")
    with self.assertRaisesRegex(ValueError, "duplicate key 'title'"):
        parse_frontmatter(path)

def test_arxiv_version_suffix_is_removed(self) -> None:
    self.assertEqual(normalize_arxiv_id("arXiv:2603.03596v2"), "2603.03596")

def test_yaml_timestamps_remain_strings_without_global_mutation(self) -> None:
    path = self.write_note("---\ndate_publish: 2026-03-03\ndate_added: 2026-11-03\n---\n")
    document = parse_frontmatter(path)
    self.assertEqual(document.frontmatter["date_publish"], "2026-03-03")
    self.assertEqual(document.frontmatter["date_added"], "2026-11-03")
    self.assertEqual(type(yaml.safe_load("value: 2026-03-03")["value"]).__name__, "date")

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
```

- [ ] **Step 3: Write schema and identity-priority tests**

Cover:

```python
def test_explicit_arxiv_conflict_with_paper_url_is_blocked(self) -> None:
    document = self.document(arxiv_id="2603.00001", paper="https://arxiv.org/abs/2603.00002")
    issues = validate_paper(document, mode="audit")
    self.assertTrue(any(issue.code == "identity-conflict" and issue.severity == "error" for issue in issues))

def test_primary_domain_must_be_in_domains(self) -> None:
    document = self.document(primary_domain="embodied-ai", domains=["ai-agent"])
    self.assertIn("primary-domain-not-in-domains", {issue.code for issue in validate_paper(document, mode="strict")})

def test_url_title_identity_needs_review(self) -> None:
    identity = resolve_identity(self.document(arxiv_id=None, doi=None, website="https://example.org/paper"))
    self.assertEqual(identity.confidence, "review")
```

Also cover malformed YAML, DOI normalization, unknown domains/tags, `review_status`, rating, 1–4 tags in strict mode, more than 4 tags as audit warning, same title with distinct strong IDs, and GR00T N1/N1.5/N1.6 remaining separate.

- [ ] **Step 4: Run the tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_paper_schema.py' -v
```

Expected: import failure because `paper_schema.py` does not exist.

- [ ] **Step 5: Implement unique YAML parsing and identity resolution**

Use `yaml.SafeLoader` with duplicate-key rejection:

```python
class UniqueKeySafeLoader(yaml.SafeLoader):
    pass

def _construct_unique_mapping(loader: UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate key {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping
```

Copy `yaml.SafeLoader.yaml_implicit_resolvers` into the subclass and remove only
entries whose tag is `tag:yaml.org,2002:timestamp`; never mutate the parent
resolver table. Register `_construct_unique_mapping` for the default mapping tag.
The parser must therefore preserve date-looking scalars as strings while leaving
global `yaml.safe_load()` behavior unchanged.

`normalize_official_url()` trims whitespace, accepts only `http`/`https` URLs with
a hostname and no credentials, lowercases scheme/IDNA hostname, removes default
ports and fragments, normalizes percent-encoding of unreserved path characters,
canonicalizes both an empty path and `/` to `/`, removes a non-root trailing slash,
drops query keys whose case-folded name matches `utm_*`, `gclid`, or `fbclid`, and
sorts the remaining query pairs by key/value. Invalid values return
`None`. `resolve_identity()` implements the fixed priority arXiv -> DOI -> verified
official URL plus normalized title. Only frontmatter `paper`, then `website`, then
`github` supplies the official URL; body references are never identity sources.
Add tests for reordered tracking queries, default ports, invalid schemes,
credential rejection, and two distinct normalized official URLs sharing a title.

- [ ] **Step 6: Write the canonical schema reference**

`references/paper-schema.md` defines:

```text
domains = multimodal-understanding | ai-agent | embodied-ai | general-ai
review_status = inbox | digested | reviewed
rating = 1 | 2 | 3
new rating labels = Peripheral | Frontier | Foundation
identity priority = arXiv ID | DOI | verified official URL + normalized title
```

Document migration-only fields and the distinction between `zotero_item_key` and `zotero_citekey`.

- [ ] **Step 7: Run the complete schema tests**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_paper_schema.py' -v
uv lock --check
```

Expected: PASS and lockfile check succeeds.

- [ ] **Step 8: Commit the schema library**

```bash
git add pyproject.toml uv.lock references/paper-schema.md \
  skills/1-literature/paper-digest/scripts/paper_schema.py \
  skills/1-literature/paper-digest/scripts/test_paper_schema.py
git commit -m "feat: define canonical paper schema"
```

---

### Task 2: Implement a Strictly Read-Only Audit CLI

**Files:**
- Create: `skills/1-literature/paper-digest/scripts/validate_papers.py`
- Create: `skills/1-literature/paper-digest/scripts/test_validate_papers.py`

**Interfaces:**
- Consumes: pure functions from `paper_schema.py`
- Produces CLI: `validate_papers.py --vault PATH --mode audit --json PATH --markdown PATH`
- Extends CLI: `validate_papers.py --write-approval-candidate PATH --manifest PATH --manifest-commit COMMIT`
- Produces: `audit_vault(vault: Path) -> AuditReport`
- Produces: `write_approval_candidate(manifest_path: Path, manifest_commit: str, output_path: Path) -> ApprovalReceipt`
- Produces stable item fields: `path`, `source_sha256`, `expected_post_sha256`, `identity`, `confidence`, `classification_candidates`, `issues`, `deterministic_updates`
- Produces summary fields: `total`, `arxiv_identity`, `url_title_review`, `duplicate_identity_groups`, `errors`, `needs_review`

The stable JSON contract is:

```python
MANIFEST_VERSION = 1

@dataclass(frozen=True)
class AuditItem:
    path: str
    source_sha256: str
    expected_post_sha256: str
    identity: PaperIdentity
    confidence: IdentityConfidence
    classification_candidates: tuple[str, ...]
    issues: tuple[ValidationIssue, ...]
    deterministic_updates: Mapping[str, str]

@dataclass(frozen=True)
class AuditSummary:
    total: int
    arxiv_identity: int
    url_title_review: int
    duplicate_identity_groups: int
    errors: int
    needs_review: int

@dataclass(frozen=True)
class AuditReport:
    manifest_version: int
    items: tuple[AuditItem, ...]
    duplicate_groups: tuple[tuple[str, tuple[str, ...]], ...]
    summary: AuditSummary

ApprovalStatus = Literal["pending", "confirmed"]

@dataclass(frozen=True)
class ApprovalReceipt:
    approval_version: int
    approval_status: ApprovalStatus
    manifest_path: str
    manifest_commit: str
    manifest_sha256: str
    approved_type_additions: int
    approved_arxiv_additions: int
    approved_other_fields: int
```

The JSON top level contains exactly `manifest_version`, `items`,
`duplicate_groups`, and `summary`. It contains no clock timestamp, so identical
inputs produce identical bytes.

- [ ] **Step 1: Write a fixture audit test**

```python
def test_audit_is_stable_and_does_not_modify_notes(self) -> None:
    before = sha256_tree(self.vault / "Papers")
    first = run_audit(self.vault)
    second = run_audit(self.vault)
    self.assertEqual(first, second)
    self.assertEqual(before, sha256_tree(self.vault / "Papers"))

def test_outputs_cannot_alias_paper_inputs(self) -> None:
    for output in (
        self.note,
        self.vault / "Papers/audit.json",
        self.vault / "paper-alias/audit.json",
    ):
        with self.subTest(output=output):
            with self.assertRaisesRegex(ValueError, "Papers"):
                write_report(self.report, json_path=output, markdown_path=self.out_md)

def test_atomic_failure_preserves_existing_output(self) -> None:
    self.out_json.write_bytes(b"old-json\n")
    with mock.patch("validate_papers.os.replace", side_effect=OSError("replace failed")):
        with self.assertRaises(OSError):
            write_report(self.report, json_path=self.out_json, markdown_path=self.out_md)
    self.assertEqual(self.out_json.read_bytes(), b"old-json\n")

def test_output_pair_cannot_alias_each_other(self) -> None:
    self.out_alias.symlink_to(self.out_json)
    with self.assertRaisesRegex(ValueError, "distinct"):
        write_report(
            self.report, json_path=self.out_json, markdown_path=self.out_alias
        )

def test_second_replace_failure_never_exposes_partial_file(self) -> None:
    self.out_json.write_bytes(b"old-json\n")
    self.out_md.write_bytes(b"old-md\n")
    real_replace = os.replace
    calls = 0
    def fail_second(source: str, target: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("second replace failed")
        real_replace(source, target)
    with mock.patch("validate_papers.os.replace", side_effect=fail_second):
        with self.assertRaises(OSError):
            write_report(self.report, json_path=self.out_json, markdown_path=self.out_md)
    self.assertIn(self.out_json.read_bytes(), {b"old-json\n", self.expected_json})
    self.assertEqual(self.out_md.read_bytes(), b"old-md\n")
```

The fixture makes `paper-alias` a symlink to `Papers` and `out_alias` a symlink to
the JSON target. Add the equivalent Markdown-output cases. Reject an output when
its lexical path is under `Papers/`, its resolved path is under the resolved
Papers directory, it aliases any input Paper, or the JSON and Markdown outputs
resolve to the same path. Resolve existing symlinks and the nearest existing
parent before creating output.

- [ ] **Step 2: Write severity and deterministic-update tests**

In audit mode, hard errors are malformed YAML and strong identity
conflicts/duplicates. Unknown tags, missing classification, URL/title identity,
shared-first/multi-domain classification, and filename/date mismatch are review
items; more than four legacy tags is a warning. In strict mode, unknown tags,
missing required canonical fields, invalid classification, and more than four
tags are errors. `summary.errors` counts only audit-mode `error`; any non-error
issue may contribute to `needs_review` without changing exit code 0.

```python
def test_audit_only_proposes_deterministic_fields(self) -> None:
    item = audit_item(self.arxiv_note)
    self.assertEqual(item.deterministic_updates, {"type": "paper", "arxiv_id": "2603.03596"})
    self.assertNotIn("primary_domain", item.deterministic_updates)
    self.assertNotIn("review_status", item.deterministic_updates)
```

- [ ] **Step 3: Run the tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_validate_papers.py' -v
```

Expected: import failure for `validate_papers`.

- [ ] **Step 4: Implement stable report generation**

Sort notes by vault-relative path, issues by `(severity, code, message)`, and duplicate groups by identity key. Serialize JSON with `sort_keys=True`, `ensure_ascii=False`, and `indent=2`; derive Markdown from the same in-memory report.

For each item, hash `document.raw_bytes` as `source_sha256`, run the shared pure
renderer with `deterministic_updates`, and hash the returned bytes as
`expected_post_sha256`. Write JSON and Markdown through separate same-directory
`NamedTemporaryFile(delete=False)` files, flush and `fsync`, and call
`os.replace()` only after both serializations succeed. Serialization and
pre-replace failures unlink only task-owned temporary files and leave both targets
unchanged. Each final replace is individually atomic; a replace error must report
which target failed and may never expose a partially written file.

`write_approval_candidate()` requires a 40-hex commit, reads the manifest blob
from that commit (not from uncommitted working bytes), requires manifest version
1 and exact 182/175/0 update counts, and serializes an `ApprovalReceipt` with
`approval_status="pending"`, the vault-relative manifest path, the supplied
commit, and the committed blob's computed SHA-256. It reuses the same output-path
guard and single-file atomic writer and never touches Papers.

The CLI exits:

```text
0 = audit completed with review items but no hard errors
1 = hard schema/identity errors
2 = invalid arguments or output failure
```

- [ ] **Step 5: Run focused and combined tests**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_*.py' -v
```

Expected: PASS.

- [ ] **Step 6: Commit the read-only auditor**

```bash
git add skills/1-literature/paper-digest/scripts/validate_papers.py \
  skills/1-literature/paper-digest/scripts/test_validate_papers.py
git commit -m "feat: add read-only paper audit"
```

---

### Task 3: Align Repository-Local Paper Workflows With the Canonical Schema

**Files:**
- Modify: `references/tags.md`
- Modify: `skills/1-literature/paper-digest/SKILL.md`
- Modify: `skills/1-literature/paper-digest/references/paper-note-template.md`
- Modify: `skills/1-literature/paper-digest/scripts/backfill_metrics.py`
- Create: `skills/1-literature/paper-digest/scripts/test_backfill_metrics.py`
- Create: `skills/1-literature/paper-digest/scripts/zotero_resolution.py`
- Create: `skills/1-literature/paper-digest/scripts/test_zotero_resolution.py`
- Modify: `skills/1-literature/daily-papers/SKILL.md`

**Interfaces:**
- Consumes: `paper_schema.parse_frontmatter()` and `resolve_identity()`
- Produces: new notes with canonical fields and `Peripheral` label
- Preserves: legacy `Archived` notes as valid audit inputs
- Produces: ambiguity-aware, read-only Zotero resolution with official-source fallback

- [ ] **Step 1: Write backfill-metrics identity regressions**

```python
def test_explicit_arxiv_id_wins_when_it_matches_url(self) -> None:
    paper = parse_paper(self.note(arxiv_id="2603.03596", paper="https://arxiv.org/abs/2603.03596v2"))
    self.assertEqual(paper.arxiv_id, "2603.03596")

def test_conflicting_explicit_and_url_ids_are_rejected(self) -> None:
    with self.assertRaisesRegex(ValueError, "identity conflict"):
        parse_paper(self.note(arxiv_id="2603.00001", paper="https://arxiv.org/abs/2603.00002"))
```

Keep the GEN-1 regression proving body citations are not used.

- [ ] **Step 2: Run the regression and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_backfill_metrics.py' -v
```

Expected: FAIL because `parse_paper()` ignores explicit `arxiv_id` and conflict detection.

- [ ] **Step 3: Reuse the shared identity parser**

Modify `backfill_metrics.parse_paper()` to use frontmatter data from `paper_schema.py`; do not add a body fallback. Preserve all network/cache behavior.

- [ ] **Step 4: Update schema, taxonomy, and rating output**

Add `world-action-model` to the controlled taxonomy and change the new-note target to 1–4 tags. Update the canonical template with `type`, `primary_domain`, `domains`, `review_status`, stable identity fields, Zotero fields, and migration fields from the spec.

Change only generator/template text:

```text
1 - Archived -> 1 - Peripheral
```

Do not edit `Papers/*.md`. Update `daily-papers` output so future recommendations also say `1 - Peripheral`.

Add the routing rule to both repository-local skills: inside MindFlow,
single-paper reading and note generation use repository `paper-digest`; the global
legacy `paper-reader` is used only when the user explicitly targets the old notes
vault or its legacy workflow. State that this changes repository-local behavior
only. Do not edit root `AGENTS.md` or any global skill in this plan.

- [ ] **Step 5: Implement and test the read-only Zotero boundary**

Create a pure adapter contract; it must not import SQLite or expose mutation calls:

```python
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

def resolve_zotero_reference(
    backend: ZoteroBackend,
    *,
    item_key: str | None,
    doi: str | None,
    arxiv_id: str | None,
    title: str,
) -> ZoteroResolution: ...

def choose_read_source(
    resolution: ZoteroResolution, official_sources: Sequence[OfficialSource]
) -> OfficialSource | None: ...
```

Resolution order is item key -> normalized DOI -> normalized arXiv ID -> title.
Every title comparison reuses `paper_schema.normalize_title()`; no second title
normalizer is allowed. Multiple candidates at any stage return `ambiguous` with
sorted item keys and no selected candidate; they never fall through to a weaker
stage. Catch only `ZoteroUnavailableError` as `unavailable`.

Using a fake backend, test: one exact item-key match returns `exact`; DOI wins over
arXiv/title; arXiv wins over title; two normalized-title matches return
`ambiguous`; a `ZoteroUnavailableError` returns `unavailable`, and
`choose_read_source()` then chooses by kind priority `paper`, `website`, `github`.
It runs every `OfficialSource.url` through `normalize_official_url()`, discards
invalid/credential-bearing URLs, and returns a new `OfficialSource` containing the
normalized URL; it never returns unchecked caller text.
Test attachment listing only when explicitly requested and assert returned
`ZoteroAttachment` objects have no local-path, body, or fulltext field. The tests
must assert the backend exposes no add/move/remove/save method and must not call a
live connector or local Zotero database.

- [ ] **Step 6: Update paper-digest validation steps**

Require duplicate resolution before writing and strict schema validation after
composing a new note. State that ambiguous identity blocks writing and that Zotero
lookup remains read-only and optional. Document this reachable orchestration path:

```text
paper-digest metadata
  -> invoke the installed global Zotero read-only capability on demand
  -> map returned item key / DOI / arXiv / normalized title into ZoteroCandidate
  -> apply zotero_resolution.py ambiguity and priority policy
  -> optionally map attachment listing to ZoteroAttachment metadata only
  -> always choose paper body/claims from normalized OfficialSource
  -> on unavailable/not_found, continue directly with OfficialSource
```

The Python Protocol is a policy seam for deterministic tests, not a second Zotero
client. The skill must not import a connector, read SQLite, expose local attachment
paths, or treat `ZoteroCandidate` as paper content. Indexed fulltext remains an
explicit user/evidence-driven call through the installed global Zotero capability,
outside default digest resolution.

- [ ] **Step 7: Run tests and both modified skill validators**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_*.py' -v
uv run --frozen python \
  /Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/1-literature/paper-digest
uv run --frozen python \
  /Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/1-literature/daily-papers
if rg -n '1[ —–-]+Archived' \
  skills/1-literature/paper-digest/references/paper-note-template.md \
  skills/1-literature/daily-papers/SKILL.md; then exit 1; fi
```

Expected: tests and both skill validations pass; the stale generator-label search
returns no matches. Report that the global same-name `daily-papers` conflict still
blocks a formal end-to-end daily pipeline cutover.

- [ ] **Step 8: Commit repository-local workflow alignment**

```bash
git add -- references/tags.md \
  skills/1-literature/paper-digest/SKILL.md \
  skills/1-literature/paper-digest/references/paper-note-template.md \
  skills/1-literature/paper-digest/scripts/backfill_metrics.py \
  skills/1-literature/paper-digest/scripts/test_backfill_metrics.py \
  skills/1-literature/paper-digest/scripts/zotero_resolution.py \
  skills/1-literature/paper-digest/scripts/test_zotero_resolution.py \
  skills/1-literature/daily-papers/SKILL.md
git diff --cached --name-only
git commit -m "feat: align repository paper workflows with canonical schema"
```

---

### Task 4: Create and Validate the Papers Base

**Files:**
- Create: `Workbench/PARA/Resources/Papers.base`
- Create: `skills/1-literature/paper-digest/scripts/papers_base_contract.py`
- Create: `skills/1-literature/paper-digest/scripts/test_papers_base.py`

**Interfaces:**
- Produces eight views: `All Papers`, `By Primary Domain`, `Cross-domain`, `VLA`, `WAM`, `Needs Review`, `Foundation`, `Recent`
- Consumes fields from `references/paper-schema.md`

- [ ] **Step 1: Invoke the Obsidian Bases skill before editing**

Read the current `$obsidian-bases` instructions in full. Use its supported `.base` syntax rather than inventing a parallel query format.

- [ ] **Step 2: Write the Base contract test**

```python
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

def test_base_exposes_exact_required_views(self) -> None:
    data = yaml.safe_load(self.base_path.read_text(encoding="utf-8"))
    self.assertEqual({view["name"] for view in data["views"]}, REQUIRED_VIEWS)
```

Also assert that all views are restricted to `Papers/`, WAM accepts
`world-action-model` or the transitional conjunction `world-model` plus `VLA`,
Needs Review covers missing identity, missing classification, unknown tags,
computed low confidence (both `arxiv_id` and `doi` absent), or
`review_status != reviewed`,
Foundation is `rating == 3`, and Recent sorts `date_added` descending.

- [ ] **Step 3: Run the test and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_papers_base.py' -v
```

Expected: FAIL because `Papers.base` does not exist.

- [ ] **Step 4: Create the Base with the eight fixed views**

Use this exact `.base` structure; keep each formula as the quoted string shown:

```yaml
filters:
  and:
    - 'file.folder == "Papers"'
    - 'file.ext == "md"'

formulas:
  is_cross_domain: 'list(domains).length > 1'
  is_vla: 'list(tags).contains("VLA")'
  is_wam: 'list(tags).contains("world-action-model") || (list(tags).contains("world-model") && list(tags).contains("VLA"))'
  low_confidence_identity: '(!file.hasProperty("arxiv_id") || arxiv_id.isEmpty()) && (!file.hasProperty("doi") || doi.isEmpty())'
  missing_identity: '(!file.hasProperty("arxiv_id") || arxiv_id.isEmpty()) && (!file.hasProperty("doi") || doi.isEmpty()) && (!file.hasProperty("paper") || paper.isEmpty()) && (!file.hasProperty("website") || website.isEmpty()) && (!file.hasProperty("github") || github.isEmpty())'
  missing_classification: '!file.hasProperty("primary_domain") || primary_domain.isEmpty() || !file.hasProperty("domains") || list(domains).isEmpty()'
  has_unknown_tag: 'list(tags).filter(!"VLM|video-LLM|video-understanding|agentic-RL|computer-use|gui-agent|web-agent|auto-research|manipulation|navigation|mobile-manipulation|VLA|imitation-learning|diffusion-policy|flow-matching|VLN|3D-representation|spatial-reasoning|spatial-memory|scene-understanding|semantic-map|SLAM|cross-embodiment|legged|world-action-model|LLM|world-model|embodied-reasoning|RL|task-planning|instruction-following".split("|").contains(value)).length > 0'
  needs_review: 'formula.missing_identity || formula.low_confidence_identity || formula.missing_classification || formula.has_unknown_tag || !file.hasProperty("review_status") || review_status != "reviewed"'

properties:
  title:
    displayName: Title
  date_publish:
    displayName: Published
  rating:
    displayName: Rating
  primary_domain:
    displayName: Primary Domain
  domains:
    displayName: Domains
  tags:
    displayName: Tags
  venue:
    displayName: Venue
  review_status:
    displayName: Review Status

views:
  - type: table
    name: All Papers
    order: [title, date_publish, rating, primary_domain, domains, tags, venue, review_status]
  - type: table
    name: By Primary Domain
    groupBy:
      property: primary_domain
      direction: ASC
    order: [title, date_publish, rating, domains, tags, review_status]
  - type: table
    name: Cross-domain
    filters: 'formula.is_cross_domain'
    order: [title, primary_domain, domains, tags, rating, review_status]
  - type: table
    name: VLA
    filters: 'formula.is_vla'
    order: [title, date_publish, rating, primary_domain, domains, tags, review_status]
  - type: table
    name: WAM
    filters: 'formula.is_wam'
    order: [title, date_publish, rating, primary_domain, domains, tags, review_status]
  - type: table
    name: Needs Review
    filters: 'formula.needs_review'
    order: [title, date_publish, primary_domain, domains, tags, review_status]
  - type: table
    name: Foundation
    filters: 'rating == 3'
    order: [title, date_publish, primary_domain, domains, tags, review_status]
  - type: table
    name: Recent
    order: [title, date_added, rating, primary_domain, domains, tags, review_status]
    sort:
      - property: date_added
        direction: DESC
```

Do not persist `identity_confidence` in Paper notes. The Base computes low
confidence as the absence of strong arXiv and DOI identity, so a fully classified
URL/title-only Paper still enters Needs Review. Do not duplicate Paper content or
create static per-tag MOCs.

Create `papers_base_contract.py` with pure predicates named
`is_cross_domain(frontmatter)`, `is_vla(frontmatter)`, `is_wam(frontmatter)`,
`has_unknown_tag(frontmatter)`, `has_low_confidence_identity(frontmatter)`, and
`needs_review(frontmatter)`. Use the same `DOMAIN_TAGS`/`SHARED_TAGS` constants
from `paper_schema.py`; `needs_review()` mirrors the formula above exactly. Export
`EXPECTED_FILTERS` containing the literal filter/formula strings so the test can
assert the `.base` file did not drift from the executable predicates.

- [ ] **Step 5: Run automated checks and record the live acceptance baseline**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_papers_base.py' -v
```

Add a fixture-free acceptance test that evaluates the implemented filters against
the current vault. It parses each root-level `Papers/*.md` with
`paper_schema.parse_frontmatter()`, applies the pure predicates from
`papers_base_contract.py`, and asserts:

```text
All Papers = 182
VLA = 70
WAM (world-action-model OR world-model+VLA) = 11
Foundation = 45
Needs Review = 182
```

Stop on count drift and report the changed view before committing. The Obsidian UI
smoke is not run from this worktree; Task 9 performs it only after an authorized
local merge in the canonical vault.

- [ ] **Step 6: Commit the Base**

```bash
git add Workbench/PARA/Resources/Papers.base \
  skills/1-literature/paper-digest/scripts/papers_base_contract.py \
  skills/1-literature/paper-digest/scripts/test_papers_base.py
git commit -m "feat: add paper classification views"
```

---

### Task 5: Generate and Freeze the Read-Only Audit

**Files:**
- Create: `Workbench/migrations/2026-11-03-paper-classification-identity-audit.json`
- Create: `Workbench/migrations/2026-11-03-paper-classification-identity-audit.md`
- Create: `Workbench/migrations/2026-11-03-paper-backfill-approval.json` with pending status
- Do not modify: `Papers/*.md`

**Interfaces:**
- Produces: review list and deterministic update manifest for Task 7

- [ ] **Step 1: Require a clean, fully tracked 182-note input set**

```bash
test -z "$(git status --porcelain --untracked-files=all -- Papers)"
test "$(find Papers -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')" = "182"
while IFS= read -r -d '' paper_path; do
  git ls-files --error-unmatch -- "$paper_path" >/dev/null
done < <(find Papers -maxdepth 1 -type f -name '*.md' -print0)
```

Expected: all 182 root-level Paper notes are tracked and none is staged,
modified, deleted, or untracked. Stop before audit generation on any mismatch.

- [ ] **Step 2: Create task-owned evidence paths and capture the Paper tree hash baseline**

Run Steps 2–6 in one persistent shell session so the owned temporary directory
and cleanup trap remain active; do not substitute a fixed `/tmp` path.

```bash
audit_tmp_dir=$(mktemp -d)
trap 'rm -rf "$audit_tmp_dir"' EXIT
find Papers -maxdepth 1 -type f -name '*.md' -exec shasum -a 256 {} + \
  | sort > "$audit_tmp_dir/papers.before"
```

- [ ] **Step 3: Run the audit into task-owned temporary outputs**

```bash
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/validate_papers.py \
  --vault . --mode audit \
  --json "$audit_tmp_dir/audit.json" \
  --markdown "$audit_tmp_dir/audit.md"
```

- [ ] **Step 4: Prove the audit was read-only**

```bash
find Papers -maxdepth 1 -type f -name '*.md' -exec shasum -a 256 {} + \
  | sort > "$audit_tmp_dir/papers.after"
cmp "$audit_tmp_dir/papers.before" "$audit_tmp_dir/papers.after"
test -z "$(git status --porcelain --untracked-files=all -- Papers)"
```

- [ ] **Step 5: Verify the approved baseline and manifest version or stop on drift**

```bash
jq -e '
  .manifest_version == 1 and
  .summary.total == 182 and
  .summary.arxiv_identity == 175 and
  .summary.url_title_review == 7 and
  .summary.duplicate_identity_groups == 0 and
  .summary.errors == 0
' "$audit_tmp_dir/audit.json"
```

Expected: true. If false, stop before copying reports or touching papers and report the changed counts/paths.

- [ ] **Step 6: Generate the tracked reports with the same atomic CLI**

Re-run the CLI directly to the two exact tracked paths. Its output guard and
same-directory atomic writer remain active; compare exact generated bytes:

```bash
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/validate_papers.py \
  --vault . --mode audit \
  --json Workbench/migrations/2026-11-03-paper-classification-identity-audit.json \
  --markdown Workbench/migrations/2026-11-03-paper-classification-identity-audit.md
cmp "$audit_tmp_dir/audit.json" \
  Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
cmp "$audit_tmp_dir/audit.md" \
  Workbench/migrations/2026-11-03-paper-classification-identity-audit.md
```

- [ ] **Step 7: Commit and identify the immutable audit snapshot**

```bash
git add Workbench/migrations/2026-11-03-paper-classification-identity-audit.json \
  Workbench/migrations/2026-11-03-paper-classification-identity-audit.md
git commit -m "docs: record paper schema audit"
audit_commit=$(git rev-parse HEAD)
audit_json=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
audit_sha256=$(shasum -a 256 "$audit_json" | awk '{print $1}')
test "$audit_sha256" = "$(git show "$audit_commit:$audit_json" | shasum -a 256 | awk '{print $1}')"
printf 'audit_commit=%s\naudit_sha256=%s\n' "$audit_commit" "$audit_sha256"
```

Record both printed values in the review request. They are the identity of the
artifact the human is being asked to approve; a later commit on the branch does
not change this pinned manifest object.

- [ ] **Step 8: Generate and commit the pending approval candidate**

```bash
audit_json=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
audit_commit=$(git log -1 --format=%H -- "$audit_json")
audit_sha256=$(shasum -a 256 "$audit_json" | awk '{print $1}')
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/validate_papers.py \
  --write-approval-candidate "$approval_path" \
  --manifest "$audit_json" \
  --manifest-commit "$audit_commit"
jq -e '
  .approval_version == 1 and
  .approval_status == "pending" and
  .manifest_path == "Workbench/migrations/2026-11-03-paper-classification-identity-audit.json" and
  .manifest_commit == $commit and
  .manifest_sha256 == $sha and
  .approved_type_additions == 182 and
  .approved_arxiv_additions == 175 and
  .approved_other_fields == 0
' --arg commit "$audit_commit" --arg sha "$audit_sha256" "$approval_path"
git add -- "$approval_path"
test "$(git diff --cached --name-only)" = "$approval_path"
git commit -m "docs: record pending paper backfill scope"
pending_approval_commit=$(git rev-parse HEAD)
pending_approval_sha256=$(git show "$pending_approval_commit:$approval_path" \
  | shasum -a 256 | awk '{print $1}')
test "$(git rev-list --count HEAD -- "$approval_path")" = "1"
test "$(git log -1 --format=%H -- "$approval_path")" = "$pending_approval_commit"
test "$(git diff --name-status "$pending_approval_commit^" \
  "$pending_approval_commit" -- "$approval_path" | awk '{print $1 ":" $2}')" \
  = "A:$approval_path"
test "$pending_approval_sha256" = "$(shasum -a 256 "$approval_path" | awk '{print $1}')"
printf 'pending_approval_commit=%s\npending_approval_sha256=%s\n' \
  "$pending_approval_commit" "$pending_approval_sha256"
```

Present this committed pending receipt together with the audit review. No value is
reconstructed after the human decision; confirmation changes only its status.

---

### Task 6: Review the Ambiguous and Classification Lists

**Files:**
- Review only: `Workbench/migrations/2026-11-03-paper-classification-identity-audit.json`
- Review only: `Workbench/migrations/2026-11-03-paper-classification-identity-audit.md`
- Modify after confirmation: `Workbench/migrations/2026-11-03-paper-backfill-approval.json`

**Interfaces:**
- Produces: explicit authorization bound to one audit commit, one JSON SHA-256, and only the manifest's deterministic updates

- [ ] **Step 1: Present the pinned manifest identity and exact review sets**

Report the `audit_commit`, `audit_sha256`, `pending_approval_commit`, and
`pending_approval_sha256` printed by Task 5, then the 7 URL/title identity items,
the 2 notes with 5 tags, every strong identity conflict if any, all filename/date
warnings, and primary-domain candidates separated from shared-first review items.

- [ ] **Step 2: State what will and will not be written**

```text
Will write: type=paper for 182 notes; canonical arxiv_id for 175 notes.
Will not write: any classification, review_status, DOI, Zotero field, WAM tag, filename change, tag deletion, or legacy rating text.
```

- [ ] **Step 3: Stop for human confirmation**

Ask the human to confirm the named `audit_commit`, `audit_sha256`,
`pending_approval_commit`, `pending_approval_sha256`, and the exact write counts
above. Do not implement or run `--apply` until all named pins and counts are
explicitly confirmed. This is one content-protection gate, not a per-file or per-commit
approval loop. Preserve the confirmed values verbatim in the task transcript;
Task 7 must receive them as external expected pins and compare live values to
them before dry-run or apply. Never reconstruct expected pins from the current
receipt, manifest, or Git history.

- [ ] **Step 4: Record the confirmed pins as machine-readable provenance**

Only after the human confirms the already-committed pending receipt, use
`apply_patch` to change its single literal line from
`"approval_status": "pending"` to `"approval_status": "confirmed"`. Do not
change or recompute any other field. Before editing, require the pending receipt
to be the only commit touching this new path so far. Unrelated-path commits are
allowed, but no intervening commit may touch the receipt path. Verify the
one-field diff, commit it, and record the immutable confirmed receipt identity:

```bash
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
: "${CONFIRMED_MANIFEST_COMMIT:?copy audit_commit verbatim from the human confirmation}"
: "${CONFIRMED_MANIFEST_SHA256:?copy audit_sha256 verbatim from the human confirmation}"
: "${CONFIRMED_PENDING_APPROVAL_COMMIT:?copy pending_approval_commit verbatim from the human confirmation}"
: "${CONFIRMED_PENDING_APPROVAL_SHA256:?copy pending_approval_sha256 verbatim from the human confirmation}"
pending_approval_commit=$(git log -1 --format=%H -- "$approval_path")
pending_approval_sha256=$(git show "$pending_approval_commit:$approval_path" \
  | shasum -a 256 | awk '{print $1}')
test "$(git rev-list --count HEAD -- "$approval_path")" = "1"
test "$pending_approval_commit" = "$CONFIRMED_PENDING_APPROVAL_COMMIT"
test "$pending_approval_sha256" = "$CONFIRMED_PENDING_APPROVAL_SHA256"
test "$(jq -r '.manifest_commit' "$approval_path")" = "$CONFIRMED_MANIFEST_COMMIT"
test "$(jq -r '.manifest_sha256' "$approval_path")" = "$CONFIRMED_MANIFEST_SHA256"
test -z "$(git status --porcelain --untracked-files=all -- "$approval_path")"
test "$(shasum -a 256 "$approval_path" | awk '{print $1}')" = "$pending_approval_sha256"
# Use apply_patch now to change only approval_status from pending to confirmed.
jq -e '
  .approval_version == 1 and
  .approval_status == "confirmed" and
  (.manifest_commit | test("^[0-9a-f]{40}$")) and
  (.manifest_sha256 | test("^[0-9a-f]{64}$")) and
  .approved_type_additions == 182 and
  .approved_arxiv_additions == 175 and
  .approved_other_fields == 0
' "$approval_path"
git add -- "$approval_path"
test "$(git diff --cached --name-only)" = "$approval_path"
test "$(git diff --cached --numstat -- "$approval_path" | awk '{print $1 ":" $2}')" = "1:1"
git diff --cached -- "$approval_path" | rg '^[-+]  "approval_status": "(pending|confirmed)"'
git commit -m "docs: record approved paper backfill scope"
approval_commit=$(git rev-parse HEAD)
approval_sha256=$(shasum -a 256 "$approval_path" | awk '{print $1}')
test "$(git rev-list --count "$approval_commit" -- "$approval_path")" = "2"
test "$(git log -2 --format=%H -- "$approval_path" | paste -sd ' ' -)" \
  = "$approval_commit $pending_approval_commit"
git merge-base --is-ancestor "$pending_approval_commit" "$approval_commit"
test "$(git diff --name-only "$pending_approval_commit" "$approval_commit" \
  -- "$approval_path")" = "$approval_path"
test "$(git diff --numstat "$pending_approval_commit" "$approval_commit" \
  -- "$approval_path" | awk '{print $1 ":" $2}')" = "1:1"
git diff --unified=0 "$pending_approval_commit" "$approval_commit" \
  -- "$approval_path" | rg '^[-+]  "approval_status": "(pending|confirmed)"'
test "$approval_sha256" = "$(git show "$approval_commit:$approval_path" | shasum -a 256 | awk '{print $1}')"
printf 'approval_commit=%s\napproval_sha256=%s\n' "$approval_commit" "$approval_sha256"
```

Task 7 requires the complete receipt-path history to contain exactly these two
path-touching commits in this order, anchored to the human-confirmed pending
commit and blob SHA. Unrelated-path commits may occur between them. It requires
the working receipt to be clean and byte-identical to the confirmation blob, and
requires `approval_status == confirmed` before reading its manifest pins.

---

### Task 7: Implement and Apply Narrow Deterministic Backfill

**Files:**
- Create: `skills/1-literature/paper-digest/scripts/backfill_paper_schema.py`
- Create: `skills/1-literature/paper-digest/scripts/test_backfill_paper_schema.py`
- Modify after confirmation: the 182 files listed in the frozen audit manifest under `Papers/`

**Interfaces:**
- Consumes: the committed audit JSON from Task 5
- Produces CLI: `backfill_paper_schema.py --vault PATH --manifest PATH --approval PATH --expected-manifest-commit COMMIT --expected-manifest-sha256 SHA256 --expected-pending-approval-commit COMMIT --expected-pending-approval-sha256 SHA256 [--apply | --emit-paper-pathspec | --verify-index]`
- Produces: `main(argv: Sequence[str] | None = None) -> int`; return `0` on success and `2` on validation failure, with diagnostics on stderr and no stdout payload before all four expected pins validate
- Produces: `parse_approved_manifest(raw: bytes) -> AuditReport`; malformed syntax or schema raises report-free `ManifestValidationError`
- Produces: `apply_manifest(vault: Path, manifest_path: Path, approval_path: Path, *, expectation: ApprovalExpectation, apply: bool) -> ApplyReport`
- Default: dry-run; no writes without `--apply`

```python
ApplyState = Literal["pending", "applied", "noop", "blocked"]

@dataclass(frozen=True)
class ApprovalExpectation:
    manifest_commit: str
    manifest_sha256: str
    pending_approval_commit: str
    pending_approval_sha256: str

class BackfillValidationError(RuntimeError):
    """Base class caught by the CLI boundary."""

class ApprovalValidationError(BackfillValidationError):
    """Receipt, history, external-pin, or pinned-object validation failed."""

class ManifestValidationError(BackfillValidationError):
    """The approved manifest schema or semantics are invalid."""

class ManifestDriftError(BackfillValidationError):
    """A complete item preflight found one or more blocked Paper states."""

    def __init__(self, message: str, report: "ApplyReport") -> None:
        super().__init__(message)
        self.report = report

@dataclass(frozen=True)
class ApplyItem:
    path: str
    state: ApplyState
    updates: Mapping[str, str]
    current_sha256: str

@dataclass(frozen=True)
class ApplyReport:
    manifest_version: int
    items: tuple[ApplyItem, ...]
    pending: int
    applied: int
    noop: int
    blocked: int
```

The test fixture initializes a temporary Git repository with 182 small Paper
notes and matching manifest items, commits the manifest, generates and commits a
pending receipt, changes only its status to confirmed in a second receipt commit,
asserts that those are the only two commits touching the receipt path, and passes
both paths plus `self.expectation: ApprovalExpectation` into every
`apply_manifest()` call. The expectation values are captured from the pending
receipt commit before confirmation; production receives the same four values
only from the human-confirmation transcript.

- [ ] **Step 1: Write raw-byte preservation and three-state hash tests**

Keep `BYTE_CASES`, `CLI_MODES`, and `PIN_MISMATCHES` at module scope. Insert
`_expectation_with()`, `_cli_args()`, and every `test_*` function below as methods
of the fixture's `BackfillPaperSchemaTests(unittest.TestCase)` class.

```python
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

BYTE_CASES = (
    b"---\ntitle: ASCII\n---\nBody\n",
    b"---\r\ntitle: CRLF\r\n---\r\nBody\r\n",
    b"---\ntitle: no-eof\n---\nBody",
    "---\ntitle: 机器人\n---\n正文\n".encode("utf-8"),
)

CLI_MODES = (
    ("dry-run", ()),
    ("apply", ("--apply",)),
    ("emit-paper-pathspec", ("--emit-paper-pathspec",)),
    ("verify-index", ("--verify-index",)),
)

PIN_MISMATCHES = (
    ("manifest_commit", "0" * 40),
    ("manifest_sha256", "0" * 64),
    ("pending_approval_commit", "0" * 40),
    ("pending_approval_sha256", "0" * 64),
)

def _expectation_with(self, **changes: str) -> ApprovalExpectation:
    values = {
        "manifest_commit": self.expectation.manifest_commit,
        "manifest_sha256": self.expectation.manifest_sha256,
        "pending_approval_commit": self.expectation.pending_approval_commit,
        "pending_approval_sha256": self.expectation.pending_approval_sha256,
    }
    values.update(changes)
    return ApprovalExpectation(**values)

def _cli_args(
    self, expectation: ApprovalExpectation, *mode_args: str
) -> list[str]:
    return [
        "--vault", str(self.vault),
        "--manifest", self.manifest_path.relative_to(self.vault).as_posix(),
        "--approval", self.approval_path.relative_to(self.vault).as_posix(),
        "--expected-manifest-commit", expectation.manifest_commit,
        "--expected-manifest-sha256", expectation.manifest_sha256,
        "--expected-pending-approval-commit",
        expectation.pending_approval_commit,
        "--expected-pending-approval-sha256", expectation.pending_approval_sha256,
        *mode_args,
    ]

def test_renderer_preserves_every_existing_byte(self) -> None:
    for raw in BYTE_CASES:
        with self.subTest(raw=raw):
            document = self.document_from_bytes(raw)
            rendered = render_deterministic_updates(
                document, {"type": "paper", "arxiv_id": "2603.03596"}
            )
            inserted = (
                b"type: paper" + document.newline
                + b"arxiv_id: 2603.03596" + document.newline
            )
            split = document.opening_delimiter_end
            self.assertEqual(rendered, raw[:split] + inserted + raw[split:])

def test_source_hash_applies_and_verifies_post_hash(self) -> None:
    report = apply_manifest(
        self.vault, self.manifest_path, self.approval_path,
        expectation=self.expectation, apply=True
    )
    self.assertEqual(report.items[0].state, "applied")
    self.assertEqual(sha256(self.note.read_bytes()), self.item.expected_post_sha256)

def test_dry_run_reports_all_pending_and_writes_nothing(self) -> None:
    before = {path: path.read_bytes() for path in self.paper_paths}
    report = apply_manifest(
        self.vault, self.manifest_path, self.approval_path,
        expectation=self.expectation, apply=False
    )
    self.assertEqual(
        (report.pending, report.applied, report.noop, report.blocked),
        (182, 0, 0, 0),
    )
    self.assertTrue(all(item.state == "pending" for item in report.items))
    self.assertEqual(before, {path: path.read_bytes() for path in self.paper_paths})

def test_pending_receipt_is_rejected_before_dry_run_or_apply(self) -> None:
    git(self.vault, "reset", "--hard", "HEAD^")
    for apply in (False, True):
        with self.subTest(apply=apply):
            with self.assertRaisesRegex(
                ApprovalValidationError, "not confirmed"
            ) as caught:
                apply_manifest(
                    self.vault, self.manifest_path, self.approval_path,
                    expectation=self.expectation, apply=apply
                )
            self.assertFalse(hasattr(caught.exception, "report"))

def test_post_hash_is_noop(self) -> None:
    self.note.write_bytes(self.expected_post_bytes)
    before = self.note.read_bytes()
    report = apply_manifest(
        self.vault, self.manifest_path, self.approval_path,
        expectation=self.expectation, apply=True
    )
    self.assertEqual(report.items[0].state, "noop")
    self.assertEqual(self.note.read_bytes(), before)

def test_blocked_dry_run_and_apply_return_same_report_and_write_nothing(self) -> None:
    self.note.write_bytes(b"---\ntitle: user edit\n---\n")
    before = {path: path.read_bytes() for path in self.paper_paths}
    reports = []
    for apply in (False, True):
        with self.subTest(apply=apply):
            with self.assertRaisesRegex(ManifestDriftError, "blocked") as caught:
                apply_manifest(
                    self.vault, self.manifest_path, self.approval_path,
                    expectation=self.expectation, apply=apply
                )
            reports.append(caught.exception.report)
            self.assertEqual(caught.exception.report.blocked, 1)
            self.assertEqual(
                before, {path: path.read_bytes() for path in self.paper_paths}
            )
    self.assertEqual(reports[0], reports[1])
    self.assertTrue(
        any(item.path == self.item.path and item.state == "blocked"
            for item in reports[0].items)
    )

def test_atomic_replace_preserves_source_mode(self) -> None:
    self.note.chmod(0o644)
    apply_manifest(
        self.vault, self.manifest_path, self.approval_path,
        expectation=self.expectation, apply=True
    )
    self.assertEqual(stat.S_IMODE(self.note.stat().st_mode), 0o644)

def test_dirty_or_recommitted_receipt_is_rejected(self) -> None:
    self.approval_path.write_text(
        self.approval_path.read_text(encoding="utf-8").replace(
            '"approved_type_additions": 182', '"approved_type_additions": 181'
        ),
        encoding="utf-8",
    )
    with self.assertRaisesRegex(
        ApprovalValidationError, "approval receipt"
    ) as caught:
        apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=False
        )
    self.assertFalse(hasattr(caught.exception, "report"))
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "tamper receipt")
    with self.assertRaisesRegex(
        ApprovalValidationError, "exactly two receipt commits"
    ) as caught:
        apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=False
        )
    self.assertFalse(hasattr(caught.exception, "report"))

def test_intermediate_pending_tamper_is_rejected(self) -> None:
    git(self.vault, "reset", "--hard", "HEAD^")
    self.approval_path.write_text(
        self.approval_path.read_text(encoding="utf-8").replace(
            '"approved_type_additions": 182', '"approved_type_additions": 181'
        ),
        encoding="utf-8",
    )
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "tamper pending receipt pins")
    self.approval_path.write_text(
        self.approval_path.read_text(encoding="utf-8").replace(
            '"approval_status": "pending"', '"approval_status": "confirmed"'
        ),
        encoding="utf-8",
    )
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "confirm tampered receipt")
    with self.assertRaisesRegex(
        ApprovalValidationError, "exactly two receipt commits"
    ) as caught:
        apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=False
        )
    self.assertFalse(hasattr(caught.exception, "report"))

def test_tamper_then_revert_before_confirmation_is_rejected(self) -> None:
    git(self.vault, "reset", "--hard", "HEAD^")
    original = self.approval_path.read_bytes()
    self.approval_path.write_bytes(
        original.replace(
            b'"approved_type_additions": 182',
            b'"approved_type_additions": 181',
        )
    )
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "tamper pending receipt")
    self.approval_path.write_bytes(original)
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "restore pending receipt bytes")
    self.approval_path.write_text(
        self.approval_path.read_text(encoding="utf-8").replace(
            '"approval_status": "pending"', '"approval_status": "confirmed"'
        ),
        encoding="utf-8",
    )
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "confirm restored receipt")
    with self.assertRaisesRegex(
        ApprovalValidationError, "exactly two receipt commits"
    ) as caught:
        apply_manifest(
            self.vault, self.manifest_path, self.approval_path,
            expectation=self.expectation, apply=False
        )
    self.assertFalse(hasattr(caught.exception, "report"))

def test_unrelated_intervening_commit_is_allowed(self) -> None:
    git(self.vault, "reset", "--hard", "HEAD^")
    unrelated = self.vault / "unrelated.txt"
    unrelated.write_text("intervening commit\n", encoding="utf-8")
    git(self.vault, "add", str(unrelated))
    git(self.vault, "commit", "-m", "add unrelated intervening commit")
    self.approval_path.write_text(
        self.approval_path.read_text(encoding="utf-8").replace(
            '"approval_status": "pending"', '"approval_status": "confirmed"'
        ),
        encoding="utf-8",
    )
    git(self.vault, "add", str(self.approval_path))
    git(self.vault, "commit", "-m", "confirm after intervening commit")
    report = apply_manifest(
        self.vault, self.manifest_path, self.approval_path,
        expectation=self.expectation, apply=False
    )
    self.assertEqual((report.pending, report.blocked), (182, 0))

def test_external_human_confirmed_pins_are_required(self) -> None:
    for field, bad_value in PIN_MISMATCHES:
        expectation = self._expectation_with(**{field: bad_value})
        with self.subTest(field=field):
            with self.assertRaisesRegex(
                ApprovalValidationError, "human-confirmed"
            ) as caught:
                apply_manifest(
                    self.vault, self.manifest_path, self.approval_path,
                    expectation=expectation, apply=False
                )
            self.assertFalse(hasattr(caught.exception, "report"))

def test_malformed_manifest_raises_report_free_validation_error(self) -> None:
    malformed_cases = (
        b"{",
        b'{"manifest_version": 2, "items": "not-a-list"}',
    )
    for raw in malformed_cases:
        with self.subTest(raw=raw):
            with self.assertRaises(ManifestValidationError) as caught:
                parse_approved_manifest(raw)
            self.assertFalse(hasattr(caught.exception, "report"))

def test_every_cli_mode_rejects_each_single_pin_mismatch(self) -> None:
    before = {path: path.read_bytes() for path in self.paper_paths}
    for mode_name, mode_args in CLI_MODES:
        for field, bad_value in PIN_MISMATCHES:
            expectation = self._expectation_with(**{field: bad_value})
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(mode=mode_name, field=field):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main(self._cli_args(expectation, *mode_args))
                self.assertEqual(exit_code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("human-confirmed", stderr.getvalue())
                self.assertEqual(
                    before, {path: path.read_bytes() for path in self.paper_paths}
                )
```

Use `ApprovalValidationError` for an untracked/dirty receipt, invalid receipt
history or status, any external-pin mismatch, and any failure to resolve the
human-pinned manifest path/commit/blob object. This exception never carries an
`ApplyReport`. Every mismatch between a supplied expectation and a receipt/Git
object includes `human-confirmed` in the message so CLI failures cannot be
confused with mode-specific index or Paper-state errors. The tool never infers
expected values from the current receipt, manifest, or Git history.

Only after approval and pinned-object validation succeeds, parse the manifest.
Raise `ManifestValidationError`, also without an `ApplyReport`, for manifest
versions other than `1`, malformed structure, missing/malformed source or post
hashes, fields outside `{type, arxiv_id}`, duplicate paths, paths outside
root-level `Papers/*.md`, or an identity that no longer matches the note. Reserve
`ManifestDriftError(report=complete_report)` exclusively for a completed Paper
item preflight containing one or more `blocked` current-byte states.

Before trusting receipt pins, require the approval path to be tracked and clean
and the working bytes to equal its latest committed blob. Parse only
`approval_version` and `approval_status` first. A clean pending receipt whose
commit/blob match the external pending expectation is rejected as `not confirmed`.
For a confirmed receipt, resolve the complete commit history
touching that path and require exactly two commits: the latest
`approval_commit` and the earlier
`pending_approval_commit`. Require the earlier commit and its blob SHA-256 to
equal the human-confirmed expectation and require it to be an ancestor of
`approval_commit`; unrelated-path commits between the two are allowed. Require
the working bytes' SHA-256 to equal `git show <approval_commit>:<approval_path>`.
Diff the two receipt blobs and require exactly one line change:
`approval_status: pending` -> `approval_status: confirmed`; all other parsed
fields must be equal. Any earlier, intermediate,
or later receipt-path commit therefore fails before pins are trusted. Require
the receipt's vault-relative `manifest_path` to equal the CLI manifest path and
its manifest commit/SHA fields to equal the external expectation before
validating the manifest commit/blob/hash. Also require the latest commit touching
the manifest path and the current manifest bytes to equal that expected commit
and blob; a later modify-or-revert commit is not accepted.

Make all four `--expected-*` arguments required in every CLI mode. `main()`
constructs one `ApprovalExpectation` and passes it unchanged into the default
dry-run, `--apply`, `--emit-paper-pathspec`, and `--verify-index` dispatch paths.
Each path runs the shared approval/manifest validation before writing Papers,
reading or validating the Git index, or emitting pathspec bytes. `main()` catches
`BackfillValidationError`, emits no stdout payload, and returns `2`.
`ApprovalValidationError` and `ManifestValidationError` write only their
diagnostic to stderr; `ManifestDriftError` writes its diagnostic plus its complete
report to stderr. The module entry point is `raise SystemExit(main())`.

- [ ] **Step 2: Run the tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_backfill_paper_schema.py' -v
```

Expected: import failure for `backfill_paper_schema`.

- [ ] **Step 3: Implement narrow line insertion**

Insert fields immediately after the opening `---` in this order:

```yaml
type: paper
arxiv_id: 2603.03596
```

Omit `arxiv_id` for the 7 review items. Reuse
`paper_schema.render_deterministic_updates()`; do not decode and re-encode note
content. Preflight every manifest item before any write. The only accepted states
are:

```text
current == source_sha256        -> pending; rendered hash must equal expected_post_sha256
current == expected_post_sha256 -> noop
anything else                   -> blocked; write nothing
```

After a clean preflight, write each pending byte sequence through a temporary file
in the note's own directory, copy `stat.S_IMODE(source.stat().st_mode)` with
`os.fchmod()`, flush and `fsync()` the temporary file, and then call
`os.replace()`. A crash may leave a mixed
source/post set, but rerunning is safe because both states are accepted. The
dry-run prints a stable state/path/update list and exits nonzero on any blocked
item.

`apply_manifest()` always builds the complete report before deciding whether it
may write. A clean dry-run returns the report and performs zero writes. Any blocked
item raises `ManifestDriftError` carrying that same report; the CLI prints the
report and exits nonzero. Approval or manifest validation failures raise their
report-free exception before Paper state evaluation or any write.

- [ ] **Step 4: Run all backfill tests**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_backfill_paper_schema.py' -v
```

Expected: PASS.

- [ ] **Step 5: Recheck clean inputs and the human-approved manifest pins**

Copy the four pins character-for-character from the human confirmation in Task 6
into the required `CONFIRMED_*` environment variables. Do not populate them from
the receipt, manifest, or Git history. Then recompute every current value and
compare it with those external expectations:

```bash
manifest_path=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
: "${CONFIRMED_MANIFEST_COMMIT:?copy audit_commit verbatim from the human confirmation}"
: "${CONFIRMED_MANIFEST_SHA256:?copy audit_sha256 verbatim from the human confirmation}"
: "${CONFIRMED_PENDING_APPROVAL_COMMIT:?copy pending_approval_commit verbatim from the human confirmation}"
: "${CONFIRMED_PENDING_APPROVAL_SHA256:?copy pending_approval_sha256 verbatim from the human confirmation}"
receipt_manifest_commit=$(jq -r '.manifest_commit' "$approval_path")
receipt_manifest_sha256=$(jq -r '.manifest_sha256' "$approval_path")
approval_commit=$(git log -1 --format=%H -- "$approval_path")
approval_sha256=$(shasum -a 256 "$approval_path" | awk '{print $1}')
actual_pending_approval_commit=$(git log -2 --format=%H -- "$approval_path" | tail -n 1)
actual_pending_approval_sha256=$(git show \
  "$CONFIRMED_PENDING_APPROVAL_COMMIT:$approval_path" \
  | shasum -a 256 | awk '{print $1}')
current_manifest_commit=$(git log -1 --format=%H -- "$manifest_path")
current_manifest_sha256=$(shasum -a 256 "$manifest_path" | awk '{print $1}')
git ls-files --error-unmatch -- "$approval_path" >/dev/null
test -z "$(git status --porcelain --untracked-files=all -- "$approval_path")"
test "$(git rev-list --count HEAD -- "$approval_path")" = "2"
test "$actual_pending_approval_commit" = "$CONFIRMED_PENDING_APPROVAL_COMMIT"
test "$actual_pending_approval_sha256" = "$CONFIRMED_PENDING_APPROVAL_SHA256"
git merge-base --is-ancestor "$CONFIRMED_PENDING_APPROVAL_COMMIT" "$approval_commit"
test "$(git diff --numstat "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  "$approval_commit" -- "$approval_path" | awk '{print $1 ":" $2}')" = "1:1"
git diff --unified=0 "$CONFIRMED_PENDING_APPROVAL_COMMIT" "$approval_commit" \
  -- "$approval_path" | rg '^[-+]  "approval_status": "(pending|confirmed)"'
test "$approval_sha256" = "$(git show "$approval_commit:$approval_path" | shasum -a 256 | awk '{print $1}')"
test "$(jq -r '.approval_status' "$approval_path")" = "confirmed"
test "$receipt_manifest_commit" = "$CONFIRMED_MANIFEST_COMMIT"
test "$receipt_manifest_sha256" = "$CONFIRMED_MANIFEST_SHA256"
test "$current_manifest_commit" = "$CONFIRMED_MANIFEST_COMMIT"
test "$current_manifest_sha256" = "$CONFIRMED_MANIFEST_SHA256"
test -z "$(git status --porcelain --untracked-files=all -- Papers)"
test "$(jq '.items | length' "$manifest_path")" = "182"
test "$(git show "$CONFIRMED_MANIFEST_COMMIT:$manifest_path" | shasum -a 256 | awk '{print $1}')" = "$CONFIRMED_MANIFEST_SHA256"
```

The `CONFIRMED_*` values come only from the human-confirmation transcript. The
receipt and current Git objects are independently recomputed and must match.
Every CLI invocation in Steps 6–9 receives and revalidates the same four external
pins.

- [ ] **Step 6: Run dry-run with the approved pins and compare with the frozen manifest**

```bash
manifest_path=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  --vault . \
  --manifest "$manifest_path" \
  --approval "$approval_path" \
  --expected-manifest-commit "$CONFIRMED_MANIFEST_COMMIT" \
  --expected-manifest-sha256 "$CONFIRMED_MANIFEST_SHA256" \
  --expected-pending-approval-commit "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  --expected-pending-approval-sha256 "$CONFIRMED_PENDING_APPROVAL_SHA256"
```

Expected: 182 `type` additions, 175 `arxiv_id` additions, 0 other fields, 0 blocked items.

- [ ] **Step 7: Apply once and verify exact scope**

```bash
manifest_path=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  --vault . \
  --manifest "$manifest_path" \
  --approval "$approval_path" \
  --expected-manifest-commit "$CONFIRMED_MANIFEST_COMMIT" \
  --expected-manifest-sha256 "$CONFIRMED_MANIFEST_SHA256" \
  --expected-pending-approval-commit "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  --expected-pending-approval-sha256 "$CONFIRMED_PENDING_APPROVAL_SHA256" \
  --apply
git diff --numstat -- Papers
```

Inspect that every diff adds one or two frontmatter lines and removes zero lines.

- [ ] **Step 8: Prove idempotency and audit consistency in an owned temp directory**

```bash
backfill_tmp_dir=$(mktemp -d)
trap 'rm -rf "$backfill_tmp_dir"' EXIT
manifest_path=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
git diff -- Papers > "$backfill_tmp_dir/first.diff"
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  --vault . \
  --manifest "$manifest_path" \
  --approval "$approval_path" \
  --expected-manifest-commit "$CONFIRMED_MANIFEST_COMMIT" \
  --expected-manifest-sha256 "$CONFIRMED_MANIFEST_SHA256" \
  --expected-pending-approval-commit "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  --expected-pending-approval-sha256 "$CONFIRMED_PENDING_APPROVAL_SHA256" \
  --apply
git diff -- Papers > "$backfill_tmp_dir/second.diff"
cmp "$backfill_tmp_dir/first.diff" "$backfill_tmp_dir/second.diff"

uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/validate_papers.py \
  --vault . --mode audit \
  --json "$backfill_tmp_dir/audit-after.json" \
  --markdown "$backfill_tmp_dir/audit-after.md"
jq -e '.summary.total == 182 and .summary.arxiv_identity == 175 and .summary.duplicate_identity_groups == 0 and .summary.errors == 0' \
  "$backfill_tmp_dir/audit-after.json"
```

- [ ] **Step 9: Stage only the approved paths and verify index semantics**

```bash
stage_tmp_dir=$(mktemp -d)
trap 'rm -rf "$stage_tmp_dir"' EXIT
manifest_path=Workbench/migrations/2026-11-03-paper-classification-identity-audit.json
approval_path=Workbench/migrations/2026-11-03-paper-backfill-approval.json
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  --vault . --manifest "$manifest_path" \
  --approval "$approval_path" \
  --expected-manifest-commit "$CONFIRMED_MANIFEST_COMMIT" \
  --expected-manifest-sha256 "$CONFIRMED_MANIFEST_SHA256" \
  --expected-pending-approval-commit "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  --expected-pending-approval-sha256 "$CONFIRMED_PENDING_APPROVAL_SHA256" \
  --emit-paper-pathspec > "$stage_tmp_dir/papers.pathspec"
git --literal-pathspecs add \
  --pathspec-from-file="$stage_tmp_dir/papers.pathspec" --pathspec-file-nul
git add -- \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  skills/1-literature/paper-digest/scripts/test_backfill_paper_schema.py
uv run --frozen python -B \
  skills/1-literature/paper-digest/scripts/backfill_paper_schema.py \
  --vault . --manifest "$manifest_path" \
  --approval "$approval_path" \
  --expected-manifest-commit "$CONFIRMED_MANIFEST_COMMIT" \
  --expected-manifest-sha256 "$CONFIRMED_MANIFEST_SHA256" \
  --expected-pending-approval-commit "$CONFIRMED_PENDING_APPROVAL_COMMIT" \
  --expected-pending-approval-sha256 "$CONFIRMED_PENDING_APPROVAL_SHA256" \
  --verify-index
git diff --cached --check
```

`--emit-paper-pathspec` writes exactly 182 NUL-terminated literal repository paths;
`git --literal-pathspecs` prevents pathspec magic or wildcard interpretation.
`--verify-index` requires the cached path set to equal those paths plus the two
explicit tool files, parses the cached Paper patch, and rejects every deletion,
context rewrite, or added line other than `type: paper` and the manifest-approved
`arxiv_id`. For every Paper path it hashes `git show :<path>` bytes and requires
the result to equal that item's `expected_post_sha256`. It also requires 182
changed Paper files, 182 type additions, and 175 arXiv additions.

- [ ] **Step 10: Commit the tool and deterministic data migration**

```bash
git commit -m "feat: backfill deterministic paper identity fields"
```

---

### Task 8: Align Documentation and Run the Full Gate

**Files:**
- Modify: `README.md`
- Modify: `docs/SPEC.md`
- Modify: `docs/INSTALL.md`

**Interfaces:**
- Consumes: Tasks 1–7
- Produces: canonical documentation and final verification evidence

- [ ] **Step 1: Document the canonical template and schema**

Update README/SPEC to point Paper generation to:

```text
skills/1-literature/paper-digest/references/paper-note-template.md
references/paper-schema.md
```

Document flat `Papers/`, metadata classification, the Papers Base, `Peripheral` compatibility, and the read-only audit -> review -> deterministic apply sequence. Do not claim all existing notes have classification fields.

In `docs/INSTALL.md`, add a `Local Obsidian paper workspace` subsection that
requires the core Bases feature, confirms `.obsidian/templates.json` uses
`Templates`, points users to `Workbench/PARA/Resources/Papers.base`, and states
that repository-local skill setup does not install, disable, or reconcile global
`paper-reader`/`daily-papers` skills.

- [ ] **Step 2: Run the full Python gate**

```bash
uv lock --check
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_*.py' -v
```

- [ ] **Step 3: Run content and documentation guards**

```bash
if rg -n 'Templates/Paper\.md' README.md docs/SPEC.md docs/INSTALL.md; then exit 1; fi
if rg -n '1[ —–-]+Archived' \
  skills/1-literature/paper-digest/references/paper-note-template.md \
  skills/1-literature/daily-papers/SKILL.md; then exit 1; fi
test "$(find Papers -maxdepth 1 -type f -name '*.md' | wc -l | tr -d ' ')" = "182"
git diff --check
```

- [ ] **Step 4: Validate every repository skill package**

```bash
skill_tmp_dir=$(mktemp -d)
trap 'rm -rf "$skill_tmp_dir"' EXIT
skill_list="$skill_tmp_dir/skills"
find skills -name SKILL.md -exec dirname {} \; > "$skill_list"
test "$(wc -l < "$skill_list" | tr -d ' ')" = "15"
while IFS= read -r skill_dir; do
  uv run --frozen python \
    /Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
    "$skill_dir"
done < "$skill_list"
```

Expected: all 15 repository skill directories validate. This includes both
modified paper skills and the A1 `mindflow-context` package.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md docs/SPEC.md docs/INSTALL.md
git commit -m "docs: document paper schema foundation"
```

- [ ] **Step 6: Prepare the completion report**

Report test count, audit summary, the 7 unresolved identity-review items,
classification gaps, the two 5-tag warnings, filename/date warnings, backfill
commit, zero deleted lines in Papers, and all remaining boundaries. Explicitly
name the global same-name `daily-papers` conflict and root `AGENTS.md`
reconciliation as unfinished integration items. Do not merge, push, alter Zotero,
migrate legacy `/Users/limx/notes`, or classify ambiguous papers.

---

### Task 9: Verify the Combined A1+A2 Branch and Integrate Once

**Files:**
- Verify only before authorization
- Local merge after authorization: `/Users/limx/mindflow`
- Verify local-only UI state after merge: `/Users/limx/mindflow/.obsidian/`

**Interfaces:**
- Consumes: every A1 and A2 task on `codex/notes-migration-design`
- Produces: one combined integration report and one local-merge authorization gate
- Preserves: all pre-existing canonical working-tree changes

- [ ] **Step 1: Run the combined branch gates**

```bash
uv lock --check
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
uv run --frozen python -B \
  skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault . --self-test
uv run --frozen python -B -m unittest discover \
  -s skills/1-literature/paper-digest/scripts -p 'test_*.py' -v
git diff --check
git status --short
```

Expected: all branch tests pass and the only working-tree changes are any final
reporting edits that this task commits explicitly. Re-run the all-15 skill loop
from Task 8 and record its count.

- [ ] **Step 2: Run the focused Quartz gates without a visual build**

From `.website/`, use the existing lockfile:

```bash
npm test -- quartz/util/glob.test.ts
npx --no-install tsc --noEmit
```

Expected: the `Projects/**` exclusion regression and TypeScript check pass. If
encrypted local dependencies make Node execution impossible, capture the exact
command/error as an environment limitation; do not reinstall, decrypt, or mutate
dependencies in this plan.

- [ ] **Step 3: Prove canonical user changes are outside the branch diff**

```bash
canonical_root=/Users/limx/mindflow
git -C "$canonical_root" status --short
canonical_head=$(git -C "$canonical_root" rev-parse HEAD)
git merge-base --is-ancestor "$canonical_head" HEAD
branch_base=$(git merge-base HEAD "$canonical_head")
test "$branch_base" = "$canonical_head"
integration_tmp_dir=$(mktemp -d)
trap 'rm -rf "$integration_tmp_dir"' EXIT
git -C "$canonical_root" status --porcelain=v1 -z --untracked-files=all \
  > "$integration_tmp_dir/canonical-status.z"
git diff --no-renames --name-only -z "$branch_base"..HEAD \
  > "$integration_tmp_dir/branch-paths.z"
uv run --frozen python - \
  "$integration_tmp_dir/canonical-status.z" \
  "$integration_tmp_dir/branch-paths.z" <<'PY'
import os
import sys
from pathlib import Path

status_records = Path(sys.argv[1]).read_bytes().split(b"\0")
dirty: set[bytes] = set()
index = 0
while index < len(status_records):
    record = status_records[index]
    index += 1
    if not record:
        continue
    if len(record) < 4 or record[2:3] != b" ":
        raise SystemExit(f"unrecognized porcelain record: {record!r}")
    status = record[:2]
    dirty.add(record[3:])
    if b"R" in status or b"C" in status:
        if index >= len(status_records) or not status_records[index]:
            raise SystemExit("missing rename/copy source path")
        dirty.add(status_records[index])
        index += 1

branch_paths = {path for path in Path(sys.argv[2]).read_bytes().split(b"\0") if path}
overlap = sorted(dirty & branch_paths)
if overlap:
    for path in overlap:
        print(os.fsdecode(path))
    raise SystemExit("canonical dirty paths overlap branch changes")
PY
```

The ancestor checks prove the requested integration can be a fast-forward before
authorization is requested. The intersection check covers every staged,
unstaged, untracked, renamed, and copied canonical path
against every branch-touched path without newline assumptions. Record the canonical
status verbatim. Do not stash, reset, stage, or commit user-owned paths. The trap
removes only this task's temporary directory.

- [ ] **Step 4: Prepare one combined integration report and stop**

Report A1/A2 commits, Python test counts, 15/15 skill validation, audit commit and
hash, Paper add/delete totals, wrapper commit and symlink target, Obsidian local
filter result, Quartz result or exact encrypted-dependency limitation, preserved
RLinf state, global `daily-papers` conflict, and root `AGENTS.md` reconciliation.
Request one authorization for a local fast-forward merge only. Do not push.

- [ ] **Step 5: After authorization, fast-forward the canonical checkout**

Re-run Step 3 immediately. If the canonical HEAD, status, or overlap result has
changed, stop and report drift. Otherwise:

```bash
integration_head=$(git rev-parse HEAD)
merge_tmp_dir=$(mktemp -d)
trap 'rm -rf "$merge_tmp_dir"' EXIT
git -C /Users/limx/mindflow status --porcelain=v1 -z > "$merge_tmp_dir/status.before"
git -C /Users/limx/mindflow merge --ff-only "$integration_head"
test "$(git -C /Users/limx/mindflow rev-parse HEAD)" = "$integration_head"
git -C /Users/limx/mindflow status --porcelain=v1 -z > "$merge_tmp_dir/status.after"
cmp "$merge_tmp_dir/status.before" "$merge_tmp_dir/status.after"
```

The merge must leave the pre-existing canonical status entries present and
unchanged. A merge conflict or non-fast-forward result is a blocker; do not stash
or rewrite history.

- [ ] **Step 6: Run canonical post-merge profile and UI smoke checks**

```bash
uv run --frozen python -B \
  /Users/limx/mindflow/skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault /Users/limx/mindflow
uv run --frozen python -B \
  /Users/limx/mindflow/skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault /Users/limx/mindflow --repo-root /Users/limx/project/pi --json
uv run --frozen python -B \
  /Users/limx/mindflow/skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault /Users/limx/mindflow \
  --repo-root /Users/limx/mindflow/Projects/pi/code/pi --json
```

Expected: zero vault errors and both code entry paths select `pi`. In Obsidian,
reload the canonical vault; confirm `pi Workspace` and `pi Engineering` are
searchable, ignored code/worklog/.git/RLinf paths are absent, and every Papers Base
view opens without invalid-property/filter errors with the Task 4 counts. Record
the Obsidian version and observed results. Do not push; global skill reconciliation
remains a separate authorized task.
