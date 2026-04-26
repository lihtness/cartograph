# Cartograph — Concept

**Typed documentation graph with deterministic reconciliation for AI-augmented projects.**

No LLM calls. No database. No external services. Plain markdown + git + a tiny state file.

---

## Problem

Three things go stale independently and silently in any project where an AI assistant is a regular collaborator:

1. **Session work gets lost.** A decision, a next step, a pivot happens in a session. Memory files may capture it. The roadmap does not. No mechanism connects them.
2. **Git activity diverges from roadmap.** Files change, features ship, but roadmap items stay marked "next" for weeks. Nobody reconciled.
3. **Docs drift from each other.** A key fact changes in one file; dependents go stale. The dependency is known but nothing enforces it automatically.

All three gaps are manual, periodic, and failure-prone.

---

## What Cartograph Is

A lightweight CLI that:

- Reads a documentation tree, a memory directory, and a git repo directly — no caching layer
- Builds a keyword index and dependency graph in memory at runtime (fresh every run, < 1s at typical scale)
- Runs three deterministic reconciliation channels and emits a markdown report
- Persists only one tiny file between runs: `.cartograph/state.toml` (last_run timestamp + resolved flag IDs)

The source of truth is always the files. There is no derived store to go out of sync.

---

## Design Principles

**No database.** Any derived store creates a sync problem — docs change, the store doesn't know, reports go stale. At typical scale (< 100 docs, < 100 memory files), scanning from scratch on each run takes under a second. For larger adopters, an optional cache can be added behind a flag, but it is never the source of truth.

**No required external tools.** Core logic uses only Python stdlib (`re`, `pathlib`, `subprocess`, `tomllib`). No dependency on external search or NLP tools. This makes the CLI installable via `pip` and runnable on any OS with Python 3.11+.

**Embeddings in Channel 2, optional elsewhere.** Keyword Jaccard with term normalization handles same-session paraphrase variations. It does not handle cross-session concept drift — an AI assistant has no memory of prior phrasing, so "session loop," "WM consolidation trigger," and "working memory cycle" may all refer to the same thing across different memory files. Jaccard between those is zero after normalization; a semantic match catches all three.

AI-generated docs are the best case for embeddings: short, dense, single-concept text — one claim per memory file description, one item per roadmap bullet. This is the regime where semantic similarity is most reliable.

Embeddings apply in Channel 2 only (memory description → roadmap item matching). Channel 1 uses keyword matching (git paths are structured, not semantic). Channel 3 uses keyword matching for declared edges; embeddings optionally improve undeclared edge detection.

Embeddings are an optional dependency — channels degrade gracefully to keyword-only when disabled, with a warning in the report.

**No LLM in any path.** Signal extraction is regex. Matching is set intersection with a configurable threshold. Staleness is timestamp arithmetic. Graph traversal is dict-based BFS. Every result is deterministic and reproducible.

---

## Three Reconciliation Channels

### Channel 1 — Git → Roadmap

**Question:** What changed in code? Is it reflected in the roadmap?

**Mechanism:**
1. `git log --since=<last_run> --name-only` → changed file paths
2. Map paths to keyword terms (directory names + filename stems, stop-word filtered)
3. Look up roadmap items that share terms with changed paths
4. Flag `STALE`: roadmap item marked "next" or "in-progress", no matching git activity in N days
5. Flag `UNTRACKED`: git changes in a domain with no roadmap item covering those terms

Pure set intersection and timestamp comparison. `git` subprocess — cross-platform.

### Channel 2 — Memory → Roadmap

**Question:** What was decided or flagged in sessions? Did it land in the roadmap?

Memory files produced by AI assistants follow a consistent schema, making signal extraction more reliable than parsing free-form human text — the structure is predictable.

**Extraction sources (in priority order):**
1. YAML frontmatter `description` field — already a pre-extracted one-line signal
2. Frontmatter `type` field — only `project` type files carry forward-looking content; `feedback` and `user` types are skipped
3. Body patterns via regex:
   - `Next:`, `Build order:`, `NOT YET BUILT`, `Track \d+\.\d+`, `TODO`, `deferred`, `not yet implemented`
   - Bold status markers: `\*\*(SUPERSEDED|DROPPED|CRITICAL PIVOT|REFRAME)\*\*`
   - Extract a ±60-char window for term context

**Mechanism:**
1. Parse each `memory/*.md` → extract signals (frontmatter `description` + body patterns)
2. Embed signal text → embed roadmap item text (bge-small, recomputed fresh each run)
3. Cosine similarity match: signal → nearest roadmap item(s) above threshold
4. Fallback to keyword Jaccard when embeddings disabled
5. Flag `GAP`: no roadmap item within similarity threshold for a signal
6. Flag `STALE REF`: roadmap references a memory file marked `SUPERSEDED` or `DROPPED`
7. Flag `ALREADY DONE`: signal matches only closed roadmap items — the memory file is stale

Embedding the `description` field is high-signal: it is a one-line, single-claim summary written with intent — not extracted from noise.

This is the channel that catches the "session work forgotten" gap. Memory files are written during sessions with forward-looking content. Channel 2 is the only mechanism that bridges them to the roadmap without manual effort.

### Channel 3 — Manifest → Docs

**Question:** Are declared dependencies still accurate? Are there undeclared dependencies that should be tracked?

**Mechanism:**
1. Parse `.cartograph/manifest.toml` dependency graph
2. Build a heading index from all docs (`H1`/`H2`/`H3` titles and subtitles, slugged to GitHub anchor format)
3. Scan live docs for markdown links and high-frequency shared terms
4. Flag `BROKEN_DEP`: declared edge exists, but the referenced term — or specific heading — no longer appears in the target doc
5. Flag `UNDECLARED`: two docs share terms above threshold with no declared manifest edge

Manifest edges can target a file or a specific section (`to = "docs/arch.md#section-slug"`). When a `heading` field is present, Channel 3 checks the heading index — not just term presence — so a renamed section is caught even if the term still appears elsewhere in the file.

---

## State File

`.cartograph/state.toml` — the only file written between runs. Human-readable, gitignored.

```toml
last_run = "2026-04-26T10:30:00"

[resolved]
# Flag IDs the user has marked resolved — suppressed in future reports
ids = [
  "C2:memory_embedding_strategy:semantic_match",
  "C3:roadmap__sales_plan:pricing",
]
```

Resolved flags are suppressed in reports until the underlying condition changes. No manual cleanup needed.

---

## Architecture

```
cartograph/
├── cartograph/
│   ├── config.py       -- load .cartograph/config.toml, typed dataclass, defaults
│   ├── state.py        -- read/write state.toml, flag ID generation, resolved check
│   ├── reconciler.py   -- orchestrates all channels, filters resolved, writes report
│   ├── reporter.py     -- render flags → markdown report
│   ├── scaffold.py     -- init, add-section, generate CARTOGRAPH.md + CLAUDE.md
│   ├── cli.py          -- cartograph reconcile | resolve | status | init | add-section
│   ├── channels/
│   │   ├── git.py      -- Channel 1: git log → roadmap diff
│   │   ├── memory.py   -- Channel 2: memory signal extraction → roadmap diff
│   │   └── manifest.py -- Channel 3: declared dep graph → actual cross-reference diff
│   └── adapters/
│       ├── markdown.py -- frontmatter parse, link extraction, keyword index builder
│       ├── claude.py   -- Claude memory file format (YAML frontmatter + typed body)
│       ├── git.py      -- git subprocess wrapper (cross-platform)
│       └── embeddings.py -- optional fastembed wrapper (only loaded when enabled)
└── tests/
```

**Adapters are the extension point.** A new AI assistant format (Cursor rules, Copilot context files, Windsurf memories) = a new adapter in `adapters/`. Channels and reconciler are format-agnostic.

**CLI commands:**
- `cartograph reconcile` — run all enabled channels, write report, update state
- `cartograph resolve <flag-id>` — mark a flag resolved in state.toml
- `cartograph status` — show last run timestamp and open flag count
- `cartograph init [--template]` — scaffold a new project
- `cartograph add-section <name>` — add a section to the scaffold

---

## Configuration

`.cartograph/config.toml` at repo root:

```toml
[docs]
root = "docs"
manifest = ".cartograph/manifest.toml"
roadmap = "docs/product/roadmap.md"

[memory]
root = ".claude/projects/<project-hash>/memory"
format = "claude"

[git]
lookback_days = 14

[reconcile]
memory_signal_threshold = 0.25     # Jaccard overlap floor (keyword fallback)
memory_semantic_threshold = 0.72   # cosine similarity floor (embeddings path)
stale_roadmap_days = 14
report_output = "docs/reports/reconcile_{date}.md"

[embeddings]
enabled = false                    # pip install cartograph[embeddings] to enable
model = "BAAI/bge-small-en-v1.5"
channels = ["memory", "manifest"]  # channel 1 (git) uses keyword only

[channels]
git = true
memory = true
manifest = true
```

---

## Output: Reconciliation Report

Plain markdown, written to the configured output path.

```markdown
# Reconciliation Report — 2026-04-26

## Channel 1: Git → Roadmap
- STALE: `roadmap.md` item "embedding adapter" — no git activity in 18 days
- UNTRACKED: changes to `src/channels/memory.py` have no roadmap entry

## Channel 2: Memory → Roadmap
- GAP: `memory_embedding_strategy.md` signals "next build" (embedding integration) — not in roadmap
- GAP: `memory_adapter_design.md` signals "Claude adapter not yet implemented" — not in roadmap
- STALE REF: `roadmap.md` references `memory_v1_design.md` — that file is marked SUPERSEDED

## Channel 3: Manifest → Docs
- BROKEN DEP: manifest declares `roadmap.md → sales.md` (pricing) but term "pricing" no longer in roadmap section 3
- UNDECLARED: `architecture.md` and `build_plan.md` share 12 terms with no manifest edge

## Resolved (suppressed)
- C2:memory_embedding_strategy:semantic_match — marked resolved 2026-04-19
```

Human reviews, decides, updates. Cartograph never edits docs.

---

## Adopter Integration

**What Cartograph catches that content audits miss:**
- Session decisions that never landed in roadmap (Channel 2 — the primary gap)
- Git activity with no roadmap coverage (Channel 1)
- Dependency edges that have silently broken (Channel 3)

**What content audits catch that Cartograph doesn't:**
- Writing quality, stale vocabulary, tone drift, within-doc consistency

Complementary, not competing. Cartograph is structural; content audits are editorial.

---

## OSS Position

**Closest prior art:** Hot-memory + vault-files + cron systems (e.g., the Hermes/Obsidian pattern). Significantly flatter: no dependency graph, no canonical source enforcement, no memory → roadmap reconciliation.

**What Cartograph adds that doesn't exist publicly:**
1. Typed dependency graph between docs (not just backlinks)
2. Memory → roadmap reconciliation (Channel 2) — the novel channel
3. Deterministic, no-LLM, no-DB design
4. Adapter pattern for multiple AI assistant memory formats
5. `resolve` workflow: flag suppression without deleting information

**Target user:** Developer whose documentation is AI-generated — produced by Claude, Cursor, or another assistant and captured as markdown — where session decisions, docs, and code need to stay structurally aligned without manual reconciliation overhead.

Most doc tools assume human authorship. Cartograph assumes AI authorship with human direction. That assumption unlocks the structured adapter design: AI assistants emit consistent, parseable formats that reward structured extraction.
