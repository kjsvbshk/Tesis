import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { usePermissions } from '@/contexts/PermissionsContext'
import { LoadingScreen } from '@/components/LoadingScreen'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole, isLoading: permissionsLoading } = usePermissions()
  const location = useLocation()

  if (isLoading || permissionsLoading) return <LoadingScreen />

  if (!isAuthenticated) return <Navigate to="/login" replace />

  if (hasRole('admin') && !location.pathname.startsWith('/admin'))
    return <Navigate to="/admin" replace />

  if (hasRole('operator') && !location.pathname.startsWith('/operator') && !location.pathname.startsWith('/admin'))
    return <Navigate to="/operator" replace />

  if ((hasRole('admin') || hasRole('operator')) && location.pathname === '/') {
    if (hasRole('admin')) return <Navigate to="/admin" replace />
    if (hasRole('operator')) return <Navigate to="/operator" replace />
  }

  return <>{children}</>
}
