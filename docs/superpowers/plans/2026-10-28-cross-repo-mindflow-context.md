# Cross-Repository MindFlow Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MindFlow a task-scoped, read-only-by-default research knowledge layer that Codex can use while working in `pi` and future code repositories, without coupling source-code retrieval to knowledge retrieval.

**Architecture:** Add one canonical `mindflow-context` skill under MindFlow, a validated project-profile schema, and a concrete `pi` profile. A minimal global trigger and one user-level symlink make the canonical skill available from external repositories, while Quartz and Obsidian exclude code repositories from publishing and local knowledge indexing. Repository skills, local-machine integration, publication exclusions, and behavioral smoke tests remain separately reviewable.

**Tech Stack:** Markdown and Obsidian YAML frontmatter, Python 3.12 standard library via `uv`, Git symlinks, TypeScript/Node.js 20+, Quartz 4.4.1, Node test runner

**Spec:** `docs/superpowers/specs/2026-10-28-cross-repo-mindflow-context-design.md`

## Global Constraints

- `skills/6-orchestration/mindflow-context/` is the only canonical source for the new skill. Do not copy it into another repository or expose the entire MindFlow skill tree globally.
- The only MVP profile is `Workbench/PARA/Projects/pi.md`; its only verified repository root is `/Users/limx/project/pi`.
- Research, architecture, experiment design, method selection, paper-to-code mapping, historical-decision work, and explicit MindFlow requests trigger knowledge retrieval. Mechanical formatting and ordinary local test fixes do not.
- Source-code retrieval is always available and is not constrained by MindFlow, Obsidian, or Quartz exclusions.
- MindFlow is read-only by default. A task may propose a writeback, but it must not write until the user explicitly approves the exact target and content.
- Initial knowledge reading is 5–8 notes; follow at most one wikilink hop; read at most 12 notes by default.
- Use project entrypoints first, then `DomainMaps/`, `Topics/`, `Workbench/memory/`, `Papers/`, and finally `Ideas/`, `Experiments/`, and the project profile.
- Keep Zotero independent. Do not add a vector database, embedding service, resident RAG service, or new runtime dependency.
- Do not move a code repository or modify `Projects/CLAUDE.md`, add `Projects/AGENTS.md`, change `.gitignore`, merge `/Users/limx/notes`, or create speculative `gr00t`/`fastwam` profiles.
- Do not run a full Quartz build as an MVP gate. Run the focused glob test, the full Node test suite, TypeScript checking, and formatting checks described below.
- Stage only paths owned by the current task. Local files under `/Users/limx/.codex/` and `.obsidian/` are not part of a Git commit.
- Authorization to execute this plan does not authorize Git commits or pushes. Before each proposed commit, show the exact staged paths and commit message and obtain explicit user approval; if approval is withheld, do not commit and pause at that review checkpoint.
- If Codex discovers two `mindflow-context` entries in the MindFlow repository, the global integration fails: remove only the newly created user-level symlink, restore the global `AGENTS.md` to its pre-task content, stop execution, and request a design amendment.

## File Map

### Tracked files

| Path | Change | Responsibility |
|:-----|:-------|:---------------|
| `skills/6-orchestration/mindflow-context/SKILL.md` | Create | Trigger, retrieve, label evidence, and enforce read-only/writeback boundaries |
| `skills/6-orchestration/mindflow-context/references/smoke-tests.md` | Create | Fixed behavioral prompts, working directories, and pass conditions |
| `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py` | Create | Standard-library profile schema, path, and ambiguity validator with six self-tests |
| `Templates/Project.md` | Modify | Add reusable repository-profile frontmatter while preserving the existing project body |
| `Workbench/PARA/Projects/pi.md` | Create | Map the external `pi` Git root to its MindFlow domains, keywords, and entrypoint |
| `README.md` | Modify | Update the active inventory to 15 and document the profile/code-repository split |
| `docs/INSTALL.md` | Modify | Document global discovery, collision verification, and the 15-skill inventory |
| `docs/SPEC.md` | Modify | Update the active architecture tree, profile location, inventory, and changelog |
| `references/skill-protocol.md` | Modify | Add `mindflow-context` to the canonical 15-skill tree |
| `.website/quartz.ignore.ts` | Create | Export the pure ignore-pattern list shared by Quartz config and tests |
| `.website/quartz.config.ts` | Modify | Consume the shared pure `ignorePatterns` export |
| `.website/quartz/util/glob.test.ts` | Create | Prove both Markdown inputs and non-Markdown assets under `Projects/` are excluded |

### Local, untracked integration

| Path | Change | Responsibility |
|:-----|:-------|:---------------|
| `/Users/limx/.codex/AGENTS.md` | Modify | Minimal conditional trigger for external repositories |
| `/Users/limx/.codex/skills/mindflow-context` | Create symlink | User-level discovery link to the canonical skill |
| `.obsidian/app.json` | Modify, remains ignored | Add `Projects/` to Obsidian excluded files without replacing other settings |

### Explicitly preserved

- `.agents/skills -> ../skills`
- `.gitignore`
- `Projects/CLAUDE.md`
- all historical files under `docs/superpowers/specs/` and `docs/superpowers/plans/`
- every existing Paper, Topic, DomainMap, Idea, Experiment, project note, and memory note

### Task 1: Add the canonical skill, profile schema, and `pi` profile

**Files:**

- Create: `skills/6-orchestration/mindflow-context/SKILL.md`
- Create: `skills/6-orchestration/mindflow-context/references/smoke-tests.md`
- Create: `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py`
- Modify: `Templates/Project.md:1-24`
- Create: `Workbench/PARA/Projects/pi.md`

**Interfaces:**

- Consumes: MindFlow vault root, current Git root, task keywords, and project profiles under `Workbench/PARA/Projects/`.
- Produces: CLI `validate_profiles.py --vault VAULT [--self-test]`; `Profile` records with canonical repository roots and vault-relative entrypoints; automatic research-context retrieval with a read-only default.
- Later tasks rely on: canonical skill path, profile schema fields, `pi` profile, and the nine-case smoke matrix.

- [ ] **Step 1: Record the failing baseline**

Run from `/Users/limx/mindflow`:

```bash
implementation_base=$(git rev-parse HEAD)
pi_baseline_head=$(git -C /Users/limx/project/pi rev-parse HEAD)
printf '%s\n' "$implementation_base"
printf '%s\n' "$pi_baseline_head"
git status --porcelain=v1 -uall
git -C /Users/limx/project/pi status --porcelain=v1 -uall

uv run --no-project --python 3.12 python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault . --self-test
```

Record both 40-character SHAs and both complete status outputs in the execution log; they are the authoritative implementation baseline for Task 6. Confirm this plan file is not accidentally staged with implementation paths. The validator command is expected to return non-zero with `can't open file` because the validator does not exist.

`--no-project --python 3.12` is intentional for this standard-library helper: it enforces the repository's Python floor without resolving the vault's unrelated document-processing dependencies. The Codex skill validator adds only its own `pyyaml` dependency explicitly.

Also confirm the new profile and skill are absent:

```bash
test ! -e skills/6-orchestration/mindflow-context/SKILL.md
test ! -e Workbench/PARA/Projects/pi.md
```

Expected: both checks pass.

- [ ] **Step 2: Implement the standard-library profile validator and its six self-tests**

Create `validate_profiles.py` with these exact schema constants and data contract:

```python
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FIELDS = (
    "repo_key",
    "repo_roots",
    "aliases",
    "domains",
    "entrypoints",
    "keywords",
    "verified_at",
)
LIST_FIELDS = {"repo_roots", "aliases", "domains", "entrypoints", "keywords"}


@dataclass(frozen=True)
class Profile:
    path: Path
    repo_key: str
    repo_roots: tuple[Path, ...]
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    entrypoints: tuple[Path, ...]
    keywords: tuple[str, ...]
    verified_at: str
```

Implement the following functions with no third-party import:

- `parse_frontmatter(path: Path) -> dict[str, str | list[str]]`
  - require an opening and closing `---` delimiter;
  - accept top-level scalar values, block lists, and inline empty lists only;
  - strip matching single or double quotes and trailing YAML comments outside quotes;
  - reject duplicate keys, nested mappings, list items without a parent key, and unsupported inline collections with a path-qualified error.
- `resolve_repo_root(vault: Path, value: str) -> Path`
  - expand `~`;
  - resolve absolute paths directly and relative paths against the vault root;
  - use canonical resolved paths for comparison.
- `load_profile(path: Path, vault: Path) -> tuple[Profile | None, list[str]]`
  - require every field in `REQUIRED_FIELDS`;
  - require `repo_key` to match lowercase kebab-case;
  - require every `LIST_FIELDS` value to be a list of non-empty strings;
  - require at least one repository root, one domain, one entrypoint, and one keyword;
  - require every resolved repository root to be an existing directory;
  - require entrypoints to be relative paths with no `..`; resolve them and reject absolute paths or symlink escapes outside the resolved vault before checking that each target is an existing file;
  - require `verified_at` to parse with `date.fromisoformat`.
- `validate_vault(vault: Path) -> tuple[list[Profile], list[str]]`
  - scan only sorted `Workbench/PARA/Projects/*.md` files;
  - report a missing profile directory as an error;
  - reject duplicate `repo_key` values;
  - normalize `repo_key` and aliases with `casefold()` and reject an identity claimed by more than one profile;
  - reject a canonical repository root claimed by more than one profile.
- `run_self_tests() -> int`
  - create all fixtures under one `TemporaryDirectory`;
  - never touch the real vault;
  - print one PASS/FAIL line per case and finish with `self-test: 6/6 passed` only when all cases succeed.
- `main() -> int`
  - support `--vault` and `--self-test` through `argparse`;
  - when `--self-test` is present, run only the temporary six-case suite and return before real-vault validation, so the self-test works before the real profile directory exists;
  - return `0` on success and `1` on any validation or self-test failure;
  - on real-vault success print `validated 1 profile(s); 1 unique repo root(s); 0 errors` for the MVP state.

The six self-test fixtures are fixed:

| Case | Fixture | Required assertion |
|:-----|:--------|:-------------------|
| `valid` | one profile, existing absolute repo root, existing `DomainMaps/VLA.md` | zero errors |
| `missing field` | omit `keywords` | error names `keywords` |
| `stale root` | point to a missing directory | error contains `repo root does not exist` |
| `missing entrypoint` | point to `DomainMaps/Missing.md` | error contains `entrypoint does not exist` |
| `ambiguous match` | two profiles claim the same canonical repo root | error contains both profile paths and `ambiguous repo root` |
| `relative-root resolution` | use `repos/pi` below the temporary vault | resolved root equals `vault / "repos/pi"` and validation succeeds |

- [ ] **Step 3: Run the validator self-tests**

```bash
uv run --no-project --python 3.12 python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault . --self-test
```

Expected: six named PASS lines followed by `self-test: 6/6 passed`; exit code `0`.

- [ ] **Step 4: Extend the Project template and create the concrete `pi` profile**

Replace the template frontmatter with the following fields, preserving every existing body section from `## Goal` through `## Notes`:

```yaml
---
title:
tags: []
type: project
repo_key:
repo_roots: []
aliases: []
domains: []
entrypoints: []
keywords: []
status: planning
date_started: "{{date}}"
verified_at:
---
```

Create `Workbench/PARA/Projects/pi.md` with this exact frontmatter:

```yaml
---
title: OpenPI
tags: []
type: project
repo_key: pi
repo_roots:
  - /Users/limx/project/pi
aliases:
  - openpi
  - pi07
domains:
  - VLA
  - RECAP
  - TRON2
entrypoints:
  - DomainMaps/VLA.md
keywords:
  - ACP
  - RTC
  - pi0
status: active
date_started: 2026-10-28
verified_at: 2026-10-28
---
```

Use the preserved project sections below the frontmatter. Set the Goal to task-scoped research context for OpenPI development; link `[[DomainMaps/VLA|VLA]]`; record that code/runtime truth stays in `/Users/limx/project/pi`; record that a future move only updates `repo_roots`; do not invent paper links, experiment results, or progress claims.

Run the real-vault check:

```bash
uv run --no-project --python 3.12 python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault .
```

Expected: `validated 1 profile(s); 1 unique repo root(s); 0 errors`.

- [ ] **Step 5: Write the canonical `mindflow-context` skill**

Use this exact frontmatter:

```yaml
---
name: mindflow-context
description: 当任务涉及研究、架构、实验设计、方法选择、论文与实现映射或历史决策，或用户明确要求使用 MindFlow 时，按项目 profile 检索相关论文、领域图谱和历史知识；机械格式化与普通局部测试修复不触发，MindFlow 默认只读。
---
```

The body must contain `## Purpose`, `## Inputs`, `## Steps`, `## Guard`, `## Verify`, and `## Examples` with these contracts:

1. **Purpose:** keep source-code truth and research knowledge as independent lanes; retrieve bounded evidence rather than loading the whole vault.
2. **Inputs:** task text is required; `vault_root` defaults to `/Users/limx/mindflow`; `repo_root` defaults to `git rev-parse --show-toplevel` when available; an explicit writeback approval is optional and never inferred.
3. **Steps:** classify the trigger; resolve a profile by canonical root first and identity second; stop on multiple matches; build terms from the task, code symbols, profile fields, and entrypoints; search in the approved order with `rg -l -i`; rank candidates by explicit profile/note link, exact title/arXiv ID/DOI/citekey, frontmatter alias/tag, then body match; read 5–8 notes; follow one evidenced wikilink hop up to 12 total; report labeled evidence and an optional writeback proposal. Include one concrete `rg -l -i --glob '*.md'` example with the complete exclusion globs and the ordered MindFlow roots.
4. **Fallback:** if there is no profile, search from repository name, task terms, and code symbols; say that no project profile was used.
5. **Search exclusions:** exclude `Projects/**`, `.git/`, `.website/`, `.worktrees/`, `assets/`, checkpoints, models, datasets, logs, caches, builds, `Private/`, `Meetings/`, and `Workbench/logs/` unless the task explicitly needs a historical decision.
6. **Evidence labels:** use `代码证据`, `论文笔记`, `历史记录`, and `Codex 推断`; cite an absolute file path plus heading for each MindFlow source.
7. **No-evidence behavior:** say `MindFlow 中未找到相关证据`; continue with available code evidence or ask for the next source; never fabricate a citation.
8. **Failure handling:** report stale roots or missing entrypoints without editing the profile; skip and name broken links; present contradictory notes side by side; attach current verification to branch, commit, host, service, checkpoint, and experiment-state claims.
9. **Sensitive data:** never write credentials, tokens, private addresses, camera serial numbers, large logs, checkpoints, or unscreened runtime output into MindFlow.
10. **Source lane boundary:** start from the current repository; inspect another code repository only when an explicit dependency, a current-code reference, or the user names that repository.
11. **Writeback:** propose only reusable knowledge and output the approved four-field proposal (`目标`, `内容`, `证据`, `理由`); do not write until the user approves; after approval reread `AGENTS.md`, the applicable reference/template, and the target note. Route single-paper conclusions to `Papers/`, cross-paper synthesis to `Topics/` or `DomainMaps/`, hypotheses to `Ideas/`, experiment plans/results to `Experiments/`, and engineering/research progress to the project profile. Route a cross-project reusable workflow to `skills/` only after separate explicit authorization. A write approval never authorizes commit or push.
12. **Zotero:** query it only when the user or evidence requires original text, metadata, or citekeys; do not synchronize libraries.
13. **Runtime verification:** link `references/smoke-tests.md` from the Verify section as the maintainer-facing behavioral matrix.

- [ ] **Step 6: Write the fixed smoke-test reference**

Create `references/smoke-tests.md` with a table containing exactly these nine cases:

| Case | Working directory | Exact prompt | Pass condition |
|:-----|:------------------|:-------------|:---------------|
| 1 | `/Users/limx/project/pi` | `基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。` | `pi` profile selected; both code and MindFlow evidence labeled |
| 2 | `/Users/limx/project/pi` | `只检查当前 pi 仓库的 pyproject.toml 是否存在尾随空格；不要修改文件，也不要检索研究知识。` | source read allowed; MindFlow not invoked |
| 3 | `/Users/limx/mindflow` | `使用 MindFlow 解释 action chunking 与 action horizon 的区别；不要扫描任何代码仓。` | MindFlow used; no unrelated code-repository scan |
| 4 | `/Users/limx/project/pi` | `把当前 pi 仓库中的 ACP 实现与 MindFlow 中相关论文笔记对应起来；区分代码证据、论文笔记和你的推断。只读。` | both lanes used and labels correct |
| 5 | temporary external Git repo without a profile | `为当前机器人代码仓设计一套 action chunking 架构并说明取舍。不要显式调用任何 skill，只读。` | automatic trigger; generic fallback; missing profile stated |
| 6 | `/Users/limx/mindflow` | `在 MindFlow 中查找 XYZZY-MINDFLOW-NO-EVIDENCE-20261028，并只报告有来源的结论。` | explicit no-evidence statement and no fabricated source |
| 7 | `/Users/limx/project/pi` | `基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。` | MindFlow hashes and Git status unchanged |
| 8 | `/Users/limx/project/pi` | `基于本次 RECAP 分析给出建议沉淀，但不要写入任何文件；我尚未批准写回。` | proposal shown; zero file changes |
| 9 | temporary fixture vault | `使用 $mindflow-context，并把 vault_root 设为本轮临时 fixture vault 的绝对路径。把“Approved fixture conclusion.”追加到 Topics/Fixture.md；我明确批准这一次写回。不得修改其他文件。` | only that note changes; pre-existing handwritten text remains |

For each case, include the exact prompt, expected files that may be read, forbidden reads/writes, evidence labels, and an empty result checkbox. The file is test documentation, not a second skill.

- [ ] **Step 7: Validate the new skill, schema, paths, and discovery count**

```bash
validator=/Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py
uv run --no-project --python 3.12 --with pyyaml python "$validator" skills/6-orchestration/mindflow-context

for section in Purpose Inputs Steps Guard Verify Examples
do
  rg -q "^## ${section}$" skills/6-orchestration/mindflow-context/SKILL.md || exit 1
done

test "$(sed -n 's/^name: //p' skills/6-orchestration/mindflow-context/SKILL.md | head -1)" = "mindflow-context"
test "$(find -L .agents/skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l | tr -d ' ')" = "15"
test "$(git -C /Users/limx/project/pi rev-parse --show-toplevel)" = "/Users/limx/project/pi"
test -f DomainMaps/VLA.md
git diff --check
```

Expected: validator success, all six sections present, canonical count `15`, both live profile paths valid, and no whitespace errors.

- [ ] **Step 8: Request commit approval for the canonical skill and profile**

```bash
git add \
  skills/6-orchestration/mindflow-context \
  Templates/Project.md \
  Workbench/PARA/Projects/pi.md
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Show the exact output and propose commit message `feat: add cross-repo MindFlow context skill`. Only after the user explicitly approves this commit, run:

```bash
git commit -m "feat: add cross-repo MindFlow context skill"
```

Without approval, do not commit or proceed to Task 2.

---

### Task 2: Install the global trigger and run the duplicate-discovery gate

**Files:**

- Modify locally: `/Users/limx/.codex/AGENTS.md`
- Create locally: `/Users/limx/.codex/skills/mindflow-context` symlink
- Preserve: `.agents/skills -> ../skills`

**Interfaces:**

- Consumes: canonical Task 1 skill and Codex repository/user skill discovery.
- Produces: external-repository automatic trigger only if both `pi` and MindFlow fresh sessions see exactly one `mindflow-context` entry resolving to the canonical realpath.
- Failure contract: if a duplicate appears, roll back the two local changes and stop the implementation before Task 3.

- [ ] **Step 1: Capture the local baseline without overwriting it**

```bash
test -f /Users/limx/.codex/AGENTS.md
wc -c /Users/limx/.codex/AGENTS.md
test ! -e /Users/limx/.codex/skills/mindflow-context
test ! -L /Users/limx/.codex/skills/mindflow-context
test "$(readlink .agents/skills)" = "../skills"
```

Expected for the current machine: global `AGENTS.md` is `0` bytes; the user-level skill path is absent; the repository discovery link is unchanged.

If the files differ when execution begins, inspect and preserve the new content. Stop if the user-level skill path exists and does not resolve to the canonical Task 1 directory.

- [ ] **Step 2: Add the minimal global trigger block**

Add this exact block once to `/Users/limx/.codex/AGENTS.md`:

```markdown
## MindFlow research context

- For research, architecture, experiment design, method selection, paper-to-code mapping, historical-decision work, or an explicit request to use MindFlow, use `$mindflow-context`.
- Profile or `MindFlow/Projects/` membership selects project retrieval versus generic fallback; it does not decide whether a research task triggers.
- Do not invoke MindFlow for mechanical formatting, ordinary local test fixes, or unrelated code changes.
- This rule controls research-knowledge retrieval only; source code remains readable whenever the task requires it.
```

Do not add project paths, keywords, or profile content to the global file.

- [ ] **Step 3: Create the one user-level symlink safely**

```bash
canonical=/Users/limx/mindflow/skills/6-orchestration/mindflow-context
global_link=/Users/limx/.codex/skills/mindflow-context

test -d "$canonical"
test ! -e "$global_link"
test ! -L "$global_link"
ln -s "$canonical" "$global_link"
test "$(realpath "$global_link")" = "$(realpath "$canonical")"
test "$(realpath .agents/skills/6-orchestration/mindflow-context)" = "$(realpath "$canonical")"
```

Do not use `ln -f`, copy files, link `/Users/limx/mindflow/skills` as a whole, or create a second user-level copy under another discovery root.

- [ ] **Step 4: Run the hard duplicate-discovery gate in fresh Codex sessions**

[Official OpenAI documentation](https://developers.openai.com/codex/skills#where-to-save-skills) states that Codex loads repo and user scopes together and does not merge skills that share a name; both can appear in selectors. Restart Codex or use fresh isolated agent contexts so discovery is recalculated.

1. From `/Users/limx/project/pi`, list the available skills and invoke `$mindflow-context` with: `只报告你加载的 mindflow-context SKILL.md 绝对路径，不执行知识检索。`
2. From `/Users/limx/mindflow`, repeat the same inspection and invocation.
3. Record the number of selector/catalog entries named `mindflow-context` and the loaded `SKILL.md` realpath in each environment.

Pass only if:

- each environment reports exactly one selectable `mindflow-context`;
- both load `/Users/limx/mindflow/skills/6-orchestration/mindflow-context/SKILL.md`;
- no copied entrypoint exists under another path.

If either environment reports zero or multiple entries, a non-canonical realpath, or a copied entrypoint, verify the new user-level path is still the exact symlink created in Step 3, remove that symlink, restore the global `AGENTS.md` to its captured pre-task content, and stop. Report that the approved single-name repo-plus-user architecture needs amendment; do not continue to documentation, exclusions, or smoke tests.

- [ ] **Step 5: Confirm the local integration did not enter the repository diff**

```bash
git status --short
git diff --check
```

Expected: no tracked changes from `/Users/limx/.codex/`; no commit is created for this task.

---

### Task 3: Update active documentation and the 15-skill inventory

**Files:**

- Modify: `README.md:28,40-55,73-101`
- Modify: `docs/INSTALL.md:1-55`
- Modify: `docs/SPEC.md:65-110,146-188,258-276`
- Modify: `references/skill-protocol.md:149-188`

**Interfaces:**

- Consumes: accepted Task 2 discovery behavior and Task 1 canonical/profile paths.
- Produces: one consistent active inventory and install contract; historical design and plan files remain unchanged.

- [ ] **Step 1: Capture the old active inventory**

```bash
rg -n '14 个 AI|14 个 skills|完整 skill 清单.*14|Expected: 14' \
  README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
```

Expected: active-inventory matches in all four files.

- [ ] **Step 2: Update `README.md`**

- Change active counts from 14 to 15.
- Describe `Projects/` as independently versioned code repositories excluded from vault publication/indexing.
- Add `Workbench/PARA/Projects/` as project research profiles and status pages.
- Add `mindflow-context` to Layer 6 beside `autoresearch` with a concise cross-repository research-context description.
- Add one invocation example: `$mindflow-context 分析当前项目的 action chunking 设计`.
- Keep the Claude compatibility note and all existing 14 skills.

- [ ] **Step 3: Update `docs/INSTALL.md`**

- Change the discovery count and expected count to 15.
- Add a section named `Optional: Cross-repository MindFlow context` after repository skill verification.
- Document the one user-level symlink to the canonical skill, the minimal global trigger, the fresh-session collision gate, and the rollback requirement from Task 2.
- State that the canonical tree is never copied and that external repositories do not inherit MindFlow's parent `AGENTS.md`.
- State that `pi` remains external in the MVP and that shared `Projects/` compatibility files are deliberately deferred until the first repository migration.
- Preserve Python/Node version boundaries and the existing Claude compatibility section.

- [ ] **Step 4: Update `docs/SPEC.md`**

- In the directory tree, distinguish `Projects/` code repositories from `Workbench/PARA/Projects/` profiles.
- Update the active inventory heading to 15 and add one `mindflow-context` L1 row under `6-orchestration`.
- Explain that `mindflow-context` is global retrieval orchestration, not part of the autonomous `autoresearch` action registry.
- Record that the current `Projects/CLAUDE.md` convention conflicts with direct code-repository roots; before the first repository moves, a separately approved task must add Codex-first `Projects/AGENTS.md`, revise Claude compatibility, and update the narrow shared-file exception without assuming parent instructions cross a nested Git root.
- Add a dated 2026-10-28 changelog entry for the profile-driven cross-repository research layer.
- Preserve all historical 14-skill changelog entries as history.

- [ ] **Step 5: Update `references/skill-protocol.md`**

- Change `Current Skill Tree` to 15.
- Add `mindflow-context/SKILL.md`, `references/smoke-tests.md`, and `scripts/validate_profiles.py` under `6-orchestration`.
- Do not alter the portable frontmatter or section requirements.

- [ ] **Step 6: Verify documentation consistency**

```bash
test "$(rg --files skills -g SKILL.md | wc -l | tr -d ' ')" = "15"

rg -n '15 个 AI|15 个 skills|完整 skill 清单.*15|Expected: 15|mindflow-context' \
  README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md

old_active=$(rg -n '14 个 AI|14 个 skills|完整 skill 清单.*14|Expected: 14' \
  README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md || true)
test -z "$old_active"

git diff --check
```

Expected: all active documentation names `mindflow-context` and 15; old active-count patterns are absent; historical changelog references remain untouched.

- [ ] **Step 7: Request commit approval for the documentation update**

```bash
git add README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Show the exact output and propose commit message `docs: document cross-repo MindFlow context`. Only after explicit approval, run:

```bash
git commit -m "docs: document cross-repo MindFlow context"
```

Without approval, do not commit or proceed to Task 4.

---

### Task 4: Exclude code repositories from Quartz and Obsidian

**Files:**

- Create: `.website/quartz.ignore.ts`
- Create: `.website/quartz/util/glob.test.ts`
- Modify: `.website/quartz.config.ts:1-20`
- Modify locally: `.obsidian/app.json:1`

**Interfaces:**

- Consumes: Quartz `glob(pattern, cwd, ignorePatterns)` and a pure exported `ignorePatterns` array shared with `quartz.config.ts`.
- Produces: a regression test that excludes both Markdown and assets under `Projects/`; a local Obsidian `userIgnoreFilters` entry.

- [ ] **Step 1: Record the website baseline and repair only encrypted ignored dependencies if required**

From `/Users/limx/mindflow/.website`:

```bash
npm test
npx tsc --noEmit
npm run check
```

Current expected baseline:

- `npm test`: 39/39 tests pass.
- The current Node 26.4 runtime emits one existing `[DEP0205] DeprecationWarning` for `module.register()`; `.website/.node-version` records v20.9.0. Prefer the configured Node version when the installed version manager supports it, otherwise preserve this warning as a baseline and reject only new warnings.
- `npx tsc --noEmit`: exit `0`.
- `npm run check`: non-zero only because Prettier reports these nine existing files: `quartz.config.ts`, `quartz.layout.ts`, `quartz/components/Date.tsx`, `quartz/components/HomepageStats.tsx`, `quartz/components/HomepageTags.tsx`, `quartz/components/PageList.tsx`, `quartz/components/pages/FolderContent.tsx`, `quartz/components/SidebarTags.tsx`, and `quartz/styles/custom.scss`.

Probe the dependency actually used by the focused test:

```bash
node --input-type=module -e 'await import("globby")'
```

If this runtime import or `npm test` fails with the `%TSD-Header-###%` / `Unexpected "%"` parse symptom, restore all ignored dependencies with `npm ci` and rerun the baseline. Do not reinstall merely because a raw file header contains the marker: the current runtime can load some transparently protected packages. Do not decrypt files manually and do not run a Quartz build.

- [ ] **Step 2: Extract the pure ignore list and add the failing regression test**

Create `.website/quartz.ignore.ts` with the current behavior and no `Projects/**` entry yet:

```typescript
export const ignorePatterns = [
  "Templates/**",
  ".obsidian/**",
  "docs/**",
  ".website/**",
  "Private/**",
  "private",
  "*.canvas",
  "CLAUDE.md",
  "AGENTS.md",
  "README.md",
  "skills/**",
  "references/**",
  "Workbench/**",
  "Meetings/**",
]
```

In `.website/quartz.config.ts`, import `ignorePatterns` from `./quartz.ignore` and replace only the existing inline array with the imported constant. This extraction must not add, remove, or reorder patterns before the red test.

Create `.website/quartz/util/glob.test.ts`:

```typescript
import assert from "node:assert/strict"
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { test } from "node:test"
import { ignorePatterns } from "../../quartz.ignore"
import { glob } from "./glob"

test("Projects is excluded from Quartz inputs and assets", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "mindflow-quartz-"))
  t.after(async () => rm(root, { recursive: true, force: true }))

  await mkdir(path.join(root, "Papers"), { recursive: true })
  await mkdir(path.join(root, "assets"), { recursive: true })
  await mkdir(path.join(root, "Projects", "pi", "assets"), { recursive: true })
  await writeFile(path.join(root, "Papers", "keep.md"), "# Keep\n")
  await writeFile(path.join(root, "assets", "keep.png"), "keep")
  await writeFile(path.join(root, "Projects", "pi", "README.md"), "# Exclude\n")
  await writeFile(path.join(root, "Projects", "pi", "assets", "model.bin"), "exclude")

  const inputs = await glob("**/*.*", root, ignorePatterns)
  assert.deepEqual(inputs.sort(), ["Papers/keep.md", "assets/keep.png"])

  const assets = await glob("**", root, [
    "**/*.md",
    ...ignorePatterns,
  ])
  assert.deepEqual(assets.sort(), ["assets/keep.png"])
})
```

Run:

```bash
npm test -- quartz/util/glob.test.ts
```

Expected before adding `Projects/**`: FAIL because one or both `Projects/pi` files appear in the actual arrays.

- [ ] **Step 3: Add the minimal Quartz exclusion and format only new website files**

Add `"Projects/**"` once to the exported array in `.website/quartz.ignore.ts`. Do not change layouts, styles, components, or emitters.

Run:

```bash
npx prettier quartz.ignore.ts quartz/util/glob.test.ts --write
npm test -- quartz/util/glob.test.ts
```

Expected: the focused test passes. Preserve the existing formatting of `quartz.config.ts`; its only behavioral change is consuming the extracted constant.

- [ ] **Step 4: Merge the local Obsidian exclusion without replacing other settings**

Update `.obsidian/app.json` so `userIgnoreFilters` contains `Projects/`. Preserve every other key and every existing filter. The current empty settings object becomes:

```json
{
  "userIgnoreFilters": ["Projects/"]
}
```

Validate with:

```bash
uv run --no-project --python 3.12 python -c 'import json; from pathlib import Path; data=json.loads(Path(".obsidian/app.json").read_text()); assert "Projects/" in data.get("userIgnoreFilters", [])'
git check-ignore .obsidian/app.json
```

Expected: JSON assertion succeeds and Git reports `.obsidian/app.json` as ignored.

- [ ] **Step 5: Run focused and full website regression checks**

From `.website/`:

```bash
npm test
npx tsc --noEmit
npx prettier quartz.ignore.ts quartz/util/glob.test.ts --check
npm run check
```

Expected:

- full tests pass with the new glob test added;
- TypeScript and formatting checks for both new files pass;
- full `npm run check` may remain non-zero only for the eight untouched baseline files; extracting the inline array removes the pre-existing `quartz.config.ts` formatting warning without reformatting that file;
- no new warning path or runtime warning beyond the recorded Node 26 `[DEP0205]` baseline is allowed.

Do not reformat the eight remaining baseline-warning files merely to make the aggregate command green.

- [ ] **Step 6: Request commit approval for the tracked exclusion and test**

```bash
cd /Users/limx/mindflow
git add .website/quartz.config.ts .website/quartz.ignore.ts .website/quartz/util/glob.test.ts
git diff --cached --check
git diff --cached --name-only
git diff --cached --stat
```

Confirm `.obsidian/app.json` is not staged. Show the exact output and propose commit message `test: exclude code projects from Quartz`. Only after explicit approval, run:

```bash
git commit -m "test: exclude code projects from Quartz"
```

Without approval, do not commit or proceed to Task 5.

---

### Task 5: Run the full automated acceptance suite

**Files:**

- Verify only: all Task 1–4 tracked and local files

**Interfaces:**

- Consumes: committed canonical implementation, accepted global discovery, and local exclusions.
- Produces: fresh evidence for schema, skill, inventory, symlink, Quartz, Obsidian, and Git acceptance criteria.

- [ ] **Step 1: Validate profiles and all 15 skills**

```bash
cd /Users/limx/mindflow

uv run --no-project --python 3.12 python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault . --self-test
uv run --no-project --python 3.12 python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault .

validator=/Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py
validated=0
for dir in skills/*/*
do
  test -f "$dir/SKILL.md" || continue
  uv run --no-project --python 3.12 --with pyyaml python "$validator" "$dir" || exit 1
  name=$(sed -n 's/^name: //p' "$dir/SKILL.md" | head -1)
  test "$name" = "$(basename "$dir")" || exit 1
  validated=$((validated + 1))
done
test "$validated" = "15"
```

Expected: 6/6 profile fixtures, one valid real profile, and 15/15 valid skill entrypoints with matching names.

- [ ] **Step 2: Validate repository and global discovery paths**

```bash
canonical=$(realpath skills/6-orchestration/mindflow-context)
test "$(readlink .agents/skills)" = "../skills"
test "$(realpath .agents/skills/6-orchestration/mindflow-context)" = "$canonical"
test "$(realpath /Users/limx/.codex/skills/mindflow-context)" = "$canonical"
test "$(find -L .agents/skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l | tr -d ' ')" = "15"
```

Expected: all three paths resolve to one canonical directory, while the fresh-session uniqueness evidence from Task 2 remains the behavioral authority.

- [ ] **Step 3: Validate inventories and exclusions**

```bash
rg -n '15 个 AI|15 个 skills|完整 skill 清单.*15|Expected: 15|mindflow-context' \
  README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md

test -z "$(rg -n '14 个 AI|14 个 skills|完整 skill 清单.*14|Expected: 14' \
  README.md docs/INSTALL.md docs/SPEC.md references/skill-protocol.md || true)"

rg -n 'Projects/\*\*' .website/quartz.ignore.ts
uv run --no-project --python 3.12 python -c 'import json; from pathlib import Path; data=json.loads(Path(".obsidian/app.json").read_text()); assert "Projects/" in data.get("userIgnoreFilters", [])'
```

Expected: active inventory is 15, Quartz excludes `Projects/**`, and Obsidian excludes `Projects/`.

- [ ] **Step 4: Re-run website and repository checks**

```bash
cd /Users/limx/mindflow/.website
npm test
npx tsc --noEmit
npx prettier quartz.ignore.ts quartz/util/glob.test.ts --check
npm run check

cd /Users/limx/mindflow
git diff --check
git status --short --branch
```

Expected: Node tests, TypeScript, and the new test-file formatting check pass; the full check has only the eight untouched Prettier warnings and no new warning beyond the recorded Node 26 runtime baseline; Git has no unstaged or staged tracked changes; the branch contains only user-approved commits and is not pushed.

---

### Task 6: Execute the behavioral smoke matrix and close out

**Files:**

- Read: `skills/6-orchestration/mindflow-context/references/smoke-tests.md`
- Temporary only: one external Git fixture and one fixture vault created with `mktemp -d`
- Verify only: MindFlow and `pi`

**Interfaces:**

- Consumes: accepted automated checks and fresh-session skill discovery.
- Produces: evidence that triggers, retrieval lanes, fallback, source labels, no-evidence behavior, and writeback authorization work end to end.

- [ ] **Step 1: Capture deterministic MindFlow, `pi`, and local-integration baselines**

```bash
cd /Users/limx/mindflow
mindflow_baseline_hashes=$(mktemp)
mindflow_baseline_git=$(mktemp)
pi_baseline_untracked_hashes=$(mktemp)
pi_baseline_git=$(mktemp)
local_baseline=$(mktemp)

rg --files --hidden --no-ignore \
  -g '!Projects/**' \
  -g '!.git/**' \
  -g '!.website/node_modules/**' \
  -g '!.website/public/**' \
  -g '!.website/quartz/.quartz-cache/**' \
  -g '!.venv/**' \
  -g '!assets/**' \
  -g '!.DS_Store' \
  | LC_ALL=C sort \
  | while IFS= read -r file; do shasum -a 256 "$file"; done \
  > "$mindflow_baseline_hashes"

{
  git rev-parse HEAD
  git status --porcelain=v1 -uall
  git diff --binary
  git diff --cached --binary
} > "$mindflow_baseline_git"

git -C /Users/limx/project/pi ls-files --others --exclude-standard -z \
  | (cd /Users/limx/project/pi && xargs -0 shasum -a 256) \
  | LC_ALL=C sort > "$pi_baseline_untracked_hashes"

{
  git -C /Users/limx/project/pi rev-parse HEAD
  git -C /Users/limx/project/pi status --porcelain=v1 -uall
  git -C /Users/limx/project/pi submodule status --recursive
  git -C /Users/limx/project/pi diff --binary
  git -C /Users/limx/project/pi diff --cached --binary
} > "$pi_baseline_git"

{
  shasum -a 256 /Users/limx/.codex/AGENTS.md .obsidian/app.json
  readlink /Users/limx/.codex/skills/mindflow-context
  realpath /Users/limx/.codex/skills/mindflow-context
} > "$local_baseline"
```

Keep all five temporary files until cases 1–8 finish. Run Step 3 in the same shell session or record each absolute `mktemp` path in the execution log. This baseline deliberately preserves the existing `pi` branch, tracked diffs, index, and untracked `web/` state instead of assuming that repository is clean.

- [ ] **Step 2: Run independent read-only trigger and retrieval cases**

Use fresh isolated agent contexts so the skill catalog is reloaded. The cases can run in parallel only because they are read-only:

- Agent A: cases 1, 2, and 4 from `/Users/limx/project/pi`.
- Agent B: cases 3 and 6 with no repository-specific assumptions.
- Agent C: case 5 in a temporary external Git repository that contains only a README and has no MindFlow profile.

Each agent must report the loaded canonical `SKILL.md`, selected profile or fallback, files read, evidence labels, total MindFlow note count, and whether any file changed. Reject a result that omits the no-evidence statement, exceeds 12 notes without user approval, or scans a code repository in case 3.

- [ ] **Step 3: Verify no-write behavior for cases 7 and 8**

Run case 7 with its recorded exact prompt, then run case 8 and stop after the writeback proposal. Recompute every baseline artifact:

```bash
mindflow_after_hashes=$(mktemp)
mindflow_after_git=$(mktemp)
pi_after_untracked_hashes=$(mktemp)
pi_after_git=$(mktemp)
local_after=$(mktemp)

rg --files --hidden --no-ignore \
  -g '!Projects/**' \
  -g '!.git/**' \
  -g '!.website/node_modules/**' \
  -g '!.website/public/**' \
  -g '!.website/quartz/.quartz-cache/**' \
  -g '!.venv/**' \
  -g '!assets/**' \
  -g '!.DS_Store' \
  | LC_ALL=C sort \
  | while IFS= read -r file; do shasum -a 256 "$file"; done \
  > "$mindflow_after_hashes"

{
  git rev-parse HEAD
  git status --porcelain=v1 -uall
  git diff --binary
  git diff --cached --binary
} > "$mindflow_after_git"

git -C /Users/limx/project/pi ls-files --others --exclude-standard -z \
  | (cd /Users/limx/project/pi && xargs -0 shasum -a 256) \
  | LC_ALL=C sort > "$pi_after_untracked_hashes"

{
  git -C /Users/limx/project/pi rev-parse HEAD
  git -C /Users/limx/project/pi status --porcelain=v1 -uall
  git -C /Users/limx/project/pi submodule status --recursive
  git -C /Users/limx/project/pi diff --binary
  git -C /Users/limx/project/pi diff --cached --binary
} > "$pi_after_git"

{
  shasum -a 256 /Users/limx/.codex/AGENTS.md .obsidian/app.json
  readlink /Users/limx/.codex/skills/mindflow-context
  realpath /Users/limx/.codex/skills/mindflow-context
} > "$local_after"

cmp "$mindflow_baseline_hashes" "$mindflow_after_hashes"
cmp "$mindflow_baseline_git" "$mindflow_after_git"
cmp "$pi_baseline_untracked_hashes" "$pi_after_untracked_hashes"
cmp "$pi_baseline_git" "$pi_after_git"
cmp "$local_baseline" "$local_after"
```

Expected: all five comparisons succeed; cases 1–8 preserve every covered MindFlow file, both Git states (including submodule status), every non-ignored untracked `pi` file by content hash, the global trigger, the user-level symlink, and the ignored Obsidian setting. The `pi` HEAD plus binary tracked and cached diffs cover tracked-file content without attempting to hash gitlink directories.

- [ ] **Step 4: Verify approved writeback only in an isolated fixture vault**

Create two explicit temporary roots:

```bash
fixture_vault=$(mktemp -d)
fixture_repo=$(mktemp -d)
git -C "$fixture_repo" init
```

Use precise file edits to create this fixture; do not use shell heredocs or redirect generated note content:

```text
fixture_vault/
├── AGENTS.md
├── DomainMaps/VLA.md
├── Templates/Project.md
├── Topics/Fixture.md
└── Workbench/PARA/Projects/fixture.md
```

- `AGENTS.md`: state that only an explicitly approved target may change and handwritten content must be preserved.
- `DomainMaps/VLA.md`: `# VLA` followed by one sourced fixture sentence.
- `Templates/Project.md`: copy the Task 1 project template.
- `fixture.md`: use the approved profile schema, `repo_key: fixture`, the actual absolute `fixture_repo` path, a block-list `entrypoints` value containing `DomainMaps/VLA.md`, and `verified_at: 2026-10-28`.
- `Topics/Fixture.md`: use exactly this starting content:

```markdown
---
title: Fixture
---

# Fixture

Handwritten text must survive.
```

Capture hashes for every fixture file. Invoke the skill with the actual absolute `fixture_vault`, approve one exact append of `Approved fixture conclusion.` to `Topics/Fixture.md`, and compare the fixture before/after.

Pass only if:

- exactly one specified target note changes;
- `Handwritten text must survive.` remains byte-for-byte present;
- no frontmatter key, profile, template, or other note changes;
- the result cites the approved evidence and reports the writeback path.

After verifying both paths still begin with the system temporary-directory prefix returned by `mktemp -d`, remove the two fixture roots. Do not point this destructive test at the real vault.

- [ ] **Step 5: Review the complete change set and report the handoff**

Assign `implementation_base` and `pi_baseline_head` to the exact 40-character SHAs recorded in Task 1 Step 1, then run:

```bash
cd /Users/limx/mindflow
git log --oneline --decorate "${implementation_base}..HEAD"
git status --short --branch
git diff --check "${implementation_base}..HEAD"
test "$(git -C /Users/limx/project/pi rev-parse HEAD)" = "$pi_baseline_head"
```

Report:

- commit hashes and messages;
- the canonical skill/profile paths;
- global trigger/link and Obsidian local integration state;
- automated test counts and the known untouched Prettier baseline;
- each smoke case result;
- confirmation that no repository was moved, no MindFlow write occurred without approval, and nothing was pushed.

Do not push, merge, move repositories, or create additional profiles as part of this plan.

## Spec Coverage Review

| Spec requirement | Implemented by |
|:-----------------|:---------------|
| Direct code-repository layout with `pi` unmoved | Global Constraints, Task 1 profile, Task 3 docs |
| Independent source and knowledge lanes | Task 1 skill, Task 6 cases 1–4 |
| Trigger policy and generic fallback | Task 1 skill, Task 2 trigger, Task 6 cases 2/3/5 |
| Bounded search order and evidence labels | Task 1 skill, Task 6 cases 1/4/6 |
| Read-only default and approved writeback | Task 1 Guard, Task 6 cases 7–9 |
| Canonical skill and profile validation | Task 1 validator and skill checks, Task 5 |
| Single global discovery link with duplicate gate | Task 2, Task 5 discovery checks |
| Active inventory updated from 14 to 15 | Task 3, Task 5 inventory checks |
| Quartz and Obsidian exclusion without source blocking | Task 4, Task 5, Task 6 case 2 |
| Zotero remains independent; no vector service | Global Constraints and Task 1 Guard |
| Deferred migrations and `Projects` shared files untouched | Global Constraints and final change-set review |

No implementation task may be marked complete if Task 2's fresh-session uniqueness gate fails, even when all static realpath checks pass.
