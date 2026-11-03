---
title: "Training Dyna-2 at million-hour scale, repeatably"
type: research-source
canonical_id: "url:https://www.dyna.co/research/dyna-2-infrastructure"
source_type: article
platform: Dyna Robotics
creator: Dyna Robotics
url: "https://www.dyna.co/research/dyna-2-infrastructure"
alternate_urls: []
published: 2026-08
captured: 2026-10-29
capture_status: summarized
evidence_role: author-statement
related_papers: []
related_authors: []
related_code: []
duration_minutes:
---

# Training Dyna-2 at million-hour scale, repeatably

<!-- source-source:start -->
## 来源

- 链接：[来源](<https://www.dyna.co/research/dyna-2-infrastructure>)
- 平台：Dyna Robotics
- 创作者：Dyna Robotics
- 发布日期：2026-08
<!-- source-source:end -->

<!-- source-summary:start -->
## 摘要

Dyna Robotics 复盘 DYNA-2 百万小时规模训练的数据与训练基础设施。本来源的 episode 存储部分描述了从 H5 单帧 JPEG 迁移到 MCAP 的两项关键改造：用 H.264 与更大 GOP 降低视频体积，并按训练访问模式把相机与状态/动作写入互不共享的 topic-group chunks。文章报告，在内部遥操作 episode 上，存储从 80.3 降至 25.1 MB/相机分钟；相对图中 MCAP+H.264 per-topic 基线，样本读取延迟从 27.0 降至 9.4 ms，chunk fetch 从 11.33 降至 3.29。以上均为公司第一方工程数据，未公开 writer、chunk/GOP 参数、样本量与独立复现。
<!-- source-summary:end -->

<!-- source-insights:start -->
## 关键洞察

### 物理布局应服从共同访问模式

- 主张：机器人 episode 的逻辑 topic 可以保持细粒度，但物理 chunk 边界应按训练 sampler 的共同访问模式组织，使请求数随访问组数量而不是 topic 数量增长。
- 来源锚点：§ 2 Scaling challenges → Episode container: MCAP and topic-group chunking；Figure 2
- 关系：supports
- 证据：practitioner-know-how
- 关联对象：[[ResearchSources/Insights/访问模式驱动的机器人训练数据物理布局|访问模式驱动的机器人训练数据物理布局]]

### 编码压缩与 chunk 布局解决不同瓶颈

- 主张：H.264/GOP 主要降低存储体积，topic-group chunking 主要减少无关数据读取、range request 与解压次数；二者需要分开归因和消融。
- 来源锚点：Figure 3: storage size savings and read performance improvements
- 关系：supports
- 证据：author-statement
- 关联对象：[[ResearchSources/Insights/访问模式驱动的机器人训练数据物理布局|访问模式驱动的机器人训练数据物理布局]]
<!-- source-insights:end -->

<!-- source-connections:start -->
## 与论文及代码的关联

- 未提供直接关联。
<!-- source-connections:end -->

<!-- source-verification:start -->
## 验证与分歧

- 证据角色：author-statement
<!-- source-verification:end -->

## 个人笔记
