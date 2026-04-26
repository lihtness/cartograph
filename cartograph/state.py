from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "this", "that", "these", "those", "it", "its", "we", "our",
    "not", "no", "and", "or", "but", "if", "as", "so",
})

_STATE_PATH = ".cartograph/state.toml"


@dataclass
class State:
    last_run: datetime | None = None
    resolved_ids: set[str] = field(default_factory=set)


def load(repo_path: Path) -> State:
    path = repo_path / _STATE_PATH
    if not path.exists():
        return State()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    last_run = None
    if raw.get("last_run"):
        last_run = datetime.fromisoformat(raw["last_run"])
    resolved_ids = set(raw.get("resolved", {}).get("ids", []))
    return State(last_run=last_run, resolved_ids=resolved_ids)


def save(state: State, repo_path: Path) -> None:
    path = repo_path / _STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_serialise(state))


def mark_resolved(state: State, flag_id: str) -> None:
    state.resolved_ids.add(flag_id)


def is_resolved(state: State, flag_id: str) -> bool:
    return flag_id in state.resolved_ids


def make_flag_id(channel: int, source: Path, term: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "_", source.stem.lower()).strip("_")
    return f"C{channel}:{stem}:{_slugify(term)}"


def _slugify(text: str, max_tokens: int = 3) -> str:
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    filtered = [t for t in tokens if t not in _STOP][:max_tokens]
    return "_".join(filtered) or "unknown"


def _serialise(state: State) -> str:
    ts = state.last_run.isoformat() if state.last_run else ""
    lines = [f'last_run = "{ts}"', "", "[resolved]"]
    if state.resolved_ids:
        inner = "\n".join(f'  "{fid}",' for fid in sorted(state.resolved_ids))
        lines.append(f"ids = [\n{inner}\n]")
    else:
        lines.append("ids = []")
    return "\n".join(lines) + "\n"
