import { useState } from 'react'
import { api, ApiError } from '@/api/client'
import { OutputChips } from '@/components/employees/OutputPicker'
import { Badge, Button, Card, Field, Select } from '@/components/ui'
import { useAuth } from '@/lib/auth'
import { Icon } from '@/lib/icons'
import type { JobRole, Role, User } from '@/types/api'

const ACCESS: { key: Role; label: string }[] = [
  { key: 'editor', label: 'Employee' },
  { key: 'admin', label: 'Administrator' },
]

const NO_ROLE = ''

/** Everyone with an account: add people, give them a role, disable access. */
export default function EmployeesTab({
  employees,
  roles,
  onChanged,
}: {
  employees: User[]
  roles: JobRole[]
  onChanged: () => void
}) {
  const { user: me } = useAuth()
  const [adding, setAdding] = useState(false)
  const [resetFor, setResetFor] = useState<string | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const roleOptions = [
    { key: NO_ROLE, label: 'No role (all outputs)' },
    ...roles.map((r) => ({ key: r.id, label: r.name })),
  ]

  async function update(id: string, body: Parameters<typeof api.updateEmployee>[1], done?: string) {
    setError(null)
    setNotice(null)
    try {
      await api.updateEmployee(id, body)
      if (done) setNotice(done)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-ink-600">
          {employees.filter((e) => e.is_active).length} active of {employees.length} accounts
        </p>
        {!adding && (
          <Button onClick={() => setAdding(true)}>
            <Icon name="plus" />
            Add employee
          </Button>
        )}
      </div>

      {adding && (
        <AddEmployee
          roleOptions={roleOptions}
          onCancel={() => setAdding(false)}
          onAdded={(name) => {
            setAdding(false)
            setNotice(`${name} can now sign in with the password you set.`)
            onChanged()
          }}
        />
      )}

      {notice && (
        <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</p>
      )}
      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="overflow-x-auto rounded-2xl border border-ink-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-200 text-left text-xs text-ink-600">
              <th className="px-4 py-3 font-medium">Employee</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Can create</th>
              <th className="px-4 py-3 font-medium">Access</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {employees.map((e) => {
              const self = e.id === me?.id
              return (
                <tr
                  key={e.id}
                  className={`border-b border-ink-100 align-top last:border-0 ${e.is_active ? '' : 'opacity-55'}`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-brand-600">
                        {e.name.charAt(0).toUpperCase()}
                      </span>
                      <div className="min-w-0">
                        <p className="font-medium">
                          {e.name}
                          {self && <span className="ml-1 text-xs text-ink-400">(you)</span>}
                        </p>
                        <p className="truncate text-xs text-ink-400">{e.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="w-56 px-4 py-3">
                    {e.role === 'admin' ? (
                      <span className="text-ink-400">All outputs</span>
                    ) : (
                      <Select
                        value={e.job_role?.id ?? NO_ROLE}
                        onChange={(v) =>
                          update(
                            e.id,
                            v === NO_ROLE ? { clear_job_role: true } : { job_role_id: v },
                            `${e.name}'s role was updated.`,
                          )
                        }
                        options={roleOptions}
                      />
                    )}
                  </td>
                  <td className="max-w-xs px-4 py-3">
                    <OutputChips types={e.allowed_types} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col items-start gap-1">
                      <Badge tone={e.role === 'admin' ? 'info' : 'neutral'}>
                        {e.role === 'admin' ? 'Administrator' : e.role === 'approver' ? 'Approver' : 'Employee'}
                      </Badge>
                      {!e.is_active && <Badge tone="bad">Disabled</Badge>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {resetFor === e.id ? (
                      <div className="flex w-56 flex-col gap-1.5">
                        <input
                          type="password"
                          value={newPassword}
                          onChange={(ev) => setNewPassword(ev.target.value)}
                          placeholder="New password (8+ characters)"
                          autoComplete="new-password"
                          className="rounded-lg border border-ink-200 px-2.5 py-1.5 text-sm outline-none focus:border-brand-500"
                        />
                        <div className="flex gap-1.5">
                          <Button
                            size="sm"
                            disabled={newPassword.length < 8}
                            onClick={() => {
                              void update(e.id, { password: newPassword }, `${e.name}'s password was reset.`)
                              setResetFor(null)
                              setNewPassword('')
                            }}
                          >
                            Save
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setResetFor(null)}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex justify-end gap-1.5 whitespace-nowrap">
                        <Button size="sm" variant="ghost" onClick={() => setResetFor(e.id)}>
                          Reset password
                        </Button>
                        {!self &&
                          (e.is_active ? (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => update(e.id, { is_active: false }, `${e.name} can no longer sign in.`)}
                            >
                              Disable
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => update(e.id, { is_active: true }, `${e.name} can sign in again.`)}
                            >
                              Enable
                            </Button>
                          ))}
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function AddEmployee({
  roleOptions,
  onCancel,
  onAdded,
}: {
  roleOptions: { key: string; label: string }[]
  onCancel: () => void
  onAdded: (name: string) => void
}) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [jobRole, setJobRole] = useState(roleOptions[1]?.key ?? NO_ROLE)
  const [access, setAccess] = useState<Role>('editor')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    setBusy(true)
    setError(null)
    try {
      await api.createEmployee({
        name,
        email,
        password,
        role: access,
        job_role_id: access === 'admin' || jobRole === NO_ROLE ? null : jobRole,
      })
      onAdded(name)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add the employee')
    } finally {
      setBusy(false)
    }
  }

  const valid = name.trim() && /\S+@\S+\.\S+/.test(email) && password.length >= 8

  return (
    <Card className="border-brand-500 ring-2 ring-blue-100">
      <p className="mb-4 font-semibold">Add an employee</p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Full name">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </Field>
        <Field label="Work email">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="off"
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </Field>
        <Field label="Temporary password" help="At least 8 characters; share it privately">
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </Field>
        <Field label="Role">
          <Select value={jobRole} onChange={setJobRole} options={roleOptions} />
        </Field>
        <Field label="Access">
          <Select value={access} onChange={(v) => setAccess(v as Role)} options={ACCESS} />
        </Field>
      </div>
      {error && <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <div className="mt-5 flex gap-2">
        <Button onClick={save} disabled={busy || !valid}>
          {busy ? 'Adding…' : 'Add employee'}
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </Card>
  )
}
