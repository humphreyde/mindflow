---
type: paper
arxiv_id: 2603.10448
source_vault: notes
source_path: PaperNotes/world model/DiT4DiT.md
date_migrated: 2026-11-03
title: "DiT4DiT: Jointly Modeling Video Dynamics and Actions for Generalizable Robot Control"
method_name: "DiT4DiT"
authors: [Teli Ma, Jia Zheng, Zifan Wang, Chunli Jiang, Andy Cui, Junwei Liang, Shuo Yang]
year: 2026
venue: arXiv
tags: [video-action-model, world-model, video-generation, flow-matching, robot-manipulation, humanoid, sim-to-real]
zotero_collection: "world model"
image_source: online
arxiv_html: https://arxiv.org/html/2603.10448v2
code_url: https://github.com/Mondo-Robotics/DiT4DiT
code_companion:
created: 2026-10-16
---

# 论文笔记：DiT4DiT: Jointly Modeling Video Dynamics and Actions for Generalizable Robot Control

## 元信息

| 项目 | 内容 |
|------|------|
| Authors | Teli Ma、Jia Zheng、Zifan Wang、Chunli Jiang、Andy Cui、Junwei Liang、Shuo Yang（Junwei Liang、Shuo Yang 为通讯作者） |
| 机构 | Mondo Robotics；HKUST(GZ)；HKUST |
| 日期 | March 2026；v2 更新于 2026-03-22 |
| 项目主页 | [DiT4DiT](https://dit4dit.github.io/) |
| 对比基线 | [[Papers/2503-GR00TN1.5|GR00T-N1.5]]、GR00T-N1.6、Qwen3DiT、[[Papers/2410-Pi05|π0.5]]、[[Papers/2505-FLARE|FLARE]] |
| 链接 | [arXiv](https://arxiv.org/abs/2603.10448) / [HTML](https://arxiv.org/html/2603.10448v2) / [Code](https://github.com/Mondo-Robotics/DiT4DiT) / [Models](https://huggingface.co/mondo-robotics/dit4dit-model) |

---

## 一句话总结

> DiT4DiT 联合训练视频与动作 DiT，以单步生成特征驱动高效、可泛化的机器人控制。

---

## 核心贡献

1. **双 DiT 的端到端 Video-Action Model**：把预训练 [[Video Generation Model|视频生成模型]] 与独立动作 [[DiT]] 串联为 [[Video-Action Model]]，让动作策略读取视频去噪过程的中间 hidden states，而不是最终重建帧。
2. **Dual Flow Matching 与 tri-timestep**：分别使用视频时间 $\tau_v$、特征抽取时间 $\tau_f$ 和动作时间 $\tau_a$，以联合损失同时优化未来视频 latent 和连续动作块。
3. **单步生成特征而非完整未来想象**：测试时只对随机未来 latent 做一次视频 DiT 前向，再用 4 步动作去噪输出控制；LIBERO / RoboCasa-GR1 分别达到 98.6% / 50.8%。

---

## 问题背景

### 要解决的问题

当前 [[VLA]] 多继承静态图文预训练表示，机器人数据必须独自承担运动、接触和状态转移学习。视频生成模型虽然在互联网视频上获得丰富时序先验，但已有机器人方法常将其用于多阶段数据生成、显式视觉规划或独立 [[Inverse Dynamics Model|逆动力学模型]]，尚未回答两个问题：

1. 视频生成能否成为比 grounding 或未来 VLM feature alignment 更有效的策略预训练代理目标？
2. 视频生成的中间表征应如何与动作生成联合训练，并满足实时控制？

#### Figure 1: Proxy objectives for scalable robot policy learning / 可扩展策略学习的代理目标

![Figure 1](https://arxiv.org/html/2603.10448v2/intro4.png)

**说明**：左侧比较 object grounding、FLARE-style 未来表征建模与视频生成三种代理目标；右侧是在 24 个 RoboCasa-GR1 任务上的训练周期和数据规模曲线。视频生成达到更高终值，论文据曲线阈值给出最高 7× 收敛和 >10× 数据效率，但没有提供多随机种子、误差棒或对应数字表。

### 现有方法的局限

- **静态 VLM backbone**：擅长物体与语言语义，但缺少连续运动和交互动态预训练。
- **显式 imagine-then-act**：完整未来视频的多步去噪与解码成本高，像素重建也未必保留最控制相关的信息。
- **FLARE-style latent alignment**：训练紧凑未来表征但不直接学习像素级连续动态；本文的 proxy study 认为其数据效率低于视频生成。
- **分阶段 video → IDM**：视频模型与动作模型独立优化，动作目标无法反向塑造视频 hidden states。

### 本文的动机

作者认为，视频生成的价值不一定是交付一张最终未来帧，而可能是其去噪网络内部逐渐形成的时空动态表示。因此，DiT4DiT 用动作损失直接监督这些中间特征：既保留视频预训练的动态先验，又避免测试时完整生成未来视频。

---

## 核心技术

### Flow Matching 基础

DiT4DiT 的视频和动作分支都采用 [[Flow Matching]]。论文约定 $\tau=0$ 为干净数据、$\tau=1$ 为高斯噪声。

#### 公式 1: [[Flow Matching|线性概率路径]]

$$
x_{\tau}=(1-\tau)x_0+\tau z,
\qquad \tau\in[0,1]
$$

**含义**：在干净样本 $x_0$ 与高斯噪声 $z$ 之间构造最优传输式直线路径。

**符号说明**：
- $x_0\sim p_{\mathrm{data}}$：干净数据样本。
- $z\sim\mathcal N(0,I)$：高斯噪声。
- $x_\tau$：时间 $\tau$ 的插值状态。

#### 公式 2: [[Flow Matching|目标速度场]]

$$
v^*(x_\tau,\tau)
=\frac{d x_\tau}{d\tau}
=z-x_0
$$

**含义**：直线路径的目标速度在整个轨迹上恒为噪声端与数据端之差。

**符号说明**：
- $v^*$：真实条件速度场。
- $z-x_0$：从干净数据指向噪声的方向。

#### 公式 3: [[Flow Matching|速度场回归损失]]

$$
\mathcal L_{\mathrm{FM}}
=\mathbb E_{x_0,z,\tau}
\left[
\left\lVert
v_\theta(x_\tau,\tau)-(z-x_0)
\right\rVert_2^2
\right]
$$

**含义**：网络在随机时间点预测目标速度，通过均方误差学习完整概率流。

**符号说明**：
- $v_\theta$：参数化速度网络。
- $\tau\sim\mathcal U[0,1]$：基础 flow-matching 时间采样。

#### 公式 4: [[Flow Matching|生成 ODE]]

$$
\frac{d x}{d\tau}=v_\theta(x,\tau),
\qquad x_1\sim\mathcal N(0,I)
$$

**含义**：推理从 $\tau=1$ 的噪声出发，反向积分到 $\tau=0$ 的数据分布。

**符号说明**：
- $x_1$：初始噪声。
- $v_\theta$：模型预测的瞬时速度。

#### 公式 5: [[Flow Matching|Euler 反向积分]]

$$
x_{\tau-\Delta\tau}
=x_\tau-\Delta\tau\,v_\theta(x_\tau,\tau)
$$

**含义**：视频生成与动作采样都使用一阶 Euler 法，从噪声端逐步走向干净样本。

**符号说明**：
- $\Delta\tau=1/N$：离散积分步长。
- $N$：采样步数。

### 模型架构

DiT4DiT 是一个双 DiT 级联架构：

- **输入**：当前 RGB 观测 $\mathbf o_t$、语言目标 $l$ 和本体状态 $s$。
- **Video DiT**：Cosmos-Predict2.5-2B，使用 causal video VAE 压缩图像，以 Cosmos-Reason1 多层语言 embedding 条件化。
- **Action DiT**：改自 GR00T-N1，输入 state tokens、noisy action tokens 和 learnable future tokens，通过 cross-attention 读取视频 hidden states。
- **输出**：可选未来视频 $\hat{\mathbf o}_{t+1}$ 与连续动作块 $\hat{\mathbf a}_t$。
- **训练参数量**：2.2B；视频 VAE 与文本编码器冻结，两个 DiT 联合微调。

#### Figure 2: Overview of DiT4DiT / 双 DiT 总体架构

![Figure 2](https://arxiv.org/html/2603.10448v2/pipe5.png)

**说明**：当前观测经 VAE 编码后进入 Video DiT；模型在指定 flow timestep 的中间层截取生成特征，作为 Action DiT 的 cross-attention 条件。训练同时回归视频与动作速度场；下半部分展示视频分支能够产生的 visual plan。

#### 公式 6: [[Video Generation Model|未来视觉动态分布]]

$$
\mathbf o_{t+1}
\sim p_v(\cdot\mid\mathbf o_t,l)
$$

**含义**：Video DiT 根据当前观测与语言目标建模未来视觉状态。

**符号说明**：
- $p_v$：视频生成分布。
- $\mathbf o_t,\mathbf o_{t+1}$：当前与未来观测。
- $l$：语言目标。

#### 公式 7: [[Inverse Dynamics Model|生成特征条件动作分布]]

$$
\mathbf a_t
\sim p_a\!\left(
\cdot\mid
\mathbf o_t,
\mathcal H(\mathbf o_{t+1}^{\tau_v})
\right),
\qquad
\mathbf o_{t+1}^{\tau_v}
\xrightarrow{\tau_v\to0}
\mathbf o_{t+1}
$$

**含义**：动作模型不必读取最终视频，而是读取视频去噪中间态的隐藏表示。

**符号说明**：
- $p_a$：动作生成分布。
- $\mathcal H$：Video DiT hidden-state hook。
- $\mathbf o_{t+1}^{\tau_v}$：流时间 $\tau_v$ 的未来视频状态。

#### 公式 8: [[Video-Action Model|视频—动作联合分布]]

$$
\mathbf o_{t+1},\mathbf a_t
\sim p_{va}(\cdot\mid\mathbf o_t,l)
$$

**含义**：训练目标不是两个互不相关的生成器，而是条件在当前观测与语言上的联合视频—动作分布。

**符号说明**：
- $p_{va}$：联合 Video-Action 分布。
- $\mathbf a_t$：动作块。

### 中间生成特征与 tri-timestep

Video DiT 不是只在最终输出层提供特征。论文在第 18 个 transformer block 设置 forward hook，并在 flow 时间 $\tau_f$ 读取 hidden states。Action DiT 使用 [[Adaptive LayerNorm|AdaLN]] 注入动作去噪时间，再通过 cross-attention 融合视频特征。

#### 公式 9: [[DiT|Video DiT 中间特征抽取]]

$$
\mathbf h_t^{\tau_f}
=\mathcal H[v_\theta^{\mathrm{video}}]
\left(
\mathbf z_{t+1}^{\tau_f},
\tau_f
\mid
\mathbf z_t^0,l
\right),
\qquad
\mathbf z_{t+1}^{\tau_f}
\xrightarrow{\tau_f\to0}
\mathbf z_{t+1}^{0}
$$

**含义**：在未来视频 latent 的去噪轨迹上选择一个 operating point，将视频 DiT 内部表征作为动作条件。

**符号说明**：
- $\mathbf z_t^0$：当前观测的干净 VAE latent。
- $\mathbf z_{t+1}^{\tau_f}$：时间 $\tau_f$ 的 noisy future latent。
- $\mathbf h_t^{\tau_f}$：提供给 Action DiT 的视频 hidden states。
- $\mathcal H[\cdot]$：指定 transformer block 的 forward hook。

#### Figure 3: Asymmetric tri-timestep design / 非对称三时间设计

![Figure 3](https://arxiv.org/html/2603.10448v2/tri_timestep_1.png)

**说明**：$\tau_v$ 均匀采样以覆盖视频完整生成路径；$\tau_a=1-\sigma$、$\sigma\sim\mathrm{Beta}(1.5,1)$，将动作训练容量集中在关键阶段；$\tau_f$ 选择动作所读取的生成特征。正文称其为固定 deterministic timestep，但 Algorithm 1 在训练时从离散时间桶采样 $\tau_f$，因此更稳妥的理解是“训练覆盖多个时间点，部署固定选择”。

### 联合训练

#### 公式 10: [[Video Co-training|Dual Flow-Matching 联合目标]]

$$
\begin{aligned}
\mathcal L_t^{\mathrm{total}}
={}&
\underbrace{
\mathbb E_{\tau_a,\epsilon}
\left[
\left\lVert
v_\phi^{\mathrm{action}}
\left(
\mathbf a_t^{\tau_a},\tau_a
\mid\mathbf h_t^{\tau_f},s
\right)
-(\epsilon-\mathbf a_t^0)
\right\rVert_2^2
\right]
}_{\mathcal L_{\mathrm{action}}}
\\
&+\lambda
\underbrace{
\mathbb E_{\tau_v,z}
\left[
\left\lVert
v_\theta^{\mathrm{video}}
\left(
\mathbf z_{t+1}^{\tau_v},\tau_v
\mid\mathbf z_t^0,l
\right)
-(z-\mathbf z_{t+1}^0)
\right\rVert_2^2
\right]
}_{\mathcal L_{\mathrm{video}}}.
\end{aligned}
$$

**含义**：动作速度场与视频速度场共同训练；动作梯度通过 $\mathbf h_t^{\tau_f}$ 回传到 Video DiT，使其生成表征变得 action-aware。

**符号说明**：
- $v_\phi^{\mathrm{action}}$：Action DiT 速度网络。
- $v_\theta^{\mathrm{video}}$：Video DiT 速度网络。
- $\epsilon,z$：动作和视频高斯噪声。
- $\mathbf a_t^0,\mathbf z_{t+1}^0$：干净动作块与未来视频 latent。
- $\lambda$：视频损失权重；论文未在配置表中给出具体值。

#### Algorithm 1: Joint Training of Video and Action DiT / 联合训练

```text
输入：观测 o_t、未来帧 o_{t+1}、动作 a^0、state s、语言 l、动作 mask M

1. z_t^0     = VAE_enc(o_t)
2. z_{t+1}^0 = VAE_enc(o_{t+1})
3. τ_v ~ U[0,1]，z ~ N(0,I)
4. z_{t+1}^{τ_v} = (1-τ_v)z_{t+1}^0 + τ_v z
5. 预测 video velocity；以 z-z_{t+1}^0 为目标计算 L_video
6. τ_f 从离散 timestep buckets 采样，并重新采样 future noise
7. h_t^{τ_f} = H(θ, future noise, τ_f, z_t^0, l)
8. σ ~ Beta(α,β)，τ_a = 1-σ，ε ~ N(0,I)
9. a_t^{τ_a} = (1-τ_a)a_t^0 + τ_a ε
10. Action DiT 以 h_t^{τ_f} 与 s 为条件预测 velocity
11. 用 mask M 计算归一化 L_action
12. L_total = L_action + λL_video，并联合更新 θ、φ
```

**说明**：视频 loss 与动作 condition 使用两次独立的 future-noise 构造；VAE 与文本编码器冻结，Video DiT 和 Action DiT 接收联合梯度。

#### Table 4: Model & training configurations / 模型与训练配置

| 模块 | Parameter | Value |
|---|---|---|
| Video DiT | Base VGM | Cosmos-Predict2.5-2B |
| Video DiT | Attention Implementation | FlashAttention 2 |
| Video DiT | Hidden Feature Dim | 2048 |
| Video DiT | Extract Layer | 18 |
| Action DiT | Action Model Type | DiT-B |
| Action DiT | Hidden Size | 2560 |
| Action DiT | Add Positional Embedding | True |
| Action DiT | Max Sequence Length | 1024 |
| Action DiT | Action Dim | 32 |
| Action DiT | State Dim | 64 |
| Action DiT | Future Action Window Size | 15 |
| Action DiT | Action Horizon | 16 |
| Action DiT | Past Action Window Size | 0 |
| Action DiT | Cross Attention Dim | 2048 |
| Action DiT | Dropout | 0.2 |
| Action DiT | Final Dropout | True |
| Action DiT | Interleave Self Attention | True |
| Action DiT | Norm Type | AdaLN |
| Action DiT | Num Layers | 16 |
| Action DiT | Output Dim | 2560 |
| Action DiT | Repeated Diffusion Steps (train) | 4 |
| Action DiT | Noise $\beta$ ($\alpha$) | 1.5 |
| Action DiT | Noise $\beta$ ($\beta$) | 1.0 |
| Action DiT | Noise $s$ | 0.999 |
| Action DiT | Num Timestep Buckets | 1000 |
| Action DiT | Num Inference Timesteps | 4 |
| Training | Per Device Batch Size | 8 |
| Training | Num of GPUs | 32 |
| Training | Max Train Steps | 100,000 |
| Training | Num Warmup Steps | 5,000 |
| Training | Warmup Ratio | 0.1 |
| Training | VGM LR | $1\times10^{-5}$ |
| Training | Action Model LR | $1\times10^{-4}$ |
| Training | LR Scheduler | Cosine with min LR |
| Training | Min LR | $5\times10^{-7}$ |
| Training | Gradient Clipping | 1.0 |
| Training | Gradient Accumulation Steps | 1 |
| Training | Optimizer | AdamW |
| Training | $\beta_1,\beta_2$ | $(0.9,0.95)$ |
| Training | $\epsilon$ | $1\times10^{-8}$ |
| Training | Weight Decay | $1\times10^{-8}$ |

**说明**：Video DiT 学习率比 Action DiT 小 10×；全局 batch size 为 256。表中同时给出 5,000 warmup steps 与 0.1 warmup ratio，但前者只占 100,000 steps 的 5%，是一个需要代码确认的报告差异。

### 推理与部署

动作推理不需要完整未来视频生成：模型对一个新采样的 future-noise latent 在固定 $\tau_f$ 上执行一次 Video DiT 前向、抽取第 18 层特征，然后 Action DiT 用 4 个 Euler steps 去噪动作。若需要可视化 visual plan，视频分支仍可独立执行 $N_v$ 步完整去噪并通过 VAE decoder 输出未来帧。

#### Algorithm 2: DiT4DiT Inference / 推理

```text
输入：当前观测 o_t、state s、语言 l；视频步数 N_v、动作步数 N_a

可选视频生成：
1. z_t^0 = VAE_enc(o_t)，future latent 从 N(0,I) 初始化
2. 对 i=0...N_v-1：在 τ_v=1-i/N_v 预测速度并做 Euler 反向更新
3. ô_{t+1} = VAE_dec(ẑ_{t+1})

动作生成：
4. 动作 â_t 与 future latent 分别从 N(0,I) 初始化
5. 仅在固定 τ_f 做一次 Video DiT 前向，得到 h_t^{τ_f}
6. 对 i=0...N_a-1：Action DiT 条件于 h_t^{τ_f},s 预测动作速度并反向更新
7. 返回动作 â_t；若启用视频路径，同时返回未来帧 ô_{t+1}
```

**说明**：部署默认 $N_a=4$，策略在单张 NVIDIA A100 上报告 6 Hz。它比完整 imagine-then-act 便宜，但仍需运行 2B Video DiT 的一次前向，并非仅保留轻量动作头。

---

## 实验

### 实验设置

#### 数据集与任务

模拟实验直接在目标 benchmark 上训练。真机实验先用 Fourier GR1 Pretrain 10K 的 241,450 episodes 做仿真预训练，再以 1,400 条 Unitree G1 遥操作数据微调。

#### Table 5: Details of the used datasets / 数据集配置

| Dataset | Episode Cnt | Embodiment | DoF |
|---|---:|---|---:|
| Fourier GR1 Unified 1K | 24,000 | GR1 humanoid | 29 |
| Fourier GR1 Pretrain 10K | 241,450 | GR1 humanoid | 29 |
| [[LIBERO]] | 1,693 | Franka Emika Panda | 7 |
| Real Robot | 1,400 | [[Unitree G1]] humanoid | 16 |

**说明**：LIBERO 正文按 4 个 suite × 500 trajectories 描述为 2,000 条，附录表则报告实际使用 1,693 episodes，可能反映过滤后的有效样本，但论文未解释差额。真机每项任务 200 条示范，共 7 项任务。

#### Figure 4: Real-world evaluation suite / Unitree G1 真机任务

![Figure 4](https://arxiv.org/html/2603.10448v2/imgs/real_exp.jpg)

**说明**：七项任务覆盖高精度空间操作（插花、叠杯、插盘）和多阶段执行（装箱、抽屉交互），统一只使用头部第一视角 RGB。

#### Figure 9: Robot system and teleoperation setup / 机器人与遥操作系统

![Figure 9](https://arxiv.org/html/2603.10448v2/imgs/teleop.jpg)

**说明**：[[Unitree G1]] 安装双 ALOHA 2 grippers 与 Intel RealSense D435i；操作者用 PICO VR 和 XRoboToolkit 收集同步遥操作轨迹。真实系统连续输出 16-DoF 动作，推理工作站为单张 RTX 4090。

#### 评测协议与实现细节

- **LIBERO**：Spatial / Object / Goal / Long 四个 suites，各 10 个任务；指标为平均成功率。
- **[[RoboCasa-GR1]]**：24 个任务，每任务 1,000 demonstrations；每任务 50 rollouts，最大 720 environment steps。
- **真机 G1**：7 个任务，每任务 20 independent rollouts，以成功率为主指标。
- **参数匹配基线**：Qwen3DiT 使用 Qwen3-VL-2B 和完全相同的 Action DiT；真机设置采用相同仿真预训练和真机微调流程。
- **“From scratch”边界**：表示不使用当前 benchmark 之外的机器人动作数据，不代表随机初始化；DiT4DiT 仍从 Cosmos-Predict2.5-2B 初始化。

### 主要结果

#### Table 1: LIBERO success rates / LIBERO 成功率（%）

| Method | Spatial | Object | Goal | Long | Average |
|---|---:|---:|---:|---:|---:|
| Diffusion Policy | 78.3 | 92.5 | 68.3 | 50.5 | 72.4 |
| Dita | 97.4 | 94.8 | 93.2 | 83.6 | 92.3 |
| $\pi_0$ | 96.8 | 98.8 | 95.8 | 85.2 | 94.2 |
| UniVLA | 96.5 | 96.8 | 95.6 | 92.0 | 95.2 |
| $\pi_{0.5}$ | 98.8 | 98.2 | 98.0 | 92.4 | 96.9 |
| OpenVLA-OFT | 97.6 | 98.4 | 97.9 | 94.5 | 97.1 |
| CogVLA | 98.6 | 98.8 | 96.6 | 95.4 | 97.4 |
| GR00T-N1.5 | 96.2 | 94.0 | 96.0 | 90.0 | 94.1 |
| Qwen3DiT (from scratch) | 98.0 | 98.8 | 96.0 | 93.6 | 96.6 |
| **DiT4DiT (from scratch)** | **98.4** | **99.6** | **98.6** | **97.6** | **98.6** |

**说明**：DiT4DiT 比参数匹配 Qwen3DiT 平均高 2.0 个百分点，Long 高 4.0 点。LIBERO 已接近饱和，因此 long-horizon 的差距比平均分更有信息量。

#### Table 2: RoboCasa-GR1 tabletop success rates / 24 任务成功率（%）

| Task | GR00T-N1.5 | GR00T-N1.6 | Qwen3DiT | DiT4DiT |
|---|---:|---:|---:|---:|
| BottleToCabinetClose | 40.0 | 36.0 | **50.0** | 48.0 |
| CanToDrawerClose | 56.0 | 28.0 | 48.0 | **74.0** |
| CupToDrawerClose | 50.0 | 12.0 | 42.0 | **52.0** |
| MilkToMicrowaveClose | **52.0** | 20.0 | 38.0 | 50.0 |
| PotatoToMicrowaveClose | 22.0 | 28.0 | 18.0 | **36.0** |
| WineToCabinetClose | **44.0** | 18.0 | 28.0 | 42.0 |
| FromCuttingboardToBasket | 46.0 | 42.0 | 42.0 | **52.0** |
| FromCuttingboardToCardboardbox | 44.0 | 40.0 | 30.0 | **48.0** |
| FromCuttingboardToPan | 58.0 | 62.0 | 50.0 | **76.0** |
| FromCuttingboardToPot | 48.0 | 60.0 | 44.0 | **62.0** |
| FromCuttingboardToTieredbasket | 28.0 | 48.0 | 36.0 | **50.0** |
| FromPlacematToBasket | 32.0 | 42.0 | 14.0 | **50.0** |
| FromPlacematToBowl | 52.0 | 34.0 | 28.0 | **56.0** |
| FromPlacematToPlate | **42.0** | **42.0** | 40.0 | 32.0 |
| FromPlacematToTieredshelf | 26.0 | 24.0 | **30.0** | 18.0 |
| FromPlateToBowl | 38.0 | 48.0 | 36.0 | **56.0** |
| FromPlateToCardboardbox | 40.0 | 44.0 | 36.0 | **58.0** |
| FromPlateToPan | 56.0 | 48.0 | 34.0 | **68.0** |
| FromPlateToPlate | 50.0 | **66.0** | 44.0 | 58.0 |
| FromTrayToCardboardbox | 36.0 | 42.0 | **48.0** | 38.0 |
| FromTrayToPlate | 54.0 | 52.0 | 44.0 | **56.0** |
| FromTrayToPot | 36.0 | **64.0** | 34.0 | 54.0 |
| FromTrayToTieredbasket | 34.0 | 42.0 | 36.0 | **46.0** |
| FromTrayToTieredshelf | 22.0 | **38.0** | 18.0 | **38.0** |
| **Average** | 41.8 | 40.8 | 36.2 | **50.8** |

**说明**：DiT4DiT 比 Qwen3DiT 高 14.6 个绝对百分点，并在 24 个任务中的 16 个取得最高值；但并非每项都占优，例如 FromPlacematToTieredshelf 和 FromTrayToCardboardbox 明显落后。

#### Figure 5: Real-world results on Unitree G1 / 真机成功率

![Figure 5](https://arxiv.org/html/2603.10448v2/real_task_res.svg)

**说明**：DiT4DiT 在七项任务上均优于 Qwen3DiT；相较 GR00T-N1.5，Arrange Flower 为 75% vs. 25%，Stack Cup 为 60% vs. 25%，Move Spoon 为 40% vs. 15%，Drawer Interaction 与 Box Packing 分别达到 90% 和 50%。每个点仅 20 次真机试验，论文未给置信区间。

### 泛化实验

模拟泛化只用 BottleToDrawer/Cabinet/Microwave 三类任务训练，测试时把 bottle 完全替换为 Can、Cup、Milk 和 Wine。DiT4DiT 在 Drawer/Cabinet/Microwave 上分别达到 54.5% / 34.0% / 30.5%，Qwen3DiT 为 32.0% / 24.5% / 17.0%。

#### Figure 6: Qualitative real-world generalization / 真机泛化定性结果

![Figure 6](https://arxiv.org/html/2603.10448v2/imgs/real_task_gene_exp.png)

**说明**：测试三种分布偏移：更换杯子、花瓶与花的类别/材质；将装箱对象从茄子换成玉米；将叠杯数量从 3 个改为 4 个。它展示的是执行序列，不能单独证明“物理抽象”机制。

#### Figure 7: Quantitative zero-shot generalization / 零样本泛化结果

![Figure 7](https://arxiv.org/html/2603.10448v2/task_gene.svg)

**说明**：左图为模拟新物体结果；右图为四项真机 OOD 测试。DiT4DiT 在 Arrange Flower(Category) 为 70%，GR00T-N1.5 / Qwen3DiT 为 10% / 0%；Stack Cup(Number) 保持 50%。结果支持 [[Open-World Generalization|OOD 泛化]]优势，但范围仍限于单一房间、相关物体替换与少量 trials。

### 消融实验

#### Figure 8: Architecture ablations / 架构消融

![Figure 8](https://arxiv.org/html/2603.10448v2/ablation_all_1.png)

**关键发现**：

1. **特征层**：早期层偏纹理，末端层过度服务像素重建，第 18 层成功率最高；全层平均接近但略低。
2. **视频去噪步数**：用于动作条件时，一次 Video DiT 前向最好，1→32 步呈单调下降，支持“抽象生成特征比确定的像素未来更适合控制”。
3. **Joint vs. decoupled**：joint training 的时间阶段 silhouette score 从 0.09 提升到 0.17；但这里只报告 t-SNE 和表征指标，没有给出 decoupled policy 的最终任务成功率。

### 效率与部署结果

#### Table 3: Deployment efficiency comparison / 部署效率

| Method | Trainable Param Cnt | Deploy Frequency |
|---|---:|---:|
| GR00T-N1.5 | 2.7B | 13 Hz |
| Qwen3DiT | 2.3B | 9 Hz |
| **DiT4DiT** | **2.2B** | 6 Hz |

**说明**：DiT4DiT 参数量略小，但 Video DiT 单次前向仍使频率低于两个 VLM 基线。表中 6 Hz 在单张 A100 上测得；附录说明真机工作站使用 RTX 4090，但没有报告对应频率。固定任务的语言 embedding 可预提取缓存。

### 定性未来视频

#### Figure 10: Future video rollouts / 未来视频生成结果

![Figure 10](https://arxiv.org/html/2603.10448v2/gen_plans.png)

**说明**：附录展示多任务 future-video rollouts，说明 Video DiT 保留了独立生成视觉计划的能力。动作默认路径不需要把这些视频完整去噪或解码，因此视觉质量不是部署控制的直接中间输出。

---

## 批判性思考

### 优点

1. **隔离了一个有价值的架构问题**：不是简单把视频生成器作为离线数据工具，而是让 action loss 直接塑造视频 DiT 中间层。
2. **参数匹配对照较强**：Qwen3DiT 使用同规模 Qwen3-VL-2B 和相同 Action DiT，特别是真机采用相同 sim-pretrain + real-finetune 流程，差距具有信息量。
3. **兼顾性能与部署**：只做一次视频前向和 4 步动作去噪，避免完整像素未来生成；6 Hz 足以作为中频闭环策略。
4. **证据覆盖较广**：包含 LIBERO、24-task RoboCasa-GR1、Unitree G1 真机、对象替换与组件消融。

### 局限性

1. **“视频生成目标更优”的归因不完全干净**：Cosmos-Predict2.5 与 Qwen3-VL 具有不同架构、预训练数据与先验，结果同时反映 backbone 与 objective 差异。
2. **“7× / >10× scaling proxy”证据偏弱**：只来自单个 RoboCasa-GR1 曲线，没有数字表、误差棒和多随机种子；主训练也没有加入外部无动作人类/互联网视频验证真正的数据扩展。
3. **Joint-training 消融不足**：t-SNE 与 silhouette score 表明时间结构更清晰，但不能替代 joint-vs-decoupled 的最终控制成功率。
4. **关键实现口径存在歧义**：正文称 $\tau_f$ 固定 deterministic，Algorithm 1 却在训练时采样；即使 $\tau_f$ 固定，输入 future latent 仍从高斯噪声采样。$\lambda$ 也未报告。
5. **“From scratch”容易误读**：它只排除额外机器人动作数据，DiT4DiT 仍继承 Cosmos 大规模视频预训练。
6. **真机统计有限**：每项 20 trials、无置信区间，只使用单头部相机；自遮挡、触觉缺失与跨房间鲁棒性未系统测试。
7. **不是可查询的规划型 WAM**：视频模型不根据候选动作预测后果，系统也不比较多个未来或做 MPC；“学到物理”主要由下游表现间接推断。

### 潜在改进方向

1. 在同一 Video DiT backbone、相同预训练数据和 compute 下比较 video FM、future-feature alignment、masked video modeling 与 temporal contrastive learning。
2. 加入大规模无动作人类视频，验证 proxy objective 是否真正减少机器人动作标签需求，而不只在已有 robot trajectories 上忽略 action 标签预训练。
3. 报告 $\tau_f$、$\lambda$、随机 future noise 的方差与多种子成功率，并直接比较 joint / stop-gradient / decoupled 三种控制性能。
4. 用接触状态、物体位姿、可达性和反事实 action probes 检验表示是否真的包含因果物理，而不是更强时序正则。
5. 根据不确定性自适应选择一次特征抽取或完整 future rollout：常规控制走低延迟路径，失败恢复或长时规划再启用显式想象。

### 可复现性评估

- [x] 代码开源：[Mondo-Robotics/DiT4DiT](https://github.com/Mondo-Robotics/DiT4DiT)
- [x] 预训练模型：LIBERO 与 RoboCasa-GR1 checkpoints 已公开
- [ ] 训练细节完整：缺少 $\lambda$、最终 $\tau_f$ 选择及若干评测随机性说明
- [ ] 数据集全部可获取：模拟数据公开；1,400 条真机示范的完整可下载性未在论文中明确

> [!warning] 版本差异
> 论文 v2 的 RoboCasa-GR1 为 50.8%；当前代码仓库 README 的新版 checkpoint 报告五次评估约 56.3%–57.4%。复现时应固定模型版本与 commit，不能混用论文表格和后续 checkpoint。

### 个人笔记

<!-- 本节留给用户手写。除非用户明确要求，否则不要代写或删除这些提示。 -->

> [!note] 我的记录
> - 与当前研究的联系：
> - 值得复现或验证：
> - 尚未理解的问题：
> - 其他：

---

## 关联笔记

### 基于
- [[Papers/2503-GR00TN1|GR00T N1]]：Action DiT、future tokens 与 4-step flow matching 的直接基础。
- [[Video Generation Model]]：Cosmos-Predict2.5-2B 提供时空生成先验。

### 对比
- [[Papers/2505-FLARE|FLARE]]：用未来 latent alignment 监督动作网络，不进行像素视频生成。
- [[Papers/2603-FastWAM|Fast-WAM]]：同样使用视频联合训练，但测试时只编码当前观测；DiT4DiT 仍以随机 future latent 做一次生成式特征抽取。
- [[Papers/2503-GR00TN1.5|GR00T-N1.5]]：采用 FLARE 隐式未来监督，是模拟与真机主要 baseline。
- [[Papers/2609-OpenWAM|OpenWAM]]：更大规模开放 WAM 体系；后续 benchmark 说明 DiT4DiT 的 SOTA 结论具有时间范围。

### 方法相关
- [[Video-Action Model]]：本文的准确架构类别。
- [[Flow Matching]]：视频与动作的共同生成目标。
- [[Video Co-training]]：联合损失让视频表征服务控制。
- [[World Action Model]]：DiT4DiT 接近生成特征条件 VAM，但不是显式 action-conditioned planner。
- [[Inverse Dynamics Model]]：从未来动态表征回推动作。

### 硬件/数据相关
- [[LIBERO]]：Franka 模拟 benchmark。
- [[RoboCasa-GR1]]：29-DoF humanoid tabletop benchmark。
- [[Unitree G1]]：16-DoF 双臂真机平台。
- [[Whole-Body Control]]：代码仓库后续还扩展到 G1 全身操作，但论文主实验聚焦桌面双臂任务。

---

## 速查卡片

> [!summary] DiT4DiT
> - **核心**：用联合训练的视频 DiT 中间生成特征条件动作 DiT，不依赖完整未来视频重建。
> - **方法**：Cosmos Video DiT + GR00T-style Action DiT + tri-timestep dual flow matching。
> - **结果**：LIBERO 98.6%，RoboCasa-GR1 50.8%；Unitree G1 上优于 Qwen3DiT 与 GR00T-N1.5。
> - **边界**：更像 generative-video-conditioned VAM，而不是会比较候选未来的规划型 WAM。
> - **代码**：[Mondo-Robotics/DiT4DiT](https://github.com/Mondo-Robotics/DiT4DiT)

---

*笔记创建时间：2026-10-16*
