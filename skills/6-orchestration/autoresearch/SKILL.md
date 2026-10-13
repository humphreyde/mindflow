---
name: autoresearch
description: >
  MindFlow 的核心研究循环。当 Owner 说"自己干活吧""开始研究"，
  或系统需要自主推进研究时启动。
  持续运行：读取当前状态 → 判断最高价值行动 → 调用卫星 skill → 记录 → 循环
---

## Purpose

autoresearch 是 MindFlow 的核心研究循环，实现了 PhD 导师制中 Researcher 的"自主研究日常"。它持续运行，每轮读取 Workbench 状态（agenda、queue、memory、logs），判断当前研究进展的最大瓶颈，调用对应的卫星 skill 执行最高价值行动，记录后进入下一轮。

与 Karpathy autoresearch 的关键区别：Karpathy 版优化单一 metric（val_bpb），MindFlow 版驱动知识积累和研究方向演化——目标不是某个指标下降，而是"我们理解了什么新东西"。

## Steps

正常行动轮严格执行 4 步，然后根据停止条件决定是否进入下一轮。若执行前终止门命中，则本轮在状态重读和终止日志后立即结束，不进入 JUDGE 或 ACT。

### Step 1：READ STATE

每轮都重新读取以下当前状态，不沿用上一轮缓存：

1. `Workbench/agenda.md` — 当前研究方向、优先级、各 direction 的 `next_action`。
2. `Workbench/queue.md` — 待处理任务（Reading / Review / Questions / Experiments）。
3. `Workbench/memory/insights.md` — 近期 insight，重点关注近 30 天的 validated 条目。
4. `Workbench/memory/patterns.md` — 近期 pattern。
5. 按路径 `Workbench/logs/YYYY-MM-DD.md` 列出并读取最近 3 天的日志，了解近期行动、失败和连续重复，避免无信息增益的重试。
6. 检查 `Experiments/` 中 `completed` / `failed` 实验的 `## Analysis`，按 Step 2 的实质性 verdict 判据识别尚待分析的目标；目录不存在时记录无实验候选。

若 `focus` 参数指定了某个 direction，优先提取该 direction 的相关状态，但仍读取上述全局状态以识别冲突、Owner override 和停止信号。

### Step 1.5：PRE-ACTION TERMINAL GATE

状态重读完成后、进入 Step 2 前，先检查以下终止条件：

- Owner 已要求暂停或停止。
- 当前状态没有证据支持任何卫星行动。
- 所有可能行动都缺少必须由 Owner 提供的输入、授权或选择，因而当前没有 authorized action。
- 已知 Guard 或用户内容保护边界明确禁止当前候选行动。

命中任一条件时，不选择、不读取也不执行卫星 skill。先向 `Workbench/logs/YYYY-MM-DD.md` 串行追加终止轮记录；文件不存在时先创建并写一级标题 `# YYYY-MM-DD`：

```markdown
### [HH:MM] autoresearch — round N (terminal)
- **state_summary**: <本轮重新读取到的关键状态，1-2 句>
- **judgment**: <命中的执行前终止条件和证据>
- **action**: none
- **status**: stopped | blocked
- **outcome**: <暂停原因，以及需要 Owner 提供的输入/授权/选择；无则写 none>
- **consecutive_failures**: unchanged
```

日志写入后立即暂停循环并等待 Owner；不得继续 Step 2、Step 3 或普通 Step 4。终止轮没有顶层卫星行动，也不增加失败计数。

### Step 2：JUDGE

基于本轮刚读取的状态，选择一个最高价值的“卫星 skill + 明确目标 + 输入参数”。以下是参考启发式，不是硬编码规则：

| 状态信号 | 候选行动 |
|:--------|:---------|
| 需要按时间窗口发现和点评近期论文 | `daily-papers` |
| queue 的 Reading 部分有待处理论文 | `paper-digest` |
| agenda 中某 direction 缺乏外部文献支撑 | `literature-survey`，使用 `external-topic` 模式 |
| vault 中有一组明确的本地论文需要比较 | `literature-survey`，使用 `local-set` 模式并传入本轮确定的封闭路径清单 |
| 近期 Topic 或 Paper 暴露了知识空白 | `idea-generate` |
| `Ideas/` 中有 `status: raw` 的 idea 待评估 | `idea-evaluate` |
| `Ideas/` 中有 `status: developing` 的 idea 缺实验方案 | `experiment-design` |
| `Experiments/` 中有正在运行的实验需要追加进展或结果 | `experiment-track` |
| `Experiments/` 中有 `status: completed` 或 `failed`，且 `## Analysis` 尚无实质性 hypothesis verdict | `result-analysis` |
| 某 direction 已有充足论文、实验和 idea，需要成文 | `draft-section` |
| 已有文稿需要在 Owner 确认后精修 | `writing-refine` |
| 最近一次记忆蒸馏距今超过 5 天 | `memory-distill` |
| 近期有新 validated insight 但 agenda 未反映 | `agenda-evolve` |

`memory-retrieve` 只保留为其他 skill 内部组合使用的 canonical satellite；它不是 autoresearch 可独立选择的顶层行动。用户仍可在 autoresearch 之外显式调用它。

实验的实质性 hypothesis verdict 必须同时包含：一个明确的 `supported` / `refuted` / `inconclusive` 结论（或语义等价的手写结论），以及关联到该实验 Run Entries 的证据说明。失败实验可用具体失败记录和缺失数据原因支持 `inconclusive`，不要求不存在的 metric。缺少 Analysis、空白正文、模板提示“结果说明了什么？假设是否被验证？”，或仅有标题/未填写的 Verdict 字段，均仍待分析；不能仅凭 `## Analysis` 存在就排除。已有实质性手写 verdict 的实验不因缺少生成标记而自动重分析。该资格判断也用于 Step 1.5 的“无行动”判断，但不改变 Owner stop、授权和保护边界的优先级。

判断时依次考虑：

1. Owner 的显式指令、暂停信号和 `agenda.md` 中的 override。
2. `priority: high` direction 的 `next_action`。
3. queue 积压和最近未处理的完成态工作。
4. 预期 information gain、最近 3 天是否已经执行，以及同一目标的失败次数。

本地多论文比较必须先形成明确的 `local_set_paths`，只包含本轮选定的现有论文笔记、本地 PDF 或路径清单。把它作为 `literature-survey` 的 `local-set` 输入；不得在该行动中扩展外部论文、静默切换到 `external-topic`，或把清单外论文当作比较证据。清单边界无法可靠确定时停止判断并等待 Owner，而不是猜测。

### Step 3：ACT

从仓库根目录的 canonical registry 精确解析目标 skill；不得从兼容链接、隐藏目录或记忆中的旧路径执行。Registry 同时记录顶层候选和 internal-only 卫星，但 autoresearch 只能选择 `top-level` 条目：

| Skill | Canonical entrypoint | Role |
|:------|:---------------------|:-----|
| `daily-papers` | `skills/1-literature/daily-papers/SKILL.md` | top-level |
| `paper-digest` | `skills/1-literature/paper-digest/SKILL.md` | top-level |
| `literature-survey` | `skills/1-literature/literature-survey/SKILL.md` | top-level |
| `idea-generate` | `skills/2-ideation/idea-generate/SKILL.md` | top-level |
| `idea-evaluate` | `skills/2-ideation/idea-evaluate/SKILL.md` | top-level |
| `experiment-design` | `skills/3-experiment/experiment-design/SKILL.md` | top-level |
| `experiment-track` | `skills/3-experiment/experiment-track/SKILL.md` | top-level |
| `result-analysis` | `skills/3-experiment/result-analysis/SKILL.md` | top-level |
| `draft-section` | `skills/4-writing/draft-section/SKILL.md` | top-level |
| `writing-refine` | `skills/4-writing/writing-refine/SKILL.md` | top-level |
| `agenda-evolve` | `skills/5-evolution/agenda-evolve/SKILL.md` | top-level |
| `memory-distill` | `skills/5-evolution/memory-distill/SKILL.md` | top-level |
| `memory-retrieve` | `skills/5-evolution/memory-retrieve/SKILL.md` | internal-only |

执行顺序：

1. 确认 entrypoint 存在，且 frontmatter `name` 与选中的 skill 完全一致；不满足时把本轮记为 failed，不猜测替代路径。
2. 完整读取该 entrypoint，以及它为本轮输入直接链接的必要 references、templates 或 scripts 说明。
3. 使用本轮明确输入执行它当前的 `Steps`，同时遵守其 `Guard`；不能用旧的复制版流程替代当前正文。
4. 运行其当前 `Verify`，并把检查结果纳入本轮 outcome。若某项无法验证，状态只能是 partial、failed 或 blocked，不能记为成功。

**一轮只执行一个顶层卫星 skill。** 该 skill 自己声明的子步骤属于同一行动；本轮不得在失败后改调第二个 skill，也不得在记录前开始下一项研究行动。

### Step 4：LOG AND DECIDE

将本轮记录串行追加到 `Workbench/logs/YYYY-MM-DD.md`；文件不存在时先创建并写一级标题 `# YYYY-MM-DD`：

```markdown
### [HH:MM] autoresearch — round N
- **state_summary**: <本轮重新读取到的关键状态，1-2 句>
- **judgment**: <为什么选择这个 skill、目标和模式>
- **action**: <skill 名、canonical entrypoint、目标与输入参数>
- **status**: success | partial | failed | blocked
- **outcome**: <产出文件/更新、Verify 结果；失败时写失败阶段和原因>
- **consecutive_failures**: <同一 skill + 同一目标的连续失败次数>
```

失败、部分完成或等待授权也必须记录，且计入同一 skill + 同一目标的连续失败次数；成功后该目标的失败计数归零。日志完成后检查以下行动后停止条件：

- 连续 3 轮判断指向同一 skill + 同一目标，或该组合连续失败 3 次。此时只在 `agenda.md` 的 Discussion Topics 追加一个包含证据和已尝试行动的问题，然后暂停等待 Owner。
- 目标 skill 的 Guard 或人类确认边界要求暂停；不得把 autoresearch 的启动视为对发布、外部通讯、覆盖用户内容或其他受保护操作的授权。

若没有命中停止条件，回到 Step 1，并从磁盘重新读取状态。

## Verify

每轮结束时检查：

- [ ] 本轮状态来自本轮重新读取的 agenda、queue、memory 和最近日志，而非上一轮缓存。
- [ ] 若执行前终止门命中，本轮在任何卫星读取或执行前记录 `action: none` 和 stopped/blocked 原因并暂停；终止轮不要求卫星行动。
- [ ] 若执行前终止门未命中，本轮恰好选择并执行或尝试执行了一个 `top-level` 卫星 skill；canonical entrypoint 存在且 `name` 匹配。
- [ ] `memory-retrieve` 未被选为顶层行动；它只可由其他 skill 内部组合使用，或由用户在 autoresearch 之外显式调用。
- [ ] 执行依据该 entrypoint 当前的 Steps/Guard/Verify；结果未通过 Verify 时没有记为 success。
- [ ] 本地多论文比较使用 `literature-survey` 的 `local-set` 模式，输入是可枚举的封闭清单，且没有外部扩展。
- [ ] 已按实质性 verdict 判据检查 `completed` 和 `failed` 实验；空白/模板 Analysis 未被当作已分析，已有手写结论未被当作缺失，失败缺 metric 未被当作无候选。
- [ ] 日志包含 state_summary / judgment / action / status / outcome / consecutive_failures，失败也已留下阶段和原因。
- [ ] 停止条件和卫星 skill 的人类决策边界已执行，没有用自主循环绕过 Owner。

## Guard

- **原子性**：一轮只执行一个顶层卫星 skill；失败后先记录，不在同一轮改调其他 skill。
- **状态刷新**：每轮必须重新读取最新状态，因为上一轮行动、Owner 编辑或外部进展可能已经改变 vault。
- **Canonical source**：只从 registry 中的 `skills/<category>/<name>/SKILL.md` 解析卫星；每次都重读当前 Steps、Guard、Verify，不凭记忆执行。
- **执行前终止**：Owner stop、无 authorized action 或已知保护边界在 Step 1.5 立即终止；不得为了满足“一轮一个行动”而执行额外卫星。
- **内部卫星边界**：`memory-retrieve` 保留在 canonical registry 供 skill 内部组合，但 autoresearch 不得将其选为独立顶层行动。
- **Mission 只读**：不修改 `agenda.md` 的 Mission 节；Mission 只能由 Owner 决定，`agenda-evolve` 也只能在自身边界内处理议程。
- **人类决策优先**：保留每个卫星 skill 的确认、授权、歧义处理和用户内容保护要求。遇到这些边界时标记 blocked、记录并暂停，不代替 Owner 作决定。
- **封闭集不外扩**：`literature-survey local-set` 只能消费本轮记录的 `local_set_paths`；外部发现必须作为另一轮 `external-topic` 行动，并具有独立依据或授权。
- **卡住检测**：同一 skill + 同一目标连续出现或失败 3 轮时停止；不得通过改写目标名称规避计数。
- **不对外发布**：不投稿论文、不发送外部通讯；这类行为必须由 Owner 另行明确授权，并且不属于 autoresearch 的默认行动。
- **日志完整**：每轮都追加一条日志；失败、部分完成、blocked 和停止原因不得省略或伪装成成功。

## Examples

**示例：一次 autoresearch 会话的前 3 轮**

```text
Owner: "自己干活吧"

--- Round 1 ---
READ STATE:
  agenda: 1 active direction "VLA few-shot adaptation"（status: exploring）
  queue: Reading 有 2 篇待读论文
  logs: 昨天执行了 1 次 paper-digest

JUDGE: queue 有积压 → 选择 paper-digest，目标为第一篇论文
ACT: 完整读取 skills/1-literature/paper-digest/SKILL.md，按当前 Steps/Guard/Verify 执行
LOG: status=success, outcome=Papers/2603-FewShotVLA.md, consecutive_failures=0

--- Round 2 ---
READ STATE: 从磁盘重读；Reading 还剩 1 篇
JUDGE: 继续清理积压，但目标改为第二篇论文
ACT: 重新读取同一 canonical entrypoint 后执行
LOG: status=success, outcome=Papers/2601-AdaptiveVLA.md, consecutive_failures=0

--- Round 3 ---
READ STATE:
  queue: Reading 为空
  vault: 已明确 5 篇 VLA 本地论文笔记尚未做比较

JUDGE: 对这 5 个精确路径做封闭集比较
ACT: 完整读取 skills/1-literature/literature-survey/SKILL.md，传入 mode=local-set 和 5 项 local_set_paths；不进行外部发现
LOG: status=success, action=literature-survey local-set, outcome=Topics/VLA-FewShot-Survey.md, consecutive_failures=0
```
