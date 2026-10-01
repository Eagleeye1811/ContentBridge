"""Trust score and the approval gate."""

from __future__ import annotations

from collections.abc import Sequence

WEIGHTS = {
    "supported": 1.0,
    "partial": 0.6,
    "unsupported": 0.15,
    "contradicted": 0.0,
}

# Each open high-severity consistency issue costs this much trust.
ISSUE_PENALTY = 0.1


def trust_score(verdicts: Sequence[str], open_high_issues: int = 0) -> float:
    """0..1. An output with no claims scores 0 -- there is nothing to trust."""
    if not verdicts:
        return 0.0
    base = sum(WEIGHTS.get(v, 0.0) for v in verdicts) / len(verdicts)
    return round(max(0.0, base - ISSUE_PENALTY * open_high_issues), 3)


def blocking_reasons(verdicts: Sequence[str], open_high_issues: int = 0) -> list[str]:
    """Why this output cannot be approved yet. Empty means it can."""
    reasons: list[str] = []
    contradicted = sum(1 for v in verdicts if v == "contradicted")
    if contradicted:
        reasons.append(
            f"{contradicted} sentence{'s conflict' if contradicted > 1 else ' conflicts'} "
            "with the source. Edit and check again."
        )
    if open_high_issues:
        reasons.append(
            f"{open_high_issues} number{'s differ' if open_high_issues > 1 else ' differs'} "
            "from the source. See Numbers check."
        )
    return reasons
