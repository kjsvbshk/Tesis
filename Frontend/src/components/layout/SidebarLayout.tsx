import { Outlet, NavLink } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Home, Trophy, Ticket, History, User, Zap, FileText, LogOut, ChevronLeft, Menu, Activity } from 'lucide-react'
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { BetSlip } from '@/components/BetSlip'
import { Button } from '@/components/ui/button'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function SidebarLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const { logout } = useAuth()


  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      // Ignore error
    }
  }

  return (
    <div className="flex h-screen bg-void text-foreground overflow-hidden font-sans relative selection:bg-acid-500 selection:text-black">
      <div className="absolute inset-0 pointer-events-none z-50 mix-blend-overlay opacity-5 bg-[url('/noise.svg')] bg-repeat" />

      {/* Sidebar Desktop */}
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
              <div className="w-8 h-8 bg-acid-500 rounded-none cut-corners flex items-center justify-center text-black font-bold font-display text-lg">H</div>
              <div>
                <h1 className="font-display font-bold text-xl tracking-tighter text-white">HAW<span className="text-acid-500">.OS</span></h1>
                <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">v2.4.0-STABLE</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto py-6 px-3 space-y-1 custom-scrollbar">
              <SideLink to="/" icon={<Home size={18} />}>DASHBOARD</SideLink>
              <SideLink to="/partidos" icon={<Trophy size={18} />}>MATCH_FEED</SideLink>
              <SideLink to="/predicciones" icon={<Zap size={18} />}>PREDICTIONS</SideLink>
              <SideLink to="/apuestas" icon={<Ticket size={18} />}>BET_SLIP</SideLink>
              <SideLink to="/requests" icon={<FileText size={18} />}>REQUESTS</SideLink>
              <div className="my-4 border-t border-white/5 mx-2" />
              <SideLink to="/historial" icon={<History size={18} />}>LOGS / HISTORY</SideLink>
              <SideLink to="/perfil" icon={<User size={18} />}>USER_PROFILE</SideLink>
            </div>

            <div className="p-4 border-t border-white/5">
              <Button
                onClick={handleLogout}
                variant="ghost"
                className="w-full justify-start text-muted-foreground hover:text-alert-red hover:bg-alert-red/10 font-mono text-xs uppercase tracking-wider"
              >
                <LogOut size={16} className="mr-2" />
                DISCONNECT
              </Button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Wrapper */}
      <div className="flex-1 flex flex-col min-w-0 bg-void relative z-10">
        {/* Top Bar / Ticker */}
        <header className="h-14 border-b border-border bg-metal-900/80 backdrop-blur flex items-center justify-between px-4 z-20">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              variant="ghost"
              size="icon"
              className="hidden md:flex text-acid-500 hover:bg-acid-500/10 hover:text-acid-500"
            >
              {isSidebarOpen ? <ChevronLeft /> : <Menu />}
            </Button>
            <MobileNav />

            {/* Ticker (Visual only) */}
            <div className="hidden md:flex items-center gap-6 text-[10px] font-mono text-muted-foreground uppercase tracking-wider border-l border-white/10 pl-4 h-8">
              <span className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-acid-500 rounded-full animate-pulse" />
                SYSTEM: ONLINE
              </span>
              <span>LATENCY: 12ms</span>
              <span>ENCRYPTION: AES-256</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="px-3 py-1 bg-acid-500/10 border border-acid-500/20 text-acid-500 font-mono text-xs rounded-sm">
              CREDITS: <span className="font-bold">2,450</span>
            </div>
            <div className="w-8 h-8 bg-metal-800 rounded-none border border-white/10 flex items-center justify-center">
              <User size={14} className="text-white" />
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          <main className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar relative">
            <Outlet />
          </main>

          {/* Right Panel - Bet Slip (Desktop) */}
          <aside className="hidden xl:flex flex-col w-80 border-l border-border bg-metal-900/30 backdrop-blur-sm">
            <div className="p-4 border-b border-border flex items-center gap-2 font-display text-white font-bold">
              <Activity size={16} className="text-acid-500" />
              LIVE_SLIP
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <BetSlip />
            </div>
          </aside>
        </div>
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
          ? 'bg-acid-500/10 text-acid-500 border-acid-500 font-medium'
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
        <Button variant="ghost" size="icon" className="md:hidden text-acid-500">
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 bg-metal-900 border-r border-border p-0">
        <SheetTitle className="sr-only">Menú</SheetTitle>
        <SheetDescription className="sr-only">Navegación Móvil</SheetDescription>

        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 bg-acid-500 rounded-none flex items-center justify-center text-black font-bold font-display text-lg">H</div>
          <h1 className="font-display font-bold text-xl tracking-tighter text-white">HAW<span className="text-acid-500">.OS</span></h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
          <SideLink to="/" icon={<Home size={18} />}>DASHBOARD</SideLink>
          <SideLink to="/partidos" icon={<Trophy size={18} />}>MATCH_FEED</SideLink>
          <SideLink to="/apuestas" icon={<Ticket size={18} />}>BET_SLIP</SideLink>
          <SideLink to="/perfil" icon={<User size={18} />}>PROFILE</SideLink>
        </nav>

        <div className="p-4 border-t border-white/5 fixed bottom-0 w-full bg-metal-900">
          <Button onClick={() => logout()} variant="outline" className="w-full font-mono text-xs border-alert-red text-alert-red hover:bg-alert-red/10">
            DISCONNECT
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}


