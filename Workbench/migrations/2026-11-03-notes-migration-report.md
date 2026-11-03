# Legacy notes migration plan

- Source HEAD: `8bdcf185e277fc522c49d22d6304ef7edb50f52d`
- Included items: 46

## Counts

- `blocked:blocked`: 1
- `import-daily:applied`: 2
- `import-insight:applied`: 3
- `import-paper:blocked`: 1
- `import-paper:ready`: 22
- `import-source:applied`: 6
- `import-topic:ready`: 2
- `import-trending:applied`: 1
- `merge-paper:ready`: 8

## Items

- `DailyPapers/.history.json` → `Workbench/daily/.history.json`: **import-daily/applied** — target matches deterministic migration output
- `DailyPapers/2026-10-28-论文推荐.md` → `Workbench/daily/2026-10-28-论文推荐.md`: **import-daily/applied** — target matches deterministic migration output
- `GitHubTrending/2026-W44 GitHub周榜.md` → `Workbench/trending/2026-W44 GitHub周榜.md`: **import-trending/applied** — target matches deterministic migration output
- `PaperNotes/VLA/FAST.md` → `Papers/2501-FAST.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/FLARE.md` → `Papers/2505-FLARE.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/FLASH.md` → `Papers/2605-FLASH.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/GR00T N1.5.md` → `Papers/lega-GR00TN15.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/GR00T N1.6.md` → `Papers/lega-GR00TN16.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/GR00T N1.md` → `Papers/2503-GR00TN1.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/VLA/GR00T-Series-Survey.md` → `Topics/GR00T-Series-Survey.md`: **import-topic/ready** — approved series survey
- `PaperNotes/VLA/HIL-SERL.md` → `Papers/2410-HILSERL.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/HiRobot.md` → `Papers/2502-HiRobot.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/VLA/KI.md` → `Papers/2505-KI.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/MEM.md` → `Papers/2603-MEM.md`: **merge-paper/ready** — exact official URL and normalized title match
- `PaperNotes/VLA/PLD.md` → `Papers/2511-PLD.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/Pi-Series-Survey.md` → `Topics/Pi-Series-Survey.md`: **import-topic/ready** — approved series survey
- `PaperNotes/VLA/Pi0.md` → `Papers/2410-Pi0.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/VLA/Pi05.md` → `Papers/2504-Pi05.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/VLA/Pi06 Base Model.md` → `-`: **blocked/blocked** — misfiled concept requires semantic absorption
- `PaperNotes/VLA/Pi06.md` → `Papers/2511-PiStar06.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/VLA/Pi07.md` → `Papers/2604-Pi07.md`: **merge-paper/ready** — exact official URL and normalized title match
- `PaperNotes/VLA/RLT.md` → `Papers/lega-RLT.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/STEAM.md` → `Papers/2606-STEAM.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/VLA/Workhorse.md` → `Papers/2610-Workhorse.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/_inbox/HEISD.md` → `Papers/2603-HEISD.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/_inbox/KERV.md` → `Papers/2603-KERV.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/_inbox/Mean Flow VLA.md` → `Papers/2603-MeanFlowVLA.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/_inbox/One-step Diffusion Policy.md` → `Papers/2410-OnestepDiffusionPolicy.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/_inbox/Pi0.md` → `Papers/2410-Pi0.md`: **merge-paper/ready** — high-confidence identity match
- `PaperNotes/_inbox/Spec-VLA.md` → `Papers/lega-SpecVLA.md`: **import-paper/blocked** — missing paper identity
- `PaperNotes/_inbox/Triton-Pi0.md` → `Papers/2510-TritonPi0.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/DiT4DiT.md` → `Papers/2603-DiT4DiT.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/Dyna-2.1.md` → `Papers/2604-Dyna21.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/Fast-WAM.md` → `Papers/2603-FastWAM.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/GAWM.md` → `Papers/2610-GAWM.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/OpenWAM.md` → `Papers/2609-OpenWAM.md`: **import-paper/ready** — old-only paper candidate
- `PaperNotes/world model/WAM-Survey.md` → `Papers/2609-WAMSurvey.md`: **import-paper/ready** — old-only paper candidate
- `ResearchNotes/Dyna2部署的一些know-how.md` → `ResearchSources/Insights/Dyna2部署的一些know-how.md`: **import-insight/applied** — target matches deterministic migration output
- `ResearchSources/Insights/任务空间接口：连接上层策略与RL控制器.md` → `ResearchSources/Insights/任务空间接口：连接上层策略与RL控制器.md`: **import-insight/applied** — target matches deterministic migration output
- `ResearchSources/Insights/访问模式驱动的机器人训练数据物理布局.md` → `ResearchSources/Insights/访问模式驱动的机器人训练数据物理布局.md`: **import-insight/applied** — target matches deterministic migration output
- `ResearchSources/Sources/Fast-WAM- Do World Action Models Need Test-time Future Imagination?.md` → `ResearchSources/Sources/Fast-WAM- Do World Action Models Need Test-time Future Imagination?.md`: **import-source/applied** — target matches deterministic migration output
- `ResearchSources/Sources/Isaac GR00T N1.7 Early Access Release.md` → `ResearchSources/Sources/Isaac GR00T N1.7 Early Access Release.md`: **import-source/applied** — target matches deterministic migration output
- `ResearchSources/Sources/Training Dyna-2 at million-hour scale, repeatably.md` → `ResearchSources/Sources/Training Dyna-2 at million-hour scale, repeatably.md`: **import-source/applied** — target matches deterministic migration output
- `ResearchSources/Sources/π0- A Foundation Model for Robotics with Sergey Levine - 719.md` → `ResearchSources/Sources/π0- A Foundation Model for Robotics with Sergey Levine - 719.md`: **import-source/applied** — target matches deterministic migration output
- `ResearchSources/Sources/数采厂的变化.md` → `ResearchSources/Sources/数采厂的变化.md`: **import-source/applied** — target matches deterministic migration output
- `ResearchSources/Sources/读懂 OpenPI 的 π0.5：从源码出发，真正看懂模型结构、训练逻辑和推理过程.md` → `ResearchSources/Sources/读懂 OpenPI 的 π0.5：从源码出发，真正看懂模型结构、训练逻辑和推理过程.md`: **import-source/applied** — target matches deterministic migration output
