"""GUA-92 regression guard: pulse.sh is retired and must stay retired.

pulse.sh targeted a dashboard section that no longer exists, silently
discarding its output. The retirement decision (issue #92) removes the
script and every live caller; these tests fail if either comes back.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PULSE = re.compile(r"\bpulse\b", re.IGNORECASE)


def test_pulse_script_deleted():
    assert not (REPO / "scripts" / "pulse.sh").exists()


def test_no_pulse_references_in_callers():
    for rel in ("Makefile", ".claude/skills/grow/SKILL.md"):
        text = (REPO / rel).read_text()
        matches = [ln for ln in text.splitlines() if PULSE.search(ln)]
        assert not matches, f"{rel} still references pulse: {matches}"
