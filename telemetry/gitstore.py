"""Repo-activity facts: commits, churn, and PR/issue flow per repo per day.

A deliberately separate table from `sessions`. Session facts describe *how Claude
worked*; these describe *what landed in the repos*. They are joinable on
(date, project) but never on session_id -- see ATTRIBUTION below.

ATTRIBUTION (measured 2026-07-20, the constraint that shapes this module):
Ramsey commits, always -- Claude never runs `git commit` (global CLAUDE.md). The
`Co-Authored-By: Claude` trailer therefore appears on only 6 of 406 commits, and
its absence says nothing about whether a session was involved. There is no
commit -> session join, and none can be manufactured. So these are **repo
activity** metrics, not Claude-productivity metrics, and the dashboard labels
them that way. Reading a commit spike as "Claude was productive" is exactly the
inference this docstring exists to block.

Bot commits (dependabot et al.) are counted separately rather than dropped: they
are real repo activity but not human work, and pooling them inflates a
"throughput" reading by ~20%.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# One row per (repo, date). Cross-source join key with `sessions` is (date, project).
GIT_COLUMNS: dict[str, type] = {
    "repo": str,
    "date": str,
    "commits": int,
    "commits_bot": int,
    "commits_claude_trailer": int,
    "insertions": int,
    "deletions": int,
    "files_changed": int,
}

PR_COLUMNS: dict[str, type] = {
    "repo": str,
    "number": int,
    "state": str,
    "created_date": str,
    "closed_date": str,
    "merged": int,
    "additions": int,
    "deletions": int,
    "is_bot": int,
    "title": str,
    "body": str,
    "head_ref": str,
}

# Issues carry the *workflow label*, which is the board's view of where a work item
# sits. Joined against plan-doc `Status:` by the loop tab to surface drift (LIB #91).
ISSUE_COLUMNS: dict[str, type] = {
    "repo": str,
    "number": int,
    "title": str,
    "state": str,
    "labels": str,
    "created_date": str,
    "closed_date": str,
}

# One row per (repo, branch-name). Grain is finer than git_activity (which is per day).
# `merged` is derived from pull_requests.head_ref, not from git state — so it reflects
# PR merge state, not whether the ref has been deleted.
BRANCH_COLUMNS: dict[str, type] = {
    "repo": str,
    "name": str,
    "merged": int,
    "pr_number": int,
    "head_sha": str,
}

_SQL_TYPES = {str: "TEXT", int: "INTEGER", float: "REAL", bool: "INTEGER"}

# Author names matching this are automation, not human work.
_BOT_AUTHOR = re.compile(r"\[bot\]|^dependabot|^github-actions", re.IGNORECASE)

_CLAUDE_TRAILER = re.compile(r"Co-Authored-By:\s*Claude", re.IGNORECASE)

# Commit subjects that are pure repo mechanics -- excluded from churn so a
# lockfile refresh or merge commit does not read as authored work.
_MECHANICAL = re.compile(r"^(Merge |Revert |Bump |chore\(deps\))", re.IGNORECASE)

# Paths excluded from churn. Without this, churn measures what was *committed*
# rather than what was *written*: an unfiltered pass over the workspace returned
# 1.37M insertions, of which the single largest contributor was a 70k-line PDF
# and the top ten were PDFs, vendored course notebooks, and lockfiles (measured
# 2026-07-20). Notebooks are excluded because one re-execution rewrites every
# output cell, so their diffs track running, not authoring.
_NON_SOURCE = re.compile(
    r"(\.(pdf|ipynb|lock|min\.js|map|png|jpe?g|gif|svg|woff2?|ttf|zip|csv|jsonl|parquet)$"
    r"|(^|/)(node_modules|dist|build|vendor|\.venv|venv|site-packages)/"
    r"|(^|/)\.obsidian/"  # bundled Obsidian plugin JS: 36k lines in one file
    # Third-party material checked in wholesale (course clones, reference repos).
    # These are real commits but not authored lines; without this a learning repo
    # dominates workspace churn (338k insertions, 2026-07-20).
    r"|(^|/)(coursera-references|readings|references?-repos?|third[-_]party)/"
    r"|(^|/)(package-lock\.json|uv\.lock|poetry\.lock|yarn\.lock|pnpm-lock\.yaml)$)",
    re.IGNORECASE,
)


def _run(args: list[str], cwd: Path) -> str:
    """Run a git command, returning stdout ('' on any failure)."""
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60, check=False)
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("gitstore.command_failed", cwd=str(cwd), error=str(exc))
        return ""
    return out.stdout if out.returncode == 0 else ""


def discover_repos(workspace: Path) -> list[Path]:
    """Every direct child of `workspace` that is a git repo."""
    return sorted(p for p in workspace.iterdir() if (p / ".git").is_dir())


def collect_commits(repo: Path, since: str) -> list[dict[str, Any]]:
    """Per-day commit + churn facts for one repo.

    Churn excludes mechanical commits (merges, dependency bumps): those are real
    history but not authored lines, and they dominate insertion counts when a
    lockfile lands.
    """
    raw = _run(
        [
            "git",
            "log",
            f"--since={since}",
            "--no-merges",
            "--format=%x00%H%x1f%ad%x1f%an%x1f%s%x1f%b",
            "--date=short",
            "--numstat",
        ],
        repo,
    )
    if not raw:
        return []

    daily: dict[str, dict[str, Any]] = {}
    for chunk in raw.split("\x00"):
        if not chunk.strip():
            continue
        header, _, stats = chunk.partition("\n")
        parts = header.split("\x1f")
        if len(parts) < 4:
            continue
        _sha, date, author, subject = parts[0], parts[1], parts[2], parts[3]
        body = parts[4] if len(parts) > 4 else ""

        day = daily.setdefault(
            date,
            {
                "repo": repo.name,
                "date": date,
                "commits": 0,
                "commits_bot": 0,
                "commits_claude_trailer": 0,
                "insertions": 0,
                "deletions": 0,
                "files_changed": 0,
            },
        )
        is_bot = bool(_BOT_AUTHOR.search(author))
        day["commits"] += 1
        if is_bot:
            day["commits_bot"] += 1
        if _CLAUDE_TRAILER.search(body):
            day["commits_claude_trailer"] += 1

        # Churn: human, non-mechanical commits only.
        if is_bot or _MECHANICAL.search(subject):
            continue
        for line in stats.splitlines():
            cols = line.split("\t")
            if len(cols) != 3 or cols[0] == "-":  # '-' marks a binary file
                continue
            if _NON_SOURCE.search(cols[2]):
                continue
            try:
                day["insertions"] += int(cols[0])
                day["deletions"] += int(cols[1])
            except ValueError:
                continue
            day["files_changed"] += 1
    return list(daily.values())


def collect_prs(repo_name: str, owner: str = "ramseywise") -> list[dict[str, Any]]:
    """PR facts via `gh`. Returns [] when gh is absent or the repo has no remote."""
    if not shutil.which("gh"):
        log.info("gitstore.gh_missing", repo=repo_name)
        return []
    raw = _run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            f"{owner}/{repo_name}",
            "--state",
            "all",
            "--limit",
            "300",
            "--json",
            "number,state,createdAt,closedAt,additions,deletions,author,title,body,headRefName",
        ],
        Path.cwd(),
    )
    if not raw.strip():
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("gitstore.pr_parse_failed", repo=repo_name)
        return []

    rows = []
    for pr in payload:
        author = pr.get("author") or {}
        # gh exposes an authoritative is_bot flag; trust it over name-matching.
        # Dependabot's PR login is "app/dependabot" (no "[bot]" suffix), so the
        # commit-author regex alone reported zero bot PRs against 158 bot commits.
        login = author.get("login", "")
        is_bot = bool(author.get("is_bot")) or bool(_BOT_AUTHOR.search(login))
        rows.append(
            {
                "repo": repo_name,
                "number": pr.get("number", 0),
                "state": pr.get("state", ""),
                "created_date": (pr.get("createdAt") or "")[:10],
                "closed_date": (pr.get("closedAt") or "")[:10],
                "merged": int(pr.get("state") == "MERGED"),
                "additions": pr.get("additions") or 0,
                "deletions": pr.get("deletions") or 0,
                "is_bot": int(is_bot),
                "title": pr.get("title") or "",
                # Truncate at 2000 chars: closing links almost always appear in the
                # first paragraph or footer, well within this limit. If a false
                # positive surfaces, raise to 4000 (see plan risks).
                "body": (pr.get("body") or "")[:2000],
                "head_ref": pr.get("headRefName") or "",
            }
        )
    return rows


def _connect(store: Path) -> sqlite3.Connection:
    store.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(store)
    gcols = ", ".join(f"{n} {_SQL_TYPES[t]}" for n, t in GIT_COLUMNS.items())
    pcols = ", ".join(f"{n} {_SQL_TYPES[t]}" for n, t in PR_COLUMNS.items())
    icols = ", ".join(f"{n} {_SQL_TYPES[t]}" for n, t in ISSUE_COLUMNS.items())
    bcols = ", ".join(f"{n} {_SQL_TYPES[t]}" for n, t in BRANCH_COLUMNS.items())
    conn.execute(f"CREATE TABLE IF NOT EXISTS git_activity ({gcols}, PRIMARY KEY (repo, date))")
    conn.execute(f"CREATE TABLE IF NOT EXISTS pull_requests ({pcols}, PRIMARY KEY (repo, number))")
    conn.execute(f"CREATE TABLE IF NOT EXISTS issues ({icols}, PRIMARY KEY (repo, number))")
    conn.execute(f"CREATE TABLE IF NOT EXISTS branches ({bcols}, PRIMARY KEY (repo, name))")
    # Migration guards: new columns added to pull_requests on an existing store.
    # SQLite has no ALTER TABLE ... ADD COLUMN IF NOT EXISTS; wrap in try/except.
    for col, sql_type in (("title", "TEXT"), ("body", "TEXT"), ("head_ref", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE pull_requests ADD COLUMN {col} {sql_type}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def upsert_commits(rows: list[dict[str, Any]], store: Path) -> int:
    return _upsert("git_activity", GIT_COLUMNS, rows, store)


def upsert_prs(rows: list[dict[str, Any]], store: Path) -> int:
    return _upsert("pull_requests", PR_COLUMNS, rows, store)


def upsert_issues(rows: list[dict[str, Any]], store: Path) -> int:
    return _upsert("issues", ISSUE_COLUMNS, rows, store)


def _upsert(table: str, columns: dict[str, type], rows: list[dict[str, Any]], store: Path) -> int:
    if not rows:
        return 0
    names = list(columns)
    sql = (
        f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) "
        f"VALUES ({', '.join('?' for _ in names)})"
    )
    conn = _connect(store)
    try:
        conn.executemany(sql, [tuple(r.get(n) for n in names) for r in rows])
        conn.commit()
    finally:
        conn.close()
    log.info("gitstore.upsert", table=table, rows=len(rows))
    return len(rows)


def read_git_activity(store: Path) -> list[dict[str, Any]]:
    return _read("git_activity", store)


def read_prs(store: Path) -> list[dict[str, Any]]:
    return _read("pull_requests", store)


def read_issues(store: Path) -> list[dict[str, Any]]:
    return _read("issues", store)


def read_branches(store: Path, repo: str | None = None) -> list[dict[str, Any]]:
    """All branch rows, optionally filtered to one repo."""
    if not store.exists():
        return []
    conn = _connect(store)
    try:
        conn.row_factory = sqlite3.Row
        if repo is not None:
            rows = conn.execute("SELECT * FROM branches WHERE repo = ?", (repo,))
        else:
            rows = conn.execute("SELECT * FROM branches")
        return [dict(r) for r in rows]
    finally:
        conn.close()


def collect_branches(
    repo_path: Path, repo_name: str, store: Path | None = None
) -> list[dict[str, Any]]:
    """Branch facts for one repo derived from remote refs + stored PR data.

    Runs `git fetch --prune` first because remote refs may be stale (no prior
    fetch in the collection pipeline — confirmed in plan refinement notes).
    `store` is used only to load existing PR rows for the head_ref join; pass
    None when the caller has already loaded them separately.
    """
    # Fetch so remote refs are current before reading them.
    _run(["git", "-C", str(repo_path), "fetch", "--prune", "--quiet"], repo_path)

    raw = _run(
        [
            "git",
            "-C",
            str(repo_path),
            "branch",
            "-r",
            "--format=%(refname:short)|%(objectname:short)",
        ],
        repo_path,
    )
    if not raw.strip():
        return []

    # Build a lookup from head_ref (branch name) → PR row using stored PR data.
    pr_by_head_ref: dict[str, dict[str, Any]] = {}
    if store is not None:
        for pr in read_prs(store):
            hr = pr.get("head_ref") or ""
            if hr:
                pr_by_head_ref[hr] = pr

    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        ref, sha = line.split("|", 1)
        # ref is like "origin/main" or "origin/HEAD -> origin/main"
        if "HEAD" in ref:
            continue
        # Strip the "origin/" prefix.
        if ref.startswith("origin/"):
            name = ref[len("origin/") :]
        else:
            name = ref
        matched_pr = pr_by_head_ref.get(name)
        rows.append(
            {
                "repo": repo_name,
                "name": name,
                "merged": int(matched_pr["merged"]) if matched_pr else 0,
                "pr_number": matched_pr["number"] if matched_pr else None,
                "head_sha": sha,
            }
        )
    return rows


def upsert_branches(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    """INSERT OR REPLACE branch rows using an already-open connection."""
    if not rows:
        return 0
    names = list(BRANCH_COLUMNS)
    sql = (
        f"INSERT OR REPLACE INTO branches ({', '.join(names)}) "
        f"VALUES ({', '.join('?' for _ in names)})"
    )
    conn.executemany(sql, [tuple(r.get(n) for n in names) for r in rows])
    conn.commit()
    log.info("gitstore.upsert", table="branches", rows=len(rows))
    return len(rows)


def _read(table: str, store: Path) -> list[dict[str, Any]]:
    if not store.exists():
        return []
    conn = _connect(store)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]
    finally:
        conn.close()


def refresh(workspace: Path, store: Path, since: str = "2026-04-01") -> tuple[int, int, int, int]:
    """Collect commit + PR + issue + branch facts for every repo under `workspace`."""
    from telemetry.loop import collect_issues

    commit_rows: list[dict[str, Any]] = []
    pr_rows: list[dict[str, Any]] = []
    issue_rows: list[dict[str, Any]] = []
    branch_rows: list[dict[str, Any]] = []
    for repo in discover_repos(workspace):
        commit_rows.extend(collect_commits(repo, since))
        repo_pr_rows = collect_prs(repo.name)
        pr_rows.extend(repo_pr_rows)
        issue_rows.extend(collect_issues(repo.name))
        # collect_branches must run after collect_prs so the head_ref join uses
        # fresh PR data. We pass the in-memory rows directly rather than re-reading
        # the store to avoid a round-trip between upsert and the branch join.
        # Build a temporary head_ref lookup from the just-collected rows.
        pr_by_head_ref: dict[str, dict[str, Any]] = {
            pr["head_ref"]: pr for pr in repo_pr_rows if pr.get("head_ref")
        }
        branch_rows.extend(_collect_branches_with_prs(repo, repo.name, pr_by_head_ref))
    conn = _connect(store)
    try:
        n_commits = _upsert_into(conn, "git_activity", GIT_COLUMNS, commit_rows)
        n_prs = _upsert_into(conn, "pull_requests", PR_COLUMNS, pr_rows)
        n_issues = _upsert_into(conn, "issues", ISSUE_COLUMNS, issue_rows)
        n_branches = upsert_branches(conn, branch_rows)
    finally:
        conn.close()
    return n_commits, n_prs, n_issues, n_branches


def _collect_branches_with_prs(
    repo_path: Path, repo_name: str, pr_by_head_ref: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Internal helper: collect_branches without a store round-trip."""
    _run(["git", "-C", str(repo_path), "fetch", "--prune", "--quiet"], repo_path)
    raw = _run(
        [
            "git",
            "-C",
            str(repo_path),
            "branch",
            "-r",
            "--format=%(refname:short)|%(objectname:short)",
        ],
        repo_path,
    )
    if not raw.strip():
        return []
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        ref, sha = line.split("|", 1)
        if "HEAD" in ref:
            continue
        name = ref.removeprefix("origin/")
        matched_pr = pr_by_head_ref.get(name)
        rows.append(
            {
                "repo": repo_name,
                "name": name,
                "merged": int(matched_pr["merged"]) if matched_pr else 0,
                "pr_number": matched_pr["number"] if matched_pr else None,
                "head_sha": sha,
            }
        )
    return rows


def _upsert_into(
    conn: sqlite3.Connection, table: str, columns: dict[str, type], rows: list[dict[str, Any]]
) -> int:
    """INSERT OR REPLACE rows into an already-open connection."""
    if not rows:
        return 0
    names = list(columns)
    sql = (
        f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) "
        f"VALUES ({', '.join('?' for _ in names)})"
    )
    conn.executemany(sql, [tuple(r.get(n) for n in names) for r in rows])
    conn.commit()
    log.info("gitstore.upsert", table=table, rows=len(rows))
    return len(rows)
