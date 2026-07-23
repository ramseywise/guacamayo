import json
import subprocess

from review.schemas.models import MergeDecision, Reporter, ReporterDispatchEntry
from review.validation import validate_finding, validate_report
from tests.review.conftest import make_finding


class TestValidateFinding:
    def test_valid_finding(self):
        f = make_finding()
        ok, err = validate_finding(f.model_dump(mode="json"))
        assert ok
        assert err == ""

    def test_invalid_finding(self):
        ok, err = validate_finding({"id": "bad"})
        assert not ok
        assert "id" in err or "reporter" in err

    def test_valid_report(self):
        f = make_finding()
        report = {
            "findings": [f.model_dump(mode="json")],
            "merge_decision": MergeDecision.COMMENT.value,
            "reporter_dispatch": [
                ReporterDispatchEntry(reporter=Reporter.AKIRA_SCAN, status="completed").model_dump(
                    mode="json"
                )
            ],
            "overall_understanding": "Test",
            "dod_assessment": "Met",
        }
        ok, _err = validate_report(report)
        assert ok

    def test_malformed_input(self):
        ok, err = validate_finding({"not_a_valid_field": True})
        assert not ok
        assert err != ""


class TestValidateCLI:
    def test_cli_valid_finding(self):
        f = make_finding()
        data = json.dumps(f.model_dump(mode="json"))
        result = subprocess.run(
            ["uv", "run", "review-cli", "validate-finding"],
            input=data,
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 0
        assert "valid" in result.stdout

    def test_cli_invalid_finding(self):
        result = subprocess.run(
            ["uv", "run", "review-cli", "validate-finding"],
            input='{"id": "bad"}',
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        assert result.returncode == 1
