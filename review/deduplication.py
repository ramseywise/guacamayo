from __future__ import annotations

from review.config import DEDUP_LINE_TOLERANCE
from review.schemas.models import FileLocation, ReviewFinding


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
    def __init__(self, items: list[str]) -> None:
        self._parent = {item: item for item in items}

    def find(self, item: str) -> str:
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        self._parent[item] = root
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def find_duplicate_clusters(findings: list[ReviewFinding]) -> list[list[ReviewFinding]]:
    by_id = {f.id: f for f in findings}
    uf = _UnionFind(list(by_id))
    for i, f1 in enumerate(findings):
        for f2 in findings[i + 1 :]:
            if _is_candidate_pair(f1, f2):
                uf.union(f1.id, f2.id)
    clusters: dict[str, list[ReviewFinding]] = {}
    for fid, finding in by_id.items():
        root = uf.find(fid)
        clusters.setdefault(root, []).append(finding)
    return list(clusters.values())
