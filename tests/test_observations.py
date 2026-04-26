from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cartograph.config import load
from cartograph.observations import update, cleanup, query_file, query_recent
from cartograph.cli import main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path,
                   check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path,
                   check=True, capture_output=True)


def _commit(tmp_path: Path, message: str = "test") -> str:
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=tmp_path,
                   check=True, capture_output=True)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                            capture_output=True, text=True)
    return result.stdout.strip()


def _write(tmp_path: Path, rel: str, content: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


# ---------------------------------------------------------------------------
# update — pair extraction
# ---------------------------------------------------------------------------

def test_update_creates_jsonl_for_co_changed_files(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md",
           "# Concept\n\n## Channel 1\n\nsome text\n")
    _write(tmp_path, "src/channels.py",
           "def run(config):\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md",
           "# Concept\n\n## Channel 1\n\nupdated text\n")
    _write(tmp_path, "src/channels.py",
           "def run(config):\n    return []\n")
    _commit(tmp_path, "update both")

    config = load(tmp_path)
    count = update(config)
    assert count > 0

    obs_dir = tmp_path / ".cartograph" / "observations"
    assert (obs_dir / "concept.jsonl").exists()


def test_update_records_section_and_func(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Channel 1\n\nv1\n")
    _write(tmp_path, "src/channels.py", "def run(config):\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Channel 1\n\nv2\n")
    _write(tmp_path, "src/channels.py", "def run(config):\n    return []\n")
    _commit(tmp_path, "update both")

    config = load(tmp_path)
    update(config)

    entries = [
        json.loads(l)
        for l in (tmp_path / ".cartograph/observations/concept.jsonl").read_text().splitlines()
        if l.strip()
    ]
    assert any(e["section"] == "Channel 1" for e in entries)
    assert any("channels" in e["code_file"] for e in entries)


def test_update_skips_commit_with_only_code(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "src/channels.py", "def run():\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "src/channels.py", "def run():\n    return []\n")
    _commit(tmp_path, "code only")

    config = load(tmp_path)
    count = update(config)
    assert count == 0


def test_update_skips_commit_with_only_md(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv1\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv2\n")
    _commit(tmp_path, "md only")

    config = load(tmp_path)
    count = update(config)
    assert count == 0


def test_update_incremental_does_not_reprocess(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv1\n")
    _write(tmp_path, "src/channels.py", "def run():\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv2\n")
    _write(tmp_path, "src/channels.py", "def run():\n    return []\n")
    _commit(tmp_path, "update both")

    config = load(tmp_path)
    first = update(config)
    second = update(config)
    assert first > 0
    assert second == 0  # nothing new to process


def test_update_multiple_sections_per_commit(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md",
           "# Concept\n\n## Section A\n\nv1\n\n## Section B\n\nv1\n")
    _write(tmp_path, "src/channels.py", "def run():\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md",
           "# Concept\n\n## Section A\n\nv2\n\n## Section B\n\nv2\n")
    _write(tmp_path, "src/channels.py", "def run():\n    return []\n")
    _commit(tmp_path, "update both sections")

    config = load(tmp_path)
    update(config)

    entries = [
        json.loads(l)
        for l in (tmp_path / ".cartograph/observations/concept.jsonl").read_text().splitlines()
        if l.strip()
    ]
    sections = {e["section"] for e in entries}
    assert "Section A" in sections
    assert "Section B" in sections


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def test_cleanup_removes_entries_for_deleted_section(tmp_path):
    _init_repo(tmp_path)
    obs_dir = tmp_path / ".cartograph" / "observations"
    obs_dir.mkdir(parents=True)

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Kept Section\n\ntext\n")
    entry_kept = {"section": "Kept Section", "md_file": "docs/concept.md",
                  "code_file": "src/a.py", "func": "run", "commit": "abc", "date": "2026-04-01"}
    entry_gone = {"section": "Removed Section", "md_file": "docs/concept.md",
                  "code_file": "src/a.py", "func": "run", "commit": "abc", "date": "2026-04-01"}
    (obs_dir / "concept.jsonl").write_text(
        json.dumps(entry_kept) + "\n" + json.dumps(entry_gone) + "\n"
    )

    config = load(tmp_path)
    removed = cleanup(config)
    assert removed == 1

    remaining = [json.loads(l) for l in
                 (obs_dir / "concept.jsonl").read_text().splitlines() if l.strip()]
    assert len(remaining) == 1
    assert remaining[0]["section"] == "Kept Section"


def test_cleanup_removes_obs_file_when_markdown_deleted(tmp_path):
    _init_repo(tmp_path)
    obs_dir = tmp_path / ".cartograph" / "observations"
    obs_dir.mkdir(parents=True)

    entry = {"section": "Section", "md_file": "docs/gone.md",
             "code_file": "src/a.py", "func": "run", "commit": "abc", "date": "2026-04-01"}
    (obs_dir / "gone.jsonl").write_text(json.dumps(entry) + "\n")

    config = load(tmp_path)
    removed = cleanup(config)
    assert removed == 1
    assert not (obs_dir / "gone.jsonl").exists()


def test_cleanup_keeps_all_when_sections_unchanged(tmp_path):
    _init_repo(tmp_path)
    obs_dir = tmp_path / ".cartograph" / "observations"
    obs_dir.mkdir(parents=True)

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section A\n\ntext\n")
    entry = {"section": "Section A", "md_file": "docs/concept.md",
             "code_file": "src/a.py", "func": "run", "commit": "abc", "date": "2026-04-01"}
    (obs_dir / "concept.jsonl").write_text(json.dumps(entry) + "\n")

    config = load(tmp_path)
    removed = cleanup(config)
    assert removed == 0


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

def test_query_file_returns_related_docs(tmp_path):
    _init_repo(tmp_path)
    obs_dir = tmp_path / ".cartograph" / "observations"
    obs_dir.mkdir(parents=True)

    for _ in range(3):
        entry = {"section": "Channel 1", "md_file": "docs/concept.md",
                 "code_file": "src/channels.py", "func": "run",
                 "commit": "abc", "date": "2026-04-01"}
        with (obs_dir / "concept.jsonl").open("a") as f:
            f.write(json.dumps(entry) + "\n")

    config = load(tmp_path)
    results = query_file(config, "src/channels.py")
    assert len(results) == 1
    md, section, count = results[0]
    assert section == "Channel 1"
    assert count == 3


def test_query_file_no_results(tmp_path):
    _init_repo(tmp_path)
    config = load(tmp_path)
    assert query_file(config, "src/unknown.py") == []


def test_query_recent_uses_git_log(tmp_path):
    _init_repo(tmp_path)
    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv1\n")
    _write(tmp_path, "src/channels.py", "def run():\n    pass\n")
    _commit(tmp_path, "initial")

    _write(tmp_path, "docs/concept.md", "# Concept\n\n## Section\n\nv2\n")
    _write(tmp_path, "src/channels.py", "def run():\n    return []\n")
    _commit(tmp_path, "update both")

    config = load(tmp_path)
    update(config)

    results = query_recent(config, n=5)
    assert len(results) > 0
    assert any("concept.md" in md for md, _, _ in results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_related_no_observations(tmp_path, capsys):
    _init_repo(tmp_path)
    rc = main(["related", "src/channels.py"], repo_path=tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "No observations" in out


def test_cli_related_shows_results(tmp_path, capsys):
    _init_repo(tmp_path)
    obs_dir = tmp_path / ".cartograph" / "observations"
    obs_dir.mkdir(parents=True)
    entry = {"section": "Channel 1", "md_file": "docs/concept.md",
             "code_file": "src/channels.py", "func": "run",
             "commit": "abc", "date": "2026-04-01"}
    (obs_dir / "concept.jsonl").write_text(json.dumps(entry) + "\n")

    main(["related", "src/channels.py"], repo_path=tmp_path)
    out = capsys.readouterr().out
    assert "Channel 1" in out
    assert "concept.md" in out
