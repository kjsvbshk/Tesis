/**
 * Metrics Dashboard Page
 * Displays system metrics and performance data
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, Activity, TrendingUp, Clock, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { metricsService, type SystemMetrics, type RequestMetrics } from '@/services/metrics.service'
import { useToast } from '@/hooks/use-toast'

export function MetricsDashboardPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [requestMetrics, setRequestMetrics] = useState<RequestMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const { toast } = useToast()

  useEffect(() => {
    loadMetrics()
  }, [])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      const [systemMetrics, reqMetrics] = await Promise.all([
        metricsService.getMetrics(),
        metricsService.getRequestMetrics(dateFrom || undefined, dateTo || undefined),
      ])
      setMetrics(systemMetrics)
      setRequestMetrics(reqMetrics)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar métricas',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFilter = () => {
    loadMetrics()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
          Dashboard de Métricas
        </h1>
        <p className="text-[#B0B3C5]">Monitoreo de rendimiento y disponibilidad del sistema</p>
      </motion.div>

      {/* Filters */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white">Filtros</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="dateFrom" className="text-[#B0B3C5]">
                Fecha Desde
              </Label>
              <Input
                id="dateFrom"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label htmlFor="dateTo" className="text-[#B0B3C5]">
                Fecha Hasta
              </Label>
              <Input
                id="dateTo"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={handleFilter} className="w-full bg-[#00FF73] hover:bg-[#00D95F] text-black">
                Aplicar Filtros
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Metrics */}
      {metrics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <MetricCard
            title="Total Requests"
            value={metrics.requests.total.toString()}
            icon={<Activity size={24} />}
            description={`${metrics.requests.completed} completados`}
            trend={metrics.requests.success_rate}
          />
          <MetricCard
            title="Tasa de Éxito"
            value={`${metrics.requests.success_rate.toFixed(2)}%`}
            icon={<TrendingUp size={24} />}
            description={`${metrics.requests.failed} fallidos`}
            trend={metrics.requests.success_rate}
          />
          <MetricCard
            title="Logs de Auditoría"
            value={metrics.audit.total_logs.toString()}
            icon={<BarChart3 size={24} />}
            description="Registros totales"
          />
          <MetricCard
            title="Eventos Outbox"
            value={metrics.outbox.total_events.toString()}
            icon={<Clock size={24} />}
            description={`${metrics.outbox.unpublished_events} pendientes`}
          />
        </motion.div>
      )}

      {/* Request Metrics */}
      {requestMetrics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid gap-4 md:grid-cols-2"
        >
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Activity size={20} className="text-[#00FF73]" />
                Métricas de Requests
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Total:</span>
                <span className="text-white font-bold">{requestMetrics.requests.total}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Completados:</span>
                <span className="text-[#00FF73] font-bold">{requestMetrics.requests.completed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Fallidos:</span>
                <span className="text-red-500 font-bold">{requestMetrics.requests.failed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">En Proceso:</span>
                <span className="text-yellow-500 font-bold">{requestMetrics.requests.processing}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Tasa de Éxito:</span>
                <span className="text-white font-bold">{requestMetrics.requests.success_rate.toFixed(2)}%</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp size={20} className="text-[#00FF73]" />
                Rendimiento
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Latencia Promedio:</span>
                <span className="text-white font-bold">
                  {requestMetrics.performance.avg_latency_ms
                    ? `${requestMetrics.performance.avg_latency_ms.toFixed(2)} ms`
                    : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#B0B3C5]">Total Predicciones:</span>
                <span className="text-white font-bold">{requestMetrics.performance.total_predictions}</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Cache Status */}
      {metrics && (
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <BarChart3 size={20} className="text-[#00FF73]" />
              Estado del Caché
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <span className="text-[#B0B3C5] text-sm">Total Entradas:</span>
                <p className="text-white font-bold text-xl">{metrics.cache.total_entries}</p>
              </div>
              <div>
                <span className="text-[#B0B3C5] text-sm">Activas:</span>
                <p className="text-[#00FF73] font-bold text-xl">{metrics.cache.active_entries}</p>
              </div>
              <div>
                <span className="text-[#B0B3C5] text-sm">Obsoletas:</span>
                <p className="text-yellow-500 font-bold text-xl">{metrics.cache.stale_entries}</p>
              </div>
              <div>
                <span className="text-[#B0B3C5] text-sm">Expiradas:</span>
                <p className="text-red-500 font-bold text-xl">{metrics.cache.expired_entries}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon,
  description,
  trend,
}: {
  title: string
  value: string
  icon: React.ReactNode
  description?: string
  trend?: number
}) {
  return (
    <Card className="bg-[#1C2541]/50 border-[#1C2541] hover:border-[#00FF73]/30 transition-all">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-[#B0B3C5]">{title}</CardTitle>
        <div className="text-[#00FF73]">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-white">{value}</div>
        {description && <p className="text-xs text-[#B0B3C5] mt-1">{description}</p>}
        {trend !== undefined && (
          <div className="mt-2 flex items-center gap-1">
            {trend >= 90 ? (
              <TrendingUp size={14} className="text-[#00FF73]" />
            ) : (
              <AlertCircle size={14} className="text-yellow-500" />
            )}
            <span className={`text-xs ${trend >= 90 ? 'text-[#00FF73]' : 'text-yellow-500'}`}>
              {trend >= 90 ? 'Excelente' : 'Revisar'}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

