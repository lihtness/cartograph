from __future__ import annotations

from cartograph.adapters.markdown import parse_roadmap
from cartograph.config import Config
from cartograph.flag import Flag, TRACK_CLOSE
from cartograph.state import make_flag_id


def run(config: Config) -> list[Flag]:
    current = config.repo_path / config.track.dir / config.track.current
    if not current.exists():
        return []
    items = parse_roadmap(current)
    closed_count = sum(1 for i in items if i.status == "closed")
    if closed_count >= config.track.close_threshold:
        return [Flag(
            id=make_flag_id(4, current, "track close"),
            channel=4, type=TRACK_CLOSE,
            source=str(current),
            detail=(
                f"current.md has {closed_count} closed items — "
                "run `cartograph track close` to seal them"
            ),
        )]
    return []
