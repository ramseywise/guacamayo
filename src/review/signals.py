"""Deterministic signal detection for dimension dispatch.

Regex-based scanner that determines which conditional scan dimensions should
be activated for a given set of files. No LLM calls — pure pattern matching.

Signals:
- is_agent_code: imports from LLM/agent frameworks, or lives in agents/**
- is_pipeline_code: sql files, core/pipelines/**, embedded query strings
- is_ml_code: imports from tabular-ML frameworks, or lives in models/**
- has_sanyi_contracts: SANYI.md exists in the repo root or a parent dir
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# Import patterns indicating LLM/agent framework usage
_AGENT_IMPORT_PATTERNS = [
    re.compile(r"from\s+anthropic\b"),
    re.compile(r"import\s+anthropic\b"),
    re.compile(r"from\s+openai\b"),
    re.compile(r"import\s+openai\b"),
    re.compile(r"from\s+langchain\b"),
    re.compile(r"import\s+langchain\b"),
    re.compile(r"from\s+langgraph\b"),
    re.compile(r"import\s+langgraph\b"),
    re.compile(r"from\s+google\.adk\b"),
    re.compile(r"import\s+google\.adk\b"),
    re.compile(r"from\s+claude_agent_sdk\b"),
    re.compile(r"import\s+claude_agent_sdk\b"),
    re.compile(r"from\s+anthropic\.types\b"),
]

# Path patterns indicating agent code location
_AGENT_PATH_PATTERNS = [
    re.compile(r"(?:^|/)agents/"),
    re.compile(r"(?:^|/)\w+_agent/"),
    re.compile(r"(?:^|/)prompts/"),
]

# Pipeline / SQL path patterns
_PIPELINE_PATH_PATTERNS = [
    re.compile(r"(?:^|/)core/pipelines/"),
    re.compile(r"\.sql$"),
]

# SQL smell patterns in file content
_SQL_CONTENT_PATTERNS = [
    re.compile(r"SELECT\s+\*\s+FROM", re.IGNORECASE),
    re.compile(r"(?:execute|cursor\.execute)\s*\(", re.IGNORECASE),
]

# Import patterns indicating tabular-ML usage (gates the leakage dimension).
# Deliberately excludes LLM frameworks — leakage is about train/test contamination
# in supervised learning, not about generative models.
_ML_IMPORT_PATTERNS = [
    re.compile(r"from\s+sklearn\b"),
    re.compile(r"import\s+sklearn\b"),
    re.compile(r"from\s+xgboost\b"),
    re.compile(r"import\s+xgboost\b"),
    re.compile(r"from\s+lightgbm\b"),
    re.compile(r"import\s+lightgbm\b"),
    re.compile(r"from\s+catboost\b"),
    re.compile(r"import\s+catboost\b"),
    re.compile(r"from\s+statsmodels\b"),
    re.compile(r"import\s+statsmodels\b"),
    re.compile(r"\btrain_test_split\b"),
    re.compile(r"\bcross_val_score\b"),
    re.compile(r"\bStandardScaler\b"),
]

# Path patterns indicating ML code location
_ML_PATH_PATTERNS = [
    re.compile(r"(?:^|/)models/"),
    re.compile(r"(?:^|/)features/"),
    re.compile(r"(?:^|/)training/"),
]


def _file_has_pattern(path: Path, patterns: list[re.Pattern]) -> bool:
    try:
        content = path.read_text(errors="replace")
        return any(p.search(content) for p in patterns)
    except OSError:
        return False


def detect_signals(files: list[str], repo_root: str = ".") -> dict[str, bool]:
    """Detect which conditional dimensions should activate for the given file list.

    Args:
        files: List of file paths (relative or absolute) to inspect.
        repo_root: Root directory for SANYI.md search.

    Returns:
        Dict with boolean signal values:
        - is_agent_code: activate runtime + safeguards dimensions
        - is_pipeline_code: activate data-correctness checks in architecture
        - is_ml_code: activate leakage dimension
        - has_sanyi_contracts: SANYI.md present (activate contracts dimension)
    """
    is_agent_code = False
    is_pipeline_code = False
    is_ml_code = False

    for raw_path in files:
        path_str = raw_path.replace("\\", "/")

        # Path-based agent detection
        if any(p.search(path_str) for p in _AGENT_PATH_PATTERNS):
            is_agent_code = True

        # Path-based pipeline detection
        if any(p.search(path_str) for p in _PIPELINE_PATH_PATTERNS):
            is_pipeline_code = True

        # Path-based ML detection
        if any(p.search(path_str) for p in _ML_PATH_PATTERNS):
            is_ml_code = True

        # Content-based agent import detection (only for Python/TS files)
        if not is_agent_code and path_str.endswith((".py", ".ts", ".tsx", ".js")):
            p = Path(path_str)
            if not p.is_absolute():
                p = Path(repo_root) / p
            if _file_has_pattern(p, _AGENT_IMPORT_PATTERNS):
                is_agent_code = True

        # Content-based SQL detection for non-.sql files
        if not is_pipeline_code and path_str.endswith(".py"):
            p = Path(path_str)
            if not p.is_absolute():
                p = Path(repo_root) / p
            if _file_has_pattern(p, _SQL_CONTENT_PATTERNS):
                is_pipeline_code = True

        # Content-based ML detection
        if not is_ml_code and path_str.endswith((".py", ".ipynb")):
            p = Path(path_str)
            if not p.is_absolute():
                p = Path(repo_root) / p
            if _file_has_pattern(p, _ML_IMPORT_PATTERNS):
                is_ml_code = True

    # SANYI contracts: check for SANYI.md in repo root
    has_sanyi = _find_sanyi_md(repo_root)

    return {
        "is_agent_code": is_agent_code,
        "is_pipeline_code": is_pipeline_code,
        "is_ml_code": is_ml_code,
        "has_sanyi_contracts": has_sanyi,
    }


def _find_sanyi_md(repo_root: str) -> bool:
    root = Path(repo_root).resolve()
    # Check repo root and one level up
    for candidate in [root / "SANYI.md", root / ".claude" / "SANYI.md"]:
        if candidate.exists():
            return True
    # Also check via git ls-files for committed SANYI.md
    try:
        result = subprocess.run(
            ["git", "ls-files", "SANYI.md", ".claude/SANYI.md"],
            capture_output=True,
            text=True,
            cwd=repo_root,
            check=False,
        )
        return bool(result.stdout.strip())
    except OSError:
        return False


# Dimensions dispatched on every run, in report order.
ALWAYS_ON_DIMENSIONS = [
    "correctness",
    "intent",
    "architecture",
    "safety",
    "testing",
    "silent-failure",
    "performance",
    "wander",
]

# Conditional dimensions → the signal key that activates each.
CONDITIONAL_DIMENSIONS: dict[str, str] = {
    "runtime": "is_agent_code",
    "safeguards": "is_agent_code",
    "leakage": "is_ml_code",
    "contracts": "has_sanyi_contracts",
}


def active_dimensions(signals: dict[str, bool]) -> list[str]:
    """Return the list of dimension names that should be dispatched.

    Always-on: correctness, intent, architecture, safety, testing,
    silent-failure, performance, wander
    Conditional: runtime + safeguards (is_agent_code), leakage (is_ml_code),
    contracts (has_sanyi_contracts)
    """
    dims = list(ALWAYS_ON_DIMENSIONS)
    dims.extend(
        dimension
        for dimension, signal_key in CONDITIONAL_DIMENSIONS.items()
        if signals.get(signal_key)
    )
    return dims
