"""Deterministic review driver — the pipeline owner.

Replaces prose orchestration of the review pipeline with a Python driver that:
1. Detects signals → computes active dimensions
2. Spawns dimension agents concurrently via the Claude Agent SDK (injectable)
3. Validates findings through Pydantic gates (one repair round-trip, then hard fail)
4. Deduplicates via union-find with deterministic cluster merge
5. Fingerprints + persists a SweepRecord
6. Diffs against previous sweep (trends)
7. Renders a deterministic Markdown report

The `scan_fn` parameter is injectable so every gate is testable with pytest and no LLM.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import re
import subprocess
import sys
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from review.deduplication import find_duplicate_clusters
from review.fingerprint import (
    finding_to_sweep_finding,
    load_sweep,
    save_sweep,
)
from review.render import render_report
from review.schemas.models import (
    MergeImpact,
    Reporter,
    ReporterDispatchEntry,
    ReviewFinding,
    SweepRecord,
)
from review.signals import active_dimensions, detect_signals
from review.trends import build_trend_report, render_trend_report
from review.validation import validate_finding

# ---------------------------------------------------------------------------
# Config + result types
# ---------------------------------------------------------------------------


@dataclass
class DriverConfig:
    """Configuration for a single driver run."""

    repo: Path = field(default_factory=lambda: Path("."))
    files: list[str] = field(default_factory=list)
    reviews_dir: Path = field(default_factory=lambda: Path(".claude/docs/reviews"))
    save_sweep: bool = True
    model: str = "haiku"
    max_turns: int = 30
    # agents dir: defaults to repo/.claude/agents
    agents_dir: Path | None = None

    def __post_init__(self) -> None:
        self.repo = Path(self.repo).resolve()
        self.reviews_dir = Path(self.reviews_dir)
        if not self.reviews_dir.is_absolute():
            self.reviews_dir = self.repo / self.reviews_dir
        if self.agents_dir is None:
            self.agents_dir = self.repo / ".claude" / "agents"


@dataclass
class ScanError:
    """Represents a dimension scan failure (SDK error subtype or validation failure)."""

    dimension: str
    subtype: str  # SDK subtype or "validation_error"
    detail: str


@dataclass
class DriverResult:
    """Result of a complete driver run."""

    findings: list[ReviewFinding] = field(default_factory=list)
    report_md: str = ""
    sweep_path: Path | None = None
    trend_md: str = ""
    errors: list[ScanError] = field(default_factory=list)
    dispatch: list[ReporterDispatchEntry] = field(default_factory=list)
    exit_code: int = 0


# ---------------------------------------------------------------------------
# Scan output contract — driver-side (OQ7: no agent file edits)
# ---------------------------------------------------------------------------

_YAML_FRONTMATTER = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)

# Dimension name → agent filename stem mapping
_DIMENSION_TO_AGENT_FILE: dict[str, str] = {
    "correctness": "correctness",
    "safety": "safety",
    "structure": "structure",
    "agent-quality": "agent-quality",
    "contracts": "contracts",
    "wander": "wander",
}

# Driver-mode output instruction appended to the system prompt
_DRIVER_MODE_SUFFIX = """
---
## Driver mode (deterministic pipeline)

You are running under the deterministic review driver. Your output MUST be a JSON object
with a single key "findings" containing an array of finding objects conforming to the
ReviewFinding schema. Do NOT output markdown prose, headers, or any text outside the
JSON object. Each finding must have all required fields.

For wander (WD-) findings: use evidence_state "question" and merge_impact "question".
If you find no issues, return {"findings": []}.
"""

# Dimension → Reporter enum value
_DIMENSION_TO_REPORTER: dict[str, Reporter] = {
    "correctness": Reporter.CORRECTNESS,
    "safety": Reporter.SAFETY,
    "structure": Reporter.STRUCTURE,
    "agent-quality": Reporter.AGENT_QUALITY,
    "contracts": Reporter.CONTRACTS,
    "wander": Reporter.WANDER,
}


def load_agent_prompt(dimension: str, agents_dir: Path) -> str:
    """Read the agent .md, strip YAML frontmatter, append driver-mode suffix.

    Args:
        dimension: Dimension name (e.g. "correctness", "agent-quality").
        agents_dir: Directory containing the agent .md files.

    Returns:
        System prompt string for SDK query.
    """
    stem = _DIMENSION_TO_AGENT_FILE.get(dimension, dimension)
    agent_file = agents_dir / f"{stem}.md"
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent file not found: {agent_file}")
    raw = agent_file.read_text()
    body = _YAML_FRONTMATTER.sub("", raw, count=1)
    return body.strip() + "\n" + _DRIVER_MODE_SUFFIX


def _findings_json_schema() -> dict[str, Any]:
    """Build the JSON schema for {"findings": [ReviewFinding...]} for SDK output_format."""
    finding_schema = ReviewFinding.model_json_schema()
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": finding_schema,
            }
        },
        "required": ["findings"],
        "$defs": finding_schema.get("$defs", {}),
    }


FINDINGS_SCHEMA: dict[str, Any] = _findings_json_schema()


def parse_scan_result(result_text: str | None, subtype: str) -> list[dict] | ScanError:
    """Parse a SDK ResultMessage into a list of raw finding dicts.

    Args:
        result_text: The .result text from a ResultMessage (may be None on error).
        subtype: The .subtype from the ResultMessage ("success" or an error subtype).

    Returns:
        list[dict] on success, ScanError on any failure.
    """
    if subtype != "success":
        return ScanError(
            dimension="",
            subtype=subtype,
            detail=result_text or f"SDK error: {subtype}",
        )
    try:
        data = json.loads(result_text or "")
        findings = data.get("findings", [])
        if not isinstance(findings, list):
            return ScanError(
                dimension="",
                subtype="parse_error",
                detail="'findings' key is not a list",
            )
        return findings
    except json.JSONDecodeError as exc:
        return ScanError(
            dimension="",
            subtype="parse_error",
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Real SDK scan implementation (Step 4)
# ---------------------------------------------------------------------------


def _scan_task_prompt(dimension: str, files: list[str]) -> str:
    """Build the user prompt for a dimension scan."""
    file_list = "\n".join(f"  - {f}" for f in files)
    return (
        f"Scan the following files for the **{dimension}** dimension.\n\n"
        f"Files to scan:\n{file_list}\n\n"
        "Return your findings as a JSON object with a 'findings' array."
    )


async def sdk_scan(
    dimension: str, files: list[str], config: DriverConfig
) -> list[dict] | ScanError:
    """Real scan implementation via the Claude Agent SDK.

    Each dimension scan is an independent claude-agent-sdk query with:
    - System prompt = stripped agent .md + driver-mode suffix
    - output_format = json_schema (API-enforced shape)
    - model = config.model (default "haiku")
    - allowed_tools = Read, Grep, Glob, Bash (read-only)
    - cwd = config.repo
    - max_turns = config.max_turns

    On schema failure the SDK returns subtype "error_max_structured_output_retries".
    This function returns ScanError in that case — the driver handles the repair loop.

    Args:
        dimension: Dimension name (e.g. "correctness").
        files: List of file paths to scan (relative to config.repo).
        config: DriverConfig with model, max_turns, repo, agents_dir.

    Returns:
        list[dict] of raw finding dicts on success, ScanError on failure.
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
    except ImportError:
        return ScanError(
            dimension=dimension,
            subtype="sdk_unavailable",
            detail="claude-agent-sdk not installed or CLI not available",
        )

    try:
        system_prompt = load_agent_prompt(dimension, config.agents_dir)
    except FileNotFoundError as exc:
        return ScanError(dimension=dimension, subtype="agent_not_found", detail=str(exc))

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=config.model,
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        cwd=str(config.repo),
        max_turns=config.max_turns,
        output_format={"type": "json_schema", "schema": FINDINGS_SCHEMA},
    )

    result_message = None
    prompt = _scan_task_prompt(dimension, files)
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result_message = message
            break

    if result_message is None:
        return ScanError(
            dimension=dimension,
            subtype="no_result",
            detail="SDK query returned no ResultMessage",
        )

    cost = getattr(result_message, "total_cost_usd", None)
    if cost is not None:
        print(f"[driver] {dimension}: ${cost:.4f}", file=sys.stderr)

    parsed = parse_scan_result(
        getattr(result_message, "result", None),
        getattr(result_message, "subtype", "unknown"),
    )
    if isinstance(parsed, ScanError):
        parsed.dimension = dimension
    return parsed


# ---------------------------------------------------------------------------
# Repair round-trip (OQ3: one repair attempt per dimension)
# ---------------------------------------------------------------------------


async def _repair_scan(
    dimension: str,
    files: list[str],
    config: DriverConfig,
    error_detail: str,
) -> list[dict] | ScanError:
    """Attempt one repair round-trip by feeding the Pydantic error back.

    This creates a new SDK session (no session_id resume needed — the agent
    file + error message is sufficient context for a corrective response).
    """
    try:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
    except ImportError:
        return ScanError(
            dimension=dimension,
            subtype="sdk_unavailable",
            detail="claude-agent-sdk not installed or CLI not available",
        )

    try:
        system_prompt = load_agent_prompt(dimension, config.agents_dir)
    except FileNotFoundError as exc:
        return ScanError(dimension=dimension, subtype="agent_not_found", detail=str(exc))

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=config.model,
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        cwd=str(config.repo),
        max_turns=config.max_turns,
        output_format={"type": "json_schema", "schema": FINDINGS_SCHEMA},
    )

    repair_prompt = (
        f"Your previous output for the **{dimension}** dimension failed validation:\n\n"
        f"```\n{error_detail}\n```\n\n"
        "Please re-scan the same files and return corrected findings conforming to the "
        "ReviewFinding schema. Return ONLY the JSON object with a 'findings' array.\n\n"
        + _scan_task_prompt(dimension, files)
    )

    result_message = None
    async for message in query(prompt=repair_prompt, options=options):
        if isinstance(message, ResultMessage):
            result_message = message
            break

    if result_message is None:
        return ScanError(
            dimension=dimension,
            subtype="repair_no_result",
            detail="Repair SDK query returned no ResultMessage",
        )

    parsed = parse_scan_result(
        getattr(result_message, "result", None),
        getattr(result_message, "subtype", "unknown"),
    )
    if isinstance(parsed, ScanError):
        parsed.dimension = dimension
    return parsed


# ---------------------------------------------------------------------------
# Deterministic cluster merge (OQ4: max merge_impact representative)
# ---------------------------------------------------------------------------

_MERGE_IMPACT_ORDER: dict[MergeImpact, int] = {
    MergeImpact.BLOCKER: 0,
    MergeImpact.IMPORTANT: 1,
    MergeImpact.QUESTION: 2,
    MergeImpact.SUGGESTION: 3,
    MergeImpact.NIT: 4,
}


def merge_cluster(cluster: list[ReviewFinding]) -> ReviewFinding:
    """Deterministically merge a dedup cluster into a single representative finding.

    Representative = finding with the highest merge_impact (lowest order index).
    Other members' IDs are appended to the representative's basis list.

    Args:
        cluster: Non-empty list of ReviewFinding objects in the same dedup cluster.

    Returns:
        Single representative ReviewFinding with absorbed IDs in basis.
    """
    if len(cluster) == 1:
        return cluster[0]

    sorted_cluster = sorted(
        cluster,
        key=lambda f: _MERGE_IMPACT_ORDER.get(f.severity.merge_impact, 99),
    )
    representative = sorted_cluster[0]
    absorbed_ids = [f.id for f in sorted_cluster[1:]]

    # Return a new instance with absorbed IDs appended to basis
    new_basis = list(representative.basis) + [f"absorbed: {fid}" for fid in absorbed_ids]
    return representative.model_copy(update={"basis": new_basis})


# ---------------------------------------------------------------------------
# Scope detection (same rule as /akira)
# ---------------------------------------------------------------------------


def _detect_scope(repo: Path) -> list[str]:
    """Detect the changed file set for this run.

    Rule (mirrors /akira scope):
    - Changed set = git status --porcelain union git diff main...HEAD --name-only
    - master fallback if main doesn't exist
    - Empty changed set → whole-repo (git ls-files)

    Returns:
        List of file paths relative to repo root.
    """
    repo_str = str(repo)

    def _git(*args: str) -> list[str]:
        try:
            result = subprocess.run(
                ["git"] + list(args),
                capture_output=True,
                text=True,
                cwd=repo_str,
                check=False,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except OSError:
            return []

    # git status --porcelain: take the filename portion (cols 3+)
    status_lines = _git("status", "--porcelain")
    status_files: list[str] = []
    for line in status_lines:
        if len(line) >= 3:
            fname = line[3:].strip()
            # handle renames: "old -> new"
            if " -> " in fname:
                fname = fname.split(" -> ")[-1]
            if fname:
                status_files.append(fname)

    # git diff main...HEAD
    diff_files = _git("diff", "main...HEAD", "--name-only")
    if not diff_files:
        diff_files = _git("diff", "master...HEAD", "--name-only")

    changed: list[str] = list(dict.fromkeys(status_files + diff_files))

    if not changed:
        # Whole-repo fallback
        changed = _git("ls-files")

    return changed


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

ScanFn = Callable[
    [str, list[str], DriverConfig],
    Coroutine[Any, Any, list[dict] | ScanError],
]


def run_review(
    config: DriverConfig,
    scan_fn: ScanFn = sdk_scan,
) -> DriverResult:
    """Run the full deterministic review pipeline.

    Args:
        config: DriverConfig controlling repo, scope, model, persistence.
        scan_fn: Async callable (dimension, files, config) → list[dict] | ScanError.
                 Defaults to sdk_scan; inject a fake for testing.

    Returns:
        DriverResult with findings, report_md, sweep_path, trend_md, errors, exit_code.
    """
    return asyncio.run(_run_review_async(config, scan_fn))


async def _run_review_async(
    config: DriverConfig,
    scan_fn: ScanFn,
) -> DriverResult:
    result = DriverResult()

    # --- Stage 1: scope + signals → dimension list ---
    files = config.files if config.files else _detect_scope(config.repo)
    signals = detect_signals(files, repo_root=str(config.repo))

    # Wander is always-on (per active_dimensions) but plan says "when diff scope exists"
    # active_dimensions already includes wander unconditionally — keep that.
    dimensions = active_dimensions(signals)

    # --- Stage 2: concurrent dimension scans ---
    print(
        f"[driver] scanning {len(dimensions)} dimensions over {len(files)} files",
        file=sys.stderr,
    )
    scan_tasks = [scan_fn(dim, files, config) for dim in dimensions]
    scan_results: list[list[dict] | ScanError] = list(await asyncio.gather(*scan_tasks))

    # --- Stage 3: validate + repair ---
    all_findings: list[ReviewFinding] = []
    errors: list[ScanError] = []

    for dim, raw in zip(dimensions, scan_results, strict=True):
        # Indexed, not .get(): an unmapped dimension is a wiring bug, and a None here
        # surfaces as a confusing Pydantic error on the non-optional reporter field.
        reporter = _DIMENSION_TO_REPORTER[dim]

        if isinstance(raw, ScanError):
            raw.dimension = dim
            errors.append(raw)
            result.dispatch.append(
                ReporterDispatchEntry(
                    reporter=reporter,
                    status="failed",
                    skip_reason=f"{raw.subtype}: {raw.detail[:120]}",
                )
            )
            continue

        # Validate each finding; collect per-finding errors
        dim_findings: list[ReviewFinding] = []
        dim_errors: list[str] = []

        for raw_finding in raw:
            ok, err = validate_finding(raw_finding)
            if ok:
                try:
                    dim_findings.append(ReviewFinding.model_validate(raw_finding))
                except (ValueError, TypeError) as exc:
                    dim_errors.append(str(exc))
            else:
                dim_errors.append(err)

        if dim_errors:
            # One repair round-trip
            error_summary = "\n".join(dim_errors[:5])
            print(
                f"[driver] {dim}: {len(dim_errors)} validation error(s), attempting repair",
                file=sys.stderr,
            )
            repaired_raw = await _repair_scan(dim, files, config, error_summary)

            if isinstance(repaired_raw, ScanError):
                repaired_raw.dimension = dim
                errors.append(repaired_raw)
                result.dispatch.append(
                    ReporterDispatchEntry(
                        reporter=reporter,
                        status="failed",
                        skip_reason=f"repair failed: {repaired_raw.subtype}",
                    )
                )
                continue

            # Re-validate repaired findings. The repair re-scans the same files in full,
            # so its output replaces pass 1 rather than adding to it — appending would
            # double every finding that was already valid before the repair.
            repaired_findings: list[ReviewFinding] = []
            repair_errors: list[str] = []
            for raw_finding in repaired_raw:
                ok, err = validate_finding(raw_finding)
                if ok:
                    try:
                        repaired_findings.append(ReviewFinding.model_validate(raw_finding))
                    except (ValueError, TypeError) as exc:
                        repair_errors.append(str(exc))
                else:
                    repair_errors.append(err)

            if repair_errors:
                scan_err = ScanError(
                    dimension=dim,
                    subtype="validation_error",
                    detail="\n".join(repair_errors[:5]),
                )
                errors.append(scan_err)
                result.dispatch.append(
                    ReporterDispatchEntry(
                        reporter=reporter,
                        status="failed",
                        skip_reason="validation failed after repair",
                    )
                )
                continue

            dim_findings = repaired_findings

        all_findings.extend(dim_findings)
        result.dispatch.append(ReporterDispatchEntry(reporter=reporter, status="completed"))

    result.errors = errors

    # Hard fail if any dimension errored (OQ3: no silent drops)
    if errors:
        result.exit_code = 1
        # Still render what we have for partial report
        if not all_findings:
            error_lines = "\n".join(f"- [{e.dimension}] {e.subtype}: {e.detail}" for e in errors)
            result.report_md = f"# Review Report\n\n## Errors\n\n{error_lines}\n"
            return result

    # --- Stage 4: dedup + deterministic cluster merge ---
    clusters = find_duplicate_clusters(all_findings)
    merged_findings: list[ReviewFinding] = [merge_cluster(c) for c in clusters]

    # --- Stage 5: fingerprint + sweep persistence ---
    sweep_path: Path | None = None
    if config.save_sweep:
        sweep_findings = [finding_to_sweep_finding(f) for f in merged_findings]
        date_str = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
        repo_name = config.repo.name
        record = SweepRecord(repo=repo_name, sweep_date=date_str, findings=sweep_findings)
        base = config.reviews_dir / f"{repo_name}-{date_str}.json"
        target = base
        counter = 1
        while target.exists():
            target = config.reviews_dir / f"{repo_name}-{date_str}-{counter}.json"
            counter += 1
        save_sweep(record, target)
        sweep_path = target
        result.sweep_path = sweep_path
        print(f"[driver] sweep saved: {sweep_path}", file=sys.stderr)
    else:
        # Build an in-memory record for trends even when not saving
        sweep_findings = [finding_to_sweep_finding(f) for f in merged_findings]
        date_str = datetime.datetime.now(tz=datetime.UTC).date().isoformat()
        repo_name = config.repo.name
        record = SweepRecord(repo=repo_name, sweep_date=date_str, findings=sweep_findings)

    # --- Stage 6: trends ---
    trend_md = ""
    if config.save_sweep:
        # Look for the previous sweep (the one before the one we just wrote)
        candidates = sorted(
            config.reviews_dir.glob(f"{repo_name}-*.json"),
            key=lambda p: p.stat().st_mtime,
        )
        if len(candidates) >= 2:
            prev_sweep = load_sweep(candidates[-2])
            curr_sweep = load_sweep(candidates[-1])
            if prev_sweep and curr_sweep:
                trend_report = build_trend_report(prev_sweep, curr_sweep)
                trend_md = render_trend_report(trend_report)
    result.trend_md = trend_md

    # --- Stage 7: render report ---
    wander_questions = [
        f.claim.observation for f in merged_findings if f.reporter == Reporter.WANDER
    ]
    # Derive merge_decision from findings
    has_blocker = any(f.severity.merge_impact == MergeImpact.BLOCKER for f in merged_findings)
    has_important = any(f.severity.merge_impact == MergeImpact.IMPORTANT for f in merged_findings)
    if errors:
        merge_decision = "insufficient_context"
    elif has_blocker:
        merge_decision = "request_changes"
    elif has_important:
        merge_decision = "comment"
    else:
        merge_decision = "approve"

    report_data: dict[str, Any] = {
        "findings": [f.model_dump() for f in merged_findings],
        "merge_decision": merge_decision,
        "reporter_dispatch": [e.model_dump() for e in result.dispatch],
        "overall_understanding": (
            f"Driver run over {len(files)} file(s), "
            f"{len(dimensions)} dimension(s). "
            f"{len(merged_findings)} finding(s) after dedup."
        ),
        "dod_assessment": (
            "All validation gates passed."
            if not errors
            else f"{len(errors)} dimension(s) failed validation."
        ),
        "wander_questions": wander_questions,
        "repo": str(config.repo),
        "diff_scope": f"{len(files)} file(s)",
    }
    result.report_md = render_report(report_data)
    result.findings = merged_findings

    return result
