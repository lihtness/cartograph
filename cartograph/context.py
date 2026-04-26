from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from cartograph.adapters.markdown import parse_roadmap
from cartograph.config import Config
from cartograph import state as state_mod

_ITEM_PREFIX = re.compile(r"^[-*•]\s*\[[ xX]\]\s*|^[-*•]\s*", re.IGNORECASE)


def generate(config: Config) -> str:
    today = date.today().isoformat()
    parts = [
        f"# Project Context — {today}",
        "",
        *_current_work(config),
        "",
        *_reconcile_status(config),
        "",
        *_orientation(config),
    ]
    return "\n".join(parts)


def _current_work(config: Config) -> list[str]:
    current_path = config.repo_path / config.track.dir / config.track.current
    lines = ["## Current work", ""]
    if not current_path.exists():
        lines.append(
            f"No track file. Create {config.track.dir}/{config.track.current} "
            "to track work items."
        )
        return lines
    items = parse_roadmap(current_path)
    open_items = [i for i in items if i.status == "open"]
    closed_count = sum(1 for i in items if i.status == "closed")
    if open_items:
        for item in open_items:
            lines.append(f"- [ ] {_strip_prefix(item.text)}")
    else:
        lines.append("No open items.")
    if closed_count:
        lines.append(f"\n_{closed_count} closed item(s) pending seal — "
                     "`cartograph track close`_")
    return lines


def _reconcile_status(config: Config) -> list[str]:
    state = state_mod.load(config.repo_path)
    lines = ["## Reconcile", ""]
    if state.last_run:
        resolved = len(state.resolved_ids)
        lines.append(
            f"Last run: {state.last_run.strftime('%Y-%m-%d')}  ·  "
            f"{resolved} resolved flag(s)"
        )
    else:
        lines.append("Never run.")
    lines.append("Run `cartograph reconcile` for full drift report.")
    return lines


def _orientation(config: Config) -> list[str]:
    from cartograph.scaffold import _load_sections
    sections = _load_sections(config.repo_path)
    lines = ["## Orientation", ""]
    if not sections:
        lines.append("No scaffold. Run `cartograph init` to scaffold this project.")
        return lines
    width = max(len(s.name) for s in sections)
    for s in sections:
        lines.append(f"{s.name:<{width}}  {s.lifecycle:<8}  — {s.primary_question}")
    return lines


def _strip_prefix(text: str) -> str:
    return _ITEM_PREFIX.sub("", text).strip()
