import datetime
import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from review import commit_verification, validation
from review.deduplication import find_duplicate_clusters
from review.fingerprint import (
    finding_to_sweep_finding,
    latest_sweep_path,
    load_sweep,
    save_sweep,
)
from review.render import render_report
from review.schemas.models import ReviewFinding, SweepRecord
from review.signals import active_dimensions, detect_signals
from review.trends import build_trend_report, render_trend_report


@click.group()
@click.version_option(package_name="review-cli")
def main():
    pass


@main.command("validate-finding")
@click.argument("input", type=click.File("r"), default="-")
def validate_finding_cmd(input):
    data = json.load(input)
    ok, err = validation.validate_finding(data)
    if not ok:
        click.echo(err, err=True)
        sys.exit(1)
    click.echo("valid")


@main.command()
@click.argument("input", type=click.File("r"), default="-")
def dedup(input):
    data = json.load(input)
    findings = [ReviewFinding.model_validate(f) for f in data]
    clusters = find_duplicate_clusters(findings)
    result = [[f.id for f in cluster] for cluster in clusters]
    click.echo(json.dumps(result, indent=2))


@main.command("validate-report")
@click.argument("input", type=click.File("r"), default="-")
def validate_report_cmd(input):
    data = json.load(input)
    ok, err = validation.validate_report(data)
    if not ok:
        click.echo(err, err=True)
        sys.exit(1)
    click.echo("valid")


@main.command("verify-commits")
@click.argument("plan_file", type=click.Path(exists=True))
@click.option("--repo", default=".", help="Git repo path")
@click.option("--branch", default=None, help="Branch to check (default: current)")
def verify_commits_cmd(plan_file, repo, branch):
    plan_text = Path(plan_file).read_text()
    results = commit_verification.verify_commits(plan_text, repo, branch)
    output = [asdict(r) for r in results]
    click.echo(json.dumps(output, indent=2))
    if any(r.status != "verified" for r in results):
        sys.exit(1)


@main.command("render-report")
@click.argument("input", type=click.File("r"), default="-")
def render_report_cmd(input):
    """Read merged findings + metadata (JSON) and output deterministic Markdown report."""
    data = json.load(input)
    md = render_report(data)
    click.echo(md)


@main.command("fingerprint")
@click.argument("input", type=click.File("r"), default="-")
@click.option("--repo", default=".", help="Repo identifier (used in sweep filenames)")
@click.option(
    "--sweep-date",
    default=None,
    help="ISO date for the sweep (YYYY-MM-DD). Defaults to today.",
)
@click.option(
    "--reviews-dir",
    default=".claude/docs/reviews",
    show_default=True,
    help="Directory where sweep JSON files are stored.",
)
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Persist the sweep record to --reviews-dir.",
)
def fingerprint_cmd(input, repo, sweep_date, reviews_dir, save):
    """Generate fingerprints for current findings and optionally save as a sweep record.

    Reads a JSON list of ReviewFinding objects from INPUT (or stdin).
    Outputs a JSON sweep record with fingerprinted findings.

    Example:
        cat findings.json | uv run review-cli fingerprint --repo guacamayo --save
    """
    data = json.load(input)
    if not isinstance(data, list):
        click.echo("error: input must be a JSON list of findings", err=True)
        sys.exit(1)

    findings = [ReviewFinding.model_validate(f) for f in data]
    sweep_findings = [finding_to_sweep_finding(f) for f in findings]

    date_str = sweep_date or datetime.datetime.now(tz=datetime.UTC).date().isoformat()
    record = SweepRecord(repo=repo, sweep_date=date_str, findings=sweep_findings)

    if save:
        rdir = Path(reviews_dir)
        base = rdir / f"{repo}-{date_str}.json"
        target = base
        counter = 1
        while target.exists():
            target = rdir / f"{repo}-{date_str}-{counter}.json"
            counter += 1
        save_sweep(record, target)
        click.echo(f"Saved sweep to {target}", err=True)

    click.echo(record.model_dump_json(indent=2))


@main.command("trends")
@click.option("--repo", required=True, help="Repo identifier to report on.")
@click.option(
    "--reviews-dir",
    default=".claude/docs/reviews",
    show_default=True,
    help="Directory where sweep JSON files are stored.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--previous",
    "previous_path",
    default=None,
    type=click.Path(),
    help="Path to previous sweep JSON (auto-detected from --reviews-dir if omitted).",
)
@click.option(
    "--current",
    "current_path",
    default=None,
    type=click.Path(),
    help="Path to current sweep JSON.",
)
def trends_cmd(repo, reviews_dir, output_format, previous_path, current_path):
    """Show a trend diff between two consecutive sweeps.

    Compares the previous sweep (auto-detected or --previous) against the current
    sweep (--current or most recent file). Outputs new/resolved/recurring findings
    and per-dimension trend directions.

    Example:
        uv run review-cli trends --repo guacamayo --format markdown
        uv run review-cli trends --repo guacamayo --previous old.json --current new.json
    """
    rdir = Path(reviews_dir)

    if current_path:
        current = load_sweep(Path(current_path))
        if current is None:
            click.echo(f"error: current sweep file not found: {current_path}", err=True)
            sys.exit(1)
    else:
        current_file = latest_sweep_path(rdir, repo)
        if current_file is None:
            click.echo(f"error: no sweep files found for repo {repo!r} in {rdir}", err=True)
            sys.exit(1)
        current = load_sweep(current_file)

    if previous_path:
        previous = load_sweep(Path(previous_path))
        if previous is None:
            click.echo(f"error: previous sweep file not found: {previous_path}", err=True)
            sys.exit(1)
    else:
        candidates = sorted(rdir.glob(f"{repo}-*.json"), key=lambda p: p.stat().st_mtime)
        if len(candidates) < 2:
            click.echo(
                f"error: need at least 2 sweep files for repo {repo!r} to compute a diff. "
                "Run `review-cli fingerprint --save` after each sweep.",
                err=True,
            )
            sys.exit(1)
        previous = load_sweep(candidates[-2])

    report = build_trend_report(previous, current)

    if output_format == "json":
        click.echo(report.model_dump_json(indent=2))
    else:
        click.echo(render_trend_report(report))


@main.command("detect-signals")
@click.option("--repo", default=".", help="Git repo root path")
@click.argument("files", nargs=-1)
def detect_signals_cmd(repo, files):
    """Detect which scan dimensions should activate for the given files.

    Reads a JSON list of file paths from stdin (if no FILES args given),
    or uses the FILES arguments directly. Outputs JSON with signal booleans
    and the list of active dimensions.

    Example:
        echo '["agents/foo.py", "src/bar.py"]' | uv run review-cli detect-signals
        uv run review-cli detect-signals agents/foo.py src/bar.py
    """
    if files:
        file_list = list(files)
    else:
        file_list = json.load(click.get_text_stream("stdin"))

    signals = detect_signals(file_list, repo_root=repo)
    dims = active_dimensions(signals)
    click.echo(json.dumps({"signals": signals, "active_dimensions": dims}, indent=2))
