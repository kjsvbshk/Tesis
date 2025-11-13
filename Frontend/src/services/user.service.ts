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
  address?: string
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
   * Note: This endpoint may need to be created in the backend
   */
  async changePassword(passwordData: PasswordChange): Promise<void> {
    // TODO: Backend needs to implement this endpoint
    // For now, we'll use a placeholder
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
}

export const userService = new UserService()

