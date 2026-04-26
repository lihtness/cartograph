import tomllib
from pathlib import Path

from cartograph.cli import main
from cartograph.scaffold import Section, add_section, generate_cartograph_md, init


# ---------------------------------------------------------------------------
# init — file creation
# ---------------------------------------------------------------------------

def test_init_creates_cartograph_dir(tmp_path):
    init(tmp_path)
    assert (tmp_path / ".cartograph").is_dir()


def test_init_creates_scaffold_toml(tmp_path):
    init(tmp_path)
    assert (tmp_path / ".cartograph" / "scaffold.toml").exists()


def test_init_scaffold_toml_is_valid_toml(tmp_path):
    init(tmp_path)
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        raw = tomllib.load(f)
    assert len(raw.get("section", [])) > 0


def test_init_creates_manifest_and_config(tmp_path):
    init(tmp_path)
    assert (tmp_path / ".cartograph" / "manifest.toml").exists()
    assert (tmp_path / ".cartograph" / "config.toml").exists()


def test_init_creates_cartograph_md(tmp_path):
    init(tmp_path)
    content = (tmp_path / "CARTOGRAPH.md").read_text()
    assert "# CARTOGRAPH" in content
    assert "## Document Map" in content
    assert "Primary Question" in content


def test_init_creates_claude_md(tmp_path):
    init(tmp_path)
    assert "## Documentation Structure" in (tmp_path / "CLAUDE.md").read_text()


def test_init_creates_index_files(tmp_path):
    init(tmp_path)
    for name in ("thesis", "architecture", "quality", "product", "ops"):
        assert (tmp_path / "docs" / name / "INDEX.md").exists()


def test_init_index_md_has_question(tmp_path):
    init(tmp_path)
    assert "Why does this exist" in (tmp_path / "docs" / "thesis" / "INDEX.md").read_text()


def test_init_index_md_has_intent(tmp_path):
    init(tmp_path)
    content = (tmp_path / "docs" / "thesis" / "INDEX.md").read_text()
    assert "Core hypothesis" in content


# ---------------------------------------------------------------------------
# init — templates
# ---------------------------------------------------------------------------

def test_init_default_template_is_software(tmp_path):
    init(tmp_path)
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = {s["name"] for s in tomllib.load(f)["section"]}
    assert names == {"thesis", "architecture", "quality", "product", "ops"}


def test_init_template_minimal(tmp_path):
    init(tmp_path, template="minimal")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = {s["name"] for s in tomllib.load(f)["section"]}
    assert names == {"thesis", "product"}
    assert not (tmp_path / "docs" / "architecture").exists()


def test_init_template_product(tmp_path):
    init(tmp_path, template="product")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = {s["name"] for s in tomllib.load(f)["section"]}
    assert "sales" in names
    assert "quality" not in names


def test_init_template_research(tmp_path):
    init(tmp_path, template="research")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = {s["name"] for s in tomllib.load(f)["section"]}
    assert names == {"thesis", "architecture", "quality"}


def test_init_unknown_template_falls_back_to_software(tmp_path):
    init(tmp_path, template="nonexistent")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = {s["name"] for s in tomllib.load(f)["section"]}
    assert "thesis" in names and "architecture" in names


# ---------------------------------------------------------------------------
# init — CLAUDE.md handling
# ---------------------------------------------------------------------------

def test_init_appends_to_existing_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Existing\n\nsome content\n")
    init(tmp_path)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "# Existing" in content
    assert "## Documentation Structure" in content


def test_init_does_not_duplicate_claude_section(tmp_path):
    init(tmp_path)
    init(tmp_path)
    assert (tmp_path / "CLAUDE.md").read_text().count("## Documentation Structure") == 1


def test_init_does_not_overwrite_existing_index_md(tmp_path):
    (tmp_path / "docs" / "thesis").mkdir(parents=True)
    (tmp_path / "docs" / "thesis" / "INDEX.md").write_text("# Custom\n\nMy custom content.\n")
    init(tmp_path)
    assert "My custom content." in (tmp_path / "docs" / "thesis" / "INDEX.md").read_text()


# ---------------------------------------------------------------------------
# init — scaffold.toml round-trip
# ---------------------------------------------------------------------------

def test_init_scaffold_toml_preserves_questions(tmp_path):
    init(tmp_path)
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        raw = tomllib.load(f)
    thesis = next(s for s in raw["section"] if s["name"] == "thesis")
    assert thesis["primary_question"] == "Why does this exist? What is the core bet?"


def test_init_scaffold_toml_preserves_intent_newlines(tmp_path):
    init(tmp_path)
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        raw = tomllib.load(f)
    thesis = next(s for s in raw["section"] if s["name"] == "thesis")
    assert "\n" in thesis["intent"]


# ---------------------------------------------------------------------------
# add_section
# ---------------------------------------------------------------------------

def test_add_section_creates_directory(tmp_path):
    init(tmp_path)
    add_section(tmp_path, "integrations", question="How do integrations work?")
    assert (tmp_path / "docs" / "integrations").is_dir()


def test_add_section_creates_index_md(tmp_path):
    init(tmp_path)
    add_section(tmp_path, "integrations", question="How do integrations work?")
    assert "How do integrations work?" in (tmp_path / "docs" / "integrations" / "INDEX.md").read_text()


def test_add_section_updates_scaffold_toml(tmp_path):
    init(tmp_path)
    add_section(tmp_path, "integrations", question="How do integrations work?")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        names = [s["name"] for s in tomllib.load(f)["section"]]
    assert "integrations" in names


def test_add_section_scaffold_toml_still_valid(tmp_path):
    init(tmp_path)
    add_section(tmp_path, "integrations", question="How do integrations work?", lifecycle="Moderate")
    with (tmp_path / ".cartograph" / "scaffold.toml").open("rb") as f:
        raw = tomllib.load(f)
    s = next(s for s in raw["section"] if s["name"] == "integrations")
    assert s["primary_question"] == "How do integrations work?"
    assert s["lifecycle"] == "moderate"


def test_add_section_updates_cartograph_md(tmp_path):
    init(tmp_path)
    add_section(tmp_path, "integrations", question="How do integrations work?")
    assert "integrations" in (tmp_path / "CARTOGRAPH.md").read_text()


def test_add_section_without_prior_init(tmp_path):
    add_section(tmp_path, "custom", question="Custom?")
    assert (tmp_path / "docs" / "custom" / "INDEX.md").exists()
    assert (tmp_path / ".cartograph" / "scaffold.toml").exists()


# ---------------------------------------------------------------------------
# generate_cartograph_md
# ---------------------------------------------------------------------------

def test_generate_cartograph_md_table_rows(tmp_path):
    sections = [
        Section(name="thesis", path="docs/thesis", primary_question="Why?", lifecycle="stable"),
        Section(name="product", path="docs/product", primary_question="What next?", lifecycle="fast"),
    ]
    md = generate_cartograph_md(sections)
    assert "| docs/thesis/" in md
    assert "Why?" in md
    assert "Stable" in md
    assert "| docs/product/" in md
    assert "Fast" in md


def test_generate_cartograph_md_conventions_section(tmp_path):
    md = generate_cartograph_md([])
    assert "## Conventions" in md
    assert "cartograph reconcile" in md


def test_generate_cartograph_md_all_init_sections(tmp_path):
    init(tmp_path, template="software")
    content = (tmp_path / "CARTOGRAPH.md").read_text()
    for name in ("thesis", "architecture", "quality", "product", "ops"):
        assert name in content


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

def test_cli_init_returns_zero(tmp_path):
    assert main(["init"], repo_path=tmp_path) == 0


def test_cli_init_creates_cartograph_md(tmp_path):
    main(["init"], repo_path=tmp_path)
    assert (tmp_path / "CARTOGRAPH.md").exists()


def test_cli_init_template_minimal(tmp_path):
    main(["init", "--template", "minimal"], repo_path=tmp_path)
    assert (tmp_path / "docs" / "thesis").exists()
    assert not (tmp_path / "docs" / "architecture").exists()


def test_cli_add_section(tmp_path):
    main(["init"], repo_path=tmp_path)
    ret = main(["add-section", "integrations", "--question", "How do integrations work?"], repo_path=tmp_path)
    assert ret == 0
    assert (tmp_path / "docs" / "integrations" / "INDEX.md").exists()
