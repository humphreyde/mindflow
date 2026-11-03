---
type: paper
arxiv_id: 2605.13778
source_vault: notes
source_path: PaperNotes/VLA/FLASH.md
date_migrated: 2026-11-03
title: "Realtime-VLA FLASH: Speculative Inference Framework for Diffusion-based VLAs"
method_name: "FLASH"
authors: [Jiahui Niu, Kefan Gu, Yucheng Zhao, Shengwen Liang, Tiancai Wang, Xing Hu, Ying Wang, Huawei Li]
year: 2026
venue: arXiv
tags: [vla, speculative-inference, flow-matching, diffusion-policy, inference-acceleration, real-time-control, libero]
zotero_collection: VLA
image_source: online
arxiv_html: https://arxiv.org/html/2605.13778v1
created: 2026-06-01
---

# 论文笔记：Realtime-VLA FLASH: Speculative Inference Framework for Diffusion-based VLAs

## 元信息

| 项目 | 内容 |
|------|------|
| 机构 | 中科院计算所 / 国科大 / 南京大学 / Dexmal |
| 日期 | May 2026 |
| 项目主页 | https://dexmal.github.io/realtime-vla-flash |
| 对比基线 | [[Pi0]]、[[Triton-Pi0]] |
| 链接 | [arXiv](http://arxiv.org/abs/2605.13778) / [HTML](https://arxiv.org/html/2605.13778v1) |

---

## 一句话总结

> 把 LLM 的 [[Speculative Decoding|投机推理]] 思想搬到 [[Flow Matching]] 型 [[Diffusion VLA|dVLA]] 上：用轻量 draft 模型出动作草稿，主模型 [[Action Expert]] 并行验证「插值端点一致性」，配合 [[Phase-aware Fallback|相位感知回退]] 把 [[Pi0|π₀]] 端到端推理延迟从 58 ms 降到 19.1 ms（3.04× 加速），任务成功率仅掉 0.3 pp。

---

## 核心贡献

1. **首次为 Flow Matching 型 dVLA 形式化 Speculative Inference**：核心难题是连续动作没有 token 概率作为接受准则，本文借 flow matching 的「线性插值路径」结构提出无概率的一致性检验。
2. **Realtime-VLA FLASH 双路径推理框架**：一条 flash path（draft + 并行验证），一条 full path（原 [[Pi0|π₀]] 流水线），运行时动态切换，输出可变长度的可执行前缀。
3. **Phase-aware Fallback**：以 [[Gripper Switch|夹爪开合信号]] 作为「即将进入精细调整阶段」的启发式，主动回退到 full path 防止误差累积。
4. **实验**：LIBERO 上单轮 flash 仅 7.8 ms（vs full 58 ms），任务级平均延迟 19.1 ms（3.04×）；真实传送带分拣在 15 m/min 极速下仅本方法成功。

---

## 问题背景

### 要解决的问题

[[Diffusion VLA|dVLA]]（如 [[Pi0|π₀]]）每个 [[Replanning Round|replanning round]] 都要跑一遍 Image Encoder + VLM prefill + 多步 [[Action Denoise]]，端到端延迟太高，无法应对反应式（latency-critical）操作任务，例如高速传送带分拣。

### 现有方法的局限

- **流水线加速**：小模型 / 层压缩 / token 剪枝 / 量化 / kernel 优化（如 [[Triton-Pi0]]）只是把"每一轮 full pipeline"做快，但仍每轮都跑完整路径。
- **Diffusion/Flow 加速**：[[Few-step Distillation|蒸馏成少步模型]]、[[One-step Diffusion|一步模型]] 要重训或改公式。
- **[[Speculative Decoding|投机推理]]**：成熟于自回归 LLM 与离散动作 VLA，但 dVLA 用 ODE 在连续动作空间积分速度场，没有 token-level 概率、没有自然接受准则，沿用不动。

### 本文的动机

观察：[[Flow Matching]] 训练时本就在「Gaussian 噪声 → 目标动作」的线性插值路径上学局部速度场。给定 draft endpoint，可以构造任意 τ 的中间态、用 [[Action Expert]] **并行**预测局部速度，进而**重构端点**与 draft 对比，实现免概率的一致性检验。再叠加「机器人大部分时间是平滑运动，少数 fine-adjustment 阶段才必须高保真」的先验，得到双路径架构。

---

## 方法详解

### 模型架构

FLASH 是建立在 π₀ 之上的**双路径推理运行时**，模型参数本身不改：

- **输入**：观测 $o_t = [I^1_t, \ldots, I^n_t, l_t, q_t]$（多视角图像、语言指令、机器人状态）
- **主模型**（Full Path，复用 π₀）：[[Vision Encoder]] → VLM prefill → [[KV Cache|视觉 KV Cache]] → [[Action Expert]] 做 10 步 [[Flow Matching|流匹配]] 去噪
- **Draft 模型**（Flash Path 新增）：单个 [[Gemma]] block + 线性 action head（约 110M 参数，相比 VLM 的 2.7B 轻量很多）
- **验证模块**：复用主模型的 [[Action Expert]]，在 $K$ 个验证 timestep 上**并行**调用一次
- **输出**：[[Action Chunking|动作块]] $A_t = [a_t, \ldots, a_{t+H-1}]$，$H=50$，每 12 个执行后 replan

### 核心模块

#### 模块 1: Draft Action Generation（草稿生成）

**设计动机**：候选动作生成必须比 full path 廉价才有意义。

**具体实现**：
- 复用主模型的 [[Vision Encoder]] 在当前图像上跑一次
- 状态 $q_t$ 通过线性层投到同隐空间
- 追加 $H$ 个 **learned action queries** $Q=[q_1, \ldots, q_H]$ 作为持久输出槽位
- 用 [[Blockwise Attention Mask|分块注意力掩码]]：视觉+语言为 prefix block、state 为单独 block、action queries 形成 action block；action block 可看到完整 prefix，并彼此可见，从而**一次前向并行预测整块**
- 共享线性 head：$\hat{a}^d_{t+h-1} = W_{act}z_h + b_{act}$
- 监督回归损失：训练时教师信号来自冻结的主模型 full path 输出（而非原始 demo 动作）

#### 模块 2: Multi-step Parallel Verification（并行验证）

**设计动机**：用 flow matching 的训练结构构造"无概率"的一致性检验。

**具体实现**：
- 给 draft 端点 $\hat{A}^{(d)}_t$ 和共享 Gaussian 噪声 $\varepsilon$，按 [[Flow Matching|流匹配]] 训练时的线性插值构造中间态 $\tilde{A}_{\tau} = \tau \hat{A}^{(d)}_t + (1-\tau)\varepsilon$
- 在 $K$ 个验证 timestep $\mathcal{T}=\{\tau_1, \ldots, \tau_K\}$ 上**并行**调用 [[Action Expert]] 预测速度场 $v_\theta$
- 重构端点：$\hat{A}_t(\tau) = \tilde{A}_\tau + (1-\tau) v_\theta(\tilde{A}_\tau, \tau | c_t, s_t)$
- 对 chunk 内每个动作 $h$ 计算 [[Distance Threshold|距离阈值]] $d^{(k)}_h$，取**满足阈值的最长前缀**
- $K$ 个 timestep 的前缀取**最小值**（保守接受）
- 只对连续位置/旋转通道用距离规则；离散的 gripper 通道单独处理

#### 模块 3: Phase-aware Fallback（相位感知回退）

**设计动机**：局部一致性检验看不到「即将进入精细调整阶段」的全局信号。在 bowl→plate 这种任务里，flash path 在最终放置阶段会漂移失败。

**具体实现**：
- gripper 通道 −1/1 编码 open/close
- 标准化后用 0 阈值检测 [[Gripper Switch]]，对应抓取/释放事件
- 任一验证 branch 内的 candidate chunk 出现 switch → 立刻回退到 full path
- 与「上一轮接受长度=0 → 立刻回退」共同构成双触发器

---

## 关键公式

### 公式 1: [[Action Chunking|动作块定义]]

$$
A_t = [a_t, a_{t+1}, \ldots, a_{t+H-1}]
$$

**含义**：dVLA 一次预测未来 $H$ 步的动作块；chunked execution 下只执行前缀就 replan。

**符号说明**：
- $a_{t+h}$：第 $h$ 步动作，含末端位置 $\Delta p_t$、旋转 $\Delta \theta_t$、夹爪 $g_t$ 三类语义通道
- $H$：chunk 长度（论文中 $H=50$）

### 公式 2: [[Flow Matching|ODE 形式的流匹配推理]]

$$
\frac{dA^\tau_t}{d\tau} = v_\theta(A^\tau_t, \tau, o_t), \quad A^0_t \sim \mathcal{N}(0, I)
$$

**含义**：[[Action Expert]] 用 ODE 从高斯噪声出发，沿学到的速度场 $v_\theta$ 数值积分到 $\tau=1$ 得到最终动作块；默认 10 个 denoising step。

**符号说明**：
- $A^\tau_t$：去噪进度 $\tau \in [0,1]$ 时的中间噪声态
- $v_\theta$：参数化的瞬时速度场
- $o_t$：当前观测条件

### 公式 3: [[Flow Matching|插值中间态构造]]（验证用）

$$
\tilde{A}_\tau = \tau \hat{A}^{(d)}_t + (1-\tau)\varepsilon, \quad \varepsilon \sim \mathcal{N}(0, I)
$$

**含义**：把 draft endpoint 与 Gaussian 噪声按 $\tau$ 线性插值，得到与训练时同分布的中间噪声态。

**符号说明**：
- $\hat{A}^{(d)}_t$：draft 模型给出的候选动作块
- $\varepsilon$：所有验证 timestep 共享的一份噪声

### 公式 4: [[Endpoint Reconstruction|端点重构]]

$$
\hat{A}_t(\tau) = \tilde{A}_\tau + (1-\tau)\, v_\theta(\tilde{A}_\tau, \tau \mid c_t, s_t)
$$

**含义**：在中间态 $\tilde{A}_\tau$ 处用 Action Expert 预测局部速度，乘以剩余去噪长度 $(1-\tau)$ 直接外推回端点，实现一步重构。draft 与重构端点接近 → 一致性通过。

**符号说明**：
- $c_t$：复用上一次 full path 的视觉 [[KV Cache]]
- $s_t$：每次验证刷新的最新机器人状态

### 公式 5: [[Speculative Inference|可执行前缀长度]]

$$
L^{(k)} = \sum_{h=1}^{H} \prod_{j=1}^{h} \mathbb{1}\!\left[d^{(k)}_j \le \delta\right], \quad L = \min_{k=1,\ldots,K} L^{(k)}
$$

**含义**：对每个验证 timestep $k$，从 chunk 起点开始累乘指示函数得到「全部连续满足阈值的最长前缀长度」；最终前缀取 $K$ 个 timestep 的最小值（保守）。$L=0$ 即 draft 完全被拒绝，立刻回退 full path。

**符号说明**：
- $d^{(k)}_h$：第 $k$ 个 timestep 下 draft 第 $h$ 步动作与重构动作的距离
- $\delta$：[[Distance Threshold|接受阈值]]（论文默认 0.15）
- $K$：验证 timestep 数量（默认 $K=2$）

### 公式 6: [[Action Chunking|Draft 训练损失]]

$$
\mathcal{L}_{draft} = \sum_{h=1}^{H} w_h\, \ell\!\left(\hat{a}^d_{t+h-1},\, a_{t+h-1}\right)
$$

**含义**：用 step-dependent 权重 $w_h$（前缀权重 $\gamma_{prefix}=0.9$、尾部权重 0.1）对 Smooth L1 / Huber 损失加权，让早期会被执行的动作权重更高。

**符号说明**：
- $\ell$：per-step Smooth L1 / Huber loss（$\beta=1.0$）
- $w_h$：第 $h$ 步权重，前 16 步采样为前缀加权区

### 公式 7: [[Speculative Inference|端点误差分解]]（理论分析）

$$
\|\hat{A}^{(d)}_t - A^\star_t\| \lesssim \delta + \varepsilon_{AE} + \varepsilon_{cond} + \varepsilon_{path}
$$

**含义**：被接受的 draft 与"真"full path 端点之间的误差受四项控制——接受阈值 $\delta$、Action Expert 重构误差 $\varepsilon_{AE}$、复用 KV cache 引入的条件偏移 $\varepsilon_{cond}$、draft-induced 与 target-induced 插值路径差 $\varepsilon_{path}$。这是启发式上界，不是形式化保证，是论文为何要叠加多 timestep + phase-aware fallback + full-path fallback 的依据。

**符号说明**：
- $A^\star_t$：当前 conditioning 下 full path 真实端点
- $\varepsilon_{AE}, \varepsilon_{cond}, \varepsilon_{path}$：三类系统误差

---

## 关键图表

### Figure 1: Overview of Realtime-VLA FLASH

![Figure 1](https://arxiv.org/html/2605.13778v1/x1.png)

**说明**：(a) 标准同步 dVLA 推理每个 replanning round 都跑 full pipeline（96 ms），导致动作过时、抓取失败；(b) FLASH 把多数轮缩短到 < 8 ms 的 [[Speculative Inference|投机轮]]，机器人能及时反应、完成抓取；(c) Flash Path 示意：Draft Model 提案 $\alpha_1,\ldots,\alpha_7$，[[Action Expert]] 在 $\tau_1, \tau_2$ 两个 timestep 并行重构 $\hat{\alpha}_1,\ldots,\hat{\alpha}_7$，执行通过一致性检验的最长前缀（图中第 5、6、7 个不一致，故只接受前 4 个）。

### Figure 2: Roofline Analysis of π₀ Inference

![Figure 2](https://arxiv.org/html/2605.13778v1/x2.png)

**说明**：在 NVIDIA RTX 4090D 上对 π₀ 三阶段做 [[Roofline Model|roofline 分析]]：峰值 FP16 147 TFLOPS、内存带宽 1008 GB/s、平衡算术强度 145.79 FLOPS/Byte。**Image Encoder 与 VLM Prefill 落在 compute-bound 区**（应消除冗余计算，故 cache 复用合理），**Action Denoise 落在 memory-bound 区**（每步反复读 cache 又无法跨步并行，留下空闲算力 → 启发并行验证）。三阶段延迟 11.3 / 26.7 / 20.0 ms。

### Figure 3: Realtime-VLA FLASH Framework

![Figure 3](https://arxiv.org/html/2605.13778v1/x3.png)

**说明**：(a) 双路径架构：Full Path 跑 Encoder + VLM prefill + Action Denoise（> 50 ms）；Flash Path 跑 Encoder + Draft + Verify（< 8 ms），复用最近一次 full path 的 [[KV Cache]]。两个回退触发：① 上一轮 Accept=0；② Gripper switch。(b) Draft Model 结构：1 个 [[Gemma]] block，输入视觉 + 语言 + state，附 H 个 learned action queries，最后线性 action head 一次性出整块动作。

### Figure 4: Parallel Verification

![Figure 4](https://arxiv.org/html/2605.13778v1/x4.png)

**说明**：(a) π₀ 原方案：10 步顺序去噪生成动作块；(b) FLASH 在选定 timestep 并行重构端点 → 按动作做 [[Distance Threshold|距离阈值]] 检查 → 取最长可执行前缀；(c) 拒绝情形：所有重构端点都超阈值，回退 full path。

### Figure 5: Phase-aware Fallback on LIBERO-Spatial

![Figure 5](https://arxiv.org/html/2605.13778v1/x5.png)

**说明**：bowl-to-plate 任务 3D 轨迹对比。(a) 无 [[Phase-aware Fallback|相位感知回退]]：flash path 在最终 fine adjustment 阶段漂移、偏离 plate 边缘、任务失败；(b) 有回退：在 gripper switch 处切回 full path 完成精细放置、成功。说明局部一致性检验对"全局阶段切换"是盲的。

### Figure 6: Key-frame Visualization

![Figure 6](https://arxiv.org/html/2605.13778v1/x6.png)

**说明**：Figure 5 的关键帧。橙色边框 = flash-path 执行，蓝色边框 = fallback 后 full-path 执行。失败 rollout 把最终放置一直留在 flash path，导致碗未与盘对齐。

### Figure 7: Conveyor-belt Sorting Demo

![Figure 7](https://arxiv.org/html/2605.13778v1/x7.png)

**说明**：真实传送带分拣任务，两类物体（toy dog、hairbrush）。JAX-π₀ 失败，FLASH+Triton 成功，验证延迟降低直接扩展了可完成任务的速度区间。

### Figure 8: Real-world Robot Platform

![Figure 8](https://arxiv.org/html/2605.13778v1/x8.png)

**说明**：单臂 UR5 + 两个 Intel RealSense D435i 多视角相机，物体经传送带通过 reachable 区域。

### Table 1: Simulation Results on LIBERO

| Methods | Spatial | Object | Goal | 10 | SR | Lat. (ms) | /Act (ms) | ΔSR | Speedup |
|---|---|---|---|---|---|---|---|---|---|
| Torch-π₀ | 96.8 | 98.8 | 95.8 | 85.2 | 94.1 | 58.0 | 5.0 | – | 1.00× |
| Triton-π₀ | 96.4 | 98.8 | 95.0 | 86.6 | 94.2 | 39.7 | 3.5 | +0.1 | 1.46× |
| FLASH-π₀ | 96.4 | 99.2 | 94.6 | 83.4 | 93.4 | 34.9 | 3.0 | -0.7 | 1.66× |
| **FLASH+Triton-π₀** | **96.8** | **99.2** | **94.4** | **84.6** | **93.8** | **19.1** | **1.9** | **-0.3** | **3.04×** |

**说明**：FLASH 单独已 1.66×，叠加 [[Triton-Pi0|Triton]] 内核后 3.04×、per-action 1.9 ms，平均成功率仅 −0.3 pp。

### Table 2: Suite-level Flash-path Statistics

| LIBERO Suites | Acc.(%) FLASH | Acc.(%) +Tri. | FR.(%) FLASH | FR.(%) +Tri. | Lat.(ms) FLASH | Lat.(ms) +Tri. | /Act FLASH | /Act +Tri. |
|---|---|---|---|---|---|---|---|---|
| Spatial | 75.8 | 60.2 | 71.6 | 68.9 | 34.3 | 19.2 | 3.0 | 2.1 |
| Object | 78.1 | 89.3 | 72.4 | 86.4 | 34.6 | 12.6 | 3.0 | 1.2 |
| Goal | 81.4 | 66.9 | 63.7 | 62.4 | 37.5 | 20.5 | 3.3 | 2.1 |
| 10 | 82.4 | 62.5 | 57.5 | 49.6 | 33.2 | 24.1 | 2.8 | 2.3 |
| **Avg.** | **79.4** | **69.7** | **66.3** | **66.8** | **34.9** | **19.1** | **3.0** | **1.9** |

**说明**：Acc. = 接受前缀长度（按 replan size 12 归一化），FR. = flash-path round 占比。平均 66.8% 的 replanning round 走 flash path，且接受前缀覆盖了 69.7% 的 replan 窗口。

### Table 3: Ablation on LIBERO-10

| Configuration | SR (%) | Lat. (ms) |
|---|---|---|
| Baseline (Flash-path only) | 58.4 | 13.3 |
| + PF = 2 | 80.6 | 21.0 |
| + PF = 3 | 82.0 | 18.6 |
| + PF = 4 | 75.4 | 17.2 |
| + FB | 66.8 | 17.7 |
| **+ FB & PF = 2** | **84.6** | **24.1** |
| + FB & PF = 3 | 81.6 | 21.9 |
| + FB & PF = 4 | 78.4 | 20.2 |

**说明**：PF=n 表示每 n 个 flash-path round 强制刷一次 full-path；FB = [[Phase-aware Fallback|相位感知回退]]。**单用 flash path SR 仅 58.4%**，加 FB 升到 66.8%，再叠 PF=2 升到 84.6%，证明三件套缺一不可。论文最终选 FB & PF=2 作为 LIBERO-10 的 success-latency trade-off。

### Table 4: Conveyor-belt Sorting Results

| Methods | Medium (10 m/min) Toy dog | Hairbrush | High (13 m/min) Toy dog | Hairbrush | Extra High (15 m/min) Toy dog | Hairbrush |
|---|---|---|---|---|---|---|
| JAX-π₀ | 20.0 | 50.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Triton-π₀ | 80.0 | 40.0 | 30.0 | 10.0 | 0.0 | 0.0 |
| **FLASH+Triton-π₀** | **80.0** | **90.0** | **50.0** | **30.0** | **20.0** | **10.0** |

**说明**：每条件 10 trials 成功率（%）。**15 m/min 极速下只有 FLASH 非零成功**；同步基线失败原因主要是「stale action chunk」——机器人按过时的传送带位置去抓，错过物体。

### Table 5: Draft Model Training Hyperparameters

| Item | Value |
|---|---|
| Optimizer | AdamW |
| Learning rate | $2 \times 10^{-3}$ |
| Weight decay | 0.01 |
| Batch size | 64 |
| Epochs | 100 |
| Precision | FP32 |
| Loss | Weighted Smooth L1 / Huber, $\beta = 1.0$ |
| Prefix weighting | Sampled prefix up to 16 steps, $\gamma_{prefix}=0.9$, tail 0.1 |
| Checkpoint | Best validation RMS over first 12 executable steps |
| Compute | 4× RTX 4090D, ~6h per draft model |

### Table 6: Inference Cost Breakdown

| Component | Torch-π₀ | Triton-π₀ | FLASH-π₀ | FLASH+Triton-π₀ |
|---|---|---|---|---|
| **Full-path round (ms)** | | | | |
| Image encoder | 11.3 | 4.7 | 11.3 | 4.7 |
| VLM prefill | 26.7 | 22.4 | 26.7 | 22.4 |
| Action denoise | 20.0 | 12.6 | 20.0 | 12.6 |
| Full-path total | 58.0 | 39.7 | 58.0 | 39.7 |
| **Flash-path round (ms)** | | | | |
| Image encoder | – | – | 11.0 | 4.7 |
| Draft model | – | – | 3.5 | 0.9 |
| Parallel verifier | – | – | 3.4 | 2.2 |
| Flash-path total | – | – | **17.9** | **7.8** |
| **Trajectory-level avg** | | | | |
| Replanning latency | 58.0 | 39.7 | 34.9 | 19.1 |
| Per-action latency | 5.0 | 3.5 | 3.0 | 1.9 |
| Speedup | 1.00× | 1.46× | 1.66× | **3.04×** |

**说明**：Triton 内核同时让 full path 和 flash path 都更快；flash-path 中 draft 与 verifier 仅占数毫秒，主要开销仍在 image encoder。

### Table 7: Verifier-only Ablation on LIBERO-10

| K | δ | SR (%) | Lat. (ms) | /Act | Acc. (%) | FR. (%) |
|---|---|---|---|---|---|---|
| 4 | 0.20 | 82.6 | 35.7 | 4.2 | 13.9 | 18.8 |
| 4 | 0.15 | 86.2 | 39.9 | 4.4 | 6.8 | 9.2 |
| 4 | 0.10 | 85.0 | 47.5 | 4.5 | 1.8 | 2.1 |
| 4 | 0.05 | 84.4 | 52.4 | 4.5 | 0.0 | 0.0 |
| 4 | 0.00 | 86.4 | 52.3 | 4.5 | 0.0 | 0.0 |
| 2 | 0.20 | 54.3 | 10.3 | 0.9 | 91.8 | 94.3 |
| 2 | 0.15 | 58.4 | 13.3 | 1.5 | 65.6 | 83.0 |
| 2 | 0.10 | 79.4 | 21.1 | 3.3 | 23.3 | 40.9 |
| 2 | 0.05 | 93.5 | 44.9 | 4.5 | 2.0 | 2.5 |
| 2 | 0.00 | 85.6 | 47.9 | 4.1 | 0.0 | 0.0 |
| 1 | 0.20 | 54.9 | 13.5 | 1.2 | 99.7 | 95.4 |
| 1 | 0.15 | 53.8 | 12.5 | 1.1 | 99.4 | 95.4 |
| 1 | 0.10 | 51.0 | 12.9 | 1.2 | 84.8 | 92.4 |
| 1 | 0.05 | 84.2 | 28.5 | 4.0 | 11.4 | 19.6 |
| 1 | 0.00 | 86.8 | 49.8 | 4.2 | 0.0 | 0.0 |

**关键发现**：松阈值 → 更多走 flash + 更低延迟 + 不准 draft 也过；严阈值 / 更大 $K$ → 拒绝更多但延迟逼近 full path。论文选 $K=2, \delta=0.15$ 作为基础点（再靠 PF/FB 补回 SR）。

### Table 8: Cross-suite Threshold Sensitivity (K=2)

| δ | Spatial SR | Object SR | Goal SR | 10 SR | Spatial Lat | Object Lat | Goal Lat | 10 Lat | Avg SR | Avg Lat | /Act | Acc. | FR. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.30 | 95.8 | 99.2 | 86.6 | 53.8 | 12.0 | 11.1 | 11.8 | 9.9 | 83.9 | 11.1 | 1.0 | 99.7 | 91.3 |
| 0.25 | 93.6 | 98.4 | 87.6 | 53.8 | 11.9 | 11.3 | 11.8 | 10.0 | 83.4 | 11.1 | 1.0 | 98.8 | 91.4 |
| 0.20 | 94.8 | 98.6 | 86.4 | 54.3 | 11.8 | 11.3 | 11.9 | 10.3 | 83.5 | 11.2 | 1.0 | 95.1 | 90.9 |
| 0.15 | 96.0 | 99.2 | 90.8 | 58.4 | 12.3 | 12.6 | 12.5 | 13.3 | 86.1 | 12.7 | 1.4 | 77.5 | 84.9 |
| 0.10 | 97.2 | 98.8 | 92.6 | 79.4 | 19.5 | 20.7 | 19.5 | 21.1 | 92.0 | 20.4 | 3.0 | 30.5 | 46.6 |
| 0.05 | 93.8 | 98.8 | 94.4 | 87.2 | 41.0 | 40.2 | 40.9 | 41.6 | 93.5 | 41.0 | 4.1 | 2.0 | 2.5 |
| 0.00 | 97.0 | 97.6 | 96.2 | 85.6 | 47.4 | 47.2 | 47.2 | 47.9 | 94.1 | 47.5 | 4.1 | 0.0 | 0.0 |

**说明**：四个 suite 阈值敏感性模式一致，但 LIBERO-10 SR 波动最大，故作为 stress test。

### Table 9: Real-world Training Hyperparameters

| Item | Value |
|---|---|
| **Main Model fine-tuning** | |
| Batch size | 128 |
| Training steps | 20k |
| LR schedule | Cosine decay with 500 warmup steps |
| Peak / final LR | $1\times 10^{-4}$ / $1 \times 10^{-5}$ |
| **Draft model training** | |
| Optimizer | AdamW |
| Learning rate | $2\times 10^{-3}$ |
| LR schedule | Cosine, 1 warmup epoch, min LR $1\times 10^{-5}$ |
| Batch size | 64 / GPU |
| Epochs | 100 |
| Gradient clipping | Global norm 1.0 |
| Loss | Weighted Smooth L1 / Huber, $\beta = 1.0$ |
| Prefix weighting | Up to 20 steps, $\gamma_{prefix}=0.9$, tail 0.1 |
| Checkpoint | Best validation RMS over first 12 executable steps |
| Compute | 8× NVIDIA H20, ~12h fine-tune + 2h draft |

### Algorithm 1: Multi-Step Parallel Verification

```
Require: Draft chunk Â_t^(d), reused KV cache c_t, latest state s_t,
         verification timesteps T = {τ_1, ..., τ_K}, threshold δ
Ensure:  Executable prefix length L
1: Sample shared Gaussian noise ε for all verification timesteps
2: for all τ_k ∈ T in parallel do
3:     Ã_{τ_k}^(k) = τ_k · Â_t^(d) + (1 - τ_k) · ε
4:     v^(k) = v_θ(Ã_{τ_k}^(k), τ_k | c_t, s_t)        # Action Expert
5:     Â_t^(k) = Ã_{τ_k}^(k) + (1 - τ_k) · v^(k)       # endpoint reconstruction
6:     for h = 1, ..., H do
7:         d_h^(k) = Dist_cont(â_{t+h-1}^(d), â_{t+h-1}^(k))
8:     end for
9:     L^(k) = Σ_{h=1..H} Π_{j=1..h} 1[d_j^(k) ≤ δ]    # 最长全合格前缀
10: end for
11: Return L = min_k L^(k)                              # 保守取最小
```

---

## 实验

### 数据集

| 数据集 | 规模 | 特点 | 用途 |
|---|---|---|---|
| [[LIBERO]] Spatial/Object/Goal/10 | 4 suites × 10 tasks × 50 trials | 标准 dVLA 仿真 benchmark | 训练 draft（每 suite 一个）+ 测试 |
| 自采 conveyor-belt 数据 | 2 类物体 × 200 demos | UR5 + 双 RealSense D435i，传送带 6 m/min 采集 | LoRA 微调 + 真机评估 |

### 实现细节

- **主模型**：[[Pi0|π₀]] checkpoint，LoRA 微调 20k step（真机）
- **Draft 模型**：1 个 Gemma block + 线性 head，~110M 参数（vs VLM 2.7B）
- **优化器**：AdamW，lr $2\times 10^{-3}$，cosine schedule
- **训练**：100 epochs，Smooth L1 / Huber loss，prefix-weighted（$\gamma=0.9$, tail 0.1）
- **运行时**：$H=50$，每 12 步 replan；$K=2$ 验证 timestep，$\delta=0.15$；PF=2，FB 启用
- **硬件**：训练 4× RTX 4090D（仿真）/ 8× H20（真机）；推理 RTX 4090D
- **优化**：FLASH+Triton 复用 [[Triton-Pi0]] 的部分 kernel

### 可视化结果

- LIBERO bowl-to-plate：无 FB 时 flash-only 在终点漂移失败，有 FB 时 gripper switch 触发 fallback 精细放置成功
- 真实传送带：高速度下 JAX/Triton 因 stale chunk 总是抓在物体身后；FLASH 因 per-action 1.9 ms 几乎跟上传送带

---

## 批判性思考

### 优点

1. **真正把 LLM 投机解码搬到了 dVLA**：解决了「连续动作没自然概率接受准则」这一核心难题，思路简洁——用 flow matching 的训练结构本身做检验。
2. **不动主模型权重 / 不改训练目标**：只加一个 ~110M 的 draft、复用 Action Expert 做验证，工程上易于嵌入已有的 π₀ 部署管线。
3. **端点重构思路直接 + 廉价**：一次前向、一次 $(1-\tau)v$ 外推即可，与并行 $K$ 个 timestep 配合等价于「同时做 $K$ 个 1 步预测」，巧妙利用了 Action Denoise 阶段空闲的算力（见 Figure 2 roofline）。
4. **真机评估有说服力**：传送带分拣这种 reactive 任务直接验证「降延迟 → 扩速度区间」的工程价值。
5. **Ablation 详尽**：Table 3 / 7 / 8 把 PF、FB、K、δ 拆得很清楚。

### 局限性

1. **接受准则是启发式**：论文自己在 Appendix B 承认 endpoint check 不是 full-path 等价性的形式化保证，仅是局部一致性试探，依赖大量 fallback 兜底。
2. **阈值 δ 与 K 完全手工**：Table 7 显示 SR 对阈值极敏感（LIBERO-10 在 K=2 下 δ=0.20 vs 0.10 SR 差 25 pp），实际部署到新任务需重调。
3. **每个 LIBERO suite 训了独立的 draft**，跨场景泛化没验证。
4. **Phase-aware Fallback 只挂在 "gripper switch" 上**，对没有夹爪事件的精细任务（双手协调、复杂插装、deformable 物体）启发式可能失效。
5. **复用 KV Cache 的条件偏移 $\varepsilon_{cond}$ 没有量化**：随着 flash path 连续接受越多，cache 越陈旧；论文用 PF=2 强制刷新，但没系统分析"最大可连续 flash 次数"上限。
6. **真机 baseline 选得偏弱**：JAX-π₀ 是同步原版，没和 RTC（论文自己 cite 的 [2] [3]）真机对比，speedup 数字可能被高估。
7. **draft 的 teacher 是 frozen full-path**，意味着 draft 永远学不到 full path 的最新行为分布（如果未来在线微调主模型，draft 必须重训）。

### 潜在改进方向

1. **可学习的 adaptive verifier**：把 $\delta$ 和验证 timestep $\mathcal{T}$ 做成 context-dependent（如附录提到），用一个小网络从 observation/draft 不确定度自适应输出。
2. **与 [[Real-time Action Chunking|RTC]] 结合**：FLASH 的可变延迟与 RTC 的固定延迟假设冲突，二者结合能同时拿到「快」和「平滑」。
3. **以 [[Mean Flow]] / [[One-step Diffusion|一步生成]] 作 draft**：把 draft 换成 mean-flow 一步预测，结构更对齐主模型的 flow field，验证误差 $\varepsilon_{path}$ 更小。
4. **多触发器 phase 检测**：把 gripper switch 扩展到「速度突变 / 接触力突变 / 视觉 saliency 突变」，覆盖无 gripper 任务。
5. **边缘端部署**：作者在 Future Work 里提到，FLASH 减少 memory traffic，对内存带宽受限的 edge 设备意义更大。

### 可复现性评估

- [x] 论文有项目主页（https://dexmal.github.io/realtime-vla-flash）
- [ ] 代码开源（项目页未公开 repo 链接）
- [ ] 预训练 draft 模型
- [x] 训练细节完整（Table 5、Table 9）
- [x] 数据集可获取（LIBERO 公开；真机 demo 自采）

---

## 关联笔记

### 基于

- [[Pi0]]：主模型即 π₀，FLASH 直接套在 π₀ 推理流水线之外
- [[Flow Matching]]：验证用到训练时的线性插值结构
- [[Speculative Decoding]]：思想源自 LLM 投机解码 (Eagle 系列)
- [[Triton-Pi0]]：内核优化，FLASH+Triton 取最佳延迟

### 对比

- [[Spec-VLA]] / [[KERV]] / [[HEISD]]：autoregressive VLA 上的投机解码，本文是首个把它推到 flow-matching dVLA
- [[Diffusion Policy]]：原始扩散策略，无加速
- [[One-step Diffusion Policy]] / [[Mean Flow VLA]]：另一条「蒸馏成少步」加速路线
- [[Real-time Action Chunking|RTC]]：另一条「异步执行 + chunk 缝合」加速路线，与本文互补

### 方法相关

- [[Action Chunking]]：dVLA 标准执行策略
- [[Action Expert]]：被 FLASH 复用做并行验证
- [[KV Cache]]：复用上一次 full path 的视觉 prefix 是 FLASH 的关键
- [[Roofline Model]]：Figure 2 的分析工具，给出"Action Denoise memory-bound → 并行验证有算力余量"的依据
- [[LoRA]]：真机微调 main model
- [[Gemma]]：Draft 模型的 backbone block

### 硬件/数据相关

- [[LIBERO]]：仿真 benchmark
- [[UR5]]：真机平台
- [[Intel RealSense D435i]]：观测相机

---

## 速查卡片

> [!summary] Realtime-VLA FLASH
> - **核心**：把 LLM speculative decoding 搬到 flow-matching dVLA，draft 模型出动作草稿、Action Expert 用「插值端点重构」做并行一致性检验
> - **方法**：双路径 = full path (π₀) + flash path (1× Gemma draft + 端点重构验证 + 距离阈值取最长前缀 + gripper-switch 触发的 phase-aware fallback)
> - **结果**：LIBERO 19.1 ms / 3.04×，SR 仅 −0.3 pp；真实传送带 15 m/min 唯一非零成功
> - **代码**：项目页 https://dexmal.github.io/realtime-vla-flash（暂未见 GitHub）

---

*笔记创建时间: 2026-06-01*
