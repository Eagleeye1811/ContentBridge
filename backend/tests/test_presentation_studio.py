import uuid
import pytest
from app.schemas.content_ir import ContentIR, Node
from app.schemas.outputs import PresentationOutlineRequest, PresentationOutlineResponse, SlideRegenerateRequest
from app.services.generation.audiences import get_audience
from app.services.generation.formats import get_format
from app.services.generation.formats.base import apply_options, resolve_options
from app.services.rendering.pdf_writer import render as render_pdf
from app.services.rendering.pptx_writer import render as render_pptx


def test_pptx_render_themes_and_layouts():
    ir = ContentIR(
        title="AI Presentation Studio Test",
        nodes=[
            Node(id="n1", kind="slide", title="Overview", layout="section_divider", text="Section 1"),
            Node(id="n2", kind="slide", title="Key Metrics", layout="metrics", items=["46 files: Confirmed Download Scope", "3h 50m: Incident Response Window"]),
            Node(id="n3", kind="slide", title="Process Steps", layout="process", items=["11 March 2026 14:32: Suspicious Sign-in", "11 March 2026 14:35: Automated Alert", "11 March 2026 18:22: Account Disabled"]),
            Node(id="n4", kind="slide", title="Comparison", layout="two_column", items=["Confirmed Scope: 46 Files Downloaded", "Unresolved: External Disclosure Unproven"]),
            Node(id="n5", kind="slide", title="Timeline", layout="timeline", items=["11 March 2026 14:32: Intrusion detected", "11 March 2026 18:22: Remediation applied"]),
            Node(id="n6", kind="slide", title="Key Takeaways", layout="key_takeaways", items=["Enforce MFA across all endpoints", "Conduct annual audit"]),
            Node(id="n7", kind="slide", title="Data Table", layout="table", rows=[["Metric", "Value"], ["Uptime", "99.9%"]]),
        ]
    )

    all_themes = [
        "corporate_blue",
        "midnight_dark",
        "minimal_monochrome",
        "modern_gradient",
        "academic_research",
        "data_analytics",
        "warm_editorial",
        "high_contrast",
        # Legacy aliases
        "navy_white",
        "corporate_blue_grey",
        "dark_charcoal_blue",
    ]

    for theme in all_themes:
        data = render_pptx(ir, source_name="test.pdf", theme=theme)
        assert isinstance(data, bytes)
        assert len(data) > 0
        assert data.startswith(b"PK")  # PPTX is a zip file starting with PK magic bytes


def test_pdf_rendering():
    ir = ContentIR(
        title="PDF Slide Deck Presentation",
        nodes=[
            Node(id="n1", kind="slide", title="Executive Briefing", items=["Key Point 1", "Key Point 2"]),
            Node(id="n2", kind="slide", title="Detailed Timeline", layout="timeline", items=["11 March 2026 14:32: Intrusion Start", "11 March 2026 18:22: Account Disabled"]),
        ]
    )
    pdf_bytes = render_pdf(ir, source_name="security_advisory.pdf", theme="corporate_blue")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")


def test_detail_level_prompts_and_controls():
    from app.services.generation.controls import resolve_controls, control_fragments
    from app.services.generation.prompt_builder import build_prompt
    from app.services.generation.audiences import get_audience
    from app.services.generation.formats import get_format

    class MockFact:
        id = uuid.uuid4()
        key = "f1"
        type = "metric"
        statement = "46 files downloaded during incident window."
        canonical_value = "46"
        unit = "files"

    facts = [MockFact()]
    spec = get_format("ppt")
    audience = get_audience("officer")

    concise_controls = resolve_controls({"detail_level": "concise"})
    balanced_controls = resolve_controls({"detail_level": "balanced"})
    detailed_controls = resolve_controls({"detail_level": "detailed"})

    assert concise_controls["detail_level"] == "concise"
    assert balanced_controls["detail_level"] == "balanced"
    assert detailed_controls["detail_level"] == "detailed"

    concise_prompt, _ = build_prompt(facts=facts, spec=spec, audience=audience, language="en", source_name="incident_report.pdf", controls=concise_controls)
    balanced_prompt, _ = build_prompt(facts=facts, spec=spec, audience=audience, language="en", source_name="incident_report.pdf", controls=balanced_controls)
    detailed_prompt, _ = build_prompt(facts=facts, spec=spec, audience=audience, language="en", source_name="incident_report.pdf", controls=detailed_controls)

    assert "Detail level: concise" in concise_prompt
    assert "Detail level: balanced" in balanced_prompt
    assert "Detail level: detailed" in detailed_prompt

    # Verify distinct instructions in prompts
    assert concise_prompt != balanced_prompt
    assert balanced_prompt != detailed_prompt
    assert concise_prompt != detailed_prompt


def test_quality_checker_placeholder_and_density_warnings():
    from app.services.generation.generator import check_deck_quality

    bad_ir = ContentIR(
        title="Generic Deck",
        nodes=[
            Node(id="n1", kind="slide", title="Overview", items=["Event 1 occurred", "#1 priority"]),
            Node(id="n2", kind="slide", title="Overview", items=["Duplicate title test"]),
        ]
    )

    warnings = check_deck_quality(bad_ir, detail_level="detailed")
    assert any("Generic placeholder 'Event 1'" in w for w in warnings)
    assert any("Repetitive slide title" in w for w in warnings)


def test_long_text_and_dense_slide_formatting():
    long_item = "Very long bullet point text that describes a detailed security finding with extensive background context and exact figures: 37 credentials compromised out of 62 percent accounts."
    ir = ContentIR(
        title="Dense Content Deck",
        nodes=[
            Node(
                id="n1",
                kind="slide",
                title="Extensive Analysis of Security Incident and Mitigation Plan",
                items=[long_item, long_item, long_item, long_item, long_item, long_item],
                notes="Detailed speaker notes explaining the incident context.",
                fact_ids=["f1", "f2"],
            )
        ]
    )
    pptx_bytes = render_pptx(ir, source_name="report.pdf", theme="corporate_blue")
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 0


def test_presentation_outline_request_schema():
    req = PresentationOutlineRequest(
        title="Cybersecurity Overview",
        purpose="executive briefing",
        audience="senior_leadership",
        slide_count="10",
        duration="15",
        language="en",
        theme="midnight_dark",
    )
    assert req.title == "Cybersecurity Overview"
    assert req.theme == "midnight_dark"
    assert req.slide_count == "10"


def test_technical_team_audience_resolution():
    spec = get_format("ppt")
    resolved = resolve_options(spec, {"presenting_to": "technical"})
    assert resolved["presenting_to"] == "technical"

    audience = get_audience("technical")
    assert audience.key == "technical"
    assert "engineers" in audience.prompt_fragment.lower()


@pytest.mark.parametrize(
    "audience_key",
    ["team", "officials", "public", "technical", "researchers", "students", "senior_leadership"],
)
def test_all_audience_choices_resolution(audience_key):
    spec = get_format("ppt")
    resolved = resolve_options(spec, {"presenting_to": audience_key})
    assert resolved["presenting_to"] == audience_key

    audience = get_audience(audience_key)
    assert audience.key == audience_key or audience.name is not None


@pytest.mark.parametrize(
    "slide_count, expected_max",
    [
        ("5", 5),
        ("8", 8),
        ("10", 10),
        ("12", 12),
        ("15", 15),
        ("20", 20),
        ("auto", 25),
    ],
)
def test_flexible_slide_counts(slide_count, expected_max):
    spec = get_format("ppt")
    resolved = resolve_options(spec, {"slides": slide_count})
    assert resolved["slides"] == slide_count

    derived_spec = apply_options(spec, {"slides": slide_count})
    assert derived_spec.max_nodes == expected_max


def test_edit_presentation_reconfigure_and_user_modified_preservation():
    from app.schemas.outputs import PresentationReconfigureRequest
    original_ir = ContentIR(
        title="Original Security Presentation",
        nodes=[
            Node(id="s1", kind="slide", title="Original Title", items=["Bullet 1"], is_user_modified=True),
            Node(id="s2", kind="slide", title="Slide 2", items=["Bullet 2"], is_user_modified=False),
        ]
    )
    
    # Test user modified flag retention in schema
    assert original_ir.nodes[0].is_user_modified is True
    assert original_ir.nodes[1].is_user_modified is False


def test_adjust_slide_count_logic():
    from app.schemas.outputs import SlideCountAdjustRequest, PresentationOutlineRequest
    req = SlideCountAdjustRequest(
        target_count="15",
        config=PresentationOutlineRequest(title="Incident Briefing", slide_count="15")
    )
    assert req.target_count == "15"
    assert req.config.title == "Incident Briefing"

