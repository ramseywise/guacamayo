"""Claude Code session JSONL parser — session-parsing subset vendored from librarian.

Provenance: ramseywise/librarian shared/parser.py @ aa3166e (LIB-110 layout;
pre-110 home tools/cartographer/parser.py). Copied for GUA-93: the ten-symbol
surface factstore needs (cost constants → parse_session + note-frontmatter
helpers), without librarian's aggregate/LLM-report path.

Drift guard: both repos parse the same ~/.claude/projects/ JSONL daily, so a
format change breaks loudly in both the same day. Librarian's copy carries the
matching pointer back to this file.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# Relative cost weights: multiples of the input-token price (Anthropic cache pricing).
# "cost units" throughout = token counts weighted by these, so percentages reflect
# spend, not raw message counts. Output priced at ~5x input across Claude models.
_COST_INPUT = 1.0
_COST_CACHE_WRITE = 1.25
_COST_CACHE_READ = 0.1
_COST_OUTPUT = 5.0

# Effective request context = input + cache_read + cache_creation tokens
_CONTEXT_BUCKETS = ("<50k", "50-100k", "100-150k", ">150k")


def _context_bucket(context_tokens: int) -> str:
    if context_tokens < 50_000:
        return "<50k"
    if context_tokens < 100_000:
        return "50-100k"
    if context_tokens < 150_000:
        return "100-150k"
    return ">150k"


def _usage_cost(usage: dict[str, Any]) -> float:
    """Cost of one request in input-price-relative units."""
    return (
        usage.get("input_tokens", 0) * _COST_INPUT
        + usage.get("cache_creation_input_tokens", 0) * _COST_CACHE_WRITE
        + usage.get("cache_read_input_tokens", 0) * _COST_CACHE_READ
        + usage.get("output_tokens", 0) * _COST_OUTPUT
    )


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------


def iter_sessions(projects_dir: Path) -> list[dict[str, Any]]:
    """Return one dict of stats per .jsonl session file."""
    sessions: list[dict[str, Any]] = []
    for jsonl in sorted(projects_dir.rglob("*.jsonl")):
        if "/subagents/" in str(jsonl):
            continue
        session = parse_session(jsonl)
        if session:
            sessions.append(session)
    return sessions


def iter_subagent_sessions(projects_dir: Path) -> list[dict[str, Any]]:
    """Parse subagent transcripts, each attributed to its parent session.

    Layout: <projects>/<project>/<session-id>/subagents/agent-*.jsonl
    """
    subs: list[dict[str, Any]] = []
    for jsonl in sorted(projects_dir.rglob("*/subagents/*.jsonl")):
        session = parse_session(jsonl)
        if session:
            session["is_subagent"] = True
            session["parent_session_id"] = jsonl.parent.parent.name
            subs.append(session)
    return subs


def _text(content: object) -> str:
    """Extract plain text from a message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def _parse_timestamp(record: dict[str, Any]) -> datetime | None:
    """Extract a datetime from a record's timestamp field."""
    raw = record.get("timestamp", "")
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return None


def _is_human_turn(record: dict[str, Any]) -> bool:
    """True when a user-role record is a real human turn, not a tool result.

    Tool results are delivered as user-role messages, so any timing or counting
    over raw type=="user" records is dominated by machine traffic.
    """
    content = record.get("message", {}).get("content", [])
    if isinstance(content, str):
        return bool(content.strip())
    if not isinstance(content, list):
        return False
    return not any(
        isinstance(block, dict) and block.get("type") == "tool_result" for block in content
    )


WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", str(Path.home() / "workspace"))


def _session_repos(records: list[dict[str, Any]]) -> dict[str, int]:
    """Repos this session actually worked in, by record count under each.

    `records[0]["cwd"]` is the *launch* directory, which is the workspace root for
    86% of July sessions (measured 2026-07-20) -- Ramsey drives many repos from
    the root, so the launch dir names no repo at all. But `cwd` is emitted on
    every record and follows the session into subdirectories, so scanning all of
    them resolves a repo for 87% of transcripts instead of 14%.

    Returns {repo_name: record_count}, empty when a session never left the root.
    Callers decide how to attribute a multi-repo session -- this deliberately
    returns the whole distribution rather than picking a winner, because 22% of
    sessions touch more than one repo and the median dominant share is only 57%.
    """
    counts: dict[str, int] = {}
    prefix = WORKSPACE_ROOT + "/"
    for record in records:
        cwd = record.get("cwd")
        if not isinstance(cwd, str) or not cwd.startswith(prefix):
            continue
        repo = cwd[len(prefix) :].split("/", 1)[0]
        if repo:
            counts[repo] = counts.get(repo, 0) + 1
    return counts


def _human_turn_times(user_msgs: list[dict[str, Any]]) -> list[datetime]:
    """Timestamps of genuine human turns, in record order."""
    return [t for r in user_msgs if _is_human_turn(r) and (t := _parse_timestamp(r)) is not None]


# Language map for file extension detection
_LANG_MAP: dict[str, str] = {
    "py": "Python",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "js": "JavaScript",
    "jsx": "JavaScript",
    "md": "Markdown",
    "json": "JSON",
    "yaml": "YAML",
    "yml": "YAML",
    "sh": "Shell",
    "bash": "Shell",
    "ipynb": "Notebook",
    "sql": "SQL",
    "toml": "TOML",
    "html": "HTML",
    "css": "CSS",
}


def parse_session(path: Path) -> dict[str, Any] | None:
    """Parse a single JSONL session file into a stats dict."""
    lines = path.read_text(errors="replace").splitlines()
    records: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    user_msgs = [r for r in records if r.get("type") == "user"]
    asst_msgs = [r for r in records if r.get("type") == "assistant"]

    if not user_msgs:
        return None

    # Subagent type name, e.g. "Explore" / "akira-scan". Emitted per-record by CLI
    # 2.1.201+; transcripts written by older builds carry no attribution at all and
    # leave this None (see SUBAGENT_ATTRIBUTION_CLI in factstore).
    attribution_agent = next(
        (str(a) for r in records if (a := r.get("attributionAgent"))),
        None,
    )

    # Surface the session ran on (e.g. "claude-vscode"). Constant per session/CLI
    # launch. None on transcripts predating this field — see factstore.NULLABLE_COLUMNS.
    entrypoint = next(
        (str(e) for r in records if (e := r.get("entrypoint"))),
        None,
    )

    # Timestamps
    user_times = [t for r in user_msgs if (t := _parse_timestamp(r)) is not None]
    if not user_times:
        return None

    start = min(user_times)
    end = max(user_times)
    duration_minutes = (end - start).total_seconds() / 60

    # First real user prompt (skip ide_opened_file injections)
    first_prompt = ""
    for record in user_msgs:
        txt = _text(record.get("message", {}).get("content", ""))
        txt = re.sub(r"<[^>]+>.*?</[^>]+>", "", txt, flags=re.DOTALL).strip()
        if txt:
            first_prompt = txt[:200]
            break

    # Tool counts from assistant messages
    tool_counts: dict[str, int] = defaultdict(int)
    for record in asst_msgs:
        for block in record.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_counts[block.get("name", "unknown")] += 1

    # Agent spawn metadata from parent sessions
    agent_spawns: list[dict[str, str | None]] = []
    for record in asst_msgs:
        for block in record.get("message", {}).get("content", []):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Agent"
            ):
                inp = block.get("input", {})
                agent_spawns.append(
                    {
                        "type": inp.get("subagent_type", "general-purpose"),
                        "description": inp.get("description"),
                        "model": inp.get("model"),
                    }
                )

    # Tool result errors from user messages.
    # Ordered most-specific-first so narrow patterns are not swallowed by broad ones.
    # Each entry is (substring_to_match, category).  First match wins.
    _ERROR_PATTERNS: list[tuple[str, str]] = [
        # --- agent-side malformed calls (before any "failed" broad match) ---
        ("inputvalidationerror", "invalid_tool_input"),
        # --- edit-tool failures (before generic "not found") ---
        ("string to replace not found", "edit_failed"),
        # --- write-before-read / stale-read (before generic "file" patterns) ---
        ("has not been read yet", "read_before_write"),
        ("modified since read", "stale_read"),
        # --- filesystem shape errors ---
        ("eisdir", "is_a_directory"),
        ("is a directory", "is_a_directory"),
        # --- skill invocation blocked by settings ---
        ("disable-model-invocation", "skill_not_invocable"),
        # --- parallel tool cancellation ---
        ("cancelled", "cancelled"),
        ("canceled", "cancelled"),
        # --- hook-level blocks (PreToolUse errors and explicit "Blocked:" messages) ---
        ("pretooluse", "blocked_by_hook"),
        ("blocked:", "blocked_by_hook"),
        # --- file-not-found (broad; must come after edit/hook patterns) ---
        ("no such file", "file_not_found"),
        ("not found", "file_not_found"),
        ("does not exist", "file_not_found"),
        ("path does not exist", "file_not_found"),
        # --- ACL / user action ---
        ("permission", "permission_denied"),
        ("rejected", "user_rejected"),
        # --- oversized content ---
        ("too large", "file_too_large"),
        ("too long", "file_too_large"),
        ("exceeds maximum", "file_too_large"),
        # --- real shell command failures: exit code present = environment-side ---
        ("exit code", "command_failed"),
        # --- remaining edit failures ---
        ("edit", "edit_failed"),
        # --- any other 'failed' substring (HTTP errors, misc) ---
        ("failed", "command_failed"),
    ]

    tool_errors: dict[str, int] = defaultdict(int)
    for record in user_msgs:
        for block in record.get("message", {}).get("content", []):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and block.get("is_error")
            ):
                content_text = _text(block.get("content", "")).lower()
                category = "other"
                for pattern, cat in _ERROR_PATTERNS:
                    if pattern in content_text:
                        category = cat
                        break
                tool_errors[category] += 1

    # Token usage + model tracking + per-request cost/context
    input_tokens = 0
    output_tokens = 0
    cache_write_tokens = 0
    cache_read_tokens = 0
    cost_units = 0.0
    max_context = 0
    context_bucket_cost: dict[str, float] = dict.fromkeys(_CONTEXT_BUCKETS, 0.0)
    cost_events: list[tuple[str, float]] = []
    model_counts: dict[str, int] = defaultdict(int)
    model_costs: dict[str, float] = defaultdict(float)
    model_tokens: dict[str, int] = defaultdict(int)
    for record in asst_msgs:
        msg = record.get("message", {})
        usage = msg.get("usage", {})
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        cache_write_tokens += usage.get("cache_creation_input_tokens", 0)
        cache_read_tokens += usage.get("cache_read_input_tokens", 0)
        cost = _usage_cost(usage)
        cost_units += cost
        context = (
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
        )
        if context:
            max_context = max(max_context, context)
            context_bucket_cost[_context_bucket(context)] += cost
        event_ts = _parse_timestamp(record)
        if event_ts is not None and cost:
            cost_events.append((event_ts.isoformat(), cost))
        model_id = msg.get("model", "")
        if model_id:
            model_counts[model_id] += 1
            model_costs[model_id] += cost
            model_tokens[model_id] += usage.get("output_tokens", 0)
    primary_model = max(model_counts, key=lambda k: model_counts[k]) if model_counts else "unknown"

    # Compaction events (system compact_boundary records; older format flags the
    # summary message instead — take the max to avoid double-counting pairs)
    compact_count = max(
        sum(
            1
            for r in records
            if r.get("type") == "system" and r.get("subtype") == "compact_boundary"
        ),
        sum(1 for r in records if r.get("isCompactSummary")),
    )

    # Compaction signals: turns-since-last-compact and trigger taxonomy.
    # Walk records in order: track the index of the last compact boundary, then
    # count human turns after it. compact_trigger reads compactMetadata.trigger
    # from the compact_boundary record ("auto" | "manual").
    #
    # Format pairing: modern transcripts emit compact_boundary (with trigger)
    # immediately followed by an isCompactSummary user record. The
    # isCompactSummary record is how the parser detects compaction when
    # compact_boundary is absent (older transcript format). When both are
    # present, compact_boundary is authoritative; isCompactSummary is skipped
    # so it cannot overwrite a good trigger value.
    turns_since_last_compact: int | None = None
    compact_trigger: str | None = None
    _last_compact_idx: int | None = None
    _prev_was_boundary = False
    for _idx, _rec in enumerate(records):
        if _rec.get("type") == "system" and _rec.get("subtype") == "compact_boundary":
            _last_compact_idx = _idx
            _meta = _rec.get("compactMetadata") or {}
            compact_trigger = str(_meta["trigger"]) if "trigger" in _meta else None
            _prev_was_boundary = True
        elif _rec.get("isCompactSummary"):
            if not _prev_was_boundary:
                # Older format: no preceding compact_boundary — use this as the
                # boundary marker. No trigger available in this format.
                _last_compact_idx = _idx
                compact_trigger = None
            # If _prev_was_boundary is True, the compact_boundary already set
            # everything correctly; skip this record entirely.
            _prev_was_boundary = False
        else:
            _prev_was_boundary = False
    if _last_compact_idx is not None:
        # Count human turns strictly after the last compact boundary record.
        turns_since_last_compact = sum(
            1
            for _rec in records[_last_compact_idx + 1 :]
            if _rec.get("type") == "user" and _is_human_turn(_rec)
        )

    # Files modified via file-history-snapshots
    files_modified: set[str] = set()
    for record in records:
        if record.get("type") == "file-history-snapshot":
            file_id = record.get("fileId", "")
            if file_id:
                files_modified.add(file_id)

    # Languages from file extensions in tool_use Read/Write/Edit
    langs: dict[str, int] = defaultdict(int)
    for record in asst_msgs:
        for block in record.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                inp = block.get("input", {})
                fpath = inp.get("file_path", inp.get("path", ""))
                if fpath:
                    ext = Path(fpath).suffix.lstrip(".").lower()
                    lang = _LANG_MAP.get(ext)
                    if lang:
                        langs[lang] += 1

    # User response times (gap between consecutive *human* turns).
    #
    # `user_msgs` is every type=="user" record, but ~90% of those are synthetic:
    # a tool_result is delivered as a user-role message. Timing those measured
    # tool latency, not the human, and inflated the interruption count roughly
    # 10x (verified 2026-07-20 over 6 transcripts). Human turns only.
    response_times: list[float] = []
    sorted_user_times = sorted(_human_turn_times(user_msgs))
    for i in range(1, len(sorted_user_times)):
        delta = (sorted_user_times[i] - sorted_user_times[i - 1]).total_seconds()
        if 1 < delta < 7200:  # ignore tiny/huge gaps
            response_times.append(delta)

    # Message hours (UTC)
    message_hours = [t.hour for t in user_times]

    # User interruptions: a human turn arriving <5s after the previous one, i.e.
    # too fast to be a considered reply. Still a heuristic, but calibrated --
    # over human-only turns the gap median is ~226s and only 3.8% fall under 5s
    # (measured 2026-07-20, n=157), so the threshold isolates a real tail rather
    # than splitting the bulk of the distribution.
    interruptions = sum(1 for t in response_times if t < 5)

    # --- Context engineering signals ---

    # Bash antipatterns: shell used where a dedicated tool exists
    _SHELL_ANTIPATTERNS = re.compile(
        r"\bcat\s+\S|\bhead\s|\btail\s|\bsed\s|\bawk\s"
        r"|\bgrep\s|\brg\s|\bfind\s+\.|\bls\s|\bwc\s"
    )
    bash_antipatterns = 0
    for record in asst_msgs:
        for block in record.get("message", {}).get("content", []):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Bash"
            ):
                cmd = block.get("input", {}).get("command", "")
                if _SHELL_ANTIPATTERNS.search(cmd):
                    bash_antipatterns += 1

    # Skill invocations: /skill-name patterns in user messages
    skill_invocations: list[str] = []
    for record in user_msgs:
        txt = _text(record.get("message", {}).get("content", ""))
        txt = re.sub(r"<[^>]+>.*?</[^>]+>", "", txt, flags=re.DOTALL)
        skill_invocations.extend(re.findall(r"(?:^|\s)/([a-z][a-z0-9-]+)", txt))

    # Skill tool calls: the regex above only sees typed /slash text, so skills
    # invoked through the Skill tool (including auto-triggered ones) are missed.
    for record in asst_msgs:
        for block in record.get("message", {}).get("content", []):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
            ):
                name = block.get("input", {}).get("skill")
                if name:
                    skill_invocations.append(name)

    # Friction labels from user messages
    friction_labels: list[str] = []
    for record in user_msgs:
        txt = _text(record.get("message", {}).get("content", ""))
        for match in re.findall(r"FRICTION:\s*(.+?)(?:\n|$)", txt):
            friction_labels.append(match.strip()[:200])

    # Output tokens per assistant message (verbosity signal)
    output_tokens_per_msg = round(output_tokens / len(asst_msgs), 1) if asst_msgs else 0.0

    # Skill/command cost attribution: assistant cost between a slash invocation
    # and the next real user prompt is attributed to that skill. The invocation
    # record is followed by a user message carrying the expanded skill prompt —
    # consume it as part of the same turn rather than resetting.
    skill_costs: dict[str, float] = defaultdict(float)
    current_skill: str | None = None
    expansion_pending = False
    for record in records:
        rtype = record.get("type")
        if rtype == "user":
            txt = _text(record.get("message", {}).get("content", ""))
            if not txt.strip():
                continue  # tool results — same turn continues
            cmd = re.search(r"<command-name>/([\w-]+)</command-name>", txt)
            if cmd:
                current_skill = cmd.group(1)
                expansion_pending = True
                continue
            stripped = re.sub(r"<[^>]+>.*?</[^>]+>", "", txt, flags=re.DOTALL).strip()
            if not stripped:
                continue
            if expansion_pending:
                expansion_pending = False
                continue
            slash = re.match(r"/([a-z][a-z0-9_-]+)", stripped)
            current_skill = slash.group(1) if slash else None
        elif rtype == "assistant" and current_skill:
            skill_costs[current_skill] += _usage_cost(record.get("message", {}).get("usage", {}))

    # Read/Edit ratio: should be > 1 (understand before changing)
    edit_calls = (
        tool_counts.get("Edit", 0) + tool_counts.get("Write", 0) + tool_counts.get("MultiEdit", 0)
    )
    read_edit_ratio = round(tool_counts.get("Read", 0) / edit_calls, 2) if edit_calls > 0 else None

    # Hook blocks: user_rejected errors on Bash (hook-triggered rejections)
    hook_blocks = tool_errors.get("user_rejected", 0)

    # Long session without TodoWrite (planning discipline)
    has_todo_write = tool_counts.get("TodoWrite", 0) > 0

    return {
        "session_id": path.stem,
        "project_path": str(records[0].get("cwd", "")) if records else "",
        # Repo attribution from every cwd, not just the launch dir -- see
        # _session_repos. JSON {repo: record_count}; {} when the session never
        # left the workspace root.
        "session_repos": _session_repos(records),
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "duration_minutes": round(duration_minutes, 1),
        # Human turns only. `user_msgs` is ~92% tool_result records (measured
        # 2026-07-20, n=3869 over 60 transcripts), so len(user_msgs) reported
        # roughly 12x the real prompt count and made msgs_per_day meaningless.
        "user_message_count": sum(1 for r in user_msgs if _is_human_turn(r)),
        "assistant_message_count": len(asst_msgs),
        "tool_counts": dict(tool_counts),
        "tool_errors": dict(tool_errors),
        "languages": dict(langs),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
        "cost_units": round(cost_units, 1),
        "max_context": max_context,
        "context_bucket_cost": {k: round(v, 1) for k, v in context_bucket_cost.items()},
        "cost_events": cost_events,
        "compact_count": compact_count,
        "skill_costs": {k: round(v, 1) for k, v in skill_costs.items()},
        "is_subagent": False,
        "parent_session_id": None,
        "attribution_agent": attribution_agent,
        "models": dict(model_counts),
        "model_costs": {k: round(v, 1) for k, v in model_costs.items()},
        "model_output_tokens": dict(model_tokens),
        "primary_model": primary_model,
        "files_modified": len(files_modified),
        "first_prompt": first_prompt,
        "user_response_times": response_times,
        "user_interruptions": interruptions,
        "message_hours": message_hours,
        "uses_task_agent": tool_counts.get("Task", 0) > 0,
        # CE / PE signals
        "bash_antipatterns": bash_antipatterns,
        "skill_invocations": skill_invocations,
        "output_tokens_per_msg": output_tokens_per_msg,
        "read_edit_ratio": read_edit_ratio,
        "hook_blocks": hook_blocks,
        "has_todo_write": has_todo_write,
        "agent_spawns": agent_spawns,
        "friction_labels": friction_labels,
        "friction_label_count": len(friction_labels),
        "entrypoint": entrypoint,
        "turns_since_last_compact": turns_since_last_compact,
        "compact_trigger": compact_trigger,
    }


# ---------------------------------------------------------------------------
# Session notes parsing (cord / no-JSONL environments)
# ---------------------------------------------------------------------------


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into a dict of {section_title: body} by ## headers."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "\n".join(lines).strip()
            current_key = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(lines).strip()
    return sections


def _extract_field(text: str, field: str) -> str:
    """Extract value from '- **Field**: value' markdown format."""
    for line in text.splitlines():
        if f"**{field}**:" in line:
            parts = line.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
    return ""


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML front-matter from markdown body.

    Returns (frontmatter_dict, body_text). If no front-matter, returns ({}, text).
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    fm: dict[str, Any] = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Parse simple lists: [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [v.strip().strip("'\"") for v in inner.split(",")] if inner else []
            elif val in ("true", "false"):
                fm[key] = val == "true"
            elif val.lstrip("-").isdigit():
                fm[key] = int(val)
            elif val == "~" or val == "":
                fm[key] = None
            else:
                fm[key] = val
    return fm, body
