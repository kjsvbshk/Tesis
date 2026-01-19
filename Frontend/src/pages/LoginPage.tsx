import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'

export function LoginPage() {
  const { toast } = useToast()
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [requires2FA, setRequires2FA] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<{ username?: string; password?: string; twoFactorCode?: string }>({})

  const validateForm = () => {
    const newErrors: { username?: string; password?: string } = {}
    
    if (!username.trim()) {
      newErrors.username = 'El nombre de usuario es requerido'
    } else if (username.trim().length < 3) {
      newErrors.username = 'El nombre de usuario debe tener al menos 3 caracteres'
    }
    
    if (!password) {
      newErrors.password = 'La contraseña es requerida'
    } else if (password.length < 6) {
      newErrors.password = 'La contraseña debe tener al menos 6 caracteres'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate username and password (always required)
    if (!validateForm()) {
      return
    }

    // If 2FA is required, validate the code
    if (requires2FA) {
      if (!twoFactorCode || twoFactorCode.length !== 6) {
        setErrors({ ...errors, twoFactorCode: 'El código de 2FA debe tener 6 dígitos' })
        return
      }
    }

    setIsLoading(true)
    try {
      // Always send username, password, and 2FA code (if required) in the same request
      // The backend will verify credentials first, then 2FA code if enabled
      await login(username.trim(), password, requires2FA ? twoFactorCode : undefined)
      // El mensaje de éxito se mostrará en HomePage después de la redirección
    } catch (error: any) {
      console.error('Login error:', error)
      
      // Check if 2FA is required - this happens on first login attempt when 2FA is enabled
      // Credentials are correct, but 2FA code is missing
      if (error?.requires2FA || error?.message?.includes('2FA code is required')) {
        setRequires2FA(true)
        setErrors({}) // Clear previous errors (credentials were correct)
        toast({
          title: 'Código 2FA requerido',
          description: 'Las credenciales son correctas. Por favor ingresa el código de 6 dígitos de tu aplicación de autenticación',
        })
        setIsLoading(false)
        return
      }
      
      // Check if 2FA code was invalid (credentials were correct, but 2FA code was wrong)
      if (requires2FA && error?.message?.includes('Invalid 2FA')) {
        setErrors({ ...errors, twoFactorCode: 'Código 2FA inválido. Por favor intenta nuevamente.' })
        setTwoFactorCode('') // Clear the code field
        toast({
          title: 'Código 2FA inválido',
          description: 'El código ingresado no es válido. Por favor verifica e intenta nuevamente.',
          variant: 'destructive',
        })
        setIsLoading(false)
        return
      }
      
      const errorMessage = error?.message || 'Error al iniciar sesión'
      
      // Mensaje más específico para errores de autenticación
      let displayMessage = errorMessage
      if (errorMessage.includes('Incorrect') || 
          errorMessage.includes('incorrect') || 
          errorMessage.includes('invalid') ||
          errorMessage.includes('401') ||
          errorMessage.includes('Unauthorized')) {
        // Only show "incorrect password" if 2FA is not required
        if (!errorMessage.includes('2FA')) {
          displayMessage = 'Usuario o contraseña incorrectos'
        }
      }
      
      toast({
        title: 'Error de autenticación',
        description: displayMessage,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8 bg-[#0B132B]">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="sm:mx-auto sm:w-full sm:max-w-sm"
      >
        <div className="flex justify-center">
          <div className="logo-container pulse-glow">
            <img src="/logo.png" alt="HAW Logo" className="h-12 w-auto" />
          </div>
        </div>
        <h2 className="mt-10 text-center text-3xl font-heading font-bold tracking-tight text-white">
          Inicia sesión en tu cuenta
        </h2>
        <p className="mt-2 text-center text-sm text-[#B0B3C5]">
          O{' '}
          <Link
            to="/registro"
            className="font-semibold text-[#00FF73] hover:text-[#00D95F] transition-colors"
          >
            crea una cuenta nueva
          </Link>
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <Label htmlFor="username" className="block text-sm font-medium text-white">
              Nombre de usuario
            </Label>
            <div className="mt-2">
              <Input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value)
                  if (errors.username) {
                    setErrors({ ...errors, username: undefined })
                  }
                }}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  errors.username ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="usuario123"
              />
              {errors.username && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{errors.username}</p>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="block text-sm font-medium text-white">
                Contraseña
              </Label>
              <div className="text-sm">
                <Link
                  to="/recuperar-contraseña"
                  className="font-semibold text-[#00FF73] hover:text-[#00D95F] transition-colors"
                >
                  ¿Olvidaste tu contraseña?
                </Link>
              </div>
            </div>
            <div className="mt-2">
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  if (errors.password) {
                    setErrors({ ...errors, password: undefined })
                  }
                }}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  errors.password ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{errors.password}</p>
              )}
            </div>
          </div>

          {requires2FA && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="mb-2 rounded-lg bg-[#00FF73]/10 border border-[#00FF73]/30 p-3">
                <p className="text-sm text-[#00FF73] text-center">
                  ✓ Credenciales verificadas. Ingresa tu código 2FA para completar el inicio de sesión.
                </p>
              </div>
              <Label htmlFor="twoFactorCode" className="block text-sm font-medium text-white">
                Código de Autenticación (2FA)
              </Label>
              <div className="mt-2">
                <Input
                  id="twoFactorCode"
                  name="twoFactorCode"
                  type="text"
                  autoComplete="one-time-code"
                  required
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => {
                    // Solo permitir números
                    const value = e.target.value.replace(/\D/g, '')
                    setTwoFactorCode(value)
                    if (errors.twoFactorCode) {
                      setErrors({ ...errors, twoFactorCode: undefined })
                    }
                  }}
                  className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 text-center text-2xl tracking-widest ${
                    errors.twoFactorCode ? 'border-[#FF4C4C]' : ''
                  }`}
                  placeholder="000000"
                  autoFocus
                />
                {errors.twoFactorCode && (
                  <p className="mt-1 text-sm text-[#FF4C4C]">{errors.twoFactorCode}</p>
                )}
                <p className="mt-2 text-xs text-[#B0B3C5] text-center">
                  Ingresa el código de 6 dígitos de tu aplicación de autenticación
                </p>
              </div>
            </motion.div>
          )}

          <div>
            <Button
              type="submit"
              disabled={isLoading || (requires2FA && twoFactorCode.length !== 6)}
              className="flex w-full justify-center rounded-lg bg-gradient-to-r from-[#00FF73] to-[#00D95F] px-3 py-2.5 text-sm font-semibold text-[#0B132B] hover:from-[#00D95F] hover:to-[#00FF73] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00FF73] transition-all duration-300 shadow-[0_0_20px_rgba(0,255,115,0.3)] hover:shadow-[0_0_25px_rgba(0,255,115,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (requires2FA ? 'Verificando código...' : 'Iniciando sesión...') : (requires2FA ? 'Verificar y continuar' : 'Iniciar sesión')}
            </Button>
          </div>
        </form>

        <p className="mt-10 text-center text-sm text-[#B0B3C5]">
          ¿No tienes una cuenta?{' '}
          <Link
            to="/registro"
            className="font-semibold text-[#00FF73] hover:text-[#00D95F] transition-colors"
          >
            Regístrate ahora
          </Link>
        </p>
      </motion.div>
    </div>
  )
}

