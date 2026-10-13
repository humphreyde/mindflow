---
name: literature-survey
description: 当用户说"调研""survey""了解研究现状"，或需要系统了解某主题的文献全貌时，以 DomainMap 为认知基线、近期 survey paper 为文献锚点，批量 digest 后综合生成调研报告
---

## Purpose

支持两种互斥模式：

1. **外部主题调研**：以 `DomainMaps/` 为认知基线、以近期 survey 为锚点发现论文，输出 `Topics/{Topic}-Survey.md` 形式的认知 delta。
2. **显式本地论文集对比**：只比较用户明确提供的本地 PDF、论文笔记或路径清单，形成跨论文结论；不得自动扩展为外部文献搜索。

先根据输入选择模式。用户同时给出 topic 和封闭论文集时，默认本地对比；是否扩展外部资料必须另行获得用户授权。

## Steps

### 1. 建立范围与基线

两种模式都先读取 `references/tags.md` 和 `references/obsidian-syntax.md`，再读取 `DomainMaps/_index.md`；若 topic 对应已有 domain，读取该 DomainMap，但不直接修改它。

若目标 `Topics/{Topic}-Survey.md` 已存在，读取其 `date_updated`，并从正文中提取形如 `[[YYMM-ShortTitle]]` 的论文 wikilink，形成已有收录清单。更新时保留仍然有效的旧论据与用户编辑。

#### 外部主题调研范围

在搜索前记录 topic、同义词、时间窗口和停止条件。默认先查 vault 中的 `Papers/`，再使用运行时可用的网页发现能力或官方 API/站点查找 1-3 篇最相关的新 survey；若没有专门 survey，再查相邻或上位 topic。达到 3 篇有效锚点，或连续两轮查询没有新增相关锚点时停止，不无限扩展搜索。

#### 本地论文集范围

把用户明确提供的路径、PDF 和 wikilink 规范化为封闭清单。按 arXiv ID、DOI、已有笔记路径、规范化标题依次去重。清单之外的论文只可作为已提供论文中的引用背景提及，不得新建笔记或作为比较证据；外部元数据仅可用于确认清单内论文身份与来源。

### 2. 建立候选清单

#### 外部主题调研

读取选中的 survey 来源或现有笔记，提取反复引用且落在既定 topic/时间范围内的 canonical 论文。与已有收录清单及 `Papers/` 中已有笔记去重，分为：

- **需 digest**：范围内 canonical 论文，且无现有笔记。
- **已有笔记**：范围内且已有笔记，可直接参与综合。

一旦论文进入既定候选清单，不得为了节省时间主观跳过；获取失败记入 issues。

#### 本地论文集对比

已有 `Papers/*.md` 直接进入综合；本地 PDF 或其他尚无笔记的显式输入进入“需 digest”。不得加入清单外论文。若不同路径指向同一论文，保留一个 canonical 条目并记录别名。

### 3. 生成缺失笔记

对“需 digest”逐篇执行 `paper-digest`。已有笔记立即复用，不覆盖、不询问批量更新。

默认顺序执行。只有同时满足以下条件时才可并行：运行时具备并行工作能力；用户明确授权；每篇 digest 相互独立；输出笔记/assets 路径不重叠；不存在并发日志、历史或目标报告等共享写入。共享内容由协调过程串行写入。否则顺序执行是必选后备。

### 4. 综合写作

外部主题调研完整读取候选清单中 `rating >= 2` 的笔记；可用 shell 批量筛 frontmatter，但不得只读摘要或截断正文。本地论文集对比必须完整读取显式清单中的每篇笔记，不以 rating 过滤，因为低评分论文也可能提供关键反例。

#### 外部主题调研结构

输出或增量更新 `Topics/{Topic}-Survey.md`，包含：

- **Overview**：一句话定位、领域活跃度与整体趋势。
- **Problem & Motivation**：核心问题、重要性与时机。
- **技术路线对比**：主流路线、实际效果、优缺点及代表性论文。
- **Datasets & Benchmarks**：training datasets、benchmarks、代表性 SOTA 与 performance。
- **Open Problems**：由证据和矛盾支持的真实 open problems。
- **调研日志**：日期、范围、查询/锚点、论文统计、失败与降级。

对应 DomainMap 已建立的知识不大段复述，优先报告窗口内的新路线、对既有 claim 的支持/挑战和新 open problems；必要时链接 `[[DomainMaps/{Name}#某节]]`。没有对应 DomainMap 时完整展开。若发现值得更新的内容，在调研日志前增加 `## DomainMap 更新建议`，但不直接改 `DomainMaps/`。

#### 本地论文集对比结构

在用户指定路径写入；未指定时使用 `Topics/{Topic}-Survey.md`，并明确 frontmatter/标题中的 comparison scope。至少包含：

- **Scope**：封闭论文清单、选择依据与不可得项。
- **Comparison dimensions**：问题设定、核心假设、方法、训练数据、评测、效率与适用边界。
- **Evidence matrix**：每项结论对应具体论文 wikilink、section/figure/table 或本地页码。
- **Agreement & contradictions**：一致结论、冲突证据及不可直接比较的原因。
- **Takeaways & open questions**：跨论文 pattern、仍缺的证据、可证伪问题。
- **调研日志**：处理统计、失败与降级；注明未做外部发现。

不得因为清单论文没有共同 benchmark 而强行排出名次；先解释 setup 差异和可比性。

新建或更新时使用：

```yaml
---
title: <Topic 全名>
description: <一句话描述范围与核心发现>
tags: [...]
date_updated: YYYY-MM-DD
year_range: YYYY-YYYY
---
```

每个论文事实用已有 `[[论文笔记]]` 追溯；外部网页只作来源补充，并保留 URL 与访问日期。无法验证的信息标成 unknown，不补造引用、年份、作者、数字或结论。

### 5. 追加日志

串行追加到 `Workbench/logs/YYYY-MM-DD.md`；不存在时先写 `# YYYY-MM-DD`：

```markdown
### [HH:MM] literature-survey
- **input**: <topic 或本地论文集>
- **mode**: external-topic | local-set
- **output**: [[Topics/{Topic}-Survey]]
- **stats**: 侦察 survey N 篇，新增论文 N 篇，对比论文 N 篇
- **observation**: <一句话核心发现>
- **issues**: <未能获取的论文及原因；无则 none>
```

## Guard

- 每个事实、数字和引用都必须能回溯到具体论文笔记、原始来源位置或有 URL 的官方来源；不确定就标 unknown，禁止虚构 citation。
- 外部模式必须遵守预先记录的 topic、时间窗口与停止条件；本地模式必须把显式论文集当作封闭集合，不得静默扩大范围。
- 以 arXiv ID、DOI、笔记路径和规范化标题去重；不重复 digest、不创建同论文的第二份笔记。
- 不覆盖已有论文笔记，不删除现有 survey 中仍有效的用户内容，不直接修改 DomainMap 或候选范围外的笔记。
- 并行仅在运行时支持、用户授权、任务独立且无共享写入时启用；否则顺序执行。
- 来源无法访问时记录尝试、原因和缺口；不要用搜索摘要或二手转述冒充已读原文。

## Verify

### 范围与来源

- [ ] 已明确记录 `external-topic` 或 `local-set`；本地模式的输出包含完整封闭清单，且没有清单外新增论文笔记。
- [ ] 已读取 `DomainMaps/_index.md`；存在相关 DomainMap 时已读取但未修改。
- [ ] 现有目标文件的 `date_updated`、论文 wikilink 和用户内容已在更新前读取并保留。
- [ ] 外部模式记录了查询、时间窗口、1-3 个锚点或“无参考 survey”，且停止条件已满足；本地模式注明未做外部发现。
- [ ] 候选已按稳定标识与已有收录清单去重。

### 笔记与综合

- [ ] “需 digest”中的每篇都已执行 `paper-digest` 或记录实际获取失败；没有为控时长主观跳过。
- [ ] 外部模式中所有纳入综合且 `rating >= 2` 的笔记均已完整读取；本地模式已完整读取显式清单中的每篇笔记，不按 rating 跳过；每个 claim 可追溯到来源。
- [ ] 外部模式包含 Overview、Problem & Motivation、技术路线对比、Datasets & Benchmarks、Open Problems、调研日志；结构与新 survey taxonomy 的关系可解释。
- [ ] 本地模式包含 Scope、Comparison dimensions、Evidence matrix、Agreement & contradictions、Takeaways & open questions、调研日志；比较结论没有跨不兼容 setup 强排。
- [ ] 所有论文引用使用存在的 `[[wikilink]]`；不可得项只出现在 issues/调研日志；没有伪造 citation、残留 `%%...%%` 或占位符。
- [ ] 增量更新没有无故删除旧论据；DomainMap 更新仅作为建议，没有直接修改 DomainMap。

### 日志

- [ ] 日志只追加一次，mode、统计、失败项与最终报告一致。
