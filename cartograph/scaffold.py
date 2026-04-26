from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Section:
    name: str
    path: str
    primary_question: str
    lifecycle: str
    intent: str = ""
    required: bool = False


_SECTION_DEFS: dict[str, Section] = {
    "thesis": Section(
        name="thesis", path="docs/thesis",
        primary_question="Why does this exist? What is the core bet?",
        lifecycle="stable",
        intent="Core hypothesis, problem statement, domain thesis, central bets.\nChanges here indicate a project pivot — treat with that weight.",
        required=True,
    ),
    "architecture": Section(
        name="architecture", path="docs/architecture",
        primary_question="How is it built? What are the key technical decisions?",
        lifecycle="moderate",
        intent="System design, component decisions, data flow, technical constraints.\nDocuments the current architecture, not aspirational state.",
        required=True,
    ),
    "quality": Section(
        name="quality", path="docs/quality",
        primary_question="How do we know it works? What are the validation methods?",
        lifecycle="moderate",
        intent="Validation approach, signal quality, confidence measures, known gaps.",
        required=False,
    ),
    "product": Section(
        name="product", path="docs/product",
        primary_question="What are we building next? What is the current roadmap?",
        lifecycle="fast",
        intent="Roadmap, requirements, feature specs, build order.\nShould reflect actual git activity — reconcile weekly.",
        required=True,
    ),
    "ops": Section(
        name="ops", path="docs/ops",
        primary_question="How do we run it? Deployment, security, infra, runbooks.",
        lifecycle="mixed",
        intent="Operational details: deployment, security design, infra, monitoring.\nSeparate from architecture — ops is how you run it, not how it is designed.",
        required=False,
    ),
    "sales": Section(
        name="sales", path="docs/sales",
        primary_question="How do we explain and sell it? Positioning, pricing, outreach.",
        lifecycle="fast",
        intent="Go-to-market: positioning, ICP, pricing, outreach scripts, one-pagers.\nUser-guided — only scaffold if the project has a GTM dimension.",
        required=False,
    ),
}

_TEMPLATES: dict[str, list[str]] = {
    "software": ["thesis", "architecture", "quality", "product", "ops"],
    "product":  ["thesis", "architecture", "product", "sales", "ops"],
    "research": ["thesis", "architecture", "quality"],
    "minimal":  ["thesis", "product"],
}
_DEFAULT_TEMPLATE = "software"

_CLAUDE_SECTION = """\
## Session Start

Run `cartograph context` at the start of each session.
It outputs current work, reconcile status, and documentation sections — everything needed to orient.
Pull additional context on demand: read a section's INDEX.md before working in it,
specific files only when the task requires them.
Do not write or update documentation without being asked.
"""

_CLAUDE_DEDUP_MARKER = "## Session Start"


def init(repo_path: Path, template: str | None = None) -> None:
    template = template or _DEFAULT_TEMPLATE
    section_names = _TEMPLATES.get(template, _TEMPLATES[_DEFAULT_TEMPLATE])
    sections = [_SECTION_DEFS[n] for n in section_names if n in _SECTION_DEFS]

    cartograph_dir = repo_path / ".cartograph"
    cartograph_dir.mkdir(parents=True, exist_ok=True)

    _write_scaffold_toml(repo_path, sections)

    for fname in ("manifest.toml", "config.toml"):
        p = cartograph_dir / fname
        if not p.exists():
            p.write_text("")

    for section in sections:
        section_dir = repo_path / section.path
        section_dir.mkdir(parents=True, exist_ok=True)
        _write_index_md(section_dir / "INDEX.md", section)

    (repo_path / "CARTOGRAPH.md").write_text(generate_cartograph_md(sections))
    _update_claude_md(repo_path / "CLAUDE.md")


def add_section(repo_path: Path, name: str, question: str = "", lifecycle: str = "Stable") -> None:
    scaffold_path = repo_path / ".cartograph" / "scaffold.toml"
    scaffold_path.parent.mkdir(parents=True, exist_ok=True)

    section_path = f"docs/{name}"
    block = (
        f'\n[[section]]\n'
        f'name = "{name}"\n'
        f'path = "{section_path}"\n'
        f'primary_question = "{_escape(question)}"\n'
        f'lifecycle = "{lifecycle.lower()}"\n'
        f'intent = ""\n'
        f'required = false\n'
    )
    with scaffold_path.open("a") as f:
        f.write(block)

    section = Section(name=name, path=section_path, primary_question=question, lifecycle=lifecycle.lower())
    section_dir = repo_path / section_path
    section_dir.mkdir(parents=True, exist_ok=True)
    _write_index_md(section_dir / "INDEX.md", section)

    sections = _load_sections(repo_path)
    (repo_path / "CARTOGRAPH.md").write_text(generate_cartograph_md(sections))


def generate_cartograph_md(sections: list[Section]) -> str:
    rows = "\n".join(
        f"| {s.path}/ | {s.primary_question} | {s.lifecycle.capitalize()} |"
        for s in sections
    )
    return (
        "# CARTOGRAPH\n\n"
        "docs/ is organized by concept — each section answers one primary question.\n"
        "When asked to document something, route to the section whose question it answers.\n"
        "Do not write or update documentation without being asked.\n\n"
        "## Document Map\n\n"
        "| Directory | Primary Question | Lifecycle |\n"
        "|-----------|-----------------|----------|\n"
        f"{rows}\n\n"
        "## Conventions\n\n"
        "- One canonical source per fact. Cross-reference, do not duplicate.\n"
        "- Memory files graduate to docs when stable. Mark SUPERSEDED when promoted.\n"
        "- Roadmap in docs/product/ should match git activity. "
        "Run `cartograph reconcile` weekly.\n"
        "- New directory needed? Add it here with a primary_question before creating files.\n"
    )


def _load_sections(repo_path: Path) -> list[Section]:
    path = repo_path / ".cartograph" / "scaffold.toml"
    if not path.exists():
        return []
    with path.open("rb") as f:
        raw = tomllib.load(f)
    return [
        Section(
            name=s.get("name", ""),
            path=s.get("path", ""),
            primary_question=s.get("primary_question", ""),
            lifecycle=s.get("lifecycle", "stable"),
            intent=s.get("intent", ""),
            required=s.get("required", False),
        )
        for s in raw.get("section", [])
    ]


def _write_scaffold_toml(repo_path: Path, sections: list[Section]) -> None:
    path = repo_path / ".cartograph" / "scaffold.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['[scaffold]', 'version = "1"', 'docs_root = "docs"', ""]
    for s in sections:
        lines += [
            "[[section]]",
            f'name = "{s.name}"',
            f'path = "{s.path}"',
            f'primary_question = "{_escape(s.primary_question)}"',
            f'lifecycle = "{s.lifecycle}"',
            f'intent = "{_escape(s.intent)}"',
            f'required = {"true" if s.required else "false"}',
            "",
        ]
    path.write_text("\n".join(lines))


def _write_index_md(path: Path, section: Section) -> None:
    if path.exists():
        return
    title = section.name.replace("-", " ").replace("_", " ").title()
    lines = [f"# {title}", "", f"> {section.primary_question}"]
    if section.intent:
        lines += ["", section.intent.strip()]
    path.write_text("\n".join(lines) + "\n")


def _update_claude_md(path: Path) -> None:
    if path.exists():
        existing = path.read_text()
        if _CLAUDE_DEDUP_MARKER not in existing:
            path.write_text(existing.rstrip() + "\n\n" + _CLAUDE_SECTION)
    else:
        path.write_text(_CLAUDE_SECTION)


def _escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
         .replace('"', '\\"')
         .replace("\n", "\\n")
         .replace("\t", "\\t")
    )
