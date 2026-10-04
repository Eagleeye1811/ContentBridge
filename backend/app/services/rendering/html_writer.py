"""ContentIR -> a standalone HTML document."""

from __future__ import annotations

from html import escape

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.srt import estimate_seconds

CSS = """
:root { color-scheme: light dark; }
body { font: 15px/1.6 -apple-system, "Segoe UI", Roboto, sans-serif;
       max-width: 46rem; margin: 2.5rem auto; padding: 0 1rem; color: #171b24; }
h1 { font-size: 1.6rem; letter-spacing: -0.01em; }
h2 { font-size: 1.15rem; margin-top: 1.8rem; }
h3 { font-size: 1rem; }
blockquote { border-left: 3px solid #e3e6ec; margin: 1rem 0; padding: 0 0 0 1rem;
             color: #4a5468; }
.callout { border: 1px solid #e3e6ec; border-left-width: 4px; border-radius: 6px;
           padding: .7rem 1rem; margin: 1rem 0; }
.callout.high, .callout.critical { border-left-color: #c2410c; background: #fff7ed; }
.callout.medium { border-left-color: #b45309; background: #fffbeb; }
.callout.low, .callout.info { border-left-color: #2563eb; background: #eff6ff; }
.callout strong { display: block; margin-bottom: .2rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
td, th { border: 1px solid #e3e6ec; padding: .4rem .6rem; text-align: left; }
tr:first-child td { background: #f6f7f9; font-weight: 600; }
.panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
          gap: .9rem; margin: 1.2rem 0; }
.panel, .scene { border: 1px solid #e3e6ec; border-radius: 10px; padding: .9rem 1rem; }
.panel h3, .scene h3 { margin: 0 0 .4rem; font-size: .8rem; text-transform: uppercase;
                       letter-spacing: .06em; color: #1d4ed8; }
.panel .stat { font-size: 1.15rem; font-weight: 650; margin: .15rem 0; }
.visual { font-size: .8rem; color: #4a5468; border-top: 1px dashed #e3e6ec;
          margin-top: .6rem; padding-top: .45rem; }
.scene { margin: .9rem 0; }
.scene .narration { font-style: italic; }
.overlay { display: inline-block; background: #eff6ff; color: #1d4ed8; border-radius: 4px;
           padding: .05rem .4rem; margin: 0 .3rem .3rem 0; font-size: .8rem; }
.sources { margin-top: 2.5rem; border-top: 1px solid #e3e6ec; padding-top: 1rem;
           font-size: .85rem; color: #4a5468; }
@media (prefers-color-scheme: dark) {
  body { background: #12151c; color: #e8eaef; }
  td, th { border-color: #2a3040; } tr:first-child td { background: #1b2030; }
  blockquote, .sources { border-color: #2a3040; color: #98a1b3; }
  .panel, .scene, .visual { border-color: #2a3040; } .visual { color: #98a1b3; }
  .overlay { background: #1b2030; color: #93b4ff; }
}
"""


def _node_html(node: Node) -> str:
    match node.kind:
        case "heading":
            level = min(max(node.level or 2, 1), 4)
            return f"<h{level}>{escape(node.text or node.title or '')}</h{level}>"
        case "paragraph":
            return f"<p>{escape(node.text or '')}</p>"
        case "quote":
            return f"<blockquote>{escape(node.text or '')}</blockquote>"
        case "bullets":
            items = "".join(f"<li>{escape(i)}</li>" for i in node.items or [])
            label = f"<p><strong>{escape(node.title)}</strong></p>" if node.title else ""
            return f"{label}<ul>{items}</ul>" if items else ""
        case "post":
            if node.items:
                res = "".join(f"<p>{escape(i)}</p>" for i in node.items if i)
                if res:
                    return res
            return f"<p>{escape(node.text)}</p>" if node.text else ""
        case "callout":
            severity = node.severity or "info"
            title = escape(node.title or severity)
            body = f"<span>{escape(node.text)}</span>" if node.text else ""
            return f'<div class="callout {escape(severity)}"><strong>{title}</strong>{body}</div>'
        case "slide":
            items = "".join(f"<li>{escape(i)}</li>" for i in node.items or [])
            notes = f"<p><em>{escape(node.notes)}</em></p>" if node.notes else ""
            return f"<h3>{escape(node.title or 'Slide')}</h3><ul>{items}</ul>{notes}"
        case "panel":
            stats = "".join(f'<p class="stat">{escape(i)}</p>' for i in node.items or [])
            caption = f"<p>{escape(node.text)}</p>" if node.text else ""
            visual = f'<p class="visual">Visual: {escape(node.notes)}</p>' if node.notes else ""
            return (
                f'<section class="panel"><h3>{escape(node.title or "Panel")}</h3>'
                f"{stats}{caption}{visual}</section>"
            )
        case "scene":
            seconds = estimate_seconds(node.text or "")
            timing = f" · ~{round(seconds)} s" if seconds else ""
            narration = f'<p class="narration">{escape(node.text)}</p>' if node.text else ""
            overlays = "".join(
                f'<span class="overlay">{escape(i)}</span>' for i in node.items or []
            )
            visual = f'<p class="visual">Visuals: {escape(node.notes)}</p>' if node.notes else ""
            return (
                f'<section class="scene"><h3>{escape(node.title or "Scene")}{timing}</h3>'
                f"{narration}{overlays}{visual}</section>"
            )
        case "table":
            rows = "".join(
                "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>"
                for row in node.rows or []
            )
            return f"<table>{rows}</table>" if rows else ""
    return ""


def render(
    ir: ContentIR,
    *,
    include_citations: bool = False,
    citations: dict[str, str] | None = None,
    output_type: str = "",
    **_: object,
) -> str:
    # Consecutive panels share one grid, so an infographic brief reads as a layout.
    parts: list[str] = []
    panels: list[str] = []
    for node in ir.nodes:
        rendered = _node_html(node)
        if not rendered:
            continue
        if node.kind == "panel":
            panels.append(rendered)
            continue
        if panels:
            parts.append(f'<div class="panels">{"".join(panels)}</div>')
            panels = []
        parts.append(rendered)
    if panels:
        parts.append(f'<div class="panels">{"".join(panels)}</div>')
    body = "\n".join(parts)

    sources = ""
    if include_citations:
        used: list[str] = []
        for node in ir.nodes:
            for fid in node.fact_ids:
                if fid not in used:
                    used.append(fid)
        if used:
            items = "".join(f"<li>{escape((citations or {}).get(fid, fid))}</li>" for fid in used)
            sources = f'<div class="sources"><strong>Sources</strong><ul>{items}</ul></div>'

    heading = (
        f"<p><strong>Subject:</strong> {escape(ir.title)}</p>"
        if output_type == "email"
        else f"<h1>{escape(ir.title)}</h1>"
    )
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(ir.title)}</title><style>{CSS}</style></head>"
        f"<body>{heading}\n{body}\n{sources}</body></html>\n"
    )
