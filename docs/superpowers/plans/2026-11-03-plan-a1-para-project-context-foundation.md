# Plan A1 PARA Project Context Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split stable repository identity from outcome-driven PARA Projects, add bounded project-wrapper retrieval, and provision the `pi` notes workspace without moving `/Users/limx/project/pi`.

**Architecture:** The tracked MindFlow branch owns schemas, validators, templates, shared `Projects/` instructions, and PARA control notes. A separate live-local lane owns ignored/nested state: `/Users/limx/mindflow/Projects/pi` is its own notes Git repository and `/Users/limx/mindflow/.obsidian/app.json` remains untracked. Repository profiles may point to a validated wrapper, but retrieval reads only `main.md`, `engineering.md`, and explicit Markdown entrypoints; it never recursively scans `code/`.

**Tech Stack:** Python 3.12 standard library, `unittest`, Markdown/YAML frontmatter, Git symlinks and nested repositories, Obsidian JSON, Quartz/Node focused regression tests.

**Spec:** `docs/superpowers/specs/2026-10-29-para-notes-migration-design.md`

## Global Constraints

- Keep `/Users/limx/project/pi` as the canonical code path; only create the absolute symlink `/Users/limx/mindflow/Projects/pi/code/pi -> /Users/limx/project/pi`.
- Do not move `/Users/limx/mindflow/Projects/RLinf` in this plan. It is a clean direct-root code repository discovered on 2026-11-03 and remains an explicit Obsidian compatibility exclusion until a separate path migration is approved.
- `Projects/<workspace>/` is an independent notes Git root. The outer MindFlow repository must ignore workspace contents and track only `Projects/AGENTS.md` plus `Projects/CLAUDE.md`.
- A repository profile is not a PARA Project. Do not create `Workbench/PARA/Projects/pi.md` without an explicit outcome and completion criteria.
- `workspace_root` must be a present, vault-relative, non-symlink `Projects/<workspace>` directory whose canonical path remains under the vault `Projects/` directory.
- `workspace_entrypoints` must be relative Markdown files inside the validated wrapper and must reject absolute paths, `..`, missing paths, directories, symlink escapes, and anything under `code/`, `worklog/`, or `.git/`.
- Quartz continues to exclude all `Projects/**`; do not run a full visual build. Run only the existing glob regression and TypeScript check when dependencies are usable.
- `.obsidian/` remains local-only. Preserve all unrelated keys in `app.json`; change only `userIgnoreFilters` in this plan.
- Do not merge, push, create remotes, or move `RLinf` without separate authorization. Local task commits inside the approved scope do not require per-commit confirmation.

---

### Task 1: Separate Repository Profiles From PARA Projects

**Files:**
- Modify: `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py`
- Modify: `skills/6-orchestration/mindflow-context/scripts/test_validate_profiles.py`
- Move: `Workbench/PARA/Projects/pi.md` -> `Workbench/RepositoryProfiles/pi.md`

**Interfaces:**
- Produces: `PROFILE_DIRECTORY = Path("Workbench/RepositoryProfiles")`
- Produces: `PROJECT_DIRECTORY = Path("Workbench/PARA/Projects")`
- Requires: profile frontmatter `type: repository-profile`
- Preserves: `parse_frontmatter(path)`, `load_profile(path, vault)`, and `validate_vault(vault)` call sites

- [ ] **Step 1: Write failing directory/type tests**

Add tests that create a valid profile only under `Workbench/RepositoryProfiles/`, require `type: repository-profile`, and prove that a note under `Workbench/PARA/Projects/` is not loaded as a repository profile.

```python
class ProfileSeparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.vault = Path(self.temporary_directory.name) / "vault"
        _prepare_fixture(self.vault)
        self.repo = Path(self.temporary_directory.name) / "repo"
        self.repo.mkdir()
        self.profile_path = _write_fixture_profile(
            self.vault, "pi.md", repo_root=str(self.repo)
        )

    def test_profiles_load_only_from_repository_profiles(self) -> None:
        legacy_directory = self.vault / "Workbench/PARA/Projects"
        legacy_directory.mkdir(parents=True, exist_ok=True)
        (legacy_directory / "legacy.md").write_text(
            "---\ntype: repository-profile\nrepo_key: legacy\n"
            f"repo_roots:\n  - {self.repo}\nverified_at: 2026-11-03\n---\n",
            encoding="utf-8",
        )
        profiles, errors = validate_vault(self.vault)
        self.assertEqual(errors, [])
        self.assertEqual([profile.repo_key for profile in profiles], ["pi"])

    def test_wrong_profile_type_is_rejected(self) -> None:
        wrong_path = _write_fixture_profile(
            self.vault,
            "wrong.md",
            repo_root=str(self.repo),
            profile_type="project",
        )
        profile, errors = load_profile(wrong_path, self.vault)
        self.assertIsNone(profile)
        self.assertIn("type must be 'repository-profile'", "\n".join(errors))
```

- [ ] **Step 2: Run the focused tests and confirm red**

Run:

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts \
  -p 'test_validate_profiles.py' -v
```

Expected: FAIL because fixtures and `validate_vault()` still use `Workbench/PARA/Projects` and profiles do not require `type`.

- [ ] **Step 3: Implement the directory and type split**

Add constants and require the explicit type without changing the deliberately small YAML parser.

```python
PROFILE_DIRECTORY = Path("Workbench/RepositoryProfiles")
PROJECT_DIRECTORY = Path("Workbench/PARA/Projects")
REPOSITORY_PROFILE_TYPE = "repository-profile"

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

This is the Task 1 shape only. Task 2 replaces it with the complete workspace-aware
shape shown there; no later task may construct `Profile` positionally.

Update `_write_fixture_profile(..., profile_type: str = "repository-profile")`
to emit the supplied type, with the canonical default:

```yaml
type: repository-profile
```

Update all profile-directory error messages to name `Workbench/RepositoryProfiles`.

In the same change, move the real `pi.md` profile and add `type: repository-profile`; keep its existing repo identity fields. Do not add `workspace_root` until the wrapper content task supplies the final profile body.

- [ ] **Step 4: Run regressions and self-test**

Run:

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
uv run --frozen python -B \
  skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault . --self-test
```

Expected: all tests pass and the self-test reports every case passed.

- [ ] **Step 5: Commit the profile split**

```bash
git add -A -- skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  skills/6-orchestration/mindflow-context/scripts/test_validate_profiles.py \
  Workbench/PARA/Projects/pi.md Workbench/RepositoryProfiles/pi.md
git commit -m "refactor: separate repository profiles from PARA projects"
```

---

### Task 2: Enforce Wrapper and Entrypoint Containment

**Files:**
- Modify: `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py`
- Create: `skills/6-orchestration/mindflow-context/scripts/test_validate_workspaces.py`

**Interfaces:**
- Produces: `resolve_workspace_root(vault: Path, value: str) -> Path`
- Produces: `resolve_workspace_entrypoint(workspace_root: Path, value: str) -> Path`
- Produces: `workspace_context_paths(profile: Profile) -> tuple[Path, ...]`
- Extends: `Profile.workspace_root: Path | None`
- Extends: `Profile.workspace_entrypoint_values: tuple[str, ...]`

The complete model after this task is:

```python
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
    workspace_root: Path | None
    workspace_entrypoint_values: tuple[str, ...]
```

`workspace_root` and `workspace_entrypoints` are optional frontmatter keys.
`workspace_entrypoints` is a YAML list of raw relative strings; a non-empty list
without `workspace_root` is invalid. `load_profile()` resolves `workspace_root`
with `resolve_workspace_root(vault, value)`, keeps the raw entrypoint strings in
`workspace_entrypoint_values`, and calls `workspace_context_paths()` before
returning a valid profile. Update the loader's optional/list-field tables and use
keyword construction for every `Profile` fixture.

- [ ] **Step 1: Write the workspace-root failure matrix**

Create table-driven tests for absolute paths, `..`, missing paths, files, wrong shapes, directory symlinks, and canonical escape.

```python
class WorkspaceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.vault = Path(self.temporary_directory.name) / "vault"
        self.workspace = self.vault / "Projects/pi"
        self.workspace.mkdir(parents=True)
        (self.workspace / "main.md").write_text("# Main\n", encoding="utf-8")
        (self.workspace / "engineering.md").write_text("# Engineering\n", encoding="utf-8")
        (self.workspace / "experiments").mkdir()
        (self.workspace / "experiments/approved.md").write_text("# Approved\n", encoding="utf-8")
        (self.workspace / "discussions").mkdir()
        (self.workspace / "discussions/unlisted.md").write_text("# Unlisted\n", encoding="utf-8")
        self.profile = Profile(
            path=self.vault / "Workbench/RepositoryProfiles/pi.md",
            repo_key="pi",
            repo_roots=(),
            aliases=(),
            domains=(),
            entrypoints=(),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=self.workspace.resolve(),
            workspace_entrypoint_values=("experiments/approved.md",),
        )

INVALID_ROOTS = (
    "/tmp/external",
    "Projects/../escape",
    "Missing/pi",
    "Projects/pi/main.md",
    "Other/pi",
)

def test_workspace_root_rejects_invalid_paths(self) -> None:
    for value in INVALID_ROOTS:
        with self.subTest(value=value):
            with self.assertRaises(ValueError):
                resolve_workspace_root(self.vault, value)
```

Add explicit symlink tests using a temporary directory; do not point fixtures at live `Projects/`.

- [ ] **Step 2: Write the entrypoint and no-recursion tests**

Cover absolute paths, `..`, missing files, non-Markdown files, directories, symlink escape, raw/canonical targets under forbidden directories, and an unrelated sibling Markdown file that must not appear in the context tuple.

```python
def test_context_is_fixed_defaults_plus_explicit_files(self) -> None:
    self.assertEqual(
        workspace_context_paths(self.profile),
        (
            self.workspace / "main.md",
            self.workspace / "engineering.md",
            self.workspace / "experiments/approved.md",
        ),
    )
    self.assertNotIn(self.workspace / "discussions/unlisted.md", workspace_context_paths(self.profile))

def test_default_main_symlink_escape_is_rejected(self) -> None:
    (self.workspace / "main.md").unlink()
    (self.workspace / "main.md").symlink_to(Path(self.temporary_directory.name) / "outside.md")
    with self.assertRaisesRegex(ValueError, "symlink|escapes"):
        workspace_context_paths(self.profile)

def test_missing_engineering_default_is_rejected(self) -> None:
    (self.workspace / "engineering.md").unlink()
    with self.assertRaisesRegex(ValueError, "does not exist"):
        workspace_context_paths(self.profile)

def test_entrypoints_require_workspace_root(self) -> None:
    profile_path = _write_fixture_profile(
        self.vault,
        "missing-root.md",
        repo_root=str(Path(self.temporary_directory.name) / "repo"),
        workspace_entrypoints=["experiments/approved.md"],
    )
    profile, errors = load_profile(profile_path, self.vault)
    self.assertIsNone(profile)
    self.assertIn("workspace_entrypoints requires workspace_root", "\n".join(errors))
```

- [ ] **Step 3: Run the new tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts \
  -p 'test_validate_workspaces.py' -v
```

Expected: import failures for the three new functions.

- [ ] **Step 4: Implement root and entrypoint resolvers**

Use raw-path checks before `resolve()` and canonical containment after it.

```python
FORBIDDEN_WORKSPACE_PARTS = {"code", "worklog", ".git"}

def resolve_workspace_root(vault: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or len(raw.parts) != 2 or raw.parts[0] != "Projects":
        raise ValueError("workspace_root must be Projects/<workspace>")
    resolved_vault = vault.resolve()
    projects_path = vault / "Projects"
    if projects_path.is_symlink():
        raise ValueError("Projects must not be a symlink")
    candidate = vault / raw
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("workspace_root must be an existing non-symlink directory")
    resolved = candidate.resolve()
    projects_root = projects_path.resolve()
    if not projects_root.is_relative_to(resolved_vault) or not resolved.is_relative_to(projects_root):
        raise ValueError("workspace_root escapes Projects")
    return resolved

def resolve_workspace_entrypoint(workspace_root: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or raw.suffix != ".md":
        raise ValueError("workspace entrypoint must be a relative Markdown file")
    if any(part in FORBIDDEN_WORKSPACE_PARTS for part in raw.parts):
        raise ValueError("workspace entrypoint enters a forbidden directory")
    candidate = workspace_root / raw
    if candidate.is_symlink():
        raise ValueError("workspace entrypoint must not be a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(workspace_root) or not resolved.is_file():
        raise ValueError("workspace entrypoint escapes or does not exist")
    relative = resolved.relative_to(workspace_root)
    if any(part in FORBIDDEN_WORKSPACE_PARTS for part in relative.parts):
        raise ValueError("workspace entrypoint resolves into a forbidden directory")
    return resolved

def workspace_context_paths(profile: Profile) -> tuple[Path, ...]:
    if profile.workspace_root is None:
        return ()
    values = ("main.md", "engineering.md", *profile.workspace_entrypoint_values)
    resolved = tuple(resolve_workspace_entrypoint(profile.workspace_root, value) for value in values)
    return tuple(dict.fromkeys(resolved))
```

Store the raw `workspace_entrypoints` strings as `Profile.workspace_entrypoint_values`; expose only validated paths through `workspace_context_paths()`.

- [ ] **Step 5: Run all context tests**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
```

Expected: PASS, including all filesystem-failure regressions.

- [ ] **Step 6: Commit bounded workspace resolution**

```bash
git add skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  skills/6-orchestration/mindflow-context/scripts/test_validate_workspaces.py
git commit -m "feat: validate project workspace boundaries"
```

---

### Task 3: Add Canonical Repository Matching

**Files:**
- Modify: `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py`
- Create: `skills/6-orchestration/mindflow-context/scripts/test_match_profiles.py`

**Interfaces:**
- Produces: `MatchResult` dataclass
- Produces: `match_profile(profiles: Sequence[Profile], repo_root: Path, repository_name: str | None = None) -> MatchResult`
- Extends CLI: optional `--repo-root PATH --json`

Use this exact result contract throughout Tasks 3–5:

```python
MatchStatus = Literal["matched", "ambiguous", "not_found", "invalid"]

@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    profile: Profile | None
    errors: tuple[str, ...]
```

- [ ] **Step 1: Write canonical-first matching tests**

Test that an original code path and a symlink path resolve to the same profile, ambiguity fails, and identity fallback runs only when canonical path matching returns no claimant.

```python
def test_original_and_symlink_paths_match_one_profile(self) -> None:
    original = match_profile(self.profiles, self.repo)
    linked = match_profile(self.profiles, self.repo_symlink)
    self.assertEqual(original.status, "matched")
    self.assertEqual(linked.status, "matched")
    self.assertEqual(original.errors + linked.errors, ())
    self.assertEqual(original.profile.repo_key, "pi")
    self.assertEqual(linked.profile.repo_key, "pi")
```

The test `setUp()` must create a real temporary repository directory, an absolute
symlink to it, and one complete keyword-constructed `Profile` whose `repo_roots`
contains the real directory. A second helper creates two complete profiles that
claim the same canonical root for the ambiguity case.

```python
class MatchProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.repo_symlink = root / "repo-link"
        self.repo_symlink.symlink_to(self.repo, target_is_directory=True)
        self.profiles = [self.make_profile("pi", (self.repo,))]

    def make_profile(
        self, key: str, roots: tuple[Path, ...], aliases: tuple[str, ...] = ()
    ) -> Profile:
        return Profile(
            path=Path("Workbench/RepositoryProfiles") / f"{key}.md",
            repo_key=key,
            repo_roots=roots,
            aliases=aliases,
            domains=(),
            entrypoints=(),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=None,
            workspace_entrypoint_values=(),
        )

    def ambiguous_profiles(self) -> list[Profile]:
        return [
            self.make_profile("pi-a", (self.repo,)),
            self.make_profile("pi-b", (self.repo_symlink,)),
        ]
```

- [ ] **Step 2: Write ambiguity and fallback tests**

```python
def test_duplicate_canonical_claim_is_ambiguous(self) -> None:
    result = match_profile(self.ambiguous_profiles(), self.repo)
    self.assertEqual(result.status, "ambiguous")
    self.assertIsNone(result.profile)
    self.assertEqual(len(result.errors), 1)

def test_identity_fallback_runs_only_without_root_claimant(self) -> None:
    other = Path(self.temporary_directory.name) / "other"
    other.mkdir()
    identity_profile = self.make_profile("identity", (other,), aliases=("openpi",))
    exact_profile = self.make_profile("exact", (self.repo,), aliases=("different",))
    result = match_profile(
        [identity_profile, exact_profile], self.repo, repository_name="openpi"
    )
    self.assertEqual(result.status, "matched")
    self.assertEqual(result.profile.repo_key, "exact")

def test_identity_fallback_is_casefolded(self) -> None:
    other = Path(self.temporary_directory.name) / "other"
    other.mkdir()
    profile = self.make_profile("pi", (other,), aliases=("OpenPI",))
    result = match_profile([profile], self.repo, repository_name="openpi")
    self.assertEqual(result.status, "matched")
    self.assertEqual(result.profile.repo_key, "pi")

def test_unknown_root_and_identity_is_not_found(self) -> None:
    result = match_profile(self.profiles, self.repo, repository_name="unknown")
    self.assertEqual(result.status, "matched")
    missing = match_profile(self.profiles, Path("/definitely/missing"), "unknown")
    self.assertEqual(missing.status, "not_found")
    self.assertIsNone(missing.profile)
```

- [ ] **Step 3: Run the new tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts \
  -p 'test_match_profiles.py' -v
```

Expected: import failure for `match_profile`.

- [ ] **Step 4: Implement canonical-first matching**

`match_profile()` canonicalizes `repo_root`, returns one exact root claimant, returns an ambiguity error for multiple claimants, and only then tries case-folded `repository_name`, `repo_key`, and aliases. `--json` prints exactly one object:

```json
{"status":"matched","profile_key":"pi","profile_path":"Workbench/RepositoryProfiles/pi.md","errors":[]}
```

Use `status: "ambiguous"` or `"not_found"` with a non-empty errors list and nonzero exit status for failure.

- [ ] **Step 5: Run tests and CLI fixtures**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
```

Expected: PASS. Do not point `--repo-root` at the live pi symlink until Task 9 provisions it.

- [ ] **Step 6: Commit matching and Project validation**

```bash
git add skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  skills/6-orchestration/mindflow-context/scripts/test_match_profiles.py
git commit -m "feat: resolve repository profiles canonically"
```

---

### Task 4: Validate PARA Projects, Areas, Resources, and Archives

**Files:**
- Modify: `skills/6-orchestration/mindflow-context/scripts/validate_profiles.py`
- Create: `skills/6-orchestration/mindflow-context/scripts/test_validate_projects.py`
- Create: `skills/6-orchestration/mindflow-context/scripts/test_validate_para_assets.py`

**Interfaces:**
- Produces: `Project` and `ArchivedProject` dataclasses
- Produces: `load_project(path, vault, profiles_by_key, areas_by_key)` and `load_archived_project(path, vault, profiles_by_key, areas_by_key)`
- Produces: `validate_projects(vault, profiles_by_key, areas_by_key) -> tuple[list[Project], list[ArchivedProject], list[str]]`
- Consumes: `workspace_context_paths(matched_profile: Profile) -> tuple[Path, ...]` from Task 2 for profile-owned wrapper defaults plus profile `workspace_entrypoints`
- Produces: `project_workspace_context_paths(project: Project) -> tuple[Path, ...]`; returns only the Project wrapper's `main.md` and `engineering.md`
- Produces: `Area`, `Resource`, `ArchivedArea`, and `ArchivedResource` dataclasses
- Produces: `load_area()`, `load_resource()`, `load_archived_area()`, and `load_archived_resource()`
- Produces: `validate_para_assets(vault: Path) -> tuple[list[Area], list[Resource], list[ArchivedArea], list[ArchivedResource], list[str]]`
- Produces: `validate_control_plane(vault: Path) -> ControlPlaneValidation`
- Produces: `ContextResult` dataclass
- Produces: `resolve_context(vault: Path, repo_root: Path, project_key: str | None = None) -> ContextResult`
- Extends CLI: explicit `--project-key KEY` and structured `--json` context output

```python
ContextStatus = Literal[
    "matched", "ambiguous", "not_found", "invalid", "project_selection_required"
]

@dataclass(frozen=True)
class ContextResult:
    status: ContextStatus
    profile_key: str | None
    project_key: str | None
    project_keys: tuple[str, ...]
    project_path: Path | None
    vault_entrypoints: tuple[Path, ...]
    workspace_context: tuple[Path, ...]
    project_workspace_context: tuple[Path, ...]
    project_knowledge_entrypoints: tuple[Path, ...]
    errors: tuple[str, ...]
```

`workspace_context` is always computed from the matched repository profile via
`workspace_context_paths(matched_profile)`; it contains that profile's wrapper
defaults and explicit `workspace_entrypoints`. `project_path` is only the selected
Project control-note path. `project_workspace_context` contains only wrapper
defaults resolved from `Project.workspace_root`, and
`project_knowledge_entrypoints` contains only validated
`Project.knowledge_entrypoints`. Never merge one channel into another.

Use these additional contracts:

```python
AREA_STATUSES = {"active", "paused"}
ARCHIVED_AREA_STATUS = "retired"
REVIEW_CADENCES = {"weekly", "monthly", "quarterly", "annual"}

@dataclass(frozen=True)
class Area:
    path: Path
    area_key: str
    owner: str
    responsibility: str
    standard: str
    status: str
    review_cadence: str
    last_reviewed: str | None
    domains: tuple[str, ...]

@dataclass(frozen=True)
class Resource:
    path: Path
    resource_key: str
    scope: str
    entrypoints: tuple[Path, ...]
    query: str | None
    review_cadence: str
    last_reviewed: str | None

@dataclass(frozen=True)
class ArchivedArea(Area):
    archived_at: str
    archive_reason: str
    final_outcome: str

@dataclass(frozen=True)
class ArchivedResource(Resource):
    archived_at: str
    archive_reason: str
    final_outcome: str

@dataclass(frozen=True)
class ControlPlaneValidation:
    profiles: tuple[Profile, ...]
    projects: tuple[Project, ...]
    archived_projects: tuple[ArchivedProject, ...]
    areas: tuple[Area, ...]
    resources: tuple[Resource, ...]
    archived_areas: tuple[ArchivedArea, ...]
    archived_resources: tuple[ArchivedResource, ...]
    errors: tuple[str, ...]
```

- [ ] **Step 1: Write complete active/archived fixtures and red tests**

The test `setUp()` creates `Workbench/RepositoryProfiles/pi.md`, a real `Projects/pi` wrapper with `main.md` and `engineering.md`, and an active Project note. Require `type`, `project_key`, non-empty `outcome`, non-empty `completion_criteria`, `status`, `target_date`, `workspace_root`, `repo_refs`, `area_refs`, and `knowledge_entrypoints`.

```python
PROJECT_STATUSES = {"planning", "active", "paused", "completed", "cancelled"}
ARCHIVED_PROJECT_STATUSES = {"completed", "cancelled"}

def test_same_repo_multiple_projects_requires_explicit_key(self) -> None:
    result = resolve_context(self.vault, repo_root=self.repo, project_key=None)
    self.assertEqual(result.status, "project_selection_required")
    self.assertEqual(result.project_keys, ("pi-recap", "pi-tron2"))

def test_single_project_still_requires_explicit_key(self) -> None:
    self.second_project_path.unlink()
    result = resolve_context(self.vault, repo_root=self.repo, project_key=None)
    self.assertEqual(result.status, "project_selection_required")
    self.assertEqual(result.project_keys, ("pi-recap",))
    self.assertIsNone(result.project_path)
    self.assertEqual(result.project_workspace_context, ())
    self.assertEqual(result.project_knowledge_entrypoints, ())

def test_profile_and_project_context_channels_stay_separate(self) -> None:
    result = resolve_context(
        self.vault, repo_root=self.repo, project_key="pi-recap"
    )
    self.assertEqual(result.status, "matched")
    self.assertEqual(result.project_keys, ("pi-recap", "pi-tron2"))
    self.assertEqual(result.project_path, self.first_project_path.resolve())
    self.assertEqual(result.vault_entrypoints, (self.domain_map.resolve(),))
    self.assertEqual(
        result.workspace_context,
        (
            self.workspace.resolve() / "main.md",
            self.workspace.resolve() / "engineering.md",
            self.workspace.resolve() / "experiments/profile-approved.md",
        ),
    )
    self.assertEqual(
        result.project_workspace_context,
        (
            self.workspace.resolve() / "main.md",
            self.workspace.resolve() / "engineering.md",
        ),
    )
    self.assertEqual(
        result.project_knowledge_entrypoints,
        ((self.vault / "Experiments/recap.md").resolve(),),
    )
    self.assertNotIn(
        self.workspace.resolve() / "experiments/profile-approved.md",
        result.project_workspace_context,
    )

def test_archived_project_requires_final_fields(self) -> None:
    archived, errors = load_archived_project(
        self.archive_path, self.vault, {"pi": self.profile}, self.areas_by_key
    )
    self.assertIsNone(archived)
    self.assertIn("missing required field 'final_outcome'", "\n".join(errors))

def test_archived_project_rejects_active_status(self) -> None:
    archived, errors = load_archived_project(
        self.write_archive(status="active"), self.vault,
        {"pi": self.profile}, self.areas_by_key
    )
    self.assertIsNone(archived)
    self.assertIn("archived status must be completed or cancelled", "\n".join(errors))
```

The fixture helper writes complete YAML using block lists and creates every
referenced file under the temporary vault. Add failures for an unknown `repo_ref`,
unknown `area_ref`, invalid status, escaping `knowledge_entrypoints`, missing `target_date` key, and
archive notes missing `archived_at`, `archive_reason`, `final_outcome`, or
`code_provenance`. Active Projects may use all `PROJECT_STATUSES`; notes loaded
from `Archives/Projects/` must use `ARCHIVED_PROJECT_STATUSES`.

```python
class ProjectValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.vault = root / "vault"
        self.repo = root / "repo"
        self.repo.mkdir()
        self.workspace = self.vault / "Projects/pi"
        self.workspace.mkdir(parents=True)
        (self.workspace / "main.md").write_text("# Main\n", encoding="utf-8")
        (self.workspace / "engineering.md").write_text("# Engineering\n", encoding="utf-8")
        (self.workspace / "experiments").mkdir()
        (self.workspace / "experiments/profile-approved.md").write_text(
            "# Profile approved\n", encoding="utf-8"
        )
        (self.vault / "Experiments").mkdir()
        (self.vault / "Experiments/recap.md").write_text("# RECAP\n", encoding="utf-8")
        (self.vault / "DomainMaps").mkdir()
        self.domain_map = self.vault / "DomainMaps/VLA.md"
        self.domain_map.write_text("# VLA\n", encoding="utf-8")
        self.profile = Profile(
            path=self.vault / "Workbench/RepositoryProfiles/pi.md",
            repo_key="pi",
            repo_roots=(self.repo,),
            aliases=(),
            domains=("VLA",),
            entrypoints=(self.domain_map.resolve(),),
            keywords=(),
            verified_at="2026-11-03",
            workspace_root=self.workspace.resolve(),
            workspace_entrypoint_values=("experiments/profile-approved.md",),
        )
        area_path = self.vault / "Workbench/PARA/Areas/Research.md"
        area_path.parent.mkdir(parents=True)
        area_path.write_text(
            "---\ntype: area\narea_key: research\nowner: hum\n"
            "responsibility: Maintain research\nstandard: Evidence first\n"
            "status: active\nreview_cadence: monthly\nlast_reviewed:\n"
            "domains: []\n---\n",
            encoding="utf-8",
        )
        self.areas_by_key = {
            "research": Area(
                path=area_path,
                area_key="research",
                owner="hum",
                responsibility="Maintain research",
                standard="Evidence first",
                status="active",
                review_cadence="monthly",
                last_reviewed=None,
                domains=(),
            )
        }
        self.first_project_path = self.write_project("pi-recap")
        self.second_project_path = self.write_project("pi-tron2")
        self.archive_path = self.write_archive(include_final_outcome=False)

    def write_project(self, key: str) -> Path:
        path = self.vault / f"Workbench/PARA/Projects/{key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\ntype: project\n"
            f"project_key: {key}\noutcome: Deliver {key}\n"
            "completion_criteria:\n  - Verified result\nstatus: active\n"
            "target_date:\nworkspace_root: Projects/pi\n"
            "repo_refs:\n  - pi\narea_refs: []\n"
            "knowledge_entrypoints:\n  - Experiments/recap.md\n---\n",
            encoding="utf-8",
        )
        return path

    def write_archive(
        self, *, status: str = "completed", include_final_outcome: bool = True
    ) -> Path:
        path = self.vault / "Workbench/PARA/Archives/Projects/pi-old.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        final = "final_outcome: Verified\n" if include_final_outcome else ""
        path.write_text(
            "---\ntype: project\nproject_key: pi-old\noutcome: Old result\n"
            "completion_criteria:\n  - Done\n"
            f"status: {status}\ntarget_date:\nworkspace_root: Projects/pi\n"
            "repo_refs:\n  - pi\narea_refs: []\nknowledge_entrypoints: []\n"
            "archived_at: 2026-11-03\narchive_reason: Finished\n"
            f"{final}code_provenance:\n  - pi@deadbeef\n---\n",
            encoding="utf-8",
        )
        return path

    def rewrite(self, path: Path, old: str, new: str) -> Path:
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(old, new), encoding="utf-8")
        return path
```

Add these exact matrix tests:

```python
def test_project_reference_and_path_failures(self) -> None:
    cases = (
        ("bad-repo", "repo_refs:\n  - pi", "repo_refs:\n  - missing", "unknown repo_ref"),
        ("bad-area", "area_refs: []", "area_refs:\n  - missing", "unknown area_ref"),
        ("bad-status", "status: active", "status: invented", "invalid status"),
        (
            "escape-entrypoint",
            "knowledge_entrypoints:\n  - Experiments/recap.md",
            "knowledge_entrypoints:\n  - ../outside.md",
            "entrypoint",
        ),
        ("missing-target", "target_date:\n", "", "missing required field 'target_date'"),
    )
    for key, old, new, expected in cases:
        with self.subTest(key=key):
            path = self.rewrite(self.write_project(key), old, new)
            project, errors = load_project(
                path, self.vault, {"pi": self.profile}, self.areas_by_key
            )
            self.assertIsNone(project)
            self.assertIn(expected, "\n".join(errors))

def test_every_archived_project_final_field_is_required(self) -> None:
    removals = {
        "archived_at": "archived_at: 2026-11-03\n",
        "archive_reason": "archive_reason: Finished\n",
        "final_outcome": "final_outcome: Verified\n",
        "code_provenance": "code_provenance:\n  - pi@deadbeef\n",
    }
    for field, fragment in removals.items():
        with self.subTest(field=field):
            path = self.rewrite(self.write_archive(), fragment, "")
            archived, errors = load_archived_project(
                path, self.vault, {"pi": self.profile}, self.areas_by_key
            )
            self.assertIsNone(archived)
            self.assertIn(f"missing required field '{field}'", "\n".join(errors))
```

- [ ] **Step 2: Write Area, Resource, and typed-archive failure tests**

```python
class ParaAssetValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.vault = Path(self.temporary_directory.name) / "vault"
        (self.vault / "DomainMaps").mkdir(parents=True)
        (self.vault / "DomainMaps/VLA.md").write_text("# VLA\n", encoding="utf-8")

    def write_note(self, relative: str, frontmatter: str) -> Path:
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\n{frontmatter}---\n", encoding="utf-8")
        return path

    def write_mapping(self, relative: str, data: dict[str, object]) -> Path:
        lines = ["---"]
        for key, value in data.items():
            if isinstance(value, list):
                if value:
                    lines.append(f"{key}:")
                    lines.extend(f"  - {item}" for item in value)
                else:
                    lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:" if value is None else f"{key}: {value}")
        lines.append("---")
        path = self.vault / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_valid_area_and_resource_load(self) -> None:
        area_path = self.write_note(
            "Workbench/PARA/Areas/Research.md",
            "type: area\narea_key: research\nowner: hum\n"
            "responsibility: Maintain research quality\nstandard: Evidence first\n"
            "status: active\nreview_cadence: monthly\nlast_reviewed:\n"
            "domains:\n  - VLA\n",
        )
        resource_path = self.write_note(
            "Workbench/PARA/Resources/VLA.md",
            "type: resource\nresource_key: vla\nscope: VLA knowledge\n"
            "entrypoints:\n  - DomainMaps/VLA.md\nquery:\n"
            "review_cadence: quarterly\nlast_reviewed:\n",
        )
        self.assertEqual(load_area(area_path, self.vault)[1], [])
        self.assertEqual(load_resource(resource_path, self.vault)[1], [])

    def test_resource_entrypoint_escape_is_rejected(self) -> None:
        path = self.write_note(
            "Workbench/PARA/Resources/escape.md",
            "type: resource\nresource_key: escape\nscope: Invalid\n"
            "entrypoints:\n  - ../outside.md\nquery:\n"
            "review_cadence: quarterly\nlast_reviewed:\n",
        )
        resource, errors = load_resource(path, self.vault)
        self.assertIsNone(resource)
        self.assertIn("entrypoint", "\n".join(errors))

    def test_archived_area_requires_retired_and_archive_fields(self) -> None:
        path = self.write_note(
            "Workbench/PARA/Archives/Areas/Research.md",
            "type: area\narea_key: research\nowner: hum\n"
            "responsibility: Old responsibility\nstandard: Evidence first\n"
            "status: active\nreview_cadence: monthly\nlast_reviewed:\n"
            "domains: []\narchived_at: 2026-11-03\narchive_reason: Retired\n",
        )
        area, errors = load_archived_area(path, self.vault)
        self.assertIsNone(area)
        self.assertIn("status must be retired", "\n".join(errors))
        self.assertIn("missing required field 'final_outcome'", "\n".join(errors))
```

Add these exact table-driven matrices using `write_mapping()`:

```python
VALID_AREA = {
    "type": "area", "area_key": "research", "owner": "hum",
    "responsibility": "Maintain research", "standard": "Evidence first",
    "status": "active", "review_cadence": "monthly", "last_reviewed": None,
    "domains": [],
}
VALID_RESOURCE = {
    "type": "resource", "resource_key": "vla", "scope": "VLA knowledge",
    "entrypoints": ["DomainMaps/VLA.md"], "query": None,
    "review_cadence": "quarterly", "last_reviewed": None,
}

def test_every_required_area_and_resource_field_is_enforced(self) -> None:
    for prefix, valid, loader in (
        ("area", VALID_AREA, load_area),
        ("resource", VALID_RESOURCE, load_resource),
    ):
        for field in valid:
            with self.subTest(prefix=prefix, field=field):
                data = dict(valid)
                data.pop(field)
                path = self.write_mapping(
                    f"Workbench/PARA/{'Areas' if prefix == 'area' else 'Resources'}/{field}.md",
                    data,
                )
                loaded, errors = loader(path, self.vault)
                self.assertIsNone(loaded)
                self.assertIn(f"missing required field '{field}'", "\n".join(errors))

def test_area_value_failures(self) -> None:
    cases = (
        ("type", "project", "type must be 'area'"),
        ("area_key", "Not Valid", "lowercase kebab-case"),
        ("responsibility", "", "responsibility must be non-empty"),
        ("standard", "", "standard must be non-empty"),
        ("status", "retired", "invalid area status"),
        ("review_cadence", "sometimes", "invalid review cadence"),
        ("last_reviewed", "03/11/2026", "ISO date"),
    )
    for field, value, expected in cases:
        data = dict(VALID_AREA)
        data[field] = value
        loaded, errors = load_area(
            self.write_mapping(f"Workbench/PARA/Areas/bad-{field}.md", data), self.vault
        )
        self.assertIsNone(loaded)
        self.assertIn(expected, "\n".join(errors))

def test_resource_value_and_entrypoint_failures(self) -> None:
    cases = (
        ({"type": "area"}, "type must be 'resource'"),
        ({"resource_key": "Not Valid"}, "lowercase kebab-case"),
        ({"scope": ""}, "scope must be non-empty"),
        ({"review_cadence": "sometimes"}, "invalid review cadence"),
        ({"last_reviewed": "03/11/2026"}, "ISO date"),
        ({"entrypoints": [], "query": None}, "entrypoint or query"),
        ({"entrypoints": ["/absolute.md"]}, "entrypoint"),
        ({"entrypoints": ["../outside.md"]}, "entrypoint"),
        ({"entrypoints": ["DomainMaps/missing.md"]}, "does not exist"),
        ({"entrypoints": ["DomainMaps"]}, "must be a file"),
    )
    for index, (changes, expected) in enumerate(cases):
        data = dict(VALID_RESOURCE)
        data.update(changes)
        loaded, errors = load_resource(
            self.write_mapping(f"Workbench/PARA/Resources/bad-{index}.md", data),
            self.vault,
        )
        self.assertIsNone(loaded)
        self.assertIn(expected, "\n".join(errors))

def test_archive_fields_are_required_for_area_and_resource(self) -> None:
    for kind, valid, loader, directory in (
        ("area", {**VALID_AREA, "status": "retired"}, load_archived_area, "Areas"),
        ("resource", VALID_RESOURCE, load_archived_resource, "Resources"),
    ):
        complete = {
            **valid,
            "archived_at": "2026-11-03",
            "archive_reason": "Retired",
            "final_outcome": "Captured",
        }
        for field in ("archived_at", "archive_reason", "final_outcome"):
            data = dict(complete)
            data.pop(field)
            loaded, errors = loader(
                self.write_mapping(
                    f"Workbench/PARA/Archives/{directory}/{kind}-{field}.md", data
                ),
                self.vault,
            )
            self.assertIsNone(loaded)
            self.assertIn(f"missing required field '{field}'", "\n".join(errors))
```

```python
def test_resource_symlink_escape_is_rejected(self) -> None:
    outside = Path(self.temporary_directory.name) / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    link = self.vault / "DomainMaps/link.md"
    link.symlink_to(outside)
    data = {**VALID_RESOURCE, "entrypoints": ["DomainMaps/link.md"]}
    resource, errors = load_resource(
        self.write_mapping("Workbench/PARA/Resources/symlink.md", data), self.vault
    )
    self.assertIsNone(resource)
    self.assertIn("escapes the vault", "\n".join(errors))
```

- [ ] **Step 3: Run Project and PARA-asset tests and confirm red**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts \
  -p 'test_validate_*.py' -v
```

- [ ] **Step 4: Implement all typed PARA models and validators**

```python
@dataclass(frozen=True)
class Project:
    path: Path
    project_key: str
    outcome: str
    completion_criteria: tuple[str, ...]
    status: str
    target_date: str | None
    workspace_root: Path
    repo_refs: tuple[str, ...]
    area_refs: tuple[str, ...]
    knowledge_entrypoints: tuple[Path, ...]

@dataclass(frozen=True)
class ArchivedProject(Project):
    archived_at: str
    archive_reason: str
    final_outcome: str
    code_provenance: tuple[str, ...]

def project_workspace_context_paths(project: Project) -> tuple[Path, ...]:
    return tuple(
        resolve_workspace_entrypoint(project.workspace_root, value)
        for value in ("main.md", "engineering.md")
    )
```

Resolve `knowledge_entrypoints` with the existing vault-entrypoint resolver.
`project_workspace_context_paths()` resolves only the two defaults through
`resolve_workspace_entrypoint()` so they cannot bypass containment. It never
reads a repository profile and therefore never appends profile
`workspace_entrypoints`. Scan active and archived directories separately;
validation never moves notes.

For Area and Resource keys, require lowercase kebab-case. Require all schema keys
to be present; blank `last_reviewed` and `query` become `None`, while
responsibility, standard, scope, owner, and archive fields are non-empty. Parse
all nonblank dates with `date.fromisoformat()`. Resolve Resource entrypoints with
the existing vault-relative containment resolver; reject paths that are absolute,
contain `..`, escape via symlink, are missing, or are directories. A Resource must
have at least one resolved entrypoint or a non-empty query. Scan
`Areas/`/`Resources/` and `Archives/Areas/`/`Archives/Resources/` separately;
active loaders reject archive-only fields, archived Areas require
`status: retired`, and validators never move notes.

Load Areas before Projects and require every non-empty `area_refs` value to match
one active Area key. Archived Areas do not satisfy an active Project reference.
Directory scanners consider only `*.md` control notes, exclude the intentional
`Workbench/PARA/Resources/_index.md`, and ignore `.gitkeep` and `.base` files;
they do not silently skip any other Markdown file in a typed control directory.
Keep `validate_vault()` backward-compatible as the repository-profile loader, but
make the CLI's default `--vault` validation aggregate profile, Project, Area,
Resource, and all typed-archive errors before returning its exit status.

Use this exact aggregation order so Project references never trigger a second,
inconsistent Area scan:

```python
def validate_control_plane(vault: Path) -> ControlPlaneValidation:
    profiles, profile_errors = validate_vault(vault)
    areas, resources, archived_areas, archived_resources, asset_errors = (
        validate_para_assets(vault)
    )
    profiles_by_key = {profile.repo_key: profile for profile in profiles}
    areas_by_key = {area.area_key: area for area in areas}
    projects, archived_projects, project_errors = validate_projects(
        vault, profiles_by_key, areas_by_key
    )
    errors = tuple(dict.fromkeys((*profile_errors, *asset_errors, *project_errors)))
    return ControlPlaneValidation(
        profiles=tuple(profiles),
        projects=tuple(projects),
        archived_projects=tuple(archived_projects),
        areas=tuple(areas),
        resources=tuple(resources),
        archived_areas=tuple(archived_areas),
        archived_resources=tuple(archived_resources),
        errors=errors,
    )
```

Each loader calls `parse_frontmatter()` once, validates type/required fields and
values, then constructs its frozen dataclass only when its local error list is
empty. Each scanner sorts paths, loads every eligible file exactly once, detects
duplicate keys, and returns objects plus path-qualified errors without mutating
the vault.

Do not implement a combined Project-context helper: a `Project` does not contain
the matched `Profile` and therefore cannot own profile `workspace_entrypoints`.
Keep the selected control note as `project.path`, profile
wrapper files as `workspace_context_paths(matched_profile)`, Project wrapper
defaults as `project_workspace_context_paths(project)`, and Project knowledge as
`project.knowledge_entrypoints`.

- [ ] **Step 5: Implement explicit project selection and JSON context output**

`--project-key` is the only way to select an outcome Project. When present, verify its `repo_refs` includes the matched profile. Emit:

Populate the channels without cross-merging:

```python
profile_workspace = workspace_context_paths(matched_profile)
project_keys = tuple(sorted(project.project_key for project in matching_projects))
if selected_project is None:
    project_path = None
    project_workspace = ()
    project_knowledge = ()
else:
    project_path = selected_project.path
    project_workspace = project_workspace_context_paths(selected_project)
    project_knowledge = selected_project.knowledge_entrypoints

result = ContextResult(
    status="matched",
    profile_key=matched_profile.repo_key,
    project_key=(
        selected_project.project_key if selected_project is not None else None
    ),
    project_keys=project_keys,
    project_path=project_path,
    vault_entrypoints=matched_profile.entrypoints,
    workspace_context=profile_workspace,
    project_workspace_context=project_workspace,
    project_knowledge_entrypoints=project_knowledge,
    errors=(),
)
```

`project_keys` is always the sorted tuple of active Project keys whose
`repo_refs` contain the matched profile, whether or not one key is explicitly
selected. Emit:

```json
{
  "status": "matched",
  "profile_key": "pi",
  "project_key": "pi-recap",
  "project_keys": ["pi-recap", "pi-tron2"],
  "project_path": "Workbench/PARA/Projects/pi-recap.md",
  "vault_entrypoints": ["DomainMaps/VLA.md"],
  "workspace_context": [
    "Projects/pi/main.md",
    "Projects/pi/engineering.md",
    "Projects/pi/experiments/profile-approved.md"
  ],
  "project_workspace_context": [
    "Projects/pi/main.md",
    "Projects/pi/engineering.md"
  ],
  "project_knowledge_entrypoints": ["Experiments/recap.md"],
  "errors": []
}
```

Failure statuses are `not_found`, `ambiguous`, `invalid`, and `project_selection_required`.

- [ ] **Step 6: Run all context tests**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
```

- [ ] **Step 7: Commit full PARA validation**

```bash
git add -- skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  skills/6-orchestration/mindflow-context/scripts/test_validate_projects.py \
  skills/6-orchestration/mindflow-context/scripts/test_validate_para_assets.py
git commit -m "feat: validate PARA control-plane contracts"
```

---

### Task 5: Update the MindFlow Context Contract and Smoke Matrix

**Files:**
- Modify: `skills/6-orchestration/mindflow-context/SKILL.md`
- Modify: `skills/6-orchestration/mindflow-context/references/smoke-tests.md`

**Interfaces:**
- Consumes: structured JSON from `validate_profiles.py --repo-root ... [--project-key ...] --json`
- Produces: documented profile/project selection, bounded read order, and behavior cases

- [ ] **Step 1: Update profile selection and bounded wrapper retrieval**

Replace the old `Workbench/PARA/Projects/*.md` profile lookup with `Workbench/RepositoryProfiles/*.md`. Require the validator's structured result before reading wrapper notes. State that a selected profile reads vault `entrypoints` from vault root and wrapper `workspace_entrypoints` from the validated `workspace_root`; defaults are `main.md` and `engineering.md`; directories and `code/` are never recursively scanned. A PARA Project is selected only by explicit `project_key`; if the CLI returns `project_selection_required`, the skill reports the candidate keys instead of guessing.

For an explicit Project selection, consume `project_path` as one control note,
`project_workspace_context` as defaults-only wrapper files, and
`project_knowledge_entrypoints` as vault-root knowledge files. Keep all three
separate from the profile's `workspace_context`; never append profile explicit
workspace files to the Project workspace channel.

Preserve the trigger boundary verbatim: research, architecture, experiment design,
method selection, paper-to-code mapping, historical-decision work, or an explicit
MindFlow request determines whether retrieval runs. Profile matching and
`Projects/` membership only select project retrieval versus generic fallback;
being inside a repository never triggers research retrieval by itself.

- [ ] **Step 2: Add smoke cases for symlink matching and escape rejection**

Add:

```text
Case 11: invoke from /Users/limx/mindflow/Projects/pi/code/pi; selected profile must equal the /Users/limx/project/pi result.
Case 12: fixture workspace_entrypoint points through a symlink outside the wrapper; validation must fail before reading the target.
Case 13: two active Projects reference pi and no project key is supplied; report both keys and read neither Project note.
Case 14: explicit project key selects one Project; JSON keeps `project_path`, profile `workspace_context`, defaults-only `project_workspace_context`, `project_knowledge_entrypoints`, and vault entrypoints separate; profile explicit workspace files never appear in the Project workspace channel.
Case 15: an ordinary local test fix inside a profiled repository does not trigger MindFlow retrieval.
```

Update existing Case 1/4 expected profile path to `Workbench/RepositoryProfiles/pi.md`.

- [ ] **Step 3: Validate the skill package and references**

```bash
uv run --frozen python \
  /Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/6-orchestration/mindflow-context
if rg -n 'Workbench/PARA/Projects/.+profile|scan.*code' \
  skills/6-orchestration/mindflow-context; then exit 1; fi
```

Expected: skill validation succeeds; the search returns no stale profile-directory instruction or permission to scan code recursively.

- [ ] **Step 4: Commit the contract update**

```bash
git add skills/6-orchestration/mindflow-context/SKILL.md \
  skills/6-orchestration/mindflow-context/references/smoke-tests.md
git commit -m "docs: define bounded project context retrieval"
```

---

### Task 6: Establish the Tracked PARA Control Plane

**Files:**
- Modify: `Workbench/RepositoryProfiles/pi.md`
- Create: `Workbench/PARA/_index.md`
- Create: `Workbench/PARA/Projects/.gitkeep`
- Create: `Workbench/PARA/Areas/Research.md`
- Create: `Workbench/PARA/Areas/Knowledge-System.md`
- Create: `Workbench/PARA/Resources/_index.md`
- Create: `Workbench/PARA/Archives/Projects/.gitkeep`
- Create: `Workbench/PARA/Archives/Areas/.gitkeep`
- Create: `Workbench/PARA/Archives/Resources/.gitkeep`
- Create: `Templates/RepositoryProfile.md`
- Create: `Templates/ArchivedProject.md`
- Create: `Templates/Area.md`
- Create: `Templates/ArchivedArea.md`
- Create: `Templates/Resource.md`
- Create: `Templates/ArchivedResource.md`
- Modify: `Templates/Project.md`

**Interfaces:**
- Produces: canonical `pi` repository profile with `workspace_root: Projects/pi`
- Produces: empty outcome-driven Projects control directory; no fake `pi` Project note
- Produces: active/archive lifecycle templates and initial Areas/Resources index

- [ ] **Step 1: Finalize the migrated pi profile**

Use block lists because the existing parser intentionally rejects non-empty inline collections.

```yaml
---
type: repository-profile
title: OpenPI
repo_key: pi
repo_roots:
  - /Users/limx/project/pi
workspace_root: Projects/pi
workspace_entrypoints: []
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
verified_at: 2026-11-03
---
```

Keep the note's provenance statement, but remove Project status, TODOs, and outcome-like sections.

- [ ] **Step 2: Create PARA templates and initial notes**

Use these exact frontmatter contracts:

```yaml
# Templates/RepositoryProfile.md
---
type: repository-profile
title:
repo_key:
repo_roots: []
workspace_root:
workspace_entrypoints: []
aliases: []
domains: []
entrypoints: []
keywords: []
verified_at:
---

# Templates/Project.md
---
type: project
project_key:
outcome:
completion_criteria: []
status: planning
target_date:
workspace_root:
repo_refs: []
area_refs: []
knowledge_entrypoints: []
---

# Templates/ArchivedProject.md
---
type: project
project_key:
outcome:
completion_criteria: []
status: completed
target_date:
workspace_root:
repo_refs: []
area_refs: []
knowledge_entrypoints: []
archived_at:
archive_reason:
final_outcome:
code_provenance: []
---

# Templates/Area.md
---
type: area
area_key:
owner: hum
responsibility:
standard:
status: active
review_cadence: monthly
last_reviewed:
domains: []
---

# Templates/ArchivedArea.md
---
type: area
area_key:
owner: hum
responsibility:
standard:
status: retired
review_cadence: monthly
last_reviewed:
domains: []
archived_at:
archive_reason:
final_outcome:
---

# Templates/Resource.md
---
type: resource
resource_key:
scope:
entrypoints: []
query:
review_cadence: quarterly
last_reviewed:
---

# Templates/ArchivedResource.md
---
type: resource
resource_key:
scope:
entrypoints: []
query:
review_cadence: quarterly
last_reviewed:
archived_at:
archive_reason:
final_outcome:
---
```

`RepositoryProfile.md` body headings are `Purpose`, `Canonical Repositories`,
`Knowledge Entrypoints`, and `Provenance`. The active Project body headings are
`Outcome`, `Completion Criteria`, `Repository References`, `Knowledge
Entrypoints`, `Progress`, and `Finalization`. `ArchivedProject.md` contains all
active headings plus `Final Outcome`, `Code Provenance`, and `Archive Rationale`.
`Area.md` and `ArchivedArea.md` use `Purpose`, `Standards`, `Active Projects`,
`Knowledge Entrypoints`, and `Review Notes`; the archived form adds `Final
Outcome` and `Archive Rationale`. `Resource.md` and `ArchivedResource.md` use
`Scope`, `Entrypoints`, `Query`, and `Review Notes`; the archived form adds `Final
Outcome` and `Archive Rationale`.

Create `Research.md` with `area_key: research`, owner `hum`, responsibility
`Maintain a high-impact, evidence-driven research program`, standard `Claims are
source-backed; hypotheses are labeled; Projects have explicit completion
criteria`, status `active`, cadence `monthly`, `last_reviewed: 2026-11-03`, empty
domains, and `[[DomainMaps/_index|Domain Maps]]` under Knowledge Entrypoints.
Create `Knowledge-System.md` with `area_key: knowledge-system`, owner `hum`,
responsibility `Maintain MindFlow retrieval, schema, provenance, and review
quality`, standard `Retrieval boundaries, schemas, and provenance are validated
before use`, status `active`, cadence `monthly`, `last_reviewed: 2026-11-03`, empty
domains, and the literal paths `Workbench/PARA/_index.md`, `references/`, and
`Templates/` under Knowledge Entrypoints. Both notes use the fixed body headings
`Purpose`, `Standards`, `Active Projects`, `Knowledge Entrypoints`, and `Review
Notes`; neither invents deadlines, experiments, or project outcomes.

Their complete frontmatter is:

```yaml
# Workbench/PARA/Areas/Research.md
---
type: area
area_key: research
owner: hum
responsibility: Maintain a high-impact, evidence-driven research program
standard: Claims are source-backed; hypotheses are labeled; Projects have explicit completion criteria
status: active
review_cadence: monthly
last_reviewed: 2026-11-03
domains: []
---

# Workbench/PARA/Areas/Knowledge-System.md
---
type: area
area_key: knowledge-system
owner: hum
responsibility: Maintain MindFlow retrieval, schema, provenance, and review quality
standard: Retrieval boundaries, schemas, and provenance are validated before use
status: active
review_cadence: monthly
last_reviewed: 2026-11-03
domains: []
---
```

Write `Workbench/PARA/_index.md` exactly with heading `PARA`, then sections
`Projects`, `Areas`, `Resources`, and `Archives`. `Projects` states that active
outcome notes live in `Workbench/PARA/Projects/` and that wrapper existence does
not create a Project. `Areas` links `[[Areas/Research|Research]]` and
`[[Areas/Knowledge-System|Knowledge System]]`. `Resources` links
`[[Resources/_index|Resource Index]]`. `Archives` lists the three typed archive
directories and states that archive moves never move profiles, code, or knowledge
assets.

Write `Workbench/PARA/Resources/_index.md` with heading `Resources`, a `Knowledge
substrate` table whose rows are the literal vault paths `Papers/`, `Topics/`,
`DomainMaps/`, `Ideas/`, and `Experiments/`, and a `System boundaries` section.
The latter states: MindFlow owns interpretation/classification; official sources
own paper facts; Zotero owns local membership/item keys/attachments; no content or
collection tree is copied into this index. Link the Papers row to
`[[Papers.base|Papers Base]]` and the DomainMaps row to
`[[DomainMaps/_index|Domain Maps]]`.

- [ ] **Step 3: Run profile and lifecycle checks**

Before Task 9, the worktree-local live profile check is expected to report missing `Projects/pi`; unit fixtures must pass. Verify all other invariants now:

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
test ! -e Workbench/PARA/Projects/pi.md
test -f Workbench/RepositoryProfiles/pi.md
```

Expected: tests pass and the old mixed note is gone.

- [ ] **Step 4: Commit the PARA control plane**

```bash
git add -- Workbench/RepositoryProfiles/pi.md \
  Workbench/PARA/_index.md Workbench/PARA/Projects/.gitkeep \
  Workbench/PARA/Areas/Research.md Workbench/PARA/Areas/Knowledge-System.md \
  Workbench/PARA/Resources/_index.md \
  Workbench/PARA/Archives/Projects/.gitkeep \
  Workbench/PARA/Archives/Areas/.gitkeep \
  Workbench/PARA/Archives/Resources/.gitkeep \
  Templates/RepositoryProfile.md Templates/ArchivedProject.md \
  Templates/Area.md Templates/ArchivedArea.md \
  Templates/Resource.md Templates/ArchivedResource.md Templates/Project.md
git commit -m "feat: establish PARA control plane"
```

---

### Task 7: Record Live Drift and Update Tracked Documentation

**Files:**
- Create: `Workbench/migrations/2026-11-03-project-wrapper-inventory.md`
- Modify: `README.md`
- Modify: `docs/SPEC.md`
- Modify: `docs/INSTALL.md`

**Interfaces:**
- Produces: dated, evidence-backed pi/RLinf inventory
- Produces: documentation that distinguishes wrappers, profiles, PARA Projects, and local Obsidian settings

- [ ] **Step 1: Record the exact live wrapper inventory**

Include these decisions plus current branch/HEAD/status evidence:

```markdown
- pi: canonical code root `/Users/limx/project/pi`; wrapper target `Projects/pi`; action `absolute symlink`, no code move.
- RLinf: canonical direct-root `/Users/limx/mindflow/Projects/RLinf`; action `preserve`; Obsidian compatibility exclusion required; migration deferred to a separately approved path decision.
```

Do not include credentials, remote tokens, or mutable runtime logs.

- [ ] **Step 2: Update README, SPEC, and INSTALL additively**

Add these exact contracts while preserving unrelated owner/research customizations:

- `README.md`, section `Workspace model`: repository identity lives in
  `Workbench/RepositoryProfiles/`; a PARA Project exists only for an explicit
  outcome/completion criterion; each `Projects/<workspace>/` is an independent
  notes repository and code lives under `code/<repo>`; typed assets such as
  `Papers/` remain at the vault root.
- `docs/SPEC.md`, section `Project context`: define vault `entrypoints` versus
  wrapper `workspace_entrypoints`, the `main.md`/`engineering.md` defaults, the
  forbidden `code/worklog/.git` paths, and the no-recursive-code rule. Document
  the structured output lanes exactly: profile `workspace_context`; selected
  `project_path`; defaults-only `project_workspace_context`; and
  `project_knowledge_entrypoints`. Profile explicit workspace files never enter
  the Project workspace lane.
- `docs/INSTALL.md`, section `Local Obsidian setup`: verify
  `.obsidian/templates.json` points to `Templates`; explain that
  `.obsidian/app.json` is local-only and uses narrow wrapper filters; show
  `Projects/pi/code/pi -> /Users/limx/project/pi` as a symlink example, not a move.
- All three documents point canonical Paper generation to
  `skills/1-literature/paper-digest/references/paper-note-template.md` and never to
  `Templates/Paper.md`.

Remove claims that `Projects/` contains only direct code roots or that repository
profiles live under `PARA/Projects`.

- [ ] **Step 3: Assert stale claims are absent**

```bash
if rg -n 'Templates/Paper\.md|PARA/Projects/.+profile|Projects/.+direct code|代码仓库根' \
  README.md docs/SPEC.md docs/INSTALL.md; then exit 1; fi
git diff --check -- README.md docs/SPEC.md docs/INSTALL.md \
  Workbench/migrations/2026-11-03-project-wrapper-inventory.md
```

- [ ] **Step 4: Commit only the documentation paths**

```bash
git add -- Workbench/migrations/2026-11-03-project-wrapper-inventory.md \
  README.md docs/SPEC.md docs/INSTALL.md
git diff --cached --check
git commit -m "docs: record PARA workspace architecture"
```

---

### Task 8: Make Shared Project Instructions Codex-First

**Files:**
- Modify: `.gitignore`
- Create: `Projects/AGENTS.md`
- Replace: `Projects/CLAUDE.md` regular file -> relative symlink to `AGENTS.md`

**Interfaces:**
- Produces: tracked shared scaffold at `Projects/AGENTS.md`
- Preserves: outer ignore for every actual workspace directory

- [ ] **Step 1: Add the narrow outer ignore exception**

Keep `Projects/*` and add only:

```gitignore
!Projects/AGENTS.md
!Projects/CLAUDE.md
```

- [ ] **Step 2: Create Codex-first shared instructions**

Create `Projects/AGENTS.md` with these normative sections and rules:

```markdown
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
```

This preserves the existing three note classes, three Git layers, convention
scope ladder, cross-repository task-log rule, distillation discipline, and
top-heavy research-note convention. The only removed claim is that an outer
`Projects/CLAUDE.md` is automatically inherited inside nested repositories; the
explicit `AGENTS.md` requirement replaces it.

- [ ] **Step 3: Replace the compatibility file with a relative symlink**

```bash
rm Projects/CLAUDE.md
ln -s AGENTS.md Projects/CLAUDE.md
```

The removal is limited to the tracked compatibility file and is recoverable from Git.

- [ ] **Step 4: Verify modes and ignore behavior**

```bash
! git check-ignore -q Projects/AGENTS.md
! git check-ignore -q Projects/CLAUDE.md
git check-ignore -q Projects/pi/main.md
test -L Projects/CLAUDE.md
test "$(readlink Projects/CLAUDE.md)" = "AGENTS.md"
```

After staging, verify the symlink mode is `120000`:

```bash
git add -- .gitignore Projects/AGENTS.md Projects/CLAUDE.md
test "$(git ls-files -s Projects/CLAUDE.md | awk '{print $1}')" = "120000"
git diff --cached --check
```

- [ ] **Step 5: Commit shared project instructions**

```bash
git commit -m "docs: make project workspace rules Codex-first"
```

---

### Task 9: Provision the Live-Local pi Notes Repository

**Files (outside the tracked MindFlow branch):**
- Create: `/Users/limx/mindflow/Projects/pi/.gitignore`
- Create: `/Users/limx/mindflow/Projects/pi/AGENTS.md`
- Create: `/Users/limx/mindflow/Projects/pi/CLAUDE.md` symlink
- Create: `/Users/limx/mindflow/Projects/pi/main.md`
- Create: `/Users/limx/mindflow/Projects/pi/engineering.md`
- Create: `/Users/limx/mindflow/Projects/pi/experiments/.gitkeep`
- Create: `/Users/limx/mindflow/Projects/pi/discussions/.gitkeep`
- Create: `/Users/limx/mindflow/Projects/pi/code/pi` absolute symlink

**Interfaces:**
- Produces: independent notes Git root `/Users/limx/mindflow/Projects/pi`
- Produces: code symlink resolving exactly to `/Users/limx/project/pi`
- Preserves: direct-root `/Users/limx/mindflow/Projects/RLinf`

- [ ] **Step 1: Re-run destructive-target preflight**

```bash
test ! -e /Users/limx/mindflow/Projects/pi
test ! -L /Users/limx/mindflow/Projects/pi
find /Users/limx/mindflow/Projects -maxdepth 1 -name 'pi' -ls
test "$(git -C /Users/limx/project/pi rev-parse --show-toplevel)" = "/Users/limx/project/pi"
git -C /Users/limx/project/pi status --short
git -C /Users/limx/mindflow/Projects/RLinf status --short
```

Expected: `Projects/pi` is absent and both code repositories report their current status. Stop if the target now exists or either status introduces an ownership ambiguity.

- [ ] **Step 2: Initialize the independent notes repository**

```bash
mkdir -p /Users/limx/mindflow/Projects/pi/{code,experiments,discussions,worklog}
git -C /Users/limx/mindflow/Projects/pi init -b main
```

Use `apply_patch` to create the two tracked marker files before staging:

```diff
*** Begin Patch
*** Add File: /Users/limx/mindflow/Projects/pi/experiments/.gitkeep
+
*** Add File: /Users/limx/mindflow/Projects/pi/discussions/.gitkeep
+
*** End Patch
```

Write `.gitignore` exactly as:

```gitignore
.DS_Store
code/
worklog/
```

- [ ] **Step 3: Create the wrapper notes and instruction bridge**

`main.md` is a workspace overview, not a PARA outcome:

```markdown
# pi Workspace

## Purpose

Maintain research context, experiment interpretation, and project-level decisions for OpenPI work without copying source code or runtime artifacts.

## Active Outcomes

No outcome-driven PARA Project has been declared yet.

## Knowledge Entrypoints

- [[DomainMaps/VLA|VLA]]

## Experiments

No tracked experiment summary has been added yet.

## Discussions

No tracked discussion summary has been added yet.

## Next Review

Review when the first outcome-driven PARA Project is declared.
```

Write `engineering.md` as:

```markdown
# pi Engineering

## Canonical repositories

- OpenPI code: `/Users/limx/project/pi`
- Workspace bridge: `code/pi -> /Users/limx/project/pi`

## Boundaries

- Source, runtime configuration, checkpoints, datasets, and deployment state remain in their owning systems; do not copy them into this notes repository.
- Read the code repository's own `AGENTS.md` before changing source.
- Store cross-repository project conventions here only after they are verified and durable.
```

Write `AGENTS.md` as:

```markdown
# pi Workspace Contract

- Read `main.md` and `engineering.md` for project-level context.
- Treat `/Users/limx/project/pi` as the canonical code root; `code/pi` is only an absolute symlink bridge.
- Follow the code repository's own `AGENTS.md` for source changes.
- Keep task logs under ignored `worklog/`; keep runtime artifacts, datasets, checkpoints, and large logs outside this notes repository.
- Do not create a PARA Project note until an explicit outcome and completion criteria exist.
```

Create the compatibility bridge and verify it:

```bash
ln -s AGENTS.md /Users/limx/mindflow/Projects/pi/CLAUDE.md
test "$(readlink /Users/limx/mindflow/Projects/pi/CLAUDE.md)" = "AGENTS.md"
```

- [ ] **Step 4: Create and verify the absolute code symlink**

```bash
ln -s /Users/limx/project/pi /Users/limx/mindflow/Projects/pi/code/pi
test -L /Users/limx/mindflow/Projects/pi/code/pi
test "$(readlink /Users/limx/mindflow/Projects/pi/code/pi)" = "/Users/limx/project/pi"
test "$(realpath /Users/limx/mindflow/Projects/pi/code/pi)" = "/Users/limx/project/pi"
```

- [ ] **Step 5: Commit only notes-repo content**

```bash
git -C /Users/limx/mindflow/Projects/pi add \
  .gitignore AGENTS.md CLAUDE.md main.md engineering.md \
  experiments/.gitkeep discussions/.gitkeep
git -C /Users/limx/mindflow/Projects/pi diff --cached --check
git -C /Users/limx/mindflow/Projects/pi commit -m "chore: initialize pi project workspace"
git -C /Users/limx/mindflow/Projects/pi check-ignore -q code/pi
git -C /Users/limx/mindflow/Projects/pi check-ignore -q worklog/probe
```

Do not add a remote or push.

---

### Task 10: Narrow Local Obsidian Indexing

**Files (local-only):**
- Verify only: `/Users/limx/mindflow/.obsidian/templates.json`
- Modify: `/Users/limx/mindflow/.obsidian/app.json`

**Interfaces:**
- Preserves: every `app.json` key except `userIgnoreFilters`
- Produces: searchable wrapper notes with code/worklog/.git and legacy RLinf excluded

- [ ] **Step 1: Verify the already-configured template folder**

The file already exists. Do not rewrite it; verify:

```json
{
  "folder": "Templates"
}
```

```bash
jq empty /Users/limx/mindflow/.obsidian/templates.json
jq -e '.folder == "Templates"' /Users/limx/mindflow/.obsidian/templates.json
```

- [ ] **Step 2: Atomically narrow filters without changing other keys**

Preserve other JSON keys and set `userIgnoreFilters` to:

```json
[
  "^Projects/RLinf(?:/|$)",
  "^Projects/[^/]+/(?:code|worklog|\\.git)(?:/|$)"
]
```

Capture unrelated keys, write through a task-owned temporary file, validate, then replace the exact target:

```bash
obsidian_app=/Users/limx/mindflow/.obsidian/app.json
obsidian_tmp_dir=$(mktemp -d)
trap 'rm -rf "$obsidian_tmp_dir"' EXIT
before_keys="$obsidian_tmp_dir/app-before.json"
after_keys="$obsidian_tmp_dir/app-after.json"
candidate="$obsidian_tmp_dir/app-candidate.json"
jq 'del(.userIgnoreFilters)' "$obsidian_app" > "$before_keys"
jq '.userIgnoreFilters = [
  "^Projects/RLinf(?:/|$)",
  "^Projects/[^/]+/(?:code|worklog|\\.git)(?:/|$)"
]' "$obsidian_app" > "$candidate"
jq empty "$candidate"
jq 'del(.userIgnoreFilters)' "$candidate" > "$after_keys"
cmp "$before_keys" "$after_keys"
mv "$candidate" "$obsidian_app"
jq empty "$obsidian_app"
```

- [ ] **Step 3: Validate intended regex behavior**

```bash
node - <<'NODE'
const fs = require('fs')
const config = JSON.parse(fs.readFileSync('/Users/limx/mindflow/.obsidian/app.json', 'utf8'))
const filters = config.userIgnoreFilters.map((value) => new RegExp(value))
const ignored = (path) => filters.some((pattern) => pattern.test(path))
if (!ignored('Projects/RLinf/rlinf/train.py')) process.exit(1)
if (!ignored('Projects/pi/code/pi/pyproject.toml')) process.exit(1)
if (!ignored('Projects/pi/worklog/2026-11-03.md')) process.exit(1)
if (!ignored('Projects/pi/.git/config')) process.exit(1)
if (ignored('Projects/pi/main.md')) process.exit(1)
if (ignored('Projects/pi/engineering.md')) process.exit(1)
NODE
```

- [ ] **Step 4: Perform the Obsidian UI smoke test**

Reload the canonical vault, search exact strings `pi Workspace` and `pi Engineering`, and confirm both notes appear. Search `Projects/pi/code`, `Projects/pi/worklog`, `.git/config`, and `Projects/RLinf/rlinf`; confirm no ignored path appears. Record the app version and observed result.

---

### Task 11: Verify A1 and Hand Off to A2

**Files:**
- Verify only; no new implementation files

**Interfaces:**
- Consumes: Tasks 1–10
- Produces: branch-local A1 evidence package and an explicit handoff to Plan A2

- [ ] **Step 1: Run all Python and skill checks**

```bash
uv run --frozen python -B -m unittest discover \
  -s skills/6-orchestration/mindflow-context/scripts -p 'test_*.py' -v
uv run --frozen python -B \
  skills/6-orchestration/mindflow-context/scripts/validate_profiles.py \
  --vault . --self-test
uv run --frozen python \
  /Users/limx/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/6-orchestration/mindflow-context
git diff --check
```

Expected: all fixture tests and skill validation pass. The branch-local live validator may not use the canonical wrapper because the wrapper is outside this worktree; do not weaken containment to hide that checkout boundary.

- [ ] **Step 2: Verify outer and nested Git boundaries**

```bash
git check-ignore -q Projects/pi/main.md
! git check-ignore -q Projects/AGENTS.md
test "$(git -C /Users/limx/mindflow/Projects/pi rev-parse --show-toplevel)" = "/Users/limx/mindflow/Projects/pi"
test "$(git -C /Users/limx/mindflow/Projects/pi status --short)" = ""
test "$(git -C /Users/limx/project/pi rev-parse --show-toplevel)" = "/Users/limx/project/pi"
test "$(git -C /Users/limx/mindflow/Projects/pi/code/pi rev-parse --show-toplevel)" = "/Users/limx/project/pi"
```

- [ ] **Step 3: Prepare the A2 handoff report**

Report branch HEAD, each A1 commit, test counts, wrapper commit, canonical symlink
target, local Obsidian smoke result, RLinf preservation, and remaining authorization
boundaries. Record that Quartz checks, live canonical profile validation, Papers Base
UI smoke, and local merge are deliberately deferred until A2 has finished on this
same branch. Do not claim live profile validation before integration.

- [ ] **Step 4: Continue with Plan A2 on the same branch**

Open `docs/superpowers/plans/2026-11-03-plan-a2-paper-schema-foundation.md`
and execute it from Task 1. Do not merge A1 separately. A2 Task 9 owns the combined
A1+A2 integration report and the single local-merge authorization gate; push remains
a separate boundary after any approved local merge.
