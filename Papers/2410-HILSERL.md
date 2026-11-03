---
type: paper
arxiv_id: 2410.21845
source_vault: notes
source_path: PaperNotes/VLA/HIL-SERL.md
date_migrated: 2026-11-03
title: "Precise and Dexterous Robotic Manipulation via Human-in-the-Loop Reinforcement Learning"
method_name: "HIL-SERL"
authors: [Jianlan Luo, Charles Xu, Jeffrey Wu, Sergey Levine]
year: 2025
venue: Science Robotics
tags: [real-world-rl, human-in-the-loop, robot-manipulation, off-policy-rl, dexterous-manipulation, sparse-reward]
zotero_collection: VLA
image_source: online
arxiv_html: https://arxiv.org/html/2410.21845
code_url: https://github.com/rail-berkeley/hil-serl
code_companion:
created: 2026-10-28
---

# 论文笔记：Precise and Dexterous Robotic Manipulation via Human-in-the-Loop Reinforcement Learning

## 元信息

| 项目 | 内容 |
|------|------|
| Authors | Jianlan Luo, Charles Xu, Jeffrey Wu, Sergey Levine |
| 机构 | UC Berkeley |
| 日期 | October 2024（arXiv）；March 2025（v3 / Science Robotics） |
| 项目主页 | [HIL-SERL](https://hil-serl.github.io/) |
| 对比基线 | [[HG-DAgger]]、Behavior Cloning、Diffusion Policy、IBRL、Residual RL、DAPG |
| 链接 | [arXiv](https://arxiv.org/abs/2410.21845) / [Code](https://github.com/rail-berkeley/hil-serl) |

---

## 一句话总结

> HIL-SERL 用少量演示启动 RLPD，在真机探索的关键失败时刻由人类短暂接管，并把纠错片段作为高价值 off-policy 数据，使单任务视觉策略在数小时内达到近满成功率和超越人类演示的节拍。

---

## 核心贡献

1. **可运行的真机 RL 系统配方**：把 [[RLPD]]、预训练视觉编码器、[[Reward Classifier|二值奖励分类器]]、安全低层控制、异步 actor/learner 和人工纠错组合成统一系统。
2. **人类介入用于探索而非纯模仿**：operator 只在策略即将进入坏状态时接管；数据被用于 Q-learning，使策略能够超过演示质量和速度上限。
3. **跨物理性质验证**：同一框架覆盖精密插装、双臂协调、柔性物体、Jenga 动态抽取和锅中翻转，并分析了 reactive 与 predictive policy 的自然涌现。

#### Figure 1: 实验任务概览

![Figure 1](https://arxiv.org/html/2410.21845v3/fig1.png)

**说明**：任务涵盖 Jenga whipping、物体翻转、timing-belt/dashboard/motherboard/IKEA 装配，要求完全不同的接触、动态与双臂协调能力。

---

## 问题背景

### 要解决的问题

真实机器人 RL 同时受制于高维视觉、稀疏奖励、危险探索、昂贵 reset 和长 horizon。论文希望回答：能否在不依赖仿真和精细 reward shaping 的前提下，在真实硬件上用数小时获得高可靠、低 cycle-time 的视觉策略？

#### 公式 1: [[Markov Decision Process|真机操作 MDP 目标]]

$$
\max_{\pi}\;\mathbb E\left[\sum_{t=0}^{H}\gamma^t r(s_t,a_t)\right]
$$

**含义**：策略最大化有限 horizon 内的折扣累计奖励；HIL-SERL 主要使用任务完成时给 1、其余为 0 的 [[Sparse Binary Reward|稀疏二值奖励]]。

**符号说明**：
- $s_t$：图像和机器人 proprioception。
- $a_t$：末端 twist、feedforward wrench 或离散 gripper action。
- $H$：episode horizon；$\gamma$：折扣因子。

### 现有方法的局限

- **纯 online RL**：在困难任务上几乎无法碰到成功，且随机动作可能损坏硬件。
- **只加 offline demonstrations**：帮助初始化，但策略进入演示未覆盖的状态后仍无法恢复。
- **BC/DAgger**：能吸收人工动作，却没有基于 task reward 改进节拍或超越不一致人工纠错的机制。
- **仿真训练**：接触丰富、柔性物体和动态操作难以获得足够 fidelity。

### 本文的动机

人工不需要持续遥操作整条轨迹，只需在 RL 的探索瓶颈处提供短暂纠错；off-policy critic 再利用 reward 区分哪些人类动作真正提高未来成功率。这把人类从“教师策略”转变为“探索向导与安全员”。

---

## 核心技术

### 模型架构

HIL-SERL 是异步 actor–learner 系统：

- **Actor process**：10 Hz 与机器人交互，接受 learner 周期发送的新参数；SpaceMouse 可随时覆盖 RL action。
- **Learner process**：从 demo/RL 两个 buffer 等量采样，用 RLPD 更新 Gaussian policy 和 Q ensemble。
- **视觉编码器**：多相机共享 ImageNet-pretrained ResNet-10。
- **本体分支**：MLP 编码末端 pose、velocity、force/torque、joint/gripper state。
- **夹爪分支**：连续 arm policy 外另训 DQN grasp critic，在 open/close/stay 中取 argmax。

#### Figure 2: HIL-SERL 系统架构

![Figure 2](https://arxiv.org/html/2410.21845v3/fig2_1.png)

**说明**：Actor、Learner 和 replay buffers 解耦。人类动作实际替换策略动作；intervention 数据被双重收录，因而比普通 transition 更频繁地进入训练 batch。

### 数据与数据处理

训练一项新任务通常包含三类数据：

1. **Reward data**：约 200 个 positive、1000 个 negative state，训练任务专用二值分类器；通常相当于约 10 条遥操作轨迹、约 5 分钟采集。
2. **Offline demonstrations**：20–30 条成功轨迹，初始化 demo buffer。
3. **Online transitions**：自主动作、失败、成功以及人工 intervention；人类接管片段同时进入 demo buffer 与 RL buffer，自主片段只进入 RL buffer。

所有相机图像裁剪到任务区域并 resize 为 $128\times128$，再做 random crop augmentation。

#### Figure 3: 完整训练数据流程

![Figure 3](https://arxiv.org/html/2410.21845v3/training_process.png)

**说明**：先训 reward classifier，再采 20–30 条 demo，最后 online RL。训练早期干预较多，策略成熟后逐渐减少，目标是 success rate 上升、cycle time 与 intervention rate 同时下降。

### 核心模块一：RLPD 的 online/offline 混合更新

RLPD 每次用相同比例的 prior/demo data 与 online data 更新；policy objective 与 [[Soft Actor-Critic|SAC]] 一致，用 entropy regularization 保持探索。

#### 公式 2: [[RLPD|Critic TD 目标]]（论文 Eq. 1）

$$
\mathcal L_Q(\phi)=
\mathbb E_{s,a,s'}\left[
\left(
Q_\phi(s,a)-
\left(r(s,a)+\gamma\mathbb E_{a'\sim\pi_\theta}
[Q_{\bar\phi}(s',a')]
\right)
\right)^2
\right]
$$

**含义**：demo 与 online transition 都通过同一个 Bellman backup 更新 Q，人工动作不会被无条件模仿，而是按其未来回报影响 policy。

**符号说明**：
- $Q_\phi,Q_{\bar\phi}$：当前与目标 critic。
- $\pi_\theta$：Gaussian motion policy。
- $r(s,a)$：reward classifier 输出的终止奖励。

#### 公式 3: [[Soft Actor-Critic|Entropy-regularized actor 目标]]（论文 Eq. 2）

$$
\mathcal L_\pi(\theta)=
-\mathbb E_s\left[
\mathbb E_{a\sim\pi_\theta}
[Q_\phi(s,a)]
+\alpha\mathcal H\!\left(\pi_\theta(\cdot\mid s)\right)
\right]
$$

**含义**：actor 最大化 Q 与策略熵；$\alpha$ 自适应调节。折扣 $\gamma<1$ 也使更快获得成功奖励的轨迹价值更高，从而缩短 cycle time。

**符号说明**：
- $\mathcal H$：策略熵。
- $\alpha$：entropy temperature。

### 核心模块二：Human intervention

在 rollout 中，人类可从任意时刻 $t_i$ 接管最多 $N$ 步；实际执行动作

$$
a_t^*=\begin{cases}
a_t^{\mathrm{itv}}, & \text{human takeover},\\
a_t^{\mathrm{RL}}, & \text{otherwise}.
\end{cases}
$$

人类重点处理不可恢复状态、局部最优或硬件风险。论文提醒：不要在早期持续给出很长、稀疏但最终成功的干预，因为这会让 critic 将此前低质量 policy states 也错误赋高值，引发 Q overestimation。

### 核心模块三：离散 gripper critic

单夹爪动作集合为 open/close/stay，双夹爪为 $3^2=9$ 个组合；它与连续末端动作共享观察和 reward，但单独用 Double-DQN 风格目标训练。

#### 公式 4: [[Deep Q-Network|离散夹爪 critic 目标]]（论文 Eq. 3）

$$
\mathcal L(\theta)=
\mathbb E_{s,a,s'}\left[
\left(
r+\gamma Q_{\theta'}
\left(s',\arg\max_{a'}Q_\theta(s',a')\right)
-Q_\theta(s,a)
\right)^2
\right]
$$

**含义**：当前网络选下一步离散动作、target network 评价；推理时把离散夹爪动作与连续 arm action 拼接后执行。

**符号说明**：
- $\theta,\theta'$：在线/目标 grasp critic。
- $a'$：候选夹爪动作。

### 核心模块四：机器人表示与安全控制

episode 开始时随机化末端初始 pose；proprioception 表示在初始末端坐标系中，policy action 表示在当前末端 frame 中，从而形成 ego-centric spatial generalization。接触任务使用带 reference limiting 的 impedance controller；动态任务直接输出 feedforward wrench。

#### 公式 5: 初始末端坐标系中的相对位姿

$$
T_{b_0^{(i)}b_t^{(i)}}
=\left(T_{b_0^{(i)}}\right)^{-1}T_{b_t^{(i)}}
$$

**含义**：第 $i$ 个机械臂的当前末端位姿改写为相对 episode 初始 pose 的变换。

**符号说明**：$b_0^{(i)}$、$b_t^{(i)}$ 分别是初始和时刻 $t$ 的末端 frame。

#### 公式 6: 齐次变换表示

$$
T_{ab}=\begin{bmatrix}
R_{ab}&p_{ab}\\
0_{1\times3}&1
\end{bmatrix}
$$

**含义**：用旋转 $R_{ab}$ 与平移 $p_{ab}$ 表示 frame $b$ 到 frame $a$ 的刚体变换。

**符号说明**：$R_{ab}\in SO(3)$，$p_{ab}\in\mathbb R^3$。

#### 公式 7: Twist 的末端坐标变换

$$
{\mathcal V_t^{(i)}}'=[\mathrm{Ad}_t^{(i)}]\mathcal V_t^{(i)}
$$

**含义**：把 base-frame twist 转为末端 frame 中的 policy observation/action 表示。

**符号说明**：$\mathcal V$ 为 6D twist，$[\mathrm{Ad}]$ 为 SE(3) adjoint。

#### 公式 8: SE(3) adjoint matrix

$$
[\mathrm{Ad}_t^{(i)}]=
\begin{bmatrix}
R_{b_t^{(i)}}&0_{3\times3}\\
[p_{b_t^{(i)}}]_\times R_{b_t^{(i)}}&R_{b_t^{(i)}}
\end{bmatrix}
$$

**含义**：将旋转和平移对角速度/线速度的耦合写入同一线性变换。

**符号说明**：$[p]_\times$ 是由平移向量构造的反对称矩阵。

#### 公式 9: [[Impedance Control|低层阻抗控制]]

$$
F=k_p e+k_d\dot e+F_{\mathrm{ff}}+F_{\mathrm{cor}}
$$

**含义**：PD feedback、policy 的 feedforward wrench 和 Coriolis compensation 共同生成末端 wrench；reference limiting 限制目标跳变以保护硬件。

**符号说明**：$e,\dot e$ 为 pose/velocity error，$k_p,k_d$ 为增益。

### 推理与部署

部署时 human intervention 关闭，只保留视觉/本体 policy、grasp critic 和低层控制器。系统运行 10 Hz；单个 RTX 4090 同时承担训练计算。人工 reset 或脚本 reset 仍由具体任务决定。

---

## 实验

### 任务覆盖

#### Figure 4: 全部实验任务

![Figure 4](https://arxiv.org/html/2410.21845v3/fig3.png)

**说明**：包括 motherboard 四个子任务、IKEA 三阶段装配、dashboard、handover、timing belt、Jenga whipping 和 object flipping；动作空间从 6D twist 到 12D 双臂 twist，再到 dynamic wrench。

### 主要结果

#### Table 1a: HIL-SERL 与 imitation learning

| Task | Train h | BC SR | HIL-SERL SR | BC cycle s | HIL-SERL cycle s |
|---|---:|---:|---:|---:|---:|
| RAM Insertion | 1.5 | 29 | **100** | 8.3 | **4.8** |
| SSD Assembly | 1 | 79 | **100** | 6.7 | **3.3** |
| USB Grasp-Insertion | 2.5 | 26 | **100** | 13.4 | **6.7** |
| Cable Clipping | 1.25 | 95 | **100** | 7.2 | **4.2** |
| IKEA - Side Panel 1 | 2 | 77 | **100** | 6.5 | **2.7** |
| IKEA - Side Panel 2 | 1.75 | 79 | **100** | 5.0 | **2.4** |
| IKEA - Top Panel | 1 | 35 | **100** | 8.9 | **2.4** |
| IKEA - Whole Assembly | – | 1/10 | **10/10** | – | – |
| Car Dashboard Assembly | 2 | 41 | **100** | 20.3 | **8.8** |
| Object Handover | 2.5 | 79 | **100** | 16.1 | **13.6** |
| Timing Belt Assembly | 6 | 2 | **100** | 9.1 | **7.2** |
| Jenga Whipping | 1.25 | 8 | **100** | – | – |
| Object Flipping | 1 | 46 | **100** | 3.9 | **3.8** |
| Average | – | 49.7 | **100** | 9.6 | **5.4** |

**说明**：除 IKEA full assembly 为 10 次外，每项评估 100 次。大多数任务 1–2.5 小时，但 timing belt 是 6 小时；“1–2.5 小时”不能概括所有任务。BC 通常为匹配 episode/intervention 数量的 HG-DAgger，Jenga/object flipping 则分别用 50/200 条 flat BC demos。

#### Table 1b: 代表任务上的算法和数据消融（成功率 %）

| Task | DP | HG-DAgger | BC | IBRL | Residual RL | DAPG | HIL no demo/no itv | HIL no itv | HIL-SERL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RAM Insertion | 27 | 29 | 12 | 75 | 0 | 8 | 0 | 48 | **100** |
| Dashboard Assembly | 18 | 41 | 35 | 0 | 0 | 18 | 0 | 0 | **100** |
| Object Flipping | 56 | 46 | 46 | 95 | 97 | 72 | 0 | 100 | **100** |
| Average | 34 | 39 | 31 | 57 | 32 | 33 | 0 | 49 | **100** |

**说明**：无 demo/无 intervention 的 RL 全部失败；只有 demo 而无在线纠错平均 49%。两者结合才在精密、双臂和动态三类任务上都稳定。

#### Figure 5: HIL-SERL 与 HG-DAgger 学习曲线

![Figure 5](https://arxiv.org/html/2410.21845v3/fig4.svg)

**说明**：HIL-SERL 的 success rate 上升、intervention rate 下降到零、cycle time 持续缩短；HG-DAgger 的干预率与节拍不呈单调改善，说明纯监督拟合没有 task-reward 驱动的性能优化。

### 鲁棒性与策略行为

#### Figure 6: 外部扰动与自主重试

![Figure 6](https://arxiv.org/html/2410.21845v3/fig5.png)

**说明**：移动主板、强制张开夹爪、改变皮带形变或制造坏抓取后，策略会重新对齐、重抓或重试。这些状态来自 RL 自主探索，不需要在演示中逐一列举。

#### 公式 10: [[Critical State|Q-value action sensitivity]]（论文 Eq. 4）

$$
\operatorname{Var}[Q(s,a)]
=\mathbb E_{\epsilon\sim\mathcal U[-c,c]}
\left[
\left(
Q(s,a+\epsilon)-
\mathbb E_{\epsilon\sim\mathcal U[-c,c]}[Q(s,a+\epsilon)]
\right)^2
\right]
$$

**含义**：对动作加均匀扰动后 Q 变化越大，该 state 越关键；论文用 $[-0.2,0.2]$ 噪声和 100 次 Monte Carlo samples 估计。

**符号说明**：$c$ 为扰动范围，$a$ 为当前 policy action。

#### Figure 7: “漏斗”形状态访问分布

![Figure 7](https://arxiv.org/html/2410.21845v3/figs/fig6.png)

**说明**：RAM insertion 的 RL state visitation 逐渐形成从随机初始位置收敛到目标的 funnel；高访问区域具有高 Q 与高 action sensitivity。HG-DAgger 分布更稀疏，缺少这种围绕关键轨迹的自主 robustification。

#### Figure 8: Reactive 与 Predictive policy

![Figure 8](https://arxiv.org/html/2410.21845v3/fig7.png)

**说明**：RAM insertion 的策略方差从接近目标前的高值快速降低，表现为视觉闭环修正；Jenga whipping 方差全程接近零，表现为高度一致的 open-loop dynamic motion。同一算法可通过交互自然形成两类控制行为。

### 完整复现配置（附录）

#### Figure 9: Motherboard assembly 硬件设置

![Figure 9](https://arxiv.org/html/2410.21845v3/figs/sup_motherboard_setup.png)

**说明**：Franka、主板工装、腕部/侧视相机和操作区域的相对布置；固定工装将研究重点放在视觉闭环插装而非移动底座定位。

#### Figure 10: RAM insertion 的 policy 输入

![Figure 10](https://arxiv.org/html/2410.21845v3/figs/sup_ram_cropped_image.png)

**说明**：两路腕部裁剪图提供插槽与 RAM 的近场视角，配合 pose、velocity 和 force/torque。

#### Table 2: RAM insertion 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, tcp_pose, tcp_vel, tcp_f/t |
| Action space | 6D twist |
| Reward function | Binary classifier |
| Classifier views | wrist_1, wrist_2 |
| Classifier accuracy | 97% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 100 environment steps |
| Reset method | Scripted reset |
| Randomization range | 4 cm in x and y, 6° in rz |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 32,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 11: SSD assembly 的 policy 输入

![Figure 11](https://arxiv.org/html/2410.21845v3/figs/sup_ssd_cropped_image.png)

**说明**：两路腕部加一路侧视裁剪图，用于观察 SSD 与插槽的相对姿态及接触过程。

#### Table 3: SSD assembly 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, side_2, tcp_pose, tcp_vel, tcp_f/t |
| Action space | 6D twist |
| Reward function | Binary classifier |
| Classifier views | wrist_1, wrist_2, side_2 |
| Classifier accuracy | 95% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 100 environment steps |
| Reset method | Scripted reset |
| Randomization range | 2 cm in x and y, 1° in rz |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 21,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 12: USB grasp-insertion 的 policy 输入

![Figure 12](https://arxiv.org/html/2410.21845v3/figs/sup_usb_insert_cropped_image.png)

**说明**：腕部与侧视图同时覆盖 free-floating USB、抓取姿态和插槽，policy 还接收 gripper position。

#### Table 4: USB grasp-insertion 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, side_1, tcp_pose, tcp_vel, tcp_f/t, gripper_pos |
| Action space | 6D twist + 1D discrete gripper control |
| Reward function | Binary classifier |
| Classifier views | side_1 |
| Classifier accuracy | 96% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 120 environment steps |
| Reset method | Scripted reset |
| Randomization range | 2 cm in x and y, 10° in rz |
| Proprio encoder size | 64 |
| Motion policy MLP size | 256×256 |
| Grasp critic MLP size | 256×256 |
| Total RL transitions | 50,000 |
| Discount factor | 0.98 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 13: Cable clipping 的 policy 输入

![Figure 13](https://arxiv.org/html/2410.21845v3/figs/sup_usb_route_cropped_image.png)

**说明**：腕部近场图展示线缆与紧配 clip，任务同时需要连续末端运动和离散夹爪控制。

#### Table 5: Cable clipping 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, tcp_pose, tcp_vel, tcp_f/t, gripper_pos |
| Action space | 6D twist + 1D discrete gripper control |
| Reward function | Binary classifier |
| Classifier views | wrist_1, wrist_2 |
| Classifier accuracy | 97% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 120 environment steps |
| Reset method | Human reset |
| Randomization range | 4 cm in x and y, 10° in rz |
| Proprio encoder size | 64 |
| Motion policy MLP size | 256×256 |
| Grasp critic MLP size | 256×256 |
| Total RL transitions | 28,000 |
| Discount factor | 0.98 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 14: IKEA assembly 硬件设置

![Figure 14](https://arxiv.org/html/2410.21845v3/figs/sup_ikea_setup.png)

**说明**：双臂分别装配侧板，再共同安装顶板；多个侧视相机覆盖不同接触区域。

#### Table 6: IKEA side panels 训练配置

| Parameter | Value |
|---|---|
| Observation space for side panel 1 | wrist_1, side_1, side_2, tcp_pose, tcp_vel, tcp_f/t |
| Observation space for side panel 2 | wrist_2, side_3, side_4, tcp_pose, tcp_vel, tcp_f/t |
| Action space | 12D twist |
| Reward function | Binary classifier |
| Classifier views for panel 1 | side_1, side_2 |
| Classifier views for panel 2 | side_3, side_4 |
| Classifier accuracy | 97% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 100 environment steps |
| Reset method | Scripted reset |
| Randomization range | 8 cm in x and y, 1° in rz |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions for panel 1 | 31,000 |
| Total RL transitions for panel 2 | 36,000 |
| Discount factor | 0.98 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Table 7: IKEA top panel 训练配置

| Parameter | Value |
|---|---|
| Observation space | side_1, side_3, side_4, tcp_pose, tcp_vel, tcp_f/t |
| Action space | 12D twist |
| Reward function | Binary classifier |
| Classifier views | side_1, side_3, side_4 |
| Classifier accuracy | 95% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 150 environment steps |
| Reset method | Scripted reset |
| Randomization range | 3 cm in x and y |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 18,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 15: Dashboard assembly 硬件设置

![Figure 15](https://arxiv.org/html/2410.21845v3/figs/sup_dashboard_setup.png)

**说明**：两臂共同抓持 dashboard component，对齐多个 pins 和 slots，属于长接触序列与双臂协调任务。

#### Figure 16: Dashboard assembly 的 policy 输入

![Figure 16](https://arxiv.org/html/2410.21845v3/figs/sup_dash_cropped_image.png)

**说明**：双腕部与侧视裁剪图用于识别多点接触、卡住和重新接近目标的状态。

#### Table 8: Dashboard assembly 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, side, tcp_pose, tcp_vel, tcp_f/t, gripper_pos |
| Action space | 12D twist + 1D discrete gripper control |
| Reward function | Binary classifier |
| Classifier views | wrist_1, wrist_2, side |
| Classifier accuracy | 98% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 200 environment steps |
| Reset method | Human reset |
| Randomization range | 2 cm in x and y |
| Proprio encoder size | 64 |
| Motion policy MLP size | 256×256 |
| Grasp critic MLP size | 256×256 |
| Total RL transitions | 36,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 17: Object handover 硬件设置

![Figure 17](https://arxiv.org/html/2410.21845v3/figs/sup_handover_setup.png)

**说明**：双臂需要协调交接时机与两个离散夹爪状态；环境没有位置随机化。

#### Figure 18: Object handover 的 policy 输入

![Figure 18](https://arxiv.org/html/2410.21845v3/figs/sup_handover_cropped_image.png)

**说明**：两路腕部加侧视相机覆盖交接双方的相对姿态和物体是否稳定夹持。

#### Table 9: Object handover 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, side, tcp_pose, tcp_vel, gripper_pos |
| Action space | 12D twist + 1D discrete gripper control |
| Reward function | Binary classifier |
| Classifier views | side |
| Classifier accuracy | 99% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 200 environment steps |
| Reset method | Human reset |
| Randomization range | None |
| Proprio encoder size | 64 |
| Motion policy MLP size | 256×256 |
| Grasp critic MLP size | 256×256 |
| Total RL transitions | 43,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 19: Timing-belt assembly 硬件设置

![Figure 19](https://arxiv.org/html/2410.21845v3/figs/sup_timing_belt_setup.png)

**说明**：双臂同时控制 tensioner 与柔性皮带，需要根据形变连续调整接触模式，是全套任务中训练时间最长的一项。

#### Figure 20: Timing-belt assembly 的 policy 输入

![Figure 20](https://arxiv.org/html/2410.21845v3/figs/sup_timing_belt_cropped_image.png)

**说明**：双腕部和双侧视图覆盖皮带形状、轮系与两个末端执行器。

#### Table 10: Timing-belt assembly 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist_1, wrist_2, side_1, side_2, tcp_pose, tcp_vel, tcp_f/t |
| Action space | 12D twist |
| Reward function | Binary classifier |
| Classifier views | side_1, side_2 |
| Classifier accuracy | 96% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 200 environment steps |
| Reset method | Human reset |
| Randomization range | 2 cm in x and y |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 108,000 |
| Discount factor | 0.97 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 21: Jenga whipping 硬件设置

![Figure 21](https://arxiv.org/html/2410.21845v3/figs/sup_jenga_setup.png)

**说明**：末端固定 whip，以 feedforward wrench 产生高速动态动作；由于实时干预不适合该任务，使用 30 条 offline demos 启动。

#### Figure 22: Jenga whipping 的 policy 输入

![Figure 22](https://arxiv.org/html/2410.21845v3/figs/sup_jenga_cropped_image.png)

**说明**：腕部与侧视图观察目标积木及塔状态，policy 另接收末端与关节位置/速度。

#### Table 11: Jenga whipping 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist, side, tcp_pose, tcp_vel, q, dq |
| Action space | Feedforward wrench $F_x,F_z,\tau_z$ |
| Reward function | Human annotation at episode end |
| Environment update frequency | 10 Hz |
| Max episode length | 20 environment steps |
| Reset method | Human reset |
| Randomization range | None |
| Initial offline demonstrations | 30 |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 10,000 |
| Discount factor | 0.96; every episode runs to maximum length |
| Optimizer | Adam |
| Learning rate | 3e-4，达到 70% SR 后降到 3e-5 |
| Image augmentation | Random crop |

#### Figure 23: Object flipping 硬件设置

![Figure 23](https://arxiv.org/html/2410.21845v3/figs/sup_object_flipping_setup.png)

**说明**：锅固定在末端，物体初始位置随机；策略需要先调整物体位置，再执行一致的动态翻转。

#### Figure 24: Object flipping 的 policy 输入

![Figure 24](https://arxiv.org/html/2410.21845v3/figs/sup_egg_flip_cropped_image.png)

**说明**：腕部与侧视图提供物体朝向、锅内位置和翻转结果。

#### Table 12: Object flipping 训练配置

| Parameter | Value |
|---|---|
| Observation space | wrist, side, tcp_pose, tcp_vel, q, dq |
| Action space | Feedforward wrench $F_x,F_z,\tau_y$ |
| Reward function | Binary classifier |
| Classifier views | wrist |
| Classifier accuracy | 97% |
| Initial offline demonstrations | 20 |
| Environment update frequency | 10 Hz |
| Max episode length | 100 environment steps |
| Reset method | Scripted reset |
| Randomization range | None |
| Proprio encoder size | 64 |
| Policy MLP size | 256×256 |
| Total RL transitions | 25,000 |
| Discount factor | 0.985 |
| Optimizer | Adam |
| Learning rate | 3e-4 |
| Image augmentation | Random crop |

#### Figure 25: Reward classifier 训练样本

![Figure 25](https://arxiv.org/html/2410.21845v3/classifier_2.png)

**说明**：RAM 插装的 positive/negative 图像包含不同插入深度和视角；作者会额外收集 potential false-positive/false-negative states，使各任务 classifier accuracy 达 95–99%。

#### Table 13: Diffusion Policy baseline 配置

| Task | Demos | Observation chunks | Prediction horizon | Executed action chunks |
|---|---:|---:|---:|---:|
| RAM Insertion | 200 | 1 | 8 | 2 |
| Dashboard Assembly | 200 | 1 | 8 | 4 |
| Object Flipping | 200 | 1 | 1 | 1 |

**说明**：作者针对每项任务选择实验中最优 chunking；即便使用 200 demos，DP 在三项任务上仍明显低于 HIL-SERL，说明主要瓶颈不是动作多模态，而是闭环纠错和 reward-directed improvement。

#### Figure 26: 全任务训练曲线

![Figure 26](https://arxiv.org/html/2410.21845v3/sup_policy_training.svg)

**说明**：附录汇总所有任务的 success、cycle time 和 intervention rate。整体趋势支持“人工需求随策略成熟下降”，但不同任务的数据量从 10k 到 108k transitions，复杂度差异很大。

---

## 批判性思考

### 优点

1. 贡献是完整系统而非孤立算法：reward、数据、控制、安全、并行采集和人机协作细节都给出。
2. 对人工预算进行了较公平的 HG-DAgger 对照，并报告成功率、节拍和 intervention rate 三个互补指标。
3. 任务物理性质跨度大，证明 model-free RL 并非只能解决短程抓取；“漏斗”与 reactive/predictive 分析也比只报成功率更有解释力。

### 局限性

1. 每个任务仍需 reward classifier、相机裁剪、reset、低层 controller 和独立训练，工程泛化不等于任务零样本泛化。
2. 人类需要在训练中持续观察并判断何时接管；论文没有报告 operator time、反应延迟或不同 operator 的方差。
3. 环境随机化有限，未验证非结构化场景；训练出的 policy 是 task-specific ResNet+MLP，而不是语言条件 generalist。
4. “近乎所有任务 1–2.5 小时”有 timing-belt 6 小时例外，且训练时间包含大量人工 reset/监督。
5. 长 horizon 仍未解决；IKEA 采用分阶段策略，论文明确把更长 horizon 列为未来工作。
6. 二值 reward classifier 的 false positive 是潜在致命风险；只报告分类 accuracy 不能完全刻画 online distribution 下的 reward hacking。

### 潜在改进方向

1. 用 [[VLA]] 或 pretrained value model 替代小 ResNet policy/value initialization，让不同任务共享视觉、语言和动作先验。
2. 学习 intervention policy 或 uncertainty trigger，降低人类持续监控成本，并把人工接管限制在真正高风险状态。
3. 把成功 specialist 的恢复数据按 [[PLD]] 方式蒸馏回 generalist，形成“人工启动 → 自动练习 → 数据回灌”的闭环。
4. 为 reward classifier 加 conservative threshold、OOD detection 和人工复核，区分“任务成功”与“分类器被欺骗”。
5. 用 action chunking 或 hierarchical skill decomposition 降低 50 Hz/长 horizon 的信用分配难度。

### 可复现性评估

- [x] 代码开源
- [ ] 官方预训练 checkpoint 完整覆盖全部任务
- [x] 每任务 observation/action/reward/reset/transition 数量公开
- [x] 主要训练算法和控制表示公开
- [ ] 原始真机数据集完整公开

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
- [[RLPD]]：offline demonstrations 与 online data 等量回放的 off-policy RL 基础。
- [[Soft Actor-Critic]]：entropy-regularized Gaussian actor。
- [[HG-DAgger]]：人工 takeover 数据收集范式，但 HIL-SERL 用 RL 而非纯监督更新。

### 对比
- [[PLD]]：把持续人工 intervention 换成 VLA prior + residual recovery，并把 specialist 数据蒸馏回 VLA。
- [[RLT]]：继承真机 off-policy actor-critic 思路，但使用 VLA representation 与 action chunks。
- [[Pi06]]：用大规模 value model 和 advantage-conditioned SFT 处理 generalist VLA 的经验学习。

### 方法相关
- [[Human-in-the-Loop Reinforcement Learning]]：人类在关键状态短暂接管。
- [[Reward Classifier]]：任务专用稀疏奖励。
- [[Off-policy Actor-Critic]]：允许复用 demo、干预和历史 online 数据。
- [[Replay Buffer]]：demo/RL 双 buffer。
- [[Impedance Control]]：接触任务的安全低层控制。

### 硬件/数据相关
- Franka Emika Panda：单臂与双臂真机平台。
- SpaceMouse：人工介入输入设备。

---

## 速查卡片

> [!summary] HIL-SERL
> - **核心**：人类只在关键失败状态接管，RLPD 用 task reward 判断并吸收纠错，最终自主策略超过演示成功率与速度。
> - **方法**：ResNet-10 + RLPD + demo/online 双 buffer + reward classifier + SpaceMouse intervention + impedance control。
> - **结果**：13 个任务/子任务接近或达到 100%；平均 BC 49.7→100，cycle time 9.6s→5.4s。
> - **代码**：[rail-berkeley/hil-serl](https://github.com/rail-berkeley/hil-serl)

---

*笔记创建时间: 2026-10-28*
