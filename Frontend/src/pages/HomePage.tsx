import { motion } from 'framer-motion'
import { FaWallet, FaBullseye, FaTrophy, FaChartLine, FaCalendarAlt, FaFire } from 'react-icons/fa'
import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { betsService } from '@/services/bets.service'
import { matchesService } from '@/services/matches.service'
import { formatCurrency } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

export function HomePage() {
  const { user } = useAuth()
  const { toast } = useToast()
  const [stats, setStats] = useState<any>(null)
  const [todayMatches, setTodayMatches] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    
    // Mostrar mensaje de bienvenida si el usuario acaba de iniciar sesión
    const justLoggedIn = sessionStorage.getItem('justLoggedIn')
    if (justLoggedIn === 'true') {
      sessionStorage.removeItem('justLoggedIn')
      // Pequeño delay para asegurar que el componente esté completamente renderizado
      setTimeout(() => {
        toast({
          title: '¡Bienvenido!',
          description: 'Has iniciado sesión correctamente',
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
      
      // Mostrar advertencia si alguna carga falló
      if (bettingStats === null && matches.length === 0) {
        toast({
          title: 'Advertencia',
          description: 'No se pudieron cargar algunos datos. Intenta recargar la página.',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      console.error('Error loading data:', error)
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar los datos. Por favor, intenta nuevamente.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const credits = user?.credits || 0
  const totalBets = stats?.total_bets || 0
  const totalWinnings = stats?.total_won || 0
  const winRate = (stats?.win_rate || 0) / 100 // El backend devuelve porcentaje, convertir a decimal
  const activeBets = stats?.pending_bets || 0

  return (
    <div className="space-y-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-heading font-bold bg-gradient-to-r from-[#00FF73] via-[#00D95F] to-[#FFD700] bg-clip-text text-transparent mb-3 drop-shadow-[0_0_15px_rgba(0,255,115,0.5)]">
          House Always Wins
        </h1>
        <p className="text-[#B0B3C5] text-lg font-medium">Bienvenido a HAW. Explora partidos y arma tu boleta.</p>
      </motion.div>
      
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
        </div>
      ) : (
        <>
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <StatCard title="Saldo" value={formatCurrency(credits)} icon={<FaWallet size={24} />} />
            <StatCard title="Apuestas Totales" value={totalBets.toString()} icon={<FaBullseye size={24} />} />
            <StatCard title="Ganancias Totales" value={formatCurrency(totalWinnings)} icon={<FaTrophy size={24} />} />
            <StatCard title="Tasa de Éxito" value={`${(winRate * 100).toFixed(1)}%`} icon={<FaChartLine size={24} />} />
          </motion.div>

          {activeBets > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <StatCard 
                title="Apuestas Activas" 
                value={activeBets.toString()} 
                icon={<FaFire size={24} />}
                className="bg-gradient-to-r from-[#FFD700]/20 to-[#00FF73]/20 border-[#FFD700]/50"
              />
            </motion.div>
          )}

          {todayMatches.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="rounded-lg border border-[#1C2541]/50 bg-[#1C2541] p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <FaCalendarAlt className="text-[#00FF73]" size={20} />
                <h2 className="text-xl font-heading font-bold text-white">Partidos de Hoy</h2>
                <span className="ml-auto text-sm text-[#B0B3C5]">{todayMatches.length} partido(s)</span>
              </div>
              <div className="space-y-2">
                {todayMatches.slice(0, 5).map((match) => (
                  <div key={match.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0B132B] border border-[#1C2541]/50">
                    <div className="flex items-center gap-3">
                      <span className="text-white font-medium">{match.home_team.name}</span>
                      <span className="text-[#B0B3C5]">vs</span>
                      <span className="text-white font-medium">{match.away_team.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      {match.home_odds && (
                        <span className="text-[#00FF73] font-mono">1: {match.home_odds.toFixed(2)}</span>
                      )}
                      {match.away_odds && (
                        <span className="text-[#00FF73] font-mono">2: {match.away_odds.toFixed(2)}</span>
                      )}
                      <span className="text-[#B0B3C5] capitalize">{match.status}</span>
                    </div>
                  </div>
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
  className = "" 
}: { 
  title: string
  value: string
  icon: React.ReactNode
  className?: string
}) {
  return (
    <motion.div 
      whileHover={{ scale: 1.05, y: -5 }}
      transition={{ duration: 0.3 }}
      className={`rounded-lg border border-[#1C2541]/50 bg-[#1C2541] p-6 shadow-lg hover:shadow-[0_0_25px_rgba(0,255,115,0.2)] hover:border-[#00FF73]/30 transition-all duration-300 card-glow ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-[#B0B3C5] font-medium uppercase tracking-wider">{title}</div>
        <div className="text-[#00FF73] neon-glow-green rounded-full p-2 bg-[#00FF73]/10">{icon}</div>
      </div>
      <div className="text-3xl font-mono font-bold text-neon-green">{value}</div>
    </motion.div>
  )
}