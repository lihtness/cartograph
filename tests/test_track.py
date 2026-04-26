import pytest
from pathlib import Path

from cartograph.config import load
from cartograph.track import close


def _setup(tmp_path, content):
    p = tmp_path / "docs" / "track" / "current.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def test_close_creates_sealed_file(tmp_path):
    _setup(tmp_path, "- [ ] open thing\n- [x] done thing\n")
    sealed = close(tmp_path, load(tmp_path), period="2026-W18")
    assert sealed.exists()
    assert sealed.name == "2026-W18.md"


def test_close_sealed_file_contains_closed_items(tmp_path):
    _setup(tmp_path, "- [ ] open\n- [x] done alpha\n- [x] done beta\n")
    sealed = close(tmp_path, load(tmp_path), period="2026-W18")
    content = sealed.read_text()
    assert "done alpha" in content
    assert "done beta" in content


def test_close_sealed_file_has_header(tmp_path):
    _setup(tmp_path, "- [x] done\n")
    sealed = close(tmp_path, load(tmp_path), period="2026-W18")
    assert "# Track — 2026-W18" in sealed.read_text()


def test_close_removes_closed_from_current(tmp_path):
    current = _setup(tmp_path, "- [ ] open\n- [x] done\n")
    close(tmp_path, load(tmp_path), period="2026-W18")
    assert "done" not in current.read_text()
    assert "open" in current.read_text()


def test_close_open_items_stay_in_current(tmp_path):
    current = _setup(tmp_path, "- [ ] alpha\n- [x] beta\n- [ ] gamma\n")
    close(tmp_path, load(tmp_path), period="2026-W18")
    text = current.read_text()
    assert "alpha" in text
    assert "gamma" in text
    assert "beta" not in text


def test_close_appends_to_existing_sealed_file(tmp_path):
    _setup(tmp_path, "- [x] first batch\n")
    close(tmp_path, load(tmp_path), period="2026-W18")

    current = tmp_path / "docs" / "track" / "current.md"
    current.write_text("- [x] second batch\n")
    close(tmp_path, load(tmp_path), period="2026-W18")

    content = (tmp_path / "docs" / "track" / "2026-W18.md").read_text()
    assert "first batch" in content
    assert "second batch" in content


def test_close_default_period_is_iso_week(tmp_path):
    from datetime import date
    _setup(tmp_path, "- [x] done\n")
    sealed = close(tmp_path, load(tmp_path))
    today = date.today()
    year, week, _ = today.isocalendar()
    assert sealed.name == f"{year}-W{week:02d}.md"


def test_close_uppercase_x_treated_as_closed(tmp_path):
    _setup(tmp_path, "- [X] DONE uppercase\n")
    sealed = close(tmp_path, load(tmp_path), period="2026-W18")
    assert "DONE uppercase" in sealed.read_text()


def test_close_no_closed_items_raises(tmp_path):
    _setup(tmp_path, "- [ ] only open\n")
    with pytest.raises(ValueError, match="No closed items"):
        close(tmp_path, load(tmp_path), period="2026-W18")


def test_close_missing_current_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        close(tmp_path, load(tmp_path), period="2026-W18")


def test_close_custom_track_config(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text(
        '[track]\ndir = "notes/track"\ncurrent = "active.md"\n'
    )
    p = tmp_path / "notes" / "track" / "active.md"
    p.parent.mkdir(parents=True)
    p.write_text("- [x] custom done\n")
    sealed = close(tmp_path, load(tmp_path), period="2026-W18")
    assert "custom done" in sealed.read_text()
    assert "custom done" not in p.read_text()


def test_cli_track_close_returns_zero(tmp_path):
    from cartograph.cli import main
    _setup(tmp_path, "- [ ] open\n- [x] done thing\n")
    assert main(["track", "close", "--period", "2026-W18"], repo_path=tmp_path) == 0


def test_cli_track_close_no_closed_returns_one(tmp_path):
    from cartograph.cli import main
    _setup(tmp_path, "- [ ] only open\n")
    assert main(["track", "close", "--period", "2026-W18"], repo_path=tmp_path) == 1


def test_cli_track_close_missing_file_returns_one(tmp_path):
    from cartograph.cli import main
    assert main(["track", "close", "--period", "2026-W18"], repo_path=tmp_path) == 1
