"""Tests for PPTX layout rendering, slide count semantics, theme variations, and layout validation."""

from __future__ import annotations

import io
from pptx import Presentation

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.pptx_writer import _clean_text, render
from app.services.rendering.layout_validator import validate_deck_geometry


def _make_deck(content_slides_count: int) -> ContentIR:
    nodes = []
    for i in range(1, content_slides_count + 1):
        nodes.append(
            Node(
                id=f"n_{i}",
                kind="slide",
                title=f"Content Slide {i}",
                items=[
                    f"Key point 1 for slide {i} with verified metric ₹4.80 crore.",
                    f"Supporting evidence and operational data item {i}.",
                    f"Strategic recommendation and milestone step {i}.",
                ],
                notes=f"Speaker narrative for slide {i}.",
                layout="standard_bullet" if i % 2 == 1 else "two_column",
            )
        )
    return ContentIR(title="Test Presentation Deck", nodes=nodes)


def test_clean_text_currency_symbols():
    """Verify corrupted currency glyphs like I4.80 crore are cleaned to ₹4.80 crore."""
    raw = "The total project cost is I4.80 crore with I18.4 lakh allocated initially."
    cleaned = _clean_text(raw)
    assert "₹4.80 crore" in cleaned
    assert "₹18.4 lakh" in cleaned


def test_physical_slide_counts():
    """Verify requested N slide count produces exactly N physical slides (1 cover + N-1 content slides)."""
    for requested_total in (5, 8, 10, 12, 15):
        content_count = requested_total - 1
        ir = _make_deck(content_count)
        pptx_bytes = render(ir, source_name="EV Feasibility Report")
        prs = Presentation(io.BytesIO(pptx_bytes))
        assert len(prs.slides) == requested_total, (
            f"Expected {requested_total} physical slides, got {len(prs.slides)}"
        )


def test_theme_rendering_variations():
    """Verify different visual themes produce distinct background colors."""
    ir = _make_deck(3)
    themes_to_test = ["corporate_blue", "midnight_dark", "academic_research", "data_analytics"]
    bg_colors = set()

    for theme in themes_to_test:
        pptx_bytes = render(ir, theme=theme)
        prs = Presentation(io.BytesIO(pptx_bytes))
        cover_slide = prs.slides[0]
        bg_rgb = cover_slide.background.fill.fore_color.rgb
        bg_colors.add(str(bg_rgb))

    # At least corporate_blue (white) and midnight_dark (dark blue) must differ
    assert len(bg_colors) >= 3, f"Expected distinct theme background colors, got {bg_colors}"


from app.services.rendering.layout_validator import validate_and_autofix_deck, validate_deck_geometry


def test_layout_geometry_validator():
    """Verify validate_deck_geometry catches oversized text and empty slides."""
    ir = _make_deck(3)
    # Add an empty slide
    ir.nodes.append(Node(id="n_empty", kind="slide", title="", items=[]))
    warnings = validate_deck_geometry(ir)
    assert any("Empty slide" in w for w in warnings)


def test_validate_and_autofix_deck():
    """Verify validate_and_autofix_deck automatically fixes long titles, metrics overflow, bullet overflow, and empty slides."""
    overloaded_ir = ContentIR(
        title="Excessively Long Presentation Title That Exceeds One Hundred Characters In Length And Needs Automatic Truncation For Presentation Cover Slide",
        nodes=[
            # Metrics slide with >4 items
            Node(
                id="n_metrics",
                kind="slide",
                title="Metrics",
                layout="metrics",
                items=["$10M: Revenue", "50%: Growth", "100k: Users", "99.9%: Uptime", "5: Extra Metric", "6: Another Metric"],
            ),
            # Standard bullet slide with >7 items
            Node(
                id="n_bullets",
                kind="slide",
                title="Bullets",
                layout="standard_bullet",
                items=[f"Bullet item {i}" for i in range(1, 10)],
            ),
            # Empty slide
            Node(id="n_empty", kind="slide", title="", items=[]),
        ]
    )

    autofixed_ir, fixes = validate_and_autofix_deck(overloaded_ir)

    assert len(fixes) > 0
    assert autofixed_ir.title.endswith("...")
    assert len(autofixed_ir.title) <= 100

    # Metrics slide should be capped to 4 items and split
    metrics_slides = [n for n in autofixed_ir.nodes if n.kind == "slide" and "Metrics" in (n.title or "")]
    assert len(metrics_slides) >= 2
    assert len(metrics_slides[0].items) == 4

    # Bullet slide should be split
    bullet_slides = [n for n in autofixed_ir.nodes if n.kind == "slide" and "Bullets" in (n.title or "")]
    assert len(bullet_slides) >= 2

    # Empty slide should be populated
    empty_fixed = [n for n in autofixed_ir.nodes if n.id == "n_empty"][0]
    assert len(empty_fixed.items) > 0

