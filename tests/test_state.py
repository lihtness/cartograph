from datetime import datetime
from pathlib import Path
from cartograph import state as st


def test_load_missing(tmp_path):
    s = st.load(tmp_path)
    assert s.last_run is None
    assert s.resolved_ids == set()


def test_roundtrip(tmp_path):
    s = st.State(
        last_run=datetime(2026, 4, 26, 10, 30, 0),
        resolved_ids={"C2:foo:bar", "C1:baz:qux"},
    )
    st.save(s, tmp_path)
    loaded = st.load(tmp_path)
    assert loaded.last_run == s.last_run
    assert loaded.resolved_ids == s.resolved_ids


def test_empty_resolved_roundtrip(tmp_path):
    s = st.State(last_run=datetime(2026, 4, 26, 0, 0, 0))
    st.save(s, tmp_path)
    loaded = st.load(tmp_path)
    assert loaded.resolved_ids == set()


def test_save_creates_dir(tmp_path):
    st.save(st.State(), tmp_path)
    assert (tmp_path / ".cartograph" / "state.toml").exists()


def test_mark_and_check_resolved(tmp_path):
    s = st.load(tmp_path)
    st.mark_resolved(s, "C2:foo:bar")
    assert st.is_resolved(s, "C2:foo:bar")
    assert not st.is_resolved(s, "C2:foo:other")


def test_resolved_persists(tmp_path):
    s = st.load(tmp_path)
    st.mark_resolved(s, "C2:foo:bar")
    st.save(s, tmp_path)
    s2 = st.load(tmp_path)
    assert st.is_resolved(s2, "C2:foo:bar")


def test_flag_id_basic():
    fid = st.make_flag_id(2, Path("memory/embedding_strategy.md"), "semantic match")
    assert fid == "C2:embedding_strategy:semantic_match"


def test_flag_id_strips_stop_words():
    fid = st.make_flag_id(1, Path("channels/git.py"), "the embedding adapter")
    assert fid == "C1:git:embedding_adapter"


def test_flag_id_max_three_tokens():
    fid = st.make_flag_id(3, Path("docs/arch.md"), "one two three four five")
    term = fid.split(":")[2]
    assert len(term.split("_")) <= 3


def test_flag_id_normalises_stem():
    fid = st.make_flag_id(1, Path("src/my-module.py"), "drift")
    assert fid == "C1:my_module:drift"
