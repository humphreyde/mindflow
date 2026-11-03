---
type: paper
arxiv_id: 2603.16666
source_vault: notes
source_path: PaperNotes/world model/Fast-WAM.md
date_migrated: 2026-11-03
title: "Fast-WAM: Do World Action Models Need Test-time Future Imagination?"
method_name: "Fast-WAM"
authors: [Tianyuan Yuan, Zibin Dong, Yicheng Liu, Hang Zhao]
year: 2026
venue: arXiv
tags: [world-action-model, video-co-training, embodied-ai, flow-matching]
zotero_collection: "world model"
image_source: online
arxiv_html: https://arxiv.org/html/2603.16666
created: 2026-09-11
---

# 论文笔记：Fast-WAM: Do World Action Models Need Test-time Future Imagination?

## 元信息

| 项目     | 内容                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 机构     | Institute for Interdisciplinary Information Sciences, Tsinghua University；Galaxea AI                                                                                                       |
| 日期     | March 2026                                                                                                                                                                                 |
| 项目主页   | [Fast-WAM](https://yuantianyuan01.github.io/FastWAM/)                                                                                                                                      |
| Zotero | Item `87XCE8U2`；附件 `GV64DXZQ`                                                                                                                                                              |
| 对比基线   | π₀、π₀.₅、Motus、LingBot-VA、OpenVLA                                                                                                                                                           |
| 链接     | [arXiv](https://arxiv.org/abs/2603.16666) / [HTML](https://arxiv.org/html/2603.16666) / [Code](https://github.com/yuantianyuan01/FastWAM) / [Model](https://huggingface.co/yuanty/fastwam) |
<!-- code-companion-link:start -->

**Code companion:** Implementation companion

<!-- code-companion-link:end -->

---

## 一句话总结

> WAM 的主要收益来自训练期视频联合训练所塑造的世界表征，而非推理期显式生成未来视频；删掉后者后，Fast-WAM 仍保持性能且延迟降至 190 ms。

---

## 核心贡献

1. **拆开两个长期纠缠的因素**：在统一 backbone、tokenization 和训练配方下，分别研究训练期 [[Video Co-training|video co-training]] 与测试期 [[Imagine-then-Execute|future imagination]] 的价值。
2. **Fast-WAM 架构**：训练时联合学习未来视频与动作，推理时彻底移除未来视频分支，仅用视频 DiT 对当前观测做一次前向编码，再由 action expert 生成动作块。
3. **受控证据与效率收益**：Fast-WAM 在 RoboTwin / LIBERO 上达到 91.8% / 97.6%，与两种显式想象变体接近；去掉视频联合训练则降至 83.8% / 93.5%。其 190 ms 延迟比 Fast-WAM-IDM 的 810 ms 快 4.26×。

---

## 问题背景

### 要解决的问题

[[World Action Model|World Action Models（WAMs）]] 常把“预测未来视觉状态”和“生成机器人动作”绑定在一起。已有方法的强性能究竟来自：

1. 训练时的视频预测辅助目标，让网络学到物理动态与交互结构；还是
2. 推理时真正把未来帧生成出来，再据此决定动作？

### 现有方法的局限

- [[Imagine-then-Execute|Imagine-then-execute]] 需要迭代视频去噪，实时控制延迟高。
- 既有 WAM 往往同时使用训练期视频建模和推理期未来生成，无法做干净归因。
- 显式未来视频可能是一种昂贵的中间表示：控制最终只需要动作，不一定需要像素级未来。

### 本文的动机

若视频预测的主要价值是把物理先验写进 latent representation，那么测试时应能直接复用该表征生成动作，而无需把未来视频完整解码出来。Fast-WAM 因而把 [[World Model|world modeling]] 视为训练期 representation-learning signal，而不是推理期必须执行的规划步骤。

---

## 方法详解

### 模型架构
<!-- code-link-模型架构-3a00abb258a5:start -->
> [!code] Implementation
> Repository mapping · [Pinned source](<https://github.com/yuantianyuan01/FastWAM/blob/7faa71108368fbb3b6885649f112af607427a2d4/src/fastwam/models/wan22/fastwam.py#L397-L418>)
<!-- code-link-模型架构-3a00abb258a5:end -->

Fast-WAM 是一个带共享 attention 的 Mixture-of-Transformer 架构：

- **输入**：语言指令 $l$、当前多相机观测 $o$ 与训练期未来帧；多相机图像先拼接。
- **World backbone**：Wan2.2-5B 的视频 [[DiT]]、T5 text encoder 和 video VAE。
- **Action expert**：约 1B 参数、hidden dimension $d_a=1024$ 的独立 action DiT。
- **输出**：长度 $H=32$ 的 [[Action Chunking|动作块]] $a_{1:H}$。
- **总参数量**：约 6B。
- **视频目标**：时间维 4× 下采样，每个 chunk 使用 9 帧 latent video tokens。

### 三组 token 与结构化 attention mask

训练时包含三类 token：

1. **当前首帧的 clean latent tokens**：两个分支共享的视觉锚点；不读取其他 token。
2. **未来帧的 noisy latent tokens**：仅服务于视频建模；在视频分支内双向注意，并可读取首帧。
3. **Action tokens**：在 action branch 内双向注意，并可读取首帧；不能读取未来视频 token。

所有 token 均通过 cross-attention 读取语言 embedding。最关键的约束是动作 token 在训练时也看不到未来视频 token，从结构上阻止 future-information leakage。这样，推理时删除未来视频分支不会制造训练—推理输入不一致。

### 训练与推理路径
<!-- code-link-训练与推理路径-d5cc6e8d7bfb:start -->
> [!code] Implementation
> Repository mapping · [Pinned source](<https://github.com/yuantianyuan01/FastWAM/blob/7faa71108368fbb3b6885649f112af607427a2d4/src/fastwam/models/wan22/fastwam.py#L979-L1159>)
<!-- code-link-训练与推理路径-d5cc6e8d7bfb:end -->

- **训练**：对动作 token 与未来视频 latent 同时做 [[Flow Matching]]，联合优化动作损失和视频损失。
- **推理**：只保留当前首帧 latent；视频 DiT 单次前向产生 world-grounded features，action expert 再用 10 个去噪步骤输出动作块。
- **效果**：保留训练期世界建模正则，却省掉迭代未来视频生成。

### 受控变体

| 变体 | 训练期视频目标 | 测试期未来生成 | 动作如何使用未来信息 |
|------|----------------|----------------|----------------------|
| Fast-WAM | ✓ | ✗ | 当前观测的 latent world representation |
| Fast-WAM-Joint | ✓ | ✓ | 视频与动作 token 在同一去噪过程中共享 attention |
| Fast-WAM-IDM | ✓ | ✓ | 先生成未来视频，再以其 representation 条件化动作 |
| w/o video co-train | ✗ | ✗ | 与 Fast-WAM 相同架构，但仅训练动作目标 |

这个对照组设计比单纯和外部模型比较更有说服力：前三者共享实现框架，第四者只移除视频目标，因而较好地隔离了两个因素。

---

## 关键公式

### 公式 1：[[VLA|标准视觉运动策略]]

$$
p(a_{1:H}\mid o,l).
$$

**含义**：标准策略直接把当前观测和语言指令映射为未来 $H$ 步动作。

**符号说明**：
- $o$：当前视觉观测。
- $l$：任务语言指令。
- $a_{1:H}$：长度为 $H$ 的动作块。

### 公式 2：[[Imagine-then-Execute|先想象、再执行的分解]]

$$
p(a_{1:H}\mid o,l)=\int p(v_{1:T}\mid o,l)\,p(a_{1:H}\mid o,l,v_{1:T})\,dv_{1:T}.
$$

**含义**：先从当前上下文生成未来视觉轨迹，再以想象到的未来为条件预测动作；积分表示边缘化所有可能的未来。

**符号说明**：
- $v_{1:T}$：预测跨度为 $T$ 的未来视觉观测。
- $p(v_{1:T}\mid o,l)$：未来视频生成模型。
- $p(a_{1:H}\mid o,l,v_{1:T})$：依赖未来视觉的动作模型。

### 公式 3：[[World Action Model|Fast-WAM 直接策略]]

$$
p_{\theta}(a_{1:H}\mid o,l).
$$

**含义**：Fast-WAM 在测试时恢复为直接策略接口，不显式采样未来观测。

**符号说明**：
- $\theta$：Fast-WAM 参数。
- $a_{1:H},o,l$：分别为动作块、当前观测和语言指令。

### 公式 4：[[World Model|潜在世界表征条件化]]

$$
p_{\theta}(a_{1:H}\mid o,l)=p_{\theta}(a_{1:H}\mid z(o,l)).
$$

**含义**：动作由当前上下文经过视频 backbone 单次前向得到的世界表征 $z(o,l)$ 参数化，而非由生成的未来帧参数化。

**符号说明**：
- $z(o,l)$：受视频联合训练塑造的 latent world representation。
- $p_\theta(\cdot)$：action expert 所表示的条件动作分布。

### 公式 5：[[Flow Matching|线性插值路径]]

$$
y_t=(1-t)y+t\epsilon.
$$

**含义**：在数据样本 $y$ 与高斯噪声 $\epsilon$ 之间构造连续概率路径。

**符号说明**：
- $y$：动作块 $a_{1:H}$ 或未来视频 latent $z_{1:T}$。
- $\epsilon\sim\mathcal{N}(0,I)$：高斯噪声。
- $t\in(0,1)$：logit-normal noise schedule 采样的时间步。

### 公式 6：[[Flow Matching|速度场损失]]

$$
\mathcal{L}_{\mathrm{FM}}(y)=
\mathbb{E}_{y,\epsilon,t}\left[
\left\|f_{\theta}(y_t,t,o,l)-(\epsilon-y)\right\|_2^2
\right].
$$

**含义**：模型学习从数据到噪声方向的条件速度场，推理时数值积分反向生成目标。

**符号说明**：
- $f_\theta$：条件速度场网络。
- $y_t$：插值后的 noisy sample。
- $\epsilon-y$：该路径上的目标速度。

### 公式 7：[[Flow Matching|动作生成损失]]

$$
\mathcal{L}_{\mathrm{act}}=\mathcal{L}_{\mathrm{FM}}(a_{1:H}).
$$

**含义**：将通用 flow-matching 目标实例化到 action chunk。

**符号说明**：
- $\mathcal{L}_{\mathrm{act}}$：动作分支损失。
- $a_{1:H}$：真值动作块。

### 公式 8：[[Video Co-training|视频联合训练损失]]

$$
\mathcal{L}_{\mathrm{vid}}=\mathcal{L}_{\mathrm{FM}}(z_{1:T}).
$$

**含义**：将相同的 flow-matching 目标用于未来视频 VAE latents，以学习物理与时序表征。

**符号说明**：
- $\mathcal{L}_{\mathrm{vid}}$：视频分支损失。
- $z_{1:T}$：预训练 VAE 编码的未来视频 latent tokens。

### 公式 9：[[Video Co-training|联合训练目标]]

$$
\mathcal{L}=\mathcal{L}_{\mathrm{act}}+\lambda\mathcal{L}_{\mathrm{vid}}.
$$

**含义**：动作生成是主任务，未来视频预测作为加权辅助目标共同训练。

**符号说明**：
- $\lambda$：视频联合训练权重；论文未报告其具体数值。
- $\mathcal{L}_{\mathrm{act}}$：动作 flow-matching 损失。
- $\mathcal{L}_{\mathrm{vid}}$：未来视频 latent flow-matching 损失。

---

## 关键图表

### Figure 1: Three WAM Paradigms / 三种 WAM 范式

![](https://arxiv.org/html/2603.16666v2/teaser_main_new.png)

**说明**：对比联合视频—动作去噪、先视频后动作的 causal WAM，以及 Fast-WAM。Fast-WAM 只在训练期保留视频去噪目标，测试时以当前观测单次编码后的 latent 直接生成动作。

### Figure 2: Architecture and Attention Masks / 架构与注意力掩码

![](https://arxiv.org/html/2603.16666v2/model_arch.png)

![](https://arxiv.org/html/2603.16666v2/mask.svg)

**说明**：图 (a) 展示 video DiT 与 action DiT 的共享 attention 架构；图 (b) 展示训练/推理 mask。动作 token 无法读取未来视频 token，因此训练期不存在未来信息泄漏，推理时可直接删除未来视频分支。

### Figure 3: Real-world Towel Folding / 真实机器人毛巾折叠

![](https://arxiv.org/html/2603.16666v2/figs/bench_grid_2560x720.png)

**说明**：Galaxea R1 Lite 上的长时程可变形物体操作。该任务同时考察闭环修正、物体动力学理解和动作效率。

### Figure 4: Real-world Performance and Latency / 真实任务性能与延迟

![](https://arxiv.org/html/2603.16666v2/method_scatter_latency.svg)

**说明**：Fast-WAM 的延迟为 190 ms，与 action-only 无视频联合训练变体相同；Joint 为 580 ms，IDM 为 810 ms。无视频联合训练变体成功率仅 10%，说明性能差异主要来自训练目标，而显式 future imagination 主要增加推理成本。

### Table 1: RoboTwin Results / RoboTwin 结果

| Method | Embodied pretraining | Clean | Randomized | Average |
|--------|:--------------------:|------:|-----------:|--------:|
| π₀ | ✓ | 65.92 | 58.40 | 62.2 |
| π₀.₅ | ✓ | 82.74 | 76.76 | 79.8 |
| Motus | ✓ | 88.66 | 87.02 | 87.8 |
| Motus from Wan2.2 | ✗ | 77.56 | 77.00 | 77.3 |
| LingBot-VA | ✓ | **92.90** | 91.50 | **92.2** |
| LingBot-VA from Wan2.2 | ✗ | 80.60 | — | 80.6 |
| **Fast-WAM (Ours)** | ✗ | 91.88 | **91.78** | 91.8 |
| **Fast-WAM Variants** |  |  |  |  |
| Fast-WAM | ✗ | 91.88 | 91.78 | 91.8 |
| Fast-WAM-Joint | ✗ | 90.84 | 90.32 | 90.6 |
| Fast-WAM-IDM | ✗ | 91.16 | 91.34 | 91.3 |
| Fast-WAM w/o video co-train | ✗ | 82.76 | 84.80 | 83.8 |

**说明**：Fast-WAM 在无 embodied pretraining 的条件下接近预训练 LingBot-VA；显式未来生成没有改善平均分，而移除视频联合训练造成 8.0 个百分点下降。

### Table 2: LIBERO Results / LIBERO 结果

| Method | Embodied pretraining | Spatial | Object | Goal | Long | Average |
|--------|:--------------------:|--------:|-------:|-----:|-----:|--------:|
| OpenVLA | ✓ | 84.7 | 88.4 | 79.2 | 53.7 | 76.5 |
| π₀ | ✓ | 96.8 | 98.8 | 95.8 | 85.2 | 94.1 |
| π₀.₅ | ✓ | 98.8 | 98.2 | 98.0 | 92.4 | 96.9 |
| LingBot-VA | ✓ | 98.5 | 99.6 | 97.2 | **98.5** | **98.5** |
| Motus | ✓ | 96.8 | 99.8 | 96.6 | 97.6 | 97.7 |
| **Fast-WAM (Ours)** | ✗ | 98.2 | **100.0** | 97.0 | 95.2 | 97.6 |
| **Fast-WAM Variants** |  |  |  |  |  |  |
| Fast-WAM | ✗ | 98.2 | 100.0 | 97.0 | 95.2 | 97.6 |
| Fast-WAM-Joint | ✗ | **99.6** | 99.4 | **98.2** | 96.8 | **98.5** |
| Fast-WAM-IDM | ✗ | 98.8 | 97.8 | 97.8 | 97.6 | 98.0 |
| Fast-WAM w/o video co-train | ✗ | 89.2 | 99.2 | 95.4 | 90.0 | 93.5 |

**说明**：Fast-WAM 比 π₀.₅ 高 0.7 点，且与显式想象变体相差不足 1 点；删除视频联合训练后下降 4.1 点，主要损失来自 Spatial 和 Long。

### Table 3: Per-task RoboTwin Results / RoboTwin 逐任务结果

缩写：FW = Fast-WAM，Joint = Fast-WAM-Joint，IDM = Fast-WAM-IDM，NoVid = w/o video co-train，LBVA = LingBot-VA。每种方法依次报告 Clean / Randomized 成功率。

| Task | FW C | FW R | Joint C | Joint R | IDM C | IDM R | NoVid C | NoVid R | LBVA C | LBVA R | π₀.₅ C | π₀.₅ R | Motus C | Motus R |
|------|-----:|-----:|--------:|--------:|------:|------:|--------:|--------:|-------:|-------:|--------:|--------:|--------:|--------:|
| Adjust Bottle | 100 | 100 | 98 | 99 | 94 | 99 | 98 | 100 | 90 | 94 | 100 | 99 | 89 | 93 |
| Beat Block Hammer | 99 | 97 | 100 | 98 | 98 | 98 | 80 | 92 | 96 | 98 | 96 | 93 | 95 | 88 |
| Blocks Ranking RGB | 100 | 100 | 100 | 100 | 100 | 99 | 88 | 86 | 99 | 98 | 92 | 85 | 99 | 97 |
| Blocks Ranking Size | 94 | 98 | 83 | 91 | 79 | 90 | 56 | 62 | 94 | 96 | 49 | 26 | 75 | 63 |
| Click Alarmclock | 100 | 100 | 100 | 100 | 98 | 100 | 100 | 98 | 99 | 100 | 98 | 89 | 100 | 100 |
| Click Bell | 100 | 100 | 100 | 98 | 100 | 96 | 100 | 100 | 100 | 100 | 99 | 66 | 100 | 100 |
| Dump Bin Bigbin | 97 | 96 | 95 | 95 | 93 | 98 | 92 | 94 | 89 | 96 | 92 | 97 | 95 | 91 |
| Grab Roller | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 |
| Handover Block | 95 | 81 | 93 | 91 | 97 | 94 | 58 | 46 | 99 | 78 | 66 | 57 | 86 | 73 |
| Handover Mic | 99 | 100 | 100 | 100 | 98 | 99 | 100 | 100 | 94 | 96 | 98 | 97 | 78 | 63 |
| Hanging Mug | 58 | 62 | 71 | 56 | 66 | 62 | 28 | 40 | 40 | 28 | 18 | 17 | 38 | 38 |
| Lift Pot | 100 | 100 | 100 | 100 | 100 | 100 | 92 | 90 | 100 | 99 | 96 | 85 | 96 | 99 |
| Move Can Pot | 90 | 88 | 97 | 99 | 97 | 100 | 80 | 68 | 94 | 97 | 51 | 55 | 34 | 74 |
| Move Pillbottle Pad | 100 | 99 | 99 | 100 | 98 | 100 | 88 | 96 | 99 | 99 | 84 | 61 | 93 | 96 |
| Move Playingcard Away | 100 | 100 | 100 | 100 | 99 | 100 | 94 | 96 | 100 | 99 | 96 | 84 | 100 | 96 |
| Move Stapler Pad | 77 | 64 | 85 | 81 | 89 | 85 | 64 | 78 | 91 | 79 | 56 | 42 | 83 | 85 |
| Open Laptop | 98 | 100 | 89 | 92 | 92 | 92 | 100 | 98 | 92 | 94 | 90 | 96 | 95 | 91 |
| Open Microwave | 62 | 45 | 3 | 14 | 54 | 53 | 46 | 52 | 82 | 86 | 34 | 77 | 95 | 91 |
| Pick Diverse Bottles | 80 | 85 | 86 | 87 | 87 | 89 | 58 | 62 | 89 | 82 | 81 | 71 | 90 | 91 |
| Pick Dual Bottles | 100 | 96 | 98 | 99 | 100 | 98 | 80 | 74 | 100 | 99 | 93 | 63 | 96 | 90 |
| Place A2B Left | 95 | 93 | 96 | 96 | 97 | 96 | 84 | 92 | 97 | 93 | 87 | 82 | 88 | 79 |
| Place A2B Right | 93 | 99 | 95 | 95 | 94 | 98 | 88 | 84 | 97 | 95 | 87 | 84 | 91 | 87 |
| Place Bread Basket | 91 | 93 | 89 | 94 | 91 | 97 | 74 | 76 | 97 | 95 | 77 | 64 | 91 | 94 |
| Place Bread Skillet | 90 | 93 | 90 | 93 | 90 | 95 | 98 | 84 | 95 | 90 | 85 | 66 | 86 | 83 |
| Place Burger Fries | 96 | 99 | 100 | 100 | 97 | 99 | 94 | 96 | 97 | 95 | 94 | 87 | 98 | 98 |
| Place Can Basket | 71 | 69 | 50 | 23 | 37 | 28 | 72 | 72 | 81 | 84 | 62 | 62 | 81 | 76 |
| Place Cans Plasticbox | 99 | 96 | 98 | 98 | 98 | 96 | 98 | 96 | 100 | 99 | 94 | 84 | 98 | 94 |
| Place Container Plate | 96 | 100 | 99 | 98 | 100 | 96 | 94 | 98 | 99 | 97 | 99 | 95 | 98 | 99 |
| Place Dual Shoes | 94 | 88 | 93 | 89 | 85 | 87 | 80 | 74 | 94 | 89 | 75 | 75 | 93 | 87 |
| Place Empty Cup | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 99 | 99 | 98 |
| Place Fan | 96 | 96 | 99 | 96 | 97 | 95 | 80 | 88 | 99 | 93 | 87 | 85 | 91 | 87 |
| Place Mouse Pad | 83 | 89 | 96 | 91 | 97 | 93 | 64 | 76 | 93 | 96 | 60 | 39 | 66 | 68 |
| Place Object Basket | 89 | 88 | 86 | 81 | 87 | 82 | 82 | 90 | 91 | 88 | 80 | 76 | 81 | 87 |
| Place Object Scale | 90 | 97 | 96 | 99 | 99 | 99 | 86 | 80 | 96 | 95 | 86 | 80 | 88 | 85 |
| Place Object Stand | 90 | 94 | 92 | 98 | 96 | 100 | 82 | 92 | 99 | 96 | 91 | 85 | 98 | 97 |
| Place Phone Stand | 97 | 99 | 100 | 100 | 99 | 99 | 90 | 92 | 97 | 97 | 81 | 81 | 87 | 86 |
| Place Shoe | 96 | 99 | 95 | 97 | 95 | 98 | 92 | 90 | 98 | 98 | 92 | 93 | 99 | 97 |
| Press Stapler | 90 | 97 | 52 | 50 | 50 | 57 | 80 | 80 | 85 | 82 | 87 | 83 | 93 | 98 |
| Put Bottles Dustbin | 95 | 90 | 93 | 95 | 97 | 92 | 78 | 88 | 87 | 91 | 84 | 79 | 81 | 79 |
| Put Object Cabinet | 94 | 89 | 95 | 90 | 93 | 90 | 88 | 84 | 85 | 87 | 80 | 79 | 88 | 71 |
| Rotate QRcode | 93 | 89 | 91 | 92 | 91 | 86 | 82 | 78 | 96 | 91 | 89 | 87 | 89 | 73 |
| Scan Object | 89 | 92 | 92 | 92 | 93 | 90 | 78 | 86 | 96 | 91 | 72 | 65 | 67 | 66 |
| Shake Bottle | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 97 | 99 | 97 | 100 | 97 |
| Shake Bottle Horizontally | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 99 | 99 | 99 | 100 | 98 |
| Stack Blocks Three | 95 | 97 | 98 | 97 | 99 | 95 | 90 | 90 | 99 | 98 | 91 | 76 | 91 | 95 |
| Stack Blocks Two | 100 | 100 | 100 | 100 | 100 | 100 | 100 | 98 | 100 | 98 | 97 | 100 | 100 | 98 |
| Stack Bowls Three | 80 | 81 | 84 | 86 | 85 | 83 | 66 | 82 | 86 | 83 | 77 | 71 | 79 | 87 |
| Stack Bowls Two | 92 | 98 | 97 | 95 | 94 | 96 | 90 | 98 | 94 | 98 | 95 | 96 | 98 | 98 |
| Stamp Seal | 90 | 94 | 96 | 99 | 99 | 94 | 60 | 78 | 96 | 97 | 79 | 55 | 93 | 92 |
| Turn Switch | 61 | 59 | 73 | 72 | 59 | 74 | 66 | 66 | 44 | 45 | 62 | 54 | 84 | 78 |
| **Average** | **91.88** | **91.78** | **90.84** | **90.32** | **91.16** | **91.34** | **82.76** | **84.80** | **92.90** | **91.50** | **82.74** | **76.76** | **88.66** | **87.02** |

**说明**：总体均值支持论文主结论，但逐任务结果显示“未来想象无用”不能一概而论。例如 Open Microwave 上 Joint 很差而 Motus 很强，Press Stapler 上 Fast-WAM 明显优于两种显式想象变体；不同任务的差异远大于全局平均差异。

---

## 实验

### 数据集

| 数据集 | 规模 | 特点 | 训练与评测 |
|--------|------|------|------------|
| LIBERO | 4 suites × 10 tasks；每 suite 500 demonstrations | Spatial、Object、Goal、Long | 训练 20k steps；40 tasks 共 2,000 evaluation trials |
| RoboTwin 2.0 | 2,500 clean + 25,000 randomized demonstrations；50+ tasks | 双臂操作、重场景随机化 | 训练 30k steps；每任务在 clean / randomized 下各评测 100 trials |
| Real-world towel folding | 60 小时遥操作数据 | Galaxea R1 Lite；长时程、可变形物体、闭环控制 | 训练 30k steps；报告成功率、完成时间和推理延迟 |

### 实现细节
<!-- code-link-实现细节-2f423a98fa53:start -->
> [!code] Implementation
> Repository mapping · [Pinned source](<https://github.com/yuantianyuan01/FastWAM/blob/7faa71108368fbb3b6885649f112af607427a2d4/src/fastwam/trainer.py#L82-L104>)
<!-- code-link-实现细节-2f423a98fa53:end -->

- **Backbone**：Wan2.2-5B video DiT + T5 encoder + video VAE。
- **Action expert**：1B 参数，hidden dimension 1024；总模型约 6B。
- **Action / video horizon**：动作块 32 步；视频时间 4× 下采样后每 chunk 9 帧。
- **生成目标**：动作与视频分支使用相同 [[Flow Matching]]；$t$ 采用 logit-normal distribution。
- **推理**：10 个 action denoising steps；[[Classifier-free Guidance|CFG]] scale 1.0。
- **优化器**：AdamW，learning rate $10^{-4}$，weight decay 0.01，cosine annealing，BF16 mixed precision，gradient clipping 1.0。
- **变体细节**：Joint 开放视频—动作 token 间 attention；IDM 以 $p=0.5$ 对真值视频 token 加噪。
- **延迟硬件**：单张 NVIDIA RTX 5090D V2 32GB。
- **未报告**：batch size、训练硬件/总算力，以及损失权重 $\lambda$。

### 关键读数

- **RoboTwin**：Fast-WAM 91.8%，Joint 90.6%，IDM 91.3%，NoVid 83.8%。
- **LIBERO**：Fast-WAM 97.6%，Joint 98.5%，IDM 98.0%，NoVid 93.5%。
- **真实毛巾折叠**：NoVid 仅 10% 成功率；带视频联合训练的 Fast-WAM family 显著更强。预训练 π₀.₅ 仍是成功率和完成时间最强的方法。
- **延迟**：π₀.₅ 180 ms、Fast-WAM 190 ms、NoVid 190 ms、Joint 580 ms、IDM 810 ms。

---

## 批判性思考

### 优点

1. **问题切得很准**：把“训练期建模未来”和“测试期生成未来”解耦，是对 WAM 成本—收益结构的直接检验。
2. **控制变量较强**：Fast-WAM、Joint、IDM 和 NoVid 尽量共享 backbone、tokenization 与训练配方，比跨论文横向比较更可信。
3. **结论有跨场景一致性**：两个仿真 benchmark 与一个真实任务都呈现相同趋势，而且延迟收益明确。
4. **工程意义大**：190 ms 已接近常规 VLA 推理成本；代码、模型和两套数据均已公开。

### 局限性

1. **不能推出“想象永远无用”**：实验只研究单 action chunk，并明确省略外层 autoregressive rollout；在部分可观测、需要搜索或长程分支决策的任务中，显式未来可能更有价值。
2. **真实世界覆盖窄**：只有单一平台上的毛巾折叠任务，且训练数据达 60 小时，尚不足以证明跨机器人、跨任务的普适性。
3. **“视频预测带来世界理解”仍是间接解释**：NoVid 消融证明视频损失有用，但尚未排除它只是更强的辅助正则或数据增广；缺少 representation probing、替代辅助目标和数据量匹配对照。
4. **统计报告不足**：主表没有置信区间或多随机种子方差；逐任务结果波动很大，单一平均分可能掩盖 task-dependent effects。
5. **复现细节有缺口**：论文没有给出 $\lambda$、batch size、训练总算力等关键配置。代码仓库虽已公开，但论文文本本身不自足。
6. **“无 embodied pretraining”需谨慎解释**：模型没有机器人数据预训练，但仍继承 Wan2.2-5B 的大规模视频生成先验；这不是从零训练。

### 潜在改进方向

1. **自适应想象**：默认走 Fast-WAM；仅在不确定性高、任务长程或失败恢复时启用 IDM future imagination，以 latency budget 换取选择性规划。
2. **表征因果验证**：用 linear probing / dynamics probing 检查视频联合训练是否真的增强物体状态、接触、遮挡与动力学表征。
3. **替代辅助目标**：与 masked video modeling、temporal contrastive learning、next-latent prediction 等等算力目标比较，判断收益是否特属于视频生成。
4. **扩大任务分布**：加入导航、多阶段装配、遮挡下操作、需要反事实选择的任务，并报告何时显式想象开始胜出。

### 可复现性评估

- [x] 代码开源
- [x] 预训练模型公开
- [x] LIBERO / RoboTwin 处理后数据公开
- [ ] 论文训练细节完全自足
- [x] 标准仿真数据集可获取
- [ ] 真实机器人 60 小时数据确认公开

---

## 关联笔记

### 基于

- [[World Model]]：用未来视觉预测为策略注入物理与时序先验。
- [[DiT]]：Wan2.2-5B video backbone 与 action expert 都采用 diffusion transformer。
- [[Flow Matching]]：视频 latent 与动作块共享同一生成目标。

### 对比

- [[VLA]]：测试时接口同样是 observation + language → action，但训练时多了视频世界建模。
- [[Imagine-then-Execute]]：显式生成未来的传统 WAM 路径，也是本文主要移除的成本来源。

### 方法相关

- [[World Action Model]]：论文所研究的方法类别。
- [[Video Co-training]]：实验显示这是 WAM 增益的主要来源。
- [[Action Chunking]]：一次生成 32 步动作。
- [[Classifier-free Guidance]]：推理时 CFG scale 为 1.0。

---

## 速查卡片

> [!summary] Fast-WAM
> - **核心**：训练时预测未来、测试时不生成未来；把 WAM 当作 representation learning，而非必须执行的 video planner。
> - **方法**：Wan2.2-5B video DiT 单次编码当前帧，1B action expert 用 flow matching 生成 32 步动作块。
> - **结果**：RoboTwin 91.8%，LIBERO 97.6%，RTX 5090D 上 190 ms；NoVid 分别降至 83.8% / 93.5%。
> - **判断**：结论支持“视频联合训练比测试期想象更重要”，但不支持“显式想象对所有长程/不确定任务都无用”。
> - **代码**：[GitHub](https://github.com/yuantianyuan01/FastWAM)

---

*笔记创建时间：2026-09-11*
