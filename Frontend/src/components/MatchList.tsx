import { MatchCard, type Match } from '@/components/MatchCard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useEffect, useState } from 'react'
import { matchesService, type MatchResponse } from '@/services/matches.service'
import { predictionsService, type PredictionResponse } from '@/services/predictions.service'
import { useToast } from '@/hooks/use-toast'
import { Activity, CalendarDays, Zap } from 'lucide-react'

function probToOdds(prob: number): number {
  if (!prob || prob <= 0 || prob >= 1) return 1.90
  return Math.max(1.01, parseFloat((1 / prob).toFixed(2)))
}

function roundHalf(n: number): number {
  return Math.round(n * 2) / 2
}

/** Calcula odds de over/under basado en el total predicho vs la línea.
 *  Si predicted_total está por encima de la línea, el over tiene odds más bajos.
 *  Si está por debajo, el under tiene odds más bajos. */
function ouOdds(predictedTotal: number, line: number): { over: number; under: number } {
  const diff = predictedTotal - line
  const abs = Math.abs(diff)
  // Ajuste máximo de 0.30 (para diferencias >= 10 puntos)
  const adjustment = Math.min(abs * 0.03, 0.30)
  if (diff > 1.5) {
    // predicted > line → over más probable
    return { over: parseFloat((1.90 - adjustment).toFixed(2)), under: parseFloat((1.90 + adjustment).toFixed(2)) }
  } else if (diff < -1.5) {
    // predicted < line → under más probable
    return { over: parseFloat((1.90 + adjustment).toFixed(2)), under: parseFloat((1.90 - adjustment).toFixed(2)) }
  }
  return { over: 1.90, under: 1.90 }
}

export function MatchList() {
  const [todayMatches, setTodayMatches] = useState<MatchResponse[]>([])
  const [upcomingMatches, setUpcomingMatches] = useState<MatchResponse[]>([])
  const [predictions, setPredictions] = useState<Map<number, PredictionResponse>>(new Map())
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadMatches()
  }, [])

  const loadMatches = async () => {
    try {
      setLoading(true)
      const [today, upcoming] = await Promise.all([
        matchesService.getTodayMatches(),
        matchesService.getUpcomingMatches(7)
      ])
      setTodayMatches(today)
      setUpcomingMatches(upcoming)

      const allMatches = [...today, ...upcoming]
      const predMap = new Map<number, PredictionResponse>()
      await Promise.allSettled(
        allMatches.map(async (m) => {
          try {
            const pred = await predictionsService.getGamePrediction(m.id as number)
            predMap.set(m.id as number, pred)
          } catch {
            // partido sin prediccion disponible
          }
        })
      )
      setPredictions(predMap)
    } catch (error: unknown) {
      console.error('Error loading matches:', error)
      toast({
        title: 'CONNECTION ERROR',
        description: 'Failed to retrieve match data.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const convertToMatch = (matchResponse: MatchResponse, pred?: PredictionResponse): Match => {
    const homeOdds = pred ? probToOdds(pred.home_win_probability) : (matchResponse.home_odds || 0)
    const awayOdds = pred ? probToOdds(pred.away_win_probability) : (matchResponse.away_odds || 0)
    const ouLine = pred ? roundHalf(pred.predicted_total) : (matchResponse.over_under || 220.5)
    const { over: overOdd, under: underOdd } = pred
      ? ouOdds(pred.predicted_total, ouLine)
      : { over: 1.90, under: 1.90 }

    return {
      id: matchResponse.id,
      home: matchResponse.home_team?.name || 'Home Team',
      away: matchResponse.away_team?.name || 'Away Team',
      odds: { home: homeOdds, away: awayOdds, over: overOdd, under: underOdd },
      overUnderLine: ouLine,
      aiHomeWinProb: pred?.home_win_probability,
      gameId: matchResponse.id,
      homeTeamId: matchResponse.home_team_id,
      awayTeamId: matchResponse.away_team_id,
      overUnderValue: ouLine,
    }
  }

  // Dedup por game ID para evitar que el mismo partido aparezca múltiples veces
  const todayMatchesConverted = Array.from(
    todayMatches.reduce<Map<number, Match>>((acc, m) => {
      if (m.home_team?.name !== 'TBD' && m.away_team?.name !== 'TBD' && !acc.has(m.id as number)) {
        acc.set(m.id as number, convertToMatch(m, predictions.get(m.id as number)))
      }
      return acc
    }, new Map()).values()
  )

  const upcomingMatchesConverted = Array.from(
    upcomingMatches.reduce<Map<number, Match>>((acc, m) => {
      if (m.home_team?.name !== 'TBD' && m.away_team?.name !== 'TBD' && !acc.has(m.id)) {
        acc.set(m.id, convertToMatch(m, predictions.get(m.id as number)))
      }
      return acc
    }, new Map()).values()
  )

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="size-12 border-2 border-acid-500 rounded-none animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Zap size={16} className="text-acid-500 animate-pulse" />
            </div>
          </div>
          <div className="text-acid-500 font-mono text-xs uppercase tracking-widest animate-pulse">
            SCANNING MATCH NETWORK...
          </div>
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
