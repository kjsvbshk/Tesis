import { motion } from 'framer-motion'
import { FaWallet, FaBullseye, FaTrophy, FaChartLine, FaFire } from 'react-icons/fa'
import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { betsService } from '@/services/bets.service'
import { matchesService } from '@/services/matches.service'
import { formatCurrency } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function HomePage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [stats, setStats] = useState<any>(null)
  const [todayMatches, setTodayMatches] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const justLoggedIn = sessionStorage.getItem('justLoggedIn')
    if (justLoggedIn === 'true') {
      sessionStorage.removeItem('justLoggedIn')
      setTimeout(() => {
        toast({
          title: 'SYSTEM ONLINE',
          description: `User ${user?.username} authenticated.`,
          variant: "default",
          className: "bg-acid-500 text-black border-none font-mono"
        })
      }, 100)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [bettingStats, matches] = await Promise.all([
        betsService.getBettingStats().catch((error) => {
          console.error('Error loading betting stats:', error)
          return null
        }),
        matchesService.getTodayMatches().catch((error) => {
          console.error('Error loading matches:', error)
          return []
        })
      ])
      setStats(bettingStats)
      setTodayMatches(matches)
    } catch (error: any) {
      console.error('Error loading data:', error)
      toast({
        title: 'DATA FETCH ERROR',
        description: 'Failed to retrieve metrics.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const credits = user?.credits || 0
  const totalBets = stats?.total_bets || 0
  const totalWinnings = stats?.total_won || 0
  const winRate = (stats?.win_rate || 0) / 100
  const activeBets = stats?.pending_bets || 0

  return (
    <div className="space-y-8 p-4 md:p-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6 }}
        className="relative"
      >
        <div className="absolute top-0 left-0 w-20 h-1 bg-acid-500 mb-4" />
        <h1 className="text-6xl md:text-8xl font-display font-bold uppercase text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-400 to-gray-600 mt-6 tracking-tighter">
          House Always<br />
          <span className="text-acid-500 hover:animate-glitch inline-block">Wins</span>
        </h1>
        <p className="text-muted-foreground font-mono mt-4 max-w-md border-l-2 border-acid-500 pl-4">
          :: PROBABILITY PROTOCOLS ENGAGED<br />
          :: MARKET VOLATILITY INDEX: STABLE
        </p>
      </motion.div>

      {loading ? (
        <div className="flex items-center justify-center h-64 font-mono text-acid-500 animate-pulse">
          [ LOADING DATA STREAMS... ]
        </div>
      ) : (
        <>
          {/* Stats Grid - Bento Style */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4"
          >
            <StatCard
              title="AVAILABLE CREDITS"
              value={formatCurrency(credits)}
              icon={<FaWallet />}
              trend="up"
            />
            <StatCard
              title="TOTAL OPERATIONS"
              value={totalBets.toString()}
              icon={<FaBullseye />}
            />
            <StatCard
              title="NET YIELD"
              value={formatCurrency(totalWinnings)}
              icon={<FaTrophy />}
              highlight
            />
            <StatCard
              title="SUCCESS RATE"
              value={`${(winRate * 100).toFixed(1)}%`}
              icon={<FaChartLine />}
            />
          </motion.div>

          {/* Active Bets Alert */}
          {activeBets > 0 && (
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3 }}
              className="bg-metal-800 border-l-4 border-alert-red p-4 flex items-center justify-between cut-corners"
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-alert-red/10 rounded-none text-alert-red animate-pulse">
                  <FaFire size={24} />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-white">ACTIVE OPERATIONS</h3>
                  <p className="text-muted-foreground font-mono text-sm">{activeBets} pending validation(s)</p>
                </div>
              </div>
              <Button variant="destructive" size="sm" className="font-mono">
                VIEW LOGS
              </Button>
            </motion.div>
          )}

          {/* Today's Matches - Console List */}
          {todayMatches.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-8 bg-acid-500" />
                  <h2 className="text-2xl font-display font-bold text-white uppercase">Live Feeds</h2>
                </div>
                <div className="font-mono text-acid-500 text-xs border border-acid-500/30 px-2 py-1">
                  SYNCED: {new Date().toLocaleTimeString()}
                </div>
              </div>

              <div className="grid gap-4">
                {todayMatches.slice(0, 5).map((match, i) => (
                  <Card key={match.id} className="group hover:border-acid-500 transition-colors">
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <span className="font-mono text-muted-foreground text-xs text-acid-500/50">0{i + 1}</span>
                        <div className="flex flex-col md:flex-row md:items-center gap-2 md:gap-8">
                          <span className="text-white font-display font-semibold text-lg hover:text-acid-500 transition-colors cursor-pointer uppercase">
                            {match.home_team.name}
                          </span>
                          <span className="text-muted-foreground text-xs px-2 py-1 bg-metal-900 border border-chrome-grey font-mono">VS</span>
                          <span className="text-white font-display font-semibold text-lg hover:text-acid-500 transition-colors cursor-pointer uppercase">
                            {match.away_team.name}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-6">
                        <div className="hidden md:flex gap-4">
                          <div className="flex flex-col items-center">
                            <span className="text-xs text-muted-foreground font-mono mb-1">HOME</span>
                            <span className="text-acid-500 font-mono font-bold bg-acid-500/10 px-2 py-0.5 border border-acid-500/20">
                              {match.home_odds?.toFixed(2) || '-'}
                            </span>
                          </div>
                          <div className="flex flex-col items-center">
                            <span className="text-xs text-muted-foreground font-mono mb-1">AWAY</span>
                            <span className="text-acid-500 font-mono font-bold bg-acid-500/10 px-2 py-0.5 border border-acid-500/20">
                              {match.away_odds?.toFixed(2) || '-'}
                            </span>
                          </div>
                        </div>
                        <Button variant="outline" size="sm" className="hidden sm:flex">
                          ANALYZE
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  highlight = false,
  trend
}: {
  title: string
  value: string
  icon: React.ReactNode
  highlight?: boolean
  trend?: 'up' | 'down'
}) {
  return (
    <Card className={`
      relative overflow-hidden group hover:translate-y-[-4px] transition-transform duration-300
      ${highlight ? 'border-acid-500/50 bg-acid-500/5' : ''}
    `}>
      <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0 border-b-0">
        <CardTitle className="text-xs font-mono text-muted-foreground group-hover:text-white transition-colors">
          {title}
        </CardTitle>
        <div className={`p-2 rounded-none transition-colors ${highlight ? 'text-acid-500' : 'text-muted-foreground group-hover:text-acid-500'}`}>
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className={`text-3xl font-display font-bold ${highlight ? 'text-acid-500' : 'text-white'}`}>
          {value}
        </div>
        {trend && (
          <div className="absolute bottom-4 right-4 flex items-center gap-1 text-xs font-mono text-acid-500">
            ▲ +2.4%
          </div>
        )}
      </CardContent>
      {/* Hover Line */}
      <div className="absolute bottom-0 left-0 w-full h-1 bg-acid-500 scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left" />
    </Card>
  )
}