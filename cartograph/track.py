from __future__ import annotations

from datetime import date
from pathlib import Path

from cartograph.config import Config


def close(repo_path: Path, config: Config, period: str | None = None) -> Path:
    """Move all [x] items from current.md into a dated sealed file."""
    if period is None:
        today = date.today()
        year, week, _ = today.isocalendar()
        period = f"{year}-W{week:02d}"

    current_path = repo_path / config.track.dir / config.track.current
    if not current_path.exists():
        raise FileNotFoundError(f"No track file at {current_path}")

    lines = current_path.read_text(encoding="utf-8").splitlines(keepends=True)
    closed = [l for l in lines if _is_closed(l)]
    remaining = [l for l in lines if not _is_closed(l)]

    if not closed:
        raise ValueError("No closed items in current.md")

    sealed_path = current_path.parent / f"{period}.md"
    if sealed_path.exists():
        existing = sealed_path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n") else "\n"
        sealed_path.write_text(existing + separator + "".join(closed), encoding="utf-8")
    else:
        sealed_path.write_text(
            f"# Track — {period}\n\n" + "".join(closed), encoding="utf-8"
        )

    while remaining and remaining[-1].strip() == "":
        remaining.pop()
    current_path.write_text("".join(remaining) + "\n" if remaining else "", encoding="utf-8")

    return sealed_path


def done(repo_path: Path, config: Config, terms: list[str]) -> dict[str, str | None]:
    """Mark open items matching each term as [x]. Returns {term: matched_line | None}."""
    current_path = repo_path / config.track.dir / config.track.current
    if not current_path.exists():
        raise FileNotFoundError(f"No track file at {current_path}")

    lines = current_path.read_text(encoding="utf-8").splitlines(keepends=True)
    results: dict[str, str | None] = {}

    for term in terms:
        needle = term.lower()
        matched = None
        for i, line in enumerate(lines):
            if _is_open(line) and needle in line.lower():
                lines[i] = line.replace("- [ ]", "- [x]", 1).replace("- [  ]", "- [x]", 1)
                matched = lines[i].strip()
                break
        results[term] = matched

    current_path.write_text("".join(lines), encoding="utf-8")
    return results


def _is_open(line: str) -> bool:
    s = line.strip()
    return s.startswith("- [ ]") or s.startswith("- [  ]")


def _is_closed(line: str) -> bool:
    s = line.strip()
    return s.startswith("- [x]") or s.startswith("- [X]")
