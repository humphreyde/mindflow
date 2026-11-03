---
type: paper
arxiv_id: 2609.07398
source_vault: notes
source_path: PaperNotes/world model/OpenWAM.md
date_migrated: 2026-11-03
title: "OpenWAM: An Open, Modular Exploration Towards Systematic World-Action Model Pretraining"
method_name: "OpenWAM"
authors: [Yuran Wang, Siqiao Huang, Mingleyang Li, Chenhao Zhang, Jiaqi Liang, Weiyang Jin, Yue Chen, Xuemin Chi, Donghao Zhou, Qize Yu, Yu-Kai Wang, Yuhan Rui, Shenzhe Yao, Zhen Yuan, Zhenhao Shen, Kefei Zhu, Zijie Zhu, Ning Gao, Xiaowei Chi, Guanqi He, Shanghang Zhang, Hao Dong, Lin Shao, Hang Zhao]
year: 2026
venue: arXiv
tags: [world-action-model, embodied-ai, video-generation, flow-matching, cross-embodiment, robot-foundation-model]
zotero_collection: "world model"
image_source: local
arxiv_html: ""
code_url: https://github.com/OpenWAM-Official/OpenWAM
code_companion: ""
created: 2026-09-17
---

# 论文笔记：OpenWAM: An Open, Modular Exploration Towards Systematic World-Action Model Pretraining

## 元信息

| 项目 | 内容 |
|------|------|
| Authors | Yuran Wang、Siqiao Huang、Mingleyang Li、Chenhao Zhang、Jiaqi Liang、Weiyang Jin、Yue Chen、Xuemin Chi、Donghao Zhou、Qize Yu、Yu-Kai Wang、Yuhan Rui、Shenzhe Yao、Zhen Yuan、Zhenhao Shen、Kefei Zhu、Zijie Zhu、Ning Gao、Xiaowei Chi、Guanqi He、Shanghang Zhang、Hao Dong、Lin Shao、Hang Zhao |
| 机构 | National University of Singapore；Tsinghua University；Peking University；The University of Hong Kong；Zhejiang University；The Chinese University of Hong Kong；Shanghai Jiao Tong University |
| 日期 | September 2026 |
| 项目主页 | [OpenWAM](https://openwam-official.github.io/) |
| 对比基线 | [[Papers/2603-FastWAM\|Fast-WAM]]、StarVLA、Qwen-RobotManip、$\pi_{0.5}$、LingBot-VA、ABot-M0.5 |
| 链接 | [arXiv](https://arxiv.org/abs/2609.07398) / [PDF](https://arxiv.org/pdf/2609.07398) / [Code](https://github.com/OpenWAM-Official/OpenWAM) / [Models](https://huggingface.co/OpenWAM) |

---

## 一句话总结

> OpenWAM 将 WAM 拆成可控变量，表明其收益主要来自紧凑世界表征、独立动作容量、训练期世界到动作信息流和同步联合去噪。

---

## 核心贡献

1. **OpenWAM-Infra**：把 [[World Action Model|WAM]] 的视觉编码器、世界/动作 backbone、信息流掩码、训练、部署和评测解耦为可组合模块，支持六种架构变体与八个仿真基准。
2. **OpenWAM-Study**：通过控制实验研究“继承什么世界知识、世界与动作如何交互、如何跨域扩展”，得到一套从 world prior 到 embodied pretraining 的经验配方。
3. **OpenWAM-α**：以 5B 视频 DiT、1B ActionDiT、80D 统一动作空间和 6369 小时人类第一视角/机器人数据实现开放预训练模型，并公开代码、预训练权重、下游 checkpoint 与数据配方。

#### Figure 1: OpenWAM 总览

![[Papers/assets/OpenWAM/OpenWAM_fig01_overview.png]]

**说明**：左侧 OpenWAM-Infra 将模型与系统组件模块化；中间 OpenWAM-Study 以控制实验积累设计原则；右侧 OpenWAM-α 将原则扩展至大规模预训练与仿真/真机评测。论文真正的价值在于把“一个 WAM”提升为“研究 WAM 的实验平台”。

---

## 问题背景

### 要解决的问题

[[VLA]] 通常从视觉—语言预训练继承语义知识，而 [[World Action Model|WAM]] 从视频生成模型继承视觉动态先验，再通过具身数据学习动作。现有 WAM 往往同时改变视频生成 backbone、视觉表示、动作容量、信息流、采样顺序和数据配方，因而很难回答三个问题：

1. WAM 应从上游视频模型继承什么知识？
2. 世界预测和动作学习通过什么机制产生协同？
3. 这种协同能否随跨域具身预训练扩展？

### 现有方法的局限

- 单体式代码库让架构和系统实现互相干扰，跨论文结果难以归因。
- “同时预测未来和动作”并不自动意味着两者形成有效信息流。
- [[Imagine-then-Execute|先想象再执行]] 与“训练期世界表征学习”常被混为一谈。
- 不同 embodiment 的动作宽度和语义不一致，妨碍联合预训练。
- 像素级未来预测容易受相机、噪声和背景变化影响，并产生 [[Compounding Error|长时误差累积]]。

### 本文的动机

作者把 WAM 设计写成组合 $C(\mathcal{E},\mathcal{S},\mathcal{M})$：视觉编码器 $\mathcal{E}$ 决定预测空间，stream backbones $\mathcal{S}$ 决定世界/动作/理解容量，注意力掩码 $\mathcal{M}$ 决定信息方向。其目标不是只寻找一个最优配置，而是建立可以复现实验、隔离变量并扩展到新模型的开放底座。

---

## 核心技术

### OpenWAM-Infra：可组合模型

OpenWAM-Infra 提供三类模块：

- **视觉编码器**：Wan2.2-VAE、FLUX.2-VAE、DINOv3、V-JEPA 2.1，以及用于语义特征降维的 S-VAE。
- **Stream backbone**：世界流 $\mathcal W$、动作流 $\mathcal A$、可选理解流 $\mathcal U$；支持 Wan、Cosmos 与 Qwen3-VL 系列。
- **可见性掩码**：控制世界 token 与动作 token 的双向、单向或隔离交互。

六种架构覆盖 Single-System Vanilla/MoE、Dual-System Joint Self-Attention/Joint Cross-Attention/IDM，以及 Tri-System Joint Self-Attention。

#### Figure 2: OpenWAM 模型基础设施

![[Papers/assets/OpenWAM/OpenWAM_fig02_model_infra.png]]

**说明**：上半部分展示编码器、stream backbone 和 visibility mask 三个正交模块；下半部分展示组合规则如何实例化单系统、双系统和三系统。每个 backbone 都遵循 `prepare → per-layer block → finalize` 接口，联合注意力通过拆分 pre/post-attention 实现，而不修改 backbone 内部。

#### 公式 1：[[Blockwise Attention Mask|世界—动作可见性矩阵]]

$$
\mathcal{M}=
\begin{pmatrix}
\mathcal{M}_{V\leftarrow V} & \mathcal{M}_{V\leftarrow A}\\
\mathcal{M}_{A\leftarrow V} & \mathcal{M}_{A\leftarrow A}
\end{pmatrix}.
$$

**含义**：矩阵四个块分别控制视频内部、视频读取动作、动作读取视频和动作内部的信息流。跨模态块组合成 Mutual、Action Sees Video、Video Sees Action 和 Isolated 四种模式。

**符号说明**：
- $V$、$A$：视频和动作 token。
- $\mathcal{M}_{X\leftarrow Y}$：模态 $X$ 是否允许注意模态 $Y$。
- 视频内部采用 first-frame causal mask；动作块内部采用双向注意力。

### OpenWAM-α 模型架构

OpenWAM-α 采用双系统 joint self-attention：

- **输入**：当前多相机观测、语言指令、80D [[Proprioceptive State|本体状态]]。
- **视觉分支**：冻结 Wan2.2-VAE；Wan2.2-TI2V-5B [[DiT]] 作为世界流。
- **动作分支**：独立 1B ActionDiT，输出连续 [[Action Chunking|动作块]]。
- **交互**：全部 30 个 paired layers 都是 bridge layer，使用 24 头、每头 128 维的共享注意力空间；训练规模下采用 Mutual visibility。
- **条件**：冻结 umT5 输出 4096 维语言上下文，本体状态经线性层追加为 context token。
- **时序编码**：视频 token 使用 3D RoPE，动作 token 使用 1D RoPE；两条流分别通过 AdaLN 注入 $t_v,t_a$。

#### Figure 12: OpenWAM-α 架构、数据、调度与动作空间

![[Papers/assets/OpenWAM/OpenWAM_fig12_architecture.png]]

**说明**：视频流和动作流使用独立 FFN/AdaLN，但在每层共享联合注意力；训练从整个 $(t_v,t_a)$ 噪声平面采样，推理沿同步对角线；异构机器人动作被映射到固定 80D 槽位。

### 统一动作空间与跨 embodiment 接口

80D 动作表示由两个镜像 34D 手臂块和 12D 预留槽组成。每个 34D 块包含末端位置 3D、6D rotation、gripper 1D 和 dexterous hand 24D。各数据集声明索引映射 $\pi$，未使用槽位不参与动作损失。

#### 公式 4：[[Unified Action Space|统一动作空间映射]]

$$
\begin{aligned}
\mathbf{u}
&=\operatorname{Scatter}_{\pi}\big(\operatorname{Norm}(\mathbf{a})\big),\\
\mathbf{a}
&=\operatorname{Norm}^{-1}\big(\operatorname{Gather}_{\pi}(\mathbf{u})\big).
\end{aligned}
$$

**含义**：训练前先把原生动作归一化并散射到统一槽位；部署时从统一向量取回本 embodiment 的维度并反归一化到物理单位。

**符号说明**：
- $\mathbf a$：机器人原生动作。
- $\mathbf u\in\mathbb R^{80}$：统一动作向量。
- $\pi$：原生维度与统一槽位的索引映射。

### 训练方法

一个训练样本为 $(\ell,\mathbf{o}_{1:T},\mathbf{a}_{1:H},\mathbf q,\mathbf m)$。视觉编码器把视频窗口编码为 $\mathbf z$；语言与可选本体状态组成上下文 $\mathbf c$。论文约定 $t=0$ 是纯噪声、$t=1$ 是干净数据：

$$
\mathbf z^{t_v}=t_v\mathbf z+(1-t_v)\boldsymbol\epsilon_v,
\qquad
\mathbf a^{t_a}=t_a\mathbf a+(1-t_a)\boldsymbol\epsilon_a.
$$

$t_v,t_a$ 独立采样，使训练覆盖整个联合噪声平面。

#### 公式 2：[[Flow Matching|联合世界—动作 Flow Matching 目标]]

$$
\begin{aligned}
\mathcal L
={}&\lambda_v\,
\mathbb E_{t_v,\epsilon_v}\!\left[
w(t_v)\left\|
\hat{\mathbf v}_z-(\mathbf z-\boldsymbol\epsilon_v)
\right\|_2^2
\right]\\
&+\lambda_a\,
\mathbb E_{t_a,\epsilon_a}\!\left[
w(t_a)\left\|
\mathbf m\odot
\big(\hat{\mathbf v}_a-(\mathbf a-\boldsymbol\epsilon_a)\big)
\right\|_2^2
\right].
\end{aligned}
$$

**含义**：同一次 forward 同时预测视频 latent 与动作的速度场；validity mask 只让当前 embodiment 实际使用的动作维度产生梯度。OpenWAM-α 使用 $\lambda_v=\lambda_a=1$，视频 DiT、ActionDiT 和 proprio encoder 联合更新，VAE 与 umT5 冻结。

**符号说明**：
- $\hat{\mathbf v}_z,\hat{\mathbf v}_a$：模型预测的视频/动作速度。
- $w(t)$：中间噪声水平权重更高的 bell-shaped timestep weight。
- $\mathbf m$：80D 有效槽位掩码。
- $\lambda_v,\lambda_a$：两类目标的损失权重。

#### Table 9: OpenWAM-α 预训练配置

| 配置 | 数值 |
|------|------|
| Compute | 16 nodes，128×NVIDIA H200 |
| Training time | 约 7 天 |
| Optimizer | AdamW |
| Global batch size | 3072（每 GPU 24） |
| Learning rate | $1\times10^{-4}$ |
| LR schedule | Cosine；5% warmup；minimum ratio 0.01 |
| Weight decay | 0.01 |
| Momentum | $\beta_1=0.9,\beta_2=0.95$ |
| Training iterations | 155862（1 epoch） |
| Gradient clipping | Global norm 1.0 |
| Precision | bfloat16 |
| Distributed | DeepSpeed ZeRO Stage 2 |
| Input clip | 33 frames；video stride 4；window stride 1 |
| Resolution | $384\times320$ |
| Multi-view | Enabled |
| Augmentation | `ColorJitter(0.2, 0.2, 0.2, 0.0)` |
| Flow shifts | Video/Action = 5.0/5.0 |
| Loss weights | $\lambda_v=1.0,\lambda_a=1.0$ |
| Control/state | 80D action；80D proprioception |

**说明**：基础模型约消耗 2.15 万 H200 GPU 小时；仅训练一个 epoch，但全局 batch 很大。

#### Table 10: 下游 SFT 配置

| Benchmark | Batch | Epochs / Steps | Augmentation |
|-----------|------:|----------------|--------------|
| LIBERO | 256 | 10 epochs / 10690 steps | — |
| VLABench | 196 | 6000 steps | ColorJitter |
| RoboTwin2.0-Full | 256 | 5 epochs / 118655 steps | — |
| RoboTwin2.0-Clean2Random | 256 | 5 epochs / 10740 steps | ColorJitter |
| RoboDojo | 256 | 60000 steps | ColorJitter |
| RoboCasa365 | 1024 | 60000 steps | ColorJitter |
| EBench | 256 | 100000 steps | ColorJitter |
| RoboCasa-GR1 | 256 | 100000 steps | ColorJitter |
| Franka single-arm | 256 | 10 epochs / 9860 steps | — |
| RoboDojo real | 256 | 30000 steps | ColorJitter |
| Wuji + Tianji dexterous hand | 256 | 5 epochs / 10925 steps | — |

**说明**：所有下游模型从同一个 foundation checkpoint 初始化；LIBERO-Plus 直接评测 LIBERO checkpoint，不额外微调。

### 推理与部署

#### Figure 3: 推理模式与联合去噪调度

![[Papers/assets/OpenWAM/OpenWAM_fig03_inference_denoise.png]]

**说明**：系统把“何时启动推理”和“视频/动作按什么相对速度去噪”分开。同步执行在动作 buffer 为空时阻塞；异步执行在剩余 $d$ 步时预取新 chunk。调度可沿同步对角线，或用 variance shift/linear offset 让某一模态领先。

同步 Euler 更新为 $\mathbf z^{t_v^{i+1}}=\mathbf z^{t_v^i}+(t_v^{i+1}-t_v^i)\hat{\mathbf v}_z$，动作流同理。

#### 公式 3：[[Action Denoise|异步去噪调度族]]

$$
f_{\alpha}(s)=\frac{\alpha s}{1+(\alpha-1)s},
\qquad
h_o(s)=\max\!\left\{\frac{s-o}{1-o},0\right\}.
$$

**含义**：$f_\alpha$ 通过 variance shift 让领先模态更早变干净；$h_o$ 让滞后模态在全局进度超过 $o$ 前保持纯噪声。$(\alpha,o)=(1,0)$ 恢复同步路径。

**符号说明**：
- $s=i/N$：全局采样进度。
- $\alpha>1$：variance shift 强度。
- $o$：linear offset。

OpenWAM-α 推理使用 $N=10$、$\rho=5$ 的同步路径 $t^i=1-f_\rho(1-i/N)$。控制只消费动作，因此部署时跳过 VAE 视频解码。

#### Figure 4: 不同架构的推理延迟

![[Papers/assets/OpenWAM/OpenWAM_fig04_acceleration.png]]

**说明**：在 RTX 5090、Wan2.2-TI2V-5B 条件下，prompt cache、跳过视频解码、`torch.compile`/CUDA Graph 和 DiT velocity cache 可将推理延迟降至约 149–216 ms。OpenWAM-α 的 10 步联合采样约 170 ms/chunk。

#### Figure 5: 统一评测协议

![[Papers/assets/OpenWAM/OpenWAM_fig05_evaluation_protocol.png]]

**说明**：仿真和真机都是 WebSocket thin client。服务端完成相机拼接、crop/resize、状态映射、动作归一化、推理和原生动作反映射，checkpoint 同时保存架构配置与 normalization statistics，减少训练—部署漂移。

### 数据与数据处理

#### Table 4: OpenWAM-α 预训练数据

| Source | Type | #Emb. | FPS | Single | Bimanual | Mobile | Dexterous | Full Frames (M) | Full Hours | Used Frames (M) | Used Hours | Share |
|--------|------|------:|----:|:------:|:--------:|:------:|:---------:|----------------:|-----------:|----------------:|-----------:|------:|
| Egocentric data (ours) | Human video | 1 | 30 | human | human | human | human | 744.9 | 6897 | 155.7 | 1442 | 30.1% |
| AgiBotWorld-Beta | Real robot | 1 | 15 | — | ✓ | ✓ | ✓ | 124.5 | 2306 | 96.9 | 1794 | 18.6% |
| RoboCOIN | Real robot | 15 | 30 | — | ✓ | ✓ | ✓ | 104.5 | 956 | 74.1 | 686 | 14.3% |
| [[DROID]] | Real robot | 1 | 10 | ✓ | — | — | — | 46.3 | 1285 | 36.3 | 1007 | 7.0% |
| InternData-A1 | Simulation | 4 | 30 | ✓ | ✓ | — | — | 313.7 | 2904 | 155.5 | 1440 | 30.0% |
| **Total** | Human + robot | 21 robot + human | — | — | — | — | — | **1333.9** | **14348** | **518.5** | **6369** | **100%** |

**说明**：人类第一视角视频仅监督世界流，动作和本体通道完全 mask；真实/仿真机器人数据同时提供世界与动作监督。混合比例按实际消费帧数而不是按小时分配。

数据清理包含：不可解码/重复/纯色/曝光/模糊/跳帧过滤；人手离开视野和无效语言过滤；state/action 一致性检查；基于 state 的首尾 idle trimming；视觉—状态交叉验证；损失超过 70% 帧或 90% 冻结的 episode 删除。

---

## 实验

### 实验设置

- **控制实验**：RoboTwin2.0-Full 与 Clean2Random，指标为成功率。
- **大规模仿真**：LIBERO、LIBERO-Plus、VLABench、RoboTwin2.0、RoboDojo、RoboCasa365、RoboCasa-GR1、EBench。
- **真机**：Franka Research 3 单臂、RoboDojo 三种双臂 embodiment、Wuji hand + Tianji arm 灵巧手平台。
- **预训练**：128×H200、约 7 天、AdamW、global batch 3072。

### OpenWAM-Study：继承什么世界知识

#### Figure 6: 视频生成 backbone 规模

![[Papers/assets/OpenWAM/OpenWAM_fig06_backbone_scale.png]]

**说明**：Wan2.1-VACE-1.3B、Cosmos-Predict2.5-2B、Wan2.2-TI2V-5B、Wan2.1-I2V-14B 分别达到 90.14、91.64、92.39、93.79。5B 与 14B 只差 1.40 点，因而被选为效率更好的默认值；但模型家族、训练数据和目标不同，不能把趋势解释为严格 scaling law。

#### Figure 7: 视觉表示先验

![[Papers/assets/OpenWAM/OpenWAM_fig07_visual_representations.png]]

**说明**：DINOv3/V-JEPA 2.1 直接接入仅为 76.42/80.91；压缩到 48D 后升至 90.18/88.46，接近 Wan2.2-VAE 的 90.30。结论不是“重建 latent 优于语义 latent”，而是 WAM 需要同时信息丰富、时间紧凑、token/通道维度紧凑的视觉空间。

### OpenWAM-Study：世界—动作协同

#### Table 1: 架构消融（RoboTwin2.0-Full SR %）

| System | Variant | Clean | Randomized | Average |
|--------|---------|------:|-----------:|--------:|
| Single | Vanilla | 85.20 | 85.80 | 85.50 |
| Single | MoE | 86.22 | 83.04 | 84.63 |
| Dual | Joint Self-Attention | 92.34 | **92.38** | 92.36 |
| Dual | Joint Cross-Attention | 87.86 | 88.64 | 88.25 |
| Dual | Detached Cross-Attention | 92.06 | 91.64 | 91.85 |
| Dual | IDM | 87.76 | 88.14 | 87.95 |
| Tri | Joint Self-Attention | **92.84** | 92.36 | **92.60** |

**说明**：独立 ActionDiT 带来最显著提升。Tri-System 略高于 Dual，但为隔离 VLM understanding stream 的影响并控制复杂度，后续采用 Dual Joint Self-Attention。

#### Figure 8: 训练期注意力掩码

![[Papers/assets/OpenWAM/OpenWAM_fig08_attention_masks.png]]

**说明**：四种 mask 仅改变跨模态可见性，保持 backbone、训练预算与推理方式一致。

#### Table 2: 训练期信息流（RoboTwin2.0-Full SR %）

| Mask | Clean | Randomized | Average |
|------|------:|-----------:|--------:|
| Isolated | 88.08 | 86.74 | 87.41 |
| Video Sees Action | 87.92 | 87.34 | 87.63 |
| **Action Sees Video** | **92.98** | **91.80** | **92.39** |
| Mutual | 92.50 | **91.80** | 92.15 |

**说明**：是否允许动作读取世界特征形成约 5 点差距；从头训练时，反向的 action-to-video 通路没有明显增益。

#### Figure 9: 推理期去噪顺序

![[Papers/assets/OpenWAM/OpenWAM_fig09_denoising_schedules.png]]

**说明**：同步联合去噪为 93.0，所有 action-leading/video-leading 的 variance-shift 与 linear-offset 方案都更低（最高约 92.3）。这支持 [[Papers/2603-FastWAM|Fast-WAM]] 的“world representation learning”解释，而不支持推理期隐式 planning-then-IDM。

### OpenWAM-Study：跨域预训练

#### Figure 10: 预训练主要改善 OOD 泛化

![[Papers/assets/OpenWAM/OpenWAM_fig10_pretraining_generalization.png]]

**说明**：RoboTwin Clean2Random 的 ID 从 87.0 小幅升至最高 88.5，而 OOD 从 14.5 升至 Robot-only 23.8、Ego→Robot 26.5、Ego+Robot co-train 26.62。人类视频扩大视觉/交互覆盖，机器人数据提供可执行 action grounding。

#### Figure 11: 预训练改变偏好的信息流

![[Papers/assets/OpenWAM/OpenWAM_fig11_information_flow_scale.png]]

**说明**：从头训练 Mutual 比 Action-Sees-Video 低 0.24 点；预训练后在 RoboTwin-Full、Clean2Random ID/OOD 分别高 0.16、0.70、0.72 点。作者据此选择 Mutual，但差值很小且未报告多随机种子方差。

#### Table 3: OpenWAM-Study 累积配方

| Stage | Finding | OpenWAM-α default |
|-------|---------|-------------------|
| Inherit | 强视频 backbone + 紧凑、信息丰富的 latent | Wan2.2-TI2V-5B；compact latent |
| Interact | 独立动作容量；world-to-action visibility；同步去噪 | Dual joint self-attention；sync denoising |
| Consolidate | 具身预训练提升 OOD；规模化后 Mutual 更优 | Ego+robot 一阶段 [[Co-training]]；Mutual visibility |

### 仿真主要结果

#### Figure 13: 八个仿真基准的代表性比较

![[Papers/assets/OpenWAM/OpenWAM_fig13_benchmark_grid.png]]

**说明**：OpenWAM-α 在 LIBERO、RoboTwin-Full、EBench、RoboCasa-GR1 和 VLABench 等代表性比较中强势，但该图只选择部分 baseline；应结合附录完整表格阅读。

#### Figure 14: 每个基准上 VLA/WAM 最强模型比较

![[Papers/assets/OpenWAM/OpenWAM_fig14_benchmark_radial.png]]

**说明**：完整强基线比较显示 OpenWAM-α 并非全面 SOTA；它在 EBench 最强，在 LIBERO/RoboTwin-Full/RoboCasa-GR1 接近头部，在 RoboTwin OOD、RoboDojo 和 RoboCasa365 仍有明显差距。

#### Table 13: LIBERO（SR %）

| Method | Spatial | Object | Goal | Long | Avg |
|--------|--------:|-------:|-----:|-----:|----:|
| OpenVLA | 84.7 | 88.4 | 79.2 | 53.7 | 76.5 |
| $\pi_0$ | 98.0 | 96.8 | 94.4 | 88.4 | 94.4 |
| StarVLA | 97.8 | 98.6 | 96.2 | 93.8 | 96.6 |
| $\pi_{0.5}$ | 98.8 | 98.2 | 98.0 | 92.4 | 96.9 |
| GR00T-N1.6 | 97.7 | 98.5 | 97.5 | 94.4 | 97.0 |
| OpenVLA-OFT | 97.6 | 98.4 | 97.9 | 94.5 | 97.1 |
| X-VLA | 98.2 | 98.6 | 97.8 | 97.6 | 98.1 |
| ABot-M0 | 98.8 | 99.8 | 99.0 | 96.6 | 98.6 |
| Being-H0.5 | 99.2 | 99.6 | 99.4 | 97.4 | 98.9 |
| Qwen-RobotManip | — | — | — | — | 99.2 |
| [[Papers/2603-FastWAM\|Fast-WAM]] | 98.2 | **100.0** | 97.0 | 95.2 | 97.6 |
| Motus | 96.8 | 99.8 | 96.6 | 97.6 | 97.7 |
| ImageWAM | 97.2 | 99.2 | 98.8 | 98.4 | 98.4 |
| LingBot-VA | 98.5 | 99.6 | 97.2 | **98.5** | 98.5 |
| DiT4DiT | — | — | — | — | 98.6 |
| Being-H0.7 | — | — | — | — | 99.2 |
| ABot-M0.5 | **100.0** | 99.8 | 99.4 | 98.4 | **99.4** |
| **OpenWAM-α** | 99.6 | 99.6 | **99.8** | 98.2 | 99.3 |

**说明**：OpenWAM-α 平均 99.3，距 ABot-M0.5 仅 0.1 点。

#### Table 14: VLABench（每格 SR / PS / IS）

| Method | In-dist. | Category | Commonsense | Instruction | Texture | Avg |
|--------|----------|----------|-------------|-------------|---------|-----|
| $\pi_0$ | 47.0 / 62.7 / 67.8 | 21.2 / 33.6 / 44.0 | 29.1 / 43.0 / 54.9 | 17.3 / 38.7 / 58.0 | 32.2 / 42.5 / 50.6 | 29.4 / 44.1 / 55.0 |
| LoHo-Manip | 54.0 / — / — | 23.0 / — / — | 36.0 / — / — | 42.0 / — / — | 39.0 / — / — | 39.0 / — / — |
| ACoT-VLA | — / 66.1 / 79.8 | — / 38.9 / 54.1 | — / 37.8 / 52.3 | — / 39.6 / 56.8 | — / 54.6 / 74.6 | — / 47.4 / 63.5 |
| $\pi_{0.5}$ | 65.4 / 77.8 / 80.4 | 38.2 / 49.7 / 52.0 | 43.9 / 57.3 / 60.0 | 48.2 / 64.2 / 67.0 | 44.9 / 62.3 / 65.0 | 48.1 / 62.3 / 64.9 |
| ERVLA | 69.7 / 81.1 / 84.2 | 47.0 / 61.0 / 66.4 | 44.0 / 55.0 / 57.2 | 58.0 / 70.2 / 73.8 | 47.4 / 62.3 / 70.6 | 53.2 / 65.9 / 70.4 |
| Xiaomi-Robotics-1 | 75.6 / 85.0 / 79.8 | 53.0 / 66.6 / 66.4 | 48.4 / 58.3 / 58.2 | 55.8 / 66.8 / 70.2 | **62.6 / 74.9 / 74.8** | **59.1 / 70.3 / 69.9** |
| Bridge-WA | 78.0 / 85.8 / **85.0** | 23.0 / 28.8 / 39.0 | 51.1 / 64.4 / **74.2** | **67.0 / 80.3 / 82.0** | 45.0 / 60.3 / **76.0** | 52.8 / 64.0 / **71.2** |
| **OpenWAM-α** | **83.4 / 87.9** / 75.2 | 38.1 / 45.9 / 45.9 | **58.0 / 64.8** / 57.9 | 53.8 / 64.5 / 66.5 | 61.4 / 72.9 / 71.6 | 58.9 / 67.2 / 63.5 |

**说明**：OpenWAM-α 的平均 SR 58.9，接近 Xiaomi-Robotics-1 的 59.1；其 in-distribution SR 83.4 最强，但综合 IS 不占优。

#### Table 15: RoboTwin2.0-Clean2Random（SR %）

| Method | Clean | Randomized | Avg |
|--------|------:|-----------:|----:|
| StarVLA | 46.5 | 3.2 | 24.9 |
| GR00T-N1.7 | 43.6 | 20.7 | 32.2 |
| X-VLA | 68.0 | 20.9 | 44.5 |
| Spatial Forcing | 77.2 | 26.7 | 52.0 |
| ABot-M0 | 70.7 | 36.0 | 53.4 |
| $\pi_{0.5}$ | 70.7 | 46.0 | 58.4 |
| GigaBrain-0.7 | 66.8 | 67.9 | 67.4 |
| Qwen-RobotManip | 84.7 | **69.4** | **77.1** |
| AHA-WAM | 64.3 | 3.2 | 33.8 |
| [[Papers/2603-FastWAM\|Fast-WAM]] | 77.8 | 1.9 | 39.9 |
| X-WAM | 70.0 | 25.8 | 47.9 |
| 4D-WAM | 81.5 | 41.8 | 61.7 |
| **OpenWAM-α** | **89.4** | 48.7 | 69.0 |

**说明**：OpenWAM-α 的 clean fitting 最强，但 randomized 比 Qwen-RobotManip 低 20.7 点；这正是论文所说的 WAM ID/OOD 张力。

#### Table 16: RoboTwin2.0-Full（SR %）

| Method | Clean | Randomized | Avg |
|--------|------:|-----------:|----:|
| X-VLA | 72.80 | 72.84 | 72.82 |
| $\pi_{0.5}$ | 82.70 | 76.80 | 79.75 |
| ABot-M0 | 86.06 | 85.08 | 85.57 |
| Qwen-VLA | 86.10 | 87.20 | 86.65 |
| StarVLA | 88.18 | 88.32 | 88.25 |
| Galaxea G0.5 | 93.70 | 92.80 | 93.25 |
| Qwen-RobotManip | 93.70 | 94.00 | 93.85 |
| Motus | 88.66 | 87.02 | 87.84 |
| [[Papers/2603-FastWAM\|Fast-WAM]] | 91.90 | 91.80 | 91.85 |
| LingBot-VA | 92.93 | 91.55 | 92.24 |
| ImageWAM | 93.20 | 93.56 | 93.38 |
| LingBot-VA 2.0 | 93.80 | 93.40 | 93.60 |
| ABot-M0.5 | **94.00** | **94.20** | **94.10** |
| **OpenWAM-α** | 93.74 | 93.46 | 93.60 |

**说明**：在包含 randomized 训练数据的 ID 设置中，OpenWAM-α 与头部方法差距很小。

#### Table 17: RoboDojo（每格 SR / Score）

| Method | Gen-Std | Gen-Rand | Precision | Long-Horizon | Memory | Open | Avg |
|--------|---------|----------|-----------|--------------|--------|------|-----|
| StarVLA-α | 5.00 / 7.54 | 0.00 / 0.33 | 4.33 / 9.90 | 6.50 / 14.15 | 2.44 / 3.34 | 0.58 / 0.68 | 3.24 / 6.40 |
| X-VLA | 12.00 / 17.90 | 1.00 / 3.04 | 12.00 / 18.32 | 9.75 / 16.53 | 3.56 / 4.76 | 0.50 / 0.55 | 6.52 / 10.13 |
| $\pi_{0.5}$ | 15.00 / 20.93 | 1.00 / 5.82 | 5.50 / 12.40 | 14.67 / 23.54 | 4.56 / 5.78 | 1.67 / 1.98 | 6.91 / 11.41 |
| Spatial Forcing | 15.00 / 21.25 | 4.00 / 6.98 | 10.58 / 17.33 | 14.58 / 23.26 | 4.11 / 5.43 | 1.58 / 1.78 | 8.04 / 12.38 |
| Hy-Embodied-0.5-VLA | 17.00 / 21.98 | 0.00 / 1.57 | 8.00 / 13.81 | 14.92 / 25.74 | 12.11 / 13.37 | 0.58 / 0.65 | 8.80 / 13.07 |
| Xiaomi-Robotics-1 | **28.00 / 35.65** | **6.00 / 11.44** | 18.83 / 26.69 | 23.67 / 38.39 | 6.56 / 7.81 | **3.58 / 3.94** | 13.93 / 20.07 |
| Galaxea G0.5 | 20.00 / 26.74 | **6.00** / 11.16 | **20.42 / 28.25** | **32.25 / 44.12** | 7.33 / 8.61 | 1.58 / 1.73 | 14.88 / 20.23 |
| DM0.5 | 18.00 / 23.49 | 4.00 / 8.06 | 16.75 / 24.82 | 19.50 / 33.70 | **47.44 / 47.74** | 2.08 / 2.43 | **19.34 / 24.90** |
| [[Papers/2603-FastWAM\|Fast-WAM]] | 2.00 / 4.33 | 0.00 / 0.34 | 0.00 / 1.96 | 5.17 / 9.14 | 3.44 / 3.55 | 0.42 / 0.42 | 2.03 / 3.48 |
| AHA-WAM | 6.00 / 10.32 | 0.00 / 1.26 | 2.42 / 5.86 | 2.67 / 8.61 | 2.78 / 2.97 | 0.83 / 0.88 | 2.39 / 4.82 |
| GigaWorld-Policy | 6.00 / 10.28 | 0.00 / 0.41 | 1.83 / 6.15 | 8.92 / 15.51 | 2.22 / 3.46 | 0.50 / 0.54 | 3.27 / 6.20 |
| X-WAM | 5.00 / 11.24 | 1.00 / 3.54 | 1.83 / 6.72 | 9.08 / 17.47 | 4.67 / 6.32 | 0.25 / 0.57 | 3.83 / 7.69 |
| **OpenWAM-α** | 25.56 / 33.16 | 4.11 / 8.26 | 9.25 / 18.45 | 25.33 / 34.93 | 9.11 / 10.41 | 1.08 / 1.41 | 11.92 / 17.18 |

**说明**：OpenWAM-α 是表中最强 WAM，但总体仍低于最强 VLA DM0.5，尤其 Memory/Open 类任务仍弱。

#### Table 18: EBench（每格 SR / Score）

| Method | Table Top | Simple PnP | Long Horizon | Overall |
|--------|-----------|------------|--------------|---------|
| StarVLA-OFT | — | — | — | 0.0 / 0.2 |
| $\pi_0$ | 15.7 / 30.0 | 35.0 / 39.0 | 17.0 / 41.0 | 23.6 / 37.0 |
| X-VLA | 8.6 / 24.0 | 50.0 / 54.0 | 6.2 / 25.0 | 23.7 / 36.0 |
| InternVLA-A1 | 4.3 / 11.0 | 43.0 / 47.0 | 17.9 / 46.0 | 23.9 / 36.0 |
| $\pi_{0.5}$ | 12.9 / 32.0 | 45.0 / 50.0 | 18.1 / 39.0 | 27.1 / 41.0 |
| GigaBrain-0.7 | — | — | — | 33.3 / 46.0 |
| Qwen-RobotManip | **50.0 / 70.0** | 56.5 / 60.0 | 29.9 / 55.0 | 45.6 / 60.0 |
| [[Papers/2603-FastWAM\|Fast-WAM]] | — | — | — | 4.7 / 7.6 |
| **OpenWAM-α** | 30.0 / 44.2 | **67.5 / 72.0** | **44.3 / 72.6** | **49.4 / 64.7** |

**说明**：OpenWAM-α 在 Simple PnP、Long Horizon 和总体两项指标上达到最佳，是论文最强的 SOTA 证据。

#### Table 19: RoboCasa365（SR %）

| Method | Atomic | Comp.-Seen | Comp.-Unseen | Avg |
|--------|-------:|-----------:|-------------:|----:|
| Diffusion Policy | 15.7 | 0.2 | 1.3 | 6.1 |
| $\pi_0$ | 36.3 | 5.2 | 0.7 | 15.0 |
| $\pi_{0.5}$ | 39.6 | 7.1 | 1.2 | 16.9 |
| GR00T-N1.5 | 50.7 | 14.8 | 2.7 | 23.9 |
| Qwen-RobotManip | 68.6 | 20.1 | 14.9 | 35.9 |
| RLDX-1 | 67.6 | 27.9 | 8.5 | 36.0 |
| Xiaomi-Robotics-1 | **80.2** | **57.1** | **32.1** | **57.4** |
| GigaWorld-Policy | 44.4 | 11.8 | 2.9 | 20.7 |
| ABot-M0.5 | 75.9 | 38.3 | 2.7 | 40.4 |
| **OpenWAM-α** | 69.7 | 32.1 | 8.9 | 38.2 |

**说明**：OpenWAM-α 是较强 WAM，但比整体最佳低 19.2 点，因此主文“接近最佳”的措辞偏乐观。

#### Table 20: RoboCasa-GR1（SR %）

| Method | SR |
|--------|---:|
| $\pi_0$ | 13.6 |
| $\pi_{0.5}$ | 37.0 |
| GR00T-N1.5 | 48.0 |
| StarVLA | 48.8 |
| GR00T-N1.6 | 49.9 |
| VP-VLA | 53.8 |
| Being-H0.5 | 53.9 |
| Qwen-VLA-Instruct | 56.7 |
| RLDX-1 | 58.7 |
| PhysBrain 1.0 | **64.5** |
| UWM | 20.0 |
| Being-H0.7 | 49.2 |
| DiT4DiT | 50.8 |
| LDA-1B | 55.4 |
| **OpenWAM-α** | 60.5 |

**说明**：OpenWAM-α 排名第二，距 PhysBrain 1.0 为 4 点。

### OOD 与像素级未来预测的失败模式

#### Figure 15: 单臂预训练数据规模对比

![[Papers/assets/OpenWAM/OpenWAM_fig15_singlearm_data.png]]

**说明**：OpenWAM-α 单臂数据约 1100+ 小时，仅来自 DROID 与 InternData-A1；ABot-M0.5 和 Being-H0.7 分别使用约 8000+、5700+ 小时且覆盖更多单臂 embodiment、场景和相机视角。

#### Table 5: LIBERO-Plus 扰动鲁棒性（SR %）

| Method | Camera | Robot | Language | Light | Background | Noise | Layout | Avg |
|--------|-------:|------:|---------:|------:|-----------:|------:|-------:|----:|
| $\pi_0$ | 13.8 | 6.0 | 58.8 | 85.0 | 81.4 | 79.0 | 68.9 | 53.6 |
| OpenVLA-OFT | 56.4 | 31.9 | 79.5 | 88.7 | 93.3 | 75.8 | 74.2 | 69.6 |
| StarVLA | 52.5 | 49.8 | 88.5 | 95.7 | 95.7 | 73.0 | 76.9 | 74.1 |
| ABot-M0 | 60.4 | 67.9 | 86.4 | 96.2 | 91.6 | 86.4 | 82.6 | 80.5 |
| $\pi_{0.5}$ | 78.4 | 73.6 | 80.8 | 96.2 | 94.1 | 89.0 | 84.5 | 84.4 |
| ACoT-VLA | 72.6 | 82.6 | 87.5 | 97.7 | 96.5 | 87.8 | 88.1 | 86.6 |
| Qwen-RobotManip | **87.2** | 75.5 | 85.6 | 96.6 | **97.7** | **97.7** | 87.3 | **89.0** |
| [[Papers/2603-FastWAM\|Fast-WAM]] | 16.4 | 44.5 | 68.9 | 78.2 | 53.7 | 37.7 | 60.7 | 51.5 |
| Being-H0.7 | 82.0 | 59.0 | 82.8 | 97.8 | 90.0 | 93.5 | **88.5** | 82.1 |
| Cosmos-Policy | 75.8 | 63.3 | 81.7 | 96.5 | 88.9 | 92.7 | 82.2 | 82.2 |
| ImageWAM | 80.8 | 50.3 | **91.4** | **98.1** | 85.5 | 93.8 | 80.5 | 83.1 |
| ABot-M0.5 | 70.5 | **87.4** | 88.6 | 94.0 | 89.7 | 75.5 | 85.2 | 83.4 |
| **OpenWAM-α** | 33.8 | 76.1 | 88.0 | 97.0 | 87.1 | 39.8 | 77.5 | 69.2 |

**说明**：OpenWAM-α 的 Camera 33.8、Noise 39.8 是主要短板。长时像素 latent rollout 对视角与噪声敏感；ImageWAM 的单帧编辑目标和 Being-H0.7 的 V-JEPA 语义 latent 更稳健。

#### Figure 16: VLA 与 WAM 的 ID/OOD 对比

![[Papers/assets/OpenWAM/OpenWAM_fig16_id_ood.png]]

**说明**：无 embodied pretraining 的 Fast-WAM 在 ID 上优于 StarVLA，但 OOD 次序反转；预训练 OpenWAM-α 同样表现为 ID fitting 强、OOD 相对弱。作者归因于视频 latent 提供额外监督但也带来长时误差累积。该结论有启发性，但跨论文模型的数据和训练并未完全对齐，不能视为范式定论。

### 真机结果

#### Figure 17: 三类真机 embodiment

![[Papers/assets/OpenWAM/OpenWAM_fig17_real_robot_setups.png]]

**说明**：覆盖 Franka 单臂 6 项任务、ARX X5/Piper/Piper X 双臂 18 项 RoboDojo 任务，以及未在预训练中出现的 Wuji hand + Tianji arm 四项灵巧操作。

#### Table 11: Franka 单臂任务指令

| Task | Instruction |
|------|-------------|
| Stack Ring | Pick the yellow ring on the left side, stack it on the other ring. |
| Stack Jenga | Pick the jenga on the left side, stack it on the other jenga. |
| Hang on Cup | Pick the cup on the table, hang it on the shelf. |
| Hang on M | Pick the M-shaped object on the table, hang it on the shelf. |
| Put Chili in Drawer | Pick the chili on the table, put it into the drawer, then push the upper drawer closed. |
| Put Jenga in Drawer | Pick up the jenga block on the table, put it into the drawer, then push the upper drawer closed. |

#### Figure 18: Franka 单臂实验环境

![[Papers/assets/OpenWAM/OpenWAM_fig18_singlearm_setup.png]]

**说明**：Franka Research 3 配合 Intel RealSense 相机和 Robotiq 平行夹爪，在固定桌面场景中执行堆叠、悬挂和抽屉任务。

#### Figure 19: Franka 六项任务执行序列

![[Papers/assets/OpenWAM/OpenWAM_fig19_singlearm_sequences.png]]

**说明**：每行是一次 rollout 均匀采样的六帧，展示抓取、移动、放置与关抽屉等关键阶段。

#### Table 6: Franka 单臂真机结果

| Method | Stack Jenga | Stack Ring | Chili→Drawer | Jenga→Drawer | Hang on M | Hang on Cup | Avg |
|--------|------------:|-----------:|-------------:|-------------:|----------:|------------:|----:|
| $\pi_{0.5}$ | 13/20 (65%) | 7/20 (35%) | 14/20 (70%) | 15/20 (75%) | 7/20 (35%) | 10/20 (50%) | 66/120 (55.0%) |
| LingBot-VA | 16/20 (80%) | **15/20 (75%)** | 17/20 (85%) | 17/20 (85%) | **13/20 (65%)** | 15/20 (75%) | 93/120 (77.5%) |
| **OpenWAM-α** | **17/20 (85%)** | 12/20 (60%) | **20/20 (100%)** | **20/20 (100%)** | **13/20 (65%)** | **17/20 (85%)** | **99/120 (82.5%)** |

**说明**：每项 20 次独立 trial；OpenWAM-α 平均成功率最高，但总体样本量仍不足以支撑细粒度显著性结论。

#### Table 7: RoboDojo 双臂真机（每格 Score / SR %）

**ARX X5**（T1 cover_blocks；T2 make_bread；T3 make_food；T4 pack_and_pour_fruit；T5 store_in_safe；T6 insert_tubes）

| Method | T1 | T2 | T3 | T4 | T5 | T6 | Avg |
|--------|----|----|----|----|----|----|-----|
| X-VLA | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 2.0/0.0 | 20.7/10.0 | 18.0/0.0 | 6.8/1.7 |
| Xiaomi-Robotics-0 | 24.0/20.0 | 0.0/0.0 | 3.0/0.0 | 4.0/0.0 | 40.0/20.0 | 19.0/10.0 | 15.0/8.3 |
| GalaxeaVLA G0 | 1.0/0.0 | 0.0/0.0 | 3.0/0.0 | 6.0/0.0 | 0.0/0.0 | 10.3/0.0 | 3.4/0.0 |
| InternVLA-A1 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 48.0/20.0 | 12.0/0.0 | 10.0/3.3 |
| $\pi_{0.5}$ | 24.6/20.0 | 1.8/0.0 | 25.8/10.0 | 47.0/20.0 | 40.0/20.0 | 26.8/10.0 | 27.7/13.3 |
| **OpenWAM-α** | **31.0/0.0** | 0.0/0.0 | 13.0/0.0 | **52.0/20.0** | **100.0/100.0** | **38.0/20.0** | **39.0/23.3** |

**Piper**（T1 stack_and_cover_blocks；T2 fill_pen_holder；T3 put_objects_into_basket；T4 insert_charger；T5 stack_bowls；T6 stand_up_bottles）

| Method | T1 | T2 | T3 | T4 | T5 | T6 | Avg |
|--------|----|----|----|----|----|----|-----|
| X-VLA | 0.0/0.0 | 5.3/0.0 | 0.0/0.0 | 0.0/0.0 | 53.0/50.0 | 37.0/0.0 | 15.9/8.3 |
| Xiaomi-Robotics-0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 23.0/20.0 | 22.7/0.0 | 7.6/3.3 |
| GalaxeaVLA G0 | 0.0/0.0 | 32.7/10.0 | 13.3/10.0 | 0.0/0.0 | 56.0/50.0 | 30.0/10.0 | 22.0/13.3 |
| InternVLA-A1 | 0.0/0.0 | 7.3/0.0 | 0.0/0.0 | 0.0/0.0 | 73.0/70.0 | 59.0/40.0 | 23.2/18.3 |
| $\pi_{0.5}$ | 10.0/10.0 | 28.0/0.0 | 10.0/10.0 | 0.0/0.0 | 72.0/60.0 | 72.0/50.0 | 32.0/21.7 |
| **OpenWAM-α** | 8.3/0.0 | **60.0/40.0** | **36.7/30.0** | 0.0/0.0 | **100.0/100.0** | **75.0/50.0** | **46.7/36.7** |

**Piper X**（T1 classify_objects；T2 disassemble_LEGO；T3 hang_mugs；T4 pack_objects_into_backpack；T5 sweep_blocks；T6 cap_pen）

| Method | T1 | T2 | T3 | T4 | T5 | T6 | Avg |
|--------|----|----|----|----|----|----|-----|
| X-VLA | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 0.7/0.0 | 0.1/0.0 |
| Xiaomi-Robotics-0 | 0.0/0.0 | 0.7/0.0 | 4.0/0.0 | 0.0/0.0 | 0.0/0.0 | 2.7/0.0 | 1.2/0.0 |
| GalaxeaVLA G0 | 0.0/0.0 | 0.0/0.0 | 0.0/0.0 | 4.0/0.0 | 0.0/0.0 | 6.0/0.0 | 1.7/0.0 |
| InternVLA-A1 | 0.0/0.0 | 0.0/0.0 | 4.0/0.0 | 2.0/0.0 | 0.0/0.0 | 10.0/0.0 | 2.7/0.0 |
| $\pi_{0.5}$ | 0.0/0.0 | 14.8/10.0 | 0.0/0.0 | 29.5/10.0 | 7.5/0.0 | 3.0/0.0 | 9.1/3.3 |
| **OpenWAM-α** | 0.0/0.0 | **28.0/10.0** | **18.0/0.0** | **52.3/20.0** | **40.0/40.0** | **24.7/10.0** | **27.2/13.3** |

**总体平均**：X-VLA 7.6/3.3；Xiaomi-Robotics-0 7.9/3.9；GalaxeaVLA 9.0/4.4；InternVLA-A1 12.0/7.2；$\pi_{0.5}$ 22.9/12.8；**OpenWAM-α 37.6/24.4**。

#### Table 12: 灵巧手任务指令

| Task | Instruction |
|------|-------------|
| Stack Toy Tower | Stack the discs onto the tower pole in order from largest to smallest. |
| Collect Shuttlecocks | Put all the shuttlecocks into the shuttlecock tube. |
| Twist off Bottle Cap | Twist off the bottle cap. |
| Put Away Clothes | Pick up the clothes from the pile on the table and put them into the basket. |

#### Figure 20: Wuji hand + Tianji arm 实验环境

![[Papers/assets/OpenWAM/OpenWAM_fig20_dexterous_setup.png]]

**说明**：图中给出灵巧手平台、相机、工作区与四类操作物体；该 embodiment 及其 9D EEF + 21D hand action space未出现在预训练数据中。

#### Figure 21: 灵巧手任务序列与 OOD 条件

![[Papers/assets/OpenWAM/OpenWAM_fig21_dexterous_sequences.png]]

**说明**：OOD 分别改变物体身份、布局、光照或背景，同时保持指令和任务目标不变。

#### 附录公式：最终成功率

$$
S_{\mathrm{final}}
=
\frac{N_{\mathrm{success}}}{N_{\mathrm{trial}}}
\times 100\%.
$$

**含义**：仅在整个任务目标完成时计为成功。

**符号说明**：$N_{\mathrm{success}}$ 是成功 trial 数；$N_{\mathrm{trial}}$ 是有效 trial 总数。

#### 附录公式：过程得分

$$
S_{\mathrm{process}}
=
\frac{\sum_i n_i}{\sum_i m_i}
\times 100\%.
$$

**含义**：即使未完成最终目标，也按已完成操作元素的比例给分。

**符号说明**：$n_i$ 是 trial $i$ 已完成元素数；$m_i$ 是该 trial 的元素总数。

#### Table 8: 灵巧手真机结果（Score / SR）

| Method | Tower ID | Tower OOD | Shuttlecocks ID | Shuttlecocks OOD | Clothes ID | Clothes OOD | Bottle ID | Bottle OOD |
|--------|----------|-----------|------------------|-------------------|------------|-------------|-----------|------------|
| $\pi_{0.5}$ | 16/30 (53.3) / 1/10 (10%) | 12/30 (40.0) / 1/10 (10%) | 11/35 (31.4) / 2/10 (20%) | 17/54 (31.5) / 3/15 (20%) | 26/30 (86.7) / 6/10 (60%) | 45/60 (75.0) / 9/20 (45%) | 8/10 (80.0) / 3/10 (30%) | 13/20 (65.0) / 6/20 (30%) |
| **OpenWAM-α** | **21/30 (70.0) / 4/10 (40%)** | **17/30 (56.7) / 3/10 (30%)** | **29/35 (82.9) / 6/10 (60%)** | **30/57 (52.6) / 4/15 (26.7%)** | **30/30 (100.0) / 10/10 (100%)** | **55/60 (91.7) / 17/20 (85%)** | **10/10 (100.0) / 7/10 (70%)** | **18/20 (90.0) / 16/20 (80%)** |

**说明**：OpenWAM-α 在所有 ID/OOD 任务上均优于 $\pi_{0.5}$，说明统一动作空间可以适配预训练中未见过的 embodiment；但每个条件只有 10–20 次 trial。

---

## 批判性思考

### 优点

1. **研究设计比单一模型更有价值**：模型、表示、容量、信息流、调度和数据配比被拆成相对清晰的控制变量。
2. **机制证据具有连贯性**：紧凑 latent、独立动作容量、world-to-action flow、同步去噪和 OOD 预训练形成一条可解释的设计链。
3. **开放度高**：Apache-2.0 代码、foundation checkpoint、多组下游 checkpoint、部署协议与数据配方均已公开。
4. **跨 embodiment 覆盖广**：从单臂、双臂、移动操作到灵巧手，并包含未见 embodiment 的真机适配。

### 局限性

1. **缺少统计不确定性**：Mutual 的预训练收益仅 0.16–0.72 点，却没有多随机种子、标准差或置信区间。
2. **backbone 比较存在混杂**：参数量、模型家族、上游数据和目标同时变化，不能作为严格 scaling law。
3. **跨论文比较并非完全公平**：VLA/WAM baseline 的预训练数据、SFT 和实现细节不同，“WAM ID 强、VLA OOD 强”应视为观察而非定论。
4. **像素 latent 的鲁棒性瓶颈明显**：LIBERO-Plus Camera/Noise 仅 33.8/39.8，且最终模型仍采用作者已识别出短板的 Wan2.2-VAE。
5. **统一动作空间仍依赖人工语义槽位**：可覆盖当前手臂/夹爪/灵巧手，但并不自动解决任意形态与新控制接口。
6. **成本较高**：foundation pretraining 约需 128×H200×7 天，难以完整独立复现。

### 潜在改进方向

1. 开发具备原生时间压缩的 DINO/V-JEPA 类语义视频编码器，兼顾信息密度与视角/噪声鲁棒性。
2. 将 VLA 的语义表示与 WAM 的未来监督结合，让未来 latent 成为辅助目标而非必须精确重建的长时像素 rollout。
3. 系统研究预测 horizon、latent 语义层级和 OOD 误差累积之间的关系。
4. 对 Mutual/one-way flow 做多 seed、置信区间与数据规模曲线，确认双向协同是否真实存在。
5. 用 UMI/DexUMI 或更多 scene-rich、action-labeled 数据弥合人类视频覆盖与机器人 action grounding。
6. 从固定 80D 槽位进一步发展基于 embodiment token、kinematic graph 或 morphology-conditioned decoder 的通用控制接口。

### 可复现性评估

- [x] 代码开源（Apache-2.0）
- [x] 预训练模型与下游 checkpoint
- [x] 训练和 SFT 细节完整
- [x] 多数机器人/仿真数据可获取
- [ ] 自建 71.6K egocentric manipulation 视频的完整公开可获取性仍需核查
- [ ] 控制实验缺少多随机种子与误差条

### 个人笔记

<!-- 本节留给用户手写。 -->

> [!note] 我的记录
> - 与当前研究的联系：
> - 值得复现或验证：
> - 尚未理解的问题：
> - 其他：

---

## 关联笔记

### 基于

- [[Papers/2603-FastWAM|Fast-WAM]]：其“训练期世界表征比测试期显式想象更重要”的结论，在 OpenWAM 的同步去噪实验中得到进一步支持。
- [[World Model]]：从视频生成预训练继承视觉动态先验。
- [[Video Co-training]]：未来视觉目标作为动作学习的辅助监督。

### 对比

- [[VLA]]：VLA 主要继承语义/语言知识；论文观察到 WAM 的 ID fitting 更强、VLA 的 OOD 鲁棒性更好。
- [[Imagine-then-Execute]]：异步/video-leading 调度没有超过同步去噪，不支持必须先生成未来再行动。

### 方法相关

- [[World Action Model]]：论文研究对象。
- [[Flow Matching]]：视频与动作联合生成目标。
- [[Blockwise Attention Mask]]：控制跨模态信息方向。
- [[Mixture of Experts]]：Single-System 的动作专用 FFN 变体。
- [[Cross-embodiment Transfer]]：80D 统一动作空间支持异构机器人预训练与适配。
- [[Open-World Generalization]]：具身预训练主要改善分布外性能。

### 硬件/数据相关

- [[DROID]]：单臂真实机器人预训练数据。
- [[Franka]]：单臂真机评测平台。
- [[LIBERO]]：单臂仿真与扰动鲁棒性评测。

---

## 速查卡片

> [!summary] OpenWAM
> - **核心**：把 WAM 拆成可控研究变量，并给出从 world prior、信息流到跨域预训练的经验配方。
> - **方法**：5B video DiT + 1B ActionDiT，Mutual Joint Attention，联合 Flow Matching，80D 统一动作空间，同步 10 步去噪。
> - **结果**：LIBERO 99.3、RoboTwin-Full 93.6、EBench 49.4 SR/64.7 Score；主要短板是相机/噪声 OOD。
> - **代码**：[OpenWAM-Official/OpenWAM](https://github.com/OpenWAM-Official/OpenWAM)

---

*笔记创建时间：2026-09-17*
