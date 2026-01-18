/**
 * Requests Service
 * Handles request-related API calls (RF-03)
 */

import { apiRequest } from '@/lib/api'

export interface Request {
  id: number
  request_key: string
  event_id: number | null
  user_id: number | null
  status: 'received' | 'processing' | 'partial' | 'completed' | 'failed'
  request_metadata: string | null
  error_message: string | null
  created_at: string
  updated_at: string | null
  completed_at: string | null
}

export interface RequestsResponse {
  items: any[]
  total: number
  page: number
  size: number
  pages: number
}

class RequestsService {
  /**
   * Get my requests
   */
  async getMyRequests(
    limit: number = 50,
    offset: number = 0,
    status?: string
  ): Promise<RequestsResponse> {
    const params = new URLSearchParams()
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    if (status) params.append('status', status)

    const results = await apiRequest<Request[]>(`/requests/me?${params.toString()}`)
    // El backend devuelve un array, pero necesitamos un objeto RequestsResponse
    const page = Math.floor(offset / limit) + 1
    const pages = Math.ceil(results.length / limit)
    return {
      items: results,
      total: results.length,
      page: page,
      size: limit,
      pages: pages
    }
  }

  /**
   * Get request by ID
   */
  async getRequestById(requestId: number): Promise<Request> {
    return apiRequest<Request>(`/requests/${requestId}`)
  }

  /**
   * Get request by key
   */
  async getRequestByKey(requestKey: string): Promise<Request> {
    return apiRequest<Request>(`/requests/key/${requestKey}`)
  }
}

export const requestsService = new RequestsService()

