/**
 * Role Based Layout
 * Redirects to the appropriate layout based on user role
 */

import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { usePermissions } from '@/contexts/PermissionsContext'
import { SidebarLayout } from './layout/SidebarLayout'
import { AdminLayout } from './layout/AdminLayout'
import { OperatorLayout } from './layout/OperatorLayout'
import { LoadingScreen } from './LoadingScreen'

interface RoleBasedLayoutProps {
  requiredRole?: 'admin' | 'operator' | 'user'
}

export function RoleBasedLayout(_props: RoleBasedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole, isLoading: permissionsLoading } = usePermissions()

  if (isLoading || permissionsLoading) {
    return <LoadingScreen />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Determine which layout to use based on role
  if (hasRole('admin')) {
    return <AdminLayout />
  }

  if (hasRole('operator')) {
    return <OperatorLayout />
  }

  // Default to user layout
  return <SidebarLayout />
}

