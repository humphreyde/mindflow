---
type: paper
arxiv_id: 2610.09117
source_vault: notes
source_path: PaperNotes/VLA/Workhorse.md
date_migrated: 2026-11-03
title: "Workhorse: Learning Robust Whole-Body Humanoid Loco-Manipulation from Human Data"
method_name: "Workhorse"
authors: [Songbo Hu, Qiayuan Liao, Yufeng Chi, Kevin Zakka, Yakun Sophia Shao, Pieter Abbeel, Koushil Sreenath]
year: 2026
venue: arXiv
tags: [humanoid-robot, loco-manipulation, whole-body-control, imitation-learning, flow-matching, human-demonstration, cross-embodiment]
zotero_collection: VLA
image_source: local
arxiv_html: https://arxiv.org/html/2610.09117v2
code_url:
code_companion:
created: 2026-10-14
---

# 论文笔记：Workhorse

## 元信息

| 项目 | 内容 |
|---|---|
| Authors | Songbo Hu、Qiayuan Liao、Yufeng Chi、Kevin Zakka、Yakun Sophia Shao、Pieter Abbeel、Koushil Sreenath |
| 机构 | University of California, Berkeley |
| 日期 | October 8, 2026（v2） |
| 项目主页 | [Workhorse](https://hybridrobotics.github.io/workhorse/) |
| 链接 | [arXiv](https://arxiv.org/abs/2610.09117) / [HTML](https://arxiv.org/html/2610.09117v2) / [PDF](https://arxiv.org/pdf/2610.09117) |

> [!info] 作者说明
> 论文明确标注 Songbo Hu 与 Qiayuan Liao 为共同一作。作者总数少于 20，因此按本库规则保留全部 7 位作者；未自行推断通讯作者或 project leader。

---

## 一句话总结

> Workhorse 用无机器人参与的人类五链路示范，训练视觉规划器与强化学习全身跟踪器，使人形机器人完成动态、接触丰富且可抗扰动的全身移动操作。

---

## 核心贡献

1. **机器人无关的人类数据采集**：以 5 个 HTC Vive tracker 和胸前相机同步记录躯干、双腕、双脚与第一视角视频，不要求机器人在采集环路中。
2. **五链路分层接口**：视觉规划器和全身跟踪器共享任务空间中的 [[Five-Link Interface|五链路接口]]，二者直接用同一份人类运动训练，无需先把示范重定向为机器人关节轨迹。
3. **面向闭环误差的协同增强**：规划器学习处理跟踪误差和推力造成的历史漂移，跟踪器学习处理规划命令在重规划间的漂移与跳变。
4. **动态全身能力与闭环仿真评测**：在 Unitree G1 上展示搬箱、空中接箱和推倒/攀爬行李箱，并在重建房间内量化成功率、抗扰性与跨本体迁移。

---

## 问题背景

### 要解决的问题

人形机器人已经能跟踪给定的全身参考运动，但在真实操作任务中，机器人还必须从自身的第一视角 RGB 与 [[Proprioceptive State|本体状态]]出发，**自己规划**何时走、蹲、伸手、踢、支撑和攀爬。难点不只是动作精度，还包括动态平衡、接触切换、长时序误差累积、物体变化和外力扰动后的恢复。

#### Figure 1: Workhorse 的全身移动操作能力

![[Papers/assets/Workhorse/Workhorse_fig1.png]]

**说明**：机器人把手、脚和身体支撑统一用于任务：双手搬运前两个箱子、用脚把第三个箱子踢入底层；在约 0.56 s 的飞行时间内接住箱子；推动并放倒 14 kg 行李箱，再爬上 0.39 m 高的平台取物。这些行为体现的是 [[Loco-Dexterous Manipulation|全身移动操作]]，而不是“先走到位、再固定双脚做手臂操作”。

### 现有方法的局限

- **运动跟踪器缺少上层参考**：已有 [[Whole-Body Control|全身控制]]通常假设参考轨迹已经给定，不能直接从视觉决定如何完成操作。
- **机器人遥操作成本高**：每条示范都需要目标机器人和熟练操作者，硬件更换后数据与控制接口往往不能复用。
- **机器人外的人体数据常依赖重定向**：把人体动作转成关节角会引入特定本体假设，也会改变原始示范。
- **动态性与恢复不足**：不少工作主要让脚承担行走，不把脚作为主动操作工具，并且较少测试外力、物体被移走等闭环扰动。

### 本文的动机

作者选择一个介于高层任务语义和低层关节控制之间的接口：躯干、双腕、双脚五个关键 link 的位姿。该接口保留了走、蹲、伸手、踢和踩踏所需的任务空间结构，又不绑定某个机器人的关节定义。视觉规划器负责从观测预测五链路动作块，RL 跟踪器负责把它落实为可平衡的关节 setpoints。

---

## 核心技术

### 数据与数据处理

#### Figure 3: 人类示范采集与跨设备同步

![[Papers/assets/Workhorse/Workhorse_fig3.png]]

**说明**：胸前相机支架、双手背和双鞋面各安装一个 HTC Vive tracker；4 个 Lighthouse 基站在 $5\,\mathrm{m}\times5\,\mathrm{m}$ 范围内以 60 Hz 给出同一重力对齐世界坐标系中的位姿。胸前 DJI Osmo Action 4 以 30 fps 记录 $129^\circ$ 近鱼眼视频。实时 IK 预览只用于发现不可达手部姿态并让示范者重做，不会把 IK 关节轨迹当作策略训练目标。

数据处理流程如下：

1. 每次 repetition 前做 T-pose，用于切分连续录制；每个 session 开头拍手三次。
2. 用双手 tracker 的距离与速度计算 clap score，与相机音频的 spectral-flux onset 对齐；对齐后两路时间残差为 **5.5 ms**。
3. tracker 位姿由 60 Hz 重采样到 50 Hz，短暂丢失的样本插值；30 fps 图像按时间戳选取。
4. 采集时改变光照、物体摆放并扰动物体，但不推搡示范者，因此人体轨迹都表示意图动作，而非外力恢复动作。

| 任务 | 人类示范时长 | 关键行为 |
|---|---:|---|
| 箱子搬运 | 2.2 h | 双手抓取、搬运、摆放和脚踢 |
| 行李箱 | 1.2 h | 推动、放倒、踩踏攀爬和跳下 |
| 空中接箱 | 13 min | 对抛掷时机与轨迹做快速反应 |

全部数据由**一名示范者、在同一房间内**采集，这是后续评估外推能力时的重要证据边界。

### 五链路接口与跨本体表示

五个 link 分别是 torso、left/right wrist、left/right foot。tracker 测得的姿态通过每个 link 的固定 mount calibration 转为机器人 link 目标，不做人体尺度缩放，也不求一条连续的机器人关节轨迹。

#### 公式 1: [[Five-Link Interface|人体 tracker 到机器人五链路目标的刚体变换]]

$$
{}^{W}\mathbf{T}_{L_b}(t)
=
{}^{W}\mathbf{T}_{K_b}(t)
{}^{K_b}\mathbf{T}_{A_b}
\left({}^{L_b}\mathbf{T}_{A_b}\right)^{-1}
$$

**含义**：把 tracker 在世界系中的实测位姿，通过人体 tracker frame 与机器人 link frame 各自到 alignment frame 的固定标定关系，转换成机器人 link $L_b$ 应达到的世界位姿。它只是刚体 offset，而不是 [[Motion Retargeting|动作重定向]]。

**符号说明**：

- $b$：五个 link 之一；
- $W$：重力对齐的固定世界坐标系；
- $K_b$：安装在人体上的 tracker 坐标系；
- $L_b$：目标机器人的对应 link 坐标系；
- $A_b$：对齐坐标系；torso 位于相机、wrist 位于掌心、foot 位于脚底中心；
- ${}^{X}\mathbf{T}_{Y}$：坐标系 $Y$ 在坐标系 $X$ 中的刚体位姿。

#### Figure 4: 同一五链路运动作用于 G1 与 H2

![[Papers/assets/Workhorse/Workhorse_fig4.png]]

**说明**：图中只为可视化而用 IK 把同一人体五链路姿态投到 Unitree G1 和 H2 上；真正训练目标仍是人体测得的五个任务空间位姿。换本体时只需重新测量 5 个 mount、替换仿真/渲染中的机器人并重新训练两层策略。H2 的体型更接近人类，因此更容易达到未缩放的人体目标，但这仍不是零样本策略迁移。

### 分层模型架构

#### Figure 2: Visual Planner + Whole-Body Tracker

![[Papers/assets/Workhorse/Workhorse_fig2.png]]

**说明**：Workhorse 由两个分开训练、异频运行的策略组成。5 Hz visual planner 读取第一视角 RGB 和机器人五链路历史，输出未来五链路 action chunk；50 Hz whole-body tracker 读取 chunk 的短时窗口和本体状态，输出关节 setpoints。虚线表示训练时两者都直接读取相同的人体五链路运动，部署时才真正闭环串联。

#### Visual Planner

- **视觉历史**：4 张图像，相邻图像间隔 0.24 s；每张图由从头训练的 ResNet-18 编码为一个 token。
- **五链路历史**：9 帧，相邻帧间隔 0.12 s；位姿由位置与 6D rotation 表示，并附加 [[Projected Gravity|投影重力]]和世界系 torso 高度。
- **生成模型**：[[Flow Matching|flow-matching]] policy，以 [[DiT|Diffusion Transformer]] 为 backbone，通过 cross-attention 读取图像与历史 token。
- **输出**：58 帧五链路目标，步长 $\Delta t=0.02\,\mathrm{s}$，覆盖 1.16 s。
- **推理**：10 步 Euler 积分，5 Hz 重规划。

#### Whole-Body Tracker

跟踪器是建立在 BeyondMimic 上的强化学习策略。它在 50 Hz 控制时刻读取当前到未来 0.2 s 的 6 个 command samples（相邻 0.04 s），再结合 IMU 角速度、关节位置/速度和上一时刻关节 setpoints，输出新的关节 setpoints。命令会变换到当前 torso frame，从而不需要外部定位。

#### Table I: Whole-Body Tracker 的奖励核

| 类别 | Kernel | Frame | Width $\sigma$ |
|---|---|---|---|
| Style | Pelvis attitude | world | 0.4 rad |
| Style | Link pose, all 14 | pelvis xy, yaw | 0.3 m, 0.4 rad |
| Style | Link velocity, all 14 | world | 1 m/s, 3.14 rad/s |
| Task | Torso, wide | world | 0.3 m, 0.4 rad |
| Task | Torso, narrow | world | 0.06 m, 0.15 rad |
| Task | Wrists | world | 0.06 m, 0.15 rad |
| Task | Feet | torso | 0.06 m, 0.1 rad |
| Task | Swing-foot clearance, 10 cm | height | 0.035 m |

**说明**：各 Gaussian kernel 权重均为 1，另外减去 joint-setpoint rate 与关节限位惩罚。14-link style reward 维持自然全身姿态；world-frame torso/wrist reward 强调操作精度；torso-frame foot reward允许为平衡调整落脚；swing-foot clearance 鼓励示范脚处于摆动期时脚踝达到 10 cm 高度。

### 训练：用增强模拟两层策略的闭环误差

#### Person-to-Robot 图像编辑

训练图像里是人，部署相机却会看到机器人自身。作者离线使用 SAM 3 分割人和搬运物，LaMa 移除人体，MoGe-2 估计带尺度深度，再按示范姿态渲染机器人并做深度合成。

#### Figure 5: 规划器图像编辑与增强

![[Papers/assets/Workhorse/Workhorse_fig5.png]]

**说明**：第一行展示“移除人 → 渲染机器人”；第二行是亮度、空间光照梯度与对比度增强；第三行把五链路历史施加的相机漂移转换成与深度有关的 image warp。图像和状态由同一随机漂移共同变换，避免产生互相矛盾的训练对。

#### Planner augmentation 与 tracker command augmentation

#### Figure 6: 两层策略各自看到的漂移

![[Papers/assets/Workhorse/Workhorse_fig6.png]]

**说明**：规划器的五链路历史从当前 $t_0$ 向过去做随机游走，但监督 chunk 保持干净；同时对每个 link 叠加较小独立随机游走、同步 warp 图像，并随机 mask history samples/links。跟踪器则在每次 0.2–1 s 的随机 replanning 时把 drift 清零，随后令命令线性漂移，最大达到 10 cm 水平平移与 $10^\circ$ yaw，模拟真实 planner/state-estimator/tracker 组合产生的“漂移后跳回”。

规划器增强教上层从执行偏差和推力后的状态继续规划；command augmentation 则教下层处理迟到、漂移和跳变的命令。它们不是端到端联合训练，而是用**对方在部署时可能产生的误差分布**连接两个独立训练过程。

#### Tracker 训练

每个 episode 从带随机扰动的 IK pose 起步，起始示范时刻由 BeyondMimic 的 adaptive sampler 选择；训练中随机化质量、摩擦、encoder bias 与脚底几何。搬箱时仿真用最高 40 N 的弹簧把双腕向外推，以替代示范中缺失的箱体接触力；行李箱任务则显式模拟箱体。作者沿 SuperMimic 路线，用 mjlab transitions 拟合 dynamics network，再在其预测 rollout 上训练 actor 与 critic。每个任务、每种机器人本体各自训练一个 tracker。

### 推理与部署

#### Figure 7: 异步延迟、时间戳与 action chunk 对齐

![[Papers/assets/Workhorse/Workhorse_fig7.png]]

**说明**：最新图像的采集时刻为 $t_0$，planner 完成推理、chunk 到达 tracker 时，前几个 action 已经过期。系统给相机、状态估计和 chunk action 统一打描述时刻的时间戳，跳过过期 action，并在当前命令窗口的 6 个采样时刻做 position linear interpolation 与 rotation SLERP。

连续两个 [[Action Chunking|action chunk]] 的重叠区可能不一致。Workhorse 采用 [[Real-time Action Chunking|RTC]]：先把上一 chunk 的重叠动作变换到新 $t_0$ 的 torso frame，再在新 chunk 的 flow integration 中将其作为已知部分 inpaint，使新旧规划平滑衔接。这样 5 Hz planner 能与 50 Hz tracker 异步协同，即使 chunk 迟到也不必暂停控制。

---

## 实验

### 实验设置

真实机器人实验使用 Unitree G1，只展示能力和闭环恢复案例，**不报告真实机器人成功率**。规划器运行于外部 laptop，tracker 在机器人 onboard 运行；机器人只使用一个第一视角 RGB 相机与自身本体感知，无外部 tracking。

量化实验在示范房间的仿真重建中进行：

- 用 Polycam 扫描房间为 3D Gaussian Splat 背景，mjlab/MuJoCo 模拟机器人和箱子；
- 约 15% planner 训练数据来自重建房间，以减小渲染外观差距；
- 每个变体分别运行 100 个无推力 episode 和 100 个有推力 episode；
- 任务时限 120 s；起点和 3 个箱子位姿随机，其余外观、光照、摩擦和质量固定；
- 推力为作用于 pelvis 的 $40\,\mathrm{N\!\cdot\!s}$ impulse：40 N 持续 1 s，每 5–10 s 随机方向施加一次。

#### Figure 9: 重建房间中的 G1/H2 闭环评测

![[Papers/assets/Workhorse/Workhorse_fig9.png]]

**说明**：Gaussian-splat 背景与物理仿真的机器人/箱子按真实胸前相机内参与分辨率合成，planner 直接接收第一视角图像。H2 也使用同一份人体示范重新训练 planner 和 tracker；无推力时完成率为 83/100，对应 G1 为 77/100，两者差异小于约 $\pm11$ percentage points 的两比例差 95% 区间，不能据此断言 H2 显著更优。

### 真实机器人定性结果

#### Figure 8: 搬箱过程中的扰动恢复

![[Papers/assets/Workhorse/Workhorse_fig8.png]]

**说明**：在一次连续运行中，机器人处理箱子被推离手臂、躯干被踢、伸手时箱子被拿走并再次被踢、行走中受推、手中箱子被夺走并丢开、下蹲时背部受压等六类扰动。示范数据只扰动物体、从不推人，因此推力恢复不是对相同恢复轨迹的直接模仿，而是 planner 的视觉闭环与 tracker 的抗扰共同产生的行为。

### 消融实验

#### Table II: 重建房间中 box transport 的完整消融结果

| 方法 | 无推力 ≥1 | 无推力 ≥2 | 无推力 Success | 无推力 Fall | 有推力 ≥1 | 有推力 ≥2 | 有推力 Success | 有推力 Fall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Ours (full system)** | 91 | **84** | **77** | **1** | 86 | **68** | **64** | 15 |
| Joint command [7] | 73 | 58 | 54 | **1** | 86 | 50 | 42 | **4** |
| Link-local action frame | 34 | 9 | 5 | 77 | 21 | 5 | 4 | 91 |
| w/o projected gravity | 24 | 5 | 1 | 97 | 13 | 2 | 1 | 99 |
| w/o planner augmentation | 36 | 25 | 20 | 79 | 7 | 1 | 0 | 95 |
| w/o command augmentation | **93** | 77 | 76 | 4 | **98** | 67 | 52 | 23 |

**说明**：数值均为 100 个 episode 的百分比。≥1/≥2 表示至少放置 1/2 个箱子；Success 表示 120 s 内放完 3 个箱子且未跌倒。无推力下 full system 成功率为 77%，有推力为 64%；100 次试验中，77% 附近比例的 95% 二项区间约为 $\pm8$ percentage points。

**关键发现**：

1. **共享 torso frame 是关键表示选择**：link-local action frame 几乎失效（5%/4%），说明五个目标必须共同表达身体几何，而不能让每个 link 只看自己的局部增量。
2. **投影重力提供不可替代的姿态信息**：删除它和 torso height 后成功率均为 1%，跌倒率接近 100%；图像无法可靠补足身体倾斜和高度。
3. **planner augmentation 决定闭环可用性**：删除后有推力成功率为 0%，说明离线“干净历史 → 干净动作”训练不足以承受执行误差累积。
4. **command augmentation 主要改善抗扰**：无推力从 77% 到 76% 几乎不变，有推力则从 64% 降至 52%，跌倒率从 15% 升至 23%。
5. **joint command 更少跌倒但任务成功更低**：在线 IK 输出总是可达，可能降低跌倒率；但奇异点与转换误差损害任务完成。论文没有把“少跌倒”与“高任务成功”混为同一指标。

---

## 批判性思考

### 优点

1. **接口设计克制而有效**：五链路表示足以覆盖手、脚、躯干协同，又避免了 robot-specific joint retargeting。
2. **真正处理分层闭环的 distribution shift**：两种 augmentation 对应 planner 与 tracker 互相制造的误差，消融也显示它们不是装饰性技巧。
3. **脚是操作器而非纯移动器官**：踢箱、抵住行李箱、踩踏和跳下把 humanoid whole-body manipulation 的能力边界推进到动态接触。
4. **评测边界表达相对清楚**：作者明确区分真实机器人定性 capability 和仿真成功率，并为有限 episode 数量给出区间量级。

### 局限性

1. **任务专用而非通用 policy**：三个任务各自训练 planner 和 tracker，不能从一条语言指令组合新任务。
2. **数据域很窄**：单一示范者、单一房间、合计约 3.6 h 数据；真实与仿真测试也没有离开该房间。
3. **真实机器人没有统计评测**：77%/64% 等成功率均来自重建房间仿真，且外观、光照、质量和摩擦固定，不能直接等同于现实可靠性。
4. **抗扰仍有限**：有推力仿真中成功率只有 64%，跌倒率 15%。
5. **跨本体不是零样本**：H2 需要重新渲染并重新训练 planner 和 tracker，论文证明的是接口与数据的可复用性，而非单个模型直接适配新机器人。
6. **五链路表达不含手指/夹爪和头部**：难以覆盖灵巧手内部状态与主动视角控制。
7. **固定基站限制采集范围**：Lighthouse 将人体示范限制在一个房间，削弱了 in-the-wild 可扩展性。
8. **代码、数据和模型尚未公开**：目前无法独立复现图像编辑、增强幅度、RL 训练和 sim reconstruction 的全部细节。

### 潜在改进方向

1. 训练跨任务或语言条件的共享 planner，在保留 task-specific tracker 稳定性的同时提升任务组合能力。
2. 引入多示范者、多房间、移动式无基站动捕和更丰富物体域，验证接口能否吸收广域人体数据。
3. 在五链路接口上增加 gripper/dexterous-hand state 与可控 head/neck，使手指操作和主动感知进入统一规划。
4. 把 planner 的不确定性或可达性反馈显式送给 tracker/重规划器，减少不可实现 chunk 导致的跌倒。
5. 在真实机器人上报告固定 protocol 的成功率、扰动强度、置信区间和失败类别，并加入跨房间测试。

### 可复现性评估

- [ ] 代码开源
- [ ] 预训练模型
- [ ] 训练数据可获取
- [x] 系统结构、频率与主要增强机制有说明
- [x] 仿真评测 protocol 和完整消融结果已报告
- [ ] 足以独立复现 RL、图像编辑和数据增强的全部超参数

### 个人笔记

<!-- 本节留给用户手写。除非用户明确要求，否则不要代写或删除这些提示。 -->

> [!note] 我的记录
> - 与当前研究的联系：
> - 值得复现或验证：
> - 尚未理解的问题：
> - 其他：

---

## 关联笔记

### 方法相关

- [[Loco-Dexterous Manipulation]]：任务类型；脚、手和躯干共同参与接触操作。
- [[Five-Link Interface]]：连接人体示范、视觉规划和机器人控制的共享任务空间表示。
- [[Whole-Body Control]]：把五链路目标落实为可平衡的关节 setpoints。
- [[Flow Matching]] / [[DiT]]：视觉规划器的动作块生成方式和 backbone。
- [[Action Chunking]] / [[Real-time Action Chunking]]：异频规划与高频控制之间的执行接口。
- [[Cross-embodiment Transfer]]：同一人体数据和接口迁移到 G1/H2，但需要按本体重新训练。

### 数据与状态相关

- [[Proprioceptive State]]：tracker 控制与 planner 历史的机器人自身状态来源。
- [[Projected Gravity]]：补足 torso-frame 表示缺失的机身倾角信息。
- [[Motion Retargeting]]：Workhorse 刻意避免先把人体动作转换成机器人关节轨迹。

---

## 速查卡片

> [!summary] Workhorse
> - **核心**：以 torso、双腕、双脚五链路作为人体示范到人形机器人之间的共享任务空间接口。
> - **方法**：5 Hz flow-matching visual planner + 50 Hz RL whole-body tracker，并以双方部署误差为训练增强。
> - **结果**：G1 完成动态搬运、接箱和攀爬；仿真 box transport 为 77%，40 N·s 推力下为 64%；H2 重训后为 83%。
> - **证据边界**：成功率来自单房间重建仿真；真实机器人只报告能力案例；代码尚未公开。

---

*笔记创建时间: 2026-10-14*
