"""Deterministic Markdown report renderer.

Accepts the merged findings + metadata dict produced by the dao pipeline and
renders a structured Markdown report.  No LLM calls — output is fully
deterministic given the same input.

Input schema (all keys optional except ``findings``):
    {
        "findings": [...],           # list of ReviewFinding dicts
        "merge_decision": str,       # approve | comment | request_changes | insufficient_context
        "reporter_dispatch": [...],  # list of ReporterDispatchEntry dicts
        "overall_understanding": str,
        "dod_assessment": str,
        "wander_questions": [...],   # list of str (from wander agent)
        "repo": str,                 # repo name / path for header
        "diff_scope": str,           # branch, PR ref, or file list
    }
"""

from __future__ import annotations

from review.schemas.models import MergeImpact, ReviewFinding

# Impact ordering: blockers first, nits last
_IMPACT_ORDER = [
    MergeImpact.BLOCKER,
    MergeImpact.IMPORTANT,
    MergeImpact.QUESTION,
    MergeImpact.SUGGESTION,
    MergeImpact.NIT,
]

_IMPACT_BADGE = {
    MergeImpact.BLOCKER: "BLOCKER",
    MergeImpact.IMPORTANT: "IMPORTANT",
    MergeImpact.QUESTION: "QUESTION",
    MergeImpact.SUGGESTION: "SUGGESTION",
    MergeImpact.NIT: "NIT",
}

_DECISION_LABEL = {
    "approve": "APPROVE",
    "comment": "COMMENT",
    "request_changes": "REQUEST CHANGES",
    "insufficient_context": "INSUFFICIENT CONTEXT",
}


def _sort_findings(findings: list[ReviewFinding]) -> list[ReviewFinding]:
    order = {impact: i for i, impact in enumerate(_IMPACT_ORDER)}
    return sorted(findings, key=lambda f: order.get(f.severity.merge_impact, 99))


def _format_location(finding: ReviewFinding) -> str:
    parts = []
    for fl in finding.location.files:
        loc = fl.path
        if fl.start_line is not None:
            loc += f":{fl.start_line}"
            if fl.end_line is not None and fl.end_line != fl.start_line:
                loc += f"-{fl.end_line}"
        parts.append(loc)
    return ", ".join(parts) if parts else "(no location)"


def _render_summary_table(findings: list[ReviewFinding]) -> str:
    if not findings:
        return "_No findings._\n"
    lines = [
        "| ID | Impact | Category | Title |",
        "|----|--------|----------|-------|",
    ]
    for f in _sort_findings(findings):
        badge = _IMPACT_BADGE.get(f.severity.merge_impact, str(f.severity.merge_impact))
        lines.append(f"| {f.id} | {badge} | {f.category.value} | {f.claim.title} |")
    return "\n".join(lines) + "\n"


def _render_finding_detail(f: ReviewFinding) -> str:
    badge = _IMPACT_BADGE.get(f.severity.merge_impact, str(f.severity.merge_impact))
    lines = [
        f"#### {f.id} — {f.claim.title} [{badge}]",
        "",
        f"**Location**: {_format_location(f)}",
        f"**Category**: {f.category.value}  |  **Evidence**: {f.evidence_state.value}",
        "",
        f"**Observation**: {f.claim.observation}",
    ]
    if f.claim.failure_scenario:
        lines += ["", f"**Failure scenario**: {f.claim.failure_scenario}"]
    if f.claim.impact:
        lines += ["", f"**Impact**: {f.claim.impact}"]
    if f.basis:
        lines += ["", "**Basis**:"]
        lines += [f"- {b}" for b in f.basis]
    return "\n".join(lines) + "\n"


def _render_reporter_dispatch(dispatch: list[dict]) -> str:
    if not dispatch:
        return "_No dispatch data._\n"
    lines = ["| Reporter | Status | Note |", "|----------|--------|------|"]
    for entry in dispatch:
        reporter = entry.get("reporter", "")
        status = entry.get("status", "")
        note = entry.get("skip_reason") or ""
        lines.append(f"| {reporter} | {status} | {note} |")
    return "\n".join(lines) + "\n"


def render_report(data: dict) -> str:
    """Render a deterministic Markdown review report from the merged findings dict.

    Args:
        data: Dict with ``findings`` list plus optional metadata keys.

    Returns:
        Markdown string.
    """
    repo = data.get("repo", "")
    diff_scope = data.get("diff_scope", "")
    overall = data.get("overall_understanding", "")
    dod = data.get("dod_assessment", "")
    merge_decision_raw = data.get("merge_decision", "")
    wander_questions: list[str] = data.get("wander_questions", [])
    reporter_dispatch: list[dict] = data.get("reporter_dispatch", [])

    # Parse findings — accept raw dicts or already-validated models
    raw_findings: list[dict] = data.get("findings", [])
    findings: list[ReviewFinding] = []
    parse_errors: list[str] = []
    for raw in raw_findings:
        try:
            findings.append(ReviewFinding.model_validate(raw))
        except Exception as exc:
            parse_errors.append(str(exc))

    sorted_findings = _sort_findings(findings)

    # Header
    header_parts = ["# Review Report"]
    if repo:
        header_parts[0] += f" — {repo}"
    if diff_scope:
        header_parts.append(f"\n**Scope**: {diff_scope}")
    sections = ["\n".join(header_parts)]

    # Decision banner
    decision_label = _DECISION_LABEL.get(
        merge_decision_raw, merge_decision_raw.upper() if merge_decision_raw else ""
    )
    if decision_label:
        sections.append(f"## Decision: {decision_label}")

    # Overall understanding
    if overall:
        sections.append(f"## Understanding\n\n{overall}")

    # Summary table
    sections.append(f"## Findings Summary\n\n{_render_summary_table(sorted_findings)}")

    # Per-finding details
    if sorted_findings:
        detail_blocks = [_render_finding_detail(f) for f in sorted_findings]
        sections.append("## Finding Details\n\n" + "\n".join(detail_blocks))

    # Wander questions
    if wander_questions:
        q_lines = "\n".join(f"- {q}" for q in wander_questions)
        sections.append(f"## Open Questions (Wander)\n\n{q_lines}")

    # DoD assessment
    if dod:
        sections.append(f"## DoD Assessment\n\n{dod}")

    # Reporter dispatch
    sections.append(f"## Reporter Dispatch\n\n{_render_reporter_dispatch(reporter_dispatch)}")

    # Parse errors (defensive — should not appear in normal flow)
    if parse_errors:
        err_lines = "\n".join(f"- {e}" for e in parse_errors)
        sections.append(f"## Parse Errors\n\n{err_lines}")

    return "\n\n".join(sections) + "\n"
