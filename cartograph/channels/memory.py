from __future__ import annotations

from pathlib import Path

from cartograph.adapters.claude import parse_memory_file
from cartograph.adapters.markdown import jaccard, normalize, parse_roadmap
from cartograph.config import Config
from cartograph.flag import ALREADY_DONE, GAP, STALE_REF, Flag
from cartograph.state import make_flag_id


def run(config: Config) -> list[Flag]:
    memory_files = _find_memory_files(config)
    if not memory_files:
        return []

    roadmap_path = config.repo_path / config.track.dir / config.track.current
    if not roadmap_path.exists():
        return []

    roadmap_items = parse_roadmap(roadmap_path)
    open_items = [i for i in roadmap_items if i.status == "open"]
    closed_items = [i for i in roadmap_items if i.status == "closed"]
    roadmap_text = roadmap_path.read_text(encoding="utf-8", errors="replace")
    threshold = config.reconcile.memory_signal_threshold
    flags: list[Flag] = []

    for memory_file in memory_files:
        try:
            sig = parse_memory_file(memory_file)
        except Exception:
            continue

        # STALE_REF: roadmap references this file by stem but it is superseded/dropped
        if (sig.is_superseded or sig.is_dropped) and memory_file.stem in roadmap_text:
            status = "SUPERSEDED" if sig.is_superseded else "DROPPED"
            flags.append(Flag(
                id=make_flag_id(2, memory_file, "stale ref"),
                channel=2, type=STALE_REF,
                source=str(memory_file),
                detail=f"roadmap references {memory_file.stem!r} but it is marked {status}",
            ))

        for signal_text in sig.signals:
            signal_terms = normalize(signal_text)
            if not signal_terms:
                continue

            open_hit = any(
                jaccard(signal_terms, i.terms) >= threshold for i in open_items
            )
            closed_hits = [
                (i, jaccard(signal_terms, i.terms))
                for i in closed_items
                if jaccard(signal_terms, i.terms) >= threshold
            ]

            if not open_hit and not closed_hits:
                flags.append(Flag(
                    id=make_flag_id(2, memory_file, signal_text[:40]),
                    channel=2, type=GAP,
                    source=str(memory_file),
                    detail=f"signal {signal_text[:60]!r} — no matching roadmap item",
                ))
            elif not open_hit and closed_hits:
                best = max(closed_hits, key=lambda x: x[1])
                flags.append(Flag(
                    id=make_flag_id(2, memory_file, signal_text[:40]),
                    channel=2, type=ALREADY_DONE,
                    source=str(memory_file),
                    detail=f"signal matches only closed item: {best[0].text[:60]!r}",
                ))

    return flags


def _find_memory_files(config: Config) -> list[Path]:
    root = config.repo_path / config.memory.root
    if root.is_dir():
        return list(root.rglob("*.md"))
    # Auto-discover under .claude/projects/*/memory/
    found: list[Path] = []
    projects_dir = config.repo_path / ".claude" / "projects"
    if projects_dir.is_dir():
        for mem_dir in projects_dir.glob("*/memory"):
            if mem_dir.is_dir():
                found.extend(mem_dir.glob("*.md"))
    return found
