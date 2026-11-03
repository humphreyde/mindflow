#!/usr/bin/env python3
"""Resolve canonical MindFlow vault and contained output paths."""

from __future__ import annotations

from pathlib import Path


SENTINELS = ("AGENTS.md", "skills", "Papers", "Workbench")


def resolve_vault_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if all((candidate / name).exists() for name in SENTINELS):
            return candidate
    raise ValueError(f"cannot resolve MindFlow vault root from {start}")


def resolve_output(vault: Path, relative: str) -> Path:
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise ValueError(f"output path must be vault-relative: {relative}")
    root = vault.resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"output escapes MindFlow vault: {relative}") from exc
    return candidate
