# MindFlow PARA Notes Migration Design

> **Date**: 2026-10-29
> **Status**: Full design approved in chat 2026-11-03; Plan A is split into A1/A2, and Plan B into B1/B2; written-spec review and implementation plans remain pending
> **Decision**: 将 MindFlow 建成个人 PARA 研究工作区；每个 project workspace 使用独立 notes-repo wrapper，代码仓统一位于 `Projects/<project>/code/`；旧 `notes` 选择性迁移，Zotero 保持独立
> **Source vault**: `/Users/limx/notes`
> **Target vault**: `/Users/limx/mindflow`

---

## 1. Context

MindFlow 已有 `Papers/`、`Topics/`、`DomainMaps/`、`Ideas/`、`Experiments/`、`Reports/` 和 `Projects/`，并用 `Workbench/PARA/Projects/` 保存代码仓的研究 profile。当前这个目录实际混合了两种不同对象：稳定的 repository mapping 与有明确 outcome 的 PARA Project；同时 Areas、Resources、Archives 尚未成为明确的工作流。

旧 `/Users/limx/notes/PaperNotes` 与 MindFlow 同时承载论文知识，形成 split-brain：新旧 skill 可能写入不同 vault，同一论文也可能有两份各自包含独有内容的笔记。当前只读盘点确认：

- 旧 `PaperNotes` 有 482 个 Markdown，其中 242 个作者实体、199 个概念实体、34 个论文通道候选和 5 个导航/代码笔记。
- 34 个候选包括 31 个结构化论文或技术报告、2 个自写系列综述和 1 个误放的 concept。
- 新 `MindFlow/Papers` 有 182 篇根级论文笔记。
- 两库明确重合 7 个论文身份，对应旧库 8 个文件；仅旧库有 26 个身份；新库内部未发现相同 arXiv ID 或规范化标题重复。
- 旧 assets 有 382 个文件、约 87 MB；新 assets 有 114 个文件、约 72 MB。全量复制会引入未引用附件和命名冲突。
- 旧 `DailyPapers`、`GitHubTrending`、`ResearchSources`、`ResearchNotes` 分别有 1、1、10、1 个 Markdown；这些内容已获批按知识类型迁移，而不是继续保留第二套写入工作流。

现有 MindFlow Paper 全部直接位于 `Papers/` 根目录。大量论文跨多个研究域，WAM 典型地同时属于 World Model、VLA 和 manipulation。将 Paper 物理拆成 `Papers/VLA/`、`Papers/WAM/` 会强迫单归属，并破坏现有 skills、wikilinks、Quartz 路径和 Giscus pathname。

## 2. Design Principles

1. **PARA 管可行动性，不替代知识类型。** Project、Area、Resource、Archive 是行动和生命周期视图；Paper、Topic、DomainMap、Idea、Experiment 是研究知识类型。
2. **Repository profile 不等于 Project。** profile 描述稳定代码身份和检索入口；Project 描述有结束条件的 outcome，并通过 `repo_refs` 引用一个或多个 profile。
3. **单一知识真源。** 迁移完成后，新的论文解读只写入 MindFlow；旧 notes 进入只读观察期，不继续作为并行写入目标。
4. **路径稳定优先。** `Papers/` 保持扁平；分类通过结构化 metadata、Topic、DomainMap 和 Obsidian Base 实现。
5. **保留内容而不是搬运目录。** 迁移按论文身份和知识类型重新路由，不复制旧目录结构、自动 MOC 或 Zotero collection。
6. **来源与判断分离。** 官方论文/DOI/arXiv 是论文事实的来源；Zotero 是本地条目和附件来源；MindFlow 是研究解读和知识关联来源。
7. **可回滚、可审计。** 源仓只读；每个迁移对象记录 identity、source path、SHA-256、decision、destination 和验证状态。
8. **不推断未知个人结构。** 只建立已有充分证据的 Area；其他生活或工作 Areas 由用户以后明确增加。
9. **Skill 与知识库一起可迁移。** MindFlow 保存 canonical skills；每台电脑只通过可验证、可回滚的 bootstrap 建立 Codex 全局软链接，不复制出第二份可漂移实现。

## 3. Target Architecture

### 3.1 Two coordinated layers

```text
MindFlow/
├── Papers/                  # 单篇论文知识，扁平路径
├── Topics/                  # 跨论文综合、系列综述
├── DomainMaps/              # 稳定领域认知
├── Ideas/                   # hypothesis / research idea
├── Experiments/             # 实验计划、运行记录、结果
├── Reports/                 # 输出型报告
├── Projects/                # 独立 project notes repos；代码位于各自 code/
│
└── Workbench/
    ├── RepositoryProfiles/  # 稳定 repo identity 与检索入口
    ├── migrations/          # 迁移 manifest、报告和 provenance
    └── PARA/                # 行动与生命周期控制层
        ├── _index.md        # PARA dashboard
        ├── Projects/        # 有明确 outcome 的 active projects
        ├── Areas/           # 持续责任，无固定完成日期
        ├── Resources/       # 知识资产的查询/导航视图，不复制内容
        └── Archives/        # inactive P/A/R control notes
            ├── Projects/
            ├── Areas/
            └── Resources/
```

Typed knowledge assets 继续使用现有顶层路径。`Workbench/PARA/Resources/` 只保存 MOC、Base 和入口，不复制 Paper/Topic/DomainMap 内容。这样既符合 PARA 的可行动性，又不引入第二份知识真源。

### 3.2 Repository profiles and Projects

- `Projects/<project>/` 始终是独立 project notes repo，不是代码仓根；单 repo 项目也使用 wrapper。
- 每个 wrapper 至少包含 `AGENTS.md`、`CLAUDE.md -> AGENTS.md`、`main.md`、`engineering.md`、`experiments/`、`discussions/`、`worklog/` 和 `code/`。
- `code/<repo>` 是独立 Git root。新项目默认直接 clone 到这里；已有外部代码仓优先使用绝对 symlink 接入，确认路径依赖已迁移后才另行批准物理移动。
- project notes repo 自己的 `.gitignore` 排除 `code/` 与 `worklog/`；外层 MindFlow Git 继续忽略 `Projects/*`。
- `Workbench/RepositoryProfiles/<repo_key>.md` 保存 `repo_key/repo_roots/aliases/domains/entrypoints/keywords/verified_at`，并可用 `workspace_root` 指向默认 wrapper、用 `workspace_entrypoints` 声明额外项目笔记，供 `mindflow-context` 匹配仓库和有界读取项目笔记。
- `Workbench/PARA/Projects/<project_key>.md` 是 vault 内的轻量 registry/control note，描述明确 outcome、完成条件、wrapper path 和生命周期，通过 `repo_refs` 引用一个或多个 repository profile；详细研究主线保存在 wrapper 的 `main.md`，两处不复制正文。
- Project 使用 `planning | active | paused | completed | cancelled`；同一 repo 可以被多个 Project 复用，同一 Project 也可以引用多个 repo。
- Project 完成时，先写 final outcome 与代码 provenance，再把 Project control note 移至 `Workbench/PARA/Archives/Projects/`。
- 移动 Project note 不移动 repository profile，也不自动移动或删除代码仓；代码仓归档是独立授权动作。
- `pi` 继续位于 `/Users/limx/project/pi`。Plan A 创建 `Projects/pi/code/pi -> /Users/limx/project/pi` 的绝对 symlink，不物理移动 repo；任何脚本、服务或 remote path 仍使用原 canonical path，直到另一次明确批准的迁移。
- 截至 2026-10-29，`Projects/` 内只有共享 `CLAUDE.md`，没有 direct-root code repo，因此当前没有需要搬移的 project code tree。

推荐 wrapper：

```text
Projects/<project>/          # 独立 project notes Git repo
├── AGENTS.md                # Codex-first project contract
├── CLAUDE.md -> AGENTS.md   # Claude compatibility
├── main.md                  # Goal / Baselines / Experiments / Next Steps
├── engineering.md           # 项目级跨 repo 工程约定
├── experiments/
├── discussions/
├── worklog/                 # 本机任务记录，不进 project notes Git
└── code/                    # 不进 project notes Git
    ├── <repo-a>/            # clone 或到 canonical repo 的 symlink
    └── <repo-b>/
```

外层 `Projects/AGENTS.md` 是创建新 project wrapper 时使用的共享 scaffold，不宣称能穿透 nested Git root 自动继承。现有规则内容迁到 `Projects/AGENTS.md`，`Projects/CLAUDE.md` 改为指向它的 compatibility symlink；每个 project wrapper 必须拥有或链接自己的 `AGENTS.md`。

Repository profile 最小 schema：

```yaml
---
type: repository-profile
repo_key: pi
repo_roots:
  - /Users/limx/project/pi
workspace_root: Projects/pi
workspace_entrypoints: []
aliases: [openpi, pi07]
domains: [VLA, RECAP, TRON2]
entrypoints:
  - DomainMaps/VLA.md
keywords: [ACP, RTC, pi0]
verified_at: 2026-10-29
---
```

Repository profile 与 PARA Project 中的 `workspace_root` 使用同一约束：必须是 vault-relative、规范化为 `Projects/<project>` 的现存真实目录，不能是 absolute path、包含 `..`、目录 symlink 或 canonical realpath 越出 vault 的 `Projects/`。`entrypoints` 与 `workspace_entrypoints` 是两条不同路径通道：前者始终相对 vault root，指向 `DomainMaps/`、`Topics/` 等共享知识；后者始终相对验证后的 `workspace_root`，只允许显式 Markdown 文件。project context 默认读取 `main.md` 和 `engineering.md`，再读取 `workspace_entrypoints`。解析时拒绝 absolute path、`..`、不存在的文件、canonical target 越出 wrapper 的 symlink，以及 `code/`、`worklog/`、`.git/` 下的任何目标；不递归扫描目录。

PARA Project 最小 schema：

```yaml
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
```

现有 `Workbench/PARA/Projects/pi.md` 中的 repo identity 字段先迁为 `Workbench/RepositoryProfiles/pi.md`，并用 `workspace_root: Projects/pi` 关联 wrapper。Plan A 创建 `Projects/pi/`，但不在没有明确 outcome 和 completion criteria 时强行创建同名 PARA Project control note；wrapper 的存在不等于一个 PARA Project。未来出现明确成果目标后，再创建 `Workbench/PARA/Projects/<project_key>.md`，通过 `workspace_root` 与 `repo_refs` 关联 wrapper 和 repository profile。

### 3.3 Areas

Area 是需要长期维护的责任，不是研究主题列表。初始只创建两个已有充分证据的 Area：

- `Research.md`：研究使命、质量标准、review cadence、active projects 和知识入口。
- `Knowledge-System.md`：MindFlow、Obsidian、skills、检索质量和迁移维护责任。

VLA、WAM、World Model、AI Agent 等是知识 domain/topic，不直接等同于 Area。它们进入 `DomainMaps/`、`Topics/` 和 Paper metadata，并由 Area 链接。

Area frontmatter：

```yaml
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
```

正文固定包含 Purpose、Standards、Active Projects、Knowledge Entrypoints、Review Notes。Area 不再承担具体论文摘要或项目日志。

### 3.4 Resources

PARA Resource 是未来可能复用的信息入口。MindFlow 的 `Papers/`、`Topics/`、`DomainMaps/` 和部分 `Reports/` 构成 resource substrate，但继续按知识类型保存。

`Workbench/PARA/Resources/` 初始包含：

- `_index.md`：指向 Papers、Topics、DomainMaps、Ideas、Experiments 和 Zotero 的职责边界。
- `Papers.base`：动态列出 All Papers、VLA、WAM、Cross-domain、Needs Review、Foundation 和 Recent。

Resources 不保存论文副本，不把 Zotero collection 镜像为目录，也不生成每个 tag 一个静态 MOC。

普通 Resource control note 的最小 schema：

```yaml
---
type: resource
resource_key:
scope:
entrypoints: []
query:
review_cadence: quarterly
last_reviewed:
---
```

### 3.5 Archives

PARA Archive 保存不再 active 的行动对象：

- `Archives/Projects/`：completed/cancelled Project control note 的 final snapshot。
- `Archives/Areas/`：不再承担的责任 Area。
- `Archives/Resources/`：停止维护的 Resource control note 或 view。

Archive note 沿用来源类型，并增加 `archived_at`、`archive_reason` 与 `final_outcome`。迁移 manifest 属于操作 provenance，保存到 `Workbench/migrations/`，不伪装成 PARA Archive item。

知识资产通常不因“暂时不用”而物理移入 Archives；Paper 的数值 `rating: 1` 表示研究重要性较低，与 PARA Archive 的生命周期含义不同。新生成文本将标签从 `1 - Archived` 改为 `1 - Peripheral`；旧笔记中的 `Archived` 文案作为兼容历史保留，只有笔记被明确更新时才渐进迁移。两者不得共用同一个 status 字段。

## 4. Paper Classification Model

### 4.1 Storage and identity

- 所有论文继续保存为 `Papers/YYMM-ShortTitle.md`。
- 物理路径不表达领域分类。
- 论文身份优先级：arXiv ID → DOI → 官方 URL + 规范化标题。
- 标题相似但 identity 不同的技术报告不得自动合并，例如 GR00T N1、N1.5、N1.6。
- 只有高置信度 identity 才可自动判定重复；低置信度候选必须进入人工 review 状态。

### 4.2 Frontmatter schema

保留现有字段，并增量增加：

```yaml
---
type: paper
title:
authors: []
institutes: []
date_publish:
venue:
primary_domain: embodied-ai
domains:
  - embodied-ai
  - multimodal-understanding
tags:
  - world-action-model
  - VLA
  - world-model
review_status: reviewed
arxiv_id:
doi:
paper:
website:
github:
zotero_library:
zotero_item_key:
zotero_citekey:
rating:
date_added:
source_vault:
source_path:
date_migrated:
---
```

Schema rules：

- `primary_domain` 必须出现在 `domains` 中。
- `domains` 使用稳定大域：`multimodal-understanding`、`ai-agent`、`embodied-ai`、`general-ai`。
- `tags` 使用 `references/tags.md` 的受控 taxonomy；VLA/WAM 等属于细粒度 facet。
- 新增 canonical tag `world-action-model`。
- 新笔记 tags 目标为 1–4 个；已有超过限制的笔记先进入 validation report，不做无依据机械删减。
- `review_status` 只使用 `inbox | digested | reviewed`。
- `source_vault/source_path/date_migrated` 只用于迁移对象；原生 MindFlow 笔记不强制填写。
- `zotero_item_key` 与 `zotero_citekey` 不得混用；citekey 只作可变引用快照，不是唯一 identity。

### 4.3 Classification views

`Workbench/PARA/Resources/Papers.base` 提供：

1. All Papers：title、date_publish、rating、primary_domain、domains、tags、venue、review_status。
2. By Primary Domain：按 `primary_domain` 分组。
3. Cross-domain：`domains` 多于一个。
4. VLA：tags 包含 `VLA`。
5. WAM：tags 包含 `world-action-model`；迁移过渡期允许 `world-model AND VLA`。
6. Needs Review：缺 identity/classification、未知 tag、低置信度迁移或 `review_status != reviewed`。
7. Foundation：`rating == 3`。
8. Recent：按 `date_added` 倒序。

Quartz 继续使用动态 TagPage；DomainMap 保存稳定认知，Topic 保存跨论文综合，Base 保存全集筛选。这三者互补，不互相复制。

## 5. Zotero Boundary

### 5.1 Source-of-truth split

| 系统 | 权威内容 |
|---|---|
| 官方论文、出版社、arXiv、DOI registry | 论文身份、正文、作者顺序、实验与 claim |
| Zotero | 本地 library membership、item key、附件存在性、collection/tag/citekey 当前状态 |
| MindFlow | 研究解读、rating、内部 tags、wikilinks、关联工作、笔记与 assets |

MindFlow 与 Zotero 通过 `zotero_library + zotero_item_key + DOI/arXiv ID` 弱关联，不做双向同步。

### 5.2 Required and optional capabilities

必要能力：

- read-only、ambiguity-aware 的 item resolve；item key、DOI、arXiv ID 优先，标题只作入口。
- 按需列出 PDF/附件；默认不暴露本地路径或读取全文。
- Zotero 不可用时降级到官方 paper/website/github source，不阻塞 paper digest。

可选能力：

- citekey/BibTeX，用于写作与引用。
- indexed fulltext，仅在用户或证据需要时读取。
- collections/tags，只作迁移提示，不决定 MindFlow 路径或 taxonomy。

明确禁止在 `paper-digest` 中执行：

- connector import/save、collection move/add/remove。
- 直接写 Zotero SQLite。
- 自动 enable/restart Zotero。
- 后台 daemon、全库自动分类或 author sync。

## 6. Migration Scope and Routing

### 6.1 Source remains read-only

迁移工具只读取 `/Users/limx/notes`。开始和结束时记录 source Git HEAD、`git status --short` 和纳入迁移集合的文件 SHA-256；迁移不得修改、格式化、移动或删除源文件。

### 6.2 Canonical manifest

迁移前生成 machine-readable manifest 和 human-readable report，保存到 `Workbench/migrations/`。每项至少包含：

```text
source_path
source_sha256
source_kind
identity: {arxiv_id, doi, normalized_title, official_url}
identity_confidence
decision: merge | import-paper | import-topic | absorb-concept | skip
destination_path
duplicate_group
referenced_assets
link_rewrites
status
```

Manifest 先以 dry-run 生成。存在 ambiguous identity、目标路径冲突、未解析资产或无法保护目标内容时，对应项保持 blocked，不自动写入。

### 6.3 Routing rules

- 7 个重合论文身份：保留 MindFlow 文件名和 schema，逐篇语义合并旧稿独有分析；旧库两份 Pi0 作为同一 duplicate group 处理。
- 仅旧库的单篇论文/技术报告：进入扁平 `Papers/`。
- `GR00T-Series-Survey.md`、`Pi-Series-Survey.md` 等人工综合：进入 `Topics/`。
- `Pi06 Base Model.md` concept：吸收到 Pi 系列 Topic 或相关 Paper/DomainMap 的明确 section；不伪装成 Paper。
- 自动生成的 VLA/world model/_inbox MOC：不迁移，由 Base、TagPage 和 Resource index 替代。
- `DailyPapers`：迁入 `Workbench/daily/`；日报按目标日期保留，历史状态合并到该目录的 `.history.json`，不得重置现有 MindFlow 历史。
- `GitHubTrending`：迁入 `Workbench/trending/`；保留周榜日期和来源，不把它伪装成 Paper 或 Topic。
- `ResearchSources`：保留 `Sources/` 与 `Insights/` 的相对结构迁入顶层 `ResearchSources/`，以便来源正文与可复用洞察继续分离。
- `ResearchNotes`：按知识类型迁入 `ResearchSources/Insights/`；当前 `Dyna2部署的一些know-how.md` 作为 source-backed insight 处理，不建立第二个 `ResearchNotes/` 根目录。
- 242 个 author entities、199 个 concept entities、自动 Dashboard/MOC 和导航页仍不迁移；它们需要独立图谱设计，不能因本次范围扩展被顺带复制。

### 6.4 Merge policy

对重合论文：

1. 完整读取两侧全部版本和 assets。
2. 保留 MindFlow 的 canonical frontmatter、文件名、正文结构和已有人工作品。
3. 将旧稿独有的可验证方法、实验、failure case、批判性分析和关联工作放入对应语义 section；不得整体粘贴成重复正文。
4. 不用旧稿覆盖 MindFlow rating、claim 或当前来源；冲突证据并列保留并标注来源。
5. 在 manifest 记录每个旧源文件的 SHA-256、迁入 section 和未采用原因。

### 6.5 Link and asset policy

- 只复制最终迁入正文实际引用的附件。
- 目标统一为 `Papers/assets/<ShortTitle>/`；Topic 特有附件使用与 Topic 同名的独立目录。
- 同名不同内容时不得覆盖；使用确定性后缀并重写引用。
- Paper link 按 manifest 重写为 canonical MindFlow wikilink。
- 旧 author link 转为 frontmatter 纯文本作者名；本阶段不创建 author entities。
- 旧 concept link 仅在 MindFlow 有明确目标时重写；否则保留可读纯文本并进入 dead-link report。
- 最终迁移对象不得残留 `PaperNotes/` 路径、旧 assets 路径或不存在的 wikilink。

### 6.6 Auxiliary-content merge policy

- 对 `DailyPapers`、`GitHubTrending`、`ResearchSources` 和 `ResearchNotes` 同样生成 manifest 项，记录 source SHA-256、目标路径、link rewrite 和状态。
- 目标文件不存在时可按既定路由导入；目标文件存在时先比较语义和来源，只有无冲突的独有内容才可合并。
- 文件名相同、identity 不明、现有 MindFlow 手写内容无法安全分离，或引用资产缺失时，对应项标记 `blocked`；不得用时间戳或自动重命名掩盖冲突。
- `DailyPapers/.history.json` 以稳定论文 identity 合并并保持有效 JSON；不得把旧历史整体覆盖到 MindFlow，也不得把历史文件当临时文件删除。
- `GitHubTrending` 中的 repository URL 是条目 identity；`ResearchSources` 中的 URL、访问日期和原始标题继续作为 provenance，迁移不把二手内容提升为论文事实来源。

## 7. Skill and Workflow Cutover

### 7.1 Canonical ownership

MindFlow 保存以下 canonical skills：

```text
skills/1-literature/paper-digest
skills/1-literature/daily-papers
skills/1-literature/github-trending
skills/1-literature/research-insights
skills/6-orchestration/mindflow-context
```

每台电脑的 Codex discovery path 只保存软链接：

```text
~/.codex/skills/<name> -> <MindFlow clone>/skills/<category>/<name>
```

`mindflow-context` 已采用该模式；其余四项在 B2 执行。canonical skill 必须从自身 resolved path 推导 MindFlow 根目录，不能假定当前工作目录正好是 vault root。写入型 skill 的默认目标只允许是 resolved MindFlow；配置默认 `git_commit=false`、`git_push=false`。

### 7.2 Daily pipeline coverage

MindFlow `daily-papers` 是单一入口，并在一次流程中覆盖：

1. `fetch`：抓取 HuggingFace Daily/Trending 与 arXiv，评分、去重并写 `Workbench/daily/.candidates.json` 与 `.history.json`。
2. `review`：根据候选做轻量分流；对入选论文读取完整 digest 后写有证据的点评。
3. `notes`：调用 canonical `paper-digest`，将新论文笔记写入 `Papers/`，已存在笔记默认只读复用。
4. `summary/log`：写 `Workbench/daily/YYYY-MM-DD.md` 并追加 `Workbench/logs/YYYY-MM-DD.md`。

这属于功能覆盖，不逐字段复制旧 `enrich_papers.py`。旧流程对全部候选批量富化 affiliation、method、figure、caption、section header 和 real-world 标记；新流程只对入选精读论文执行完整 `paper-digest`，日报中的机构、方法和关键数字从可追溯的完整笔记获得。不得为了形式兼容恢复对全部候选的高成本批量富化。

### 7.3 Legacy retirement

以下旧全局 skills 在成功验证新流程后移入 `~/.codex/skills-legacy/<date>/`，不删除：

- `paper-reader`
- `daily-papers`、`daily-papers-fetch`、`daily-papers-review`、`daily-papers-notes`
- 旧 `github-trending`
- 旧 `research-insights`
- `author-graph` 与 `generate-mocs`；对应实体/MOC 尚未迁移，因此先停用，待后续图谱设计提供 MindFlow-compatible replacement

同名 skill 必须先比较 committed content 与本机 worktree 状态；legacy archive 记录原路径、类型、SHA-256 或 tree hash 和恢复目标。未完成 B2 前，旧 pipeline 仍是当前全局入口，不能声称已切换。

### 7.4 Bootstrap contract

仓库提供从 MindFlow clone 内运行的 bootstrap。脚本以自身路径解析 vault root，并维护固定 allowlist，不扫描任意目录：

- 目标已是指向同一 canonical skill 的软链接：no-op。
- 目标缺失：建立相对当前电脑 clone 的绝对软链接。
- 目标是普通目录、文件或指向其他位置的软链接：停止并报告冲突；未经明确迁移步骤不得覆盖。
- canonical source 缺失、名称不一致或 skill validation 失败：不创建链接。
- 重复运行必须幂等；失败不得留下半切换状态。

新电脑只需 clone MindFlow、验证运行时依赖并执行 bootstrap。project code repositories、Zotero library 和私有本地配置不由 skill bootstrap 同步；repository profile 的本地路径失效时保持显式 stale 状态。

## 8. Implementation Decomposition

该设计分为两个连续、可独立验证的 implementation plan：

### Plan A: PARA and Paper Schema Foundation

- 将 repository profile 从 PARA Project 中拆出，迁移 `pi` profile，并更新 `mindflow-context` 与 validator 的 canonical profile path。先验证 `workspace_root` 是 vault 内 `Projects/<project>` 的现存真实目录，再有界读取 wrapper 的 `main.md`、`engineering.md` 和 `workspace_entrypoints`；拒绝 absolute、`..`、目录 symlink、越界 symlink 和禁止目录，不递归扫描 `code/`。
- 将共享项目规范迁到 Codex-first `Projects/AGENTS.md`，把 `Projects/CLAUDE.md` 改为 compatibility symlink，并更新外层 `.gitignore` 的窄例外。
- 创建 `Projects/pi/` wrapper notes repo scaffold，以 `code/pi -> /Users/limx/project/pi` 接入现有代码，不物理移动 `pi`。
- 建立完整 `Workbench/PARA/{Projects,Areas,Resources,Archives}` 控制层和初始 index/Area notes。
- 新增 `Templates/RepositoryProfile.md`，将 `Templates/Project.md` 收敛为真正的 outcome-driven Project template，并新增 Area/Resource 模板、Paper Base、Paper schema/taxonomy/validator。
- 将新 Paper rating label 的 `Archived` 改为 `Peripheral`，旧笔记保持兼容、按触达渐进迁移。
- 更新 `paper-digest`、README、SPEC 和相关文档。
- 对现有 182 篇 Paper 生成 classification/identity audit；只自动补写确定性字段，ambiguous 项进入 review report。

### Plan B1: Legacy Knowledge Migration

- 生成并冻结覆盖 PaperNotes、DailyPapers、GitHubTrending、ResearchSources 和 ResearchNotes 的 migration manifest。
- 在唯一一次内容确认门中展示自动迁移、语义合并、跳过和 blocked 项；确认后不再按 commit 请求批准。
- 合并 7 个重合 Paper identity，路由 26 个仅旧 identity，并按 6.3/6.6 路由其他已批准内容。
- 只迁移实际引用的 assets，重写 links，生成迁移报告。
- 验证 source 零修改、target 无 duplicate identity、无 legacy path、无 broken migrated assets/wikilinks。
- 进入观察期；不删除旧 notes。

### Plan B2: Skill Cutover and Cross-machine Bootstrap

- 修正 canonical skills 的 vault-root 解析、默认写入路径和 git automation 默认值。
- 为 `daily-papers` 的 fetch、review、paper note、daily note、history 和 log 六类产物建立集成测试。
- 迁入并适配 `github-trending` 与 `research-insights`，验证它们只写 MindFlow 目标目录。
- 实现并测试 allowlist bootstrap、legacy archive manifest 和精确 rollback。
- 在新 skills 全部通过后才切换全局软链接；失败保持旧入口可恢复，不留下混合状态。

Authors/concepts 图谱、自动 Dashboard/MOC 和导航页属于后续设计，不与 Plan A/B 混在一次批量改写中。

## 9. Validation Strategy

### 9.1 Schema and classification

- 所有新/修改 Paper frontmatter 可解析。
- `type == paper`、`primary_domain in domains`、domain 值受控、tag 值受控。
- `review_status` 只含 `inbox | digested | reviewed`。
- 明确 arXiv/DOI 的 Paper 不得出现 duplicate identity。
- `world-action-model` 加入 taxonomy；WAM view 能返回已标注论文。
- `Papers.base` 能在 Obsidian Bases 中打开，所有 view/filter/property 引用有效。

### 9.2 Migration correctness

- Manifest 数量与盘点一致：7 个重合 identity、26 个仅旧 identity；旧 Pi0 duplicate group 明确。
- 低置信度 identity 不自动 merge。
- 每个 migrated source 都有 SHA-256、decision 和 destination。
- 迁入正文中的每个本地 asset 存在且 hash 可核验。
- 迁移对象无 `PaperNotes/`、旧 assets 路径、未知 tag、未解析模板占位符。
- 目标已有手写段落、frontmatter 和 assets 保留。
- `/Users/limx/notes` 的 HEAD、tracked diff 和任务前记录一致；现有用户修改不被触碰。
- `DailyPapers`、`GitHubTrending`、`ResearchSources`、`ResearchNotes` 的每个纳入项均有唯一 manifest decision；未批准的 author/concept/MOC 不出现在目标写集。
- 合并后的 `.history.json` 可解析、按稳定 identity 去重，并同时保留两侧不冲突的历史记录。
- `Workbench/daily/`、`Workbench/trending/`、`ResearchSources/Sources/` 和 `ResearchSources/Insights/` 中的迁移结果不残留旧 vault 绝对路径。

### 9.3 PARA behavior

- 从 `/Users/limx/project/pi` 和 `Projects/pi/code/pi` 两个入口解析 canonical realpath 时，`mindflow-context` 都唯一命中同一个 `pi` repository profile。
- Repository profile 与 PARA Project 的 `workspace_root` 都只接受 vault 内现存、非 symlink 的 `Projects/<project>` 目录；absolute path、`..`、不存在、非目录、目录 symlink 和 canonical escape 均有失败测试。
- `entrypoints` 只按 vault root 解析，`workspace_entrypoints` 只按 canonical `workspace_root` 解析；absolute path、`..`、越界 symlink、`code/`、`worklog/`、`.git/` 和目录型 entrypoint 均有失败测试。
- Repository profile 与 PARA Project schema 分离；Project 通过 `repo_refs` 引用 profile。
- Area 不复制 DomainMap 内容；Resource 不复制 Paper 内容；Archive 不改变 Paper rating 语义。
- Quartz 继续排除整个 `Projects/**`，避免发布私有项目记录和代码。
- Obsidian 只索引 project notes；窄规则至少排除 `Projects/*/code/`、`Projects/*/worklog/` 和 `Projects/*/.git/`，同时实际验证 `main.md` 与 `engineering.md` 可搜索。当前 broad `Projects/` exclusion 必须替换为经过验证的窄规则。
- MindFlow 通用知识搜索继续排除 `Projects/**`。匹配到的 repository profile 单独提供 vault `entrypoints`，以及由 profile `workspace_root` 解析的 `main.md`、`engineering.md` 和 profile `workspace_entrypoints`；selected PARA Project 另行提供单个 control-note path、由 Project `workspace_root` 解析且仅含 `main.md`/`engineering.md` 的 defaults channel，以及 vault-root `knowledge_entrypoints`。这些通道保持分离，Project 不继承 profile explicit workspace files，也不扫描 code tree。
- `Projects/AGENTS.md` 与每个 wrapper 自身的 `AGENTS.md` 均不依赖跨 nested Git root 的隐式继承。
- `git -C Projects/pi rev-parse --show-toplevel` 的 canonical 结果等于 `Projects/pi`，证明 wrapper 是独立 notes Git root；wrapper 内 `main.md`、`engineering.md` 可跟踪，`code/` 与 `worklog/` 被其 `.gitignore` 排除，外层 vault 仍忽略 `Projects/pi/`。
- `/Users/limx/project/pi` canonical path 保持不变；`test -L Projects/pi/code/pi` 成功，且 `readlink Projects/pi/code/pi` 精确返回绝对路径 `/Users/limx/project/pi`。

### 9.4 Zotero safety

- 迁移和 digest 验证不调用 connector 写接口，不修改 SQLite，不移动 collection。
- 标题多命中时返回 ambiguity，不静默选择第一项。
- Zotero unavailable 时官方来源路径仍可工作。
- item key 和 citekey 分字段保存。

### 9.5 Repository checks

- `git diff --check`。
- Paper/PARA/migration validators 和 focused unit tests 全部通过。
- 所有 repository skills 通过 skill validator。
- profile validator self-test 和 live vault check 通过。
- Quartz 只运行配置/路径相关 regression tests 和 TypeScript check；完整可视化 build 不是本迁移门禁。

### 9.6 Skill cutover and bootstrap

- 在临时 vault 与 fixture upstream 上完整验证 `fetch -> review -> paper note -> daily note -> history -> log`，六类产物内容和计数一致；测试不得依赖实时网络结果。
- `paper-digest`、`daily-papers`、`github-trending`、`research-insights` 从非 vault cwd 启动时仍解析到同一 canonical MindFlow root。
- 写入型 skill 不写 `/Users/limx/notes`，不自动 commit/push，不覆盖已有手写内容。
- bootstrap 对正确链接 no-op，对缺失目标创建链接，对真实目录、普通文件、错误链接、缺失 source 和 validation failure 均 fail closed。
- 全局链接逐一通过 `readlink` 和 canonical realpath 校验；skill validator 在 source 与 link 两个入口得到相同结果。
- rollback 只移除 bootstrap manifest 精确记录且仍匹配预期 target 的链接；目标已漂移时停止，不做宽泛删除。

## 10. Rollout and Recovery

1. 先完成 Plan A，确认 wrapper layout、PARA/dashboard/schema/Base 不改变现有知识路径或 `/Users/limx/project/pi` canonical path。
2. 对现有 Papers 运行只读 audit；人工确认 ambiguous 列表后才允许确定性 backfill。
3. B1 先生成 dry-run manifest 和 human-readable report；用户在唯一一次内容确认门确认写集后，再执行 overlaps、old-only Papers、auxiliary content 和 assets。
4. B1 可按风险拆成多个本地 commit，但已批准范围内不逐 commit 请求确认；只有 fatal blocker、范围扩大或无法保护用户内容时中断。
5. B1 全部验证通过后才进入 B2。先在 repository 与临时环境修正并验证 canonical skills，再处理全局 discovery path。
6. B2 将旧全局 skills 原样归档并写 archive manifest，再原子化建立 allowlist links；任一验证失败即停止并恢复本轮已经切换的精确条目。
7. 迁移完成后，旧 notes 保持原位并进入只读观察期；不删除、不改 remote、不自动归档。
8. merge、push、旧 notes 删除和代码仓物理移动仍是独立授权边界；已明确批准的 `pi` symlink scaffold 不等于物理移动。全局 skill cutover 只在 B2 implementation plan 获批后执行，不由设计批准自动触发。

B1 失败时只回退 MindFlow 目标分支对应 commit；源仓从未修改，不需要恢复源内容。B2 回滚只依据 archive/bootstrap manifest 恢复精确路径：删除仍指向记录 target 的新软链接，恢复 hash 未漂移的 legacy directory；任一目标发生人工修改时停止并报告，绝不递归清理 `~/.codex/skills`。

## 11. Success Criteria

- MindFlow 明确区分 repository profile 与 outcome-driven Project，并实现 Projects、Areas、Resources、Archives 四个 PARA 维度，同时保持 typed knowledge assets 的单一真源。
- 所有 project workspace 遵循 `Projects/<project>/code/<repo>` wrapper；现有外部 repo 可通过可验证 symlink 接入，未来新 repo 直接 clone 到 `code/`。
- VLA、WAM 等分类无需物理子目录即可通过 metadata、Topic、DomainMap 和 Base 稳定访问。
- 旧 PaperNotes 的 7 个重合身份得到内容保护合并，26 个仅旧身份得到明确路由，不复制自动 MOC 或未引用 assets。
- `DailyPapers`、`GitHubTrending`、`ResearchSources` 和 `ResearchNotes` 按知识类型进入 MindFlow canonical 路径；author/concept/MOC 保持范围外。
- Zotero 能作为可选本地 source 使用，但不成为 MindFlow taxonomy 或写入自动化的控制面。
- `daily-papers` 功能覆盖 fetch/review/notes，入选论文由 `paper-digest` 写入 `Papers/`，日报、历史和日志全部写入 MindFlow；旧 notes 不再继续产生新的论文 split-brain。
- canonical skills 可随 MindFlow clone 跨电脑复用；bootstrap 幂等、冲突 fail closed、legacy 可精确恢复。
- 旧 notes 零修改且保留可恢复来源；任何删除、merge、push、全局 skill 改动都未被本设计默认授权。

## 12. Evidence Used

- `docs/SPEC.md`：当前 typed knowledge assets、code repositories 和 Workbench 三分结构。
- `Projects/CLAUDE.md`：project notes repo、`code/<repo>`、worklog 与三层 Git 的既有推荐；本设计保留其布局并迁为 Codex-first instructions。
- `docs/superpowers/specs/2026-10-28-cross-repo-mindflow-context-design.md`：profile、read-only knowledge lane 和 Zotero independent 边界；其中 direct-root 决策由本设计的 wrapper 决策取代。
- `references/tags.md`：现有 canonical tag taxonomy。
- `skills/1-literature/paper-digest/SKILL.md` 与 `references/paper-note-template.md`：当前扁平 Paper 路径、schema、去重和写入规则。
- `skills/1-literature/daily-papers/SKILL.md` 与 `fetch_and_score.py`：MindFlow 的抓取、分流、digest、日报、历史和日志协议。
- 当前全局 skill inventory：旧 `paper-reader`、三段式 daily skills、`github-trending`、`research-insights` 仍为普通目录；仅 `mindflow-context` 已链接到 MindFlow canonical skill。
- `/Users/limx/notes/{DailyPapers,GitHubTrending,ResearchSources,ResearchNotes}` 的只读 inventory：分别有 1、1、10、1 个 Markdown，作为 B1 路由与 manifest 数量依据。
- `DomainMaps/VLA.md`、`DomainMaps/WorldModel.md`、`Topics/WorldActionModel-Survey.md`：WAM 跨 VLA/World Model 的知识证据。
- 当前只读 inventory：旧 notes 与 MindFlow 的数量、identity、schema、link 和 asset 差异。
