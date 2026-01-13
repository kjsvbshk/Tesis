import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { authService } from '@/services/auth.service'

export function ResetPasswordPage() {
  const { toast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const { username, code } = location.state || {}
  
  const [formData, setFormData] = useState({
    newPassword: '',
    confirmPassword: '',
  })
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<{
    newPassword?: string
    confirmPassword?: string
  }>({})

  // Redirect if no username or code provided
  useEffect(() => {
    if (!username || !code) {
      navigate('/recuperar-contraseña')
    }
  }, [username, code, navigate])

  if (!username || !code) {
    return null
  }

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
    
    if (!formData.newPassword) {
      newErrors.newPassword = 'La nueva contraseña es requerida'
    } else if (formData.newPassword.length < 6) {
      newErrors.newPassword = 'La contraseña debe tener al menos 6 caracteres'
    }
    
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Por favor confirma tu nueva contraseña'
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Las contraseñas no coinciden'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    try {
      await authService.resetPassword(username, code, formData.newPassword)
      
      toast({
        title: 'Contraseña restablecida',
        description: 'Tu contraseña ha sido cambiada exitosamente',
      })
      
      // Redirect to login after a short delay
      setTimeout(() => {
        navigate('/login')
      }, 1500)
    } catch (error: any) {
      const errorMessage = error.message || 'Error al restablecer la contraseña'
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
          Nueva contraseña
        </h2>
        <p className="mt-2 text-center text-sm text-[#B0B3C5]">
          Ingresa tu nueva contraseña
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
            <Label htmlFor="newPassword" className="block text-sm font-medium text-white">
              Nueva contraseña
            </Label>
            <div className="mt-2">
              <Input
                id="newPassword"
                name="newPassword"
                type="password"
                autoComplete="new-password"
                required
                value={formData.newPassword}
                onChange={handleChange}
                className={`block w-full rounded-lg bg-white/5 px-3 py-2.5 text-base text-white outline-1 -outline-offset-1 outline-white/10 placeholder:text-[#B0B3C5] focus:outline-2 focus:-outline-offset-2 focus:outline-[#00FF73] sm:text-sm/6 ${
                  errors.newPassword ? 'border-[#FF4C4C]' : ''
                }`}
                placeholder="••••••••"
              />
              {errors.newPassword && (
                <p className="mt-1 text-sm text-[#FF4C4C]">{errors.newPassword}</p>
              )}
            </div>
          </div>

          <div>
            <Label htmlFor="confirmPassword" className="block text-sm font-medium text-white">
              Confirmar nueva contraseña
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

          <div>
            <Button
              type="submit"
              disabled={isLoading}
              className="flex w-full justify-center rounded-lg bg-gradient-to-r from-[#00FF73] to-[#00D95F] px-3 py-2.5 text-sm font-semibold text-[#0B132B] hover:from-[#00D95F] hover:to-[#00FF73] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#00FF73] transition-all duration-300 shadow-[0_0_20px_rgba(0,255,115,0.3)] hover:shadow-[0_0_25px_rgba(0,255,115,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Restableciendo...' : 'Restablecer contraseña'}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
