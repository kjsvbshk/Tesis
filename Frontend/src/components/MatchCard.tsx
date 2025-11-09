import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { useBetStore, type BetType } from '@/store/bets'

export interface Match {
  id: string
  home: string
  away: string
  odds: {
    home: number
    away: number
    over: number
    under: number
  }
  aiHomeWinProb?: number // 0..1
}

export function MatchCard({ match, delay = 0 }: { match: Match; delay?: number }) {
  const addBet = useBetStore((s) => s.addBet)

  const add = (type: BetType) => {
    const label = `${match.home} vs ${match.away} · ${type.toUpperCase()}`
    const odd = match.odds[type]
    addBet({ id: `${match.id}-${type}`, matchId: match.id, eventLabel: label, type, odd })
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20, scale: 0.95 }} 
      animate={{ opacity: 1, y: 0, scale: 1 }} 
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      whileHover={{ scale: 1.02, y: -2 }}
      className="football-pattern"
    >
      <Card className="bg-card/80 backdrop-blur border-border/50 overflow-hidden">
        <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
              ⚽
            </div>
            <span className="font-semibold">{match.home} vs {match.away}</span>
          </div>
          {typeof match.aiHomeWinProb === 'number' && (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-xs text-muted-foreground">
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
        className="justify-between rounded-lg h-12 bg-gradient-to-r from-green-500/10 to-blue-500/10 border-green-500/20 hover:from-green-500/20 hover:to-blue-500/20 hover:border-green-400/40 transition-all duration-200" 
        onClick={onClick}
      >
        <span className="text-sm font-medium">{label}</span>
        <span className="text-base font-bold text-green-400">{odd.toFixed(2)}</span>
      </Button>
    </motion.div>
  )
}


