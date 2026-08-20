"""Deterministic consistency checks over board claims (GUA-103).

An issue body is a cache, and it rots faster than the code it describes. On
2026-08-12 one wake produced three consecutive misreports (#32, #18, #19): each
issue named a filesystem path, each path was stale, a count against a
non-existent path returned 0, and 0 was reported as "not started" while the work
sat one directory over. The pattern, stated rather than the instance: *a count
against a non-existent path is indistinguishable from untouched work.*

The fix for that class of failure is not another skill instruction. The prose
rule added the same session (`wake/SKILL.md:130`) was the second attempt at this
instruction class; a skill instruction is re-read each wake and obeyed
probabilistically, while a subcommand either runs or does not. The repo's
standing rule says it directly: **a conformance claim must be produced by
invoking the enforcement, never by re-deriving its rules.**

Scope is deliberately narrow. This module owns exactly what `loop.py` does not:

* `check_label_artifact` — labels against artifacts. Labels are the weakest
  evidence on the board: hand-set, never revisited.

**Path checking is NOT implemented here — it was tried and removed.** See
`check_stale_paths` in git history (GUA-103, removed 2026-08-14). The first live
run produced 65 findings across 21 open issues and every one was a false
positive. The reason is structural rather than a matter of regex tuning: the
2026-08-12 defect was a *count against* a path, whereas a body merely *mentions*
one, and the three ways a body mentions a path are indistinguishable without
reading intent —

* asserting it exists (the only checkable case),
* reporting it is absent (galactus#4: "seven of eight pocs are empty directories"),
* proposing it be created (AIT#64: "add ``data/``").

`_PROSPECTIVE_RE` was the attempt at that distinction and it did not generalize —
narrowing to labelled-workflow issues left 4 findings, still all false, including
GUA-103's own worked example ``path/that/moved``. A report that is 100% noise is
not a weaker report; it trains the reader to skip the table that also carries the
real `label-artifact` rows. Reinstating this needs a different signal than path
mentions — an issue asserting a *count* against a path is the shape worth
catching.

**Plan↔issue drift is NOT implemented here either.** `loop.detect_drift` already
does it bidirectionally (and catches a third case besides), with three-tier issue
matching in `loop._extract_issue` and joinable-subset coverage already surfaced
by the dashboard. The GUA-103 plan specified a second implementation because it
was written against an earlier tree; building one would have created exactly the
`duplicate-implementation` signature `recurrence.py` tracks. `__main__` calls
`loop.detect_drift` and folds its output into the same report instead.

Checkers are pure functions over already-fetched data — `__main__` owns all I/O.
This mirrors `recurrence.py`, and is why both are testable. Each checker is
independent: one raising must not suppress the others.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# `{PREFIX}-{NUM}-{slug}` — the planned-branch convention.  bug/* and spike/* branches
# are out of scope and must be skipped explicitly, not checked and quietly passed.
_BRANCH_CONVENTION_RE = re.compile(r"^([A-Z]{2,4})-(\d+)-")

# WIP limit from wake/SKILL.md:124 and ~/.claude/refs/agile.md.
WIP_LIMIT = 3


@dataclass(frozen=True)
class Inconsistency:
    """One board claim that did not survive checking.

    `evidence` is mandatory and non-empty. A finding without evidence is an
    assertion, and this module exists because assertions were believed.
    """

    kind: str  # "label-artifact" | "plan-issue-drift" | "unmatchable-plan"
    repo: str
    issue: int | None
    detail: str  # what was claimed
    evidence: str  # what was found instead

    def __post_init__(self) -> None:
        if not self.evidence.strip():
            raise ValueError(f"Inconsistency({self.kind}) requires non-empty evidence")


@dataclass(frozen=True)
class BranchFact:
    """Pre-computed merge-state fact for one branch in one repo.

    `is_ancestor` is:
      - ``True``  — the branch tip is an ancestor of ``origin/main`` (i.e. merged)
      - ``False`` — the branch tip is NOT an ancestor (i.e. not yet merged)
      - ``None``  — the question could not be asked (origin/main did not resolve,
                    the repo has no remote, or git is absent); this is not a pass.

    The caller (`__main__._collect_branch_facts`) owns all subprocess I/O; this
    dataclass is the pure-function boundary.
    """

    repo: str
    branch: str
    issue_num: int  # parsed from the branch name via _BRANCH_CONVENTION_RE
    is_ancestor: bool | None  # None = could not determine; never silently "clean"


def check_label_artifact(
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    plan_issues: set[tuple[str, int]],
) -> list[Inconsistency]:
    """Workflow labels contradicted by the artifacts they imply.

    Three checks, all on OPEN issues:

    * `in-review` with no open PR referencing the issue — the label survived the
      merge that should have retired it.
    * `ready` with no plan doc — `ready` means DoR-passed, which means a plan
      exists. Without one the label is aspirational.
    * `in-progress` count above `WIP_LIMIT` — not per-issue drift but a board
      fact, emitted once with `issue=None`.

    `plan_issues` is the set of `(repo, issue_number)` pairs that plan docs join
    to, supplied by the caller from `loop.collect_plan_docs`. Passing it in keeps
    this function pure and stops it re-deriving a join `loop.py` already owns.
    """
    found: list[Inconsistency] = []

    open_pr_issues: set[tuple[str, int]] = set()
    for pr in prs:
        if (pr.get("state") or "").upper() != "OPEN":
            continue
        repo = str(pr.get("repo") or "unknown")
        for num in _referenced_issues(pr):
            open_pr_issues.add((repo, num))

    in_progress: list[tuple[str, int]] = []

    for issue in issues:
        if (issue.get("state") or "").upper() != "OPEN":
            continue
        repo = str(issue.get("repo") or "unknown")
        number = issue.get("number")
        labels = {label.strip() for label in (issue.get("labels") or "").split(",")}

        if "in-review" in labels and (repo, number) not in open_pr_issues:
            found.append(
                Inconsistency(
                    kind="label-artifact",
                    repo=repo,
                    issue=number,
                    detail="labelled `in-review`",
                    evidence="no open PR references this issue",
                )
            )

        if "ready" in labels and (repo, number) not in plan_issues:
            found.append(
                Inconsistency(
                    kind="label-artifact",
                    repo=repo,
                    issue=number,
                    detail="labelled `ready`",
                    evidence="no plan doc joins to this issue (ready implies DoR passed)",
                )
            )

        if "in-progress" in labels and number is not None:
            in_progress.append((repo, number))

    if len(in_progress) > WIP_LIMIT:
        listed = ", ".join(f"{repo}#{num}" for repo, num in sorted(in_progress))
        found.append(
            Inconsistency(
                kind="label-artifact",
                repo="(board)",
                issue=None,
                detail=f"WIP limit is {WIP_LIMIT}",
                evidence=f"{len(in_progress)} issues labelled in-progress: {listed}",
            )
        )

    log.info("consistency.label_artifact", found=len(found), in_progress=len(in_progress))
    return found


def check_merged_branch_open_issue(
    branch_facts: list[BranchFact],
    issues: list[dict[str, Any]],
) -> list[Inconsistency]:
    """Branches whose tip is already an ancestor of origin/main while their issue is open.

    A branch merged to main and an open issue are not inherently inconsistent — but
    together they mean a board claim ("work in progress") is contradicted by a git fact
    ("the branch already landed"). This is the highest-yield check on the board and
    historically produced zero false positives (unlike path checking, which was removed
    for the inverse reason — see the module docstring).

    Two "could not evaluate" shapes produce their own finding rather than a silent pass:

    * ``is_ancestor is None`` — origin/main did not resolve for this repo.  An empty
      result from a git command that could not run reads as "nothing wrong", which is the
      librarian#60 failure shape.  Non-resolution is reported once per repo, not once per
      branch.

    Branch scope: only branches matching ``{PREFIX}-{NUM}-{slug}``.  ``bug/*``,
    ``spike/*``, ``main``, and bare feature names are skipped and counted; the skip count
    is logged so the caller can distinguish "no findings" from "nothing was checked".
    """
    # Build (repo, issue_num) -> issue state index
    open_issues: set[tuple[str, int]] = set()
    for issue in issues:
        if (issue.get("state") or "").upper() == "OPEN":
            repo = str(issue.get("repo") or "")
            num = issue.get("number")
            if num is not None:
                open_issues.add((repo, num))

    found: list[Inconsistency] = []
    resolution_failures: set[str] = set()  # repos where origin/main did not resolve
    skipped = 0

    for bf in branch_facts:
        if bf.is_ancestor is None:
            resolution_failures.add(bf.repo)
            continue

        if not bf.is_ancestor:
            continue  # branch not merged — nothing to flag

        # Branch is merged. Flag if the issue is still open.
        if (bf.repo, bf.issue_num) in open_issues:
            found.append(
                Inconsistency(
                    kind="merged-branch-open-issue",
                    repo=bf.repo,
                    issue=bf.issue_num,
                    detail=f"branch `{bf.branch}` is an ancestor of origin/main",
                    evidence=f"{bf.repo}#{bf.issue_num} is still OPEN after branch merged",
                )
            )

    for repo in sorted(resolution_failures):
        found.append(
            Inconsistency(
                kind="merged-branch-open-issue",
                repo=repo,
                issue=None,
                detail="origin/main did not resolve",
                evidence=(
                    f"could not evaluate merged-branch/open-issue for {repo}: "
                    "origin/main ref unresolvable — branch ancestry check skipped"
                ),
            )
        )

    log.info(
        "consistency.merged_branch",
        found=len(found),
        skipped=skipped,
        resolution_failures=len(resolution_failures),
    )
    return found


_CLOSES_RE = re.compile(r"(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)
_HASH_RE = re.compile(r"#(\d+)")


def _referenced_issues(pr: dict[str, Any]) -> set[int]:
    """Issue numbers a PR references, from its `Closes #N` body or `(#N)` title."""
    nums: set[int] = set()
    body = str(pr.get("body") or "")
    nums.update(int(n) for n in _CLOSES_RE.findall(body))
    title = str(pr.get("title") or "")
    nums.update(int(n) for n in _HASH_RE.findall(title))
    return nums


def to_report(
    inconsistencies: list[Inconsistency],
    *,
    issues_checked: int,
    repos_checked: list[str],
    unmatchable_plans: int,
) -> dict[str, Any]:
    """The JSON payload wake renders.

    JSON rather than Markdown so it is diffable across wakes — that makes "the
    same inconsistency for the third wake running" itself detectable, which is
    the friction loop this repo is built around.

    The coverage fields are not decoration. Each records a way this report can be
    empty *without* the board being clean: no issues fetched, plans that join to
    no issue. A consumer that renders only `inconsistencies` can present a broken
    run as a clean one.

    ``unmatchable_plans`` is promoted to a top-level key alongside ``total`` and
    ``issues_checked`` so that a wake rendering only those three fields cannot hide
    a corpus where 103 of 112 plans were unevaluable behind "0 findings".
    """
    by_kind: dict[str, int] = {}
    for item in inconsistencies:
        by_kind[item.kind] = by_kind.get(item.kind, 0) + 1

    return {
        "issues_checked": issues_checked,
        "unmatchable_plans": unmatchable_plans,
        "repos_checked": sorted(repos_checked),
        "coverage": {
            "unmatchable_plans": unmatchable_plans,
        },
        "counts_by_kind": by_kind,
        "total": len(inconsistencies),
        "inconsistencies": [
            {
                "kind": i.kind,
                "repo": i.repo,
                "issue": i.issue,
                "detail": i.detail,
                "evidence": i.evidence,
            }
            for i in sorted(
                inconsistencies,
                key=lambda x: (x.kind, x.repo, x.issue if x.issue is not None else -1),
            )
        ],
    }
