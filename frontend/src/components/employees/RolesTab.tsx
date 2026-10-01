import { useState } from 'react'
import { api, ApiError } from '@/api/client'
import OutputPicker, { OutputChips } from '@/components/employees/OutputPicker'
import { Button, Card } from '@/components/ui'
import { Icon } from '@/lib/icons'
import type { JobRole } from '@/types/api'

type Draft = { name: string; description: string; allowed_types: string[] }

/** Job roles and the outputs each may create. */
export default function RolesTab({
  roles,
  onChanged,
}: {
  roles: JobRole[]
  onChanged: () => void
}) {
  const [editing, setEditing] = useState<string | 'new' | null>(null)
  const [draft, setDraft] = useState<Draft>({ name: '', description: '', allowed_types: [] })
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function start(role: JobRole | null) {
    setError(null)
    setEditing(role ? role.id : 'new')
    setDraft(
      role
        ? { name: role.name, description: role.description, allowed_types: role.allowed_types }
        : { name: '', description: '', allowed_types: [] },
    )
  }

  async function save() {
    setBusy(true)
    setError(null)
    try {
      if (editing === 'new') await api.createRole(draft)
      else if (editing) await api.updateRole(editing, draft)
      setEditing(null)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the role')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setError(null)
    try {
      await api.deleteRole(id)
      setConfirmDelete(null)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete the role')
    }
  }

  const form = (
    <Card className="border-brand-500 ring-2 ring-blue-100">
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm font-medium">Role name</span>
            <input
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              placeholder="e.g. Social Media Analyst"
              className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium">What they do</span>
            <input
              value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              placeholder="One line, optional"
              className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </label>
        </div>
        <div>
          <p className="mb-2 text-sm font-medium">Outputs this role can create</p>
          <OutputPicker
            value={draft.allowed_types}
            onChange={(t) => setDraft({ ...draft, allowed_types: t })}
          />
        </div>
        {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div className="flex gap-2">
          <Button
            onClick={save}
            disabled={busy || draft.name.trim().length < 2 || draft.allowed_types.length === 0}
          >
            {busy ? 'Saving…' : editing === 'new' ? 'Create role' : 'Save role'}
          </Button>
          <Button variant="ghost" onClick={() => setEditing(null)}>
            Cancel
          </Button>
        </div>
      </div>
    </Card>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-ink-600">
          A role decides which outputs its people see and can create.
        </p>
        {editing === null && (
          <Button onClick={() => start(null)}>
            <Icon name="plus" />
            Add role
          </Button>
        )}
      </div>

      {editing === 'new' && form}
      {error && editing === null && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {roles.map((role) =>
          editing === role.id ? (
            <div key={role.id} className="md:col-span-2">
              {form}
            </div>
          ) : (
            <Card key={role.id} className="flex flex-col">
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{role.name}</p>
                  {role.description && (
                    <p className="mt-0.5 text-sm text-ink-600">{role.description}</p>
                  )}
                </div>
                <span className="shrink-0 rounded-full bg-ink-100 px-2 py-0.5 text-xs text-ink-600">
                  {role.employee_count} {role.employee_count === 1 ? 'person' : 'people'}
                </span>
              </div>
              <div className="mt-4 flex-1">
                <OutputChips types={role.allowed_types} />
              </div>
              <div className="mt-4 flex items-center gap-2 border-t border-ink-100 pt-3">
                <Button size="sm" variant="secondary" onClick={() => start(role)}>
                  <Icon name="edit" />
                  Edit
                </Button>
                {confirmDelete === role.id ? (
                  <>
                    <Button size="sm" variant="danger" onClick={() => remove(role.id)}>
                      Delete role
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(null)}>
                      Cancel
                    </Button>
                  </>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setConfirmDelete(role.id)}
                    disabled={role.employee_count > 0}
                    title={
                      role.employee_count > 0 ? 'Move its people to another role first' : undefined
                    }
                  >
                    <Icon name="trash" />
                    Delete
                  </Button>
                )}
              </div>
            </Card>
          ),
        )}
      </div>
    </div>
  )
}
