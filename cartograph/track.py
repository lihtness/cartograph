from __future__ import annotations

from pathlib import Path

from cartograph.config import Config


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
