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
