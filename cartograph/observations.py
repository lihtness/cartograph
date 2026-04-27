from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from cartograph.config import Config

_HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', re.MULTILINE)
_HEADING_RE = re.compile(r'^#{1,6}\s+(.+)')
_DEF_RE = re.compile(r'^(?:\s*)(?:async )?(?:def|class)\s+(\w+)')
_MD_EXT = {'.md', '.markdown'}
_CODE_EXT = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.c', '.cpp', '.h'}


def update(config: Config) -> int:
    """Walk git log since last run, write co-occurrence pairs to JSONL files."""
    obs_dir = _obs_dir(config)
    obs_dir.mkdir(parents=True, exist_ok=True)

    last_commit = _load_state(obs_dir)
    commits = _commits_since(config.repo_path, last_commit)
    if not commits:
        return 0

    track_prefix = config.track.dir.rstrip("/") + "/"
    total = 0
    for commit_hash, commit_date in commits:
        total += _process_commit(config.repo_path, obs_dir, commit_hash,
                                 commit_date, track_prefix)

    _save_state(obs_dir, commits[0][0])  # newest first
    return total


def cleanup(config: Config) -> int:
    """Remove entries for sections that no longer exist in their markdown files."""
    obs_dir = _obs_dir(config)
    if not obs_dir.exists():
        return 0
    removed = 0
    for jsonl_path in sorted(obs_dir.glob("*.jsonl")):
        removed += _cleanup_file(config.repo_path, jsonl_path)
    return removed


def query_recent(config: Config, n: int = 10) -> list[tuple[str, str, int]]:
    """Return top (md_file, section, count) for code files changed in recent n commits."""
    obs_dir = _obs_dir(config)
    code_files = _recent_code_files(config.repo_path, n)
    counts: dict[tuple[str, str], int] = {}
    for cf in code_files:
        for (md, section), cnt in _lookup_code(obs_dir, cf).items():
            counts[(md, section)] = counts.get((md, section), 0) + cnt
    return sorted(
        [(md, sec, cnt) for (md, sec), cnt in counts.items()],
        key=lambda x: x[2], reverse=True,
    )


def query_file(config: Config, code_file: str) -> list[tuple[str, str, int]]:
    """Return (md_file, section, count) for a specific code file."""
    obs_dir = _obs_dir(config)
    result = _lookup_code(obs_dir, code_file)
    return sorted(
        [(md, sec, cnt) for (md, sec), cnt in result.items()],
        key=lambda x: x[2], reverse=True,
    )


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------

def _obs_dir(config: Config) -> Path:
    return config.repo_path / ".cartograph" / "observations"


def _load_state(obs_dir: Path) -> str | None:
    p = obs_dir / "_state.json"
    if p.exists():
        return json.loads(p.read_text()).get("last_commit")
    return None


def _save_state(obs_dir: Path, commit: str) -> None:
    (obs_dir / "_state.json").write_text(json.dumps({"last_commit": commit}))


def _commits_since(repo_path: Path, last_commit: str | None) -> list[tuple[str, str]]:
    cmd = ["git", "log", "--format=%H %as"]
    if last_commit:
        cmd += [f"{last_commit}..HEAD"]
    else:
        cmd += ["--max-count=200"]
    result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
    pairs = []
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs  # newest first


def _process_commit(repo_path: Path, obs_dir: Path,
                    commit: str, commit_date: str,
                    track_prefix: str = "") -> int:
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only",
         "--diff-filter=AM", commit],
        cwd=repo_path, capture_output=True, text=True,
    )
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    md_files = [
        f for f in files
        if Path(f).suffix in _MD_EXT
        and (not track_prefix or not f.startswith(track_prefix))
    ]
    code_files = [f for f in files if Path(f).suffix in _CODE_EXT]
    if not md_files or not code_files:
        return 0

    total = 0
    for md_file in md_files:
        sections = _changed_sections(repo_path, commit, md_file)
        if not sections:
            continue
        for code_file in code_files:
            funcs = _changed_funcs(repo_path, commit, code_file)
            if not funcs:
                funcs = [Path(code_file).stem]
            for section in sections:
                for func in funcs:
                    _append(obs_dir, md_file, section, code_file, func,
                            commit[:8], commit_date)
                    total += 1
    return total


def _changed_sections(repo_path: Path, commit: str, md_file: str) -> list[str]:
    diff = _git(repo_path, ["diff", f"{commit}^..{commit}", "-U0", "--", md_file])
    if not diff:
        return []
    content = _git(repo_path, ["show", f"{commit}:{md_file}"])
    if not content:
        return []
    lines = content.splitlines()
    changed = _hunk_new_lines(diff)
    sections = {_nearest_heading(lines, i - 1) for i in changed}
    return [s for s in sections if s]


def _changed_funcs(repo_path: Path, commit: str, code_file: str) -> list[str]:
    diff = _git(repo_path, ["diff", f"{commit}^..{commit}", "-U0", "--", code_file])
    if not diff:
        return []
    content = _git(repo_path, ["show", f"{commit}:{code_file}"])
    if not content:
        return []
    lines = content.splitlines()
    changed = _hunk_new_lines(diff)
    funcs = {_nearest_def(lines, i - 1) for i in changed}
    return [f for f in funcs if f]


def _hunk_new_lines(diff: str) -> list[int]:
    nums = []
    for m in _HUNK_RE.finditer(diff):
        start = int(m.group(1))
        count = int(m.group(2)) if m.group(2) is not None else 1
        if count > 0:
            nums.extend(range(start, start + min(count, 100)))
    return nums


def _nearest_heading(lines: list[str], idx: int) -> str | None:
    for i in range(min(idx, len(lines) - 1), -1, -1):
        m = _HEADING_RE.match(lines[i])
        if m:
            return m.group(1).strip()
    return None


def _nearest_def(lines: list[str], idx: int) -> str | None:
    for i in range(min(idx, len(lines) - 1), -1, -1):
        m = _DEF_RE.match(lines[i])
        if m:
            return m.group(1)
    return None


def _append(obs_dir: Path, md_file: str, section: str,
            code_file: str, func: str, commit: str, date: str) -> None:
    stem = Path(md_file).stem
    entry = {
        "section": section,
        "md_file": md_file,
        "code_file": code_file,
        "func": func,
        "commit": commit,
        "date": date,
    }
    with (obs_dir / f"{stem}.jsonl").open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _cleanup_file(repo_path: Path, jsonl_path: Path) -> int:
    raw = jsonl_path.read_text()
    lines = [l for l in raw.splitlines() if l.strip()]
    if not lines:
        return 0

    try:
        md_file = json.loads(lines[0]).get("md_file", "")
    except (json.JSONDecodeError, IndexError):
        return 0

    md_path = repo_path / md_file
    if not md_path.exists():
        jsonl_path.unlink()
        return len(lines)

    current = _current_headings(md_path)
    kept, removed = [], 0
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if entry.get("section") in current:
            kept.append(line)
        else:
            removed += 1

    jsonl_path.write_text("\n".join(kept) + ("\n" if kept else ""))
    return removed


def _current_headings(md_path: Path) -> set[str]:
    result = set()
    for line in md_path.read_text().splitlines():
        m = _HEADING_RE.match(line)
        if m:
            result.add(m.group(1).strip())
    return result


def _lookup_code(obs_dir: Path, code_file: str) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    if not obs_dir.exists():
        return result
    for jsonl_path in obs_dir.glob("*.jsonl"):
        for line in jsonl_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            cf = entry.get("code_file", "")
            if cf == code_file or cf.startswith(code_file.rstrip("/") + "/"):
                key = (entry.get("md_file", ""), entry.get("section", ""))
                result[key] = result.get(key, 0) + 1
    return result


def _recent_code_files(repo_path: Path, n: int) -> set[str]:
    result = subprocess.run(
        ["git", "log", f"-{n}", "--name-only", "--format=", "--diff-filter=M"],
        cwd=repo_path, capture_output=True, text=True,
    )
    return {f for f in result.stdout.splitlines() if f and Path(f).suffix in _CODE_EXT}


def _git(repo_path: Path, cmd: list[str]) -> str:
    result = subprocess.run(
        ["git"] + cmd, cwd=repo_path, capture_output=True, text=True,
    )
    return result.stdout
