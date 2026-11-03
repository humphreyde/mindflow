# Project Wrapper Inventory — 2026-11-03

## MindFlow primary checkout

- Path: `/Users/limx/mindflow`
- Branch: `main`
- HEAD: `095b8736fe413612d81a76a4d4ac43684d20a90f`
- Existing user-owned status at inspection:
  - modified `AGENTS.md`
  - modified `Workbench/agenda.md`
  - added `docs/superpowers/plans/2026-10-28-cross-repo-mindflow-context.md`
  - modified `skills/1-literature/daily-papers/config.json`

These paths are not modified or staged by the migration worktree.

## pi

- Canonical code root: `/Users/limx/project/pi`
- Wrapper target: `Projects/pi`
- Integration: absolute symlink `Projects/pi/code/pi -> /Users/limx/project/pi`
- Decision: preserve the canonical code path; do not move the repository.

## RLinf

- Canonical direct-root repository: `/Users/limx/mindflow/Projects/RLinf`
- Branch: `main`
- HEAD: `c50c60b475654a71533e9c5bacf13ef899a10104`
- Status at inspection: clean
- Decision: preserve in place and keep an Obsidian compatibility exclusion. Wrapper migration requires a separate approved path decision.
