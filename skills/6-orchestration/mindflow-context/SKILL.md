---
name: mindflow-context
description: 当任务涉及研究、架构、实验设计、方法选择、论文与实现映射或历史决策，或用户明确要求使用 MindFlow 时，按项目 profile 检索相关论文、领域图谱和历史知识；机械格式化与普通局部测试修复不触发，MindFlow 默认只读。
---

## Purpose

保持源码事实与研究知识两条独立证据通道。只检索与当前任务相关的有界证据，不加载整个 vault，也不把源码、运行时状态或大型产物复制进 MindFlow。

## Inputs

- `task_text`：必需，使用用户的当前任务文本。
- `skill_dir`：将实际读取的 `SKILL.md` 路径解析为 canonical path 后取其父目录；不要保留全局 discovery symlink 的未解析路径。
- `vault_root`：用户可显式指定绝对路径；否则从 canonical `skill_dir` 向上查找同时包含 `AGENTS.md`、`pyproject.toml` 和 `skills/6-orchestration/mindflow-context` 的最近祖先。找不到时停止，不用机器专属路径或 cwd 猜测。
- `repo_root`：若可用，默认取 `git rev-parse --show-toplevel` 的结果。
- `writeback_approval`：可选且必须来自用户对本次具体写回的显式批准；永不从任务背景、只读分析或既往批准中推断。

## Steps

1. **分类触发条件。** 研究、架构、实验设计、方法选择、论文与实现映射、历史决策，以及用户明确要求 MindFlow 时触发。机械格式化、普通局部测试修复和纯语法检查不触发。
2. **解析 profile 与可选 Project。** 优先使用 vault 的 Python 3.12 环境运行 validator；为兼容 code repository 内的只读沙箱，通过 stdin 执行脚本：`PYTHONDONTWRITEBYTECODE=1 <resolved-vault>/.venv/bin/python - --vault <resolved-vault> --repo-root <repo-root> --json < <canonical-skill-dir>/scripts/validate_profiles.py`。若 `.venv/bin/python` 不存在，改用 `uv run --project <resolved-vault> --frozen python -B - ...`。如果且仅如果这两条路径被只读沙箱禁止读取标准库或写 cache，可在确认 `python3` 为 3.10+ 且 `python3 -c 'import yaml'` 成功后，用 `PYTHONDONTWRITEBYTECODE=1 python3 -B - ... < validate_profiles.py` 执行同一只读 validator；该例外不适用于其他 MindFlow helper。只从 `Workbench/RepositoryProfiles/*.md` 选择 repository profile。canonical resolved `repo_root` 优先，repository name、`repo_key` 和 aliases 的 case-folded identity 只在没有 root claimant 时兜底；歧义立即停止。PARA Project 只在用户明确给出 `project_key` 时通过 `--project-key` 选择；返回 `project_selection_required` 时报告候选 keys，不读取任何 Project note，也不猜测。
3. **处理 profile 失败。** 对 stale root 或 missing entrypoint 只报告路径和错误，不编辑 profile。没有 profile 时，以 repository name、任务词和代码符号继续通用检索，并明确说明“本次未使用项目 profile”。
4. **读取有界 project context。** validator 的 `vault_entrypoints` 相对 vault root；profile `workspace_context` 只含已验证 wrapper 的 `main.md`、`engineering.md` 和显式 `workspace_entrypoints`。显式选择 Project 后，另行读取单个 `project_path`、defaults-only `project_workspace_context` 和 vault-root `project_knowledge_entrypoints`。四条通道不得互相合并，不递归扫描目录，永不把 `code/`、`worklog/` 或 `.git/` 当知识入口。
5. **构造检索词。** 合并任务文本中的实体与方法名、当前代码中直接相关的 symbols、profile 的 `repo_key` / `aliases` / `domains` / `keywords`，以及已验证 entrypoints 的标题和显式链接。不要用无关仓库内容扩词。
6. **按顺序搜索。** 使用 `rg -l -i`，依次搜索 profile vault entrypoints、`DomainMaps/`、`Topics/`、`Workbench/memory/`、`Papers/`、`Ideas/`、`Experiments/`、profile wrapper context；只有显式选择 Project 时才加入其三条独立 Project channels。默认示例：

   ```bash
   rg -l -i \
     --glob '*.md' \
     --glob '!Projects/**' \
     --glob '!.git/**' \
     --glob '!.website/**' \
     --glob '!.worktrees/**' \
     --glob '!assets/**' \
     --glob '!**/checkpoints/**' \
     --glob '!**/models/**' \
     --glob '!**/datasets/**' \
     --glob '!**/logs/**' \
     --glob '!**/cache/**' \
     --glob '!**/caches/**' \
     --glob '!**/build/**' \
     --glob '!**/builds/**' \
     --glob '!Private/**' \
     --glob '!Meetings/**' \
     --glob '!Workbench/logs/**' \
     '(RECAP|ACP|policy)' \
     DomainMaps/VLA.md DomainMaps Topics Workbench/memory Papers Ideas Experiments Workbench/RepositoryProfiles/pi.md
   ```

   将首项替换为实际 vault entrypoints，将末项替换为 repository profile；wrapper 文件作为 validator 返回的精确文件逐个读取，不把 `Projects/` 加入递归搜索。默认排除 `Projects/**`、`.git/`、`.website/`、`.worktrees/`、`assets/`、checkpoints、models、datasets、logs、caches、builds、`Private/`、`Meetings/` 和 `Workbench/logs/`。仅当任务明确需要历史决策时，才移除 `!Meetings/**` 并加入 `Meetings`；还必须同时移除 `!**/logs/**` 与 `!Workbench/logs/**`，并加入 `Workbench/logs`。
7. **排序候选。** 优先级依次为：profile 或笔记的显式链接；精确 title / arXiv ID / DOI / Zotero citekey；frontmatter alias / tag；正文匹配。先读 5–8 篇最高相关笔记；只沿已有证据支持的 wikilink 跟进一跳，总数最多 12 篇。broken link 要跳过并点名。
8. **保持源码通道边界。** 从当前 repository 开始；只有显式 dependency、当前代码的直接 reference，或用户点名另一 repository 时，才检查另一个代码仓。不得为了补齐背景扫描无关仓库。
9. **综合证据。** 每条结论标为 `代码证据`、`论文笔记`、`历史记录` 或 `Codex 推断`。每个 MindFlow 来源引用绝对文件路径和 heading。矛盾笔记并列展示，不静默裁决。若没有证据，原样说明 `MindFlow 中未找到相关证据`，然后使用现有代码证据继续，或询问下一来源；绝不编造 citation。
10. **按需查询 Zotero。** 只有用户或当前证据需要原文、metadata 或 citekey 时才查询；不执行 library synchronization。
11. **结束时保持只读。** 可给出可选 writeback proposal，但未获得本次明确批准时不修改 MindFlow。

## Guard

- **默认只读。** 只提出可复用知识的写回建议，格式固定为：

  ```text
  目标: <目标笔记或类别>
  内容: <拟沉淀的可复用结论>
  证据: <可核验来源>
  理由: <为何值得沉淀>
  ```

- 用户批准后，先解析 canonical `<resolved vault_root>`，重新读取 `<resolved vault_root>/AGENTS.md`（若存在）、目标路径层级适用的 target-vault instructions、适用 references/templates 和 destination note，再做最小兼容写入。当前 source repository 的 `AGENTS.md` 只约束 source lane，不能替代 target-vault rules。单篇论文结论进入 `Papers/`；跨论文综合进入 `Topics/` 或 `DomainMaps/`；hypothesis 进入 `Ideas/`；实验计划/结果进入 `Experiments/`；工程或研究进展进入 project profile。跨项目可复用 workflow 只有在另一次明确授权后才能进入 `skills/`。
- 写回批准不授权 commit 或 push，也不授权修改批准目标之外的文件。
- 不向 MindFlow 写入 credentials、tokens、private addresses、camera serial numbers、large logs、checkpoints 或未经筛选的 runtime output。
- branch、commit、host、service、checkpoint 和 experiment-state 等易漂移事实必须附带本轮当前验证；旧笔记不能代替 runtime verification。
- stale root、missing entrypoint、broken link 和互相矛盾的笔记都保留为显式失败信息，不通过静默修复、跳转或合并掩盖。

## Verify

- [ ] 触发分类正确；机械任务未启动 MindFlow 检索。
- [ ] profile 选择遵循 canonical root 优先、identity 次之，并在多匹配时停止。
- [ ] 检索根目录、排除项、5–8 篇初读和最多 12 篇一跳边界均已遵守。
- [ ] 每个 MindFlow 引用包含绝对路径与 heading，结论使用四类 evidence labels。
- [ ] 没有证据时使用固定 no-evidence 声明，且没有伪造来源。
- [ ] 未经明确批准没有写回；获批写回仅修改批准目标并保留原有手写内容。
- [ ] validator 的 profile、wrapper、Project channels 保持分离；没有递归扫描 `Projects/` 或 `code/`。
- [ ] 默认 vault 从 canonical skill path 解析；validator 优先使用 vault Python 3.12，并仅在已验证的只读沙箱阻断下使用 3.10+ compatibility fallback。
- [ ] 维护者做运行时行为验证时，读取并执行 [references/smoke-tests.md](references/smoke-tests.md) 的十六案例矩阵。

## Examples

研究任务：“把当前 ACP 实现与相关论文对应起来。”触发本 skill；选择当前仓库 profile，分别报告 `代码证据`、`论文笔记` 与 `Codex 推断`，默认不写文件。

机械任务：“只检查 pyproject.toml 是否有尾随空格。”不触发 MindFlow；仅检查当前源码文件。
