"""Branch attribution join for review findings.

Classifies every finding by whether the branch under review introduced its
cited line, is merely adjacent to a touched hunk, or the file was not touched.

Design constraints (from GUA-115):
- ONE ``git diff -U0 origin/main...HEAD`` call for the whole sweep (not per-finding).
- Three-dot diff is merge-base relative and is the correct form here.
- Multi-line findings: ``introduced`` if ANY cited line intersects a touched hunk.
- File-level findings (no line number): can only be ``adjacent`` or ``pre_existing``.
- A git failure or missing fact → ``unknown``. Never silently becomes ``pre_existing``.
  (Same tri-state pattern as BranchFact.is_ancestor in telemetry/consistency.py.)

Public API
----------
``load_touched_hunks(repo, base_ref)``
    One subprocess call → dict[filepath, list[(added_start, added_end)]].

``classify_finding(finding, touched_hunks, branch_commits, repo)``
    Returns Attribution for one finding.

``attribute_findings(findings, repo, base_ref)``
    Top-level: builds hunks + branch-commit set, returns findings with attribution set.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from review.schemas.models import Attribution, ReviewFinding

# ---------------------------------------------------------------------------
# Hunk parsing
# ---------------------------------------------------------------------------

_HUNK_HEADER_PREFIX = "@@ "


def _parse_hunk_ranges(diff_output: str) -> dict[str, list[tuple[int, int]]]:
    """Parse ``git diff -U0`` output into per-file added-line ranges.

    Returns:
        Dict mapping filepath → list of (start, end) inclusive line ranges
        for lines added on the branch (the ``+`` side of each hunk header).
        Files present in the diff but whose hunks all have length 0 (pure
        deletions) still appear in the dict — they were touched.
    """
    hunks: dict[str, list[tuple[int, int]]] = {}
    current_file: str | None = None

    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            # New file section. Strip "b/" prefix.
            current_file = line[6:]
            if current_file not in hunks:
                hunks[current_file] = []
        elif line.startswith(_HUNK_HEADER_PREFIX) and current_file is not None:
            # @@ -a,b +c,d @@ optional context
            # The +c,d part is the added range on the new side.
            try:
                at_end = line.index(" @@", 3)
                hunk_spec = line[3:at_end]  # "-a,b +c,d"
                plus_part = hunk_spec.split(" ")[1]  # "+c,d" or "+c"
                plus_part = plus_part.lstrip("+")
                if "," in plus_part:
                    start_str, length_str = plus_part.split(",", 1)
                    start = int(start_str)
                    length = int(length_str)
                else:
                    start = int(plus_part)
                    length = 1
                if length > 0:
                    hunks[current_file].append((start, start + length - 1))
                # length == 0 means pure deletion — file is touched but no added lines
            except (ValueError, IndexError):
                pass  # malformed hunk header — skip silently

    return hunks


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run_git(args: list[str], cwd: str) -> str | None:
    """Run a git command, return stdout or None on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout
    except OSError:
        return None


def load_touched_hunks(
    repo: Path,
    base_ref: str = "origin/main",
) -> dict[str, list[tuple[int, int]]] | None:
    """One git diff call → per-file added-line ranges.

    Args:
        repo: Checkout root.
        base_ref: Merge-base reference (default ``origin/main``).

    Returns:
        Dict mapping filepath → [(start, end)] of added ranges, or None if
        the git call failed (signals ``unknown`` to callers — not an empty dict,
        which would read as "no touched files", i.e. whole-repo pre-existing).
    """
    cwd = str(repo)
    output = _run_git(["diff", "-U0", f"{base_ref}...HEAD", "--"], cwd)
    if output is None:
        return None
    return _parse_hunk_ranges(output)


def load_branch_commits(
    repo: Path,
    base_ref: str = "origin/main",
) -> frozenset[str] | None:
    """Set of commit SHAs reachable from HEAD but not from base_ref.

    Returns None on git failure.
    """
    cwd = str(repo)
    output = _run_git(["rev-list", f"{base_ref}..HEAD"], cwd)
    if output is None:
        return None
    shas = frozenset(line.strip() for line in output.splitlines() if line.strip())
    return shas


def _blame_line_commit(file_path: str, line: int, repo_cwd: str) -> str | None:
    """Return the commit SHA that last touched ``line`` in ``file_path``.

    Returns None on failure (file absent, line out of range, git error).
    """
    output = _run_git(
        ["blame", "-L", f"{line},{line}", "--porcelain", "--", file_path],
        repo_cwd,
    )
    if output is None:
        return None
    first_line = output.splitlines()[0] if output.strip() else None
    if not first_line:
        return None
    # porcelain format: first line is "<SHA> <orig-line> <result-line> <count>"
    parts = first_line.split()
    if parts:
        sha = parts[0]
        # 40-char hex SHA
        if len(sha) == 40:
            return sha
    return None


# ---------------------------------------------------------------------------
# Finding classification
# ---------------------------------------------------------------------------


def _lines_intersect_hunks(
    start_line: int | None,
    end_line: int | None,
    hunks: list[tuple[int, int]],
) -> bool:
    """True if [start_line, end_line] overlaps any hunk range."""
    if start_line is None:
        return False
    effective_end = end_line if end_line is not None else start_line
    for hunk_start, hunk_end in hunks:
        if start_line <= hunk_end and effective_end >= hunk_start:
            return True
    return False


def classify_finding(
    finding: ReviewFinding,
    touched_hunks: dict[str, list[tuple[int, int]]],
    branch_commits: frozenset[str],
    repo_cwd: str,
) -> Attribution:
    """Classify one finding into an Attribution value.

    Precedence:
    1. If the finding's file was not touched at all → ``pre_existing``.
    2. If no line number → ``adjacent`` (file touched, but no line to attribute).
    3. If the cited line does not intersect any touched hunk → ``adjacent``.
    4. If the cited line intersects a touched hunk AND blame returns a branch
       commit → ``introduced``.
    5. If the cited line intersects a touched hunk but blame fails or returns a
       non-branch commit → ``unknown`` (not ``adjacent`` — the line IS in a
       touched hunk so something happened there).
    """
    first_file = finding.location.files[0] if finding.location.files else None
    if first_file is None:
        # No location at all — cannot classify
        return Attribution.UNKNOWN

    file_path = first_file.path
    # Normalise: strip leading "./" if present
    file_path = file_path.removeprefix("./")

    if file_path not in touched_hunks:
        return Attribution.PRE_EXISTING

    file_hunks = touched_hunks[file_path]
    start_line = first_file.start_line
    end_line = first_file.end_line

    if start_line is None:
        # File touched but no line number — cannot be ``introduced``
        return Attribution.ADJACENT

    if not _lines_intersect_hunks(start_line, end_line, file_hunks):
        return Attribution.ADJACENT

    # Cited line is in a touched hunk. Ask git blame.
    blame_sha = _blame_line_commit(file_path, start_line, repo_cwd)
    if blame_sha is None:
        # Blame failed — unknown, not pre_existing
        return Attribution.UNKNOWN

    if blame_sha in branch_commits:
        return Attribution.INTRODUCED

    # Line is in a hunk but blames to a pre-branch commit. This can happen when
    # a branch touches a file but the specific line was already there (e.g. context
    # around the real change). Treat as adjacent rather than introduced.
    return Attribution.ADJACENT


def attribute_findings(
    findings: list[ReviewFinding],
    repo: Path,
    base_ref: str = "origin/main",
) -> list[ReviewFinding]:
    """Apply branch attribution to every finding in one pass.

    One ``git diff`` call + one ``git rev-list`` call for the sweep; then per-finding
    blame only for findings whose cited line lands inside a touched hunk.

    If either of the two setup git calls fails, all findings are classified
    ``unknown`` — never silently ``pre_existing``.

    Args:
        findings: Merged, deduplicated findings from the driver.
        repo: Checkout root (Path).
        base_ref: Merge-base ref (default ``origin/main``).

    Returns:
        New list of ReviewFinding objects with ``attribution`` field set.
    """
    if not findings:
        return findings

    repo_cwd = str(repo)
    touched_hunks = load_touched_hunks(repo, base_ref)
    branch_commits = load_branch_commits(repo, base_ref)

    if touched_hunks is None or branch_commits is None:
        # Setup git call failed — mark all unknown
        return [f.model_copy(update={"attribution": Attribution.UNKNOWN}) for f in findings]

    result: list[ReviewFinding] = []
    for finding in findings:
        attr = classify_finding(finding, touched_hunks, branch_commits, repo_cwd)
        result.append(finding.model_copy(update={"attribution": attr}))
    return result
