/**
 * Operator Layout
 * Layout for operator users with operator-specific sidebar
 */

import { Outlet, NavLink } from 'react-router-dom'
import { Key, Activity, FileText, Home } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'

function SideLink({
  to,
  icon,
  children,
}: {
  to: string
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
          isActive
            ? 'bg-[#00FF73]/20 text-[#00FF73] border-l-2 border-[#00FF73]'
            : 'text-[#B0B3C5] hover:bg-[#1C2541]/50 hover:text-white'
        }`
      }
    >
      {icon}
      <span className="font-medium">{children}</span>
    </NavLink>
  )
}

export function OperatorLayout() {
  const { user } = useAuth()

  return (
    <div className="main-grid football-pattern">
      <aside className="hidden md:block col-span-2 sidebar-bg h-full">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="p-5 text-2xl font-heading font-bold tracking-wide text-white flex items-center gap-3"
        >
          <div className="logo-container pulse-glow">
            <img src="/logo.png" alt="Logo" width={28} height={28} />
          </div>
          <span className="bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent">
            HAW Operator
          </span>
        </motion.div>
        <div className="px-4 pb-4 text-xs uppercase tracking-wider text-[#B0B3C5] font-medium">
          Panel de Operador
        </div>
        <nav className="px-2 space-y-1">
          <SideLink to="/operator" icon={<Home size={22} />}>
            Inicio
          </SideLink>
          <SideLink to="/operator/proveedores" icon={<Key size={22} />}>
            Proveedores
          </SideLink>
          <SideLink to="/operator/monitoreo" icon={<Activity size={22} />}>
            Monitoreo de Integraciones
          </SideLink>
          <SideLink to="/operator/sincronizacion" icon={<FileText size={22} />}>
            Registros de Sincronización
          </SideLink>
        </nav>
        <div className="absolute bottom-4 left-4 right-4 px-4 py-2 bg-[#1C2541]/50 rounded-lg border border-[#1C2541]">
          <p className="text-xs text-[#B0B3C5]">Usuario:</p>
          <p className="text-sm font-medium text-white">{user?.username}</p>
          <p className="text-xs text-[#FFD700]">Operador</p>
        </div>
      </aside>

      <main className="col-span-12 md:col-span-10 p-4 h-full bg-[#0B132B] overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}

