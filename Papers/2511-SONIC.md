---
type: paper
title: "SONIC: Supersizing Motion Tracking for Natural Humanoid Whole-Body Control"
authors: [Zhengyi Luo, Ye Yuan, Tingwu Wang, Chenran Li, Fernando Castañeda, Sirui Chen, Zi-Ang Cao, Jiefeng Li, David Minor, Qingwei Ben, Jinhyung Park, David Sami, Zi Wang, Xingye Da, Runyu Ding, Cyrus Hogg, Lina Song, Edy Lim, Eugene Jeong, Tairan He, Haoru Xue, Wenli Xiao, Simon Yuen, Jan Kautz, Yan Chang, Umar Iqbal, Linxi “Jim” Fan, Yuke Zhu]
institutes: [NVIDIA]
date_publish: 2025-11-11
venue: Science Robotics 2026
primary_domain: embodied-ai
domains: [embodied-ai]
tags: [legged, imitation-learning, RL, VLA]
review_status: reviewed
arxiv_id: 2511.07820
doi: 10.1126/scirobotics.aed4592
paper: https://arxiv.org/abs/2511.07820
website: https://nvlabs.github.io/GEAR-SONIC/
github: https://github.com/NVlabs/GR00T-WholeBodyControl
rating: 3
date_added: 2026-11-09
---

## Summary

> [!summary] SONIC: Supersizing Motion Tracking for Natural Humanoid Whole-Body Control
> - **核心**: 把 physics-based motion tracking 沿模型、数据和算力三轴扩展成一个 generalist humanoid motor controller，并用共享 token interface 把 motion generation、teleoperation 与 VLA 接到同一低层策略上。
> - **方法**: robot / human / hybrid 三类 encoder 经 FSQ 对齐为 64 维 universal motion token，共享 PPO control decoder；另配短时 generative kinematic planner，把高层意图转成可跟踪的全身参考运动。
> - **结果**: 42M 模型在 unseen-content split 上达到 99.6% success / 23.8 mm MPJPE-L；真机 124 段动作成功 123 段；GR00T N1.5 经 token interface 完成五类 loco-manipulation，平均成功率 75%。
> - **Sources**: [paper](https://arxiv.org/abs/2511.07820) | [website](https://nvlabs.github.io/GEAR-SONIC/) | [github](https://github.com/NVlabs/GR00T-WholeBodyControl)
> - **Rating**: 3 - Foundation（奠定了“scale motion tracking as motor substrate”的主线，并形成高引用、广泛使用且可训练/部署的公开基础设施）

**Key Takeaways:**

1. **真正被 scale 的是 motor prior，不是语义自主性**：SONIC 接收 motion reference 或 universal token；视频、文本、音乐和语言任务分别由 GEM、planner 或 GR00T VLA 解释。
2. **generalist 的关键从 one-recipe-per-motion 变成 one-policy-for-many-motions**：317k clips、100M+ frames 和 42M 参数进入同一个 controller，且 test-content 明确隔离 182 个训练未见 sub-categories。
3. **universal token 是 action interface，不是完整世界模型**：它对齐 robot、SMPL human 和 hybrid teleop command，既降低 runtime retargeting 依赖，也把 VLA 的全身 action 压到 64 维 latent。
4. **证据最强的是 tracker scale 与 sim-to-real，最弱的是公平 baseline 归因**：三轴 scaling、7k+ OOD clips 和 124 段真机覆盖很强；但 BeyondMimic 等基线使用不同数据与 retargeting pipeline。
5. **SONIC 定义了范式，但未锁定最佳训练经济学**：后来的 [[2610-SuperMimic|SuperMimic]] 表明相同 generalist tracking problem 可能不需要 21k GPU-hours。

**Teaser. SONIC 把多源 motion command 编码成统一 token，再由单一全身 controller 落到 Unitree G1。**

![](https://arxiv.org/html/2511.07820v4/fig1_teaser.png)

## 1. 问题定义：把 motion tracking 变成 humanoid 的 motor substrate

传统 humanoid controller 往往围绕单个任务设计 reward；动作集合一扩张，reward、数据与训练流程就一起碎片化。SONIC 的核心 formulation 是选择 **motion tracking** 作为可扩展预训练任务：每一帧 mocap 都提供稠密姿态监督，不必为 walking、dance、combat、crawl 等行为分别发明任务 reward。

系统边界可以概括为：

```text
planner / GEM / GR00T VLA / VR operator
                    ↓
       motion reference 或 universal token
                    ↓
           SONIC motor controller
                    ↓
          29-DoF Unitree G1 action
```

因此 SONIC 的“foundation model”含义是 **behavior foundation / motor foundation**：它提供自然、稳定、覆盖面广的全身动作先验，但不自己完成开放词汇感知、长时任务规划或语义推理。文本与音乐输入由外部 GEM 生成人体 motion；自主 loco-manipulation 的视觉语言决策由 GR00T N1.5 完成。

*来源定位：论文 Abstract、§1 Introduction、§2.3–2.5、§3.2 Tasks and Applications。*

## 2. Scale 的三个轴

原始 mocap collection 约 700 小时；经 GMR / PyRoki retargeting，并过滤楼梯、坐姿等目标机器人无法执行的片段后，训练集为 317,189 clips、611 小时、100M+ frames（50 Hz），覆盖 33 个 main categories 和 8,447 个 motion sub-categories。

| Scale axis | 配置 | 论文中的最大配置 |
| --- | --- | --- |
| Data | 4M / 10M / 22M / 100M frames | 317k clips，611 h |
| Model | 1.2M / 16M / 42M parameters | 42M |
| Compute | 16 / 32 / 128 GPUs | 约 2k / 9k / 21k GPU-hours |

两个内部 held-out split 区分了不同泛化问题：

- **test-content**：7,016 clips、15 h、182 个训练集中完全不存在的 sub-categories，测试 unseen motion content；
- **test-repetition**：9,395 clips、12 h，动作类型已见但 actor / take 不同，测试同类动作的新演绎；
- **PHUMA**：68,326 motions，来自不同 video-pose 与 retargeting pipeline，作为额外外部分布测试。

公开的 BONES-SEED 是训练来源的子集：142,220 motions、522 actors、约 288 h，带 SOMA / G1 格式、文字描述和 temporal labels；它并不等于论文使用的完整 611 h filtered training set。

*来源定位：论文 §2.1、§3.1、Table 2；GitHub README / BONES-SEED release。*

## 3. Universal control policy

### 3.1 State、action 与 tracking objective

Actor 输入由两部分组成：

- 10-step proprioceptive history：joint pose / velocity、root angular velocity、projected gravity、previous action；
- motion command：robot motion、human SMPL motion 或 upper-body keypoints + lower-body robot motion 的 hybrid command。

所有量都转到 robot-local frame，旋转使用 6D representation。Policy 输出 29 个 target joint positions，由低层 PD controller 执行。Reward 同时追踪 root、body links、head / wrists / ankles 的 pose 与 velocity，并加入 action-rate、joint-limit、undesired-contact、anti-shake 和 feet-acceleration penalties。训练还随机化 friction、restitution、COM、初始关节位置、root perturbation 与 target-command noise。

这仍然是精心设计的 tracking reward，而不是“完全没有 reward engineering”；更准确的说法是同一套 objective 可在大量 motion 上复用，不再为每种语义行为单独设计任务 reward。

*来源定位：论文 §3.2 Motion Tracking Formulation；Supplement §S1.1、Tables S2–S4。*

### 3.2 三个 encoder，一个 token space

**Figure 6. 三类 command encoder 经共享量化空间驱动同一 control decoder。**

![](https://arxiv.org/html/2511.07820v4/fig6_method_overview.png)

三个 MLP encoder 分别处理：

- $\mathcal{E}_r$：未来 robot joint position / velocity；
- $\mathcal{E}_h$：未来 human 3D joints / SMPL motion；
- $\mathcal{E}_m$：当前 sparse head / hand keypoints 与未来 lower-body robot motion。

默认 quantizer 是两个 FSQ token，每个 token 32 维、每维 32 levels，合起来形成下游使用的 64 维 universal motion token。FSQ 相比 VQ-VAE 不需要 codebook EMA / commitment loss，且可通过 straight-through estimator 与 PPO 联合优化。

Token 进入两个 decoder：

1. $\mathcal{D}_c(z,s_t^p)$ 结合 proprioception 输出 motor action；
2. $\mathcal{D}_r(z)$ 重建 robot motion command，既提供辅助监督，也让 human encoder 隐式承担 human-to-robot retargeting。

### 3.3 联合训练目标

总目标由 PPO 与三个 representation losses 组成：

$$
\mathcal{L}
=
\mathcal{L}_{\mathrm{ppo}}
+\mathcal{L}_{\mathrm{recon}}
+\mathcal{L}_{\mathrm{token}}
+\mathcal{L}_{\mathrm{cycle}}.
$$

其中 reconstruction 要求三类 token 都能解码回同一 robot command；pairwise token loss 对齐 robot / human / hybrid encoder；cycle loss 约束 human token 解码成 robot motion 后再次编码仍接近 robot token。训练使用 asymmetric actor–critic：critic 可见 privileged simulation state，actor 只使用部署可得观测。Bin-based adaptive sampler 按 capped failure rate 增加困难 motion 的采样概率。

这套设计的关键不是“量化”本身，而是让多种 command source 在训练期被迫占据一致的 motor manifold；否则 VR 数据、SMPL 数据与 VLA 预测 token 会形成互不兼容的 action distributions。

*来源定位：论文 §3.2 Universal Control Policy / Training；Supplement Table S1。*

## 4. 从 reference tracker 到可交互系统

### 4.1 Generative kinematic planner

Planner 把当前 pose 与目标 keyframe 之间的运动视作 latent masked-token in-betweening：训练片段长度为 0.8–2.4 s，先以 4× temporal downsampling 编码，再迭代填充未知 motion tokens。Navigation target 由 velocity / direction / style command 生成；squat、crawl、boxing 等技能使用少量直观 keyframes。

Critically damped spring 用来平滑 pelvis xy 与 heading，避免从 $6\,\mathrm{m/s}$ 突然反向到 $-6\,\mathrm{m/s}$ 一类不现实 command。Planner 在普通 laptop 上小于 5 ms、Jetson Orin 上约 12 ms，可每 100 ms 或 command 更新时重规划；论文称一个模型覆盖 25+ skills / styles，每类只需一个代表性 clip，无需再训练 tracker。

**Video. Planner 以统一策略执行可交互 running style。**

<video src="https://nvlabs.github.io/GEAR-SONIC/static/videos/planner/styled/planner_run.mp4" controls muted playsinline width="720"></video>

*来源定位：论文 §2.2、§3.3、§3.5、Supplement §S1.2–S1.3；媒体来自官方项目页。*

### 4.2 Video / text / music / VR

- Video、text 和 music 先进入外部 GEM，得到 human motion，再由 $\mathcal{E}_h$ 编码；
- whole-body VR 使用头显、手柄和 ankle trackers 输出 SMPL；
- 3-point VR 只给 head / wrists、hand joints、waist height 与 navigation command，下半身由 planner 补齐；
- control loop 对 motion source 无感，切换 source 等价于更换 MotionSequence 与 encoder mode。

这说明 universal interface 的价值是把上游 generator 与下游 physical controller 解耦，但也再次限定了 claim：SONIC 自身不完成 video pose estimation、text-to-motion 或 music understanding。

*来源定位：论文 §2.3–2.4、§3.4；Supplement §S1.2 Unified motion interface。*

### 4.3 VLA loco-manipulation

GR00T N1.5 的 whole-body action 为 78 维：64 维 universal token + 14 维 hand joints。相比直接预测 81 维 SMPL pose + hands，token action space 在三个 ablation tasks 上平均为 68% vs 27%，复杂的 soda-can-to-trash-can 为 60% vs 0%。

| Task | Training trajectories | Trials | Success |
| --- | ---: | ---: | ---: |
| Apple to plate | 300 | 20 | 90% |
| Carrot pickup | 3,900 multi-object | 20 | 75% |
| Scrub pickup | 3,900 multi-object | 20 | 95% |
| Open trash can with foot | 200 | 10 | 70% |
| Soda can to trash can | 1,000 | 10 | 60% |
| Drill and box relocation | 300 | 10 | 70% |

论文把两个 object-pickup variants 视为同一类任务，因此报告“五类任务平均 75%”。这些结果证明 token 可以承载手脚协同，但每项只有 10–20 trials，且没有证明 SONIC 本身产生语义决策——该能力来自 fine-tuned GR00T N1.5。

**Video. VLA 取罐、行走、踩垃圾桶踏板并投掷。**

<video src="https://nvlabs.github.io/GEAR-SONIC/static/videos/vla/trashcan_soda.mp4" controls muted playsinline width="720"></video>

*来源定位：论文 §2.5、Table 1、§3.6 FSQ Tokens vs. Explicit Poses；媒体来自官方项目页。*

## 5. 实验：scale、泛化与真机

### 5.1 Scaling result

**Figure 2. 数据、模型、算力 scaling；跨方法 benchmark；sim-to-real。**

![](https://arxiv.org/html/2511.07820v4/fig2_scaling_benchmark.svg)

在固定 50k iterations 的设置下，data、model 和 GPU count 三轴都显著改善 test-content / test-repetition（smallest vs largest，所有 $P\leq0.011$）。模型规模最清楚：

| Model | Test-content success | MPJPE-L |
| --- | ---: | ---: |
| 1.2M | 98.0% | 27.7 mm |
| 42M | 99.6% | 23.8 mm |

Success 已接近饱和，因此 1.6 个百分点看似不大；但 MPJPE-L 下降 3.9 mm，而且增益在 OOD split 更明显。需要注意，compute scaling 同时提高 GPU 数、global batch 和总 GPU-hours，它证明“更多 compute 得到更好 asymptote”，不是等成本效率比较。

*来源定位：论文 §2.1、Figure 2A–C、§3.7 Statistical Analysis。*

### 5.2 与 tracker baseline 的比较

在统一 MuJoCo evaluation 与 termination criterion 下：

| Method | Test-content | Test-repetition | PHUMA |
| --- | ---: | ---: | ---: |
| SONIC | 98.5% | 99.2% | 97.2% |
| BeyondMimic | 82.0% | 85.4% | 73.8% |
| Any2Track | 61.6% | 69.4% | 78.5% |

SONIC 的 MPJPE-L 为 23.7 mm，论文称比 BeyondMimic 的 40.9 mm 低 42%。但作者明确承认这主要反映 **cross-dataset generalization + scale**：BeyondMimic / Any2Track 使用 LaFAN，GMT 使用 AMASS，而 SONIC 使用自己的 611 h corpus 和 retargeting pipeline。因此该表不能单独支持“架构优于 baseline”；它支持的是“数据、统一 policy 与训练规模的整体系统更强”。

另一个有意义的对照是 velocity specialist OpenHomie：200 次 runs 中 SONIC survival 197，OpenHomie 为 86。这个结果说明广覆盖 motor prior 没有必然牺牲窄任务鲁棒性，但两者训练目标与数据仍不同。

*来源定位：论文 §2.1、Figure 2D–J。*

### 5.3 Sim-to-real 与 failure cases

在同一组 124 motions 上，simulation 成功 124/124，真机成功 123/124；整体 MPJPE-L 为 22.3 vs 25.7 mm。Upper body gap 很小（21.8 vs 22.2 mm），feet gap 最大（29.0 vs 53.7 mm），说明接触与落脚仍是 sim-to-real 的主要误差源。

这个 protocol 的覆盖面很强，但每段 motion 只有一次真机 trial，因此 99.2% 更接近“多样动作能否执行一次”，而不是同一动作反复执行的 reliability estimate。

OOD 成功案例包括 hip-hop、stage bow、sword lunge 和 roundhouse kick；失败案例是 zombie crawl 与 cross-legged sit。二者分别触及 kinematic limit 和持续复杂地面接触，说明当前 universal tracker 对非足底 contact topology 仍不 universal。

*来源定位：论文 §2.1、Figure 2K–L；Supplement §S2.2–S2.3、Figure S3–S4。*

## 6. Ablation：哪些设计真正必要

1. **FSQ vs VQ-VAE**：128-GPU setting 下，test-content MPJPE-L 为 26.6 vs 35.3 mm；FSQ 优势 8.7 mm。
2. **Token capacity**：32-GPU sweep 中，增加 token dimension 比增加 quantization levels 更重要；默认选择两枚 FSQ-32-32 tokens。
3. **Multi-encoder consistency**：robot / human / hybrid encoder 的 success 都高于 99.2%；去掉 token / cycle consistency 后 cross-encoder divergence 增加 8×。
4. **VLA action space**：FSQ token 在三个任务平均 68%，explicit SMPL 为 27%，复杂任务差距随 horizon / coordination 增大。

这些 ablations 能支持“shared quantized interface 有用”，但 Table 3 每个配置只评估一次、没有 statistical test；VLA action-space ablation 也只有 10–20 trials。因此方向证据清楚，effect size 的稳定性仍需独立重复。

*来源定位：论文 §3.6、Tables 1B and 3、Supplement §S2.6。*

## 关联工作

### 直接基础与对比

- [[2508-BeyondMimic|BeyondMimic]]：提供可复用的 high-quality motion-tracking formulation，但 tracker 仍是 one recipe per motion；SONIC 把 coverage 推到单一 generalist policy，并加入统一 token interface。SONIC 对它的主表不是 data-matched comparison。
- GMT / Any2Track：同属 universal / general motion tracking baseline；SONIC 的优势包含数据规模和 retargeting pipeline 差异，不能只归因于网络。
- [[2610-SuperMimic|SuperMimic]]：沿用 generalist tracker 问题，却用 shared differentiable dynamics + BPTT 大幅降低训练成本。它挑战 SONIC 的 optimizer economics，不否定 SONIC 对任务 formulation、规模化数据和 interface 的贡献。

### 下游系统

- [[2506-GR00TN15|GR00T N1.5]]：SONIC 论文用它从 vision / language 预测 universal token；语义决策来自 VLA，SONIC 提供全身 motor action space。
- [[2610-Workhorse|Workhorse]]：同样采用 planner → tracker 分层，但规划 interface 是显式 torso / wrists / feet targets，tracker 继承 BeyondMimic / SuperMimic；相较之下 SONIC 更强调一个统一 latent interface 与大规模 generalist motor prior。
- [[2611-HALOHumanoidMotion|HALO]]：同样把语义、kinematic motion 与 physical tracking 分层。HALO 的强项是 perceptive sim-to-real 与多环境真机统计；SONIC 的强项是 motor repertoire、multi-source interface 与公开部署基础设施。

### 方法相关

- FSQ：避免 VQ codebook collapse，并允许 PPO gradient 通过 straight-through estimator 塑造 latent；这里的作用是 action-space alignment，而不是压缩视觉语义。
- Motion in-betweening / masked-token generation：planner 生成短时可执行 reference，不负责开放式 long-horizon planning。
- Asymmetric actor–critic + domain randomization：privileged critic 提高仿真训练效率，actor 保持 deployment-observation constraint。

## 论文点评

### Strengths

1. **找对了可 scale 的 task formulation**：mocap 的 dense supervision、统一 tracking objective 与海量已有 human motion 形成自然的数据飞轮。
2. **不只是一张 scaling curve**：planner、token interface、VR、GEM、VLA 与 onboard deployment 证明 motor prior 能被多种上层系统实际消费。
3. **OOD 与真机 protocol 有规模**：7,016 个 unseen-content clips、68,326 个 PHUMA motions、124 段真机动作远强于少量 cherry-picked demo。
4. **interface 设计有长期价值**：把多种 human / robot command 对齐到同一 motor space，使 perception / planning 与 physical control 可以独立演进。
5. **artifact 完整度高**：训练代码、C++ TensorRT deployment、三个 checkpoints、VR / VLA pipeline 和 BONES-SEED 均已公开。

### Weaknesses

1. **算力成本极高**：主训练约 21k GPU-hours；SuperMimic 的后续结果说明这不是 generalist tracking 的必然成本。
2. **baseline 不是 data-matched**：不同训练数据和 retargeting pipeline 混入主表，无法干净归因到 SONIC architecture。
3. **full training corpus 未公开**：BONES-SEED 约 288 h，而论文实际训练集 611 h；公开复现无法严格对齐数据规模与分布。
4. **真机 reliability 仍缺重复试验**：124 motions 各一次展示 coverage，不提供 per-motion repeated success / confidence interval。
5. **VLA 证据样本较小**：每任务 10–20 trials，且上层 foundation model 与 teleop data 对结果贡献没有被完全拆开。
6. **接触 topology 仍窄**：feet error 最大，zombie crawl / cross-legged sit 暴露持续或复杂 ground contact 的缺口。
7. **不是端到端 autonomy**：高层语义、环境理解与 long-horizon recovery 必须由外部系统提供。

### 可信评估

#### Artifact 可获取性

- **代码**: inference + training；官方仓包含 PPO training、data processing、Isaac Lab evaluation、C++ TensorRT deployment、VR teleoperation 与 VLA workflow。
- **模型权重**: 已发布 Default SONIC、Low-latency teleoperation、SONIC v1.1 三套 G1 checkpoints；包含 ONNX deployment files 与 PyTorch training checkpoint。
- **训练细节**: 论文给出 architecture、PPO hyperparameters、reward、domain randomization、adaptive sampling 和 deployment rates；仓库给出从 BONES-SEED 训练 / finetune 的命令。
- **数据集**: BONES-SEED 公开 142,220 motions / 522 actors / 约 288 h；论文完整 611 h filtered corpus 仅部分公开。

#### Claim 可验证性

- ✅ **scale 改善 unseen-motion tracking**：三轴 sweep、明确 test-content split 和大规模 evaluation 支持；最大模型相对最小模型同时提升 success 与 MPJPE-L。
- ✅ **strong sim-to-real motion coverage**：同一 124 motions 的 sim / real 结果与 body-part error 支持，且公开部署 stack 可用于进一步核验。
- ✅ **universal token 优于 explicit SMPL action**：Table 1B 在三个 VLA tasks 上给出 68% vs 27%，Table 3 与 latent-alignment 分析提供机制证据。
- ⚠️ **优于 SOTA tracker architecture**：headline baseline 数字成立，但训练数据和 retargeting 不匹配，不能排除 data-scale 主导。
- ⚠️ **foundation-model-driven autonomy**：VLA 确实闭环运行，但 SONIC 只提供 motor interface；语义、视觉和任务决策来自 GR00T N1.5。
- ⚠️ **universal whole-body control**：覆盖非常广，但复杂持续地面接触仍失败，且只验证 Unitree G1 embodiment。
- **无明确 ❌ 营销话术**：主要问题是“foundation / universal”容易被读得超过 motor-control scope，而非论文数字与证据冲突。

### Notes

- SONIC 最值得继承的不是“大模型”标签，而是 **motion tracking objective + aligned action interface + modular stack**。上层 VLA 只要学低维 token，就不必重学每个 joint 的 stabilizing reflex。
- 下一步关键问题是 token 是否能跨 terrain、object contact 和 embodiment 保持一致语义；目前 encoder alignment 只在同一 G1 dynamics 下成立。
- 如果用 SuperMimic 一类 optimizer 重训 SONIC interface，最有价值的实验是保持 611 h data、42M architecture 与 evaluation protocol 不变，只替换 PPO backend，从而分离“scale 的价值”与“model-free compute 浪费”。
- 对 perceptive humanoid，更合理的 mental model 是：HALO / Workhorse / GR00T 负责产生 intent-aware motion，SONIC 一类 tracker 负责把它物理落地；真正开放的研究问题在两层之间的 feasibility、contact intent 与 uncertainty interface。

### Rating

**Metrics** (as of 2026-11-09): citation=306, influential=58 (19.0%), velocity=25.5/mo; HF upvotes=0; github 3895⭐ / forks=634 / 90d commits=22 / pushed 6d ago

**分数**：3 - Foundation

**理由**：SONIC 把 generalist humanoid motion tracking 从“可行 demo”推进为明确的 scaling paradigm、通用 motor interface 与可训练/部署的公共基础设施；306 次引用、19% influential-citation ratio、3895 GitHub stars 和后续工作的直接对照表明它已经成为这条主线的必读节点。SuperMimic 使其 21k GPU-hour recipe 不再像最终答案，但那是在改写训练经济学，而不是取代 SONIC 所建立的问题定义和系统范式，因此仍高于 2 - Frontier。
