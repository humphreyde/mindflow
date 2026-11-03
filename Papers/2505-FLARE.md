---
type: paper
arxiv_id: 2505.15659
source_vault: notes
source_path: PaperNotes/VLA/FLARE.md
date_migrated: 2026-11-03
title: "FLARE: Robot Learning with Implicit World Modeling"
method_name: "FLARE"
authors: [Ruijie Zheng, Jing Wang, Scott Reed, Johan Bjorck, Yu Fang, Fengyuan Hu, Joel Jang, Kaushil Kundalia, Zongyu Lin, Loic Magne, Avnish Narayan, You Liang Tan, Guanzhi Wang, Qi Wang, Jiannan Xiang, Yinzhen Xu, Seonghyeon Ye, Jan Kautz, Furong Huang, Yuke Zhu, Linxi Fan]
year: 2025
venue: arXiv
tags: [vla, world-model, latent-alignment, flow-matching, humanoid-robot, egocentric-video, imitation-learning]
zotero_collection: VLA
image_source: online
arxiv_html: https://arxiv.org/html/2505.15659v1
code_url:
code_companion:
created: 2026-09-30
---

# 论文笔记：FLARE: Robot Learning with Implicit World Modeling

## 元信息

| 项目 | 内容 |
|---|---|
| Authors | Ruijie Zheng、Jing Wang、Scott Reed、Johan Bjorck、Yu Fang、Fengyuan Hu、Joel Jang、Kaushil Kundalia、Zongyu Lin、Loic Magne、Avnish Narayan、You Liang Tan、Guanzhi Wang、Qi Wang、Jiannan Xiang、Yinzhen Xu、Seonghyeon Ye、Jan Kautz、Furong Huang、Yuke Zhu、Linxi Fan |
| 机构 | NVIDIA；University of Maryland, College Park；Nanyang Technological University；University of Texas at Austin |
| 日期 | May 2025 |
| 项目主页 | [NVIDIA GEAR FLARE](https://research.nvidia.com/labs/gear/flare/) |
| 对比基线 | [[Papers/2503-GR00TN1\|GR00T N1]]、UWM、[[Diffusion Policy]] |
| 链接 | [arXiv](https://arxiv.org/abs/2505.15659) / [PDF](https://arxiv.org/pdf/2505.15659) / Code：尚未公开 |

> [!info] 作者与材料范围
> 本笔记保留署名顺序前 20 位作者，并追加论文明确标注为 equal advising 的第 21 位作者 Linxi Fan，因此最终保留全部 21 位作者。Ruijie Zheng、Jing Wang、Scott Reed 为 equal contribution；Yuke Zhu、Linxi Fan 为 equal advising。论文共有 **12 张 Figure、3 张 Table、6 个展示公式和 1 个 Algorithm**，下文全部按内容位置收录。项目页标注代码 coming soon，论文所给 GitHub 地址当前返回 404，因此不伪造 code companion。

---

## 一句话总结

> FLARE 让动作 DiT 的 future tokens 对齐未来观测的控制相关表征，以极小架构改动获得隐式世界建模监督，并能直接利用没有动作标签的人类第一视角视频。

---

## 核心贡献

1. **隐式未来建模**：提出 [[Future Latent Representation Alignment]]，预测紧凑未来表征而非重建像素或 VAE latent。
2. **轻量集成**：只向标准 flow-matching VLA 的动作 [[DiT]] 添加少量 future tokens，部署时不运行 teacher、也不生成未来视频。
3. **Action-aware teacher**：用跨本体动作预测预训练紧凑的视觉语言表示，明显优于通用 SigLIP2 target。
4. **无动作视频共训练**：对人类 egocentric video 仅施加未来 latent 对齐损失，在极少真机示范下提升新物体泛化。

---

## 问题背景

### 要解决的问题

显式 [[World Model]] 往往同时预测未来像素和动作，计算量大，并把模型容量浪费在纹理与背景重建上；但机器人策略真正需要的是与可执行动作有关的未来状态。FLARE 的目标是把“预测未来”压缩成动作网络内部的表征监督，让策略获得前瞻性，同时维持高频控制。

#### Figure 1：FLARE 与普通 Flow-Matching Policy 的差别

![Figure 1](https://arxiv.org/html/2505.15659v1/flare_concept.png)

**说明**：普通策略只对有动作数据计算 flow-matching loss；FLARE 额外让 future tokens 对齐未来视觉语言 embedding。对无动作视频，可以跳过动作损失、只保留未来对齐，因此无需 latent action 或 IDM 伪标签。

### 现有方法的局限

- 像素/VAE latent 未来生成需要大生成模型和高质量重建，训练目标可能与控制竞争。
- 显式视频 rollout 增加推理延迟，不易嵌入高频真机控制。
- 通用视觉 encoder 的表示未必保留抓取姿态、接触关系等 action-relevant 信息。
- 无动作人类视频通常需要手部追踪、姿态估计、[[Latent Action Model|latent action]] 或 [[Inverse Dynamics Model|IDM]] 才能转成策略监督。

### 本文的动机

如果动作去噪网络的中间表示能预测 $t+H$ 的任务相关 embedding，它就必须在生成动作时编码“执行这段动作后会到哪里”。这种训练期的隐式未来约束比完整视觉生成更紧凑，并且在推理时可以被丢弃。

---

## 核心技术

### Flow-Matching 动作策略

观测 $o_t$ 包含多视角图像和语言指令，本体状态为 $q_t$，专家动作块为 $A_t=(a_t,\ldots,a_{t+H})$，视觉语言表示为 $\phi_t=VL(o_t)$。

#### 公式 1：[[Flow Matching|带噪动作插值]]

$$
A_t^\tau=\tau A_t+(1-\tau)\epsilon.
$$

**含义**：在专家动作与高斯噪声之间按 flow 时间插值，构造动作 DiT 的训练输入。

**符号说明**：

- $\tau\in[0,1]$：flow-matching 时间。
- $\epsilon\sim\mathcal{N}(\mathbf{0},\mathbf{I})$：高斯噪声。
- $A_t$：长度为 $H$ 的专家动作块。

#### 公式 2：[[Flow Matching|动作流匹配损失]]

$$
\mathcal{L}_{\mathrm{fm}}(\theta)
=\mathbb{E}_{\tau}
\left[
\left\|V_\theta(\phi_t,A_t^\tau,q_t)-(\epsilon-A_t)\right\|^2
\right].
\tag{1}
$$

**含义**：$V_\theta$ 学习从带噪动作指向目标动作的速度场。论文沿用 GR00T N1 的方向约定 $\epsilon-A_t$。

**符号说明**：

- $V_\theta$：动作 DiT 的速度预测。
- $\phi_t$：当前图像与指令的视觉语言 embedding。
- $q_t$：当前本体状态。

#### 公式 3：[[Flow Matching|四步 Euler 动作采样]]

$$
A_t^{\tau+1/K}
=A_t^\tau
+\frac{1}{K}V_\theta(\phi_t,A_t^\tau,q_t).
$$

**含义**：从 $A_t^0\sim\mathcal{N}(0,I)$ 出发，用前向 Euler 法迭代生成动作块。全文固定 $K=4$，因此 FLARE 的动作部署路径与 GR00T N1 相同。

**符号说明**：

- $K=4$：采样步数。
- $1/K$：离散积分步长。

### 模型架构

#### Figure 2：FLARE 架构

![Figure 2](https://arxiv.org/html/2505.15659v1/flare_architecture.png)

**说明**：state token、noised action tokens 与 $M$ 个可学习 future tokens 拼接后共同经过 DiT self-attention；当前视觉语言 token 通过 cross-attention 注入。第 $L$ 个中间层的 future-token hidden states 经 MLP 投影，与未来观测 embedding 对齐；动作 token 仍用于 flow matching。

具体信息流：

- **当前条件**：$o_t$、$q_t$、语言指令和带噪动作块 $A_t^\tau$。
- **共享主干**：8 层 DiT，交替 self-attention 与 cross-attention。
- **future stream**：默认 $M=32$ 个 learnable tokens，在第 6 层读取。
- **动作输出**：动作 token 经 2 层 MLP 解码为速度场。
- **未来输出**：future tokens 经 2 层 MLP 解码为未来 latent，只在训练期使用。

### Future Latent Representation Alignment

#### 公式 4：[[Future Latent Representation Alignment|未来潜在表征对齐损失]]

$$
\mathcal{L}_{\mathrm{align}}(\theta)
=-\mathbb{E}_{\tau}
\left[
\cos\!\left(
f_\theta(\phi_t,A_t^\tau,q_t),
g(\phi_{t+H})
\right)
\right].
\tag{2}
$$

**含义**：策略网络从当前观测与候选动作的中间状态预测未来表征，并最大化它与 teacher 对未来观测编码的余弦相似度。它约束动作网络保留未来可达状态信息，但不要求重建未来像素。

**符号说明**：

- $f_\theta:\mathbb{R}^{B\times M\times D}$：第 $L$ 层 future tokens 的预测表示。
- $g:\mathbb{R}^{B\times M\times D}$：未来观测的 target encoder。
- $B,M,D$：batch、future-token 数量和 embedding 维度。
- $H$：动作块 horizon；target 时刻为 $t+H$。

#### 公式 5：[[Future Latent Representation Alignment|联合训练目标]]

$$
\mathcal{L}
=\mathcal{L}_{\mathrm{fm}}
+\lambda\mathcal{L}_{\mathrm{align}},
\qquad \lambda=0.2.
\tag{3}
$$

**含义**：有动作数据同时优化动作与未来对齐；无动作人类视频只优化 $\mathcal{L}_{\mathrm{align}}$。实验选择 $\lambda=0.2$，在动作精度与未来表征监督之间折中。

**符号说明**：

- $\mathcal{L}_{\mathrm{fm}}$：动作 flow-matching 损失。
- $\mathcal{L}_{\mathrm{align}}$：未来 latent 对齐损失。
- $\lambda$：对齐损失权重。

### Action-Aware Future Embedding Model

#### Figure 10：Q-Former 视觉语言表示模块

![Figure 10](https://arxiv.org/html/2505.15659v1/qformer_architecture.png)

**说明**：SigLIP2-Large-Patch16-256 把 $256\times256$ 图像变成 256 个 patch tokens，文本编码器输出 32 个语言 tokens；4 层 self-attention 融合为 288 tokens，再由 32 个 learnable queries 的 Q-Former 压缩成固定长度表示。随后接 8 层 DiT 通过动作预测预训练，使表示保留控制相关信息。

#### Figure 3：Action-Aware Encoder 的预训练数据混合

![Figure 3](https://arxiv.org/html/2505.15659v1/data_mixture.svg)

**说明**：混合真实 GR-1、Open X-Embodiment 与 GR-1 simulation，数据采样权重并不简单按原始时长分配；真实 GR-1 与仿真 GR-1 各占约 30%，DROID 占 20%，其余数据集各约 3.3%。

#### Table 3：Action-Aware Encoder 预训练数据统计

| Dataset | Frames | Duration (hr) | FPS | Camera View | Category |
|---|---:|---:|---:|---|---|
| GR-1 In-house Dataset | 6.4M | 88.4 | 20 | Egocentric | Real robot |
| DROID (OXE) | 23.1M | 428.3 | 15 | Left, Right, Wrist | Real robot |
| RT-1 (OXE) | 3.7M | 338.4 | 3 | Egocentric | Real robot |
| Language Table (OXE) | 7.0M | 195.7 | 10 | Front-facing | Real robot |
| Bridge-v2 (OXE) | 2.0M | 111.1 | 5 | Shoulder, left, right, wrist | Real robot |
| MUTEX (OXE) | 362K | 5.0 | 20 | Wrist | Real robot |
| Plex (OXE) | 77K | 1.1 | 20 | Wrist | Real robot |
| RoboSet (OXE) | 1.4M | 78.9 | 5 | Left, Right, Wrist | Real robot |
| GR-1 Simulation | 125.5M | 1,742.6 | 20 | Egocentric | Simulation |
| **Total** | **169.5M** | **2,989.5** | — | — | — |

**表格说明**：action-aware encoder 共使用约 1.695 亿帧、2,989.5 小时的跨本体数据。附录报告在 256 张 H100 上以 batch 8192 训练 150K steps。

### 训练算法与稳定目标

#### 公式 6：Target Encoder 的 EMA 更新

$$
\theta_{\mathrm{target\_vl\_embedding}}
\leftarrow
\rho\,\theta_{\mathrm{target\_embedding}}
+(1-\rho)\,\theta_{\mathrm{policy\_vl\_embedding}}.
$$

**含义**：target encoder 不参与反向传播，而是缓慢跟随 policy encoder，以适应 downstream 视觉分布并维持稳定监督。论文默认 $\rho=0.995$。

**符号说明**：

- $\rho$：EMA 衰减系数。
- $\theta_{\mathrm{policy\_vl\_embedding}}$：当前策略 encoder 参数。
- $\theta_{\mathrm{target\_vl\_embedding}}$：生成未来 target 的 teacher 参数。

#### Algorithm 1：FLARE 训练伪代码

```python
# target_vl_embedding: pretrained action-aware target encoder
# vl_embedding: current policy vision-language encoder
# dit: current policy diffusion transformer
# lambda_: FLARE loss weight, default 0.2

future_tokens = nn.Embedding(M, hidden_dim)
target_vl_embedding.load_state_dict(vl_embedding.state_dict())
target_vl_embedding.requires_grad_(False)

for _ in range(N):
    obs, proprio, actions, future_obs = dataset.next()

    noise = gaussian.sample()
    timestep = beta.sample()
    noisy_action = timestep * actions + (1 - timestep) * noise
    velocity = actions - noise

    action_tokens = action_embed(noisy_action, timestep)
    state_token = state_embed(proprio)
    vl_tokens = vl_embedding(obs)

    sa_tokens = torch.concat(
        [state_token, action_tokens, future_tokens], dim=1
    )
    policy_outputs = dit(sa_tokens, vl_tokens)

    action_outputs = action_decoder(
        policy_outputs[:, 1 : 1 + action_tokens.shape[1]]
    )
    action_loss = MSE(action_outputs, velocity)

    with torch.no_grad():
        embedding_to_align = target_vl_embedding(future_obs)
    predicted_embedding = embedding_decoder(policy_outputs[:, -M:])
    flare_loss = 1 - COSINE_SIMILARITY(
        predicted_embedding, embedding_to_align
    )

    loss = action_loss + lambda_ * flare_loss
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
```

**说明**：该算法的关键是动作 token 与 future tokens 共用 DiT self-attention，因此未来监督能改变动作表示；teacher 分支 stop-gradient。上面保留原算法流程，并修正原伪代码中 `hiddem_dim`、`state` 等明显排版变量错误。

### 推理与部署

部署阶段仅保留视觉语言 encoder、状态/动作编码器、DiT 和动作解码器：

- 不输入未来观测；
- 不运行 target encoder；
- 不计算 latent alignment；
- 不生成未来帧或 latent rollout；
- 仍以 $K=4$ 的 Euler 采样生成动作块。

因此 FLARE 更准确地说是“带隐式未来表征监督的 VLA”，而不是推理时能枚举未来、比较候选动作的完整 [[World Action Model|WAM]]。

---

## 实验

### 实验设置

#### Figure 4：多任务仿真 Benchmark

![Figure 4](https://arxiv.org/html/2505.15659v1/latent_wm_task_figure.png)

**说明**：RoboCasa 包含 24 个 Panda 单臂厨房任务；GR-1 suite 包含 18 个物体重排和 6 个铰接物体任务，用于评估 humanoid dexterous manipulation。

#### Figure 5：真实 GR-1 任务

![Figure 5](https://arxiv.org/html/2505.15659v1/real_gr1_task_figure.png)

**说明**：四个真实任务都是不同 source/target 组合的 pick-and-place，并用苹果、罐子、瓶装水、黄瓜等物体构成 8 个参考初始状态。

#### 评测协议与实现细节

- 多任务仿真模型训练 80K steps；UWM 为保证收敛训练 400K steps。
- 每 1K steps 对每任务评估 50 episodes，报告最后 5 个 checkpoint 的最佳成功率。
- 多任务与 post-training 使用 32 张 H100、global batch 1024、80K steps。
- 优化器为 AdamW，$\beta_1=0.95$、$\beta_2=0.999$、$\epsilon=10^{-8}$、weight decay $10^{-5}$，cosine schedule 与 0.05 warmup ratio。

### 主要结果

#### Table 1：多任务策略成功率

| Task Group | FLARE | Policy Only | UWM | GR00T N1 (Scratch) | Diffusion Policy |
|---|---:|---:|---:|---:|---:|
| Pick and Place (RoboCasa) | **53.2%** | 43.8% | 35.6% | 44.1% | 29.2% |
| Open & Close Doors / Drawers | **88.8%** | 78.7% | 82.0% | 80.0% | 78.7% |
| Others | **80.0%** | 75.2% | 74.2% | 69.6% | 61.3% |
| **24 RoboCasa Tasks Average** | **70.1%** | 61.9% | 60.8% | 60.6% | 51.7% |
| Pick and Place Tasks (GR-1) | **58.2%** | 46.6% | 30.1% | 51.8% | 40.4% |
| Articulated Tasks (GR-1) | **51.3%** | 47.4% | 38.4% | 42.8% | 50.1% |
| **24 GR-1 Tasks Average** | **55.0%** | 44.0% | 29.5% | 45.1% | 40.9% |

**表格说明**：FLARE 在两套 benchmark 均显著优于 policy-only 和显式 joint image/action prediction 的 UWM。Policy-only 继续训练到 160K steps 仍只有 44.1%，说明增益不是简单来自额外优化时间。

### 数据效率与跨本体迁移

#### Figure 6：RoboCasa 与真实 GR-1 Post-training 曲线

![Figure 6](https://arxiv.org/html/2505.15659v1/posttrain_results.svg)

**说明**：FLARE 在不同示范规模上均领先 policy-only，低数据区间差距更大。RoboCasa 每任务 100 条轨迹时约提升 10 个百分点；跨本体 teacher 从未见过 RoboCasa，却在 1,000 trajectories 时达到 71.3%，接近同域 teacher 的 70.2%。真实 GR-1 最高平均成功率为 95.1%，比 policy-only 平均高约 14 个百分点。

### 无动作人类视频与新物体泛化

#### Figure 7：人类第一视角视频与少样本真机示范

![Figure 7](https://arxiv.org/html/2505.15659v1/novel_objects_setup_v2.png)

**说明**：五个训练未见物体各收集 150 条 GoPro 人类第一视角视频和最多 10 条真机示范。每物体仅 1 条真机轨迹时，加入人类视频从 37.5% 提升到 60.0%；10 条时从 42.5% 提升到 80.0%。无动作视频只计算未来对齐损失。

### 消融实验

#### Table 2：Target Embedding 模型消融

| Method | Success Rate (%) |
|---|---:|
| No FLARE loss | 43.9 |
| SigLIP2 | 49.6 |
| SigLIP2 (Average Pooled) | 50.9 |
| **Action-aware Embedding** | **55.0** |

**表格说明**：通用 SigLIP2 也能带来 5.7–7.0 个百分点提升，但 action-aware teacher 再提高 4.1 个百分点，说明“预测什么表征”与是否加入对齐损失同样重要。

#### Figure 8：对齐层与损失权重消融

![Figure 8](https://arxiv.org/html/2505.15659v1/ablation_results.svg)

**说明**：主设置在 8 层 DiT 的第 6 层读取 future tokens，并取 $\lambda=0.2$。较晚层能让更多参数接收未来监督；过早在第 4 层对齐会明显下降，可能使尚未形成动作语义的表示过早受 target 约束。

#### Figure 9：EMA 系数消融

![Figure 9](https://arxiv.org/html/2505.15659v1/flare_ema.svg)

**说明**：baseline 为 60.1%；$\rho=0.99,0.995,0.999,1.0$ 分别约为 63.5%、66.4%、65.7%、64.6%。$\rho=0.995$ 最佳；过快更新 target 会降低稳定性，而完全冻结 target 仍优于无 FLARE。

### 定性结果

#### Figure 11：四个真实 GR-1 Rollout

![Figure 11](https://arxiv.org/html/2505.15659v1/real_gr1_rollouts.png)

**说明**：对瓶装水、罐子、黄瓜和苹果，FLARE 学会先绕到或悬停到物体上方再抓取，减少 policy-only 直接撞倒物体的失败。这是未来表征监督改善接近策略的直观证据。

#### Figure 12：五个新物体 Rollout

![Figure 12](https://arxiv.org/html/2505.15659v1/real_gr1_rollouts_novel_objects.png)

**说明**：模型处理毛绒玩具、锤子、胶带等未见几何形状，需要采用不同抓取方式；结果支持“人类视频补充视觉—动作后果结构”，但仍依赖至少一条目标本体示范。

---

## 批判性思考

### 优点

1. 把 world-model supervision 压缩到控制相关 latent，不承担高保真像素生成的成本。
2. future tokens 与动作 tokens 共享 DiT，架构改动小，且 inference path 基本不增加 teacher 成本。
3. 对 teacher 类型、读取层、loss 权重与 EMA 都有消融，能定位真正有效的设计因素。
4. 无动作人类视频无需显式 pose tracking 或伪动作，显著降低数据工程复杂度。

### 局限性

1. 论文主要评估 imitation learning 与 pick-and-place，尚未验证长时序任务、强化学习或 locomotion。
2. latent 对齐能改善动作学习，但不能直接可视化、查询或 rollout 未来，因此不支持显式 planning 或反事实比较。
3. 人类视频实验在受控场景中用头戴 GoPro 采集，域差异远小于互联网视频；扩展性仍需验证。
4. 新物体泛化仍需要少量真机专家示范，尚未达到纯视频 zero-shot control。
5. action-aware teacher 本身需要 256 张 H100、150K steps 的预训练，整体计算成本并不“轻量”；轻量主要指策略架构和部署。
6. 代码截至笔记创建时尚未公开，复现实验中的 target encoder、数据 mixture 与训练细节存在缺口。

### 潜在改进方向

1. 将 future tokens 扩展为多时间尺度或多模态分布，而不是只对齐固定 $t+H$。
2. 给 future latent 增加可解码的接触、对象状态或奖励头，使其可用于 planning 与失败诊断。
3. 研究动作条件是否真正进入 target prediction，避免模型只凭当前图像预测平均未来。
4. 用自然环境 egocentric video、跨相机和跨人形平台检验域鲁棒性。
5. 与显式 [[World Action Model]] 混合：训练时 latent alignment，困难场景才调用生成式 rollout。

### 可复现性评估

- [ ] 代码开源
- [ ] 预训练模型公开
- [ ] 完整训练数据可获取
- [x] 训练细节较完整
- [x] 关键消融较完整

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

- [[Papers/2503-GR00TN1|GR00T N1]]：沿用其动作 flow-matching DiT 与四步 Euler 采样。
- [[Flow Matching]]：动作生成主目标。
- [[DiT]]：动作 token 与 future tokens 的共享计算主干。

### 对比

- [[Diffusion Policy]]：纯动作生成基线。
- UWM：联合预测未来图像 VAE latent 与动作的显式生成基线。
- [[World Model]]：FLARE 只学习未来表征对齐，不重建完整观测。

### 方法相关

- [[Future Latent Representation Alignment]]：本论文的核心概念页。
- [[World Action Model]]：FLARE 可视为训练期隐式世界建模，但不是完整 test-time WAM。
- [[Action Chunking]]：以动作块为建模与预测单位。

### 系列相关

- [[Topics/GR00T-Series-Survey|GR00T 系列综述]]：FLARE 在 N1.5 中的角色与后续版本演化。

---

## 速查卡片

> [!summary] FLARE
> - **核心**：让动作 DiT 的 future tokens 对齐未来 action-aware 表征，以隐式未来监督改善控制。
> - **方法**：flow matching + 32 future tokens + 第 6 层 cosine alignment + EMA teacher。
> - **结果**：RoboCasa 70.1%、GR-1 simulation 55.0%；新物体 10 demos + 人类视频达到 80.0%。
> - **代码**：项目页标注 coming soon，当前无可用公开仓库。

---

*笔记创建时间：2026-09-30*
