# Backward-compat shim — canonical location is review.dao.commit_verification
from review.dao.commit_verification import (  # noqa: F401
    StepVerification,
    parse_plan_steps,
    verify_commits,
)
