from __future__ import annotations

import re
from enum import Enum
from typing import Literal

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
    """Finding sources.

    The dimension reporters mirror the ``review-*`` skill family in galactus, which
    is canonical for dimension vocabulary. Legacy values predate that reconciliation
    and are retained only so historical sweep records still deserialize.
    """

    # Deprecated — retired 2026-08-11 with the akira/sanyi generation.
    # Never emitted by the driver; kept so persisted findings still parse.
    AKIRA_SCAN = "akira_scan"
    AKIRA_WANDER = "akira_wander"
    SANYI = "sanyi"  # superseded by CONTRACTS, which carries the violation-code check
    # Non-dimension reporters (no prefix constraint)
    LINT = "lint"
    PLAN_FIDELITY = "plan_fidelity"
    # Dimension reporters — one per galactus review-* skill
    CORRECTNESS = "correctness"
    INTENT = "intent"
    ARCHITECTURE = "architecture"
    SAFETY = "safety"
    CONTRACTS = "contracts"
    TESTING = "testing"
    RUNTIME = "runtime"
    SAFEGUARDS = "safeguards"
    SILENT_FAILURE = "silent_failure"
    LEAKAGE = "leakage"
    PERFORMANCE = "performance"
    WANDER = "wander"


# Reporters retired 2026-08-11. Retained in the enum for backward-compatible
# deserialization of existing sweep records; the driver never dispatches them.
DEPRECATED_REPORTERS: frozenset[Reporter] = frozenset(
    {
        Reporter.AKIRA_SCAN,
        Reporter.AKIRA_WANDER,
        Reporter.SANYI,
    }
)


# Maps dimension reporter → expected ID prefix (e.g. correctness → "CR")
REPORTER_ID_PREFIX: dict[str, str] = {
    Reporter.CORRECTNESS: "CR",
    Reporter.INTENT: "IN",
    Reporter.ARCHITECTURE: "AR",
    Reporter.SAFETY: "SF",
    Reporter.CONTRACTS: "CT",
    Reporter.TESTING: "TE",
    Reporter.RUNTIME: "RT",
    Reporter.SAFEGUARDS: "SG",
    Reporter.SILENT_FAILURE: "SI",
    Reporter.LEAKAGE: "LK",
    Reporter.PERFORMANCE: "PF",
    Reporter.WANDER: "WD",
}


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
    def dimension_id_prefix_matches_reporter(self) -> ReviewFinding:
        expected = REPORTER_ID_PREFIX.get(self.reporter)
        if expected is not None:
            actual_prefix = self.id.split("-")[0]
            if actual_prefix != expected:
                raise ValueError(
                    f"reporter={self.reporter.value!r} requires id prefix {expected!r}, "
                    f"got {actual_prefix!r} in id={self.id!r}"
                )
        return self

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


# ---------------------------------------------------------------------------
# Phase 3a — temporal / fingerprint models
# ---------------------------------------------------------------------------


class FindingFingerprint(BaseModel):
    """Stable identity key for a finding across sweeps.

    The fingerprint is derived deterministically from finding content so the same
    real-world issue maps to the same key regardless of which sweep produced it.
    The ``digest`` field holds the hex SHA-256 of
    ``<file_path>|<start_line>|<category>|<reporter>|<title>``.
    """

    digest: str  # hex SHA-256
    file_path: str
    start_line: int | None
    category: str
    reporter: str
    title: str


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    UNKNOWN = "unknown"  # fewer than 2 data points


class DimensionTrend(BaseModel):
    """Trend for a single dimension across sweeps."""

    dimension: str
    repo: str
    counts: list[int] = Field(default_factory=list)  # oldest → newest
    direction: TrendDirection = TrendDirection.UNKNOWN


class SweepFinding(BaseModel):
    """A finding captured as part of a sweep record (serialisable snapshot)."""

    fingerprint: str  # digest from FindingFingerprint
    finding_id: str
    file_path: str
    start_line: int | None = None
    category: str
    reporter: str
    title: str
    merge_impact: str
    evidence_state: str


class SweepRecord(BaseModel):
    """One sweep run for a single repo.

    Written to ``.claude/docs/reviews/`` as
    ``{repo}-{YYYY-MM-DD}.json`` (or with a counter suffix when multiple
    sweeps run on the same day).
    """

    repo: str
    sweep_date: str  # ISO date YYYY-MM-DD
    findings: list[SweepFinding] = Field(default_factory=list)


class TrendReport(BaseModel):
    """Diff between two consecutive sweeps for a repo."""

    repo: str
    from_date: str
    to_date: str
    new_findings: list[SweepFinding] = Field(default_factory=list)
    resolved_findings: list[SweepFinding] = Field(default_factory=list)
    recurring_findings: list[SweepFinding] = Field(default_factory=list)
    dimension_trends: list[DimensionTrend] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Static analysis (Layer 1) result
# ---------------------------------------------------------------------------


class StaticAnalysisResult(BaseModel):
    """Result of running a static analysis (lint) tool in check mode.

    This is a *separate* model from ReviewFinding — it never enters all_findings,
    find_duplicate_clusters, or sweep persistence. It is carried on DriverResult and
    rendered in its own report section, tagged as tool-verified.
    """

    tool: str | None
    status: Literal["ok", "violations", "not_detected", "tool_unavailable", "failed"]
    command: list[str] = Field(default_factory=list)
    exit_code: int | None = None
    violation_count: int = 0
    raw_output: str = ""
    scoped: bool = True
    detail: str | None = None
