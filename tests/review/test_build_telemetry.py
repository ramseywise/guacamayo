import json

REQUIRED_FIELDS = {"ts", "issue", "repo", "plan", "branch", "stage", "round", "verdict", "outcome"}
VALID_STAGES = {"execute", "review", "fix"}
VALID_OUTCOMES = {
    "started",
    "execute_complete",
    "ship_ready",
    "fix_dispatched",
    "blocked",
    "max_rounds",
    "escalated",
}
VALID_VERDICTS = {"approve", "comment", "request_changes", "insufficient_context", "pending"}


def build_entry(**overrides):
    base = {
        "ts": "2026-08-20T10:00:00Z",
        "issue": 165,
        "repo": "guacamayo",
        "plan": ".claude/docs/plans/2026-08-20-build-orchestrator.md",
        "branch": "GUA-165-build-orchestrator",
        "stage": "review",
        "round": 1,
        "verdict": "approve",
        "outcome": "ship_ready",
    }
    return {**base, **overrides}


def validate_entry(entry: dict) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []
    missing = REQUIRED_FIELDS - entry.keys()
    if missing:
        errors.append(f"Missing fields: {missing}")
    if "round" in entry and not (1 <= entry["round"] <= 3):
        errors.append(f"round {entry['round']} outside [1, 3]")
    if "stage" in entry and entry["stage"] not in VALID_STAGES:
        errors.append(f"invalid stage: {entry['stage']}")
    if "outcome" in entry and entry["outcome"] not in VALID_OUTCOMES:
        errors.append(f"invalid outcome: {entry['outcome']}")
    if "verdict" in entry and entry["verdict"] not in VALID_VERDICTS:
        errors.append(f"invalid verdict: {entry['verdict']}")
    return errors


class TestBuildDecisionSchema:
    def test_valid_entry_passes(self):
        assert validate_entry(build_entry()) == []

    def test_missing_required_field_fails(self):
        entry = build_entry()
        del entry["verdict"]
        assert validate_entry(entry) != []

    def test_round_out_of_range_fails(self):
        assert validate_entry(build_entry(round=0)) != []
        assert validate_entry(build_entry(round=4)) != []

    def test_invalid_stage_fails(self):
        assert validate_entry(build_entry(stage="deploy")) != []

    def test_invalid_outcome_fails(self):
        assert validate_entry(build_entry(outcome="unknown")) != []

    def test_invalid_verdict_fails(self):
        assert validate_entry(build_entry(verdict="reject")) != []

    def test_all_valid_outcomes(self):
        for o in VALID_OUTCOMES:
            assert validate_entry(build_entry(outcome=o)) == [], f"outcome={o}"

    def test_all_valid_verdicts(self):
        for v in VALID_VERDICTS:
            assert validate_entry(build_entry(verdict=v)) == [], f"verdict={v}"

    def test_all_valid_stages(self):
        for s in VALID_STAGES:
            assert validate_entry(build_entry(stage=s)) == [], f"stage={s}"

    def test_roundtrip_json_serialization(self):
        entry = build_entry()
        assert json.loads(json.dumps(entry)) == entry
