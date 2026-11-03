---
source_vault: notes
source_path: PaperNotes/VLA/Pi-Series-Survey.md
date_migrated: 2026-11-03
title: Pi 系列 VLA 综述（2024-10 → 2026-05）
tags: [VLA, Survey, PhysicalIntelligence]
type: survey
created: 2026-06-06
updated: 2026-09-29
covers: ["[[Pi0]]", "[[FAST]]", "[[Pi05]]", "[[Pi06]]", "[[Pi07]]", "[[KI]]", "[[RLT]]", "[[HiRobot]]", "[[MEM]]", "[[FLASH]]"]
---

# Pi 系列 VLA 综述：从单模态到分层记忆 + 在线 RL 的两年演进

> 综述对象：Physical Intelligence 自 2024-10 起公开的 10 篇 VLA 工作。
> 关键问题：他们到底解决了什么问题？为什么是这条路而不是别的？

## 0. 一句话总结

> Pi 系列不是一个模型，而是 **以连续 flow-matching 为主线、并行探索 FAST 离散动作 token 的 VLA 工程体系**——
> 用十篇工作，把 VLA 从「能做单任务」一路推到「动作可高效 token 化、能跟人对话、能从经验学、能记住半小时上下文、能实时部署」。
> **核心不在架构创新，而在**：每代都精准识别上一代的瓶颈，用最便宜的工程手段解决它。

## 1. 全景图

```
                                ┌── 训练策略 ────┐
                                │  KI (2025-05) │
                                │  stop-gradient │
                                │  + co-training │
                                └───────┬────────┘
                                        ▼ 启发
基座线（每代解决前代痛点）
   ┌──────────────────────────────────────────────────────────┐
   │  Pi0 (2024-10) ─► Pi05 (2025-04) ─► Pi06 (2025-11) ─► Pi07 (2026)
   │   架构基座          开放世界泛化       从经验学(Recap)       涌现能力
   │   PaliGemma        异构 co-training  Iterated Offline RL  Prompt Expansion
   │   + Action Expert  离散→连续两阶段                         三件套
   │   + Flow Matching                                          + KI 风格训练
   └──────────────────────────────────────────────────────────┘
            │              │                 │                  │
            ├── FAST (2025-01)               │                  │
            │   DCT + 量化 + BPE              │                  │
            │   └── Pi0-FAST：纯 AR 动作路线   │                  │
            │              │                 │                  │
            │              │                 ├── RLT (2026)     │
            │              │                 │   冻结 VLA       │
            │              │                 │   + 在线 actor-critic
            │              │                 │
            ├── HiRobot (2025-02) ◄──────────┤
            │   双 VLM 分层                   │
            │   System 1 / System 2          │
            │                                 │
            └── MEM (2026-03) ◄──────────────┘
                双记忆系统
                short-term video + long-term language
                                                          ┌──────────────────┐
                                                          │ FLASH (2026-05)  │
                                                          │ speculative      │
                                                          │ inference 加速   │
                                                          │ 3.04×            │
                                                          └──────────────────┘
                                                          所有 dVLA 通用
```

## 2. 十篇工作卡片

### 2.1 [[Pi0]]（2024-10）— 一切的基座

- **架构**：PaliGemma 3B（VLM 主干）+ 300M Action Expert（独立 FFN，共享 self-attention）+ flow matching
- **关键决策**：
  - 用 **flow matching** 而非 diffusion → 10 步出 50 步动作 chunk，73 ms 时延
  - 用 **跨形态混杂数据**（OXE + Bridge + DROID + 自采 903M 步）+ sqrt(n) 加权
  - **双 expert 共享 attention 但 FFN 独立** → VLM 知识不被动作训练污染（这就是后来 KI 的雏形）
- **意义**：第一个真正能"开箱即用"通用 dexterous manipulation 的 VLA。

### 2.2 [[FAST]]（2025-01, RSS 2025）— 频域动作 tokenizer 与 π0-FAST

- **FAST tokenizer**：把连续动作 chunk 依次做 [[DCT]]、量化、列优先展开和 [[BPE]]，得到紧凑的 [[FAST Token|离散动作 token]]；它是分析式可逆流水线，不需要另训神经 tokenizer。
- **要解决的问题**：朴素逐时间步分箱会在高频控制中生成数百个高度相关 token，使 next-token prediction 退化成“复制上一步”。FAST 先压缩动作的时间冗余，再交给自回归 VLA 学习。
- **π0-FAST 模型**：把 FAST token 接到 π0 的 PaliGemma 主干上，以纯 cross-entropy 自回归生成动作；它不是原版 π0 的 flow-matching action expert，而是同一数据/视觉语言基座上的离散动作分支。
- **关键结果**：在约 10,000 小时跨形态数据上，π0-FAST 基本匹配连续动作 π0 的任务性能，训练 GPU 时间约为后者的 **1/5**；FAST+ 还能跨机器人形态、动作空间与控制频率复用。
- **系列定位**：FAST 同时开启两条后续路线：其一是可独立部署的 π0-FAST；其二是在 Pi05、KI、Pi06、Pi07 中用 FAST token 给 VLM 提供稳定的离散监督，而连续 action expert 仍用 flow matching。

> [!important] FAST 与 π0-FAST 不是同一个概念
> **FAST** 是动作 tokenizer；**π0-FAST** 是使用该 tokenizer 训练出的 autoregressive VLA。后续 Pi05/KI/Pi06/Pi07 使用 FAST token 监督 backbone，并不意味着它们的最终动作头都变成 π0-FAST。

### 2.3 [[Pi05]]（2025-04）— 开放世界泛化

- **核心**：400 小时移动操作 + 6 类异构数据 co-training（97.6% 不来自目标机器人）
- **训练 recipe**：
  - Stage 1：280k 步 FAST token next-token-prediction（α=0）
  - Stage 2：80k 步加 action expert + flow matching（α=10）
- **解决的问题**：Pi0 训练不稳定 + 单形态局限
- **新能力**：完全没见过的真实家庭做 10–15 分钟长程清扫；统一权重的 hierarchical inference 击败 zero-shot GPT-4
- **副作用**：数据基础设施门槛极高，复现成本天花板

### 2.4 [[KI]]（2025-05）— 训练策略原典

- **核心机制**：
  - VLM backbone 通过 FAST token AR loss + VLM 数据 co-training 训练（梯度回传）
  - Action expert 通过 flow matching 训练（**stop-gradient 切断到 VLM 的梯度**）
- **效果**：训练 **7.5×** 加速 + 推理与 Pi0-FAST 相当 + **语言遵循最强**
- **历史定位**：Pi05 的两阶段是 KI 的"时间展开"，Pi07 的 Knowledge Insulation 直接复用本论文方法
- **核心洞察**：连续动作监督会"污染"VLM 的语言能力，必须用离散信号给 VLM、连续信号给 action expert

### 2.5 [[HiRobot]]（2025-02, ICML 2025）— 分层语言架构

- **架构**：高层 VLM（PaliGemma）拆指令 → 低层 Pi0 执行
  - **System 2 慢思考**（~1 Hz）：开放式指令解析
  - **System 1 快反应**（~50 Hz）：连续动作生成
- **关键工程**：用 LLM 合成「用户中途打断 / 改主意 / 纠错」的 [[Synthetic Interaction Data|交互数据]]
- **效果**：3 平台 × 3 任务，Instruction Adherence 比 GPT-4o 高 **40%+**
- **解决的问题**：单一 VLA 听不懂复杂/对话式指令

### 2.6 [[Pi06]]（2025-11）— 从经验学（Recap）

- **核心算法 Recap = Distributional Value Function + Advantage-Conditioned Policy + Iterated Offline RL + HG-DAgger**
- **关键 trick**：用**二值 advantage token**（`<good>` / `<bad>`）当文本条件 → 完全绕开 PPO/AWR 在 flow-matching 上的 likelihood 难题
- **效果**：espresso / laundry / box assembly 三大任务，**吞吐翻倍、失败率减半**
- **意义**：VLA 走向真实生产部署的里程碑（"能从失败中学"）

### 2.7 [[MEM]]（2026-03）— 长程记忆

- **双记忆系统**：
  - **Short-term**：30 秒视频，用 [[Space-Time Separable Attention]] 编码
  - **Long-term**：LLM 把视觉/动作历史**压缩成语言摘要** + RAG 检索
- **效果**：15 分钟级长程任务（厨房整理 / 煎奶酪）进度 **25% → 75%**
- **解决的问题**：Pi 系列长期诟病的 [[Causal Confusion]] + 无跨房间记忆
- **关键技巧**：把视觉/动作压成**语言**而非 token，上下文不爆炸

### 2.8 [[Pi07]]（2026）— 涌现能力

- **核心**：5B VLA + **Prompt Expansion 三件套** + Knowledge Insulation
  - **Detailed Language Label**：子任务级语言指令（"pinch left sleeve at cuff"）
  - **Multi-view Subgoal Image**：世界模型生成视觉中间目标
  - **Episode Metadata**：场景/机器人/相机配置
- **涌现能力**：指令跟随 / 跨形态零样本 / 组合泛化
- **效果**：UR5e shirt folding 上零样本与 **top-2% 经验人类遥操作**打平
- **意义**：单一通用模型零样本追平甚至超过专门 RL 后训练的 specialist

### 2.9 [[RLT|RL Token]]（2026）— 在线 RL 适配

- **架构**：冻结的 Pi06 + `<rl>` readout token + encoder-decoder transformer + 轻量 TD3 actor-critic
- **关键设计**：actor 接收 VLA 参考动作作为 pass-through 输入 + BC 正则 + 50% reference action dropout
- **效果**：4 个亚毫米精度任务 throughput 最多 **3×**；Ethernet 任务比专家遥操作还快 **2.2×**
- **vs Recap**：Recap 重训整个 VLA（离线），RL Token 冻结 VLA + 外挂 actor-critic（在线、轻量、快）

### 2.10 [[FLASH]]（2026-05）— 推理加速

- **核心**：把 LLM 的 [[Speculative Decoding]] 搬到 flow-matching dVLA
- **机制**：
  - **Full path**：完整多步 flow matching（正确但慢）
  - **Flash path**：draft 模型出动作草稿 + Action Expert 用「插值端点重构」并行验证
  - **Phase-aware Fallback**：gripper switch 时强制走 full path
  - **Distance Threshold**：草稿验证偏差超阈值时回退
- **效果**：LIBERO 19.1 ms / **3.04× 加速**，SR 仅掉 0.3 pp；真实传送带 15 m/min 是测试中**唯一非零成功**的方法
- **意义**：和训练侧改进解耦，整个 Pi 全家可用

## 3. 横向对比表

### 3.1 训练策略

| 论文 | 数据规模 | 关键 trick | 训练成本 | VLM 是否更新 |
|---|---|---|---|---|
| [[Pi0]] | 903M 步混杂 | sqrt(n) 加权 | 高 | ✓ |
| [[FAST]] / [[Pi0-FAST]] | 约 10,000h 跨形态 | DCT + 量化 + BPE；纯 AR 动作 | **约为 diffusion π0 的 1/5** | ✓（cross-entropy） |
| [[Pi05]] | 400h 移动 + 6 类异构 | 离散→连续两阶段 | **极高** | ✓ |
| [[KI]] | 同 Pi0 | **stop-gradient + co-training** | **低（7.5×）** | ✓（仅离散信号） |
| [[Pi07]] | 同 Pi0.5 + Prompt Expansion | KI 风格 + 三件套 | 高 | ✓（仅离散信号） |
| [[Pi06]] (Recap) | 自采 rollout + HG-DAgger | Advantage token + 迭代离线 RL | **重**（每轮重训） | ✓ |
| [[RLT]] | rollout + replay buffer | 冻结 + 外挂 actor-critic | **极轻** | ✗ |

### 3.2 推理性能

| 模型 | 单步时延 | 加速倍数 | 适用场景 |
|---|---|---|---|
| Pi0 | 73 ms | 1× | baseline |
| Pi0-FAST | ~60 ms | 1.2× | 离散 token 路线 |
| FLASH（Pi 任意基座 + Flash path） | **19.1 ms** | **3.04×** | 实时部署 |

### 3.3 解决的核心问题

| 论文 | 痛点 | 解决方法 | 留下的痛点 |
|---|---|---|---|
| Pi0 | "通用 VLA 不存在" | flow matching + 跨形态混杂 | 训练不稳，单形态局限 |
| FAST / π0-FAST | 高频动作 token 冗长、AR 策略学成复制 | 频域压缩 + BPE + next-token prediction | 离散动作仍受量化误差与自回归延迟影响 |
| Pi05 | 单形态 + OOD 弱 | 异构 co-training + 两阶段 | 数据门槛极高，无法从失败学 |
| KI | 训练慢 + 语言能力流失 | stop-gradient + co-training | （工程组件，不独立解决任务） |
| HiRobot | 听不懂对话式指令 | 双 VLM + 合成对话数据 | 高层无长上下文记忆 |
| Pi06 (Recap) | 不能从失败学 | Advantage-conditioned 监督学习 | 全模型重训，长 horizon 弱 |
| MEM | 记不住半小时上下文 | 双时间尺度记忆系统 | 静态环境假设 |
| Pi07 | 任务专门化 | Prompt Expansion + KI | 推理慢 |
| RL Token | 全模型微调贵且慢 | 冻结 + 外挂 actor-critic | 仅适合短程高精度任务 |
| FLASH | dVLA 推理慢 | Speculative Inference | 训练侧无收益 |

## 4. 技术演化的四条主线

### 主线 A：**架构层级化**（语义抽象 + 时间尺度）

```
Pi0 (单一 VLA)
   │
   ├──► HiRobot：高层 VLM + 低层 VLA  ← 语义抽象分层（System 1/2）
   │
   └──► MEM：双时间尺度记忆系统      ← 时间尺度分层（秒 / 分 / 小时）

Pi07 同时整合两者的精神（Prompt Expansion 三件套本质是"显式给低层提供高层语义"）
```

### 主线 B：**训练策略精细化**（"什么时候不让 VLM 被污染"）

```
Pi0：双 expert 共享 attention，FFN 独立      → 弱隔离
KI：stop-gradient 完全切断动作梯度回 VLM     → 半冻结
RLT：冻结整个 VLA，外挂 readout + actor-critic → 全冻结
```

**洞察**：Pi 团队对"VLM 知识在 RL/微调过程中会被污染"这件事想得极透。
三种隔离强度对应三种使用场景：
- **弱隔离**：从零训练通用 VLA
- **半冻结**：在大规模数据上加新能力（如 Pi07 的语言遵循）
- **全冻结**：在线快速适配特定任务（如 RLT 的高精度插针）

### 主线 C：**RL 路线分叉**（offline vs online）

```
Pi06 Recap                          RL Token
─────────────                       ─────────────
全模型微调                            冻结 + 外挂
迭代离线 RL                           Off-policy 在线 actor-critic
HG-DAgger 收数据                     环境 rollout
Advantage-conditioned 监督学习        TD3 actor-critic
长程多任务（espresso/laundry）        高精度短程（插针/拧螺丝）
```

两条路**正交互补**——同样是"让 VLA 从经验学"，但**离线 vs 在线**、**重训 vs 冻结**、**长程 vs 高频**完全不一样。

### 主线 D：**动作表示与推理效率**（连续流 vs 离散 token）

- **连续路线**：Pi0 用 flow matching action expert 直接生成连续动作，表达精度高、适合多模态动作，但需要多步积分；FLASH 再从推理侧减少昂贵 full-path 调用。
- **离散路线**：FAST 先在时间频域压缩动作，再由 π0-FAST 做标准 next-token prediction，复用 LLM 的训练、后训练与解码基础设施。
- **混合路线**：Pi05、KI、Pi06、Pi07 用 FAST token 稳定训练 VLM/backbone，同时保留 flow-matching action expert 输出连续控制，实现“离散语义监督 + 连续精细动作”。

这里最容易混淆的一点是：FAST 不只是加速器。它首先改变的是 **action representation 和训练目标**；FLASH 才主要改变推理调度。

## 5. 关键概念地图

| 概念 | 首次出现 | 后续被谁继承 |
|---|---|---|
| [[Flow Matching VLA]] | Pi0 | 全系列 |
| [[Action Expert]] | Pi0 | 全系列 |
| [[FAST Token]] | FAST / π0-FAST | Pi05 / KI / Pi06 / Pi07 |
| [[Co-training]] | Pi05 | KI / Pi07 |
| [[Knowledge Insulation]] | KI | Pi07 |
| [[Hierarchical Inference]] | Pi05 | HiRobot |
| [[System 1 System 2]] | HiRobot | （概念引入） |
| [[Synthetic Interaction Data]] | HiRobot | （概念引入） |
| [[Recap]] | Pi06 | （Pi06 内置） |
| [[Advantage-Conditioned Policy]] | Pi06 | （Pi06 内置） |
| [[Iterated Offline RL]] | Pi06 | （Pi06 内置） |
| [[Multi-Scale Memory Factorization]] | MEM | （概念引入） |
| [[Language Memory]] | MEM | （概念引入） |
| [[Prompt Expansion]] | Pi07 | （概念引入） |
| [[RL Token]] | RLT | （概念引入） |
| [[Reference-Action Pass-Through]] | RLT | （概念引入） |
| [[Speculative Inference]] | FLASH | （概念引入） |
| [[Endpoint Reconstruction]] | FLASH | （概念引入） |

## 6. 三个值得思考的设计哲学

### 6.1 「不破坏既有能力」是 Pi 团队的最高原则

- KI 用 stop-gradient 保 VLM 语言能力
- Pi07 的 Knowledge Insulation 同样思路
- RLT 直接全冻结
- HiRobot 也是新加高层 VLM 而非改 Pi0

**反例**：业界很多 VLA 工作直接 fine-tune 整个 VLM，结果语言能力退化。Pi 团队的"洁癖"反而是工程胜利。

### 6.2 「先文本，再连续」是反复出现的模式

- FAST：连续动作 → DCT 频域系数 → 量化 + BPE 离散 token
- Pi05 两阶段：FAST token → flow matching
- KI：FAST token 信号给 VLM，flow matching 信号给 action expert
- Pi06 Recap：用**二值 token** 而非连续 advantage 做条件
- MEM：长期记忆用**语言摘要**而非 raw token

**洞察**：Pi 团队发现连续监督信号在大模型训练里**信噪比极低 + 数值不稳**，能用离散文本表达的就先转文本——这是 LLM 时代留下的工程经验。

### 6.3 「数据 + 工程」远比「架构创新」重要

十篇工作里，真正大改基座或控制接口的仍是少数；更多收益来自围绕既有基座逐层补齐工程瓶颈：
- 动作表示（FAST / π0-FAST）
- 训练策略（KI、Pi05 两阶段、Recap）
- 数据组合（Pi05 的六类异构、Pi07 的 Prompt Expansion）
- 推理调度（FLASH）
- 系统外挂（HiRobot 高层、MEM 记忆、RLT actor-critic）

**对学术界的启示**：在 VLA 这个领域，**改架构的边际收益在递减**，把工程做扎实的边际收益还很大。

## 7. 还没解决的瓶颈

| 瓶颈 | Pi 系列现状 | 可能的下一步 |
|---|---|---|
| **多 agent 协作** | 完全没碰 | 类似 Decision Transformer 的多 agent 扩展？ |
| **完全开放词汇任务** | Pi07 已涌现，但远未 robust | 更大数据 + 更好 grounding |
| **Sim-to-real** | 几乎全靠真实数据 | 世界模型生成数据（Pi07 已开始） |
| **跨室记忆** | MEM 只解决到 30 分钟 | 持久化记忆系统 |
| **能耗 + 部署** | FLASH 缓解了延迟，但模型本体还是 5B+ | 蒸馏 / 量化（Pi 团队尚未公开） |

## 8. 推荐阅读顺序

如果你刚入坑 VLA，按以下顺序读 vault 里的笔记最省事：

1. **[[Pi0]]**（先理解 VLA 的基础架构）
2. **[[FAST]]**（理解动作为什么要先压缩，以及 π0-FAST 与连续 π0 的分叉）
3. **[[Pi05]]**（看怎么靠数据 + 训练 recipe 把基础拉开档次）
4. **[[KI]]**（搞懂 stop-gradient 的训练哲学，后面会反复用到）
5. **[[HiRobot]]**（看分层 + System 1/2 思路）
6. **[[Pi06]]**（理解 Recap = 把 RL 还原为监督学习的精彩 trick）
7. **[[RLT]]**（对比 Recap，看另一种"让 VLA 用 RL 学"的路线）
8. **[[MEM]]**（看怎么把"记忆"工程化）
9. **[[Pi07]]**（看以上所有积木怎么集成出涌现能力）
10. **[[FLASH]]**（推理加速，用一次理解 speculative inference 在 VLA 上的迁移）

## 9. 一句话外推

> 如果你赌 Pi 团队的下一篇论文（暂称 Pi08），最可能的方向不是更大的模型，
> 而是 **持久化跨场景记忆 + 多 agent 协作 + 蒸馏后的实时部署系统**——
> 因为这正是当前 vault 10 篇工作**横向对照后仍没人填的格子**。

---

## 引用的笔记

- [[Pi0]] · [[FAST]] · [[Pi05]] · [[Pi06]] · [[Pi07]]
- [[KI]] · [[RLT]] · [[HiRobot]] · [[MEM]] · [[FLASH]]
- 配套：[[Pi06 Base Model]]

## 相关概念

- 动作表示：[[FAST Token]] · [[Pi0-FAST]] · [[DCT]] · [[BPE]]
- 训练策略：[[Knowledge Insulation]] · [[Co-training]] · [[Hierarchical Inference]]
- RL：[[Recap]] · [[Advantage-Conditioned Policy]] · [[Iterated Offline RL]] · [[RL Token]] · [[Off-policy Actor-Critic]] · [[TD3]]
- 推理：[[Speculative Inference]] · [[Flow Matching VLA]]
- 记忆：[[Multi-Scale Memory Factorization]] · [[Language Memory]] · [[Causal Confusion]]
- 系统设计：[[System 1 System 2]] · [[Synthetic Interaction Data]] · [[Prompt Expansion]]
