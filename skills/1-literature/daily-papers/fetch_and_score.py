#!/usr/bin/env python3
"""
fetch_and_score.py — 抓取 HuggingFace Trending + arXiv 论文，关键词打分，输出 Top N。

零 token 消耗。纯 Python，无外部依赖。

Usage:
    python3 fetch_and_score.py                          # 当天
    python3 fetch_and_score.py --days 3                 # 过去 3 天
    python3 fetch_and_score.py --date 2026-04-07        # 指定日期

Stderr: 进度日志。Stdout: JSON array。
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from typing import NamedTuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

VAULT_PACKAGE_ROOT = Path(__file__).resolve().parents[3]
if str(VAULT_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(VAULT_PACKAGE_ROOT))

from scripts.mindflow_paths import resolve_output, resolve_vault_root

# ── 加载配置 ──────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
VAULT_ROOT = resolve_vault_root(Path(__file__))
DEFAULT_HISTORY_PATH = resolve_output(
    VAULT_ROOT, "Workbench/daily/.history.json"
)

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_CONFIG = load_config()

KEYWORDS = [kw.lower() for kw in _CONFIG["keywords"]]
ARXIV_CATEGORIES = _CONFIG["arxiv_categories"]
MIN_SCORE = _CONFIG["min_score"]
TOP_N = _CONFIG["top_n"]
ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


# ── 打分 ───────────────────────────────────────────────────────────────────

def score_paper(paper: dict) -> int:
    """按 keyword 命中次数打分。标题命中 +3，摘要命中 +1。"""
    title_lower = paper["title"].lower()
    text = (title_lower + " " + paper["abstract"]).lower()
    score = 0
    for kw in KEYWORDS:
        if kw in title_lower:
            score += 3
        elif kw in text:
            score += 1
    return score


# ── 数据抓取 ───────────────────────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 30) -> str:
    try:
        req = Request(url, headers={"User-Agent": "daily-papers-bot/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  [WARN] fetch failed {url}: {e}", file=sys.stderr)
        return ""


def _parse_hf_item(item: dict, source: str) -> tuple[str, dict] | None:
    """解析单个 HF API 条目。返回 (arxiv_id, paper_dict) 或 None。"""
    p = item.get("paper", {})
    arxiv_id = p.get("id", "")
    if not arxiv_id:
        return None

    authors_raw = p.get("authors", [])
    if isinstance(authors_raw, list):
        names = []
        for a in authors_raw:
            if isinstance(a, dict):
                names.append(a.get("name", ""))
            elif isinstance(a, str):
                names.append(a)
        authors = ", ".join(n for n in names if n)
    else:
        authors = str(authors_raw)

    paper = {
        "title": p.get("title", ""),
        "authors": authors,
        "abstract": p.get("summary", ""),
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "date": (p.get("publishedAt") or "")[:10],
        "score": 0,
        "source": source,
        "hf_upvotes": p.get("upvotes", 0),
    }
    paper["score"] = score_paper(paper)
    # upvote scaling: ≥50 → must read (inf), <50 → score × (1 + upvotes/10)
    upvotes = paper.get("hf_upvotes", 0) or 0
    if upvotes >= 50:
        paper["score"] = 9999
    elif upvotes > 0:
        paper["score"] = int(paper["score"] * (1 + upvotes / 10))
    return arxiv_id, paper


def fetch_hf_papers(start_date, end_date) -> list[dict]:
    """抓取 HF Daily（逐天）+ HF Trending（一次，过滤旧论文）。"""
    papers = {}

    # HF Daily：逐天抓取
    d = start_date
    while d <= end_date:
        date_str = d.isoformat()
        endpoint = f"https://huggingface.co/api/daily_papers?date={date_str}&limit=100"
        print(f"  Fetching hf-daily {date_str}...", file=sys.stderr)
        raw = fetch_url(endpoint)
        if raw:
            try:
                items = json.loads(raw)
            except json.JSONDecodeError:
                items = []
            for item in items:
                result = _parse_hf_item(item, "hf-daily")
                if result:
                    aid, paper = result
                    if aid not in papers or paper["score"] > papers[aid]["score"]:
                        papers[aid] = paper
        d += timedelta(days=1)

    # HF Trending：一次抓取，过滤 30 天前的旧论文
    endpoint = "https://huggingface.co/api/daily_papers?sort=trending&limit=50"
    print(f"  Fetching hf-trending...", file=sys.stderr)
    raw = fetch_url(endpoint)
    trending_cutoff = (datetime.now().date() - timedelta(days=30)).isoformat()
    if raw:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
        for item in items:
            result = _parse_hf_item(item, "hf-trending")
            if result:
                aid, paper = result
                if paper["date"] and paper["date"] < trending_cutoff:
                    continue
                if aid not in papers or paper["score"] > papers[aid]["score"]:
                    papers[aid] = paper

    result = list(papers.values())
    print(f"  HF: {len(result)} papers", file=sys.stderr)
    return result


def fetch_arxiv_papers(start_date, end_date, days: int = 1) -> list[dict]:
    max_results = min(400 * days, 3000)
    cats = "+OR+".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=({cats})"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )

    timeout = max(60, 30 * days)
    print(f"  Fetching arXiv (max_results={max_results}, timeout={timeout}s)...", file=sys.stderr)
    xml_text = fetch_url(url, timeout=timeout)
    if not xml_text:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  [WARN] arXiv XML parse error: {e}", file=sys.stderr)
        return []

    papers = []
    filtered_by_date = 0
    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)
        published_el = entry.find("atom:published", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)

        if title_el is None or summary_el is None:
            continue

        title = " ".join(title_el.text.split())
        abstract = " ".join(summary_el.text.split())
        entry_url = id_el.text.strip() if id_el is not None else ""
        date = published_el.text[:10] if published_el is not None else ""
        arxiv_id = entry_url.split("/abs/")[-1] if "/abs/" in entry_url else ""

        # 多天模式按日期过滤（单天模式不过滤，因为 arXiv 日期常有偏差）
        if days > 1 and start_date and end_date and date:
            try:
                pub_date = datetime.strptime(date, "%Y-%m-%d").date()
                if pub_date < start_date or pub_date > end_date:
                    filtered_by_date += 1
                    continue
            except ValueError:
                pass

        author_els = entry.findall("atom:author", ATOM_NS)
        names = []
        for a in author_els:
            name_el = a.find("atom:name", ATOM_NS)
            if name_el is not None and name_el.text:
                names.append(name_el.text.strip())

        paper = {
            "title": title,
            "authors": ", ".join(names),
            "abstract": abstract,
            "url": entry_url,
            "date": date,
            "score": 0,
            "source": "arxiv",
        }
        paper["score"] = score_paper(paper)
        papers.append(paper)

    print(
        f"  arXiv: {len(papers)} papers"
        f" (from {len(papers) + filtered_by_date} parsed, {filtered_by_date} filtered by date)",
        file=sys.stderr,
    )
    return papers


# ── 历史去重 ──────────────────────────────────────────────────────────────

def extract_arxiv_id(url: str) -> str:
    m = re.search(r"(\d{4}\.\d{4,5})", url)
    return m.group(1) if m else ""


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> list[dict]:
    """加载历史推荐记录。格式: [{"id": "2504.12345", "date": "2026-04-08"}, ...]"""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_history(papers: list[dict], target_date, path: Path = DEFAULT_HISTORY_PATH) -> None:
    """追加本次推荐的论文到历史，保留最近 30 天。"""
    history = load_history(path)
    existing_ids = {h["id"] for h in history}

    for p in papers:
        aid = extract_arxiv_id(p["url"])
        if aid and aid not in existing_ids:
            history.append({"id": aid, "date": str(target_date), "title": p.get("title", "")})
            existing_ids.add(aid)

    # 清理 30 天前的记录
    cutoff = str((datetime.now().date() - timedelta(days=30)))
    history = [h for h in history if h.get("date", "") >= cutoff]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  History updated: {len(history)} entries → {path}", file=sys.stderr)



# ── 合并去重 ──────────────────────────────────────────────────────────────

def merge_and_rank(
    hf_papers: list[dict],
    arxiv_papers: list[dict],
    target_date,
    days: int = 1,
    top_n: int = TOP_N,
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> list[dict]:
    is_weekend = target_date.weekday() >= 5

    # 按 arXiv ID 合并，保留高分
    by_id: dict[str, dict] = {}
    for p in hf_papers + arxiv_papers:
        aid = extract_arxiv_id(p["url"])
        if not aid:
            continue
        if aid not in by_id or p["score"] > by_id[aid]["score"]:
            by_id[aid] = p

    print(f"  Merged: {len(by_id)} unique papers", file=sys.stderr)

    # 多天模式：跳过历史去重（用户明确要看多天内容）
    if days > 1:
        print(f"  Multi-day mode (days={days}): skipping history dedup", file=sys.stderr)
        candidates = [p for p in by_id.values() if p["score"] >= MIN_SCORE]
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[:top_n]
        print(f"  Final: {len(top)} papers (top_n={top_n})", file=sys.stderr)
        return top

    # 单天模式：历史去重
    history = load_history(history_path)
    history_ids: dict[str, str] = {}  # id → earliest date
    for h in history:
        hid, hdate = h.get("id", ""), h.get("date", "")
        if hid and hdate:
            if hid not in history_ids or hdate < history_ids[hid]:
                history_ids[hid] = hdate

    # 跨天去重
    deduped: dict[str, dict] = {}
    removed = 0
    for aid, p in by_id.items():
        if aid in history_ids:
            # 周末：允许高 upvote 的 trending 论文重新推荐
            if is_weekend and p.get("source") == "hf-trending" and (p.get("hf_upvotes") or 0) >= 5:
                p["is_re_recommend"] = True
                p["last_recommend_date"] = history_ids[aid]
                deduped[aid] = p
            else:
                removed += 1
        else:
            deduped[aid] = p

    print(f"  After history dedup: {len(deduped)} (removed {removed})", file=sys.stderr)

    # 过滤 + 排序
    candidates = [p for p in deduped.values() if p["score"] >= MIN_SCORE]
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top = candidates[:top_n]
    print(f"  Final: {len(top)} papers", file=sys.stderr)
    return top


# ── 离线编排契约 ───────────────────────────────────────────────────────────

class FixturePipelineResult(NamedTuple):
    fetched: int
    read: int
    skipped: int


RATING_LABELS = {
    3: ("🔥", "Foundation"),
    2: ("👀", "Frontier"),
    1: ("💤", "Peripheral"),
}


def _exclusive_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise FileExistsError(f"pipeline artifact already exists: {path}") from exc


def _render_fixture_daily(payload: dict, target_date) -> str:
    digests = payload["digests"]
    skipped = payload["skipped"]
    lines = [
        "---",
        f"date: {target_date.isoformat()}",
        "tags: [daily-papers]",
        "---",
        "",
        "# 🔪 今日总结",
        "",
        f"离线契约样例：抓取 {len(payload['candidates'])} 篇，精读 {len(digests)} 篇。",
        "",
        "## 评分表",
        "",
        "| Rating | 论文 |",
        "|---|---|",
    ]
    for rating in (3, 2, 1):
        emoji, label = RATING_LABELS[rating]
        entries = [
            f"[[#{item['short_title']}]]（{item['reason']}）"
            for item in digests
            if item["rating"] == rating
        ]
        lines.append(
            f"| {emoji} `{rating} - {label}` | "
            + ("；".join(entries) if entries else "—")
            + " |"
        )
    lines.extend(["", "## 论文点评", ""])
    for item in digests:
        lines.extend(
            [
                f"### {item['short_title']}",
                f"- **Title**: {next(candidate['title'] for candidate in payload['candidates'] if candidate['url'] == item['candidate_url'])}",
                f"- **📒 论文笔记**: [[{Path(item['filename']).stem}]]",
                f"- **锐评**: {item['commentary']}",
                f"- **Rating**: `{item['rating']}`，{item['reason']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 已跳过论文",
            "",
            "| 论文 | 跳过原因 |",
            "|---|---|",
            *[f"| {item['title']} | {item['reason']} |" for item in skipped],
            "",
        ]
    )
    return "\n".join(lines)


def _render_fixture_log(payload: dict, target_date) -> str:
    digests = payload["digests"]
    skipped = payload["skipped"]
    lines = [f"# {target_date.isoformat()}", ""]
    for item in digests:
        lines.extend(
            [
                "### [00:00] paper-digest",
                f"- **input**: {item['candidate_url']}",
                f"- **output**: [[Papers/{Path(item['filename']).stem}]]",
                "- **observation**: offline fixture digest",
                "",
            ]
        )
    counts = {rating: sum(item["rating"] == rating for item in digests) for rating in (3, 2, 1)}
    lines.extend(
        [
            "### [00:00] daily-papers",
            "- **input**: offline fixture",
            f"- **output**: [[Workbench/daily/{target_date.isoformat()}]]",
            (
                f"- **observation**: 抓取 {len(payload['candidates'])} 篇，精读 {len(digests)} 篇"
                f"（rating 3: {counts[3]} / 2: {counts[2]} / 1: {counts[1]}），"
                f"跳过 {len(skipped)} 篇"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_fixture_pipeline(vault: Path, fixture: Path) -> FixturePipelineResult:
    """Exercise the six-artifact orchestration contract without network or LLMs."""
    root = resolve_vault_root(vault)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    candidates = payload.get("candidates")
    digests = payload.get("digests")
    skipped = payload.get("skipped")
    if not all(isinstance(value, list) for value in (candidates, digests, skipped)):
        raise ValueError("fixture requires candidates, digests, and skipped arrays")
    if len(candidates) != len(digests) + len(skipped):
        raise ValueError("fixture accounting requires fetched = read + skipped")
    candidate_urls = {item["url"] for item in candidates}
    accounted_urls = {item["candidate_url"] for item in digests + skipped}
    if candidate_urls != accounted_urls:
        raise ValueError("fixture decisions must account for each candidate exactly once")

    target_date = datetime.strptime(payload["date"], "%Y-%m-%d").date()
    candidates_path = resolve_output(root, "Workbench/daily/.candidates.json")
    _exclusive_write(
        candidates_path,
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
    )
    history_path = resolve_output(root, "Workbench/daily/.history.json")
    save_history(candidates, target_date, history_path)

    for digest in digests:
        filename = Path(digest["filename"])
        if filename.name != digest["filename"] or filename.suffix != ".md":
            raise ValueError(f"invalid fixture paper filename: {digest['filename']}")
        _exclusive_write(
            resolve_output(root, f"Papers/{digest['filename']}"), digest["paper_note"]
        )

    _exclusive_write(
        resolve_output(root, f"Workbench/daily/{target_date.isoformat()}.md"),
        _render_fixture_daily(payload, target_date),
    )
    _exclusive_write(
        resolve_output(root, f"Workbench/logs/{target_date.isoformat()}.md"),
        _render_fixture_log(payload, target_date),
    )
    return FixturePipelineResult(len(candidates), len(digests), len(skipped))


# ── 主入口 ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch and score daily papers")
    parser.add_argument("--date", help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to fetch")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--vault", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    vault = resolve_vault_root(args.vault or Path(__file__))
    if args.vault is not None and vault != args.vault.resolve():
        raise ValueError(f"vault override is not a MindFlow root: {args.vault}")
    output_path = resolve_output(vault, args.output) if args.output else None

    target_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date
        else datetime.now().date()
    )
    days = max(1, args.days)
    start_date = target_date - timedelta(days=days - 1)
    top_n = min(TOP_N * days, 100)

    is_weekend = target_date.weekday() >= 5
    print(
        f"[fetch_and_score] {target_date} ({'weekend' if is_weekend else 'weekday'})"
        + (f", days={days} [{start_date} ~ {target_date}], top_n={top_n}" if days > 1 else ""),
        file=sys.stderr,
    )

    # history 路径：与 output 同目录，或默认位置
    if output_path:
        history_path = output_path.parent / ".history.json"
    else:
        history_path = DEFAULT_HISTORY_PATH

    hf_papers = fetch_hf_papers(start_date, target_date)
    arxiv_papers = fetch_arxiv_papers(start_date, target_date, days)
    top = merge_and_rank(hf_papers, arxiv_papers, target_date, days=days, top_n=top_n, history_path=history_path)

    # 更新历史
    save_history(top, target_date, history_path)

    output = json.dumps(top, ensure_ascii=False, indent=2) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"  Output written to {output_path}", file=sys.stderr)
    else:
        sys.stdout.write(output)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
