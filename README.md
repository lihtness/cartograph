# What
Most AI coding assistant workflows fail at the same point: session decisions don't survive the session. You re-explain context every week. The agent contradicts something decided a month ago. Docs drift from code. Cartograph fixes the infrastructure underneath: a concept-organized doc scaffold your agent can route to accurately, and a reconciliation check that surfaces drift between session work, git activity, and your roadmap. No LLM. No database. Plain markdown and git.

# Why
Everyone building with AI coding agents eventually hits the same wall. The agent is good — but it only knows what's in its context window. Every new session starts cold. Decisions made last Tuesday are gone. The roadmap says one thing, git says another, and somewhere in a memory file from three weeks ago is the pivot that never made it anywhere.

The instinct is to fix this with smarter chat history management — compression, decay models, summarization. That's the wrong abstraction. The problem isn't memory. It's that intent is never captured in a durable, queryable form.

Cartograph is the infrastructure layer that fixes this. A concept-organized scaffold (thesis, architecture, product, ops) that both you and your agent can navigate without thinking. A lightweight reconciliation tool that runs weekly and tells you exactly where session decisions, git activity, and your documentation have drifted apart. No LLM. No database. Zero required dependencies. Plain markdown, a tiny state file, and git.

Your agent doesn't need a better memory system. It needs better-organized knowledge to work from. That's what Cartograph builds.
