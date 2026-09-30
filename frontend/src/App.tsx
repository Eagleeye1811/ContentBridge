import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from '@/components/AppShell'
import DocumentDetail from '@/pages/DocumentDetail'
import Documents from '@/pages/Documents'
import Login from '@/pages/Login'
import Placeholder from '@/pages/Placeholder'
import { useAuth } from '@/lib/auth'
import type { ReactNode } from 'react'

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-10 text-sm text-ink-400">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
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
        <Route path="/documents" element={<Documents />} />
        <Route path="/documents/:id" element={<DocumentDetail />} />
        <Route path="/fact-sheet" element={<Placeholder title="Fact Sheet" phase="Phase 2" />} />
        <Route path="/studio" element={<Placeholder title="Studio" phase="Phase 3" />} />
        <Route path="/review" element={<Placeholder title="Review" phase="Phase 3" />} />
        <Route
          path="/consistency"
          element={<Placeholder title="Consistency Matrix" phase="Phase 4" />}
        />
        <Route path="/approvals" element={<Placeholder title="Approvals" phase="Phase 7" />} />
        <Route path="/settings" element={<Placeholder title="Settings" phase="Phase 7" />} />
      </Route>
      <Route path="*" element={<Navigate to="/documents" replace />} />
    </Routes>
  )
}
