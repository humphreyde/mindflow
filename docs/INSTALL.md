# Installation Guide

Codex CLI / desktop 是 MindFlow 的默认 agent 入口；Obsidian 是 vault 的浏览与编辑界面。仓库内的 14 个 skills 已通过 `.agents/skills` 暴露给 Codex，无需复制或全局安装。

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

`skills/` 是唯一的 skill 源码目录；版本库内的 `.agents/skills -> ../skills` 是 Codex discovery link。验证 symlink 和 14 个入口：

```bash
test -L .agents/skills
test "$(readlink .agents/skills)" = "../skills"
find -H .agents/skills -mindepth 3 -maxdepth 3 -name SKILL.md | wc -l
# Expected: 14
```

若 symlink 在不保留链接的下载或复制过程中丢失，请重新使用 `git clone`；不要在 `.agents/skills` 下维护第二份 skill 副本。

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

Templates、attachments 和 link format 已在 `.obsidian/` 中预配置。[Obsidian Git](https://github.com/Vinzent03/obsidian-git) 可选，用于在 UI 中查看版本控制状态。

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
