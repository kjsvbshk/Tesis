import { BetSlip } from '@/components/BetSlip'

export function BetsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-heading font-bold text-white">Apuestas</h1>
      <div className="max-w-md"><BetSlip /></div>
    </div>
  )
}

