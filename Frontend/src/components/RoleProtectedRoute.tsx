import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { usePermissions } from '@/contexts/PermissionsContext'
import { LoadingScreen } from '@/components/LoadingScreen'

interface RoleProtectedRouteProps {
  children: React.ReactNode
  allowedRoles: string[]
  fallbackPath?: string
}

export function RoleProtectedRoute({
  children,
  allowedRoles,
  fallbackPath = '/',
}: RoleProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole, isLoading: permissionsLoading } = usePermissions()

  if (isLoading || permissionsLoading) return <LoadingScreen />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!allowedRoles.some(role => hasRole(role))) return <Navigate to={fallbackPath} replace />

  return <>{children}</>
}
