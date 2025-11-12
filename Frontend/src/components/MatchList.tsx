import { MatchCard, type Match } from '@/components/MatchCard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useEffect, useState } from 'react'
import { matchesService, type MatchResponse } from '@/services/matches.service'
import { useToast } from '@/hooks/use-toast'

export function MatchList() {
  const [todayMatches, setTodayMatches] = useState<MatchResponse[]>([])
  const [upcomingMatches, setUpcomingMatches] = useState<MatchResponse[]>([])
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
    } catch (error: any) {
      console.error('Error loading matches:', error)
      toast({
        title: 'Error',
        description: 'Error al cargar los partidos',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const convertToMatch = (matchResponse: MatchResponse): Match => {
    // Calcular cuotas por defecto si no existen
    const homeOdds = matchResponse.home_odds || 1.90
    const awayOdds = matchResponse.away_odds || 1.90
    const overUnder = matchResponse.over_under || 220.5
    
    // Calcular cuotas over/under basadas en el total
    const overOdds = 1.85
    const underOdds = 1.95

    return {
      id: matchResponse.id,
      home: matchResponse.home_team.name,
      away: matchResponse.away_team.name,
      odds: {
        home: homeOdds,
        away: awayOdds,
        over: overOdds,
        under: underOdds,
      },
      gameId: matchResponse.id,
      homeTeamId: matchResponse.home_team_id,
      awayTeamId: matchResponse.away_team_id,
      overUnderValue: overUnder,
    }
  }

  const todayMatchesConverted = todayMatches.map(convertToMatch)
  const upcomingMatchesConverted = upcomingMatches.map(convertToMatch)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
      </div>
    )
  }

  return (
    <Tabs defaultValue="today" className="space-y-4 relative">
      <TabsList className="grid grid-cols-2 w-full">
        <TabsTrigger value="today">Hoy</TabsTrigger>
        <TabsTrigger value="upcoming">Próximos 7 días</TabsTrigger>
      </TabsList>

      <TabsContent value="today" className="space-y-3 nba-watermark">
        {todayMatchesConverted.length === 0 ? (
          <div className="text-center py-8 text-[#B0B3C5]">
            No hay partidos programados para hoy
          </div>
        ) : (
          todayMatchesConverted.map((m, index) => (
            <MatchCard key={m.id} match={m} delay={index * 0.08} />
          ))
        )}
      </TabsContent>

      <TabsContent value="upcoming" className="space-y-3 relative nba-watermark">
        {upcomingMatchesConverted.length === 0 ? (
          <div className="text-center py-8 text-[#B0B3C5]">
            No hay partidos programados para los próximos 7 días
          </div>
        ) : (
          upcomingMatchesConverted.map((m, index) => (
            <MatchCard key={m.id} match={m} delay={index * 0.08} />
          ))
        )}
      </TabsContent>
    </Tabs>
  )
}


