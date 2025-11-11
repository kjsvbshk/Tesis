import { apiRequest } from '@/lib/api'

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: number
  username: string
  email: string
  rol: string
  credits: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    return apiRequest<TokenResponse>('/users/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
  },

  async register(data: RegisterData): Promise<UserResponse> {
    return apiRequest<UserResponse>('/users/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getCurrentUser(): Promise<UserResponse> {
    return apiRequest<UserResponse>('/users/me')
  },

  async logout(): Promise<void> {
    try {
      // Intentar notificar al servidor del logout (opcional, no crítico si falla)
      const token = this.getToken()
      if (token) {
        try {
          await apiRequest('/users/logout', {
            method: 'POST',
          })
        } catch (error) {
          // Si falla, no importa, seguimos con el logout local
          console.warn('Logout server notification failed, continuing with local logout')
        }
      }
    } finally {
      // Siempre limpiar el almacenamiento local, incluso si el servidor falla
      this.clearStorage()
    }
  },

  clearStorage() {
    // Limpiar todos los datos de autenticación
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    // Limpiar cualquier otro dato relacionado con la sesión si existe
    sessionStorage.clear()
  },

  saveToken(token: string) {
    localStorage.setItem('token', token)
  },

  getToken(): string | null {
    return localStorage.getItem('token')
  },

  saveUser(user: UserResponse) {
    localStorage.setItem('user', JSON.stringify(user))
  },

  getUser(): UserResponse | null {
    const userStr = localStorage.getItem('user')
    if (!userStr) return null
    try {
      return JSON.parse(userStr)
    } catch {
      return null
    }
  },
}

