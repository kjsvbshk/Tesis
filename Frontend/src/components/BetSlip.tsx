import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useBetStore, potentialPayout, computeParlayOdd, type BetItem } from '@/store/bets'
import { formatCurrency, formatDecimal, parseLocaleNumber } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { betsService, type BetCreate } from '@/services/bets.service'
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function BetSlip() {
  const { items, stake, removeBet, setStake, clear } = useBetStore()
  const { toast } = useToast()
  const { refreshUser } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const totalPayout = potentialPayout(stake, items)
  const parlayOdd = computeParlayOdd(items)

  const mapBetTypeToBackend = (item: BetItem, individualStake: number): BetCreate => {
    // Usar gameId si está disponible, sino usar matchId
    const gameId = item.gameId || (typeof item.matchId === 'number' ? item.matchId : parseInt(item.matchId))
    
    // Calcular el payout individual para esta apuesta
    const individualPayout = individualStake * item.odd
    
    // Mapear tipos de apuesta del frontend al backend
    if (item.type === 'home' || item.type === 'away') {
      // Moneyline bet
      return {
        game_id: gameId,
        bet_type: 'moneyline',
        bet_amount: individualStake,
        odds: item.odd,
        potential_payout: individualPayout,
        selected_team_id: item.type === 'home' ? item.homeTeamId : item.awayTeamId,
      }
    } else {
      // Over/Under bet
      // Usar overUnderValue del match si está disponible, sino usar un valor por defecto
      const overUnderValue = item.overUnderValue || 220.5
      
      return {
        game_id: gameId,
        bet_type: 'over_under',
        bet_amount: individualStake,
        odds: item.odd,
        potential_payout: individualPayout,
        over_under_value: overUnderValue,
        is_over: item.type === 'over',
      }
    }
  }

  const confirm = async () => {
    if (items.length === 0 || stake <= 0) return

    // Validar que todas las apuestas tengan al menos un matchId válido
    // Si no hay gameId, intentaremos usar matchId como gameId
    const invalidBets = items.filter(item => {
      const hasGameId = item.gameId || (typeof item.matchId === 'number' && item.matchId > 0) || (typeof item.matchId === 'string' && !isNaN(parseInt(item.matchId)))
      return !hasGameId
    })
    
    if (invalidBets.length > 0) {
      toast({
        title: 'Error',
        description: 'Algunas apuestas no tienen información completa. Por favor, selecciona apuestas válidas.',
        variant: 'destructive',
      })
      return
    }

    try {
      setIsSubmitting(true)

      // Si hay múltiples apuestas, dividir el stake entre todas
      // Por ahora, creamos una apuesta por cada item con el stake dividido
      const individualStake = stake / items.length
      
      const betPromises = items.map(item => {
        const betData = mapBetTypeToBackend(item, individualStake)
        return betsService.placeBet(betData)
      })

      await Promise.all(betPromises)

      toast({
        title: 'Apuesta registrada',
        description: `Se registraron ${items.length} apuesta(s) exitosamente.`,
      })

      // Refrescar datos del usuario (credits)
      await refreshUser()

      clear()
    } catch (error: any) {
      console.error('Error placing bet:', error)
      toast({
        title: 'Error',
        description: error.message || 'Error al registrar la apuesta. Verifica tu saldo y los datos.',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="bg-[#1C2541] border-[#1C2541]/50">
      <CardHeader>
        <CardTitle className="text-white font-heading">Boleta</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length === 0 && <p className="text-sm text-[#B0B3C5]">No hay apuestas seleccionadas.</p>}
        {items.map((i) => (
          <div key={i.id} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-[#0B132B] border border-[#1C2541]/50">
            <div>
              <div className="text-sm font-medium text-white">{i.eventLabel}</div>
              <div className="text-xs text-[#B0B3C5] font-mono">Cuota {i.odd.toFixed(2)}</div>
            </div>
            <Button size="sm" variant="ghost" onClick={() => removeBet(i.id)} className="text-[#FF4C4C] hover:text-[#FF3333] hover:bg-[#FF4C4C]/10">Quitar</Button>
          </div>
        ))}
        <Separator className="bg-[#1C2541]" />
        <div className="space-y-2">
          <div className="text-sm text-[#B0B3C5] font-medium">Monto</div>
          <Input
            inputMode="decimal"
            value={stake ? formatDecimal(stake) : ''}
            onChange={(e) => {
              const v = e.target.value
              setStake(v === '' ? 0 : parseLocaleNumber(v))
            }}
            onBlur={(e) => {
              const v = parseLocaleNumber(e.target.value)
              setStake(v)
            }}
            placeholder="0,00"
            className="bg-[#0B132B] border-[#1C2541] text-white focus:border-[#00FF73] focus:ring-[#00FF73]"
          />
        </div>
      </CardContent>
      <CardFooter className="flex flex-col items-stretch gap-3">
        <div className="flex items-center justify-between text-sm text-[#B0B3C5]">
          <span>Selecciones</span>
          <span className="font-mono font-medium text-white">{items.length}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-[#B0B3C5]">
          <span>Cuota total</span>
          <span className="font-mono font-medium text-neon-green">{parlayOdd ? parlayOdd.toFixed(3) : '-'}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-[#B0B3C5]">
          <span>Posible ganancia</span>
          <span className="font-mono font-semibold text-neon-yellow">{formatCurrency(totalPayout)}</span>
        </div>
        <Button 
          disabled={items.length === 0 || stake <= 0 || isSubmitting} 
          onClick={confirm} 
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-white border-r-transparent mr-2"></div>
              Procesando...
            </>
          ) : (
            stake > 0 ? `Confirmar apuesta ${formatCurrency(stake)}` : 'Confirmar apuesta'
          )}
        </Button>
      </CardFooter>
    </Card>
  )
}


