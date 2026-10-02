import uuid
import pytest
from app.schemas.content_ir import ContentIR, Node, node_word_count
from app.services.generation.audiences import get_audience
from app.services.generation.formats import get_format
from app.services.generation.formats.base import apply_options
from app.services.generation.controls import resolve_controls
from app.services.generation.prompt_builder import build_prompt
from app.services.rendering.pptx_writer import render as render_pptx
from app.services.generation.generator import check_deck_quality, _validate


class FakeFact:
    def __init__(self, key, ftype, statement, value=None, unit=None):
        self.id = uuid.uuid4()
        self.key = key
        self.type = ftype
        self.statement = statement
        self.canonical_value = value
        self.unit = unit


CYBERSECURITY_FACTS = [
    FakeFact("window", "date", "Suspicious sign-in occurred at 14:32 UTC on 11 March 2026 and account was disabled at 18:22 UTC (3 hours 50 minutes window).", "11 March 2026", None),
    FakeFact("scope", "metric", "46 sensitive files were downloaded by the affected user account during the active session.", "46", "files"),
    FakeFact("indicators", "metric", "12 identity and cloud audit indicators were reviewed during investigation, with 3 requiring further deep-dive analysis.", "12", "indicators"),
    FakeFact("policy", "finding", "The compromised service account had an explicit MFA policy exclusion configured.", None, None),
    FakeFact("disclosure", "finding", "Available audit logs did not establish evidence of external data disclosure or production system access.", None, None),
    FakeFact("remediation", "recommendation", "Immediate action: Revoke active sessions, enforce MFA on all excluded accounts within 30 days, and conduct 90-day comprehensive audit.", None, None),
]


def test_cybersecurity_incident_deck_acceptance_matrix():
    spec = get_format("ppt")
    audience = get_audience("officer")
    labels = {f"f{i}" for i in range(len(CYBERSECURITY_FACTS))}

    configurations = [
        ("corporate_blue", "concise"),
        ("corporate_blue", "detailed"),
        ("midnight_dark", "balanced"),
        ("academic_research", "detailed"),
        ("data_analytics", "balanced"),
        ("minimal_monochrome", "concise"),
    ]

    rendered_decks = {}

    for theme, detail_level in configurations:
        controls = resolve_controls({"detail_level": detail_level, "theme": theme})
        prompt, _ = build_prompt(
            facts=CYBERSECURITY_FACTS,
            spec=spec,
            audience=audience,
            language="en",
            source_name="incident_report.pdf",
            controls=controls,
        )

        assert f"Detail level: {detail_level}" in prompt

        # Create representative ContentIR deck for acceptance testing
        ir = ContentIR(
            title="Cybersecurity Incident Report: Executive Briefing",
            nodes=[
                Node(id="n1", kind="slide", title="Incident Overview", items=["Suspicious sign-in at 14:32 UTC on 11 March 2026", "Account disabled at 18:22 UTC after 3h 50m window", "Current status: Account isolated, investigation ongoing"], fact_ids=["f0"]),
                Node(id="n2", kind="slide", title="Detection and Timeline", layout="timeline", items=["11 March 2026 14:32 UTC: Suspicious sign-in detected", "11 March 2026 14:35 UTC: Automated risk alert triggered", "11 March 2026 18:22 UTC: Account disabled by SOC team"], fact_ids=["f0"]),
                Node(id="n3", kind="slide", title="Affected Account & Policy Exclusion", layout="two_column", items=["Service account possessed elevated cloud read access", "Explicit MFA policy exclusion permitted unauthenticated entry", "46 files downloaded during session", "No confirmed external disclosure established"], fact_ids=["f1", "f3", "f4"]),
                Node(id="n4", kind="slide", title="Investigation Findings & Indicators", layout="metrics", items=["46 Files: Downloaded Scope", "12 Indicators: Audit Logs Reviewed", "3 Indicators: Deep-dive Follow-up", "3h 50m: Duration Window"], fact_ids=["f1", "f2"]),
                Node(id="n5", kind="slide", title="Remediation Action Plan", layout="process", items=["Immediate: Revoke all active sessions and tokens", "30-Day: Eliminate MFA policy exclusions across service accounts", "90-Day: Conduct end-to-end cloud control plane security audit"], fact_ids=["f5"]),
                Node(id="n6", kind="slide", title="Conclusion & Key Priorities", layout="key_takeaways", items=["Containment achieved with zero production disruption", "MFA enforcement is primary immediate priority", "External disclosure unproven based on current logs"], fact_ids=["f4", "f5"]),
            ]
        )

        # Quality check deck
        warnings = check_deck_quality(ir, detail_level=detail_level)
        # Verify no generic placeholders present
        assert not any("Event 1" in w or "#1" in w for w in warnings)

        # Render to PPTX
        pptx_data = render_pptx(ir, source_name="incident_report.pdf", theme=theme)
        assert isinstance(pptx_data, bytes)
        assert len(pptx_data) > 0
        assert pptx_data.startswith(b"PK")

        rendered_decks[(theme, detail_level)] = (pptx_data, ir)

    # Verify that different themes produce distinct binaries
    binary_1 = rendered_decks[("corporate_blue", "concise")][0]
    binary_2 = rendered_decks[("midnight_dark", "balanced")][0]
    binary_3 = rendered_decks[("academic_research", "detailed")][0]
    assert binary_1 != binary_2
    assert binary_2 != binary_3
