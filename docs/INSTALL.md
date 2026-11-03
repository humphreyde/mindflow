# Installation Guide

Codex CLI / desktop 是 MindFlow 的默认 agent 入口；Obsidian 是 vault 的浏览与编辑界面。仓库内的 15 个 skills 已通过 `.agents/skills` 暴露给 Codex，无需复制或全局安装。

## Prerequisites

| Dependency | Requirement | Used for |
|:-----------|:------------|:---------|
| [Codex](https://developers.openai.com/codex/) | Codex CLI，或支持 repo-scoped skills 的 Codex desktop environment | 默认 agent runtime |
| [Git](https://git-scm.com/) | Required | Clone、版本控制与 Quartz 的修改时间 |
| [Obsidian](https://obsidian.md/) | Recommended | Vault UI；不影响 Codex 在 Markdown 上执行 skills |
| [Python](https://www.python.org/) + [uv](https://docs.astral.sh/uv/) | Python 3.12+；通过根目录 `pyproject.toml` / `uv.lock` 使用 `uv` | PDF 提取和 Python helpers；不要安装到 system Python |
| [Node.js](https://nodejs.org/) + npm | Paper HTML 提取需要 Node 18+；`.website/` Quartz workspace 需要 Node 20+ | HTML 提取与网站构建 |
| [GitHub CLI](https://cli.github.com/) | Optional | GitHub metadata；缺失时 skill 可回退到公开 API |

## Step 1: Clone the Repository

```bash
git clone https://github.com/liqing-ustc/MindFlow.git
cd MindFlow
```

后续命令都从仓库根目录执行，除非命令明确进入 `.website/`。

## Step 2: Verify Codex Skill Discovery

`skills/` 是唯一的 skill 源码目录；版本库内的 `.agents/skills -> ../skills` 是 Codex discovery link。验证 symlink 和 15 个入口：

```bash
test -L .agents/skills
test "$(readlink .agents/skills)" = "../skills"
find -H .agents/skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l
# Expected: 15
```

若 symlink 在不保留链接的下载或复制过程中丢失，请重新使用 `git clone`；不要在 `.agents/skills` 下维护第二份 skill 副本。

## Optional: Cross-repository MindFlow context

外部代码仓库不会继承 MindFlow 父目录的 `AGENTS.md`。若要让 Codex 在这些仓库的研究、架构、实验设计、方法选择、论文到代码映射或历史决策任务中使用 MindFlow，可安装一个 user-level discovery link：

```bash
: "${canonical:=/Users/limx/mindflow/skills/6-orchestration/mindflow-context}"
: "${global_link:=/Users/limx/.codex/skills/mindflow-context}"

(
  test -d "$canonical" || {
    printf 'canonical skill directory is missing: %s\n' "$canonical" >&2
    exit 1
  }
  if test -e "$global_link" || test -L "$global_link"; then
    printf 'refusing existing discovery path: %s\n' "$global_link" >&2
    exit 1
  fi
  ln -s "$canonical" "$global_link" || exit 1
  test "$(realpath "$global_link")" = "$(realpath "$canonical")"
)
```

这里只允许这一条指向 canonical skill 目录的 symlink；canonical `skills/` tree 永远不复制，也不整体链接到另一个 discovery root。片段会拒绝任何已经存在的普通文件、目录、有效 symlink 或 broken symlink，不会覆盖、跟随或改写现有路径；重复安装前必须先按下方 rollback 明确移除旧链接。安装前应保存 `/Users/limx/.codex/AGENTS.md` 的原始内容，然后只追加一次以下最小全局 trigger：

```markdown
## MindFlow research context

- For research, architecture, experiment design, method selection, paper-to-code mapping, historical-decision work, or an explicit request to use MindFlow, use `$mindflow-context`.
- Profile or `MindFlow/Projects/` membership selects project retrieval versus generic fallback; it does not decide whether a research task triggers.
- Do not invoke MindFlow for mechanical formatting, ordinary local test fixes, or unrelated code changes.
- This rule controls research-knowledge retrieval only; source code remains readable whenever the task requires it.
```

重启 Codex 或使用 fresh isolated sessions，分别从外部仓库（MVP 使用 `/Users/limx/project/pi`）和 MindFlow 根目录检查 selector/catalog。两个环境都必须恰好只有一个可选的 `mindflow-context`，并加载 `/Users/limx/mindflow/skills/6-orchestration/mindflow-context/SKILL.md`；其他路径下不得存在复制的 entrypoint。

若任一环境出现零个或多个条目、非 canonical realpath 或复制的 entrypoint，先确认 user-level path 仍是上面创建的精确 symlink，再删除该 symlink、把全局 `AGENTS.md` 恢复为安装前的原始内容并停止；不得继续使用未经验证的 discovery 布局。

`pi` 的 canonical code path 仍位于 `/Users/limx/project/pi`。MindFlow 使用 project wrapper，并以 `Projects/pi/code/pi -> /Users/limx/project/pi` 的绝对 symlink 接入；这不是物理移动。

## Step 3: Start Codex and Verify a Skill

从 MindFlow 根目录启动 Codex，使根 `AGENTS.md` 与 `.agents/skills` 同时生效：

```bash
codex
```

在 Codex 中显式调用任一 skill，例如：

```text
$paper-digest arXiv:2410.24164
$daily-papers 过去 3 天
$literature-survey GUI Agent
```

Codex 应先读取对应 `SKILL.md`，再按其中的 Steps、Guard 和 Verify 执行。完整 skill 清单见 [README](../README.md#ai-research-skills)。

## Step 4: Open the Obsidian Vault

1. Open Obsidian.
2. Click **Open folder as vault**.
3. Select the cloned `MindFlow` directory.
4. Trust the vault when prompted if you want to enable community plugins.

### Local Obsidian paper workspace

- 在 Obsidian 设置中启用 core **Bases** feature；无需安装第三方数据库插件。
- `.obsidian/templates.json` 的 `folder` 应为 `Templates`。
- `.obsidian/app.json` 是 local-only 配置；`userIgnoreFilters` 只排除 wrapper 的 `code/`、`worklog/`、`.git/`，并为暂未迁移的 direct-root repository 保留精确兼容项。
- `Projects/<workspace>/main.md` 与 `engineering.md` 应可在 Obsidian 搜索；code tree 不应进入索引。
- Paper 的 canonical generation template 位于 `skills/1-literature/paper-digest/references/paper-note-template.md`，字段契约位于 `references/paper-schema.md`；不在 `Templates/` 下另建 Paper 副本。
- 在 Obsidian 中打开 `Workbench/PARA/Resources/Papers.base`，确认八个 Paper views 可用。Paper 保持在 `Papers/` 根目录，分类由 metadata 与 Base 完成。
- repository-local skill setup 不会安装、禁用或协调全局 `paper-reader` / `daily-papers`。若全局存在同名或旧版 skill，必须另行比较和切换；本安装步骤不会覆盖它们。

[Obsidian Git](https://github.com/Vinzent03/obsidian-git) 可选，用于在 UI 中查看版本控制状态。

## Optional: Published Website (Quartz)

Quartz 是独立的 Node 20+ workspace。不要在 vault 根目录安装其依赖：

```bash
cd .website
npm ci
npx quartz build --directory ../ --output dist
# Local preview:
npx quartz build --directory ../ --serve
```

## Optional compatibility: Claude Code

Claude Code 不是默认入口，但可通过兼容链接复用 canonical `skills/`。仅在需要该 runtime 时，从仓库根目录执行：

```bash
mkdir -p .claude/skills
for skill in skills/*/*; do
  [ -d "$skill" ] && ln -sfn "../../$skill" ".claude/skills/$(basename "$skill")"
done
```

验证 `.claude/skills/` 中的链接后，从仓库根目录启动 Claude Code。不要修改 `skills/` 之外的链接副本。
