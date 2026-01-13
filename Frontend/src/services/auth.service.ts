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

  async sendVerificationCode(email: string, purpose: 'registration' | 'password_reset' = 'registration'): Promise<{ message: string; code?: string }> {
    return apiRequest<{ message: string; code?: string }>('/users/send-verification-code', {
      method: 'POST',
      body: JSON.stringify({ email, purpose }),
    })
  },

  async verifyCode(
    email: string, 
    code: string, 
    purpose: 'registration' | 'password_reset' = 'registration',
    username?: string
  ): Promise<{ message: string; verified: boolean; email?: string }> {
    const body: any = { code, purpose }
    if (purpose === 'password_reset' && username) {
      body.username = username
    } else {
      body.email = email
    }
    return apiRequest<{ message: string; verified: boolean; email?: string }>('/users/verify-code', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  },

  async registerWithVerification(data: {
    username: string
    email: string
    password: string
    verification_code: string
  }): Promise<UserResponse> {
    return apiRequest<UserResponse>('/users/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async forgotPassword(username: string): Promise<{ message: string; code?: string; email?: string }> {
    return apiRequest<{ message: string; code?: string; email?: string }>('/users/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ username }),
    })
  },

  async resetPassword(username: string, code: string, newPassword: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>('/users/reset-password', {
      method: 'POST',
      body: JSON.stringify({ username, code, new_password: newPassword }),
    })
  },
}

