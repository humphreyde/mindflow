# Skill Protocol

This document defines the portable Agent Skills format used by MindFlow. Every skill — atomic or orchestrating — has a `SKILL.md` at its root. `skills/` is the canonical tree; Codex discovers the same files through `.agents/skills -> ../skills`.

MindFlow follows the [Codex skills guide](https://developers.openai.com/codex/skills) and the portable [Agent Skills specification](https://agentskills.io/specification).

---

## Discovery and Invocation

Codex reads the lightweight `name` and `description` metadata during discovery. When a skill matches the request, it reads the complete `SKILL.md`; it loads linked references, scripts, or assets only when execution needs them. This progressive-disclosure model keeps discovery concise while preserving detailed workflows close to the skill.

Users can invoke a skill explicitly with `$skill-name`:

```text
$paper-digest arXiv:2410.24164
$daily-papers 过去 3 天
$experiment-design Ideas/example.md
```

The `description` can also cause a compatible agent to select a skill implicitly. Explicit invocation is preferred when the user needs a specific workflow.

## Frontmatter Specification

Each `SKILL.md` begins with YAML frontmatter enclosed by `---` delimiters. MindFlow requires the portable discovery fields below; runtime permissions are controlled by the agent environment rather than by a platform-specific tool allowlist.

| Field | Required | Type | Description |
|:------|:---------|:-----|:------------|
| `name` | Yes | string (kebab-case) | Unique identifier; must match the skill directory name. Lowercase letters, numbers, and hyphens only; maximum 64 characters. |
| `description` | Yes | string | State what the skill does, when it should trigger, and important boundaries; maximum 1024 characters. |

### Example Frontmatter

```yaml
---
name: paper-digest
description: 当用户给出论文 URL、标题、PDF 或 DOI，或阅读队列中有待处理论文时，消化论文并生成结构化笔记到 Papers/；已有笔记需要先检查并保护用户编辑。
---
```

### Inputs belong in the body

Document inputs immediately after the frontmatter rather than encoding them in framework-specific metadata. State required and optional values, accepted forms, defaults, and what to do when an input is missing or ambiguous.

```markdown
## Inputs

- Required: one paper URL, local PDF path, DOI, or unambiguous title.
- Optional: target domain and user-provided reading questions.
- If the source is ambiguous, present candidates and ask the user to choose before writing.
```

## Body Sections

Every `SKILL.md` body must include the required sections below. `Inputs`, `Verify`, and `Examples` are strongly recommended; a skill may omit one only when it genuinely has no corresponding contract.

| Section | Required | Purpose |
|:--------|:---------|:--------|
| `## Purpose` | Yes | The workflow goal, its place in MindFlow, and its output |
| `## Inputs` | Recommended | Required/optional inputs, accepted forms, defaults, and ambiguity handling |
| `## Steps` | Yes | Ordered, capability-oriented execution instructions |
| `## Guard` | Yes | Preconditions, invariants, protected content, and prohibited actions |
| `## Verify` | Recommended | Objective checks proving the output meets the contract |
| `## Examples` | Recommended | Representative `$skill-name` invocations and expected outputs |

### Purpose

Explain in 2–5 sentences what problem the skill solves, where it fits in the research workflow, and which durable output or state change it produces.

### Steps: describe capabilities, not one runtime's tools

Write numbered instructions in terms of intent and observable results. For example:

- Write “读取目标 note 和相关 template”，not a proprietary file-read tool name.
- Write “在 `Papers/` 中搜索重复项”，not a proprietary glob or grep call.
- Write “精确更新目标段落并保留其他内容”，not a proprietary edit primitive.
- Write “使用当前环境可用的联网搜索与网页读取能力”，not a vendor-specific web command.

Shell, Python, and Node commands may be included when they are executable implementation details. State their prerequisite, input, output, and failure fallback; follow the runtime boundaries in root `AGENTS.md`.

### Guard

Guard constrains behavior during execution. It must define write scope and protect user content, source integrity, and irreversible actions.

```markdown
## Guard

- Never overwrite an existing paper note without explicit user authorization.
- Preserve frontmatter, wikilinks, and handwritten sections outside the requested scope.
- Do not present an unverified claim as sourced fact.
- If network retrieval fails, report the missing evidence instead of fabricating it.
```

### Verify

Verify runs after execution and contains mechanical, objectively checkable assertions. It is evidence that the workflow met its output contract, not a restatement of Guard.

```markdown
## Verify

- [ ] Output file exists and is non-empty.
- [ ] Required frontmatter fields are populated.
- [ ] No `[TODO]` or `[TBD]` placeholders remain.
- [ ] Every cited paper has a resolvable source or existing vault note.
```

## Progressive Disclosure

Keep the main `SKILL.md` concise enough to discover and execute:

1. `name` and `description` provide discovery metadata.
2. The body provides the complete core workflow, Guard, and Verify contract.
3. Detailed schemas, lookup tables, and extended examples live under the skill's `references/` directory and are linked from `SKILL.md`.
4. Deterministic helpers live under `scripts/`; reusable static material lives under `assets/` when needed.
5. Read only the linked resources needed for the current request, but read each selected instruction file completely before acting.

Reference files are plain Markdown and do not define nested skills. `SKILL.md` remains the authoritative entry point.

## Orchestration

An orchestration skill coordinates other skills by name without assuming a proprietary “call skill” tool:

1. Locate the target skill in `.agents/skills` / canonical `skills/`.
2. Read its complete `SKILL.md` and the referenced material required for the current input.
3. Execute its Steps while honoring its Guard.
4. Run its Verify checks before consuming the output in the next stage.

Parallel execution is optional. Use it only when the runtime supports it, subtasks are independent, and they do not share writes; otherwise run the same sequence serially. The orchestration skill owns the final cross-stage verification and reports partial failures explicitly.

## Skill Levels

| Level | Scope | Examples |
|:------|:------|:---------|
| L0 — Atomic | One focused research capability; does not orchestrate other skills | `paper-digest`, `idea-evaluate`, `experiment-track` |
| L1 — Workflow | Sequences or conditions multiple capabilities for a compound result | `daily-papers`, `literature-survey` |
| L2 — Global | Operates across vault-wide research state or the full research loop | `memory-distill`, `agenda-evolve`, `autoresearch` |

## Naming Conventions

| Element | Convention | Example |
|:--------|:-----------|:--------|
| Skill directory name | kebab-case | `paper-digest/` |
| Category directory name | numbered prefix + kebab-case | `1-literature/` |
| Skill entrypoint filename | Uppercase, exact | `SKILL.md` |
| `name` frontmatter field | Must match directory name exactly | `paper-digest` |

Numbered category prefixes preserve the research workflow order in Obsidian and file explorers.

## Current Skill Tree（14 个 skills）

```text
skills/
  1-literature/
    daily-papers/
      SKILL.md
    literature-survey/
      SKILL.md
    paper-digest/
      SKILL.md
  2-ideation/
    idea-evaluate/
      SKILL.md
    idea-generate/
      SKILL.md
  3-experiment/
    experiment-design/
      SKILL.md
    experiment-track/
      SKILL.md
    result-analysis/
      SKILL.md
  4-writing/
    draft-section/
      SKILL.md
    writing-refine/
      SKILL.md
  5-evolution/
    agenda-evolve/
      SKILL.md
    memory-distill/
      SKILL.md
    memory-retrieve/
      SKILL.md
  6-orchestration/
    autoresearch/
      SKILL.md
      references/
```
