import json
import subprocess


from review.dao.render import render_report
from review.schemas.models import MergeImpact
from tests.review.conftest import make_finding


def _report_dict(**kwargs) -> dict:
    """Minimal valid report dict for render_report."""
    base = {
        "findings": [],
        "merge_decision": "comment",
        "reporter_dispatch": [],
        "overall_understanding": "",
        "dod_assessment": "",
    }
    base.update(kwargs)
    return base


class TestRenderReport:
    def test_returns_string(self):
        result = render_report(_report_dict())
        assert isinstance(result, str)

    def test_header_present(self):
        result = render_report(_report_dict())
        assert "# Review Report" in result

    def test_repo_in_header(self):
        result = render_report(_report_dict(repo="guacamayo"))
        assert "guacamayo" in result

    def test_diff_scope_in_output(self):
        result = render_report(_report_dict(diff_scope="GUA-38-review-agent-arch"))
        assert "GUA-38-review-agent-arch" in result

    def test_decision_label_rendered(self):
        result = render_report(_report_dict(merge_decision="request_changes"))
        assert "REQUEST CHANGES" in result

    def test_empty_findings_shows_placeholder(self):
        result = render_report(_report_dict())
        assert "No findings" in result

    def test_finding_appears_in_summary_table(self):
        f = make_finding("AK-001", title="Missing null check")
        result = render_report(_report_dict(findings=[f.model_dump(mode="json")]))
        assert "AK-001" in result
        assert "Missing null check" in result

    def test_findings_sorted_blockers_first(self):
        blocker = make_finding("AK-001", merge_impact=MergeImpact.BLOCKER, title="Blocker finding")
        nit = make_finding("AK-002", merge_impact=MergeImpact.NIT, title="Nit finding")
        result = render_report(
            _report_dict(findings=[nit.model_dump(mode="json"), blocker.model_dump(mode="json")])
        )
        blocker_pos = result.index("AK-001")
        nit_pos = result.index("AK-002")
        assert blocker_pos < nit_pos, "Blockers must appear before nits"

    def test_finding_detail_section(self):
        f = make_finding("AK-001", title="Bad import")
        result = render_report(_report_dict(findings=[f.model_dump(mode="json")]))
        assert "## Finding Details" in result
        assert "Bad import" in result

    def test_location_rendered(self):
        f = make_finding("AK-001", path="src/main.py", start_line=10, end_line=20)
        result = render_report(_report_dict(findings=[f.model_dump(mode="json")]))
        assert "src/main.py" in result
        assert "10" in result

    def test_wander_questions_section(self):
        result = render_report(
            _report_dict(wander_questions=["Why is this not tested?", "What happens on timeout?"])
        )
        assert "## Open Questions" in result
        assert "Why is this not tested?" in result
        assert "What happens on timeout?" in result

    def test_no_wander_section_when_empty(self):
        result = render_report(_report_dict())
        assert "Open Questions" not in result

    def test_dod_assessment_rendered(self):
        result = render_report(_report_dict(dod_assessment="All criteria met."))
        assert "All criteria met." in result

    def test_reporter_dispatch_table(self):
        dispatch = [{"reporter": "akira_scan", "status": "completed", "skip_reason": None}]
        result = render_report(_report_dict(reporter_dispatch=dispatch))
        assert "akira_scan" in result
        assert "completed" in result

    def test_overall_understanding_rendered(self):
        result = render_report(_report_dict(overall_understanding="Change adds render-report CLI."))
        assert "Change adds render-report CLI." in result

    def test_multiple_findings_all_present(self):
        findings = [
            make_finding("AK-001", title="Finding one").model_dump(mode="json"),
            make_finding("AK-002", title="Finding two").model_dump(mode="json"),
            make_finding("AK-003", title="Finding three").model_dump(mode="json"),
        ]
        result = render_report(_report_dict(findings=findings))
        assert "AK-001" in result
        assert "AK-002" in result
        assert "AK-003" in result

    def test_invalid_finding_goes_to_parse_errors(self):
        result = render_report(_report_dict(findings=[{"id": "bad", "not_valid": True}]))
        assert "Parse Errors" in result

    def test_impact_badge_blocker(self):
        f = make_finding("AK-001", merge_impact=MergeImpact.BLOCKER)
        result = render_report(_report_dict(findings=[f.model_dump(mode="json")]))
        assert "BLOCKER" in result

    def test_impact_badge_nit(self):
        f = make_finding("AK-001", merge_impact=MergeImpact.NIT, comment_type="nit")
        result = render_report(_report_dict(findings=[f.model_dump(mode="json")]))
        assert "NIT" in result


class TestRenderReportCLI:
    def test_cli_render_report_empty(self):
        data = json.dumps({"findings": []})
        result = subprocess.run(
            ["uv", "run", "review-cli", "render-report"],
            input=data,
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        assert "# Review Report" in result.stdout

    def test_cli_render_report_with_finding(self):
        f = make_finding("AK-001", title="Test finding via CLI")
        data = json.dumps({"findings": [f.model_dump(mode="json")]})
        result = subprocess.run(
            ["uv", "run", "review-cli", "render-report"],
            input=data,
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        assert "AK-001" in result.stdout
        assert "Test finding via CLI" in result.stdout

    def test_cli_render_report_shows_in_help(self):
        result = subprocess.run(
            ["uv", "run", "review-cli", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        assert "render-report" in result.stdout
