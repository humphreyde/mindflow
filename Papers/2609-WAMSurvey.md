---
type: paper
arxiv_id: 2609.16074
source_vault: notes
source_path: PaperNotes/world model/WAM-Survey.md
date_migrated: 2026-11-03
title: "World-Action Models for Robot Learning and Control: A Survey"
method_name: "WAM-Survey"
authors: [Zuxing Lu, Hongjia Zhai, Guanzhi Wang, Huajian Zeng, Jiaqi Yang, Jingyu Liu, Lei Cheng, Yuantai Zhang, Yuheng Qiu, Zezhou Cheng, Ivan Laptev, Danfei Xu, Benjamin Riviere, Giuseppe Loianno, Eric Xing, Xingxing Zuo]
year: 2026
venue: arXiv
tags: [world-action-model, world-model, vla, embodied-ai, predictive-control, model-based-rl, survey]
zotero_collection: "world model"
image_source: online
arxiv_html: https://arxiv.org/html/2609.16074
code_url: https://github.com/RCL-Robotics/Awesome-World-Action-Models
code_companion: null
created: 2026-09-23
---

# 论文笔记：World-Action Models for Robot Learning and Control: A Survey

## 元信息

| 项目 | 内容 |
|---|---|
| Authors | Zuxing Lu、Hongjia Zhai、Guanzhi Wang、Huajian Zeng、Jiaqi Yang、Jingyu Liu、Lei Cheng、Yuantai Zhang、Yuheng Qiu、Zezhou Cheng、Ivan Laptev、Danfei Xu、Benjamin Riviere、Giuseppe Loianno、Eric Xing、Xingxing Zuo |
| 特殊作者角色 | Zuxing Lu、Hongjia Zhai 为共同一作；Xingxing Zuo 为通讯作者 |
| 机构 | MBZUAI、Caltech、Amazon FAR、University of Virginia、Georgia Tech、New York University、UC Berkeley |
| 日期 | September 2026 |
| 项目主页 | [Awesome World-Action Models](https://rcl-robotics.github.io/Awesome-World-Action-Models) |
| 对比基线 | [[Papers/2603-FastWAM\|Fast-WAM]]、[[Papers/2410-Pi07\|Pi07]]、[[Papers/2609-OpenWAM\|OpenWAM]] |
| 链接 | [arXiv](https://arxiv.org/abs/2609.16074) / [HTML](https://arxiv.org/html/2609.16074) / [PDF](https://arxiv.org/pdf/2609.16074) / [Resource Repository](https://github.com/RCL-Robotics/Awesome-World-Action-Models) |

> [!info] 论文性质与完整性
> 这是一篇 19 页的机器人方向综述，不提出新模型，也没有新的训练实验。原文包含 **7 张编号 Figure、18 组编号公式和 3 张 Table**，均在下文随对应内容收录。作者共 16 位，少于 20 位，因此按统一规则全部保留。

---

## 一句话总结

> WAM 将未来世界预测与可执行动作生成结构性耦合，为反应式 VLA 增加行动后果推演，并把视频模型、潜在动力学、逆动力学和闭环策略学习纳入统一框架。

---

## 核心贡献

1. **定义研究边界**：把 [[World Action Model|World-Action Model（WAM）]] 定义为连接未来状态建模与可执行动作生成的预测控制模型，区分于单纯 [[World Model]]、视频生成模型和反应式 [[VLA]]。
2. **统一技术分类**：从表示、转移建模、动作接口、端到端/双系统架构、训练流水线、数据模态与规模七个维度整理领域。
3. **跨领域综述**：统一覆盖机器人操作、导航和自动驾驶，并把视频—动作模型、几何世界模型、世界模型规划与 imagined-rollout RL 放入同一坐标系。
4. **指出评测缺口**：强调视觉逼真度不等于动作可执行性，WAM 必须同时报告预测质量、闭环控制效用、安全性与推理成本。

---

## 问题背景

### 要解决的问题

开放环境中的机器人工作在 [[POMDP|部分可观测马尔可夫决策过程]] 下，需要从视觉、本体状态和语言指令中推断意图、预测行动后果，并在物理约束下闭环控制。传统 VLA 通常直接由短历史生成动作，缺少对备选动作后果的显式建模；传统 world model 虽能预测未来，却可能与动作策略分离，出现“预测得像但控制无用”的错配。

#### 公式 1：[[World Model|世界模型单步转移]]

$$
\hat{\mathbf z}_{t+1}=f_{\mathrm{WM}}(\mathbf z_t,\mathbf a_t).
\tag{1}
$$

**含义**：世界模型根据当前潜在状态与动作预测下一潜在状态。

**符号说明**：
- $\mathbf z_t$、$\hat{\mathbf z}_{t+1}$：当前与预测潜在状态；
- $\mathbf a_t$：当前动作；
- $f_{\mathrm{WM}}$：学习到的环境转移模型。

#### 公式 2：[[VLA|反应式 VLA 动作生成]]

$$
\hat{\mathbf a}_{t:t+H}=f_{\mathrm{VLA}}(\mathbf o_{<t},\ell).
\tag{2}
$$

**含义**：VLA 由历史观测与语言直接输出未来 $H$ 步动作块，不显式产生未来状态轨迹。

**符号说明**：
- $\mathbf o_{<t}$：当前时刻以前的观测历史；
- $\ell$：语言指令；
- $\mathbf a_{t:t+H}$：预测动作块。

#### 公式 3：[[World Action Model|WAM 联合预测定义]]

$$
\hat{\mathbf o}_{t:t+H},\hat{\mathbf a}_{t:t+H}
=f_{\mathrm{WAM}}(\mathbf o_{<t},\ell).
\tag{3}
$$

**含义**：WAM 同时产生未来观测轨迹和动作块，使预测结构进入决策过程。

**符号说明**：
- $\hat{\mathbf o}_{t:t+H}$：预测的未来观测；
- $\hat{\mathbf a}_{t:t+H}$：预测的未来动作；
- $H$：预测与控制时域。

### 现有方法的局限

- **反应式策略短视**：局部合理的动作可能破坏后续子目标的可达性，尤其影响长时、遮挡和接触丰富任务。
- **预测—控制目标错位**：低像素误差或高视觉真实性不保证未来状态可达，也不保证动作安全。
- **显式规划代价高**：在生成式世界模型中搜索或逐帧去噪难以满足高频控制。
- **数据监督极不平衡**：互联网视频规模巨大但没有机器人动作，配对机器人轨迹有动作却规模有限。

### 本文的动机

作者希望用“预测结构是否真正连接可执行动作”统一原本分散在 [[Model-Based Reinforcement Learning|模型式强化学习]]、视频生成、latent action、VLA 与机器人模仿学习中的工作。

#### Figure 1: Evolution of World-Action Models / WAM 演进时间线

![Figure 1](https://arxiv.org/html/2609.16074v1/timeline_cropped.svg)

**说明**：时间线从 latent world-model RL 与生成模型基础出发，经 Foundation VLA、通用 VLA、video-action model 和 flow-based VLA，逐步汇合到 2026 年的 unified WAM。它表达的是研究范式的收敛，而非单一模型族的线性继承。

---

## 核心技术

### 四条基础研究线索

#### Figure 2: Foundational Threads / 四条基础技术路线

![Figure 2](https://arxiv.org/html/2609.16074v1/wam_background.png)

**说明**：四条路线分别提供环境动力学、视觉未来、无标签视频中的动作抽象和直接控制接口。WAM 的关键是把这些能力从松散组合变成共享训练或推理链路。

#### 公式 4：[[Model-Based Reinforcement Learning|RSSM 状态空间模型]]

$$
\begin{aligned}
\text{Deterministic state model:}\quad
\mathbf h_t &= f(\mathbf h_{t-1},\mathbf s_{t-1},\mathbf a_{t-1}),\\
\text{Stochastic state model:}\quad
\mathbf s_t &\sim p(\mathbf s_t\mid\mathbf h_t),\\
\text{Observation model:}\quad
\mathbf o_t &\sim p(\mathbf o_t\mid\mathbf h_t,\mathbf s_t),\\
\text{Reward model:}\quad
r_t &\sim p(r_t\mid\mathbf h_t,\mathbf s_t).
\end{aligned}
\tag{4}
$$

**含义**：PlaNet 的 RSSM 用确定性记忆与随机潜变量联合表示动力学，并从潜在状态重建观测和奖励，为 Dreamer 类 imagined rollout 奠定基础。

**符号说明**：
- $\mathbf h_t$：确定性循环状态；$\mathbf s_t$：随机潜在状态；
- $\mathbf o_t$、$r_t$：观测与奖励；
- $f$：RNN 转移函数。

#### 公式 5：[[World Model|编码后的潜在动力学]]

$$
\begin{aligned}
\mathbf z_t &= E(\mathbf o_t),\\
\hat{\mathbf z}_{t+1} &= f_\theta(\mathbf z_t,\mathbf a_t).
\end{aligned}
\tag{5}
$$

**含义**：显式解码式和隐式表征式 world model 都可先编码观测，再预测动作条件下的下一潜在状态。

**符号说明**：$E$ 为观测编码器；$f_\theta$ 为参数化动力学；$\mathbf z_t$ 为紧凑状态表示。

#### 公式 6：[[Video Generation Model|条件未来视频生成]]

$$
\mathbf o_{t:t+H}\sim
p_\theta\!\left(\mathbf o_{t:t+H}\mid\mathbf o_{<t},\ell\right).
\tag{6}
$$

**含义**：视频生成模型从视觉历史和语言采样未来观测，提供长时视觉先验，但并未天然保证这些未来可被机器人动作实现。

**符号说明**：$p_\theta$ 为条件视频分布；$\mathbf o_{t:t+H}$ 为未来视频；$\ell$ 为任务条件。

#### 公式 7：[[Latent Action Model|潜在动作预训练]]

$$
\begin{aligned}
\mathbf z_t &= E(\mathbf o_t),\\
\mathbf u_t &\sim q_\phi(\mathbf u_t\mid\mathbf z_t,\mathbf z_{t+1}),\\
\hat{\mathbf z}_{t+1} &= F_\theta(\mathbf z_t,\mathbf u_t).
\end{aligned}
\tag{7}
$$

**含义**：从连续两帧反推潜在动作 $\mathbf u_t$，再要求它能解释状态变化，从而利用没有机器人动作标签的视频。

**符号说明**：$q_\phi$ 为 latent action encoder；$F_\theta$ 为前向动力学；$\mathcal U$ 为潜在动作空间。

#### 公式 8：[[VLA|自回归动作序列]]

$$
\pi_\theta(\mathbf a_{t:t+H}\mid\mathbf o_{<t},\ell)
=\prod_{h=0}^{H-1}
\pi_\theta(\mathbf a_{t+h}\mid\mathbf o_{<t},\ell,\mathbf a_{t:t+h}).
\tag{8}
$$

**含义**：自回归 VLA 将动作离散化或序列化，逐步条件生成未来动作。

**符号说明**：$\pi_\theta$ 为策略；$h$ 为动作块内索引；$H$ 为动作时域。

#### 公式 9：[[Flow Matching|动作流匹配插值路径]]

$$
\mathbf a^\tau_{t:t+H}
=(1-\tau)\boldsymbol\epsilon+\tau\mathbf a^1_{t:t+H},
\qquad \tau\sim\mathcal U(0,1).
\tag{9}
$$

**含义**：flow-based VLA 在噪声动作与干净动作之间学习连续速度场，避免离散动作量化误差，但推理仍需数值积分。

**符号说明**：$\boldsymbol\epsilon$ 为噪声；$\mathbf a^1$ 为干净动作；$\tau$ 为插值时间。

### 模型架构

#### Figure 3: Component-level Taxonomy / 功能组件分类

![Figure 3](https://arxiv.org/html/2609.16074v1/wam_component.png)

**说明**：作者把 WAM 拆成四个功能模块：语言接口提供任务条件，视觉编码器决定预测状态，预测主干承载时空动力学，动作解码器把预测表征变成控制量。这一视角便于比较共享表征与 embodiment-specific action interface。

四类模块的常见选择如下：

- **语言编码器**：CLIP 全局语义、T5 密集 token 或 autoregressive LLM。
- **视觉编码器**：2D/Video VAE、DINO/CLIP/V-JEPA 表征、点云/occupancy/BEV，或预训练 VLM。
- **预测主干**：从头训练的 causal Transformer，或 Wan/Cosmos 等预训练视频生成主干。
- **动作解码器**：离散 action tokenizer、[[Latent Action Model|latent action model]]，或 diffusion/flow action head。

### 转移建模：联合预测与逆动力学

WAM 的生成过程可拆成策略、前向动力学、逆动力学和视觉规划四个概率模块。

#### 公式 10：[[VLA|策略生成]]

$$
p(\mathbf a_{t:t+H}\mid\mathbf o_{<t},\ell).
\tag{10}
$$

**含义**：直接从历史观测与语言生成动作块。

**符号说明**：$p$ 为条件分布；$\mathbf a_{t:t+H}$ 为未来动作；$\mathbf o_{<t}$、$\ell$ 为上下文。

#### 公式 11：[[World Model|前向动力学]]

$$
p(\mathbf o_{t:t+H}\mid\mathbf o_{<t},\mathbf a_{t:t+H}).
\tag{11}
$$

**含义**：给定候选动作预测其导致的未来世界，是反事实规划最直接的接口。

**符号说明**：$\mathbf a_{t:t+H}$ 为动作干预；$\mathbf o_{t:t+H}$ 为其条件未来。

#### 公式 12：[[Inverse Dynamics Model|逆动力学]]

$$
p(\mathbf a_{t:t+H}\mid\mathbf o_{<t},\mathbf o_{t:t+H}).
\tag{12}
$$

**含义**：根据当前状态与期望未来状态恢复可执行动作，是 plan-then-act 的 action grounding 接口。

**符号说明**：$\mathbf o_{t:t+H}$ 为目标视觉轨迹；$\mathbf a_{t:t+H}$ 为对应动作块。

#### 公式 13：[[Video Generation Model|视觉规划]]

$$
p(\mathbf o_{t:t+H}\mid\mathbf o_{<t},\ell).
\tag{13}
$$

**含义**：先根据任务想象期望未来，不显式输入机器人动作。

**符号说明**：$\ell$ 为任务目标；$\mathbf o_{t:t+H}$ 为视觉计划。

#### Figure 4: Transition Modeling Paradigms / 转移建模范式

![Figure 4](https://arxiv.org/html/2609.16074v1/wam_paradigms.png)

**说明**：Joint prediction 在共享过程中同时产生动作与未来；IDM 则先生成未来，再将状态转移翻译成机器人动作。前者耦合紧、摊销推理直接，后者模块清晰但依赖未来预测的信息充分性。

#### 公式 14：[[World Action Model|联合未来—动作分布]]

$$
p_{\mathrm{joint}}
(\mathbf o_{t:t+H},\mathbf a_{t:t+H}\mid\mathbf o_{<t},\ell).
\tag{14}
$$

**含义**：未来状态和动作共享生成过程，使 foresight 同时成为策略输出与辅助表示学习信号。

**符号说明**：$p_{\mathrm{joint}}$ 为联合生成分布；其余符号同前。

#### 公式 15：[[Inverse Dynamics Model|Plan-then-Act 分解]]

$$
\begin{aligned}
&p_{\mathrm{plan}}(\hat{\mathbf o}_{t:t+H}\mid\mathbf o_{<t},\ell)\\
&\qquad\cdot
p_{\mathrm{idm}}(\mathbf a_{t:t+H}\mid
\hat{\mathbf o}_{t:t+H},\mathbf o_{<t}).
\end{aligned}
\tag{15}
$$

**含义**：先生成期望视觉轨迹，再由 IDM 把它翻译成动作。

**符号说明**：$p_{\mathrm{plan}}$ 为视觉规划器；$p_{\mathrm{idm}}$ 为逆动力学；$\hat{\mathbf o}$ 为生成的计划。

#### 公式 16：[[World Action Model|单步联合预测]]

$$
\pi_{\mathrm{joint}}
=p(\mathbf a_{t+1},\mathbf o_{t+1}\mid\mathbf o_t,\ell).
\tag{16}
$$

**含义**：Eq. 14 的单步形式；GR-1/GR-2、UWM、WorldVLA、Cosmos Policy 等采用不同自回归、diffusion 或 flow 实现。

**符号说明**：$\pi_{\mathrm{joint}}$ 为联合策略；$\mathbf a_{t+1}$、$\mathbf o_{t+1}$ 为下一动作和观测。

#### 公式 17：[[Inverse Dynamics Model|单步逆动力学分解]]

$$
\pi_{\mathrm{idm}}
=p_{\mathrm{plan}}(\mathbf o_{t+1}\mid\mathbf o_t,\ell)
\,p_{\mathrm{idm}}(\mathbf a_{t+1}\mid\mathbf o_t,\mathbf o_{t+1}).
\tag{17}
$$

**含义**：Eq. 15 的单步形式。DreamZero 更接近显式 predict-then-act；Fast-WAM、GigaWorld-Policy 通过解耦注意力，在训练时联合建模而在推理时直接输出动作，更接近隐式 IDM。

**符号说明**：$\pi_{\mathrm{idm}}$ 为分解策略；两个概率项分别负责未来规划与动作恢复。

### 端到端与双系统

#### Figure 5: Taxonomy of WAM Architectures / WAM 架构二维分类

![Figure 5](https://arxiv.org/html/2609.16074v1/wam_models.png)

**说明**：图中两条正交轴是“联合预测/逆动力学”与“端到端/双系统”。端到端系统共享一条多模态计算路径，利于统一预训练；双系统将 world expert 与 action expert 分离，通过共享 self-attention、cross-attention 或 KV 接口交换信息，利于模块化适配和推理裁剪。

| 架构 | 联合预测 | 逆动力学 |
|---|---|---|
| End-to-End | 共享主干同时生成未来与动作 | 共享主干内按顺序 predict-then-act |
| Dual System | world/action expert 分工并联合输出 | world expert 先规划，action expert 再解码 |

端到端代表包括 GR-1/2、PAD、UWM、WorldVLA、DreamZero、Cosmos Policy；双系统常见 MoT 路由或 cross-attention，如 LingBot-VA、Fast-WAM、VidMan、VPP 和 ImageWAM。

### 训练方法

#### Figure 6: Policy Training Pipeline / 两阶段训练流水线

![Figure 6](https://arxiv.org/html/2609.16074v1/wam_pipeline.png)

**说明**：预训练负责学习通用时空结构、动作表示和 video-action alignment；后训练再针对机器人传感、动作空间和部署条件做策略微调、合成数据增强与 imagined-rollout RL。

#### 预训练

- **时空表征**：使用 Wan、Cosmos、Sora 等视频基础模型的视觉动力学先验，或在 JEPA 特征空间预测。
- **动作表征**：离散 action token、连续动作、频域 token，或从无动作视频中学习 latent action。
- **视频—动作对齐**：联合优化 action generation、video generation、forward dynamics 和 IDM 中的一项或多项。

#### 后训练

- **策略微调**：[[LoRA]]、adapter、residual action head 等在保留视频先验的同时适配具体 embodiment。
- **生成式数据增强**：重写外观、形态和光照，或用 IDM 给生成视频补 pseudo-action。
- **想象中强化学习**：在 world model rollout 中以 PPO、价值学习或教师监督优化策略，降低真实交互成本，但必须控制 model bias。

### 数据模态与规模

#### Figure 7: Data Modality and Scaling / 数据模态与金字塔

![Figure 7](https://arxiv.org/html/2609.16074v1/wam_data.png)

**说明**：语言、多视角视频、3D 几何、触觉/声音与 [[Proprioceptive State|本体状态]] 提供互补的控制变量；数据规模从海量无动作互联网视频，经第一视角人类演示，逐级收窄到稀缺但具有动作监督的机器人轨迹。

- **互联网视频**：获得广泛视觉动力学和交互先验。
- **第一视角人类演示**：提供操作意图、手—物体运动和跨 embodiment 线索。
- **机器人轨迹**：提供真正可执行的 action grounding，是从“看懂运动”到“控制机器人”的桥梁。
- **3D 与多模态数据**：点云、occupancy、3D Gaussian、触觉、声音和 proprioception 比纯 RGB 更直接反映接触和空间状态，但跨视角联合生成仍不成熟。

### 应用版图

#### 项目页补充图：WAM 应用领域

![WAM Applications](https://rcl-robotics.github.io/Awesome-World-Action-Models/survey-assets/wam-applications.webp)

**说明**：项目页将 WAM 应用汇总为 manipulation、navigation 和 autonomous driving。三者分别更强调接触动力学、长时空间推理，以及实时安全与多智能体一致性。

#### Table I: Surveyed WAMs by Application Domain

原表将方法分为 VAM（Video-Action Model）、Uni（联合 WAM）、WM-Plan（world-model-guided planning）、RL（WM-RL）和 3D（几何/结构化状态）。以下按领域展开原表全部条目。

**Manipulation**

| Method | Paradigm | Backbone | Eval / Note |
|---|---|---|---|
| GR-1 | VAM | GPT | LIBERO, CALVIN |
| GR-2 | VAM | GPT, 38M | LIBERO, CALVIN |
| PAD | Uni | DiT | LIBERO |
| UWM | Uni | 4-mode DiT | LIBERO |
| VPP | VAM | video prediction | dexterous |
| Seer | VAM | GPT + mask | 100K demos |
| VidMan | VAM | video diffusion + adapter | Bridge |
| Cosmos Policy | VAM | Cosmos-P2 | bimanual |
| ViPRA | VAM | flow matching | 100–200 demos |
| GigaWorld-Policy | Uni | action-centric | DROID |
| [[Papers/2603-FastWAM\|Fast-WAM]] | VAM | video prediction | LIBERO, RoboTwin |
| WorldVLA | Uni | Chameleon AR | LIBERO |
| Motus | Uni | MoT | RoboTwin |
| LingBot-VA | Uni | causal-diffusion MoT | AgiBot |
| World2Act | Uni | LLM + skill | RoboCasa |
| Act2Goal | VAM | goal-conditioned | RoboTwin 2.0 |
| VLA-JEPA | VAM | JEPA + flow | LIBERO |
| LAWM | VAM | latent action | LIBERO |
| HiLAM | VAM | hierarchical latent | long-horizon |
| PRWM | RL | contrastive RL | DROID |
| EVA | RL | video WM | RoboTwin 2.0 |
| RISE | RL | latent | contact-rich |
| VLA-MBPO | RL | video WM | LIBERO-Plus |
| GPC | RL | rollout WM | Push-T |
| WMPO | RL | pixel WM | LIBERO |
| RoboHorizon | RL | LLM + WM | sparse reward |
| World-VLA-Loop | RL | feedback | ManiSkill |
| IWS | RL | video WM | 10 min @ 15 FPS |
| ManiGaussian++ | 3D | Gaussian | bimanual |
| ParticleFormer | 3D | particles | deformable |
| GWM | 3D | VAE + diffusion | MetaWorld |
| PointWorld | 3D | point cloud | 2M+ trajectories |
| PIN-WM | 3D | physics-informed | non-prehensile |
| VT-WM | 3D | visuo-tactile | contact |
| Cloth-WM | 3D | DreamerV2 | cloth |
| Audio-WM | 3D | acoustic | liquid pouring |
| World4RL | RL | diffusion WM | frozen environment |
| DreamPlan | RL | video WM | VLA fine-tuning |
| VAMPO | RL | GRPO / denoising | LIBERO, CALVIN |

**Navigation**

| Method | Paradigm | Backbone | Eval / Note |
|---|---|---|---|
| PathDreamer | WM-Plan | panoramic generation | R2R |
| MonoDream | WM-Plan | monocular | R2R-CE, RxR-CE |
| DreamWalker | WM-Plan | latent + MCTS | R2R, VLN-CE |
| X-MOBILITY | RL | latent WM environment | mobile robot |
| NWM | WM-Plan | multi-domain | Habitat, Ego4D |
| InternVLA-N1 | VAM | dual-system latent | R2R-CE perceptive |
| FDM | WM-Plan | GRU | ANYmal, quadruped |
| RWM | RL | GRU | A1, quadruped |
| WMP | RL | RSSM | Isaac |

**Autonomous Driving**

| Method | Paradigm | Backbone | Eval / Note |
|---|---|---|---|
| DriveDreamer | WM-Plan | video generation | nuScenes |
| GAIA-1 | WM-Plan | text-video | large-scale |
| DriveDreamer-2 | WM-Plan | multi-camera generation | nuScenes |
| GAIA-2 | WM-Plan | multi-camera scaled | OpenDV |
| DrivingWorld | WM-Plan | long-horizon AR | nuScenes |
| DrivingGen | WM-Plan | policy-controllable | nuScenes |
| OccWorld | WM-Plan | voxel tokens | nuScenes-Occ |
| Drive-OccWorld | WM-Plan | multi-step occupancy | nuScenes-Occ |
| DreamerAD | RL | Dreamer-AD | nuScenes, nuPlan |
| World4Drive | RL | virtual-environment RL | NAVSIM, nuPlan |
| ADriver-I | Uni | AR image + action | nuScenes |
| DrivingGPT | Uni | large AR video | NAVSIM |
| Doe-1 | Uni | autoregressive | nuScenes |
| OccLLaMA | Uni | occupancy + language | nuScenes-QA |
| ProphetDWM | Uni | long-horizon | NAVSIM, nuPlan |
| VaViM/VaVAM | Uni | video AR + action AR | OpenDV |
| DriveLaW | Uni | language-action | nuScenes |
| AutoMoT | Uni | asynchronous MoT | Bench2Drive |

**说明**：Table I 的方法横跨不同数据、任务和评测协议，适合做研究地图，不适合据此直接排名。操作领域方法最密集；导航更常将 world model 用作 look-ahead planner；驾驶则更偏 structured occupancy、可控视频与安全闭环。

### 开放技术问题

#### 1. Motion intent 与 action alignment

先用海量视频学习“应该发生什么”，再用少量机器人轨迹学习“机器人如何实现”。关键是避免 action fine-tuning 遗忘视觉动力学先验，可用冻结、alignment layer、residual action head 或更强 anti-forgetting。

#### 2. World–action factorization

#### 公式 18：[[World Action Model|Agent–Universe 轨迹因子分解]]

$$
\begin{aligned}
&p^\pi_\mu(a_t,s_{t+1},\ldots,a_{T-1},s_T\mid s_t)\\
&=\prod_{k=t}^{T-1}
\underbrace{p_\pi(a_k\mid s_k)}_{\text{agent}}
\underbrace{p_\mu(s_{k+1}\mid s_k,a_k)}_{\text{universe}}.
\end{aligned}
\tag{18}
$$

**含义**：策略与世界转移有不同自然目标。策略最大化回报，世界模型追求干预条件下的预测准确性；盲目联合训练可能让 policy 利用 world model 的乐观偏差。

**符号说明**：$p_\pi$ 为 agent policy；$p_\mu$ 为环境转移；$s_k,a_k$ 为状态与动作；$T$ 为轨迹终点。

#### 3. 空间、多视角与长期状态

当前视频 backbone 难以保证物体恒常性、显式 3D 几何和 [[Multi-View Consistency|跨视角一致性]]。长时任务又不能简单无限延长视觉上下文，需要事件记忆、语言记忆、episodic memory 或外置 agentic harness。

#### 4. 神经模拟器与闭环学习

[[Neural Simulator|神经模拟器]] 可利用失败轨迹和 imagined interaction 改进策略，但长时 rollout 的误差累积会被策略主动利用。重要方向是 uncertainty-aware rollout、短真实反馈闭环，以及把高保真世界模型放在训练期而不是控制热路径中。

#### 5. 推理与部署

few-step consistency/mean/rectified flow、蒸馏、量化、剪枝、operator fusion、batching 和 KV cache 能降低成本；但真正的控制预算还由 rollout horizon、候选轨迹数、重规划频率和 action decoding 决定。

---

## 实验

### 实验设置

本文没有训练或评测一个新 WAM，而是汇总现有工作的 datasets、benchmarks、metrics 与 protocols。因而这里的“实验”应理解为综述提出的评测框架。

### 评测指标

#### Table II: Compact Definitions of WAM Metrics

| 类别 | Metric | 原文定义 |
|---|---|---|
| Task | SR | $\operatorname{SR}=N^{-1}\sum_{i=1}^{N}s_i$，$s_i\in\{0,1\}$ |
| Navigation | SPL | $N^{-1}\sum_i s_i\ell_i/\max(p_i,\ell_i)$ |
| Navigation | NE | $N^{-1}\sum_i d_{\mathcal G}(v_i^{\mathrm{stop}},v_i^{\mathrm{goal}})$ |
| Navigation | nDTW | $\operatorname{nDTW}_i=\exp[-\operatorname{DTW}_{d_{\mathcal G}}(\mathbf P_i^\star,\hat{\mathbf P}_i)/(\lvert\mathbf P_i^\star\rvert d_{\mathrm{th}})]$，再对样本平均 |
| Trajectory | ADE | $N^{-1}\sum_i T_i^{-1}\sum_t\lVert\hat{\mathbf x}_{i,t}-\mathbf x_{i,t}\rVert_2$ |
| Trajectory | FDE | $N^{-1}\sum_i\lVert\hat{\mathbf x}_{i,T_i}-\mathbf x_{i,T_i}\rVert_2$ |
| Localization | ATE | 对齐 $\mathbf S\in\mathrm{SE}(3)$ 后，$[N^{-1}\sum_i\lVert\operatorname{trans}(\mathbf T_i^{-1}\mathbf S\hat{\mathbf T}_i)\rVert_2^2]^{1/2}$ |
| Localization | RPE | $[(N-\Delta)^{-1}\sum_i\lVert\operatorname{trans}(\mathbf E_i)\rVert_2^2]^{1/2}$，$\mathbf E_i=(\mathbf T_i^{-1}\mathbf T_{i+\Delta})^{-1}(\hat{\mathbf T}_i^{-1}\hat{\mathbf T}_{i+\Delta})$ |
| Generation | FID | $\lVert\boldsymbol\mu_r-\boldsymbol\mu_g\rVert_2^2+\operatorname{tr}[\boldsymbol\Sigma_r+\boldsymbol\Sigma_g-2(\boldsymbol\Sigma_r^{1/2}\boldsymbol\Sigma_g\boldsymbol\Sigma_r^{1/2})^{1/2}]$ |
| Generation | FVD | 与 FID 相同的 Fréchet 形式，但在视频特征分布上计算 |
| Generation | PSNR | $10\log_{10}[v_{\max}^2/\operatorname{MSE}(\mathbf I,\hat{\mathbf I})]$ |
| Generation | SSIM | $[(2\mu_I\mu_{\hat I}+c_1)(2\sigma_{I\hat I}+c_2)]/[(\mu_I^2+\mu_{\hat I}^2+c_1)(\sigma_I^2+\sigma_{\hat I}^2+c_2)]$ |
| Generation | LPIPS | $\sum_l(H_lW_l)^{-1}\sum_{h,w}\lVert\mathbf w_l\odot[\hat{\boldsymbol\phi}_l(\mathbf I)_{h,w}-\hat{\boldsymbol\phi}_l(\hat{\mathbf I})_{h,w}]\rVert_2^2$ |
| Language | BLEU | $\operatorname{BP}\exp(\sum_{n=1}^{M}w_n\log p_n)$ |
| Language | ROUGE-L | $(1+\beta^2)P_{\mathrm{LCS}}R_{\mathrm{LCS}}/(R_{\mathrm{LCS}}+\beta^2P_{\mathrm{LCS}})$ |
| Language | CIDEr | $\sum_{n=1}^{4}w_n\lvert\mathcal R\rvert^{-1}\sum_{r\in\mathcal R}\cos[\mathbf g_n(c),\mathbf g_n(r)]$ |
| Language | METEOR | $F_{\mathrm{mean}}(1-\operatorname{Penalty})$，其中 $F_{\mathrm{mean}}=PR/[\alpha P+(1-\alpha)R]$ |
| Driving | DS | $N^{-1}\sum_i\operatorname{RC}_i\operatorname{IS}_i$ |
| Driving | PDMS | $q_i=\operatorname{NC}_i\operatorname{DAC}_i(5\operatorname{TTC}_i+5\operatorname{EP}_i+2C_i)/12$，$\operatorname{PDMS}=N^{-1}\sum_iq_i$ |
| RL | HNS | $(s_{\mathrm{agent},g}-s_{\mathrm{random},g})/(s_{\mathrm{human},g}-s_{\mathrm{random},g})$，先逐游戏计算再聚合 |

**说明**：SR、route completion、driving score 和 return 最接近最终控制目标，却不能解释收益来自预测、模仿先验还是任务特定训练；FID/FVD/LPIPS 仅衡量生成外观，不能替代 action grounding 与闭环安全评测。

### 数据集、模拟器与 benchmark

#### Table III: Surveyed Datasets, Simulators, and Benchmarks

| 类别 | Name | Reported Scale | Type | Eval Metrics |
|---|---|---:|---|---|
| Robot corpus | DROID | 76k trajectories | Real | SR, FVD, FID |
| Robot corpus | BridgeData V2 | 60,096 trajectories | Real | SR, Accuracy |
| Robot corpus | Open X-Embodiment | 1M+ trajectories | Mixed | SR, FVD, LPIPS |
| Robot corpus | AgiBot-World | 1M+ trajectories | Real | SR, FVD, LPIPS |
| Human video | SSv2 V2 | 220k clips | Real | SR downstream |
| Human video | Ego4D | 3.67k hours | Real | SR, ATE, RPE |
| Human video | EgoDex | 829 hours / 194 tasks | Real | SR downstream |
| Human video | Kinetics-700 | 700 classes | Real | SR downstream |
| Human video | HowTo100M | 136M clips | Real | SR downstream |
| Manipulation | LIBERO | 130 tasks | Sim | SR, FVD, LPIPS, PSNR |
| Manipulation | MimicGen | 18 tasks / 50k+ demos | Sim | SR, FVD |
| Manipulation | CALVIN | 34 tasks | Sim | Avg. Len., SR, FID |
| Manipulation | RLBench | 100+ tasks | Sim | SR |
| Manipulation | MetaWorld | 50 tasks | Sim | SR, normalized score |
| Manipulation | ManiSkill 1/2/3 | 20+ tasks | Sim | SR, normalized score |
| Manipulation | RoboTwin / 2.0 | 50+ tasks | Mixed | SR, PSNR, SSIM |
| Manipulation | SimplerEnv | — | Sim | SR, Accuracy |
| Manipulation | RoboCasa | 100 tasks / 120 scenes | Sim | SR, FVD, SSIM |
| Manipulation | Push-T | 1 task | Sim | IoU, SR |
| Manipulation | RoboDojo | 60 tasks | Mixed | SR, Avg. Score |
| Driving | nuScenes | 1k scenes | Real | Collision, L2, mIoU, FVD |
| Driving | Waymo Open Motion | 103k segments | Real | ADE, FDE, Miss Rate |
| Driving | nuPlan | 1.3k hours | Real | PDMS, Comfort, TTC |
| Driving | OpenDV-2K | 2,059 hours | Real | FID, FVD, LPIPS |
| Driving | NAVSIM v1/v2 | — | Mixed | PDMS, EPDMS, NC |
| Driving | BDD100K | 100k videos | Real | Accuracy, mAP |
| Driving | Bench2Drive | 220 routes / 12 towns | Sim | DS, RC, IS, L2 |
| Driving | KITTI | 6 hours | Real | FID, FVD |
| Driving | CARLA | N/A | Sim | DS, IS, RC, Collision |
| Driving | Argoverse | 327.8k sequences | Real | ADE, FDE |
| Driving | OpenScene | 120+ hours | Real | mIoU, Collision Rate |
| Driving | ZOD | 1.5k scenes | Real | mAP |
| Navigation | Matterport3D | 90 buildings | Real | SR, SPL, NE, nDTW |
| Navigation | RECON | — | Real | SR |
| Navigation | R2R / R2R-CE | 7.2k paths | Sim | SR, SPL, NE, Oracle |
| Navigation | TartanDrive | — | Real | SR |
| Navigation | RxR / RxR-CE | 16.5k paths | Sim | SR, SPL, NE |
| Navigation | SCAND | — | Real | SR |
| Navigation | Habitat | N/A | Sim | SR, SPL, ATE, RPE |
| Navigation | ScaleVLN | 4.9M trajectories | Sim | SR, SPL |
| RL | DMControl | 28 tasks | Sim | Return, normalized score |
| RL | Craftax | 1 game | Sim | Return, Reward |
| RL | Atari ALE | 55 games | Sim | HNS, IQM, Mean/Median |
| RL | DMLab | — | Sim | Return |
| RL | Atari 100k | 26 games / 100k steps | Sim | HNS, IQM |
| RL | BSuite | 23 tasks | Sim | Return |
| RL | Procgen | 16 games | Sim | Return, Reward |
| RL / Real bridge | FMB | — | Real | SR, Cycle Time |

**说明**：机器人轨迹用于 action grounding，人类视频用于扩大视觉与运动先验；操作 benchmark 强调任务成功与接触，导航强调路径效率和空间一致性，驾驶必须把视频质量、结构化预测与闭环安全结合起来。RL benchmark 只适合作为 latent dynamics 与 imagined optimization 的方法学诊断，不能替代真实机器人评测。

### 主要结论

1. 视觉预测指标和闭环控制指标必须成对报告。
2. 不同 WAM 使用的数据、embodiment、预测空间和推理方式差异很大，当前不存在真正统一的排行榜。
3. 最值得建立的 benchmark 是“同一 world/action backbone、同一机器人数据预算”下，对比无预测辅助、训练期预测、显式 test-time imagination 和 WM-RL。

---

## 批判性思考

### 优点

1. **定义及时**：把 rapidly emerging 的 video-action、latent world model、IDM 与 WM-RL 文献放入统一语言。
2. **二维架构分类清晰**：transition paradigm 与 system structure 分离，比单纯按模型名罗列更能指导设计。
3. **控制导向明确**：反复强调“有用的预测”必须改善任务成功、安全、鲁棒性和 embodiment transfer。
4. **覆盖面广**：同时整理操作、导航、驾驶、数据、metric 和开放问题，项目页适合继续跟踪新工作。

### 局限性

1. **WAM 边界偏宽**：辅助 future-prediction loss、显式视觉规划、latent simulator 和 imagined RL 都被纳入，机制差异可能被术语掩盖。
2. **联合分布不等于因果动力学**：Eq. 3/14 的 $p(o_{\mathrm{future}},a_{\mathrm{future}}\mid h,\ell)$ 可以依赖数据相关性，不保证学到动作干预 $p(o_{\mathrm{future}}\mid h,do(a))$；因此“显式建模动作如何影响未来”的定义比公式本身更强。
3. **缺少统一实证比较**：Table I 汇总的模型横跨不同 benchmark 和数据预算，不能据此判断 joint prediction 与 IDM 谁更好。
4. **生成指标仍占较大篇幅**：虽指出 FVD 不等于控制效用，但尚未提出反事实正确性、可达性、uncertainty calibration 和 policy exploitability 的标准测试。
5. **文献新且成熟度不一**：论文提交于 2026 年 9 月，大量条目是刚发布的预印本，结论会快速变化。

### 潜在改进方向

1. 按 world prediction 在控制链中的作用再分层：representation pretraining、policy conditioning、online search、neural simulator 和 data generator。
2. 建立候选动作干预测试：固定状态，对多个动作预测后果，再与真实 rollout 比较排序与校准，而不只比较单一路径视频。
3. 训练期使用高容量 multimodal/3D world model，部署期蒸馏为低延迟 action-centric latent 或轻量 action head。
4. 将失败轨迹、uncertainty 与短周期真实反馈引入 imagined policy improvement，限制策略利用 world-model bias。
5. 对接触丰富操作优先建模 3D、触觉和 proprioception，而非把像素视频质量视为唯一世界状态。

### 可复现性评估

- [x] 官方维护的论文与资源列表
- [x] arXiv HTML/PDF 可获取
- [ ] 新模型代码（本文不提出模型）
- [ ] 统一 benchmark 实现
- [ ] 可复现实证结论（本文无统一重跑实验）

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

- [[World Model]]：提供动作条件下的环境动力学与 imagined rollout。
- [[VLA]]：提供语言条件与可执行动作生成接口。
- [[Model-Based Reinforcement Learning]]：提供规划、价值学习和模型偏差分析基础。
- [[Video Generation Model]]：提供大规模视觉时空先验。

### 对比

- [[Papers/2603-FastWAM\|Fast-WAM]]：检验 test-time future imagination 是否必要，代表训练期世界建模、推理期直接行动。
- [[Papers/2410-Pi07\|Pi07]]：本文把它视为 goal-conditioned WAM，而非普通 next-step joint prediction。
- [[Papers/2609-OpenWAM\|OpenWAM]]：侧重受控拆解 WAM 的视觉先验、信息流和规模效应。

### 方法相关

- [[Inverse Dynamics Model]]：plan-then-act 的动作接口。
- [[Latent Action Model]]：从无标签视频获得可迁移运动抽象。
- [[Flow Matching]]：连续动作与视频生成的常见训练范式。
- [[Multi-View Consistency]]：操作与驾驶的关键空间约束。
- [[Neural Simulator]]：闭环 imagined policy learning 的环境接口。

---

## 速查卡片

> [!summary] World-Action Models for Robot Learning and Control: A Survey
> - **核心**：WAM = 预测未来世界 + 生成可执行动作，并让两者在训练或推理中结构性耦合。
> - **分类**：joint prediction vs. IDM；end-to-end vs. dual system。
> - **数据**：互联网视频学习世界先验，第一视角视频学习动作意图，机器人轨迹完成 action grounding。
> - **判断标准**：闭环控制收益优先于视频观感，实时性和模型偏差属于算法问题。
> - **资源**：[Project](https://rcl-robotics.github.io/Awesome-World-Action-Models) / [GitHub](https://github.com/RCL-Robotics/Awesome-World-Action-Models)

---

*笔记创建时间：2026-09-23*
