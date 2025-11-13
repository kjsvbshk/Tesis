/**
 * Predictions Page
 * User page to request and view predictions
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, Calendar, Target, Users, Trophy, BarChart3, Clock, Zap } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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
        title: 'Error',
        description: 'Por favor ingresa un Game ID',
        variant: 'destructive',
      })
      return
    }

    try {
      setLoading(true)
      const result = await predictionsService.getGamePrediction(parseInt(gameId))
      setPrediction(result)
      toast({
        title: 'Éxito',
        description: 'Predicción obtenida correctamente',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al obtener predicción',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
          Predicciones
        </h1>
        <p className="text-[#B0B3C5]">Obtén predicciones para partidos de NBA</p>
      </motion.div>

      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Target size={20} className="text-[#00FF73]" />
            Solicitar Predicción
          </CardTitle>
          <CardDescription className="text-[#B0B3C5]">
            Ingresa el ID del partido para obtener una predicción
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="gameId" className="text-[#B0B3C5]">
              Game ID
            </Label>
            <Input
              id="gameId"
              type="number"
              value={gameId}
              onChange={(e) => setGameId(e.target.value)}
              placeholder="Ej: 401585601"
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <Button
            onClick={handleGetPrediction}
            disabled={loading}
            className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
          >
            {loading ? (
              <>
                <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-black border-r-transparent mr-2"></div>
                Obteniendo predicción...
              </>
            ) : (
              <>
                <TrendingUp size={16} className="mr-2" />
                Obtener Predicción
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {prediction && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-4"
        >
          {/* Información del Partido */}
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Users size={20} className="text-[#00FF73]" />
                Información del Partido
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-[#B0B3C5] text-sm">Equipo Local</Label>
                  <p className="text-white font-semibold mt-1">{prediction.home_team_name || 'N/A'}</p>
                </div>
                <div>
                  <Label className="text-[#B0B3C5] text-sm">Equipo Visitante</Label>
                  <p className="text-white font-semibold mt-1">{prediction.away_team_name || 'N/A'}</p>
                </div>
              </div>
              {prediction.game_date && (
                <div>
                  <Label className="text-[#B0B3C5] text-sm flex items-center gap-2">
                    <Calendar size={14} />
                    Fecha del Partido
                  </Label>
                  <p className="text-white mt-1">
                    {new Date(prediction.game_date).toLocaleString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Probabilidades de Victoria */}
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Trophy size={20} className="text-[#00FF73]" />
                Probabilidades de Victoria
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-[#0B132B] rounded-lg">
                  <Label className="text-[#B0B3C5] text-sm">{prediction.home_team_name}</Label>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="flex-1">
                      <div className="h-4 bg-[#1C2541] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[#00FF73] to-[#00D95F] rounded-full transition-all"
                          style={{ width: `${(prediction.home_win_probability || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-white font-bold text-lg min-w-[60px] text-right">
                      {((prediction.home_win_probability || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="p-4 bg-[#0B132B] rounded-lg">
                  <Label className="text-[#B0B3C5] text-sm">{prediction.away_team_name}</Label>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="flex-1">
                      <div className="h-4 bg-[#1C2541] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[#FFD700] to-[#FFA500] rounded-full transition-all"
                          style={{ width: `${(prediction.away_win_probability || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-white font-bold text-lg min-w-[60px] text-right">
                      {((prediction.away_win_probability || 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Predicción de Marcadores */}
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <BarChart3 size={20} className="text-[#00FF73]" />
                Predicción de Marcadores
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-[#0B132B] rounded-lg text-center">
                  <Label className="text-[#B0B3C5] text-sm">{prediction.home_team_name}</Label>
                  <p className="text-white font-bold text-3xl mt-2">{prediction.predicted_home_score?.toFixed(1) || 'N/A'}</p>
                </div>
                <div className="p-4 bg-[#0B132B] rounded-lg text-center">
                  <Label className="text-[#B0B3C5] text-sm">Total</Label>
                  <p className="text-white font-bold text-3xl mt-2">{prediction.predicted_total?.toFixed(1) || 'N/A'}</p>
                </div>
                <div className="p-4 bg-[#0B132B] rounded-lg text-center">
                  <Label className="text-[#B0B3C5] text-sm">{prediction.away_team_name}</Label>
                  <p className="text-white font-bold text-3xl mt-2">{prediction.predicted_away_score?.toFixed(1) || 'N/A'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recomendación de Apuesta */}
          {prediction.recommended_bet && prediction.recommended_bet !== 'none' && (
            <Card className="bg-[#1C2541]/50 border-[#1C2541]">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Zap size={20} className="text-[#00FF73]" />
                  Recomendación de Apuesta
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-[#B0B3C5] text-sm">Apuesta Recomendada</Label>
                    <p className="text-white font-semibold mt-1 capitalize">
                      {prediction.recommended_bet === 'home' 
                        ? `${prediction.home_team_name} (Local)`
                        : prediction.recommended_bet === 'away'
                        ? `${prediction.away_team_name} (Visitante)`
                        : prediction.recommended_bet}
                    </p>
                  </div>
                  {prediction.expected_value !== null && prediction.expected_value !== undefined && (
                    <Badge 
                      className={`${
                        prediction.expected_value > 0 
                          ? 'bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]' 
                          : 'bg-red-500/20 text-red-400 border-red-500'
                      }`}
                    >
                      EV: {prediction.expected_value > 0 ? '+' : ''}{prediction.expected_value.toFixed(3)}
                    </Badge>
                  )}
                </div>
                {prediction.confidence_score !== null && prediction.confidence_score !== undefined && (
                  <div>
                    <Label className="text-[#B0B3C5] text-sm">Nivel de Confianza</Label>
                    <div className="mt-2 flex items-center gap-3">
                      <div className="flex-1">
                        <div className="h-3 bg-[#1C2541] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[#00FF73] to-[#00D95F] rounded-full transition-all"
                            style={{ width: `${(prediction.confidence_score || 0) * 100}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-white font-semibold text-sm min-w-[50px] text-right">
                        {(prediction.confidence_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Información del Modelo */}
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp size={20} className="text-[#00FF73]" />
                Información del Modelo
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-[#B0B3C5] text-sm">Versión del Modelo</Label>
                <Badge className="bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]">
                  {prediction.model_version || 'N/A'}
                </Badge>
              </div>
              {prediction.latency_ms !== null && prediction.latency_ms !== undefined && (
                <div className="flex items-center justify-between">
                  <Label className="text-[#B0B3C5] text-sm flex items-center gap-2">
                    <Clock size={14} />
                    Tiempo de Respuesta
                  </Label>
                  <span className="text-white font-mono text-sm">{prediction.latency_ms}ms</span>
                </div>
              )}
              {prediction.prediction_timestamp && (
                <div className="flex items-center justify-between">
                  <Label className="text-[#B0B3C5] text-sm">Fecha de Predicción</Label>
                  <span className="text-white text-sm">
                    {new Date(prediction.prediction_timestamp).toLocaleString('es-ES')}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}

