from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cartograph.adapters.markdown import normalize


@dataclass
class GitEvent:
    hash: str
    date: datetime
    message: str
    files: list[str] = field(default_factory=list)


def git_log_since(repo_path: Path, since_iso: str) -> list[GitEvent]:
    result = subprocess.run(
        ["git", "log", f"--since={since_iso}", "--name-only", "--format=\x1e%H\t%aI\t%s"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return _parse_log(result.stdout)


def path_to_terms(path: str) -> set[str]:
    """Extract normalized keyword terms from a file path for Channel 1 matching."""
    p = Path(path)
    parts = list(p.parts[:-1]) + [p.stem]
    return normalize(" ".join(parts).replace("-", " ").replace("_", " "))


def _parse_log(output: str) -> list[GitEvent]:
    events: list[GitEvent] = []
    for block in output.split("\x1e"):
        block = block.strip()
        if not block:
            continue
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        parts = lines[0].split("\t")
        if len(parts) < 3:
            continue
        try:
            date = datetime.fromisoformat(parts[1].strip())
        except ValueError:
            continue
        events.append(GitEvent(
            hash=parts[0].strip(),
            date=date,
            message=parts[2].strip(),
            files=[l.strip() for l in lines[1:]],
        ))
    return events
