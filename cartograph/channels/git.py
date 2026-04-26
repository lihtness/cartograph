from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from cartograph.adapters.git import git_log_since, path_to_terms
from cartograph.adapters.markdown import parse_roadmap
from cartograph.config import Config
from cartograph.flag import Flag, STALE, UNTRACKED
from cartograph.state import make_flag_id


def run(config: Config, last_run: datetime | None = None) -> list[Flag]:
    roadmap_path = config.repo_path / config.track.dir / config.track.current
    if not roadmap_path.exists():
        return []

    window_days = max(config.git.lookback_days, config.reconcile.stale_roadmap_days)
    try:
        events = git_log_since(
            config.repo_path,
            (_utcnow() - timedelta(days=window_days)).isoformat(),
        )
    except Exception:
        return []

    roadmap_items = parse_roadmap(roadmap_path)
    flags: list[Flag] = []

    # STALE: open roadmap item, no matching git activity within stale window
    stale_since = _utcnow() - timedelta(days=config.reconcile.stale_roadmap_days)
    stale_terms: set[str] = set()
    for e in events:
        if _aware(e.date) >= stale_since:
            for f in e.files:
                stale_terms |= path_to_terms(f)

    for item in (i for i in roadmap_items if i.status == "open"):
        if not item.terms & stale_terms:
            flags.append(Flag(
                id=make_flag_id(1, roadmap_path, " ".join(sorted(item.terms)[:3])),
                channel=1, type=STALE,
                source=str(roadmap_path),
                detail=f"no git activity in {config.reconcile.stale_roadmap_days}d matching open item: {item.text[:80]}",
            ))

    # UNTRACKED: git changes since last_run with no roadmap coverage
    all_roadmap_terms: set[str] = set()
    for item in roadmap_items:
        all_roadmap_terms |= item.terms
    if not all_roadmap_terms:
        return flags  # no roadmap items — skip to avoid noise

    lookback_dt = _aware(last_run) if last_run else (_utcnow() - timedelta(days=config.git.lookback_days))
    seen: set[str] = set()
    for event in events:
        if _aware(event.date) < lookback_dt:
            continue
        for fpath in event.files:
            if fpath in seen:
                continue
            seen.add(fpath)
            if not path_to_terms(fpath) & all_roadmap_terms:
                flags.append(Flag(
                    id=make_flag_id(1, Path(fpath), "untracked"),
                    channel=1, type=UNTRACKED,
                    source=fpath,
                    detail=f"git changes to {fpath!r} — no roadmap item covers these terms",
                ))

    return flags


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
