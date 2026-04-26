import subprocess
from pathlib import Path

import pytest

from cartograph.adapters.markdown import (
    Heading,
    build_heading_index,
    build_keyword_index,
    extract_headings,
    extract_links,
    heading_slug,
    normalize,
    parse_frontmatter,
)
from cartograph.adapters.claude import parse_memory_file
from cartograph.adapters.git import GitEvent, git_log_since, path_to_terms


# ---------------------------------------------------------------------------
# markdown adapter
# ---------------------------------------------------------------------------

_SAMPLE_MD = """\
---
name: concept doc
description: the core concept
type: project
---

# Main Title

Body text with a [link](docs/something.md) and [another](https://example.com).

## Section One

Content here.

### Subsection A

Deep content.
"""


def test_parse_frontmatter_basic(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(_SAMPLE_MD)
    fm = parse_frontmatter(f)
    assert fm["name"] == "concept doc"
    assert fm["description"] == "the core concept"
    assert fm["type"] == "project"


def test_parse_frontmatter_missing(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# No frontmatter here\n")
    assert parse_frontmatter(f) == {}


def test_parse_frontmatter_unclosed(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("---\nname: foo\n")
    assert parse_frontmatter(f) == {}


def test_extract_links(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(_SAMPLE_MD)
    links = extract_links(f)
    assert "docs/something.md" in links
    assert "https://example.com" in links


def test_extract_links_none(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("No links here.\n")
    assert extract_links(f) == []


def test_extract_headings(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(_SAMPLE_MD)
    headings = extract_headings(f)
    assert len(headings) == 3
    assert headings[0].level == 1
    assert headings[0].text == "Main Title"
    assert headings[1].level == 2
    assert headings[1].text == "Section One"
    assert headings[2].level == 3
    assert headings[2].text == "Subsection A"


def test_extract_headings_only_h1_to_h3(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# H1\n## H2\n### H3\n#### H4 ignored\n")
    headings = extract_headings(f)
    assert len(headings) == 3
    assert all(h.level <= 3 for h in headings)


def test_extract_headings_line_numbers(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# First\n\nsome text\n\n## Second\n")
    headings = extract_headings(f)
    assert headings[0].line == 1
    assert headings[1].line == 5


def test_heading_slug_basic():
    assert heading_slug("Main Title") == "main-title"


def test_heading_slug_special_chars():
    assert heading_slug("Channel 1 — Git") == "channel-1-git"


def test_heading_slug_underscores_kept():
    assert heading_slug("my_module setup") == "my_module-setup"


def test_heading_slug_collapses_hyphens():
    assert heading_slug("A  B") == "a-b"


def test_build_keyword_index(tmp_path):
    (tmp_path / "a.md").write_text("# Embedding Adapter\nfastembed integration\n")
    (tmp_path / "b.md").write_text("# Roadmap\nembedding adapter next step\n")
    index = build_keyword_index([tmp_path / "a.md", tmp_path / "b.md"])
    assert "embedding" in index[str(tmp_path / "a.md")]
    assert "embedding" in index[str(tmp_path / "b.md")]


def test_build_heading_index(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Concept\n## Design\n")
    idx = build_heading_index([f])
    headings = idx[str(f)]
    assert len(headings) == 2
    assert headings[0].slug == "concept"
    assert headings[1].slug == "design"


def test_normalize_strips_stop_words():
    terms = normalize("the embedding adapter is not yet built")
    assert "embedding" in terms
    assert "adapter" in terms
    assert "the" not in terms
    assert "is" not in terms


def test_normalize_basic_stemming():
    terms = normalize("channels adapters reconcilers")
    assert "channel" in terms
    assert "adapter" in terms
    assert "reconciler" in terms


# ---------------------------------------------------------------------------
# claude adapter
# ---------------------------------------------------------------------------

_MEMORY_PROJECT = """\
---
name: embedding strategy
description: embedding adapter not yet built
type: project
---

## Status

NOT YET BUILT — deferred to phase 2.

Next: implement the fastembed wrapper.
"""

_MEMORY_FEEDBACK = """\
---
name: test style
description: use real fixtures not mocks
type: feedback
---

## Rule

TODO: update all tests to use real git repos.
"""

_MEMORY_SUPERSEDED = """\
---
name: old design
description: original embedding design
type: project
---

**SUPERSEDED** by new architecture.
"""

_MEMORY_DROPPED = """\
---
name: web ui
description: web UI concept
type: project
---

**DROPPED** — out of scope for v1.
"""


def test_parse_memory_project_signals(tmp_path):
    f = tmp_path / "embedding_strategy.md"
    f.write_text(_MEMORY_PROJECT)
    sig = parse_memory_file(f)
    assert sig.type == "project"
    assert sig.description == "embedding adapter not yet built"
    assert not sig.is_superseded
    assert not sig.is_dropped
    # description + body signal patterns
    assert len(sig.signals) >= 2
    assert any("NOT YET BUILT" in s or "fastembed" in s for s in sig.signals)


def test_parse_memory_feedback_no_body_scan(tmp_path):
    f = tmp_path / "test_style.md"
    f.write_text(_MEMORY_FEEDBACK)
    sig = parse_memory_file(f)
    assert sig.type == "feedback"
    # description is included, but body TODO should not be scanned for feedback type
    assert sig.signals == ["use real fixtures not mocks"]


def test_parse_memory_superseded(tmp_path):
    f = tmp_path / "old_design.md"
    f.write_text(_MEMORY_SUPERSEDED)
    sig = parse_memory_file(f)
    assert sig.is_superseded
    assert not sig.is_dropped


def test_parse_memory_dropped(tmp_path):
    f = tmp_path / "web_ui.md"
    f.write_text(_MEMORY_DROPPED)
    sig = parse_memory_file(f)
    assert sig.is_dropped
    assert not sig.is_superseded


def test_parse_memory_no_frontmatter(tmp_path):
    f = tmp_path / "bare.md"
    f.write_text("Some text with TODO: do something.\n")
    sig = parse_memory_file(f)
    assert sig.description == ""
    assert sig.type == ""
    assert sig.signals == []


# ---------------------------------------------------------------------------
# git adapter
# ---------------------------------------------------------------------------

def test_git_log_since(repo):
    (repo / "docs").mkdir()
    (repo / "docs" / "concept.md").write_text("# Concept\n")
    subprocess.run(["git", "add", "docs/concept.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add concept doc"], cwd=repo, check=True, capture_output=True)

    events = git_log_since(repo, "1970-01-01T00:00:00+00:00")
    file_events = [e for e in events if e.files]
    assert len(file_events) == 1
    assert file_events[0].message == "add concept doc"
    assert "docs/concept.md" in file_events[0].files


def test_git_log_since_multiple_commits(repo):
    for name in ["a.md", "b.md"]:
        (repo / name).write_text(f"# {name}\n")
        subprocess.run(["git", "add", name], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"add {name}"], cwd=repo, check=True, capture_output=True)

    events = git_log_since(repo, "1970-01-01T00:00:00+00:00")
    messages = [e.message for e in events]
    assert "add a.md" in messages
    assert "add b.md" in messages


def test_git_log_since_respects_cutoff(repo):
    (repo / "old.md").write_text("old\n")
    subprocess.run(["git", "add", "old.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "old commit"], cwd=repo, check=True, capture_output=True)

    # Use a future cutoff — should return nothing
    events = git_log_since(repo, "2099-01-01T00:00:00+00:00")
    assert events == []


def test_path_to_terms_directory_and_stem():
    terms = path_to_terms("cartograph/adapters/markdown.py")
    assert "cartograph" in terms
    assert "adapter" in terms
    assert "markdown" in terms


def test_path_to_terms_hyphenated():
    terms = path_to_terms("src/my-module.py")
    assert "my" in terms
    assert "module" in terms


def test_path_to_terms_stop_words_removed():
    terms = path_to_terms("docs/the-concept.md")
    assert "the" not in terms
    assert "concept" in terms
