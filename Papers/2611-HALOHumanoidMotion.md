---
type: paper
arxiv_id: 2611.06908
title: "Perceptive Humanoid Motion from Simulation"
authors: [Siyuan Hu, Abulikemu Abuduweili, Yue Meng, Shipeng Liu, Quentin Leboutet, Chen Chen, Matthias Müller, Vladlen Koltun]
institutes: [Apple]
date_publish: 2026-11-04
venue: arXiv preprint
primary_domain: embodied-ai
domains: [embodied-ai]
tags: [VLA, legged, flow-matching, task-planning]
review_status: reviewed
paper: https://arxiv.org/abs/2611.06908
website: https://apple-aiml-research.github.io/ml-halo/
github: https://github.com/apple-aiml-research/ml-halo
rating: 2
date_added: 2026-11-07
---

## Summary

> [!summary] Perceptive Humanoid Motion from Simulation
> - **核心**: HALO 用程序化场景、生成式人体运动和仿真渲染构造 vision-language-motion 数据，再以 0.5/3/50 Hz 的 orchestrator–generator–tracker 分层系统实现零样本真机迁移。
> - **方法**: 冻结 Qwen3.5-2B 负责视觉语言编码，49.3M DiT 通过 flow matching 生成 5 秒全身计划；15-frame clean prefix 保证异步重规划连续，depth-conditioned multi-critic PPO tracker 负责动力学落地。
> - **结果**: 六项原子技能在 6 个未扫描真实环境、360 次试验中平均成功率 91%；三类多任务链在单一真实环境、每类 10 次试验中平均 70%。
> - **Sources**: [paper](https://arxiv.org/abs/2611.06908) | [website](https://apple-aiml-research.github.io/ml-halo/) | [github](https://github.com/apple-aiml-research/ml-halo)
> - **Rating**: 2 - Frontier（真机与系统证据强，但技能库、长时评测和可复现 artifact 尚不足以成为 Foundation）

**Key Takeaways:**

1. **真正的贡献是系统接口设计，不是端到端“大一统”**：语义规划、运动生成、动力学控制被显式解耦，dense whole-body trajectory 成为三层之间可训练、可检查的中间表示。
2. **仿真扩展的是 episode 数量，不会自动消除人工先验**：162,698 个 episode 无需逐条遥操作，但六类技能的分解、prompt、keyframe 与若干 motion prior 仍由人提供。
3. **clean-prefix 比 flow-matching 标签本身更关键**：训练时把已承诺的 15 帧固定为无噪声前缀，使异步计划在交换点严格衔接；回归基线同时失去这一机制，因此不能把 65 个百分点差距全归功于生成建模。
4. **“generalist autonomy”仍是有限技能组合**：orchestrator 把自由语言映射到 10 个固定 subtask，物理能力实际只有 Go-To、Sit、Door、Crouch、Crawl、Push 六类；这不是开放世界 humanoid VLA。

**Teaser. HALO 的三层 autonomy stack：VLM 编排、全身运动生成与实时 motion tracking。**

![](https://apple-aiml-research.github.io/ml-halo/assets/fig-stack.webp)

## 1. 问题定义与核心判断

HALO 试图解决的不是“让 humanoid 做出漂亮动作”，而是让机器人在**未扫描、未建图、未见过的真实房间**里，根据第一视角视觉和自然语言完成需要全身接触的任务。难点同时存在于两个尺度：上层要判断“用户指的是哪把椅子、应先做什么”，下层要让身体在未知几何、真实摩擦和执行器延迟下稳定接触目标。

论文没有把语言直接映射到 joint targets，而是选择清晰的三层分解：VLM 只负责把请求变成有限 subtask；generator 把 RGB 与 subtask 变成稠密运动计划；tracker 再把 kinematic plan 变成满足物理约束的 29 关节命令。这个选择牺牲了技能开放性，却显著降低了 sim-to-real 的学习难度和系统耦合。

> [!important] 我的判断
> HALO 是一个完成度很高的**有限技能 sim-to-real stack**。它证明“程序化环境 × 生成式 motion prior × 分层控制”可以产生强真机泛化，但尚未证明开放词汇、开放技能或真正长时的通用 humanoid autonomy。

*来源定位：论文 Introduction、§III Methods、§V-1 Limitations。*

## 2. 三层异频架构：0.5 / 3 / 50 Hz

| 层级 | 输入 | 输出 | 频率与模型 | 责任边界 |
| --- | --- | --- | --- | --- |
| Orchestrator | 用户请求、egocentric video、执行状态 | 固定 subtask 序列与转移决定 | 约 0.5 Hz；默认 Qwen3.6-35B-A3B 4-bit/MLX | 消歧、任务分解、成功判断、失败重试 |
| Motion generator | 当前 RGB、当前 subtask、clean prefix | 150 × 36 的 5 秒全身 kinematic plan | 约 3 Hz；frozen Qwen3.5-2B + 49.3M DiT | 视觉语义到稠密全身运动 |
| Motion tracker | motion plan、depth、proprioception、IMU | 29 个 joint position targets | 50 Hz；CNN + SimBa residual MLP policy | 接触、平衡、地形与执行器约束 |

每帧 36 维计划由 29 个关节角、相对 pelvis translation 的 3 维和 quaternion 的 4 维组成。Generator 虽然预测 5 秒 horizon，却每约 0.33 秒重规划一次；tracker 只把计划当参考轨迹，而不是盲目逐帧复现。

这种时间尺度分工很务实：VLM 不进入硬实时控制环，generator 的延迟被异步规划吸收，50 Hz tracker 则留在 Jetson Orin NX 上以严格周期运行。

*来源定位：论文 §III、Appendix §B、§C、§D、§E，Fig. 2、Fig. 6、Table IX。*

## 3. 仿真数据引擎，以及“无人工数据”的边界

**Figure 3. 数据生成与训练流水线。**

![](https://arxiv.org/html/2611.06908v1/data_pipeline.png)

流水线先把每个任务写成 motion segments、waypoints 和 terminal keyframes，再调用 Kimodo 生成候选全身运动；前向运动学 verifier 检查 foot skating、穿地、腾空、关节越界等问题。随后，轨迹和目标物体被放进 Infinigen 程序化房间，快速 rasterizer 重放运动并渲染 hardware-matched fisheye RGB，最后施加视觉 domain randomization。

主文把数据规模约写为 300 小时；Appendix Table IV 给出精确规模：**162,698 episodes、296.3 小时、1,000 个训练房间**。生成与渲染 50,000 个 Sit episode 并缓存 VLM feature 约需 250 张 H100 运行 9 小时；完整主数据生成报告为 250 张 H100 运行 48 小时，generator 训练使用 64 张 B200。

| Skill | Episodes | Hours | 人工或外部先验 |
| --- | ---: | ---: | --- |
| Sit | 25,349 | 50.0 | 终止姿态来自真实 G1 joint-state log |
| Go-To | 50,000 | 47.1 | standing pose + 预定义目标类别 |
| Door | 29,207 | 50.0 | 5 个 hand-edited keyframes |
| Crawl | 19,066 | 50.0 | 手机人体视频 → GVHMR/GMR → 手工编辑 keyframes |
| Crouch | 19,369 | 49.2 | 手机人体视频 → GVHMR/GMR → 手工编辑 keyframes |
| Push | 19,707 | 50.0 | 真人 motion-capture push 片段 |
| **Total** | **162,698** | **296.3** | 六类技能均依赖一次性 task authoring |

因此，“data scales with compute rather than human labor”只在**episode 级扩增**上成立。更准确的表述是：HALO 去除了每条 trajectory 的 teleoperation 和部署房间扫描，但没有去掉 skill definition、关键姿态、人体运动先验或人工 motion capture。论文自己在 Limitations 中也承认：新增任务仍需人写 prompt 和 author keyframes。

*来源定位：论文 §III-A、§IV-A、Appendix §A，Table IV；“人工先验”逐项来自 Table IV 与 Appendix §A3。*

## 4. Motion generator：Flow matching 与 clean-prefix RTC

Generator 的 encoder 是冻结的 Qwen3.5-2B，decoder 是 8 blocks、width 512、8 heads 的 DiT。VLM 产生 image/text conditioning tokens，DiT 把 150 帧噪声计划迭代成 150 × 36 的运动；只有 projection 与 decoder 参与训练，共 49.3M 参数，推理使用 15 步 Euler sampler。

给定标准化后的真实计划 $x_1$、Gaussian noise $x_0$ 和 $s\sim\mathrm{Beta}(1.5,1)$，训练路径为：

$$
x_s=s\,x_1+(1-s)\,x_0.
$$

网络 $v_\phi$ 预测速度 $x_1-x_0$。异步执行时，机器人已经承诺执行的前 $P=15$ 帧不能被下一次采样改写，因此这 15 帧直接作为 clean tokens；模型只对余下 $H-P=135$ 帧去噪：

$$
\mathcal{L}(\phi)=\mathbb{E}\left[\frac{1}{D(H-P)}\sum_{\tau=P+1}^{H}
\big\|v_{\phi}(\tilde{x}_s,\tilde{s},c)_\tau-(x_1-x_0)_\tau\big\|^2\right],
$$

其中 $H=150$、$D=36$。推理时，新 plan 的前 15 帧直接复制当前 plan 接下来将执行的 15 帧；每一步 Euler 更新后都再次覆盖这个 prefix。因此计划交换点不是“被 guidance 鼓励连续”，而是由输入构造保证从同一个已承诺前缀继续。

这比 inference-time RTC 更适合 onboard 系统：后者每个 denoising step 都要额外算 guidance gradient，仍不能严格保证连续；训练时 conditioning 把连续性变成模型任务本身。

*来源定位：论文 §III-B、Appendix §B1–B2、Table V。*

## 5. Motion tracker：从 privileged experts 到 unified real-world policy

**Figure 6. Tracker 在 Orin NX 上融合 depth、proprioception 与 motion plan。**

![](https://arxiv.org/html/2611.06908v1/tracker_architecture.png)

训练分三阶段：

1. **Privileged experts**：每个 skill 单独训练 PPO expert，观察 proprioception、未来 10 帧计划和 ground-truth local height map；对 Push 等 interaction skill 额外加入 hand proximity 与 object displacement reward，避免“姿态正确、物体没动”。
2. **Multi-teacher distillation**：把多个 expert 蒸馏成单一 student，只能使用 onboard motion plan、depth、proprioception 与 IMU；采用 BC + DAgger，让每个 simulation instance 始终由对应 skill teacher 监督。
3. **Multi-critic PPO fine-tuning**：共享 actor，但每个 skill 保留独立 critic 和独立 advantage normalization，避免不同 reward scale 让单一技能主导更新。

Sim-to-real 的关键不是泛泛的 domain randomization，而是把实际硬件失败模式显式塞进训练：actuator inertia 和 torque limit、15–40 ms command latency、friction、柔性地面、camera offset、depth dropout/speckle/frame delay，以及深蹲时膝关节负机械功率限制。论文的部署观察也指出，simulation reward 与真机稳定性相关性较弱，action-rate smoothness 反而更能预测 transfer。

*来源定位：论文 §III-C、Appendix §C、Tables VI–VIII、§G2。*

## 6. Orchestrator 与 onboard system

Orchestrator 并不直接生成动作，而是把 free-form request 映射到固定 vocabulary：`go_to_chair`、`go_to_box`、`go_to_human`、`sit`、`crouch_under`、`crawl_through`、`sidewalk`、`push_box`、`stand`、`hold`。其中 `stand` 与 `hold` 不调用 generator，只构造站立或保持 pose 的参考轨迹。

它以闭环方式决定“继续当前 subtask、进入下一步、还是重试”，默认使用 Mac mini M4 Pro 上的 Qwen3.6-35B-A3B 4-bit MLX，也可选云端模型。所谓开放语言能力主要发生在**固定技能库前的语义映射**；运动 generator 的训练语料只有 10 条固定 instruction。

系统完全 onboard：Mac mini 处理 120° OAK-1W RGB、orchestrator 与 generator；Jetson Orin NX 运行 50 Hz PREEMPT_RT tracker，并把 RealSense D435i 的 raw stereo IR 交给 TensorRT LiteAnyStereo 得到 depth。Measured generator inference 约 155 ms，orchestrator transition 单独运行约 0.72 s、与 generator co-serve 时约 1.46 s。

*来源定位：论文 §III-D、Appendix §D–E，Tables IX–X；10 条 generator instruction 来自 Appendix §A。*

## 7. 实验：单任务证据强，多任务证据仍薄

**Table II. Held-out environment success rate（%）。**

| Category | Task | Sim | Real |
| --- | --- | ---: | ---: |
| Single | Go-To | 98 | 92 |
| Single | Sit | 84 | 85 |
| Single | Door | 91 | 93 |
| Single | Crouch | 95 | 100 |
| Single | Crawl | 84 | 90 |
| Single | Push | 93 | 88 |
| **Single mean** |  | **91** | **91** |
| Multi | Door → Go-To | 71 | 100 |
| Multi | Crouch → Sit | 73 | 60 |
| Multi | Crouch → Go-To → Push | 64 | 50 |
| **Multi mean** |  | **69** | **70** |

单任务评测覆盖 100 个 held-out simulation environments 和 6 个此前未扫描的真实环境；每个任务在每个环境 10 次，共 **6,000 sim + 360 real trials**。这一部分是论文最扎实的证据：技能定义明确、trial 数量充足、真机环境确实未用于训练或 reconstruction，而且 sim/real 平均值同为 91%。

多任务则不能同等解读。它只有 3 条固定 sequence；simulation 使用 50 个环境，而 real-world 只在 **1 个环境中每条 sequence 运行 10 次**。70% 表明系统可以在线串联技能，但不足以支持广义 long-horizon autonomy。

**Figure 10. 不同人物、桌子和座椅上的真实运行。**

![](https://arxiv.org/html/2611.06908v1/real_gallery_generalization.png)

**Video. 官方项目页汇总演示。**

<video src="https://apple-aiml-research.github.io/ml-halo/assets/promo/halo_promo.mp4?v=20261104a" controls muted playsinline width="720"></video>

*来源定位：论文 §IV-C–D、Table II、Appendix §F2；媒体来自论文 Fig. 10 与官方项目页。*

## 8. Ablation：什么真正起作用

Table III 在 held-out Sit task 上给出四组关键结果：

| 变量 | 配置 | Success rate |
| --- | --- | ---: |
| Training scenes | 1 / 10 / 100 / 1,000 | 43 / 64 / 81 / 84 |
| Real-time chunking | training-time / inference-time / w/o | 84 / 66 / 24 |
| Generator decoder | flow matching / regression | 84 / 19 |
| Motion tracker | w/ depth / w/o depth | 84 / 74 |

最有信息量的结论有三点：

- **环境 diversity 的收益快速饱和**：1 → 100 scenes 带来 +38 点，100 → 1,000 只有 +3 点。至少对 Sit，前 100 个环境覆盖了大部分重要变化；继续 scale scene 数量不是唯一瓶颈。
- **计划连续性是必要条件**：完全无 RTC 只剩 24%；inference-time RTC 为 66%，仍比 clean-prefix training 低 18 点。
- **Flow matching 的 65 点优势存在混杂变量**：regression decoder 不仅改变生成分布，也无法直接使用 diffusion RTC，因此同时失去异步连续性；这个对照不能证明“多模态生成”本身贡献了全部差距。

Depth ablation 从 84% 降到 74%，说明 tracker 的 near-field geometry 确实能修正上游 kinematic plan 未建模的地形，但不是系统性能的唯一来源。

*来源定位：论文 §IV-E、Table III。*

## 9. Failure cases、局限与可扩展性

1. **目标离开 FOV 就会断链**：多任务失败常发生在前一个 skill 结束时朝向异常，下一目标不在视野内。Crouch → Go-To → Push 的 5 个失败 trial 中有 3 个在 crouch 后头部背向 box；系统没有 search、turn-in-place 或 persistent spatial memory。
2. **没有 tactile/world-state interface**：目标被遮挡或离开相机后，策略无法直接感知接触；tracker 只知道“跟踪什么姿态”，不知道计划想对世界产生什么效果。
3. **技能增加仍是人工线性成本**：每个新 physical task 都要设计 prompt、segment chain、keyframes、filter 与 reward。程序化场景放大已有技能，不会自动发明技能。
4. **语言存在 shortcut 风险**：训练中“看见 chair”通常就对应 Sit，fine-tuned VLM 会忽略 instruction；作者需把 30% 样本 RGB 替换成黑帧才恢复语言依赖。冻结 encoder 对新人物反而更泛化。
5. **评测离开放世界仍远**：技能只有六类，multi-task 最长三步，没有物体搜索、探索、空间记忆、复杂 manipulation 或任务级错误恢复。

这也提示下一步研究不只是继续扩数据：更关键的是让 generator–tracker interface 带上 intended world state，让 orchestrator 拥有可更新的 spatial memory，并用主动 perception/search 把“看不见目标”从终止失败变成恢复行为。

*来源定位：论文 §IV-D、§V-1、Appendix §G1–G2。最后一段为 Codex 推断。*

## 关联工作

### 对比

- [[2610-Workhorse|Workhorse]]：同样追求真实世界长时任务，但更强调通用 VLA/策略层的能力扩展；HALO 选择有限技能库和显式 trajectory interface，真机控制链更清楚，开放任务性更弱。
- [[2512-WholeBodyVLA|WholeBodyVLA]]：都是视觉语言驱动的 humanoid whole-body control。HALO 没有端到端从语言到关节，而是把 VLM 语义、kinematic generation 与 physical tracking 分层。
- [[2503-GR00TN1|GR00T N1]]：GR00T N1 代表通用 robot foundation model 路线；HALO 更像为单一 embodiment 精心打造的完整 autonomy stack，强项是落地闭环而不是 cross-embodiment foundation capability。

### 方法相关

- [[2505-DreamGen|DreamGen]]：共同利用生成模型扩大 motion/data coverage。HALO 进一步把 generated motion 放进程序化房间，配对 egocentric vision 和 language，再用独立 tracker 吸收动力学误差。
- Flow matching + training-time action conditioning：前者建模多解的全身计划，后者解决 streaming action chunk 的连续交换；从 ablation 看，二者不能被简单合并成单一“diffusion 更强”的结论。
- Infinigen + Kimodo：分别提供环境分布与 motion prior。HALO 的贡献是把两者通过 placement、verification、rendering 和分层 policy training 组织成可扩展数据引擎。

## 论文点评

### Strengths

1. **真机证据扎实**：6 个真实环境、360 次单任务 trial、清楚的 success definition，比只展示少量 cherry-picked video 的 humanoid 工作可信得多。
2. **系统设计诚实且工程闭环完整**：从数据生成、generator、tracker、orchestrator 到 onboard dual-compute deployment 都有具体实现和延迟数字。
3. **关键接口有洞察**：dense trajectory 把语义规划与动力学控制解耦；clean prefix 把异步 continuity 从推理期补丁变成训练目标。
4. **Sim-to-real 不停留在口号**：真实执行器延迟、negative knee power、柔性 carpet、低摩擦、depth artifacts 都被纳入设计，并报告了来自真机部署的观察。

### Weaknesses

1. “Generalist” 表述超过证据：物理 repertoire 只有 6 类，训练 corpus 只有 10 条 generator instruction，orchestrator 的自由语言最终落入固定 subtask vocabulary。
2. “Simulation removes human labor” 容易误导：它去掉逐 episode 操作，却仍依赖 task authoring、真实 G1 log、手机人体视频、手工 keyframe 和 motion capture。
3. 多任务真机评测只有 1 个环境、3 条 sequence、每条 10 次；最多三步不足以刻画真正 long-horizon error accumulation。
4. Regression ablation 与 RTC 能力绑定，无法干净拆分 generative modeling 和 plan continuity 的各自贡献。
5. 代码仓缺少论文使用的数据、generator checkpoint 与 tracker weights，公开代码尚不能复现论文主结果。

### 可信评估

#### Artifact 可获取性

- **代码**: inference+training；官方仓包含 datagen、generator、三阶段 tracker training、orchestrator、simulation/real launchers 与 C++ real-time deployment。
- **模型权重**: 未发布 HALO generator checkpoint 或 tracker weights；仓库明确写明 `No weights ship with the repository`。Qwen/Kimodo 等第三方基础模型需另行取得。
- **训练细节**: 网络结构、主要超参、reward、domain-randomization 范围和训练命令较完整；但无法仅靠仓库 artifact 对齐论文 checkpoint。
- **数据集**: 论文训练集未发布；公开 datagen 只覆盖 `sit_on_chair` 示例/流程，其他任务仍需自建数据。

#### Claim 可验证性

- ✅ **真机单任务 91%**：论文给出逐任务结果、成功条件、6 个环境和 360 次 trial；官方项目页提供大量运行视频。该结论有强内部证据，但尚无第三方复现。
- ✅ **训练时 clean-prefix 优于 inference-time/no RTC**：Table III 分别为 84/66/24%，对 continuity 的必要性支持明确。
- ⚠️ **“generalist humanoid autonomy”**：真实证据只覆盖 6 类原子技能和 3 条短序列，开放语言没有扩展底层物理能力边界。
- ⚠️ **“数据与 human labor 解耦”**：逐 episode 扩增确实自动化，但 motion/keyframe/task 先验仍含明显人工来源。
- ⚠️ **flow matching 远胜 regression**：84% 对 19% 的数值成立，但 regression 同时不能使用 RTC，因果归因不干净。
- **无明确 ❌ 营销话术**：主要问题是 claim scope 偏宽，而不是结果数字与论文证据直接冲突。

### Notes

- 值得复现实验的最小问题不是整套 HALO，而是：在同一 decoder capacity 下，把 stochasticity 与 clean-prefix continuity 分离，比较 flow matching、deterministic regression + prefix conditioning、以及 consistency-style one/few-step generator。
- 更根本的架构问题是 tracker 是否应接收“希望世界发生什么”而不只是“身体应到哪里”。把 object-state goal 或 contact intent 加进 interface，可能比继续堆视觉随机化更能扩展 manipulation。
- HALO 与现有 spatial-memory gap 高度一致：如果下一目标不在当前 egocentric frame 中，VLM 的语义能力也无法补偿缺失的可检索世界状态。

### Rating

**Metrics** (as of 2026-11-07): citation=0, influential=0 (N/A; total citation=0), velocity=0.0/mo; HF upvotes=N/A（paper API 404）; github 159⭐ / forks=13 / 90d commits=3 / pushed 1d ago

**分数**：2 - Frontier

**理由**：这是当前 simulation-to-real perceptive humanoid 的重要系统参考：91%/360 次真机单任务结果、完整的三层接口和 clean-prefix 设计都值得后续工作比较。它尚不够 3 - Foundation，因为发布时间极短，底层技能和长时评测范围有限，且训练数据与论文权重未发布；社区影响与可复现性都仍待时间验证。
