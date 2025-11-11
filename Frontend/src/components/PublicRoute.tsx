import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { motion } from 'framer-motion'

interface PublicRouteProps {
  children: React.ReactNode
}

export function PublicRoute({ children }: PublicRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
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

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

