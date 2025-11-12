/**
 * Users Service
 * Handles user management API calls (for admin)
 */

import { apiRequest } from '@/lib/api'

export interface User {
  id: number
  username: string
  email: string
  rol: string
  credits: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface UserCreate {
  username: string
  email: string
  password: string
}

export interface UserUpdate {
  username?: string
  email?: string
  password?: string
  credits?: number
  is_active?: boolean
}

class UsersService {
  /**
   * Get all users (admin only)
   */
  async getAllUsers(limit: number = 50, offset: number = 0): Promise<User[]> {
    return apiRequest<User[]>(`/users/?limit=${limit}&offset=${offset}`)
  }

  /**
   * Get user by ID
   */
  async getUserById(userId: number): Promise<User> {
    return apiRequest<User>(`/users/${userId}`)
  }

  /**
   * Create user (admin only - if endpoint exists)
   */
  async createUser(user: UserCreate): Promise<User> {
    return apiRequest<User>('/users/register', {
      method: 'POST',
      body: JSON.stringify(user),
    })
  }

  /**
   * Update user (admin only - if endpoint exists)
   */
  async updateUser(userId: number, user: UserUpdate): Promise<User> {
    return apiRequest<User>(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(user),
    })
  }

  /**
   * Delete user (admin only - if endpoint exists)
   */
  async deleteUser(userId: number): Promise<void> {
    return apiRequest(`/users/${userId}`, {
      method: 'DELETE',
    })
  }
}

export const usersService = new UsersService()

