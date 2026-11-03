# MindFlow

An Obsidian-based research workspace for building a **human-AI collaborative research pipeline** — from paper reading to idea generation to experiment validation.

基于 Obsidian 的 AI 研究知识管理工作区，构建从论文阅读到 idea 生成再到实验验证的 **human-AI 协作研究流水线**。

## Vision

论文太多，靠人工逐篇阅读不现实。MindFlow 让人和 AI 更好地配合——**人专注于创造性工作，AI 负责重复性、工程性的事情**，共同构建一个 personalized knowledge space。

核心流程：

1. **AI 阅读与总结** — 让 AI 批量阅读论文、生成结构化笔记
2. **人工精炼与补充** — 人来修改、补充个人见解
3. **交互式讨论** — 人和 AI 围绕论文内容深入讨论
4. **知识网络构建** — 逐步积累形成 personalized knowledge space
5. **Research Idea 生成** — 基于知识积累，碰撞产出研究想法
6. **实验设计与验证** — 设计实验方案，跟踪结果，验证假设

![Obsidian Demo](docs/obsidian-demo.png)

## Features

- **Paper Notes** — 182 篇扁平存储的结构化论文笔记，通过 metadata、Base 与跨论文链接组织
- **Domain Maps** — 按研究领域构建的认知地图（VLM、CUA、VLA 等）
- **Research Ideas** — 灵感记录与评估，双向链接到相关论文
- **Literature Survey** — 按主题系统调研，多篇论文对比分析
- **AI Skills** — 15 个 AI 技能覆盖完整研究流程（阅读→构思→实验→写作→反思）
- **Workbench** — 研究状态追踪（agenda、日志、记忆库）
- **Project & Meeting Tracking** — 项目进展与会议记录
- **Published Website** — 基于 Quartz v4 的知识库站点

## Getting Started

Codex CLI / desktop 是 MindFlow 的默认 agent 入口；Obsidian 用于浏览和编辑 vault。详细安装步骤见 [INSTALL.md](docs/INSTALL.md)。你可以手动执行，也可以将以下指令交给 Codex：
```
Install MindFlow from: https://github.com/liqing-ustc/mindflow/blob/main/docs/INSTALL.md
```

## Directory Structure

| Folder | Purpose | Naming |
|--------|---------|--------|
| `Papers/` | 扁平存储的论文笔记；分类由 metadata 与 `Workbench/PARA/Resources/Papers.base` 提供 | `YYMM-ShortTitle.md` |
| `DomainMaps/` | 核心认知地图，每个 domain 一个文件 | `_index.md` 为索引 |
| `Ideas/` | 研究灵感与评估 | 自由命名 |
| `Topics/` | 文献调研与分析报告 | 主题名称 |
| `Projects/` | 独立 project notes repositories；代码统一位于各 wrapper 的 `code/<repo>`，不纳入 vault 发布 | project workspace |
| `Reports/` | 生成的报告 | — |
| `Experiments/` | 实验设计、运行记录与结果（由 skill 按需生成） | — |
| `Meetings/` | 会议记录 | `YYYY-MM-DD-Description.md` |
| `Workbench/` | 研究工作状态（agenda、日志、记忆） | — |
| `Workbench/RepositoryProfiles/` | 稳定 repository identity 与有界检索入口 | `{repo_key}.md` |
| `Workbench/PARA/Projects/` | 有明确 outcome 与 completion criteria 的 Project control notes | `{project_key}.md` |
| `skills/` | 15 个 AI 研究技能的唯一源码目录 | — |
| `.agents/skills` | Codex repo-scoped skill 发现入口（指向 `../skills`） | symlink |
| `Templates/` | Obsidian 模板 | — |
| `references/` | 协议文档（tag taxonomy 等） | — |

## Templates

| Template | Purpose |
|----------|---------|
| Paper | 由 `skills/1-literature/paper-digest/references/paper-note-template.md` 生成，字段遵循 `references/paper-schema.md`；不在 `Templates/` 维护副本 |
| Idea | 研究灵感（status: raw → developing → validated → archived） |
| Project | 项目追踪（status: planning → active → paused → completed） |
| Topic | 主题综述/文献对比（含论文对比表格） |
| Survey | 系统文献调研报告 |
| Experiment | 实验设计与跟踪 |
| DomainMap | 认知地图 |
| Report | 研究报告 |
| Meeting | 会议记录（含 Action Items） |
| Daily | 每日研究日志 |

## AI Research Skills

MindFlow 内置了 17 个 AI 技能，按研究流程分为 6 层：

| Layer | Skills | Purpose |
|-------|--------|---------|
| 1. Literature | `daily-papers`, `paper-digest`, `literature-survey`, `github-trending`, `research-insights` | 每日论文推荐、论文阅读、文献调研、GitHub 趋势与外部研究资料沉淀 |
| 2. Ideation | `idea-generate`, `idea-evaluate` | 研究 idea 生成与评估 |
| 3. Experiment | `experiment-design`, `experiment-track`, `result-analysis` | 实验设计、跟踪与分析 |
| 4. Writing | `draft-section`, `writing-refine` | 论文写作与打磨 |
| 5. Evolution | `memory-retrieve`, `memory-distill`, `agenda-evolve` | 记忆管理与方向演化 |
| 6. Orchestration | `autoresearch`, `mindflow-context` | 自主研究循环；按项目 profile 检索跨仓库研究上下文 |

### Quick Start with Codex

从仓库根目录启动 Codex，然后显式调用 skill：

```text
$daily-papers 过去 3 天          # 筛选并点评近期论文
$paper-digest arXiv:2410.24164  # 抓取、总结并生成论文笔记
$literature-survey GUI Agent    # 系统文献调研
$idea-generate                  # 基于知识库生成 research idea
$idea-evaluate Ideas/example.md # 评估已有 idea
$experiment-design Ideas/example.md # 生成实验方案到 Experiments/
$mindflow-context 分析当前项目的 action chunking 设计
```

### Canonical Codex skill links

在新电脑上，先把 MindFlow clone 到长期使用的主检出路径。推荐把 uv-managed Python 安装在 vault 内，使从嵌套 code repository 启动的 Codex 沙箱也能读取完整 Python 3.12 环境；不要把临时 worktree 当作全局 skill 目标：

```bash
UV_PYTHON_INSTALL_DIR="$PWD/.python" uv python install 3.12 --no-bin
UV_PYTHON_INSTALL_DIR="$PWD/.python" uv sync --frozen --python 3.12
uv run --frozen python -B scripts/bootstrap_codex_skills.py plan --codex-home /absolute/path/to/.codex
```

检查 plan 只包含固定 allowlist，且每个 action 与现有安装相符后，再执行：

```bash
uv run --frozen python -B scripts/bootstrap_codex_skills.py apply \
  --codex-home /absolute/path/to/.codex \
  --archive-date YYYY-MM-DD
```

脚本把既有 allowlisted skill 精确归档到 `.codex/skills-legacy/YYYY-MM-DD/`，写入包含 hash 的 `manifest.json`，再让 `.codex/skills/<name>` 指向本 MindFlow 的 canonical skill。验证时检查 `readlink`、resolved target 与各 skill validator。需要恢复时使用同一 manifest：

```bash
uv run --frozen python -B scripts/bootstrap_codex_skills.py rollback \
  --codex-home /absolute/path/to/.codex \
  --manifest /absolute/path/to/.codex/skills-legacy/YYYY-MM-DD/manifest.json
```

该流程只管理 allowlisted Codex skill。Project 代码仓、Zotero library、credentials 和机器私有路径不会随 MindFlow 同步。

## Workspace Model

- Repository identity 保存在 `Workbench/RepositoryProfiles/`；它不等于 PARA Project。
- PARA Project 只有在存在明确 outcome 与 completion criteria 时创建。
- 每个 `Projects/<workspace>/` 是独立 notes Git repository，代码位于 `code/<repo>`。已有外部代码仓优先通过绝对 symlink 接入，物理移动需另行批准。
- `Papers/`、`Topics/`、`DomainMaps/`、`Ideas/` 和 `Experiments/` 继续作为 vault-root typed knowledge assets，不复制到 Project wrapper。

### Paper workspace

- `Papers/` 保持扁平路径，领域归属使用 `primary_domain`、`domains` 与受控 `tags`，不按 VLA、WAM 等主题拆目录。
- canonical generation template 是 `skills/1-literature/paper-digest/references/paper-note-template.md`，字段契约是 `references/paper-schema.md`。
- `Workbench/PARA/Resources/Papers.base` 提供全集、领域、VLA、WAM、待复核、Foundation 与最近更新等动态视图。
- 既有笔记的确定性迁移遵循“只读 audit → 人工 review → 固定 manifest 的窄范围 apply”。当前 backfill 只增加 `type: paper` 与高置信度 `arxiv_id`；分类、DOI、Zotero、tags、rating 文本和文件名仍需单独复核。
- 新内容使用 `1 - Peripheral`；既有 `1 - Archived` 是兼容历史文本，不做全库替换。

#### Optional compatibility: Claude Code

Claude Code 仍可使用同一套 `skills/`；兼容链接的配置方法见 [INSTALL.md](docs/INSTALL.md#optional-compatibility-claude-code)。Codex discovery 仍以 `.agents/skills` 为默认入口。

## Tags

Flat tags using canonical English terms:

- **Domain**: `LLM`, `CV`, `RL`, `multimodal`, `diffusion`
- **Method**: `transformer`, `RLHF`, `distillation`, `RAG`
- **Task**: `text-generation`, `image-classification`, `alignment`
- **Venue** (optional): `NeurIPS`, `ICML`, `ICLR`, `ACL`, `CVPR`

## Linking Strategy

Notes are connected via `[[wikilinks]]` to form a knowledge graph:

- Paper ↔ Paper (related work)
- Idea → Paper (inspiration source)
- DomainMap → Papers (knowledge structure)
- Topic → Papers (literature survey)
- Project → Paper + Idea (foundations)

Use Obsidian's **Graph View** to visualize your research knowledge network.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=liqing-ustc/MindFlow&type=Date)](https://star-history.com/#liqing-ustc/MindFlow&Date)

If you find this useful, please give it a star! It helps others discover this project.

**Author**: [Qing Li](https://liqing.io/)

## Acknowledgements

- The `daily-papers` skill is adapted from [huangkiki/dailypaper-skills](https://github.com/huangkiki/dailypaper-skills).

## License

Feel free to use this as a template for your own research workspace.
