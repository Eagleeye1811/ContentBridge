"""Who may see and do what.

Pure functions, deliberately separate from the route handlers: the approval
rules are the part worth testing exhaustively, and they should be readable in
one place rather than inferred from a handler.
"""

from __future__ import annotations

from dataclasses import dataclass

# An approver can act on anything submitted; before submission an output is the
# editor's own business.
VISIBLE_TO_APPROVERS = frozenset({"in_review", "approved", "rejected", "exported"})

# States an editor may submit from. `rejected` is included so a rejection can
# be fixed and resubmitted rather than requiring a fresh generation.
SUBMITTABLE = frozenset({"draft", "verified", "rejected"})


@dataclass(frozen=True, slots=True)
class Permissions:
    can_submit: bool
    can_approve: bool
    can_reject: bool


def can_view(*, status: str, role: str, is_owner: bool) -> bool:
    if is_owner:
        return True
    return role == "approver" and status in VISIBLE_TO_APPROVERS


def permissions(
    *, status: str, role: str, is_owner: bool, verified: bool, blocked: bool
) -> Permissions:
    """What this user may do to this output right now.

    An output must be verified before it can be submitted, and free of blocking
    reasons before it can be approved. Rejection is always available to an
    approver looking at something in review -- refusing bad work must never be
    gated on the work being good.
    """
    is_approver = role == "approver"
    return Permissions(
        can_submit=is_owner and verified and status in SUBMITTABLE,
        can_approve=is_approver and status == "in_review" and not blocked,
        can_reject=is_approver and status == "in_review",
    )
