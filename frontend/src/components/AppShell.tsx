import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '@/api/client'
import { useAuth } from '@/lib/auth'
import { latestOnly, typeOf } from '@/lib/formats'
import { Icon } from '@/lib/icons'
import { formatLabel } from '@/lib/labels'

/** The output types, grouped into the navbar's two menus. */
const MENUS: { label: string; icon: string; keys: string[] }[] = [
  {
    label: 'Documents',
    icon: 'summary',
    keys: ['advisory', 'summary', 'report', 'email', 'press_release'],
  },
  { label: 'Media', icon: 'ppt', keys: ['ppt', 'linkedin', 'twitter', 'infographic', 'video'] },
]

const itemClass = (active: boolean) =>
  `flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 transition ${
    active ? 'bg-ink-100 font-medium text-ink-900' : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900'
  }`

export default function AppShell() {
  const { user, logout } = useAuth()
  const counts = useOutputCounts()
  // Each person sees only the outputs their job role allows.
  const allowed = new Set(user?.allowed_types ?? [])
  const menus = MENUS.map((m) => ({ ...m, keys: m.keys.filter((k) => allowed.has(k)) })).filter(
    (m) => m.keys.length > 0,
  )

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-20 border-b border-ink-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 sm:px-6">
          <NavLink to="/sources" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
              <Icon name="spark" className="h-4 w-4" />
            </span>
            <span className="hidden lg:inline">ContentBridge</span>
          </NavLink>

          <nav className="flex min-w-0 items-center gap-1 text-sm">
            <NavLink to="/sources" className={({ isActive }) => itemClass(isActive)}>
              <Icon name="sources" />
              Sources
            </NavLink>
            {menus.map((m) => (
              <Menu key={m.label} label={m.label} icon={m.icon} keys={m.keys} counts={counts} />
            ))}
            <NavLink to="/outputs" end className={({ isActive }) => itemClass(isActive)}>
              <Icon name="spark" />
              <span className="hidden md:inline">All outputs</span>
              {counts.all ? <Count n={counts.all} /> : null}
            </NavLink>
            {user?.role === 'admin' && (
              <NavLink to="/employees" className={({ isActive }) => itemClass(isActive)}>
                <Icon name="users" />
                <span className="hidden md:inline">Employees</span>
              </NavLink>
            )}
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-2">
            <div className="flex items-center gap-2.5 rounded-full bg-ink-100 py-1 pl-1 pr-1 sm:pr-3">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-xs font-semibold text-brand-600 shadow-sm">
                {(user?.name ?? '?').charAt(0).toUpperCase()}
              </span>
              <span className="hidden leading-tight sm:block">
                <span className="block text-xs font-medium">{user?.name}</span>
                <span className="block text-[11px] text-ink-400">
                  {user?.role === 'admin' ? 'Administrator' : (user?.job_role?.name ?? 'All outputs')}
                </span>
              </span>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="rounded-lg p-2 text-ink-400 hover:bg-ink-100 hover:text-ink-900"
            >
              <Icon name="logout" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}

/** A navbar group with a down arrow that opens its output types. */
function Menu({
  label,
  icon,
  keys,
  counts,
}: {
  label: string
  icon: string
  keys: string[]
  counts: Record<string, number>
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { pathname } = useLocation()
  const current = keys.find((k) => pathname === `/formats/${k}`)
  const total = keys.reduce((sum, k) => sum + (counts[k] ?? 0), 0)

  // Close on navigation, on a click outside and on Escape.
  useEffect(() => setOpen(false), [pathname])
  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={itemClass(Boolean(current) || open)}
      >
        <Icon name={current ?? icon} />
        <span>
          {label}
          {current && (
            <span className="hidden font-normal text-brand-600 md:inline">
              : {formatLabel(current)}
            </span>
          )}
        </span>
        {!current && total > 0 && <Count n={total} />}
        <svg
          viewBox="0 0 24 24"
          className={`h-3.5 w-3.5 text-ink-400 transition ${open ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute left-0 top-full z-30 mt-2 w-64 rounded-2xl border border-ink-200 bg-white p-1.5 shadow-lg"
        >
          {keys.map((k) => (
            <Link
              key={k}
              to={`/formats/${k}`}
              role="menuitem"
              className={`flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm transition ${
                k === current
                  ? 'bg-blue-50 font-medium text-brand-600'
                  : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900'
              }`}
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-lg ${
                  k === current ? 'bg-white text-brand-600' : 'bg-ink-100 text-ink-600'
                }`}
              >
                <Icon name={k} className="h-3.5 w-3.5" />
              </span>
              <span className="flex-1">{formatLabel(k)}</span>
              {counts[k] ? <Count n={counts[k]} /> : null}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function Count({ n }: { n: number }) {
  return (
    <span className="rounded-full bg-ink-100 px-1.5 text-[11px] font-medium text-ink-600">{n}</span>
  )
}

/** How many of each output type exist, refreshed whenever the page changes. */
function useOutputCounts(): Record<string, number> {
  const { pathname } = useLocation()
  const [counts, setCounts] = useState<Record<string, number>>({})

  useEffect(() => {
    let cancelled = false
    api
      .listAllOutputs()
      .then((outputs) => {
        if (cancelled) return
        const latest = latestOnly(outputs)
        const c: Record<string, number> = { all: latest.length }
        for (const o of latest) c[typeOf(o)] = (c[typeOf(o)] ?? 0) + 1
        setCounts(c)
      })
      .catch(() => !cancelled && setCounts({}))
    return () => {
      cancelled = true
    }
  }, [pathname])

  return counts
}
