/**
 * DataSyncPage — Panel de sincronización de datos NBA desde ESPN.
 * Permite al admin disparar un sync de partidos y ver el resultado.
 */

import { useState } from 'react'
import { RefreshCw, CheckCircle, AlertTriangle, Calendar, Database, Zap } from 'lucide-react'
import { adminService } from '@/services/admin.service'
import { useToast } from '@/hooks/use-toast'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface SyncResult {
  message: string
  dates_queried: [string, string]
  games_fetched: number
  games_synced: number
  fetch_errors: string[]
  synced_at: string
}

export function DataSyncPage() {
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<SyncResult | null>(null)
  const [daysBack, setDaysBack] = useState(3)
  const [daysForward, setDaysForward] = useState(14)

  const handleSync = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await adminService.syncGames(daysBack, daysForward)
      setResult(res)
      toast({
        title: 'Sync completado',
        description: `${res.games_synced} partidos sincronizados desde ESPN.`,
      })
    } catch (err: any) {
      toast({
        title: 'Error en sync',
        description: err?.message || 'No se pudo conectar con ESPN.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-4xl font-display font-semibold text-white tracking-tight">
          DATA <span className="text-[#00FF73]">SYNC</span>
        </h1>
        <p className="text-muted-foreground font-mono text-sm uppercase tracking-widest">
          Sincronización de partidos NBA desde ESPN API
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Config + trigger */}
        <Card className="bg-metal-900/50 border-white/10">
          <CardHeader>
            <CardTitle className="font-mono text-sm uppercase tracking-widest text-white flex items-center gap-2">
              <Zap size={16} className="text-[#00FF73]" />
              Configurar Sync
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs font-mono">
              Rango de fechas a sincronizar desde la API de ESPN Scoreboard.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                  Días hacia atrás
                </label>
                <input
                  type="number"
                  min={0}
                  max={14}
                  value={daysBack}
                  onChange={(e) => setDaysBack(Number(e.target.value))}
                  className="w-full bg-void border border-white/10 rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#00FF73]/50"
                />
                <p className="text-[10px] text-muted-foreground font-mono">
                  Actualiza scores de partidos recientes
                </p>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
                  Días hacia adelante
                </label>
                <input
                  type="number"
                  min={0}
                  max={21}
                  value={daysForward}
                  onChange={(e) => setDaysForward(Number(e.target.value))}
                  className="w-full bg-void border border-white/10 rounded px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-[#00FF73]/50"
                />
                <p className="text-[10px] text-muted-foreground font-mono">
                  Carga partidos futuros programados
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground border border-white/5 bg-white/5 p-3 rounded">
              <Calendar size={14} className="text-[#00FF73] shrink-0" />
              <span>
                Se sincronizará desde{' '}
                <span className="text-white">hoy − {daysBack}d</span>
                {' '}hasta{' '}
                <span className="text-white">hoy + {daysForward}d</span>
                {' '}({daysBack + daysForward + 1} días total)
              </span>
            </div>

            <Button
              onClick={handleSync}
              disabled={loading}
              className="w-full bg-[#00FF73] hover:bg-[#00FF73]/80 text-black font-mono font-bold uppercase tracking-widest"
            >
              {loading ? (
                <>
                  <RefreshCw size={16} className="mr-2 animate-spin" />
                  Sincronizando...
                </>
              ) : (
                <>
                  <RefreshCw size={16} className="mr-2" />
                  Iniciar Sync
                </>
              )}
            </Button>

            {loading && (
              <p className="text-xs font-mono text-muted-foreground text-center animate-pulse">
                Consultando ESPN API · Esto puede tardar hasta 30s...
              </p>
            )}
          </CardContent>
        </Card>

        {/* Resultado */}
        <Card className="bg-metal-900/50 border-white/10">
          <CardHeader>
            <CardTitle className="font-mono text-sm uppercase tracking-widest text-white flex items-center gap-2">
              <Database size={16} className="text-[#00FF73]" />
              Resultado
            </CardTitle>
            <CardDescription className="text-muted-foreground text-xs font-mono">
              Estadísticas del último sync ejecutado.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result === null && !loading && (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Database size={32} className="mb-3 opacity-30" />
                <p className="text-xs font-mono uppercase tracking-widest">Sin resultados aún</p>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle size={16} className="text-[#00FF73]" />
                  <span className="text-xs font-mono text-[#00FF73] uppercase tracking-wider">
                    {result.message}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <StatBox label="Partidos encontrados" value={result.games_fetched} />
                  <StatBox label="Partidos sincronizados" value={result.games_synced} accent />
                </div>

                <div className="text-xs font-mono text-muted-foreground border border-white/5 bg-white/5 p-3 rounded space-y-1">
                  <div>
                    <span className="text-white/50">Rango: </span>
                    <span className="text-white">{result.dates_queried[0]} → {result.dates_queried[1]}</span>
                  </div>
                  <div>
                    <span className="text-white/50">Sincronizado: </span>
                    <span className="text-white">{new Date(result.synced_at).toLocaleString()}</span>
                  </div>
                </div>

                {result.fetch_errors.length > 0 && (
                  <div className="border border-yellow-500/30 bg-yellow-500/5 rounded p-3 space-y-1">
                    <div className="flex items-center gap-2 text-yellow-400 text-xs font-mono uppercase tracking-wider mb-2">
                      <AlertTriangle size={13} />
                      {result.fetch_errors.length} errores de fetch
                    </div>
                    {result.fetch_errors.slice(0, 5).map((e, i) => (
                      <p key={i} className="text-[10px] font-mono text-yellow-400/70">{e}</p>
                    ))}
                    {result.fetch_errors.length > 5 && (
                      <p className="text-[10px] font-mono text-yellow-400/50">
                        ...y {result.fetch_errors.length - 5} más
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info box */}
      <Card className="bg-metal-900/50 border-white/10">
        <CardContent className="pt-5">
          <div className="grid gap-3 md:grid-cols-3 text-xs font-mono text-muted-foreground">
            <div className="space-y-1">
              <p className="text-white uppercase tracking-widest text-[10px]">¿Qué hace el sync?</p>
              <p>Consulta la ESPN Scoreboard API para cada fecha del rango y hace upsert en <span className="text-white">espn.games</span>. Los partidos nuevos se insertan; los existentes se actualizan solo si tienen scores nuevos.</p>
            </div>
            <div className="space-y-1">
              <p className="text-white uppercase tracking-widest text-[10px]">¿Cuándo ejecutarlo?</p>
              <p>Al inicio de cada jornada (para cargar partidos del día) y después de que terminen los partidos (para actualizar scores). También al inicio de temporada para cargar el calendario completo.</p>
            </div>
            <div className="space-y-1">
              <p className="text-white uppercase tracking-widest text-[10px]">Caché invalidado</p>
              <p>Después del sync se invalidan automáticamente los cachés de <span className="text-white">/matches/upcoming</span> y <span className="text-white">/predict/upcoming</span> para que el frontend refleje los datos nuevos.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function StatBox({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div className={`border rounded p-3 text-center ${accent ? 'border-[#00FF73]/30 bg-[#00FF73]/5' : 'border-white/10 bg-white/5'}`}>
      <div className={`text-2xl font-display font-bold ${accent ? 'text-[#00FF73]' : 'text-white'}`}>
        {value}
      </div>
      <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider mt-1">
        {label}
      </div>
    </div>
  )
}
