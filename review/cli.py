import json
import sys
from dataclasses import asdict
from pathlib import Path

import click

from review import commit_verification, validation
from review.deduplication import find_duplicate_clusters
from review.schemas.models import ReviewFinding


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
