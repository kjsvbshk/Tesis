import { Outlet, NavLink } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Users, Shield, BarChart3, FileText, Settings, Activity, Key, Home, LogOut, ChevronLeft, Menu } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from '@/components/ui/sheet'

export function AdminLayout() {
  const { user, logout } = useAuth()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      // Ignore
    }
  }

  return (
    <div className="flex h-screen bg-void text-foreground overflow-hidden font-sans relative selection:bg-alert-red selection:text-white">
      <div className="absolute inset-0 pointer-events-none z-50 mix-blend-overlay opacity-5 bg-[url('/noise.svg')] bg-repeat" />

      {/* Admin Sidebar */}
      <AnimatePresence mode="wait">
        {isSidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="hidden md:flex flex-col border-r border-border bg-metal-900/50 backdrop-blur-sm relative z-20"
          >
            <div className="p-6 border-b border-white/5 flex items-center gap-3">
              <div className="w-8 h-8 bg-alert-red rounded-none cut-corners flex items-center justify-center text-white font-bold font-display text-lg">A</div>
              <div>
                <h1 className="font-display font-bold text-xl tracking-tighter text-white">ADMIN<span className="text-alert-red">.CORE</span></h1>
                <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">ROOT ACCESS</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto py-6 px-3 space-y-1 custom-scrollbar">
              <SideLink to="/admin" icon={<Home size={18} />}>OVERVIEW</SideLink>
              <div className="my-2 px-3 text-[10px] text-muted-foreground font-mono uppercase tracking-widest">User Management</div>
              <SideLink to="/admin/usuarios" icon={<Users size={18} />}>USERS</SideLink>
              <SideLink to="/admin/roles" icon={<Shield size={18} />}>PERMISSIONS</SideLink>

              <div className="my-2 px-3 text-[10px] text-muted-foreground font-mono uppercase tracking-widest">System</div>
              <SideLink to="/admin/metricas" icon={<BarChart3 size={18} />}>METRICS</SideLink>
              <SideLink to="/admin/monitoreo" icon={<Activity size={18} />}>MONITORING</SideLink>
              <SideLink to="/admin/auditoria" icon={<FileText size={18} />}>AUDIT_LOGS</SideLink>

              <div className="my-2 px-3 text-[10px] text-muted-foreground font-mono uppercase tracking-widest">Config</div>
              <SideLink to="/admin/proveedores" icon={<Key size={18} />}>PROVIDERS</SideLink>
              <SideLink to="/admin/configuracion" icon={<Settings size={18} />}>SETTINGS</SideLink>
            </div>

            <div className="p-4 border-t border-white/5 bg-alert-red/5">
              <div className="mb-4 px-2">
                <div className="text-xs text-muted-foreground font-mono">Logged as:</div>
                <div className="text-sm font-bold text-white font-display uppercase tracking-wide">{user?.username}</div>
                <div className="text-[10px] text-alert-red font-mono bg-alert-red/10 inline-block px-1 rounded border border-alert-red/20">ADMINISTRATOR</div>
              </div>
              <Button
                onClick={handleLogout}
                variant="ghost"
                className="w-full justify-start text-muted-foreground hover:text-white hover:bg-white/5 font-mono text-xs uppercase tracking-wider"
              >
                <LogOut size={16} className="mr-2" />
                SECURE EXIT
              </Button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col min-w-0 bg-void relative z-10">
        {/* Top Bar */}
        <header className="h-14 border-b border-alert-red/30 bg-metal-900/80 backdrop-blur flex items-center justify-between px-4 z-20">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              variant="ghost"
              size="icon"
              className="hidden md:flex text-alert-red hover:bg-alert-red/10 hover:text-alert-red"
            >
              {isSidebarOpen ? <ChevronLeft /> : <Menu />}
            </Button>
            <MobileNav />

            <div className="hidden md:flex items-center gap-6 text-[10px] font-mono text-alert-red/70 uppercase tracking-wider border-l border-white/10 pl-4 h-8">
              <span className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-alert-red rounded-full animate-pulse" />
                SYSTEM STATUS: CRITICAL
              </span>
              <span>CPU: 34%</span>
              <span>MEM: 64%</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar relative">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </div>
  )
}

function SideLink({ to, icon, children }: { to: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-all duration-200 group relative border-l-2 ${isActive
          ? 'bg-alert-red/10 text-alert-red border-alert-red font-bold'
          : 'text-muted-foreground border-transparent hover:text-white hover:bg-white/5 hover:border-white/20'
        }`
      }
      end
    >
      {icon}
      <span className="font-mono text-xs uppercase tracking-wide truncate">{children}</span>
    </NavLink>
  )
}

function MobileNav() {
  const { logout } = useAuth()

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden text-alert-red">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 bg-metal-900 border-r border-border p-0">
        <SheetTitle className="sr-only">Menú Admin</SheetTitle>
        <SheetDescription className="sr-only">Navegación Admin Móvil</SheetDescription>

        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 bg-alert-red rounded-none flex items-center justify-center text-white font-bold font-display text-lg">A</div>
          <h1 className="font-display font-bold text-xl tracking-tighter text-white">ADMIN<span className="text-alert-red">.CORE</span></h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
          <SideLink to="/admin" icon={<Home size={18} />}>OVERVIEW</SideLink>
          <SideLink to="/admin/usuarios" icon={<Users size={18} />}>USERS</SideLink>
          <SideLink to="/admin/roles" icon={<Shield size={18} />}>PERMISSIONS</SideLink>
          <SideLink to="/admin/metricas" icon={<BarChart3 size={18} />}>METRICS</SideLink>
          <SideLink to="/admin/configuracion" icon={<Settings size={18} />}>SETTINGS</SideLink>
        </nav>

        <div className="p-4 border-t border-white/5 fixed bottom-0 w-full bg-metal-900">
          <Button onClick={() => logout()} variant="outline" className="w-full font-mono text-xs border-alert-red text-alert-red hover:bg-alert-red/10">
            SECURE EXIT
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}

