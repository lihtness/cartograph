from cartograph.channels.track import run
from cartograph.config import load


def _write_current(tmp_path, content):
    p = tmp_path / "docs" / "track" / "current.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_no_flag_below_threshold(tmp_path):
    _write_current(tmp_path, "- [x] done thing\n- [ ] open thing\n")
    flags = run(load(tmp_path))
    assert flags == []


def test_track_close_flag_at_threshold(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text("[track]\nclose_threshold = 2\n")
    _write_current(tmp_path, "- [x] first\n- [x] second\n- [ ] open\n")
    from cartograph.flag import TRACK_CLOSE
    flags = run(load(tmp_path))
    assert len(flags) == 1
    assert flags[0].type == TRACK_CLOSE
    assert flags[0].channel == 4
    assert "2 closed" in flags[0].detail


def test_track_close_flag_above_threshold(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text("[track]\nclose_threshold = 3\n")
    items = "".join(f"- [x] item {i}\n" for i in range(5))
    _write_current(tmp_path, items)
    flags = run(load(tmp_path))
    assert len(flags) == 1
    assert "5 closed" in flags[0].detail


def test_missing_current_returns_empty(tmp_path):
    assert run(load(tmp_path)) == []


def test_only_open_items_no_flag(tmp_path):
    _write_current(tmp_path, "- [ ] a\n- [ ] b\n- [ ] c\n")
    assert run(load(tmp_path)) == []


def test_flag_source_is_current_path(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text("[track]\nclose_threshold = 1\n")
    _write_current(tmp_path, "- [x] done\n")
    flags = run(load(tmp_path))
    assert "current.md" in flags[0].source
