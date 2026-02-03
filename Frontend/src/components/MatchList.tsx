import { MatchCard, type Match } from '@/components/MatchCard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useEffect, useState } from 'react'
import { matchesService, type MatchResponse } from '@/services/matches.service'
import { useToast } from '@/hooks/use-toast'
import { Activity, CalendarDays, Zap } from 'lucide-react'

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
        title: 'CONNECTION ERROR',
        description: 'Failed to retrieve match data.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const convertToMatch = (matchResponse: MatchResponse): Match => {
    // Default odds logic
    const homeOdds = matchResponse.home_odds || 1.90
    const awayOdds = matchResponse.away_odds || 1.90
    const overUnder = matchResponse.over_under || 220.5

    // Default over/under odds
    const overOdds = 1.85
    const underOdds = 1.95

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
      <div className="flex h-64 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-12 h-12 border-2 border-acid-500 rounded-none animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <Zap size={16} className="text-acid-500 animate-pulse" />
            </div>
          </div>
          <div className="text-acid-500 font-mono text-xs uppercase tracking-widest animate-pulse">SCANNING MATCH NETWORK...</div>
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
          <span className="w-2 h-2 rounded-full bg-acid-500 animate-pulse" />
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


