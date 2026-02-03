import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { useBetStore, type BetType } from '@/store/bets'
import { Crosshair } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

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

            {/* Teams Section */}
            <div className="flex-1 p-5 border-b md:border-b-0 md:border-r border-white/5 relative">
              <div className="absolute top-0 right-0 p-1">
                {typeof match.aiHomeWinProb === 'number' && (
                  <div className="flex items-center gap-1.5 bg-black/40 px-2 py-1 rounded border border-white/5">
                    <Crosshair size={12} className="text-electric-violet" />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">AI PROB: <span className="text-electric-violet font-bold">{(match.aiHomeWinProb * 100).toFixed(0)}%</span></span>
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

            {/* Odds Section */}
            <div className="p-4 bg-black/20 flex-shrink-0">
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                <OddButton label="1" odd={match.odds.home} onClick={() => add('home')} highlight="acid" />
                <OddButton label="X" odd={match.odds.away} onClick={() => add('away')} />
                <OddButton label="O 2.5" odd={match.odds.over} onClick={() => add('over')} />
                <OddButton label="U 2.5" odd={match.odds.under} onClick={() => add('under')} />
              </div>
            </div>

          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function OddButton({ label, odd, onClick, highlight }: { label: string; odd: number; onClick: () => void; highlight?: 'acid' | 'violet' }) {
  return (
    <Button
      variant="ghost"
      onClick={onClick}
      className="h-14 flex flex-col items-center justify-center gap-0.5 bg-metal-900 border border-white/5 hover:bg-white/5 hover:border-acid-500/50 rounded-sm w-full min-w-[80px] group/btn transition-all relative overflow-hidden"
    >
      <span className="text-[10px] font-mono text-muted-foreground uppercase">{label}</span>
      <span className={`text-lg font-mono font-bold ${highlight === 'acid' ? 'text-white' : 'text-acid-500'} group-hover/btn:text-white transition-colors`}>
        {odd.toFixed(2)}
      </span>
      {/* Hover Glitch Effect */}
      <div className="absolute inset-0 bg-acid-500/10 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-200" />
    </Button>
  )
}


