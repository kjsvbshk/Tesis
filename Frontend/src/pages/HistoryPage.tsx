import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const rows = [
  { date: '2025-10-10', event: 'Celtics vs Heat - Local', odd: 1.75, result: 'Ganada', profit: 37.5 },
  { date: '2025-10-11', event: 'Lakers vs Warriors - Over', odd: 2.05, result: 'Perdida', profit: -20 },
]

export function HistoryPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-heading font-bold text-white">Historial</h1>
      <div className="rounded-lg border border-[#1C2541]/50 overflow-x-auto bg-[#1C2541] card-glow">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-[#B0B3C5]">Fecha</TableHead>
              <TableHead className="text-[#B0B3C5]">Evento</TableHead>
              <TableHead className="text-[#B0B3C5]">Cuota</TableHead>
              <TableHead className="text-[#B0B3C5]">Resultado</TableHead>
              <TableHead className="text-right text-[#B0B3C5]">Ganancia</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, idx) => (
              <TableRow key={idx} className={r.profit > 0 ? 'win-highlight' : 'loss-highlight'}>
                <TableCell className="text-white font-mono text-sm">{r.date}</TableCell>
                <TableCell className="text-white">{r.event}</TableCell>
                <TableCell className="text-[#B0B3C5] font-mono">{r.odd.toFixed(2)}</TableCell>
                <TableCell>
                  <span className={`font-medium ${r.result === 'Ganada' ? 'text-neon-green' : 'text-[#FF4C4C]'}`}>
                    {r.result}
                  </span>
                </TableCell>
                <TableCell className={`text-right font-mono font-bold ${r.profit > 0 ? 'text-neon-green' : 'text-[#FF4C4C]'}`}>
                  {r.profit > 0 ? '+' : ''}{r.profit.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

