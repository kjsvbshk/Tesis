/**
 * UpcomingGamesPage
 *
 * Lista partidos NBA próximos con predicciones calculadas en tiempo real
 * usando el LiveFeatureExtractor del backend.
 */

import { useState, useEffect, useCallback } from 'react'
import { predictionsService, PredictionResponse } from '@/services/predictions.service'

// ─── helpers ────────────────────────────────────────────────────────────────

function probBar(prob: number, color: string) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.round(prob * 100)}%` }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right">
        {(prob * 100).toFixed(1)}%
      </span>
    </div>
  )
}

function confidenceBadge(score: number) {
  if (score >= 0.70) return 'bg-emerald-900/60 text-emerald-300 border border-emerald-700'
  if (score >= 0.60) return 'bg-yellow-900/60 text-yellow-300 border border-yellow-700'
  return 'bg-gray-800 text-gray-400 border border-gray-700'
}

function betLabel(bet: string) {
  if (bet === 'home') return { label: 'Local favorito', cls: 'text-violet-300' }
  if (bet === 'away') return { label: 'Visitante favorito', cls: 'text-cyan-300' }
  return { label: 'Sin señal clara', cls: 'text-gray-500' }
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString('es-CO', { weekday: 'short', month: 'short', day: 'numeric' })
}

// ─── subcomponentes ──────────────────────────────────────────────────────────

function GameCard({ pred }: { pred: PredictionResponse }) {
  const { label: betLbl, cls: betCls } = betLabel(pred.recommended_bet)
  const homeWins = pred.home_win_probability >= pred.away_win_probability

  return (
    <div className="rounded-xl border border-gray-700/60 bg-gray-900/80 backdrop-blur p-5
                    hover:border-violet-600/50 transition-all duration-200 flex flex-col gap-4">

      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 font-mono">
          {formatDate(pred.game_date)} · #{pred.game_id}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${confidenceBadge(pred.confidence_score)}`}>
          Confianza {(pred.confidence_score * 100).toFixed(0)}%
        </span>
      </div>

      {/* Equipos */}
      <div className="grid grid-cols-3 items-center gap-2">
        {/* Home */}
        <div className={`text-right ${homeWins ? 'text-white font-semibold' : 'text-gray-400'}`}>
          <p className="text-sm leading-tight">{pred.home_team_name}</p>
          <p className="text-xs text-gray-500 mt-0.5">Local</p>
        </div>

        {/* VS + scores */}
        <div className="text-center">
          <span className="text-lg font-bold text-gray-600">VS</span>
          <div className="mt-1 flex justify-center gap-1 text-xs text-gray-500">
            <span>{pred.predicted_home_score}</span>
            <span>-</span>
            <span>{pred.predicted_away_score}</span>
          </div>
        </div>

        {/* Away */}
        <div className={`text-left ${!homeWins ? 'text-white font-semibold' : 'text-gray-400'}`}>
          <p className="text-sm leading-tight">{pred.away_team_name}</p>
          <p className="text-xs text-gray-500 mt-0.5">Visitante</p>
        </div>
      </div>

      {/* Barras de probabilidad */}
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-gray-500 mb-0.5">
          <span className="w-3 h-3 rounded-sm bg-violet-500 inline-block" />
          <span>Local</span>
          <span className="flex-1" />
          <span className="w-3 h-3 rounded-sm bg-cyan-500 inline-block" />
          <span>Visitante</span>
        </div>
        {probBar(pred.home_win_probability, 'bg-violet-500')}
        {probBar(pred.away_win_probability, 'bg-cyan-500')}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-gray-800">
        <span className={`text-xs font-medium ${betCls}`}>{betLbl}</span>
        <div className="text-right text-xs text-gray-600">
          <span>Margen pred.: </span>
          <span className="text-gray-400 font-mono">
            {pred.predicted_margin !== undefined && pred.predicted_margin !== null
              ? `${pred.predicted_margin > 0 ? '+' : ''}${pred.predicted_margin.toFixed(1)} pts`
              : '—'}
          </span>
        </div>
      </div>

      {/* Odds si existen */}
      {pred.features_used?.values?.implied_prob_home &&
        !isNaN(pred.features_used.values.implied_prob_home) && (
        <div className="text-xs text-gray-600 border-t border-gray-800 pt-2 flex gap-4">
          <span>Mercado local: <span className="text-gray-400">
            {(pred.features_used.values.implied_prob_home * 100).toFixed(1)}%
          </span></span>
          <span>Mercado visitante: <span className="text-gray-400">
            {(pred.features_used.values.implied_prob_away * 100).toFixed(1)}%
          </span></span>
        </div>
      )}
    </div>
  )
}

// ─── página principal ────────────────────────────────────────────────────────

export default function UpcomingGamesPage() {
  const [predictions, setPredictions] = useState<PredictionResponse[]>([])
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState<string | null>(null)
  const [days, setDays]               = useState(7)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await predictionsService.getUpcomingPredictions(days)
      setPredictions(data)
      setLastRefresh(new Date())
    } catch (e: any) {
      setError(e?.message || 'Error al cargar predicciones')
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Próximos Partidos NBA
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Predicciones calculadas en tiempo real con el modelo v2.2.0
              (35 features · ELO + rolling stats + odds)
            </p>
          </div>

          {/* Controles */}
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5
                         text-sm text-gray-300 focus:outline-none focus:border-violet-500"
            >
              <option value={3}>Próximos 3 días</option>
              <option value={7}>Próximos 7 días</option>
              <option value={14}>Próximas 2 semanas</option>
            </select>

            <button
              onClick={load}
              disabled={loading}
              className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500
                         disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {loading ? 'Cargando…' : 'Actualizar'}
            </button>
          </div>
        </div>

        {lastRefresh && (
          <p className="text-xs text-gray-600 mt-3">
            Última actualización: {lastRefresh.toLocaleTimeString('es-CO')}
          </p>
        )}
      </div>

      {/* Contenido */}
      <div className="max-w-4xl mx-auto">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent
                            rounded-full animate-spin" />
            <p className="text-sm text-gray-500">
              Calculando predicciones en vivo…
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-xl border border-red-800/60 bg-red-950/40 p-6 text-center">
            <p className="text-red-400 font-medium">{error}</p>
            <button
              onClick={load}
              className="mt-3 text-sm text-red-300 underline underline-offset-2"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && predictions.length === 0 && (
          <div className="text-center py-20 text-gray-600">
            <p className="text-lg">No hay partidos programados</p>
            <p className="text-sm mt-1">
              en los próximos {days} días con datos disponibles
            </p>
          </div>
        )}

        {!loading && predictions.length > 0 && (
          <>
            <p className="text-xs text-gray-600 mb-4">
              {predictions.length} partido{predictions.length !== 1 ? 's' : ''} encontrado{predictions.length !== 1 ? 's' : ''}
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              {predictions.map(p => (
                <GameCard key={p.game_id} pred={p} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
