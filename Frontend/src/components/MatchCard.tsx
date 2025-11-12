import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { useBetStore, type BetType } from '@/store/bets'

export interface Match {
  id: string | number
  home: string
  away: string
  odds: {
    home: number
    away: number
    over: number
    under: number
  }
  aiHomeWinProb?: number // 0..1
  gameId?: number
  homeTeamId?: number
  awayTeamId?: number
  overUnderValue?: number
}

export function MatchCard({ match, delay = 0 }: { match: Match; delay?: number }) {
  const addBet = useBetStore((s) => s.addBet)

  const add = (type: BetType) => {
    const label = `${match.home} vs ${match.away} · ${type.toUpperCase()}`
    const odd = match.odds[type]
    addBet({ 
      id: `${match.id}-${type}`, 
      matchId: match.id, 
      eventLabel: label, 
      type, 
      odd,
      gameId: match.gameId,
      homeTeamId: match.homeTeamId,
      awayTeamId: match.awayTeamId,
      overUnderValue: match.overUnderValue,
    })
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20, scale: 0.95 }} 
      animate={{ opacity: 1, y: 0, scale: 1 }} 
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      whileHover={{ scale: 1.02, y: -2 }}
      className="football-pattern"
    >
      <Card className="bg-[#1C2541] border-[#1C2541]/50 overflow-hidden hover:border-[#00FF73]/30 transition-all duration-300">
        <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg font-heading">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#00FF73] to-[#0B132B] rounded-full flex items-center justify-center text-white font-bold text-sm neon-glow-green shadow-lg">
              ⚽
            </div>
            <span className="font-semibold text-white">{match.home} vs {match.away}</span>
          </div>
          {typeof match.aiHomeWinProb === 'number' && (
            <div className="flex items-center gap-2 px-3 py-1 bg-[#00FF73]/10 rounded-full border border-[#00FF73]/30">
              <div className="w-2 h-2 bg-[#00FF73] rounded-full animate-pulse neon-glow-green"></div>
              <span className="text-xs text-[#B0B3C5] font-mono font-medium">
                IA: {(match.aiHomeWinProb * 100).toFixed(0)}% {match.home}
              </span>
            </div>
          )}
        </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <OddButton label="1" odd={match.odds.home} onClick={() => add('home')} />
          <OddButton label="X" odd={match.odds.away} onClick={() => add('away')} />
          <OddButton label="Over 2.5" odd={match.odds.over} onClick={() => add('over')} />
          <OddButton label="Under 2.5" odd={match.odds.under} onClick={() => add('under')} />
        </CardContent>
      </Card>
    </motion.div>
  )
}

function OddButton({ label, odd, onClick }: { label: string; odd: number; onClick: () => void }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <Button 
        variant="secondary" 
        className="justify-between rounded-lg h-14 bg-[#0B132B] border border-[#1C2541] hover:border-[#00FF73]/50 hover:bg-[#1C2541] transition-all duration-300 hover:shadow-[0_0_15px_rgba(0,255,115,0.3)]" 
        onClick={onClick}
      >
        <span className="text-sm font-medium text-white">{label}</span>
        <span className="text-base font-mono font-bold text-neon-green">{odd.toFixed(2)}</span>
      </Button>
    </motion.div>
  )
}


