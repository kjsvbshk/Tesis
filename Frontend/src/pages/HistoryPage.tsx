import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { betsService, type BetResponse } from '@/services/bets.service'
import { useToast } from '@/hooks/use-toast'
import { formatCurrency } from '@/lib/utils'

export function HistoryPage() {
  const [bets, setBets] = useState<BetResponse[]>([])
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadBets()
  }, [])

  const loadBets = async () => {
    try {
      setLoading(true)
      const allBets = await betsService.getUserBets(undefined, 100, 0)
      setBets(allBets)
    } catch (error: any) {
      console.error('Error loading bets:', error)
      toast({
        title: 'Error',
        description: 'Error al cargar el historial de apuestas',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      won: 'Ganada',
      lost: 'Perdida',
      pending: 'Pendiente',
      cancelled: 'Cancelada',
    }
    return labels[status] || status
  }

  const getStatusColor = (status: string) => {
    if (status === 'won') return 'text-neon-green'
    if (status === 'lost') return 'text-[#FF4C4C]'
    if (status === 'pending') return 'text-yellow-500'
    return 'text-[#B0B3C5]'
  }

  const getProfit = (bet: BetResponse) => {
    if (bet.status === 'won' && bet.actual_payout) {
      return bet.actual_payout - bet.bet_amount
    }
    if (bet.status === 'lost') {
      return -bet.bet_amount
    }
    return 0
  }

  const formatEventName = (bet: BetResponse) => {
    if (bet.game) {
      const homeTeam = bet.game.home_team?.name || 'Equipo Local'
      const awayTeam = bet.game.away_team?.name || 'Equipo Visitante'
      let betType = ''
      
      if (bet.bet_type === 'moneyline') {
        betType = bet.selected_team_id === bet.game.home_team_id ? 'Local' : 'Visitante'
      } else if (bet.bet_type === 'over_under') {
        betType = bet.is_over ? `Over ${bet.over_under_value}` : `Under ${bet.over_under_value}`
      } else if (bet.bet_type === 'spread') {
        betType = `Spread ${bet.spread_value}`
      }
      
      return `${homeTeam} vs ${awayTeam} - ${betType}`
    }
    return `Partido #${bet.game_id} - ${bet.bet_type}`
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
            Historial de Apuestas
          </h1>
          <p className="text-[#B0B3C5]">Revisa todas tus apuestas pasadas y actuales</p>
        </div>
        <Button
          onClick={loadBets}
          disabled={loading}
          variant="outline"
          size="sm"
          className="border-[#1C2541] text-[#B0B3C5] hover:bg-[#1C2541]"
        >
          <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
          Actualizar
        </Button>
      </motion.div>

      <div className="rounded-lg border border-[#1C2541]/50 overflow-x-auto bg-[#1C2541] card-glow">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          </div>
        ) : bets.length === 0 ? (
          <div className="text-center py-8 text-[#B0B3C5]">
            No hay apuestas en tu historial
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-[#1C2541]">
                <TableHead className="text-[#B0B3C5]">Fecha</TableHead>
                <TableHead className="text-[#B0B3C5]">Evento</TableHead>
                <TableHead className="text-[#B0B3C5]">Tipo</TableHead>
                <TableHead className="text-[#B0B3C5]">Monto</TableHead>
                <TableHead className="text-[#B0B3C5]">Cuota</TableHead>
                <TableHead className="text-[#B0B3C5]">Resultado</TableHead>
                <TableHead className="text-right text-[#B0B3C5]">Ganancia</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bets.map((bet) => {
                const profit = getProfit(bet)
                return (
                  <TableRow 
                    key={bet.id} 
                    className={`border-[#1C2541] hover:bg-[#1C2541]/30 ${profit > 0 ? 'win-highlight' : profit < 0 ? 'loss-highlight' : ''}`}
                  >
                    <TableCell className="text-white font-mono text-sm">
                      {new Date(bet.placed_at).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </TableCell>
                    <TableCell className="text-white max-w-xs truncate">
                      {formatEventName(bet)}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5] capitalize">
                      {bet.bet_type.replace('_', ' ')}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5] font-mono">
                      {formatCurrency(bet.bet_amount)}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5] font-mono">
                      {bet.odds.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <span className={`font-medium ${getStatusColor(bet.status)}`}>
                        {getStatusLabel(bet.status)}
                      </span>
                    </TableCell>
                    <TableCell className={`text-right font-mono font-bold ${profit > 0 ? 'text-neon-green' : profit < 0 ? 'text-[#FF4C4C]' : 'text-[#B0B3C5]'}`}>
                      {profit > 0 ? '+' : ''}{formatCurrency(profit)}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}

