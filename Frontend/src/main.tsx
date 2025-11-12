import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from '@/contexts/AuthContext'
import { PermissionsProvider } from '@/contexts/PermissionsContext'

import { SidebarLayout } from '@/components/layout/SidebarLayout'
import { AdminLayout } from '@/components/layout/AdminLayout'
import { OperatorLayout } from '@/components/layout/OperatorLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RoleProtectedRoute } from '@/components/RoleProtectedRoute'
import { PublicRoute } from '@/components/PublicRoute'
import { HomePage } from '@/pages/HomePage'
import { MatchesPage } from '@/pages/MatchesPage'
import { BetsPage } from '@/pages/BetsPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { PredictionsPage } from '@/pages/PredictionsPage'
import { RequestsPage } from '@/pages/RequestsPage'
import { AdminHomePage } from '@/pages/admin/AdminHomePage'
import { UsersManagementPage } from '@/pages/admin/UsersManagementPage'
import { RolesManagementPage } from '@/pages/admin/RolesManagementPage'
import { MetricsDashboardPage } from '@/pages/admin/MetricsDashboardPage'
import { AuditManagementPage } from '@/pages/admin/AuditManagementPage'
import { AdvancedSearchPage } from '@/pages/admin/AdvancedSearchPage'
import { MonitoringPage } from '@/pages/admin/MonitoringPage'


// Create router with AuthProvider and PermissionsProvider wrapper
const routerWithAuth = createBrowserRouter([
  {
    path: '/',
    element: (
      <AuthProvider>
        <PermissionsProvider>
          <App />
        </PermissionsProvider>
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
      // Admin routes (check first to redirect admins)
      {
        path: 'admin',
        element: (
          <RoleProtectedRoute allowedRoles={['admin']}>
            <AdminLayout />
          </RoleProtectedRoute>
        ),
        children: [
          { index: true, element: <AdminHomePage /> },
          { path: 'usuarios', element: <UsersManagementPage /> },
          { path: 'roles', element: <RolesManagementPage /> },
          { path: 'metricas', element: <MetricsDashboardPage /> },
          { path: 'auditoria', element: <AuditManagementPage /> },
          { path: 'buscar', element: <AdvancedSearchPage /> },
          { path: 'proveedores', element: <div>Providers Management (to be created)</div> },
          { path: 'monitoreo', element: <MonitoringPage /> },
          { path: 'configuracion', element: <div>Configuration (to be created)</div> },
        ],
      },
      // Operator routes
      {
        path: 'operator',
        element: (
          <RoleProtectedRoute allowedRoles={['operator']}>
            <OperatorLayout />
          </RoleProtectedRoute>
        ),
        children: [
          { index: true, element: <div>Operator Home (to be created)</div> },
          { path: 'proveedores', element: <div>Providers Management (to be created)</div> },
          { path: 'monitoreo', element: <div>Integration Monitoring (to be created)</div> },
          { path: 'sincronizacion', element: <div>Sync Records (to be created)</div> },
        ],
      },
      // User routes (default layout) - exclude admins and operators
      {
        element: (
          <ProtectedRoute>
            <SidebarLayout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <HomePage /> },
          { path: 'partidos', element: <MatchesPage /> },
          { path: 'predicciones', element: <PredictionsPage /> },
          { path: 'apuestas', element: <BetsPage /> },
          { path: 'historial', element: <HistoryPage /> },
          { path: 'requests', element: <RequestsPage /> },
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
