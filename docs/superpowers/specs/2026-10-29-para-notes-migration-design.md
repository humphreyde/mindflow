# MindFlow PARA Notes Migration Design

> **Date**: 2026-10-29
> **Status**: Approved direction; pending written-spec review
> **Decision**: 将 MindFlow 建成个人 PARA 研究工作区；PARA 管行动与生命周期，typed knowledge assets 管长期知识；旧 `notes` 选择性迁移，Zotero 保持独立
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
├── Projects/                # 独立 Git 代码仓；不进入知识索引/发布
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

- `Projects/<repo>` 默认直接是独立代码 Git 根；多仓项目才使用 wrapper。
- `Workbench/RepositoryProfiles/<repo_key>.md` 保存 `repo_key/repo_roots/aliases/domains/entrypoints/keywords/verified_at`，供 `mindflow-context` 匹配仓库。
- `Workbench/PARA/Projects/<project_key>.md` 描述明确 outcome、完成条件和生命周期，通过 `repo_refs` 引用一个或多个 repository profile。
- Project 使用 `planning | active | paused | completed`；同一 repo 可以被多个 Project 复用，同一 Project 也可以引用多个 repo。
- Project 完成时，先写 final outcome 与代码 provenance，再把 Project control note 移至 `Workbench/PARA/Archives/Projects/`。
- 移动 Project note 不移动 repository profile，也不自动移动或删除代码仓；代码仓归档是独立授权动作。
- `pi` 继续位于 `/Users/limx/project/pi`，本阶段不移动。

Repository profile 最小 schema：

```yaml
---
type: repository-profile
repo_key: pi
repo_roots:
  - /Users/limx/project/pi
aliases: [openpi, pi07]
domains: [VLA, RECAP, TRON2]
entrypoints:
  - DomainMaps/VLA.md
keywords: [ACP, RTC, pi0]
verified_at: 2026-10-29
---
```

PARA Project 最小 schema：

```yaml
---
type: project
project_key:
outcome:
completion_criteria: []
status: planning
target_date:
repo_refs: []
area_refs: []
knowledge_entrypoints: []
---
```

现有 `Workbench/PARA/Projects/pi.md` 先迁为 `Workbench/RepositoryProfiles/pi.md`。不把“维护 pi 仓库”伪造为一个无结束条件的 PARA Project；首个真实 Project 在有明确 outcome 时创建。

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
- 242 个 author entities、199 个 concept entities、导航/代码笔记：本阶段不迁移；后续作为独立图谱项目评估。
- `DailyPapers`、`ResearchNotes`、`ResearchSources`、`GitHubTrending` 等旧 notes 其他目录：不在本 Paper migration plan 中批量搬运，后续按知识类型和 PARA lifecycle 单独盘点。

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

## 7. Skill and Workflow Cutover

- MindFlow 内新的论文阅读和笔记生成使用 canonical `paper-digest`。
- `paper-digest` 更新 schema、分类、稳定 identity 与可选只读 Zotero lookup，但保持单篇目标和最小写入边界。
- 旧全局 `paper-reader` 在迁移期间视为 legacy；不得让它与 `paper-digest` 同时向两个 vault 生成新笔记。
- 修改、禁用或删除全局 `paper-reader` 属于仓库外 integration，需在 MindFlow 迁移验证后单独执行；本阶段只记录 cutover requirement，不改全局 skill。
- `daily-papers` 同名冲突和旧 notes 自动 commit/push 配置不在本迁移实现中处理；在正式切换 daily pipeline 前单独解决。

## 8. Implementation Decomposition

该设计分为两个连续、可独立验证的 implementation plan：

### Plan A: PARA and Paper Schema Foundation

- 将 repository profile 从 PARA Project 中拆出，迁移 `pi` profile，并更新 `mindflow-context` 与 validator 的 canonical profile path。
- 建立完整 `Workbench/PARA/{Projects,Areas,Resources,Archives}` 控制层和初始 index/Area notes。
- 新增 `Templates/RepositoryProfile.md`，将 `Templates/Project.md` 收敛为真正的 outcome-driven Project template，并新增 Area/Resource 模板、Paper Base、Paper schema/taxonomy/validator。
- 将新 Paper rating label 的 `Archived` 改为 `Peripheral`，旧笔记保持兼容、按触达渐进迁移。
- 更新 `paper-digest`、README、SPEC 和相关文档。
- 对现有 182 篇 Paper 生成 classification/identity audit；只自动补写确定性字段，ambiguous 项进入 review report。

### Plan B: Legacy Paper Migration

- 生成并冻结 migration manifest。
- 合并 7 个重合身份，路由 26 个仅旧身份。
- 迁移实际引用的 assets，重写 links，生成迁移报告。
- 验证 source 零修改、target 无 duplicate identity、无 legacy path、无 broken migrated assets/wikilinks。
- 进入观察期；不删除旧 notes。

Authors/concepts 图谱和其他 notes 目录属于后续设计，不与 Plan A/B 混在一次批量改写中。

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

### 9.3 PARA behavior

- Repository profile 仍能被 `mindflow-context` 唯一解析。
- Repository profile 与 PARA Project schema 分离；Project 通过 `repo_refs` 引用 profile。
- Area 不复制 DomainMap 内容；Resource 不复制 Paper 内容；Archive 不改变 Paper rating 语义。
- `Projects/**` 继续不进入 Quartz、Obsidian 知识索引或 MindFlow knowledge search。
- `pi` 外部路径保持不变。

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

## 10. Rollout and Recovery

1. 先完成 Plan A，确认 PARA/dashboard/schema/Base 不改变现有知识路径。
2. 对现有 Papers 运行只读 audit；人工确认 ambiguous 列表后才允许确定性 backfill。
3. Plan B 先生成 dry-run manifest，再逐批执行 overlaps、old-only notes、assets。
4. 每批独立 commit、验证和 review；范围内本地 commit 无需逐个请求用户批准。
5. 迁移完成后，旧 notes 保持原位并进入只读观察期；不删除、不改 remote、不自动归档。
6. merge、push、旧 notes 删除、全局 skill cutover 和代码仓移动仍是独立授权边界。

若某批验证失败，回退目标分支对应 commit 即可；源仓从未修改，不需要恢复源内容。

## 11. Success Criteria

- MindFlow 明确区分 repository profile 与 outcome-driven Project，并实现 Projects、Areas、Resources、Archives 四个 PARA 维度，同时保持 typed knowledge assets 的单一真源。
- VLA、WAM 等分类无需物理子目录即可通过 metadata、Topic、DomainMap 和 Base 稳定访问。
- 旧 PaperNotes 的 7 个重合身份得到内容保护合并，26 个仅旧身份得到明确路由，不复制自动 MOC 或未引用 assets。
- Zotero 能作为可选本地 source 使用，但不成为 MindFlow taxonomy 或写入自动化的控制面。
- 新论文工作流只面向 MindFlow canonical schema；旧 notes 不再继续产生新的论文 split-brain。
- 旧 notes 零修改且保留可恢复来源；任何删除、merge、push、全局 skill 改动都未被本设计默认授权。

## 12. Evidence Used

- `docs/SPEC.md`：当前 typed knowledge assets、code repositories 和 Workbench 三分结构。
- `docs/superpowers/specs/2026-10-28-cross-repo-mindflow-context-design.md`：Projects direct-root、profile、read-only knowledge lane 和 Zotero independent 边界。
- `references/tags.md`：现有 canonical tag taxonomy。
- `skills/1-literature/paper-digest/SKILL.md` 与 `references/paper-note-template.md`：当前扁平 Paper 路径、schema、去重和写入规则。
- `DomainMaps/VLA.md`、`DomainMaps/WorldModel.md`、`Topics/WorldActionModel-Survey.md`：WAM 跨 VLA/World Model 的知识证据。
- 当前只读 inventory：旧 notes 与 MindFlow 的数量、identity、schema、link 和 asset 差异。
