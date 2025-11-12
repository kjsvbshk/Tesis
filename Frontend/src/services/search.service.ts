/**
 * Search Service
 * Handles advanced search API calls (RF-12)
 */

import { apiRequest } from '@/lib/api'

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
    const params = new URLSearchParams()
    if (filters.request_id) params.append('request_id', filters.request_id.toString())
    if (filters.request_key) params.append('request_key', filters.request_key)
    if (filters.event_id) params.append('event_id', filters.event_id.toString())
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    if (filters.status) params.append('status', filters.status)
    if (filters.user_id) params.append('user_id', filters.user_id.toString())
    params.append('limit', (filters.limit || 50).toString())
    params.append('offset', (filters.offset || 0).toString())

    return apiRequest<SearchResponse<RequestSearchResult>>(
      `/search/requests?${params.toString()}`
    )
  }

  /**
   * Search idempotency keys
   */
  async searchIdempotencyKeys(
    filters: Omit<SearchFilters, 'status' | 'user_id' | 'event_id'>
  ): Promise<SearchResponse<IdempotencyKeySearchResult>> {
    const params = new URLSearchParams()
    if (filters.request_key) params.append('request_key', filters.request_key)
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    params.append('limit', (filters.limit || 50).toString())
    params.append('offset', (filters.offset || 0).toString())

    return apiRequest<SearchResponse<IdempotencyKeySearchResult>>(
      `/search/idempotency-keys?${params.toString()}`
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
    const params = new URLSearchParams()
    if (filters.actor_user_id) params.append('actor_user_id', filters.actor_user_id.toString())
    if (filters.action) params.append('action', filters.action)
    if (filters.resource_type) params.append('resource_type', filters.resource_type)
    if (filters.resource_id) params.append('resource_id', filters.resource_id.toString())
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    params.append('limit', (filters.limit || 50).toString())
    params.append('offset', (filters.offset || 0).toString())

    return apiRequest<SearchResponse<AuditLogSearchResult>>(
      `/search/audit-logs?${params.toString()}`
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
    const params = new URLSearchParams()
    if (filters.event_id) params.append('event_id', filters.event_id.toString())
    if (filters.date_from) params.append('date_from', filters.date_from)
    if (filters.date_to) params.append('date_to', filters.date_to)
    params.append('limit', (filters.limit || 50).toString())
    params.append('offset', (filters.offset || 0).toString())

    return apiRequest<SearchResponse<EventSearchResult>>(
      `/search/events?${params.toString()}`
    )
  }
}

export const searchService = new SearchService()

