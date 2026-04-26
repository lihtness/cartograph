from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from cartograph.adapters.markdown import parse_frontmatter


_SIGNAL_RE = re.compile(
    r"Next\s*:|Build order\s*:|NOT YET BUILT|Track\s+\d+\.\d+|\bTODO\b|\bdeferred\b|not yet implemented",
    re.IGNORECASE,
)

_STATUS_RE = re.compile(
    r"\*\*(SUPERSEDED|DROPPED|CRITICAL PIVOT|REFRAME)\*\*",
    re.IGNORECASE,
)

_WINDOW = 60


@dataclass
class MemorySignal:
    path: Path
    description: str
    type: str               # user | feedback | project | reference
    signals: list[str]      # forward-looking signal strings for roadmap matching
    is_superseded: bool
    is_dropped: bool


def parse_memory_file(path: Path) -> MemorySignal:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(path)
    description = fm.get("description", "")
    mem_type = fm.get("type", "")

    markers = [m.upper() for m in _STATUS_RE.findall(text)]
    is_superseded = "SUPERSEDED" in markers
    is_dropped = "DROPPED" in markers

    signals: list[str] = []
    if description:
        signals.append(description)

    # Only project-type files carry forward-looking content worth reconciling
    if mem_type == "project":
        for m in _SIGNAL_RE.finditer(text):
            start = max(0, m.start() - _WINDOW)
            end = min(len(text), m.end() + _WINDOW)
            signals.append(text[start:end].strip())

    return MemorySignal(
        path=path,
        description=description,
        type=mem_type,
        signals=signals,
        is_superseded=is_superseded,
        is_dropped=is_dropped,
    )
