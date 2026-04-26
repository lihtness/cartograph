from __future__ import annotations

from pathlib import Path


def init(repo_path: Path, template: str | None = None) -> None:
    raise NotImplementedError


def add_section(repo_path: Path, name: str, question: str = "", lifecycle: str = "Stable") -> None:
    raise NotImplementedError
