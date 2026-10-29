"""Default paths must resolve to the repo root, not to `src/`.

When the package moved under `src/` (0f9bd64), every `Path(__file__).parents[1]` that
meant "repo root" silently became `src/`. Nothing failed: the board wrote board.json and
proposal sightings into a git-ignored `src/.sounding/`, facts skipped verdicts ("ledger
not found") and dashboard injection ("dashboard not found") — all at exit 0, for ten
weeks. Every one of those is a soft skip, so only a direct check catches the next move.
"""

from __future__ import annotations

import re
from pathlib import Path

from telemetry import actions, sightings

REPO_ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_SRC = REPO_ROOT / "src" / "telemetry"
_PARENTS = re.compile(r"Path\(__file__\)\.resolve\(\)\.parents\[(\d+)\]")


def test_repo_root_anchor_is_the_repo() -> None:
    """Guards this file's own assumption before the others rely on it."""
    assert (REPO_ROOT / "pyproject.toml").is_file()


def test_module_defaults_live_under_repo_sounding() -> None:
    sounding = REPO_ROOT / ".sounding" / "telemetry"
    assert actions._DEFAULT_ACTIONS_LOG.parent == sounding
    assert sightings._DEFAULT_SIGHTINGS_PATH.parent == sounding


def test_every_file_anchor_in_telemetry_resolves_to_repo_root() -> None:
    """Covers the argparse defaults in __main__ too, which are built inside functions
    and so cannot be imported as constants."""
    hits = []
    for path in sorted(TELEMETRY_SRC.glob("*.py")):
        for match in _PARENTS.finditer(path.read_text()):
            resolved = path.resolve().parents[int(match.group(1))]
            hits.append((path.name, resolved))
    assert hits, "no __file__ anchors found — the pattern no longer matches the source"
    wrong = [(name, str(p)) for name, p in hits if p != REPO_ROOT]
    assert not wrong, f"anchors not at repo root: {wrong}"
