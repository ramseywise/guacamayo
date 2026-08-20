"""Capability advisor resolution — does a capability's advisor actually load?

Ported from galactus `review/phases.py` (GUA-158) alongside the `/fog` skill.
Guacamayo has no `Capability` enum or phase machine, so capabilities are keyed by
name; the resolution logic and its rationale are galactus's.

This is the CROSS-side counterpart to the skill-load check in `driver.py`: a review
dispatch that loads the wrong dimension skill is caught by its ID prefix, but a
capability that dispatches an advisor had no equivalent. Without this, a `/fog` run
whose advisor never loaded is indistinguishable — at the point the result is read —
from one where the advisor ran and found nothing. The check has to happen where the
result is produced, not where it is consumed.
"""

from __future__ import annotations

import re
from pathlib import Path

# Capability name → the agent definition its dispatch names.
CAPABILITY_AGENT: dict[str, str] = {
    "fog": ".claude/agents/fog-advisor.md",
}

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_NAME_RE = re.compile(r"^[ \t]*name:[ \t]*(.*)$")


def _declared_name(frontmatter: str) -> str | None:
    """First `name:` in the frontmatter, or None."""
    for line in frontmatter.splitlines():
        match = _NAME_RE.match(line)
        if match:
            value = match.group(1).strip()
            return value.split()[0] if value.split() else None
    return None


def resolve_capability_agent(capability: str, repo_root: str | Path = ".") -> dict[str, object]:
    """Check that a capability's advisor is loadable *before* it is dispatched.

    Returns the resolution rather than raising: a failure to resolve is a result the
    caller must record as a failed dispatch, not an exception. `reason` is "" when
    resolved and otherwise names what was looked for and why it did not load — a bare
    False sends the caller back to guessing, which is the failure this closes.

    Args:
        capability: Capability name (e.g. "fog").
        repo_root: Repo the agent path is resolved against.

    Returns:
        ``{"resolved": bool, "agent": str | None, "reason": str}``
    """
    agent_path = CAPABILITY_AGENT.get(capability)
    if agent_path is None:
        return {
            "resolved": False,
            "agent": None,
            "reason": (
                f"capability {capability!r} has no registered agent in "
                f"CAPABILITY_AGENT; it cannot be dispatched as a subagent"
            ),
        }

    path = Path(repo_root) / agent_path
    if not path.is_file():
        return {
            "resolved": False,
            "agent": agent_path,
            "reason": f"agent definition not found at {agent_path}",
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {
            "resolved": False,
            "agent": agent_path,
            "reason": (f"{agent_path} has no YAML front matter; the registry cannot register it"),
        }

    # `name:` is what the registry registers under and what the dispatch names. A file
    # that parses but registers under a different name resolves to a *different agent*
    # than the one the caller asked for — the substitution this check exists to catch,
    # one layer subtler than a missing file.
    name = _declared_name(match.group(1))
    expected = Path(agent_path).stem
    if name is None:
        return {
            "resolved": False,
            "agent": agent_path,
            "reason": f"{agent_path} front matter declares no `name:`",
        }
    if name != expected:
        return {
            "resolved": False,
            "agent": agent_path,
            "reason": (
                f"{agent_path} registers as {name!r}, not {expected!r}; "
                f"a dispatch naming {expected!r} would not resolve to this file"
            ),
        }

    return {"resolved": True, "agent": agent_path, "reason": ""}
