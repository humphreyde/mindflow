# MindFlow Codex-First Migration Design

> **Date**: 2026-10-13
> **Status**: Approved direction; pending written-spec review
> **Decision**: Codex-first，保留轻量 Claude compatibility
> **Scope**: Codex discovery、14 个研究 skills、安装文档、运行协议，以及会阻断迁移后工作流的现有漂移

---

## 1. Context

MindFlow 已经有完整的 Obsidian 研究工作区和 14 个 `SKILL.md`，但当前 agent 集成主要围绕 Claude Code：

- 安装文档只把 skills 链接到 `.claude/skills/`。
- `references/skill-protocol.md` 以 Claude Code frontmatter 和工具名为规范。
- skill 正文直接写 `Read`、`Write`、`Edit`、`Glob`、`Grep`、`Task`、`WebSearch`、`WebFetch`。
- `literature-survey` 假设存在 Claude `Task` 子代理。
- 仓库根目录已有 `AGENTS.md`，但主要记录 Owner 和知识库背景，缺少 Codex 执行约定。

Codex 官方约定是：

- 项目 skills 从仓库路径上的 `.agents/skills/` 自动发现；symlink 受支持。
- 每个 skill 至少包含 `SKILL.md`，frontmatter 必须有 `name` 和 `description`。
- 仓库级持续指令写在 `AGENTS.md`，并按目录层级合并。

因此迁移不是替换品牌名，而是把“发现入口、协议和执行语义”切换到 Codex，同时不破坏现有 Obsidian 内容和 Claude 使用路径。

## 2. Goals and Non-Goals

### Goals

1. 从仓库根目录启动 Codex 时，14 个 MindFlow skills 可被自动发现和显式调用。
2. `SKILL.md` 遵循 Codex/Open Agent Skills 可验证格式。
3. skill 正文描述能力和产出，不依赖某个 agent 的专有工具名称。
4. `AGENTS.md` 同时承载现有 Owner context 和可执行的仓库规则。
5. README、安装文档、skill protocol 默认介绍 Codex；Claude 作为兼容路径保留。
6. 修复会让迁移后工作流立即失败的引用、目录和 schema 漂移。
7. 保留全部用户笔记、Obsidian wikilink/frontmatter 和 Quartz 发布能力。

### Non-Goals

- 不批量改写现有论文笔记、DomainMaps、Ideas 或其他用户内容。
- 不把 skills 打包成 Codex plugin；本次采用 repo-scoped skills。
- 不新增 `agents/openai.yaml`；当前没有必须提供的 UI 图标、MCP dependency 或特殊 invocation policy。
- 不重新设计 MindFlow 的研究方法论或 6 层 skill 架构。
- 不自动发布网站、不改远端仓库、不安装全局软件。

## 3. Runtime Integration

### 3.1 Canonical skill tree

继续以现有 `skills/` 为唯一源码目录，新增：

```text
.agents/
└── skills -> ../skills
```

这样可以同时满足：

- Codex 按官方路径发现 skills。
- Obsidian 中现有目录结构和 wikilink 不变。
- 不复制 14 份 skill，不产生双份漂移。

### 3.2 Repository instructions

保留根 `AGENTS.md` 中的 Owner、研究原则和目录说明，在文件前部增加 Codex 执行契约：

- 先读相关 protocol/template，再修改知识库。
- 保留用户已有内容，禁止无授权覆盖或批量重写。
- 搜索优先使用 `rg`，编辑使用精确 patch，Git 只窄范围 staging。
- 说明 14 个 skills 的发现位置与调用方式。
- 列出验证命令和 website/paper scripts 的依赖边界。
- 明确 Obsidian Markdown 与 wikilink 约束。

现有 `CLAUDE.md -> AGENTS.md` symlink 保留，作为 Claude compatibility 的项目上下文入口。

## 4. Skill Format and Execution Semantics

### 4.1 Frontmatter

14 个 skill 统一保留 Open Agent Skills 的可移植字段：

```yaml
---
name: paper-digest
description: 明确说明做什么、何时触发，以及关键边界。
---
```

具体规则：

- `name` 必须与 skill 目录名一致，使用 kebab-case。
- `description` 前置触发场景，控制在 1024 字符内。
- 删除 Claude-only 或当前 Codex validator 不接受的 `argument-hint`、`user-invocable`。
- 删除平台工具 allowlist；权限由运行时和用户策略决定，不在 workflow 文本里伪装成安全边界。
- 输入格式、内部调用属性等信息移到正文，不再塞进非标准 frontmatter。

### 4.2 Capability-oriented language

正文统一从工具名改成操作意图：

| 当前写法 | 迁移后写法 |
|---|---|
| `用 Read 打开...` | `读取...` |
| `用 Glob/Grep 搜索...` | `在指定目录中搜索...` |
| `用 Write/Edit 写入...` | `创建文件或精确更新目标段落...` |
| `用 WebSearch/WebFetch...` | `使用当前环境可用的联网搜索与网页读取能力...` |
| `用 Task 启动子代理...` | `在能力可用且任务独立时并行；否则顺序执行同一流程...` |

Shell、Python、Node 命令仍可保留，因为它们是可执行实现细节；每条命令必须注明前置依赖、输入、输出和失败回退。

### 4.3 Skill composition

- 用户可通过 `$skill-name` 显式调用，也可由 `description` 匹配隐式触发。
- 编排 skill 不假设存在专有“调用另一个 skill”工具；它按名称定位并完整读取目标 `SKILL.md`，再执行其 Steps、Guard 和 Verify。
- 并行只是优化项：仅在运行时具备能力、任务相互独立且没有共享写入时使用；否则顺序执行。
- 三个缺少 `## Guard` 的 literature skills 补齐写入边界、来源真实性、网络失败与用户内容保护规则。

## 5. Installation and Documentation

`README.md` 与 `docs/INSTALL.md` 改为 Codex-first：

1. 安装 Codex CLI 或使用支持 repo-scoped skills 的 Codex 桌面环境。
2. clone 后确认 `.agents/skills` symlink 有效。
3. 从仓库根目录启动 Codex，使根 `AGENTS.md` 和全部 skills 被发现。
4. 提供 `$paper-digest`、`$daily-papers`、`$literature-survey` 等示例。
5. 列出运行时依赖：
   - Git；Obsidian（知识库 UI）。
   - Python 3；`uv`（PDF 提取与可重复临时依赖环境）。
   - Node.js/npm（paper HTML 提取至少 Node 18；Quartz 按自身要求 Node 20+）。
   - `gh` 为 GitHub metadata 的可选增强，缺失时降级到公开 API。
6. 将 Claude Code 安装方式放到单独的 compatibility 小节，不再作为默认入口。

## 6. Blocking Drift Repairs

本次只修复会直接影响 Codex 使用或迁移验证的漂移：

1. **Skill inventory**：README 的 `13` 改为实际的 `14`，补上 `daily-papers`。
2. **Removed skill reference**：将 `autoresearch` 和协议中已不存在的 `cross-paper-analysis` 语义并入现有 `literature-survey` 的“已有论文对比”模式，清除活动运行路径中的失效引用。
3. **Experiment output path**：加入可跟踪的 `Experiments/` 入口，并让相关 skills 在写入前确认目录存在；保留 `Templates/Experiment.md` 作为 schema 来源。
4. **Memory lifecycle**：`Workbench/logs/` 保持 append-only；memory 条目允许窄范围追加 evidence/occurrences 和更新 status/confidence，但不得删除历史，且必须写 evolution changelog。同步修正文档与 `memory-distill`。
5. **Paper metadata**：Quartz `PaperMeta.tsx` 优先读取现行 `institutes`，同时兼容旧的 `institute`。
6. **Guard completeness**：为 `daily-papers`、`literature-survey`、`paper-digest` 增加 `## Guard`。
7. **Docs and examples**：当前规范文档中的旧 skill 树、Claude 工具表和失效示例一并更新；历史设计文档保持不动，避免改写历史记录。

## 7. Validation Strategy

### Static validation

- 对 14 个 skill 逐一运行 Codex `skill-creator` 附带的 `quick_validate.py`。
- 检查 skill 名称与父目录一致、frontmatter 只有受支持字段、描述非空。
- 检查每个 skill 都有 `Purpose`、`Steps`、`Guard`，有写入行为的 skill 还应有 `Verify`。
- 扫描活动文档和 skill，确认不存在失效的 `cross-paper-analysis`、Claude 专有工具调用或错误的 `.claude` 默认安装说明。
- 验证 `.agents/skills` symlink 指向唯一 canonical tree。

### Script and workflow smoke tests

- Python helpers 至少通过 `py_compile` 和 `--help`/无网络参数检查。
- Node helper 通过语法检查；不在测试中强制抓取外网或安装大型 PDF 依赖。
- 用临时目录验证一个只读 skill、一个写入 skill 和一个编排 skill 的路径解析，不触碰现有用户笔记。
- 检查 `Experiments/`、Workbench memory、模板和日志引用都能解析。

### Website validation

- 在 `.website/` 使用已有 lockfile 安装/复用依赖。
- 运行 TypeScript/format check 和 Quartz build，确认 `institutes` 兼容修改不破坏发布。

## 8. Rollout Order

1. 增加 Codex discovery 与 `AGENTS.md` 执行契约。
2. 更新 protocol、README 和安装文档。
3. 批量规范化 14 个 skill frontmatter 与能力语义。
4. 修复 orchestration、Experiments、memory 和 PaperMeta 漂移。
5. 运行全量静态验证、脚本 smoke tests 和 Quartz 验证。
6. 审核 diff，确保没有用户笔记被改写，再提交实现。

## 9. Success Criteria

- 从仓库根目录启动 Codex 可发现 14 个 skills。
- 所有 skill 通过 `quick_validate.py`。
- 活动 skills/protocol 中不再依赖 Claude 专有工具名或已删除的 skill。
- Codex 是 README/INSTALL 的默认 agent，Claude 路径仍可用。
- Experiment、memory、Paper metadata 工作流不存在已知断链。
- Quartz build 和与改动相关的 smoke tests 通过。
- `Papers/`、`DomainMaps/`、`Ideas/` 等用户内容目录无非预期改动。

## References

- [Build skills — Codex](https://developers.openai.com/codex/skills)
- [Custom instructions with AGENTS.md — Codex](https://developers.openai.com/codex/guides/agents-md)
- [Agent Skills specification](https://agentskills.io/specification)
