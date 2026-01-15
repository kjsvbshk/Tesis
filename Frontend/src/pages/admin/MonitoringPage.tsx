/**
 * Monitoring Page
 * Real-time system monitoring and health checks
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { metricsService, type HealthStatus, type ReadinessStatus, type SystemMetrics } from '@/services/metrics.service'
import { useToast } from '@/hooks/use-toast'

export function MonitoringPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [readiness, setReadiness] = useState<ReadinessStatus | null>(null)
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
    if (autoRefresh) {
      const interval = setInterval(loadData, 30000) // Refresh every 30 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const loadData = async () => {
    try {
      setLoading(true)
      const [healthData, readinessData, metricsData] = await Promise.all([
        metricsService.getHealth(),
        metricsService.getReadiness(),
        metricsService.getMetrics(),
      ])
      setHealth(healthData)
      setReadiness(readinessData)
      setMetrics(metricsData)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar datos de monitoreo',
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
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
            Monitoreo del Sistema
          </h1>
          <p className="text-[#B0B3C5]">Estado en tiempo real y métricas de salud</p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setAutoRefresh(!autoRefresh)}
            variant={autoRefresh ? 'default' : 'outline'}
            className={autoRefresh ? 'bg-[#00FF73] hover:bg-[#00D95F] text-black' : 'border-[#1C2541] text-[#B0B3C5]'}
          >
            {autoRefresh ? 'Auto-refresh: ON' : 'Auto-refresh: OFF'}
          </Button>
          <Button onClick={loadData} variant="outline" className="border-[#1C2541] text-[#B0B3C5]">
            Actualizar
          </Button>
        </div>
      </motion.div>

      {/* Health Status */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Activity size={20} className="text-[#00FF73]" />
              Health Check
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-4">
                <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
              </div>
            ) : health ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <CheckCircle className="text-[#00FF73]" size={20} />
                  <span className="text-white font-bold">Status: {health.status}</span>
                </div>
                <p className="text-[#B0B3C5] text-sm">Service: {health.service}</p>
                <p className="text-[#B0B3C5] text-sm">Version: {health.version}</p>
                <p className="text-[#B0B3C5] text-xs">
                  {new Date(health.timestamp).toLocaleString()}
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <XCircle className="text-red-500" size={20} />
                <span className="text-red-500">No disponible</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <CheckCircle size={20} className="text-[#00FF73]" />
              Readiness Check
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-4">
                <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
              </div>
            ) : readiness ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {readiness.status === 'ready' ? (
                    <CheckCircle className="text-[#00FF73]" size={20} />
                  ) : (
                    <XCircle className="text-red-500" size={20} />
                  )}
                  <span className="text-white font-bold">Status: {readiness.status}</span>
                </div>
                <div className="flex items-center gap-2">
                  {readiness.database === 'connected' ? (
                    <CheckCircle className="text-[#00FF73]" size={16} />
                  ) : (
                    <XCircle className="text-red-500" size={16} />
                  )}
                  <span className="text-[#B0B3C5] text-sm">Database: {readiness.database}</span>
                </div>
                <p className="text-[#B0B3C5] text-xs">
                  {new Date(readiness.timestamp).toLocaleString()}
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <XCircle className="text-red-500" size={20} />
                <span className="text-red-500">No disponible</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Outbox Status */}
      {metrics && (
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Clock size={20} className="text-[#00FF73]" />
              Estado del Outbox
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <p className="text-[#B0B3C5] text-sm">Total Eventos</p>
                <p className="text-white font-bold text-2xl">{metrics.outbox.total_events}</p>
              </div>
              <div>
                <p className="text-[#B0B3C5] text-sm">Publicados</p>
                <p className="text-[#00FF73] font-bold text-2xl">
                  {metrics.outbox.published_events}
                </p>
              </div>
              <div>
                <p className="text-[#B0B3C5] text-sm">Pendientes</p>
                <p className="text-yellow-500 font-bold text-2xl">
                  {metrics.outbox.unpublished_events}
                </p>
                {metrics.outbox.unpublished_events > 10 && (
                  <Badge variant="destructive" className="mt-2">
                    <AlertTriangle size={12} className="mr-1" />
                    Atención requerida
                  </Badge>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Metrics Summary */}
      {metrics && (
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader>
            <CardTitle className="text-white">Resumen del Sistema</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-[#B0B3C5] text-sm">Total Requests</p>
                <p className="text-white font-bold text-xl">{metrics.requests.total}</p>
              </div>
              <div>
                <p className="text-[#B0B3C5] text-sm">Tasa de Éxito</p>
                <p className="text-white font-bold text-xl">
                  {metrics.requests.success_rate.toFixed(2)}%
                </p>
              </div>
              <div>
                <p className="text-[#B0B3C5] text-sm">Logs de Auditoría</p>
                <p className="text-white font-bold text-xl">{metrics.audit.total_logs}</p>
              </div>
              <div>
                <p className="text-[#B0B3C5] text-sm">Predicciones</p>
                <p className="text-white font-bold text-xl">{metrics.predictions.total}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

