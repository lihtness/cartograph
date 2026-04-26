from pathlib import Path

from cartograph.channels.memory import run
from cartograph.config import load
from cartograph.flag import ALREADY_DONE, GAP, STALE_REF


def _write_roadmap(tmp_path, content):
    p = tmp_path / "docs" / "track" / "current.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _write_memory(tmp_path, filename, content):
    p = tmp_path / ".claude" / "projects" / "test" / "memory" / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_gap_when_no_roadmap_match(tmp_path):
    _write_roadmap(tmp_path, "- [ ] authentication system\n")
    _write_memory(tmp_path, "embedding_strategy.md", """\
---
name: embedding strategy
description: embedding adapter not yet built
type: project
---
""")
    gap = [f for f in run(load(tmp_path)) if f.type == GAP]
    assert len(gap) >= 1


def test_no_gap_when_roadmap_matches(tmp_path):
    _write_roadmap(tmp_path, "- [ ] embedding adapter integration\n")
    _write_memory(tmp_path, "embedding_strategy.md", """\
---
name: embedding strategy
description: embedding adapter integration
type: project
---
""")
    gap = [f for f in run(load(tmp_path)) if f.type == GAP]
    assert len(gap) == 0


def test_already_done_when_only_closed_match(tmp_path):
    _write_roadmap(tmp_path, "- [x] embedding adapter\n")
    _write_memory(tmp_path, "embedding_strategy.md", """\
---
name: embedding strategy
description: embedding adapter not yet built
type: project
---
""")
    done = [f for f in run(load(tmp_path)) if f.type == ALREADY_DONE]
    assert len(done) >= 1


def test_stale_ref_superseded_file_in_roadmap(tmp_path):
    _write_roadmap(tmp_path, "- [ ] see embedding_strategy for details\n")
    _write_memory(tmp_path, "embedding_strategy.md", """\
---
name: embedding strategy
description: original design
type: project
---

**SUPERSEDED** by new architecture.
""")
    stale = [f for f in run(load(tmp_path)) if f.type == STALE_REF]
    assert len(stale) == 1


def test_stale_ref_dropped_file_in_roadmap(tmp_path):
    _write_roadmap(tmp_path, "- [ ] see web_ui plan\n")
    _write_memory(tmp_path, "web_ui.md", """\
---
name: web ui
description: web ui concept
type: project
---

**DROPPED** — out of scope for v1.
""")
    stale = [f for f in run(load(tmp_path)) if f.type == STALE_REF]
    assert len(stale) == 1


def test_feedback_type_only_description_signal(tmp_path):
    _write_roadmap(tmp_path, "- [ ] write better tests\n")
    _write_memory(tmp_path, "test_style.md", """\
---
name: test style
description: unrelated feedback about code style
type: feedback
---

TODO: update all tests to use real repos.
""")
    flags = [f for f in run(load(tmp_path)) if "test_style" in f.source]
    # Feedback type: only description contributes a signal, not the body TODO
    assert len(flags) <= 1


def test_no_memory_files_returns_empty(tmp_path):
    _write_roadmap(tmp_path, "- [ ] embedding integration\n")
    assert run(load(tmp_path)) == []


def test_missing_roadmap_returns_empty(tmp_path):
    _write_memory(tmp_path, "foo.md", """\
---
name: foo
description: some forward-looking signal
type: project
---
""")
    assert run(load(tmp_path)) == []


def test_superseded_not_in_roadmap_no_stale_ref(tmp_path):
    _write_roadmap(tmp_path, "- [ ] auth system\n")
    _write_memory(tmp_path, "old_design.md", """\
---
name: old design
description: old design
type: project
---

**SUPERSEDED** by new approach.
""")
    stale = [f for f in run(load(tmp_path)) if f.type == STALE_REF]
    assert len(stale) == 0  # stem "old_design" not mentioned in roadmap
