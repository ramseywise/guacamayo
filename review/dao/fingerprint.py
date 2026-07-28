"""Fingerprint-based finding identity across sweeps.

A fingerprint is a stable SHA-256 digest derived from:
    ``<file_path>|<start_line>|<category>|<reporter>|<title>``

This lets us match the same real-world issue across successive sweeps even when
the assigned finding ID (e.g. CR-001) changes.

Public API
----------
make_fingerprint(finding) -> FindingFingerprint
    Build a fingerprint from a ReviewFinding.

compare_sweeps(previous, current) -> tuple[new, resolved, recurring]
    Diff two SweepRecords; return three lists of SweepFindings.

load_sweep(path) -> SweepRecord | None
    Read a SweepRecord from a JSON file; return None if file is missing.

save_sweep(record, path)
    Write a SweepRecord as JSON to *path* (creates parent dirs).

fingerprint_from_review_finding(finding) -> str
    Convenience: return just the digest string.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from review.schemas.models import (
    FindingFingerprint,
    ReviewFinding,
    SweepFinding,
    SweepRecord,
)


def _digest(
    file_path: str, start_line: int | None, category: str, reporter: str, title: str
) -> str:
    key = f"{file_path}|{start_line}|{category}|{reporter}|{title}"
    return hashlib.sha256(key.encode()).hexdigest()


def make_fingerprint(finding: ReviewFinding) -> FindingFingerprint:
    """Build a FindingFingerprint from a ReviewFinding."""
    first_file = finding.location.files[0] if finding.location.files else None
    file_path = first_file.path if first_file else ""
    start_line = first_file.start_line if first_file else None
    category = finding.category.value
    reporter = finding.reporter.value
    title = finding.claim.title

    digest = _digest(file_path, start_line, category, reporter, title)
    return FindingFingerprint(
        digest=digest,
        file_path=file_path,
        start_line=start_line,
        category=category,
        reporter=reporter,
        title=title,
    )


def fingerprint_from_review_finding(finding: ReviewFinding) -> str:
    """Return just the digest string for a ReviewFinding."""
    return make_fingerprint(finding).digest


def finding_to_sweep_finding(finding: ReviewFinding) -> SweepFinding:
    """Convert a ReviewFinding to a SweepFinding (snapshot for storage)."""
    fp = make_fingerprint(finding)
    return SweepFinding(
        fingerprint=fp.digest,
        finding_id=finding.id,
        file_path=fp.file_path,
        start_line=fp.start_line,
        category=fp.category,
        reporter=fp.reporter,
        title=fp.title,
        merge_impact=finding.severity.merge_impact.value,
        evidence_state=finding.evidence_state.value,
    )


def compare_sweeps(
    previous: SweepRecord,
    current: SweepRecord,
) -> tuple[list[SweepFinding], list[SweepFinding], list[SweepFinding]]:
    """Compare two consecutive SweepRecords.

    Returns (new_findings, resolved_findings, recurring_findings).

    - **new**: digest in current but not in previous
    - **resolved**: digest in previous but not in current
    - **recurring**: digest in both previous and current
    """
    prev_digests: dict[str, SweepFinding] = {f.fingerprint: f for f in previous.findings}
    curr_digests: dict[str, SweepFinding] = {f.fingerprint: f for f in current.findings}

    prev_set = set(prev_digests)
    curr_set = set(curr_digests)

    new_findings = [curr_digests[d] for d in sorted(curr_set - prev_set)]
    resolved_findings = [prev_digests[d] for d in sorted(prev_set - curr_set)]
    recurring_findings = [curr_digests[d] for d in sorted(curr_set & prev_set)]

    return new_findings, resolved_findings, recurring_findings


def load_sweep(path: Path) -> SweepRecord | None:
    """Load a SweepRecord from a JSON file.

    Returns None if the file does not exist.
    """
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return SweepRecord.model_validate(data)


def save_sweep(record: SweepRecord, path: Path) -> None:
    """Write a SweepRecord as JSON, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2))


def latest_sweep_path(reviews_dir: Path, repo: str) -> Path | None:
    """Return the most recently modified sweep JSON for *repo* in *reviews_dir*.

    Files are expected to be named ``{repo}-{date}.json`` or
    ``{repo}-{date}-{n}.json``.  Returns None if no sweep exists.
    """
    candidates = sorted(
        reviews_dir.glob(f"{repo}-*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    return candidates[-1] if candidates else None
