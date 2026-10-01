import { useCallback, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api } from '@/api/client'
import EmployeesTab from '@/components/employees/EmployeesTab'
import RolesTab from '@/components/employees/RolesTab'
import { PageHeader, Segmented } from '@/components/ui'
import { useAuth } from '@/lib/auth'
import { Icon } from '@/lib/icons'
import type { JobRole, User } from '@/types/api'

/** Administrators manage who can sign in and which outputs each role creates. */
export default function Employees() {
  const { user } = useAuth()
  const [tab, setTab] = useState<'employees' | 'roles'>('employees')
  const [employees, setEmployees] = useState<User[] | null>(null)
  const [roles, setRoles] = useState<JobRole[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    Promise.all([api.listEmployees(), api.listRoles()])
      .then(([e, r]) => {
        setEmployees(e)
        setRoles(r)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load employees'))
  }, [])

  useEffect(() => {
    if (user?.role === 'admin') load()
  }, [load, user])

  if (user?.role !== 'admin') return <Navigate to="/sources" replace />

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="Employees"
        subtitle="Add your team and give each person a role. A role decides which outputs they can create."
        icon={<Icon name="users" className="h-5 w-5" />}
        action={
          <Segmented
            options={[
              { key: 'employees', label: `Employees${employees ? ` (${employees.length})` : ''}` },
              { key: 'roles', label: `Roles${roles ? ` (${roles.length})` : ''}` },
            ]}
            value={tab}
            onChange={(t) => setTab(t as 'employees' | 'roles')}
          />
        }
      />

      {error && <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {!employees || !roles ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : tab === 'employees' ? (
        <EmployeesTab employees={employees} roles={roles} onChanged={load} />
      ) : (
        <RolesTab roles={roles} onChanged={load} />
      )}
    </div>
  )
}
