import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { ConsistencyReport, Doc, MatrixCell } from '@/types/api'

export default function ConsistencyMatrix({ doc }: { doc: Doc }) {
  const [report, setReport] = useState<ConsistencyReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hover, setHover] = useState<MatrixCell | null>(null)

  const load = useCallback(() => {
    api
      .consistency(doc.id)
      .then(setReport)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : 'Could not load consistency report'),
      )
  }, [doc.id])

  useEffect(load, [load])

  if (error) return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
  if (!report) return <p className="text-sm text-ink-400">Checking consistency…</p>

  if (report.outputs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-10 text-center">
        <p className="text-sm font-medium">Nothing to compare yet</p>
        <p className="mt-1 text-sm text-ink-600">
          Generate at least one output and its figures will be checked against the Source of Truth.
        </p>
      </div>
    )
  }

  const label = (id: string) => {
    const o = report.outputs.find((x) => x.id === id)
    return o ? `${o.type} · ${o.language}` : 'output'
  }
  const mismatched = report.rows.filter((r) => r.has_mismatch)
  const openIssues = report.issues.filter((i) => i.status === 'open')

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm">
        <span className="font-medium">
          {report.rows.length} facts × {report.outputs.length} outputs
        </span>
        {mismatched.length > 0 ? (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            {mismatched.length} mismatch{mismatched.length === 1 ? '' : 'es'}
          </span>
        ) : (
          <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
            all outputs agree with the source
          </span>
        )}
        {report.unsourced.length > 0 && (
          <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            {report.unsourced.length} unsourced figure{report.unsourced.length === 1 ? '' : 's'}
          </span>
        )}
        <span className="ml-auto text-xs text-ink-400">
          Deterministic — no model involved, so it cannot flake.
        </span>
      </div>

      <div className="overflow-x-auto rounded-xl border border-ink-200 bg-white">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-ink-200 bg-ink-50 text-left">
              <th className="px-3 py-2 font-medium">Fact</th>
              <th className="px-3 py-2 font-medium">Source</th>
              {report.outputs.map((o) => (
                <th key={o.id} className="px-3 py-2 font-medium whitespace-nowrap">
                  {o.type}
                  <span className="ml-1 font-normal text-ink-400">
                    {o.language} v{o.version}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.rows.map((row) => {
              const cells = new Map(row.cells.map((c) => [c.output_id, c]))
              return (
                <tr
                  key={row.fact_id}
                  className={`border-b border-ink-200 last:border-0 ${
                    row.has_mismatch ? 'bg-red-50/50' : ''
                  }`}
                >
                  <td className="max-w-[22rem] px-3 py-2" title={row.statement}>
                    <span className="block truncate text-ink-900">{row.statement}</span>
                    <span className="text-xs text-ink-400">{row.key}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs font-semibold">
                    {row.expected}
                    {row.unit === 'percent' ? '%' : ''}
                  </td>
                  {report.outputs.map((o) => {
                    const cell = cells.get(o.id)
                    return (
                      <td
                        key={o.id}
                        className="px-3 py-2"
                        onMouseEnter={() => cell && setHover(cell)}
                      >
                        {!cell || cell.stated === null ? (
                          <span className="text-ink-400">—</span>
                        ) : cell.agrees ? (
                          <span className="font-mono text-xs text-emerald-700">
                            {cell.stated} ✓
                          </span>
                        ) : (
                          <span className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-xs font-semibold text-red-700">
                            {cell.stated} ✗
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {hover && (
        <p className="rounded-lg bg-ink-50 px-3 py-2 text-xs text-ink-600">
          <span className="font-medium">{label(hover.output_id)}:</span> {hover.snippet}
        </p>
      )}

      {report.unsourced.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm font-semibold text-amber-900">Figures with no source</p>
          <p className="mt-0.5 text-xs text-amber-800">
            These numbers appear in an output but in no fact. The system flags them rather than
            changing them.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {report.unsourced.map((u, i) => (
              <li key={i} className="flex gap-2">
                <span className="rounded bg-white px-1.5 py-0.5 font-mono text-xs font-semibold text-amber-900">
                  {u.value}
                </span>
                <span className="text-xs text-ink-600">
                  {label(u.output_id)} — {u.snippet}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {openIssues.length > 0 && (
        <div className="rounded-xl border border-ink-200 bg-white p-3">
          <p className="text-sm font-semibold">Open issues</p>
          <ul className="mt-2 space-y-2">
            {openIssues.map((issue) => (
              <li key={issue.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                    issue.severity === 'high'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {issue.kind.replace('_', ' ')}
                </span>
                <span className="text-ink-600">
                  expected {issue.expected_value ?? '—'}, saw{' '}
                  {Object.entries(issue.observed)
                    .map(([oid, v]) => `${label(oid)}: ${v}`)
                    .join(', ')}
                </span>
                <span className="ml-auto flex gap-1">
                  <button
                    onClick={() => api.updateIssue(issue.id, 'accepted').then(load)}
                    className="rounded border border-ink-200 px-2 py-0.5 text-xs hover:border-ink-400"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => api.updateIssue(issue.id, 'resolved').then(load)}
                    className="rounded border border-ink-200 px-2 py-0.5 text-xs hover:border-ink-400"
                  >
                    Resolve
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
