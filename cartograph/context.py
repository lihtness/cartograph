from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from cartograph.adapters.markdown import parse_roadmap
from cartograph.config import Config
from cartograph import state as state_mod

_ITEM_PREFIX = re.compile(r"^[-*•]\s*\[[ xX]\]\s*|^[-*•]\s*", re.IGNORECASE)


def generate(config: Config, query: str | None = None) -> str:
    today = date.today().isoformat()
    parts = [
        f"# Project Context — {today}",
        "",
        *_current_work(config),
        "",
        *_reconcile_status(config),
        "",
        *_orientation(config, query=query),
    ]
    affected = _recently_affected(config)
    if affected:
        parts += ["", *affected]
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
    if open_items:
        for item in open_items:
            lines.append(f"- [ ] {_strip_prefix(item.text)}")
    else:
        lines.append("No open items.")
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


def _orientation(config: Config, query: str | None = None) -> list[str]:
    from cartograph.scaffold import _load_sections
    sections = _load_sections(config.repo_path)
    lines = ["## Orientation", ""]
    if not sections:
        lines.append("No scaffold. Run `cartograph init` to scaffold this project.")
        return lines
    if query:
        ranked, ok = _rank_sections(sections, query)
        if ok:
            lines.append(f'_Top sections for: "{query}"_')
            lines.append("")
            sections = ranked
        else:
            lines.append("_Query ranking unavailable — `pip install cartograph[embeddings]`_")
            lines.append("")
    width = max(len(s.name) for s in sections)
    for s in sections:
        lines.append(f"{s.name:<{width}}  {s.lifecycle:<8}  — {s.primary_question}")
    return lines


def _rank_sections(sections: list, query: str) -> tuple[list, bool]:
    try:
        from cartograph.adapters.embeddings import available, embed, cosine_sim
    except ImportError:
        return sections, False
    if not available():
        return sections, False
    texts = [f"{s.primary_question} {s.intent}".strip() for s in sections]
    vecs = embed([query] + texts)
    q_vec = vecs[0]
    scored = sorted(
        zip(vecs[1:], sections),
        key=lambda pair: cosine_sim(pair[0], q_vec),
        reverse=True,
    )
    top = min(3, len(sections))
    return [s for _, s in scored[:top]], True


def _recently_affected(config: Config) -> list[str]:
    try:
        from cartograph import observations as obs_mod
        recent = obs_mod.query_recent(config, n=10)
    except Exception:
        return []
    if not recent:
        return []
    lines = ["## Recently affected docs", ""]
    for md_file, section, count in recent[:6]:
        lines.append(f"  {md_file}#{section}  ({count}×)")
    return lines


def _strip_prefix(text: str) -> str:
    return _ITEM_PREFIX.sub("", text).strip()
