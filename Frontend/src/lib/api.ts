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
  
  const headers: any = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
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
      throw new Error('No se pudo conectar con el servidor. Verifica la configuración de la API.')
    }

    // Read response as text first to check if it's empty
    const text = await response.text()
    
    if (!response.ok) {
      // Handle 401 Unauthorized specifically
      if (response.status === 401) {
        if (!text || text.trim() === '') {
          throw new Error('Usuario o contraseña incorrectos')
        }
        try {
          const error = JSON.parse(text)
          // Check for common 401 error messages
          const errorMessage = error.detail || error.message || 'Usuario o contraseña incorrectos'
          throw new Error(errorMessage.includes('Incorrect') || errorMessage.includes('invalid') || errorMessage.includes('401') 
            ? 'Usuario o contraseña incorrectos' 
            : errorMessage)
        } catch (parseError) {
          throw new Error('Usuario o contraseña incorrectos')
        }
      }
      
      // Handle other errors
      if (!text || text.trim() === '') {
        throw new Error(`Error HTTP ${response.status}: ${response.statusText}`)
      }
      try {
        const error = JSON.parse(text)
        throw new Error(error.detail || error.message || `Error HTTP ${response.status}`)
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
      throw new Error('Error de conexión: No se pudo conectar con el servidor. Verifica la configuración de la API y que el backend esté disponible.')
    }
    // Re-throw other errors
    throw error
  }
}

