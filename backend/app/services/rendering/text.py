"""ContentIR -> plain text, for email bodies and LinkedIn posts."""

from __future__ import annotations

from app.schemas.content_ir import ContentIR, Node


def _render_node(node: Node) -> str:
    match node.kind:
        case "heading":
            text = node.text or node.title or ""
            return f"{text.upper()}" if (node.level or 2) <= 1 else text
        case "bullets":
            lines = [node.title] if node.title else []
            return "\n".join(lines + [f"* {item}" for item in (node.items or [])])
        case "post":
            # A post's items are its paragraphs, pasted as-is into the platform.
            return "\n\n".join(item for item in (node.items or []) if item)
        case "panel" | "scene":
            lines = [(node.title or node.kind.title()).upper()]
            if node.text:
                lines.append(node.text.strip())
            lines += [f"* {item}" for item in (node.items or [])]
            if node.notes:
                lines.append(f"[Visual] {node.notes}")
            return "\n".join(lines)
        case "callout":
            title = node.title or (node.severity or "Note").upper()
            return f"[{title}] {(node.text or '').strip()}".strip()
        case "slide":
            lines = [node.title or "Slide"]
            lines += [f"* {item}" for item in (node.items or [])]
            return "\n".join(lines)
        case "table":
            return "\n".join("  ".join(row) for row in (node.rows or []))
    return (node.text or "").strip()


def render(ir: ContentIR, *, output_type: str = "", **_: object) -> str:
    # A post is pasted as-is, so it has no document title; an email's title is
    # its subject line.
    if output_type in {"linkedin", "social"}:
        parts: list[str] = []
    elif output_type == "email":
        parts = [f"Subject: {ir.title}", ""]
    else:
        parts = [ir.title, "=" * len(ir.title), ""]
    for node in ir.nodes:
        rendered = _render_node(node)
        if rendered:
            parts += [rendered, ""]
    return "\n".join(parts).rstrip() + "\n"
