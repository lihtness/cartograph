from pathlib import Path

from cartograph.channels.manifest import run
from cartograph.config import load
from cartograph.flag import BROKEN_DEP, UNDECLARED


def _write_manifest(tmp_path, content):
    p = tmp_path / ".cartograph" / "manifest.toml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _write_doc(tmp_path, rel_path, content):
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_broken_dep_missing_term(tmp_path):
    _write_doc(tmp_path, "docs/arch.md", "# Architecture\n\nSome unrelated content.\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md"
type = "depends_on"
term = "embedding adapter"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 1
    assert "embedding adapter" in broken[0].detail


def test_no_broken_dep_when_term_present(tmp_path):
    _write_doc(tmp_path, "docs/arch.md", "# Architecture\n\nEmbedding adapter design.\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md"
type = "depends_on"
term = "embedding adapter"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 0


def test_broken_dep_missing_heading(tmp_path):
    _write_doc(tmp_path, "docs/arch.md", "# Architecture\n\n## Overview\n\nContent.\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md#embedding-adapter-design"
type = "depends_on"
term = "embedding adapter"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 1
    assert "embedding-adapter-design" in broken[0].detail


def test_no_broken_dep_heading_present(tmp_path):
    _write_doc(tmp_path, "docs/arch.md", "# Architecture\n\n## Embedding Adapter Design\n\nContent.\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md#embedding-adapter-design"
type = "depends_on"
term = "embedding adapter"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 0


def test_broken_dep_target_missing(tmp_path):
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/nonexistent.md"
type = "depends_on"
term = "something"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 1
    assert "does not exist" in broken[0].detail


def test_undeclared_high_overlap(tmp_path):
    shared = "embedding adapter reconciler channel memory roadmap drift detection"
    _write_doc(tmp_path, "docs/concept.md", f"# Concept\n\n{shared}\n")
    _write_doc(tmp_path, "docs/build_plan.md", f"# Build Plan\n\n{shared}\n")
    _write_manifest(tmp_path, "")

    undeclared = [f for f in run(load(tmp_path)) if f.type == UNDECLARED]
    assert len(undeclared) == 1


def test_no_undeclared_when_edge_declared(tmp_path):
    shared = "embedding adapter reconciler channel memory roadmap drift detection"
    _write_doc(tmp_path, "docs/concept.md", f"# Concept\n\n{shared}\n")
    _write_doc(tmp_path, "docs/build_plan.md", f"# Build Plan\n\n{shared}\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/concept.md"
to = "docs/build_plan.md"
type = "depends_on"
term = "embedding adapter"
""")
    undeclared = [f for f in run(load(tmp_path)) if f.type == UNDECLARED]
    assert len(undeclared) == 0


def test_no_manifest_returns_empty(tmp_path):
    _write_doc(tmp_path, "docs/concept.md", "# Concept\n")
    assert run(load(tmp_path)) == []


def test_empty_docs_returns_empty(tmp_path):
    _write_manifest(tmp_path, "")
    assert run(load(tmp_path)) == []


def test_multiple_edges_one_broken(tmp_path):
    _write_doc(tmp_path, "docs/arch.md", "# Architecture\n\nEmbedding adapter design.\n")
    _write_manifest(tmp_path, """\
[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md"
type = "depends_on"
term = "embedding adapter"

[[edge]]
from = "docs/roadmap.md"
to = "docs/arch.md"
type = "depends_on"
term = "pricing tiers"
""")
    broken = [f for f in run(load(tmp_path)) if f.type == BROKEN_DEP]
    assert len(broken) == 1
    assert "pricing tiers" in broken[0].detail
