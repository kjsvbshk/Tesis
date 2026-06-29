/**
 * Matches Service
 * Handles match-related API calls from ESPN schema
 */

import { apiRequest, buildQueryString } from '@/lib/api'
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

export interface MatchSentiment {
  game_id: number
  total_bets: number
  home_pct: number | null
  away_pct: number | null
  over_pct: number | null
  under_pct: number | null
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
    return cacheService.getOrSet(
      cacheService.generateKey('matches', 'list', params),
      async () => {
        return apiRequest<MatchResponse[]>(`/matches/${buildQueryString({ ...params })}`)
      },
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get today's matches
   * Uses cache to avoid repeated API calls during the same session
   */
  async getTodayMatches(): Promise<MatchResponse[]> {
    return cacheService.getOrSet(
      cacheService.generateKey('matches', 'today'),
      () => apiRequest<MatchResponse[]>('/matches/today'),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get upcoming matches
   * Uses cache to avoid repeated API calls during the same session
   */
  async getUpcomingMatches(days: number = 7): Promise<MatchResponse[]> {
    return cacheService.getOrSet(
      cacheService.generateKey('matches', 'upcoming', days),
      () => apiRequest<MatchResponse[]>(`/matches/upcoming?days=${days}`),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get a specific match by ID
   * Uses cache to avoid repeated API calls during the same session
   */
  async getMatchById(matchId: number): Promise<MatchResponse> {
    return cacheService.getOrSet(
      cacheService.generateKey('matches', 'by_id', matchId),
      () => apiRequest<MatchResponse>(`/matches/${matchId}`),
      5 * 60 * 1000 // 5 minutes TTL
    )
  }

  /**
   * Get betting sentiment for a match (% of user bets per side).
   * Returns null when there are no bets yet.
   * Short TTL — sentiment changes as users place bets.
   */
  async getMatchSentiment(matchId: number): Promise<MatchSentiment | null> {
    try {
      return await cacheService.getOrSet(
        cacheService.generateKey('matches', 'sentiment', matchId),
        () => apiRequest<MatchSentiment>(`/matches/${matchId}/sentiment`),
        60 * 1000 // 1 minute TTL
      )
    } catch {
      return null
    }
  }
}

export const matchesService = new MatchesService()

