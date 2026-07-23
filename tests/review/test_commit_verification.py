import json
import subprocess
import textwrap

import pytest

from review.commit_verification import parse_plan_steps, verify_commits

SAMPLE_PLAN = textwrap.dedent("""\
    # Test Plan

    Status: IN PROGRESS

    ### Steps

    #### Step 1: Create config ✓ DONE — 2026-07-23

    **Files**: (all new)
    - `src/config.py`
    - `src/utils.py`

    **What**: Create config module.

    #### Step 2: Add models

    **Files**: (all new)
    - `src/models.py`

    **What**: Define models.

    #### Step 3: Update tests ✓ DONE — 2026-07-23

    **Files**: (modify)
    - `tests/test_config.py`

    **What**: Add tests.
""")


class TestParsePlanSteps:
    def test_parses_step_numbers_and_titles(self):
        steps = parse_plan_steps(SAMPLE_PLAN)
        assert len(steps) == 3
        assert steps[0]["number"] == 1
        assert steps[0]["title"] == "Create config"
        assert steps[1]["number"] == 2
        assert steps[2]["number"] == 3

    def test_parses_done_status(self):
        steps = parse_plan_steps(SAMPLE_PLAN)
        assert steps[0]["done"] is True
        assert steps[1]["done"] is False
        assert steps[2]["done"] is True

    def test_parses_file_lists(self):
        steps = parse_plan_steps(SAMPLE_PLAN)
        assert steps[0]["files"] == ["src/config.py", "src/utils.py"]
        assert steps[1]["files"] == ["src/models.py"]
        assert steps[2]["files"] == ["tests/test_config.py"]

    def test_step_with_no_files_section(self):
        plan = textwrap.dedent("""\
            #### Step 1: No files ✓ DONE — 2026-07-23

            **What**: Just documentation.
        """)
        steps = parse_plan_steps(plan)
        assert steps[0]["files"] == []


class TestVerifyCommits:
    @pytest.fixture
    def git_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
        (repo / "src").mkdir()
        (repo / "tests").mkdir()
        (repo / "README.md").write_text("init")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
        return repo

    def test_verified_when_all_files_committed(self, git_repo):
        (git_repo / "src" / "config.py").write_text("# config")
        (git_repo / "src" / "utils.py").write_text("# utils")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "step 1"], cwd=git_repo, capture_output=True)

        results = verify_commits(SAMPLE_PLAN, str(git_repo))
        step1 = next(r for r in results if r.step == 1)
        assert step1.status == "verified"
        assert step1.missing_files == []

    def test_missing_when_no_files_committed(self, git_repo):
        results = verify_commits(SAMPLE_PLAN, str(git_repo))
        step1 = next(r for r in results if r.step == 1)
        assert step1.status == "missing"

    def test_partial_when_some_files_committed(self, git_repo):
        (git_repo / "src" / "config.py").write_text("# config")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "partial step 1"], cwd=git_repo, capture_output=True)

        results = verify_commits(SAMPLE_PLAN, str(git_repo))
        step1 = next(r for r in results if r.step == 1)
        assert step1.status == "partial"
        assert "src/utils.py" in step1.missing_files

    def test_skips_non_done_steps(self, git_repo):
        results = verify_commits(SAMPLE_PLAN, str(git_repo))
        step_nums = [r.step for r in results]
        assert 2 not in step_nums

    def test_cli_verify_commits(self, git_repo):
        plan_file = git_repo / "plan.md"
        plan_file.write_text(SAMPLE_PLAN)
        (git_repo / "src" / "config.py").write_text("# config")
        (git_repo / "src" / "utils.py").write_text("# utils")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "step 1"], cwd=git_repo, capture_output=True)

        result = subprocess.run(
            ["uv", "run", "review-cli", "verify-commits", str(plan_file), "--repo", str(git_repo)],
            capture_output=True,
            text=True,
            cwd="/Users/wiseer/workspace/guacamayo",
        )
        output = json.loads(result.stdout)
        assert any(s["step"] == 1 and s["status"] == "verified" for s in output)
