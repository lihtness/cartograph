import subprocess
from pathlib import Path

from cartograph.channels.git import run
from cartograph.config import load
from cartograph.flag import STALE, UNTRACKED


def _write_roadmap(repo, content):
    p = repo / "docs" / "product" / "roadmap.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _commit(repo, rel_path, msg):
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=repo, check=True, capture_output=True)


def test_stale_open_item_no_matching_git(repo):
    _write_roadmap(repo, "- [ ] embedding integration\n")
    (repo / "auth.py").write_text("# auth\n")
    _commit(repo, "auth.py", "add auth")

    flags = run(load(repo))
    stale = [f for f in flags if f.type == STALE]
    assert len(stale) == 1
    assert stale[0].channel == 1


def test_no_stale_when_git_covers_item(repo):
    _write_roadmap(repo, "- [ ] auth login\n")
    (repo / "auth.py").write_text("# auth login\n")
    _commit(repo, "auth.py", "add auth login")

    stale = [f for f in run(load(repo)) if f.type == STALE]
    assert len(stale) == 0


def test_closed_item_not_stale(repo):
    _write_roadmap(repo, "- [x] embedding integration\n")
    stale = [f for f in run(load(repo)) if f.type == STALE]
    assert len(stale) == 0


def test_untracked_git_change_no_roadmap_item(repo):
    _write_roadmap(repo, "- [ ] auth login\n")
    (repo / "infra.py").write_text("# deploy\n")
    _commit(repo, "infra.py", "add deploy infra")

    untracked = [f for f in run(load(repo)) if f.type == UNTRACKED]
    assert any("infra.py" in f.source for f in untracked)


def test_no_untracked_when_roadmap_covers(repo):
    _write_roadmap(repo, "- [ ] auth login\n- next: infra deploy\n")
    (repo / "infra.py").write_text("# infra\n")
    _commit(repo, "infra.py", "add infra deploy")

    untracked = [f for f in run(load(repo)) if f.type == UNTRACKED and "infra.py" in f.source]
    assert len(untracked) == 0


def test_empty_roadmap_no_flags(repo):
    _write_roadmap(repo, "# Roadmap\n\nNothing yet.\n")
    (repo / "foo.py").write_text("x\n")
    _commit(repo, "foo.py", "add foo")
    assert run(load(repo)) == []


def test_missing_roadmap_no_flags(repo):
    assert run(load(repo)) == []


def test_multiple_open_items_stale_flags_each(repo):
    _write_roadmap(repo, "- [ ] embedding integration\n- [ ] manifest channel\n")
    (repo / "auth.py").write_text("x\n")
    _commit(repo, "auth.py", "add auth")

    stale = [f for f in run(load(repo)) if f.type == STALE]
    assert len(stale) == 2
