import { Outlet, NavLink } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Home, Trophy, Ticket, History, User, Zap } from 'lucide-react'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { BetSlip } from '@/components/BetSlip'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'

export function SidebarLayout() {
  return (
    <div className="main-grid football-pattern">
      <aside className="hidden md:block col-span-2 sidebar-bg h-full">
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="p-5 text-2xl font-bold tracking-wide text-foreground flex items-center gap-2"
        >
          <div className="logo-container">
            <img src="/logo.png" alt="Logo" width={28} height={28} />
          </div>
          HAW
        </motion.div>
        <div className="px-4 pb-2 text-xs uppercase tracking-wider text-muted-foreground">Place your bets, we’ve already won</div>
        <nav className="px-2 space-y-1">
          <SideLink to="/" icon={<Home size={22} />}>Inicio</SideLink>
          <SideLink to="/partidos" icon={<Trophy size={22} />}>Partidos</SideLink>
          <SideLink to="/apuestas" icon={<Ticket size={22} />}>Apuestas</SideLink>
          <SideLink to="/historial" icon={<History size={22} />}>Historial</SideLink>
          <SideLink to="/perfil" icon={<User size={22} />}>Perfil</SideLink>
        </nav>
      </aside>

      <main className="col-span-12 md:col-span-7 p-4 h-full">
        <div className="md:hidden mb-4">
          <MobileNav />
        </div>
        <Outlet />
      </main>

      <section className="hidden md:block col-span-3 border-l p-4 bg-card/40 h-full">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg font-semibold mb-2 flex items-center gap-2"
        >
          <Zap size={20} className="text-green-400" />
          Boleta
        </motion.div>
        <BetSlip />
      </section>
      <Toaster />
    </div>
  )
}

function SideLink({ to, icon, children }: { to: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-md text-base hover:bg-accent/50 transition-all duration-200 ${isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'}`
      }
      end
    >
      {icon}
      <span className="font-medium">{children}</span>
    </NavLink>
  )
}

function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="default" className="text-base flex items-center gap-2">
          <div className="logo-container">
            <img src="/logo.png" alt="Logo" width={18} height={18} />
          </div>
          Menú
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64">
        <nav className="mt-6 space-y-1">
          <SideLink to="/" icon={<Home size={22} />}>Inicio</SideLink>
          <SideLink to="/partidos" icon={<Trophy size={22} />}>Partidos</SideLink>
          <SideLink to="/apuestas" icon={<Ticket size={22} />}>Apuestas</SideLink>
          <SideLink to="/historial" icon={<History size={22} />}>Historial</SideLink>
          <SideLink to="/perfil" icon={<User size={22} />}>Perfil</SideLink>
        </nav>
      </SheetContent>
    </Sheet>
  )
}


