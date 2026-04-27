import pytest
from pathlib import Path

from cartograph.config import load
from cartograph.track import done


def _setup(tmp_path, content):
    p = tmp_path / "docs" / "track" / "current.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# track done
# ---------------------------------------------------------------------------

def test_done_marks_single_item(tmp_path):
    _setup(tmp_path, "- [ ] embedding integration\n- [ ] manifest channel\n")
    results = done(tmp_path, load(tmp_path), ["embedding"])
    assert results["embedding"] is not None
    content = (tmp_path / "docs" / "track" / "current.md").read_text()
    assert "- [x] embedding integration" in content
    assert "- [ ] manifest channel" in content


def test_done_marks_multiple_items(tmp_path):
    _setup(tmp_path, "- [ ] auth flow\n- [ ] data layer\n- [ ] ui polish\n")
    results = done(tmp_path, load(tmp_path), ["auth", "data"])
    assert results["auth"] is not None
    assert results["data"] is not None
    content = (tmp_path / "docs" / "track" / "current.md").read_text()
    assert "- [x] auth flow" in content
    assert "- [x] data layer" in content
    assert "- [ ] ui polish" in content


def test_done_no_match_returns_none(tmp_path):
    _setup(tmp_path, "- [ ] embedding integration\n")
    results = done(tmp_path, load(tmp_path), ["nonexistent"])
    assert results["nonexistent"] is None


def test_done_case_insensitive(tmp_path):
    _setup(tmp_path, "- [ ] Reddit RSS watcher\n")
    results = done(tmp_path, load(tmp_path), ["reddit rss"])
    assert results["reddit rss"] is not None


def test_done_does_not_match_already_closed(tmp_path):
    _setup(tmp_path, "- [x] already done\n- [ ] still open\n")
    results = done(tmp_path, load(tmp_path), ["already"])
    assert results["already"] is None


def test_done_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        done(tmp_path, load(tmp_path), ["anything"])


def test_cli_track_done_returns_zero(tmp_path):
    from cartograph.cli import main
    _setup(tmp_path, "- [ ] auth flow\n- [ ] data layer\n")
    assert main(["track", "done", "auth", "data"], repo_path=tmp_path) == 0


def test_cli_track_done_prints_matched(tmp_path, capsys):
    from cartograph.cli import main
    _setup(tmp_path, "- [ ] auth flow\n")
    main(["track", "done", "auth"], repo_path=tmp_path)
    out = capsys.readouterr().out
    assert "done:" in out
    assert "auth" in out


def test_cli_track_done_prints_no_match(tmp_path, capsys):
    from cartograph.cli import main
    _setup(tmp_path, "- [ ] auth flow\n")
    main(["track", "done", "unknown"], repo_path=tmp_path)
    out = capsys.readouterr().out
    assert "no match" in out
