"""Static analysis (Layer 1) — deterministic lint detection and invocation.

Detects the first configured linter in TOOL_TABLE, invokes it in check mode only
(never --fix, never --write), and returns a StaticAnalysisResult.

Non-negotiable rules (enforced by tests):
- The command list is a literal constant per tool — never string-interpolated,
  never shell=True, always subprocess.run(list, shell=False).
- '--fix', '--write', 'format', '--unsafe-fixes' are forbidden tokens in any command.
- File args are passed after '--' so filenames cannot be interpreted as flags.
- Timeout 120 s; TimeoutExpired → status="failed".
- >200 changed files → drop path args, record scoped=False.
- Never raises; every failure path becomes a status on the result.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from review.schemas.models import StaticAnalysisResult

# ---------------------------------------------------------------------------
# Tool table
# ---------------------------------------------------------------------------

# Tokens that must never appear in any check_argv entry.
_FORBIDDEN_TOKENS = frozenset(["--fix", "--write", "format", "--unsafe-fixes"])

# File-extension sets: tools only understand certain file types.
_PY_EXTS = frozenset([".py", ".pyi"])
_JS_EXTS = frozenset([".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"])
_GO_EXTS = frozenset([".go"])

_SCOPE_LIMIT = 200  # files above this → drop path args


@dataclass(frozen=True)
class _ToolSpec:
    name: str
    # Relative marker paths to check for existence (any match → detected)
    marker_paths: tuple[str, ...]
    # Content marker: (file_relative_path, substring) — checked only if file exists
    content_marker: tuple[str, str] | None
    # Command argv for check-only invocation (file args appended after "--" when scoped)
    check_argv: tuple[str, ...]
    # File extensions this tool handles; None = no filtering
    extensions: frozenset[str] | None
    # Whether this tool supports per-file path arguments
    supports_file_args: bool


TOOL_TABLE: tuple[_ToolSpec, ...] = (
    _ToolSpec(
        name="ruff",
        marker_paths=("ruff.toml", ".ruff.toml"),
        content_marker=("pyproject.toml", "[tool.ruff]"),
        check_argv=("ruff", "check", "--output-format=json"),
        extensions=_PY_EXTS,
        supports_file_args=True,
    ),
    _ToolSpec(
        name="biome",
        marker_paths=("biome.json", "biome.jsonc"),
        content_marker=None,
        check_argv=("biome", "lint", "--reporter=json"),
        extensions=_JS_EXTS,
        supports_file_args=True,
    ),
    _ToolSpec(
        name="eslint",
        marker_paths=(
            ".eslintrc",
            ".eslintrc.js",
            ".eslintrc.cjs",
            ".eslintrc.yaml",
            ".eslintrc.yml",
            ".eslintrc.json",
            "eslint.config.js",
            "eslint.config.mjs",
            "eslint.config.cjs",
            "eslint.config.ts",
        ),
        content_marker=None,
        check_argv=("eslint", "--format=json"),
        extensions=_JS_EXTS,
        supports_file_args=True,
    ),
    _ToolSpec(
        name="golangci-lint",
        marker_paths=(".golangci.yml", ".golangci.yaml"),
        content_marker=None,
        check_argv=("golangci-lint", "run", "--out-format=json"),
        extensions=_GO_EXTS,
        supports_file_args=False,
    ),
    _ToolSpec(
        name="flake8",
        marker_paths=(".flake8",),
        content_marker=("setup.cfg", "[flake8]"),
        check_argv=("flake8", "--format=json"),
        extensions=_PY_EXTS,
        supports_file_args=True,
    ),
)

# Sanity check at import time: no forbidden tokens in any command
for _spec in TOOL_TABLE:
    for _token in _spec.check_argv:
        if _token in _FORBIDDEN_TOKENS:
            raise RuntimeError(
                f"TOOL_TABLE violation: {_spec.name!r} check_argv contains forbidden token {_token!r}"
            )


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_tool(repo: Path) -> _ToolSpec | None:
    """Return the first matching tool in TOOL_TABLE, or None if none detected."""
    for spec in TOOL_TABLE:
        # Check marker files
        for marker in spec.marker_paths:
            if (repo / marker).exists():
                return spec
        # Check content marker
        if spec.content_marker is not None:
            cfile, substr = spec.content_marker
            cpath = repo / cfile
            if cpath.exists():
                try:
                    if substr in cpath.read_text():
                        return spec
                except OSError:
                    pass
    return None


# ---------------------------------------------------------------------------
# Invocation
# ---------------------------------------------------------------------------


def _count_violations(raw_output: str, tool_name: str) -> int:
    """Parse violation count from JSON output where available; fall back to line count."""
    if not raw_output.strip():
        return 0
    try:
        data = json.loads(raw_output)
        if tool_name == "ruff":
            # ruff --output-format=json → list of violation objects
            if isinstance(data, list):
                return len(data)
        elif tool_name in ("biome", "eslint"):
            # eslint → list of file result objects, each with messages[]
            if isinstance(data, list):
                total = 0
                for file_result in data:
                    msgs = file_result.get("messages") or []
                    total += len(msgs)
                return total
        elif tool_name == "golangci-lint" and isinstance(data, dict):
            # golangci-lint → {"Issues": [...]}
            issues = data.get("Issues") or []
            return len(issues)
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    # Fallback: count non-empty lines
    return sum(1 for line in raw_output.splitlines() if line.strip())


def run_static_analysis(repo: Path, files: list[str]) -> StaticAnalysisResult:
    """Detect the first configured linter and invoke it in check mode.

    Args:
        repo: Absolute path to the repository root.
        files: Changed file paths (relative to repo root) from scope detection.

    Returns:
        StaticAnalysisResult — never raises.
    """
    spec = detect_tool(repo)

    if spec is None:
        return StaticAnalysisResult(
            tool=None,
            status="not_detected",
        )

    # Build command
    argv = list(spec.check_argv)
    scoped = False

    if spec.supports_file_args and files:
        # Filter to files this tool handles
        if spec.extensions is not None:
            relevant = [f for f in files if Path(f).suffix in spec.extensions]
        else:
            relevant = list(files)

        if relevant:
            if len(relevant) > _SCOPE_LIMIT:
                scoped = False
                # Drop path args — let the tool use its config scope
            else:
                scoped = True
                argv += ["--"] + relevant
        else:
            # No relevant files → trivially OK, scoped
            return StaticAnalysisResult(
                tool=spec.name,
                status="ok",
                command=list(spec.check_argv),
                exit_code=0,
                violation_count=0,
                raw_output="",
                scoped=True,
                detail="No files matching tool extensions in changed set.",
            )
    else:
        scoped = not spec.supports_file_args  # package-scoped tools like golangci-lint

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            cwd=str(repo),
            shell=False,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        return StaticAnalysisResult(
            tool=spec.name,
            status="tool_unavailable",
            command=argv,
            detail=f"{spec.check_argv[0]!r} not found — tool configured but not installed.",
        )
    except subprocess.TimeoutExpired:
        return StaticAnalysisResult(
            tool=spec.name,
            status="failed",
            command=argv,
            detail="Static analysis timed out after 120 s.",
        )
    except OSError as exc:
        return StaticAnalysisResult(
            tool=spec.name,
            status="failed",
            command=argv,
            detail=f"OS error running {spec.check_argv[0]!r}: {exc}",
        )

    raw_output = proc.stdout or proc.stderr or ""
    violation_count = _count_violations(raw_output, spec.name) if proc.returncode != 0 else 0

    if proc.returncode == 0:
        status: str = "ok"
    else:
        status = "violations"

    return StaticAnalysisResult(
        tool=spec.name,
        status=status,  # type: ignore[arg-type]
        command=argv,
        exit_code=proc.returncode,
        violation_count=violation_count,
        raw_output=raw_output,
        scoped=scoped,
    )
