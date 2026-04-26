import subprocess
from pathlib import Path

import pytest

from cartograph import reconciler, state as state_mod
from cartograph.cli import main
from cartograph.config import load


# ---------------------------------------------------------------------------
# fixture helper
# ---------------------------------------------------------------------------

def _setup_project(repo):
    (repo / "docs" / "product").mkdir(parents=True)
    (repo / "docs" / "product" / "roadmap.md").write_text(
        "- [ ] embedding integration\n"
    )
    (repo / "src").mkdir()
    (repo / "src" / "auth.py").write_text("# auth\n")
    subprocess.run(["git", "add", "src/auth.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add auth"], cwd=repo, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# reconcile
# ---------------------------------------------------------------------------

def test_reconcile_returns_zero(repo):
    _setup_project(repo)
    assert main(["reconcile"], repo_path=repo) == 0


def test_reconcile_writes_report_file(repo):
    _setup_project(repo)
    main(["reconcile"], repo_path=repo)
    reports = list((repo / "docs" / "reports").glob("*.md"))
    assert len(reports) == 1


def test_reconcile_output_has_summary(repo, capsys):
    _setup_project(repo)
    main(["reconcile"], repo_path=repo)
    out = capsys.readouterr().out
    assert "Report:" in out
    assert "Flags:" in out


def test_reconcile_output_lists_flags(repo, capsys):
    _setup_project(repo)
    main(["reconcile"], repo_path=repo)
    out = capsys.readouterr().out
    assert any(t in out for t in ("STALE", "UNTRACKED", "GAP", "BROKEN_DEP"))


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------

def test_resolve_marks_flag_in_state(repo):
    _setup_project(repo)
    result = reconciler.run(load(repo))
    flag_id = result.flags[0].id

    assert main(["resolve", flag_id], repo_path=repo) == 0
    assert state_mod.is_resolved(state_mod.load(repo), flag_id)


def test_resolve_already_resolved_message(repo, capsys):
    _setup_project(repo)
    result = reconciler.run(load(repo))
    flag_id = result.flags[0].id

    main(["resolve", flag_id], repo_path=repo)
    capsys.readouterr()
    main(["resolve", flag_id], repo_path=repo)
    assert "Already resolved" in capsys.readouterr().out


def test_resolve_unknown_id_still_marks(repo, capsys):
    main(["resolve", "C1:fake:flag"], repo_path=repo)
    assert state_mod.is_resolved(state_mod.load(repo), "C1:fake:flag")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def test_status_before_reconcile(repo, capsys):
    main(["status"], repo_path=repo)
    assert "never" in capsys.readouterr().out


def test_status_after_reconcile(repo, capsys):
    _setup_project(repo)
    main(["reconcile"], repo_path=repo)
    capsys.readouterr()
    main(["status"], repo_path=repo)
    out = capsys.readouterr().out
    assert "never" not in out
    assert "Resolved flags:" in out


def test_status_shows_resolved_count(repo, capsys):
    _setup_project(repo)
    result = reconciler.run(load(repo))
    state_mod.mark_resolved(state_mod.load(repo), result.flags[0].id)
    st = state_mod.load(repo)
    state_mod.mark_resolved(st, result.flags[0].id)
    state_mod.save(st, repo)

    main(["status"], repo_path=repo)
    out = capsys.readouterr().out
    assert "Resolved flags: 1" in out


# ---------------------------------------------------------------------------
# no command / help
# ---------------------------------------------------------------------------

def test_no_command_returns_zero(repo):
    assert main([], repo_path=repo) == 0


def test_manifest_no_subcommand_returns_zero(repo):
    assert main(["manifest"], repo_path=repo) == 0


# ---------------------------------------------------------------------------
# manifest add-edge
# ---------------------------------------------------------------------------

def test_manifest_add_edge_creates_file(tmp_path):
    main([
        "manifest", "add-edge",
        "--from", "docs/roadmap.md",
        "--to", "docs/arch.md",
        "--type", "depends_on",
        "--term", "embedding adapter",
    ], repo_path=tmp_path)
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    assert 'from = "docs/roadmap.md"' in content
    assert 'term = "embedding adapter"' in content


def test_manifest_add_edge_with_heading(tmp_path):
    main([
        "manifest", "add-edge",
        "--from", "docs/roadmap.md",
        "--to", "docs/arch.md#my-section",
        "--type", "depends_on",
        "--term", "adapter",
        "--heading", "My Section",
    ], repo_path=tmp_path)
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    assert 'heading = "My Section"' in content


def test_manifest_add_edge_appends(tmp_path):
    for term in ("first term", "second term"):
        main([
            "manifest", "add-edge",
            "--from", "a.md", "--to", "b.md",
            "--type", "depends_on", "--term", term,
        ], repo_path=tmp_path)
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    assert "first term" in content
    assert "second term" in content


def test_manifest_add_edge_creates_cartograph_dir(tmp_path):
    assert not (tmp_path / ".cartograph").exists()
    main([
        "manifest", "add-edge",
        "--from", "a.md", "--to", "b.md",
        "--type", "depends_on",
    ], repo_path=tmp_path)
    assert (tmp_path / ".cartograph" / "manifest.toml").exists()


# ---------------------------------------------------------------------------
# manifest add-fact
# ---------------------------------------------------------------------------

def test_manifest_add_fact_creates_fact(tmp_path):
    assert main([
        "manifest", "add-fact",
        "--key", "pricing",
        "--canonical", "docs/pricing.md",
        "--duplicate", "docs/outreach.md",
        "--duplicate", "docs/roadmap.md",
    ], repo_path=tmp_path) == 0
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    assert 'key = "pricing"' in content
    assert '"docs/outreach.md"' in content
    assert '"docs/roadmap.md"' in content


def test_manifest_add_fact_no_duplicates(tmp_path):
    main([
        "manifest", "add-fact",
        "--key", "arch",
        "--canonical", "docs/arch.md",
    ], repo_path=tmp_path)
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    assert 'key = "arch"' in content


def test_manifest_add_edge_and_fact_toml_valid(tmp_path):
    import tomllib
    main([
        "manifest", "add-edge",
        "--from", "a.md", "--to", "b.md",
        "--type", "depends_on", "--term", "foo",
    ], repo_path=tmp_path)
    main([
        "manifest", "add-fact",
        "--key", "bar", "--canonical", "a.md",
        "--duplicate", "b.md",
    ], repo_path=tmp_path)
    content = (tmp_path / ".cartograph" / "manifest.toml").read_text()
    parsed = tomllib.loads(content)
    assert len(parsed["edge"]) == 1
    assert len(parsed["fact"]) == 1
