/**
 * Matches Service
 * Handles match-related API calls from ESPN schema
 */

import { apiRequest } from '@/lib/api'
import { cacheService } from './cache.service'

export interface Team {
  id: number
  name: string
  abbreviation: string
  city: string
  conference: string
  division: string
}

export interface MatchResponse {
  id: number
  espn_id?: string | null
  home_team_id: number
  away_team_id: number
  game_date: string
  season: string
  season_type: string
  status: string
  home_score?: number | null
  away_score?: number | null
  winner_id?: number | null
  home_odds?: number | null
  away_odds?: number | null
  over_under?: number | null
  created_at: string
  updated_at?: string | null
  home_team: Team
  away_team: Team
  winner?: Team | null
}

class MatchesService {
  /**
   * Get matches with optional filters
   * Uses cache to avoid repeated API calls during the same session
   */
  async getMatches(params?: {
    date_from?: string
    date_to?: string
    status?: string
    team_id?: number
    limit?: number
    offset?: number
  }): Promise<MatchResponse[]> {
    const cacheKey = cacheService.matchesKey('list', params)
    return cacheService.getOrSet(
      cacheKey,
      async () => {
        const searchParams = new URLSearchParams()
        if (params?.date_from) searchParams.append('date_from', params.date_from)
        if (params?.date_to) searchParams.append('date_to', params.date_to)
        if (params?.status) searchParams.append('status', params.status)
        if (params?.team_id) searchParams.append('team_id', params.team_id.toString())
        if (params?.limit) searchParams.append('limit', params.limit.toString())
        if (params?.offset) searchParams.append('offset', params.offset.toString())

        const query = searchParams.toString()
        return apiRequest<MatchResponse[]>(`/matches/${query ? `?${query}` : ''}`)
      },
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get today's matches
   * Uses cache to avoid repeated API calls during the same session
   */
  async getTodayMatches(): Promise<MatchResponse[]> {
    const cacheKey = cacheService.matchesKey('today')
    return cacheService.getOrSet(
      cacheKey,
      () => apiRequest<MatchResponse[]>('/matches/today'),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get upcoming matches
   * Uses cache to avoid repeated API calls during the same session
   */
  async getUpcomingMatches(days: number = 7): Promise<MatchResponse[]> {
    const cacheKey = cacheService.matchesKey('upcoming', { days })
    return cacheService.getOrSet(
      cacheKey,
      () => apiRequest<MatchResponse[]>(`/matches/upcoming?days=${days}`),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get a specific match by ID
   * Uses cache to avoid repeated API calls during the same session
   */
  async getMatchById(matchId: number): Promise<MatchResponse> {
    const cacheKey = cacheService.matchesKey('by_id', { matchId })
    return cacheService.getOrSet(
      cacheKey,
      () => apiRequest<MatchResponse>(`/matches/${matchId}`),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }
}

export const matchesService = new MatchesService()

