import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { useBetStore, type BetType } from '@/store/bets'
import { Crosshair } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import type { MatchSentiment } from '@/services/matches.service'

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
  overUnderLine?: number
  aiHomeWinProb?: number
  gameId?: number
  homeTeamId?: number
  awayTeamId?: number
  overUnderValue?: number
}

export function MatchCard({ match, delay = 0, sentiment = null }: {
  match: Match
  delay?: number
  sentiment?: MatchSentiment | null
}) {
  const addBet = useBetStore((s) => s.addBet)
  const { toast } = useToast()

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
    toast({
      title: "BET ADDED",
      description: `${label} @ ${odd.toFixed(2)}`,
      variant: "success",
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay, ease: "easeOut" }}
      className="w-full relative group"
    >
      <div className="absolute -left-[1px] top-4 bottom-4 w-[2px] bg-white/10 group-hover:bg-acid-500 transition-colors duration-300" />
      <Card className="bg-metal-900/40 border-white/5 hover:border-acid-500/30 transition-all duration-300 overflow-hidden backdrop-blur-sm">
        <CardContent className="p-0">
          <div className="flex flex-col md:flex-row md:items-center">
            <div className="flex-1 p-5 border-b md:border-b-0 md:border-r border-white/5 relative">
              <div className="absolute top-0 right-0 p-1">
                {typeof match.aiHomeWinProb === 'number' && (
                  <div className="flex items-center gap-1.5 bg-black/40 px-2 py-1 rounded border border-white/5">
                    <Crosshair size={12} className="text-electric-violet" />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">
                      AI PROB:{' '}
                      <span className="text-electric-violet font-bold">
                        {(match.aiHomeWinProb * 100).toFixed(0)}%
                      </span>
                    </span>
                  </div>
                )}
              </div>
              <div className="flex flex-col justify-center h-full gap-3 pt-2">
                <div className="flex items-center justify-between">
                  <span className="text-xl font-display font-bold text-white group-hover:text-acid-500 transition-colors tracking-tight">{match.home}</span>
                  <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest bg-white/5 px-2 py-0.5 rounded">HOME</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <div className="h-px bg-white/10 w-full" />
                  <span className="text-xs font-mono font-bold text-acid-500 mx-2">VS</span>
                  <div className="h-px bg-white/10 w-full" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-display font-bold text-white group-hover:text-white/80 transition-colors tracking-tight">{match.away}</span>
                  <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest bg-white/5 px-2 py-0.5 rounded">AWAY</span>
                </div>
              </div>
            </div>
            <div className="p-4 bg-black/20 flex-shrink-0 flex flex-col gap-3">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                <OddButton label="1" odd={match.odds.home} onClick={() => add('home')} highlight="acid" />
                <OddButton label="2" odd={match.odds.away} onClick={() => add('away')} />
                <OddButton label={match.overUnderLine ? `O ${match.overUnderLine}` : 'O/U'} odd={match.odds.over} onClick={() => add('over')} />
                <OddButton label={match.overUnderLine ? `U ${match.overUnderLine}` : 'O/U'} odd={match.odds.under} onClick={() => add('under')} />
              </div>
              {sentiment && sentiment.total_bets > 0 && (
                <SentimentBar
                  homePct={sentiment.home_pct ?? 0}
                  awayPct={sentiment.away_pct ?? 0}
                  totalBets={sentiment.total_bets}
                />
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function SentimentBar({ homePct, awayPct, totalBets }: {
  homePct: number
  awayPct: number
  totalBets: number
}) {
  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-wider">
          HAW SENTIMENT · {totalBets} bet{totalBets !== 1 ? 's' : ''}
        </span>
        <span className="text-[9px] font-mono text-muted-foreground">{homePct}% / {awayPct}%</span>
      </div>
      <div className="h-1 w-full rounded-full bg-white/10 overflow-hidden flex">
        <div
          className="h-full bg-acid-500 transition-all duration-500"
          style={{ width: `${homePct}%` }}
        />
        <div
          className="h-full bg-electric-violet transition-all duration-500"
          style={{ width: `${awayPct}%` }}
        />
      </div>
      <div className="flex justify-between mt-0.5">
        <span className="text-[9px] font-mono text-acid-500">HOME</span>
        <span className="text-[9px] font-mono text-electric-violet">AWAY</span>
      </div>
    </div>
  )
}

function OddButton({ label, odd, onClick, highlight }: {
  label: string; odd: number; onClick: () => void; highlight?: 'acid' | 'violet'
}) {
  const hasOdd = odd > 0
  return (
    <Button
      variant="ghost"
      onClick={hasOdd ? onClick : undefined}
      disabled={!hasOdd}
      className="h-14 flex flex-col items-center justify-center gap-0.5 bg-metal-900 border border-white/5 hover:bg-white/5 hover:border-acid-500/50 rounded-sm w-full min-w-[80px] group/btn transition-all relative overflow-hidden disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <span className="text-[10px] font-mono text-muted-foreground uppercase">{label}</span>
      <span className={`text-lg font-mono font-bold ${highlight === 'acid' ? 'text-white' : 'text-acid-500'} group-hover/btn:text-white transition-colors`}>
        {hasOdd ? odd.toFixed(2) : '—'}
      </span>
      {hasOdd && <div className="absolute inset-0 bg-acid-500/10 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-200" />}
    </Button>
  )
}
