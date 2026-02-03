import { Outlet, NavLink } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Activity, LogOut, ChevronLeft, Menu, Database, FileText, Settings, Shield } from 'lucide-react'
import { Sheet, SheetContent, SheetTrigger, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function ProviderLayout() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true)
    const { logout, user } = useAuth()

    // Provider theme colors: Cyan/Teal (#00F0FF) to distinguish from Admin (Acid Lime) and Operator (Orange/Yellow)
    const themeColor = "text-[#00F0FF]"
    const themeBorder = "border-[#00F0FF]"
    const themeBg = "bg-[#00F0FF]"

    const handleLogout = async () => {
        try {
            await logout()
        } catch (error) {
            // Ignore error
        }
    }

    return (
        <div className="flex h-screen bg-void text-foreground overflow-hidden font-sans relative selection:bg-[#00F0FF] selection:text-black">
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
                            <div className={`w-8 h-8 ${themeBg} rounded-none cut-corners flex items-center justify-center text-black font-bold font-display text-lg`}>P</div>
                            <div>
                                <h1 className="font-display font-bold text-xl tracking-tighter text-white">HAW<span className={themeColor}>.PRO</span></h1>
                                <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">PROVIDER ACCESS</p>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto py-6 px-3 space-y-1 custom-scrollbar">
                            <SideLink to="/provider" icon={<Activity size={18} />} themeColor={themeColor} themeBorder={themeBorder}>DASHBOARD</SideLink>
                            <SideLink to="/provider/integration" icon={<Database size={18} />} themeColor={themeColor} themeBorder={themeBorder}>INTEGRATION</SideLink>
                            <SideLink to="/provider/docs" icon={<FileText size={18} />} themeColor={themeColor} themeBorder={themeBorder}>API_DOCS</SideLink>
                            <SideLink to="/provider/settings" icon={<Settings size={18} />} themeColor={themeColor} themeBorder={themeBorder}>CONFIG</SideLink>

                            <div className="my-4 border-t border-white/5 mx-2" />

                            <div className="px-3 py-2">
                                <div className="bg-[#00F0FF]/5 border border-[#00F0FF]/20 p-3 rounded-sm">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Shield size={14} className="text-[#00F0FF]" />
                                        <span className="text-[10px] font-mono text-[#00F0FF] uppercase">Secure Connection</span>
                                    </div>
                                    <div className="h-1 w-full bg-[#00F0FF]/20 rounded-full overflow-hidden">
                                        <div className="h-full bg-[#00F0FF] animate-pulse w-full" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-4 border-t border-white/5">
                            <div className="mb-4 flex items-center gap-3 px-2">
                                <div className="w-8 h-8 bg-metal-800 rounded-full flex items-center justify-center text-xs font-bold border border-white/10">
                                    {user?.username?.charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1 overflow-hidden">
                                    <p className="text-sm font-medium text-white truncate">{user?.username}</p>
                                    <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                                </div>
                            </div>
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
                {/* Top Bar */}
                <header className="h-14 border-b border-border bg-metal-900/80 backdrop-blur flex items-center justify-between px-4 z-20">
                    <div className="flex items-center gap-4">
                        <Button
                            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                            variant="ghost"
                            size="icon"
                            className={`hidden md:flex ${themeColor} hover:bg-[#00F0FF]/10 hover:text-[#00F0FF]`}
                        >
                            {isSidebarOpen ? <ChevronLeft /> : <Menu />}
                        </Button>
                        <MobileNav themeColor={themeColor} themeBg={themeBg} themeBorder={themeBorder} />

                        <div className="hidden md:flex items-center gap-6 text-[10px] font-mono text-muted-foreground uppercase tracking-wider border-l border-white/10 pl-4 h-8">
                            <span className="flex items-center gap-2">
                                <span className={`w-1.5 h-1.5 ${themeBg} rounded-full animate-pulse`} />
                                NODE: ACTIVE
                            </span>
                            <span>UPTIME: 99.98%</span>
                        </div>
                    </div>
                </header>

                {/* Content Area */}
                <div className="flex-1 flex overflow-hidden">
                    <main className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar relative">
                        <Outlet />
                    </main>
                </div>
            </div>

            <Toaster />
        </div>
    )
}

function SideLink({ to, icon, children, themeColor, themeBorder }: { to: string; icon: React.ReactNode; children: React.ReactNode; themeColor: string; themeBorder: string }) {
    return (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-sm text-sm transition-all duration-200 group relative border-l-2 ${isActive
                    ? `bg-[#00F0FF]/10 ${themeColor} ${themeBorder} font-medium`
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

function MobileNav({ themeColor, themeBg, themeBorder }: { themeColor: string; themeBg: string; themeBorder: string }) {
    const { logout } = useAuth()

    return (
        <Sheet>
            <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className={`md:hidden ${themeColor}`}>
                    <Menu />
                </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 bg-metal-900 border-r border-border p-0">
                <SheetTitle className="sr-only">Menú</SheetTitle>
                <SheetDescription className="sr-only">Navegación Móvil</SheetDescription>

                <div className="p-6 border-b border-white/5 flex items-center gap-3">
                    <div className={`w-8 h-8 ${themeBg} rounded-none flex items-center justify-center text-black font-bold font-display text-lg`}>P</div>
                    <h1 className="font-display font-bold text-xl tracking-tighter text-white">HAW<span className={themeColor}>.PRO</span></h1>
                </div>

                <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
                    <SideLink to="/provider" icon={<Activity size={18} />} themeColor={themeColor} themeBorder={themeBorder}>DASHBOARD</SideLink>
                    <SideLink to="/provider/integration" icon={<Database size={18} />} themeColor={themeColor} themeBorder={themeBorder}>INTEGRATION</SideLink>
                    <SideLink to="/provider/docs" icon={<FileText size={18} />} themeColor={themeColor} themeBorder={themeBorder}>API_DOCS</SideLink>
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
