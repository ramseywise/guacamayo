"""Rule table for review/verdict.py — the single verdict implementation."""

from __future__ import annotations

import pytest

from review.schemas.models import CommentType, EvidenceState, MergeDecision, MergeImpact
from review.verdict import derive_merge_decision
from tests.review.conftest import make_finding


def _finding(merge_impact: MergeImpact, id: str = "AK-001"):
    comment_type = {
        MergeImpact.BLOCKER: CommentType.REQUEST_CHANGE,
        MergeImpact.IMPORTANT: CommentType.REQUEST_CHANGE,
        MergeImpact.QUESTION: CommentType.QUESTION,
        MergeImpact.SUGGESTION: CommentType.SUGGESTION,
        MergeImpact.NIT: CommentType.NIT,
    }[merge_impact]
    evidence_state = (
        EvidenceState.QUESTION if merge_impact == MergeImpact.QUESTION else EvidenceState.VERIFIED
    )
    return make_finding(
        id,
        merge_impact=merge_impact,
        comment_type=comment_type,
        evidence_state=evidence_state,
    )


@pytest.mark.parametrize(
    ("impacts", "expected"),
    [
        ([], MergeDecision.APPROVE),
        ([MergeImpact.NIT], MergeDecision.APPROVE),
        ([MergeImpact.SUGGESTION], MergeDecision.COMMENT),
        ([MergeImpact.QUESTION], MergeDecision.COMMENT),
        ([MergeImpact.IMPORTANT], MergeDecision.COMMENT),
        ([MergeImpact.BLOCKER], MergeDecision.REQUEST_CHANGES),
        ([MergeImpact.NIT, MergeImpact.SUGGESTION], MergeDecision.COMMENT),
        ([MergeImpact.IMPORTANT, MergeImpact.BLOCKER], MergeDecision.REQUEST_CHANGES),
    ],
)
def test_rule_table(impacts, expected):
    findings = [_finding(impact, id=f"AK-{i + 1:03d}") for i, impact in enumerate(impacts)]
    assert derive_merge_decision(findings) == expected


def test_dispatch_failed_overrides_everything():
    findings = [_finding(MergeImpact.BLOCKER)]
    assert (
        derive_merge_decision(findings, dispatch_failed=True) == MergeDecision.INSUFFICIENT_CONTEXT
    )


def test_dispatch_failed_with_no_findings():
    assert derive_merge_decision([], dispatch_failed=True) == MergeDecision.INSUFFICIENT_CONTEXT
