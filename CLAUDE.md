# Cartograph — Agent Instructions

## Documentation Structure

docs/ is organized by concept. CARTOGRAPH.md at the project root is the routing map.
Each section declares a primary_question — the question that content in that section answers.

When asked to document something, read CARTOGRAPH.md and route to the section
whose primary_question the content answers.

Do not write or update documentation without being asked.
The user decides what gets captured and when.

## Code Style

- Python 3.11+. Standard library only for core logic.
- Optional deps imported defensively: `try: from cartograph.adapters.embeddings import embed` etc.
- `pathlib.Path` everywhere — no `os.path`.
- `subprocess` for git — no gitpython.
- `argparse` for CLI — no click.
- All channel `run()` functions are pure: take data in, return `list[Flag]`. No side effects.
- Tests use real tmp filesystems and real git repos — no mocks for I/O.

## Key Directories

- `cartograph/` — Python package (channels/, adapters/, cli.py, reconciler.py, reporter.py, scaffold.py)
- `docs/foundation/` — concept, philosophy, scaffold design, build plan
- `tests/` — pytest, real fixture repos

## What NOT to Do

- Do not add features beyond what is asked
- Do not introduce LLM calls anywhere in the tool
- Do not add required dependencies — zero required deps is a hard constraint
- Do not auto-edit user docs — Cartograph surfaces drift, humans resolve it
