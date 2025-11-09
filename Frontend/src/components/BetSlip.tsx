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
    <Card>
      <CardHeader>
        <CardTitle>Boleta</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.length === 0 && <p className="text-sm text-muted-foreground">No hay apuestas seleccionadas.</p>}
        {items.map((i) => (
          <div key={i.id} className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-medium">{i.eventLabel}</div>
              <div className="text-xs text-muted-foreground">Cuota {i.odd.toFixed(2)}</div>
            </div>
            <Button size="sm" variant="ghost" onClick={() => removeBet(i.id)}>Quitar</Button>
          </div>
        ))}
        <Separator />
        <div className="space-y-2">
          <div className="text-sm">Monto</div>
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
          />
        </div>
      </CardContent>
      <CardFooter className="flex flex-col items-stretch gap-3">
        <div className="flex items-center justify-between text-sm">
          <span>Selecciones</span>
          <span className="font-medium">{items.length}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Cuota total</span>
          <span className="font-medium">{parlayOdd ? parlayOdd.toFixed(3) : '-'}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span>Posible ganancia</span>
          <span className="font-semibold">{formatCurrency(totalPayout)}</span>
        </div>
        <Button disabled={items.length === 0 || stake <= 0} onClick={confirm}>
          {stake > 0 ? `Confirmar apuesta ${formatCurrency(stake)}` : 'Confirmar apuesta'}
        </Button>
      </CardFooter>
    </Card>
  )
}


