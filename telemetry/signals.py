"""Declared signal namespace for ledger hypotheses (GUA telemetry, 2026-08-19).

`verdicts.py` scores a metric clause; this module owns *what a signal name means*
and whether it can be measured at all. Both the scorer and the `/track`
authoring skill import from here so a hypothesis cannot be written against a name
the system will silently fail to resolve.

Why a registry rather than a pattern match
------------------------------------------
Naively grepping a signal slug against session text would either always return 0
(a false "confirmed" for an absence claim) or require unbounded heuristics. Only
names with a declared resolver are scorable; everything else reports *why* it is
not -- which is the whole point, because "unscorable" has four distinct causes
that were previously indistinguishable.

The four states
---------------
    REGISTERED        resolver exists; scores normally.
    NEEDS_COLLECTION  observable in principle, but the field is not captured yet.
                      The fix is upstream of this registry -- a collection change,
                      named in `remedy`. NOT the author's fault, and NOT
                      unobservable.
    UNOBSERVABLE      no event stream could record this claim. The fix is to
                      rewrite the hypothesis into a countable form.
    (absent)          unregistered -- an authoring gap.

The registry has two parts: ``_ENTRIES`` (Signal objects with REGISTERED /
NEEDS_COLLECTION / UNOBSERVABLE states) and ``_UNOBSERVABLE`` (names that have
no conceivable event stream). Together they cover every slug an author might
write. Run ``python -m telemetry.signals`` for the live count; as of 2026-08-19:
28 ``_ENTRIES`` (21 REGISTERED) + 36 ``_UNOBSERVABLE`` names = 64 declared; 21
scorable.

Source bundle
-------------
Resolvers receive a `SignalSources` bundle rather than only `sessions` rows,
because the answerable signals live across four stores (session facts, git
tables, the hook logs, and repo file content). A resolver returns `None` when its
source has no data for the window -- distinct from a genuine zero, so an absence
claim is never confirmed by silence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC
from datetime import date as _date
from datetime import datetime as _datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Registry states
# ---------------------------------------------------------------------------

REGISTERED = "registered"
NEEDS_COLLECTION = "needs-collection"
UNOBSERVABLE = "unobservable"
UNREGISTERED = "unregistered"

# Source kinds -- what a resolver reads. Used by the skill to tell an author
# which collection path a new signal would depend on.
KIND_SESSION = "session"
KIND_GIT = "git"
KIND_HOOKLOG = "hooklog"
KIND_FINDINGS = "findings"
KIND_REPOFILE = "repofile"


@dataclass
class SignalSources:
    """Everything a resolver may read, assembled once per scoring run.

    Every field defaults to empty/None so a caller that only has session rows
    (the pre-2026-08-19 signature) still works -- resolvers needing an absent
    source return None ("no data"), never a fabricated zero.
    """

    sessions: list[dict[str, Any]] = field(default_factory=list)
    git_activity: list[dict[str, Any]] = field(default_factory=list)
    prs: list[dict[str, Any]] = field(default_factory=list)
    issues: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    hook_log: list[dict[str, Any]] = field(default_factory=list)
    hook_pass_log: list[dict[str, Any]] = field(default_factory=list)
    branches: list[dict[str, Any]] = field(default_factory=list)
    workspace: Path | None = None


@dataclass(frozen=True)
class Signal:
    """One declared signal name.

    `resolver` is None for every non-REGISTERED state; `remedy` says what would
    have to change for the name to become scorable, and is required for
    NEEDS_COLLECTION and UNOBSERVABLE so no entry can be parked without an
    explanation an author can act on.
    """

    name: str
    state: str
    kind: str | None = None
    resolver: Callable[[SignalSources], float | None] | None = None
    description: str = ""
    remedy: str = ""


# ---------------------------------------------------------------------------
# Session-fact resolvers (moved from verdicts._SIGNAL_METRICS, unchanged)
# ---------------------------------------------------------------------------


def _bash_antipatterns_p50(src: SignalSources) -> float | None:
    values = [
        float(r["bash_antipatterns"])
        for r in src.sessions
        if r.get("bash_antipatterns") is not None
    ]
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])


def _output_tokens_p90(src: SignalSources) -> float | None:
    values = [float(r.get("output_tokens") or 0) for r in src.sessions]
    if not values:
        return None
    ordered = sorted(values)
    idx = min(round(0.9 * (len(ordered) - 1)), len(ordered) - 1)
    return float(ordered[idx])


_EXECUTION_GUARDRAIL_SKILLS = frozenset(
    {
        "workflow-execute",
        "workflow-review",
        "code-review",
        "code-debug",
        "code-refactor",
    }
)
"""Skills that count as execution guardrails for compliance measurement.

Identity skills (wake/grow/dream) and meta skills (insights/retro) are NOT
execution guardrails — counting them inflated this metric from 4.9% to 36%
(feedback-log 2026-08-20, C5).
"""


def _execution_skill_compliance_pct(src: SignalSources) -> float | None:
    exec_rows = [r for r in src.sessions if r.get("session_intent") == "execution"]
    if not exec_rows:
        return None
    with_skills = sum(
        1
        for r in exec_rows
        if _EXECUTION_GUARDRAIL_SKILLS & set(json.loads(r.get("skill_costs") or "{}"))
    )
    return round(100 * with_skills / len(exec_rows), 2)


def _cost_over_150k_share_pct(src: SignalSources) -> float | None:
    scored = [r for r in src.sessions if r.get("max_context") is not None]
    if not scored:
        return None
    total_cost = sum(float(r.get("cost_units") or 0) for r in scored)
    if not total_cost:
        return None
    over_cost = sum(
        float(r.get("cost_units") or 0) for r in scored if (r.get("max_context") or 0) >= 150_000
    )
    return round(100 * over_cost / total_cost, 2)


def _fable_share_of_cost_pct(src: SignalSources) -> float | None:
    """Share of total cost spent on fable across sessions with a `models` breakdown."""
    total = 0.0
    fable = 0.0
    scored = False
    for r in src.sessions:
        try:
            models: dict[str, Any] = json.loads(r.get("models") or "{}")
        except (TypeError, ValueError):
            continue
        if not models:
            continue
        scored = True
        for model, cost in models.items():
            c = float(cost) if isinstance(cost, int | float) else 0.0
            total += c
            if "fable" in model.lower():
                fable += c
    if not scored or not total:
        return None
    return round(100 * fable / total, 2)


# ---------------------------------------------------------------------------
# Class A resolvers -- store-backed, verified against the live store 2026-08-19
# ---------------------------------------------------------------------------


def _file_not_found_errors(src: SignalSources) -> float | None:
    """Total `file_not_found` tool errors across scored sessions (measured: 192)."""
    total = 0.0
    seen = False
    for r in src.sessions:
        raw = r.get("tool_errors")
        if not raw:
            continue
        try:
            errors: dict[str, Any] = json.loads(raw)
        except (TypeError, ValueError):
            continue
        seen = True
        for kind, count in errors.items():
            if "file_not_found" in kind:
                total += float(count or 0)
    return total if seen else None


def _unique_hooks_in_pass_log(src: SignalSources) -> float | None:
    """Distinct hooks that ever call `log_pass` (measured: 2).

    The ledger hypothesis is that the pass-log logger exists but hooks do not
    call it. This counts the distinct callers, which is the claim's own metric.
    """
    if not src.hook_pass_log:
        return None
    return float(len({d.get("hook") for d in src.hook_pass_log if d.get("hook")}))


def _co_authored_by_in_drafted_commits(src: SignalSources) -> float | None:
    """Commits carrying a Claude co-author trailer (measured: 14).

    Ramsey's standing rule is that no drafted commit names Claude as co-author,
    so this is an absence claim over `git_activity.commits_claude_trailer`.
    """
    values = [
        r.get("commits_claude_trailer")
        for r in src.git_activity
        if r.get("commits_claude_trailer") is not None
    ]
    if not values:
        return None
    return float(sum(values))


_SILENT_SWALLOW_RE = re.compile(r"silent|swallow", re.IGNORECASE)


def _silent_swallow_findings(src: SignalSources) -> float | None:
    """Review findings about silently-swallowed errors (measured: 88)."""
    if not src.findings:
        return None
    return float(
        sum(
            1
            for f in src.findings
            if _SILENT_SWALLOW_RE.search(f"{f.get('title') or ''} {f.get('category') or ''}")
        )
    )


def _hook_blocks(hook_name: str) -> Callable[[SignalSources], float | None]:
    """Build a resolver counting exit_code=2 (block) events for one hook."""

    def _resolve(src: SignalSources) -> float | None:
        if not src.hook_log:
            return None
        return float(
            sum(1 for d in src.hook_log if d.get("hook") == hook_name and d.get("exit_code") == 2)
        )

    return _resolve


# ---------------------------------------------------------------------------
# Class B: repo-file content
# ---------------------------------------------------------------------------
#
# Declared as explicit (repo, path-glob, pattern) triples rather than free-text
# grep, so an unregistered claim cannot become "scorable" by accident just
# because some file happens to contain a matching word.


@dataclass(frozen=True)
class FileClaim:
    repo: str
    glob: str
    pattern: str


def _repofile_resolver(claim: FileClaim) -> Callable[[SignalSources], float | None]:
    """Count files under `repo`/`glob` whose text matches `pattern`.

    Returns None (no data) when the workspace or repo is absent -- a missing
    checkout must never read as a confirmed absence.
    """
    regex = re.compile(claim.pattern, re.IGNORECASE | re.MULTILINE)

    def _resolve(src: SignalSources) -> float | None:
        if src.workspace is None:
            return None
        repo_root = src.workspace / claim.repo
        if not repo_root.is_dir():
            return None
        matches = 0
        for path in repo_root.glob(claim.glob):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if regex.search(text):
                matches += 1
        return float(matches)

    return _resolve


_HEAVY_SESSION_TOOL_CALLS = 100
"""What "heavy" means for `todowrite-in-heavy-sessions`.

The predecessor hypothesis was unobservable *only* because this number lived in
prose and differed per row. Pinning it here is what makes the claim scorable --
change it deliberately, never to make a metric pass.
"""


def _todowrite_in_heavy_sessions(src: SignalSources) -> float | None:
    """Heavy sessions with no TodoWrite call (the failure the hook should prevent)."""
    missing = 0
    seen = False
    for r in src.sessions:
        try:
            counts: dict[str, Any] = json.loads(r.get("tool_counts") or "{}")
        except (TypeError, ValueError):
            continue
        if not counts:
            continue
        if sum(float(v or 0) for v in counts.values()) < _HEAVY_SESSION_TOOL_CALLS:
            continue
        seen = True
        if not float(counts.get("TodoWrite") or 0):
            missing += 1
    return float(missing) if seen else None


_ACTIVE_LEDGER = Path(".sounding/tooling-ledger.md")


def _duplicate_ledger_signals(src: SignalSources) -> float | None:
    """Signals claimed by more than one active ledger row.

    Scorable from the ledger text alone -- no collector change. Guards the
    duplicate-row class the 2026-08-19 backlog audit found (#40/#41 were one
    finding written twice; two rows shared `execution-sessions-with-skills`).
    Imported lazily because `verdicts` imports this module.
    """
    if src.workspace is None:
        return None
    ledger = src.workspace / "guacamayo" / _ACTIVE_LEDGER
    if not ledger.is_file():
        return None
    from telemetry.verdicts import parse_metric

    counts: dict[str, int] = {}
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        for clause in parse_metric(line):
            key = normalize(clause.signal)
            counts[key] = counts.get(key, 0) + 1
    return float(sum(1 for n in counts.values() if n > 1))


_FEEDBACK_LOG = Path(".sounding/telemetry/feedback-log.md")
_FEEDBACK_RUN_HEADER = re.compile(r"^# Feedback Run\s*[—-]\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _feedback_run_age_days(src: SignalSources) -> float | None:
    """Days since the last /meta-feedback run.

    None when the workspace, repo or log is absent -- the gate is manual, so an
    unfired gate must read as "no data", never as a fresh zero.
    """
    if src.workspace is None:
        return None
    log = src.workspace / "guacamayo" / _FEEDBACK_LOG
    if not log.is_file():
        return None
    dates = _FEEDBACK_RUN_HEADER.findall(log.read_text(encoding="utf-8", errors="replace"))
    if not dates:
        return None
    try:
        newest = _date.fromisoformat(max(dates))
    except ValueError:
        return None
    # UTC, matching the dashboard's ageing ladder -- a local-time `today()` would
    # make the same log read one day older or younger than the rendered cell.
    return float((_datetime.now(UTC).date() - newest).days)


# ---------------------------------------------------------------------------
# Git-store resolvers: PR title/body + branch-level signals (GUA-163)
# ---------------------------------------------------------------------------

_SLUG_DERIVED_TITLE_RE = re.compile(r"^[A-Z]+-\d+ [A-Z]")
"""A PR title that is a branch slug: prefix-number then a capitalised word.

e.g. "GUA-163 Add branches table" is slug-derived; "Add branches table" is not.
The pattern requires at least one capital letter after the space so that
"GUA-163" alone (no description) is not a false positive.
"""


def _slug_derived_pr_titles(src: SignalSources) -> float | None:
    """Open PRs whose title appears to be derived from the branch slug."""
    open_prs = [p for p in src.prs if p.get("state") == "OPEN"]
    if not open_prs:
        return None
    return float(sum(1 for p in open_prs if _SLUG_DERIVED_TITLE_RE.match(p.get("title") or "")))


_CLOSING_LINK_RE = re.compile(r"(?i)(closes|fixes)\s+#\d+")


def _merged_prs_without_closing_links(src: SignalSources) -> float | None:
    """Merged PRs whose body carries no Closes #N or Fixes #N link."""
    merged = [p for p in src.prs if p.get("merged") == 1]
    if not merged:
        return None
    return float(sum(1 for p in merged if not _CLOSING_LINK_RE.search(p.get("body") or "")))


# Repo-name → expected branch prefix. Defined inline per plan refinement note
# (no REPO_PREFIX_MAP exists in this module). Add repos as needed.
_REPO_PREFIX_MAP: dict[str, str] = {
    "guacamayo": "GUA",
    "galactus": "GAL",
    "librarian": "LIB",
    "atlas": "ATL",
    "listen-wiseer": "LIS",
    "ai-project-template": "AIT",
    "playground": "PLG",
    "lebanese-blonde": "LEB",
    "sisyphus": "SIS",
    "job-system": "JOB",
    "dssg": "DSG",
}

_BRANCH_PREFIX_RE = re.compile(r"^([A-Z]+)-\d+")


def _cross_repo_prefix_mismatch_branches(src: SignalSources) -> float | None:
    """Branches whose prefix (e.g. GUA-) does not match their repo."""
    if not src.branches:
        return None
    count = 0
    for branch in src.branches:
        name = branch.get("name") or ""
        repo = branch.get("repo") or ""
        m = _BRANCH_PREFIX_RE.match(name)
        if not m:
            continue  # unformatted branch (main, develop, etc.) — skip
        prefix = m.group(1)
        expected = _REPO_PREFIX_MAP.get(repo)
        if expected is not None and prefix != expected:
            count += 1
    return float(count)


def _stale_merged_branches(src: SignalSources) -> float | None:
    """Merged branches that still have a remote ref (not yet deleted)."""
    if not src.branches:
        return None
    # A branch in the table means its remote ref existed at last collection.
    # merged=1 means a PR for it was merged. Together: stale merged branch.
    return float(sum(1 for b in src.branches if b.get("merged") == 1))


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

_ENTRIES: list[Signal] = [
    # --- session facts (pre-existing, behaviour unchanged) ---
    Signal(
        "bash-antipatterns",
        REGISTERED,
        KIND_SESSION,
        _bash_antipatterns_p50,
        "Median (p50) bash antipattern count per session. This is NOT the mean — "
        "insights prose must say 'median', never 'average' (feedback-log 2026-08-20, C2).",
    ),
    Signal(
        "p90-output-tokens",
        REGISTERED,
        KIND_SESSION,
        _output_tokens_p90,
        "90th-percentile output tokens across sessions.",
    ),
    Signal(
        "execution-sessions-with-skills",
        REGISTERED,
        KIND_SESSION,
        _execution_skill_compliance_pct,
        "Percent of execution sessions that invoked at least one guardrail skill "
        "(workflow-execute/review, code-review/debug/refactor). Identity and meta "
        "skills are excluded (feedback-log 2026-08-20, C5).",
    ),
    Signal(
        "top-session-cost-concentration",
        REGISTERED,
        KIND_SESSION,
        _cost_over_150k_share_pct,
        "Share of total cost from sessions above 150k context.",
    ),
    Signal(
        "fable-tokens-in-non-verdict-skills",
        REGISTERED,
        KIND_SESSION,
        _fable_share_of_cost_pct,
        "Fable's share of total cost.",
    ),
    # --- Class A: store-backed, verified 2026-08-19 ---
    Signal(
        "file-not-found-errors",
        REGISTERED,
        KIND_SESSION,
        _file_not_found_errors,
        "Total file_not_found tool errors (192 of 1356 at registration).",
    ),
    Signal(
        "unique-hooks-in-pass-log",
        REGISTERED,
        KIND_HOOKLOG,
        _unique_hooks_in_pass_log,
        "Distinct hooks calling log_pass (2 at registration).",
    ),
    Signal(
        "co-authored-by-in-drafted-commits",
        REGISTERED,
        KIND_GIT,
        _co_authored_by_in_drafted_commits,
        "Commits carrying a Claude co-author trailer (14 at registration).",
    ),
    Signal(
        "silent-swallow-findings",
        REGISTERED,
        KIND_FINDINGS,
        _silent_swallow_findings,
        "Review findings naming silent/swallowed errors (88 at registration).",
    ),
    Signal(
        "worktree-commit-blocks",
        REGISTERED,
        KIND_HOOKLOG,
        _hook_blocks("risky_git_guard"),
        "risky_git_guard block events (exit 2).",
    ),
    Signal(
        "stop-hook-e2e-false-blocks",
        REGISTERED,
        KIND_HOOKLOG,
        _hook_blocks("task_complete_check"),
        "task_complete_check block events (exit 2).",
    ),
    # --- Class B: repo-file content ---
    Signal(
        "co-authored-by-rule-in-claude.md",
        REGISTERED,
        KIND_REPOFILE,
        _repofile_resolver(FileClaim("", "*/CLAUDE.md", r"Co-Authored-By")),
        "CLAUDE.md files stating the co-author rule.",
    ),
    Signal(
        "re-derive-clause-in-retro-step-0",
        REGISTERED,
        KIND_REPOFILE,
        _repofile_resolver(
            FileClaim("guacamayo", ".claude/skills/meta-retro/SKILL.md", r"re-derive")
        ),
        "meta-retro Step 0 carrying the re-derive clause.",
    ),
    Signal(
        "update-ref-coverage-in-risky_git_guard",
        REGISTERED,
        KIND_REPOFILE,
        _repofile_resolver(FileClaim("", ".claude/hooks/*.sh", r"update-ref")),
        "risky_git_guard covering update-ref.",
    ),
    Signal(
        "prose-gate-instructions-in-skills",
        REGISTERED,
        KIND_REPOFILE,
        _repofile_resolver(
            FileClaim("guacamayo", ".claude/skills/*/SKILL.md", r"gate|unskippable")
        ),
        "Skills still carrying prose gate instructions.",
    ),
    Signal(
        "daily-telemetry-capture-in-guacamayo",
        REGISTERED,
        KIND_REPOFILE,
        _repofile_resolver(FileClaim("guacamayo", "logs/telemetry-facts.log", r".")),
        "Presence of the daily telemetry capture log.",
    ),
    # --- registered by the 2026-08-19 backlog audit ---
    Signal(
        "duplicate-active-ledger-signals",
        REGISTERED,
        KIND_REPOFILE,
        _duplicate_ledger_signals,
        "Signals claimed by more than one active ledger row (0 after the audit).",
    ),
    Signal(
        "todowrite-in-heavy-sessions",
        REGISTERED,
        KIND_SESSION,
        _todowrite_in_heavy_sessions,
        "Heavy sessions (>100 tool calls) with no TodoWrite call. Heavy is pinned "
        "here at 100 so the metric resolves; it was unobservable only because the "
        "threshold lived per-hypothesis and was never stored.",
    ),
    Signal(
        "meta-feedback-run-age-days",
        REGISTERED,
        KIND_REPOFILE,
        _feedback_run_age_days,
        "Days since the last /meta-feedback run (None when never run — the gate is "
        "manual, so absence means unfired, never fresh).",
    ),
    # --- promoted from needs-collection in GUA-163 ---
    Signal(
        "merged-prs-without-closing-links",
        REGISTERED,
        KIND_GIT,
        _merged_prs_without_closing_links,
        "Merged PRs whose body carries no Closes #N or Fixes #N link.",
    ),
    Signal(
        "cross-repo-prefix-mismatch-branches",
        REGISTERED,
        KIND_GIT,
        _cross_repo_prefix_mismatch_branches,
        "Branches whose prefix (e.g. GUA-) does not match their repo.",
    ),
    Signal(
        "stale-merged-branches",
        REGISTERED,
        KIND_GIT,
        _stale_merged_branches,
        "Merged branches (PR merged) whose remote ref still exists.",
    ),
    Signal(
        "slug-derived-pr-titles",
        REGISTERED,
        KIND_GIT,
        _slug_derived_pr_titles,
        "Open PRs whose title looks derived from the branch slug (PREFIX-NUM WORD).",
    ),
    Signal(
        "unverified-agent-counts-in-promoted-issue-bodies",
        NEEDS_COLLECTION,
        None,
        None,
        "Promoted issue bodies citing unverified agent counts.",
        remedy="issues carries no `body` column; capture it in collect_issues().",
    ),
    Signal(
        "flat-sibling-issues-without-parent-link",
        NEEDS_COLLECTION,
        None,
        None,
        "Sub-issues filed without a parent link.",
        remedy="issues carries no parent/sub-issue relation; capture the GraphQL parent field.",
    ),
    Signal(
        "shipped-scheduler-dod-in-workflow-execute",
        REGISTERED,
        "presence",
        _repofile_resolver(
            FileClaim(
                "guacamayo", ".claude/skills/workflow-execute/SKILL.md", r"scheduler|launchctl"
            )
        ),
        "workflow-execute SKILL.md carrying the shipped-scheduler DoD clause.",
    ),
    Signal(
        "sweep-records-in-reviews-dir",
        REGISTERED,
        "presence",
        _repofile_resolver(FileClaim("guacamayo", ".claude/docs/reviews/*.md", r".")),
        "Review sweep records present in the reviews directory.",
    ),
]


# Class C -- structurally unobservable. Each carries the reason it cannot be seen,
# so /hypothesis can quote it back to an author proposing the same claim again.
_UNOBSERVABLE: dict[str, str] = {
    "land-verification-by-message-alone": "No record distinguishes verifying a landing "
    "by message from verifying it by inspection.",
    "variable-cd-misresolution": "Shell variable resolution is not captured in any log.",
    "design-skill-invoked": "Skill invocations are recorded per session, but this claim "
    "is about a design-heavy session judgement no field encodes.",
    "autocompact-non-firing-reports": "A non-firing autocompact leaves no event.",
    "merges-into-red-main": "CI state at merge time is not captured.",
    "model-claim-settings-mismatch": "Requires comparing prose claims against settings; "
    "no structured claim source exists.",
    "precommit-ci-lint-skew": "Requires paired local/CI lint runs; only one side is logged.",
    "ref-without-commit-push-events": "Ref-level push events are not collected.",
    "wrong-branch-ship-events": "No ship-event stream records the branch.",
    "sync-churn-from-unversioned-source": "Unversioned sources leave no diff history.",
    "lint-mirror-config-omission-incidents": "Config-mirror omissions are only found by "
    "manual diff; no incident stream.",
    "stale-verdict-cli-references": "Requires prose-vs-CLI cross-reference; no source.",
    "writes-to-sounding-dashboard.html": "File writes are not attributed per target path.",
    "writes-to-sounding-root-reports": "File writes are not attributed per target path.",
    "double-dated-report-filenames": "Report filenames are not collected.",
    "heredoc-prose-false-positives": "Hook false-positive judgements are not labelled.",
    "stop-hook-blocks-on-vendored-code": "Block events carry no vendored/authored label.",
    "update-ref-bypass-events": "Bypass events leave no trace by construction.",
    "insights-agent-spawn-protocol": "Protocol adherence is a prose property of the spawn.",
    "bash-stratified-taxonomy": "Taxonomy completeness is a judgement about a report.",
    "major-update-review-path": "No event marks a 'major update' review path.",
    "repo-rename-checklist": "Checklist completion is not recorded.",
    "perf-scale-findings": "Requires findings labelled by dimension provenance.",
    "static-analysis-section-in-review-reports": "Report sections are not indexed.",
    "otel-spans-in-new-projects": "New-project scaffolding is not inventoried.",
    "token-budget-utility-in-new-projects": "New-project scaffolding is not inventoried.",
    "verification-loop-in-new-projects": "New-project scaffolding is not inventoried.",
    "portfolio-avg-score": "Portfolio scores are hand-assessed, not collected.",
    "fable-token-premium-vs-quality-delta": "Requires a quality measure per phase; none exists.",
    "dispatches-ending-staged": "Dispatch outcomes are not recorded as events.",
    "unmatched-promotable-groups": "Requires recurrence-group match state across runs.",
    "parse-error-dimension-runs": "Dimension run parse errors are not persisted.",
    "falsely-claimed-applied-rows": "Requires re-deriving each ledger row's presence metric; not automated.",
    "hardcoded-not-configurable-findings": "Recurrence-group count; computed per retro, not per session.",
    "lint-findings-in-merged-findings": "Review finding categories are not indexed by session.",
    "vague-dimension-findings": "Review finding vagueness is not scored automatically.",
    "writes-to-sounding-dashboard": "File write targets are not tracked per session.",
}

_REGISTRY: dict[str, Signal] = {s.name: s for s in _ENTRIES}
for _name, _reason in _UNOBSERVABLE.items():
    _REGISTRY[_name] = Signal(
        _name,
        UNOBSERVABLE,
        None,
        None,
        "",
        remedy=f"{_reason} Rewrite the hypothesis into a countable form.",
    )


def normalize(name: str) -> str:
    """Normalise a ledger slug to a registry key (see verdicts._normalize_signal)."""
    return name.strip().strip("`").strip().lower()


def lookup(name: str) -> Signal | None:
    """Return the Signal for `name`, or None when unregistered."""
    return _REGISTRY.get(normalize(name))


def state_of(name: str) -> str:
    """Return the registry state for `name` (UNREGISTERED when absent)."""
    sig = lookup(name)
    return sig.state if sig else UNREGISTERED


def is_scorable(name: str) -> bool:
    """True when `name` has a resolver that can produce a value."""
    sig = lookup(name)
    return bool(sig and sig.state == REGISTERED and sig.resolver)


def resolve(name: str, sources: SignalSources) -> float | None:
    """Measure `name` against `sources`; None when unresolvable or no data."""
    sig = lookup(name)
    if sig is None or sig.resolver is None:
        return None
    return sig.resolver(sources)


def all_signals() -> list[Signal]:
    """Every declared signal, sorted by name -- the authoring surface."""
    return sorted(_REGISTRY.values(), key=lambda s: s.name)


def registered_names() -> list[str]:
    """Names with a working resolver."""
    return sorted(s.name for s in _REGISTRY.values() if s.state == REGISTERED and s.resolver)
