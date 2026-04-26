# Cartograph

Documentation infrastructure for AI-augmented projects. Structured capture, drift detection, no LLM.

---

## What

Cartograph is documentation infrastructure for AI-augmented projects. It gives your docs a concept-organized structure your agent can navigate without re-explanation, and a weekly reconciliation check that surfaces where session decisions, git activity, and documentation have drifted apart.

No LLM. No database. Zero required dependencies. Plain markdown, a tiny state file, and git.

## Why

Every session starts cold. The agent is capable — but it only knows what is in its context window right now. Decisions made last week are gone. The tracking file says one thing, git says another, and the memory note with the pivot that changed everything is connected to nothing.

The obvious fix is better memory — compression, summarization, smarter retrieval. That is the wrong model. The problem is not that the agent forgets. It is that intent was never captured in a durable, structured form to begin with.

Cartograph is the layer underneath. Docs organized by concept, each section answering one declared question at a stated lifecycle. A session brief generated on demand — current work, drift status, orientation — so the agent can continue rather than restart. A reconcile check that runs weekly and tells you exactly what has gone stale.

The agent does not need a better memory system. It needs better-organized knowledge to start from.

---

## Commands

### `cartograph context`

**When:** Start of every session. Feed the output to your agent to orient without re-explanation.

```bash
cartograph context
```

Shows open work items (hot layer), last reconcile status, and documentation sections (cold layer).
If you have Claude Code, `/cartograph` runs this as a slash command and interprets the output for you.

---

### `cartograph reconcile`

**When:** Weekly. Before a sprint. After a large batch of commits. Whenever you suspect drift.

```bash
cartograph reconcile
```

Runs all four channels, writes a dated report to `docs/reports/`, and updates state. Check the report
for flags — STALE items have been open with no git activity, GAP items exist in memory but not in
your tracking file, BROKEN_DEP edges point at missing docs.

---

### `cartograph resolve`

**When:** After reading a reconcile report and deciding a flag is noise, already handled, or not worth
tracking.

```bash
cartograph resolve C1:auth:stale
```

Suppresses the flag in all future reports. The ID comes from the reconcile output. Resolved flags are
listed in a separate section of the report so the decision is auditable — they don't disappear.

---

### `cartograph status`

**When:** Quick check without running a full reconcile — to see when you last ran it and how many
flags you've resolved.

```bash
cartograph status
# Last run:       2026-04-20T09:14:00+00:00
# Resolved flags: 3
```

---

### `cartograph init`

**When:** Starting a new project from scratch. Not for projects that already have a doc structure —
use a manual `.cartograph/scaffold.toml` instead (see Configuration).

```bash
cartograph init                        # software template (default)
cartograph init --template minimal     # thesis + product only — good for early-stage
cartograph init --template research    # thesis + architecture + quality
cartograph init --template product     # includes sales section
```

Creates the full scaffold: `.cartograph/`, `docs/` sections with `INDEX.md` files, `CARTOGRAPH.md`
routing map, and appends session-start instructions to `CLAUDE.md`.

---

### `cartograph add-section`

**When:** A new concern area emerges that doesn't fit existing sections — integrations, legal,
data, security as a standalone domain.

```bash
cartograph add-section integrations \
  --question "How do integrations work?" \
  --lifecycle fast
```

Creates `docs/integrations/INDEX.md`, appends to `scaffold.toml`, regenerates `CARTOGRAPH.md`.
`--lifecycle` defaults to `stable` if omitted.

---

### `cartograph track close`

**When:** `current.md` has accumulated completed items and is getting long. Channel 4 will flag
this automatically once the count hits `close_threshold` (default 10).

```bash
cartograph track close                    # seals to current ISO week, e.g. 2026-W18
cartograph track close --period 2026-W18  # explicit period label
```

All `- [x]` items move from `current.md` to `docs/track/2026-W18.md`. Open items stay. Running
again for the same period appends — sealed files accumulate the full history of what was done.

---

### `cartograph manifest add-edge`

**When:** You write a doc that depends on another — a roadmap item that refers to an architecture
decision, a sales doc that depends on pricing, an ops runbook that assumes a specific deployment
model. Declare it so the reconciler can catch breakage.

```bash
cartograph manifest add-edge \
  --from docs/product/roadmap.md \
  --to docs/architecture/decisions.md \
  --type depends_on \
  --term "embedding adapter"

# Point to a specific section heading within the target file
cartograph manifest add-edge \
  --from docs/product/roadmap.md \
  --to "docs/architecture/decisions.md#embedding-adapter" \
  --type depends_on \
  --term "embedding adapter" \
  --heading "Embedding Adapter"
```

`--term` is the concept being referenced. `--heading` pins to a specific section anchor — if that
heading is renamed or removed, the reconciler raises a BROKEN_DEP flag.

---

### `cartograph manifest add-fact`

**When:** A fact is referenced in multiple docs and you want to enforce a single canonical source.
Pricing, tagline, API cost, ICP definition — anything that drifts when updated in one place but
not others.

```bash
cartograph manifest add-fact \
  --key pricing \
  --canonical docs/thesis/pricing.md \
  --duplicate docs/product/roadmap.md \
  --duplicate docs/ops/runbook.md
```

The reconciler will flag any duplicate that contradicts the canonical source.

---

## Install

```bash
pip install cartograph
```

Or from source:

```bash
pip install -e .
```

Optional embedding support (enables semantic matching in channels 2 and 3):

```bash
pip install "cartograph[embeddings]"
```

---

## Quick start

```bash
# Scaffold a new project (default: software template)
cartograph init

# Or choose a template
cartograph init --template minimal    # thesis + product only
cartograph init --template research   # thesis + architecture + quality
cartograph init --template product    # includes sales section

# Orient at session start
cartograph context

# Run drift detection
cartograph reconcile

# Check status
cartograph status
```

---

## Session start

```bash
cartograph context
```

Outputs a session brief — current work, reconcile status, documentation sections. Feed it to your agent at the start of a session to orient without manual explanation.

Example output:

```
# Project Context — 2026-04-26

## Current work
- [ ] embedding integration
- [ ] manifest channel

_2 closed item(s) pending seal — `cartograph track close`_

## Reconcile
Last run: 2026-04-20  ·  3 resolved flag(s)
Run `cartograph reconcile` for full drift report.

## Orientation
thesis        stable    — Why does this exist? What is the core bet?
architecture  moderate  — How is it built? What are the key technical decisions?
quality       moderate  — How do we know it works?
product       fast      — What are we building next?
ops           fast      — How do we run it?
```

`current.md` is the hot layer — open items tell the agent exactly where work is. The orientation section is the cold layer — pulled once, rarely changes. Nothing is injected automatically; `cartograph context` is on-demand.

`cartograph init` appends one line to `CLAUDE.md`: *run `cartograph context` at session start*. No structural explanation required.

---

## Scaffold structure

`cartograph init` creates the following layout:

```
.cartograph/
  scaffold.toml    # section definitions and metadata
  manifest.toml    # declared dependency edges and canonical facts
  config.toml      # optional overrides (not created until needed)
  state.toml       # last-run timestamp and resolved flag IDs

CARTOGRAPH.md      # routing map — one table row per section
CLAUDE.md          # agent instructions (appended; existing file preserved)

docs/
  thesis/
    INDEX.md       # Why does this exist? What is the core bet?
  architecture/
    INDEX.md       # How is it built? What are the key technical decisions?
  quality/
    INDEX.md       # How do we know it works? What are the validation methods?
  product/
    INDEX.md       # What are we building next? What is the current roadmap?
  ops/
    INDEX.md       # How do we run it? Deployment, security, infra, runbooks.
```

Each `INDEX.md` declares a `primary_question` — the question that content in that section answers. `CARTOGRAPH.md` is the routing map your agent reads to decide where to put or find information.

### Work tracking

The reconciler watches `docs/track/current.md` for live work items. Create it manually:

```markdown
# Track

- [ ] embedding integration
- [ ] manifest channel
- [x] config module
```

Open items (`- [ ]`) are checked against git activity. Closed items (`- [x]`) accumulate until you seal them.

### Add a custom section

```bash
cartograph add-section integrations \
  --question "How do integrations work?" \
  --lifecycle fast
```

This creates `docs/integrations/INDEX.md`, appends the section to `scaffold.toml`, and regenerates `CARTOGRAPH.md`. `--lifecycle` defaults to `stable` if omitted.

---

## Lifecycle

Each section has a `lifecycle` value that describes how frequently its content changes. This appears in `CARTOGRAPH.md` and is recorded in `scaffold.toml`.

| Lifecycle | Meaning |
|-----------|---------|
| `stable`  | Changes indicate a project pivot. Treat edits with that weight. |
| `moderate` | Evolves with the design. Reconcile monthly. |
| `fast`    | Reflects active work. Should match git activity. Reconcile weekly. |
| `mixed`   | Contains both stable policy and fast-changing operational details. |

The default template assigns:
- **thesis** → stable
- **architecture**, **quality** → moderate
- **product**, **ops** → fast (ops is mixed)

---

## Reconciliation

Run `cartograph reconcile` to check four channels and write a report to `docs/reports/`.

### Channel 1 — Git → Track

Compares recent git commits against open items in `docs/track/current.md`.

| Flag | Meaning |
|------|---------|
| `STALE` | Open item with no matching git activity in the lookback window |
| `UNTRACKED` | Git change with no corresponding tracking item |

### Channel 2 — Memory → Track

Reads Claude memory files (`.claude/projects/*/memory/*.md`) and checks them against `current.md`.

| Flag | Meaning |
|------|---------|
| `GAP` | Memory signal describes something with no matching tracking item |
| `ALREADY_DONE` | Memory signal matches only a closed item — memory may be stale |
| `STALE_REF` | Tracking file references a memory file that is marked SUPERSEDED or DROPPED |

### Channel 3 — Manifest → Docs

Validates declared edges in `.cartograph/manifest.toml`.

| Flag | Meaning |
|------|---------|
| `BROKEN_DEP` | A declared edge points to a missing file or heading |
| `UNDECLARED` | Two doc files are closely related but have no declared edge |

### Channel 4 — Track Housekeeping

| Flag | Meaning |
|------|---------|
| `TRACK_CLOSE` | `current.md` has accumulated too many closed items — run `cartograph track close` |

---

## Resolving flags

```bash
# Run reconciliation and see the report path
cartograph reconcile

# Suppress a specific flag (it won't appear in future reports)
cartograph resolve C1:auth:stale

# Show last run time and resolved flag count
cartograph status
```

Flag IDs are stable across runs for the same source + term. Resolving one persists to `.cartograph/state.toml`.

---

## Track: sealing closed items

When `current.md` accumulates closed items, seal them into a dated archive file:

```bash
# Seal to current ISO week (e.g. docs/track/2026-W18.md)
cartograph track close

# Seal to a specific period
cartograph track close --period 2026-W18
```

The sealed file is immutable history. All `- [x]` items move from `current.md` to `docs/track/<period>.md`. Open items stay in place. Running close again for the same period appends to the existing sealed file.

---

## Manifest

Declare dependencies between docs explicitly so the reconciler can validate them:

```bash
# Declare that roadmap depends on an architecture decision
cartograph manifest add-edge \
  --from docs/product/roadmap.md \
  --to docs/architecture/decisions.md \
  --type depends_on \
  --term "embedding adapter"

# Point to a specific section heading within the target file
cartograph manifest add-edge \
  --from docs/product/roadmap.md \
  --to "docs/architecture/decisions.md#embedding-adapter" \
  --type depends_on \
  --term "embedding adapter" \
  --heading "Embedding Adapter"

# Declare a canonical source for a fact
cartograph manifest add-fact \
  --key pricing \
  --canonical docs/thesis/pricing.md \
  --duplicate docs/product/roadmap.md \
  --duplicate docs/ops/runbook.md
```

---

## Configuration

Override defaults in `.cartograph/config.toml`:

```toml
[git]
lookback_days = 7

[track]
close_threshold = 5   # suggest seal when current.md has >= 5 closed items

[reconcile]
stale_roadmap_days = 21

[channels]
memory = false        # disable channel 2
```

---

## Documentation

- [Concept](docs/foundation/concept.md) — what Cartograph is, the three reconciliation channels, architecture
- [Philosophy](docs/foundation/philosophy.md) — why it's built this way, OSS guidelines
- [Scaffold Design](docs/foundation/scaffold.md) — how the directory scaffold works, CARTOGRAPH.md format
- [Build Plan](docs/foundation/build_plan.md) — implementation breakdown, design decisions, estimated scope

## License

MIT
