import type { ContentIR, IRNode } from '@/types/api'

type Field = 'title' | 'text' | 'items' | 'notes'

/** Every text field the part actually carries, so nothing is left uneditable. */
function fieldsOf(node: IRNode): Field[] {
  const fields: Field[] = []
  if (node.kind === 'heading') return [node.text != null ? 'text' : 'title']
  if (node.title != null) fields.push('title')
  if (node.text != null) fields.push('text')
  if (node.items != null) fields.push('items')
  if (node.notes != null) fields.push('notes')
  if (fields.length === 0) {
    if (node.kind === 'post' || node.kind === 'bullets' || node.kind === 'slide') {
      fields.push('items')
    } else {
      fields.push('text')
    }
  }
  return fields
}

const LABELS: Record<string, Partial<Record<Field, string>>> = {
  scene: { title: 'Scene name', text: 'Voice-over', items: 'On-screen text (one per line)', notes: 'Visual idea' },
  panel: { title: 'Section label', text: 'Caption', items: 'Key numbers (one per line)', notes: 'Design idea' },
  slide: { title: 'Slide title', items: 'Bullet points (one per line)', notes: 'Speaker notes' },
  heading: { text: 'Heading', title: 'Heading' },
  post: { items: 'Paragraphs (one per line)' },
  bullets: { items: 'List (one item per line)' },
  callout: { title: 'Highlight title', text: 'Highlight text' },
}

function labelFor(node: IRNode, field: Field): string {
  return LABELS[node.kind]?.[field] ?? { title: 'Title', text: 'Text', items: 'Lines', notes: 'Notes' }[field]
}

/** Edit the content part by part. Changes are saved as a new draft. */
export default function ContentEditor({
  draft,
  onChange,
}: {
  draft: ContentIR
  onChange: (ir: ContentIR) => void
}) {
  function patch(id: string, update: Partial<IRNode>) {
    onChange({ ...draft, nodes: draft.nodes.map((n) => (n.id === id ? { ...n, ...update } : n)) })
  }

  return (
    <div className="space-y-5">
      <label className="block">
        <span className="text-xs font-medium text-ink-400">Title</span>
        <input
          value={draft.title}
          onChange={(e) => onChange({ ...draft, title: e.target.value })}
          className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-lg font-semibold outline-none focus:border-brand-500"
        />
      </label>
      {draft.nodes.map((node) => (
        <div key={node.id} id={`ir-${node.id}`} className="space-y-2 rounded-xl border border-ink-200 p-3">
          {fieldsOf(node).map((field) => (
            <label key={field} className="block">
              <span className="text-xs font-medium text-ink-400">{labelFor(node, field)}</span>
              <textarea
                value={field === 'items' ? (node.items ?? []).join('\n') : (node[field] ?? '')}
                onChange={(e) =>
                  patch(
                    node.id,
                    field === 'items' ? { items: e.target.value.split('\n') } : { [field]: e.target.value },
                  )
                }
                rows={field === 'items' ? Math.max(2, node.items?.length ?? 0) : field === 'title' ? 1 : 3}
                className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-sm leading-relaxed outline-none focus:border-brand-500"
              />
            </label>
          ))}
          {node.kind === 'slide' && (
            <label className="block">
              <span className="text-xs font-medium text-ink-400">Slide Layout</span>
              <select
                value={node.layout || 'standard_bullet'}
                onChange={(e) => patch(node.id, { layout: e.target.value })}
                className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-1.5 text-xs outline-none focus:border-brand-500"
              >
                <option value="standard_bullet">Standard Bullets</option>
                <option value="two_column">Two-Column Split</option>
                <option value="process">Process Flow</option>
                <option value="timeline">Timeline</option>
                <option value="metrics">Key Metrics</option>
                <option value="comparison">Comparison</option>
                <option value="table">Data Table</option>
                <option value="section_divider">Section Divider</option>
                <option value="references">References</option>
              </select>
            </label>
          )}
          {node.kind === 'table' && (
            <p className="text-xs text-ink-400">Tables can be edited after downloading.</p>
          )}
        </div>
      ))}
    </div>
  )
}
