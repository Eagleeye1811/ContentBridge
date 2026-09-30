import type { ContentIR, Fact, IRNode } from '@/types/api'

const SEVERITY_TONE: Record<string, string> = {
  critical: 'border-red-300 bg-red-50',
  high: 'border-orange-300 bg-orange-50',
  medium: 'border-amber-300 bg-amber-50',
  low: 'border-blue-300 bg-blue-50',
  info: 'border-ink-200 bg-ink-50',
}

interface Props {
  ir: ContentIR
  facts: Map<string, Fact>
  selectedFactId: string | null
  onSelectFact: (factId: string) => void
}

/** Renders ContentIR with a citation chip on every attributable node. */
export default function ContentIRView({ ir, facts, selectedFactId, onSelectFact }: Props) {
  return (
    <article className="space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">{ir.title}</h1>
      {ir.nodes.map((node) => (
        <section key={node.id} id={`ir-${node.id}`} className="scroll-mt-4">
          <NodeBody node={node} />
          <Citations
            node={node}
            facts={facts}
            selectedFactId={selectedFactId}
            onSelectFact={onSelectFact}
          />
        </section>
      ))}
    </article>
  )
}

function NodeBody({ node }: { node: IRNode }) {
  switch (node.kind) {
    case 'heading': {
      const level = Math.min(Math.max(node.level ?? 2, 1), 4)
      const size = level <= 1 ? 'text-lg' : level === 2 ? 'text-base' : 'text-sm'
      return <h2 className={`${size} font-semibold`}>{node.text ?? node.title}</h2>
    }
    case 'paragraph':
      return <p className="text-sm leading-relaxed">{node.text}</p>
    case 'quote':
      return (
        <blockquote className="border-l-2 border-ink-200 pl-3 text-sm italic text-ink-600">
          {node.text}
        </blockquote>
      )
    case 'bullets':
    case 'post':
      return (
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {(node.items ?? []).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )
    case 'callout':
      return (
        <div className={`rounded-lg border px-3 py-2 ${SEVERITY_TONE[node.severity ?? 'info']}`}>
          <p className="text-sm font-semibold">{node.title ?? node.severity}</p>
          {node.text && <p className="mt-0.5 text-sm">{node.text}</p>}
        </div>
      )
    case 'slide':
      return (
        <div className="rounded-lg border border-ink-200 bg-white p-3">
          <p className="text-sm font-semibold">{node.title}</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
            {(node.items ?? []).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
          {node.notes && <p className="mt-2 text-xs italic text-ink-400">{node.notes}</p>}
        </div>
      )
    case 'table':
      return (
        <table className="w-full border-collapse text-sm">
          <tbody>
            {(node.rows ?? []).map((row, r) => (
              <tr key={r} className={r === 0 ? 'bg-ink-50 font-medium' : ''}>
                {row.map((cell, c) => (
                  <td key={c} className="border border-ink-200 px-2 py-1">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )
  }
}

function Citations({ node, facts, selectedFactId, onSelectFact }: Omit<Props, 'ir'> & { node: IRNode }) {
  if (!node.fact_ids.length) return null
  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {node.fact_ids.map((id) => {
        const fact = facts.get(id)
        const evidence = fact?.evidence[0]
        const selected = id === selectedFactId
        return (
          <button
            key={id}
            onClick={() => onSelectFact(id)}
            title={fact?.statement ?? 'Unresolved citation'}
            className={`rounded border px-1.5 py-0.5 font-mono text-xs transition ${
              selected
                ? 'border-amber-400 bg-amber-100 text-amber-800'
                : fact
                  ? 'border-ink-200 bg-ink-50 text-ink-600 hover:border-brand-500 hover:text-brand-600'
                  : 'border-red-300 bg-red-50 text-red-700'
            }`}
          >
            {fact
              ? `${fact.canonical_value ?? fact.key.slice(0, 14)}${
                  evidence ? ` · p${evidence.page_no}` : ''
                }`
              : 'unresolved'}
          </button>
        )
      })}
    </div>
  )
}
