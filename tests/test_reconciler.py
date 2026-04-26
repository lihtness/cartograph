import subprocess
from datetime import datetime, timezone
from pathlib import Path

from cartograph import state as state_mod
from cartograph.config import load
from cartograph.flag import BROKEN_DEP, GAP, STALE, UNTRACKED
from cartograph.reconciler import ReconcileResult, run
from cartograph.reporter import render, write_report


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

def _setup_project(repo):
    """Full fixture: roadmap, memory, manifest, one unrelated git commit."""
    (repo / "docs" / "product").mkdir(parents=True)
    (repo / "docs" / "product" / "roadmap.md").write_text(
        "- [ ] embedding integration\n- [x] config module\n"
    )
    (repo / ".claude" / "projects" / "test" / "memory").mkdir(parents=True)
    (repo / ".claude" / "projects" / "test" / "memory" / "auth_design.md").write_text("""\
---
name: auth design
description: authentication system not yet built
type: project
---
""")
    (repo / ".cartograph").mkdir(exist_ok=True)
    (repo / ".cartograph" / "manifest.toml").write_text("""\
[[edge]]
from = "docs/product/roadmap.md"
to = "docs/architecture/decisions.md"
type = "depends_on"
term = "embedding adapter"
""")
    (repo / "src").mkdir()
    (repo / "src" / "auth.py").write_text("# auth\n")
    subprocess.run(["git", "add", "src/auth.py"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add auth"], cwd=repo, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# reconciler
# ---------------------------------------------------------------------------

def test_reconcile_returns_flags(repo):
    _setup_project(repo)
    result = run(load(repo))
    assert isinstance(result, ReconcileResult)
    assert len(result.flags) > 0


def test_reconcile_channels_run(repo):
    _setup_project(repo)
    result = run(load(repo))
    assert result.channels_run == [1, 2, 3]


def test_reconcile_all_channel_types_present(repo):
    _setup_project(repo)
    result = run(load(repo))
    types = {f.type for f in result.flags}
    assert STALE in types       # Channel 1: embedding item, no embedding git
    assert UNTRACKED in types   # Channel 1: auth.py not in roadmap
    assert GAP in types         # Channel 2: auth signal vs embedding roadmap
    assert BROKEN_DEP in types  # Channel 3: decisions.md missing


def test_reconcile_disabled_channel_skipped(repo):
    _setup_project(repo)
    (repo / ".cartograph" / "config.toml").write_text("[channels]\nmemory = false\n")
    result = run(load(repo))
    assert 2 not in result.channels_run
    assert all(f.channel != 2 for f in result.flags)


def test_reconcile_marks_resolved_flags(repo):
    _setup_project(repo)
    # First run to collect flag IDs
    result1 = run(load(repo))
    first_flag = result1.flags[0]

    # Mark it resolved in state
    st = state_mod.load(repo)
    state_mod.mark_resolved(st, first_flag.id)
    state_mod.save(st, repo)

    # Second run — that flag should be marked resolved
    result2 = run(load(repo))
    match = next((f for f in result2.flags if f.id == first_flag.id), None)
    assert match is not None
    assert match.resolved is True


def test_reconcile_updates_last_run(repo):
    _setup_project(repo)
    assert state_mod.load(repo).last_run is None
    run(load(repo))
    assert state_mod.load(repo).last_run is not None


def test_reconcile_timestamp_is_utc(repo):
    _setup_project(repo)
    result = run(load(repo))
    assert result.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# reporter — render
# ---------------------------------------------------------------------------

def _make_result(flags, channels_run=None):
    return ReconcileResult(
        flags=flags,
        channels_run=channels_run or [1, 2, 3],
        timestamp=datetime(2026, 4, 26, 10, 0, 0, tzinfo=timezone.utc),
    )


def test_render_title():
    result = _make_result([])
    assert "# Reconciliation Report — 2026-04-26" in render(result)


def test_render_channel_headings():
    result = _make_result([], channels_run=[1, 2, 3])
    text = render(result)
    assert "## Channel 1: Git → Roadmap" in text
    assert "## Channel 2: Memory → Roadmap" in text
    assert "## Channel 3: Manifest → Docs" in text


def test_render_no_issues_when_empty():
    result = _make_result([])
    text = render(result)
    assert text.count("No issues found.") == 3


def test_render_flag_in_correct_channel():
    from cartograph.flag import Flag
    flags = [
        Flag(id="C1:x:y", channel=1, type=STALE, source="roadmap.md", detail="stale item"),
        Flag(id="C2:a:b", channel=2, type=GAP, source="mem.md", detail="no match"),
    ]
    result = _make_result(flags)
    text = render(result)
    ch1_pos = text.index("## Channel 1")
    ch2_pos = text.index("## Channel 2")
    stale_pos = text.index("STALE")
    gap_pos = text.index("GAP")
    assert ch1_pos < stale_pos < ch2_pos
    assert ch2_pos < gap_pos


def test_render_resolved_section():
    from cartograph.flag import Flag
    flags = [
        Flag(id="C1:x:y", channel=1, type=STALE, source="roadmap.md", detail="stale", resolved=True),
    ]
    result = _make_result(flags)
    text = render(result)
    assert "## Resolved (suppressed)" in text
    assert "C1:x:y" in text
    assert "No issues found." in text  # open section is empty


def test_render_relative_source(tmp_path):
    from cartograph.flag import Flag
    source = str(tmp_path / "docs" / "roadmap.md")
    flags = [Flag(id="C1:x:y", channel=1, type=STALE, source=source, detail="d")]
    result = _make_result(flags, channels_run=[1])
    text = render(result, repo_path=tmp_path)
    assert "docs/roadmap.md" in text
    assert str(tmp_path) not in text


# ---------------------------------------------------------------------------
# reporter — write_report
# ---------------------------------------------------------------------------

def test_write_report_creates_file(repo):
    _setup_project(repo)
    result = run(load(repo))
    path = write_report(result, load(repo))
    assert path.exists()
    assert path.suffix == ".md"


def test_write_report_path_contains_date(repo):
    _setup_project(repo)
    result = run(load(repo))
    path = write_report(result, load(repo))
    assert result.timestamp.strftime("%Y-%m-%d") in path.name


def test_write_report_content_has_flags(repo):
    _setup_project(repo)
    result = run(load(repo))
    path = write_report(result, load(repo))
    content = path.read_text()
    assert "# Reconciliation Report" in content
    assert "STALE" in content or "UNTRACKED" in content or "GAP" in content
