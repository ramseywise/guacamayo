from pydantic import ValidationError

from review.schemas.models import ReviewFinding, ReviewReport


def validate_finding(data: dict) -> tuple[bool, str]:
    try:
        ReviewFinding.model_validate(data)
        return True, ""
    except ValidationError as e:
        return False, e.json()


def validate_report(data: dict) -> tuple[bool, str]:
    try:
        ReviewReport.model_validate(data)
        return True, ""
    except ValidationError as e:
        return False, e.json()
