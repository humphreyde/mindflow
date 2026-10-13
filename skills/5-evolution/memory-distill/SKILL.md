---
name: memory-distill
description: >
  当积累了多天工作日志、或 Owner 说"整理记忆""蒸馏"时，从日志中提取 pattern 和 insight 到记忆库。也可被 autoresearch 在合适时机自动调用
---

## Purpose

memory-distill 是 MindFlow 记忆演化体系的基础技能。它定期扫描 `Workbench/logs/` 中的原始工作日志，从中提取跨日期重复出现的 pattern 和意外发现，并将有价值的 observation 提升为结构化的记忆条目，写入 `Workbench/memory/patterns.md` 和 `Workbench/memory/insights.md`。

该技能实现了 `references/memory-protocol.md` 中定义的 Insight Promotion Hierarchy 的底层两级跃迁：从 Level 0（Raw Log）提升至 Level 1（Pattern），再进一步触发 Level 1 → Level 2（Provisional Insight）和 Level 2 → Level 3（Validated Insight）的升级。它将"散落的日常观察"转化为"可复用的研究经验"，是 MindFlow 自我进化机制的核心入口。

输入为时间范围内的日志文件（`Workbench/logs/YYYY-MM-DD.md`），输出为更新后的记忆文件和 changelog 条目。

## Steps

### Step 1：收集日志

1. 解析 `period` 参数，确定起止日期。若未提供，默认为今天往前 7 天（含今天）。
2. 按 `Workbench/logs/YYYY-MM-DD.md` 路径模式列出所有日志文件。
3. 根据文件名中的日期过滤，保留落在 `period` 范围内的文件。
4. 逐一读取全部匹配的日志文件，记录每个文件的日期和内容。
5. 若范围内无任何日志文件，输出提示"指定时间段内无日志，跳过蒸馏"，终止执行。

### Step 2：提取候选 Pattern

通读所有收集到的日志内容，重点扫描每条 log entry 的 `observation` 字段及其他叙述性文字，寻找以下三类候选 pattern：

1. **跨日期重复观察**：同一现象、规律或结论在两个或更多不同日期的日志中均有提及。即使措辞不同，只要语义相似，均视为同一 pattern 的多次出现。
2. **意外发现（anomaly）**：某个结果或行为与 `DomainMaps/` 中记录的已有知识相悖，或日志中明确标注为"出乎意料"、"与预期不符"的观察。
3. **关联线索（correlation clue）**：日志中提示两篇论文、两个实验或两个概念之间存在潜在联系，且该联系尚未在任何记忆文件中被明确记录。

对每个候选 pattern，记录：
- 核心 observation 的一句话概括
- 来源日志文件列表（`Workbench/logs/YYYY-MM-DD.md`）

### Step 3：检查已有记忆

1. 读取 `Workbench/memory/patterns.md`，逐条对比 Step 2 的候选 pattern。对每个匹配项在任何写入前记录快照：
   - 本轮开始时的 `occurrences` 去重集合及数量
   - `status` 是否已包含 `promoted` 标记和 insight wikilink
   - 本轮候选日志中哪些来源尚未记录
   - 该候选是全新 pattern，还是已有 pattern 的新证据

2. 读取 `Workbench/memory/insights.md`，通过 pattern `status` 中的 insight 链接、insight 的 `source_pattern` 反向链接，以及必要的语义重复检查，判断该 pattern 是否已有关联 insight。只要已存在关联 insight，该 pattern 就不再符合 L1 → L2 条件，即使 pattern 缺少旧式标记。

3. 对每个已有 insight，在任何写入前记录本轮开始时的 `status`、`evidence` 去重集合，以及它是否早于本次 memory-distill 就已存在。同一来源不重复追加到 `occurrences` 或 `evidence`。

### Step 4：更新记忆

根据 Step 3 的写入前快照分三种情况处理。新条目只能追加；已有条目只能追加尚未记录的 `occurrences` / `evidence` 引用，或对 `status` / `confidence` 做有证据支撑的窄范围生命周期更新。不得删除条目、移除旧证据或改写原有 claim / observation。

**情况 A：全新 pattern**

将以下格式的新条目追加到 `Workbench/memory/patterns.md` 末尾：

```markdown
### [YYYY-MM-DD] <Pattern 描述>

- **observation**: <一句话描述跨源观察到的规律或现象>
- **occurrences**: [[Workbench/logs/YYYY-MM-DD]], [[Workbench/logs/YYYY-MM-DD]], ...
- **confidence**: low
- **needs_verification**: yes
- **status**: unpromoted
```

日期填写今天（执行蒸馏的日期）。
将新 pattern 的写入前 occurrences 数视为 `0`，然后按情况 B 判定它是否在本轮从 `< 3` 跨越到 `≥ 3`。

**情况 B：pattern 获得新证据或达到晋升条件**

1. 再次读取并确认目标 pattern 条目，使用 Step 3 的写入前快照记录 `before_count`。只向 `occurrences` 行末追加本轮尚未记录的独立来源，并计算去重后的 `after_count`。
2. 先做幂等性门检查：
   - 若 pattern `status` 已含 `promoted` 标记，或已找到任何关联 insight，**不得再执行 L1 → L2**。
   - 若已找到关联 insight 但 pattern 缺少标记，仅将 pattern `status` 窄范围更新为 `promoted ([YYYY-MM-DD]) → [[Workbench/memory/insights.md#<heading>]]`，作为一次性链接修复；不新建 insight，并在 changelog 中记录。
   - 若关联 insight 仍为 `provisional`，将本轮尚未记录的新独立来源传给情况 C；不传递旧 occurrences。
3. 仅当 pattern **无 promoted 标记且无关联 insight** 时，检查以下两个互斥条件：
   - **当前轮跨阈值**：`before_count < 3` 且 `after_count ≥ 3`。
   - **一次性 legacy reconciliation**：`before_count ≥ 3`，且本轮开始时既无 promoted 标记也无关联 insight。
   - 若均不满足，只保留新 occurrences，不晋升。
4. 满足其中一个晋升条件时，创建且只创建一个 provisional insight：
   - 先确定 insight heading，将以下格式的新条目追加到 `Workbench/memory/insights.md` 末尾：

     ```markdown
     ### [YYYY-MM-DD] <Insight 标题（与 pattern 描述一致）>

     - **claim**: <从 pattern observation 提炼的可证伪的一句话断言>
     - **evidence**: [[Workbench/logs/YYYY-MM-DD]], [[Workbench/logs/YYYY-MM-DD]], ...
     - **confidence**: low
     - **source_pattern**: [[Workbench/memory/patterns.md#<heading>]]
     - **source**: cross-validation
     - **impact**: <该 insight 可能影响的研究方向，若暂不明确可填"待评估">
     - **status**: provisional
     ```
   - 成功追加 insight 后，将 pattern `status` 窄范围更新为 `promoted ([YYYY-MM-DD]) → [[Workbench/memory/insights.md#<heading>]]`。若 legacy pattern 没有 `status` 字段，只追加该字段一次。若两步之间中断，下轮通过 insight `source_pattern` 识别已存在的关联并只修复 status，不重复创建 insight。
   - 在本次执行中将该 insight 标记为"本轮新建"，不得继续进入情况 C。

**情况 C：已有 provisional insight 获得新证据**

1. 只处理在本轮开始前已存在且当时 `status: provisional` 的 insight。本轮新建的 provisional insight 无论初始 evidence 有多少都不得在同一轮晋升。
2. 使用 Step 3 的写入前快照，只向 `evidence` 行末追加至少一个在 insight 成为 provisional 之后新加入、此前未记录的独立证据来源。保留已有引用不变，并计算去重后的证据总数。
3. 同时满足以下条件才触发 L2 → L3：
   - 本轮确实追加了 **≥ 1 个**此前未记录的独立证据来源；
   - 追加后独立证据来源总数 **≥ 2**；
   - insight 不是本轮新建。
4. 若没有新证据，即使已有 evidence 总数 `≥ 2`，也保持 `status: provisional`。用于创建 provisional insight 的证据不能在同一轮内再用于 validated。
5. 满足条件时，将 `status: provisional` 窄范围更新为 `status: validated`，并根据证据强度将 `confidence` 窄范围更新为 `medium` 或 `high`。不改写 claim 或任何历史证据。

   若晋升后 `status: validated` 且 `confidence > 0.8`（即 `high`）：
   - 将以下条目追加到 `Workbench/queue.md` 的 Review 部分，建议晋升至 DomainMaps：

     ```markdown
     ### [YYYY-MM-DD] 建议晋升至 DomainMaps

     - **insight**: [[Workbench/memory/insights.md#<heading>]]
     - **claim**: <insight 的 claim 原文>
     - **confidence**: high
     - **reason**: validated insight，≥2 独立来源，confidence > 0.8，符合 L3 → L4 晋升条件
     - **suggested_map**: <建议写入的 DomainMaps/{Name}.md 文件名>
     ```

### Step 5：记录变更

将以下格式的条目追加到 `Workbench/evolution/changelog.md` 末尾（若文件不存在，先创建并加一级标题 `# Evolution Changelog`）：

```markdown
### [YYYY-MM-DD] memory-distill

- **period**: <YYYY-MM-DD ~ YYYY-MM-DD>
- **logs_processed**: <数量>
- **new_patterns**: <数量>
- **evidence_appended**: <追加 occurrences / evidence 的条目数>
- **promoted_to_insight**: <数量>（L1 → L2）
- **legacy_reconciliations**: <数量>（已达阈值且未标记/未关联的旧 pattern 一次性晋升）
- **validated_insights**: <数量>（L2 → L3）
- **queued_for_review**: <数量>（L3 → L4 候选）
- **promotion_basis**: <逐条列出 L1 → L2 是 `threshold-crossing` 还是 `legacy-reconciliation`；若无则填"无">
- **lifecycle_changes**: <逐条列出 `[[memory file#heading]]: old status/confidence → new status/confidence`；若无则填"无">
```

`promotion_basis` 和 `lifecycle_changes` 必须覆盖本次每一个晋升及其他实质性 `status` / `confidence` 变更，不得只记总数而丢失具体条目。

## Guard

- **历史不可变，生命周期窄更新**：不得删除记忆条目、改写 claim / observation、移除已有证据或静默重写历史。只可追加新条目、向已有 `occurrences` / `evidence` 追加来源，以及根据证据窄范围更新 `status` / `confidence`。需纠正或取代 claim 时，追加带日期且互相引用的新条目。
- **原始记录只读**：`Workbench/logs/` 日志和实验 Run Entries 保持 append-only；memory-distill 只读取它们，不删除、改写或重排旧记录。
- **L1 → L2 幂等**：晋升前必须同时确认 pattern 无 promoted 标记且无关联 insight。晋升后必须写入双向链接；后续轮次只追加新证据，不重复创建 insight 或晋升记录。
- **L2 → L3 分阶段**：本轮新建的 provisional insight 不得同轮 validated。只有后续轮次追加了至少一个此前未记录的独立来源，且证据总数 `≥ 2`，才可晋升。
- **生命周期变更留痕**：每次晋升和每个实质性 `status` / `confidence` 变更都必须追加到 `Workbench/evolution/changelog.md`，并指明目标条目及变更前后的值。
- **不直接修改 DomainMaps**：memory-distill 无权写入 `DomainMaps/` 下的任何文件，只能通过 `Workbench/queue.md` 的 Review 部分提出建议，由 Human 或上层技能决策。
- **来源引用必须明确**：patterns.md 中每条 pattern 的 `occurrences`，以及 insights.md 中每条 insight 的 `evidence`，都必须包含指向具体日志文件的 Obsidian wikilink，不得仅凭印象记录"多次观察到"。
- **不捏造 pattern**：只有在日志中确实出现的 observation 才能被提取为候选 pattern，不得基于推断或联想凭空生成。若某规律听起来合理但日志中找不到明确依据，不记录。
- **晋升需引用具体证据**：将 pattern 晋升为 provisional insight，或将 provisional insight 标记为 validated 时，必须在 insight 的 `evidence` 字段中列出支撑该结论的所有具体日志来源。
- **独立来源的判断**：同一天的多条日志条目不算作独立来源；独立来源需来自不同日期，或来自不同论文/实验的观察。

## Verify

- [ ] `Workbench/evolution/changelog.md` 已追加本次蒸馏记录
- [ ] 蒸馏结果已记录（新增 pattern 数 + 晋升 insight 数，允许为 0 但须明确记录）
- [ ] 每个 L1 → L2 都是本轮跨阈值或一次性 legacy reconciliation，且 pattern 标记与 insight `source_pattern` 双向链接唯一
- [ ] 没有本轮新建的 provisional insight 在同一轮被标记为 validated

## Examples

**示例：指定时间段蒸馏**

```
$memory-distill --period "2026-03-20 ~ 2026-03-26"
```

执行过程：

1. 解析 period，确定范围为 2026-03-20 至 2026-03-26
2. 按路径模式在 `Workbench/logs/` 找到 `2026-03-20.md`、`2026-03-22.md`、`2026-03-24.md`、`2026-03-26.md` 共 4 个文件，逐一读取
3. 扫描 observation 字段，发现：
   - "reward shaping 在 sparse-reward 环境中显著提升收敛速度" 在 03-22 和 03-24 均有记录 → 候选 pattern（2次出现，全新）
   - "基于 diffusion 的策略对 action chunk size 高度敏感" 在 03-20、03-22、03-26 均有记录 → 候选 pattern（3次出现，全新但已达晋升阈值）
   - "cross-attention 替代 concatenation 在多模态融合中更有效" 在 03-24 出现，且 patterns.md 已有一条相似 pattern（来自 03-15、03-18），本次为第3次出现 → 已有 pattern 获得新证据
   - "waypoint curriculum 在 unseen environment 中改善泛化" 在 03-26 出现；对应 pattern 已有 promoted 标记，并链接到 03-19 已创建的 provisional insight，03-26 是其成为 provisional 后的新独立来源
4. 读取 patterns.md 并保存写入前快照：
   - reward shaping：`before_count = 0`，`after_count = 2` → 不晋升
   - diffusion 敏感性：`before_count = 0`，`after_count = 3`，无标记且无关联 insight → `threshold-crossing`
   - cross-attention：`before_count = 2`，`after_count = 3`，无标记且无关联 insight → `threshold-crossing`
   - waypoint curriculum：已有 promoted 标记和关联 insight → 禁止再次 L1 → L2，仅传递 03-26 的新证据
5. 读取 insights.md：
   - 无与 diffusion 或 cross-attention 候选直接相关的旧 insight
   - waypoint curriculum insight 在本轮开始前已是 `provisional`，其原 evidence 来自 03-10、03-15、03-18；03-26 此前未记录，且是 provisional 之后加入的新独立来源
6. 写入：
   - patterns.md 新增 2 条 pattern（reward shaping、diffusion chunk size）
   - diffusion 和 cross-attention pattern 各自写入唯一 promoted 标记与 insight 链接，insights.md 新增 2 条带 `source_pattern` 反向链接的 provisional insight
   - 上述两条新 provisional insight 本轮均不参与 L2 → L3
   - waypoint curriculum 只追加 03-26 occurrence/evidence；因 insight 在本轮前已是 provisional，且本轮新增了独立证据，将其更新为 validated
7. 追加 changelog 条目：`promotion_basis` 记录两个 `threshold-crossing`，`lifecycle_changes` 记录两个 L1 → L2 和一个 L2 → L3

最终输出摘要：

```
memory-distill 完成（2026-03-20 ~ 2026-03-26）
- 处理日志：4 个文件
- patterns.md 新增 2 条 pattern
- L1 → L2：2 条（diffusion、cross-attention，均为本轮跨阈值）
- L2 → L3：1 条（waypoint curriculum，来自既有 provisional insight 的后续新证据）
- 本轮新建的 2 条 provisional insight 未同轮 validated
- changelog 已更新
```
