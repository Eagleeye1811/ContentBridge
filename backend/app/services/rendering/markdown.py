"""ContentIR -> Markdown.

A renderer is a pure function of ContentIR with no LLM call. That is what makes
export reproducible and testable.
"""

from __future__ import annotations

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.srt import estimate_seconds

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

        case "bullets":
            lines = [f"**{node.title}**", ""] if node.title else []
            return "\n".join(lines + [f"- {item}" for item in (node.items or [])])

        case "post":
            return "\n\n".join(item for item in (node.items or []) if item)

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

        case "panel":
            lines = [f"### {node.title or 'Panel'}"]
            lines += [f"- **{item}**" for item in (node.items or [])]
            if node.text:
                lines.append(f"\n{node.text.strip()}")
            if node.notes:
                lines.append(f"\n_Visual: {node.notes}_")
            return "\n".join(lines)

        case "scene":
            seconds = estimate_seconds(node.text or "")
            heading = f"### {node.title or 'Scene'}"
            if seconds:
                heading += f" (~{round(seconds)} s)"
            lines = [heading]
            if node.text:
                lines.append(f"\n**Narration:** {node.text.strip()}")
            if node.items:
                lines.append("\n**On-screen text:** " + " · ".join(node.items))
            if node.notes:
                lines.append(f"\n**Visuals:** {node.notes}")
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


def render(
    ir: ContentIR,
    *,
    include_citations: bool = False,
    citations: dict[str, str] | None = None,
    output_type: str = "",
    **_: object,
) -> str:
    # A post is pasted as-is, so it has no document title; an email's title is
    # its subject line.
    if output_type in {"linkedin", "social"}:
        parts: list[str] = []
    elif output_type == "email":
        parts = [f"**Subject:** {ir.title}", ""]
    else:
        parts = [f"# {ir.title}", ""]
    used: list[str] = []

    for node in ir.nodes:
        rendered = _render_node(node)
        if not rendered:
            continue
        if include_citations and node.fact_ids:
            rendered += f"\n\n<!-- facts: {', '.join(node.fact_ids)} -->"
            used += [f for f in node.fact_ids if f not in used]
        parts.append(rendered)
        parts.append("")

    if include_citations and used:
        parts += ["## Sources", ""]
        parts += [f"- {(citations or {}).get(fid, fid)}" for fid in used]
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"
