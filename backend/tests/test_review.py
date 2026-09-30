"""Approval gate tests.

This is the last line between a generated document and someone acting on it,
so the rules are tested exhaustively rather than sampled.
"""

from __future__ import annotations

import pytest

from app.services.review.policy import SUBMITTABLE, VISIBLE_TO_APPROVERS, can_view, permissions
from app.services.verification.scoring import blocking_reasons

STATES = ["draft", "verified", "in_review", "approved", "rejected", "exported"]


def perms(**kw):
    base = dict(status="in_review", role="approver", is_owner=False, verified=True, blocked=False)
    return permissions(**{**base, **kw})


# --- visibility ------------------------------------------------------------


@pytest.mark.parametrize("status", STATES)
def test_an_owner_sees_their_own_output_in_any_state(status):
    assert can_view(status=status, role="editor", is_owner=True)


@pytest.mark.parametrize("status", sorted(VISIBLE_TO_APPROVERS))
def test_an_approver_sees_anything_submitted(status):
    """Without this an approver could never act on an editor's work."""
    assert can_view(status=status, role="approver", is_owner=False)


@pytest.mark.parametrize("status", ["draft", "verified"])
def test_an_approver_cannot_see_unsubmitted_drafts(status):
    assert not can_view(status=status, role="approver", is_owner=False)


@pytest.mark.parametrize("status", STATES)
def test_an_editor_never_sees_another_editors_output(status):
    assert not can_view(status=status, role="editor", is_owner=False)


# --- the gate --------------------------------------------------------------


def test_a_clean_verified_output_can_be_approved():
    assert perms().can_approve


def test_a_blocked_output_cannot_be_approved():
    """The whole point: a contradicted claim stops the document here."""
    assert not perms(blocked=True).can_approve


def test_a_blocked_output_can_still_be_rejected():
    """Refusing bad work must never be gated on the work being good."""
    assert perms(blocked=True).can_reject


@pytest.mark.parametrize("status", [s for s in STATES if s != "in_review"])
def test_only_an_output_in_review_can_be_approved(status):
    assert not perms(status=status).can_approve
    assert not perms(status=status).can_reject


def test_an_editor_cannot_approve_even_their_own_work():
    """Separation of duties is the reason the two roles exist."""
    assert not perms(role="editor", is_owner=True).can_approve
    assert not perms(role="editor", is_owner=True).can_reject


def test_an_approver_cannot_approve_something_never_submitted():
    assert not perms(status="verified").can_approve


def test_approval_is_not_repeatable():
    assert not perms(status="approved").can_approve


# --- submission ------------------------------------------------------------


@pytest.mark.parametrize("status", sorted(SUBMITTABLE))
def test_an_owner_can_submit_verified_work(status):
    assert perms(status=status, role="editor", is_owner=True, verified=True).can_submit


def test_a_rejected_output_can_be_fixed_and_resubmitted():
    assert perms(status="rejected", role="editor", is_owner=True).can_submit


def test_unverified_work_cannot_be_submitted():
    """Submitting before verification would put an unchecked document in the queue."""
    assert not perms(status="draft", role="editor", is_owner=True, verified=False).can_submit


def test_a_non_owner_cannot_submit():
    assert not perms(status="verified", role="approver", is_owner=False).can_submit


@pytest.mark.parametrize("status", ["in_review", "approved", "exported"])
def test_already_submitted_work_is_not_submitted_again(status):
    assert not perms(status=status, role="editor", is_owner=True).can_submit


# --- the reasons the gate gives ------------------------------------------


def test_a_contradicted_claim_is_reported_as_the_blocker():
    reasons = blocking_reasons(["supported", "supported", "contradicted"])
    assert reasons == ["1 claim contradicted by the source"]


def test_several_blockers_are_all_reported():
    reasons = blocking_reasons(["contradicted", "contradicted"], open_high_issues=2)
    assert len(reasons) == 2
    assert "2 claims contradicted" in reasons[0]
    assert "2 unresolved high-severity" in reasons[1]


def test_unsupported_claims_do_not_block_on_their_own():
    """Unsupported means unproven, not wrong. A human decides."""
    assert blocking_reasons(["unsupported", "partial"]) == []
