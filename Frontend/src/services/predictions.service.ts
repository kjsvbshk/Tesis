/**
 * Predictions Service
 * Handles prediction-related API calls
 */

import { apiRequest } from '@/lib/api'

export interface PredictionRequest {
  game_id: number
}

export interface PredictionResponse {
  game_id: number
  home_team_id: number
  away_team_id: number
  home_team_name: string
  away_team_name: string
  game_date: string
  home_win_probability: number
  away_win_probability: number
  predicted_home_score: number
  predicted_away_score: number
  predicted_total: number
  recommended_bet: string
  expected_value: number
  confidence_score: number
  model_version: string
  latency_ms?: number
  prediction_timestamp?: string
  features_used?: Record<string, any>
}

export interface ModelStatus {
  model_loaded: boolean
  model_version: string
  model_type: string
  last_trained: string
  accuracy: number
  status: string
}

class PredictionsService {
  /**
   * Get prediction for a specific game
   * Supports idempotency with X-Idempotency-Key header
   */
  async getPrediction(
    gameId: number,
    idempotencyKey?: string
  ): Promise<PredictionResponse> {
    const headers: HeadersInit = {}
    if (idempotencyKey) {
      headers['X-Idempotency-Key'] = idempotencyKey
    }

    return apiRequest<PredictionResponse>('/predict/', {
      method: 'POST',
      headers,
      body: JSON.stringify({ game_id: gameId }),
    })
  }

  /**
   * Get prediction for a specific game by ID
   */
  async getGamePrediction(gameId: number): Promise<PredictionResponse> {
    return apiRequest<PredictionResponse>(`/predict/game/${gameId}`)
  }

  /**
   * Get predictions for upcoming games
   */
  async getUpcomingPredictions(days: number = 7): Promise<PredictionResponse[]> {
    return apiRequest<PredictionResponse[]>(`/predict/upcoming?days=${days}`)
  }

  /**
   * Get ML model status
   */
  async getModelStatus(): Promise<ModelStatus> {
    return apiRequest<ModelStatus>('/predict/model/status')
  }

  /**
   * Retrain the ML model (admin only)
   */
  async retrainModel(): Promise<{ message: string; status: string; details: any }> {
    return apiRequest('/predict/retrain', {
      method: 'POST',
    })
  }
}

export const predictionsService = new PredictionsService()

