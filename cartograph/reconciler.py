from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cartograph import state as state_mod
from cartograph.channels import git as git_channel
from cartograph.channels import manifest as manifest_channel
from cartograph.channels import memory as memory_channel
from cartograph.channels import track as track_channel
from cartograph.config import Config
from cartograph.flag import Flag


@dataclass
class ReconcileResult:
    flags: list[Flag]
    channels_run: list[int]
    timestamp: datetime


def run(config: Config) -> ReconcileResult:
    state = state_mod.load(config.repo_path)
    flags: list[Flag] = []
    channels_run: list[int] = []

    if config.channels.git:
        flags.extend(git_channel.run(config, state.last_run))
        channels_run.append(1)

    if config.channels.memory:
        flags.extend(memory_channel.run(config))
        channels_run.append(2)

    if config.channels.manifest:
        flags.extend(manifest_channel.run(config))
        channels_run.append(3)

    if config.channels.track:
        flags.extend(track_channel.run(config))
        channels_run.append(4)

    for flag in flags:
        if state_mod.is_resolved(state, flag.id):
            flag.resolved = True

    from cartograph import observations as obs_mod
    obs_mod.update(config)
    obs_mod.cleanup(config)

    state.last_run = datetime.now(tz=timezone.utc)
    state_mod.save(state, config.repo_path)

    return ReconcileResult(flags=flags, channels_run=channels_run, timestamp=state.last_run)
