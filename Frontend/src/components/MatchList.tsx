import { MatchCard, type Match } from '@/components/MatchCard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useEffect, useRef, useState } from 'react'
import { matchesService, type MatchResponse } from '@/services/matches.service'
import { predictionsService, type PredictionResponse } from '@/services/predictions.service'
import { useToast } from '@/hooks/use-toast'
import { Activity, CalendarDays, Zap } from 'lucide-react'

/** Convierte probabilidad ML → cuota decimal (sin margen de casa) */
function probToOdds(prob: number): number {
  if (!prob || prob <= 0 || prob >= 1) return 1.90
  return Math.max(1.01, parseFloat((1 / prob).toFixed(2)))
}

/** Redondea el total al 0.5 más cercano para la línea O/U */
function roundHalf(n: number): number {
  return Math.round(n * 2) / 2
}

export function MatchList() {
  const [todayMatches, setTodayMatches] = useState<MatchResponse[]>([])
  const [upcomingMatches, setUpcomingMatches] = useState<MatchResponse[]>([])
  const [predictions, setPredictions] = useState<Map<number, PredictionResponse>>(new Map())
  // loading is only used as a guard, not rendered — using useRef to avoid re-render
  const loading = useRef(true)
  const { toast } = useToast()

  useEffect(() => {
    loadMatches()
  }, [])

  const loadMatches = async () => {
    try {
      loading.current = true
      const [today, upcoming] = await Promise.all([
        matchesService.getTodayMatches(),
        matchesService.getUpcomingMatches(7)
      ])
      setTodayMatches(today)
      setUpcomingMatches(upcoming)

      // Obtener predicciones ML para derivar cuotas reales por partido
      const allMatches = [...today, ...upcoming]
      const predMap = new Map<number, PredictionResponse>()
      await Promise.allSettled(
        allMatches.map(async (m) => {
          try {
            const pred = await predictionsService.getGamePrediction(m.id as number)
            predMap.set(m.id as number, pred)
          } catch {
            // Partido sin predicción disponible — se usarán cuotas de la DB o N/A
          }
        })
      )
      setPredictions(predMap)
    } catch (error: any) {
      console.error('Error loading matches:', error)
      toast({
        title: 'CONNECTION ERROR',
        description: 'Failed to retrieve match data.',
        variant: 'destructive',
      })
    } finally {
      loading.current = false
    }
  }

  const convertToMatch = (matchResponse: MatchResponse, pred?: PredictionResponse): Match => {
    // Cuotas derivadas del modelo ML (odds = 1/probabilidad)
    // Si no hay predicción disponible, usar cuotas de la DB o marcar como N/A (1.00 = placeholder)
    const homeOdds = pred
      ? probToOdds(pred.home_win_probability)
      : matchResponse.home_odds || 0   // 0 = sin dato

    const awayOdds = pred
      ? probToOdds(pred.away_win_probability)
      : matchResponse.away_odds || 0

    // Línea O/U: usar total predicho por el modelo, o fallback de DB, o estándar NBA
    const ouLine = pred
      ? roundHalf(pred.predicted_total)
      : (matchResponse.over_under || 220.5)

    // Cuotas O/U: el modelo no predice probabilidad over/under → cuotas neutras 1.90
    const overOdds  = 1.90
    const underOdds = 1.90

    return {
      id: matchResponse.id,
      home: matchResponse.home_team?.name || 'Home Team',
      away: matchResponse.away_team?.name || 'Away Team',
      odds: {
        home: homeOdds,
        away: awayOdds,
        over: overOdds,
        under: underOdds,
      },
      overUnderLine: ouLine,
      aiHomeWinProb: pred?.home_win_probability,
      gameId: matchResponse.id,
      homeTeamId: matchResponse.home_team_id,
      awayTeamId: matchResponse.away_team_id,
      overUnderValue: ouLine,
    }
  }

  const todayMatchesConverted = todayMatches.reduce<ReturnType<typeof convertToMatch>[]>((acc, m) => {
    if (m.home_team?.name !== 'TBD' && m.away_team?.name !== 'TBD') {
      acc.push(convertToMatch(m, predictions.get(m.id as number)))
    }
    return acc
  }, [])

  // Deduplicate and convert in a single pass
  const upcomingMatchesConverted = Array.from(
    upcomingMatches.reduce<Map<number, ReturnType<typeof convertToMatch>>>((acc, m) => {
      if (m.home_team?.name !== 'TBD' && m.away_team?.name !== 'TBD' && !acc.has(m.id)) {
        acc.set(m.id, convertToMatch(m, predictions.get(m.id as number)))
      }
      return acc
    }, new Map()).values()
  )

  if (loading.current) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="size-12 border-2 border-acid-500 rounded-none animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Zap size={16} className="text-acid-500 animate-pulse" />
            </div>
          </div>
          <div className="text-acid-500 font-mono text-xs uppercase tracking-widest animate-pulse">SCANNING MATCH NETWORK…</div>
        </div>
      </div>
    )
  }

  return (
    <Tabs defaultValue="today" className="space-y-6">
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <TabsList className="bg-transparent p-0 gap-6">
          <TabTrigger value="today" icon={<Activity size={16} />} label="LIVE / TODAY" />
          <TabTrigger value="upcoming" icon={<CalendarDays size={16} />} label="UPCOMING" />
        </TabsList>
        <div className="hidden md:flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
          <span className="size-2 rounded-full bg-acid-500 animate-pulse" />
          LIVE DATA FEED
        </div>
      </div>

      <TabsContent value="today" className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
        {todayMatchesConverted.length === 0 ? (
          <EmptyState message="NO MATCHES SCHEDULED FOR TODAY" />
        ) : (
          todayMatchesConverted.map((m, index) => (
            <MatchCard key={m.id} match={m} delay={index * 0.05} />
          ))
        )}
      </TabsContent>

      <TabsContent value="upcoming" className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
        {upcomingMatchesConverted.length === 0 ? (
          <EmptyState message="NO UPCOMING MATCHES FOUND" />
        ) : (
          upcomingMatchesConverted.map((m, index) => (
            <MatchCard key={m.id} match={m} delay={index * 0.05} />
          ))
        )}
      </TabsContent>
    </Tabs>
  )
}

function TabTrigger({ value, icon, label }: { value: string; icon: React.ReactNode; label: string }) {
  return (
    <TabsTrigger
      value={value}
      className="data-[state=active]:bg-transparent data-[state=active]:text-acid-500 data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-acid-500 rounded-none border-b-2 border-transparent px-0 py-2 gap-2 font-mono font-bold text-muted-foreground hover:text-white transition-colors uppercase tracking-wide"
    >
      {icon}
      {label}
    </TabsTrigger>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 border border-dashed border-white/10 rounded-lg bg-white/5">
      <Activity size={32} className="text-muted-foreground mb-4 opacity-50" />
      <p className="font-mono text-sm text-muted-foreground uppercase tracking-widest">{message}</p>
    </div>
  )
}


