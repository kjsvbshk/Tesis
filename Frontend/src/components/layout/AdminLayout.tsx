/**
 * Admin Layout
 * Layout for admin users with admin-specific sidebar
 */

import { Outlet, NavLink } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import {
  Users,
  Shield,
  BarChart3,
  FileText,
  Settings,
  Search,
  Activity,
  Key,
  Home,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
} from 'lucide-react'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from '@/components/ui/sheet'

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

export function AdminLayout() {
  const { user, logout } = useAuth()
  const { toast } = useToast()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const handleLogout = async () => {
    try {
      await logout()
      toast({
        title: 'Sesión cerrada',
        description: 'Has cerrado sesión exitosamente.',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Hubo un problema al cerrar sesión.',
        variant: 'destructive',
      })
    }
  }

  return (
    <div className="main-grid football-pattern">
      {isSidebarOpen && (
        <motion.aside
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="hidden md:flex md:col-span-2 sidebar-bg h-full relative flex-col"
        >
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
              HAW Admin
            </span>
          </motion.div>
          <div className="px-4 pb-4 text-xs uppercase tracking-wider text-[#B0B3C5] font-medium">
            Panel de Administración
          </div>
          <nav className="px-2 space-y-1 flex-1 overflow-y-auto">
            <SideLink to="/admin" icon={<Home size={22} />}>
              Inicio
            </SideLink>
            <SideLink to="/admin/usuarios" icon={<Users size={22} />}>
              Usuarios
            </SideLink>
            <SideLink to="/admin/roles" icon={<Shield size={22} />}>
              Roles y Permisos
            </SideLink>
            <SideLink to="/admin/metricas" icon={<BarChart3 size={22} />}>
              Métricas
            </SideLink>
            <SideLink to="/admin/auditoria" icon={<FileText size={22} />}>
              Auditoría
            </SideLink>
            <SideLink to="/admin/buscar" icon={<Search size={22} />}>
              Búsqueda Avanzada
            </SideLink>
            <SideLink to="/admin/proveedores" icon={<Key size={22} />}>
              Proveedores
            </SideLink>
            <SideLink to="/admin/monitoreo" icon={<Activity size={22} />}>
              Monitoreo
            </SideLink>
            <SideLink to="/admin/configuracion" icon={<Settings size={22} />}>
              Configuración
            </SideLink>
          </nav>
          <div className="px-2 pb-4 pt-4 border-t border-[#1C2541]/50 space-y-2">
            <div className="px-4 py-2 bg-[#1C2541]/50 rounded-lg border border-[#1C2541]">
              <p className="text-xs text-[#B0B3C5]">Usuario:</p>
              <p className="text-sm font-medium text-white">{user?.username}</p>
              <p className="text-xs text-[#00FF73]">Administrador</p>
            </div>
            <Button
              onClick={handleLogout}
              variant="ghost"
              className="w-full justify-start gap-3 px-4 py-3 text-base text-[#FF4C4C] hover:bg-[#FF4C4C]/10 hover:text-[#FF4C4C] border-l-4 border-transparent hover:border-[#FF4C4C]/50 transition-all duration-300"
            >
              <LogOut size={22} />
              <span className="font-medium">Cerrar Sesión</span>
            </Button>
          </div>
          <Button
            onClick={() => setIsSidebarOpen(false)}
            variant="ghost"
            size="icon"
            className="absolute top-4 -right-3 h-6 w-6 rounded-full bg-[#1C2541] border border-[#00FF73]/30 hover:bg-[#00FF73]/10 text-[#00FF73] z-10 shadow-lg"
          >
            <ChevronLeft size={16} />
          </Button>
        </motion.aside>
      )}

      <main className={`col-span-12 p-4 h-full bg-[#0B132B] overflow-y-auto transition-all duration-300 ${isSidebarOpen ? 'md:col-span-10' : 'md:col-span-12'}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="md:hidden">
            <MobileNav />
          </div>
          {!isSidebarOpen && (
            <Button
              onClick={() => setIsSidebarOpen(true)}
              variant="ghost"
              size="icon"
              className="hidden md:flex h-8 w-8 rounded-full bg-[#1C2541] border border-[#00FF73]/30 hover:bg-[#00FF73]/10 text-[#00FF73] shadow-lg"
            >
              <ChevronRight size={16} />
            </Button>
          )}
        </div>
        <Outlet />
      </main>
      <Toaster />
    </div>
  )
}

function MobileNav() {
  const { user, logout } = useAuth()
  const { toast } = useToast()

  const handleLogout = async () => {
    try {
      await logout()
      toast({
        title: 'Sesión cerrada',
        description: 'Has cerrado sesión exitosamente.',
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Hubo un problema al cerrar sesión.',
        variant: 'destructive',
      })
    }
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="default" className="text-base flex items-center gap-2">
          <Menu size={18} />
          Menú Admin
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 sidebar-bg">
        <SheetTitle className="sr-only">Menú de administración</SheetTitle>
        <SheetDescription className="sr-only">Menú principal del panel de administración</SheetDescription>
        <div className="p-5 text-2xl font-heading font-bold tracking-wide text-white flex items-center gap-3 mb-4">
          <div className="logo-container pulse-glow">
            <img src="/logo.png" alt="Logo" width={28} height={28} />
          </div>
          <span className="bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent">
            HAW Admin
          </span>
        </div>
        <div className="px-4 pb-4 text-xs uppercase tracking-wider text-[#B0B3C5] font-medium mb-4">
          Panel de Administración
        </div>
        <nav className="space-y-1">
          <SideLink to="/admin" icon={<Home size={22} />}>
            Inicio
          </SideLink>
          <SideLink to="/admin/usuarios" icon={<Users size={22} />}>
            Usuarios
          </SideLink>
          <SideLink to="/admin/roles" icon={<Shield size={22} />}>
            Roles y Permisos
          </SideLink>
          <SideLink to="/admin/metricas" icon={<BarChart3 size={22} />}>
            Métricas
          </SideLink>
          <SideLink to="/admin/auditoria" icon={<FileText size={22} />}>
            Auditoría
          </SideLink>
          <SideLink to="/admin/buscar" icon={<Search size={22} />}>
            Búsqueda Avanzada
          </SideLink>
          <SideLink to="/admin/proveedores" icon={<Key size={22} />}>
            Proveedores
          </SideLink>
          <SideLink to="/admin/monitoreo" icon={<Activity size={22} />}>
            Monitoreo
          </SideLink>
          <SideLink to="/admin/configuracion" icon={<Settings size={22} />}>
            Configuración
          </SideLink>
        </nav>
        <div className="mt-6 pt-4 border-t border-[#1C2541]/50 space-y-2">
          <div className="px-4 py-2 bg-[#1C2541]/50 rounded-lg border border-[#1C2541]">
            <p className="text-xs text-[#B0B3C5]">Usuario:</p>
            <p className="text-sm font-medium text-white">{user?.username}</p>
            <p className="text-xs text-[#00FF73]">Administrador</p>
          </div>
          <Button
            onClick={handleLogout}
            variant="ghost"
            className="w-full justify-start gap-3 px-4 py-3 text-base text-[#FF4C4C] hover:bg-[#FF4C4C]/10 hover:text-[#FF4C4C]"
          >
            <LogOut size={22} />
            <span className="font-medium">Cerrar Sesión</span>
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

