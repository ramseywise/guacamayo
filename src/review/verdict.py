"""Single source of the merge verdict.

``derive_merge_decision`` is the only place merge-decision rules live. The driver,
``review-cli verdict``, and the workflow-review / sanyi skills all consume this
function — none re-derive the rules. The function is policy; the call site owns
scope (e.g. the driver excludes ``Reporter.WANDER`` findings, which are questions
by construction and would make ``approve`` structurally unreachable).
"""

from __future__ import annotations

from review.schemas.models import MergeDecision, MergeImpact, ReviewFinding

_COMMENT_IMPACTS = frozenset({MergeImpact.IMPORTANT, MergeImpact.QUESTION, MergeImpact.SUGGESTION})


def derive_merge_decision(
    findings: list[ReviewFinding], *, dispatch_failed: bool = False
) -> MergeDecision:
    if dispatch_failed:
        return MergeDecision.INSUFFICIENT_CONTEXT
    impacts = {f.severity.merge_impact for f in findings}
    if MergeImpact.BLOCKER in impacts:
        return MergeDecision.REQUEST_CHANGES
    if impacts & _COMMENT_IMPACTS:
        return MergeDecision.COMMENT
    return MergeDecision.APPROVE
