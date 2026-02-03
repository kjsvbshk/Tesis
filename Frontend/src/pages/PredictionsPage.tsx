/**
 * Predictions Page
 * User page to request and view predictions
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Target, Users, Zap, Cpu, Search } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { predictionsService } from '@/services/predictions.service'
import type { PredictionResponse } from '@/services/predictions.service'
import { useToast } from '@/hooks/use-toast'

export function PredictionsPage() {
  const [gameId, setGameId] = useState('')
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const { toast } = useToast()

  const handleGetPrediction = async () => {
    if (!gameId) {
      toast({
        title: 'INPUT REQUIRED',
        description: 'Please input a valid Game Identifier.',
        variant: 'destructive',
      })
      return
    }

    try {
      setLoading(true)
      const result = await predictionsService.getGamePrediction(parseInt(gameId))
      setPrediction(result)
      toast({
        title: 'ANALYSIS COMPLETE',
        description: 'Prediction model execution successful.',
      })
    } catch (error: any) {
      toast({
        title: 'ANALYSIS FAILED',
        description: error.message || 'Error executing prediction model.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="space-y-2"
      >
        <div className="flex items-center gap-2 text-acid-500 mb-2">
          <Cpu size={16} className="animate-pulse" />
          <span className="text-xs font-mono uppercase tracking-widest">AI Predictive Core v2.4</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-display font-bold text-white tracking-tight">
          PREDICTIVE <span className="text-acid-500">ANALYSIS</span>
        </h1>
        <p className="text-muted-foreground font-mono uppercase tracking-wide max-w-lg">
          Execute Neural Network models to probability outcomes for upcoming matches.
        </p>
      </motion.div>

      {/* Input Section */}
      <Card className="bg-metal-900 border-white/10 relative overflow-hidden group">
        <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-acid-500 to-transparent opacity-50" />
        <CardContent className="pt-8 pb-8">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="space-y-2 flex-1 w-full">
              <Label htmlFor="gameId" className="text-xs font-mono uppercase tracking-widest text-muted-foreground">Target Match Identifier (Game ID)</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input
                  id="gameId"
                  type="number"
                  value={gameId}
                  onChange={(e) => setGameId(e.target.value)}
                  placeholder="ENTER ID :: 401585601"
                  className="pl-10 bg-black/50 border-white/10 focus:border-acid-500 font-mono text-lg h-12 text-white placeholder:text-white/20"
                />
              </div>
            </div>
            <Button
              onClick={handleGetPrediction}
              disabled={loading}
              className="h-12 px-8 bg-acid-500 text-black hover:bg-white font-mono font-bold uppercase tracking-wider min-w-[180px]"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  <span>PROCESSING</span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Target size={16} />
                  <span>EXECUTE MODEL</span>
                </div>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {prediction && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Main Stats - Center Column on Desktop */}
            <div className="lg:col-span-2 space-y-6">
              {/* Matchup Header */}
              <Card className="bg-metal-900/50 border-white/10 overflow-hidden">
                <CardHeader className="bg-white/5 border-b border-white/5 pb-4">
                  <CardTitle className="flex items-center gap-2 text-sm font-mono text-acid-500 uppercase tracking-widest">
                    <Users size={16} /> Matchup Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between gap-4">
                    <div className="text-center md:text-left">
                      <div className="text-2xl md:text-3xl font-display font-bold text-white mb-1">{prediction.home_team_name}</div>
                      <Badge variant="outline" className="border-acid-500/30 text-acid-500 font-mono text-[10px] uppercase">HOME UNIT</Badge>
                    </div>
                    <div className="hidden md:flex flex-col items-center">
                      <span className="text-2xl font-display font-bold text-white/20">VS</span>
                    </div>
                    <div className="text-center md:text-right">
                      <div className="text-2xl md:text-3xl font-display font-bold text-white mb-1">{prediction.away_team_name}</div>
                      <Badge variant="outline" className="border-white/10 text-muted-foreground font-mono text-[10px] uppercase">AWAY UNIT</Badge>
                    </div>
                  </div>

                  {/* Probability Bars */}
                  <div className="mt-8 space-y-6">
                    <ProbabilityBar
                      label={prediction.home_team_name || 'HOME'}
                      value={prediction.home_win_probability || 0}
                      color="acid"
                    />
                    <ProbabilityBar
                      label={prediction.away_team_name || 'AWAY'}
                      value={prediction.away_win_probability || 0}
                      color="violet"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Predicted Scores */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <StatCard label="PREDICTED HOME" value={prediction.predicted_home_score?.toFixed(1) || 'N/A'} sub="Expected Points" />
                <StatCard label="TOTAL POINTS" value={prediction.predicted_total?.toFixed(1) || 'N/A'} sub="Over/Under Line" highlight />
                <StatCard label="PREDICTED AWAY" value={prediction.predicted_away_score?.toFixed(1) || 'N/A'} sub="Expected Points" />
              </div>
            </div>

            {/* Sidebar - Recommendation */}
            <div className="space-y-6">
              {prediction.recommended_bet && prediction.recommended_bet !== 'none' && (
                <Card className="bg-acid-500 text-black border-none relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Zap size={120} />
                  </div>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-sm font-mono font-bold uppercase tracking-widest border-b border-black/10 pb-2">
                      <Zap size={16} /> Alpha Signal
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-xs font-mono uppercase opacity-70 mb-1">Recommended Action</div>
                    <div className="text-2xl font-display font-bold leading-tight uppercase mb-4">
                      {prediction.recommended_bet === 'home'
                        ? `BET ${prediction.home_team_name}`
                        : prediction.recommended_bet === 'away'
                          ? `BET ${prediction.away_team_name}`
                          : `BET ${prediction.recommended_bet}`}
                    </div>

                    {prediction.expected_value !== undefined && (
                      <div className="bg-black/10 rounded p-3 flex justify-between items-end">
                        <div>
                          <div className="text-[10px] font-mono uppercase font-bold opacity-70">Expected Value</div>
                          <div className="text-3xl font-mono font-bold tracking-tighter">
                            {prediction.expected_value > 0 ? '+' : ''}{prediction.expected_value.toFixed(2)}
                          </div>
                        </div>
                        <Badge className="bg-black text-acid-500 hover:bg-black/90 font-mono border-none">Ev+</Badge>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              <Card className="bg-metal-900 border-white/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Model Telemetry</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 font-mono text-xs">
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-muted-foreground">VERSION</span>
                    <span className="text-white">{prediction.model_version || 'v1.0.0'}</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-muted-foreground">CONFIDENCE</span>
                    <span className="text-acid-500 font-bold">{((prediction.confidence_score || 0) * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-muted-foreground">LATENCY</span>
                    <span className="text-white">{prediction.latency_ms || 0}ms</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-muted-foreground">TIMESTAMP</span>
                    <span className="text-white">{new Date(prediction.prediction_timestamp || Date.now()).toLocaleTimeString()}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function StatCard({ label, value, sub, highlight }: { label: string; value: string; sub: string; highlight?: boolean }) {
  return (
    <Card className={`border-white/10 bg-metal-900/50 ${highlight ? 'border-acid-500/50' : ''}`}>
      <CardContent className="p-4 flex flex-col items-center justify-center text-center h-full">
        <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1">{label}</span>
        <span className={`text-3xl lg:text-4xl font-mono font-bold ${highlight ? 'text-acid-500' : 'text-white'} tracking-tighter`}>{value}</span>
        <span className="text-[10px] text-white/30 mt-1">{sub}</span>
      </CardContent>
    </Card>
  )
}

function ProbabilityBar({ label, value, color }: { label: string; value: number; color: 'acid' | 'violet' }) {
  const percentage = (value * 100).toFixed(1)
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs font-mono uppercase tracking-wide">
        <span className="text-white">{label}</span>
        <span className={color === 'acid' ? 'text-acid-500' : 'text-electric-violet'}>{percentage}%</span>
      </div>
      <div className="h-2 bg-black/50 rounded-none overflow-hidden relative">
        {/* Grid background for bar */}
        <div className="absolute inset-0 w-full h-full opacity-20 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNCIgaGVpZ2h0PSI0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxwYXRoIGQ9Ik0xIDFoMXYxSDF6IiBmaWxsPSIjZmZmIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiLz48L3N2Zz4=')]"></div>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: "circOut" }}
          className={`h-full ${color === 'acid' ? 'bg-acid-500' : 'bg-electric-violet'}`}
        />
      </div>
    </div>
  )
}

