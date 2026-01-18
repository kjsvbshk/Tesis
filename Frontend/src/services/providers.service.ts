/**
 * Providers Service
 * Handles provider-related API calls
 */

import { apiRequest } from '@/lib/api'

export interface Provider {
  id: number
  code: string
  name: string
  is_active: boolean
  timeout_seconds: number
  max_retries: number
  circuit_breaker_threshold: number
  provider_metadata: string | null
  created_at: string
  updated_at: string | null
}

export interface ProviderEndpoint {
  id: number
  provider_id: number
  purpose: string
  url: string
  method: string
  headers: string | null
  created_at: string
}

export interface ProviderStatus {
  provider_code: string
  provider_id: number
  is_active: boolean
  circuit_breaker: {
    state: string
    failure_count: number
    last_failure: string | null
  }
}

class ProvidersService {
  /**
   * Get all providers
   */
  async getProviders(): Promise<Provider[]> {
    return apiRequest<Provider[]>('/admin/providers')
  }

  /**
   * Get a specific provider
   */
  async getProvider(providerId: number): Promise<Provider> {
    return apiRequest<Provider>(`/admin/providers/${providerId}`)
  }

  /**
   * Create a new provider
   */
  async createProvider(provider: {
    code: string
    name: string
    timeout_seconds?: number
    max_retries?: number
    circuit_breaker_threshold?: number
    provider_metadata?: string
  }): Promise<Provider> {
    return apiRequest<Provider>('/admin/providers', {
      method: 'POST',
      body: JSON.stringify(provider),
    })
  }

  /**
   * Update a provider
   */
  async updateProvider(
    providerId: number,
    provider: {
      name?: string
      is_active?: boolean
      timeout_seconds?: number
      max_retries?: number
      circuit_breaker_threshold?: number
      provider_metadata?: string
    }
  ): Promise<Provider> {
    return apiRequest<Provider>(`/admin/providers/${providerId}`, {
      method: 'PUT',
      body: JSON.stringify(provider),
    })
  }

  /**
   * Delete a provider
   */
  async deleteProvider(providerId: number): Promise<void> {
    return apiRequest(`/admin/providers/${providerId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Get provider endpoints
   */
  async getProviderEndpoints(providerId: number): Promise<ProviderEndpoint[]> {
    return apiRequest<ProviderEndpoint[]>(`/admin/providers/${providerId}/endpoints`)
  }

  /**
   * Create provider endpoint
   */
  async createProviderEndpoint(
    providerId: number,
    endpoint: {
      purpose: string
      url: string
      method?: string
      headers?: string
    }
  ): Promise<ProviderEndpoint> {
    return apiRequest<ProviderEndpoint>(`/admin/providers/${providerId}/endpoints`, {
      method: 'POST',
      body: JSON.stringify(endpoint),
    })
  }

  /**
   * Update provider endpoint
   */
  async updateProviderEndpoint(
    providerId: number,
    endpointId: number,
    endpoint: {
      purpose?: string
      url?: string
      method?: string
      headers?: string
    }
  ): Promise<ProviderEndpoint> {
    return apiRequest<ProviderEndpoint>(`/admin/providers/${providerId}/endpoints/${endpointId}`, {
      method: 'PUT',
      body: JSON.stringify(endpoint),
    })
  }

  /**
   * Delete provider endpoint
   */
  async deleteProviderEndpoint(providerId: number, endpointId: number): Promise<void> {
    return apiRequest(`/admin/providers/${providerId}/endpoints/${endpointId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Get provider status (circuit breaker, etc.)
   */
  async getProviderStatus(providerCode: string): Promise<ProviderStatus> {
    return apiRequest<ProviderStatus>(`/admin/providers/${providerCode}/status`)
  }

  /**
   * Test provider endpoint
   */
  async testProviderEndpoint(providerCode: string, purpose: string): Promise<any> {
    return apiRequest(`/admin/providers/${providerCode}/test`, {
      method: 'POST',
      body: JSON.stringify({ purpose }),
    })
  }
}

export const providersService = new ProvidersService()
