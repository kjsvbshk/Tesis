// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const apiConfig = {
  baseURL: API_BASE_URL,
  timeout: 10000,
}

// Helper function to make API requests
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token')
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Support for idempotency key header
  if (options.headers && 'X-Idempotency-Key' in options.headers) {
    headers['X-Idempotency-Key'] = (options.headers as any)['X-Idempotency-Key']
  }

  try {
    const response = await fetch(`${apiConfig.baseURL}${endpoint}`, {
      ...options,
      headers,
    })

    // Handle empty response (network error, CORS, etc.)
    if (!response || response.status === 0) {
      throw new Error('No se pudo conectar con el servidor. Verifica que el backend esté corriendo en http://localhost:8000')
    }

    // Read response as text first to check if it's empty
    const text = await response.text()
    
    if (!response.ok) {
      if (!text || text.trim() === '') {
        throw new Error(`Error HTTP ${response.status}: ${response.statusText}`)
      }
      try {
        const error = JSON.parse(text)
        throw new Error(error.detail || `Error HTTP ${response.status}`)
      } catch (parseError) {
        throw new Error(`Error HTTP ${response.status}: ${text || response.statusText}`)
      }
    }

    // Handle empty response body
    if (!text || text.trim() === '') {
      throw new Error('Respuesta vacía del servidor')
    }

    // Try to parse as JSON
    try {
      return JSON.parse(text) as T
    } catch (parseError) {
      // If not JSON, return as text
      return text as unknown as T
    }
  } catch (error: any) {
    // Handle network errors
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Error de conexión: No se pudo conectar con el servidor. Verifica que el backend esté corriendo.')
    }
    // Re-throw other errors
    throw error
  }
}

