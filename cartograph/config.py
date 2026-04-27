from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields as dc_fields
from pathlib import Path


@dataclass
class DocsConfig:
    root: str = "docs"
    manifest: str = ".cartograph/manifest.toml"


@dataclass
class TrackConfig:
    dir: str = "docs/track"
    current: str = "current.md"


@dataclass
class MemoryConfig:
    root: str = ".claude/projects"
    format: str = "claude"


@dataclass
class GitConfig:
    lookback_days: int = 14


@dataclass
class ReconcileConfig:
    memory_signal_threshold: float = 0.25
    memory_semantic_threshold: float = 0.72
    stale_roadmap_days: int = 14
    report_output: str = "docs/reports/reconcile_{date}.md"


@dataclass
class EmbeddingsConfig:
    enabled: bool = False
    model: str = "BAAI/bge-small-en-v1.5"
    channels: list[str] = field(default_factory=lambda: ["memory", "manifest"])


@dataclass
class ChannelsConfig:
    git: bool = True
    memory: bool = True
    manifest: bool = True


@dataclass
class Config:
    repo_path: Path
    docs: DocsConfig = field(default_factory=DocsConfig)
    track: TrackConfig = field(default_factory=TrackConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    git: GitConfig = field(default_factory=GitConfig)
    reconcile: ReconcileConfig = field(default_factory=ReconcileConfig)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    channels: ChannelsConfig = field(default_factory=ChannelsConfig)


def load(repo_path: Path) -> Config:
    config_path = repo_path / ".cartograph" / "config.toml"
    raw: dict = {}
    if config_path.exists():
        with config_path.open("rb") as f:
            raw = tomllib.load(f)
    return Config(
        repo_path=repo_path,
        docs=_merge(DocsConfig, raw.get("docs", {})),
        track=_merge(TrackConfig, raw.get("track", {})),
        memory=_merge(MemoryConfig, raw.get("memory", {})),
        git=_merge(GitConfig, raw.get("git", {})),
        reconcile=_merge(ReconcileConfig, raw.get("reconcile", {})),
        embeddings=_merge(EmbeddingsConfig, raw.get("embeddings", {})),
        channels=_merge(ChannelsConfig, raw.get("channels", {})),
    )


def _merge(cls, data: dict):
    known = {f.name for f in dc_fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})
