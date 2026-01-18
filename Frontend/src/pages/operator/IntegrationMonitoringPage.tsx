/**
 * Integration Monitoring Page
 * Monitoreo en tiempo real de proveedores y circuit breakers
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, XCircle, AlertTriangle, RefreshCw, Zap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { providersService, type Provider, type ProviderStatus } from '@/services/providers.service'
import { useToast } from '@/hooks/use-toast'

export function IntegrationMonitoringPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderStatus>>({})
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
    if (autoRefresh) {
      const interval = setInterval(loadData, 10000) // Refresh every 10 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const loadData = async () => {
    try {
      setLoading(true)
      const providersData = await providersService.getProviders()
      setProviders(providersData)

      // Load status for each provider
      const statusPromises = providersData.map(async (provider) => {
        try {
          const status = await providersService.getProviderStatus(provider.code)
          return { code: provider.code, status }
        } catch (error) {
          return { code: provider.code, status: null }
        }
      })

      const statuses = await Promise.all(statusPromises)
      const statusMap: Record<string, ProviderStatus> = {}
      statuses.forEach(({ code, status }) => {
        if (status) {
          statusMap[code] = status
        }
      })
      setProviderStatuses(statusMap)
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

  const getCircuitBreakerColor = (state: string) => {
    switch (state.toLowerCase()) {
      case 'closed':
        return 'text-[#00FF73]'
      case 'open':
        return 'text-red-500'
      case 'half_open':
        return 'text-yellow-500'
      default:
        return 'text-[#B0B3C5]'
    }
  }

  const getCircuitBreakerLabel = (state: string) => {
    switch (state.toLowerCase()) {
      case 'closed':
        return 'Cerrado (Normal)'
      case 'open':
        return 'Abierto (Fallando)'
      case 'half_open':
        return 'Semi-Abierto (Recuperando)'
      default:
        return state
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
            Monitoreo de Integraciones
          </h1>
          <p className="text-[#B0B3C5]">Estado en tiempo real de proveedores y circuit breakers</p>
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
            <RefreshCw size={16} className="mr-2" />
            Actualizar
          </Button>
        </div>
      </motion.div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Total Proveedores</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{providers.length}</div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Activos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#00FF73]">
              {providers.filter(p => p.is_active).length}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Circuit Breakers Cerrados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#00FF73]">
              {Object.values(providerStatuses).filter(s => s.circuit_breaker?.state === 'closed').length}
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Circuit Breakers Abiertos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">
              {Object.values(providerStatuses).filter(s => s.circuit_breaker?.state === 'open').length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Provider Status List */}
      <div className="grid gap-4">
        {loading ? (
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardContent className="flex justify-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
            </CardContent>
          </Card>
        ) : providers.length === 0 ? (
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardContent className="text-center py-8">
              <p className="text-[#B0B3C5]">No hay proveedores configurados</p>
            </CardContent>
          </Card>
        ) : (
          providers.map((provider) => {
            const status = providerStatuses[provider.code]
            const circuitBreakerState = status?.circuit_breaker?.state || 'unknown'

            return (
              <Card key={provider.id} className="bg-[#1C2541]/50 border-[#1C2541]">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {provider.is_active ? (
                        <CheckCircle className="text-[#00FF73]" size={24} />
                      ) : (
                        <XCircle className="text-red-500" size={24} />
                      )}
                      <div>
                        <CardTitle className="text-white">{provider.name}</CardTitle>
                        <p className="text-sm text-[#B0B3C5] font-mono">{provider.code}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {provider.is_active ? (
                        <Badge className="bg-[#00FF73] text-black">Activo</Badge>
                      ) : (
                        <Badge variant="destructive">Inactivo</Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <div>
                      <p className="text-xs text-[#B0B3C5] mb-1">Timeout</p>
                      <p className="text-white font-medium">{provider.timeout_seconds}s</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#B0B3C5] mb-1">Máximo Reintentos</p>
                      <p className="text-white font-medium">{provider.max_retries}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#B0B3C5] mb-1">Umbral Circuit Breaker</p>
                      <p className="text-white font-medium">{provider.circuit_breaker_threshold}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#B0B3C5] mb-1">Estado Circuit Breaker</p>
                      {status ? (
                        <div className="flex items-center gap-2">
                          <Zap className={getCircuitBreakerColor(circuitBreakerState)} size={16} />
                          <p className={`font-medium ${getCircuitBreakerColor(circuitBreakerState)}`}>
                            {getCircuitBreakerLabel(circuitBreakerState)}
                          </p>
                        </div>
                      ) : (
                        <p className="text-[#B0B3C5]">No disponible</p>
                      )}
                    </div>
                  </div>
                  {status?.circuit_breaker && (
                    <div className="mt-4 pt-4 border-t border-[#1C2541]">
                      <div className="grid gap-2 md:grid-cols-3">
                        <div>
                          <p className="text-xs text-[#B0B3C5] mb-1">Fallos</p>
                          <p className="text-white font-medium">
                            {status.circuit_breaker.failure_count || 0}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-[#B0B3C5] mb-1">Último Fallo</p>
                          <p className="text-white font-medium text-sm">
                            {status.circuit_breaker.last_failure
                              ? new Date(status.circuit_breaker.last_failure).toLocaleString()
                              : 'N/A'}
                          </p>
                        </div>
                        {status.circuit_breaker.state === 'open' && (
                          <div>
                            <AlertTriangle className="text-yellow-500 inline mr-2" size={16} />
                            <span className="text-yellow-500 text-sm">
                              Circuit breaker abierto - Revisar proveedor
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
