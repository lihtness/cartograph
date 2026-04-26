# Cartograph — Philosophy and OSS Guidelines

## The Problem Everyone Gets Wrong

Most AI coding assistant systems built around "chat history management" — compression, decay models, summarization pipelines — are solving the wrong problem.

The LLM context constraint is not a memory problem. It is a **capture problem.**

Chat history is an artifact of the conversation, not of the work. It contains the right information buried in noise: false starts, clarifying questions, abandoned approaches, repeated context-setting. Compressing or decaying chat history is an attempt to extract signal from the wrong source.

The signal is the decision — the moment when direction crystallizes. That moment does not need compression. It needs capture into a durable, structured, queryable form.

**The systems that work don't summarize chat history. They bypass it entirely by capturing intent directly.**

---

## The Right Framing

The LLM's context window is not a limitation to engineer around. It is a forcing function that rewards structured thinking.

If the relevant context for a session fits in the window, the session is productive. If it doesn't, the problem is not context size — it is that the project's knowledge is not organized in a queryable form.

The solution is documentation architecture, not context engineering.

---

## What This Means for AI-Augmented Projects

An AI coding agent produces three kinds of artifacts during a session:

| Artifact | Durability | Destination |
|---|---|---|
| Conversation turns | Ephemeral | Discard |
| Decisions, pivots, next steps | Session-scoped | Memory files (hot layer) |
| Stable knowledge, architecture, thesis | Persistent | Structured docs |

The agent captures decisions at the moment they crystallize — not by mining the conversation after the fact, but by writing a memory entry while context is still live. Memory files are the bridge between the ephemeral session and the persistent documentation.

Cartograph's Channel 2 is the automated check that this bridge was actually crossed: session decisions in memory files that never landed in the roadmap are surfaced as gaps.

---

## The Directory-as-Concept Pattern

Documentation organized by time (sprint folders, date-prefixed files) or by feature (one folder per PR) creates a system that is impossible to query. The question "how do we validate signal quality?" has no obvious home. The question "what's the architecture decision on embeddings?" is scattered across three sprint folders.

Organize docs by **concept** — the question each directory answers:

| Concept | Question | Lifecycle |
|---|---|---|
| **Thesis** | Why does this exist? What is the central bet? | Slow — edits signal pivots |
| **Architecture** | How is it built? What are the key technical decisions? | Moderate |
| **Quality** | How do we know it works? What are the validation methods? | Moderate |
| **Product** | What are we building next? What is the roadmap? | Fast |
| **Operations** | How do we run it? Deployment, security, infra. | Mixed |
| **Sales / GTM** | How do we explain and sell it? | User-driven |

When a new doc needs to be written, the question "where does this go?" has a deterministic answer: which concept question does this document answer?

When a new session starts and context needs to be injected, the question "what does the LLM need?" has a deterministic answer: read the thesis for orientation, read the product for current direction, read architecture for technical grounding.

---

## Machine-Readable Intent is a First-Class Primitive

A directory with a README that explains its purpose to a human is not enough. The LLM reading the filesystem needs the same information in a form it can parse and route against.

`CARTOGRAPH.md` at the project root is the LLM navigation file. It is not documentation — it is a structured map of where documentation lives and what each location means. Every directory has a declared `intent`, `lifecycle`, and `primary_question`.

When an AI coding agent starts a session in a Cartograph-structured project, it reads `CARTOGRAPH.md` first. Every routing decision — where to write a new doc, which directory to read for context, where to look for the roadmap — flows from that map.

This is the mechanism that makes the directory structure self-maintaining. The user doesn't have to remember conventions. The agent reads the map.

---

## The Contract

The documentation is not a byproduct of the work. It is the interface between the user's intent and the agent's execution.

The user holds one side: what they want built, what direction the project is headed, what constraints apply, what the core bet is. The agent holds the other side: what it executes, what decisions it makes in ambiguous moments, what code it writes. The docs are the only shared artifact between them.

When the docs are current, the agent executes against the user's real intent. When they are stale, the agent fills gaps with its own assumptions — and the user experiences this as "the AI doesn't understand what I want." The problem is never the AI. The problem is the contract drifted.

**This is the user's responsibility.** Not the tool's. Not the agent's. The user decides what gets captured and when. The agent cannot know that intent changed unless the user says so.

Cartograph makes capture easy: the structure is declared, the routing is unambiguous, and the agent knows exactly where something belongs when asked to document it. The user says "capture this decision" — the agent routes it correctly, formats it consistently, and files it in the right section.

The agent does not write documentation without being asked. Autonomous updates are a source of confusion — the user loses track of what was written, docs accumulate noise, and trust in the content erodes. The user drives capture; the tool makes capture accurate.

The reconciliation report is the safety net. It surfaces gaps between what sessions produced and what the roadmap reflects. The user decides what to do with each flag.

---

## Guidelines for AI-Augmented Project Documentation

These are the conventions Cartograph encodes and the tools enforce. They apply regardless of which AI assistant you use.

**1. Capture decisions at the moment they crystallize, not by post-hoc mining.**
Write the memory entry or update the doc while the session is live. After the session ends, the context is gone. Cartograph's Channel 2 catches what slips, but it is a safety net — not the primary mechanism.

**2. Separate thesis from operations.**
The core hypothesis changes rarely and slowly. If you're editing the thesis directory, you're making a pivot — treat it with that weight. Operations docs (security, deployment, infra) change with scale. Mixing them obscures both.

**3. One canonical source per fact.**
If pricing appears in three docs, all three will drift. Designate one as canonical; the others reference it. The manifest enforces this. Cartograph's Channel 3 flags when the link breaks.

**4. The roadmap is a reconciliation artifact, not a planning document.**
Write roadmap items when work is confirmed. Reconcile against git activity weekly. The roadmap should reflect what is actually being built, not aspirations. Cartograph's Channel 1 surfaces the gap.

**5. Memory files are not permanent.**
A memory file is a session artifact. Its job is to survive the session boundary and inform the next session. Once its content is stable enough to reference repeatedly, it graduates to a live doc and the memory file is marked SUPERSEDED. Memory accumulation without graduation is drift.

**6. Directory structure should evolve with the project, not be designed upfront.**
The scaffold provides sensible defaults. As the project grows into domains not covered by the defaults, new directories are added with declared intent. The structure is never finalized — it is always current.

**7. LLM-friendly organization means queryable organization.**
A well-organized project is one where any question about the system has an obvious place to look. If finding an answer requires reading three directories, the organization has failed. The `primary_question` field in `CARTOGRAPH.md` is the test: can you answer any question by reading one directory?

---

## What Cartograph Is Not

- Not a chat history manager
- Not a summarization or compression tool
- Not a replacement for thinking — it surfaces drift, it does not resolve it
- Not a rigid framework — the scaffold is a starting point, not a constraint
- Not AI-specific — the conventions work for any project where an AI assistant is the primary doc author, regardless of which assistant
