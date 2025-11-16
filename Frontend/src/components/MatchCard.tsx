import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { motion } from 'framer-motion'
import { useBetStore, type BetType } from '@/store/bets'
import { FaBasketballBall } from 'react-icons/fa'

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
      className="w-full"
    >
      <Card className="bg-gradient-to-br from-[#1C2541] to-[#0B132B] border border-[#1C2541]/50 overflow-hidden hover:border-[#00FF73]/50 hover:shadow-[0_0_20px_rgba(0,255,115,0.15)] transition-all duration-300 w-full group">
        <CardHeader className="pb-4 px-4 sm:px-5 md:px-6 pt-4 sm:pt-5">
          <div className="flex items-center justify-between gap-3 sm:gap-4">
            <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0 overflow-hidden">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-[#00FF73] via-[#00D95F] to-[#0B132B] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#00FF73]/20 flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
                <FaBasketballBall size={20} className="sm:w-6 sm:h-6" />
              </div>
              <div className="flex-1 min-w-0 overflow-hidden">
                <CardTitle className="text-base sm:text-lg md:text-xl font-heading font-bold text-white mb-1">
                  <div className="flex items-center gap-1.5 sm:gap-2 md:gap-3 flex-wrap">
                    <span className="truncate font-semibold max-w-[120px] sm:max-w-[150px] md:max-w-none">{match.home}</span>
                    <span className="text-[#00FF73] font-bold text-xs sm:text-sm md:text-base flex-shrink-0">vs</span>
                    <span className="truncate font-semibold max-w-[120px] sm:max-w-[150px] md:max-w-none">{match.away}</span>
                  </div>
                </CardTitle>
                {typeof match.aiHomeWinProb === 'number' && (
                  <div className="flex items-center gap-1.5 sm:gap-2 mt-2 overflow-hidden">
                    <div className="w-2 h-2 bg-[#00FF73] rounded-full animate-pulse shadow-[0_0_8px_rgba(0,255,115,0.8)] flex-shrink-0"></div>
                    <span className="text-xs text-[#B0B3C5] font-mono font-medium truncate">
                      IA: <span className="text-[#00FF73] font-bold">{(match.aiHomeWinProb * 100).toFixed(0)}%</span> <span className="hidden sm:inline">{match.home}</span>
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 sm:px-5 md:px-6 pb-4 sm:pb-5 md:pb-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
            <OddButton label="1" odd={match.odds.home} onClick={() => add('home')} />
            <OddButton label="X" odd={match.odds.away} onClick={() => add('away')} />
            <OddButton label="Over 2.5" odd={match.odds.over} onClick={() => add('over')} />
            <OddButton label="Under 2.5" odd={match.odds.under} onClick={() => add('under')} />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function OddButton({ label, odd, onClick }: { label: string; odd: number; onClick: () => void }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05, y: -2 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className="w-full min-w-0"
    >
      <Button 
        variant="secondary" 
        className="justify-between rounded-xl h-14 sm:h-16 bg-gradient-to-br from-[#0B132B] to-[#1C2541] border border-[#1C2541] hover:border-[#00FF73] hover:from-[#1C2541] hover:to-[#0B132B] transition-all duration-300 hover:shadow-[0_0_20px_rgba(0,255,115,0.4)] px-2 sm:px-3 md:px-4 group/button w-full min-w-0" 
        onClick={onClick}
      >
        <span className="text-xs sm:text-sm font-semibold text-white group-hover/button:text-[#00FF73] transition-colors truncate">{label}</span>
        <span className="text-sm sm:text-base md:text-lg font-mono font-bold text-[#00FF73] ml-2 sm:ml-3 group-hover/button:scale-110 transition-transform flex-shrink-0">{odd.toFixed(2)}</span>
      </Button>
    </motion.div>
  )
}


