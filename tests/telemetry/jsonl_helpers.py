"""JSONL transcript builders shared by the moved factstore tests.

Vendored from ramseywise/librarian tests/unit/test_cartographer_parser.py @ aa3166e
(GUA-93) — that file stays in librarian (it tests shared/parser.py), but the moved
tests imported these builders from it cross-file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _user(ts: str, text: str = "hello", **extra: bool) -> dict[str, Any]:
    return {
        "type": "user",
        "timestamp": ts,
        "message": {"content": text},
        **extra,
    }


def _assistant(
    ts: str,
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_write: int = 0,
    model: str = "claude-sonnet-5",
) -> dict[str, Any]:
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {
            "model": model,
            "content": [{"type": "text", "text": "ok"}],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
        },
    }


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def _assistant_with_tools(ts: str, tool_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Assistant message with tool_use blocks in content."""
    base = _assistant(ts)
    base["message"]["content"] = [
        {"type": "text", "text": "ok"},
        *tool_blocks,
    ]
    return base
