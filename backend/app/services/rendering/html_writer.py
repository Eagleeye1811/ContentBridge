"""ContentIR -> a standalone HTML document."""

from __future__ import annotations

from html import escape

from app.schemas.content_ir import ContentIR, Node

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
.sources { margin-top: 2.5rem; border-top: 1px solid #e3e6ec; padding-top: 1rem;
           font-size: .85rem; color: #4a5468; }
@media (prefers-color-scheme: dark) {
  body { background: #12151c; color: #e8eaef; }
  td, th { border-color: #2a3040; } tr:first-child td { background: #1b2030; }
  blockquote, .sources { border-color: #2a3040; color: #98a1b3; }
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
        case "bullets" | "post":
            items = "".join(f"<li>{escape(i)}</li>" for i in node.items or [])
            return f"<ul>{items}</ul>" if items else ""
        case "callout":
            severity = node.severity or "info"
            title = escape(node.title or severity)
            body = f"<span>{escape(node.text)}</span>" if node.text else ""
            return f'<div class="callout {escape(severity)}"><strong>{title}</strong>{body}</div>'
        case "slide":
            items = "".join(f"<li>{escape(i)}</li>" for i in node.items or [])
            notes = f"<p><em>{escape(node.notes)}</em></p>" if node.notes else ""
            return f"<h3>{escape(node.title or 'Slide')}</h3><ul>{items}</ul>{notes}"
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
    **_: object,
) -> str:
    body = "\n".join(filter(None, (_node_html(n) for n in ir.nodes)))

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

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(ir.title)}</title><style>{CSS}</style></head>"
        f"<body><h1>{escape(ir.title)}</h1>\n{body}\n{sources}</body></html>\n"
    )
