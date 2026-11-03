---
title: "任务空间接口：连接上层策略与 RL 控制器"
type: research-insight
status: active
tags: [task-space-interface, whole-body-control, human-demonstration, vla, visual-action-policy, hierarchical-policy]
related_papers: ["[[Papers/2604-Dyna21|Dyna-2.1]]", "[[Papers/2610-Workhorse|Workhorse]]"]
created: 2026-10-14
updated: 2026-10-14
---

# 任务空间接口：连接上层策略与 RL 控制器

## 核心洞察

[[Papers/2604-Dyna21|Dyna-2.1]] 与 [[Papers/2610-Workhorse|Workhorse]] 共享同一种分层学习范式：

> 人类示范先被表示为结构化的任务空间身体轨迹；上层策略学习如何从观测预测这类轨迹，底层 RL 控制器学习如何在具体机器人动力学下稳定执行它。

因此，两者最关键的共同点不是上层究竟叫 VLA、VA 还是 WAM，而是用一个相对本体无关的任务空间接口，把**行为生成**与**动态执行**解耦。

## 两个系统的对应关系

| 层级 | Dyna-2.1 | Workhorse |
|---|---|---|
| 任务/语义层 | VLM workflow orchestrator 选择下一子任务 | 无独立语义编排层；每个任务单独训练 |
| 上层动作策略 | 约 5 Hz、语言条件的 DYNA-2 VLA/WAM | 5 Hz、图像与本体历史条件的 visual-action planner |
| 任务空间接口 | URR：双腕、双肘、胸部、底盘 footprint | Five-link：躯干、双腕、双脚 |
| 底层执行策略 | 100 Hz RL whole-body controller | 50 Hz RL whole-body tracker |
| 硬件输出 | 关节目标与轮速 | 关节 setpoints |

Workhorse 的 planner 不是纯粹的“视觉到动作”：它还输入 five-link history、投影重力和躯干高度，因此更准确的说法是 **visual-proprioceptive action policy**。Dyna-2.1 则在动作策略之上还有语言工作流编排器，能够维持小时级任务状态。

## “同一份数据训练两层”的准确含义

### Workhorse：强意义上的同一数据

同一批同步人体示范同时提供：

1. 第一视角图像与 five-link history，用于训练 visual planner 预测未来 five-link chunk；
2. 同一 five-link motion，作为 RL tracker 的命令、姿态目标与动作先验。

两层分开训练，但共享同一条人体任务空间轨迹。部署时，planner 的预测才真正成为 tracker 的输入。作者还分别模拟对方会产生的误差：planner augmentation 注入执行后的历史漂移，command augmentation 注入重规划之间的命令漂移与跳变。

### Dyna-2.1：共享表示与部分共享数据

Dyna 报告称同一人体动作转成 URR 后，可以同时作为：

1. DYNA-2 policy 的动作监督；
2. 仿真 RL whole-body controller 的姿态跟踪目标和动作先验。

但 Dyna 的训练集合更加异构：上层策略还混合大规模人类视频和 robot fleet data，底层控制器还使用合成 URR 目标与仿真域随机化。因此它更准确地体现为**共享 URR 数据表示与部分监督来源**，不应理解为两层逐样本使用完全相同的数据集。

## 为什么这种架构重要

### 1. 把人类数据变成可复用的行为监督

人体示范不必先被压成某个机器人专属的关节角。上层学习“手、脚、躯干应该去哪里”，底层再解决关节协调、平衡、可达性与动力学约束。

### 2. 把硬件差异限制在控制层附近

稳定的任务空间接口允许机器人换代后复用上层数据和动作语义。新的 embodiment 仍可能需要重训 controller，甚至因相机外观、身体比例和可达空间不同而重训 planner，但不必重新定义整个 action space。

### 3. 让 RL 专注于它擅长的问题

RL 不负责从图像理解“下一步做什么”，而负责在仿真中学习平衡、抗扰、接触切换和动力学鲁棒性。上层策略则集中处理视觉闭环、任务进展和较长时间尺度的行为生成。

### 4. 为分层误差建模提供明确边界

两层独立训练会产生 interface distribution shift：上层给出的命令可能漂移、跳变或不可达，底层执行误差又会改变上层下一次看到的状态。Workhorse 的消融说明，仅共享动作接口还不够，必须显式训练两层适应彼此在部署时产生的误差。

## 对 VLA / WAM 研究的启发

1. **动作表示可能比模型名字更关键**：与其只比较 VLA、VA 或 WAM backbone，不如先判断中间动作空间是否保留任务结构、能否由人体数据稳定提取、能否被低层控制器可靠跟踪。
2. **Policy 与 controller 可以共享示范，但优化目标不同**：上层学习条件生成和闭环纠错；下层学习 dynamics-aware tracking。共享数据不意味着共享网络或端到端联合损失。
3. **跨本体迁移应拆成三项评估**：动作表示是否复用、人体数据是否复用、模型权重是否零样本复用。Workhorse 证明了前两项，没有证明第三项。
4. **WAM 不一定需要直接输出电机动作**：WAM/VLA 可以在可解释的任务空间中生成身体轨迹，由独立 RL controller 承接高频执行。
5. **值得进一步研究 policy-controller co-training**：可以让 planner 看到 controller 的可达性、不确定性或失败预测，也可以让 controller 的训练命令分布由当前 planner 在线生成，而不只依赖手工增强。

## 局限与反例风险

- 任务空间接口可能形成信息瓶颈。URR 与 five-link 都没有完整表达触觉、接触力和灵巧手内部状态。
- 稳定接口不等于真正零样本跨本体；相机自遮挡、身体比例和控制能力仍会改变上层策略的输入输出分布。
- Workhorse 的证据来自单一示范者、单一房间和任务专用策略；Dyna-2.1 则是缺少完整训练细节与消融的公司技术报告。
- 因此，目前可以把它视为一个有工程吸引力、得到初步实验支持的架构模式，不能据此断言它优于所有端到端 VLA。

## 关联笔记

- [[Papers/2604-Dyna21|Dyna-2.1]]：URR、VLA/WAM、100 Hz RL controller 与 workflow orchestration。
- [[Papers/2610-Workhorse|Workhorse]]：five-link interface、visual-action planner、50 Hz RL tracker 与双向误差增强。
- [[Unified Robot Representation]]：Dyna 使用的任务空间身体表示。
- [[Five-Link Interface]]：Workhorse 使用的五链路任务空间表示。
- [[Whole-Body Control]]：将任务空间目标转成具体硬件命令。
- [[Cross-embodiment Transfer]]：区分接口、数据和模型权重的迁移层次。

## 个人笔记

> [!note] 我的记录
> - 对当前 VLA/WAM 架构的启发：
> - 可以设计的验证实验：
> - 中间动作接口还需要包含什么：
> - 其他：
