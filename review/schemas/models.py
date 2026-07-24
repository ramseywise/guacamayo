from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceState(str, Enum):
    VERIFIED = "verified"
    SUPPORTED = "supported"
    HYPOTHESIS = "hypothesis"
    QUESTION = "question"


class MergeImpact(str, Enum):
    BLOCKER = "blocker"
    IMPORTANT = "important"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    NIT = "nit"


class NativeSeverity(str, Enum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"
    NOTICE = "notice"


class CommentType(str, Enum):
    REQUEST_CHANGE = "request_change"
    QUESTION = "question"
    SUGGESTION = "suggestion"
    NIT = "nit"


class MergeDecision(str, Enum):
    APPROVE = "approve"
    COMMENT = "comment"
    REQUEST_CHANGES = "request_changes"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class Category(str, Enum):
    CORRECTNESS = "correctness"
    RELIABILITY = "reliability"
    SECURITY = "security"
    DATA = "data"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    OPERATIONS = "operations"
    AGENT_BEHAVIOR = "agent_behavior"
    EVALUATION = "evaluation"
    COMMUNICATION = "communication"


class Reporter(str, Enum):
    AKIRA_SCAN = "akira_scan"
    AKIRA_WANDER = "akira_wander"
    SANYI = "sanyi"
    LINT = "lint"
    PLAN_FIDELITY = "plan_fidelity"


class FileLocation(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None

    @model_validator(mode="after")
    def validate_line_range(self) -> FileLocation:
        if (
            self.start_line is not None
            and self.end_line is not None
            and self.end_line < self.start_line
        ):
            raise ValueError(
                f"end_line ({self.end_line}) must be >= start_line ({self.start_line})"
            )
        return self


class Location(BaseModel):
    files: list[FileLocation]
    symbols: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    title: str
    observation: str
    failure_scenario: str | None = None
    impact: str | None = None


class Severity(BaseModel):
    source_native: NativeSeverity | None = None
    merge_impact: MergeImpact
    violation_code: str | None = None


_FINDING_ID_PATTERN = re.compile(r"^[A-Z]{2,}-\d{3,}$")


class ReviewFinding(BaseModel):
    id: str
    reporter: Reporter
    category: Category
    evidence_state: EvidenceState
    location: Location
    claim: Claim
    severity: Severity
    basis: list[str] = Field(default_factory=list)
    comment_type: CommentType
    plan_step: int | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not _FINDING_ID_PATTERN.match(v):
            raise ValueError(f"id {v!r} must match {{SRC}}-{{NNN}} (e.g. AK-001)")
        return v

    @model_validator(mode="after")
    def question_state_constrains_impact(self) -> ReviewFinding:
        if self.evidence_state == EvidenceState.QUESTION and self.severity.merge_impact not in (
            MergeImpact.QUESTION,
            MergeImpact.SUGGESTION,
            MergeImpact.NIT,
        ):
            raise ValueError(
                "evidence_state=question cannot carry "
                f"merge_impact={self.severity.merge_impact.value}"
            )
        return self


class ReporterDispatchEntry(BaseModel):
    reporter: Reporter
    status: str  # completed, skipped, failed
    skip_reason: str | None = None

    @model_validator(mode="after")
    def skipped_requires_reason(self) -> ReporterDispatchEntry:
        if self.status == "skipped" and not self.skip_reason:
            raise ValueError("skip_reason is required when status is 'skipped'")
        return self


class ReviewReport(BaseModel):
    findings: list[ReviewFinding]
    merge_decision: MergeDecision
    reporter_dispatch: list[ReporterDispatchEntry]
    overall_understanding: str
    dod_assessment: str
