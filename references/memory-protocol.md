# Memory Protocol

This document defines how MindFlow stores, organizes, and promotes research knowledge. The memory system transforms raw observations into structured, reusable insights.

---

## Directory Structure

All persistent memory lives under `Workbench/memory/` as plain Markdown files.

```
Workbench/
  memory/
    patterns.md            # Cross-paper or cross-experiment patterns (not yet validated)
    insights.md            # Discovered insights (provisional -> validated)
    effective-methods.md   # Proven experiment and analysis strategies
    failed-directions.md   # Abandoned research directions and the reasons why
  logs/                    # Raw session logs (Level 0 input to memory)
  evolution/
    changelog.md           # Record of promotions and material lifecycle changes
```

| File | Purpose | Key Fields |
|---|---|---|
| `patterns.md` | Early-stage observations that recur across sources; feeds the promotion pipeline | observation, occurrences, confidence (low/medium), needs_verification, status |
| `insights.md` | Curated claims with evidence and confidence tracking; provisional -> validated | claim, evidence, confidence, source_pattern, source, impact, status |
| `effective-methods.md` | Strategies that worked, with context and caveats | context, method, evidence, pitfalls |
| `failed-directions.md` | What was tried and why it was abandoned; prevents re-exploring dead ends | original_hypothesis, evidence_against, lesson, related_directions |

---

## Entry Format

All memory files use the same heading-and-bullet structure. An entry's claim and history are immutable: never delete an entry, remove prior evidence, or silently rewrite its substantive text. Add a new cross-referenced entry when a claim must be corrected or superseded.

```markdown
### [YYYY-MM-DD] Entry title

- **field_1**: value
- **field_2**: value
- ...
```

Each file's specific fields are listed in the table above. Common rules:
- Use Obsidian `[[wikilinks]]` for all evidence references.
- Claims and hypotheses must be falsifiable and specific.
- `confidence` in `patterns.md` is capped at `medium` — validated patterns belong in `insights.md`.
- Existing memory entries may only receive appended `occurrences` / `evidence` references and narrow lifecycle updates to `status` / `confidence`. These changes preserve the original claim and prior history.
- A promoted pattern's `status` value contains both the immutable promotion marker and the linked insight, for example `promoted ([YYYY-MM-DD]) → [[Workbench/memory/insights.md#heading]]`. A provisional insight records the reverse link in `source_pattern` when it is created.

---

## Insight Promotion Hierarchy

Knowledge is promoted upward through five levels as evidence accumulates.

```
Level 4  Domain Map           DomainMaps/{Name}.md
         Stable, integrated knowledge
              |  Researcher promotes when evidence sufficient
Level 3  Validated Insight    insights.md, status: validated
              |  >=1 new independent source after provisional creation; >=2 total
Level 2  Provisional Insight  insights.md, status: provisional
              |  Unpromoted pattern crosses from <3 to >=3 independent occurrences
Level 1  Pattern              patterns.md
              |  memory-distill extracts from logs
Level 0  Raw Log              Workbench/logs/
```

### Promotion Rules

| Transition | Trigger | Who |
|---|---|---|
| L0 -> L1 | `memory-distill` processes session logs and extracts recurring observations | Researcher (via skill) |
| L1 -> L2 | Pattern is unpromoted and has no linked insight, and either crosses from <3 to >=3 independent occurrences in the current run or is reconciled once as a legacy already-eligible but unmarked/unlinked pattern | Researcher (via skill) |
| L2 -> L3 | An insight that was already provisional before the current run receives at least one previously unrecorded independent evidence source, added after provisional creation, and has >=2 independent sources in total | Researcher (via skill) |
| L3 -> L4 | Researcher judges evidence sufficient for Domain Map integration. No numeric threshold — Researcher uses judgment. Logged to `evolution/changelog.md` | Researcher |

Promotion is staged and idempotent. L1 -> L2 writes a linked marker into the pattern `status` and a `source_pattern` back-reference into the new insight; either link makes the pattern ineligible for another L1 -> L2 promotion. Evidence used to create a provisional insight cannot validate it in the same run. A newly created provisional insight must wait for a later run that contributes new independent evidence.

---

## Update Rules

1. **Immutable records**: `Workbench/logs/` entries, experiment Run Entries, and `Workbench/evolution/changelog.md` entries are append-only. Never delete, reorder, or rewrite an earlier log, run, or changelog record.

2. **Memory mutation boundary**: Memory claims and history are never deleted or silently rewritten. New memory entries are appended. Within an existing entry, the only permitted in-place changes are appending `occurrences` / `evidence` references and narrowly updating `status` / `confidence` as evidence changes. Corrections to the claim itself require a new dated entry that links to the superseded entry.

3. **Promotion identity**: Before L1 -> L2, check both the pattern `status` marker and existing insight links. Never create a second insight for an already-promoted or already-linked pattern. A legacy pattern that began the run with >=3 independent occurrences may be promoted once only when it has neither marker nor linked insight; write both links during that reconciliation.

4. **Lifecycle logging**: Every promotion and every material lifecycle change—including a `status` transition or a material `confidence` change—must be appended to `Workbench/evolution/changelog.md`. L4 promotions use this format:

   ```markdown
   ### [YYYY-MM-DD] Domain Map updated: <map name>
   - **added**: <insight title>
   - **source**: [[Workbench/memory/insights.md#<heading>]]
   - **promoted_by**: <skill name or "human">
   ```

5. **Owner writes**: Owner may write directly to any memory file, but the same history-preservation boundary applies: append new claims or evidence and use explicit lifecycle updates rather than deleting or silently rewriting prior history.

6. **Conflict handling**: If a new insight contradicts an existing validated one, create a new `provisional` entry noting the contradiction. Do not modify the old claim or remove its history.
