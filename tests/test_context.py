import pytest
import subprocess
from datetime import datetime, timezone

from cartograph.config import load
from cartograph.context import generate
from cartograph.cli import main
from cartograph import state as state_mod


def _write_current(tmp_path, content):
    p = tmp_path / "docs" / "track" / "current.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _init_scaffold(tmp_path):
    from cartograph.scaffold import init
    init(tmp_path)


# ---------------------------------------------------------------------------
# current work section
# ---------------------------------------------------------------------------

def test_context_shows_open_items(tmp_path):
    _write_current(tmp_path, "- [ ] embedding integration\n- [ ] manifest channel\n")
    out = generate(load(tmp_path))
    assert "embedding integration" in out
    assert "manifest channel" in out


def test_context_open_items_formatted_as_checkboxes(tmp_path):
    _write_current(tmp_path, "- [ ] do the thing\n")
    out = generate(load(tmp_path))
    assert "- [ ] do the thing" in out


def test_context_closed_items_not_listed(tmp_path):
    _write_current(tmp_path, "- [ ] open\n- [x] done\n")
    out = generate(load(tmp_path))
    assert "done" not in out.split("## Current work")[1].split("##")[0]


def test_context_closed_count_shown(tmp_path):
    _write_current(tmp_path, "- [ ] open\n- [x] done one\n- [x] done two\n")
    out = generate(load(tmp_path))
    assert "2 closed item(s)" in out


def test_context_no_track_file_message(tmp_path):
    out = generate(load(tmp_path))
    assert "No track file" in out


def test_context_no_open_items_message(tmp_path):
    _write_current(tmp_path, "- [x] all done\n")
    out = generate(load(tmp_path))
    assert "No open items." in out


# ---------------------------------------------------------------------------
# reconcile section
# ---------------------------------------------------------------------------

def test_context_never_run_message(tmp_path):
    out = generate(load(tmp_path))
    assert "Never run." in out


def test_context_shows_last_run_date(tmp_path):
    st = state_mod.load(tmp_path)
    st.last_run = datetime(2026, 4, 20, tzinfo=timezone.utc)
    state_mod.save(st, tmp_path)
    out = generate(load(tmp_path))
    assert "2026-04-20" in out


def test_context_shows_resolved_count(tmp_path):
    st = state_mod.load(tmp_path)
    st.last_run = datetime(2026, 4, 20, tzinfo=timezone.utc)
    state_mod.mark_resolved(st, "C1:foo:bar")
    state_mod.mark_resolved(st, "C2:baz:qux")
    state_mod.save(st, tmp_path)
    out = generate(load(tmp_path))
    assert "2 resolved flag(s)" in out


def test_context_reconcile_hint_present(tmp_path):
    out = generate(load(tmp_path))
    assert "cartograph reconcile" in out


# ---------------------------------------------------------------------------
# orientation section
# ---------------------------------------------------------------------------

def test_context_no_scaffold_message(tmp_path):
    out = generate(load(tmp_path))
    assert "No scaffold" in out


def test_context_orientation_shows_sections(tmp_path):
    _init_scaffold(tmp_path)
    out = generate(load(tmp_path))
    for name in ("thesis", "architecture", "product"):
        assert name in out


def test_context_orientation_shows_lifecycle(tmp_path):
    _init_scaffold(tmp_path)
    out = generate(load(tmp_path))
    assert "stable" in out
    assert "moderate" in out
    assert "fast" in out


def test_context_orientation_shows_primary_question(tmp_path):
    _init_scaffold(tmp_path)
    out = generate(load(tmp_path))
    assert "Why does this exist" in out


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------

def test_context_has_date_header(tmp_path):
    from datetime import date
    out = generate(load(tmp_path))
    assert f"# Project Context — {date.today().isoformat()}" in out


def test_context_sections_in_order(tmp_path):
    out = generate(load(tmp_path))
    assert out.index("## Current work") < out.index("## Reconcile") < out.index("## Orientation")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_context_returns_zero(tmp_path):
    assert main(["context"], repo_path=tmp_path) == 0


def test_cli_context_prints_output(tmp_path, capsys):
    main(["context"], repo_path=tmp_path)
    out = capsys.readouterr().out
    assert "# Project Context" in out
    assert "## Current work" in out
    assert "## Reconcile" in out
    assert "## Orientation" in out


# ---------------------------------------------------------------------------
# query ranking
# ---------------------------------------------------------------------------

def _fake_embed_factory(n_sections):
    """Return an embed fn that gives query vec [1,0] and sections with decreasing similarity."""
    np = pytest.importorskip("numpy")

    def fake_embed(texts):
        vecs = np.zeros((len(texts), 2))
        vecs[0] = [1.0, 0.0]
        for i in range(1, len(texts)):
            vecs[i] = [round(1.0 - i * 0.15, 4), round(i * 0.15, 4)]
        return vecs

    return fake_embed


def test_query_ranked_shows_top_note(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    _init_scaffold(tmp_path)
    import cartograph.adapters.embeddings as emb
    monkeypatch.setattr(emb, "_AVAILABLE", True)
    monkeypatch.setattr(emb, "embed", _fake_embed_factory(5))
    out = generate(load(tmp_path), query="architecture decisions")
    assert 'Top sections for: "architecture decisions"' in out


def test_query_ranked_limits_to_three(tmp_path, monkeypatch):
    pytest.importorskip("numpy")
    _init_scaffold(tmp_path)
    import cartograph.adapters.embeddings as emb
    monkeypatch.setattr(emb, "_AVAILABLE", True)
    monkeypatch.setattr(emb, "embed", _fake_embed_factory(5))
    out = generate(load(tmp_path), query="architecture decisions")
    orientation = out.split("## Orientation")[1]
    section_rows = [l for l in orientation.splitlines() if " — " in l and not l.startswith("_")]
    assert len(section_rows) == 3


def test_query_no_embeddings_fallback_shows_all(tmp_path, monkeypatch):
    _init_scaffold(tmp_path)
    import cartograph.adapters.embeddings as emb
    monkeypatch.setattr(emb, "_AVAILABLE", False)
    out = generate(load(tmp_path), query="architecture decisions")
    assert "unavailable" in out
    orientation = out.split("## Orientation")[1]
    section_rows = [l for l in orientation.splitlines() if " — " in l and not l.startswith("_")]
    assert len(section_rows) == 5


def test_query_none_shows_all_sections(tmp_path):
    _init_scaffold(tmp_path)
    out = generate(load(tmp_path), query=None)
    assert 'Top sections for' not in out
    orientation = out.split("## Orientation")[1]
    assert orientation.count(" — ") == 5


def test_cli_context_query_flag(tmp_path, monkeypatch, capsys):
    _init_scaffold(tmp_path)
    import cartograph.adapters.embeddings as emb
    monkeypatch.setattr(emb, "_AVAILABLE", False)
    main(["context", "--query", "ops and deployment"], repo_path=tmp_path)
    out = capsys.readouterr().out
    assert "unavailable" in out
