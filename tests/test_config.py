from pathlib import Path
from cartograph.config import load


def test_defaults(tmp_path):
    cfg = load(tmp_path)
    assert cfg.repo_path == tmp_path
    assert cfg.docs.root == "docs"
    assert cfg.docs.manifest == ".cartograph/manifest.toml"
    assert cfg.git.lookback_days == 14
    assert cfg.embeddings.enabled is False
    assert cfg.embeddings.channels == ["memory", "manifest"]
    assert cfg.channels.git is True


def test_partial_git_override(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text("[git]\nlookback_days = 7\n")
    cfg = load(tmp_path)
    assert cfg.git.lookback_days == 7
    assert cfg.docs.root == "docs"


def test_docs_section_partial(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text(
        '[docs]\nroot = "knowledge"\nroadmap = "knowledge/roadmap.md"\n'
    )
    cfg = load(tmp_path)
    assert cfg.docs.root == "knowledge"
    assert cfg.docs.roadmap == "knowledge/roadmap.md"
    assert cfg.docs.manifest == ".cartograph/manifest.toml"


def test_embeddings_enabled(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text(
        '[embeddings]\nenabled = true\nchannels = ["memory"]\n'
    )
    cfg = load(tmp_path)
    assert cfg.embeddings.enabled is True
    assert cfg.embeddings.channels == ["memory"]


def test_channels_disabled(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text("[channels]\ngit = false\n")
    cfg = load(tmp_path)
    assert cfg.channels.git is False
    assert cfg.channels.memory is True


def test_unknown_keys_ignored(tmp_path):
    (tmp_path / ".cartograph").mkdir()
    (tmp_path / ".cartograph/config.toml").write_text(
        "[git]\nlookback_days = 3\nfuture_option = true\n"
    )
    cfg = load(tmp_path)
    assert cfg.git.lookback_days == 3
