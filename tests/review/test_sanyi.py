import pytest

from review.sanyi import violation_merge_impact, violation_source_native
from review.schemas.models import MergeImpact, NativeSeverity, Reporter
from review.validation import validate_finding
from tests.review.conftest import make_finding

# All 11 violation codes with their expected mappings
_ALL_CODES: list[tuple[str, MergeImpact, NativeSeverity]] = [
    ("BY-1", MergeImpact.BLOCKER, NativeSeverity.BLOCKER),
    ("BY-2", MergeImpact.BLOCKER, NativeSeverity.BLOCKER),
    ("BY-3", MergeImpact.BLOCKER, NativeSeverity.BLOCKER),
    ("BY-4", MergeImpact.BLOCKER, NativeSeverity.BLOCKER),
    ("JY-1", MergeImpact.IMPORTANT, NativeSeverity.WARNING),
    ("JY-2", MergeImpact.IMPORTANT, NativeSeverity.WARNING),
    ("JY-3", MergeImpact.IMPORTANT, NativeSeverity.WARNING),
    ("BN-1", MergeImpact.SUGGESTION, NativeSeverity.INFO),
    ("MG-1", MergeImpact.NIT, NativeSeverity.NOTICE),
    ("UN-1", MergeImpact.NIT, NativeSeverity.NOTICE),
    ("UN-2", MergeImpact.NIT, NativeSeverity.NOTICE),
]


class TestViolationMergeImpact:
    @pytest.mark.parametrize("code,expected_impact,_", _ALL_CODES)
    def test_all_codes(self, code, expected_impact, _):
        assert violation_merge_impact(code) == expected_impact

    def test_unknown_code_raises(self):
        with pytest.raises(ValueError, match="Unknown SANYI violation code"):
            violation_merge_impact("XX-9")

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="Unknown SANYI violation code"):
            violation_merge_impact("")


class TestViolationSourceNative:
    @pytest.mark.parametrize("code,_,expected_native", _ALL_CODES)
    def test_all_codes(self, code, _, expected_native):
        assert violation_source_native(code) == expected_native

    def test_unknown_code_raises(self):
        with pytest.raises(ValueError, match="Unknown SANYI violation code"):
            violation_source_native("XX-9")

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="Unknown SANYI violation code"):
            violation_source_native("")


class TestValidateFindingSanyiConsistency:
    def _sanyi_finding(self, code: str, merge_impact: MergeImpact) -> dict:
        f = make_finding(
            id="SY-001",
            reporter=Reporter.SANYI,
            merge_impact=merge_impact,
        )
        # Override severity to include violation_code
        f_dict = f.model_dump(mode="json")
        f_dict["severity"]["violation_code"] = code
        return f_dict

    @pytest.mark.parametrize("code,expected_impact,_", _ALL_CODES)
    def test_consistent_mapping_passes(self, code, expected_impact, _):
        data = self._sanyi_finding(code, expected_impact)
        ok, err = validate_finding(data)
        assert ok, err

    def test_inconsistent_mapping_fails(self):
        # BY-1 must be blocker; passing nit should fail
        data = self._sanyi_finding("BY-1", MergeImpact.NIT)
        ok, err = validate_finding(data)
        assert not ok
        assert "BY-1" in err
        assert "blocker" in err

    def test_sanyi_without_violation_code_passes(self):
        f = make_finding(id="SY-001", reporter=Reporter.SANYI)
        ok, err = validate_finding(f.model_dump(mode="json"))
        assert ok, err

    def test_non_sanyi_with_violation_code_ignored(self):
        # violation_code on a non-SANYI reporter should not trigger the check
        f = make_finding(id="AK-001", reporter=Reporter.AKIRA_SCAN)
        f_dict = f.model_dump(mode="json")
        f_dict["severity"]["violation_code"] = "BY-1"
        # merge_impact is IMPORTANT (from make_finding default) — would fail SANYI check
        # but reporter is not sanyi, so it should pass
        ok, err = validate_finding(f_dict)
        assert ok, err

    def test_unknown_violation_code_fails(self):
        data = self._sanyi_finding("XX-9", MergeImpact.BLOCKER)
        # force an unknown code into the dict
        data["severity"]["violation_code"] = "XX-9"
        ok, err = validate_finding(data)
        assert not ok
        assert "XX-9" in err
