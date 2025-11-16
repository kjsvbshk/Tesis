import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useBetStore, potentialPayout, computeParlayOdd, type BetItem } from '@/store/bets'
import { formatCurrency } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'
import { betsService, type BetCreate } from '@/services/bets.service'
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function BetSlip() {
  const { items, stake, removeBet, setStake, clear } = useBetStore()
  const { toast } = useToast()
  const { refreshUser, user } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [stakeInput, setStakeInput] = useState('')

  const totalPayout = potentialPayout(stake, items)
  const parlayOdd = computeParlayOdd(items)

  // Sincronizar stakeInput con stake cuando stake cambia desde fuera (por ejemplo, al limpiar)
  useEffect(() => {
    // Solo sincronizar si stake se resetea a 0 y stakeInput no está vacío
    // Esto evita interferir cuando el usuario está escribiendo
    if (stake === 0 && stakeInput !== '' && stakeInput !== ',') {
      setStakeInput('')
    }
  }, [stake])

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

  const handleStakeChange = (value: string) => {
    // Permitir solo números, punto y coma
    let cleaned = value.replace(/[^0-9,.]/g, '')
    
    // Si el usuario escribe una coma, permitirla (será el separador decimal)
    // Si escribe un punto, también permitirlo pero convertirlo a coma para consistencia
    cleaned = cleaned.replace(/\./g, ',')
    
    // Permitir solo una coma decimal
    const parts = cleaned.split(',')
    if (parts.length > 2) {
      // Si hay más de una coma, mantener solo la primera
      cleaned = parts[0] + ',' + parts.slice(1).join('')
    }
    
    // Limitar a 2 decimales después de la coma
    if (parts.length === 2 && parts[1].length > 2) {
      cleaned = parts[0] + ',' + parts[1].substring(0, 2)
    }
    
    // Actualizar el input visual primero
    setStakeInput(cleaned)
    
    // Convertir a número para el stake (reemplazar coma por punto para parseFloat)
    // Si cleaned termina en coma, removerla antes de convertir
    let normalized = cleaned
    if (normalized.endsWith(',')) {
      normalized = normalized.slice(0, -1)
    }
    normalized = normalized.replace(',', '.')
    const numValue = parseFloat(normalized)
    
    // Actualizar el stake siempre de forma explícita
    if (cleaned === '' || cleaned === ',') {
      setStake(0)
    } else if (!isNaN(numValue) && numValue >= 0 && isFinite(numValue)) {
      // Asegurar que el valor se actualiza correctamente
      setStake(numValue)
    } else {
      // Si el valor no es válido pero no está vacío, establecer a 0 para deshabilitar el botón
      setStake(0)
    }
  }

  const handleStakeBlur = () => {
    // Solo formatear al perder el foco si hay un valor válido
    if (stake > 0) {
      // Formatear con 2 decimales y coma como separador
      setStakeInput(stake.toFixed(2).replace('.', ','))
    } else {
      setStakeInput('')
    }
  }

  const confirm = async () => {
    if (items.length === 0 || stake <= 0) {
      toast({
        title: 'Error',
        description: 'Debes seleccionar al menos una apuesta y un monto válido.',
        variant: 'destructive',
      })
      return
    }

    // Validar créditos disponibles
    const availableCredits = (user?.credits !== null && user?.credits !== undefined) ? user.credits : 0
    if (stake > availableCredits) {
      toast({
        title: 'Créditos insuficientes',
        description: `No tienes suficientes créditos. Disponibles: ${formatCurrency(availableCredits)}`,
        variant: 'destructive',
      })
      return
    }

    // Validar monto mínimo y máximo
    if (stake < 1.0) {
      toast({
        title: 'Error',
        description: 'El monto mínimo de apuesta es $1.00',
        variant: 'destructive',
      })
      return
    }

    if (stake > 100.0) {
      toast({
        title: 'Error',
        description: 'El monto máximo de apuesta es $100.00',
        variant: 'destructive',
      })
      return
    }

    // Validar que todas las apuestas tengan al menos un matchId válido
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

      // Limpiar el input y el stake
      setStakeInput('')
      setStake(0)
      clear()
    } catch (error: any) {
      console.error('Error placing bet:', error)
      const errorMessage = error.message || 'Error al registrar la apuesta. Verifica tu saldo y los datos.'
      
      // Mensajes de error más específicos
      let displayMessage = errorMessage
      if (errorMessage.includes('Insufficient credits') || errorMessage.includes('insufficient')) {
        displayMessage = `Créditos insuficientes. Disponibles: ${formatCurrency(availableCredits)}`
      } else if (errorMessage.includes('between')) {
        displayMessage = 'El monto debe estar entre $1.00 y $100.00'
      }
      
      toast({
        title: 'Error',
        description: displayMessage,
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
          <div className="flex items-center justify-between">
            <div className="text-sm text-[#B0B3C5] font-medium">Monto</div>
            {user && user.credits !== null && user.credits !== undefined && (
              <div className="text-xs text-[#B0B3C5]">
                Disponible: <span className="font-mono text-[#00FF73]">{formatCurrency(user.credits)}</span>
              </div>
            )}
          </div>
          <Input
            type="text"
            inputMode="decimal"
            value={stakeInput}
            onChange={(e) => handleStakeChange(e.target.value)}
            onBlur={handleStakeBlur}
            placeholder="0,00"
            className="bg-[#0B132B] border-[#1C2541] text-white focus:border-[#00FF73] focus:ring-[#00FF73]"
          />
          {stake > 0 && user && user.credits !== null && user.credits !== undefined && stake > user.credits && (
            <p className="text-xs text-[#FF4C4C]">
              Créditos insuficientes. Disponibles: {formatCurrency(user.credits)}
            </p>
          )}
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
          disabled={
            items.length === 0 || 
            stake <= 0 || 
            stake < 1.0 || 
            stake > 100.0 ||
            isSubmitting || 
            (user && user.credits !== null && user.credits !== undefined && typeof user.credits === 'number' && stake > user.credits) ||
            isNaN(stake) ||
            !isFinite(stake)
          } 
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
        {user && user.credits !== null && user.credits !== undefined && stake > user.credits && (
          <p className="text-xs text-center text-[#FF4C4C]">
            No tienes suficientes créditos para esta apuesta
          </p>
        )}
        {(stake < 1.0 && stake > 0) && (
          <p className="text-xs text-center text-[#FF4C4C]">
            El monto mínimo es $1.00
          </p>
        )}
        {stake > 100.0 && (
          <p className="text-xs text-center text-[#FF4C4C]">
            El monto máximo es $100.00
          </p>
        )}
      </CardFooter>
    </Card>
  )
}


