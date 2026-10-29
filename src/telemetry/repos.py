"""Repo registry — loads `repos.toml`, the one list of repos guacamayo governs.

Before this there were three lists (`ACTIVE_REPOS`, `hygiene.sh`'s `REPOS`, the VS Code
workspace) and each had drifted: kiez was on none of them, so nothing ever checked it.
A malformed entry raises rather than being dropped — a repo that silently falls out of
the registry is the same failure as a repo that was never on a list.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "repos.toml"

ROLES = frozenset({"platform", "product", "job-search", "retiring"})
VISIBILITIES = frozenset({"public", "private"})


@dataclass(frozen=True)
class Repo:
    """One governed repo."""

    name: str
    role: str
    visibility: str
    path: Path
    review: bool

    @property
    def cloned(self) -> bool:
        return (self.path / ".git").exists()


def load_repos(path: Path = REGISTRY_PATH) -> tuple[Repo, ...]:
    """Parse the registry, in file order.

    Raises:
        ValueError: an entry is missing a field or uses an unknown role/visibility.
    """
    data = tomllib.loads(path.read_text())
    repos: list[Repo] = []
    for name, entry in data.get("repos", {}).items():
        missing = {"role", "visibility", "path", "review"} - entry.keys()
        if missing:
            raise ValueError(f"{path.name}: [repos.{name}] missing {sorted(missing)}")
        if entry["role"] not in ROLES:
            raise ValueError(
                f"{path.name}: [repos.{name}] role {entry['role']!r} not in {sorted(ROLES)}"
            )
        if entry["visibility"] not in VISIBILITIES:
            raise ValueError(
                f"{path.name}: [repos.{name}] visibility {entry['visibility']!r} "
                f"not in {sorted(VISIBILITIES)}"
            )
        if not isinstance(entry["review"], bool):
            raise ValueError(  # noqa: TRY004 — a config error, like the checks above
                f"{path.name}: [repos.{name}] review must be true or false"
            )
        repos.append(
            Repo(
                name=name,
                role=entry["role"],
                visibility=entry["visibility"],
                path=Path(entry["path"]).expanduser(),
                review=entry["review"],
            )
        )
    if not repos:
        raise ValueError(f"{path.name}: no [repos.*] entries")
    return tuple(repos)
