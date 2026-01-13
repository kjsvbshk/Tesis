import { Outlet } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'

function App() {
  return (
    <div className="min-h-screen bg-[#0B132B] text-white">
      <Outlet />
      <Toaster />
    </div>
  )
}

export default App
