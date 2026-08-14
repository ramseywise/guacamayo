"""Resolve *when* a finding's friction landed, as opposed to when a sweep found it (GUA-109).

A finding row carries two dates and they answer different questions:

- `date` is the **run date** — when the review sweep ran. It feeds `finding_uid`
  (`factstore.py`), so it is immutable: rewriting it orphans every existing factstore row.
- `occurred` is the **friction date** — when the cited code was last touched. This is the
  one to trend on, because a bulk sweep otherwise stamps hundreds of findings with a single
  date and makes every signature look like it spiked that day.

`occurred` is a **last-touch date, not an introduction date.** It is resolved by blaming the
cited line range, so a reformat that rewrites the line resets it. Finding the commit that
*introduced* the friction needs a pickaxe search (`git log -S`), which is substantially more
expensive per finding and still ambiguous for multi-line findings. For trend *shape* the
last-touch date is sufficient; `occurred_source` records how each date was obtained so the
imprecision stays visible rather than being quietly assumed away.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Worktree and phase names that are not themselves repos. A finding emitted from a
# worktree records the worktree's directory name, which has no checkout under
# ~/workspace; mapping it back recovers those rows instead of dropping them to the
# run-date fallback.
REPO_ALIASES = {"lib110-phaseA": "librarian"}

# Source values for the `occurred_source` field, in precedence order.
SOURCE_BLAME = "blame"  # blamed the cited line range — the good case
SOURCE_HEAD = "head"  # repo found, line not blameable; used HEAD's commit date
SOURCE_UNRESOLVED = "unresolved"  # no usable checkout; caller falls back to the run date

_GIT_TIMEOUT = 15


def canonical_repo(repo: str) -> str:
    """Map a recorded repo name through the alias table."""
    return REPO_ALIASES.get(repo, repo)


def parse_lines(lines: str | None) -> tuple[int, int] | None:
    """Parse a `lines` field into an inclusive `(start, end)` range.

    Accepts `"42"`, `"42-48"`, and `"42-42"`. Returns `None` for anything absent or
    malformed, which sends the caller to the whole-file fallback rather than raising —
    a junk `lines` value should cost precision, not the whole resolution.
    """
    if not lines:
        return None
    text = str(lines).strip()
    if not text:
        return None
    start_text, _, end_text = text.partition("-")
    try:
        start = int(start_text)
        end = int(end_text) if end_text else start
    except ValueError:
        return None
    if start < 1 or end < start:
        return None
    return start, end


def _run_git(args: list[str], cwd: Path) -> str | None:
    """Run a git command, returning stripped stdout or `None` if it yielded nothing.

    Checks the return code **and** stdout: `git log -L` exits 0 with empty output for a
    path outside the index, so a returncode-only check would read success from silence.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            check=False,  # a failed lookup is a fallback, not an error
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    return out or None


def resolve_occurred(
    repo: str,
    file: str | None,
    lines: str | None,
    *,
    workspace: Path,
    cache: dict | None = None,
) -> tuple[str | None, str]:
    """Return `(ISO date or None, source)` for the friction a finding cites.

    Precedence: blame the cited line range -> the repo's HEAD commit date -> unresolved.
    `source` is one of `blame`, `head`, `unresolved`. A `None` date always pairs with
    `unresolved`, and the caller substitutes the run date.

    `cache` is an optional per-run dict keyed on `(repo, file, lines)`. A 40-finding sweep
    clusters heavily on the same files, and without it each row spawns its own subprocess.
    """
    key = (repo, file, lines)
    if cache is not None and key in cache:
        return cache[key]

    result = _resolve_uncached(repo, file, lines, workspace=workspace)
    if cache is not None:
        cache[key] = result
    return result


def _resolve_uncached(
    repo: str, file: str | None, lines: str | None, *, workspace: Path
) -> tuple[str | None, str]:
    repo_path = workspace / canonical_repo(repo)
    # Guard the checkout before spending subprocesses on it: a finding may name a repo
    # that was never cloned here, or a plain directory that is not a git repo at all.
    if not (repo_path / ".git").exists():
        return None, SOURCE_UNRESOLVED

    # `file` is "n/a" for findings that cite no specific location (2 rows in the live
    # corpus). There is nothing to blame, but the repo still dates the sweep better than
    # the run date does, so fall through to HEAD.
    if file and file != "n/a":
        line_range = parse_lines(lines)
        if line_range is not None:
            start, end = line_range
            # %cs is the committer date as a bare ISO day — no parsing, no timezone math.
            blamed = _run_git(["log", "-1", "--format=%cs", f"-L{start},{end}:{file}"], repo_path)
            if blamed:
                # `git log -L` prints the commit header followed by the diff hunk; the
                # format string is only the first line.
                return blamed.splitlines()[0].strip(), SOURCE_BLAME

        # No line range, or the range did not resolve (file renamed, line past EOF).
        # Blaming the file as a whole still beats the run date.
        touched = _run_git(["log", "-1", "--format=%cs", "--", file], repo_path)
        if touched:
            return touched.splitlines()[0].strip(), SOURCE_BLAME

    head = _run_git(["log", "-1", "--format=%cs"], repo_path)
    if head:
        return head.splitlines()[0].strip(), SOURCE_HEAD

    return None, SOURCE_UNRESOLVED
