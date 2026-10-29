"""Repo registry: the shipped repos.toml parses, and malformed entries raise."""

from __future__ import annotations

from pathlib import Path

import pytest

from telemetry.repos import load_repos

_ENTRY = 'role = "product"\nvisibility = "public"\npath = "~/x"\nreview = true\n'


def test_shipped_registry_loads() -> None:
    names = [r.name for r in load_repos()]
    assert "guacamayo" in names
    assert len(names) == len(set(names))


def test_path_is_expanded(tmp_path: Path) -> None:
    reg = tmp_path / "repos.toml"
    reg.write_text(f"[repos.x]\n{_ENTRY}")
    (repo,) = load_repos(reg)
    assert repo.path == Path.home() / "x"
    assert not repo.cloned


@pytest.mark.parametrize(
    "body",
    [
        "",  # empty registry
        _ENTRY.replace("review = true\n", ""),  # missing field
        _ENTRY.replace('"product"', '"playground"'),  # unknown role
        _ENTRY.replace('"public"', '"secret"'),  # unknown visibility
        _ENTRY.replace("review = true", 'review = "yes"'),  # non-bool review
    ],
)
def test_malformed_registry_raises(tmp_path: Path, body: str) -> None:
    reg = tmp_path / "repos.toml"
    reg.write_text(f"[repos.x]\n{body}" if body else "")
    with pytest.raises(ValueError, match=r"repos\.toml"):
        load_repos(reg)
