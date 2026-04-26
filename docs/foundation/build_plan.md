# Cartograph — Build Plan

## What We Are Building

A Python CLI tool. Not an agent. Not a service.

Cartograph:
- Reads files via `pathlib`
- Calls `git` via `subprocess`
- Does set arithmetic, regex extraction, timestamp comparison
- Optionally generates embedding vectors (not reasoning — float arrays)
- Writes a markdown report

No LLM. No autonomous decisions. No action without being invoked. The tool serves agents; it is not one.

---

## Repository Structure

```
cartograph/
├── CARTOGRAPH.md            ← this repo uses its own scaffold
├── CLAUDE.md                ← routing contract for agents working on this repo
├── docs/
│   └── foundation/          ← concept, philosophy, scaffold, build plan
├── cartograph/
│   ├── __init__.py
│   ├── config.py
│   ├── state.py
│   ├── reconciler.py
│   ├── reporter.py
│   ├── scaffold.py
│   ├── cli.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── markdown.py
│   │   ├── claude.py
│   │   ├── git.py
│   │   └── embeddings.py    ← only imported when [embeddings] enabled = true
│   └── channels/
│       ├── __init__.py
│       ├── memory.py
│       ├── git.py
│       └── manifest.py
├── tests/
│   ├── conftest.py
│   ├── test_adapters.py
│   ├── test_channel_memory.py
│   ├── test_channel_git.py
│   ├── test_channel_manifest.py
│   └── test_scaffold.py
├── pyproject.toml
└── README.md
```

---

## Dependencies

```toml
[project]
name = "cartograph"
requires-python = ">=3.11"
dependencies = []                         # zero required — stdlib only

[project.optional-dependencies]
embeddings = ["fastembed>=0.3"]           # Channel 2 semantic matching
dev = ["pytest>=8", "pytest-cov"]

[project.scripts]
cartograph = "cartograph.cli:main"
```

Zero required dependencies. `gitpython` rejected — raw subprocess git is sufficient and avoids a heavy transitive dep tree. `fastembed` opt-in via `pip install cartograph[embeddings]`.

---

## Design Decisions

### Manifest Format

The human-readable `docs_manifest.md` pattern (free-form markdown) is not parseable reliably across adopters. Cartograph introduces `.cartograph/manifest.toml` as the machine-readable dependency graph. The human-readable companion can coexist or be dropped — Channel 3 reads only `manifest.toml`.

```toml
# .cartograph/manifest.toml

[[edge]]
from = "docs/product/roadmap.md"
to = "docs/architecture/decisions.md"
type = "depends_on"
term = "embedding adapter"    # the specific concept that must stay in sync

# Section-level edge: `heading` pins the dependency to a specific H1/H2/H3 in the target.
# Channel 3 flags BROKEN_DEP if that heading is removed or renamed.
[[edge]]
from = "docs/product/roadmap.md"
to = "docs/architecture/decisions.md#embedding-adapter-design"
type = "depends_on"
term = "embedding adapter"
heading = "Embedding Adapter Design"   # exact heading text; slug used for matching

[[edge]]
from = "docs/sales/pricing.md"
to = "docs/sales/outreach.md"
type = "canonical_for"
term = "pricing tiers"

[[fact]]
key = "pricing"
canonical = "docs/sales/pricing.md"
duplicates = ["docs/sales/outreach.md", "docs/product/roadmap.md"]
```

CLI: `cartograph manifest add-edge` and `cartograph manifest add-fact` append to this file. Users can also edit it directly.

### Heading Index

`adapters/markdown.py` builds a heading index alongside the keyword index. This enables section-level dependency tracking in Channel 3.

```python
@dataclass
class Heading:
    path: Path
    level: int      # 1 = H1, 2 = H2, 3 = H3
    text: str       # raw heading text, e.g. "Embedding Adapter Design"
    slug: str       # URL-style slug, e.g. "embedding-adapter-design"
    line: int       # line number in the file

def extract_headings(path: Path) -> list[Heading]: ...
def build_heading_index(paths: list[Path]) -> dict[str, list[Heading]]:
    # returns {path_str: [Heading, ...]} for fast Channel 3 lookup
```

**How Channel 3 uses it:**
- `manifest.toml` edge with a `heading` field → Channel 3 looks up the slug in the heading index for the target file
- If the heading is absent: `BROKEN_DEP` flag (heading was removed or renamed)
- `extract_headings` is also used to populate the keyword index with heading text at higher weight than body text — headings are the author's chosen names for concepts

**Heading slug format:** lowercase, spaces and punctuation → hyphens, strip leading/trailing hyphens. Same convention as GitHub Markdown anchors, so `#heading` fragments in markdown links resolve correctly.

### Roadmap Item Parsing

The roadmap file is declared in config. Items are identified by two conventions:

**Status markers (Channel 1 — staleness detection):**
- Open: `[ ]`, `next`, `in-progress`, `TODO`, `planned`
- Closed: `[x]`, `done`, `complete`, `shipped`
- Both are configurable regex in `config.toml`

**Term extraction (Channel 2 — memory signal matching):**
All items are indexed for terms regardless of status. If a memory signal matches only closed items, it is flagged `ALREADY DONE` — the memory file is stale, not a gap.

### Flag ID Scheme

```
C{channel}:{source_stem}:{term_slug}
```

Examples:
- `C1:memory_py:embedding_adapter` — Channel 1, git change to memory.py, term "embedding adapter"
- `C2:memory_embedding_strategy:semantic_match` — Channel 2, memory file, signal term
- `C3:roadmap__decisions:embedding_adapter` — Channel 3, edge from roadmap to decisions

Terms are slugified: lowercase, spaces→underscore, stop words removed, max 3 tokens. On collision, numeric suffix appended.

### Keyword Index

Simple term frequency. No tf-idf. The corpus is small and terminology is consistent (AI-generated docs).

```python
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "this", "that", "these", "those", "it", "its", "we", "our",
    "not", "no", "and", "or", "but", "if", "as", "so",
})

def normalize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z][a-z0-9]*", text.lower())
    stemmed = {t.rstrip("s") for t in tokens}
    return stemmed - STOP_WORDS
```

Jaccard: `len(a & b) / len(a | b)`. Default threshold: 0.25.

### Embedding Implementation

```python
# cartograph/adapters/embeddings.py
from fastembed import TextEmbedding
import numpy as np

_model = None

def embed(texts: list[str]) -> np.ndarray:
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return np.array(list(_model.embed(texts)))

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

Model loads once per run. All Channel 2 texts embedded in a single batch call. No caching between runs — at typical scale (< 200 texts), embedding takes 2–4 seconds total.

### Flag Dataclass

```python
@dataclass
class Flag:
    id: str        # C2:memory_embedding_strategy:semantic_match
    channel: int   # 1 | 2 | 3
    type: str      # GAP | STALE | UNTRACKED | BROKEN_DEP | UNDECLARED | ALREADY_DONE | STALE_REF
    source: str    # file path that triggered the flag
    detail: str    # human-readable one-line description
    resolved: bool # from state.toml
```

---

## Build Order

Each phase is independently testable before moving to the next.

### Phase 1 — Config and State

`config.py` — load `.cartograph/config.toml`, apply defaults, expose typed dataclass.
`state.py` — read/write `.cartograph/state.toml`, generate flag IDs, check resolved.

Tests: unit tests with tmp config files. No git, no docs needed.

### Phase 2 — Adapters

`adapters/markdown.py`:
- `parse_frontmatter(path) → dict`
- `extract_links(path) → list[str]`
- `extract_headings(path) → list[Heading]`
- `build_keyword_index(paths) → dict[str, set[str]]`
- `build_heading_index(paths) → dict[str, list[Heading]]`

`adapters/claude.py`:
- `parse_memory_file(path) → MemorySignal`
- Signal extraction: frontmatter `description` + body regex patterns

`adapters/git.py`:
- `git_log_since(repo_path, since_iso) → list[GitEvent]`
- `map_path_to_domain(path, scaffold) → str | None`

Tests: fixture files — sample markdown, sample memory files, small git repo via subprocess.

### Phase 3 — Channels

Each channel: `run(config, ...) -> list[Flag]`

`channels/memory.py` — Channel 2: memory signals → roadmap diff
`channels/git.py` — Channel 1: git events → roadmap diff
`channels/manifest.py` — Channel 3: manifest edges → doc cross-reference diff

Tests: unit tests with synthetic signals and indexes. No filesystem.

### Phase 4 — Reconciler and Reporter

`reconciler.py` — orchestrates channels, filters resolved flags, returns `ReconcileResult`.
`reporter.py` — renders `ReconcileResult` to markdown, writes to configured path.

Tests: integration test — fixture project (tmp git repo + docs + memory files), run reconcile, check report output.

### Phase 5 — CLI

`cli.py` using `argparse` (stdlib):

```
cartograph reconcile          → run all channels, write report, update state
cartograph resolve <flag-id>  → mark flag resolved in state.toml
cartograph status             → show last run, open flag count
cartograph init [--template]  → scaffold new project
cartograph add-section        → add section to scaffold
cartograph manifest add-edge  → append edge to manifest.toml
cartograph manifest add-fact  → append fact to manifest.toml
```

### Phase 6 — Scaffold

`scaffold.py`:
- `init(template, discover)` — create dirs, write CARTOGRAPH.md, CLAUDE.md, scaffold.toml
- `add_section(name, question, lifecycle)` — append to scaffold.toml, create dir + INDEX.md, regenerate CARTOGRAPH.md
- `generate_cartograph_md(scaffold_toml) → str`

---

## Testing Strategy

No mocks for filesystem or git. Fixtures create real temporary structures:

```python
@pytest.fixture
def fixture_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path)
    (tmp_path / "docs/thesis").mkdir(parents=True)
    (tmp_path / "docs/product").mkdir(parents=True)
    # write sample memory files, roadmap, config.toml
    return tmp_path
```

3–5 scenarios per channel covering every flag type it emits.

---

## Estimated Scope

| Phase | Files | Est. Lines |
|---|---|---|
| Config + State | 2 | ~100 |
| Adapters | 4 | ~220 |
| Channels | 3 | ~200 |
| Reconciler + Reporter | 2 | ~100 |
| CLI | 1 | ~100 |
| Scaffold | 1 | ~120 |
| Tests | 6 | ~350 |
| **Total** | **19** | **~1190** |

---

## Out of Scope for v1

- Web UI
- Database or persistent cache
- Background daemon or watch mode
- LLM calls of any kind
- GitHub Actions integration
- Plugin system beyond the adapter pattern
- Automatic doc editing
