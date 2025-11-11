import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from '@/contexts/AuthContext'

import { SidebarLayout } from '@/components/layout/SidebarLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { PublicRoute } from '@/components/PublicRoute'
import { HomePage } from '@/pages/HomePage'
import { MatchesPage } from '@/pages/MatchesPage'
import { BetsPage } from '@/pages/BetsPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'


// Create router with AuthProvider wrapper
const routerWithAuth = createBrowserRouter([
  {
    path: '/',
    element: (
      <AuthProvider>
        <App />
      </AuthProvider>
    ),
    children: [
      {
        path: 'login',
        element: (
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        ),
      },
      {
        path: 'registro',
        element: (
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        ),
      },
      {
        element: (
          <ProtectedRoute>
            <SidebarLayout />
          </ProtectedRoute>
        ),
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
    <RouterProvider router={routerWithAuth} />
  </StrictMode>,
)
