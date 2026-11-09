---
type: paper
title: "SLA: Scaling Spatial-Language-Action Model via Continual Pre-training"
authors: [Fuhao Li, Wenxuan Song, Qizhou Huang, Ziyang Zhou, Jingbo Wang, Junwu E, Pengwei Wang, Yan Wang, Shunbo Zhou, Haoang Li]
institutes: [The Hong Kong University of Science and Technology (Guangzhou), OLA Dimensions, Beijing Academy of Artificial Intelligence, Tsinghua University]
date_publish: 2026-11-05
venue: arXiv
primary_domain: embodied-ai
domains: [embodied-ai]
tags: [VLA, spatial-reasoning, manipulation, cross-embodiment]
review_status: reviewed
arxiv_id: 2611.08373
paper: https://arxiv.org/abs/2611.08373
website: https://sla-team.github.io/omnisf_projectpage/
github: https://github.com/OpenHelix-Team/Spatial-Forcing/tree/master/SLA
rating: 2
date_added: 2026-11-09
---

## Summary

> [!summary] SLA: Scaling Spatial-Language-Action Model via Continual Pre-training
> - **核心**: 把 training-only 的 3D feature alignment 从 task-specific post-training 扩展到 [[2504-Pi05|π0.5]] continual pre-training，使空间能力成为可迁移的 foundation representation，而不改变部署时的 policy architecture。
> - **方法**: 冻结 OmniVGGT 作为 spatial teacher，用 cosine loss 对齐 VLA 多层 visual tokens；配合 adaptive layer gating、25% state dropout、统一 EEF action 与 rotation-vector 表示。
> - **结果**: RoboTwin Clean2Random 从 π0.5 的 46.0% 提升到 72.3%，八个私有真机条件平均从 59.8% 提升到 83.8%；但 Open/long-horizon 任务仍弱，当前公开配置也未完整实例化论文的 adaptive/calibrated recipe。
> - **Sources**: [paper](https://arxiv.org/abs/2611.08373) | [website](https://sla-team.github.io/omnisf_projectpage/) | [github](https://github.com/OpenHelix-Team/Spatial-Forcing/tree/master/SLA)
> - **Rating**: 2 - Frontier（空间监督 continual pre-training 的强 baseline 与当前 SOTA recipe，但发布仅四天、因果归因和完整复现仍不足以成为 Foundation）

**Key Takeaways:**

1. **SLA 不是新的 3D inference architecture**: 它本质上是 privileged spatial feature distillation；OmniVGGT、projector 和 gates 只在训练时存在，部署仍是原始 RGB + language + state 的 π0.5。
2. **真正的贡献是把 spatial alignment 移到 foundation stage**: full-data RoboTwin Clean2Random 中，两阶段 alignment 达 72.3%，高于仅 continual pre-training 的 63.2%、仅 post-training 的 57.1% 和完全不对齐的 48.2%。
3. **训练 recipe 与方法本身强耦合**: state dropout、rotation representation、统一 action coordinates 和数据筛选都带来大幅变化；不能把全部提升简单归因于 3D alignment。
4. **最强证据在 randomized manipulation，不在 open-world autonomy**: RoboTwin Clean2Random 很强，但 RoboDojo-Sim Open SR 仅 1.9%，Long-Horizon SR 仅 11.9%。
5. **公开 artifact 尚未闭环**: code、base checkpoint 和 benchmark checkpoints 已发布；processed continual-pretraining corpus 未发布，公开配置固定第 12 层且关闭 camera/depth teacher input。

**Teaser. SLA 用 heterogeneous robot data 和 frozen 3D teacher 塑造 VLA visual representations。**（论文 Figure 1；[source](https://arxiv.org/html/2611.08373#S1.F1)）

![](https://sla-team.github.io/omnisf_projectpage/assets/teaser.webp)

---

## 1. Problem Framing

[[2504-Pi05|π0.5]] 一类 2D VLA 从 image-text pre-training 继承 semantic knowledge，却主要靠 robot demonstrations 间接学 3D control。已有 PointVLA、GeoVLA、BridgeVLA 和 FALCON 将 depth、point cloud 或 geometry tokens 显式接入 policy，但会增加部署传感器、feature extractor 或 architecture 依赖。Spatial Forcing 改用 training-only representation alignment，却只发生在下游 post-training，空间能力仍像 task-specific add-on。SLA 的问题定义是：**能否用大规模 robot experience 在 continual pre-training 阶段内化空间表示，再在下游继续强化，同时保持原始 inference graph？**（论文 §1、§2.2；[source](https://arxiv.org/html/2611.08373#S1)）

这个 framing 与 MindFlow 的既有判断一致：VLA 的主要杠杆往往是 data recipe 和 representation shaping，而非扩大模型；SLA 进一步把 spatial teacher 变成 continual-pretraining supervision。这里的“空间理解”是隐式 visual representation，不是可查询的 metric map、scene graph 或 persistent spatial memory。（论文笔记：[[2504-Pi05|π0.5]]；Codex 推断：[[DomainMaps/SpatialRep|Spatial Representation]]）

## 2. Method

### 2.1 Training-only spatial alignment

给定多视角 RGB 图像集合 $\mathcal{I}$，冻结的 3D teacher $f^{\mathrm{3D}}$ 输出 pixel-level spatial features；若样本带 camera intrinsics、extrinsics 或 depth，OmniVGGT 可以一并利用，缺失时用 placeholder/multimodal fusion 退化到 RGB-only。teacher feature 加 positional encoding 后，被 bilinear resample 到 VLA visual-token resolution：（论文 §3.2.1–3.2.2，Eq. 3；[source](https://arxiv.org/html/2611.08373#S3.SS2.SSS1)）

$$
\mathbf{y}=\mathcal{R}\Big[f^{\mathrm{3D}}(\mathcal{I})+E\Big].
$$

其中 $\mathbf{y}$ 是与每个 VLA visual token 同 view、同 image location 的 teacher target，$\mathcal{R}$ 是 bilinear resampling，$E$ 保留 spatial position order。

VLA 第 $\ell$ 层的 visual token ${}^{(\ell)}\mathbf{x}^{\mathcal V}_i$ 先经 shared LayerNorm 和 two-layer MLP，再由 token- and channel-wise gate 聚合：（论文 §3.2.1、§3.2.3，Eq. 4、7；[source](https://arxiv.org/html/2611.08373#S3.SS2.SSS3)）

$$
\begin{aligned}
{}^{(\ell)}\mathbf{g}_i
&=\sigma\Big(W_g{}^{(\ell)}\mathbf{x}^{\mathcal V}_i+\mathbf{b}_g\Big),\\
\mathbf{z}_i
&=\sum_{\ell=1}^{L}{}^{(\ell)}\mathbf{g}_i\odot
\operatorname{MLP}\Big(\operatorname{LN}({}^{(\ell)}\mathbf{x}^{\mathcal V}_i)\Big).
\end{aligned}
$$

最终使用 per-token cosine loss，并与 π0.5 flow-matching action loss 联合优化：（论文 §3.2.1，Eq. 5–6；[source](https://arxiv.org/html/2611.08373#S3.E5)）

$$
\begin{aligned}
\mathcal{L}_{\mathrm{align}}
&=\frac{1}{N}\sum_{i=1}^{N}\Big[1-\cos(\mathbf{z}_i,\mathbf{y}_i)\Big],\\
\mathcal{L}
&=\mathcal{L}_{\mathrm{action}}+\alpha\mathcal{L}_{\mathrm{align}}.
\end{aligned}
$$

论文没有给出 $\alpha$ 的具体值；截至 2026-11-09，公开 pre-training 与 benchmark configs 使用 `align_loss_coeff=0.5`。（代码证据：[pretrain.py L140–150](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/src/openpi/external_config/pretrain.py#L140-L150)）

**Figure 2. Depth linear probing：alignment 后的 VLA visual embedding 能恢复更清晰的 depth structure。**（论文 §3.1，Figure 2；[source](https://arxiv.org/html/2611.08373#S3.F2)）

![](https://arxiv.org/html/2611.08373v1/Figures/fig_probing.png)

> [!important] Inference boundary
> Spatial teacher、alignment projector 和 adaptive gates 全部在训练结束后丢弃；normal benchmark inference 不需要 depth 或 camera calibration。RoboDojo 的 memory variant 是例外：它在 inference 额外输入历史图像，见 §5.3。

### 2.2 Adaptive layer selection

PaliGemma language backbone 有 18 层。不同 domain 的 low-level geometry 与 task context 可能分布在不同深度，因此论文没有手选单层，而是让每个 token、每个 channel 的 gate 从所有层加权取 feature。RoboTwin ablation 中，固定第 12 层是最佳单层（Clean2Random 67.3%），adaptive fusion 达 72.3%，提升 5.0pp；最后一层只有 64.6%，说明“越深越 spatial”不成立。（论文 §4.4.2，Table 7；[source](https://arxiv.org/html/2611.08373#S4.T7)）

### 2.3 State dropout

Robot state 很精确，也很容易成为 demonstration trajectory shortcut。SLA 对每个训练样本以概率 $p$ 整段移除 state tokens，保留 images 与 instruction；inference 恢复正常 state input。RoboTwin post-training 的最佳值是 $p=25\%$，其 Clean2Random 为 72.3%，而 $p=0$ 只有 20.7%；$p=50\%,75\%,100\%$ 分别为 41.3%、51.6%、50.9%，呈明显非单调关系。（论文 §3.2.4、§4.4.3，Table 8；[source](https://arxiv.org/html/2611.08373#S4.T8)）

> [!warning] Attribution caveat
> 这是全文最大的局部 sensitivity，甚至大于 alignment 的单项差异。它支持“视觉依赖很重要”，但也意味着 headline 增益是 spatial alignment、state masking 与整体 data/action recipe 的组合结果，不能只归因于 teacher alignment。

### 2.4 Unified state and action representation

跨 morphology 统一 joint coordinates 很困难，作者改用 robot-centered absolute EEF state 与 chunk-wise delta EEF action。单臂原点设在 arm base，双臂设在两 arm bases 中点，坐标轴统一为 forward $+x$、left $+y$、up $+z$。每个 chunk 内所有 target 都相对 chunk 起始 pose $(\mathbf p_0,R_0)$：（论文 §3.3.2，Eq. 8–10；[source](https://arxiv.org/html/2611.08373#S3.SS3.SSS2)）

$$
\Delta\mathbf p_t=\mathbf p_t-\mathbf p_0,\qquad
\Delta R_t=R_tR_0^\top,\qquad
\Delta\mathbf r_t=\operatorname{Log}(\Delta R_t)^\vee.
$$

Rotation vector 在 RoboTwin 上达到 79.2% average，优于 quaternion 74.3%、Euler 65.5% 和 Rot6D 62.9%；四者都使用 SO(3) composition，因而该实验隔离的是 representation，而不是“composition vs subtraction”。作者还采用 per-channel normalization，尽管 rotation vector 物理上可共享一个 scale。（论文 §4.4.4，Table 9）

**Figure 3. 直接相减 Euler angle 会在 $\pm2\pi$ 附近产生 wrap outlier，压缩 quantile-normalized typical actions。**（论文 §3.3.2，Figure 3；[source](https://arxiv.org/html/2611.08373#S3.F3)）

![](https://arxiv.org/html/2611.08373v1/rotataion_action_distribution.png)

## 3. Continual-pretraining Corpus and Compute

论文汇总的六个 public source datasets 原始规模约 1.714M episodes、1,504 tasks、14,330 hours。**Table 1 明确说明这些是 selection 和 processing 前的 source statistics，不是实际训练集大小。**（论文 §3.3.1，Table 1；[source](https://arxiv.org/html/2611.08373#S3.T1)）

| Data source | Source episodes | Tasks | Hours | Role |
| --- | ---: | ---: | ---: | --- |
| InternData-A1 | 630K | 70 | 7,430 | scripted simulation；scene/asset/texture diversity |
| AgiBotWorld-Beta | 168K | 217 | 2,970 | real-world two-finger manipulation |
| RoboCasa365-Pretrain | 630K | 300 | 2,090 | simulated kitchen atomic/composite/MimicGen |
| RoboCOIN | 183K | 808 | 1,300 | heterogeneous real bimanual platforms |
| DROID | 95K | 86 | 510 | real Franka, varied environments |
| MolmoAct | 7.9K | 23 | 30 | focused real Franka tasks |
| **Total before processing** | **1,713.9K** | **1,504** | **14,330** | — |

为避免 repetitive simulation data 主导 mixture，作者按 task/source 下采样完整 episodes：InternData-A1 的部分高重复 task 留 3%，其他留 10%；RoboCasa365 MimicGen 留 0.5%，composite 留 15%。此外排除 dexterous hand、mobile-base motion、异常 arm speed 和可识别的 idle frames，并声明去除会造成 downstream leakage 的 benchmark data。（论文 §3.3.2，Downsampling / Filtering）

> ❓ 论文没有给出 filtering 后每个 source 的最终 episode/frame/hour 数，也没有完整披露 sampling weights。因而“14,330h continual pre-training”不能理解为模型实际遍历了 14,330 小时去重数据。

Continual pre-training 从 π0.5 checkpoint 初始化，训练 36K optimizer steps；microstep global batch 2,304，accumulate 2 次得到 effective batch 4,608。学习率先在 1K steps warm up 到 $5\times10^{-5}$，30K steps cosine decay 到 $1\times10^{-5}$，之后保持常数。总耗时约 110 小时、48 张 H100，即约 5,280 H100-hours；论文未给 vanilla continual-pretraining control 的 wall-clock，也未量化 OmniVGGT teacher 的额外成本。（论文 §4.2；[source](https://arxiv.org/html/2611.08373#S4.SS2)）

## 4. Main Results

### 4.1 Public benchmarks

| Benchmark | Downstream protocol | SLA | Primary comparison | Reading |
| --- | --- | ---: | ---: | --- |
| LIBERO-Plus | standard LIBERO demos；10,030 perturbed rollouts | **87.4%** | π0.5 84.4%; Spatial Forcing 85.1% | gain is broad but modest; only +0.3pp over Qwen-RobotManip |
| RoboTwin 2.0 Clean2Random | 50 tasks × 50 clean demos/task；100 trials/task | **72.3%** | π0.5 46.0%; Spatial Forcing 62.6% | strongest evidence for scene/randomization robustness |
| RoboCasa-Panda | 24 tasks × 50 demos/task；3,600 trials | **68.4%** | Spatial Forcing 67.6%; Cosmos Policy 67.1% | data-efficient but margin is <1.5pp |
| RoboDojo-Real | one policy, 18 tasks, 3 embodiments | **33.9% SR** | π0.5 12.8%; InternW0-$\Delta$ 31.7% | meaningful relative gain, but absolute completion remains low |

Sources: 论文 §4.1、§4.3，Tables 2–5（[LIBERO-Plus](https://arxiv.org/html/2611.08373#S4.T2)、[RoboTwin](https://arxiv.org/html/2611.08373#S4.T3)、[RoboCasa](https://arxiv.org/html/2611.08373#S4.T4)、[RoboDojo-Real](https://arxiv.org/html/2611.08373#S4.T5)）。不同工作可能使用不同 pre-training data、checkpoint 和 demo budget；除表内明确 protocol 外，不宜把所有 row 当作严格 controlled comparison。

### 4.2 Scaling and stage interaction

RoboTwin Clean2Random 的数据 scaling 是全文最能支持核心 claim 的实验。所有曲线从同一个 π0.5 起点出发，continual-pretraining data 按 task 内 demonstrations 构造 5%、25%、50%、100% 子集，再分别开关 pre-/post-training alignment：（论文 §4.4.1，Table 6、Figure 4；[source](https://arxiv.org/html/2611.08373#S4.T6)）

| Alignment in continual pre-train | Alignment in post-train | 5% | 25% | 50% | 100% |
| --- | --- | ---: | ---: | ---: | ---: |
| ✗ | ✗ | 43.8 | 46.5 | 46.1 | 48.2 |
| ✗ | ✓ | 45.6 | 53.4 | 55.3 | 57.1 |
| ✓ | ✗ | 46.6 | 52.0 | 58.4 | 63.2 |
| ✓ | ✓ | **49.2** | **60.5** | **67.4** | **72.3** |

两阶段都对齐时，从 5% 到 100% 数据增加 23.1pp；完全不对齐只增加 4.4pp。full data 时，joint 比 pre-only 高 9.1pp、比 post-only 高 15.2pp。这个结果支持“spatial supervision 使 data scaling 变得有效”，但尚不足以建立 scaling law：只有一个 downstream benchmark、四个数据点、单次训练且没有误差条。

**Figure 4. 只有带 spatial alignment 的配置随数据量持续上升。**（论文 §4.4.1，Figure 4）

![](https://arxiv.org/html/2611.08373v1/fig_scaling.png)

### 4.3 Other ablations

| Ablation | Main result | What it supports | Remaining ambiguity |
| --- | --- | --- | --- |
| Adaptive layers | adaptive 72.3% C2R vs best fixed layer 12 at 67.3% | heterogeneous data benefits from multi-depth features | current public configs disable it |
| State dropout | 25% dropout 72.3% C2R vs 0% at 20.7% | proprioception shortcut is severe | not factorially crossed with no-alignment baseline |
| Rotation | rotvec 79.2% avg vs quaternion 74.3% | SO(3)-consistent target representation matters | improvement belongs to action recipe, not spatial teacher |
| Calibration | no align 31.8% avg; RGB-only OmniVGGT 42.8%; +calibration 46.0% | teacher is useful without calibration; calibration adds 3.2pp | conducted on personally collected RoboTwin clean data |

Sources: 论文 §4.4.2–4.4.5，Tables 7–10。

### 4.4 Private real-world deployments

八个 conditions A–H 覆盖 bimanual handover、物体被人抛出后的 recovery、moving target、10-shot Franka adaptation、table-height shift、moving table 和 unseen black tape instruction following。SLA 在全部 conditions 都是表中最高，平均 83.8%，相比 π0.5 的 59.8% 提升 24.0pp。（论文 §4.5，Table 11；[source](https://arxiv.org/html/2611.08373#S4.T11)）

| Condition | π0.5 | Spatial Forcing | SLA |
| --- | ---: | ---: | ---: |
| A: bimanual vegetable handover | 74 | 84 | **94** |
| B: retrieve human-thrown fruit | 52 | 66 | **82** |
| C: grasp human-moved fruit | 42 | 58 | **76** |
| D: 10-shot Franka adaptation | 48 | 62 | **78** |
| E: base bottle scene | 90 | 94 | **98** |
| F: changed table height | 68 | 64 | **84** |
| G: moving table | 44 | 60 | **78** |
| H: unseen black tape instruction | 60 | 56 | **80** |

**Video. Condition C：目标在 grasp 过程中被人移动。**（project page；[source](https://sla-team.github.io/omnisf_projectpage/#real-world)）

<video src="https://sla-team.github.io/omnisf_projectpage/video/grasp_banana.mp4" controls muted playsinline width="720"></video>

这些结果有现实意义，但统计独立性弱于表面上的“50 instances/task”：A、B、D 各是 10 rollouts × 5 objects，同一 rollout 内的五个 object outcomes 相关。论文也未报告多个 training seeds、policy-to-policy variance 或 confidence interval。（Codex 推断，protocol 见论文 §4.1）

## 5. Failure Cases and Boundaries

### 5.1 Randomization remains task-dependent

RoboTwin 的 mean 从 Clean2Clean 85.96% 降到 Clean2Random 72.34%，但 task gap 很不均匀：Place Cans Plasticbox 从 96% 降到 40%，Handover Block 从 91% 降到 38%，Pick Dual Bottles 从 97% 降到 55%；与此同时 Grab Roller 与 Shake Bottle 保持 100%。这说明 aggregate SOTA 不等于 uniformly robust spatial representation。（论文 Appendix A.1，Table 12）

### 5.2 Cross-embodiment performance is uneven

RoboDojo-Real 中 ARX X5 / Piper / Piper X 的 SR 分别为 38.3% / 53.3% / 10.0%。Piper X 六项里只有 `classify_objects` 40% 与 `pack_objects_into_backpack` 20% 有完整成功，其余四项为 0%。单一 policy 的多 embodiment transfer 成立，但远未均衡。（论文 Appendix A.3，Table 14）

### 5.3 RoboDojo results include a memory mechanism

为处理 long-horizon RoboDojo tasks，作者在 post-training 与 inference 额外输入九张 main-camera history frames：episode 初始帧 + 过去八秒每秒一帧。每帧经 SigLIP 变成 256 tokens，并与当前三视角、语言 tokens 一起进入 prefix；memory frames 不参与 spatial alignment。该机制增加 inference context/compute，所以 RoboDojo headline 不能完全归因于“原始 π0.5 architecture + SLA training”。（论文 Appendix B，Eq. 11；[source](https://arxiv.org/html/2611.08373#A2)）

### 5.4 Open and long-horizon capability is still weak

RoboDojo-Sim 平均 Score/SR 只有 16.4/12.0。按 capability 分解：Generalization SR 9.4%、Precision 11.2%、Long-Horizon 11.9%、Memory 25.8%、Open 1.9%。Open 八项中只有 `general_pickup` 非零成功；randomized layout 也会造成显著崩塌，例如 `stack_bowls` 70%→10%，`pour_liquid_into_cup` 45%→15%。（论文 Appendix A.4，Tables 15–16）

因此 SLA 最准确的定位是：**提升 spatially perturbed manipulation 和 downstream adaptation 的 representation recipe，而不是解决开放世界任务发现、长程规划或 failure recovery。**（Codex 推断）

## 6. Artifact and Reproduction Status

截至 2026-11-09，官方已发布：[training/inference code](https://github.com/OpenHelix-Team/Spatial-Forcing/tree/master/SLA)、[`SLA_base`](https://huggingface.co/haofuly/SLA_base)、[`SLA_training_component`](https://huggingface.co/haofuly/SLA_training_component)、[`SLA_benchmark_ckpts`](https://huggingface.co/haofuly/SLA_benchmark_ckpts) 和 300-row real-world demo dataset。README 的 continual-pretraining data、RoboDojo-Real post-training/evaluation 与 training-efficiency optimization 仍标为 TODO。（代码证据：[README](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/README.md)）

当前公开实现存在三处需要明确记录的 paper–code gap：

1. **Adaptive gate 未在公开 configs 开启**：JAX `AlignProjector` 支持 all-layer gates，但 `pretrain.py`、LIBERO、RoboTwin 和 real-world configs 均为 `vla_adapt_layers_align=False`、`vla_layers_align=12`。（[projector](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/src/openpi/models/projectors.py#L18-L29)，[pretrain config](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/src/openpi/external_config/pretrain.py#L140-L142)）
2. **公开 path 未使用论文强调的 partial geometry**：configs 为 `use_camera_params=False`，feature extractor 初始化 OmniVGGT 时 `enable_depth=False`。代码支持 camera parameters，但发布配置没有启用。（[align_utils](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/src/openpi/training/align_utils.py#L124-L143)，[pretrain config](https://github.com/OpenHelix-Team/Spatial-Forcing/blob/master/SLA/src/openpi/external_config/pretrain.py#L147-L151)）
3. **processed corpus 未发布**：config 只引用本地 `Data/...` paths，README 未提供六源数据的完整 conversion/filter/downsample pipeline 或最终 mixture manifest。

这些差异不证明论文实验错误：公开 config 可能只是可运行示例，而非 paper-run exact config。但在作者补齐 config/data manifest 前，第三方无法无歧义重现 adaptive + heterogeneous-geometry 的完整 headline recipe。（Codex 推断）

## 关联工作

### 基于

- **[[2504-Pi05|π0.5]]**：直接初始化 checkpoint 与 inference backbone；SLA 保留 PaliGemma + flow-matching action expert，只改变 continual/post-training supervision。
- **Spatial Forcing**：同团队前作，将 VLA visual tokens 对齐到 frozen 3D teacher；SLA 的关键增量是 continual pre-training、adaptive layers、heterogeneous data curation 与 state dropout。
- **OmniVGGT / [[2503-VGGT|VGGT]]**：提供 multi-view spatial teacher。OmniVGGT 能吸收不完整 camera/depth annotations，SLA 只使用其 frozen intermediate representation。

### 对比

- **Explicit 3D VLA**：PointVLA、GeoVLA、BridgeVLA、FALCON 在 inference 显式输入 point cloud/depth/geometric tokens；SLA 以 training-only distillation 换取零 inference overhead。
- **[[2406-OpenVLA|OpenVLA]] / [[2502-OpenVLA-OFT|OpenVLA-OFT]]**：real-world deployment baselines；SLA 继承 π 系列连续 action path，而非 autoregressive raw-action path。
- **[[2510-XVLA|X-VLA]] / [[2503-GR00TN1|GR00T N1]] / [[2605-MolmoAct2|MolmoAct2]]**：代表 cross-embodiment、humanoid foundation 与 action reasoning 的其他主线；SLA 的差异是把 3D representation supervision 放在 foundation stage。

### 对 MindFlow research ideas 的影响

- **论文笔记**：[[2504-Pi05|π0.5]] 已显示 heterogeneous co-training 和 representation-shaping target 比单纯扩模型更重要；SLA 给出了 spatial supervision 版本的直接证据。
- **Codex 推断**：SLA 是 [[SpatialToken-VLA]] 必须比较的 strongest implicit baseline。后续应至少做 π0.5、SLA implicit alignment、explicit spatial tokens、两者结合四组；否则 explicit-token 收益可能只是复现了 teacher alignment 已能提供的 feature shaping。
- **Codex 推断**：SLA 不产生 object-centric、queryable 或 persistent representation，因此没有回答 [[DomainMaps/SpatialRep|Spatial Representation]] 中的 Nav+Manip shared representation 与 spatial memory 问题。

## 论文点评

### Strengths

1. **问题与方法匹配且 scalable**：用 frozen teacher 给已有 VLA 增加 supervision，不改 deployment architecture，避免显式 3D sensor/interface 对落地的约束。
2. **核心 stage ablation 有信息量**：pre-only、post-only、both、neither × data fraction 的设计比只报最终 SOTA 更能支持 continual-pretraining claim。
3. **数据与 action engineering 扎实**：EEF coordinates、SO(3) delta、downsampling、filtering、state dropout 都针对 cross-embodiment mixture 的真实 failure mode。
4. **评测覆盖面广**：三套 simulation benchmark、一套 public real benchmark、八个 private deployment conditions，并公开 per-task failure cases。
5. **训练期 privileged information 的边界清楚**：teacher 与 calibration 不进入 normal deployment，方法的 inference cost claim 对核心 SLA branch 成立。

### Weaknesses

1. **实际 continual-pretraining data scale 不透明**：source headline 是 processing 前统计，最终 corpus size、source weights、重复采样程度和 data manifest 均缺失。
2. **因果归因不完整**：state dropout 与 rotation representation 的 effect 极大，但没有 alignment × dropout × action representation 的 factorial study。
3. **统计不确定性缺失**：没有 training seeds、error bars 或 confidence intervals；private real-world 的 object-level samples 部分 clustered within rollout。
4. **“spatial understanding”定义偏行为化**：主要用 manipulation SR 证明，没有独立 geometric probing benchmark；depth probe 只给 qualitative visualization。
5. **跨 benchmark 增益不均匀**：RoboTwin 很强，LIBERO/RoboCasa margin 小；RoboDojo Open/Long-Horizon 和 Piper X 仍弱。
6. **公开实现与论文 recipe 不一致**：adaptive layers、camera/depth supervision 与 processed corpus 尚不足以完整复现 headline model。
7. **训练成本高且缺少 overhead breakdown**：约 5,280 H100-hours，但未对比 vanilla continual pre-training 或报告 teacher compute 占比。

### 可信评估

#### Artifact 可获取性

- **代码**: inference + training 已开源，基于 OpenPI 的 JAX path，并附 LIBERO-Plus、RoboTwin 与 private real-world 示例 config。
- **模型权重**: `SLA_base`、`SLA_training_component`、`SLA_benchmark_ckpts` 已发布；RoboDojo-Real release 仍在 README TODO。
- **训练细节**: optimizer steps、batch、LR schedule、state dropout、alignment coefficient 可从论文/代码获得；exact adaptive/calibrated paper config 与最终 data mixture 不完整。
- **数据集**: 六个 source datasets 是 public，但 processed continual-pretraining corpus/manifest 未发布；只发布 300-row real-world demo dataset。

#### Claim 可验证性

- ✅ **“training-only spatial alignment 不增加 normal inference structure”**：方法图、公式和公开代码均将 teacher/projector 隔离在 training path。
- ✅ **“continual + post 两阶段 alignment 优于单阶段”**：Table 6 在所有四个 data fractions 上一致成立。
- ✅ **“RoboTwin randomization 显著提升”**：50 tasks × 100 trials/task，π0.5 46.0% → SLA 72.3%，并提供 per-task breakdown。
- ⚠️ **“SLA 本身带来全部 SOTA gain”**：完整 recipe 同时改变 state masking、action coordinates/rotation、data curation 与 alignment，factorial isolation 不足。
- ⚠️ **“14,330h scalable continual pre-training”**：14,330h 是 source-level pre-selection 统计，实际 retained corpus 未说明。
- ⚠️ **“generalized spatial understanding”**：随机化 manipulation 有支持，但 Open SR 1.9%、Long-Horizon SR 11.9%，且没有独立 quantitative geometry benchmark。
- ⚠️ **“完整方法已开源可复现”**：核心框架和 checkpoint 可用，但 current public configs 未启用 adaptive layers/camera/depth，processed corpus 缺失。

### Notes

- **最值得复用的实验**：不是 final SOTA table，而是 Table 6 的 stage × data scaling matrix。它把“spatial supervision 应该发生在哪个 training stage”变成了可证伪问题。
- **state dropout 可能是独立研究点**：25% dropout 的巨大增益说明 VLA benchmark 中 proprioceptive shortcut 可能比预期严重。应在无 spatial teacher、不同 camera perturbation 和真实 dynamic scenes 上单独复核。
- **implicit vs explicit spatial representation**：SLA 只优化 action-useful geometry；它可能不保留 language-queryable relations、object permanence 或 global metric consistency。这正是 explicit spatial tokens/scene graph 仍可能有优势的地方。
- **更公平的下一步实验**：用同一 π0.5 checkpoint、同一 processed mixture、同一 dropout/action recipe，只切换 no teacher / single-layer / adaptive implicit / explicit tokens / hybrid，并加入 depth、relative-pose、occlusion 和 cross-view correspondence probes。
- **发布热度**：论文发布四天已有 95 HF upvotes；Semantic Scholar citation 为 0 属正常 early-stage 状态，不能据此判断长期影响力。

### Rating

**Metrics** (as of 2026-11-09): citation=0, influential=0 (比例 N/A：citation=0), velocity=0.0/mo; HF upvotes=95; github 390⭐ / forks=20 / 90d commits=13 / pushed 2d ago

GitHub 指标来自共享的 `OpenHelix-Team/Spatial-Forcing` repository，不是 SLA subdirectory 的独立 adoption metric，因此只视作 artifact 活跃度信号。

**分数**：2 - Frontier

**理由**：SLA 给出 spatially supervised continual pre-training 的强结果、清晰 stage ablation 和较完整的公开 checkpoint/code，已足以成为 3D-aware VLA 与 representation alignment 研究必须比较的 frontier baseline。它尚不足以评为 Foundation：发布仅四天、无外部复现或后续继承，实际 corpus 与 headline config 未闭环，且 state dropout/action recipe 使核心方法的独立归因仍不够干净。
