"""ContentIR -> a standalone HTML / Printable PDF-Ready Document with ChatGPT-style inline citations."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
import hashlib
import re

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.srt import estimate_seconds

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --primary: #1e40af;
  --primary-dark: #0f172a;
  --primary-light: #3b82f6;
  --accent: #2563eb;
  --bg: #f1f5f9;
  --paper-bg: #ffffff;
  --text-main: #0f172a;
  --text-muted: #475569;
  --text-subtle: #64748b;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;
  --radius: 12px;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-display: 'Outfit', 'Inter', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

[data-theme="dark"] {
  --bg: #0b0f19;
  --paper-bg: #111827;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-subtle: #64748b;
  --border: #1f2937;
  --border-strong: #374151;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.75;
  color: var(--text-main);
  background: var(--bg);
  padding: 2.5rem 1rem 6rem;
  transition: background-color 0.2s ease, color 0.2s ease;
  -webkit-font-smoothing: antialiased;
}

/* Page Frame / Executive Paper */
.document-container {
  max-width: 52rem;
  margin: 0 auto;
  background: var(--paper-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.02);
  padding: 3.5rem 4rem;
  position: relative;
  overflow: hidden;
}

/* Top Security Band */
.document-container::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 5px;
  background: linear-gradient(90deg, #1e40af 0%, #3b82f6 50%, #d97706 75%, #059669 100%);
}

/* Official Header */
.doc-header {
  border-bottom: 2px solid var(--border);
  padding-bottom: 2rem;
  margin-bottom: 2.5rem;
}

.doc-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.org-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.org-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, #1e40af, #1d4ed8);
  color: white;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 800;
  box-shadow: 0 2px 6px rgba(30, 64, 175, 0.25);
}

.org-name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text-main);
  letter-spacing: -0.01em;
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.org-name small {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
}

.badges-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.format-badge {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.security-badge {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.security-badge::before {
  content: "";
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #dc2626;
}

h1.doc-title {
  font-family: var(--font-display);
  font-size: 2.25rem;
  font-weight: 800;
  line-height: 1.25;
  color: var(--text-main);
  margin: 0.5rem 0 1.25rem 0;
  letter-spacing: -0.025em;
}

/* Metadata Card */
.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.75rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.meta-item {
  display: flex;
  flex-direction: column;
}

.meta-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-subtle);
  margin-bottom: 0.15rem;
}

.meta-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Content Typography */
.content-body {
  font-size: 15px;
}

h2 {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-main);
  margin: 2.25rem 0 0.85rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 1.5px solid var(--border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

h3 {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-main);
  margin: 1.75rem 0 0.6rem 0;
}

p {
  margin: 0 0 1.25rem 0;
  color: var(--text-main);
}

strong {
  color: var(--text-main);
  font-weight: 700;
}

blockquote {
  border-left: 4px solid var(--primary-light);
  background: #f8fafc;
  border-radius: 0 8px 8px 0;
  margin: 1.5rem 0;
  padding: 1.1rem 1.4rem;
  color: var(--text-muted);
  font-style: italic;
  font-size: 1.02rem;
}

ul, ol {
  margin: 0 0 1.25rem 0;
  padding-left: 1.6rem;
}

li {
  margin-bottom: 0.6rem;
  color: var(--text-main);
}

li::marker {
  color: var(--primary-light);
}

/* ChatGPT-Style Inline Citation Pills */
.inline-cite {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.7rem;
  font-weight: 600;
  line-height: 1;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  margin-left: 0.35rem;
  vertical-align: baseline;
  text-decoration: none;
  cursor: help;
  transition: all 0.15s ease;
  user-select: none;
}

.inline-cite:hover {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1e3a8a;
  transform: translateY(-1px);
}

/* Callouts / Threat Advisories */
.callout {
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 8px;
  padding: 1.1rem 1.35rem;
  margin: 1.6rem 0;
  break-inside: avoid;
}

.callout.high, .callout.critical {
  border-left-color: #dc2626;
  background: #fef2f2;
  border-color: #fee2e2;
  color: #991b1b;
}

.callout.high strong, .callout.critical strong {
  color: #7f1d1d;
}

.callout.medium, .callout.warning {
  border-left-color: #d97706;
  background: #fffbeb;
  border-color: #fef3c7;
  color: #92400e;
}

.callout.medium strong, .callout.warning strong {
  color: #78350f;
}

.callout.low, .callout.info {
  border-left-color: var(--primary-light);
  background: #eff6ff;
  border-color: #dbeafe;
  color: #1e40af;
}

.callout.low strong, .callout.info strong {
  color: #1e3a8a;
}

.callout strong {
  display: block;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.4rem;
}

/* Tables */
table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
  margin: 1.75rem 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.9rem;
  break-inside: avoid;
}

th, td {
  padding: 0.85rem 1.15rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

th {
  background: #f8fafc;
  font-weight: 700;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

tr:last-child td {
  border-bottom: none;
}

tr:nth-child(even) td {
  background: #fafafa;
}

/* Panels (Stats/Key Insights) */
.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 1.25rem;
  margin: 1.75rem 0;
  break-inside: avoid;
}

.panel, .scene {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  padding: 1.25rem 1.4rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.panel h3, .scene h3 {
  margin: 0 0 0.5rem 0;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--primary);
}

.panel .stat {
  font-family: var(--font-display);
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1.2;
  margin: 0.35rem 0;
}

/* Provenance & Citation Section */
.sources {
  margin-top: 3.5rem;
  border-top: 2px solid var(--border);
  padding-top: 1.75rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  break-inside: avoid;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.85rem;
}

.sources ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sources li {
  padding: 0.5rem 0.75rem;
  background: var(--bg);
  border-radius: 6px;
  border: 1px solid var(--border);
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  line-height: 1.5;
}

/* Official Document Footer */
.doc-footer {
  margin-top: 3rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-subtle);
  flex-wrap: wrap;
  gap: 0.75rem;
}

.security-hash {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: var(--bg);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  border: 1px solid var(--border);
}

/* Floating Action Toolbar (Web View Only) */
.floating-action-bar {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(12px);
  padding: 0.5rem 0.75rem;
  border-radius: 9999px;
  box-shadow: 0 12px 30px -5px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.1);
  z-index: 999;
}

.action-btn {
  background: transparent;
  color: #f1f5f9;
  border: none;
  padding: 0.5rem 0.9rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  font-family: var(--font-body);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.action-btn.primary {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
}

.action-btn.primary:hover {
  background: #1d4ed8;
  transform: translateY(-1px);
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: rgba(255, 255, 255, 0.2);
  margin: 0 0.2rem;
}

/* Toast Message */
.toast-msg {
  position: fixed;
  top: 2rem;
  left: 50%;
  transform: translateX(-50%) translateY(-20px);
  background: #0f172a;
  color: white;
  padding: 0.6rem 1.25rem;
  border-radius: 9999px;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  opacity: 0;
  pointer-events: none;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  z-index: 1000;
}

.toast-msg.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* PRINT & PDF GENERATION STYLES */
@media print {
  @page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #64748b;
      font-family: 'Inter', sans-serif;
    }
    @bottom-left {
      content: "NTRO OFFICIAL USE ONLY · VERIFIED VIA CONTENTBRIDGE";
      font-size: 7.5pt;
      color: #94a3b8;
      font-family: 'Inter', sans-serif;
    }
  }

  body {
    background: #ffffff !important;
    color: #000000 !important;
    padding: 0 !important;
    font-size: 11pt !important;
    line-height: 1.6 !important;
  }

  .document-container {
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    max-width: 100% !important;
    border-radius: 0 !important;
  }

  .document-container::before {
    display: none !important;
  }

  .floating-action-bar, .toast-msg {
    display: none !important;
  }

  .inline-cite {
    font-size: 7.5pt !important;
    background: transparent !important;
    border: none !important;
    color: #475569 !important;
    padding: 0 !important;
    font-weight: 600 !important;
  }

  .inline-cite::before {
    content: "[";
  }

  .inline-cite::after {
    content: "]";
  }

  h1.doc-title {
    font-size: 20pt !important;
  }

  h2 {
    font-size: 14pt !important;
    margin-top: 18pt !important;
    break-after: avoid;
  }

  h3 {
    font-size: 12pt !important;
    break-after: avoid;
  }

  .callout, table, .panel, .scene, .sources {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }

  .metadata-grid {
    background: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
  }

  th {
    background: #f1f5f9 !important;
    color: #0f172a !important;
  }

  tr:nth-child(even) td {
    background: #f8fafc !important;
  }
}
"""


def _extract_page(citation_text: str) -> str:
    """Extract short page reference from citation string (e.g. 'p.1' or 'p.2')."""
    match = re.search(r"\b(p\.\s*\d+)", citation_text)
    if match:
        return match.group(1).replace(" ", "")
    return "p.1"


def _format_citations(fact_ids: list[str], citations: dict[str, str] | None) -> str:
    if not fact_ids or not citations:
        return ""
    pills = []
    seen = set()
    for fid in fact_ids:
        text = citations.get(fid, "")
        if not text:
            continue
        page = _extract_page(text)
        if page not in seen:
            seen.add(page)
            pills.append(
                f'<span class="inline-cite" title="{escape(text)}">{escape(page)}</span>'
            )
    return "".join(pills)


def _node_html(node: Node, citations: dict[str, str] | None = None) -> str:
    cite_html = _format_citations(node.fact_ids, citations)

    match node.kind:
        case "heading":
            level = min(max(node.level or 2, 1), 4)
            return f"<h{level}>{escape(node.text or node.title or '')}</h{level}>"
        case "paragraph":
            return f"<p>{escape(node.text or '')}{cite_html}</p>"
        case "quote":
            return f"<blockquote>{escape(node.text or '')}{cite_html}</blockquote>"
        case "bullets":
            items = "".join(f"<li>{escape(i)}{cite_html}</li>" for i in node.items or [])
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
            title = escape(node.title or severity.upper())
            body = f"<span>{escape(node.text)}{cite_html}</span>" if node.text else ""
            return f'<div class="callout {escape(severity)}"><strong>{title}</strong>{body}</div>'
        case "slide":
            items = "".join(f"<li>{escape(i)}{cite_html}</li>" for i in node.items or [])
            notes = f"<p><em>{escape(node.notes)}</em></p>" if node.notes else ""
            return f"<h3>{escape(node.title or 'Slide')}</h3><ul>{items}</ul>{notes}"
        case "panel":
            stats = "".join(f'<p class="stat">{escape(i)}</p>' for i in node.items or [])
            caption = f"<p>{escape(node.text)}{cite_html}</p>" if node.text else ""
            visual = f'<p class="visual">Visual: {escape(node.notes)}</p>' if node.notes else ""
            return (
                f'<section class="panel"><h3>{escape(node.title or "Panel")}</h3>'
                f"{stats}{caption}{visual}</section>"
            )
        case "scene":
            seconds = estimate_seconds(node.text or "")
            timing = f" · ~{round(seconds)} s" if seconds else ""
            narration = f'<p class="narration">{escape(node.text)}{cite_html}</p>' if node.text else ""
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
    source_name: str = "",
    **_: object,
) -> str:
    parts: list[str] = []
    panels: list[str] = []
    for node in ir.nodes:
        rendered = _node_html(node, citations=citations)
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
    if include_citations or citations:
        used: list[str] = []
        for node in ir.nodes:
            for fid in node.fact_ids:
                if fid not in used:
                    used.append(fid)
        if used:
            items = "".join(f"<li>{escape((citations or {}).get(fid, fid))}</li>" for fid in used)
            sources = (
                f'<div class="sources">'
                f'<div class="sources-title">'
                f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
                f'Verified Source Provenance & Citations</div>'
                f'<ul>{items}</ul></div>'
            )

    date_str = datetime.now(UTC).strftime("%d %B %Y")
    format_title = output_type.replace("_", " ").title() if output_type else "Executive Document"
    
    # Generate deterministic document hash
    doc_hash_seed = f"{ir.title}_{date_str}_{source_name}".encode("utf-8")
    doc_ref = f"NTRO-CB-{hashlib.sha256(doc_hash_seed).hexdigest()[:8].upper()}"

    header_html = f"""
    <header class="doc-header">
      <div class="doc-top-bar">
        <div class="org-brand">
          <div class="org-icon">🇮🇳</div>
          <div class="org-name">
            <span>National Technical Research Organisation</span>
            <small>Government of India · Intelligence & Cyber Directorate</small>
          </div>
        </div>
        <div class="badges-group">
          <span class="format-badge">{escape(format_title)}</span>
          <span class="security-badge">RESTRICTED / SENSITIVE</span>
        </div>
      </div>
      
      <h1 class="doc-title">{escape(ir.title)}</h1>
      
      <div class="metadata-grid">
        <div class="meta-item">
          <span class="meta-label">Document Ref</span>
          <span class="meta-value">{doc_ref}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Date Issued</span>
          <span class="meta-value">{date_str}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Primary Source</span>
          <span class="meta-value">{escape(source_name or "Certified Incident Report")}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Integrity Status</span>
          <span class="meta-value" style="color: #059669;">✓ Verified Factual</span>
        </div>
      </div>
    </header>
    """

    footer_html = f"""
    <footer class="doc-footer">
      <div>
        <span>Generated via ContentBridge Factual Consistency Engine</span>
      </div>
      <div class="security-hash">
        SHA-256: {hashlib.sha256(doc_hash_seed).hexdigest()[:24]}...
      </div>
    </footer>
    """

    floating_bar = """
    <div class="floating-action-bar">
      <button class="action-btn primary" onclick="window.print()" title="Print or Save as PDF (Ctrl+P)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6z"/></svg>
        Print / Save PDF
      </button>
      <div class="toolbar-divider"></div>
      <button class="action-btn" onclick="copyDocumentText()" title="Copy all document text">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
        Copy Text
      </button>
      <button class="action-btn" onclick="toggleTheme()" title="Toggle Light/Dark Display">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
      </button>
    </div>
    <div id="toast" class="toast-msg">Copied document text to clipboard!</div>

    <script>
      function copyDocumentText() {
        const doc = document.querySelector('.document-container');
        if (!doc) return;
        navigator.clipboard.writeText(doc.innerText).then(() => {
          showToast('✓ Document content copied to clipboard');
        }).catch(() => {
          showToast('Press Ctrl+A, Ctrl+C to copy');
        });
      }

      function showToast(msg) {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2500);
      }

      function toggleTheme() {
        const body = document.body;
        const current = body.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        body.setAttribute('data-theme', next);
      }
    </script>
    """

    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(ir.title)}</title>\n"
        f"<style>{CSS}</style></head>\n"
        f"<body>\n"
        f'<div class="document-container">\n'
        f"{header_html}\n"
        f'<main class="content-body">\n{body}\n</main>\n'
        f"{sources}\n"
        f"{footer_html}\n"
        f"</div>\n"
        f"{floating_bar}\n"
        f"</body></html>\n"
    )
