from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_STOP = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "this", "that", "these", "those", "it", "its", "we", "our",
    "not", "no", "and", "or", "but", "if", "as", "so",
})


@dataclass
class Heading:
    path: Path
    level: int      # 1 = H1, 2 = H2, 3 = H3
    text: str
    slug: str
    line: int


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    result = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def extract_links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"\[(?:[^\]]*)\]\(([^)]+)\)", text)


def extract_headings(path: Path) -> list[Heading]:
    headings = []
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            text = m.group(2).strip()
            headings.append(Heading(
                path=path,
                level=len(m.group(1)),
                text=text,
                slug=heading_slug(text),
                line=lineno,
            ))
    return headings


def build_keyword_index(paths: list[Path]) -> dict[str, set[str]]:
    index = {}
    for path in paths:
        terms = normalize(path.read_text(encoding="utf-8", errors="replace"))
        for h in extract_headings(path):
            terms |= normalize(h.text)  # headings included twice — higher signal
        index[str(path)] = terms
    return index


def build_heading_index(paths: list[Path]) -> dict[str, list[Heading]]:
    return {str(p): extract_headings(p) for p in paths}


def normalize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    return {t.rstrip("s") for t in tokens} - _STOP


def heading_slug(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9_\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")
