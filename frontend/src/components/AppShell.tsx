import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

const NAV = [
  { to: '/documents', label: 'Documents' },
  { to: '/consistency', label: 'Consistency' },
  { to: '/approvals', label: 'Approvals' },
  { to: '/settings', label: 'Settings' },
]

export default function AppShell() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-ink-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <span className="font-semibold tracking-tight">ContentBridge</span>
          <nav className="flex flex-wrap gap-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md px-2.5 py-1.5 ${
                    isActive ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-200'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="text-ink-600">
              {user?.name}
              <span className="ml-1.5 rounded bg-ink-200 px-1.5 py-0.5 text-xs">{user?.role}</span>
            </span>
            <button onClick={logout} className="text-ink-600 hover:text-ink-900">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
