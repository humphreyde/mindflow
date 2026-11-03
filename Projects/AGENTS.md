# Project Workspace Contract

## Wrapper layout

- Every `Projects/<workspace>/` is an independent notes Git repository.
- Track `AGENTS.md`, `CLAUDE.md -> AGENTS.md`, `main.md`, `engineering.md`, `experiments/`, and `discussions/`.
- Ignore `code/` and `worklog/` in the notes repository.

## Three note classes

- Research narrative is owner-facing: keep goals, hypotheses, results, insights, and decisions in `main.md`, `experiments/*.md`, and `discussions/`; put a TL;DR first and link downward instead of inlining engineering detail.
- Task records are agent/debugging drafts: keep one cross-repository narrative per task under ignored `worklog/<date>-<issue-id>.md`, including touched repositories/commits, failures, fixes, jobs, and discarded paths.
- Engineering conventions are pre-work reading: keep project-wide, cross-repository pipeline/environment conventions in `engineering.md`; keep repository-specific behavior in each code repository's own `AGENTS.md` and source documentation.

## Git boundaries

- The outer MindFlow repository, each wrapper notes repository, and every `code/<repo>` repository are independent Git roots with independent history, remotes, permissions, and commits.
- The outer repository tracks only this shared scaffold and ignores actual wrapper contents.
- The wrapper repository tracks research and engineering notes and ignores `code/` and `worklog/`.
- Initializing or committing a wrapper locally does not authorize creating a remote or pushing it.

## Convention scope

- Repository-only knowledge belongs in that code repository's `AGENTS.md` or linked documentation.
- Project-wide cross-repository knowledge belongs in wrapper `engineering.md`.
- Cross-project reusable workflows belong in an installed global skill only after separate review and authorization.

## Working discipline

- Read the wrapper `engineering.md` and every relevant code repository's `AGENTS.md` before source changes.
- Keep one worklog per task even when work crosses repositories.
- Periodically distill durable findings from disposable worklogs into the narrowest valid convention layer; move research findings into the research narrative and remove stale guidance.
- Keep the first roughly 30 lines of research notes sufficient for the main conclusions; push implementation detail downward.

## Agent discovery

- This file is a creation scaffold, not an automatic-inheritance guarantee across nested Git roots.
- Every wrapper and code repository must contain its own applicable `AGENTS.md`.
