/**
 * User Service
 * Handles user profile and account management API calls
 */

import { apiRequest } from '@/lib/api'

export interface UserUpdate {
  username?: string
  email?: string
  first_name?: string
  last_name?: string
  phone?: string
  birth_date?: string
}

export interface PasswordChange {
  current_password: string
  new_password: string
  confirm_password: string
}

class UserService {
  /**
   * Update current user profile
   */
  async updateProfile(update: UserUpdate): Promise<any> {
    return apiRequest('/users/me', {
      method: 'PUT',
      body: JSON.stringify(update),
    })
  }

  /**
   * Change user password
   * Requires current password and new password (min 8 chars, complexity requirements)
   */
  async changePassword(passwordData: PasswordChange): Promise<void> {
    return apiRequest('/users/me/password', {
      method: 'PUT',
      body: JSON.stringify({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      }),
    })
  }

  /**
   * Get current user info
   */
  async getCurrentUser(): Promise<any> {
    return apiRequest('/users/me')
  }

  /**
   * 2FA Methods
   */
  async setup2FA(): Promise<any> {
    return apiRequest('/users/me/2fa/setup', {
      method: 'POST',
    })
  }

  async verify2FA(code: string): Promise<any> {
    return apiRequest('/users/me/2fa/verify', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
  }

  async enable2FA(code: string): Promise<any> {
    return apiRequest('/users/me/2fa/enable', {
      method: 'POST',
      body: JSON.stringify({ code }),
    })
  }

  async disable2FA(password: string): Promise<any> {
    return apiRequest('/users/me/2fa/disable', {
      method: 'POST',
      body: JSON.stringify({ password }),
    })
  }

  async get2FAStatus(): Promise<any> {
    return apiRequest('/users/me/2fa/status')
  }

  /**
   * Avatar Methods
   */
  async uploadAvatar(file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    
    return apiRequest('/users/me/avatar', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type with boundary for FormData
    })
  }

  async deleteAvatar(): Promise<any> {
    return apiRequest('/users/me/avatar', {
      method: 'DELETE',
    })
  }

  /**
   * Session Methods
   */
  async getSessions(): Promise<any> {
    return apiRequest('/users/me/sessions')
  }

  async revokeSession(sessionId: number): Promise<any> {
    return apiRequest(`/users/me/sessions/${sessionId}/revoke`, {
      method: 'POST',
    })
  }

  async revokeAllSessions(): Promise<any> {
    return apiRequest('/users/me/sessions/revoke-all', {
      method: 'POST',
    })
  }

  /**
   * Deactivate account (clients only)
   * Requires 2FA code verification
   */
  async deactivateAccount(twoFactorCode: string): Promise<any> {
    return apiRequest('/users/me/deactivate', {
      method: 'POST',
      body: JSON.stringify({ two_factor_code: twoFactorCode }),
    })
  }
}

export const userService = new UserService()

