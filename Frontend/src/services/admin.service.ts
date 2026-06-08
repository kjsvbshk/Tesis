/**
 * Admin Service
 * Handles admin-related API calls (RF-01 - RBAC)
 */

import { apiRequest } from '@/lib/api'

export interface Role {
  id: number
  code: string
  name: string
  description: string | null
  created_at: string
}

export interface Permission {
  id: number
  code: string
  name: string
  description: string | null
  scope: string | null
  created_at: string
}

export interface UserRole {
  id: number
  user_id: number
  role_id: number
  is_active: boolean
  assigned_at: string
  role?: Role
}

export interface ModelVersion {
  id: number
  version: string
  is_active: boolean
  model_metadata: any
  created_at: string
}

class AdminService {
  /**
   * Get all ML models
   */
  async getModels(): Promise<ModelVersion[]> {
    return apiRequest<ModelVersion[]>('/admin/models')
  }

  /**
   * Activate a specific model version
   */
  async activateModel(versionId: number): Promise<{ message: string; version: string }> {
    return apiRequest<{ message: string; version: string }>(`/admin/models/${versionId}/activate`, {
      method: 'POST',
    })
  }

  /**
   * Get all roles
   */
  async getRoles(): Promise<Role[]> {
    return apiRequest<Role[]>('/admin/roles')
  }

  /**
   * Get all permissions
   */
  async getPermissions(): Promise<Permission[]> {
    return apiRequest<Permission[]>('/admin/permissions')
  }

  /**
   * Get user roles
   */
  async getUserRoles(userId: number): Promise<UserRole[]> {
    return apiRequest<UserRole[]>(`/admin/users/${userId}/roles`)
  }

  /**
   * Assign role to user
   */
  async assignRoleToUser(
    userId: number,
    roleId: number
  ): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(`/admin/users/${userId}/roles/${roleId}`, {
      method: 'POST',
    })
  }

  /**
   * Remove role from user
   */
  async removeRoleFromUser(
    userId: number,
    roleId: number
  ): Promise<void> {
    return apiRequest(`/admin/users/${userId}/roles/${roleId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Assign permission to role
   */
  async assignPermissionToRole(
    roleId: number,
    permissionId: number
  ): Promise<{ message: string }> {
    return apiRequest(`/admin/roles/${roleId}/permissions/${permissionId}`, {
      method: 'POST',
    })
  }

  /**
   * Remove permission from role
   */
  async removePermissionFromRole(
    roleId: number,
    permissionId: number
  ): Promise<void> {
    return apiRequest(`/admin/roles/${roleId}/permissions/${permissionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Create a new role
   */
  async createRole(role: { code: string; name: string; description?: string }): Promise<Role> {
    return apiRequest<Role>('/admin/roles', {
      method: 'POST',
      body: JSON.stringify(role),
    })
  }

  /**
   * Update a role
   */
  async updateRole(roleId: number, role: { name?: string; description?: string }): Promise<Role> {
    return apiRequest<Role>(`/admin/roles/${roleId}`, {
      method: 'PUT',
      body: JSON.stringify(role),
    })
  }

  /**
   * Delete a role
   */
  async deleteRole(roleId: number): Promise<void> {
    return apiRequest(`/admin/roles/${roleId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Create a new permission
   */
  async createPermission(permission: { code: string; name: string; description?: string; scope?: string }): Promise<Permission> {
    return apiRequest<Permission>('/admin/permissions', {
      method: 'POST',
      body: JSON.stringify(permission),
    })
  }

  /**
   * Update a permission
   */
  async updatePermission(permissionId: number, permission: { name?: string; description?: string; scope?: string }): Promise<Permission> {
    return apiRequest<Permission>(`/admin/permissions/${permissionId}`, {
      method: 'PUT',
      body: JSON.stringify(permission),
    })
  }

  /**
   * Delete a permission
   */
  async deletePermission(permissionId: number): Promise<void> {
    return apiRequest(`/admin/permissions/${permissionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Check if current user has a specific permission
   */
  async checkPermission(permissionCode: string): Promise<boolean> {
    try {
      const result = await apiRequest<{ has_permission: boolean }>(
        `/admin/permissions/check?permission_code=${encodeURIComponent(permissionCode)}`
      )
      return result.has_permission
    } catch (error: any) {
      console.error('Error checking permission:', error)
      return false
    }
  }
}

export const adminService = new AdminService()

