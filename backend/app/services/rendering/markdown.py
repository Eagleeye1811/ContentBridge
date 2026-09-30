"""ContentIR -> Markdown.

A renderer is a pure function of ContentIR with no LLM call. That is what makes
export reproducible and testable.
"""

from __future__ import annotations

from app.schemas.content_ir import ContentIR, Node

SEVERITY_LABEL = {
    "info": "Information",
    "low": "Low severity",
    "medium": "Medium severity",
    "high": "High severity",
    "critical": "Critical severity",
}


def _render_node(node: Node) -> str:
    match node.kind:
        case "heading":
            level = min(max(node.level or 2, 1), 6)
            return f"{'#' * level} {node.text or node.title or ''}".rstrip()

        case "paragraph" | "quote":
            body = (node.text or "").strip()
            return f"> {body}" if node.kind == "quote" else body

        case "bullets" | "post":
            return "\n".join(f"- {item}" for item in (node.items or []))

        case "callout":
            label = SEVERITY_LABEL.get(node.severity or "", node.severity or "Note")
            title = node.title or label
            body = (node.text or "").strip()
            return f"> **{title}**\n>\n> {body}" if body else f"> **{title}**"

        case "slide":
            lines = [f"### {node.title or 'Slide'}"]
            lines += [f"- {item}" for item in (node.items or [])]
            if node.notes:
                lines.append(f"\n_Speaker notes: {node.notes}_")
            return "\n".join(lines)

        case "table":
            rows = node.rows or []
            if not rows:
                return ""
            header, *body = rows
            out = [
                "| " + " | ".join(header) + " |",
                "| " + " | ".join("---" for _ in header) + " |",
            ]
            out += ["| " + " | ".join(r) + " |" for r in body]
            return "\n".join(out)

    return (node.text or "").strip()


def render(ir: ContentIR, *, include_citations: bool = False) -> str:
    parts = [f"# {ir.title}", ""]
    for node in ir.nodes:
        rendered = _render_node(node)
        if not rendered:
            continue
        if include_citations and node.fact_ids:
            rendered += f"\n\n<!-- facts: {', '.join(node.fact_ids)} -->"
        parts.append(rendered)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
