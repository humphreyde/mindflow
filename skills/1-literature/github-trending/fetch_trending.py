#!/usr/bin/env python3
"""Fetch GitHub Trending, score repositories, and write deterministic JSON."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VAULT_IMPORT_ROOT = Path(__file__).resolve().parents[3]
if str(VAULT_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(VAULT_IMPORT_ROOT))

from scripts.mindflow_paths import resolve_vault_root  # noqa: E402


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def fetch_html(url: str, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 mindflow-github-trending/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def strip_tags(fragment: str) -> str:
    return html_lib.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_trending(html_text: str, period: str) -> list[dict[str, object]]:
    period_word = {
        "daily": "today",
        "weekly": "this week",
        "monthly": "this month",
    }[period]
    repositories: list[dict[str, object]] = []
    for block in re.split(r'<article class="Box-row">', html_text)[1:]:
        match = re.search(r'<h2[^>]*>\s*<a\b[^>]*\shref="/([^"]+)"', block)
        if not match:
            continue
        full_name = match.group(1).strip().strip("/")
        if full_name.count("/") != 1:
            continue
        owner, name = full_name.split("/", 1)

        description_match = re.search(
            r'<p class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', block, re.S
        )
        language_match = re.search(
            r'itemprop="programmingLanguage">\s*([^<]+?)\s*</span>', block
        )
        totals = re.findall(
            r"Link--muted[^>]*>\s*<svg[\s\S]*?</svg>\s*([\d,]+)", block
        )
        period_match = re.search(
            rf"([\d,]+)\s+stars\s+{re.escape(period_word)}", block
        )

        def to_int(value: str) -> int:
            return int(value.replace(",", "")) if value else 0

        repositories.append(
            {
                "repo": full_name,
                "owner": owner,
                "name": name,
                "url": f"https://github.com/{full_name}",
                "description": (
                    strip_tags(description_match.group(1))
                    if description_match
                    else ""
                ),
                "language": language_match.group(1).strip() if language_match else "",
                "stars_total": to_int(totals[0]) if totals else 0,
                "forks_total": to_int(totals[1]) if len(totals) > 1 else 0,
                "stars_period": to_int(period_match.group(1)) if period_match else 0,
                "period": period,
            }
        )
    return repositories


def load_scoring_config(vault: Path) -> tuple[list[str], list[str], list[str]]:
    config_path = vault / "skills/1-literature/daily-papers/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return tuple(
        [str(item).strip().lower() for item in config.get(key, []) if str(item).strip()]
        for key in ("keywords", "negative_keywords", "domain_boost_keywords")
    )  # type: ignore[return-value]


def keyword_in_text(keyword: str, text: str) -> bool:
    if re.fullmatch(r"[a-z0-9]{2,4}", keyword):
        return re.search(
            rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text
        ) is not None
    return keyword in text


def score_repository(
    repository: dict[str, object],
    keywords: list[str],
    negatives: list[str],
    boosts: list[str],
) -> None:
    text = " ".join(
        str(repository.get(field, ""))
        for field in ("repo", "description", "language")
    ).lower()
    matched = [keyword for keyword in keywords if keyword_in_text(keyword, text)]
    boosted = [keyword for keyword in boosts if keyword_in_text(keyword, text)]
    negative = [keyword for keyword in negatives if keyword_in_text(keyword, text)]
    score = 2 * len(matched) + len(boosted) - 3 * len(negative)
    repository["score"] = score
    repository["matched_keywords"] = sorted(set(matched + boosted))
    repository["relevant"] = bool(matched or boosted) and score >= 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--since", default="weekly", choices=("daily", "weekly", "monthly")
    )
    parser.add_argument("--language", default="")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    vault = resolve_vault_root(Path(__file__))
    url = f"https://github.com/trending?since={args.since}"
    if args.language:
        url += f"&l={args.language}"

    try:
        html_text = fetch_html(url)
    except (HTTPError, URLError, TimeoutError) as exc:
        log(f"GitHub Trending fetch failed: {exc}")
        return 1

    repositories = parse_trending(html_text, args.since)
    if not repositories:
        log("GitHub Trending returned no parseable repositories")
        return 1

    keywords, negatives, boosts = load_scoring_config(vault)
    for repository in repositories:
        score_repository(repository, keywords, negatives, boosts)
    repositories.sort(key=lambda item: int(item["stars_period"]), reverse=True)
    for rank, repository in enumerate(repositories, 1):
        repository["rank"] = rank

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(repositories, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(
        f"Fetched {len(repositories)} repositories; "
        f"{sum(bool(item['relevant']) for item in repositories)} relevant"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
