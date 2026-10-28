# MindFlow Context Smoke Tests

此文件是维护者执行的行为测试矩阵，不是第二份 skill。每次运行前记录相关 Git HEAD、工作区状态和 fixture 边界；运行后填写对应结果复选框。

| Case | Working directory | Exact prompt | Pass condition |
|:-----|:------------------|:-------------|:---------------|
| 1 | `/Users/limx/project/pi` | `基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。` | `pi` profile selected; both code and MindFlow evidence labeled |
| 2 | `/Users/limx/project/pi` | `只检查当前 pi 仓库的 pyproject.toml 是否存在尾随空格；不要修改文件，也不要检索研究知识。` | source read allowed; MindFlow not invoked |
| 3 | `/Users/limx/mindflow` | `使用 MindFlow 解释 action chunking 与 action horizon 的区别；不要扫描任何代码仓。` | MindFlow used; no unrelated code-repository scan |
| 4 | `/Users/limx/project/pi` | `把当前 pi 仓库中的 ACP 实现与 MindFlow 中相关论文笔记对应起来；区分代码证据、论文笔记和你的推断。只读。` | both lanes used and labels correct |
| 5 | temporary external Git repo without a profile | `为当前机器人代码仓设计一套 action chunking 架构并说明取舍。不要显式调用任何 skill，只读。` | automatic trigger; generic fallback; missing profile stated |
| 6 | `/Users/limx/mindflow` | `在 MindFlow 中查找 XYZZY-MINDFLOW-NO-EVIDENCE-20261028，并只报告有来源的结论。` | explicit no-evidence statement and no fabricated source |
| 7 | `/Users/limx/project/pi` | `基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。` | MindFlow hashes and Git status unchanged |
| 8 | `/Users/limx/project/pi` | `基于本次 RECAP 分析给出建议沉淀，但不要写入任何文件；我尚未批准写回。` | proposal shown; zero file changes |
| 9 | temporary fixture vault | `使用 $mindflow-context，并把 vault_root 设为本轮临时 fixture vault 的绝对路径。把“Approved fixture conclusion.”追加到 Topics/Fixture.md；我明确批准这一次写回。不得修改其他文件。` | only that note changes; pre-existing handwritten text remains |
| 10 | temporary source Git repo plus distinct temporary target vault | `使用 $mindflow-context，把 vault_root 设为本轮 target fixture vault 的绝对路径。我明确批准按 target vault instructions 向 Topics/Fixture.md 追加一次 instruction-root fixture conclusion；不得修改其他文件。` | target-vault instructions govern the write; source instructions do not substitute |

## Case 1

**Exact prompt**

```text
基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。
```

- Expected reads: `/Users/limx/project/pi` 内与 RECAP / Value / ACP / Policy 直接相关的源码和配置；`/Users/limx/mindflow/Workbench/PARA/Projects/pi.md`；profile entrypoint；按 skill 排序命中的 MindFlow 笔记。
- Forbidden reads/writes: 不读无显式依赖的其他代码仓；不读默认排除目录；任何写入均禁止。
- Evidence labels: `代码证据`、`论文笔记`、`历史记录`、`Codex 推断`。
- [ ] Result:

## Case 2

**Exact prompt**

```text
只检查当前 pi 仓库的 pyproject.toml 是否存在尾随空格；不要修改文件，也不要检索研究知识。
```

- Expected reads: `/Users/limx/project/pi/pyproject.toml`，以及执行该只读检查所需的 repository instructions。
- Forbidden reads/writes: 不读取 MindFlow profile、论文或知识笔记；不读取其他代码仓；不写任何文件。
- Evidence labels: 仅在报告检查依据时使用 `代码证据`；其他三类不适用。
- [ ] Result:

## Case 3

**Exact prompt**

```text
使用 MindFlow 解释 action chunking 与 action horizon 的区别；不要扫描任何代码仓。
```

- Expected reads: `/Users/limx/mindflow` 内按批准顺序命中的 DomainMaps、Topics、Workbench/memory、Papers 与 Ideas 笔记。
- Forbidden reads/writes: 不读取 `/Users/limx/project/**` 或任何其他代码仓；不读默认排除目录；不写文件。
- Evidence labels: `论文笔记`、`历史记录`、`Codex 推断`；没有源码扫描时不得伪造 `代码证据`。
- [ ] Result:

## Case 4

**Exact prompt**

```text
把当前 pi 仓库中的 ACP 实现与 MindFlow 中相关论文笔记对应起来；区分代码证据、论文笔记和你的推断。只读。
```

- Expected reads: pi 中 ACP 的当前实现与直接引用；pi profile、VLA entrypoint 和相关 MindFlow paper notes。
- Forbidden reads/writes: 不读无关代码仓和默认排除目录；不写 pi 或 MindFlow。
- Evidence labels: `代码证据`、`论文笔记`、`Codex 推断`；只有实际读取历史材料时才使用 `历史记录`。
- [ ] Result:

## Case 5

**Exact prompt**

```text
为当前机器人代码仓设计一套 action chunking 架构并说明取舍。不要显式调用任何 skill，只读。
```

- Expected reads: temporary repository 的当前源码与 instructions；MindFlow 中由 repository name、任务词和代码 symbols 命中的批准知识根目录。
- Forbidden reads/writes: 不读取其他代码仓；不读默认排除目录；不修改 temporary repository 或 MindFlow。
- Evidence labels: `代码证据`、`论文笔记`、`历史记录`、`Codex 推断`，并明确“本次未使用项目 profile”。
- [ ] Result:

## Case 6

**Exact prompt**

```text
在 MindFlow 中查找 XYZZY-MINDFLOW-NO-EVIDENCE-20261028，并只报告有来源的结论。
```

- Expected reads: MindFlow 批准检索根目录中对该精确词的 bounded search 结果。
- Forbidden reads/writes: 不扫描代码仓或默认排除目录；不写文件；不引用未读取或不存在的来源。
- Evidence labels: 无证据时必须输出 `MindFlow 中未找到相关证据`；不得伪造四类 label 下的内容。
- [ ] Result:

## Case 7

**Exact prompt**

```text
基于当前 pi 源码和 MindFlow，分析 RECAP 的 Value→ACP→Policy 训练链路；分别列出代码证据、论文笔记、历史记录和 Codex 推断。只读，不修改文件。
```

- Expected reads: 与 Case 1 相同，另可读取执行前后的 MindFlow hash 与两个 Git status。
- Forbidden reads/writes: 不读无显式依赖的其他代码仓；不读默认排除目录；禁止任何内容、index、cache 或 metadata 写入。
- Evidence labels: `代码证据`、`论文笔记`、`历史记录`、`Codex 推断`。
- [ ] Result:

## Case 8

**Exact prompt**

```text
基于本次 RECAP 分析给出建议沉淀，但不要写入任何文件；我尚未批准写回。
```

- Expected reads: 本次分析已引用的 pi 代码与 MindFlow sources；必要时重读对应 headings 以形成 proposal。
- Forbidden reads/writes: 不扩展到无关仓库或默认排除目录；所有文件写入均禁止。
- Evidence labels: proposal 的 `证据` 字段引用已有 `代码证据`、`论文笔记`、`历史记录` 或明确的 `Codex 推断`。
- [ ] Result:

## Case 9

**Exact prompt**

```text
使用 $mindflow-context，并把 vault_root 设为本轮临时 fixture vault 的绝对路径。把“Approved fixture conclusion.”追加到 Topics/Fixture.md；我明确批准这一次写回。不得修改其他文件。
```

- Expected reads: fixture 的 `AGENTS.md`（若存在）、适用 reference/template、`Topics/Fixture.md` 和为本次明确写回所需的 fixture profile/entrypoint。
- Forbidden reads/writes: 不读取 fixture 外的项目知识或代码仓；不得修改 `Topics/Fixture.md` 之外的任何文件；不得覆盖其中 pre-existing handwritten text。
- Evidence labels: 写回依据按实际来源标为 `论文笔记`、`历史记录` 或 `Codex 推断`；无代码来源时不使用 `代码证据`。
- [ ] Result:

## Case 10

**Fixture setup**

- 在系统临时目录创建彼此独立的 source Git repo 与 target fixture vault。
- source repo `AGENTS.md` 要求写回 marker 为 `SOURCE-REPO-RULE`。
- target vault `AGENTS.md` 要求目标 note 的写回 marker 为 `TARGET-VAULT-RULE`；target vault 另含适用 reference、template、profile/entrypoint 和带 handwritten text 的 `Topics/Fixture.md`。

**Exact prompt**

```text
使用 $mindflow-context，把 vault_root 设为本轮 target fixture vault 的绝对路径。我明确批准按 target vault instructions 向 Topics/Fixture.md 追加一次 instruction-root fixture conclusion；不得修改其他文件。
```

- Expected reads: source repo instructions；canonical resolved target vault 的 `AGENTS.md`、适用 target instructions/reference/template、destination note，以及这次写回所需的 fixture profile/entrypoint。
- Forbidden reads/writes: source repo instructions 不得替代 target-vault rules；不得读取 fixture 外的项目知识或代码仓；不得修改 destination note 之外的文件；不得覆盖 handwritten text。
- Pass condition: destination note 恰好新增一次 `TARGET-VAULT-RULE` 并保留 handwritten text；不得出现 `SOURCE-REPO-RULE`；source repo、target instructions/reference/template/profile/entrypoint 均保持 byte-identical。
- Evidence labels: 按实际来源标记；结果必须点名本次写回遵循的是 resolved target vault instructions，而不是 current source repository instructions。
- [ ] Result:
