/**
 * Bets Service
 * Handles bet-related API calls
 */

import { apiRequest } from '@/lib/api'

export type BetTypeBackend = 'moneyline' | 'spread' | 'over_under'
export type BetStatus = 'pending' | 'won' | 'lost' | 'cancelled'

export interface BetCreate {
  game_id: number
  bet_type: BetTypeBackend
  bet_amount: number
  odds: number
  potential_payout: number
  selected_team_id?: number | null
  spread_value?: number | null
  over_under_value?: number | null
  is_over?: boolean | null
}

export interface BetResponse {
  id: number
  user_id: number
  game_id: number
  bet_type: BetTypeBackend
  bet_amount: number
  odds: number
  potential_payout: number
  selected_team_id?: number | null
  spread_value?: number | null
  over_under_value?: number | null
  is_over?: boolean | null
  status: BetStatus
  actual_payout?: number | null
  placed_at: string
  settled_at?: string | null
  created_at: string
  updated_at?: string | null
  game?: any
  selected_team?: any
}

class BetsService {
  /**
   * Place a new bet
   */
  async placeBet(bet: BetCreate): Promise<BetResponse> {
    return apiRequest<BetResponse>('/bets/', {
      method: 'POST',
      body: JSON.stringify(bet),
    })
  }

  /**
   * Get user's bets
   */
  async getUserBets(
    status?: BetStatus,
    limit: number = 50,
    offset: number = 0
  ): Promise<BetResponse[]> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())

    return apiRequest<BetResponse[]>(`/bets/?${params.toString()}`)
  }

  /**
   * Get a specific bet by ID
   */
  async getBetById(betId: number): Promise<BetResponse> {
    return apiRequest<BetResponse>(`/bets/${betId}`)
  }

  /**
   * Update a bet
   */
  async updateBet(betId: number, update: Partial<BetCreate>): Promise<BetResponse> {
    return apiRequest<BetResponse>(`/bets/${betId}`, {
      method: 'PUT',
      body: JSON.stringify(update),
    })
  }

  /**
   * Cancel a bet
   */
  async cancelBet(betId: number): Promise<void> {
    return apiRequest(`/bets/${betId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Get betting statistics
   */
  async getBettingStats(): Promise<any> {
    return apiRequest('/bets/stats/summary')
  }
}

export const betsService = new BetsService()

