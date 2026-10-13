---
name: result-analysis
description: >
  当 Owner 说"分析一下实验结果"，
  或 completed / failed 实验尚无实质性 hypothesis verdict 时由 autoresearch 调用，
  分析实验数据并判断假设是否成立
---

## Purpose

result-analysis 是 MindFlow 实验闭环的最后一环。给定一个实验笔记（`[[Experiments/xxx.md]]`），它系统性地读取所有 Run Entries、关联 Idea 的 hypothesis，结合历史记忆上下文，从五个维度完成分析：

| 分析维度 | 含义 |
| :--- | :--- |
| **Hypothesis Verdict** | hypothesis 是否得到支持——supported / refuted / inconclusive |
| **Key Findings** | 实验揭示的最重要事实，不局限于 hypothesis |
| **Comparison to Baseline** | 与 baseline 或对照组的量化对比 |
| **Limitations** | 当前实验的约束条件和潜在偏差 |
| **Implications** | 对后续研究方向、Idea 修正或 DomainMaps 更新的启示 |

分析结果写入 Experiment 笔记的 `## Analysis` 节；若发现跨实验规律，追加到 `Workbench/memory/patterns.md`；若 verdict 明确，同步更新关联 Idea 的 `status` 字段。

## Steps

### Step 0：确认实验输出入口与 schema

在产生任何分析输出前：

1. 确认 `Experiments/` 目录存在；若不存在则创建。若目录无法创建，停止执行并告知 Owner。
2. 读取 `Templates/Experiment.md`，以其 frontmatter 和 section 结构作为 Experiment 笔记的 schema。若模板缺失或无法读取，停止执行，不修改任何实验文件。
3. 读取 `references/memory-protocol.md`；追加 pattern 时严格使用其中的 canonical 生命周期字段，并先读取现有 `Workbench/memory/patterns.md`。

### Step 1：读取目标 Experiment 全部 Run Entries

读取 `experiment` 参数指向的 `Experiments/xxx.md` 文件。若文件不存在，停止并告知 Owner，不创建替代笔记。提取以下字段：

- `status`：按 `Templates/Experiment.md` 读取；`running`、`completed`、`failed` 均可继续分析（`failed` 是重要的负面证据），仅当 status 为 `planned` 时停止并告知 Owner"实验尚未运行，暂无数据可分析"
- `hypothesis`（若直接记录在 Experiment 文件中）或 `idea`（`Templates/Experiment.md` 中指向关联 Idea 的字段；兼容读取旧笔记中的 `idea_ref`）
- 所有 `### Run [N]` 节或 Run Entries 表格：记录每个 run 的 config、metrics、observations
- `baseline`：对照指标或对照组描述

将所有 run 数据整理为结构化列表，方便后续比较。

### Step 2：找到关联 Idea，读取其 hypothesis

若 Step 1 中发现 `idea` 或旧版 `idea_ref` 字段（格式为 `[[Ideas/xxx.md]]`），读取对应 Idea 文件，提取：

- `hypothesis`：本实验试图验证的核心假设（完整保留原文）
- `status`：当前 Idea 状态（用于 Step 7 的同步更新）
- `tags`：领域关键词（用于 memory-retrieve 检索范围）

若关联字段为空或文件不存在，从 Experiment 文件本身提取 hypothesis，并在分析记录中注明"未找到关联 Idea，hypothesis 来自 Experiment 文件"。

### Step 3：执行 memory-retrieve（scope: insights + patterns）

调用 memory-retrieve skill，以 Step 2 的 hypothesis 和 tags 作为 `query`，scope 设为 `insights` 和 `patterns`，检索与本实验相关的历史经验：

- 相似假设在过去实验中是否被验证或否定
- 已知有效或无效的 method/config 模式
- 领域内的已知规律（patterns）

将检索结果作为分析的背景上下文，在后续五维分析中标注"参考历史记忆"的依据。若记忆库为空或无相关条目，继续执行，在分析中注明"暂无相关历史记忆"。

### Step 4：执行五维分析

综合 Step 1-3 的全部信息，逐维完成分析：

#### 4.1 Hypothesis Verdict

根据实验数据判断 hypothesis 的成立情况，给出三选一结论：

- **supported**：主要 run 的核心 metric 一致、显著地支持 hypothesis，且排除了明显的混淆因素
- **refuted**：主要 run 的核心 metric 一致地与 hypothesis 相悖，结果方向明确
- **inconclusive**：数据不足（run 数量少、方差过大）、结果矛盾、或 metric 与 hypothesis 不直接对应

给出 1-3 句证据说明：有 metric 时直接引用 run 数据中的具体数字；失败且无 metric 时引用实际失败记录和数据缺失原因，判为 inconclusive。禁止在数据不充分时强行判断为 supported 或 refuted。

#### 4.2 Key Findings

列出 2-5 条最重要的发现，不局限于 hypothesis 的直接验证。每条一句话，格式：

```
- [Finding]：<具体描述，引用数据>
```

Key Findings 可以包含：意外规律、config 敏感性、数据质量问题、与预期相悖的现象等。

#### 4.3 Comparison to Baseline

若 Experiment 文件中定义了 baseline，量化比较核心 metric 的提升/下降：

```
| Metric | Baseline | Best Run | Delta | 说明 |
| :----- | :------: | :------: | :---: | :--- |
| ...    |    ...   |    ...   |  ...  | ...  |
```

若无 baseline 定义，在此节注明"本实验未定义 baseline，无对照比较"，不伪造对比数据。

#### 4.4 Limitations

列出 2-4 条当前实验的主要局限，包括但不限于：

- 样本量/run 数量不足
- 超参搜索范围有限
- 评估 metric 与 hypothesis 的对应关系存疑
- 数据集分布偏差或 generalization 风险
- 实验条件与实际应用场景的差距

#### 4.5 Implications

基于本次实验结果，给出 2-4 条对后续研究的启示：

- 若 supported：可推进的下一步实验或值得写入 DomainMaps 的规律
- 若 refuted：应修正的 hypothesis 方向或需要放弃的 Idea
- 若 inconclusive：需要补充的实验设计（更多 runs / 不同 metric / ablation）
- 跨实验的 pattern（若本次发现与历史记忆有共鸣）

### Step 5：将分析写入 Experiment 笔记的 ## Analysis 节

在目标 Experiment 文件（`Experiments/xxx.md`）中精确更新 `## Analysis` 节，格式如下：

```markdown
## Analysis

<!-- result-analysis:generated:start -->

**Analysis date**：YYYY-MM-DD

### Hypothesis Verdict

**Verdict**：supported / refuted / inconclusive

<1-3 句证据说明，引用具体 run 数据>

### Key Findings

- [Finding 1]：<描述>
- [Finding 2]：<描述>
- ...

### Comparison to Baseline

| Metric | Baseline | Best Run | Delta | 说明 |
| :----- | :------: | :------: | :---: | :--- |
| ...    |   ...    |   ...    |  ...  | ...  |

（若无 baseline，注明"未定义 baseline"）

### Limitations

- <限制 1>
- <限制 2>
- ...

### Implications

- <启示 1>
- <启示 2>
- ...

<!-- result-analysis:generated:end -->
```

日期填写今天（`YYYY-MM-DD`），保留 canonical `## Analysis` 标题。写入前保存目标原文并确定该节与相邻节的边界，按以下规则最小合并：

- Analysis 不存在时创建该节；存在但没有可确认的生成边界时，保留原正文（包括模板提示、手写结论和批注），在该节末尾追加上述生成块。
- 有成对 `result-analysis:generated:start/end` 标记，或有先前产物/明确归属可核对的生成内容时，只精确更新能确认归属的生成字段、子节；标记不授权整块覆盖。生成块内外的手写插注、未知归属内容均逐字节保留；不能只凭 `Hypothesis Verdict` 等通用标题推断作者身份。
- 没有生成边界本身不要求暂停；可安全追加时直接追加。仅当 Analysis 的边界、标记配对或生成/手写归属冲突导致无法安全更新或追加时，保留原文件并向 Owner 说明具体歧义，等待澄清。

写后比对原文，确认所有手写/用户内容、frontmatter、Run Entries 和其他节逐字节不变。在日志中记录 `appended-generated-block` 或 `updated-generated-fields` 及范围；不得记录或执行整节覆盖。

### Step 6：若有跨实验 pattern，追加到 patterns.md

检查 Step 4 的分析结果，判断是否发现了跨实验规律（cross-experiment pattern）——即：本次发现与 memory-retrieve 返回的历史记忆高度一致，或本次发现可能对多个 Idea/实验具有普适价值。

若存在 cross-experiment pattern，先核对各来源的原始实验/日志。把本次观察和 `[[Experiments/xxx]]` 记录在 Step 8 的分析日志中，并在本次执行结束前确认该日志已落盘，使下列 occurrence 可直接解析。将候选追加到 `Workbench/memory/patterns.md`，严格使用 canonical 格式：

```markdown
### [YYYY-MM-DD] <Pattern 标题>

- **observation**: <含适用范围的一句话可证伪规律>
- **occurrences**: [[Workbench/logs/YYYY-MM-DD]], <其他已核验的独立来源日志 wikilinks>
- **confidence**: low
- **needs_verification**: yes
- **status**: unpromoted
```

`occurrences` 必须包含具体日志 wikilink；日志的 `input` / `observation` 追溯到具体 Experiment 和 Run Entries。可附加原始 Experiment 引用以定位证据，但同一实验及其分析日志只算一个独立来源，同一来源不因重复分析而增加次数。`confidence` 仅允许 `low` / `medium`，新候选默认 `low`；确有多个独立来源时可为 `medium`，不能为 `high`。

若已有同义 pattern，不重复创建：仅向其 `occurrences` 追加尚未记录的独立来源，保留 observation、既有证据、`needs_verification` 和生命周期状态不变；晋升交给 `memory-distill`。若无跨实验规律，跳过此步。上述产物可直接作为 `memory-distill` 的 pattern 输入，不需要 schema 归一化。

### Step 7：若 verdict 明确，更新关联 Idea status

若 Step 4.1 的 verdict 为 **supported** 或 **refuted**（即非 inconclusive），且 Step 2 中找到了关联 Idea 文件，仅精确更新 Idea 文件 frontmatter 的 `status` 字段：

| Verdict | Idea 新 status |
| :--- | :--- |
| supported | `validated` |
| refuted | `archived` |
| inconclusive | 保持原值，不修改 |

仅修改 `status` 字段，Idea 文件其他内容保持不变。

### Step 8：追加日志

将以下 log entry 追加到 `Workbench/logs/YYYY-MM-DD.md`：

```markdown
### [HH:MM] result-analysis
- **input**: [[Experiments/xxx]]
- **verdict**: supported / refuted / inconclusive
- **key-finding**: <最重要的一条发现，一句话>
- **observation**: <候选 pattern 的实际观察与对应 Experiment/Run 引用；无候选时写本次关键观察>
- **analysis-update**: appended-generated-block / updated-generated-fields（注明精确范围）
- **idea-status-updated**: yes（[[Ideas/xxx]] → validated/archived）/ no
- **pattern-added**: yes / no
- **status**: success
```

若日志文件不存在，先创建文件（一级标题 `# YYYY-MM-DD`），再追加 entry。

## Verify

- [ ] Experiment 文件保留 canonical `## Analysis` 标题，生成块内含 `**Analysis date**：YYYY-MM-DD` 和全部五个子节
- [ ] 已确认 `Experiments/` 存在，且分析基于 `Templates/Experiment.md` schema 读取的实验笔记
- [ ] Verdict 为 supported / refuted / inconclusive 三选一
- [ ] 关联 Idea 的 `status` 已同步更新（若 verdict 非 inconclusive 且 `idea` 或旧版 `idea_ref` 存在）
- [ ] 手写/用户内容（包括生成块内的插注）、frontmatter、Run Entries 和其他节与写入前逐字节一致；只追加生成块或窄更新可确认归属的生成字段
- [ ] 若发现跨实验 pattern，产物含 canonical `observation` / `occurrences` / `confidence` / `needs_verification` / `status`；新候选为 `needs_verification: yes`、`status: unpromoted`，confidence 仅 low/medium
- [ ] occurrence 日志已落盘且可追溯到实际 Experiment/Run；同一实验的重复日志未当作独立证据，已有 pattern 未重复创建或擅自晋升
- [ ] 日志已追加到 `Workbench/logs/YYYY-MM-DD.md`

## Guard

- **verdict 必须基于实际数据**：Hypothesis Verdict 必须引用 Experiment 文件中的具体 run metric；失败导致无 metric 时，引用实际失败记录并说明数据缺失，以 inconclusive 记录，不捏造数值。不得根据主观印象或"感觉上"下结论。
- **inconclusive 不强行下结论**：数据不充分时（run 数量 < 3、metric 方差过大、结果相互矛盾），必须判为 inconclusive，不得为追求"明确结论"而强行判定 supported 或 refuted。
- **不修改 Run Entries**：只读取 Run Entry 数据，绝对不修改 Experiment 文件中任何 `### Run [N]` 节的原始内容。分析是独立节，与 run 数据并存；更新 Analysis 时必须保留全部其他 section、frontmatter 与手写内容。
- **语言规范**：中文正文 + 英文技术术语（模型名、metric 名、benchmark 名、方法名保持英文，不翻译）。

## Examples

**示例：分析一个已完成的 VLN fine-tuning 实验**

假设 Experiment 文件为 `Experiments/VLN-LoRA-R2R-2026Q1.md`，包含以下信息：

- `status: completed`
- `idea: "[[Ideas/VLN-LoRAFinetuning]]"`
- baseline：DUET 在 R2R val-unseen 的 SR=0.57
- 3 个 Run Entries：
  - Run A（rank=8）：SR=0.61, SPL=0.52
  - Run B（rank=16）：SR=0.63, SPL=0.54
  - Run C（rank=32）：SR=0.62, SPL=0.53

关联 Idea `Ideas/VLN-LoRAFinetuning.md` 的 hypothesis：
> "对 DUET 应用 LoRA fine-tuning（rank 8-32），可以在 R2R val-unseen 上将 SR 提升至少 5 个百分点，同时保持 SPL 不显著下降。"

执行过程：

1. 确认 `Experiments/` 存在并读取 `Templates/Experiment.md`，再读取 `Experiments/VLN-LoRA-R2R-2026Q1.md` — 提取 3 个 Run Entries 数据，整理为结构化列表

2. 读取 `Ideas/VLN-LoRAFinetuning.md` — 提取 hypothesis（SR 提升 ≥5pp）和 `status: developing`、`tags: [VLN, LoRA, R2R]`

3. 调用 memory-retrieve（scope: insights + patterns，query: "LoRA fine-tuning VLN R2R"）— 假设返回一条历史 pattern："rank 过大在低数据量场景易过拟合"

4. 五维分析：

   - **Verdict**：supported — Run A/B/C 的 SR 分别提升 +4pp、+6pp、+5pp，平均 +5pp，满足 hypothesis 阈值；SPL 均保持在 0.52-0.54，未显著下降
   - **Key Findings**：rank=16 为最优（SR=0.63）；rank=32 相比 rank=16 无进一步提升，与历史 pattern"高 rank 易过拟合"一致
   - **Comparison to Baseline**：SR 0.57→0.63（+10.5%），SPL 0.51→0.54（+5.9%）
   - **Limitations**：仅测试 rank ∈ {8, 16, 32}，未覆盖更大范围；仅在 val-unseen 验证，未测 test set
   - **Implications**：可将 rank=16 作为 VLN LoRA 的推荐默认值；可进一步探索 LoRA + data augmentation 的组合

5. 精确更新 `Experiments/VLN-LoRA-R2R-2026Q1.md` 的 `## Analysis` 节，并在节内写入 `**Analysis date**：2026-03-28`

6. 在 `Workbench/memory/patterns.md` 追加候选："本次 VLN R2R 实验中 rank=16 的 SR 最高，rank=32 未继续提高 SR"；使用 canonical 五字段，confidence=low、needs_verification=yes、status=unpromoted，occurrences 指向本次含 Experiment/Run 证据的分析日志

7. 精确更新 `Ideas/VLN-LoRAFinetuning.md` 的 `status: validated`（verdict=supported）

8. 在 `Workbench/logs/2026-03-28.md` 追加 log entry
