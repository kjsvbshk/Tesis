/**
 * Predictions Page
 * User page to request and view predictions
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, Calendar, Target } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { predictionsService } from '@/services/predictions.service'
import { useToast } from '@/hooks/use-toast'

export function PredictionsPage() {
  const [gameId, setGameId] = useState('')
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState<any>(null)
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
        >
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp size={20} className="text-[#00FF73]" />
                Resultado de la Predicción
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {prediction.prediction && (
                <div>
                  <Label className="text-[#B0B3C5]">Predicción</Label>
                  <div className="mt-2 p-4 bg-[#0B132B] rounded-lg">
                    <pre className="text-white text-sm whitespace-pre-wrap">
                      {JSON.stringify(prediction.prediction, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
              {prediction.request_key && (
                <div>
                  <Label className="text-[#B0B3C5]">Request Key</Label>
                  <p className="text-white font-mono text-sm mt-1">{prediction.request_key}</p>
                </div>
              )}
              {prediction.model_version && (
                <div>
                  <Label className="text-[#B0B3C5]">Versión del Modelo</Label>
                  <Badge className="bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73] mt-1">
                    {prediction.model_version}
                  </Badge>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}

