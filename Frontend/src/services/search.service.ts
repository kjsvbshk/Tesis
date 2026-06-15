/**
 * Search Service
 * Handles advanced search API calls (RF-12)
 */

import { apiRequest, buildQueryString } from '@/lib/api'

export interface SearchFilters {
  request_id?: number
  request_key?: string
  event_id?: number
  date_from?: string
  date_to?: string
  status?: string
  user_id?: number
  limit?: number
  offset?: number
}

export interface RequestSearchResult {
  id: number
  request_key: string
  event_id: number | null
  user_id: number | null
  status: string
  created_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface IdempotencyKeySearchResult {
  id: number
  request_key: string
  request_id: number | null
  created_at: string | null
  expires_at: string | null
}

export interface AuditLogSearchResult {
  id: number
  actor_user_id: number | null
  action: string
  resource_type: string | null
  resource_id: number | null
  created_at: string | null
  before: string | null
  after: string | null
  metadata: string | null
}

export interface EventSearchResult {
  event_id: number
  request_id: number
  request_key: string
  user_id: number | null
  status: string
  created_at: string | null
}

export interface SearchResponse<T> {
  total: number
  limit: number
  offset: number
  results: T[]
}

class SearchService {
  /**
   * Search requests
   */
  async searchRequests(
    filters: SearchFilters
  ): Promise<SearchResponse<RequestSearchResult>> {
    return apiRequest<SearchResponse<RequestSearchResult>>(
      `/search/requests${buildQueryString({
        ...filters,
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
      })}`
    )
  }

  /**
   * Search idempotency keys
   */
  async searchIdempotencyKeys(
    filters: Omit<SearchFilters, 'status' | 'user_id' | 'event_id'>
  ): Promise<SearchResponse<IdempotencyKeySearchResult>> {
    return apiRequest<SearchResponse<IdempotencyKeySearchResult>>(
      `/search/idempotency-keys${buildQueryString({
        ...filters,
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
      })}`
    )
  }

  /**
   * Search audit logs
   */
  async searchAuditLogs(
    filters: {
      actor_user_id?: number
      action?: string
      resource_type?: string
      resource_id?: number
      date_from?: string
      date_to?: string
      limit?: number
      offset?: number
    }
  ): Promise<SearchResponse<AuditLogSearchResult>> {
    return apiRequest<SearchResponse<AuditLogSearchResult>>(
      `/search/audit-logs${buildQueryString({
        ...filters,
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
      })}`
    )
  }

  /**
   * Search events
   */
  async searchEvents(
    filters: {
      event_id?: number
      date_from?: string
      date_to?: string
      limit?: number
      offset?: number
    }
  ): Promise<SearchResponse<EventSearchResult>> {
    return apiRequest<SearchResponse<EventSearchResult>>(
      `/search/events${buildQueryString({
        ...filters,
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
      })}`
    )
  }
}

export const searchService = new SearchService()

