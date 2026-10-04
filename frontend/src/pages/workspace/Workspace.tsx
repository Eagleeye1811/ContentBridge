import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useOutletContext, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import { useAuth } from '@/lib/auth'
import { Badge } from '@/components/ui'
import { Icon } from '@/lib/icons'
import { FORMAT_GROUPS } from '@/lib/formats'
import { DOC_STATUS, sourceKind } from '@/lib/labels'
import type { Block, Catalog, Doc, Output } from '@/types/api'


export interface WorkspaceContext {
  doc: Doc
  blocks: Block[]
  catalog: Catalog
  outputs: Output[]
  reloadDoc: () => void
  reloadOutputs: () => void
}

export function useWorkspace(): WorkspaceContext {
  return useOutletContext<WorkspaceContext>()
}

/** Newest version of each (type, audience, language): older versions are history. */
export function latestOutputs(outputs: Output[]): Output[] {
  const seen = new Map<string, Output>()
  for (const o of outputs) {
    const key = `${o.type === 'social' ? 'linkedin' : o.type}|${o.audience}|${o.language}`
    const prev = seen.get(key)
    if (!prev || o.version > prev.version) seen.set(key, o)
  }
  return [...seen.values()].sort((a, b) => b.created_at.localeCompare(a.created_at))
}

export default function Workspace() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const [doc, setDoc] = useState<Doc | null>(null)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [outputs, setOutputs] = useState<Output[]>([])
  const [error, setError] = useState<string | null>(null)

  const reloadDoc = useCallback(() => {
    Promise.all([api.getDocument(id), api.listBlocks(id)])
      .then(([d, bs]) => {
        setDoc(d)
        setBlocks(bs)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load this source'))
  }, [id])

  const reloadOutputs = useCallback(() => {
    api.listOutputs(id).then(setOutputs).catch(() => setOutputs([]))
  }, [id])

  useEffect(() => {
    reloadDoc()
    reloadOutputs()
    api.catalog().then(setCatalog).catch(() => setCatalog(null))
  }, [reloadDoc, reloadOutputs])

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const o of latestOutputs(outputs)) {
      const key = o.type === 'social' ? 'linkedin' : o.type
      c[key] = (c[key] ?? 0) + 1
    }
    return c
  }, [outputs])

  if (error)
    return (
      <div className="mx-auto max-w-lg rounded-2xl border border-ink-200 bg-white p-8 text-center shadow-sm">
        <p className="text-base font-semibold text-ink-900">Source Not Found</p>
        <p className="mt-1 text-sm text-ink-600">This document may have been removed or the database was refreshed.</p>
        <div className="mt-6">
          <Link
            to="/sources"
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700"
          >
            <Icon name="document" className="h-4 w-4" />
            Go to Sources
          </Link>
        </div>
      </div>
    )

  const names = new Map(catalog.formats.map((f) => [f.key, f.name]))
  const status = DOC_STATUS[doc.status] ?? { label: doc.status, tone: 'neutral' as const }
  const context: WorkspaceContext = { doc, blocks, catalog, outputs, reloadDoc, reloadOutputs }

  return (
    <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="lg:sticky lg:top-20 lg:self-start">
        <Link
          to="/sources"
          className="mb-3 inline-flex items-center gap-1 text-sm text-ink-600 hover:text-ink-900"
        >
          <Icon name="back" />
          All sources
        </Link>
        <div className="mb-4 rounded-2xl border border-ink-200 bg-white p-3">
          <p className="truncate text-sm font-semibold" title={doc.filename}>
            {doc.filename}
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-xs text-ink-400">{sourceKind(doc.mime)}</span>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
        </div>

        <nav className="space-y-4 text-sm">
          <Group>
            <Item to={`/sources/${id}`} end icon="document" label="Document" />
            <Item to={`/sources/${id}/facts`} icon="facts" label="Key facts" />
          </Group>
          {FORMAT_GROUPS.map((g) => ({
            ...g,
            keys: g.keys.filter((k) => names.has(k) && (user?.allowed_types ?? []).includes(k)),
          }))
            .filter((g) => g.keys.length > 0)
            .map((g) => (
            <Group key={g.label} label={g.label}>
              {g.keys
                .map((k) => (
                  <Item
                    key={k}
                    to={`/formats/${k}?source=${id}`}
                    icon={k}
                    label={names.get(k) ?? k}
                    count={counts[k]}
                  />
                ))}
            </Group>
          ))}
        </nav>
      </aside>

      <section className="min-w-0">
        <Outlet context={context} />
      </section>
    </div>
  )
}

function Group({ label, children }: { label?: string; children: React.ReactNode }) {
  return (
    <div>
      {label && (
        <p className="mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider text-ink-400">
          {label}
        </p>
      )}
      <div className="space-y-0.5">{children}</div>
    </div>
  )
}

function Item({
  to,
  icon,
  label,
  count,
  end,
}: {
  to: string
  icon: string
  label: string
  count?: number
  end?: boolean
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-lg px-3 py-2 transition ${
          isActive
            ? 'bg-white font-medium text-ink-900 shadow-sm ring-1 ring-ink-200'
            : 'text-ink-600 hover:bg-white hover:text-ink-900'
        }`
      }
    >
      <Icon name={icon} />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {count ? (
        <span className="rounded-full bg-ink-100 px-1.5 text-xs text-ink-600">{count}</span>
      ) : null}
    </NavLink>
  )
}
