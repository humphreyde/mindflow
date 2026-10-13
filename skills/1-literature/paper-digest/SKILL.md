---
name: paper-digest
description: Use when user asks to "read paper", "analyze paper", "summarize paper", "读论文", "分析文献", "帮我看一下这篇paper", "论文笔记", or provides a PDF file that appears to be an academic paper.
---

## Purpose

给定论文或技术 blog 的 URL、本地 PDF、标题或关键词，使用可用的发现能力和现有确定性提取脚本获取来源，生成一份有出处、保留媒体、符合 Obsidian 规范的结构化笔记。

支持 `paper`（学术论文）和 `blog`（技术或产品文章）。

## Runtime capabilities

- Node.js 18+：运行 `scripts/defuddle_parse.mjs` 提取 HTML。
- Python 3.12+ 与仓库 `uv` 环境：运行 `scripts/pdf_to_md.py`。
- `curl`：下载 PDF、HTML、README 和调用公开 API。
- `gh` 可选：已登录时提高 GitHub API 配额；不可用或未登录时降级为匿名 `curl`。
- 网页搜索/浏览能力可选：用于发现官方源和 Semantic Scholar 失败后的 Scholar 查询；不可用时使用输入 URL、官方 API 和直接站点 URL，不得假装已经搜索。

先确认依赖。不要在未经授权时安装软件。Node 提取失败时，论文优先降级到 PDF 路线；网页源无法可靠提取时保留 URL 与失败原因，不以搜索摘要代替正文。

## Steps

### 1. 去重预检

在 `Papers/` 中按 arXiv ID、DOI、规范化标题和文件名查找已有笔记。命中后立即停止写入，向用户返回 `[[已有笔记]]` 并询问取消或显式更新。只有用户明确授权更新时，才先完整读取现有笔记并做最小合并；不得覆盖手写段落、frontmatter 字段或已有 assets。

### 2. 获取来源

#### 2.1 发现官方源

对三类来源分别尝试发现并验证所有权：

- **paper**：arXiv、出版社或作者提供的 PDF/HTML。
- **website**：project page 或官方 blog。
- **github**：官方代码仓库及 README。

优先使用输入中的明确 URL、arXiv ID、DOI 和官方页面关系；再使用运行时可用的网页发现能力兜底。没有网页发现能力或某类源不存在时，在 issues 中写明，不得使用未验证的镜像、聚合转载或二手摘要冒充官方源。

#### 2.2 提取到任务临时目录

将 `ShortTitle` 规范化为不含路径分隔符的短名，使用本次任务专属的 `/tmp/{ShortTitle}/` 目录并记录绝对路径。若该目录已存在且归属不明，换用带唯一后缀的目录，不覆盖旧内容。

| 源 | 确定性提取方式 | 降级 |
|---|---|---|
| arXiv HTML | `node {skill_dir}/scripts/defuddle_parse.mjs "https://arxiv.org/html/{arxiv_id}" -o /tmp/{ShortTitle}/paper.json`，同时生成 `paper.md` | arXiv HTML 失败后可使用经批准且可追溯的 ar5iv fallback：`https://ar5iv.labs.arxiv.org/html/{arxiv_id}`；同时记录原始 arXiv ID/URL、ar5iv URL 和访问日期。仍失败则走 PDF |
| PDF | `curl -sL "<url>" -o /tmp/{ShortTitle}/paper.pdf && uv run {skill_dir}/scripts/pdf_to_md.py /tmp/{ShortTitle}/paper.pdf` | 下载或解析失败则记录原因，保留其他可用源 |
| website | `node {skill_dir}/scripts/defuddle_parse.mjs "<url>" -o /tmp/{ShortTitle}/website.json`，同时生成 `website.md` | 提取失败则用 `curl` 保存 raw HTML 供校验；不能可靠提取正文时标为不可得 |
| github | `curl -sL "https://raw.githubusercontent.com/<org>/<repo>/main/README.md" -o /tmp/{ShortTitle}/github.md` | `main` 不存在时试 `master` |

记录每类网络来源的原始 URL、访问日期和 `local_path`。用户提供的本地 PDF 记录原始绝对路径和 SHA-256，再复制或读取到任务临时目录；该“原始路径 + SHA-256 + 提取文件位置”是充分 provenance，不需要额外网络来源才能继续。

#### 2.3 校验提取文件

逐个解析生成文件，确认非空、正文完整、标题与目标一致，并检查：

- website 的 figure/video URL 是否完整；缺失时从 `curl` 保存的 raw HTML 恢复绝对 URL。
- arXiv HTML 的 multi-panel figure：逐个 `<figure class="ltx_figure">` 检查 `ltx_flex_figure` 中所有 `<img>` 是否齐全；缺失时从 raw HTML 补全。嵌入时遵循 `references/obsidian-syntax.md` §2.3 的 flex 写法。

失败只重试对应来源和既定 fallback，不无限循环；仍失败则记录 issues，继续使用其他已验证来源。

#### 2.4 影响力指标

输出 `/tmp/{ShortTitle}/metrics.json`。字段始终存在；没有来源或 API 失败的块为 `null`。

Citation 优先调用 Semantic Scholar batch API：

```bash
curl -sX POST 'https://api.semanticscholar.org/graph/v1/paper/batch?fields=citationCount,influentialCitationCount,publicationDate' \
  -H 'Content-Type: application/json' -d '{"ids":["arXiv:<arxiv_id>"]}'
```

匿名配额出现 429 时只重试一次并等待 30 秒；仍失败且运行时能获取网页时，查询 `https://scholar.google.com/scholar?q=arxiv+<arxiv_id>` 的 top hit “Cited by N”，单次间隔至少 30 秒，写 `citation_source="scholar"`、`influential_citations=null`。两路失败时 `paper=null`，不阻塞 digest。批量复核（≥10 篇）优先串行、每篇至少间隔 3 秒，并接受降级为 Scholar 或 `null`。

其他指标：

- HF：`curl -s "https://huggingface.co/api/papers/<arxiv_id>"`，取 `.upvotes`；404 → `null`。
- GitHub：优先 `gh api "repos/<owner>/<repo>"` 和 `gh api "repos/<owner>/<repo>/commits?since=<90d-ago-ISO>&per_page=100"`；否则用 `curl https://api.github.com/...`。记录 stars、forks、open issues、pushed time 和 90 天 commits；长度 100 标为 `"100+"`。`is_stale = pushed_days_ago > 180 AND commits_last_90d == 0`。

Schema：

```json
{
  "measured_at": "YYYY-MM-DD",
  "paper":  {"citation_count": 0, "influential_citations": 0, "citation_velocity_per_month": 0.0, "months_since_publish": 0, "citation_source": "s2"},
  "hf":     {"upvotes": 0},
  "github": {"stars": 0, "forks": 0, "open_issues": 0, "pushed_days_ago": 0, "commits_last_90d": "0", "is_stale": false}
}
```

`citation_velocity_per_month = citationCount / max(months_since_publish, 1)`。单个 API 失败只把对应块置 `null`，并记录具体 endpoint、状态和原因。

### 3. 生成并保存笔记

完整读取所有成功提取的来源，以及：

- `{skill_dir}/references/paper-note-template.md`
- vault 根目录 `references/obsidian-syntax.md`
- vault 根目录 `references/tags.md`

笔记顺序固定为 Frontmatter → `## Summary` → Body → `## 关联工作` → `## 论文点评`。撰写顺序使用 Body → 关联工作 → 论文点评 → Summary → Frontmatter，使判断建立在已读证据之上。

- Body 保留论文核心结构、方法、实验、ablation、failure case 和 caveat，不机械翻译或过度压缩。
- 每个事实、数值、公式、表格和媒体都记录到具体来源文件与原文 section/figure/table；有疑问写 `> ❓ ...`。
- 只嵌入有解释价值的 figure/equation/table/video，并紧邻相关讨论；overview/concept/motivation teaser 可放在 `## Summary`。
- 不嵌入 OG image、social card、banner、favicon。删除模板中的所有 `%% ... %%` 提示。
- PDF 图片从任务临时目录复制到 `Papers/assets/{ShortTitle}/`，命名为 `fig{N}-{FigureTitle}.{ext}`，使用 `![](Papers/assets/{ShortTitle}/fig{N}-{FigureTitle}.{ext})`。

文件名为 `YYMM-ShortTitle.md`：`YYMM` 来自 `date_publish`，`ShortTitle` 是 2-4 个关键词的 CamelCase 缩写。保存到 `Papers/{文件名}.md`。

### 4. 注入 Wikilink

只处理正文，跳过 frontmatter、代码块、现有 wikilink 和路径字符串。候选包括具体论文、方法、数据集和模型；排除宽泛类别词及论文自己的新术语。

#### 文件名匹配协议

把 term 折叠为 CamelCase/常用 ASCII（去空格和连字符，例如 `Flow Matching` → `FlowMatching`、`GEN-1` → `GEN1`、`π0.5` → `Pi05`），再在存在的目录中搜索：

```text
Papers/*<TermCamelCase>*.md
Concepts/*<TermCamelCase>*.md
DomainMaps/*<TermCamelCase>*.md
```

可用 `rg --files Papers Concepts DomainMaps` 配合文件名过滤。命中后读取候选 frontmatter 的 `title:` 确认相关性，避免子串 false positive。只有目标文件确实存在时才替换为 `[[文件名|term]]`；未命中的 term 汇总进 dead-link inventory。

完成后逐个检查所有 `[[...]]`，修复嵌套、路径污染、短 term 破坏长 alias，以及表格内未转义的 `\|`。

### 5. 追加日志

串行追加到 `Workbench/logs/YYYY-MM-DD.md`；不存在时先写 `# YYYY-MM-DD`：

```markdown
### [HH:MM] paper-digest
- **input**: <原始输入>
- **output**: [[Papers/{笔记文件名}]]
- **observation**: <一句话核心贡献>
- **sources**: <source type, official URL；或 user-supplied local path + SHA-256；以及 extracted local_path>
- **extracted**: figures=<N>, tables=<N>, equations=<N>, videos=<N>
- **embedded**: figures=<N>, tables=<N>, equations=<N>, videos=<N>, wikilinks=<N>
- **dead_links**: term1, term2, ...
- **issues**: <依赖、网络、解析、API 或来源缺失；无则 none>
```

## Guard

- 默认不改已有论文笔记或 assets；只有用户明确授权更新时才最小合并，并保留 frontmatter、手写内容和已有链接。
- 每个 claim、URL、数字、公式、表格和媒体必须追溯到具体来源位置。网络来源记录官方 URL 与本地提取文件位置；用户提供的本地文件以原始绝对路径、SHA-256 和提取文件位置作为充分 provenance。搜索摘要和二手转载不能替代原文。
- 网络、API 或单类来源失败时按既定 fallback 有限重试，随后把对应来源/指标标为 unavailable 或 `null`；不得编造缺失信息，也不得让非关键指标阻塞正文 digest。
- 临时目录必须专属于本次任务，不覆盖同名旧目录；只清理已确认由本次创建的精确路径，绝不对 `/tmp` 或宽泛路径做递归删除。
- 只创建或更新本次目标论文的 note、assets 和一条日志；不批量修改其他 paper notes、helper scripts、DomainMaps 或索引。
- ar5iv 是 arXiv HTML 失败时唯一预先批准的非官方镜像 fallback，必须保留原始 arXiv ID/URL 和实际 ar5iv URL 以便追溯。其他非官方镜像只有在用户明确授权且来源身份可验证时才可使用；不得安装缺失依赖或绕过访问控制。

## Verify

### Fetch

- [ ] 已对 paper/website/github 三类官方源分别尝试发现；没有网页发现能力或来源不存在时已如实记录。
- [ ] 每个网络源都有官方 URL、访问日期和唯一 `local_path`；ar5iv fallback 同时记录原始 arXiv ID/URL 与实际镜像 URL。用户提供的本地文件有原始绝对路径、SHA-256 和提取文件位置。生成文件非空且标题匹配目标。
- [ ] HTML/PDF/README 使用现有 Node/Python/curl 管线；依赖缺失和 fallback 路径已记录，没有修改 helper scripts。
- [ ] website URL 和 multi-panel figure 完整性已检查；未恢复项已进入 issues。
- [ ] `metrics.json` 可解析、含 `measured_at` 和三个固定块；可用来源有值，缺失/失败来源为 `null`，计算字段可复算。

### Compose and save

- [ ] `Papers/{文件名}.md` 已创建；若原笔记存在，只有在显式授权下做最小更新且用户内容仍在。
- [ ] frontmatter、Summary、Body、关联工作、论文点评符合模板；无 `%%...%%` 或占位符。
- [ ] 所有 URL、数字、公式、表格、方法 claim 可在记录的本地来源文件中搜索到，并已标明来源位置；没有凭记忆补写。
- [ ] 媒体与说明紧邻且语境一致；teaser 位置正确；无装饰图；PDF assets 命名和路径符合约定。
- [ ] Summary、frontmatter `rating` 和 `### Rating` 分数一致；Rating 首行的 Metrics 日期和数值来自 `metrics.json`，缺失字段写 `N/A（原因）`。

### Wikilink and log

- [ ] 最终笔记中每个 wikilink 成对、无嵌套、目标存在；alias 只有一个分隔符，表格 cell 中已转义；没有污染路径或更长术语。
- [ ] dead-link inventory 与未命中候选一致，没有为消除 dead link 创建范围外笔记。
- [ ] 日志只追加一次；sources、extracted、embedded、dead_links、issues 与最终 artifacts 一致。
