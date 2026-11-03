---
name: github-trending
description: Use when the user asks for GitHub Trending, GitHub 周榜、日榜、月榜、star 增长榜，或近期热门开源项目，并希望结果写入 MindFlow。
---

## Purpose

抓取 GitHub Trending，按 MindFlow 研究关键词标注相关性，并把完整榜单写入 resolved canonical vault 的 `Workbench/trending/`。

## Workflow

1. 从用户请求选择 `daily`、`weekly` 或 `monthly`，默认 `weekly`；可选 GitHub language slug。
2. 创建本次任务专属的临时 JSON 路径，运行：

   ```bash
   uv run --project {vault_root} python -B {skill_dir}/fetch_trending.py --since weekly --output /tmp/<unique>-github-trending.json
   ```

3. 确认 JSON 是非空数组，报告网络或解析失败，不把失败解释为“没有热门项目”。
4. 写入笔记：

   ```bash
   uv run --project {vault_root} python -B {skill_dir}/write_trending_note.py --input /tmp/<unique>-github-trending.json
   ```

   正常运行不传 `--vault`；该参数只用于隔离测试。脚本从自身 resolved canonical path 定位 MindFlow。
5. 报告抓取总数、相关项目数和生成路径。

## Output contract

- 周榜：`Workbench/trending/YYYY-Www GitHub周榜.md`
- 日榜/月榜：`Workbench/trending/YYYY-MM-DD GitHub日榜.md` 或 `GitHub月榜.md`
- 笔记包含 provenance frontmatter、相关项目列表和完整榜单。

## Guard

- 使用系统证书验证；TLS、HTTP 或页面解析失败时停止并保留诊断，不绕过证书验证。
- 已存在的目标笔记视为用户内容：停止并报告，绝不覆盖。
- 不安装依赖，不调用模型 API，不执行 Git commit/push，也不修改论文、日报或历史状态。
- 只清理本次创建且路径已确认的临时 JSON。

## Verify

- [ ] 输入 JSON 非空、可解析，条目有 repo、URL、周期 star 和 rank。
- [ ] 输出位于 resolved MindFlow 的 `Workbench/trending/`。
- [ ] 表格中的 pipe 已转义，统计与 JSON 一致。
- [ ] 没有覆盖既有文件，也没有 Git 副作用。
