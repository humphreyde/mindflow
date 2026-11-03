#!/usr/bin/env python3
"""Render GitHub Trending JSON into a collision-safe MindFlow note."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path


VAULT_IMPORT_ROOT = Path(__file__).resolve().parents[3]
if str(VAULT_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(VAULT_IMPORT_ROOT))

from scripts.mindflow_paths import resolve_output, resolve_vault_root  # noqa: E402


PERIOD_LABEL = {"daily": "日榜", "weekly": "周榜", "monthly": "月榜"}
PERIOD_UNIT = {"daily": "今日", "weekly": "本周", "monthly": "本月"}


def note_filename(period: str, today: date) -> str:
    label = PERIOD_LABEL.get(period, "榜单")
    if period == "weekly":
        iso_year, iso_week, _ = today.isocalendar()
        return f"{iso_year}-W{iso_week:02d} GitHub{label}.md"
    return f"{today.isoformat()} GitHub{label}.md"


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown(
    repositories: list[dict[str, object]], period: str, today: date
) -> str:
    unit = PERIOD_UNIT.get(period, "")
    label = PERIOD_LABEL.get(period, "榜单")
    relevant = [item for item in repositories if item.get("relevant")]
    lines = [
        "---",
        f"date: {today.isoformat()}",
        "type: github-trending",
        f"period: {period}",
        "tags: [github, trending]",
        "---",
        "",
        f"# GitHub {label} · {today.isoformat()}",
        "",
        (
            f"> {unit} star 涨得最快的 {len(repositories)} 个项目，其中 "
            f"**{len(relevant)}** 个与你的研究方向相关。"
        ),
        "",
    ]

    if relevant:
        lines.extend(["## 🎯 与研究方向相关", ""])
        for item in relevant:
            keywords = "、".join(str(value) for value in item.get("matched_keywords", []))
            language = f" · `{item['language']}`" if item.get("language") else ""
            lines.append(
                f"- **[{item['repo']}]({item['url']})** — ⭐ "
                f"+{int(item['stars_period']):,} {unit}"
                f"（累计 {int(item['stars_total']):,}）{language}"
            )
            if item.get("description"):
                lines.append(f"  - {item['description']}")
            if keywords:
                lines.append(f"  - 命中关键词: {keywords}")
        lines.append("")

    lines.extend(
        [
            f"## 📊 完整{label}",
            "",
            f"| # | 项目 | {unit}新增⭐ | 累计⭐ | 语言 | 相关 | 简介 |",
            "| --- | --- | ---: | ---: | --- | :---: | --- |",
        ]
    )
    for item in repositories:
        description = markdown_escape(str(item.get("description", "")))
        if len(description) > 80:
            description = description[:79] + "…"
        flag = "✅" if item.get("relevant") else ""
        lines.append(
            f"| {item['rank']} | [{markdown_escape(str(item['repo']))}]({item['url']}) "
            f"| +{int(item['stars_period']):,} | {int(item['stars_total']):,} "
            f"| {item.get('language', '')} | {flag} | {description} |"
        )
    lines.extend(
        [
            "",
            (
                f"*生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                f"数据源 github.com/trending?since={period}*"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_note(
    vault: Path, today: date, repositories: list[dict[str, object]]
) -> Path:
    if not repositories:
        raise ValueError("repository list is empty")
    root = resolve_vault_root(vault)
    period = str(repositories[0].get("period", "weekly"))
    output = resolve_output(
        root, f"Workbench/trending/{note_filename(period, today)}"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(build_markdown(repositories, period, today))
    except FileExistsError as exc:
        raise FileExistsError(f"trending note already exists: {output}") from exc
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    repositories = json.loads(args.input.read_text(encoding="utf-8"))
    vault = args.vault if args.vault is not None else resolve_vault_root(Path(__file__))
    output = write_note(vault, args.date, repositories)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
