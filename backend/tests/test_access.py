"""Employee roles decide which outputs a person may create."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.schemas.content_ir import ContentIR, Node
from app.services.access import DEFAULT_JOB_ROLES, all_types, allowed_types, can_create
from app.services.generation.formats import FORMATS
from app.services.generation.generator import _validate
from app.services.rendering import render_text


def person(role="editor", job=None):
    job_role = SimpleNamespace(id=uuid.uuid4(), name="Job", allowed_types=job) if job else None
    return SimpleNamespace(
        id=uuid.uuid4(), role=role, job_role=job_role, created_at=datetime.now(UTC)
    )


def test_a_social_media_analyst_gets_only_social_outputs():
    analyst = person(job=["linkedin", "twitter"])
    assert allowed_types(analyst) == ["linkedin", "twitter"]
    assert can_create(analyst, "twitter")
    assert not can_create(analyst, "report")


def test_admins_and_unassigned_people_get_everything():
    assert allowed_types(person(role="admin", job=["linkedin"])) == all_types()
    assert allowed_types(person()) == all_types()


def test_allowed_types_keep_catalog_order():
    assert allowed_types(person(job=["video", "advisory"])) == ["advisory", "video"]


def test_the_old_social_key_still_means_linkedin():
    assert allowed_types(person(job=["social"])) == ["linkedin"]


def test_every_default_role_lists_real_outputs():
    for role in DEFAULT_JOB_ROLES:
        assert role["allowed_types"], role["name"]
        assert set(role["allowed_types"]) <= set(FORMATS), role["name"]


def test_the_social_media_analyst_has_linkedin_and_twitter():
    analyst = next(r for r in DEFAULT_JOB_ROLES if r["name"] == "Social Media Analyst")
    assert {"linkedin", "twitter"} <= set(analyst["allowed_types"])


# --- Twitter/X ------------------------------------------------------------------


def test_an_x_post_over_280_characters_is_sent_back():
    long_post = Node(id="p", kind="post", items=["x" * 300], fact_ids=["f0"])
    problems = _validate(ContentIR(title="T", nodes=[long_post]), FORMATS["twitter"], {"f0"})
    assert any("280" in p for p in problems)


def test_a_thread_is_numbered_in_the_download():
    ir = ContentIR(
        title="Internal",
        nodes=[
            Node(id="a", kind="post", items=["First"], fact_ids=["f0"]),
            Node(id="b", kind="post", items=["Second"], fact_ids=["f0"]),
        ],
    )
    out = render_text(ir, "text", output_type="twitter")
    assert "First\n1/2" in out and "Second\n2/2" in out and "Internal" not in out
