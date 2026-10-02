"""Automatic layout geometry & text-fitting validation for Presentation Studio."""

from __future__ import annotations

from app.schemas.content_ir import ContentIR, Node


def validate_deck_geometry(ir: ContentIR, detail_level: str = "balanced") -> list[str]:
    """Validate layout geometry, bounding box boundaries, character limits, and content density."""
    warnings: list[str] = []
    slides = [n for n in ir.nodes if n.kind == "slide"]
    
    if not slides:
        warnings.append("Deck contains no content slides.")
        return warnings

    for idx, s in enumerate(slides, start=2):
        layout = (s.layout or "standard_bullet").lower()
        title = (s.title or f"Slide {idx}").strip()

        # Title boundary check
        if len(title) > 90:
            warnings.append(f"Slide {idx} ('{title[:30]}...'): Title exceeds recommended 90 character limit.")

        items = [i for i in (s.items or []) if i.strip()]

        # Layout-specific capacity & overflow validation
        if layout in {"metrics"}:
            if len(items) > 4:
                warnings.append(f"Slide {idx} ('{title}'): Metrics layout has {len(items)} items. Maximum recommended for readable KPI cards is 4.")
            for item in items:
                if len(item) > 120:
                    warnings.append(f"Slide {idx} ('{title}'): Metric card text '{item[:30]}...' is too long and may clip.")
        elif layout in {"timeline", "process", "roadmap"}:
            if len(items) > 5:
                warnings.append(f"Slide {idx} ('{title}'): {layout.capitalize()} layout has {len(items)} nodes. Maximum recommended per slide is 5.")
        elif layout in {"two_column", "comparison"}:
            if len(items) > 8:
                warnings.append(f"Slide {idx} ('{title}'): Two-column comparison layout has {len(items)} total items, which may overflow column cards.")
        elif layout == "standard_bullet":
            if len(items) > 7:
                warnings.append(f"Slide {idx} ('{title}'): Standard bullet slide has {len(items)} bullet points. Maximum recommended is 7 to prevent text box overflow.")
            for item in items:
                if len(item) > 220:
                    warnings.append(f"Slide {idx} ('{title}'): Bullet item '{item[:40]}...' is excessively long (>220 chars). Rephrase or split into multiple points.")

        # Content density check vs detail_level setting
        if not items and not s.text and not s.rows:
            warnings.append(f"Slide {idx} ('{title}'): Empty slide detected (no items, text, or table rows).")
        elif detail_level == "detailed" and len(items) < 2 and not s.rows:
            warnings.append(f"Slide {idx} ('{title}'): Low information density for 'detailed' setting (only {len(items)} point).")

    return warnings
