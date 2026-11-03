# AGENTS.md

## Codex Repository Contract

- **Purpose and canonical paths**: MindFlow is an Obsidian research vault for a human-AI research workflow. User knowledge lives in `Papers/`, `DomainMaps/`, `Topics/`, `Ideas/`, `Projects/`, `Reports/`, `Meetings/`, and `Workbench/`; reusable schemas live in `Templates/` and protocols in `references/`. `skills/` is the single canonical skill tree, while `.website/` contains the separate Quartz publisher.
- **Skill discovery**: Codex discovers all repository skills through `.agents/skills -> ../skills`. Invoke one explicitly as `$skill-name`, then read its complete `SKILL.md` and required referenced files before acting. Do not duplicate or move the canonical `skills/` tree.
- **Read before write**: Before changing the vault, read the relevant file in `references/`, the matching file in `Templates/` when one exists, and the current target note. Follow their schema and local conventions instead of inventing a parallel format.
- **Protect user content**: Preserve existing notes, frontmatter, and handwritten edits. Do not overwrite, delete, rename, or batch-rewrite user content unless the user has explicitly authorized that exact scope; make the smallest compatible change.
- **Obsidian syntax**: Follow `references/obsidian-syntax.md` for formulas, tables, embeds, wikilinks and aliases, literal characters, and pipes inside table cells. Keep valid Obsidian links and YAML frontmatter intact.
- **Editing and validation**: Prefer `rg` for search and precise patches for edits. Stage only task-owned paths, never broad unrelated changes. Validate in proportion to the change: inspect the diff, run `git diff --check`, and run the relevant script, schema, or build checks for executable changes.
- **Runtime boundaries**: Use Python 3.12+ and the root `pyproject.toml`/`uv.lock` via `uv` for Python helpers; do not install into the system interpreter. The sole compatibility exception is the read-only `mindflow-context` profile validator: when a Codex sandbox blocks both the vault interpreter and uv cache, it may use an already-installed system Python 3.10+ with PyYAML through stdin; it must not install packages or use this fallback for other helpers. Use Node.js/npm only for Node helpers and the Quartz workspace; paper HTML extraction requires Node 18+, while `.website/` requires Node 20+ and its own lockfile. Run Quartz/npm commands from `.website/` (for example `npm ci`, then `npx quartz build --directory ../ --output dist`) so vault content and website dependencies remain separate.

本文件描述本工作区的 **Owner**，供所有 agent 共享参考——理解他是谁、研究什么、看重什么，以及这个 notebook 如何组织。各 agent 自身的身份与职责由各自的 instruction / 项目级 CLAUDE.md 定义，本文件不覆盖那些。

## Owner

hum，一名Engineer Researcher，追求从事高影响力的科研和将前沿研究转换为落地应用。他是本工作区的所有者、所有重要决策的最终审批人，会与各 agent 讨论、提出建议和反馈。

## 研究兴趣

Multimodal Understanding: VLM, Video LLM, Video Understanding, Visual Reasoning
AI Agent: LLM Agent, Computer-use Agent, GUI Agent, Agentic RL
Embodied AI: VLA, World Model, World Action Model, Spatial Intelligence, Robot Manipulation & Locomotion, RL

## 研究原则

Owner 的研究品味——做研究相关工作时与之对齐：

### 1. Research Taste — 重要的问题，简洁的方法

- 区分 "publishable" 和 "important"，追求后者。+0.3% SOTA 不是 insight
- 追求真机表现和第一性原理，最本质的理论和最具落地性的工作才是王道
- 追求 **simple, scalable, generalizable** 的方法。复杂往往是理解不够深的信号
- 不 scale 的方法大概率方向不对；不 generalize 的方法大概率在 exploit bias
- 有勇气 pivot——sunk cost 不是坚持的理由

### 2. Think from First Principles — 追问 Why

- 理解**为什么 work、什么条件下会 break**，而非收集结论
- Convention 不等于 truth。"大家都这么做" 不是理由，证据才是
- 问对问题比解对问题更重要——关注 problem formulation

### 3. Honest & Evidence-Driven — 诚实面对认知边界，用证据而非直觉做判断

- 严格区分**已知**、**推测**、**不知道**。每个 claim 标注 grounding：论文、实验、还是推理
- 不 overclaim，不掩盖错误。对自己的 idea 和对别人的论文施加同等的审视标准
- 先想清楚 "什么结果能推翻假说" 再动手。Negative result 同等重要

### 4. Read Critically — 论文不是圣经

- 每篇论文都有隐含假设和适用边界，找出它们
- Ablation、failure case、baseline 选择往往比 main result 更有信息量
- 影响力不等于正确性，对高引论文同样保持批判

### 5. Connect and Compound — 让知识产生复利

- 单篇论文是数据点，跨论文 pattern 才是 knowledge。矛盾是最有价值的信号
- 每次阅读都应更新 mental model，而非仅增加一条记录
- 定期修剪知识库——过时的认知比无知更危险

### 6. Explore Efficiently — 聪明地分配注意力

- Breadth 和 depth 动态平衡。20% 的论文包含 80% 的 insight
- 连续探索无产出时换角度，而非更用力。每个 action 要有清晰的 expected information gain

### 7. Write Clearly — 写不清楚说明想不清楚

- 先结论再论据，先 what 再 how 再 why
- 用术语是因为精确，不是因为显得高级

## Anti-Patterns

Owner 警惕的失败模式：

- **Literature hoarding**: 读很多但没有自己的判断
- **Method worship**: 迷恋方法精巧而忽略问题本身
- **Confirmation bias**: 只看支持自己假设的证据
- **Premature convergence**: 未充分探索就锁定方向
- **Perfectionism paralysis**: 等完美方案而错过行动窗口

## Directory Structure

这是 Owner 的 notebook（知识库），记录他的所有知识，所有笔记是 Obsidian markdown 文件：

- `DomainMaps/` — 核心认知地图，每个 domain 一个文件，`_index.md` 为索引页
- `Papers/` — 论文笔记（YYMM-ShortTitle.md）
- `Topics/` — 文献调研与分析报告
- `Ideas/` — 研究 idea
- `Projects/` - 项目记录
- `Reports/` — 生成的报告
- `Meetings/` — 会议记录
- `Workbench/` — 工作状态
- `skills/` — 科研技能库
- `references/` — 协议文档
- `Templates/` — 各类笔记模板

**语言**：中英文，技术术语（模型名、方法名、数据集名等）保持英文不翻译

**Markdown 语法**：写笔记前先参考 [[references/obsidian-syntax|references/obsidian-syntax.md]]——公式 / 表格 / 图片 / 视频 / wikilink alias / 表格内 pipe 转义 / `*` 字面字符等坑都在那里。

各 agent 必须认真使用和维护这个 notebook！
