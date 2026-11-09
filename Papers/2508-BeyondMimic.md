---
type: paper
title: "BeyondMimic: From Motion Tracking to Versatile Humanoid Control via Guided Diffusion"
authors: [Qiayuan Liao, Takara E. Truong, Xiaoyu Huang, Yuman Gao, Guy Tevet, Koushil Sreenath, C. Karen Liu]
institutes: [University of California Berkeley, Stanford University]
date_publish: 2025-08-11
venue: arXiv preprint
primary_domain: embodied-ai
domains: [embodied-ai]
tags: [legged, imitation-learning, diffusion-policy, RL]
review_status: reviewed
arxiv_id: 2508.08241
paper: https://arxiv.org/abs/2508.08241
website: https://beyondmimic.github.io/
github: https://github.com/HybridRobotics/whole_body_tracking
rating: 3
date_added: 2026-11-07
---

## Summary

> [!summary] BeyondMimic: From Motion Tracking to Versatile Humanoid Control via Guided Diffusion
> - **核心**: 用一套无需 motion-specific tuning 的 RL 配方训练高质量真机 motion trackers，再将选出的 trackers 蒸馏成 latent state–action diffusion model，通过 inference-time classifier guidance 组合技能并适配未训练任务。
> - **方法**: anchor-centered whole-body tracking reward、minimal domain randomization、adaptive sampling；随后用 DAgger VAE 压缩 tracker policy，以短时 state–latent trajectory diffusion 建模动作分布，并用可微 task cost 引导采样。
> - **结果**: 约 2.5 小时动作全部通过仿真验证，30 段共 15 分钟 motion 部署到 Unitree G1；用户研究中整体自然度偏好为 70.8%，并展示 joystick、waypoint、keyframe inpainting 和 obstacle avoidance。
> - **Sources**: [paper](https://arxiv.org/abs/2508.08241) | [website](https://beyondmimic.github.io/) | [github](https://github.com/HybridRobotics/whole_body_tracking)
> - **Rating**: 3 - Foundation（tracker formulation 已被 MJLab、Workhorse 等后续系统继承，并成为 humanoid motion tracking 的重要基础设施）

**Key Takeaways:**

1. **scalable 的准确含义是 one recipe per motion，不是一个 policy 覆盖全部动作**：每条或每段 motion 仍训练自己的 PPO policy；被消除的是 reward 与超参数的逐动作调节。
2. **sim-to-real 的关键不是无限增加 randomization，而是减少错误建模**：正确 armature、连续旋转表示、低控制延迟和适度 PD impedance 比堆叠 observation history 或广泛随机化更重要。
3. **guided diffusion 是短时 predictive control，不是长时语义规划**：模型预测约 0.64 秒 state–latent trajectory，再用手写 differentiable cost 在 denoising 中优化未来状态。
4. **unlabeled 不等于无任务先验**：训练轨迹不含 task label，但部署时仍要提供 joystick、waypoint、SDF 或 keyframe cost。
5. **论文影响主要来自 tracker，diffusion 部分证据与开源较弱**：官方仓只开放 motion-tracking training，完整 VAE、diffusion、guidance controller 和论文权重均未发布。

**Teaser. BeyondMimic 先把多套高质量 tracker 蒸馏进 latent space，再用 state–latent diffusion 和 test-time guidance 组合技能。**

![](https://arxiv.org/html/2508.08241v4/Fig7.png)

## 1. 问题定义：从“复现动作”到“按目标组合动作”

论文区分了两个问题：

1. 如何把 retargeted human motion 稳定地变成真机可执行的全身控制策略；
2. 如何在不为每个 downstream task 重新训练策略的情况下，组合已有动作并满足新的控制目标。

第一阶段追求的是 motion-agnostic training recipe。论文对 scalable motion tracking 的正式定义非常明确：**每条 motion 有自己的 policy，但所有 policy 共用同一个 MDP、reward、网络与训练超参数**。项目页进一步说明，LAFAN1 展示来自 14 条约 3 分钟序列训练出的多套 policies，而不是一个统一 policy。

第二阶段才训练 unified controller：选取多套 tracker，先蒸馏为连续 latent motor space，再训练 diffusion model 预测短时 state–latent trajectory。这样任务成本可以直接作用于 future state，而 decoder 把当前 latent 转回关节动作。

这使 BeyondMimic 位于两种传统路线之间：它保留 per-motion expert 的动作质量，又试图通过 diffusion 把专家集合变成可组合的统一 motor prior。

*来源定位：论文 Materials and Methods / Overview、Scalable Human Motion Tracking via RL；项目页 Policies trained with BeyondMimic pipeline on the LAFAN1 Dataset。*

## 2. Motion tracking：简单配方为什么能跨动作成立

### 2.1 Anchor-centered tracking

人形机器人受到扰动或 sim-to-real mismatch 后必然发生全局漂移。如果强制每个 body link 追踪世界坐标，策略会为了“回到原轨迹”做出不自然甚至不稳定的动作。

BeyondMimic 选定 torso/root 作为 anchor：

- anchor 可保留全局 position/orientation target；
- 其他 body 的目标位姿在当前 anchor-centered、yaw-aligned frame 中表达；
- body twist 继续追踪 reference velocity。

因此 policy 可以在整体平移或偏航后继续保持局部动作风格，而不是机械追回原始 mocap 世界坐标。

### 2.2 Compact reward

四类 task-space tracking score 使用统一 Gaussian kernel：

$$
r_{\text{task}}
=
\sum_{s\in\{\mathbf p,R,\mathbf v,\boldsymbol\omega\}}
\exp\Big(-\bar e_s/\sigma_s^2\Big).
$$

总 reward 只再加入三项 regularization：

$$
r
=
r_{\text{task}}
-\lambda_l r_{\text{limit}}
-\lambda_s r_{\text{smooth}}
-\lambda_c r_{\text{contact}}.
$$

它分别约束 joint limit、连续 action 的变化和 undesired self-contact。论文有意避免为不同运动引入专用 reward shaping。

### 2.3 Observation、action 与执行器建模

Actor 只接收单帧 robot-centric observation：motion phase、anchor pose error、IMU twist、joint position/velocity 和 previous action，不使用 history stacking。输出是 normalized joint setpoint，经低阻抗 PD 转成 torque；setpoint 是 torque-shaping 中间变量，而不是必须精确追踪的 kinematic plan。

作者的核心工程判断是：高 impedance 会压制自然动力学、放大噪声并降低碰撞顺应性。与其靠更强反馈掩盖误差，不如正确建模 armature、action scale、delay 和低层控制周期。

### 2.4 Minimal domain randomization 与 adaptive sampling

随机化只覆盖：

- ground friction / restitution；
- joint calibration offset；
- torso center-of-mass；
- 训练时的 velocity perturbation。

长序列按经验 failure rate 自适应采样。难片段先得到更多 reset probability；掌握后采样逐渐恢复均匀，从而避免容易片段消耗大部分 rollout。

**Figure 8. 关键 MDP 与 adaptive-sampling 消融。**

![](https://arxiv.org/html/2508.08241v4/Fig8.png)

最有信息量的消融不是 reward 数量，而是：

- Rot6D 优于 quaternion / axis-angle；
- observation history 反而恶化真机迁移；
- 错误 armature 导致 overswing 和 self-collision；
- 人为增加 2 ms delay 已提高 velocity error，5 ms 出现失败，10 ms 在 3 次中失败 2 次；
- 无 adaptive sampling 时，4 条 motion 中有 3 条在 30k iterations 后仍有失败片段。

*来源定位：论文 §Tracking Objective、§Rewards、§Observation and Action、§Domain Randomization、§Adaptive Sampling、§Validation of the method；Supplement S1–S2。*

## 3. 从专家策略到 latent state–action diffusion

### 3.1 DAgger VAE：先得到可解码的 motor latent

VAE encoder 读取 reference-motion components 和 anchor error，输出 latent motion intent；decoder 同时读取 latent 与最新 proprioception，重建 tracker action。训练采用 DAgger，而不是只模仿固定 expert rollout，因此 decoder 能在自身访问到的偏离状态上学习恢复。

这一拆分解决了两个问题：

- 原始 PD setpoint 带有尖锐 torque spike，不适合直接 diffusion；
- lightweight decoder 可以读取最新状态，避免整段 diffusion 推理造成 action lag。

### 3.2 State–latent trajectory model

作者 rollout VAE 并收集不含 reference information 的 state–latent trajectories。Diffusion 同时预测：

- 当前 character-yaw frame 下的 root trajectory；
- 各时刻 local root frame 下的 body features；
- 对应的 motor latent。

每个 state/latent timestep 有独立 noise level，因此同一个模型可以完成 history conditioning、future keyframe inpainting 和自由 trajectory generation。

为提高 offline diffusion 对执行偏差的恢复能力，数据收集时加入 temporally correlated Ornstein–Uhlenbeck action noise，形成围绕 clean rollout 的 error band。

### 3.3 Classifier guidance：任务只在推理时出现

对任意可微 task cost $G(\tau)$，conditional score 写成：

$$
\nabla_{\tau}\log p(\tau\mid\tau^*)
=
\nabla_{\tau}\log p(\tau)
-\nabla_{\tau}G(\tau).
$$

论文实现了三类代表性 cost：

- joystick：未来 planar root velocity 与 command 的平方误差；
- waypoint：远离目标时优化 position，接近目标后抑制 velocity；
- obstacle avoidance：对 body collision sphere 与 SDF 使用 relaxed barrier。

这些 cost 可以相加，因此 waypoint navigation 与 obstacle avoidance 可以在 inference time 组合，不需要重新训练 diffusion。

### 3.4 实时部署边界

| 项目 | 配置 |
|---|---:|
| Diffusion backbone | 约 19.8M Transformer |
| Control frequency | 25 Hz |
| Future horizon | 16 steps，约 0.64 s |
| Denoising | 20 steps |
| Diffusion latency | RTX 4060 Mobile 上约 20 ms |
| Execution | diffusion 异步；VAE decoder 在 CPU 同步运行 |

这更接近短时 reactive MPC，而不是能自行分解任务的 long-horizon planner。

**Figure 6. Keyframe inpainting、技能切换与 obstacle avoidance。**

![](https://arxiv.org/html/2508.08241v4/Fig6.png)

*来源定位：论文 §LDMs for Trajectory Modeling、§Online Optimization via Guidance；Supplement S3 Diffusion Formulation、Task Costs、S4 Diffusion。*

## 4. 实验结果：动作质量强，任务成功率证据较薄

| 证据 | 结果 | 能支持什么 |
|---|---:|---|
| Human-motion data | 约 2.5 h，全部仿真验证 | recipe 可覆盖多样动作 |
| Real deployment | 30 clips，共 15 min | 多类动作可直接 sim-to-real |
| User study | N=77；总体 70.8% vs Unitree 29.2% | walking/running 的感知自然度更高 |
| 分项偏好 | walking 57.0%；running 84.7% | running 优势更明显 |
| Velocity tracking error | walking 12.14%；running 13.65% | command-conditioned locomotion 可量化 |
| Continuous running | 超过 50 m | 动态 locomotion 可持续 |
| Cartwheel sim-to-sim | latent 95%；无 latent 5% | latent representation 对稳定性关键 |

用户研究、GRF 曲线和动态真机视频共同支持“动作自然且具有高 agility”。但 30 clips / 15 min 是展示时长，不是成功率统计；论文没有给每个动作的 trial count、failure rate 或第三方复现。

**Figure 4. GRF、walking/running 与用户自然度评价。**

![](https://arxiv.org/html/2508.08241v4/Fig4.png)

*来源定位：论文 Results / Diverse Skills、Human-level Agility、Natural Human-like Behaviors、Command-conditioned Locomotion；§Latent Diffusion ablation。*

## 5. Claim scope：哪些“zero-shot”需要打折

1. **zero-shot downstream task 是 optimization zero-shot**：不更新模型参数，但人仍需定义可微 cost。
2. **不是 onboard perceptive autonomy**：waypoint 与 obstacle demo 使用 motion capture 提供环境位置和更好的 localization。
3. **不是 long-horizon planning**：0.64 秒 horizon 反复重规划；长序列来自短时 controller 的持续闭环，而不是一次生成完整任务计划。
4. **技能切换仍有 failure mode**：论文明确指出 mode 开始/结束时可能 stumble，guidance weight 也需轻量调节。
5. **完整方法不可复现**：官方仓仅含 tracker；VAE、diffusion、guidance 与论文 checkpoint 未开放。

因此更准确的定位是：

> BeyondMimic 建立了高质量 humanoid tracker 的通用 recipe，并证明短时 generative motor prior 可以通过 cost guidance 组合；它没有证明开放技能、开放感知或长时自主规划。

*来源定位：论文 Discussion / Limitations and Future Works、S4 Diffusion；官方项目页关于 mocap 的说明；官方 GitHub README。*

## 关联工作

### 基于与对比

- DeepMimic：代表 per-motion tracking，但通常需要 motion-specific reward 与调参；BeyondMimic 试图把这部分工程成本归一化。
- PULSE、MaskedMimic：同样把 motion experts 压缩为可复用 latent controller；BeyondMimic 的差异是用 state–latent diffusion 的 classifier guidance 支持新 cost。
- [[2610-SuperMimic|SuperMimic]]：直接采用 BeyondMimic tracking reward，但把 PPO optimizer 替换为 differentiable world model + BPTT，并训练一个覆盖 264 小时动作的 generalist tracker。

### 后续系统

- [[2610-Workhorse|Workhorse]]：whole-body tracker 明确建立在 BeyondMimic formulation 上，并使用 adaptive sampler；证明其影响已经从论文 demo 进入后续系统组件。
- [[2611-HALOHumanoidMotion|HALO]]：同样使用 motion-plan → tracker 的分层接口，但 HALO 通过 privileged experts、distillation 和 multi-critic PPO 处理视觉生成计划，而不是使用 BeyondMimic diffusion controller。

### 方法相关

- [[2303-DiffusionPolicy|Diffusion Policy]]：都使用 diffusion 表达多模态动作分布；BeyondMimic 额外建模 future state，使 task cost 可以直接优化预测轨迹。
- [[DomainMaps/WorldModel|World Model]]：BeyondMimic 的 diffusion 学的是 human-like state–action trajectory distribution，不是物理 simulator dynamics；这一点与 SuperMimic 的 differentiable dynamics model 必须区分。

## 论文点评

### Strengths

1. **问题 formulation 非常清楚**：把“每个动作重新设计 reward”改成“固定 recipe，只换 reference motion”，直接攻击 motion-tracking 的扩展瓶颈。
2. **sim-to-real insight 有工程价值**：armature、delay、Rot6D、低 impedance 和 minimal randomization 的消融，比单纯堆网络结构更可迁移。
3. **generative model 被用于约束内优化**：state–latent co-diffusion 让未来状态可被 cost guidance，统一了 joystick、waypoint、inpainting 与 avoidance。
4. **动作质量确实形成后续基础设施**：官方 tracker 获得大规模社区使用并迁入 MJLab，Workhorse 等后续系统直接继承 formulation。

### Weaknesses

1. “scalable tracking”容易被误读成一个 generalist policy；实际是每条或每段 motion 单独训练 policy。
2. diffusion controller 缺少统一的 task-level success metric，主要证据是视频和少量 tracking statistics。
3. waypoint/avoidance 依赖 mocap，尚未闭合 perception–localization–control 链路。
4. 短 horizon 和手写 cost 限制了任务复杂度；新增语义任务仍需要外部 planner 或新的 objective design。
5. 官方仓没有开放论文最具新意的 diffusion half。

### 可信评估

#### Artifact 可获取性

- **代码**: motion-tracking training 已开源；原仓已 retired，README 指向 MJLab tracking task。Diffusion / guidance 未开源。
- **模型权重**: 未发现官方 tracker 或 diffusion checkpoint。
- **训练细节**: 论文与 supplement 给出 MDP、reward、domain randomization、网络和主要超参；tracker 仓给出训练入口。
- **数据集**: LAFAN1 retargeting 等组成部分可获取，但论文使用的完整 2.5 h motion collection 与 diffusion rollout dataset 未作为统一 artifact 发布。

#### Claim 可验证性

- ✅ **同一 tracker recipe 覆盖多类动作**：论文消融、项目页 14 条序列与开源 tracker 共同支持；后续 MJLab / Workhorse 也继承该接口。
- ✅ **高动态真机 motion tracking**：30 clips、15 min 视频与定量 tracking / user-study 结果构成较强内部证据。
- ✅ **latent 优于 direct diffusion**：cartwheel sim-to-sim 为 95% vs 5%，支持 latent representation 的必要性。
- ⚠️ **zero-shot versatile control**：参数确实不更新，但每类任务仍需手写 cost，waypoint/avoidance 还使用外部 mocap。
- ⚠️ **可靠真机迁移**：展示广泛，但没有 per-motion trial count 或 success rate。
- ⚠️ **统一 framework 可复现**：开源只覆盖 tracker，无法复现 diffusion composition 主张。

### Notes

- 对新 humanoid stack，最值得直接继承的是 tracking reward、anchor representation、adaptive sampler 和执行器/延迟建模；这些组件比 guided diffusion 更成熟。
- Guided diffusion 最适合“短 horizon、目标可微、状态可观测”的 task composition。若目标依赖视觉语义或长时记忆，上层 generator/planner 会比继续增加 cost 更自然。
- BeyondMimic 与 SuperMimic 可以正交组合：前者定义 control problem，后者替换 policy optimizer。Workhorse 已经给出了这一组合的早期实例。

### Rating

**Metrics** (as of 2026-11-07): citation=N/A（Semantic Scholar 429，Google Scholar 要求验证）, influential=N/A, velocity=N/A; HF upvotes=0; github 2445⭐ / forks=339 / 90d commits=1 / pushed 22d ago · archived（实现已迁入 MJLab）

**分数**：3 - Foundation

**理由**：它不只是一个动作视频更好的 SOTA 点，而是把 humanoid motion tracking 重新表述为可复用的 one-recipe-per-motion infrastructure，并通过代码、2445 stars、MJLab 迁移与 Workhorse 的直接继承显示了真实社区影响。Diffusion half 的定量证据和开源仍弱，但 tracker formulation 已足以使其成为理解当前 humanoid whole-body control 主线时不可跳过的基础工作，因此高于 2 - Frontier。
