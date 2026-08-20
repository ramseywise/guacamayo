from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


@dataclass
class StepVerification:
    step: int
    title: str
    expected_files: list[str]
    status: str  # verified | missing | partial
    matching_commits: list[str]
    missing_files: list[str]


_STEP_HEADER = re.compile(r"^####\s+Step\s+(\d+):\s+(.+?)(?:\s+✓\s+DONE.*)?$", re.MULTILINE)
_FILES_SECTION = re.compile(r"^\*\*Files\*\*:\s*(.+?)$", re.MULTILINE)
_DONE_MARKER = re.compile(r"✓\s+DONE")


def parse_plan_steps(plan_text: str) -> list[dict]:
    steps = []
    headers = list(_STEP_HEADER.finditer(plan_text))

    for i, match in enumerate(headers):
        step_num = int(match.group(1))
        title = match.group(2).strip()
        start = match.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(plan_text)
        section = plan_text[start:end]

        done = bool(_DONE_MARKER.search(match.group(0)))

        files = []
        files_match = _FILES_SECTION.search(section)
        if files_match:
            rest = section[files_match.start() :]
            lines = rest.split("\n")
            for line in lines[1:]:
                stripped = line.strip()
                if stripped.startswith("- `") and stripped.endswith("`"):
                    files.append(stripped[3:-1])
                elif stripped.startswith("- "):
                    candidate = stripped[2:].strip().strip("`")
                    if candidate and not candidate.startswith("*"):
                        files.append(candidate)
                elif stripped == "" or stripped.startswith("**"):
                    break

        steps.append(
            {
                "number": step_num,
                "title": title,
                "files": files,
                "done": done,
            }
        )

    return steps


def _find_commits_for_files(
    repo_path: str, files: list[str], branch: str | None = None
) -> list[str]:
    if not files:
        return []
    cmd = ["git", "-C", repo_path, "log", "--oneline", "--all", "--diff-filter=ACDMR", "--"]
    cmd.extend(files)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]


def _file_in_commits(repo_path: str, filepath: str, branch: str | None = None) -> bool:
    cmd = [
        "git",
        "-C",
        repo_path,
        "log",
        "--oneline",
        "--all",
        "--diff-filter=ACDMR",
        "--",
        filepath,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return bool(result.stdout.strip())


def verify_commits(
    plan_text: str,
    repo_path: str,
    branch: str | None = None,
) -> list[StepVerification]:
    steps = parse_plan_steps(plan_text)
    results = []
    for step in steps:
        if not step["done"]:
            continue
        commits = _find_commits_for_files(repo_path, step["files"], branch)
        missing = [f for f in step["files"] if not _file_in_commits(repo_path, f, branch)]
        if not step["files"] or not missing:
            status = "verified"
        elif commits:
            status = "partial"
        else:
            status = "missing"
        results.append(
            StepVerification(
                step=step["number"],
                title=step["title"],
                expected_files=step["files"],
                status=status,
                matching_commits=commits,
                missing_files=missing,
            )
        )
    return results
