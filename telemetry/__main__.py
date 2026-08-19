"""CLI entry point for the guacamayo telemetry pipeline.

Usage:
    uv run telemetry --facts               # Refresh the fact table + inject dashboard regions
    uv run telemetry --consistency         # Emit the board-consistency report /wake renders
    uv run telemetry --board               # Emit the board state snapshot /wake reads

Ported from ramseywise/librarian tools/cartographer/__main__.py:147-458 (`_run_facts`)
@ aa3166e (GUA-93), minus the derive-notes step (stays librarian) and the
--cron/--migrate/--compare/--enrich routes. Path defaults are repo-relative.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from telemetry.signals import SignalSources

from telemetry.log_config import configure_logging


class EmptyInputError(RuntimeError):
    """A stage ran with nothing to read.

    Raised instead of continuing on empty input. Continuing made an empty run look
    byte-for-byte like a healthy one from the outside — the pipeline could not
    distinguish "no input" from "fine" and stayed broken for eleven days
    (ramseywise/librarian#60). Local mirror of core/cron.py's class of the same name.
    """


def main() -> None:
    """Route to the appropriate telemetry subcommand."""
    configure_logging()
    if "--facts" in sys.argv:
        sys.argv.remove("--facts")
        _run_facts()
    elif "--consistency" in sys.argv:
        sys.argv.remove("--consistency")
        _run_consistency()
    elif "--board" in sys.argv:
        sys.argv.remove("--board")
        _run_board()
    else:
        print("usage: telemetry [--facts | --consistency | --board] [options]", file=sys.stderr)
        raise SystemExit(2)


# Regions the v2 board declares but no longer displays. Context Health ends at tool
# failures there, and the windowed COST-EFFICIENCY region absorbed the token/KPI cards.
# v1 still renders all six, so the renderers stay wired; only the v2 injection skips
# them. The markers stay declared on v2 (parked in the hidden block) so the
# board-completeness test still passes, but nothing is ever written into them.
_V2_RETIRED_REGIONS: frozenset[str] = frozenset(
    {
        "CONTEXT-ORCHESTRATION",
        "SUBAGENT-WINDOWS",
        "INSIGHTS-CONTEXT",
        "INPUT-TOKENS",
        "TOKEN-GRID",
        "INSIGHTS-KPI",
        "INSIGHTS-COST",
    }
)


# The ten repos wake's Phase 5 loop already walks (wake/SKILL.md:97). Reused rather
# than maintained separately — a second list would drift from the first, and a repo
# missing from the checker's copy would be silently unchecked.
ACTIVE_REPOS: tuple[str, ...] = (
    "guacamayo",
    "sisyphus",
    "learn-ai-engineering",
    "librarian",
    "atlas",
    "ai-project-template",
    "listen-wiseer",
    "playground",
    "lebanese-blonde",
    "galactus",
)


def _fetch_issues_with_bodies(repo: str, owner: str = "ramseywise") -> list[dict[str, Any]]:
    """Open issues including `body`, which `loop.collect_issues` does not request.

    Separate call rather than widening loop's `--json` set: that function feeds the
    dashboard's loop tab and stores its rows, and issue bodies are large enough that
    adding them there would bloat every consumer for one caller's benefit.
    """
    import json
    import shutil
    import subprocess

    if not shutil.which("gh"):
        return []
    try:
        out = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "-R",
                f"{owner}/{repo}",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,state,labels,body",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if out.returncode != 0 or not out.stdout.strip():
        return []
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []

    return [
        {
            "repo": repo,
            "number": issue.get("number", 0),
            "title": issue.get("title", ""),
            "state": (issue.get("state") or "").upper(),
            "labels": ",".join(sorted(lbl.get("name", "") for lbl in (issue.get("labels") or []))),
            "body": issue.get("body") or "",
        }
        for issue in payload
    ]


def _fetch_open_prs(repo: str, owner: str = "ramseywise") -> list[dict[str, Any]]:
    """Open PRs with title + body, for resolving `in-review` against real PRs."""
    import json
    import shutil
    import subprocess

    if not shutil.which("gh"):
        return []
    try:
        out = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "-R",
                f"{owner}/{repo}",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,title,state,body",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if out.returncode != 0 or not out.stdout.strip():
        return []
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []

    return [
        {
            "repo": repo,
            "number": pr.get("number", 0),
            "title": pr.get("title", ""),
            "state": (pr.get("state") or "").upper(),
            "body": pr.get("body") or "",
        }
        for pr in payload
    ]


def _fetch_prs_for_board(repo: str, owner: str = "ramseywise") -> list[dict[str, Any]]:
    """All PRs (open + merged) for board column derivation.

    Unlike `_fetch_open_prs` (which feeds `--consistency`), this fetches `--state all`
    so the `merged` column can be derived from PRs that have already closed. `headRefName`
    enables branch-name joins; `mergedAt` distinguishes merged from simply-closed.

    Returns [] on any failure — the caller tracks `skipped_repos` per-repo.
    Do NOT modify `_fetch_open_prs`; it is `--consistency`'s fetcher and must not change.
    """
    import json
    import shutil
    import subprocess

    if not shutil.which("gh"):
        return []
    try:
        out = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "-R",
                f"{owner}/{repo}",
                "--state",
                "all",
                "--limit",
                "100",
                "--json",
                "number,title,state,headRefName,body,mergedAt",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if out.returncode != 0 or not out.stdout.strip():
        return []
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []

    return [
        {
            "repo": repo,
            "number": pr.get("number", 0),
            "title": pr.get("title", ""),
            "state": (pr.get("state") or "").upper(),
            "head_ref": pr.get("headRefName") or "",
            "body": pr.get("body") or "",
            "merged_at": pr.get("mergedAt") or None,
        }
        for pr in payload
    ]


def _collect_branch_facts(
    repo: str,
    repo_root: Path,
) -> list[Any]:
    """Pre-compute merge-state facts for all convention-matching branches in one repo.

    Runs ``git branch -r`` to list remote branches, then
    ``git merge-base --is-ancestor`` against ``origin/main`` for each matching one.
    Returns a list of ``BranchFact`` objects.

    Non-resolution of ``origin/main`` (the galactus case before 2026-08-14 when the
    default branch was not main) yields BranchFacts with ``is_ancestor=None`` for
    every matching branch — the caller turns those into explicit findings rather than
    silent passes.

    All exceptions are caught: this runs across 10 repos and must not abort on a repo
    that is missing, has no remote, or has a detached HEAD.
    """
    import subprocess

    from telemetry.consistency import _BRANCH_CONVENTION_RE, BranchFact

    if not repo_root.is_dir():
        return []

    # Verify origin/main resolves before running any per-branch queries.
    try:
        verify = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", "origin/main"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        main_resolves = verify.returncode == 0 and bool(verify.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        main_resolves = False

    # List remote branches.
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "-r", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        branch_lines = out.stdout.splitlines() if out.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        branch_lines = []

    # Also check local branches — a branch that has never been pushed still matters.
    try:
        out_local = subprocess.run(
            ["git", "-C", str(repo_root), "branch", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        local_lines = out_local.stdout.splitlines() if out_local.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        local_lines = []

    # Strip remote prefix (e.g. "origin/GUA-114-foo" -> "GUA-114-foo")
    seen_names: set[str] = set()
    branch_names: list[str] = []
    for raw in branch_lines + local_lines:
        name = raw.strip()
        # Strip "origin/" prefix from remote refs
        name = name.removeprefix("origin/")
        if name in ("main", "HEAD", "") or name in seen_names:
            continue
        seen_names.add(name)
        branch_names.append(name)

    facts: list[BranchFact] = []
    for branch in branch_names:
        m = _BRANCH_CONVENTION_RE.match(branch)
        if not m:
            # bug/*, spike/*, or non-convention names — explicitly out of scope
            continue
        issue_num = int(m.group(2))

        if not main_resolves:
            facts.append(
                BranchFact(repo=repo, branch=branch, issue_num=issue_num, is_ancestor=None)
            )
            continue

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "merge-base",
                    "--is-ancestor",
                    branch,
                    "origin/main",
                ],
                capture_output=True,
                timeout=15,
                check=False,
            )
            is_ancestor = result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            is_ancestor = None

        facts.append(
            BranchFact(repo=repo, branch=branch, issue_num=issue_num, is_ancestor=is_ancestor)
        )

    return facts


def _run_board() -> None:
    """Emit the board state snapshot `/wake` reads instead of re-running gh sweeps.

    Derives one column per issue from issue state + PR state + branch facts. Write is
    atomic (tmp + os.replace); no .tmp file survives a successful run.

    Raises on a total gh failure — an empty board from a broken derivation is
    byte-for-byte a board where every issue closed (the librarian#60 lesson).

    The `skipped_repos` key is ALWAYS present in the output, even when empty. An absent
    key is indistinguishable from "no repos were skipped", which makes a truncated board
    presentable as a complete one.

    Heartbeat (GUA-118): every run — including failures — records `started_at`,
    `finished_at`, `exit`, and `duration_s` in the output so a stopped or crashed job
    leaves evidence it tried. On failure a minimal envelope with `exit != 0` is written
    atomically, so the reader sees the failure rather than a stale board from the last
    successful run.
    """
    import argparse
    import json
    import os
    import shutil
    import subprocess
    from datetime import UTC, datetime
    from pathlib import Path

    import structlog

    from telemetry import board as board_module
    from telemetry.consistency import BranchFact
    from telemetry.evaluator import evaluate
    from telemetry.loop import collect_plan_docs

    log = structlog.get_logger(__name__)

    repo_root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Emit the board state snapshot")
    p.add_argument("--workspace", default="~/workspace", help="Root holding the active repo clones")
    p.add_argument(
        "--out",
        default=str(repo_root / ".sounding" / "telemetry" / "board.json"),
        help="Output path (wake reads this)",
    )
    p.add_argument(
        "--repos",
        default=",".join(ACTIVE_REPOS),
        help="Comma-separated repos to check (default: wake's Phase 5 list)",
    )
    p.add_argument(
        "--act",
        action="store_true",
        default=False,
        help=(
            "Execute the two idempotent auto-mutations (auto_close_merged, auto_fix_label) "
            "for auto_eligible proposals. DEFAULT OFF — without --act, auto-eligible records "
            "degrade to proposals and ZERO subprocess calls to gh-for-mutation happen. "
            "Enable in scripts/telemetry-cron.sh only after the actions log shows proposal "
            "accuracy (uncomment the --act flag documented there)."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "With --act: print mutation calls instead of executing them. "
            "Writes to actions.jsonl are replaced with stdout. "
            "Without --act, this flag has no effect."
        ),
    )
    args = p.parse_args()

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    run_started = datetime.now(UTC)
    started_at = run_started.isoformat()

    def _write_failure_envelope(exc: BaseException, exit_code: int = 1) -> None:
        """Write a minimal heartbeat-only board.json so failures are visible."""
        finished = datetime.now(UTC)
        envelope = {
            "collected_at": started_at,
            "repos_checked": [],
            "skipped_repos": [],
            "total_issues": 0,
            "heartbeat": {
                "started_at": started_at,
                "finished_at": finished.isoformat(),
                "exit": exit_code,
                "duration_s": round((finished - run_started).total_seconds(), 2),
                "error": str(exc),
            },
            "proposed_actions": [],  # required key; empty on failure (GUA-119)
            "records": [],
        }
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, out_path)

    workspace = Path(args.workspace).expanduser()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]

    all_issues: list[dict] = []
    skipped_repos: list[dict[str, str]] = []
    repos_checked: list[str] = []

    # Per-repo data buckets
    prs_by_repo: dict[str, list[dict]] = {}
    pr_fetch_ok_by_repo: dict[str, bool] = {}
    branch_facts_by_repo: dict[str, list[BranchFact]] = {}

    try:
        for repo in repos:
            root = workspace / repo

            # Branch facts
            if root.is_dir():
                branch_facts_by_repo[repo] = _collect_branch_facts(repo, root)
            else:
                branch_facts_by_repo[repo] = []

            # Issues
            issues = _fetch_issues_with_bodies(repo)

            # Distinguish "no open issues" from "gh failed" by probing the repo if empty
            fetch_failed = False
            if not issues:
                # Quick existence check: gh repo view returns 0 even for repos with no issues
                if not shutil.which("gh"):
                    fetch_failed = True
                else:
                    try:
                        probe = subprocess.run(
                            ["gh", "repo", "view", f"ramseywise/{repo}"],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            check=False,
                        )
                        fetch_failed = probe.returncode != 0
                    except (subprocess.SubprocessError, OSError):
                        fetch_failed = True

            if fetch_failed:
                skipped_repos.append({"repo": repo, "reason": "gh issue fetch failed"})
                log.warning("board.issue_fetch_failed", repo=repo)
                continue

            # PRs for board
            prs = _fetch_prs_for_board(repo)
            pr_ok = True
            if not prs:
                # Same probe: distinguish "no PRs" from "gh pr fetch failed"
                if not shutil.which("gh"):
                    pr_ok = False
                else:
                    try:
                        probe = subprocess.run(
                            ["gh", "repo", "view", f"ramseywise/{repo}"],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            check=False,
                        )
                        pr_ok = probe.returncode == 0
                    except (subprocess.SubprocessError, OSError):
                        pr_ok = False

            if not pr_ok:
                skipped_repos.append({"repo": repo, "reason": "gh PR fetch failed"})
                log.warning("board.pr_fetch_failed", repo=repo)
                # Still include issues but mark pr_fetch_ok=False so derivation uses undetermined
                pr_fetch_ok_by_repo[repo] = False
            else:
                pr_fetch_ok_by_repo[repo] = True

            prs_by_repo[repo] = prs
            all_issues.extend(issues)
            repos_checked.append(repo)

        if not all_issues:
            exc = EmptyInputError(
                f"no issues fetched across {len(repos)} repos — refusing to write a board "
                "on what is almost certainly a gh failure"
            )
            _write_failure_envelope(exc)
            print(f"FATAL: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

        plans = collect_plan_docs(workspace)
        plan_issues = {(d.repo, d.issue) for d in plans if d.issue is not None}

        now_ts = datetime.now(UTC).isoformat()

        records: list[board_module.BoardRecord] = []
        for issue in all_issues:
            repo = str(issue.get("repo") or "")
            record = board_module.derive_column(
                issue=issue,
                prs_for_repo=prs_by_repo.get(repo, []),
                branch_facts_for_repo=branch_facts_by_repo.get(repo, []),
                plan_issues=plan_issues,
                pr_fetch_ok=pr_fetch_ok_by_repo.get(repo, True),
                collected_at=now_ts,
            )
            records.append(record)

        # Flatten branch facts across all repos for the evaluator.
        all_branch_facts = [bf for bfs in branch_facts_by_repo.values() for bf in bfs]

        # Load cascade state for the reconcile_plan_status rule (absent file = None).
        cascade_state: dict[str, Any] | None = None
        cascade_path = repo_root / ".sounding" / "telemetry" / "cascade-state.json"
        if cascade_path.exists():
            try:
                import json as _json

                cascade_state = _json.loads(cascade_path.read_text(encoding="utf-8"))
            except Exception:
                log.warning("board.cascade_state_load_failed", path=str(cascade_path))

        # Consistency checks for the evaluator — only the merged-branch rule; label checks
        # require open PRs which _run_board fetches for derivation, not for consistency.
        # The evaluator's close_issue rule is the primary consumer here.
        from telemetry.consistency import check_merged_branch_open_issue

        merged_inconsistencies = check_merged_branch_open_issue(all_branch_facts, all_issues)

        proposals = evaluate(records, all_branch_facts, merged_inconsistencies, cascade_state)

        run_finished = datetime.now(UTC)
        heartbeat = {
            "started_at": started_at,
            "finished_at": run_finished.isoformat(),
            "exit": 0,
            "duration_s": round((run_finished - run_started).total_seconds(), 2),
            "error": None,
        }

        payload = board_module.to_board_json(
            records, skipped_repos, repos_checked, heartbeat, proposals
        )

        tmp_path = out_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp_path, out_path)  # atomic

        # Auto-mutations (GUA-119 step 6): only when --act is passed explicitly.
        # Without --act, auto-eligible proposals stay as proposals — ZERO gh mutation
        # calls happen. This is a structural guarantee: the import only occurs here,
        # inside the --act branch.
        if args.act:
            from telemetry.actions import run_eligible_actions

            # Flatten all PRs for the close-issue handler (needs body + repo)
            all_prs_for_actions: list[dict] = []
            for repo_name, repo_prs in prs_by_repo.items():
                for pr in repo_prs:
                    pr_with_repo = dict(pr)
                    pr_with_repo.setdefault("repo", repo_name)
                    all_prs_for_actions.append(pr_with_repo)

            action_results = run_eligible_actions(
                proposals,
                branch_facts=all_branch_facts,
                prs=all_prs_for_actions,
                records=records,
                dry_run=args.dry_run,
            )
            acted = sum(1 for r in action_results if r.get("outcome") == "acted")
            declined = sum(1 for r in action_results if r.get("outcome") == "declined")
            print(
                f"Actions: {len(action_results)} eligible dispatched; {acted} acted, {declined} declined"
            )

    except SystemExit:
        raise  # already handled above — failure envelope written before SystemExit
    except Exception as exc:
        _write_failure_envelope(exc)
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Column breakdown for coverage line
    col_counts: dict[str, int] = {}
    for r in records:
        col_counts[r.column] = col_counts.get(r.column, 0) + 1

    col_str = " ".join(
        f"{col}={col_counts.get(col, 0)}"
        for col in ("closed", "merged", "in_review", "in_progress", "backlog", "undetermined")
    )

    print(
        f"Board: {payload['total_issues']} issues across {len(repos_checked)} repos; "
        f"{len(skipped_repos)} skipped -> {out_path}"
    )
    print(f"Columns: {col_str}")


def _run_consistency() -> None:
    """Emit the board-consistency report `/wake` renders instead of re-deriving.

    Two sources fold into one report: label-vs-artifact from `consistency.py`,
    and plan<->issue drift from `loop.detect_drift` (already bidirectional —
    this does not reimplement it).

    Path checking was a third source and was removed after its first live run
    (65 findings, all false positives). See the `consistency.py` docstring.

    Raises on a total `gh` failure. An empty report from a broken fetch is
    byte-for-byte a clean board from the outside, which is the librarian#60
    lesson stated at `EmptyInputError` above.
    """
    import argparse
    import json
    from pathlib import Path

    from telemetry.consistency import (
        BranchFact,
        Inconsistency,
        check_label_artifact,
        check_merged_branch_open_issue,
        to_report,
    )
    from telemetry.loop import collect_plan_docs, detect_drift

    repo_root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Emit the board-consistency report")
    p.add_argument("--workspace", default="~/workspace", help="Root holding the active repo clones")
    p.add_argument(
        "--out",
        default=str(repo_root / ".sounding" / "telemetry" / "consistency.json"),
        help="Report path (wake reads this)",
    )
    p.add_argument(
        "--repos",
        default=",".join(ACTIVE_REPOS),
        help="Comma-separated repos to check (default: wake's Phase 5 list)",
    )
    args = p.parse_args()

    workspace = Path(args.workspace).expanduser()
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]

    issues: list[dict[str, Any]] = []
    prs: list[dict[str, Any]] = []
    repo_roots: dict[str, Path] = {}
    branch_facts: list[BranchFact] = []
    for repo in repos:
        root = workspace / repo
        if root.is_dir():
            repo_roots[repo] = root
            branch_facts.extend(_collect_branch_facts(repo, root))
        issues.extend(_fetch_issues_with_bodies(repo))
        prs.extend(_fetch_open_prs(repo))

    if not issues:
        exc = EmptyInputError(
            f"no issues fetched across {len(repos)} repos — refusing to report a clean "
            "board on what is almost certainly a gh failure"
        )
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    plans = collect_plan_docs(workspace)
    plan_issues = {(d.repo, d.issue) for d in plans if d.issue is not None}
    unmatchable_plans = sum(1 for d in plans if d.issue is None)

    findings: list[Inconsistency] = []

    findings.extend(check_label_artifact(issues, prs, plan_issues))
    findings.extend(check_merged_branch_open_issue(branch_facts, issues))

    # Plan<->issue drift is loop.py's, already bidirectional. Folded in as
    # Inconsistency rows so wake renders one table, not two.
    for drift in detect_drift(plans, issues):
        findings.append(
            Inconsistency(
                kind="plan-issue-drift",
                repo=drift.repo,
                issue=drift.issue,
                detail=f"plan {Path(drift.path).name} reads {drift.status}",
                evidence=f"{drift.reason} (labels: {drift.label})",
            )
        )

    report = to_report(
        findings,
        issues_checked=len(issues),
        repos_checked=list(repo_roots),
        unmatchable_plans=unmatchable_plans,
    )

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    by_kind = ", ".join(f"{k}={v}" for k, v in sorted(report["counts_by_kind"].items())) or "none"
    # Coverage leads: unmatchable_plans beside total means a reader cannot mistake
    # "0 findings from 9 of 112 plans" for "board is clean".
    print(
        f"Consistency: {report['total']} findings ({by_kind}); "
        f"{unmatchable_plans} of {len(plans)} plans unevaluable -> {out_path}"
    )
    print(
        f"Coverage: {len(issues)} issues across {len(repo_roots)} repos; "
        f"{unmatchable_plans} plans join to no issue"
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL log, skipping malformed lines rather than failing the run.

    The hook logs are appended to by shell hooks; a truncated final line during a
    concurrent write must not abort verdict scoring.
    """
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _build_signal_sources(
    store: Path,
    workspace: Path,
    hook_log: Path,
    hook_pass_log: Path,
) -> SignalSources:
    """Assemble every source a signal resolver may read.

    Passing only session rows (the pre-2026-08-19 behaviour) would make every
    git-, hooklog-, findings- and repofile-backed signal silently resolve to
    "no data" -- indistinguishable from a genuine empty window.
    """
    from telemetry.factstore import read_all, read_findings
    from telemetry.gitstore import read_git_activity, read_issues, read_prs
    from telemetry.signals import SignalSources

    return SignalSources(
        sessions=read_all(store),
        git_activity=read_git_activity(store),
        prs=read_prs(store),
        issues=read_issues(store),
        findings=read_findings(store),
        hook_log=_read_jsonl(hook_log),
        hook_pass_log=_read_jsonl(hook_pass_log),
        workspace=workspace,
    )


def _report_signal_coverage(experiments: list[Any]) -> None:
    """Print which ledger rows are scorable and, for the rest, *why* not.

    The failure this addresses: 49 of 59 rows reported one collapsed
    `inconclusive` message, so a row nobody had registered looked identical to a
    row no telemetry could ever observe. The three causes have different owners --
    register a name, change a collector, or rewrite the hypothesis -- so they are
    listed separately with the names spelled out.
    """
    from telemetry import signals
    from telemetry.verdicts import _normalize_signal, parse_metric

    buckets: dict[str, list[str]] = {
        signals.UNREGISTERED: [],
        signals.NEEDS_COLLECTION: [],
        signals.UNOBSERVABLE: [],
    }
    scorable = 0
    untyped = 0

    for exp in experiments:
        clauses = parse_metric(exp.metric)
        if not clauses:
            untyped += 1
            continue
        states = {}
        for clause in clauses:
            name = _normalize_signal(clause.signal)
            states[name] = signals.state_of(name)
        if all(state == signals.REGISTERED for state in states.values()):
            scorable += 1
            continue
        # Report the row under its most actionable blocker, worst-first.
        for state in (signals.UNREGISTERED, signals.NEEDS_COLLECTION, signals.UNOBSERVABLE):
            named = sorted(n for n, s in states.items() if s == state)
            if named:
                buckets[state].extend(named)
                break

    total = len(experiments)
    print(f"  scorable: {scorable}/{total} ({untyped} rows carry no typed metric)")

    labels = [
        (signals.UNREGISTERED, "unregistered — declare in telemetry/signals.py"),
        (signals.NEEDS_COLLECTION, "needs collection change — capture the field first"),
        (signals.UNOBSERVABLE, "unobservable — rewrite the hypothesis"),
    ]
    for state, label in labels:
        names = sorted(set(buckets[state]))
        if not names:
            continue
        print(f"  {len(names)} {label}:")
        for name in names:
            print(f"    - {name}")


def _run_facts() -> None:
    """Refresh the session fact table and inject dashboard regions.

    Capture is cheap and needs no API key, so this is the piece that runs daily —
    local JSONL rotates out in roughly five days, and anything not captured before
    then is gone for good.
    """
    import argparse
    from datetime import UTC, datetime
    from pathlib import Path

    from telemetry import sessions as sessions_module
    from telemetry.factstore import (
        from_findings_jsonl,
        from_jsonl,
        from_notes,
        read_all,
        upsert,
        upsert_findings,
    )

    repo_root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Refresh the session fact table + dashboard regions")
    # The live fact store is librarian's, not guacamayo's: the daily cartographer
    # job passes --store pointing there, and librarian owns session derivation.
    # This default previously resolved to guacamayo/data/sessions.db, which nothing
    # scheduled ever wrote -- a manual un-flagged run would write that copy and
    # every reader of it would then report ~stale-by-N-days against a store the
    # pipeline had abandoned (misdiagnosed as "telemetry is broken", 2026-08-12).
    p.add_argument(
        "--store",
        default=str(Path("~/workspace/librarian/data/sessions.db").expanduser()),
        help="Session fact store (default: librarian's, which the daily job writes)",
    )
    p.add_argument("--projects-dir", default="~/.claude/projects")
    p.add_argument(
        "--notes-dir",
        default="~/workspace/librarian/data/raw/sessions",
        help=(
            "Session-note directory (note era, Apr-Jun). Cross-repo read-only — "
            "librarian derives and owns the notes; skipped with a warning if absent"
        ),
    )
    p.add_argument(
        "--dashboard",
        default=None,
        help=(
            "Opt-in full-page dashboard render path (engine artifact). The daily job "
            "does not pass this — region injection into --context-dashboard is the "
            "supported refresh (ramseywise/librarian#60/#68)"
        ),
    )
    p.add_argument(
        "--context-dashboard",
        default=str(repo_root / ".sounding" / "context-dashboard.html"),
        help=(
            "Path to the shared context-dashboard.html for region injection. "
            "Telemetry injects only the regions it owns (REVIEW-FINDINGS, "
            "EXPERIMENTS-LIFECYCLE, LOOP-CLOSURE, INPUT-TOKENS, SKILL-ECONOMICS, "
            "TOOL-TRENDS, FRICTION-REGROUP, SKILL-EVALS, LOOP); all other regions "
            "and hand-written "
            "content are left untouched."
        ),
    )
    p.add_argument(
        "--growth-md",
        default=str(repo_root / ".sounding" / "growth" / "growth.md"),
    )
    p.add_argument("--stale-days", type=int, default=3)
    p.add_argument(
        "--no-inject", action="store_true", help="Skip region injection into context-dashboard.html"
    )
    p.add_argument("--workspace", default="~/workspace", help="Root scanned for git repos")
    p.add_argument("--no-git", action="store_true", help="Skip repo-activity collection")
    p.add_argument(
        "--plans-root",
        default="~/workspace",
        help=(
            "Root scanned for plan docs at <root>/*/.claude/docs/plans/*.md (loop tab). "
            "Deliberately not librarian's ingested copies under data/raw/claude-docs/, "
            "which would double-count the corpus"
        ),
    )
    p.add_argument(
        "--findings",
        default=str(repo_root / ".claude" / "docs" / "review-findings.jsonl"),
        help="Review findings JSONL for the review card",
    )
    p.add_argument(
        "--eval-results",
        default=str(repo_root / ".sounding" / "eval-results.jsonl"),
        help="Skill eval results JSONL (written by scripts/eval-runner.sh) for the eval tab",
    )
    p.add_argument(
        "--ledger",
        default=str(repo_root / ".sounding" / "tooling-ledger.md"),
        help="Tooling ledger path for the experiments card",
    )
    p.add_argument(
        "--ledger-log",
        default=None,
        help="Tooling ledger log path (optional, for archived experiments)",
    )
    p.add_argument(
        "--no-verdicts",
        action="store_true",
        help="Skip deterministic verdict scoring against the tooling ledger",
    )
    # Hook sinks moved out of global ~/.claude into this repo (2026-08-12) -- guacamayo
    # owns the pipeline that reads them, so data and consumer now live together. The
    # writer is ~/.claude/hooks/lib.sh, which honours CLAUDE_TELEMETRY_DIR and falls
    # back to ~/.claude when this repo is absent; these defaults mirror that.
    p.add_argument(
        "--hook-log",
        default=str(repo_root / ".sounding" / "telemetry" / ".hook-log.jsonl"),
        help="Guard-hook event log (blocks/warns) for the hook-activity card",
    )
    p.add_argument(
        "--hook-pass-log",
        default=str(repo_root / ".sounding" / "telemetry" / ".hook-pass-log.jsonl"),
        help="Guard-hook pass log (silent OKs) for the hook-activity card",
    )
    p.add_argument(
        "--actions-log",
        default=str(repo_root / ".sounding" / "telemetry" / "actions.jsonl"),
        help="Automated-actions event log (GUA-119) for the automated-actions tile",
    )
    args = p.parse_args()

    store = Path(args.store).expanduser()
    store.parent.mkdir(parents=True, exist_ok=True)

    projects_dir = Path(args.projects_dir).expanduser()
    jsonl_sessions = sessions_module.iter_sessions(projects_dir)
    if not jsonl_sessions:
        # Fail loud. Continuing here would upsert an empty fact table and exit 0,
        # which is byte-for-byte how a healthy run looks from the outside (#60).
        exc = EmptyInputError(
            f"no JSONL sessions found in {projects_dir} — refusing to run on empty input"
        )
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    # Note derivation stays in librarian; its notes dir is read cross-repo when present.
    notes_dir = Path(args.notes_dir).expanduser()
    if notes_dir.exists():
        rows = from_notes(notes_dir)
    else:
        print(f"WARNING: notes dir not found, skipping note era: {notes_dir}", file=sys.stderr)
        rows = []
    rows += from_jsonl(projects_dir)
    written = upsert(rows, store)
    print(f"Fact table: {written} rows upserted -> {store}")

    findings_path = Path(args.findings).expanduser()
    finding_rows = from_findings_jsonl(findings_path)
    findings_written = upsert_findings(finding_rows, store)
    print(f"Findings table: {findings_written} rows upserted -> {store}")

    from telemetry.recurrence import RECURRENCE_THRESHOLD, compute_recurrence

    recurrence_groups = compute_recurrence(finding_rows)
    promotable = sum(1 for g in recurrence_groups if g.promotable)
    print(
        f"Recurrence: {len(recurrence_groups)} groups, {promotable} promotable "
        f"(threshold >= {RECURRENCE_THRESHOLD})"
    )

    if not args.no_git:
        from telemetry.gitstore import refresh as refresh_git

        commits, prs, issues = refresh_git(Path(args.workspace).expanduser(), store)
        print(f"Repo activity: {commits} commit-days, {prs} PRs, {issues} issues")

    if not args.no_verdicts:
        from telemetry.dashboard import parse_ledger
        from telemetry.factstore import append_verdicts, read_all
        from telemetry.verdicts import score_metric

        ledger_path = Path(args.ledger).expanduser()
        ledger_log_path = Path(args.ledger_log).expanduser() if args.ledger_log else None
        if ledger_path.exists():
            experiments = parse_ledger(ledger_path, ledger_log_path)
            run_at = datetime.now(UTC).isoformat()
            sources = _build_signal_sources(
                store,
                Path(args.workspace).expanduser(),
                Path(args.hook_log).expanduser(),
                Path(args.hook_pass_log).expanduser(),
            )
            verdict_rows = []
            for exp in experiments:
                verdict = score_metric(exp.metric, sources)
                verdict_rows.append(
                    {
                        "experiment": exp.name,
                        "date": exp.date,
                        "metric": exp.metric,
                        "verdict": verdict.verdict,
                        "evidence": verdict.evidence,
                    }
                )
            appended = append_verdicts(verdict_rows, store, run_at)
            print(f"Verdicts: {appended} scored -> {store}")
            _report_signal_coverage(experiments)
        else:
            print(f"Verdicts: skipped — ledger not found at {ledger_path}")

    if args.dashboard:
        from telemetry.dashboard import (
            parse_findings,
            patch_experiments_card,
            patch_friction_regroup_card,
            patch_hook_activity_card,
            patch_input_tokens_card,
            patch_review_findings,
            patch_skill_economics_card,
            patch_tool_trends_card,
        )

        dashboard = Path(args.dashboard).expanduser()
        findings_path = Path(args.findings).expanduser()
        ledger_path = Path(args.ledger).expanduser()
        ledger_log_path = Path(args.ledger_log).expanduser() if args.ledger_log else None

        findings = parse_findings(findings_path) if findings_path.exists() else []
        if patch_review_findings(dashboard, findings):
            print(f"Dashboard: review card refreshed ({len(findings)} findings) -> {dashboard}")
        else:
            print(f"Dashboard: skipped — {dashboard} missing or has no REVIEW-FINDINGS markers")

        if patch_input_tokens_card(dashboard, store):
            print("Dashboard: input-tokens card refreshed")
        else:
            print("Dashboard: input-tokens card skipped (missing markers)")

        if patch_skill_economics_card(dashboard, store):
            print("Dashboard: skill-economics card refreshed")
        else:
            print("Dashboard: skill-economics card skipped (missing markers)")

        if patch_tool_trends_card(dashboard, store):
            print("Dashboard: tool-trends card refreshed")
        else:
            print("Dashboard: tool-trends card skipped (missing markers)")

        if patch_friction_regroup_card(dashboard, store):
            print("Dashboard: friction-regroup card refreshed")
        else:
            print("Dashboard: friction-regroup card skipped (missing markers)")

        if patch_experiments_card(
            dashboard, ledger_path=ledger_path, ledger_log_path=ledger_log_path
        ):
            print("Dashboard: experiments card refreshed")
        else:
            print("Dashboard: experiments card skipped (missing markers)")

        hook_log = Path(args.hook_log).expanduser()
        hook_pass_log = Path(args.hook_pass_log).expanduser()
        if patch_hook_activity_card(dashboard, hook_log, hook_pass_log):
            print("Dashboard: hook-activity card refreshed")
        else:
            print("Dashboard: hook-activity card skipped (missing markers)")

    # Deliberately NOT gated on --dashboard. The full-page render is opt-in and the
    # daily job never passes it; region injection is the behaviour that replaced it —
    # coupling them would mean the daily job never refreshes a region. --no-inject is
    # the only opt-out.
    if not args.no_inject:
        from telemetry.dashboard import (
            inject_regions,
            parse_actions_log,
            parse_eval_results,
            parse_findings,
            parse_ledger,
            render_automated_actions_region,
            render_context_health_kpi_region,
            render_context_orchestration_card,
            render_cost_efficiency_region,
            render_eval_results_region,
            render_experiments_region,
            render_failure_kinds_region,
            render_friction_regroup_card,
            render_input_tokens_card,
            render_insights_kpi_region,
            render_insights_region,
            render_insights_tab_region,
            render_loop_closure_card,
            render_loop_region,
            render_pipeline_health_region,
            render_retro_region,
            render_review_findings_region,
            render_scope_decisions_region,
            render_session_health_region,
            render_skill_economics_card,
            render_subagent_windows_card,
            render_token_grid_region,
            render_tool_trends_card,
            render_verdict_trajectories_region,
        )
        from telemetry.factstore import read_verdicts
        from telemetry.gitstore import read_issues
        from telemetry.loop import collect_plan_docs

        ctx_path = Path(args.context_dashboard).expanduser()
        if ctx_path.exists():
            ledger_path = Path(args.ledger).expanduser()
            ledger_log_path = Path(args.ledger_log).expanduser() if args.ledger_log else None
            experiments = (
                parse_ledger(ledger_path, ledger_log_path) if ledger_path.exists() else None
            )
            findings_path = Path(args.findings).expanduser()
            review_findings = parse_findings(findings_path) if findings_path.exists() else None
            eval_results_path = Path(args.eval_results).expanduser()
            eval_results = (
                parse_eval_results(eval_results_path) if eval_results_path.exists() else None
            )
            actions_log_path = Path(args.actions_log).expanduser()
            action_records = (
                parse_actions_log(actions_log_path) if actions_log_path.exists() else None
            )

            regions: dict[str, str] = {
                "REVIEW-FINDINGS": render_review_findings_region(review_findings),
                "EXPERIMENTS-LIFECYCLE": render_experiments_region(experiments or None, store),
                "LOOP-CLOSURE": render_loop_closure_card(
                    Path(args.ledger_log).expanduser()
                    if args.ledger_log
                    else Path(args.ledger).expanduser().parent / "tooling-ledger-log.md"
                ),
                "PIPELINE-HEALTH": render_pipeline_health_region(store),
                "SCOPE-DECISIONS": render_scope_decisions_region(
                    Path(args.actions_log).expanduser().parent / "scope-decisions.jsonl"
                ),
                "INPUT-TOKENS": render_input_tokens_card(store),
                "SKILL-ECONOMICS": render_skill_economics_card(store),
                "TOOL-TRENDS": render_tool_trends_card(store),
                "FAILURE-KINDS": render_failure_kinds_region(store),
                "FRICTION-REGROUP": render_friction_regroup_card(store),
                "SKILL-EVALS": render_eval_results_region(eval_results),
                "LOOP": render_loop_region(
                    collect_plan_docs(Path(args.plans_root).expanduser()),
                    read_issues(store),
                ),
                "AUTOMATED-ACTIONS": render_automated_actions_region(action_records),
                "SUBAGENT-WINDOWS": render_subagent_windows_card(store),
                "INSIGHTS-KPI": render_insights_kpi_region(store),
                "SESSION-HEALTH": render_session_health_region(store),
                "COST-EFFICIENCY": render_cost_efficiency_region(store),
                "CONTEXT-HEALTH-KPI": render_context_health_kpi_region(store),
                "TOKEN-GRID": render_token_grid_region(store),
                "INSIGHTS-COST": render_insights_tab_region(
                    ctx_path.parent / "insights" / "insights-report.html", "cost"
                ),
                "INSIGHTS-CONTEXT": render_insights_tab_region(
                    ctx_path.parent / "insights" / "insights-report.html", "context"
                ),
                "CONTEXT-ORCHESTRATION": render_context_orchestration_card(store),
                "RETRO": render_retro_region(
                    findings=review_findings,
                    experiments=experiments or None,
                    verdict_rows=read_verdicts(store),
                    store=store,
                ),
                "OVERVIEW": render_insights_region(
                    ctx_path.parent / "insights" / "insights-report.html",
                    today=datetime.now(UTC).date().isoformat(),
                ),
                "VERDICT-TRAJECTORIES": render_verdict_trajectories_region(read_verdicts(store)),
            }
            # The v2 board retired these three from Context Health (which now ends at
            # tool failures), but v1 still renders them, so the renderers stay wired.
            # Their markers remain declared on v2 — parked in the hidden block so the
            # board-completeness test still passes — and are left empty here rather
            # than refilled on every run.
            if ctx_path.name == "context-dashboard-v2.html":
                regions = {k: v for k, v in regions.items() if k not in _V2_RETIRED_REGIONS}
            injected = inject_regions(ctx_path, regions)
            print(f"Region injection: {injected}")
        else:
            print(f"context-dashboard not found, skipping injection: {ctx_path}", flush=True)

    # Staleness guard: the newest row aging past --stale-days means capture is not
    # keeping up with the ~5-day JSONL retention window, i.e. history is being lost.
    stored = read_all(store)
    newest = max((r["date"] for r in stored), default="")
    if newest:
        age = (datetime.now(UTC).date() - datetime.fromisoformat(newest).date()).days
        if age > args.stale_days:
            print(
                f"WARNING: newest fact row is {age} days old ({newest}). "
                f"Local JSONL rotates in ~5 days — sessions may already be lost. "
                f"Check the scheduled --facts run.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
