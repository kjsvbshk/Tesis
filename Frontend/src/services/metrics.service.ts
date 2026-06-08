/**
 * Metrics Service
 * Handles metrics and health check API calls (RF-14)
 */

import { apiRequest } from '@/lib/api'

export interface HealthStatus {
  status: string
  service: string
  timestamp: string
  version: string
}

export interface ReadinessStatus {
  status: string
  database: string
  timestamp: string
}

export interface CacheStatus {
  total_entries: number
  active_entries: number
  stale_entries: number
  expired_entries: number
  last_cleaned: string | null
}

export interface SystemMetrics {
  timestamp: string
  requests: {
    total: number
    completed: number
    failed: number
    processing: number
    success_rate: number
    failure_rate: number
  }
  audit: {
    total_logs: number
  }
  outbox: {
    total_events: number
    unpublished_events: number
    published_events: number
  }
  predictions: {
    total: number
  }
  cache: CacheStatus
}

export interface RequestMetrics {
  timestamp: string
  period: {
    from: string | null
    to: string | null
  }
  requests: {
    total: number
    completed: number
    failed: number
    processing: number
    success_rate: number
    failure_rate: number
  }
  performance: {
    avg_latency_ms: number | null
    total_predictions: number
  }
}

class MetricsService {
  /**
   * Get basic health check
   */
  async getHealth(): Promise<HealthStatus> {
    return apiRequest<HealthStatus>('/health/health')
  }

  /**
   * Get liveness probe
   */
  async getLiveness(): Promise<{ status: string; timestamp: string }> {
    return apiRequest('/health/liveness')
  }

  /**
   * Get readiness probe
   */
  async getReadiness(): Promise<ReadinessStatus> {
    return apiRequest<ReadinessStatus>('/health/readiness')
  }

  /**
   * Get system metrics
   */
  async getMetrics(): Promise<SystemMetrics> {
    return apiRequest<SystemMetrics>('/health/metrics')
  }

  /**
   * Get request metrics
   */
  async getRequestMetrics(
    dateFrom?: string,
    dateTo?: string
  ): Promise<RequestMetrics> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)

    const query = params.toString()
    return apiRequest<RequestMetrics>(
      `/health/metrics/requests${query ? `?${query}` : ''}`
    )
  }
}

export const metricsService = new MetricsService()

