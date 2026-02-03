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
  const [errors, setErrors] = useState<{ [key: string]: string | undefined }>({})

  useEffect(() => {
    if (verified && parsedData) {
      sessionStorage.removeItem('registrationData')
    }
  }, [verified, parsedData])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData({ ...formData, [name]: value })
    if (errors[name]) setErrors({ ...errors, [name]: undefined })
  }

  const validateForm = () => {
    const newErrors: typeof errors = {}
    if (!formData.username.trim()) newErrors.username = 'ID Required'
    if (!formData.email.trim()) newErrors.email = 'Email Contact Required'
    if (!formData.password) newErrors.password = 'Secure Passkey Required'
    if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passkeys Do Not Match'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSendCode = async () => {
    setIsLoading(true)
    try {
      await authService.sendVerificationCode(formData.email.trim(), 'registration')
      sessionStorage.setItem('registrationData', JSON.stringify({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      }))
      toast({ title: 'SIGNAL SENT', description: 'Verification code transmitted to endpoint.' })
      setStep('verify')
      navigate('/verify-email', { state: { email: formData.email.trim(), purpose: 'registration' } })
    } catch (error: any) {
      toast({ title: 'TRANSMISSION ERROR', description: error.message, variant: 'destructive' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (step === 'form') {
      if (!validateForm()) return
      await handleSendCode()
      return
    }

    if (!formData.verificationCode || formData.verificationCode.length !== 6) {
      setErrors({ ...errors, verificationCode: 'Invalid Length' })
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
      toast({ title: 'ENTITY REGISTERED', description: 'Welcome to the network.' })
      setTimeout(() => navigate('/login'), 1500)
    } catch (error: any) {
      toast({ title: 'REGISTRATION FAILED', description: error.message, variant: 'destructive' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-void font-sans">
      {/* Visual Side */}
      <div className="hidden lg:flex w-1/2 bg-metal-900 flex-col justify-between p-12 relative overflow-hidden border-r border-border">
        <div className="scanlines absolute inset-0 opacity-10" />
        <div className="z-10">
          <h1 className="text-4xl font-display font-bold text-white mb-2">NEW<br /><span className="text-acid-500">ENTITY</span></h1>
          <div className="h-1 w-20 bg-acid-500" />
        </div>
        <div className="z-10 font-mono text-muted-foreground text-sm">
          :: INITIALIZE PROTOCOL<br />
          :: AWAITING CREDENTIALS
        </div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] border-2 border-dashed border-acid-500/20 rounded-full animate-spin-slow" />
      </div>

      {/* Form Side */}
      <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-20 xl:px-24 bg-void relative">
        <div className="absolute top-0 right-0 p-8">
          <Link to="/" className="text-muted-foreground hover:text-acid-500 font-mono text-xs transition-colors">
            ← ABORT
          </Link>
        </div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="mx-auto w-full max-w-sm lg:w-96"
        >
          <h2 className="text-2xl font-display font-bold tracking-tight text-white mb-8 border-b border-border pb-4">
            {step === 'register' ? 'VERIFY IDENTITY' : 'CREATE PROFILE'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {step === 'form' && (
              <>
                <div>
                  <Label className="text-muted-foreground font-mono text-xs uppercase mb-1 block">Username ID</Label>
                  <Input name="username" value={formData.username} onChange={handleChange} className={errors.username ? "border-red-500" : ""} placeholder="USER_ID" />
                </div>
                <div>
                  <Label className="text-muted-foreground font-mono text-xs uppercase mb-1 block">Email Contact</Label>
                  <Input name="email" value={formData.email} onChange={handleChange} className={errors.email ? "border-red-500" : ""} placeholder="CONTACT@DOMAIN" />
                </div>
                <div>
                  <Label className="text-muted-foreground font-mono text-xs uppercase mb-1 block">Passkey</Label>
                  <Input type="password" name="password" value={formData.password} onChange={handleChange} className={errors.password ? "border-red-500" : ""} placeholder="******" />
                </div>
                <div>
                  <Label className="text-muted-foreground font-mono text-xs uppercase mb-1 block">Confirm Passkey</Label>
                  <Input type="password" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} className={errors.confirmPassword ? "border-red-500" : ""} placeholder="******" />
                </div>
              </>
            )}

            {step === 'register' && (
              <div>
                <Label className="text-acid-500 font-mono text-xs uppercase mb-2 block animate-pulse">Verification Code</Label>
                <Input
                  name="verificationCode"
                  value={formData.verificationCode}
                  onChange={handleChange}
                  className="text-center tracking-[0.5em] font-display text-xl border-acid-500"
                  maxLength={6}
                  placeholder="000000"
                />
                <p className="text-xs text-muted-foreground mt-2 text-center">Code sent to {formData.email}</p>
              </div>
            )}

            <Button type="submit" className="w-full mt-6" disabled={isLoading}>
              {isLoading ? "PROCESSING..." : step === 'register' ? "COMPLETE REGISTRATION" : "INITIATE"}
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-border text-center">
            <p className="text-sm text-muted-foreground">
              Already registered?{' '}
              <Link to="/login" className="font-bold text-acid-500 hover:text-white transition-colors">
                ACCESS TERMINAL
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
