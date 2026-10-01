import { FORMAT_GROUPS } from '@/lib/formats'
import { Icon } from '@/lib/icons'
import { formatLabel } from '@/lib/labels'

/** Tick the output types a role may create, grouped like the navbar. */
export default function OutputPicker({
  value,
  onChange,
}: {
  value: string[]
  onChange: (types: string[]) => void
}) {
  function toggle(key: string) {
    onChange(value.includes(key) ? value.filter((k) => k !== key) : [...value, key])
  }
  return (
    <div className="space-y-3">
      {FORMAT_GROUPS.map((g) => (
        <div key={g.label}>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-400">
            {g.label}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {g.keys.map((k) => {
              const on = value.includes(k)
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => toggle(k)}
                  aria-pressed={on}
                  className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm transition ${
                    on
                      ? 'bg-brand-600 text-white'
                      : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
                  }`}
                >
                  <Icon name={k} className="h-3.5 w-3.5" />
                  {formatLabel(k)}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Small chips showing what a role can create. */
export function OutputChips({ types }: { types: string[] }) {
  if (types.length === 0) return <span className="text-xs text-ink-400">No outputs</span>
  return (
    <div className="flex flex-wrap gap-1">
      {types.map((k) => (
        <span
          key={k}
          className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-1.5 py-0.5 text-xs text-brand-600"
        >
          <Icon name={k} className="h-3 w-3" />
          {formatLabel(k)}
        </span>
      ))}
    </div>
  )
}
