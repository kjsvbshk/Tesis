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

interface RoleBasedLayoutProps {
  requiredRole?: 'admin' | 'operator' | 'user'
}

export function RoleBasedLayout(_props: RoleBasedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole, isLoading: permissionsLoading } = usePermissions()

  if (isLoading || permissionsLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B132B]">
        <div className="text-center">
          <div className="logo-container pulse-glow mx-auto mb-4">
            <img src="/logo.png" alt="HAW Logo" className="h-12 w-auto" />
          </div>
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          <p className="mt-4 text-[#B0B3C5]">Cargando...</p>
        </div>
      </div>
    )
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

