/**
 * MatchupPage
 *
 * Predice el resultado de un enfrentamiento entre dos equipos NBA
 * sin necesitar un game_id. Usa el endpoint POST /predict/matchup
 * que corre LiveFeatureExtractor con las estadísticas más recientes.
 */

import { useState } from 'react'
import { Swords, TrendingUp, AlertCircle, Loader2, RotateCcw } from 'lucide-react'
import { apiRequest } from '@/lib/api'

// ─── tipos ───────────────────────────────────────────────────────────────────

interface TeamPropsBundle {
  home: { reb?: number | null; ast?: number | null; stl?: number | null; blk?: number | null; to?: number | null }
  away: { reb?: number | null; ast?: number | null; stl?: number | null; blk?: number | null; to?: number | null }
}

interface MatchupResponse {
  home_team_name: string
  away_team_name: string
  game_date: string | null
  home_win_probability: number
  away_win_probability: number
  predicted_home_score: number
  predicted_away_score: number
  predicted_total: number
  predicted_margin?: number | null
  team_props?: TeamPropsBundle | null
  recommended_bet: string
  expected_value: number
  confidence_score: number
  model_version: string
  inference_latency_ms?: number | null
  model_signals?: Record<string, number> | null
}

// ─── equipos NBA ─────────────────────────────────────────────────────────────

const NBA_TEAMS = [
  { name: 'Atlanta Hawks',          tricode: 'ATL' },
  { name: 'Boston Celtics',         tricode: 'BOS' },
  { name: 'Brooklyn Nets',          tricode: 'BKN' },
  { name: 'Charlotte Hornets',      tricode: 'CHA' },
  { name: 'Chicago Bulls',          tricode: 'CHI' },
  { name: 'Cleveland Cavaliers',    tricode: 'CLE' },
  { name: 'Dallas Mavericks',       tricode: 'DAL' },
  { name: 'Denver Nuggets',         tricode: 'DEN' },
  { name: 'Detroit Pistons',        tricode: 'DET' },
  { name: 'Golden State Warriors',  tricode: 'GSW' },
  { name: 'Houston Rockets',        tricode: 'HOU' },
  { name: 'Indiana Pacers',         tricode: 'IND' },
  { name: 'LA Clippers',            tricode: 'LAC' },
  { name: 'Los Angeles Lakers',     tricode: 'LAL' },
  { name: 'Memphis Grizzlies',      tricode: 'MEM' },
  { name: 'Miami Heat',             tricode: 'MIA' },
  { name: 'Milwaukee Bucks',        tricode: 'MIL' },
  { name: 'Minnesota Timberwolves', tricode: 'MIN' },
  { name: 'New Orleans Pelicans',   tricode: 'NOP' },
  { name: 'New York Knicks',        tricode: 'NYK' },
  { name: 'Oklahoma City Thunder',  tricode: 'OKC' },
  { name: 'Orlando Magic',          tricode: 'ORL' },
  { name: 'Philadelphia 76ers',     tricode: 'PHI' },
  { name: 'Phoenix Suns',           tricode: 'PHX' },
  { name: 'Portland Trail Blazers', tricode: 'POR' },
  { name: 'Sacramento Kings',       tricode: 'SAC' },
  { name: 'San Antonio Spurs',      tricode: 'SAS' },
  { name: 'Toronto Raptors',        tricode: 'TOR' },
  { name: 'Utah Jazz',              tricode: 'UTA' },
  { name: 'Washington Wizards',     tricode: 'WAS' },
]

// ─── helpers ─────────────────────────────────────────────────────────────────

function ProbBar({ prob, color }: { prob: number; color: string }) {
  const pct = Math.round(prob * 100)
  return (
    <div className="flex items-center gap-3">
      <span className="text-2xl font-bold text-white w-12 text-right">{pct}%</span>
      <div className="flex-1 h-3 rounded-full bg-gray-800 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function StatRow({ label, home, away }: { label: string; home?: number | null; away?: number | null }) {
  if (home == null && away == null) return null
  return (
    <div className="flex items-center justify-between text-sm py-1 border-b border-white/5">
      <span className="text-white font-medium w-16 text-right">{home != null ? home.toFixed(1) : '—'}</span>
      <span className="text-gray-400 mx-3">{label}</span>
      <span className="text-white font-medium w-16">{away != null ? away.toFixed(1) : '—'}</span>
    </div>
  )
}

// ─── componente principal ────────────────────────────────────────────────────

export default function MatchupPage() {
  const [homeTeam, setHomeTeam] = useState('')
  const [awayTeam, setAwayTeam] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MatchupResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canPredict = homeTeam && awayTeam && homeTeam !== awayTeam

  const handlePredict = async () => {
    if (!canPredict) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await apiRequest<MatchupResponse>('/predict/matchup', {
        method: 'POST',
        body: JSON.stringify({ home_team: homeTeam, away_team: awayTeam }),
        timeout: 60000, // ML cold start en Render free tier puede tomar ~60s
      })
      setResult(data)
    } catch (e: any) {
      const msg = e?.message || 'Error al calcular la predicción'
      if (msg.includes('503')) {
        setError('El modelo ML no está disponible en este momento.')
      } else if (msg.includes('422')) {
        setError('No hay suficientes datos históricos para uno de los equipos seleccionados.')
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setResult(null)
    setError(null)
    setHomeTeam('')
    setAwayTeam('')
  }

  const winnerName = result
    ? result.home_win_probability >= result.away_win_probability
      ? result.home_team_name
      : result.away_team_name
    : null

  const betLabel: Record<string, string> = {
    home: 'Local gana',
    away: 'Visitante gana',
    none: 'Sin apuesta clara',
  }

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-violet-600/20">
          <Swords size={24} className="text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Predicción de Enfrentamiento</h1>
          <p className="text-gray-400 text-sm">
            Selecciona dos equipos y el modelo calculará la probabilidad de victoria basándose en sus estadísticas reales.
          </p>
        </div>
      </div>

      {/* Selector */}
      {!result && (
        <div className="bg-[#1C2541]/60 border border-white/10 rounded-xl p-6 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Local */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-violet-400 uppercase tracking-wider">
                Equipo Local (Home)
              </label>
              <select
                value={homeTeam}
                onChange={e => setHomeTeam(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 transition-colors"
              >
                <option value="">— Seleccionar equipo —</option>
                {NBA_TEAMS.filter(t => t.name !== awayTeam).map(t => (
                  <option key={t.tricode} value={t.name}>{t.name}</option>
                ))}
              </select>
            </div>

            {/* Visitante */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-gray-400 uppercase tracking-wider">
                Equipo Visitante (Away)
              </label>
              <select
                value={awayTeam}
                onChange={e => setAwayTeam(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-gray-500 transition-colors"
              >
                <option value="">— Seleccionar equipo —</option>
                {NBA_TEAMS.filter(t => t.name !== homeTeam).map(t => (
                  <option key={t.tricode} value={t.name}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Preview del matchup */}
          {homeTeam && awayTeam && (
            <div className="flex items-center justify-center gap-4 py-2">
              <span className="text-white font-semibold">{homeTeam}</span>
              <span className="text-violet-400 font-bold text-lg">VS</span>
              <span className="text-white font-semibold">{awayTeam}</span>
            </div>
          )}

          <button
            onClick={handlePredict}
            disabled={!canPredict || loading}
            className="w-full py-3 rounded-lg font-semibold text-sm transition-all
              bg-violet-600 hover:bg-violet-500 text-white
              disabled:opacity-40 disabled:cursor-not-allowed
              flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Calculando predicción…
              </>
            ) : (
              <>
                <TrendingUp size={16} />
                Calcular probabilidad
              </>
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-900/20 border border-red-500/30 rounded-lg">
              <AlertCircle size={18} className="text-red-400 mt-0.5 shrink-0" />
              <p className="text-red-300 text-sm">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Resultado */}
      {result && (
        <div className="space-y-4">
          {/* Cabecera del resultado */}
          <div className="bg-[#1C2541]/60 border border-violet-500/30 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="text-xs font-mono text-violet-400 uppercase tracking-wider">
                Resultado del modelo · {result.model_version}
              </div>
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
              >
                <RotateCcw size={13} />
                Nueva predicción
              </button>
            </div>

            {/* Equipos y scores */}
            <div className="grid grid-cols-3 items-center gap-4 mb-6">
              <div className="text-center">
                <p className="text-white font-bold text-lg leading-tight">{result.home_team_name}</p>
                <p className="text-xs text-violet-400 font-mono mt-1">LOCAL</p>
                <p className="text-4xl font-bold text-white mt-3">{result.predicted_home_score}</p>
              </div>
              <div className="text-center">
                <p className="text-gray-500 text-sm font-mono">VS</p>
                <div className="mt-2 px-3 py-1 bg-violet-600/20 rounded-full">
                  <p className="text-violet-300 text-xs font-mono">total: {result.predicted_total}</p>
                </div>
              </div>
              <div className="text-center">
                <p className="text-white font-bold text-lg leading-tight">{result.away_team_name}</p>
                <p className="text-xs text-gray-400 font-mono mt-1">VISITANTE</p>
                <p className="text-4xl font-bold text-white mt-3">{result.predicted_away_score}</p>
              </div>
            </div>

            {/* Barras de probabilidad */}
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-400 mb-1">{result.home_team_name}</p>
                <ProbBar prob={result.home_win_probability} color="bg-violet-500" />
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">{result.away_team_name}</p>
                <ProbBar prob={result.away_win_probability} color="bg-gray-500" />
              </div>
            </div>
          </div>

          {/* Recomendación */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-[#1C2541]/60 border border-white/10 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-400 font-mono uppercase mb-2">Ganador predicho</p>
              <p className="text-white font-bold">{winnerName}</p>
            </div>
            <div className="bg-[#1C2541]/60 border border-white/10 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-400 font-mono uppercase mb-2">Confianza</p>
              <p className="text-white font-bold">{Math.round(result.confidence_score * 100)}%</p>
            </div>
            <div className={`border rounded-xl p-4 text-center ${
              result.recommended_bet === 'none'
                ? 'bg-gray-900/40 border-white/10'
                : 'bg-violet-600/20 border-violet-500/40'
            }`}>
              <p className="text-xs text-gray-400 font-mono uppercase mb-2">Recomendación</p>
              <p className={`font-bold ${result.recommended_bet === 'none' ? 'text-gray-400' : 'text-violet-300'}`}>
                {betLabel[result.recommended_bet] ?? result.recommended_bet}
              </p>
              {result.recommended_bet !== 'none' && (
                <p className="text-xs text-gray-400 mt-1">EV: {result.expected_value > 0 ? '+' : ''}{result.expected_value.toFixed(3)}</p>
              )}
            </div>
          </div>

          {/* Team props */}
          {result.team_props && (
            <div className="bg-[#1C2541]/60 border border-white/10 rounded-xl p-5">
              <p className="text-xs font-mono text-gray-400 uppercase tracking-wider mb-4">
                Estadísticas proyectadas por equipo
              </p>
              <div className="flex text-xs text-gray-500 justify-between mb-2">
                <span className="w-16 text-right text-violet-400">{result.home_team_name.split(' ').pop()}</span>
                <span className="mx-3" />
                <span className="w-16 text-gray-400">{result.away_team_name.split(' ').pop()}</span>
              </div>
              <StatRow label="Rebotes"     home={result.team_props.home.reb}  away={result.team_props.away.reb} />
              <StatRow label="Asistencias" home={result.team_props.home.ast}  away={result.team_props.away.ast} />
              <StatRow label="Robos"       home={result.team_props.home.stl}  away={result.team_props.away.stl} />
              <StatRow label="Bloqueos"    home={result.team_props.home.blk}  away={result.team_props.away.blk} />
              <StatRow label="Pérdidas"    home={result.team_props.home.to}   away={result.team_props.away.to} />
            </div>
          )}

          {/* Meta */}
          <div className="flex justify-between text-xs text-gray-600 font-mono px-1">
            <span>Inferencia: {result.inference_latency_ms ?? '—'}ms</span>
            {result.model_signals?.rf_probability != null && (
              <span>RF prob: {(result.model_signals.rf_probability * 100).toFixed(1)}%</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
