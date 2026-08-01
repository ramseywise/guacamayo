from pathlib import Path

import pytest

REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)

from review.schemas.models import (
    Category,
    Claim,
    CommentType,
    EvidenceState,
    FileLocation,
    Location,
    MergeImpact,
    Reporter,
    ReviewFinding,
    Severity,
)


@pytest.fixture(autouse=True)
def _isolate_findings_jsonl(tmp_path, monkeypatch):
    """Redirect the shared findings JSONL to a scratch path for every test.

    `emit_findings_jsonl` defaults to ~/workspace/guacamayo/.claude/docs/
    review-findings.jsonl — a real, git-ignored cross-repo data file with no
    history to restore from. Pipeline tests reach it through `run_review`
    without naming it, so without this fixture a test run appends fixture rows
    to production data (observed: 31 fixture rows against 7 real ones).

    Autouse and unconditional on purpose: opting in per-test is the failure
    mode this prevents.
    """
    monkeypatch.setattr("review.driver._FINDINGS_JSONL_PATH", tmp_path / "review-findings.jsonl")


def make_finding(
    id: str = "AK-001",
    *,
    reporter: Reporter = Reporter.AKIRA_SCAN,
    path: str = "src/example.py",
    start_line: int | None = 1,
    end_line: int | None = 10,
    category: Category = Category.CORRECTNESS,
    evidence_state: EvidenceState = EvidenceState.VERIFIED,
    merge_impact: MergeImpact = MergeImpact.IMPORTANT,
    symbols: list[str] | None = None,
    title: str = "Test finding",
    comment_type: CommentType = CommentType.REQUEST_CHANGE,
) -> ReviewFinding:
    return ReviewFinding(
        id=id,
        reporter=reporter,
        category=category,
        evidence_state=evidence_state,
        location=Location(
            files=[FileLocation(path=path, start_line=start_line, end_line=end_line)],
            symbols=symbols or [],
        ),
        claim=Claim(title=title, observation="test observation"),
        severity=Severity(merge_impact=merge_impact),
        basis=["test basis"],
        comment_type=comment_type,
    )
