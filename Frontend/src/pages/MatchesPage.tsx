import { MatchList } from '@/components/MatchList'

export function MatchesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-heading font-bold text-white">Partidos</h1>
      <MatchList />
    </div>
  )
}

