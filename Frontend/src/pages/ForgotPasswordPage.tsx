import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { authService } from '@/services/auth.service'

export function ForgotPasswordPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [userEmail, setUserEmail] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!username.trim()) {
      setError('El nombre de usuario es requerido')
      return
    }
    
    if (username.trim().length < 3) {
      setError('El nombre de usuario debe tener al menos 3 caracteres')
      return
    }

    setIsLoading(true)
    setError('')
    
    try {
      const response = await authService.forgotPassword(username.trim())
      setCodeSent(true)
      
      // Guardar email si viene en la respuesta (solo en desarrollo)
      if (response.email) {
        setUserEmail(response.email)
      }
      
      toast({
        title: 'Código enviado',
        description: 'Si el usuario existe, se ha enviado un código de verificación al correo asociado',
      })
      
      // Navigate to verification page with username and email (if available)
      setTimeout(() => {
        navigate('/verify-email', { 
          state: { 
            username: username.trim(),
            email: response.email || null,
            purpose: 'password_reset' 
          } 
        })
      }, 1000)
    } catch (error: any) {
      const errorMessage = error.message || 'Error al enviar el código'
      setError(errorMessage)
      toast({
        title: 'Error',
        description: errorMessage,
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
          Recuperar contraseña
        </h2>
        <p className="mt-2 text-center text-sm text-[#B0B3C5]">
          Ingresa tu nombre de usuario y te enviaremos un código de verificación al correo asociado
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm"
      >
        {codeSent ? (
          <div className="text-center space-y-4">
            <div className="text-[#00FF73] text-lg font-medium">
              ✓ Código enviado
            </div>
            <p className="text-[#B0B3C5]">
              Redirigiendo a la página de verificación...
            </p>
          </div>
        ) : (
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
                    setError('')
                  }}
                  className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                    error ? 'border-[#FF4C4C]' : ''
                  }`}
                  placeholder="usuario123"
                />
                {error && (
                  <p className="mt-1 text-sm text-[#FF4C4C]">{error}</p>
                )}
                {userEmail && (
                  <p className="mt-2 text-xs text-[#B0B3C5]">
                    Código enviado a: {userEmail}
                  </p>
                )}
              </div>
            </div>

            <div>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex w-full justify-center rounded-lg bg-gradient-to-r from-[#00FF73] to-[#00D95F] px-3 py-2.5 text-sm font-semibold text-[#0B132B] hover:from-[#00D95F] hover:to-[#00FF73] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00FF73] transition-all duration-300 shadow-[0_0_20px_rgba(0,255,115,0.3)] hover:shadow-[0_0_25px_rgba(0,255,115,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Enviando...' : 'Enviar código'}
              </Button>
            </div>
          </form>
        )}

        <p className="mt-10 text-center text-sm text-[#B0B3C5]">
          ¿Recordaste tu contraseña?{' '}
          <Link
            to="/login"
            className="font-semibold text-[#00FF73] hover:text-[#00D95F] transition-colors"
          >
            Inicia sesión
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
