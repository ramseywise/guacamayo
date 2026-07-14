---
name: research
description: Multi-agent research orchestration. Use when user asks to research a topic, investigate something, gather information, or says 'research X'. Spawns haiku agents for parallel investigation with optional synthesis.
user-invocable: true
---

# Research - Multi-Agent Investigation

Spawn specialized (haiku) agents to research a topic, then optionally synthesize findings.

## When to Use

- User asks to "research [topic]"
- User wants to investigate or learn about something
- User needs comprehensive information on a topic
- Deep dive requested

## Process

### 1. Quick Reconnaissance

Do preliminary research to understand scope:

**Web topics**: Quick WebSearch to gauge what exists
**Codebase topics**: Quick Grep to see relevant code
**Unclear**: Try both, determine best approach

### 2. Propose Research Plan

Based on findings, propose naturally:

```
I'll research "[topic]"

[2-3 sentences on what you found in recon]

This looks like a [web/codebase/hybrid] topic.

I suggest [N] agents focusing on:
1. [angle 1] - [why]
2. [angle 2] - [why]
[etc.]

Sound good, or want to adjust?
```

**Agent count heuristics**:
- 1-2 aspects: 2-3 agents
- 3-5 angles: 4-5 agents
- Complex topic: 6-8 agents
- Very broad: 8-10 agents (max parallel)

**Wait for confirmation before deploying.**

### 3. Deploy Agents

For each agent, spawn with Task tool:

```python
Task(
  description="Research [angle] for [topic]",
  prompt=f"""
Research {angle} for topic: {topic}

Your mission:
1. {'Web research (WebSearch + WebFetch)' if web else 'Codebase (Read + Grep + Glob)'}
2. Focus on: {angle}
3. Find authoritative sources
4. Write findings to: .sounding/notes/research/{date}_{topic}_{angle}.md
5. Return 200-word summary

Be thorough but concise.
""",
  subagent_type="general-purpose",
  model="haiku"
)
```

### 4. Synthesis (Default: Yes)

After agents complete:

```
All [N] agents complete!

Individual reports in .sounding/notes/research/

I'll synthesize into .sounding/notes/{topic}.md
(individual reports kept for reference).

Proceed? [Y/n]
```

If yes: Read all reports, synthesize, write unified file
If no: Keep individual reports only

## Output

- Individual reports: `.sounding/notes/research/{YYYY-MM-DD}_{topic-slug}_{angle}.md`
- Synthesis: `.sounding/notes/{topic}.md`

## Notes
 
- **Parallel execution**: All agents run simultaneously
- Create `.sounding/notes/research/` directory before spawning

---

**Version**: 2.0.0 (2026-02-03)
**Pattern**: Recon → Propose → Confirm → Deploy → Synthesize
