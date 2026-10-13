# MindFlow Codex-First Migration Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task with verification checkpoints.

**Goal:** Make Codex the default MindFlow agent runtime, expose all 14 repository skills through Codex discovery, remove Claude-specific execution assumptions, and repair the active workflow drift identified in the approved design.

**Architecture:** Keep `skills/` as the single canonical skill tree and expose it through `.agents/skills`. Keep the existing Owner context in `AGENTS.md`, prepend a concise Codex repository contract, and retain `CLAUDE.md` as a compatibility symlink. Standardize every skill to portable Agent Skills frontmatter and capability-oriented instructions. Limit adjacent repairs to active workflow blockers: removed skill references, missing experiment output path, memory lifecycle mismatch, and the Quartz institute field mismatch.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, Git symlinks, Python 3/uv, Node.js/npm, Quartz/TypeScript

**Design:** `docs/superpowers/specs/2026-10-13-codex-first-migration-design.md`

---

## Task 1: Add Codex discovery and repository instructions

**Files:**

- Create: `.agents/skills` symlink to `../skills`
- Modify: `AGENTS.md`
- Preserve: `CLAUDE.md` symlink to `AGENTS.md`

- [ ] **Step 1: Record the failing discovery baseline**

Run:

```bash
test -L .agents/skills
```

Expected: non-zero because the Codex discovery link does not exist yet.

- [ ] **Step 2: Create the Codex skill discovery link**

Create `.agents/` and add the relative symlink `.agents/skills -> ../skills`. Do not move or duplicate the canonical `skills/` tree.

- [ ] **Step 3: Add a Codex execution contract to `AGENTS.md`**

Prepend concise repository rules covering:

- repository purpose and canonical directories;
- `.agents/skills` discovery and `$skill-name` invocation;
- read protocol/template before writes;
- preserve existing notes and handwritten edits;
- Obsidian syntax requirements;
- precise edits, narrow Git staging, and proportional validation;
- runtime dependency boundaries for Python/uv, Node/npm, and Quartz.

Keep the existing Owner profile, research principles, anti-patterns, and directory explanation intact.

- [ ] **Step 4: Verify discovery and compatibility links**

Run:

```bash
test "$(readlink .agents/skills)" = "../skills"
test "$(readlink CLAUDE.md)" = "AGENTS.md"
find .agents/skills -name SKILL.md | wc -l
git diff --check
```

Expected: both link checks pass; skill count is `14`; no whitespace errors.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md .agents/skills
git commit -m "feat: expose MindFlow skills to Codex"
```

---

## Task 2: Make public documentation and protocol Codex-first

**Files:**

- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/SPEC.md`
- Modify: `references/skill-protocol.md`

- [ ] **Step 1: Capture current Claude-default and inventory drift**

Run:

```bash
rg -n 'Quick Start with Claude Code|\.claude/skills|Claude Code 官方|完整 skill 清单.*13|AI Skills.*13' README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
```

Expected: matches in all four files.

- [ ] **Step 2: Rewrite README entry points**

- Describe Codex as the default CLI/desktop agent.
- Change the skill inventory to 14 and include `daily-papers`.
- Add `.agents/skills` and `Experiments/` to the directory model.
- Replace the Claude quick-start heading/examples with Codex `$skill-name` examples.
- Keep a short Claude compatibility note rather than deleting Claude support.

- [ ] **Step 3: Rewrite installation guidance**

Document:

- Codex and Git prerequisites; Obsidian as the vault UI;
- Python 3 + uv, Node/npm version boundaries, and optional `gh`;
- clone, discovery-link verification, and starting Codex from the repository root;
- skill verification and example invocation;
- Obsidian and Quartz setup;
- a separate optional Claude compatibility section linking skills into `.claude/skills`.

Do not run installers or mutate user-global configuration.

- [ ] **Step 4: Update active architecture documentation**

In `docs/SPEC.md`, reflect the actual 14-skill inventory, Codex discovery link, restored/generated `Experiments/` output area, and Codex-first `AGENTS.md` role. Preserve the historical changelog entries as history.

- [ ] **Step 5: Rewrite `skill-protocol.md` around Agent Skills**

- Make `name` and `description` the required frontmatter fields.
- Remove Claude tool allowlist and Claude-only field requirements.
- Explain inputs in the body, progressive disclosure, `$skill-name` invocation, capability-oriented steps, orchestration, Guard, and Verify.
- Update the current skill tree to the actual 14 skills.
- Link the official Codex skills and Agent Skills specifications.

- [ ] **Step 6: Verify docs**

Run:

```bash
rg -n 'Codex|\.agents/skills|14 个|daily-papers' README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
rg -n 'Claude Code 官方|Claude Code tools|Quick Start with Claude Code' README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
git diff --check
```

Expected: Codex/default-path matches are present; the second scan is empty. A clearly labeled Claude compatibility section may still contain `Claude Code` and `.claude/skills`.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
git commit -m "docs: make MindFlow Codex-first"
```

---

## Task 3: Standardize all 14 skill frontmatters

**Files:**

- Modify: every `skills/*/*/SKILL.md`

- [ ] **Step 1: Run the Codex validator against the current frontmatters**

Run:

```bash
validator="$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py"
test -f "$validator" || validator="$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py"
for dir in skills/*/*; do
  test -f "$dir/SKILL.md" || continue
  uv run --with pyyaml python "$validator" "$dir"
done
```

Expected: failures for unsupported `argument-hint` and/or `user-invocable` fields.

- [ ] **Step 2: Normalize each frontmatter**

For all 14 skills:

- retain `name` and a concise trigger-rich `description`;
- remove `argument-hint`, `user-invocable`, and `allowed-tools`;
- ensure YAML remains valid and `name` exactly matches the containing directory;
- keep input syntax and internal-only semantics in the body where needed.

- [ ] **Step 3: Run validator and directory-name checks**

Run the loop from Step 1 again, then:

```bash
for file in skills/*/*/SKILL.md; do
  dir="$(basename "$(dirname "$file")")"
  name="$(sed -n 's/^name: //p' "$file" | head -1)"
  test "$dir" = "$name" || { echo "$file: $name != $dir"; exit 1; }
done
```

Expected: all 14 validators and all name checks pass.

- [ ] **Step 4: Commit**

```bash
git add skills/*/*/SKILL.md
git commit -m "refactor: standardize skill metadata for Codex"
```

---

## Task 4: Migrate literature skills to capability-oriented execution

**Files:**

- Modify: `skills/1-literature/daily-papers/SKILL.md`
- Modify: `skills/1-literature/literature-survey/SKILL.md`
- Modify: `skills/1-literature/paper-digest/SKILL.md`

- [ ] **Step 1: Capture current proprietary-tool and Guard failures**

Run:

```bash
rg -n '\b(Read|Write|Edit|Glob|Grep|Task|WebSearch|WebFetch)\b|\.claude/' skills/1-literature --glob 'SKILL.md'
for file in skills/1-literature/*/SKILL.md; do rg -q '^## Guard$' "$file" || echo "$file"; done
```

Expected: tool-name matches and all three files reported as missing Guard.

- [ ] **Step 2: Migrate `daily-papers`**

- Keep its deterministic Python fetch/score pipeline.
- Describe file reads/writes/searches as operations, not agent tool calls.
- Add Guard rules for date range, network failure, deduplication, user-owned notes, and transient files.
- Add or tighten Verify items for candidates, generated notes, summaries, and history.

- [ ] **Step 3: Migrate `literature-survey`**

- Replace the Claude `Task` subagent assumption with portable composition.
- Support two modes: topic survey with external discovery, and comparison of an explicitly supplied local paper set.
- Permit parallel digestion only when runtime capability exists and writes are independent; otherwise process sequentially.
- Add Guard rules for source traceability, bounded search, duplicate avoidance, and no fabricated citations.

- [ ] **Step 4: Migrate `paper-digest`**

- Replace prose references to proprietary file/web tools with operation/capability language.
- Keep explicit shell commands for deterministic extractors and APIs.
- Make dependency and fallback behavior explicit.
- Add Guard rules for existing-note preservation, source attribution, network degradation, temporary files, and user edits.

- [ ] **Step 5: Validate literature skills and helper syntax**

Run:

```bash
for file in skills/1-literature/*/SKILL.md; do rg -q '^## Guard$' "$file"; done
rg -n '\b(Read|Write|Edit|Glob|Grep|Task|WebSearch|WebFetch)\b|\.claude/' skills/1-literature --glob 'SKILL.md'
python3 -m py_compile skills/1-literature/daily-papers/fetch_and_score.py skills/1-literature/paper-digest/scripts/*.py
node --check skills/1-literature/paper-digest/scripts/defuddle_parse.mjs
git diff --check
```

Expected: Guard checks pass; proprietary-tool scan is empty except literal terms inside an explicitly documented compatibility example, if any; syntax checks pass.

- [ ] **Step 6: Commit**

```bash
git add skills/1-literature
git commit -m "refactor: make literature skills Codex-native"
```

---

## Task 5: Migrate ideation and experiment workflows

**Files:**

- Modify: `skills/2-ideation/idea-generate/SKILL.md`
- Modify: `skills/2-ideation/idea-evaluate/SKILL.md`
- Modify: `skills/3-experiment/experiment-design/SKILL.md`
- Modify: `skills/3-experiment/experiment-track/SKILL.md`
- Modify: `skills/3-experiment/result-analysis/SKILL.md`
- Create: `Experiments/.gitkeep`

- [ ] **Step 1: Capture current tool coupling and missing output directory**

Run:

```bash
rg -n '\b(Read|Write|Edit|Glob|Grep|WebSearch|WebFetch)\b' skills/2-ideation skills/3-experiment --glob 'SKILL.md'
test -d Experiments
```

Expected: tool-name matches; the directory check fails.

- [ ] **Step 2: Migrate ideation skills**

- Convert file/search/web steps to capability-oriented language.
- Keep evidence traceability, failed-direction checks, and no-overwrite rules.
- Make external evidence optional with explicit degradation when network access is unavailable.

- [ ] **Step 3: Restore the experiment output entry point**

Add tracked `Experiments/.gitkeep`. In all three experiment skills, require confirming/creating `Experiments/` before output and use `Templates/Experiment.md` as the schema source.

- [ ] **Step 4: Migrate experiment skills**

- Convert tool-specific instructions to read/create/append/precise-update operations.
- Preserve append-only Run Entries.
- Preserve hypothesis verdict, Idea status, memory evidence, and logging semantics.
- Ensure missing files/directories produce an explicit stop or creation path rather than an assumed tool call.

- [ ] **Step 5: Validate**

Run:

```bash
test -f Experiments/.gitkeep
rg -n '\b(Read|Write|Edit|Glob|Grep|WebSearch|WebFetch)\b' skills/2-ideation skills/3-experiment --glob 'SKILL.md'
for file in skills/2-ideation/*/SKILL.md skills/3-experiment/*/SKILL.md; do
  rg -q '^## Guard$' "$file" && rg -q '^## Verify$' "$file"
done
rg -n 'Templates/Experiment\.md|Experiments/' skills/3-experiment docs/SPEC.md README.md
git diff --check
```

Expected: proprietary-tool scan empty; section and path checks pass.

- [ ] **Step 6: Commit**

```bash
git add Experiments/.gitkeep skills/2-ideation skills/3-experiment
git commit -m "refactor: repair Codex ideation and experiment workflows"
```

---

## Task 6: Migrate writing and evolution workflows

**Files:**

- Modify: `skills/4-writing/draft-section/SKILL.md`
- Modify: `skills/4-writing/writing-refine/SKILL.md`
- Modify: `skills/5-evolution/agenda-evolve/SKILL.md`
- Modify: `skills/5-evolution/memory-distill/SKILL.md`
- Modify: `skills/5-evolution/memory-retrieve/SKILL.md`
- Modify: `references/memory-protocol.md`

- [ ] **Step 1: Capture current tool coupling and lifecycle conflict**

Run:

```bash
rg -n '\b(Read|Write|Edit|Glob|Grep)\b|\.claude/' skills/4-writing skills/5-evolution --glob 'SKILL.md'
rg -n 'append-only|occurrences|status|confidence' references/memory-protocol.md skills/5-evolution/memory-distill/SKILL.md
```

Expected: proprietary-tool matches and a protocol/implementation mismatch around editing memory entries.

- [ ] **Step 2: Migrate writing skills**

- Use capability-oriented file/search/update language.
- Replace the hardcoded `.claude/skills/...` self-read path with canonical skill resolution.
- Preserve Owner confirmation before applying prose refinements.
- Preserve tight section boundaries and wikilink verification.

- [ ] **Step 3: Define the memory mutation boundary**

Update `references/memory-protocol.md` so:

- Workbench logs and experiment Run Entries remain append-only.
- Memory claims/history are never deleted or silently rewritten.
- A memory entry may receive appended occurrences/evidence and narrow lifecycle updates to status/confidence.
- Every promotion or material lifecycle change is recorded in the evolution changelog.

- [ ] **Step 4: Migrate evolution skills**

- Convert tool-specific operations to capabilities.
- Align `memory-distill` exactly with the clarified lifecycle.
- Keep `memory-retrieve` read-only and state its input format in the body.
- Preserve agenda Owner overrides, narrow updates, and changelog requirements.

- [ ] **Step 5: Validate**

Run:

```bash
rg -n '\b(Read|Write|Edit|Glob|Grep)\b|\.claude/' skills/4-writing skills/5-evolution --glob 'SKILL.md'
rg -n 'append-only|evidence|occurrences|status|confidence|changelog' references/memory-protocol.md skills/5-evolution/memory-distill/SKILL.md
for file in skills/4-writing/*/SKILL.md skills/5-evolution/*/SKILL.md; do rg -q '^## Guard$' "$file"; done
git diff --check
```

Expected: proprietary-tool scan empty; protocol and skill both describe the same permitted lifecycle updates; Guard checks pass.

- [ ] **Step 6: Commit**

```bash
git add skills/4-writing skills/5-evolution references/memory-protocol.md
git commit -m "refactor: make writing and memory workflows portable"
```

---

## Task 7: Repair orchestration and active references

**Files:**

- Modify: `skills/6-orchestration/autoresearch/SKILL.md`
- Modify as needed: `skills/1-literature/literature-survey/SKILL.md`
- Modify as needed: `README.md`
- Modify as needed: `docs/SPEC.md`
- Modify as needed: `references/skill-protocol.md`

- [ ] **Step 1: Capture stale orchestration references**

Run:

```bash
rg -n 'cross-paper-analysis|\b(Read|Write|Edit|Glob|Grep|WebSearch|WebFetch)\b' skills/6-orchestration skills/1-literature/literature-survey/SKILL.md README.md docs/SPEC.md references/skill-protocol.md
```

Expected: `autoresearch` references the removed `cross-paper-analysis` and proprietary tools.

- [ ] **Step 2: Migrate `autoresearch`**

- Resolve satellite skills by canonical repository path and execute their current Steps/Guard/Verify.
- Replace removed `cross-paper-analysis` actions with `literature-survey` local-comparison mode.
- Keep one-action-per-round, state reread, logging, stop conditions, and human decision boundaries.
- Remove assumptions about Claude web/file tools.

- [ ] **Step 3: Reconcile all active inventories and examples**

Ensure current README, SPEC, protocol, survey skill, and orchestration skill agree on:

- 14 skills;
- `daily-papers` present;
- `cross-paper-analysis` absent;
- `literature-survey` owns local multi-paper comparison;
- `Experiments/` is a valid output directory.

Do not rewrite archived documents under `docs/superpowers/specs/` or old plans merely to remove historical names.

- [ ] **Step 4: Validate active reference closure**

Run:

```bash
rg -n 'cross-paper-analysis' README.md docs/SPEC.md docs/INSTALL.md references skills
rg -n '\b(Read|Write|Edit|Glob|Grep|Task|WebSearch|WebFetch)\b|\.claude/' skills --glob 'SKILL.md'
find skills -name SKILL.md | wc -l
git diff --check
```

Expected: first two scans empty; count is `14`.

- [ ] **Step 5: Commit**

```bash
git add skills/6-orchestration/autoresearch/SKILL.md skills/1-literature/literature-survey/SKILL.md README.md docs/SPEC.md references/skill-protocol.md
git commit -m "fix: close MindFlow orchestration gaps"
```

---

## Task 8: Fix Quartz paper institute compatibility

**Files:**

- Modify: `.website/quartz/components/PaperMeta.tsx`

- [ ] **Step 1: Confirm the schema mismatch**

Run:

```bash
rg -n '^institutes:' Papers skills/1-literature/paper-digest/references/paper-note-template.md | head
rg -n 'fm\?\.institute' .website/quartz/components/PaperMeta.tsx
```

Expected: notes/template use `institutes`; component reads only singular `institute`.

- [ ] **Step 2: Add plural-first compatibility**

Read `fm.institutes` first and fall back to legacy `fm.institute`. Normalize the chosen value to an array before rendering. Rename local variables/classes only if needed; avoid unrelated visual changes.

- [ ] **Step 3: Run focused website checks**

From `.website/`:

```bash
npm ci --ignore-scripts
npx tsc --noEmit
npx prettier quartz/components/PaperMeta.tsx --check
npx quartz build
```

Expected: all commands pass. If `npm ci --ignore-scripts` prevents a required native dependency from working, record the exact failure and rerun the minimal documented install command without changing global state.

- [ ] **Step 4: Commit**

```bash
git add .website/quartz/components/PaperMeta.tsx
git commit -m "fix: render plural paper institutes in Quartz"
```

---

## Task 9: Run end-to-end migration validation

**Files:**

- Modify only if validation exposes a scoped defect in files already covered above.

- [ ] **Step 1: Validate every skill with the bundled Codex validator**

```bash
validator="$CODEX_HOME/skills/.system/skill-creator/scripts/quick_validate.py"
test -f "$validator" || validator="$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py"
count=0
for dir in skills/*/*; do
  test -f "$dir/SKILL.md" || continue
  uv run --with pyyaml python "$validator" "$dir" || exit 1
  count=$((count + 1))
done
test "$count" -eq 14
```

- [ ] **Step 2: Validate required sections and discovery**

```bash
for file in skills/*/*/SKILL.md; do
  rg -q '^## Purpose$' "$file"
  rg -q '^## Steps$' "$file"
  rg -q '^## Guard$' "$file"
done
test "$(readlink .agents/skills)" = "../skills"
test "$(find .agents/skills -name SKILL.md | wc -l | tr -d ' ')" -eq 14
```

- [ ] **Step 3: Validate portability and active reference closure**

```bash
rg -n '\b(Read|Write|Edit|Glob|Grep|Task|WebSearch|WebFetch)\b|\.claude/' skills --glob 'SKILL.md'
rg -n 'cross-paper-analysis' README.md docs/SPEC.md docs/INSTALL.md references skills
```

Expected: both scans empty. Shell command names such as `curl`, `uv`, `python`, and `node` are allowed.

- [ ] **Step 4: Validate helper code**

```bash
python3 -m py_compile skills/1-literature/daily-papers/fetch_and_score.py skills/1-literature/paper-digest/scripts/*.py
node --check skills/1-literature/paper-digest/scripts/defuddle_parse.mjs
```

- [ ] **Step 5: Re-run website checks**

```bash
(cd .website && npx tsc --noEmit && npx prettier quartz/components/PaperMeta.tsx --check && npx quartz build)
```

- [ ] **Step 6: Audit preservation and Git state**

```bash
git diff --check
git status --short
git diff --name-only d281213f..HEAD -- Papers DomainMaps Ideas Projects Reports Topics Workbench
```

Expected: no diff errors; no unexpected changes under user-content directories. `Experiments/.gitkeep` is the only newly tracked content-area entry.

- [ ] **Step 7: Commit validation-only fixes if required**

If any scoped fixes were necessary:

```bash
git add <only-the-files-fixed-during-validation>
git commit -m "test: finish Codex migration validation"
```

If no fixes were required, do not create an empty commit.

---

## Final Review Checklist

- [ ] Design scope is fully implemented without rewriting historical specs or user notes.
- [ ] `git status --short` is clean.
- [ ] All 14 skills pass the Codex validator.
- [ ] Codex discovery, required skill sections, helper syntax, and Quartz build pass.
- [ ] README/INSTALL default to Codex and retain a clearly isolated Claude compatibility path.
- [ ] Commit history is task-scoped and reviewable.
