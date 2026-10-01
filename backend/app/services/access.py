"""Who may create which outputs.

An employee's job role lists the output types they may create. Administrators
and people without a job role may create every type. This is the one place
that rule lives; the API and the UI both ask it.
"""

from __future__ import annotations

from app.models import User
from app.services.generation.formats import FORMATS

# Starting roles for an organisation. Administrators can edit or replace them.
DEFAULT_JOB_ROLES: list[dict] = [
    {
        "name": "Social Media Analyst",
        "description": "Runs the organisation's public social media presence.",
        "allowed_types": ["linkedin", "twitter", "infographic", "video"],
    },
    {
        "name": "Public Relations Officer",
        "description": "Handles statements to the press and the public.",
        "allowed_types": ["press_release", "linkedin", "twitter", "email"],
    },
    {
        "name": "Research Analyst",
        "description": "Turns technical findings into reports and briefings.",
        "allowed_types": ["report", "summary", "advisory"],
    },
    {
        "name": "Cyber Security Analyst",
        "description": "Issues security advisories and incident reports.",
        "allowed_types": ["advisory", "report", "email"],
    },
    {
        "name": "Training & Outreach Officer",
        "description": "Prepares training and awareness material.",
        "allowed_types": ["ppt", "video", "infographic"],
    },
    {
        "name": "Senior Management",
        "description": "Needs short briefings and decks for decisions.",
        "allowed_types": ["summary", "ppt", "report"],
    },
]


def all_types() -> list[str]:
    return list(FORMATS)


def allowed_types(user: User) -> list[str]:
    """Output types this user may create, in catalog order."""
    if user.role == "admin" or user.job_role is None:
        return all_types()
    permitted = set(user.job_role.allowed_types or [])
    # Outputs stored under the old key still count as LinkedIn.
    if "social" in permitted:
        permitted.add("linkedin")
    return [key for key in FORMATS if key in permitted]


def can_create(user: User, output_type: str) -> bool:
    return output_type in allowed_types(user)
