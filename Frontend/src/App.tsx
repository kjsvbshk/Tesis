import { Outlet } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans selection:bg-acid-500 selection:text-black noise-bg">
      <div className="scanlines absolute inset-0 z-50 pointer-events-none opacity-20 h-full fixed" />
      <div className="relative z-10 w-full h-full">
        <Outlet />
      </div>
      <Toaster />
    </div>
  )
}

export default App
