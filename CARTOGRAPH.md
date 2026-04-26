# CARTOGRAPH

docs/ is organized by concept — each section answers one primary question.
When asked to document something, route to the section whose question it answers.
Do not write or update documentation without being asked.

## Document Map

| Directory | Primary Question | Lifecycle |
|-----------|-----------------|-----------|
| docs/foundation/ | What is Cartograph, why is it built this way, and how is it built? | Stable |

## Conventions

- One canonical source per fact. Cross-reference, do not duplicate.
- New directory needed? Add it here with a primary_question before creating files.
- Run `cartograph reconcile` to check structural drift between docs, memory, and git.
