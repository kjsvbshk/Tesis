/**
 * Admin Home Page
 * Dashboard principal para administradores
 */

import { motion } from 'framer-motion'
import { Users, Shield, BarChart3, FileText, Activity } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { usePermissions } from '@/contexts/PermissionsContext'
import { useEffect, useState } from 'react'
import { metricsService, type SystemMetrics } from '@/services/metrics.service'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'

export function AdminHomePage() {
  const { userRoles } = usePermissions()
  const { toast } = useToast()
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMetrics()
  }, [])

  const loadMetrics = async () => {
    try {
      const data = await metricsService.getMetrics()
      setMetrics(data)
    } catch (error: any) {
      console.error('Error loading metrics:', error)
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar las métricas del sistema',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-heading font-bold bg-gradient-to-r from-[#00FF73] via-[#00D95F] to-[#FFD700] bg-clip-text text-transparent mb-3 drop-shadow-[0_0_15px_rgba(0,255,115,0.5)]">
          Panel de Administración
        </h1>
        <p className="text-[#B0B3C5] text-lg font-medium">
          Gestión completa del sistema HAW
        </p>
      </motion.div>

      {/* Quick Stats */}
      {metrics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <StatCard
            title="Total Requests"
            value={metrics.requests.total.toString()}
            icon={<Activity size={24} />}
            description={`${metrics.requests.completed} completados`}
            link="/admin/metricas"
          />
          <StatCard
            title="Tasa de Éxito"
            value={`${metrics.requests.success_rate}%`}
            icon={<BarChart3 size={24} />}
            description={`${metrics.requests.failed} fallidos`}
            link="/admin/metricas"
          />
          <StatCard
            title="Logs de Auditoría"
            value={metrics.audit.total_logs.toString()}
            icon={<FileText size={24} />}
            description="Registros totales"
            link="/admin/auditoria"
          />
          <StatCard
            title="Eventos Outbox"
            value={metrics.outbox.total_events.toString()}
            icon={<Activity size={24} />}
            description={`${metrics.outbox.unpublished_events} pendientes`}
            link="/admin/monitoreo"
          />
        </motion.div>
      )}

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <QuickActionCard
          title="Gestión de Usuarios"
          description="Configurar usuarios, roles y permisos"
          icon={<Users size={32} />}
          link="/admin/usuarios"
        />
        <QuickActionCard
          title="Roles y Permisos"
          description="Administrar roles y permisos del sistema"
          icon={<Shield size={32} />}
          link="/admin/roles"
        />
        <QuickActionCard
          title="Métricas y Monitoreo"
          description="Supervisar rendimiento y disponibilidad"
          icon={<BarChart3 size={32} />}
          link="/admin/metricas"
        />
        <QuickActionCard
          title="Auditoría"
          description="Ver registros de auditoría completos"
          icon={<FileText size={32} />}
          link="/admin/auditoria"
        />
        <QuickActionCard
          title="Búsqueda Avanzada"
          description="Buscar requests, logs y eventos"
          icon={<Activity size={32} />}
          link="/admin/buscar"
        />
        <QuickActionCard
          title="Proveedores"
          description="Gestionar proveedores externos"
          icon={<Activity size={32} />}
          link="/admin/proveedores"
        />
      </motion.div>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  description,
  link,
}: {
  title: string
  value: string
  icon: React.ReactNode
  description: string
  link?: string
}) {
  const content = (
    <Card className="bg-[#1C2541]/50 border-[#1C2541] hover:border-[#00FF73]/30 transition-all">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-[#B0B3C5]">{title}</CardTitle>
        <div className="text-[#00FF73]">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-white">{value}</div>
        <p className="text-xs text-[#B0B3C5] mt-1">{description}</p>
      </CardContent>
    </Card>
  )

  if (link) {
    return <Link to={link}>{content}</Link>
  }

  return content
}

function QuickActionCard({
  title,
  description,
  icon,
  link,
}: {
  title: string
  description: string
  icon: React.ReactNode
  link: string
}) {
  return (
    <Link to={link}>
      <Card className="bg-[#1C2541]/50 border-[#1C2541] hover:border-[#00FF73]/30 hover:bg-[#1C2541]/70 transition-all cursor-pointer">
        <CardHeader>
          <div className="text-[#00FF73] mb-2">{icon}</div>
          <CardTitle className="text-white">{title}</CardTitle>
          <CardDescription className="text-[#B0B3C5]">{description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  )
}

