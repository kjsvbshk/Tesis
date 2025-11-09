import { BetSlip } from '@/components/BetSlip'

export function BetsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Apuestas</h1>
      <div className="max-w-md"><BetSlip /></div>
    </div>
  )
}

