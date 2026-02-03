import { MatchList } from '@/components/MatchList'

export function MatchesPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-4xl font-display font-bold text-white tracking-tight">
          LIVE <span className="text-acid-500">MATCHES</span>
        </h1>
        <p className="text-muted-foreground font-mono text-sm uppercase tracking-widest">
          Real-time betting data feed
        </p>
      </div>

      <div className="p-1 border border-white/5 bg-metal-900/50 rounded-lg">
        <MatchList />
      </div>
    </div>
  )
}

