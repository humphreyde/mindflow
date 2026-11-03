# Plan B2 Skill Cutover and Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Make MindFlow the canonical home for research-writing skills, prove they write only to the resolved vault, and replace legacy global skill directories with recoverable links on this and future computers.

**Architecture:** Repository skills derive the vault root from their resolved canonical file path and expose deterministic helpers for all writes. GitHub Trending and Research Insights are adapted into the canonical tree rather than copied unchanged. A tested allowlist bootstrap archives exact legacy directories, creates global symlinks atomically, records rollback metadata, and fails closed on drift.

**Tech Stack:** Python 3.12 standard library, unittest, Markdown skill contracts, JSON manifests, filesystem symlinks, Git.

**Spec:** docs/superpowers/specs/2026-10-29-para-notes-migration-design.md

## Global Constraints

- Canonical skills live only under MindFlow skills. Global Codex discovery contains symlinks, not editable copies.
- Resolve MindFlow from Path(__file__).resolve(), never cwd. A test-only vault argument may override discovery.
- Outputs go only to Papers, Workbench/daily, Workbench/trending, ResearchSources, and Workbench/logs in the resolved vault.
- git_commit and git_push default to false. No skill commits or pushes implicitly.
- Existing notes/assets are never overwritten.
- Archive, link, and rollback operations use a fixed allowlist and exact paths. Never recursively clean the global skills directory.
- Retire paper-reader, the four legacy daily skills, legacy github-trending, legacy research-insights, author-graph, and generate-mocs; preserve them under skills-legacy/date with hashes.
- B2 starts only after B1 validation succeeds. Merge and push remain outside this plan.
- On this machine, live global links must target the primary checkout /Users/limx/mindflow, never this worktree. Repository implementation and temporary-home tests run before merge; Task 6 waits for separately authorized local merge.

---

### Task 1: Add Canonical Vault-root Resolution

**Files:**
- Create: scripts/mindflow_paths.py
- Create: scripts/test_mindflow_paths.py
- Modify: skills/1-literature/daily-papers/fetch_and_score.py
- Modify: skills/1-literature/daily-papers/SKILL.md
- Modify: skills/1-literature/paper-digest/SKILL.md

**Interfaces:**
- Produces resolve_vault_root(start: Path) -> Path.
- Produces resolve_output(vault: Path, relative: str) -> Path.
- Vault sentinel requires AGENTS.md, skills, Papers, and Workbench.

- [ ] **Step 1: Write resolution and escape tests**

    def test_resolves_from_real_file_behind_symlink(self):
        link = self.home / ".codex/skills/daily-papers"
        link.parent.mkdir(parents=True)
        link.symlink_to(self.vault / "skills/1-literature/daily-papers")
        self.assertEqual(resolve_vault_root(link / "fetch_and_score.py"), self.vault.resolve())

    def test_output_rejects_absolute_and_parent_paths(self):
        for value in ("/tmp/out", "../notes", "Workbench/../../notes"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_output(self.vault, value)

- [ ] **Step 2: Run tests and confirm red**

    uv run --frozen python -B -m unittest scripts.test_mindflow_paths -v

- [ ] **Step 3: Implement fail-closed resolution**

    SENTINELS = ("AGENTS.md", "skills", "Papers", "Workbench")

    def resolve_vault_root(start: Path) -> Path:
        current = start.resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if all((candidate / name).exists() for name in SENTINELS):
                return candidate
        raise ValueError(f"cannot resolve MindFlow vault root from {start}")

resolve_output rejects absolute paths and parent traversal, then verifies canonical containment. It does not create directories.

- [ ] **Step 4: Route daily and digest instructions through resolved vault**

Add a test-only vault argument to the fetch script. Production SKILL commands invoke scripts through their canonical skill directory and use the script-derived vault. Remove cwd-relative skills paths.

- [ ] **Step 5: Test and commit**

    uv run --frozen python -B -m unittest scripts.test_mindflow_paths -v
    uv run --frozen python -B -m unittest discover -s skills/1-literature/daily-papers -p "test_*.py" -v
    git diff --check
    git add scripts/mindflow_paths.py scripts/test_mindflow_paths.py skills/1-literature/daily-papers skills/1-literature/paper-digest/SKILL.md
    git commit -m "fix: resolve research skill outputs from MindFlow"

---

### Task 2: Canonicalize GitHub Trending

**Files:**
- Create: skills/1-literature/github-trending/SKILL.md
- Create: skills/1-literature/github-trending/fetch_trending.py
- Create: skills/1-literature/github-trending/write_trending_note.py
- Create: skills/1-literature/github-trending/test_github_trending.py

**Interfaces:**
- CLI: fetch_trending.py --since weekly --output PATH.
- CLI: write_trending_note.py --input PATH --vault PATH --date YYYY-MM-DD.
- Output: Workbench/trending/YYYY-Www GitHub周榜.md.

- [ ] **Step 1: Copy reusable deterministic logic and write failing tests**

    def test_writer_uses_mindflow_trending_directory(self):
        output = write_note(self.vault, date(2026, 11, 3), self.repositories)
        self.assertEqual(output, self.vault / "Workbench/trending/2026-W45 GitHub周榜.md")

    def test_existing_week_is_not_overwritten(self):
        output = self.vault / "Workbench/trending/2026-W45 GitHub周榜.md"
        output.parent.mkdir(parents=True)
        output.write_text("handwritten\n", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "already exists"):
            write_note(self.vault, date(2026, 11, 3), self.repositories)

- [ ] **Step 2: Adapt paths and contract**

The SKILL invokes scripts through its canonical directory and reports network failures. The writer accepts parsed JSON, renders Obsidian Markdown, and writes with exclusive create. It never invokes Git.

- [ ] **Step 3: Test and commit**

    uv run --frozen python -B -m unittest discover -s skills/1-literature/github-trending -p "test_*.py" -v
    git diff --check
    git add skills/1-literature/github-trending
    git commit -m "feat: add MindFlow GitHub trending skill"

---

### Task 3: Canonicalize Research Insights

**Files:**
- Create: skills/1-literature/research-insights/SKILL.md
- Create: skills/1-literature/research-insights/capture_source.py
- Create: skills/1-literature/research-insights/assets/source-note-template.md
- Create: skills/1-literature/research-insights/assets/insight-note-template.md
- Create: skills/1-literature/research-insights/test_capture_source.py

**Interfaces:**
- CLI: capture_source.py --vault PATH --url URL --title TITLE --content PATH.
- Outputs: ResearchSources/Sources/safe-title.md and optional ResearchSources/Insights/safe-title.md.

- [ ] **Step 1: Write provenance and collision tests**

    def test_source_note_records_url_and_access_date(self):
        note = build_source_note(self.record)
        self.assertIn("source_url: https://example.org/post", note)
        self.assertIn("accessed: 2026-11-03", note)

    def test_capture_does_not_overwrite_existing_source(self):
        destination = self.vault / "ResearchSources/Sources/Post.md"
        destination.parent.mkdir(parents=True)
        destination.write_text("existing\n", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            save_source(self.vault, "Post", self.note)

- [ ] **Step 2: Adapt the old skill without author/MOC side effects**

Keep URL/title/content capture and templates. Remove old notes-vault defaults, author sync, MOC generation, commit/push, and implicit dependency installation. Use resolved MindFlow root and exact output directories.

- [ ] **Step 3: Test and commit**

    uv run --frozen python -B -m unittest discover -s skills/1-literature/research-insights -p "test_*.py" -v
    git diff --check
    git add skills/1-literature/research-insights
    git commit -m "feat: add MindFlow research insights skill"

---

### Task 4: Add Daily Pipeline Contract Integration Tests

**Files:**
- Create: skills/1-literature/daily-papers/test_daily_pipeline_contract.py
- Create: skills/1-literature/daily-papers/fixtures/candidates.json
- Modify: skills/1-literature/daily-papers/SKILL.md
- Modify: skills/1-literature/daily-papers/fetch_and_score.py

**Interfaces:**
- Fixture outputs candidate, history, Paper note, daily summary, and two log entries.
- New labels are 3 - Foundation, 2 - Frontier, and 1 - Peripheral.

- [ ] **Step 1: Write the six-artifact contract test**

    def test_fixture_pipeline_accounts_for_six_artifact_classes(self):
        result = run_fixture_pipeline(self.vault, self.fixture)
        self.assertTrue((self.vault / "Workbench/daily/.candidates.json").is_file())
        self.assertTrue((self.vault / "Workbench/daily/.history.json").is_file())
        self.assertEqual(len(list((self.vault / "Papers").glob("*.md"))), 1)
        self.assertTrue((self.vault / "Workbench/daily/2026-11-03.md").is_file())
        log = (self.vault / "Workbench/logs/2026-11-03.md").read_text(encoding="utf-8")
        self.assertIn("paper-digest", log)
        self.assertIn("daily-papers", log)
        self.assertEqual(result.fetched, result.read + result.skipped)

- [ ] **Step 2: Add an offline fixture runner**

The runner tests orchestration contracts only. It injects candidate JSON and a fixed digest result, then uses production path/history/render helpers. It does not claim to test LLM judgment or live upstream availability.

- [ ] **Step 3: Replace new-output Archived with Peripheral**

Update only canonical daily templates/tests. Do not globally rewrite existing Papers or old daily notes.

- [ ] **Step 4: Run tests and commit**

    uv run --frozen python -B -m unittest discover -s skills/1-literature -p "test_*.py" -v
    git diff --check
    git add skills/1-literature/daily-papers
    git commit -m "test: cover MindFlow daily paper pipeline"

---

### Task 5: Implement the Allowlist Bootstrap and Rollback

**Files:**
- Create: scripts/bootstrap_codex_skills.py
- Create: scripts/test_bootstrap_codex_skills.py
- Modify: README.md

**Interfaces:**
- CLI: bootstrap_codex_skills.py plan --codex-home PATH.
- CLI: bootstrap_codex_skills.py apply --codex-home PATH --archive-date YYYY-MM-DD.
- CLI: bootstrap_codex_skills.py rollback --codex-home PATH --manifest PATH.
- Managed links: paper-digest, daily-papers, github-trending, research-insights, mindflow-context.
- Retire-only: paper-reader, daily-papers-fetch, daily-papers-review, daily-papers-notes, author-graph, generate-mocs.

- [ ] **Step 1: Write the state matrix**

    def test_correct_link_is_noop(self):
        self.link("daily-papers", self.vault / "skills/1-literature/daily-papers")
        self.assertEqual(plan_bootstrap(self.vault, self.codex_home)["daily-papers"].action, "noop")

    def test_conflicting_directory_is_archived_before_link(self):
        (self.skills / "daily-papers").mkdir(parents=True)
        self.assertEqual(plan_bootstrap(self.vault, self.codex_home)["daily-papers"].action, "archive-and-link")

    def test_rollback_stops_if_link_drifted(self):
        manifest = self.apply_fixture()
        (self.skills / "daily-papers").unlink()
        (self.skills / "daily-papers").symlink_to(self.other)
        with self.assertRaisesRegex(ValueError, "drift"):
            rollback(manifest, self.codex_home)

Also cover missing canonical source, ordinary file conflict, wrong symlink, archive collision, partial apply rollback, idempotent second apply, and path escape.

- [ ] **Step 2: Implement fixed allowlists and tree hashes**

    MANAGED_LINKS = {
        "paper-digest": "skills/1-literature/paper-digest",
        "daily-papers": "skills/1-literature/daily-papers",
        "github-trending": "skills/1-literature/github-trending",
        "research-insights": "skills/1-literature/research-insights",
        "mindflow-context": "skills/6-orchestration/mindflow-context",
    }
    RETIRE_ONLY = (
        "paper-reader", "daily-papers-fetch", "daily-papers-review",
        "daily-papers-notes", "author-graph", "generate-mocs",
    )

Archive exact directories with os.replace into skills-legacy/date. Record pre-state, archive path, tree hash, new target, and operation order. Create links through a temporary sibling symlink plus os.replace. Reverse only operations recorded in the current transaction on failure.

- [ ] **Step 3: Implement exact rollback**

Rollback verifies manifest containment, current link target, and archive tree hash before changing anything. Restore in reverse order. Never overwrite a current path and never use recursive deletion.

- [ ] **Step 4: Document new-computer setup**

README sequence is clone MindFlow, install locked dependencies, run plan, inspect actions, run apply, then validate. State that project repos, Zotero, credentials, and private machine paths are not synchronized.

- [ ] **Step 5: Test and commit**

    uv run --frozen python -B -m unittest scripts.test_bootstrap_codex_skills -v
    git diff --check
    git add scripts/bootstrap_codex_skills.py scripts/test_bootstrap_codex_skills.py README.md
    git commit -m "feat: bootstrap canonical Codex skills"

---

### Task 6: Validate and Perform the Local Skill Cutover

**Files:**
- Create outside repository: ~/.codex/skills-legacy/2026-11-03/manifest.json
- Replace outside repository: allowlisted ~/.codex/skills entries

**Interfaces:**
- Validate canonical source and corresponding discovery symlink independently.
- Precondition: the implementation commits are present in canonical /Users/limx/mindflow after separately authorized local merge.

- [ ] **Step 1: Validate canonical skills from a non-vault cwd**

Verify the current branch commit is an ancestor of `/Users/limx/mindflow` HEAD. If not, stop at the merge boundary without touching global skills. Then run the repository skill validator on paper-digest, daily-papers, github-trending, research-insights, and mindflow-context from the canonical checkout, and run all skill tests from /tmp.

- [ ] **Step 2: Generate and inspect the live plan**

    uv run --frozen python -B scripts/bootstrap_codex_skills.py plan --codex-home /Users/limx/.codex

Expected: legacy directories are archive-and-link or archive-only; the correct mindflow-context link is noop; no unrecognized path appears.

- [ ] **Step 3: Apply the exact cutover**

    uv run --frozen python -B scripts/bootstrap_codex_skills.py apply --codex-home /Users/limx/.codex --archive-date 2026-11-03

- [ ] **Step 4: Verify links, hashes, and discovery behavior**

For each managed link compare readlink, canonical realpath, skill inventory, and validator result with its source. Confirm retire-only names are absent from active discovery and present in the archive manifest. Re-run daily and canonical skill tests.

- [ ] **Step 5: Freeze evidence without merge or push**

    git status --short
    git diff --check
    uv run --frozen python -B -m unittest discover -s scripts -p "test_*.py" -v
    uv run --frozen python -B -m unittest discover -s skills/1-literature -p "test_*.py" -v

No repository commit is expected for the external link operation; the archive manifest is the rollback record.

