import { MatchCard, type Match } from '@/components/MatchCard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

const nbaMatches: Match[] = [
  { id: 'nba-1', home: 'Lakers', away: 'Warriors', odds: { home: 1.95, away: 1.85, over: 2.05, under: 1.80 }, aiHomeWinProb: 0.52 },
  { id: 'nba-2', home: 'Celtics', away: 'Heat', odds: { home: 1.75, away: 2.10, over: 1.90, under: 1.90 }, aiHomeWinProb: 0.60 },
  { id: 'nba-3', home: 'Bucks', away: 'Knicks', odds: { home: 1.60, away: 2.30, over: 1.88, under: 1.92 }, aiHomeWinProb: 0.63 },
]

const uclMatches: Match[] = [
  { id: 'ucl-1', home: 'Real Madrid', away: 'Manchester City', odds: { home: 1.85, away: 1.95, over: 1.90, under: 1.90 }, aiHomeWinProb: 0.52 },
  { id: 'ucl-2', home: 'Barcelona', away: 'Bayern Munich', odds: { home: 2.10, away: 1.75, over: 2.05, under: 1.80 }, aiHomeWinProb: 0.45 },
]

const eplMatches: Match[] = [
  { id: 'epl-1', home: 'Arsenal', away: 'Manchester United', odds: { home: 1.90, away: 1.92, over: 1.95, under: 1.85 }, aiHomeWinProb: 0.54 },
  { id: 'epl-2', home: 'Liverpool', away: 'Chelsea', odds: { home: 1.88, away: 1.94, over: 1.92, under: 1.88 }, aiHomeWinProb: 0.51 },
]

export function MatchList() {
  return (
    <Tabs defaultValue="nba" className="space-y-4 relative">
      <TabsList className="grid grid-cols-3 w-full">
        <TabsTrigger value="nba">NBA</TabsTrigger>
        <TabsTrigger value="ucl">Champions</TabsTrigger>
        <TabsTrigger value="epl">Premier League</TabsTrigger>
      </TabsList>

      <TabsContent value="nba" className="space-y-3 nba-watermark">
        {nbaMatches.map((m, index) => (
          <MatchCard key={m.id} match={m} delay={index * 0.08} />
        ))}
      </TabsContent>

      <TabsContent value="ucl" className="space-y-3 relative ucl-watermark">
        {uclMatches.map((m, index) => (
          <MatchCard key={m.id} match={m} delay={index * 0.08} />
        ))}
      </TabsContent>

      <TabsContent value="epl" className="space-y-3 relative epl-watermark">
        {eplMatches.map((m, index) => (
          <MatchCard key={m.id} match={m} delay={index * 0.08} />
        ))}
      </TabsContent>
    </Tabs>
  )
}


