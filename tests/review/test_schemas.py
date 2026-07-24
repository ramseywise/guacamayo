import json

import pytest
from pydantic import ValidationError

from review.schemas.export import export_finding_schema
from review.schemas.models import (
    EvidenceState,
    FileLocation,
    MergeDecision,
    MergeImpact,
    Reporter,
    ReporterDispatchEntry,
    ReviewReport,
)
from tests.review.conftest import make_finding


class TestReviewFinding:
    def test_valid_finding_roundtrip(self):
        f = make_finding()
        data = f.model_dump(mode="json")
        rebuilt = f.__class__.model_validate(data)
        assert rebuilt.id == f.id
        assert rebuilt.category == f.category

    def test_invalid_id_lowercase(self):
        with pytest.raises(ValidationError, match="must match"):
            make_finding(id="lowercase-001")

    def test_invalid_id_short_digits(self):
        with pytest.raises(ValidationError, match="must match"):
            make_finding(id="A-01")

    def test_invalid_line_range(self):
        with pytest.raises(ValidationError, match="end_line"):
            FileLocation(path="foo.py", start_line=10, end_line=5)

    def test_question_state_blocks_blocker_impact(self):
        with pytest.raises(ValidationError, match="evidence_state=question"):
            make_finding(
                evidence_state=EvidenceState.QUESTION,
                merge_impact=MergeImpact.BLOCKER,
            )

    def test_question_state_allows_question_impact(self):
        f = make_finding(
            evidence_state=EvidenceState.QUESTION,
            merge_impact=MergeImpact.QUESTION,
            comment_type="question",
        )
        assert f.evidence_state == EvidenceState.QUESTION


class TestReporterDispatchEntry:
    def test_skipped_requires_reason(self):
        with pytest.raises(ValidationError, match="skip_reason"):
            ReporterDispatchEntry(reporter=Reporter.SANYI, status="skipped")

    def test_skipped_with_reason_ok(self):
        entry = ReporterDispatchEntry(
            reporter=Reporter.SANYI, status="skipped", skip_reason="no SANYI.md"
        )
        assert entry.skip_reason == "no SANYI.md"


class TestReviewReport:
    def test_valid_report(self):
        f = make_finding()
        report = ReviewReport(
            findings=[f],
            merge_decision=MergeDecision.COMMENT,
            reporter_dispatch=[
                ReporterDispatchEntry(reporter=Reporter.AKIRA_SCAN, status="completed")
            ],
            overall_understanding="Test report",
            dod_assessment="All items met",
        )
        assert len(report.findings) == 1


class TestJsonSchemaExport:
    def test_export_produces_valid_schema(self, tmp_path):
        out = tmp_path / "schema.json"
        schema = export_finding_schema(output_path=out)
        assert "properties" in schema
        assert "id" in schema["properties"]
        loaded = json.loads(out.read_text())
        assert loaded == schema
