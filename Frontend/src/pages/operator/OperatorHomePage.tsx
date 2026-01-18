/**
 * Operator Home Page
 * Dashboard principal para operadores
 */

import { motion } from 'framer-motion'
import { Activity, Database, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useEffect, useState } from 'react'
import { metricsService, type SystemMetrics } from '@/services/metrics.service'
import { providersService, type Provider } from '@/services/providers.service'
import { Link } from 'react-router-dom'
import { useToast } from '@/hooks/use-toast'

export function OperatorHomePage() {
  const { toast } = useToast()
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [metricsData, providersData] = await Promise.all([
        metricsService.getMetrics(),
        providersService.getProviders().catch(() => []), // Si falla, usar array vacío
      ])
      setMetrics(metricsData)
      setProviders(providersData)
    } catch (error: any) {
      console.error('Error loading data:', error)
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar datos del dashboard',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const activeProviders = providers.filter(p => p.is_active).length
  const inactiveProviders = providers.filter(p => !p.is_active).length

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-heading font-bold bg-gradient-to-r from-[#00FF73] via-[#00D95F] to-[#FFD700] bg-clip-text text-transparent mb-3 drop-shadow-[0_0_15px_rgba(0,255,115,0.5)]">
          Panel de Operador
        </h1>
        <p className="text-[#B0B3C5] text-lg font-medium">
          Gestión de proveedores y sincronizaciones
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
            title="Proveedores Activos"
            value={activeProviders.toString()}
            icon={<CheckCircle size={24} />}
            description={`${inactiveProviders} inactivos`}
            link="/operator/proveedores"
          />
          <StatCard
            title="Requests Totales"
            value={metrics.requests.total.toString()}
            icon={<Activity size={24} />}
            description={`${metrics.requests.completed} completados`}
            link="/operator/sincronizacion"
          />
          <StatCard
            title="Tasa de Éxito"
            value={`${metrics.requests.success_rate.toFixed(1)}%`}
            icon={<RefreshCw size={24} />}
            description={`${metrics.requests.failed} fallidos`}
            link="/operator/monitoreo"
          />
          <StatCard
            title="Eventos Outbox"
            value={metrics.outbox.unpublished_events.toString()}
            icon={<Database size={24} />}
            description="Pendientes de publicación"
            link="/operator/monitoreo"
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
          title="Gestión de Proveedores"
          description="Configurar y administrar proveedores externos"
          icon={<Activity size={32} />}
          link="/operator/proveedores"
        />
        <QuickActionCard
          title="Monitoreo de Integraciones"
          description="Estado en tiempo real de proveedores y circuit breakers"
          icon={<AlertCircle size={32} />}
          link="/operator/monitoreo"
        />
        <QuickActionCard
          title="Registros de Sincronización"
          description="Historial y logs de sincronizaciones"
          icon={<RefreshCw size={32} />}
          link="/operator/sincronizacion"
        />
      </motion.div>

      {/* Provider Status Summary */}
      {providers.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white">Resumen de Proveedores</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2">
                {providers.slice(0, 5).map((provider) => (
                  <div
                    key={provider.id}
                    className="flex items-center justify-between p-3 bg-[#0B132B] border border-[#1C2541] rounded-lg"
                  >
                    <div>
                      <p className="text-white font-medium">{provider.name}</p>
                      <p className="text-sm text-[#B0B3C5]">{provider.code}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {provider.is_active ? (
                        <CheckCircle className="text-[#00FF73]" size={20} />
                      ) : (
                        <AlertCircle className="text-red-500" size={20} />
                      )}
                      <span className={`text-sm ${provider.is_active ? 'text-[#00FF73]' : 'text-red-500'}`}>
                        {provider.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                  </div>
                ))}
                {providers.length > 5 && (
                  <Link
                    to="/operator/proveedores"
                    className="text-center text-[#00FF73] hover:text-[#00D95F] text-sm font-medium mt-2"
                  >
                    Ver todos los proveedores →
                  </Link>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
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
          <p className="text-sm text-[#B0B3C5] mt-1">{description}</p>
        </CardHeader>
      </Card>
    </Link>
  )
}
