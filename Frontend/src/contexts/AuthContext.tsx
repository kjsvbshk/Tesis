import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { authService, type UserResponse } from '@/services/auth.service'

interface AuthContextType {
  user: UserResponse | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check if user is already logged in
    const token = authService.getToken()
    const savedUser = authService.getUser()
    
    if (token && savedUser) {
      setUser(savedUser)
      // Optionally verify token is still valid
      refreshUser().catch(() => {
        authService.logout()
        setUser(null)
      })
    }
    setIsLoading(false)
  }, [])

  const refreshUser = async () => {
    try {
      const userData = await authService.getCurrentUser()
      setUser(userData)
      authService.saveUser(userData)
    } catch (error) {
      throw error
    }
  }

  const login = async (username: string, password: string) => {
    try {
      const tokenResponse = await authService.login({ username, password })
      authService.saveToken(tokenResponse.access_token)
      
      const userData = await authService.getCurrentUser()
      setUser(userData)
      authService.saveUser(userData)
      
      // Marcar que el usuario acaba de iniciar sesión para mostrar mensaje de bienvenida
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('justLoggedIn', 'true')
        // Pequeño delay para que el toast se muestre antes de redirigir
        setTimeout(() => {
          window.location.href = '/'
        }, 100)
      }
    } catch (error) {
      throw error
    }
  }

  const register = async (username: string, email: string, password: string) => {
    try {
      await authService.register({ username, email, password })
      // After registration, redirect to login page (don't auto-login)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    } catch (error) {
      throw error
    }
  }

  const logout = async () => {
    try {
      // Limpiar estado local primero
      setUser(null)
      setIsLoading(true)
      
      // Llamar al servicio de logout (notifica al servidor y limpia storage)
      await authService.logout()
      
      // Redirigir al login
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    } catch (error) {
      // Aunque falle, asegurarse de limpiar todo localmente
      console.error('Error during logout:', error)
      authService.clearStorage()
      setUser(null)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

