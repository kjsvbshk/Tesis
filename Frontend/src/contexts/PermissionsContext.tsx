/**
 * Permissions Context
 * Manages user permissions and role-based access control
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { adminService, type Role, type Permission, type UserRole } from '@/services/admin.service'
import { apiRequest } from '@/lib/api'

interface PermissionsContextType {
  roles: Role[]
  permissions: Permission[]
  userRoles: UserRole[]
  isLoading: boolean
  hasPermission: (permissionCode: string) => boolean
  hasScope: (scope: string) => boolean
  hasRole: (roleCode: string) => boolean
  refreshPermissions: () => Promise<void>
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined)

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth()
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated && user) {
      refreshPermissions()
    } else {
      setRoles([])
      setPermissions([])
      setUserRoles([])
      setIsLoading(false)
    }
  }, [isAuthenticated, user?.id]) // Add user?.id to dependencies

  const refreshPermissions = async () => {
    if (!user) return

    try {
      setIsLoading(true)
      
      // Get current user's permissions and roles from /users/me/permissions
      try {
        const permissionsData = await apiRequest<{
          user_id: number
          username: string
          roles: Array<{ id: number; code: string; name: string }>
          permissions: string[]
          scopes: string[]
        }>('/users/me/permissions')
        
        // Convert roles to UserRole format
        const userRolesData = permissionsData.roles.map(role => ({
          id: 0, // Will be set by backend
          user_id: user.id,
          role_id: role.id,
          is_active: true,
          assigned_at: new Date().toISOString(),
          role: {
            id: role.id,
            code: role.code,
            name: role.name,
            description: null,
            created_at: new Date().toISOString(),
          },
        }))
        setUserRoles(userRolesData)

        // Get all roles and permissions (for admin view) - only if user is admin
        if (permissionsData.roles.some(r => r.code === 'admin')) {
          try {
            const allRoles = await adminService.getRoles()
            const allPermissions = await adminService.getPermissions()
            setRoles(allRoles)
            setPermissions(allPermissions)
          } catch (error) {
            // User might not have admin permissions, that's ok
            console.warn('Could not fetch all roles/permissions:', error)
          }
        }
      } catch (error) {
        // If endpoint doesn't exist or fails, try alternative method
        console.warn('Could not fetch permissions from /users/me/permissions:', error)
        // Fallback: try to get user roles directly (may fail if not admin)
        try {
          const rolesData = await adminService.getUserRoles(user.id)
          setUserRoles(rolesData)
        } catch (fallbackError) {
          console.warn('Could not fetch user roles:', fallbackError)
        }
      }
    } catch (error) {
      console.error('Error refreshing permissions:', error)
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Check if user has a specific permission
   */
  const hasPermission = (_permissionCode: string): boolean => {
    if (!user || !userRoles.length) return false

    // For now, we'll check based on the user's role
    // In a full implementation, we'd check the permissions associated with the user's roles
    // This is a simplified version - the backend should handle permission checks
    
    // Check if user has admin role (has all permissions)
    const hasAdminRole = userRoles.some(ur => ur.role?.code === 'admin')
    if (hasAdminRole) return true

    // TODO: Implement full permission checking based on role-permission associations
    // For now, return false for specific permission checks
    return false
  }

  /**
   * Check if user has access to a specific scope
   */
  const hasScope = (scope: string): boolean => {
    if (!user || !userRoles.length) return false

    // Check if user has admin role
    const hasAdminRole = userRoles.some(ur => ur.role?.code === 'admin')
    if (hasAdminRole) return true

    // Check if user has a role that grants access to this scope
    // This is a simplified check - in production, this should check actual permissions
    const scopeRoles: Record<string, string[]> = {
      'predictions': ['admin', 'user', 'operator'],
      'bets': ['admin', 'user'],
      'users': ['admin'],
      'admin': ['admin'],
      'audit': ['admin', 'operator'],
    }

    const allowedRoles = scopeRoles[scope] || []
    return userRoles.some(ur => allowedRoles.includes(ur.role?.code || ''))
  }

  /**
   * Check if user has a specific role
   */
  const hasRole = (roleCode: string): boolean => {
    if (!user || !userRoles.length) return false
    return userRoles.some(ur => ur.role?.code === roleCode && ur.is_active)
  }

  return (
    <PermissionsContext.Provider
      value={{
        roles,
        permissions,
        userRoles,
        isLoading,
        hasPermission,
        hasScope,
        hasRole,
        refreshPermissions,
      }}
    >
      {children}
    </PermissionsContext.Provider>
  )
}

export function usePermissions() {
  const context = useContext(PermissionsContext)
  if (context === undefined) {
    throw new Error('usePermissions must be used within a PermissionsProvider')
  }
  return context
}

