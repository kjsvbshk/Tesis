import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { authService } from '@/services/auth.service'

export function RegisterPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const { email: verifiedEmail, verified } = location.state || {}
  
  // Recuperar datos del formulario si existen
  const savedData = sessionStorage.getItem('registrationData')
  const parsedData = savedData ? JSON.parse(savedData) : null
  
  const [formData, setFormData] = useState({
    username: parsedData?.username || '',
    email: verifiedEmail || parsedData?.email || '',
    password: parsedData?.password || '',
    confirmPassword: '',
    verificationCode: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [step, setStep] = useState<'form' | 'verify' | 'register'>(verified ? 'register' : 'form')
  const [errors, setErrors] = useState<{
    username?: string
    email?: string
    password?: string
    confirmPassword?: string
    verificationCode?: string
  }>({})

  // Limpiar datos guardados si se completó el registro
  useEffect(() => {
    if (verified && parsedData) {
      sessionStorage.removeItem('registrationData')
    }
  }, [verified, parsedData])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData({
      ...formData,
      [name]: value,
    })
    // Clear error when user starts typing
    if (errors[name as keyof typeof errors]) {
      setErrors({ ...errors, [name]: undefined })
    }
  }

  const validateForm = () => {
    const newErrors: typeof errors = {}
    
    if (!formData.username.trim()) {
      newErrors.username = 'El nombre de usuario es requerido'
    } else if (formData.username.trim().length < 3) {
      newErrors.username = 'El nombre de usuario debe tener al menos 3 caracteres'
    } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username.trim())) {
      newErrors.username = 'El nombre de usuario solo puede contener letras, números y guiones bajos'
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'El correo electrónico es requerido'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      newErrors.email = 'El correo electrónico no es válido'
    }
    
    if (!formData.password) {
      newErrors.password = 'La contraseña es requerida'
    } else if (formData.password.length < 6) {
      newErrors.password = 'La contraseña debe tener al menos 6 caracteres'
    }
    
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Por favor confirma tu contraseña'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Las contraseñas no coinciden'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSendCode = async () => {
    if (!formData.email.trim()) {
      setErrors({ ...errors, email: 'El correo electrónico es requerido' })
      return
    }
    
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      setErrors({ ...errors, email: 'El correo electrónico no es válido' })
      return
    }

    setIsLoading(true)
    try {
      await authService.sendVerificationCode(formData.email.trim(), 'registration')
      
      // Guardar datos del formulario en sessionStorage para recuperarlos después
      sessionStorage.setItem('registrationData', JSON.stringify({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      }))
      
      toast({
        title: 'Código enviado',
        description: 'Se ha enviado un código de verificación a tu correo',
      })
      setStep('verify')
      navigate('/verify-email', { state: { email: formData.email.trim(), purpose: 'registration' } })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al enviar el código',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (step === 'form') {
      if (!validateForm()) {
        return
      }
      // Send verification code
      await handleSendCode()
      return
    }
    
    // Step: register (after verification)
    if (!formData.verificationCode || formData.verificationCode.length !== 6) {
      setErrors({ ...errors, verificationCode: 'El código de verificación es requerido' })
      return
    }

    setIsLoading(true)
    try {
      await authService.registerWithVerification({
        username: formData.username.trim(),
        email: formData.email.trim(),
        password: formData.password,
        verification_code: formData.verificationCode,
      })
      
      toast({
        title: '¡Cuenta creada!',
        description: 'Te has registrado correctamente',
      })
      
      // Redirect to login
      setTimeout(() => {
        navigate('/login')
      }, 1500)
    } catch (error: any) {
      const errorMessage = error.message || 'Error al crear la cuenta'
      let displayMessage = errorMessage
      
      if (errorMessage.includes('Username already registered')) {
        displayMessage = 'El nombre de usuario ya está registrado'
      } else if (errorMessage.includes('Email already registered')) {
        displayMessage = 'El correo electrónico ya está registrado'
      } else if (errorMessage.includes('verification')) {
        displayMessage = 'Por favor verifica tu correo electrónico primero'
        setStep('verify')
        navigate('/verify-email', { state: { email: formData.email.trim(), purpose: 'registration' } })
      }
      
      toast({
        title: 'Error',
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
          {step === 'register' ? 'Completa tu registro' : 'Crea tu cuenta'}
        </h2>
        <p className="mt-2 text-center text-sm text-[#B0B3C5]">
          {step === 'register' 
            ? 'Ingresa el código de verificación y completa tu registro'
            : 'O '}
          {step !== 'register' && (
            <Link
              to="/login"
              className="font-semibold text-[#00FF73] hover:text-[#00D95F] transition-colors"
            >
              inicia sesión si ya tienes una cuenta
            </Link>
          )}
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
                value={formData.username}
                onChange={handleChange}
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
            <Label htmlFor="email" className="block text-sm font-medium text-white">
              Correo electrónico
            </Label>
            <div className="mt-2">
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleChange}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  errors.email ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="tu@email.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{errors.email}</p>
              )}
            </div>
          </div>

          <div>
            <Label htmlFor="password" className="block text-sm font-medium text-white">
              Contraseña
            </Label>
            <div className="mt-2">
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={handleChange}
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

          <div>
            <Label htmlFor="confirmPassword" className="block text-sm font-medium text-white">
              Confirmar contraseña
            </Label>
            <div className="mt-2">
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  errors.confirmPassword ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="••••••••"
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{errors.confirmPassword}</p>
              )}
            </div>
          </div>

          {step === 'register' && (
            <div>
              <Label htmlFor="verificationCode" className="block text-sm font-medium text-white">
                Código de verificación
              </Label>
              <div className="mt-2">
                <Input
                  id="verificationCode"
                  name="verificationCode"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  required
                  value={formData.verificationCode}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 6)
                    setFormData({ ...formData, verificationCode: value })
                    if (errors.verificationCode) {
                      setErrors({ ...errors, verificationCode: undefined })
                    }
                  }}
                  className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white text-center text-2xl tracking-widest font-mono outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                    errors.verificationCode ? 'border-[#FF4C4C]' : ''
                  }`}
                  placeholder="000000"
                />
                {errors.verificationCode && (
                  <p className="mt-1 text-sm text-[#FF4C4C]">{errors.verificationCode}</p>
                )}
                <p className="mt-2 text-xs text-[#B0B3C5] text-center">
                  Ingresa el código de 6 dígitos enviado a {formData.email}
                </p>
              </div>
            </div>
          )}

          <div>
            <Button
              type="submit"
              disabled={isLoading || (step === 'register' && formData.verificationCode.length !== 6)}
              className="flex w-full justify-center rounded-lg bg-gradient-to-r from-[#00FF73] to-[#00D95F] px-3 py-2.5 text-sm font-semibold text-[#0B132B] hover:from-[#00D95F] hover:to-[#00FF73] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00FF73] transition-all duration-300 shadow-[0_0_20px_rgba(0,255,115,0.3)] hover:shadow-[0_0_25px_rgba(0,255,115,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading 
                ? (step === 'register' ? 'Creando cuenta...' : 'Enviando código...')
                : (step === 'register' ? 'Crear cuenta' : 'Enviar código de verificación')}
            </Button>
          </div>
        </form>

        <p className="mt-10 text-center text-sm text-[#B0B3C5]">
          ¿Ya tienes una cuenta?{' '}
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

