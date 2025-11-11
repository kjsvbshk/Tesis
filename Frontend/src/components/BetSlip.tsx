import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useBetStore, potentialPayout, computeParlayOdd } from '@/store/bets'
import { formatCurrency, formatDecimal, parseLocaleNumber } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

export function BetSlip() {
  const { items, stake, removeBet, setStake, clear } = useBetStore()
  const { toast } = useToast()

  const totalPayout = potentialPayout(stake, items)
  const parlayOdd = computeParlayOdd(items)

  const confirm = () => {
    toast({ title: 'Apuesta registrada', description: 'Tu boleta fue confirmada.' })
    clear()
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
        <Button disabled={items.length === 0 || stake <= 0} onClick={confirm} className="w-full">
          {stake > 0 ? `Confirmar apuesta ${formatCurrency(stake)}` : 'Confirmar apuesta'}
        </Button>
      </CardFooter>
    </Card>
  )
}


