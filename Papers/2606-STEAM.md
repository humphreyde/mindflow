---
type: paper
arxiv_id: 2606.29834
source_vault: notes
source_path: PaperNotes/VLA/STEAM.md
date_migrated: 2026-11-03
title: "STEAM: Self-Supervised Temporal Ensemble Advantage Modeling for Real-World Robot Learning"
method_name: "STEAM"
authors: [Zhihao Liu, Qiuyi Gu, Yitao Wang, Dongming Qiao, Yixian Zhang, Shuaihang Chen, Liangzhi Shi, Tianxing Zhou, Zefang Huang, Kang Chen, Zhen Guo, Quanlu Zhang, Jincheng Yu, Xiaodan Liang, Guoliang Fan, Yu Wang, Feng Gao, Xinlei Chen, Chao Yu]
year: 2026
venue: arXiv
tags: [vla, advantage-modeling, self-supervised-learning, offline-rl, mixed-quality-data, robot-manipulation]
zotero_collection: VLA
image_source: mixed
arxiv_html: https://arxiv.org/html/2606.29834v1
code_url:
code_companion:
created: 2026-10-29
---

# 论文笔记：STEAM: Self-Supervised Temporal Ensemble Advantage Modeling for Real-World Robot Learning

## 元信息

| 项目 | 内容 |
|------|------|
| Authors | Zhihao Liu, Qiuyi Gu, Yitao Wang, Dongming Qiao, Yixian Zhang, Shuaihang Chen, Liangzhi Shi, Tianxing Zhou, Zefang Huang, Kang Chen, Zhen Guo, Quanlu Zhang, Jincheng Yu, Xiaodan Liang, Guoliang Fan, Yu Wang, Feng Gao, Xinlei Chen, Chao Yu |
| 作者筛选 | 共 19 位作者，全部保留；Zhihao Liu、Qiuyi Gu 为共同一作，Xinlei Chen、Chao Yu 为通讯作者 |
| 机构 | 中国科学院自动化研究所、清华大学、逐际动力、中国科学院大学、中关村学院、鹏城实验室、哈尔滨工业大学、北京理工大学、浙江大学、北京大学、无问芯穹 |
| 日期 | June 2026（arXiv v1） |
| 项目主页 | [STEAM Project](https://liuzhihao2022.github.io/steam.github.io/) |
| 对比基线 | [[Behavior Cloning]]、[[HG-DAgger]]、[[Pi06|RECAP]] |
| 链接 | [arXiv](https://arxiv.org/abs/2606.29834) / [HTML](https://arxiv.org/html/2606.29834v1) / [Project Repository](https://github.com/LiuZhihao2022/steam.github.io) |

> [!warning] 发布状态
> 项目仓库 README 将论文标为 CoRL 2026，但公开页面 BibTeX 仍写着 `Under review`，代码按钮也是 `soon`。当前应按 arXiv 预印本理解，不能视作已正式录用或已有实现代码。

---

## 一句话总结

> STEAM 从专家轨迹的时间顺序中自监督学习局部进展代理，再保守筛选混合质量数据，用 CFGRL 提升真实机器人 VLA。

---

## 核心贡献

1. **无 reward 的逐帧质量信号**：用专家轨迹内帧对的归一化时间差作为监督，不依赖人工 reward、成功失败标注或外部 VLM judge。
2. **保守的时序 ensemble**：训练多个 signed temporal-offset predictor，对 OOD rollout 取最小 advantage，降低错误高分对策略训练的污染。
3. **混合质量数据的统一利用**：把专家演示、自主 rollout 和人工纠错片段转成 frame-level optimality label，并通过 [[CFGRL]] 训练 [[VLA]]。

#### Figure 1: STEAM 总览

![Figure 1](https://arxiv.org/html/2606.29834v1/fig1_v6.png)

**说明**：STEAM 位于数据与策略之间。它不直接控制机器人，而是先从专家演示学习时序进展，再离线评价专家、rollout 与人工纠错轨迹，最后把高质量局部片段交给 CFGRL。右侧可视化展示毛巾折叠失败重试后，STEAM advantage 随有效恢复重新升高。

---

## 问题背景

### 要解决的问题

真实机器人训练数据往往不是整条轨迹都好或都坏：自主 rollout 可能先前进后卡死，人工纠错轨迹可能先由策略犯错、再由人恢复。episode-level success filtering 会丢掉失败轨迹中仍有价值的前半段，也会保留成功轨迹中的停滞和无效调整。论文因此研究如何在没有 dense reward 的情况下，为每个局部动作片段估计可用于策略改进的质量信号。

> [!important] “Advantage”的含义
> STEAM 的分数不是标准强化学习中的 $A(s,a)=Q(s,a)-V(s)$。它没有学习 return、$Q$ 或 $V$，而是在固定未来窗口内估计视觉状态变化相对专家轨迹有多快。因此更准确地说，它是 **local temporal progress / efficiency proxy**。

### 现有方法的局限

- [[Pi06|RECAP]] 等方法先从 success/failure reward 学 [[Distributional Value Function]]，再推导 advantage；结果相关性强，但需要 outcome label。
- VLM reward/value model 依赖大规模预训练，细粒度物理状态上可能不可靠。
- 绝对或单调 progress estimator 难处理真实 rollout 中的暂时回退、重试和人工接管恢复。
- 单一 predictor 在专家分布外可能过度自信，给失败 rollout 错误的高 advantage。

### 本文的动机

作者使用 [[Self-Supervised Learning]] 的思路：成功专家轨迹本身已经提供“哪一帧在前、哪一帧在后”的免费监督。相对帧序避免跨轨迹对齐绝对 progress，倒序帧对又能从成功数据构造 regression 信号。若再用 [[Deep Ensemble]] 的 worst-of-$M$ 聚合抑制 OOD 高估，就可能得到一个便宜、稠密且保守的数据质量代理。

---

## 核心技术

### 数据与数据处理

STEAM predictor 只在专家演示上训练。每次从一条专家轨迹中采样相隔不超过 $k_{\max}$ 的帧对，并同时采正、负 offset；策略阶段再用 predictor 离线标注专家演示、策略 rollout 和人工纠错数据。

| 任务 | 专家演示 | 自主 rollout | 人工纠错 | 阶段数 | 平台 |
|------|---------:|-------------:|---------:|-------:|------|
| Towel Folding | 240 | 125 | 20 | 5 | ARX 双臂 |
| Chip Checkout | 200 | 63 | 20 | 8 | ARX 双臂 |
| Cola Restocking | 89 | 49 | 27 | 4 | ARX 双臂 |
| Pick-and-Place | 50 | 594 | 0 | 2 | Franka 单臂 |

**说明**：前三项覆盖长程双臂协作，最后一项是短程单臂任务。Pick-and-place 的专家数据最少但 rollout 最多，也是 expert-only filtering 会退化的任务。

### 模型架构

每个 STEAM predictor 使用 SigLIP-SO400M 视觉编码器和 Gemma-3-270M 语言 backbone，输入两个视觉帧与自然语言指令，输出 $N$ 个 signed temporal-offset bins 的 categorical distribution。默认训练 $M=3$ 个不同随机初始化的 predictor。策略端采用 [[Pi0]] 作为 flow-matching policy backbone。

#### Figure 2: STEAM Framework / 总体架构

![Figure 2](https://arxiv.org/html/2606.29834v1/fig2_v4.png)

**说明**：左侧从专家轨迹生成正序与倒序帧对；中间 ensemble 学习 temporal-offset distribution；右侧用最小聚合后的 $A_{\mathrm{STEAM}}$ 标注多源数据，再通过 CFGRL refinement π0。predictor 与 policy 分开训练，部署策略时不需要运行 STEAM。

### 核心模块一：归一化时序偏移监督

#### 公式 1: [[Temporal Offset Prediction|轨迹内时间偏移]]

$$
\Delta_{\tau_k}(i,j)
=\Delta(f_{k,i},f_{k,j})
=j-i.
$$

**含义**：同一专家轨迹中，未来帧产生正 offset，交换帧序产生负 offset。后者被当作 pseudo-regression supervision。

**符号说明**：
- $\tau_k$：第 $k$ 条专家轨迹。
- $f_{k,i},f_{k,j}$：轨迹中的第 $i,j$ 帧。
- $\Delta_{\tau_k}(i,j)$：带符号时间偏移。

#### 公式 2: [[Temporal Offset Prediction|轨迹长度归一化偏移]]

$$
\tilde{\Delta}_{\tau_k}(i,j)
=\Delta(f_{k,i},f_{k,j})\frac{L_{\max}}{L_{\tau_k}}
=(j-i)\frac{L_{\max}}{L_{\tau_k}}.
$$

**含义**：相同原始 offset 在短轨迹中代表更大比例的任务进展，因此被放大；这使 STEAM 同时编码“有没有前进”和“执行是否高效”。

**符号说明**：
- $L_{\tau_k}$：当前专家轨迹长度。
- $L_{\max}$：专家轨迹最大长度，论文也建议用高分位数降低异常值敏感性。
- $\tilde{\Delta}_{\tau_k}$：归一化 temporal offset。

### 核心模块二：分布式 offset predictor 与 advantage proxy

连续 offset 被截断到 $[-\tilde{\Delta}_{\max},\tilde{\Delta}_{\max}]$，再均匀量化为 $N$ 个 bins。分布式预测比单点回归保留了不确定性，也避免为长、高频轨迹建立过大的离散输出空间。

#### 公式 3: [[Temporal Offset Prediction|分布式 offset 交叉熵目标]]

$$
\mathcal{L}(\theta)
=\mathbb{E}_{\tau_k,i,j}
\left[
H\left(
\tilde{\Delta}^{\mathcal{B}}_{\tau_k}(i,j),
p_\theta(\Delta\mid f_{k,i},f_{k,j},\ell)
\right)
\right].
$$

**含义**：predictor 根据帧对和语言指令预测 temporal-offset bin，使用 one-hot target 的交叉熵训练。

**符号说明**：
- $\tilde{\Delta}^{\mathcal{B}}$：量化后的 one-hot bin target。
- $p_\theta$：参数为 $\theta$ 的 categorical predictor。
- $H(\cdot,\cdot)$：交叉熵；$\ell$ 为任务语言指令。

#### 公式 4: [[Advantage Modeling|固定 lookahead 的时序 advantage]]

$$
\begin{aligned}
A(f_{k,i};\theta)
=\frac{2}{N}\Bigg[
&\mathbb{E}_{b\sim p_\theta(\cdot\mid f_{k,i},f_{k,i+H},\ell)}[b]\\
&-\tilde{\Delta}^{\mathcal{B}}_{\tau_{\max}}(i,i+H)
\Bigg].
\end{aligned}
$$

**含义**：在固定 $H$ 帧窗口内，预测到的 progress 超过最长参考轨迹的基准进展时得正分；停滞或回退得到低分或负分。它衡量的是局部时序效率，而非 causal action advantage。

**符号说明**：
- $H$：固定 lookahead，长任务为 32 帧，pick-and-place 为 16 帧。
- $b$：预测 temporal bin index。
- $N$：bin 数量。
- $\tau_{\max}$：参考长度最大的专家 episode。

### 核心模块三：最小值 ensemble 抑制 OOD 高估

#### 公式 5: [[Deep Ensemble|保守的 worst-of-M 聚合]]

$$
A_{\mathrm{STEAM}}(f_{k,i};\Theta)
=\min_{m=1,\ldots,M}A(f_{k,i};\theta_m).
$$

**含义**：专家分布内各成员通常一致；在陌生 rollout 状态上若成员分歧，只要有一个模型认为质量低，最终分数就被压低。该设计牺牲 recall，优先减少会污染策略的 false positive。

**符号说明**：
- $\Theta=\{\theta_1,\ldots,\theta_M\}$：独立初始化的 predictor ensemble。
- $A_{\mathrm{STEAM}}$：最终保守 advantage proxy。

### 训练方法

#### Algorithm 1: Training STEAM

1. 对每个 ensemble member 使用独立随机种子初始化 $\theta_m$。
2. 从专家数据集采样轨迹 $\tau_k$ 与语言指令 $\ell$。
3. 从 $\{\pm1,\ldots,\pm k_{\max}\}$ 均匀采样 offset，并选择有效帧索引 $i,j=i+\Delta$。
4. 按公式 2 计算归一化 offset，截断并量化成 one-hot bin。
5. 按公式 3 更新 predictor，直到收敛。
6. 重复得到 $M$ 个 predictor，组成 $\Theta$。

#### 公式 6: [[Advantage-Conditioned Policy|分位数 optimality label]]

$$
o_{k,i}
=\mathbf{1}\left[
A_{\mathrm{STEAM}}(f_{k,i};\Theta)\geq\delta_q
\right].
$$

**含义**：把连续 advantage proxy 转成二值 optimality condition。论文对专家和非专家数据分别计算阈值，以适应两类数据不同的得分分布。

**符号说明**：
- $o_{k,i}\in\{0,1\}$：当前帧是否被视作高质量局部进展。
- $\delta_q$：对应数据源上的分位数阈值。

#### 公式 7: [[Advantage-Conditioned Policy|分数据源 optimality 标注]]

$$
o=
\begin{cases}
\mathbf{1}\left[A_{\mathrm{STEAM}}(f_{k,i};\Theta)\geq
\varpi_q^{\mathrm{exp}}\right],
& f_{k,i}\in\mathcal{D}_{\mathrm{exp}},\\[4pt]
\mathbf{1}\left[A_{\mathrm{STEAM}}(f_{k,i};\Theta)\geq
\varpi_q^{\mathrm{non\text{-}exp}}\right],
& f_{k,i}\in\mathcal{D}_{\mathrm{nexp}}.
\end{cases}
$$

**含义**：专家数据和 rollout/人工纠错数据各自排序，避免用同一绝对阈值直接比较两种不同分布。

**符号说明**：
- $\mathcal{D}_{\mathrm{exp}}$：专家数据。
- $\mathcal{D}_{\mathrm{nexp}}$：自主 rollout 与人工纠错数据。
- $\varpi_q^{\mathrm{exp}},\varpi_q^{\mathrm{non\text{-}exp}}$：两类数据的分位阈值。

#### 公式 8: [[Flow Matching|动作线性插值路径]]

$$
a_t=(1-t)a_0+ta.
$$

**含义**：CFGRL policy 从高斯噪声 $a_0$ 到数据动作 $a$ 建立 flow-matching interpolation path。

**符号说明**：
- $a_0\sim\mathcal{N}(0,I)$：初始噪声动作。
- $a$：数据中的目标 action chunk。
- $t\sim\mathcal{U}[0,1]$：flow time。

#### 公式 9: [[CFGRL|带 optimality dropout 的 flow-matching 目标]]

$$
\begin{aligned}
\mathcal{L}_\pi(\phi)
=\mathbb{E}_{\substack{
(s,a,o)\sim\mathcal{D}_{\mathrm{exp}}\cup\mathcal{D}_{\mathrm{nexp}},\\
t\sim\mathcal{U}[0,1],\ a_0\sim\mathcal{N}(0,I)
}}
\left[
\left\|
v_\phi(a_t,t,s,\tilde{o})-(a-a_0)
\right\|^2
\right].
\end{aligned}
$$

**含义**：policy 同时学习带 optimality condition 与无条件的速度场；训练时以概率 $p_{\mathrm{drop}}$ 将 $o$ 替换为空条件，为推理阶段 classifier-free guidance 做准备。

**符号说明**：
- $v_\phi$：参数为 $\phi$ 的 flow velocity field。
- $s$：当前策略观测。
- $\tilde{o}$：保留或 dropout 后的 optimality condition。

#### Algorithm 2: CFGRL Policy Learning with STEAM

1. 用固定 STEAM ensemble 为 $\mathcal{D}_{\mathrm{exp}}\cup\mathcal{D}_{\mathrm{nexp}}$ 中每个 $(s_t,a_t,s_{t+H})$ 计算 $A_{\mathrm{STEAM}}$。
2. 分别在专家和非专家数据上求分位阈值并生成 $o_t$。
3. 构建带 optimality label 的数据集 $\mathcal{D}_o=\{(s_t,a_t,o_t)\}$。
4. 采样 flow time 与高斯噪声，按公式 8 构造 $a_t$。
5. 随机丢弃 optimality condition，按公式 9 更新 flow-matching policy。
6. 部署时固定引导到 $o=1$。

### 推理与部署

推理时 STEAM predictor 不参与控制；只运行训练好的条件/无条件 flow policy。由高斯噪声出发，用固定步长 Euler 积分生成 action chunk。

#### 公式 10: [[Flow Matching|Euler 动作积分]]

$$
a_{t+\Delta t}
=a_t+\Delta t\,v_{\mathrm{cfg}}(a_t,t,s).
$$

**含义**：沿 CFG 引导的 velocity field 迭代，将噪声逐步变成动作。

**符号说明**：
- $\Delta t=1/T$：$T$ 步 Euler integration 的步长。
- $v_{\mathrm{cfg}}$：optimality-guided velocity field。

#### 公式 11: [[Classifier-free Guidance|高质量动作引导]]

$$
\begin{aligned}
v_{\mathrm{cfg}}(a_t,t,s)
=\;&v_\phi(a_t,t,s,\varnothing)\\
&+w\left[
v_\phi(a_t,t,s,o=1)
-v_\phi(a_t,t,s,\varnothing)
\right].
\end{aligned}
$$

**含义**：以无条件 policy 为基线，把动作生成方向外推到高 optimality condition。$w>1$ 会增强高质量偏置，但也可能把动作推向数据 support 边缘。

**符号说明**：
- $\varnothing$：无 optimality condition。
- $w$：guidance scale，实验统一使用 2.5。

---

## 实验

### 实验设置

#### Figure 3: Robot Setup and Tasks / 机器人平台与任务

![Figure 3](https://arxiv.org/html/2606.29834v1/fig3_v4.png)

**说明**：毛巾折叠、薯片结账和可乐补货使用 ARX 双臂机器人，分别包含 5、8、4 个阶段；pick-and-place 使用单 Franka，包含 grasp/place 两阶段。任务覆盖柔性物体、双臂交接、主动避碰与短程抓放。

#### Table 4: STEAM 与 CFGRL 超参数

| Hyperparameter | Towel Folding | Chip Checkout | Cola Restocking | Pick-and-Place |
|---|---:|---:|---:|---:|
| Maximum offset | 32 | 32 | 32 | 16 |
| Number of bins $N$ | 32 | 32 | 32 | 16 |
| Ensemble size $M$ | 3 | 3 | 3 | 3 |
| Advantage lookahead $H$ | 32 | 32 | 32 | 16 |
| $q$ over $\mathcal{D}_{\mathrm{exp}}$ | 0.8（论文标注 top 80%） | 0.8 | 0.8 | 0.8 |
| $q$ over $\mathcal{D}_{\mathrm{nexp}}$ | 0.3（论文标注 top 30%） | 0.3 | 0.3 | 0.3 |
| Conditioning dropout $p_{\mathrm{drop}}$ | 0.1 | 0.1 | 0.1 | 0.1 |
| Guidance scale $w$ | 2.5 | 2.5 | 2.5 | 2.5 |
| Learning rate | $5\times10^{-5}$ | $5\times10^{-5}$ | $5\times10^{-5}$ | $5\times10^{-5}$ |
| Training steps | 30,000 | 30,000 | 30,000 | 30,000 |
| Batch size | 512 | 512 | 512 | 512 |

**说明**：四项任务大部分设置相同，短程 pick-and-place 将 offset、bins 和 lookahead 减半。值得注意的是，公式 7 若把 $q=0.8$ 理解为通常的 80th percentile，保留下来的应是 top 20%，与表中的“top 80%”标注不一致；代码未公开，当前无法消解这一复现歧义。

### STEAM 能否识别局部进展

#### Figure 4: Towel Folding Advantage Curves / 毛巾折叠逐帧 advantage

![Figure 4](https://arxiv.org/html/2606.29834v1/fig4_v2.png)

**说明**：专家轨迹大部分时间保持高分；成功 rollout 因更慢而得分较低且波动；失败 rollout 卡死后降到接近零；人工纠错轨迹则在接管后恢复。它支持“逐帧区分停滞、失败与恢复”的定性主张，但没有 frame-level 人工真值可用于计算 ROC 或 calibration error。

#### Figure 5: Frame-level Advantage Density / 不同数据源的得分密度

![[Papers/assets/STEAM/figure5.png]]

**说明**：四项任务中，专家数据集中在 $+1$ 附近；成功 rollout 向较低正值偏移；失败 rollout 在零或负值附近出现峰；人工纠错覆盖低分自主阶段和高分恢复阶段。该图表明 STEAM 与数据来源和成败具有统计相关性，但尚不能证明 causal credit assignment。

#### Figure 6: Episode-wise Sum of Advantages / episode 累计 advantage

![[Papers/assets/STEAM/figure6.png]]

**说明**：成功与失败 episode 的累计 advantage 明显分离。毛巾和薯片失败通常发生在中后段，因此仍积累不少正分；可乐和 pick-and-place 多在初次抓取就失败，累计值更低。这也说明分数同时编码“失败发生得多晚”，并非纯粹的 episode success probability。

### 主要策略结果

#### Table 1: Policy Performance Comparison

| Method | Towel Succ. | Towel Score | Towel Thr. | Chip Succ. | Chip Score | Chip Thr. | Cola Succ. | Cola Score | Cola Thr. | PnP Succ. | PnP Score | PnP Thr. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BC | 33.3 | 3.3 | 42 | 39.5 | 4.6 | 16 | 52.0 | 2.4 | 71 | 63.8 | 1.5 | 230 |
| HG-DAgger | 40.0 | 3.7 | 48 | 53.3 | 6.0 | 22 | 58.3 | 2.6 | 84 | — | — | — |
| RECAP | 55.6 | 2.9 | 39 | 53.3 | 5.33 | 24 | 52.9 | 2.1 | 46 | 53.8 | 1.5 | 161 |
| **STEAM** | **92.3** | **4.9** | **58** | **93.8** | **7.5** | **48** | **75.0** | **3.0** | **90** | **80.0** | **1.8** | **254** |

**说明**：STEAM 在四项任务的 success、阶段分数和成功 episode/hour 上整体最优。摘要中的“+59、+54.3、+23、+16.2%”是相对 BC 的**绝对百分点**，不是相对最强 baseline 的相对百分比。论文没有报告 trial 数、随机种子或置信区间，因此真机数字的统计稳定性仍不清楚。

#### Figure 7: Different Training Data Combinations / 不同数据组合

![[Papers/assets/STEAM/figure7.png]]

**说明**：从 expert-only 到加入 correction，再到加入完整 rollout，长程任务持续受益。短程 pick-and-place 在 expert-only 下从 BC 63.8% 降到 55%，说明过滤干净而有限的专家数据可能因删掉过多样本而有害；只有加入大量非专家数据后才升到 80%。

### 消融实验

#### Table 2: Effect of Bin Count $N$

| Bins | Succ. | Score | Thr. |
|---|---:|---:|---:|
| $N=2$ | 27.3 | 2.8 | 41 |
| $N=8$ | 54.6 | 3.8 | 51 |
| **$N=32$（default）** | **92.3** | **4.9** | **58** |

**说明**：仅区分前进/后退不足以支持策略学习；更细的 temporal progress granularity 带来显著增益。不过该消融同时改变 predictor 输出难度与 advantage 分辨率，尚不能区分二者各自贡献。

#### Table 3: Effect of Ensemble Size $M$

| Ensemble | Succ. | Score | Thr. |
|---|---:|---:|---:|
| $M=1$ | 72.7 | 3.9 | 53 |
| **$M=3$（default）** | **92.3** | **4.9** | **58** |
| $M=5$ | 90.9 | 4.6 | 55 |

**说明**：从单模型到三模型提升明显，支持“ensemble-min 抑制 OOD false positive”的主张；继续扩大到五模型没有收益，作者选择 $M=3$ 平衡性能与计算量。

### 其他任务定性结果

#### Figure 8: Chip Checkout Advantage Curves

![Figure 8](https://arxiv.org/html/2606.29834v1/fig8.png)

**说明**：薯片交接重试时 advantage 暂时下降，成功恢复后重新升高；失败 rollout 在约 400 帧后持续低分；人工接管前可降至负值，接管后恢复。

#### Figure 9: Cola Restocking Advantage Curves

![Figure 9](https://arxiv.org/html/2606.29834v1/fig10.png)

**说明**：可乐补货中的初始错位、重新对齐和双臂交接速度被曲线捕获。论文 HTML 中该图片文件名为 `fig10.png`，但 caption 对应 Figure 9。

#### Figure 10: Pick-and-Place Advantage Curves

![Figure 10](https://arxiv.org/html/2606.29834v1/fig9.png)

**说明**：短程任务的专家轨迹几乎始终接近 $+1$；成功 rollout 多次抓取失败时得分下降，成功抓取后恢复；失败 rollout 初期接近物体仍有高分，随后卡死转为低分。HTML 文件名 `fig9.png` 与正文编号 Figure 10 互换，笔记按 caption 标注。

#### Figure 11: Individual Predictors vs. Minimum Aggregation

![Figure 11](https://arxiv.org/html/2606.29834v1/appendix_adv_3models.png)

**说明**：毛巾最终折叠重试时，Ensemble 3 错误维持高 advantage，而另外两个成员明显下降。逐点最小值成功压制该假阳性。该案例解释了机制，但尚未与 mean、median、LCB 或显式不确定性校准做系统比较。

---

## 批判性思考

### 优点

1. **监督成本低**：只用成功专家轨迹的时序结构就能获得 signed、dense、frame-level 信号。
2. **工程边界清楚**：STEAM 只做离线数据标注，部署时无需额外 critic，适合现有 VLA pipeline。
3. **保守聚合有效**：$M=1\rightarrow3$ 的真机消融和 Figure 11 都支持 min ensemble 的必要性。
4. **直接面对 mixed-quality data**：不再把整条 correction/rollout 简化成全好或全坏，能保留失败前进展与接管后恢复片段。
5. **多任务真机验证**：覆盖柔性物体、双臂协作、避碰和短程抓放，结果不仅来自仿真 benchmark。

### 局限性

1. **不是标准 RL advantage**：分数只反映时序效率，不保证对应 task return，更不提供 $Q-V$ 的 causal action credit。
2. **单调且“越快越好”的假设偏强**：必要等待、重抓、接触建立和安全减速可能被惩罚；不同阶段同样 offset 也未必同等重要。
3. **倒序专家轨迹不等于真实失败**：模型可能学到任务阶段顺序或视频时间箭头，而非物理可执行的 regression dynamics。
4. **分数据源 quantile 会强制保留固定比例**：即使某批 rollout 全部很差，也会挑出其中相对较好的片段；这不是跨数据源的绝对质量校准。
5. **未来窗口带来离线限制**：标注 $a_t$ 时需要 $f_{t+H}$，不能直接作为 online intervention trigger；动作产生延迟效果时，固定 $H$ 也可能错配 credit。
6. **实证统计不足**：没有 trial count、置信区间、多 seed predictor accuracy、frame-level ground truth、OOD calibration 或跨 control-frequency 实验。
7. **关键设计未充分拆分**：缺少 length normalization、reverse pairs、min vs. mean/LCB、统一阈值 vs. 分源阈值等消融。

### 潜在改进方向

1. 将 STEAM temporal score 与 episode success、[[Distributional Value Function]] 或 TD advantage 联合校准，避免把 proxy 当真实 reward。
2. 用 task-phase-aware normalization 区分抓取、交接、放置等阶段的重要性，特别适合布料和长程双臂任务。
3. 将 ensemble disagreement 显式转为置信度或 reject option，而不是只取最小值。
4. 加入 proprioception、力觉和触觉，弥补纯视觉无法区分接触质量、夹持力和轻微错位的问题。
5. 将固定 $H$ 改为 multi-horizon prediction，或按控制频率、动作 chunk 与阶段自适应选择 lookahead。
6. 在数据筛选之外，将低置信状态交给 [[HIL-SERL]] 式人工接管或 [[PLD]] 式 residual specialist 主动生成恢复数据。

### 与 RECAP、PLD、HIL-SERL 的关系

| 方法 | 质量信号 | 是否在线探索 | 主要作用 |
|------|----------|--------------|----------|
| [[Pi06|RECAP]] | episode reward → value → advantage | 分批 rollout/retrain | outcome-aware advantage-conditioned VLA |
| STEAM | 专家时间顺序 → temporal proxy | 否 | 离线筛选 mixed-quality frame/action |
| [[PLD]] | 稀疏任务 reward + residual Q | 是 | 生成 base-policy failure recovery data |
| [[HIL-SERL]] | reward classifier + Bellman Q | 是 | 真机 actor-critic 与人工探索纠错 |

**判断**：STEAM 最适合被理解为 RECAP 的廉价、无 reward 的 advantage-label front end，而不是完整 RL 替代品。对已有 RECAP/HIL 流水线，可把它作为 warm start、采样权重或诊断信号，并让 outcome-aware value 负责最终校准。

### 可复现性评估

- [ ] 训练代码开源——项目仓库只有静态页面，Code 按钮仍为 `soon`
- [ ] 预训练模型发布
- [x] 主要模型结构与核心超参数披露
- [ ] 数据集可获取——真机数据未公开
- [ ] 完整评测协议——缺 trial 数、置信区间与 seed 信息

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

- [[Pi0]]：policy backbone 与 flow-matching action generation。
- [[CFGRL]]：把二值 optimality condition 转成 classifier-free guided policy improvement。
- [[Pi06|RECAP]]：共享 advantage-conditioned VLA 的问题背景，但 STEAM 替换了 value/reward 来源。

### 对比

- [[HG-DAgger]]：只利用人工 corrective intervention，不对全部混合数据做 frame-level temporal scoring。
- [[HIL-SERL]]：真正的 online off-policy actor-critic，信号来自 reward 与 Bellman backup。
- [[PLD]]：用 residual RL specialist 主动生成恢复轨迹，而 STEAM 只重标已有数据。

### 方法相关

- [[Self-Supervised Learning]]：从专家轨迹时序结构获得免费监督。
- [[Temporal Offset Prediction]]：预测帧对间 signed progress。
- [[Advantage Modeling]]：将预测 offset 转成局部效率代理。
- [[Deep Ensemble]]：抑制专家分布外的高估。
- [[Advantage-Conditioned Policy]]：用二值 optimality condition 训练策略。
- [[Classifier-free Guidance]]：推理时将动作分布引向 $o=1$。

### 硬件/数据相关

- ARX 双臂机器人：毛巾折叠、薯片结账、可乐补货。
- Franka：单臂 pick-and-place。

---

## 速查卡片

> [!summary] STEAM
> - **核心**：从专家轨迹的 signed temporal offset 自监督学习 frame-level progress proxy。
> - **方法**：distributional offset predictor + worst-of-3 ensemble + 分源 quantile label + CFGRL。
> - **结果**：毛巾/薯片/可乐/PnP 成功率分别为 92.3/93.8/75.0/80.0%。
> - **边界**：不是 $Q-V$ advantage，依赖局部进展近似单调且“更快更好”。
> - **代码**：尚未公开；[项目页](https://liuzhihao2022.github.io/steam.github.io/)。

---

## 研究脉络依据

- **论文笔记**：[π*0.6 / RECAP](/Users/limx/mindflow/Papers/2511-PiStar06.md) 的 `## Method: Recap` 与 `### Advantage-Conditioned Policy Extraction` 用于区分 outcome-aware advantage 与 STEAM temporal proxy。
- **论文笔记**：[RoboBrain 2.5](/Users/limx/mindflow/Papers/2601-RoboBrain25.md) 的 `### Dense Temporal Value Estimation` 用于对照 hop-normalized、双向一致性的 temporal progress modeling。
- **论文笔记**：[π0.7](/Users/limx/mindflow/Papers/2604-Pi07.md) 的 `### 训练数据混合` 用于理解 mixed-quality data conditioning 的研究背景。
- **领域综述**：[VLA Survey](/Users/limx/mindflow/Topics/VLA-Survey.md) 的 `### 8. World Model Conditioning / RL Post-Training` 用于定位 advantage conditioning 在 flow-matching VLA 中的作用。
- **Codex 推断**：STEAM 更适合作为数据筛选与弱监督 front end，而不是 outcome-aware critic 或完整在线 RL 的替代品。

---

*笔记创建时间：2026-10-29*
