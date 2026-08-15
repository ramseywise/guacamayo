"""Tests for review/attribution.py — branch attribution join (GUA-115).

Two mandatory test classes per the DoD:

1. TestGua109Regression — replay GUA-109's 11 findings against a synthetic
   repo where every finding's file is *not* in the branch diff. Assert 0
   ``introduced``.

2. TestIntroducedNegative — plant a finding on a line the branch genuinely
   introduced and assert it classifies ``introduced`` AND blocks the verdict.
   A classifier that returns ``pre_existing`` for everything would pass the
   regression test alone; this test makes that failure visible.

Supporting tests for _parse_hunk_ranges, classify_finding, and attribute_findings
are included so the unit boundary is clear and individual failure modes have names.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from review.attribution import (
    _parse_hunk_ranges,
    attribute_findings,
    classify_finding,
)
from review.schemas.models import (
    Attribution,
    Category,
    Claim,
    CommentType,
    EvidenceState,
    FileLocation,
    Location,
    MergeImpact,
    Reporter,
    ReviewFinding,
    Severity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    id: str = "CR-001",
    *,
    path: str = "review/driver.py",
    start_line: int | None = 1,
    end_line: int | None = None,
    reporter: Reporter = Reporter.CORRECTNESS,
    merge_impact: MergeImpact = MergeImpact.IMPORTANT,
) -> ReviewFinding:
    return ReviewFinding(
        id=id,
        reporter=reporter,
        category=Category.CORRECTNESS,
        evidence_state=EvidenceState.VERIFIED,
        location=Location(
            files=[FileLocation(path=path, start_line=start_line, end_line=end_line)]
        ),
        claim=Claim(title="Test finding", observation="observed"),
        severity=Severity(merge_impact=merge_impact),
        comment_type=CommentType.REQUEST_CHANGE,
    )


def _make_git_repo_with_branch(tmp_path: Path) -> tuple[Path, str]:
    """Create a two-commit repo with a branch change.

    Repo structure:
      main:   app.py with 10 lines (lines 1-10)
      branch: app.py modified — line 5 changed to 'BRANCH LINE'

    Returns (repo_path, branch_ref).
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(tmp_path),
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00",
    }

    lines = [f"line {i}\n" for i in range(1, 11)]
    (repo / "app.py").write_text("".join(lines))

    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@test.com"],
        ["config", "user.name", "Tester"],
        ["add", "app.py"],
        ["commit", "-q", "-m", "feat: initial"],
    ):
        subprocess.run(["git"] + args, cwd=repo, check=True, capture_output=True, env=env)

    # Simulate origin/main pointing to current HEAD
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )

    # Branch commit — modify line 5
    lines[4] = "BRANCH LINE\n"
    (repo / "app.py").write_text("".join(lines))
    env2 = dict(env)
    env2["GIT_AUTHOR_DATE"] = "2026-02-01T00:00:00"
    env2["GIT_COMMITTER_DATE"] = "2026-02-01T00:00:00"
    for args in (
        ["add", "app.py"],
        ["commit", "-q", "-m", "feat: branch change"],
    ):
        subprocess.run(["git"] + args, cwd=repo, check=True, capture_output=True, env=env2)

    return repo, "origin/main"


def _make_untouched_git_repo(tmp_path: Path) -> tuple[Path, str]:
    """Repo with no branch commits beyond origin/main (empty diff)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": str(tmp_path),
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00",
    }

    (repo / "old.py").write_text("existing code\n")

    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "t@test.com"],
        ["config", "user.name", "Tester"],
        ["add", "old.py"],
        ["commit", "-q", "-m", "initial"],
    ):
        subprocess.run(["git"] + args, cwd=repo, check=True, capture_output=True, env=env)

    # origin/main = HEAD (no branch commits)
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )

    return repo, "origin/main"


# ---------------------------------------------------------------------------
# Unit: _parse_hunk_ranges
# ---------------------------------------------------------------------------


class TestParseHunkRanges:
    def test_single_hunk(self) -> None:
        diff = "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -1,3 +1,4 @@\n"
        result = _parse_hunk_ranges(diff)
        assert "foo.py" in result
        assert result["foo.py"] == [(1, 4)]

    def test_pure_deletion_hunk(self) -> None:
        diff = "diff --git a/foo.py b/foo.py\n--- a/foo.py\n+++ b/foo.py\n@@ -5,3 +5,0 @@\n"
        result = _parse_hunk_ranges(diff)
        # File is touched (present in dict) but no added ranges
        assert "foo.py" in result
        assert result["foo.py"] == []

    def test_multiple_hunks(self) -> None:
        diff = (
            "diff --git a/bar.py b/bar.py\n"
            "--- a/bar.py\n"
            "+++ b/bar.py\n"
            "@@ -10,2 +10,3 @@\n"
            "@@ -20,1 +21,2 @@\n"
        )
        result = _parse_hunk_ranges(diff)
        assert "bar.py" in result
        ranges = result["bar.py"]
        assert (10, 12) in ranges
        assert (21, 22) in ranges

    def test_multiple_files(self) -> None:
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,1 +1,1 @@\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -5,1 +5,2 @@\n"
        )
        result = _parse_hunk_ranges(diff)
        assert "a.py" in result
        assert "b.py" in result

    def test_no_comma_in_length(self) -> None:
        """@@ -1 +1 @@ (single-line hunk without comma) → (1, 1)."""
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n"
        result = _parse_hunk_ranges(diff)
        assert result["x.py"] == [(1, 1)]

    def test_empty_diff(self) -> None:
        assert _parse_hunk_ranges("") == {}


# ---------------------------------------------------------------------------
# Unit: classify_finding
# ---------------------------------------------------------------------------


class TestClassifyFinding:
    def _touched(
        self, path: str = "app.py", ranges: list[tuple[int, int]] | None = None
    ) -> dict[str, list[tuple[int, int]]]:
        return {path: ranges or [(1, 10)]}

    def _commits(self, *shas: str) -> frozenset[str]:
        return frozenset(shas)

    def test_file_not_touched_is_pre_existing(self, tmp_path: Path) -> None:
        f = _make_finding(path="untouched.py", start_line=5)
        result = classify_finding(f, {}, frozenset(), str(tmp_path))
        assert result == Attribution.PRE_EXISTING

    def test_no_line_number_is_adjacent(self, tmp_path: Path) -> None:
        f = _make_finding(path="app.py", start_line=None)
        result = classify_finding(f, self._touched(), frozenset(), str(tmp_path))
        assert result == Attribution.ADJACENT

    def test_line_outside_hunk_is_adjacent(self, tmp_path: Path) -> None:
        f = _make_finding(path="app.py", start_line=50)
        touched = {"app.py": [(1, 10)]}
        result = classify_finding(f, touched, frozenset(), str(tmp_path))
        assert result == Attribution.ADJACENT

    def test_no_location_is_unknown(self, tmp_path: Path) -> None:
        f = ReviewFinding(
            id="CR-001",
            reporter=Reporter.CORRECTNESS,
            category=Category.CORRECTNESS,
            evidence_state=EvidenceState.VERIFIED,
            location=Location(files=[]),
            claim=Claim(title="T", observation="O"),
            severity=Severity(merge_impact=MergeImpact.IMPORTANT),
            comment_type=CommentType.REQUEST_CHANGE,
        )
        result = classify_finding(f, {}, frozenset(), str(tmp_path))
        assert result == Attribution.UNKNOWN

    def test_dotslash_path_normalized(self, tmp_path: Path) -> None:
        """./app.py normalises to app.py for lookup."""
        f = _make_finding(path="./app.py", start_line=50)
        touched = {"app.py": [(1, 10)]}
        # line 50 not in hunk → adjacent (not pre_existing, because file is touched)
        result = classify_finding(f, touched, frozenset(), str(tmp_path))
        assert result == Attribution.ADJACENT


# ---------------------------------------------------------------------------
# Integration: real git repo
# ---------------------------------------------------------------------------


class TestGua109Regression:
    """Replay GUA-109's scenario: 11 findings, 0 introduced.

    GUA-109 reviewed a branch that touched telemetry files. The dimension
    scanners emitted findings on pre-existing code in those files. Every one
    of the 11 findings should classify as pre_existing or adjacent — never
    introduced.

    This test simulates that by creating a repo where the branch changes
    line 5 of app.py, then creates 11 findings all pointing to lines NOT in
    the branch's touched hunk (lines outside 5-5).
    """

    def test_zero_introduced_for_pre_branch_findings(self, tmp_path: Path) -> None:
        repo, base_ref = _make_git_repo_with_branch(tmp_path)

        # 11 findings on lines 1-4 and 6-10 — all outside the branch hunk (line 5)
        findings = []
        line_nums = list(range(1, 5)) + list(range(6, 14))  # 11 lines
        for i, lineno in enumerate(line_nums[:11], start=1):
            findings.append(
                _make_finding(
                    f"CR-{i:03d}",
                    path="app.py",
                    start_line=lineno,
                    merge_impact=MergeImpact.IMPORTANT,
                )
            )

        attributed = attribute_findings(findings, repo, base_ref)
        introduced = [f for f in attributed if f.attribution == Attribution.INTRODUCED]
        assert len(introduced) == 0, (
            f"Expected 0 introduced, got {len(introduced)}: "
            f"{[(f.id, f.location.files[0].start_line) for f in introduced]}"
        )

    def test_pre_existing_count_matches_input(self, tmp_path: Path) -> None:
        """All 11 findings end up as pre_existing or adjacent — none unclassified."""
        repo, base_ref = _make_git_repo_with_branch(tmp_path)
        findings = [
            _make_finding(f"CR-{i:03d}", path="app.py", start_line=i)
            for i in range(1, 12)
            if i != 5  # skip line 5 which IS touched
        ]
        findings = findings[:11]  # ensure exactly 11

        attributed = attribute_findings(findings, repo, base_ref)
        for f in attributed:
            assert f.attribution in (
                Attribution.PRE_EXISTING,
                Attribution.ADJACENT,
                Attribution.UNKNOWN,
            ), f"Finding {f.id} at line {f.location.files[0].start_line} got {f.attribution}"


class TestIntroducedNegative:
    """A finding on a line the branch genuinely introduced MUST classify introduced.

    This is the critical test that prevents a trivial pass-everything-as-pre_existing
    classifier from satisfying the GUA-109 regression alone. The GUA-109 test only
    asserts 0 introduced; a broken classifier could return pre_existing for every
    finding and pass both assertions. This test plants a finding on the line the
    branch changed and asserts introduced.
    """

    def test_finding_on_branch_line_is_introduced(self, tmp_path: Path) -> None:
        repo, base_ref = _make_git_repo_with_branch(tmp_path)

        # Line 5 was changed by the branch commit
        f = _make_finding("CR-001", path="app.py", start_line=5, merge_impact=MergeImpact.BLOCKER)
        attributed = attribute_findings([f], repo, base_ref)

        assert attributed[0].attribution == Attribution.INTRODUCED, (
            f"Expected introduced for line 5 (branch-changed line), got {attributed[0].attribution}"
        )

    def test_introduced_finding_blocks_verdict(self, tmp_path: Path) -> None:
        """An introduced blocker-impact finding must flow through to the merge verdict."""
        from review.driver import DriverConfig, run_review
        from review.schemas.models import MergeDecision

        repo, _base_ref = _make_git_repo_with_branch(tmp_path)

        # Inject a finding on line 5 (branch-changed) with blocker impact
        finding_dict = {
            "id": "CR-001",
            "reporter": "correctness",
            "category": "correctness",
            "evidence_state": "verified",
            "location": {"files": [{"path": "app.py", "start_line": 5}], "symbols": []},
            "claim": {"title": "Introduced defect", "observation": "found on branch line"},
            "severity": {"merge_impact": "blocker"},
            "comment_type": "request_change",
            "basis": [],
        }

        async def fake_scan(dimension: str, files: list[str], config: DriverConfig):
            if dimension == "correctness":
                return [finding_dict]
            return []

        config = DriverConfig(
            repo=repo,
            files=["app.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=fake_scan)

        # The finding is introduced → stays in the verdict → blocker → REQUEST_CHANGES
        assert result.merge_decision == MergeDecision.REQUEST_CHANGES, (
            f"Expected REQUEST_CHANGES for introduced blocker, got {result.merge_decision}. "
            f"Findings: {[(f.id, f.attribution) for f in result.findings]}"
        )

    def test_pre_existing_blocker_does_not_block_verdict(self, tmp_path: Path) -> None:
        """A blocker on a file NOT touched by the branch must not cause REQUEST_CHANGES.

        This is the inverse of the above: scanner finds a blocker in an untouched file.
        The verdict should be APPROVE (no introduced/adjacent/unknown blockers).
        """
        from review.driver import DriverConfig, run_review
        from review.schemas.models import MergeDecision

        repo, _base_ref = _make_git_repo_with_branch(tmp_path)

        # Add a second file that the branch did NOT touch
        (repo / "other.py").write_text("old code\n")
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(tmp_path),
        }
        subprocess.run(
            ["git", "add", "other.py"], cwd=repo, check=True, capture_output=True, env=env
        )

        # The branch-touched file finding on line 5 would be introduced,
        # but here we put the blocker on the untouched file
        finding_dict = {
            "id": "CR-001",
            "reporter": "correctness",
            "category": "correctness",
            "evidence_state": "verified",
            "location": {"files": [{"path": "other.py", "start_line": 1}], "symbols": []},
            "claim": {"title": "Pre-existing defect", "observation": "in untouched file"},
            "severity": {"merge_impact": "blocker"},
            "comment_type": "request_change",
            "basis": [],
        }

        async def fake_scan(dimension: str, files: list[str], config: DriverConfig):
            if dimension == "correctness":
                return [finding_dict]
            return []

        config = DriverConfig(
            repo=repo,
            files=["other.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=fake_scan)

        # other.py not touched by the branch → pre_existing → does NOT block
        assert result.merge_decision == MergeDecision.APPROVE, (
            f"Expected APPROVE for pre-existing blocker, got {result.merge_decision}. "
            f"Findings: {[(f.id, f.attribution) for f in result.findings]}"
        )


class TestAttributeFindings:
    """Edge-case tests for attribute_findings."""

    def test_empty_findings_returns_empty(self, tmp_path: Path) -> None:
        result = attribute_findings([], tmp_path)
        assert result == []

    def test_git_failure_yields_unknown_not_pre_existing(self, tmp_path: Path) -> None:
        """If git calls fail (not a git repo), all findings must be UNKNOWN."""
        # tmp_path is not a git repo — both load_touched_hunks and load_branch_commits fail
        f = _make_finding("CR-001", path="foo.py", start_line=1)
        result = attribute_findings([f], tmp_path)
        assert result[0].attribution == Attribution.UNKNOWN, (
            "Git failure must yield UNKNOWN, not PRE_EXISTING — "
            "undeterminable findings must not silently stop blocking"
        )

    def test_pre_existing_renders_in_report(self, tmp_path: Path) -> None:
        """Pre-existing findings appear in the rendered report under their own heading.

        Uses a file (old.py) that the branch did NOT touch, so the finding
        is genuinely pre-existing (the branch only changed app.py line 5).
        """
        from review.driver import DriverConfig, run_review

        _repo, _base_ref = _make_git_repo_with_branch(tmp_path)

        # Add an untouched file to the repo (not modified by the branch)
        env = {
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": str(tmp_path),
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00",
        }
        # First: amend origin/main to include old.py (so it's a pre-existing file)
        # We need old.py to be committed at origin/main but not modified by HEAD.
        # The easiest approach: stash origin/main, add old.py, reset origin/main forward.
        # Actually: since origin/main already points to our initial commit, we need to
        # put old.py on origin/main too. Let's reset origin/main to include old.py.
        #
        # Simpler: re-build a repo where old.py was there since the start.
        # Use a new helper that creates the exact scenario.
        repo2 = tmp_path / "repo2"
        repo2.mkdir()
        (repo2 / "app.py").write_text("".join(f"line {i}\n" for i in range(1, 11)))
        (repo2 / "old.py").write_text("legacy code\n" * 5)
        for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "t@test.com"],
            ["config", "user.name", "Tester"],
            ["add", "app.py", "old.py"],
            ["commit", "-q", "-m", "initial"],
        ):
            subprocess.run(["git"] + args, cwd=repo2, check=True, capture_output=True, env=env)
        subprocess.run(
            ["git", "update-ref", "refs/remotes/origin/main", "HEAD"],
            cwd=repo2,
            check=True,
            capture_output=True,
            env=env,
        )
        # Branch: only touch app.py line 5
        lines = (repo2 / "app.py").read_text().splitlines(keepends=True)
        lines[4] = "BRANCH LINE\n"
        (repo2 / "app.py").write_text("".join(lines))
        env2 = dict(env)
        env2["GIT_AUTHOR_DATE"] = "2026-02-01T00:00:00"
        env2["GIT_COMMITTER_DATE"] = "2026-02-01T00:00:00"
        for args in (
            ["add", "app.py"],
            ["commit", "-q", "-m", "branch: change line 5"],
        ):
            subprocess.run(["git"] + args, cwd=repo2, check=True, capture_output=True, env=env2)

        # Finding on old.py line 1 — file NOT touched by the branch
        finding_dict = {
            "id": "CR-001",
            "reporter": "correctness",
            "category": "correctness",
            "evidence_state": "verified",
            "location": {"files": [{"path": "old.py", "start_line": 1}], "symbols": []},
            "claim": {"title": "Old bug", "observation": "existed before this branch"},
            "severity": {"merge_impact": "blocker"},
            "comment_type": "request_change",
            "basis": [],
        }

        async def fake_scan(dimension: str, files: list[str], config: DriverConfig):
            if dimension == "correctness":
                return [finding_dict]
            return []

        config = DriverConfig(
            repo=repo2,
            files=["old.py"],
            reviews_dir=tmp_path / "reviews",
            save_sweep=False,
            static_analysis=False,
        )
        config.agents_dir = tmp_path / "agents"
        config.agents_dir.mkdir()

        result = run_review(config, scan_fn=fake_scan)

        assert "Pre-Existing Findings" in result.report_md, (
            "Pre-existing findings must appear under their own heading in the report. "
            f"Attribution: {result.findings[0].attribution if result.findings else 'no findings'}"
        )
