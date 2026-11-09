---
type: paper
title: "SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model"
authors: [Qiayuan Liao, Yiyang Shao, Junfeng Long, Kevin Zakka, Roberto Horowitz, Pieter Abbeel, Koushil Sreenath]
institutes: [University of California Berkeley]
date_publish: 2026-10-20
venue: CoRL 2026 Oral
primary_domain: embodied-ai
domains: [embodied-ai]
tags: [legged, world-model, RL]
review_status: reviewed
arxiv_id: 2610.28480
paper: https://arxiv.org/abs/2610.28480
website: https://supermimic.github.io/
rating: 2
date_added: 2026-11-07
---

## Summary

> [!summary] SuperMimic: Scaling Humanoid Whole-Body Control with One Differentiable World Model
> - **核心**: 用一个由 simulator transition 拟合出的 differentiable dynamics model 摊销整套 motion library 的共享机器人动力学，再通过短时 imagined rollout 的 BPTT analytic gradient 训练 generalist humanoid tracker。
> - **方法**: policy 在 MuJoCo Warp 中采集 replay；world model 对 logged actions 做 8-step autoregressive fit；actor 在冻结模型中 rollout 32 步并反向传播 return，critic bootstrap horizon 外价值。
> - **结果**: 单张 H100 训练 3 小时超过 SONIC released checkpoint，129,514 条训练动作仅失败 25 条；两张 H100 训练 9.8 小时达到 0 failures，而 SONIC 失败 179 条。
> - **Sources**: [paper](https://arxiv.org/abs/2610.28480) | [website](https://supermimic.github.io/)
> - **Rating**: 2 - Frontier（训练效率和 controlled comparison 极强，但论文发布不到一个月、无官方代码，真机与 unseen-motion 证据尚不足以定为 Foundation）

**Key Takeaways:**

1. **SuperMimic 替换的是 optimizer，不是 humanoid control problem**：observation、action 和 tracking reward 基本继承 BeyondMimic，创新在于 learned dynamics + analytic policy gradient。
2. **真正可摊销的是 physics，不是 motion semantics**：十几万条 reference motion 不同，但同一 Unitree G1 的 body/contact dynamics 共享，因此一个 world model 可以服务所有 goal。
3. **world model 不是视频生成或真实世界模型**：它是由 simulator transition 学到的 proprioceptive differentiable surrogate，提供 prediction 和 Jacobian。
4. **0 failures 衡量训练集 coverage，不衡量泛化**：129,514 条 benchmark motions 同时也是两种方法的训练动作。
5. **最可信的效率证据来自 controlled LAFAN1 comparison**：同 motion、reward、network 与 evaluation 下，SuperMimic 单卡 1.2 h 达到 0.82，而 PPO-Sim 1/4/8 卡在 18 h 内均未达到。

**Teaser. SuperMimic 将 cluster-scale model-free motion tracking 压缩成单卡小时级的 world-model policy optimization。**

![](https://supermimic.github.io/media/compute/compute_single-wall_F5F5F7.jpg)

## 1. 问题定义：为什么 motion 越多不应重复学习同一套 dynamics

SONIC 一类 generalist tracker 证明了 motion data、policy capacity 和 compute 可以共同扩展 humanoid skill coverage，但其训练约需 128 张 L40、168 小时，即约 21,000 GPU-hours。

SuperMimic 的第一性原理判断是：

> reference motion 决定机器人“想做什么”，但 action 如何改变下一时刻 body/contact state 由同一套 humanoid dynamics 决定。模型无关 PPO 为每个 motion 反复从 simulator sample 这一关系，浪费了可共享结构。

因此作者不再把 simulator 视为只能采样的 black box，而是用 logged simulator transitions 拟合可微 surrogate。Policy improvement 时只需通过 surrogate 的 Jacobian 反向传播，无需 simulator 自身可微，也不受 rigid contact 实现不可微的限制。

这与典型 visual world model 不同：SuperMimic 不预测 RGB，也不学习开放环境语义，只预测 robot proprioceptive state、reward 和 termination。

*来源定位：论文 §1 Introduction、§2 Learned differentiable dynamics for motion control。*

## 2. One loop, two learners

每次训练 iteration 包含三步：

1. **Collect**：当前 deterministic actor 加 action noise，在 MuJoCo Warp 中 rollout；transition 进入 fixed-size replay buffer。
2. **Fit world model**：采样 logged 8-step windows，用实际执行过的 actions 做 autoregressive dynamics fitting。
3. **Improve policy**：从 replay state 出发，在冻结 world model 中进行 32-step on-policy imagination；BPTT 更新 actor，critic bootstrap horizon 以后的 return。

<video src="https://supermimic.github.io/media/compute/compute_collapse-lines_FFFFFF.mp4" controls muted playsinline width="720"></video>

World model 与 policy 并不是先后训练：二者每轮交替更新。World model 只在 actor backward pass 中 stop-gradient；随着 policy distribution 变化，新 simulator transitions 会继续刷新模型。

旧 policy 的 transition 仍可训练 dynamics，因为环境 transition 不依赖采集它的 policy identity。

*来源定位：论文 Figure 2、§3.1 SuperMimic training loop、Appendix D Algorithm A.1。*

## 3. Differentiable world model

### 3.1 模型输入与训练目标

Dynamics model 输入 predicted state、executed action 和 per-episode simulation context $\xi$，输出下一状态。$\xi$ 包含 friction、joint calibration offset 和 torso center-of-mass offset。

World model 被设计为 deterministic：

- 已知的 domain-randomization parameters 显式作为 context；
- sensor noise 不让模型学习，而是在模型输出的 noise-free observation 上重新采样；
- data collection action noise 扩大模型见过的 action support，但 replay 保存的是实际执行的 noisy action。

默认 dynamics network 是 3 层、每层 2048 hidden units 的 MLP。它用 8-step autoregressive window 训练，每次 world-model update 使用 10 × 2048 windows。

### 3.2 为什么短模型 rollout 足够

Actor imagination horizon 为 32 个 50 Hz control steps。Critic 对 horizon 以后进行 value bootstrap，所以 dynamics 只需在短窗口内提供足够准确的 prediction 和 action Jacobian。

论文报告：

- 数据从 1 h 增至 264 h，8-step prediction error 保持在 0.007–0.011；
- world-model rollout 在实际 batch 范围内比 MuJoCo Warp 快 10× 以上；
- 64k parallel environments 时最高约 62×；
- BPTT actor–critic 达到 PPO-on-world-model 最佳 return 时，imagined steps 少约 64×。

这说明收益不只来自“neural model forward 更快”，也来自 first-order analytic gradient 比 likelihood-ratio policy gradient 更高效。

### 3.3 Critic 的作用

无 critic 时，policy 只优化 32-step 内可见 reward，恢复和再平衡的收益可能落在窗口外。消融显示：

- 无 critic 时 $H\leq16$ 训练失败；
- 有 critic 的 $H=16$ 可匹配无 critic 的 $H=32$；
- 默认 $H=32$ 最快达到 0.82 return；
- T-pose push recovery 中，critic policy 可在约 0.5–2.4 s 内稳定，而无 critic policy 持续 stumble 或跌倒。

*来源定位：论文 §3.2–3.3、§4.2–4.3；Appendix A、C、D，Tables A.3–A.5。*

## 4. Tracker 与多接口结构

Motion-tracking interface 基本沿用 [[2508-BeyondMimic|BeyondMimic]]：

- 29-DoF proprioceptive observation；
- 最近 10 帧 observation history；
- 未来 10 帧 reference motion goal；
- low-PD joint setpoint action；
- body pose/velocity tracking reward、action smoothness 和 joint-limit penalty。

SuperMimic 移除了 BeyondMimic self-collision penalty，并把 joint-limit weight 从 -10 降为 -2。作者解释，self-collision exploit 主要来自 stochastic policy 通过夹紧身体抑制 action noise；imagined rollout 中 actor 是 deterministic，因此该 exploit 没有收益。

Policy 由 per-interface encoder 与 shared decoder 组成：

- motion encoder：未来 reference → 32-D latent；
- velocity encoder：velocity command + observation history → 同一 latent；
- shared decoder：latent + observation history → action；
- 每个 interface 有独立 critic，但共享 dynamics model。

因此一个 learned physics model 理论上可以训练 reference motion、velocity、end-effector target 或 SMPL pose 等多种 goal interface。

*来源定位：论文 Appendix A–C，Tables A.1–A.4。*

## 5. 训练效率：强结果与公平比较

### 5.1 与 SONIC 的 headline comparison

| 方法 | Hardware | Wall-clock | GPU-hours | Motion data | 训练集 failures |
|---|---:|---:|---:|---:|---:|
| SONIC released checkpoint | 128 × L40 | 168 h | 约 21,000 | 611 h | 179 / 129,514 |
| SuperMimic | 1 × H100 | 3 h | 3 | 264.56 h | 25 / 129,514 |
| SuperMimic | 2 × H100 | 9.8 h | 19.6 | 264.56 h | 0 / 129,514 |

论文保守写成大于 1000× GPU-hour、超过 50× wall-clock；直接账面比约为 7200× GPU-hour 和 56× wall-clock。

这个对照并不完全同构：

- SuperMimic 数据量约为 SONIC 的 1/2.3；
- H100 与 L40 的 tensor throughput 不同；
- 两边训练与 implementation stack 不完全相同。

但作者的计算表明，即便把 2.3× 数据量和最高约 5.5× peak tensor throughput 全部算给 SuperMimic，也无法解释 1000× 级 GPU-hour gap。

### 5.2 Controlled LAFAN1 comparison

更关键的是 PPO-Sim 对照：

- 两边共享 motions、observation、reward、termination、domain randomization、actor/critic size 和 evaluation；
- PPO-Sim 甚至每 GPU 使用 8192 environments，是 SuperMimic 的两倍；
- SuperMimic 单 GPU 1.2 h 达到 0.82 evaluation return；
- PPO-Sim 在 18 h 内，1/4/8 GPU 最终分别只有 0.60 / 0.70 / 0.72。

这比 headline SONIC comparison 更能把收益归因到 world-model BPTT，而不是硬件或工程差异。

*来源定位：论文 §4.1、Figures 3–4、Appendix F.3。*

## 6. “0 failures”究竟测量什么

BONES-SEED raw release 有 142,220 clips。作者过滤楼梯、梯子、箱子、椅子等无法在 flat-ground free-standing setting 中执行的动作，以及明显 retargeting artifact，保留：

- 129,514 clips；
- 264.56 h；
- 作为 SuperMimic 与 SONIC 的共同 benchmark。

每条动作只从第一帧 deterministic rollout 一次，触发 SuperMimic training termination 即算失败。

最关键的 caveat 来自论文 Appendix F 自己：

> benchmark motions 对两种方法都是 training motions，所以 failure count 衡量 policy 是否完整覆盖训练动作，不衡量对新动作的 generalization。

因此 0 failures 的正确解释是“training-library coverage / memorization completeness 达到 100%”，而不是 zero-shot motion generalization。

*来源定位：论文 Appendix E Motion data filtering、F.1 Benchmark metrics、F.2 Failed motions。*

## 7. 真机与 downstream interface

### 7.1 Real robot

一个 general tracker 被部署到 Unitree G1，并展示四种动作：

- skipping jump；
- side roll；
- 90° flip；
- in-place 360° flip。

<video src="https://supermimic.github.io/media/real/film-1080.mp4" controls muted playsinline width="720"></video>

这些 demo 覆盖 locomotion、地面接触和 acrobatics，但论文没有 trial count、success rate 或不同地面条件评测，因此只能支持“能够 sim-to-real”，不能支持“可靠部署”。

### 7.2 Velocity interface

作者比较：

- RL encoder：直接通过 world model 优化 velocity-tracking reward；
- distillation encoder：用 reference motion 导出的 velocity command，通过 motion-tracking reward 学 latent alignment。

672 个 step commands 中：

- RL encoder 在 650 个 command 上误差更低；
- distillation 在 15 个上更低；
- median relative error 为 0.16 vs 0.49；
- distillation 在 7 个高速 translation + turning commands 上四次全跌倒。

但每个 policy 只有一个 training seed；而且 velocity reward 只更新 velocity encoder，对 shared decoder stop-gradient。因此当前实验尚未证明 concurrent multi-interface training 会改善共享 motor decoder。

*来源定位：论文 §4.4–4.5、Figure 6–7、Appendix B、G。*

## 8. 边界与可能的 break point

1. **world model 只拟合 simulator**：没有 real transition，也没有 online system identification。
2. **只验证 flat ground**：terrain 与 object interaction 被数据过滤掉，尚不知道 contact distribution 扩展后 prediction error 是否仍稳定。
3. **未报告 seed variation**：作者称尝试多个 seeds 且训练稳定，但 main figures 没有 error band；velocity interface 明确只有一个 seed。
4. **model bias 仍可能被 actor exploit**：online replay 和短 horizon 降低风险，但论文没有专门给出 adversarial model exploitation 分析。
5. **0 failures 不是 OOD**：没有 held-out motion、held-out morphology 或 unseen contact regime 的 scaling curve。
6. **暂无官方 artifact**：截至 2026-11-07，项目页没有官方 GitHub、checkpoint 或训练代码链接。

## 关联工作

### 直接基础

- [[2508-BeyondMimic|BeyondMimic]]：SuperMimic 继承其 observation/action/reward formulation，并把 per-motion PPO / distillation 路线替换成 one-world-model generalist training。
- SONIC：SuperMimic 的主要规模化基线；SONIC 证明 generalist tracker 可随 motion/compute 扩展，SuperMimic 则攻击其训练成本。

### 已出现的后续使用

- [[2610-Workhorse|Workhorse]]：tracker training 明确沿 SuperMimic 路线，用 MJLab transitions 拟合 dynamics network，再在 predicted rollout 上训练 actor/critic。这是方法快速进入下游系统的早期证据。
- [[2611-HALOHumanoidMotion|HALO]]：同样需要把 kinematic plan 变成真机 action，但使用 privileged experts → multi-teacher distillation → multi-critic PPO；它提供了与 SuperMimic 不同的 tracker scaling 路线。

### 方法相关

- Dreamer / SHAC：SuperMimic 结合 learned dynamics imagination 与短时 critic bootstrap，但使用标准 rigid-body simulator 采集数据，不要求 differentiable simulator。
- [[DomainMaps/WorldModel|World Model]]：这里的 world model 是 robot-state dynamics surrogate，不是 video world model，也不承担视觉 planning 或环境生成。
- [[2505-DreamGen|DreamGen]]：两者都通过解耦计算阶段获得 scaling；DreamGen 用 video world model 离线扩数据，SuperMimic 用 dynamics world model 在线提供 analytic policy gradient。

## 论文点评

### Strengths

1. **问题选得比“再做一个更强 tracker”更基础**：它直接改变 motion coverage 与训练 compute 的关系。
2. **方法简洁且可解释**：共享 dynamics、短 imagined rollout、analytic gradient、critic bootstrap 四个组件各自对应明确瓶颈。
3. **机制消融完整**：prediction scaling、rollout throughput、BPTT vs PPO-WM、critic horizon 都提供了因果链，而不只给最终 return。
4. **controlled PPO-Sim comparison 很有说服力**：同一数据和 control formulation 下，单卡 BPTT 显著超过多卡 PPO。
5. **下游接口方向正确**：相比只蒸馏 reference motion，直接用 task reward 优化 goal encoder 更可能覆盖 motion library 中稀缺的 command。

### Weaknesses

1. SONIC headline comparison 同时改变 GPU、数据量和 implementation，虽然差距过大不太可能完全由这些因素解释。
2. 0 failures 是训练集 coverage，不能支持 unseen-motion generalization。
3. 真机只有四类动作展示，没有重复试验统计。
4. 论文没有报告 seed variance，速度接口还是单 seed。
5. world model 未验证 terrain、objects、跨机器人 morphology 或 real-data adaptation。
6. 无官方代码和权重使核心效率主张当前无法独立复现。

### 可信评估

#### Artifact 可获取性

- **代码**: 截至 2026-11-07 未发现官方 repository；项目页没有 GitHub 链接。
- **模型权重**: 未发布。
- **训练细节**: 论文给出完整训练 loop、network sizes、主要 hyperparameters、reward、domain randomization 与 dataset filtering，足以理解方法但不足以核验实现。
- **数据集**: BONES-SEED 与 LAFAN1 可公开获取；作者使用的 filtered 129,514-clip list 和论文 checkpoints 未作为独立 artifact 发布。

#### Claim 可验证性

- ✅ **world-model training 显著降低 compute**：controlled LAFAN1 PPO-Sim comparison 与机制消融共同支持，内部证据强。
- ✅ **一个 dynamics model 可摊销更大 motion library**：1–264 h sweep 中 prediction error 稳定，compute-to-target 增长缓慢。
- ✅ **critic 允许较短 horizon 并改善 recovery**：horizon sweep 与 push test 直接支持。
- ⚠️ **大于 1000× GPU-hour 优势**：账面成立，但 SONIC 对照的 GPU、数据量与软件栈不同；应与 controlled comparison 一起解读。
- ⚠️ **0 failures**：只说明 filtered training-set coverage，不是新动作泛化。
- ⚠️ **可部署 general tracker**：四类真机 demo 支持 feasibility，但没有 success statistics。
- ⚠️ **multi-interface learning**：velocity 结果强，但单 seed、decoder stop-gradient，尚未证明真正的共享多任务协同。

### Notes

- 对新 tracker 项目，合理组合是：BeyondMimic 定义 MDP/reward/interface，SuperMimic 作为 optimizer backend；两者不是竞争关系。
- 下一步最重要的实验不是继续扩大 flat-ground mocap，而是验证 world-model prediction error 是否在 terrain、object contact 和 planner-induced OOD command 下仍保持稳定。
- 如果加入少量 real transition，可微 dynamics 很适合同时做 residual system identification；这可能把目前的 simulator surrogate 推向真正 adaptive sim-to-real controller。

### Rating

**Metrics** (as of 2026-11-07): citation=N/A（Semantic Scholar 429，Google Scholar 要求验证）, influential=N/A, velocity=N/A; HF upvotes=5; github=N/A（项目页无官方仓库）

**分数**：2 - Frontier

**理由**：SuperMimic 提出的 shared differentiable dynamics + BPTT 可能改变 humanoid motion tracking 的训练经济学，controlled comparison 与机制分析也足以让它成为当前必须关注的前沿工作。但论文发布不到一个月、官方代码与权重缺失、真机和 OOD evidence 较薄；在独立复现和下游采用出现前，将其定为 3 - Foundation 仍然过早。
