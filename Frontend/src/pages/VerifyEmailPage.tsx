import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { authService } from '@/services/auth.service'

export function VerifyEmailPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const { email, username, purpose = 'registration' } = location.state || {}
  
  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // Redirect if no email/username provided based on purpose
  useEffect(() => {
    if (purpose === 'password_reset' && !username) {
      navigate('/recuperar-contraseña')
    } else if (purpose === 'registration' && !email) {
      navigate('/registro')
    }
  }, [email, username, purpose, navigate])

  if ((purpose === 'password_reset' && !username) || (purpose === 'registration' && !email)) {
    return null
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!code || code.length !== 6) {
      setError('Por favor ingresa el código de 6 dígitos')
      return
    }

    setIsLoading(true)
    setError('')
    
    try {
      let response
      // For password reset, use username. For registration, use email
      if (purpose === 'password_reset' && username) {
        response = await authService.verifyCode('', code, purpose as 'registration' | 'password_reset', username)
      } else if (email) {
        response = await authService.verifyCode(email, code, purpose as 'registration' | 'password_reset')
      } else {
        throw new Error('Email or username is required')
      }
      
      const verifiedEmail = response.email || email
      
      // Redirect based on purpose
      if (purpose === 'password_reset') {
        navigate('/reset-password', { state: { username, code } })
      } else {
        // For registration: verify code and then complete registration automatically
        // Get saved registration data from sessionStorage
        const savedData = sessionStorage.getItem('registrationData')
        if (!savedData) {
          throw new Error('No se encontraron datos de registro. Por favor, regístrate nuevamente.')
        }
        
        const parsedData = JSON.parse(savedData)
        
        // Complete registration with verified code
        await authService.registerWithVerification({
          username: parsedData.username,
          email: verifiedEmail || parsedData.email,
          password: parsedData.password,
          verification_code: code,
        })
        
        // Clear saved data
        sessionStorage.removeItem('registrationData')
        
        toast({
          title: '¡Cuenta creada!',
          description: 'Te has registrado correctamente',
        })
        
        // Redirect to login after a brief delay
        setTimeout(() => {
          navigate('/login')
        }, 1500)
      }
    } catch (error: any) {
      const errorMessage = error.message || 'Código inválido o expirado'
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

  const handleResendCode = async () => {
    setIsLoading(true)
    try {
      if (purpose === 'password_reset' && username) {
        // For password reset, resend using username
        await authService.forgotPassword(username)
      } else if (email) {
        // For registration, use email
        await authService.sendVerificationCode(email, purpose as 'registration' | 'password_reset')
      }
      toast({
        title: 'Código reenviado',
        description: 'Se ha enviado un nuevo código a tu correo',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al reenviar el código',
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
          Verifica tu correo
        </h2>
        <p className="mt-2 text-center text-sm text-[#B0B3C5]">
          Hemos enviado un código de verificación
          {purpose === 'password_reset' && username 
            ? ` al correo asociado a tu cuenta`
            : email 
            ? ` a`
            : ''}
        </p>
        {email && (
          <p className="mt-1 text-center text-sm font-medium text-[#00FF73]">
            {email}
          </p>
        )}
        {purpose === 'password_reset' && username && !email && (
          <p className="mt-1 text-center text-sm font-medium text-[#00FF73]">
            Usuario: {username}
          </p>
        )}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm"
      >
        <form onSubmit={handleVerify} className="space-y-6">
          <div>
            <Label htmlFor="code" className="block text-sm font-medium text-white">
              Código de verificación
            </Label>
            <div className="mt-2">
              <Input
                id="code"
                name="code"
                type="text"
                inputMode="numeric"
                maxLength={6}
                required
                value={code}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 6)
                  setCode(value)
                  setError('')
                }}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white text-center text-2xl tracking-widest font-mono outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  error ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="000000"
              />
              {error && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{error}</p>
              )}
            </div>
          </div>

          <div>
            <Button
              type="submit"
              disabled={isLoading || code.length !== 6}
              className="flex w-full justify-center rounded-lg bg-gradient-to-r from-[#00FF73] to-[#00D95F] px-3 py-2.5 text-sm font-semibold text-[#0B132B] hover:from-[#00D95F] hover:to-[#00FF73] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00FF73] transition-all duration-300 shadow-[0_0_20px_rgba(0,255,115,0.3)] hover:shadow-[0_0_25px_rgba(0,255,115,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Verificando...' : 'Verificar código'}
            </Button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={handleResendCode}
              disabled={isLoading}
              className="text-sm text-[#00FF73] hover:text-[#00D95F] transition-colors disabled:opacity-50"
            >
              ¿No recibiste el código? Reenviar
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
