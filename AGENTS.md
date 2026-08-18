# AGENTS.md

## Project

Guacamayo is a live instance of the Puffin framework for AI identity,
long-term continuity, persistent workflow state, and AI-assisted
software development.

The repository also contains the review package:
`review/` — deterministic Python backbone plus LLM review dimensions.

## Architecture

Guacamayo separates three concerns:

1. Identity — continuity across sessions.
2. Process — scaffolding work items end-to-end.
3. Execution — performing changes in the codebase.

Metacognition observes these layers and proposes system improvements.

Identity:
- `.sounding/`
- repo-local lifecycle skills

Process:
- plans
- GitHub Issues
- workflow skills

Execution:
- code/design/git/review tooling

Do not collapse these layers without explicit architectural justification.
