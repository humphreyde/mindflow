# MindFlow Cross-Repository Research Context Design

> **Date**: 2026-10-28
> **Status**: Approved direction; pending written-spec review
> **Decision**: 以全局 `mindflow-context` bridge 将 MindFlow 作为代码项目的只读研究知识层；源码检索与知识检索保持独立
> **Pilot**: `/Users/limx/project/pi`，暂不移动代码仓

---

## 1. Context

MindFlow 已经包含 `Papers/`、`Topics/`、`DomainMaps/`、`Ideas/`、`Experiments/`、`Projects/` 和 `Workbench/memory/` 等研究资产。用户希望在开发 `pi`、`gr00t`、`fastwam` 等代码仓时，Codex 能按任务读取这些资产，尤其是论文知识，而不复制论文到代码仓，也不把整个 vault 一次性装入上下文。

未来多数代码仓会直接位于 `MindFlow/Projects/<repo>`，每个目录仍是独立 Git 仓库；只有一个项目横跨多个代码仓时才增加 workspace wrapper。`pi` 当前继续位于 `/Users/limx/project/pi`，先作为外部仓库试点。

物理嵌套不能自动解决 Codex discovery：从独立代码 Git 根启动时，父级 MindFlow `AGENTS.md` 和 repo-scoped skills 不会自然成为该任务的执行契约。因此需要显式的全局触发器、单个全局可发现 skill 和项目 profile。

## 2. Goals and Non-Goals

### Goals

1. 在代码仓中执行研究、架构、实验设计、方法选择或历史决策任务时，Codex 自动检索相关 MindFlow 知识。
2. 在代码修改、诊断、测试、review 或实现解释中，Codex 始终可按需检索当前源码，不受知识检索排除规则影响。
3. 通过项目 profile 缩小搜索范围，初始读取 5–8 篇高相关笔记，必要时沿 wikilink 扩展一跳，总量约束在 12 篇以内。
4. 明确区分代码证据、论文笔记、历史记录和 Codex 推断。
5. MindFlow 默认只读；任务结束时只提出建议沉淀项，获得用户确认后才写入。
6. 支持当前外部 `pi`，并能在未来平滑支持 `Projects/<repo>` 直接代码仓布局。
7. 源码、checkpoint、日志和生成物不进入 Obsidian 知识索引或 Quartz 发布范围。

### Non-Goals

- 本阶段不移动 `pi`、`gr00t`、`fastwam` 或其他代码仓。
- 不迁移 `/Users/limx/notes`；其合并需要单独的去重与内容保护方案。
- 不引入向量数据库、embedding 服务或常驻 RAG 服务。
- 不自动修改 Paper、Topic、DomainMap、Idea、Experiment 或项目页。
- 不自动 commit、push 或跨仓库合并写入。
- 不复制或全局链接 MindFlow 的整棵 `skills/`。
- 不把 Zotero 并入 MindFlow；只有明确需要原文、元数据或 citekey 时才单独查询 Zotero。
- 不把 Quartz 的完整网站构建或视觉验收作为本 MVP 的完成条件。

## 3. Decisions

### 3.1 Projects layout

默认布局为：

```text
mindflow/
├── Papers/
├── Topics/
├── DomainMaps/
├── Workbench/
│   └── PARA/
│       └── Projects/
│           ├── pi.md
│           ├── gr00t.md
│           └── fastwam.md
└── Projects/
    ├── gr00t/       # 独立代码 Git 根
    ├── fastwam/     # 独立代码 Git 根
    └── ...
```

`Projects/<repo>` 默认直接是代码仓根目录。只有一个项目涉及多个代码仓时，才采用 `Projects/<project>/code/<repo>` 形式。PARA 项目目标、关联论文、进展和研究结论记录在 `Workbench/PARA/Projects/<repo>.md`，不要求写入公开代码仓。

当前 `Projects/CLAUDE.md` 的 wrapper-only、独立 notes repo 约定与此决策冲突，但 `pi` 外部试点不依赖该文件。MVP 不修改 `Projects/` 共享规范；在第一个代码仓实际迁入前，必须通过单独批准的变更建立 Codex-first `Projects/AGENTS.md`、修订 `Projects/CLAUDE.md` compatibility，并明确父级文件不会自动穿透嵌套 Git 根。

### 3.2 Two retrieval lanes

源码检索和 MindFlow 知识检索是两条独立通道。

| 任务类型 | 源码通道 | MindFlow 通道 |
|---|---|---|
| 改代码、修 bug、测试、review | 必须按任务读取相关实现 | 默认不触发 |
| 架构、实验设计、方法选择 | 先确认当前实现和约束 | 自动触发 |
| 解释论文或通用概念 | 通常不需要 | 自动触发 |
| 论文与实现对应 | 必须 | 必须 |
| 格式化、机械重构 | 只读取必要源码 | 不触发 |

源码通道以当前仓库为默认范围，从 `AGENTS.md`、相关文档、配置、测试、入口符号和调用链开始窄范围检索。只有存在明确依赖、当前代码引用或用户指定时，才扩展到另一个代码仓。当前代码是实现事实的最高优先级；MindFlow 为研究证据；Codex 推断必须明确标注。

“排除 `Projects/**`”只约束 Obsidian/Quartz 和 MindFlow 知识搜索，不限制 Codex 在开发任务中读取源码。

## 4. Runtime Architecture

### 4.1 Global trigger

`~/.codex/AGENTS.md` 当前为空。MVP 在其中增加一段最小条件规则：

- 当前任务涉及研究、架构、实验设计、方法选择、论文与实现映射或历史决策，或用户明确要求使用 MindFlow 时，使用 `$mindflow-context`。
- 当前仓库是否匹配 MindFlow profile 或位于 `MindFlow/Projects/` 下，只决定使用项目化检索还是通用 fallback，不决定是否触发。
- 机械性格式修复、普通测试修复或不需要研究背景的局部代码修改不触发。
- 该规则只决定是否检索研究知识，不限制正常源码读取。

全局文件不保存项目详情；所有项目语义进入 MindFlow profile。

### 4.2 Canonical skill and global discovery

新 skill 的唯一源码位置为：

```text
skills/6-orchestration/mindflow-context/
├── SKILL.md
├── references/
│   └── smoke-tests.md
└── scripts/
    └── validate_profiles.py
```

它遵循 `references/skill-protocol.md`，至少包含 `Purpose`、`Inputs`、`Steps`、`Guard`、`Verify` 和 `Examples`。`validate_profiles.py` 是 Python 3.12+、无第三方依赖、严格只读的 profile schema/path validator；运行时知识搜索仍由 skill 按 `rg` 协议完成，不增加常驻服务或索引。`smoke-tests.md` 固定记录人工 Codex 触发矩阵和预期结果，不定义第二个 skill。

外部仓库通过一个单独的全局 discovery link 访问 canonical skill：

```text
~/.codex/skills/mindflow-context
  -> /Users/limx/mindflow/skills/6-orchestration/mindflow-context
```

不得复制 skill，也不得把整个 MindFlow `skills/` 链接到全局或代码仓。MindFlow 内部继续通过 `.agents/skills -> ../skills` 发现 canonical tree。安装 link 后必须分别从 MindFlow 根和外部 `pi` 检查 discovery；两个环境都应只出现一个可调用的 `mindflow-context`，并解析到同一 realpath。若出现同名重复或歧义，本地 integration 不得验收，也不得假设 Codex 会自动去重。

新增后 skill 总数由 14 变为 15；`README.md`、`docs/INSTALL.md`、`docs/SPEC.md` 和 `references/skill-protocol.md` 的 active inventory 必须同步更新。

### 4.3 Project profiles

项目 profile 是基于 `Templates/Project.md` 的普通 Obsidian note，默认位于：

```text
Workbench/PARA/Projects/<repo-key>.md
```

建议 frontmatter：

```yaml
---
title: OpenPI
type: project
repo_key: pi
repo_roots:
  - /Users/limx/project/pi
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
status: active
verified_at: 2026-10-28
---
```

相对 `repo_roots` 按 MindFlow 根解析，`~` 在匹配时展开。MVP 只记录实际存在的 `/Users/limx/project/pi`；`pi` 实际移动后再将新路径加入 profile。不得把计划路径标记为已验证路径。路径迁移只更新 profile，不改 skill。`verified_at` 表示 profile 的仓库映射和知识入口最后核对日期，不表示代码或运行状态仍然有效。

MVP 只创建 `pi` profile。`gr00t`、`fastwam` 在仓库实际移动或接入时再各自创建，不预填未经核实的路径和关键词。

## 5. Retrieval Protocol

### 5.1 Trigger and profile resolution

1. 确认当前任务是否符合研究知识触发条件。
2. 通过当前 Git 根、展开后的 `repo_roots`、`repo_key` 和 aliases 匹配 profile。
3. 精确路径优先于 repo 名和 alias；如果多个 profile 同时匹配，停止自动选择并请求用户确认。
4. 没有 profile 时进入通用 fallback，以仓库名、任务关键词和当前代码符号检索全库，并明确报告未使用项目 profile。

### 5.2 Query construction and search order

查询词来自：

- 用户任务描述中的模型、方法、数据集、论文和实验术语。
- 当前源码通道发现的关键模块、symbol、配置名和算法名。
- profile 的 domains、aliases、keywords 和 entrypoints。

搜索顺序：

1. profile 的 `entrypoints`
2. `DomainMaps/`
3. `Topics/`
4. `Workbench/memory/`
5. `Papers/`
6. `Ideas/`、`Experiments/` 和项目 profile

候选按以下优先级排序：profile 或笔记中的显式链接、精确标题/arXiv ID/DOI/citekey、frontmatter alias/tag、正文命中。第一轮读取 5–8 篇；仅当已有证据指出相关链接时扩展一跳，总读取量默认不超过 12 篇。

默认排除：

- `Projects/**` 代码树
- `.git/`、`.website/`、`.worktrees/`
- `assets/` 和大型媒体
- checkpoint、模型、数据、日志、cache、build 输出
- `Private/`、`Meetings/`
- `Workbench/logs/`；只有追溯具体历史决策时才显式进入

### 5.3 Result contract

使用知识时必须区分：

- **代码证据**：当前实现、配置、测试或仓库文档。
- **论文笔记**：MindFlow Paper/Topic/DomainMap 中有来源的结论。
- **历史记录**：memory、Experiment 或项目页中的时间性证据。
- **Codex 推断**：基于前述证据的推理，不得伪装成原始事实。

结果引用具体文件路径和 heading。若 MindFlow 没有匹配证据，应明确写出“MindFlow 中未找到相关证据”，继续使用可用的代码证据或请求下一步，而不是编造来源。

## 6. Writeback Protocol

MindFlow 默认只读。只有任务产生可复用的新知识时，最终回复增加一个可选区块：

```text
建议沉淀
- 目标：Papers / Topics / DomainMaps / Ideas / Experiments / Project
- 内容：拟写入的核心结论
- 证据：代码路径、commit、实验产物或论文来源
- 理由：为什么值得长期保留
```

用户可以批准全部、部分或拒绝。未获得明确批准时，不能修改任何 MindFlow note、profile、memory 或日志。

批准写回后：

1. 重新读取 MindFlow `AGENTS.md`、相关 reference、template 和目标 note。
2. 保护现有 frontmatter、wikilink 和手写内容，使用最小兼容修改。
3. 按知识归属路由：
   - 单篇论文结论 → `Papers/`
   - 跨论文综合 → `Topics/` 或 `DomainMaps/`
   - 新假设 → `Ideas/`
   - 实验计划与结果 → `Experiments/`
   - 工程决策、研究进展 → 项目 profile
   - 跨项目通用工作流 → `skills/`，但必须获得单独的明确授权
4. 代码仓和 MindFlow 分别检查 diff、验证和提交；一次批准写入不自动授权 commit 或 push。

## 7. Failure and Safety Handling

- **Profile missing**：使用通用 fallback，并在结果中提示创建 profile 是可选改进，不阻塞开发。
- **Profile stale**：如果 `repo_roots` 不匹配或入口不存在，报告具体字段；不得静默改写 profile。
- **Ambiguous project**：多个 profile 匹配时请求用户选择。
- **Broken link or unreadable note**：跳过并报告，不把缺失内容当证据。
- **Contradictory notes**：并列呈现冲突及各自来源，不自动合并或覆盖旧结论。
- **Sensitive data**：不得把凭据、token、私有地址、相机序列号、大日志、checkpoint 或未经筛选的运行产物写入 vault。
- **Dynamic state**：branch、commit、主机、服务、checkpoint 和实验状态必须附 `verified_at` 或当前验证证据。
- **No write authorization**：通过前后文件 hash 或 Git diff 证明检索任务未修改 MindFlow。

## 8. Publication and Indexing Boundaries

外层 MindFlow Git 继续忽略 `Projects/*`，使其中代码仓保持独立 Git 边界。共享规范文件通过窄范围 exception 跟踪。

Quartz `ignorePatterns` 增加 `Projects/**`，避免代码仓 Markdown、资产和内部文档被发布。项目 profile 位于已经被 Quartz 排除的 `Workbench/**`，因此不会公开。

Obsidian 本地配置增加 `Projects/` excluded-files filter，避免索引整个代码树。该设置只影响 Obsidian 搜索和图谱，不限制 Codex 源码通道。

## 9. MVP Implementation Scope

### Tracked MindFlow changes

- 新建 `skills/6-orchestration/mindflow-context/{SKILL.md,references/smoke-tests.md,scripts/validate_profiles.py}`；MVP 不再增加其他 helper。
- 扩展 `Templates/Project.md` 的 profile 字段，同时保留现有 Goal、Papers、Ideas、Progress 和 Results 结构。
- 新建 `Workbench/PARA/Projects/pi.md` 作为唯一试点 profile。
- 更新 `.website/quartz.config.ts`，排除 `Projects/**`。
- 将 active skill inventory 从 14 更新为 15：`README.md`、`docs/INSTALL.md`、`docs/SPEC.md` 和 `references/skill-protocol.md`。历史 specs/plans 保持不变。

### Local machine integration

- 向当前为空的 `~/.codex/AGENTS.md` 增加条件触发规则。
- 创建单个 `~/.codex/skills/mindflow-context` discovery link。
- 在 `.obsidian/app.json` 配置本地 `Projects/` 排除项；`.obsidian/` 继续不进入 Git。

### Explicitly deferred

- 移动任何代码仓。
- 创建 `gr00t`、`fastwam` 或其他未经核实的 profile。
- 修改 `Projects/CLAUDE.md`、新增 `Projects/AGENTS.md` 或调整共享 exception；这些是第一个仓库迁入前的独立任务。
- `/Users/limx/notes` 合并。
- 向量索引或外部检索服务。
- Quartz 视觉修改和完整网站发布验收。

## 10. Validation Strategy

### Automated static and profile checks

- 使用 Codex `skill-creator` validator 验证全部 15 个 `SKILL.md`。
- 验证 `mindflow-context` 的 name、目录名、required sections 和 Guard/Verify 一致。
- 验证 `.agents/skills` 仍指向唯一 canonical tree，repo discovery 数量为 15。
- 验证单个全局 link 指向 canonical `mindflow-context`，没有复制或暴露整棵 skill tree；从 MindFlow 根和外部 `pi` 检查时，各自只发现一个同名 skill。
- 执行以下只读 profile 检查：

  ```bash
  uv run python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault . --self-test
  uv run python skills/6-orchestration/mindflow-context/scripts/validate_profiles.py --vault .
  ```

  `--self-test` 必须在临时目录覆盖 valid、missing field、stale root、missing entrypoint、ambiguous match 和 relative-root resolution 六类 fixture，并输出 6/6 passed；真实 vault 检查必须确认 `pi` profile 唯一匹配当前外部 Git 根。
- 扫描 `README.md`、`docs/INSTALL.md`、`docs/SPEC.md` 和 `references/skill-protocol.md`，确保 active inventory 无旧的 14-skill 计数。

### Manual Codex smoke matrix

`references/smoke-tests.md` 固定以下 prompts、执行目录、应读取/不应读取的范围和通过条件：

1. 从 `/Users/limx/project/pi` 发起研究/架构任务：命中 `pi` profile，同时读取相关代码和 MindFlow 证据。
2. 从同一仓库发起普通格式或局部测试修复：读取必要源码但不触发 MindFlow。
3. 解释通用论文概念：检索 MindFlow，但不无故扫描代码仓。
4. 执行论文与实现对应任务：两条通道同时工作，来源标签正确。
5. 在 `MindFlow/Projects/` 下没有 profile 的临时仓库中运行，或从普通外部无 profile 仓库发起研究类 prompt（不显式调用 skill）：自动触发并进入通用 fallback，明确提示 profile 缺失；显式调用 `$mindflow-context` 也遵循同一 fallback。
6. 构造无匹配查询：明确报告没有 MindFlow 证据。
7. 只读检索前后比较 MindFlow 文件 hash 和 Git 状态：零修改。
8. 生成“建议沉淀”后不批准：零修改。
9. 在临时 fixture vault 中批准写回：只修改指定目标，保留既有手写段落。

### Exclusion and regression checks

- 用 Quartz glob/配置测试确认 `Projects/**` 不进入输入文件或 assets；不以完整 Quartz build 作为本 MVP 门禁。
- 验证 Obsidian excluded-files 配置包含 `Projects/`。
- 从代码仓执行窄范围源码搜索，确认排除规则没有阻断 Codex 读取代码。
- 对原有 14 个 skills 和新增 skill 全部运行 `skill-creator` validator；不声称仓库存在当前并不存在的通用 workflow fixture harness。
- 从 `.website/` 运行 `npm test` 和 `npm run check`，再运行 Markdown/YAML、`git diff --check`；完整 Quartz build 不作为本 MVP 门禁。

## 11. Rollout Order

1. 新增 `mindflow-context` canonical skill 和 profile schema。
2. 创建 `pi` profile，并完成 profile resolution、知识搜索和 read-only fixtures。
3. 更新 global trigger 与单 skill discovery link，从外部 `pi` 验证实际触发。
4. 修订 skill inventory 和安装文档。
5. 加入 Obsidian/Quartz exclusion，验证源码通道仍可工作。
6. 运行静态、行为和回归检查，审核所有 tracked/local changes。
7. 试用一段时间后，再按实际路径为 `gr00t`、`fastwam` 增加 profile；不预先迁移代码。

## 12. Success Criteria

- 从外部 `pi` 仓库执行研究型开发任务时，Codex 能自动发现 `$mindflow-context`、解析 `pi` profile，并引用相关 MindFlow 笔记。
- 机械性代码任务不触发研究检索；所有代码任务仍可按需读取当前源码。
- 搜索上下文有明确上限、来源标签和无证据回退，不把整个 vault 或代码仓装入上下文。
- 未获得写回批准时，MindFlow Git 状态和文件 hash 不变化。
- 获得批准后，只修改明确目标并保护用户手写内容。
- `Projects/<repo>` 可以直接作为独立代码 Git 根；多仓 wrapper 仍受支持。
- `Projects/**` 不进入 Quartz、Obsidian 知识索引或 MindFlow 知识搜索，但不阻断 Codex 源码通道。
- MindFlow 内可发现 15 个 canonical skills，外部仓库只全局暴露 `mindflow-context`，原有 14 个 skills 无回归。

## References

- [MindFlow Skill Protocol](../../../references/skill-protocol.md)
- [MindFlow Project Template](../../../Templates/Project.md)
- [Build skills — Codex](https://developers.openai.com/codex/skills)
- [Custom instructions with AGENTS.md — Codex](https://developers.openai.com/codex/guides/agents-md)
