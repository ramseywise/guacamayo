"""Portfolio sweep — `uv run telemetry --sweep`: state + review across every governed repo.

Two passes over the repos in `repos.toml`, written to `.sounding/sweeps/` (git-ignored,
so private repos' findings never leave the machine):

    state   — fetch, then default-branch drift, working tree, gone/merged/unmerged
              branches, external worktrees, open and dependabot PRs, board actions.
              Replaces `hygiene.sh --dry-run` as the read-only view; hygiene keeps
              the mutations.
    review  — for `review = true` repos, files changed on origin/<default> since the
              last reviewed SHA (first run: the last `--days`), reviewed in a detached
              worktree via `review.driver.run_review` on the plan (no API key).

Report-only: nothing here opens issues, deletes branches, or edits a repo. A repo that
cannot be read is reported with its error, never dropped — a sweep that skips quietly
is indistinguishable from a sweep that found nothing.

Ledger (`findings.json`) carries findings across sweeps, keyed `<repo>:<fingerprint>`:
    open          reported, not yet acted on
    acknowledged  ticked `[x]` in the previous digest
    resolved      its file was re-reviewed and the finding was not reported again
A finding whose file was not re-reviewed this run is carried over untouched.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telemetry.repos import Repo, load_repos

if TYPE_CHECKING:
    from collections.abc import Callable

    from review.driver import ScanFn
    from review.schemas.models import SweepFinding

REPO_ROOT = Path(__file__).resolve().parents[2]
SWEEPS_DIR = REPO_ROOT / ".sounding" / "sweeps"
BOARD_PATH = REPO_ROOT / ".sounding" / "telemetry" / "board.json"

# A first run over 30 days of a busy repo is hundreds of files; past this the review
# takes the most recently changed and the digest says how many it left out.
MAX_REVIEW_FILES = 40

_SKIP_NAMES = frozenset(
    {"uv.lock", "poetry.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock"}
)
_SKIP_SUFFIXES = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
        ".parquet", ".pkl", ".db", ".sqlite", ".woff", ".woff2", ".ttf", ".mp3", ".mp4",
        ".ipynb", ".svg", ".lock",
    }
)  # fmt: skip
_IMPACT_RANK = {"blocker": 0, "important": 1, "question": 2, "suggestion": 3, "nit": 4}
_FP_MARKER = re.compile(r"^\s*- \[[xX]\].*<!-- fp:(\S+) -->")


# ---------------------------------------------------------------------------
# subprocess helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def _git_out(repo: Path, *args: str) -> str | None:
    """stdout of a git call, or None when it failed."""
    out = _git(repo, *args)
    return out.stdout.strip() if out.returncode == 0 else None


def gh_json(repo: Path, args: list[str]) -> list[dict[str, Any]] | str:
    """`gh <args>` parsed as JSON, or the error text. Run inside the repo for its remote."""
    out = subprocess.run(["gh", *args], cwd=repo, capture_output=True, text=True, check=False)
    if out.returncode != 0:
        return (out.stderr.strip() or f"gh exited {out.returncode}").splitlines()[-1]
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError as exc:
        return f"gh returned non-JSON: {exc}"


# ---------------------------------------------------------------------------
# state pass
# ---------------------------------------------------------------------------


@dataclass
class RepoState:
    name: str
    role: str
    visibility: str
    status: str = "ok"  # ok | not_cloned | fetch_failed
    errors: list[str] = field(default_factory=list)
    default_branch: str | None = None
    default_sha: str | None = None
    local_ahead: int | None = None
    local_behind: int | None = None
    head_branch: str | None = None
    head_ahead_of_default: int | None = None
    staged: int = 0
    unstaged: int = 0
    untracked: int = 0
    gone_branches: list[str] = field(default_factory=list)
    # remote branches other than the default: {name, ahead, merged_pr}
    remote_branches: list[dict[str, Any]] = field(default_factory=list)
    external_worktrees: list[str] = field(default_factory=list)
    open_prs: list[dict[str, Any]] = field(default_factory=list)
    dependabot_prs: list[dict[str, Any]] = field(default_factory=list)
    board_actions: list[dict[str, Any]] = field(default_factory=list)


def _ahead_behind(repo: Path, left: str, right: str) -> tuple[int, int] | None:
    """(commits only in left, commits only in right), or None when either ref is missing."""
    out = _git_out(repo, "rev-list", "--left-right", "--count", f"{left}...{right}")
    if out is None:
        return None
    ahead, behind = out.split()
    return int(ahead), int(behind)


def _board_actions(repo_name: str, board_path: Path) -> list[dict[str, Any]]:
    try:
        board = json.loads(board_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return [
        a
        for a in board.get("proposed_actions", [])
        if str(a.get("target", {}).get("repo", "")).rsplit("/", 1)[-1] == repo_name
    ]


def collect_state(
    repo: Repo,
    *,
    board_path: Path = BOARD_PATH,
    gh: Callable[[Path, list[str]], list[dict[str, Any]] | str] = gh_json,
) -> RepoState:
    """Read-only snapshot of one repo. Every failure lands in `errors`; nothing raises."""
    st = RepoState(name=repo.name, role=repo.role, visibility=repo.visibility)
    st.board_actions = _board_actions(repo.name, board_path)
    if not repo.cloned:
        st.status = "not_cloned"
        st.errors.append(f"no clone at {repo.path}")
        return st
    path = repo.path

    fetch = _git(path, "fetch", "--prune", "--quiet", "origin")
    if fetch.returncode != 0:
        st.status = "fetch_failed"
        st.errors.append(f"fetch: {fetch.stderr.strip() or 'failed'} (state below may be stale)")

    head_ref = _git_out(path, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head_ref is None:
        # origin/HEAD is only set by clone; fall back to the usual names.
        for candidate in ("main", "master"):
            if _git_out(path, "rev-parse", "--verify", "--quiet", f"origin/{candidate}"):
                head_ref = f"origin/{candidate}"
                break
    if head_ref is None:
        st.errors.append("no origin default branch (origin/HEAD unset, no main/master)")
        return st
    default = head_ref.removeprefix("origin/")
    st.default_branch = default
    st.default_sha = _git_out(path, "rev-parse", f"origin/{default}")

    if (ab := _ahead_behind(path, default, f"origin/{default}")) is not None:
        st.local_ahead, st.local_behind = ab
    st.head_branch = _git_out(path, "branch", "--show-current") or "(detached)"
    if st.head_branch not in (default, "(detached)"):
        ab = _ahead_behind(path, "HEAD", f"origin/{default}")
        st.head_ahead_of_default = ab[0] if ab else None

    # Not _git_out: stripping eats the leading space that marks a porcelain line unstaged.
    for line in _git(path, "status", "--porcelain").stdout.splitlines():
        if line.startswith("??"):
            st.untracked += 1
            continue
        if line[0] != " ":
            st.staged += 1
        if line[1] != " ":
            st.unstaged += 1

    refs = _git_out(
        path, "for-each-ref", "--format=%(refname:short)\t%(upstream:track)", "refs/heads"
    )
    st.gone_branches = [
        ln.split("\t")[0] for ln in (refs or "").splitlines() if ln.endswith("[gone]")
    ]

    merged = gh(
        path, ["pr", "list", "--state", "merged", "--limit", "200", "--json", "headRefName,number"]
    )
    merged_by_branch: dict[str, int] = {}
    if isinstance(merged, str):
        st.errors.append(f"merged PRs: {merged}")
    else:
        merged_by_branch = {p["headRefName"]: p["number"] for p in merged}
    remotes = _git_out(path, "for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    for ref in (remotes or "").splitlines():
        branch = ref.removeprefix("origin/")
        if branch in ("HEAD", default) or ref == "origin":
            continue
        ab = _ahead_behind(path, ref, f"origin/{default}")
        st.remote_branches.append(
            {
                "name": branch,
                "ahead": ab[0] if ab else None,
                "merged_pr": merged_by_branch.get(branch),
            }
        )

    worktrees = _git_out(path, "worktree", "list", "--porcelain") or ""
    resolved = path.resolve()
    for line in worktrees.splitlines():
        if not line.startswith("worktree "):
            continue
        wt = Path(line.removeprefix("worktree ")).resolve()
        if wt != resolved and resolved not in wt.parents:
            st.external_worktrees.append(str(wt))

    prs = gh(path, ["pr", "list", "--state", "open", "--json", "number,title,author,headRefName"])
    if isinstance(prs, str):
        st.errors.append(f"open PRs: {prs}")
    else:
        for pr in prs:
            login = str(pr.get("author", {}).get("login", ""))
            (st.dependabot_prs if "dependabot" in login else st.open_prs).append(pr)
    return st


# ---------------------------------------------------------------------------
# review pass
# ---------------------------------------------------------------------------


def _reviewable(path: str) -> bool:
    p = Path(path)
    return p.name not in _SKIP_NAMES and p.suffix.lower() not in _SKIP_SUFFIXES


def select_files(repo: Path, ref: str, last_sha: str | None, days: int) -> tuple[list[str], int]:
    """Files changed on `ref` since `last_sha` (or in the last `days`), newest first.

    Returns (files to review, count dropped by MAX_REVIEW_FILES). Deleted files,
    lockfiles and binaries are excluded.
    """
    if last_sha and _git_out(repo, "cat-file", "-e", f"{last_sha}^{{commit}}") is not None:
        log_args = [f"{last_sha}..{ref}"]
    else:
        log_args = [f"--since={days} days ago", ref]
    out = _git_out(repo, "log", "--name-only", "--format=", "--diff-filter=d", *log_args) or ""
    present = set((_git_out(repo, "ls-tree", "-r", "--name-only", ref) or "").splitlines())
    files: list[str] = []
    for f in out.splitlines():
        if f and f not in files and f in present and _reviewable(f):
            files.append(f)
    return files[:MAX_REVIEW_FILES], max(0, len(files) - MAX_REVIEW_FILES)


@dataclass
class ReviewOutcome:
    files: list[str] = field(default_factory=list)
    dropped: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    completed: bool = False
    skipped_reason: str | None = None


def _finding_dict(f: SweepFinding) -> dict[str, Any]:
    return {
        "fingerprint": f.fingerprint,
        "file": f.file_path,
        "line": f.start_line,
        "title": f.title,
        "merge_impact": f.merge_impact,
        "category": f.category,
    }


def review_repo(
    repo: Repo,
    state: RepoState,
    last_sha: str | None,
    *,
    days: int,
    sweeps_dir: Path,
    scan_fn: ScanFn | None = None,
) -> ReviewOutcome:
    """Review what changed on origin/<default> in a throwaway detached worktree.

    The user's checkout is never touched: it may be mid-edit on another branch.
    """
    from review.driver import DriverConfig, run_review, sdk_scan
    from review.fingerprint import finding_to_sweep_finding

    outcome = ReviewOutcome()
    if state.default_sha is None or state.default_branch is None:
        outcome.skipped_reason = "no default branch to review"
        return outcome
    if last_sha == state.default_sha:
        outcome.skipped_reason = "no new commits since last review"
        outcome.completed = True
        return outcome
    ref = f"origin/{state.default_branch}"
    outcome.files, outcome.dropped = select_files(repo.path, ref, last_sha, days)
    if not outcome.files:
        outcome.skipped_reason = "no reviewable files changed"
        outcome.completed = True
        return outcome

    checkout = sweeps_dir / "checkouts" / repo.name
    if checkout.exists():  # left by a crashed run
        _git(repo.path, "worktree", "remove", "--force", str(checkout))
    _git(repo.path, "worktree", "prune")
    add = _git(repo.path, "worktree", "add", "--detach", str(checkout), state.default_sha)
    if add.returncode != 0:
        outcome.errors.append(f"worktree add: {add.stderr.strip()}")
        return outcome
    try:
        result = run_review(
            DriverConfig(
                repo=checkout,
                files=outcome.files,
                reviews_dir=sweeps_dir / "reviews",
                static_analysis=False,
                findings_path=sweeps_dir / "review-findings.jsonl",
            ),
            scan_fn=scan_fn or sdk_scan,
        )
    except Exception as exc:
        outcome.errors.append(f"review crashed: {type(exc).__name__}: {exc}")
        return outcome
    finally:
        _git(repo.path, "worktree", "remove", "--force", str(checkout))

    outcome.findings = [_finding_dict(finding_to_sweep_finding(f)) for f in result.findings]
    outcome.errors.extend(f"{e.dimension}: {e.subtype} — {e.detail}" for e in result.errors)
    outcome.completed = result.exit_code == 0
    return outcome


# ---------------------------------------------------------------------------
# ledger
# ---------------------------------------------------------------------------


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"cursors": {}, "findings": {}}
    return json.loads(path.read_text())


def acknowledged_keys(digest: Path | None) -> set[str]:
    """Ledger keys the user ticked `[x]` in a digest."""
    if digest is None or not digest.exists():
        return set()
    return {m.group(1) for line in digest.read_text().splitlines() if (m := _FP_MARKER.match(line))}


def update_ledger(
    ledger: dict[str, Any],
    repo: str,
    outcome: ReviewOutcome,
    today: str,
) -> None:
    """Fold one repo's review into the ledger in place.

    Resolution needs a clean review: a dimension that errored may simply not have
    reported the finding, so a partial run adds findings but never resolves any.
    """
    findings: dict[str, Any] = ledger["findings"]
    seen: set[str] = set()
    for f in outcome.findings:
        key = f"{repo}:{f['fingerprint']}"
        seen.add(key)
        entry = findings.get(key)
        if entry is None:
            findings[key] = {
                **f,
                "repo": repo,
                "first_seen": today,
                "last_seen": today,
                "status": "open",
            }
            continue
        entry.update(f, last_seen=today)
        if entry["status"] == "resolved":
            entry["status"] = "open"
            entry.pop("resolved_on", None)
    if not outcome.completed:
        return
    reviewed = set(outcome.files)
    for key, entry in findings.items():
        if (
            entry["repo"] == repo
            and key not in seen
            and entry["status"] != "resolved"
            and entry["file"] in reviewed
        ):
            entry["status"] = "resolved"
            entry["resolved_on"] = today


# ---------------------------------------------------------------------------
# digest
# ---------------------------------------------------------------------------


def _count(n: int | None) -> str:
    return "?" if n is None else str(n)


def _state_rows(st: RepoState) -> list[tuple[str, str]]:
    if st.status == "not_cloned":
        return [("status", "**not cloned**")]
    # preserve/* is rescued work kept on purpose — counted, never listed as unmerged.
    preserved = [b for b in st.remote_branches if b["name"].startswith("preserve/")]
    unmerged = [
        b
        for b in st.remote_branches
        if not b["merged_pr"] and b["ahead"] and not b["name"].startswith("preserve/")
    ]
    stale = [b for b in st.remote_branches if b["merged_pr"]]
    rows = [
        ("status", st.status if st.status == "ok" else f"**{st.status}**"),
        (
            "default",
            f"`{st.default_branch}` @ `{(st.default_sha or '?')[:8]}` — local "
            f"+{_count(st.local_ahead)}/−{_count(st.local_behind)}",
        ),
    ]
    head = f"`{st.head_branch}`"
    if st.head_ahead_of_default is not None:
        head += f" (+{st.head_ahead_of_default} vs default)"
    rows.append(("checked out", head))
    rows.append(
        ("working tree", f"{st.staged} staged · {st.unstaged} unstaged · {st.untracked} untracked")
    )
    if st.gone_branches:
        rows.append(("gone upstream", ", ".join(f"`{b}`" for b in st.gone_branches)))
    if stale:
        rows.append(
            ("merged, not deleted", ", ".join(f"`{b['name']}` (#{b['merged_pr']})" for b in stale))
        )
    if unmerged:
        rows.append(
            ("unmerged remote", ", ".join(f"`{b['name']}` (+{b['ahead']})" for b in unmerged))
        )
    if preserved:
        rows.append(("preserve/* (kept)", str(len(preserved))))
    if st.external_worktrees:
        rows.append(("external worktrees", ", ".join(f"`{w}`" for w in st.external_worktrees)))
    if st.open_prs:
        rows.append(("open PRs", ", ".join(f"#{p['number']} {p['title']}" for p in st.open_prs)))
    if st.dependabot_prs:
        rows.append(("dependabot", f"{len(st.dependabot_prs)} open"))
    if st.board_actions:
        rows.append(
            (
                "board actions",
                ", ".join(
                    f"{a['action']} #{a['target'].get('issue_num')}" for a in st.board_actions
                ),
            )
        )
    return rows


def _finding_line(key: str, f: dict[str, Any]) -> str:
    loc = f["file"] + (f":{f['line']}" if f.get("line") else "")
    tick = "x" if f["status"] == "acknowledged" else " "
    return f"- [{tick}] **{f['merge_impact']}** `{loc}` — {f['title']} <!-- fp:{key} -->"


def render_digest(
    today: str,
    repos: list[Repo],
    states: dict[str, RepoState],
    outcomes: dict[str, ReviewOutcome],
    ledger: dict[str, Any],
) -> str:
    lines = [
        f"# Portfolio sweep — {today}",
        "",
        "Report only. Tick `[x]` to acknowledge a finding; the next sweep carries the tick "
        "into `findings.json`. Lives in `.sounding/` — private repos' findings stay local.",
        "",
    ]
    findings = ledger["findings"]
    for repo in repos:
        st = states[repo.name]
        lines += [f"## {repo.name}", "", f"_{repo.role} · {repo.visibility}_", ""]
        lines += ["| | |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in _state_rows(st)]
        lines.append("")

        outcome = outcomes.get(repo.name)
        live = sorted(
            (
                (k, f)
                for k, f in findings.items()
                if f["repo"] == repo.name and f["status"] != "resolved"
            ),
            key=lambda kf: (_IMPACT_RANK.get(kf[1]["merge_impact"], 9), kf[1]["file"]),
        )
        if outcome is not None:
            if outcome.skipped_reason:
                lines += [f"Review: skipped — {outcome.skipped_reason}.", ""]
            else:
                note = f"Review: {len(outcome.files)} files"
                if outcome.dropped:
                    note += (
                        f" — {outcome.dropped} more changed files were over the {MAX_REVIEW_FILES}-file cap"
                        " and are not reviewed (the cursor moves past them; review them by hand)"
                    )
                lines += [note + ("." if outcome.completed else " — **incomplete**."), ""]
        new = [(k, f) for k, f in live if f["last_seen"] == today]
        carried = [(k, f) for k, f in live if f["last_seen"] != today]
        if new:
            lines += ["### Findings", "", *(_finding_line(k, f) for k, f in new), ""]
        if carried:
            lines += ["### Carried over", ""]
            lines += [f"{_finding_line(k, f)} _(since {f['first_seen']})_" for k, f in carried]
            lines.append("")
        resolved = [
            f for f in findings.values() if f["repo"] == repo.name and f.get("resolved_on") == today
        ]
        if resolved:
            lines += [f"Resolved this sweep: {len(resolved)}.", ""]
        errors = st.errors + (outcome.errors if outcome else [])
        if errors:
            lines += ["### Errors", "", *(f"- {e}" for e in errors), ""]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def run_sweep(
    repos: list[Repo],
    *,
    today: str,
    review: bool = True,
    days: int = 30,
    sweeps_dir: Path = SWEEPS_DIR,
    board_path: Path = BOARD_PATH,
    gh: Callable[[Path, list[str]], list[dict[str, Any]] | str] = gh_json,
    scan_fn: ScanFn | None = None,
) -> Path:
    """Run both passes and write `<today>.state.json`, `findings.json`, `<today>.md`."""
    sweeps_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = sweeps_dir / "findings.json"
    ledger = load_ledger(ledger_path)

    previous = sorted(p for p in sweeps_dir.glob("????-??-??.md") if p.stem < today)
    for key in acknowledged_keys(previous[-1] if previous else None):
        if key in ledger["findings"] and ledger["findings"][key]["status"] == "open":
            ledger["findings"][key]["status"] = "acknowledged"

    states: dict[str, RepoState] = {}
    outcomes: dict[str, ReviewOutcome] = {}
    for repo in repos:
        print(f"[sweep] {repo.name}: state", file=sys.stderr)
        st = collect_state(repo, board_path=board_path, gh=gh)
        states[repo.name] = st
        if not (review and repo.review and st.default_sha):
            continue
        print(f"[sweep] {repo.name}: review", file=sys.stderr)
        cursor = ledger["cursors"].get(repo.name, {})
        outcome = review_repo(
            repo, st, cursor.get("sha"), days=days, sweeps_dir=sweeps_dir, scan_fn=scan_fn
        )
        outcomes[repo.name] = outcome
        update_ledger(ledger, repo.name, outcome, today)
        # Advance only past a clean review: an errored dimension may have missed things,
        # and the next sweep should look at the same commits again.
        if outcome.completed:
            ledger["cursors"][repo.name] = {"sha": st.default_sha, "reviewed_on": today}

    (sweeps_dir / f"{today}.state.json").write_text(
        json.dumps({"date": today, "repos": [asdict(s) for s in states.values()]}, indent=2) + "\n"
    )
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    digest = sweeps_dir / f"{today}.md"
    digest.write_text(render_digest(today, repos, states, outcomes, ledger))
    return digest


def main() -> None:
    p = argparse.ArgumentParser(prog="telemetry --sweep", description=__doc__.splitlines()[0])
    p.add_argument("--no-review", action="store_true", help="State pass only")
    p.add_argument(
        "--repos", default="", help="Comma-separated subset (default: all in repos.toml)"
    )
    p.add_argument("--days", type=int, default=30, help="First-review lookback (default 30)")
    p.add_argument("--date", default=None, help="Override today's date (YYYY-MM-DD)")
    args = p.parse_args()

    repos = list(load_repos())
    if args.repos:
        wanted = {r.strip() for r in args.repos.split(",") if r.strip()}
        unknown = wanted - {r.name for r in repos}
        if unknown:
            sys.exit(f"not in repos.toml: {', '.join(sorted(unknown))}")
        repos = [r for r in repos if r.name in wanted]
    today = args.date or datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    digest = run_sweep(repos, today=today, review=not args.no_review, days=args.days)
    print(digest)
