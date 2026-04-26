from __future__ import annotations

import tomllib
from pathlib import Path

from cartograph.adapters.markdown import (
    build_heading_index,
    build_keyword_index,
    heading_slug,
    jaccard,
    normalize,
)
from cartograph.config import Config
from cartograph.flag import BROKEN_DEP, UNDECLARED, Flag
from cartograph.state import make_flag_id


def run(config: Config) -> list[Flag]:
    manifest_path = config.repo_path / config.docs.manifest
    if not manifest_path.exists():
        return []

    with manifest_path.open("rb") as f:
        raw = tomllib.load(f)
    edges = raw.get("edge", [])

    docs_root = config.repo_path / config.docs.root
    doc_files = list(docs_root.rglob("*.md")) if docs_root.exists() else []

    keyword_index = build_keyword_index(doc_files) if doc_files else {}
    heading_index = build_heading_index(doc_files) if doc_files else {}
    flags: list[Flag] = []

    # BROKEN_DEP: declared edge whose term or heading is absent in target
    for edge in edges:
        from_raw = edge.get("from", "")
        to_raw = edge.get("to", "")
        term = edge.get("term", "")
        heading_text = edge.get("heading", "")

        to_path_str, _, anchor = to_raw.partition("#")
        target = config.repo_path / to_path_str
        if not target.exists():
            flags.append(Flag(
                id=make_flag_id(3, Path(from_raw), term or "missing"),
                channel=3, type=BROKEN_DEP,
                source=from_raw,
                detail=f"target {to_path_str!r} does not exist",
            ))
            continue

        target_str = str(target)
        expected_slug = heading_slug(heading_text) if heading_text else anchor

        if expected_slug:
            slugs = {h.slug for h in heading_index.get(target_str, [])}
            if expected_slug not in slugs:
                flags.append(Flag(
                    id=make_flag_id(3, Path(from_raw), heading_text or anchor),
                    channel=3, type=BROKEN_DEP,
                    source=from_raw,
                    detail=f"heading {expected_slug!r} not found in {to_path_str!r}",
                ))
        elif term:
            if not normalize(term) & keyword_index.get(target_str, set()):
                flags.append(Flag(
                    id=make_flag_id(3, Path(from_raw), term),
                    channel=3, type=BROKEN_DEP,
                    source=from_raw,
                    detail=f"term {term!r} not found in {to_path_str!r}",
                ))

    # UNDECLARED: doc pairs above Jaccard threshold with no declared manifest edge
    declared: set[frozenset[str]] = set()
    for edge in edges:
        f = edge.get("from", "")
        t = edge.get("to", "").split("#")[0]
        if f and t:
            declared.add(frozenset([f, t]))

    threshold = config.reconcile.memory_signal_threshold
    for i, path_a in enumerate(doc_files):
        for path_b in doc_files[i + 1:]:
            rel_a = str(path_a.relative_to(config.repo_path))
            rel_b = str(path_b.relative_to(config.repo_path))
            if frozenset([rel_a, rel_b]) in declared:
                continue
            if jaccard(keyword_index.get(str(path_a), set()), keyword_index.get(str(path_b), set())) >= threshold:
                flags.append(Flag(
                    id=make_flag_id(3, path_a, path_b.stem[:20]),
                    channel=3, type=UNDECLARED,
                    source=rel_a,
                    detail=f"{rel_a!r} and {rel_b!r} share terms — no manifest edge declared",
                ))

    return flags
