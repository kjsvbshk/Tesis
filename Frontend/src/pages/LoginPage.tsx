import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'
import { motion } from 'framer-motion'
import { useAuth } from '@/contexts/AuthContext'
import { Label } from '@/components/ui/label'

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
    if (!username.trim()) newErrors.username = 'ID Required'
    if (!password) newErrors.password = 'Passkey Required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return
    if (requires2FA && (!twoFactorCode || twoFactorCode.length !== 6)) {
      setErrors({ ...errors, twoFactorCode: 'Invalid Protocol' })
      return
    }

    setIsLoading(true)
    try {
      await login(username.trim(), password, requires2FA ? twoFactorCode : undefined)
    } catch (error: any) {
      if (error?.requires2FA || error?.message?.includes('2FA')) {
        setRequires2FA(true)
        setErrors({})
        toast({ title: 'SECURE PROTOCOL', description: '2FA Verification Required' })
        setIsLoading(false)
        return
      }
      toast({
        title: 'ACCESS DENIED',
        description: 'Invalid credentials provided.',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-void font-sans">
      {/* Visual Side */}
      <div className="hidden lg:flex w-1/2 bg-metal-900 flex-col justify-between p-12 relative overflow-hidden border-r border-border">
        <div className="scanlines absolute inset-0 opacity-10" />

        {/* Animated circles — centered */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] border border-acid-500/10 rounded-full animate-pulse-glow" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[540px] h-[540px] border border-acid-500/15 rounded-full animate-pulse-glow" style={{ animationDelay: '0.5s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[380px] h-[380px] border border-acid-500/20 rotate-45" />

        {/* Text content — centered over circles */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 text-center w-72">
          <h1 className="text-8xl font-display font-black text-white leading-none mb-3">HAW</h1>
          <p className="text-xl font-display font-bold text-white mb-2">House Always Wins</p>
          <p className="text-muted-foreground text-xs leading-relaxed mb-6">
            Únete a la comunidad de predicciones NBA
          </p>
          <div className="space-y-2">
            {[
              'Registro gratuito',
              '1,000 créditos de inicio',
              'Sin dinero real',
            ].map((item) => (
              <div key={item} className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                <span className="text-acid-500 font-bold">✓</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom version tag */}
        <div className="z-10 mt-auto font-mono text-muted-foreground/40 text-xs">
          v2.0.4
        </div>
      </div>

      {/* Form Side */}
      <div className="flex-1 flex flex-col justify-center px-4 sm:px-6 lg:px-20 xl:px-24 bg-void relative">
        <div className="absolute top-0 right-0 p-8">
          <Link to="/" className="text-muted-foreground hover:text-acid-500 font-mono text-xs transition-colors">
            ← BACK TO ROOT
          </Link>
        </div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto w-full max-w-sm lg:w-96"
        >
          <h2 className="text-2xl font-display font-bold tracking-tight text-white mb-8 border-b border-border pb-4">
            AUTHENTICATE
          </h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <Label className="text-muted-foreground font-mono text-xs uppercase mb-2 block">Username</Label>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={errors.username ? "border-red-500" : ""}
                placeholder="USER_ID"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <Label className="text-muted-foreground font-mono text-xs uppercase block">Passkey</Label>
                <Link to="/recuperar-contraseña" className="text-xs text-acid-500 hover:text-white font-mono">
                  FORGOT?
                </Link>
              </div>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={errors.password ? "border-red-500" : ""}
                placeholder="******"
              />
            </div>

            {requires2FA && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
                <Label className="text-acid-500 font-mono text-xs uppercase mb-2 block animate-pulse">2FA Verification Code</Label>
                <Input
                  inputMode="numeric"
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  className="text-center tracking-[0.5em] font-display text-xl border-acid-500"
                  placeholder="000000"
                />
              </motion.div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "PROCESSING..." : "ESTABLISH CONNECTION"}
            </Button>
          </form>

          <div className="mt-8 pt-6 border-t border-border text-center">
            <p className="text-sm text-muted-foreground">
              Fresh Unit?{' '}
              <Link to="/registro" className="font-bold text-acid-500 hover:text-white transition-colors">
                REGISTER NEW ID
              </Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
