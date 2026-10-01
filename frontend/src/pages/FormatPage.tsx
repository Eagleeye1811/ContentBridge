import { useCallback, useEffect, useMemo, useState } from 'react'
import { Navigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '@/api/client'
import CreateForm from '@/components/CreateForm'
import OutputGrid from '@/components/OutputGrid'
import { Button, Empty, Notice } from '@/components/ui'
import { useAuth } from '@/lib/auth'
import { FORMAT_KEYS, latestOnly, typeOf } from '@/lib/formats'
import { Icon } from '@/lib/icons'
import type { Catalog, Doc, OutputListItem } from '@/types/api'

/**
 * One page per output type, read top to bottom: what it is, a create panel
 * (open when there is nothing yet, folded away otherwise) and the ones made.
 */
export default function FormatPage() {
  const { format: key = '' } = useParams()
  const [params] = useSearchParams()
  const { user } = useAuth()
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [sources, setSources] = useState<Doc[] | null>(null)
  const [outputs, setOutputs] = useState<OutputListItem[] | null>(null)
  const [fresh, setFresh] = useState<string[]>([])
  const [creating, setCreating] = useState<boolean | null>(null)

  const reload = useCallback(() => {
    api.listAllOutputs().then(setOutputs).catch(() => setOutputs([]))
  }, [])

  useEffect(() => {
    api.catalog().then(setCatalog).catch(() => setCatalog(null))
    api.listDocuments().then(setSources).catch(() => setSources([]))
    reload()
  }, [reload])

  // Each type starts fresh: no highlight, and the panel decides its own default.
  useEffect(() => {
    setFresh([])
    setCreating(null)
  }, [key])

  const mine = useMemo(
    () => (outputs ? latestOnly(outputs).filter((o) => typeOf(o) === key) : []),
    [outputs, key],
  )

  if (!FORMAT_KEYS.includes(key)) return <Navigate to="/outputs" replace />
  if (!catalog || !sources || !outputs) return <p className="text-sm text-ink-400">Loading…</p>

  const format = catalog.formats.find((f) => f.key === key)
  if (!format) return <Navigate to="/outputs" replace />

  const permitted = user?.allowed_types.includes(format.key) ?? false
  const name = format.name.toLowerCase()
  const plural = name.endsWith('y') ? `${name.slice(0, -1)}ies` : `${name}s`
  // Open by default when nothing exists yet, or when a source was handed over.
  const open = permitted && (creating ?? (mine.length === 0 || params.has('source')))

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div className="flex flex-wrap items-center gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-brand-600">
          <Icon name={format.key} className="h-6 w-6" />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{format.name}</h1>
          <p className="text-sm text-ink-600">{format.description}</p>
        </div>
        {permitted && !open && (
          <Button onClick={() => setCreating(true)}>
            <Icon name="plus" />
            New {name}
          </Button>
        )}
      </div>

      {!permitted && (
        <Notice tone="warn">
          {format.name} is not part of your role
          {user?.job_role ? ` (${user.job_role.name})` : ''}. Ask your administrator if you need
          it.
        </Notice>
      )}

      {open && (
        <CreateForm
          key={format.key}
          format={format}
          sources={sources}
          languages={Object.keys(catalog.languages)}
          initialSource={params.get('source') ?? undefined}
          onCancel={mine.length > 0 ? () => setCreating(false) : undefined}
          onCreated={(ids) => {
            setFresh(ids)
            setCreating(false)
            reload()
          }}
        />
      )}

      <section>
        <div className="mb-4 flex items-baseline gap-2">
          <h2 className="text-lg font-semibold">Your {plural}</h2>
          <span className="text-sm text-ink-400">{mine.length}</span>
        </div>
        {mine.length === 0 ? (
          <Empty title={`No ${plural} yet`} icon={<Icon name={format.key} />}>
            Fill in the panel above and press Create. It will appear here.
          </Empty>
        ) : (
          <OutputGrid outputs={mine} highlight={fresh} />
        )}
      </section>
    </div>
  )
}
