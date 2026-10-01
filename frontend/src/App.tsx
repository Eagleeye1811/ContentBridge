import { Navigate, Route, Routes, useParams } from 'react-router-dom'
import type { ReactNode } from 'react'
import AppShell from '@/components/AppShell'
import { useAuth } from '@/lib/auth'
import Employees from '@/pages/Employees'
import FormatPage from '@/pages/FormatPage'
import Login from '@/pages/Login'
import OutputReview from '@/pages/OutputReview'
import Outputs from '@/pages/Outputs'
import Sources from '@/pages/Sources'
import DocumentPage from '@/pages/workspace/DocumentPage'
import FactsPage from '@/pages/workspace/FactsPage'
import Workspace from '@/pages/workspace/Workspace'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-10 text-sm text-ink-400">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

/** A source's "create" links now open the shared page for that output type. */
function SourceFormat() {
  const { id = '', format = '' } = useParams()
  return <Navigate to={`/formats/${format}?source=${id}`} replace />
}

/** Older links (/documents/...) keep working. */
function LegacyDocument() {
  const { id = '' } = useParams()
  return <Navigate to={`/sources/${id}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path="/sources" element={<Sources />} />
        <Route path="/sources/:id" element={<Workspace />}>
          <Route index element={<DocumentPage />} />
          <Route path="facts" element={<FactsPage />} />
          <Route path="create/:format" element={<SourceFormat />} />
        </Route>
        <Route path="/outputs" element={<Outputs />} />
        <Route path="/formats/:format" element={<FormatPage />} />
        <Route path="/outputs/:id" element={<OutputReview />} />
        <Route path="/employees" element={<Employees />} />
        <Route path="/approvals" element={<Navigate to="/outputs" replace />} />
        <Route path="/documents/:id/*" element={<LegacyDocument />} />
      </Route>
      <Route path="*" element={<Navigate to="/sources" replace />} />
    </Routes>
  )
}
