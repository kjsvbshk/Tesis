import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { usePermissions } from '@/contexts/PermissionsContext'
import { motion } from 'framer-motion'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const { hasRole, isLoading: permissionsLoading } = usePermissions()
  const location = useLocation()

  if (isLoading || permissionsLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0B132B]">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <div className="logo-container pulse-glow mx-auto mb-4">
            <img src="/logo.png" alt="HAW Logo" className="h-12 w-auto" />
          </div>
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          <p className="mt-4 text-[#B0B3C5]">Cargando...</p>
        </motion.div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Redirect admins to admin panel
  if (hasRole('admin') && !location.pathname.startsWith('/admin')) {
    return <Navigate to="/admin" replace />
  }

  // Redirect operators to operator panel
  if (hasRole('operator') && !location.pathname.startsWith('/operator') && !location.pathname.startsWith('/admin')) {
    return <Navigate to="/operator" replace />
  }

  // If user is admin or operator trying to access user routes, redirect
  if ((hasRole('admin') || hasRole('operator')) && location.pathname === '/') {
    if (hasRole('admin')) {
      return <Navigate to="/admin" replace />
    }
    if (hasRole('operator')) {
      return <Navigate to="/operator" replace />
    }
  }

  return <>{children}</>
}

