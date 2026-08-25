/**
 * Bets Service
 * Handles bet-related API calls
 */

import { apiRequest, buildQueryString } from '@/lib/api'
import { cacheService } from './cache.service'

const STATS_CACHE_KEY = cacheService.generateKey('bets', 'stats')

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
    const result = await apiRequest<BetResponse>('/bets/', {
      method: 'POST',
      body: JSON.stringify(bet),
    })
    cacheService.delete(STATS_CACHE_KEY) // credits/pending_bets changed
    return result
  }

  /**
   * Get user's bets
   */
  async getUserBets(
    status?: BetStatus,
    limit: number = 50,
    offset: number = 0
  ): Promise<BetResponse[]> {
    return apiRequest<BetResponse[]>(`/bets/${buildQueryString({ status, limit, offset })}`)
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
    const result = await apiRequest<BetResponse>(`/bets/${betId}`, {
      method: 'PUT',
      body: JSON.stringify(update),
    })
    cacheService.delete(STATS_CACHE_KEY)
    return result
  }

  /**
   * Cancel a bet
   */
  async cancelBet(betId: number): Promise<void> {
    await apiRequest(`/bets/${betId}`, {
      method: 'DELETE',
    })
    cacheService.delete(STATS_CACHE_KEY) // credits refunded, pending_bets changed
  }

  /**
   * Get betting statistics.
   * Cached client-side (short TTL) — this was hitting the backend fresh on
   * every dashboard visit, opening 2 DB sessions (app + espn) each time for
   * a full scan of the user's bets that rarely changes between page loads.
   * Invalidated explicitly on placeBet/cancelBet so credits update right away.
   */
  async getBettingStats(): Promise<any> {
    return cacheService.getOrSet(
      STATS_CACHE_KEY,
      () => apiRequest('/bets/stats/summary'),
      30 * 1000 // 30s TTL
    )
  }
}

export const betsService = new BetsService()

