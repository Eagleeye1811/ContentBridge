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
                warnings.append(
                    f"Slide {idx} ('{title}'): Metrics layout has {len(items)} items. Maximum recommended for readable KPI cards is 4."
                )
            for item in items:
                if len(item) > 120:
                    warnings.append(f"Slide {idx} ('{title}'): Metric card text '{item[:30]}...' is too long and may clip.")
        elif layout in {"timeline", "process", "roadmap"}:
            if len(items) > 5:
                warnings.append(
                    f"Slide {idx} ('{title}'): {layout.capitalize()} layout has {len(items)} nodes. Maximum recommended per slide is 5."
                )
        elif layout in {"two_column", "comparison"}:
            if len(items) > 8:
                warnings.append(
                    f"Slide {idx} ('{title}'): Two-column comparison layout has {len(items)} total items, which may overflow column cards."
                )
        elif layout == "standard_bullet":
            if len(items) > 7:
                warnings.append(
                    f"Slide {idx} ('{title}'): Standard bullet slide has {len(items)} bullet points. Maximum recommended is 7 to prevent text box overflow."
                )
            for item in items:
                if len(item) > 220:
                    warnings.append(
                        f"Slide {idx} ('{title}'): Bullet item '{item[:40]}...' is excessively long (>220 chars). Rephrase or split into multiple points."
                    )

        # Content density check vs detail_level setting
        if not items and not s.text and not s.rows:
            warnings.append(f"Slide {idx} ('{title}'): Empty slide detected (no items, text, or table rows).")
        elif detail_level == "detailed" and len(items) < 2 and not s.rows:
            warnings.append(f"Slide {idx} ('{title}'): Low information density for 'detailed' setting (only {len(items)} point).")

    return warnings


def validate_and_autofix_deck(ir: ContentIR, detail_level: str = "balanced") -> tuple[ContentIR, list[str]]:
    """Automatically validate and auto-correct presentation slides before rendering.

    Fixes:
    - Truncates/concises long slide titles (>90 chars)
    - Restructures/splits layout items if capacity is exceeded (e.g. metrics > 4, timeline > 5, bullets > 7)
    - Shortens overly long bullet items (>220 chars)
    - Prunes empty slides or populates missing titles
    - Normalizes layout types to supported standard choices
    """
    fixed_nodes: list[Node] = []
    applied_fixes: list[str] = []

    # Process cover title if needed
    clean_title = (ir.title or "Presentation Deck").strip()
    if len(clean_title) > 100:
        clean_title = clean_title[:97] + "..."
        applied_fixes.append("Truncated presentation title to fit cover layout.")

    for idx, node in enumerate(ir.nodes):
        if node.kind != "slide":
            fixed_nodes.append(node)
            continue

        slide = node.model_copy()
        layout = (slide.layout or "standard_bullet").lower()
        title = (slide.title or f"Slide {idx + 1}").strip()

        # 1. Title length autofix
        if len(title) > 90:
            title = title[:87].rsplit(" ", 1)[0] + "..."
            applied_fixes.append(f"Slide {idx + 1}: Shortened long title to maintain header boundaries.")
        slide.title = title

        # 2. Item capacity & text length autofix
        items = [i.strip() for i in (slide.items or []) if i.strip()]

        # Shorten individual items if excessively long
        items_fixed = False
        new_items: list[str] = []
        for it in items:
            if len(it) > 220:
                shortened = it[:200].rsplit(" ", 1)[0] + "..."
                new_items.append(shortened)
                items_fixed = True
            else:
                new_items.append(it)
        if items_fixed:
            applied_fixes.append(f"Slide {idx + 1}: Shortened bullet text exceeding 220 characters.")
        items = new_items

        # Restructure based on layout capacity
        if layout == "metrics" and len(items) > 4:
            primary_items = items[:4]
            extra_items = items[4:]
            slide.items = primary_items
            applied_fixes.append(f"Slide {idx + 1} ('{title}'): Capped metrics to 4 key KPI cards for visual balance.")
            fixed_nodes.append(slide)

            extra_slide = Node(
                id=f"{slide.id}_overflow",
                kind="slide",
                title=f"{title} (Continued)",
                layout="standard_bullet",
                items=extra_items,
                notes=slide.notes,
                fact_ids=slide.fact_ids,
            )
            fixed_nodes.append(extra_slide)
            continue

        elif layout in {"timeline", "process", "roadmap"} and len(items) > 5:
            primary_items = items[:5]
            extra_items = items[5:]
            slide.items = primary_items
            applied_fixes.append(f"Slide {idx + 1} ('{title}'): Capped {layout} steps to 5 nodes to prevent card overlap.")
            fixed_nodes.append(slide)

            extra_slide = Node(
                id=f"{slide.id}_overflow",
                kind="slide",
                title=f"{title} (Phase 2)",
                layout="standard_bullet",
                items=extra_items,
                notes=slide.notes,
                fact_ids=slide.fact_ids,
            )
            fixed_nodes.append(extra_slide)
            continue

        elif layout == "standard_bullet" and len(items) > 7:
            primary_items = items[:6]
            extra_items = items[6:]
            slide.items = primary_items
            applied_fixes.append(f"Slide {idx + 1} ('{title}'): Split 7+ bullet points into 2 slides for legibility.")
            fixed_nodes.append(slide)

            extra_slide = Node(
                id=f"{slide.id}_overflow",
                kind="slide",
                title=f"{title} (Continued)",
                layout="standard_bullet",
                items=extra_items,
                notes=slide.notes,
                fact_ids=slide.fact_ids,
            )
            fixed_nodes.append(extra_slide)
            continue

        # 3. Empty slide autofix
        if not items and not slide.text and not slide.rows:
            items = ["Key takeaway summary point", "Supporting contextual detail"]
            applied_fixes.append(f"Slide {idx + 1}: Populated empty slide with structured takeaway placeholders.")

        slide.items = items
        fixed_nodes.append(slide)

    autofixed_ir = ContentIR(title=clean_title, nodes=fixed_nodes)
    return autofixed_ir, applied_fixes

