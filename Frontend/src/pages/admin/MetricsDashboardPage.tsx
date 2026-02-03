/**
 * Metrics Dashboard Page
 * Displays system metrics and performance data
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, Activity, TrendingUp, Clock, AlertCircle, RefreshCcw } from 'lucide-react'
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
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-acid-500/20 border-t-acid-500 rounded-full animate-spin" />
          <div className="text-acid-500 font-mono text-sm animate-pulse">LOADING METRICS...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-white mb-1">
            SYSTEM METRICS
          </h1>
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
            Real-time performance monitoring
          </p>
        </div>
        <Button onClick={loadMetrics} variant="outline" className="border-acid-500/20 hover:bg-acid-500/10 text-acid-500">
          <RefreshCcw size={16} className="mr-2" />
          REFRESH DATA
        </Button>
      </div>

      {/* Filters */}
      <Card className="bg-metal-900/50 border-white/10 backdrop-blur-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Time Range Filter</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3 items-end">
            <div>
              <Label htmlFor="dateFrom" className="text-xs uppercase text-muted-foreground mb-1.5 block">From</Label>
              <Input
                id="dateFrom"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="bg-black/50 border-white/10 text-white font-mono h-9"
              />
            </div>
            <div>
              <Label htmlFor="dateTo" className="text-xs uppercase text-muted-foreground mb-1.5 block">To</Label>
              <Input
                id="dateTo"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="bg-black/50 border-white/10 text-white font-mono h-9"
              />
            </div>
            <Button onClick={handleFilter} className="w-full bg-white text-black hover:bg-gray-200 font-mono text-xs font-bold h-9">
              APPLY FILTER
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* System Metrics */}
      {metrics && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <MetricCard
            title="TOTAL REQUESTS"
            value={metrics.requests.total.toString()}
            icon={<Activity size={18} />}
            description={`${metrics.requests.completed} completed`}
            trend={metrics.requests.success_rate}
          />
          <MetricCard
            title="SUCCESS RATE"
            value={`${metrics.requests.success_rate.toFixed(1)}%`}
            icon={<TrendingUp size={18} />}
            description={`${metrics.requests.failed} failed`}
            trend={metrics.requests.success_rate}
          />
          <MetricCard
            title="AUDIT LOGS"
            value={metrics.audit.total_logs.toString()}
            icon={<BarChart3 size={18} />}
            description="Total entries"
          />
          <MetricCard
            title="OUTBOX EVENTS"
            value={metrics.outbox.total_events.toString()}
            icon={<Clock size={18} />}
            description={`${metrics.outbox.unpublished_events} pending`}
          />
        </motion.div>
      )}

      {/* Request Metrics */}
      {requestMetrics && (
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="bg-metal-900 border-white/10 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-acid-500" />
            <CardHeader className="border-b border-white/5 bg-white/5 py-4">
              <CardTitle className="text-white flex items-center gap-2 font-display text-lg">
                <Activity size={20} className="text-acid-500" />
                REQUEST ANALYTICS
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-6">
              <div className="flex justify-between items-center bg-black/30 p-3 rounded border border-white/5">
                <span className="text-muted-foreground font-mono text-xs uppercase">Total Volume</span>
                <span className="text-white font-mono font-bold text-lg">{requestMetrics.requests.total}</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded border border-white/5 bg-acid-500/5">
                  <div className="text-acid-500 font-mono text-xs uppercase mb-1">Completed</div>
                  <div className="text-white font-mono font-bold">{requestMetrics.requests.completed}</div>
                </div>
                <div className="p-3 rounded border border-white/5 bg-alert-red/5">
                  <div className="text-alert-red font-mono text-xs uppercase mb-1">Failed</div>
                  <div className="text-white font-mono font-bold">{requestMetrics.requests.failed}</div>
                </div>
              </div>

              <div className="flex justify-between items-center pt-2 border-t border-white/5">
                <span className="text-muted-foreground font-mono text-xs uppercase">Current Processing</span>
                <span className="text-yellow-500 font-mono font-bold">{requestMetrics.requests.processing}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-metal-900 border-white/10 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-electric-violet" />
            <CardHeader className="border-b border-white/5 bg-white/5 py-4">
              <CardTitle className="text-white flex items-center gap-2 font-display text-lg">
                <TrendingUp size={20} className="text-electric-violet" />
                PERFORMANCE
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 pt-6">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-muted-foreground font-mono text-xs uppercase">Avg Latency</span>
                  <span className="text-electric-violet font-mono font-bold">
                    {requestMetrics.performance.avg_latency_ms ? `${requestMetrics.performance.avg_latency_ms.toFixed(2)}ms` : 'N/A'}
                  </span>
                </div>
                <div className="h-1 w-full bg-metal-800 rounded-full overflow-hidden">
                  <div className="h-full bg-electric-violet w-[35%]" />
                </div>
              </div>

              <div className="p-4 bg-black/30 border border-white/5 rounded">
                <div className="text-xs text-muted-foreground font-mono uppercase mb-1">Total Predictions</div>
                <div className="text-3xl font-display font-bold text-white tracking-tight">{requestMetrics.performance.total_predictions}</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Cache Status */}
      {metrics && (
        <Card className="bg-metal-900 border-white/10">
          <CardHeader className="py-4 border-b border-white/5">
            <CardTitle className="text-white flex items-center gap-2 font-mono text-sm uppercase tracking-wider">
              <BarChart3 size={16} className="text-acid-500" />
              Redis Cache Status
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="bg-black/40 p-4 rounded border border-white/5 text-center">
                <div className="text-2xl font-display font-bold text-white mb-1">{metrics.cache.total_entries}</div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Total Entries</div>
              </div>
              <div className="bg-acid-500/10 p-4 rounded border border-acid-500/20 text-center">
                <div className="text-2xl font-display font-bold text-acid-500 mb-1">{metrics.cache.active_entries}</div>
                <div className="text-[10px] uppercase tracking-widest text-acid-500/70">Active</div>
              </div>
              <div className="bg-metal-800/50 p-4 rounded border border-white/5 text-center">
                <div className="text-2xl font-display font-bold text-yellow-500 mb-1">{metrics.cache.stale_entries}</div>
                <div className="text-[10px] uppercase tracking-widest text-yellow-500/70">Stale</div>
              </div>
              <div className="bg-metal-800/50 p-4 rounded border border-white/5 text-center">
                <div className="text-2xl font-display font-bold text-alert-red mb-1">{metrics.cache.expired_entries}</div>
                <div className="text-[10px] uppercase tracking-widest text-alert-red/70">Expired</div>
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
    <Card className="bg-metal-900 border-white/10 hover:border-acid-500/50 transition-colors group">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground group-hover:text-white transition-colors">{title}</CardTitle>
        <div className="text-muted-foreground group-hover:text-acid-500 transition-colors">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-display font-bold text-white tracking-tight">{value}</div>
        {description && <p className="text-xs text-muted-foreground mt-1 font-mono">{description}</p>}
        {trend !== undefined && (
          <div className="mt-3 pt-3 border-t border-white/5 flex items-center gap-1">
            {trend >= 90 ? (
              <TrendingUp size={12} className="text-acid-500" />
            ) : (
              <AlertCircle size={12} className="text-yellow-500" />
            )}
            <span className={`text-[10px] font-mono uppercase ${trend >= 90 ? 'text-acid-500' : 'text-yellow-500'}`}>
              {trend >= 90 ? 'System Optimal' : 'Needs Review'}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

