import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

import { SidebarLayout } from '@/components/layout/SidebarLayout'
import { HomePage } from '@/pages/HomePage'
import { MatchesPage } from '@/pages/MatchesPage'
import { BetsPage } from '@/pages/BetsPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ProfilePage } from '@/pages/ProfilePage'

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        element: <SidebarLayout />,
        children: [
          { index: true, element: <HomePage /> },
          { path: 'partidos', element: <MatchesPage /> },
          { path: 'apuestas', element: <BetsPage /> },
          { path: 'historial', element: <HistoryPage /> },
          { path: 'perfil', element: <ProfilePage /> },
        ],
      },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
