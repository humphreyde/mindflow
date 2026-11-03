# Plan B1 Legacy Knowledge Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Migrate the approved PaperNotes, DailyPapers, GitHubTrending, ResearchSources, and ResearchNotes knowledge into MindFlow without modifying /Users/limx/notes or overwriting existing MindFlow content.

**Architecture:** A deterministic scanner produces a versioned JSON manifest and human report from a read-only source snapshot. A separate apply command accepts only frozen hashes and safe routing decisions; semantic Paper merges remain explicit manifest operations with section-level provenance. A final validator proves source immutability, target identity uniqueness, link/asset validity, and exact accounting.

**Tech Stack:** Python 3.12, PyYAML, unittest, Markdown/YAML frontmatter, SHA-256 manifests, Git.

**Spec:** docs/superpowers/specs/2026-10-29-para-notes-migration-design.md

## Global Constraints

- /Users/limx/notes is read-only. Record its HEAD, git status --short, and included hashes before and after every apply batch.
- Include only PaperNotes paper/topic candidates, DailyPapers, GitHubTrending, ResearchSources, and ResearchNotes. Exclude author entities, concept entities, generated MOCs, dashboards, navigation notes, and code notes.
- Preserve existing MindFlow filenames, frontmatter, handwritten prose, wikilinks, and assets. An unsafe target collision becomes blocked.
- Paper identity priority is arXiv ID, DOI, then normalized official URL plus title. Low-confidence title-only matches never auto-merge.
- Copy only assets referenced by migrated content. Same-name/different-content assets receive deterministic hash suffixes and rewritten links.
- The user directive “按你推荐的做，不问我” is the approval basis for the single frozen-manifest gate. It does not authorize merge, push, source deletion, or target overwrite.
- Local commits in this approved scope do not require per-commit confirmation.

---

### Task 1: Build the Read-only Inventory and Manifest Planner

**Files:**
- Create: scripts/migrations/__init__.py
- Create: scripts/migrations/legacy_notes.py
- Create: scripts/migrations/test_legacy_notes.py

**Interfaces:**
- Produces SourceSnapshot, MigrationItem, and MigrationManifest dataclasses.
- Produces snapshot_source(source: Path) -> SourceSnapshot.
- Produces build_manifest(source: Path, target: Path) -> MigrationManifest.
- Produces CLI: legacy_notes.py plan --source PATH --target PATH --json PATH --markdown PATH.
- Decisions are import-paper, merge-paper, import-topic, import-daily, import-trending, import-source, import-insight, skip, or blocked.

- [ ] **Step 1: Write failing scope and determinism tests**

    def test_manifest_is_stable_and_source_is_unchanged(self):
        before = snapshot_source(self.source)
        first = build_manifest(self.source, self.target).to_json_bytes()
        second = build_manifest(self.source, self.target).to_json_bytes()
        self.assertEqual(first, second)
        self.assertEqual(before, snapshot_source(self.source))

    def test_auxiliary_routes_are_exact(self):
        routes = {i.source_path: i.destination_path for i in build_manifest(self.source, self.target).items}
        self.assertEqual(routes["DailyPapers/2026-10-28-论文推荐.md"], "Workbench/daily/2026-10-28-论文推荐.md")
        self.assertEqual(routes["GitHubTrending/2026-W44 GitHub周榜.md"], "Workbench/trending/2026-W44 GitHub周榜.md")

- [ ] **Step 2: Run the focused test and confirm red**

    uv run --frozen python -B -m unittest scripts.migrations.test_legacy_notes -v

Expected: import failure because legacy_notes.py does not exist.

- [ ] **Step 3: Implement stable models and source snapshotting**

SourceSnapshot stores git_head, sorted git_status, and sorted relative-path/SHA-256 pairs. MigrationItem stores source_path, source_sha256, source_kind, identity, identity_confidence, decision, destination_path, duplicate_group, referenced_assets, link_rewrites, status, and reason. JSON uses sorted keys, UTF-8, a trailing newline, and no clock timestamp. Reuse the Plan A2 Paper identity parser.

- [ ] **Step 4: Implement exact routing and collision classification**

Scan only approved roots. Exclude PaperNotes root navigation, _authors, _concepts, and generated MOCs. Route GR00T-Series-Survey.md and Pi-Series-Survey.md to Topics. Mark Pi06 Base Model.md blocked pending semantic absorption. Existing destinations without high-confidence identity matches are blocked.

- [ ] **Step 5: Implement atomic JSON and Markdown report writing**

Write sibling temporary files, fsync, then os.replace. Reject output paths inside the source root or Papers. The report lists counts and reasons for every decision.

- [ ] **Step 6: Run tests and commit**

    uv run --frozen python -B -m unittest scripts.migrations.test_legacy_notes -v
    git diff --check
    git add scripts/migrations
    git commit -m "feat: plan legacy knowledge migration"

---

### Task 2: Add Frozen-manifest Approval and Safe Apply

**Files:**
- Modify: scripts/migrations/legacy_notes.py
- Modify: scripts/migrations/test_legacy_notes.py

**Interfaces:**
- CLI: legacy_notes.py approve --manifest PATH --receipt PATH --basis TEXT.
- CLI: legacy_notes.py apply --manifest PATH --receipt PATH --target PATH --decisions CSV.
- Produces verify_receipt(manifest: Path, receipt: Path) -> None.

- [ ] **Step 1: Write stale-input, receipt, and overwrite tests**

    def test_apply_rejects_source_hash_drift(self):
        manifest, receipt = self.freeze_manifest()
        self.source_note.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash drift"):
            apply_manifest(manifest, receipt, self.source, self.target, {"import-daily"})

    def test_apply_never_overwrites_existing_target(self):
        destination = self.target / "Workbench/daily/2026-10-28-论文推荐.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("user content\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "target exists"):
            apply_manifest(*self.freeze_manifest(), self.source, self.target, {"import-daily"})

- [ ] **Step 2: Run tests and confirm red**

    uv run --frozen python -B -m unittest scripts.migrations.test_legacy_notes -v

- [ ] **Step 3: Implement approval receipt and exclusive writes**

Receipt version 1 stores confirmed status, repo-relative manifest path, manifest SHA-256, and approval basis “user directive 2026-11-03: 按你推荐的做，不问我”. Apply accepts only ready items in the explicit decisions set, rechecks source hash, and uses O_CREAT plus O_EXCL. A failed batch removes only paths created by that invocation.

- [ ] **Step 4: Run tests and commit**

    uv run --frozen python -B -m unittest scripts.migrations.test_legacy_notes -v
    git diff --check
    git add scripts/migrations
    git commit -m "feat: freeze and apply migration manifests safely"

---

### Task 3: Migrate Auxiliary Notes and History

**Files:**
- Modify: scripts/migrations/legacy_notes.py
- Modify: scripts/migrations/test_legacy_notes.py
- Create at execution: Workbench/migrations/2026-11-03-notes-migration-manifest.json
- Create at execution: Workbench/migrations/2026-11-03-notes-migration-report.md
- Create at execution: Workbench/migrations/2026-11-03-notes-migration-approval.json
- Create or merge at execution: Workbench/daily, Workbench/trending, ResearchSources/Sources, ResearchSources/Insights

**Interfaces:**
- Produces merge_history(source: list[dict], target: list[dict]) -> list[dict].
- Stable history key is arXiv ID, then DOI, then normalized title.

- [ ] **Step 1: Write history and link-rewrite tests**

    def test_history_merge_preserves_both_sides_and_deduplicates(self):
        merged = merge_history(
            [{"id": "2601.00001", "date": "2026-10-01", "title": "A"}],
            [{"id": "2601.00001", "date": "2026-10-02", "title": "A"},
             {"id": "2601.00002", "date": "2026-10-03", "title": "B"}],
        )
        self.assertEqual([item["id"] for item in merged], ["2601.00001", "2601.00002"])
        self.assertEqual(merged[0]["date"], "2026-10-01")

- [ ] **Step 2: Implement deterministic history merge and auxiliary transforms**

Preserve note bodies except exact path rewrites recorded in the manifest. Add provenance only when target schema supports frontmatter; otherwise provenance remains in the manifest. Serialize history with sorted keys and a trailing newline.

- [ ] **Step 3: Generate and freeze the live manifest**

    uv run --frozen python -B scripts/migrations/legacy_notes.py plan --source /Users/limx/notes --target . --json Workbench/migrations/2026-11-03-notes-migration-manifest.json --markdown Workbench/migrations/2026-11-03-notes-migration-report.md
    uv run --frozen python -B scripts/migrations/legacy_notes.py approve --manifest Workbench/migrations/2026-11-03-notes-migration-manifest.json --receipt Workbench/migrations/2026-11-03-notes-migration-approval.json --basis "user directive 2026-11-03: 按你推荐的做，不问我"

- [ ] **Step 4: Apply safe auxiliary decisions and commit**

    uv run --frozen python -B scripts/migrations/legacy_notes.py apply --manifest Workbench/migrations/2026-11-03-notes-migration-manifest.json --receipt Workbench/migrations/2026-11-03-notes-migration-approval.json --target . --decisions import-daily,import-trending,import-source,import-insight
    git add Workbench/migrations Workbench/daily Workbench/trending ResearchSources
    git commit -m "migrate: import legacy research feeds and sources"

---

### Task 4: Import Old-only Papers, Topics, and Referenced Assets

**Files:**
- Modify: scripts/migrations/legacy_notes.py
- Modify: scripts/migrations/test_legacy_notes.py
- Create at execution: approved Papers, Topics, and referenced asset files

**Interfaces:**
- Produces render_imported_paper(item, source_bytes, rewrites) -> bytes.
- Produces copy_referenced_assets(item, source, target) -> tuple[AssetResult, ...].

- [ ] **Step 1: Write body-preservation and asset-collision tests**

    def test_import_preserves_body_and_adds_only_migration_fields(self):
        rendered = render_imported_paper(self.item, self.paper_bytes, ())
        self.assertIn(b"source_vault: notes\n", rendered)
        self.assertTrue(rendered.endswith(self.original_body))

    def test_asset_collision_uses_hash_suffix(self):
        result = plan_asset_copy("figure.png", b"source", existing=b"different")
        self.assertRegex(result.destination_name, r"^figure-[0-9a-f]{12}\.png$")

- [ ] **Step 2: Implement minimal frontmatter and link normalization**

Preserve existing keys/body bytes; add deterministic migration fields and strong identities already evidenced by the source. Convert author wikilinks to plain names. Convert unresolved concept links to readable text and report them.

- [ ] **Step 3: Implement referenced-asset discovery**

Resolve embeds only beneath the source vault. Reject traversal and missing sources. Copy to Papers/assets/ShortTitle or a Topic-specific asset directory. Reuse identical content; suffix different content with 12 SHA-256 hex characters.

- [ ] **Step 4: Apply, validate, and commit**

    uv run --frozen python -B scripts/migrations/legacy_notes.py apply --manifest Workbench/migrations/2026-11-03-notes-migration-manifest.json --receipt Workbench/migrations/2026-11-03-notes-migration-approval.json --target . --decisions import-paper,import-topic
    uv run --frozen python -B skills/1-literature/paper-digest/scripts/validate_papers.py --vault . --mode audit --json /tmp/mindflow-post-import.json --markdown /tmp/mindflow-post-import.md
    git add Papers Topics Workbench/migrations
    git commit -m "migrate: import legacy papers and surveys"

---

### Task 5: Merge High-confidence Overlapping Papers

**Files:**
- Modify: exact existing Papers paths named by merge-paper manifest items
- Modify: Workbench/migrations/2026-11-03-notes-migration-manifest.json
- Modify: Workbench/migrations/2026-11-03-notes-migration-report.md

**Interfaces:**
- Each merged item records merged_sections, omitted_sections, and destination_post_sha256.
- Existing MindFlow file remains canonical.

- [ ] **Step 1: Build a section ledger for every source/destination pair**

List source-only claims under method, experiments, ablations, failure cases, critique, and related work. Every imported claim retains a source heading or official citation.

- [ ] **Step 2: Apply one semantic merge at a time**

Preserve target frontmatter/rating and all handwritten text. Place source-only material in matching sections. If no safe section exists, add one Legacy Notes Addendum with provenance. Keep conflicting interpretations side by side.

- [ ] **Step 3: Record hashes, omissions, and validate every pair**

    uv run --frozen python -B skills/1-literature/paper-digest/scripts/validate_papers.py --vault . --mode audit --json /tmp/mindflow-merge-audit.json --markdown /tmp/mindflow-merge-audit.md

- [ ] **Step 4: Commit reviewed merges**

    git add Papers Workbench/migrations
    git commit -m "migrate: merge overlapping legacy paper insights"

---

### Task 6: Prove Migration Integrity

**Files:**
- Modify: scripts/migrations/legacy_notes.py
- Modify: scripts/migrations/test_legacy_notes.py
- Modify: Workbench/migrations/2026-11-03-notes-migration-report.md

**Interfaces:**
- CLI: legacy_notes.py verify --manifest PATH --source PATH --target PATH.
- Exit zero only when accounting, source snapshot, hashes, identities, assets, and forbidden-path scans pass.

- [ ] **Step 1: Write end-state validation tests**

Cover source HEAD/status/hash drift, duplicate Paper identity, missing copied asset, old absolute paths, PaperNotes links, unknown status, and manifest count mismatch.

- [ ] **Step 2: Implement the verifier**

Recompute source snapshot, target hashes, identity groups, asset existence, and forbidden paths. A blocked item is valid only with a reason and no target write. Every included source path appears exactly once.

- [ ] **Step 3: Run full verification and commit**

    uv run --frozen python -B -m unittest scripts.migrations.test_legacy_notes -v
    uv run --frozen python -B scripts/migrations/legacy_notes.py verify --manifest Workbench/migrations/2026-11-03-notes-migration-manifest.json --source /Users/limx/notes --target .
    git diff --check
    git add scripts/migrations Workbench/migrations/2026-11-03-notes-migration-report.md
    git commit -m "test: verify legacy knowledge migration integrity"

