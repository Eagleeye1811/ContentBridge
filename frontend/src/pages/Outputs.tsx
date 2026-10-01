import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import OutputGrid from '@/components/OutputGrid'
import { Button, Empty, PageHeader, Select } from '@/components/ui'
import { Icon } from '@/lib/icons'
import { formatLabel } from '@/lib/labels'
import { FORMAT_GROUPS, latestOnly, typeOf } from '@/lib/formats'
import type { Catalog, OutputListItem } from '@/types/api'

/** Everything you have created, from every source, in one place. */
export default function Outputs() {
  const [outputs, setOutputs] = useState<OutputListItem[] | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [format, setFormat] = useState('all')
  const [source, setSource] = useState('all')
  const [query, setQuery] = useState('')
  const [allVersions, setAllVersions] = useState(false)

  useEffect(() => {
    api
      .listAllOutputs()
      .then(setOutputs)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load outputs'))
    api.catalog().then(setCatalog).catch(() => setCatalog(null))
  }, [])

  const base = useMemo(
    () => (outputs ? (allVersions ? outputs : latestOnly(outputs)) : []),
    [outputs, allVersions],
  )

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const o of base) c[typeOf(o)] = (c[typeOf(o)] ?? 0) + 1
    return c
  }, [base])

  const sources = useMemo(() => {
    const m = new Map<string, string>()
    for (const o of outputs ?? []) m.set(o.document_id, o.document_name)
    return [...m.entries()]
  }, [outputs])

  const visible = base.filter((o) => {
    if (format !== 'all' && typeOf(o) !== format) return false
    if (source !== 'all' && o.document_id !== source) return false
    const q = query.trim().toLowerCase()
    if (q && !`${o.title} ${o.document_name} ${formatLabel(typeOf(o))}`.toLowerCase().includes(q))
      return false
    return true
  })

  const formatOrder = FORMAT_GROUPS.flatMap((g) => g.keys).filter((k) => counts[k])

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Outputs"
        subtitle="Everything you have created, from all your sources."
        icon={<Icon name="spark" className="h-5 w-5" />}
      />

      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {outputs === null || !catalog ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : outputs.length === 0 ? (
        <Empty title="Nothing created yet" icon={<Icon name="spark" />}>
          <p>Open a source and pick a format, such as Presentation or Video, to create your first one.</p>
          <div className="mt-4">
            <Link to="/sources">
              <Button>Go to sources</Button>
            </Link>
          </div>
        </Empty>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-1.5">
            <Pill active={format === 'all'} onClick={() => setFormat('all')}>
              All <Count n={base.length} />
            </Pill>
            {formatOrder.map((k) => (
              <Pill key={k} active={format === k} onClick={() => setFormat(k)}>
                <Icon name={k} className="h-3.5 w-3.5" />
                {formatLabel(k)} <Count n={counts[k]} />
              </Pill>
            ))}
          </div>

          <div className="mb-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_14rem_auto] sm:items-center">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title or source"
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <Select
              value={source}
              onChange={setSource}
              options={[
                { key: 'all', label: 'All sources' },
                ...sources.map(([id, name]) => ({ key: id, label: name })),
              ]}
            />
            <label className="flex items-center gap-2 whitespace-nowrap text-sm text-ink-600">
              <input
                type="checkbox"
                checked={allVersions}
                onChange={(e) => setAllVersions(e.target.checked)}
                className="accent-brand-600"
              />
              Show older versions
            </label>
          </div>

          {visible.length === 0 ? (
            <Empty title="No matches">Try a different type, source or search.</Empty>
          ) : (
            <OutputGrid outputs={visible} showFormat />
          )}
        </>
      )}
    </div>
  )
}

function Pill({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition ${
        active
          ? 'bg-ink-900 text-white'
          : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
      }`}
    >
      {children}
    </button>
  )
}

function Count({ n }: { n: number }) {
  return <span className="text-xs opacity-60">{n}</span>
}
