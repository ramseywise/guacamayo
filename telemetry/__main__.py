"""CLI entry point for the guacamayo telemetry pipeline.

Usage:
    uv run telemetry --facts               # Refresh the fact table + inject dashboard regions

Ported from ramseywise/librarian tools/cartographer/__main__.py:147-458 (`_run_facts`)
@ aa3166e (GUA-93), minus the derive-notes step (stays librarian) and the
--cron/--migrate/--compare/--enrich routes. Path defaults are repo-relative.
"""

from __future__ import annotations

import sys

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
    else:
        print("usage: telemetry --facts [options]", file=sys.stderr)
        raise SystemExit(2)


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
    p.add_argument("--store", default=str(repo_root / "data" / "sessions.db"))
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
            "EXPERIMENTS-LIFECYCLE, INPUT-TOKENS, SKILL-ECONOMICS, TOOL-TRENDS, "
            "FRICTION-REGROUP, SKILL-EVALS, LOOP); all other regions and hand-written "
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
    p.add_argument(
        "--hook-log",
        default=str(Path("~/.claude/.hook-log.jsonl").expanduser()),
        help="Guard-hook event log (blocks/warns) for the hook-activity card",
    )
    p.add_argument(
        "--hook-pass-log",
        default=str(Path("~/.claude/.hook-pass-log.jsonl").expanduser()),
        help="Guard-hook pass log (silent OKs) for the hook-activity card",
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
            scored_rows = read_all(store)
            run_at = datetime.now(UTC).isoformat()
            verdict_rows = []
            for exp in experiments:
                verdict = score_metric(exp.metric, scored_rows)
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
            parse_eval_results,
            parse_findings,
            parse_ledger,
            render_eval_results_region,
            render_experiments_region,
            render_friction_regroup_card,
            render_input_tokens_card,
            render_loop_region,
            render_review_findings_region,
            render_skill_economics_card,
            render_tool_trends_card,
        )
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

            regions: dict[str, str] = {
                "REVIEW-FINDINGS": render_review_findings_region(review_findings),
                "EXPERIMENTS-LIFECYCLE": render_experiments_region(experiments or None),
                "INPUT-TOKENS": render_input_tokens_card(store),
                "SKILL-ECONOMICS": render_skill_economics_card(store),
                "TOOL-TRENDS": render_tool_trends_card(store),
                "FRICTION-REGROUP": render_friction_regroup_card(store),
                "SKILL-EVALS": render_eval_results_region(eval_results),
                "LOOP": render_loop_region(
                    collect_plan_docs(Path(args.plans_root).expanduser()),
                    read_issues(store),
                ),
            }
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
