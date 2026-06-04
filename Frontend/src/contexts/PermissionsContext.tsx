/**
 * Permissions Context
 * Manages user permissions and role-based access control
 */

import { createContext, use, useReducer, useEffect, type ReactNode } from 'react'
import { useAuth } from './AuthContext'
import { adminService, type Role, type Permission, type UserRole } from '@/services/admin.service'
import { apiRequest } from '@/lib/api'

interface PermissionsContextType {
  roles: Role[]
  permissions: Permission[]
  userRoles: UserRole[]
  isLoading: boolean
  hasPermission: (permissionCode: string) => Promise<boolean>
  hasPermissionSync: (permissionCode: string) => boolean
  hasScope: (scope: string) => boolean
  hasRole: (roleCode: string) => boolean
  refreshPermissions: () => Promise<void>
}

const PermissionsContext = createContext<PermissionsContextType | undefined>(undefined)

interface PermissionsState {
  roles: Role[]
  permissions: Permission[]
  userRoles: UserRole[]
  userPermissions: string[]
  isLoading: boolean
}

type PermissionsAction =
  | { type: 'SET_ROLES'; payload: Role[] }
  | { type: 'SET_PERMISSIONS'; payload: Permission[] }
  | { type: 'SET_USER_ROLES'; payload: UserRole[] }
  | { type: 'SET_USER_PERMISSIONS'; payload: string[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'RESET' }

const permissionsInitialState: PermissionsState = {
  roles: [],
  permissions: [],
  userRoles: [],
  userPermissions: [],
  isLoading: true,
}

function permissionsReducer(state: PermissionsState, action: PermissionsAction): PermissionsState {
  switch (action.type) {
    case 'SET_ROLES': return { ...state, roles: action.payload }
    case 'SET_PERMISSIONS': return { ...state, permissions: action.payload }
    case 'SET_USER_ROLES': return { ...state, userRoles: action.payload }
    case 'SET_USER_PERMISSIONS': return { ...state, userPermissions: action.payload }
    case 'SET_LOADING': return { ...state, isLoading: action.payload }
    case 'RESET': return { ...permissionsInitialState, isLoading: false }
    default: return state
  }
}

export function PermissionsProvider({ children }: { children: ReactNode }) {
  const { user, isAuthenticated } = useAuth()
  const [state, dispatch] = useReducer(permissionsReducer, permissionsInitialState)
  const { roles, permissions, userRoles, userPermissions, isLoading } = state
  // Cache for permission checks to reduce API calls
  const permissionCache = new Map<string, { hasPermission: boolean; timestamp: number }>()
  const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

  useEffect(() => {
    if (isAuthenticated && user) {
      refreshPermissions()
    } else {
      dispatch({ type: 'RESET' })
    }
  }, [isAuthenticated, user?.id]) // Add user?.id to dependencies

  const refreshPermissions = async () => {
    if (!user) return

    try {
      dispatch({ type: 'SET_LOADING', payload: true })
      
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
        dispatch({ type: 'SET_USER_ROLES', payload: userRolesData })
        // Store permissions for fast local checking
        dispatch({ type: 'SET_USER_PERMISSIONS', payload: permissionsData.permissions })
        
        // Pre-populate cache with known permissions
        permissionsData.permissions.forEach(perm => {
          permissionCache.set(perm, {
            hasPermission: true,
            timestamp: Date.now(),
          })
        })

        // Get all roles and permissions (for admin view) - only if user is admin
        if (permissionsData.roles.some(r => r.code === 'admin')) {
          try {
            const allRoles = await adminService.getRoles()
            const allPermissions = await adminService.getPermissions()
            dispatch({ type: 'SET_ROLES', payload: allRoles })
            dispatch({ type: 'SET_PERMISSIONS', payload: allPermissions })
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
          dispatch({ type: 'SET_USER_ROLES', payload: rolesData })
        } catch (fallbackError) {
          console.warn('Could not fetch user roles:', fallbackError)
        }
      }
    } catch (error) {
      console.error('Error refreshing permissions:', error)
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }

  /**
   * Check if user has a specific permission
   * Uses backend API with caching to reduce calls
   */
  const hasPermission = async (permissionCode: string): Promise<boolean> => {
    if (!user || !userRoles.length) return false

    // Check if user has admin role (has all permissions) - fast path
    const hasAdminRole = userRoles.some(ur => ur.role?.code === 'admin')
    if (hasAdminRole) return true

    // Check local permissions list first (from /users/me/permissions)
    if (userPermissions.includes(permissionCode)) {
      return true
    }

    // Check cache
    const cached = permissionCache.get(permissionCode)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.hasPermission
    }

    // Call backend to check permission (for permissions not in local list)
    try {
      const hasPerm = await adminService.checkPermission(permissionCode)
      // Update cache
      permissionCache.set(permissionCode, {
        hasPermission: hasPerm,
        timestamp: Date.now(),
      })
      return hasPerm
    } catch (error) {
      console.error('Error checking permission:', error)
      return false
    }
  }

  /**
   * Synchronous version of hasPermission for use in components
   * Returns cached value or checks local permissions list
   */
  const hasPermissionSync = (permissionCode: string): boolean => {
    if (!user || !userRoles.length) return false

    // Check if user has admin role (has all permissions) - fast path
    const hasAdminRole = userRoles.some(ur => ur.role?.code === 'admin')
    if (hasAdminRole) return true

    // Check local permissions list (from /users/me/permissions)
    if (userPermissions.includes(permissionCode)) {
      return true
    }

    // Check cache
    const cached = permissionCache.get(permissionCode)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.hasPermission
    }

    // If not cached, trigger async check and return false for now
    // Component should use useEffect to handle async permission checks
    hasPermission(permissionCode).catch(console.error)
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
        hasPermissionSync,
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
  const context = use(PermissionsContext)
  if (context === undefined) {
    throw new Error('usePermissions must be used within a PermissionsProvider')
  }
  return context
}

