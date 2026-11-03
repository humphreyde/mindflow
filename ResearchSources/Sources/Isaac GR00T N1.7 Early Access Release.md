---
title: Isaac GR00T N1.7 Early Access Release
type: research-source
canonical_id: "url:https://github.com/NVIDIA/Isaac-GR00T/tree/n1.7-release"
source_type: article
platform: github
creator: NVIDIA
url: "https://github.com/NVIDIA/Isaac-GR00T/tree/n1.7-release"
alternate_urls: []
published: 2026-04-18
captured: 2026-09-30
capture_status: summarized
evidence_role: author-statement
related_papers: ["[[Topics/GR00T-Series-Survey|GR00T 系列综述]]"]
related_authors: []
related_code: []
duration_minutes:
---

# Isaac GR00T N1.7 Early Access Release

<!-- source-source:start -->
## 来源

- 链接：[来源](<https://github.com/NVIDIA/Isaac-GR00T/tree/n1.7-release>)
- 平台：github
- 创作者：NVIDIA
- 发布日期：2026-04-18
- 直接关联：
  - 相关论文：[[Topics/GR00T-Series-Survey|GR00T 系列综述]]
<!-- source-source:end -->

<!-- source-summary:start -->
## 摘要

N1.7 是 Early Access 代码与权重发布，而不是新的完整论文。主要变化是采用 Cosmos-Reason2-2B / Qwen3-VL backbone、加入 20K 小时 EgoScale 人类视频，并提供更完整的 ONNX/TensorRT 部署路径。官方明确说明完整 benchmark 和稳定功能集要等 GA，因此现阶段不应对性能增益下强结论。
<!-- source-summary:end -->

<!-- source-insights:start -->
## 关键洞察

### N1.7 更换为 Cosmos-Reason2/Qwen3-VL

- 主张：N1.7 用 Cosmos-Reason2-2B（Qwen3-VL 架构）替代 N1.6 的 Eagle 路径，并支持原始宽高比与 flexible resolution。
- 来源锚点：What's New in GR00T N1.7 — Key Changes from N1.6
- 关系：explains
- 证据：author-statement
- 关联对象：[[Topics/GR00T-Series-Survey#公开变化|N1.7 公开变化]]

### 20K 小时人类视频成为泛化主张的核心

- 主张：发布说明把 N1.7 的泛化与语言遵循改进归因于预训练加入 20K 小时 EgoScale 人类视频，但没有给出完整版本消融。
- 来源锚点：GR00T N1.7 overview
- 关系：supports
- 证据：author-statement
- 关联对象：[[Topics/GR00T-Series-Survey#为什么暂时不能下强结论|N1.7 证据边界]]

### EA 阶段尚无完整 benchmark

- 主张：NVIDIA 将完整 benchmark、生产支持与稳定功能集列为 GA 才提供的内容。
- 来源锚点：Early Access notice — Available at GA
- 关系：explains
- 证据：author-statement
- 关联对象：[[Topics/GR00T-Series-Survey#为什么暂时不能下强结论|N1.7 证据边界]]
<!-- source-insights:end -->

<!-- source-connections:start -->
## 与论文及代码的关联

- 相关论文：[[Topics/GR00T-Series-Survey|GR00T 系列综述]]
<!-- source-connections:end -->

<!-- source-verification:start -->
## 验证与分歧

- 证据角色：author-statement
<!-- source-verification:end -->

## 个人笔记
