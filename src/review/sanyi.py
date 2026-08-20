"""SANYI violation code → merge impact / native severity mappings.

Authoritative source for the 11 violation codes defined in
~/.claude/skills/sanyi/references/violations.md.
"""

from review.schemas.models import MergeImpact, NativeSeverity

_MERGE_IMPACT: dict[str, MergeImpact] = {
    # 不易 Buyi — invariant violations
    "BY-1": MergeImpact.BLOCKER,
    "BY-2": MergeImpact.BLOCKER,
    "BY-3": MergeImpact.BLOCKER,
    "BY-4": MergeImpact.BLOCKER,
    # 简易 Jianyi — complexity/entropy violations
    "JY-1": MergeImpact.IMPORTANT,
    "JY-2": MergeImpact.IMPORTANT,
    "JY-3": MergeImpact.IMPORTANT,
    # 变易 Bianyi — changeable-value violations
    "BN-1": MergeImpact.SUGGESTION,
    # Hygiene / unassigned
    "MG-1": MergeImpact.NIT,
    "UN-1": MergeImpact.NIT,
    "UN-2": MergeImpact.NIT,
}

_NATIVE_SEVERITY: dict[str, NativeSeverity] = {
    "BY-1": NativeSeverity.BLOCKER,
    "BY-2": NativeSeverity.BLOCKER,
    "BY-3": NativeSeverity.BLOCKER,
    "BY-4": NativeSeverity.BLOCKER,
    "JY-1": NativeSeverity.WARNING,
    "JY-2": NativeSeverity.WARNING,
    "JY-3": NativeSeverity.WARNING,
    "BN-1": NativeSeverity.INFO,
    "MG-1": NativeSeverity.NOTICE,
    "UN-1": NativeSeverity.NOTICE,
    "UN-2": NativeSeverity.NOTICE,
}


def violation_merge_impact(code: str) -> MergeImpact:
    """Return the canonical MergeImpact for a SANYI violation code.

    Raises ValueError for unknown codes.
    """
    try:
        return _MERGE_IMPACT[code]
    except KeyError:
        raise ValueError(f"Unknown SANYI violation code: {code!r}")


def violation_source_native(code: str) -> NativeSeverity:
    """Return the canonical NativeSeverity for a SANYI violation code.

    Raises ValueError for unknown codes.
    """
    try:
        return _NATIVE_SEVERITY[code]
    except KeyError:
        raise ValueError(f"Unknown SANYI violation code: {code!r}")
