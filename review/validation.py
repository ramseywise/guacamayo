from pydantic import ValidationError

from review.sanyi import violation_merge_impact
from review.schemas.models import Reporter, ReviewFinding, ReviewReport


def validate_finding(data: dict) -> tuple[bool, str]:
    try:
        finding = ReviewFinding.model_validate(data)
    except ValidationError as e:
        return False, e.json()

    if finding.reporter == Reporter.SANYI and finding.severity.violation_code:
        code = finding.severity.violation_code
        try:
            expected = violation_merge_impact(code)
        except ValueError as e:
            return False, str(e)
        if finding.severity.merge_impact != expected:
            return False, (
                f"SANYI finding with violation_code={code!r} must have "
                f"merge_impact={expected.value!r}, "
                f"got {finding.severity.merge_impact.value!r}"
            )

    return True, ""


def validate_report(data: dict) -> tuple[bool, str]:
    try:
        ReviewReport.model_validate(data)
        return True, ""
    except ValidationError as e:
        return False, e.json()
