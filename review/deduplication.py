from __future__ import annotations

from review.schemas.models import FileLocation, ReviewFinding

DEDUP_LINE_TOLERANCE = 5


def _file_ranges_overlap(a: FileLocation, b: FileLocation) -> bool:
    if a.path != b.path:
        return False
    if a.start_line is None or b.start_line is None:
        return True
    a_start = a.start_line - DEDUP_LINE_TOLERANCE
    a_end = (a.end_line or a.start_line) + DEDUP_LINE_TOLERANCE
    b_start = b.start_line
    b_end = b.end_line or b.start_line
    return a_start <= b_end and b_start <= a_end


def _symbols_overlap(a: ReviewFinding, b: ReviewFinding) -> bool:
    sa = set(a.location.symbols)
    sb = set(b.location.symbols)
    return bool(sa and sb and sa & sb)


def _any_file_overlap(a: ReviewFinding, b: ReviewFinding) -> bool:
    for fa in a.location.files:
        for fb in b.location.files:
            if _file_ranges_overlap(fa, fb):
                return True
    return False


def _is_candidate_pair(a: ReviewFinding, b: ReviewFinding) -> bool:
    if not _any_file_overlap(a, b):
        return False
    return a.category == b.category or _symbols_overlap(a, b)


class _UnionFind:
    def __init__(self, items: list[int]) -> None:
        self._parent = {item: item for item in items}

    def find(self, item: int) -> int:
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        self._parent[item] = root
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def find_duplicate_clusters(findings: list[ReviewFinding]) -> list[list[ReviewFinding]]:
    # Keyed on list index, not id: ids are only unique within a dimension's numbering
    # (see .claude/skills/shared/SKILL.md), and a repair re-scan renumbers from 001, so
    # distinct findings routinely collide on id. Index keys conserve every finding.
    uf = _UnionFind(list(range(len(findings))))
    for i, f1 in enumerate(findings):
        for j, f2 in enumerate(findings[i + 1 :], start=i + 1):
            if _is_candidate_pair(f1, f2):
                uf.union(i, j)
    clusters: dict[int, list[ReviewFinding]] = {}
    for idx, finding in enumerate(findings):
        root = uf.find(idx)
        clusters.setdefault(root, []).append(finding)
    return list(clusters.values())
