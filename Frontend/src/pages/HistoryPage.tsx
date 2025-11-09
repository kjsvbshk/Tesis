import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

const rows = [
  { date: '2025-10-10', event: 'Celtics vs Heat - Local', odd: 1.75, result: 'Ganada', profit: 37.5 },
  { date: '2025-10-11', event: 'Lakers vs Warriors - Over', odd: 2.05, result: 'Perdida', profit: -20 },
]

export function HistoryPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Historial</h1>
      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Fecha</TableHead>
              <TableHead>Evento</TableHead>
              <TableHead>Cuota</TableHead>
              <TableHead>Resultado</TableHead>
              <TableHead className="text-right">Ganancia</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r, idx) => (
              <TableRow key={idx}>
                <TableCell>{r.date}</TableCell>
                <TableCell>{r.event}</TableCell>
                <TableCell>{r.odd.toFixed(2)}</TableCell>
                <TableCell>{r.result}</TableCell>
                <TableCell className="text-right">{r.profit.toFixed(2)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

