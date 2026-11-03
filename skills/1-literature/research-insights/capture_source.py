#!/usr/bin/env python3
"""Create collision-safe research source and optional insight notes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


VAULT_IMPORT_ROOT = Path(__file__).resolve().parents[3]
if str(VAULT_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(VAULT_IMPORT_ROOT))

from scripts.mindflow_paths import resolve_output, resolve_vault_root  # noqa: E402


ASSETS = Path(__file__).resolve().parent / "assets"


def yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def validate_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"source URL must be http or https: {value}")
    return value


def safe_title(value: str) -> str:
    title = re.sub(r"[\\/:\x00]", "-", value).strip().rstrip(".")
    title = re.sub(r"\s+", " ", title)
    if not title or title in {".", ".."}:
        raise ValueError("title does not produce a safe filename")
    return title


def render_template(path: Path, values: Mapping[str, str]) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text.rstrip() + "\n"


def build_source_note(record: Mapping[str, str]) -> str:
    title = str(record.get("title", "")).strip()
    source_url = validate_url(str(record.get("source_url", "")).strip())
    accessed = str(record.get("accessed", "")).strip()
    content = str(record.get("content", "")).strip()
    if not title or not accessed or not content:
        raise ValueError("source note requires title, accessed date, and content")
    date.fromisoformat(accessed)
    return render_template(
        ASSETS / "source-note-template.md",
        {
            "title": title,
            "title_yaml": yaml_string(title),
            "source_url": source_url,
            "source_url_yaml": yaml_string(source_url),
            "accessed": accessed,
            "content": content,
        },
    )


def build_insight_note(
    *, title: str, source_url: str, accessed: str, content: str
) -> str:
    title = title.strip()
    source_url = validate_url(source_url.strip())
    content = content.strip()
    if not title or not content:
        raise ValueError("insight note requires title and content")
    date.fromisoformat(accessed)
    return render_template(
        ASSETS / "insight-note-template.md",
        {
            "title": title,
            "title_yaml": yaml_string(title),
            "source_url": source_url,
            "source_url_yaml": yaml_string(source_url),
            "accessed": accessed,
            "content": content,
        },
    )


def save_note(vault: Path, relative_directory: str, title: str, note: str) -> Path:
    root = resolve_vault_root(vault)
    output = resolve_output(root, f"{relative_directory}/{safe_title(title)}.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            handle.write(note)
    except FileExistsError as exc:
        raise FileExistsError(f"research note already exists: {output}") from exc
    return output


def save_source(vault: Path, title: str, note: str) -> Path:
    return save_note(vault, "ResearchSources/Sources", title, note)


def save_insight(vault: Path, title: str, note: str) -> Path:
    return save_note(vault, "ResearchSources/Insights", title, note)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--vault", type=Path)
    result.add_argument("--url", required=True)
    result.add_argument("--title", required=True)
    result.add_argument("--content", required=True, type=Path)
    result.add_argument("--accessed", type=date.fromisoformat, default=date.today())
    result.add_argument("--insight-title")
    result.add_argument("--insight-content", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    if bool(args.insight_title) != bool(args.insight_content):
        parser().error("--insight-title and --insight-content must be used together")

    vault = args.vault if args.vault is not None else resolve_vault_root(Path(__file__))
    accessed = args.accessed.isoformat()
    content = args.content.read_text(encoding="utf-8")
    source_note = build_source_note(
        {
            "title": args.title,
            "source_url": args.url,
            "accessed": accessed,
            "content": content,
        }
    )
    outputs = [save_source(vault, args.title, source_note)]

    if args.insight_title and args.insight_content:
        insight_note = build_insight_note(
            title=args.insight_title,
            source_url=args.url,
            accessed=accessed,
            content=args.insight_content.read_text(encoding="utf-8"),
        )
        outputs.append(save_insight(vault, args.insight_title, insight_note))

    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
