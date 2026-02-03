import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/contexts/AuthContext'
import { userService } from '@/services/user.service'
import { User, CreditCard, Bell, Shield, ChevronRight } from 'lucide-react'

export function ProfilePage() {
  const { toast } = useToast()
  const { user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState('personal')
  const [isLoading, setIsLoading] = useState(false)

  // Helper function to construct avatar URL
  const getAvatarUrl = (avatarPath: string | null | undefined): string | null => {
    if (!avatarPath) return null
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const baseUrl = apiBaseUrl.replace(/\/api\/v1\/?$/, '')
    return `${baseUrl}${avatarPath}`
  }

  // Personal info state
  const [personalInfo, setPersonalInfo] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    birth_date: '',
  })

  // Password change state
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })

  // 2FA state
  const [twoFactorStatus, setTwoFactorStatus] = useState({
    is_setup: false,
    is_enabled: false,
  })
  const [twoFactorSetup, setTwoFactorSetup] = useState<{
    secret?: string
    qr_code_url?: string
    backup_codes?: string[]
    showBackupCodes?: boolean
  }>({})
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [twoFactorDisablePassword, setTwoFactorDisablePassword] = useState('')

  // Avatar state
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)

  useEffect(() => {
    const loadProfileData = async () => {
      try {
        const profileData = await userService.getCurrentUser()
        // Map date_of_birth from backend to birth_date for frontend
        const birthDate = profileData.date_of_birth
          ? new Date(profileData.date_of_birth).toISOString().split('T')[0]
          : ''

        setPersonalInfo({
          username: profileData.username || '',
          email: profileData.email || '',
          first_name: profileData.first_name || '',
          last_name: profileData.last_name || '',
          phone: profileData.phone || '',
          birth_date: birthDate,
        })

        // Load avatar - construct full URL
        setAvatarUrl(getAvatarUrl(profileData.avatar_url))

        // Load 2FA status
        try {
          const status = await userService.get2FAStatus()
          setTwoFactorStatus(status)
        } catch (error) {
          console.error('Error loading 2FA status:', error)
        }
      } catch (error) {
        console.error('Error loading profile data:', error)
        // Fallback to user data from context if available
        if (user) {
          setPersonalInfo({
            username: user.username || '',
            email: user.email || '',
            first_name: '',
            last_name: '',
            phone: '',
            birth_date: '',
          })
        }
      }
    }

    loadProfileData()
  }, [user])

  const handlePersonalInfoChange = (field: string, value: string) => {
    setPersonalInfo(prev => ({ ...prev, [field]: value }))
  }

  const handlePasswordChange = (field: string, value: string) => {
    setPasswordData(prev => ({ ...prev, [field]: value }))
  }

  const handleSavePersonalInfo = async () => {
    try {
      setIsLoading(true)
      const updateData = {
        ...personalInfo,
        birth_date: personalInfo.birth_date || undefined,
      }
      await userService.updateProfile(updateData)
      await refreshUser()
      const profileData = await userService.getCurrentUser()
      const birthDate = profileData.date_of_birth
        ? new Date(profileData.date_of_birth).toISOString().split('T')[0]
        : ''
      setPersonalInfo({
        username: profileData.username || '',
        email: profileData.email || '',
        first_name: profileData.first_name || '',
        last_name: profileData.last_name || '',
        phone: profileData.phone || '',
        birth_date: birthDate,
      })
      toast({
        title: 'IDENTITY UPDATED',
        description: 'Profile data synchronized successfully.',
      })
    } catch (error: any) {
      toast({
        title: 'UPDATE FAILED',
        description: error.message || 'Error updating profile',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast({
        title: 'MISMATCH',
        description: 'Passkeys do not match.',
        variant: 'destructive',
      })
      return
    }

    try {
      setIsLoading(true)
      await userService.changePassword(passwordData)
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })
      toast({
        title: 'SECURE UPDATE',
        description: 'Passkey changed successfully.',
      })
    } catch (error: any) {
      toast({
        title: 'ACCESS DENIED',
        description: error.message || 'Error changing passkey.',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSetup2FA = async () => {
    try {
      setIsLoading(true)
      const setupData = await userService.setup2FA()
      setTwoFactorSetup({
        secret: setupData.secret,
        qr_code_url: setupData.qr_code_url,
        backup_codes: setupData.backup_codes,
        showBackupCodes: true,
      })
      toast({
        title: '2FA INITIATED',
        description: 'Scan QR code to authorize device.',
      })
    } catch (error: any) {
      toast({
        title: 'SETUP FAILED',
        description: error.message,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleEnable2FA = async () => {
    if (!twoFactorCode) return
    try {
      setIsLoading(true)
      await userService.enable2FA(twoFactorCode)
      setTwoFactorStatus({ is_setup: true, is_enabled: true })
      setTwoFactorSetup({})
      setTwoFactorCode('')
      toast({
        title: 'PROTOCOL ACTIVE',
        description: '2FA protection enabled.',
      })
    } catch (error: any) {
      toast({
        title: 'VERIFICATION FAILED',
        description: error.message,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisable2FA = async () => {
    if (!twoFactorDisablePassword) return
    try {
      setIsLoading(true)
      await userService.disable2FA(twoFactorDisablePassword)
      setTwoFactorStatus({ is_setup: false, is_enabled: false })
      setTwoFactorDisablePassword('')
      toast({
        title: 'PROTOCOL DISABLED',
        description: '2FA protection removed.',
      })
    } catch (error: any) {
      toast({
        title: 'Action Failed',
        description: error.message,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      setIsLoading(true)
      const result = await userService.uploadAvatar(file)
      setAvatarUrl(getAvatarUrl(result.avatar_url))
      await refreshUser()
      toast({
        title: 'IMAGE UPLOADED',
        description: 'Avatar updated successfully.',
      })
    } catch (error: any) {
      toast({
        title: 'UPLOAD ERROR',
        description: error.message,
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
      event.target.value = ''
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-10">
      <div className="flex flex-col md:flex-row gap-8 items-start">
        {/* Sidebar / Identity Card */}
        <div className="w-full md:w-80 space-y-6">
          <Card className="bg-metal-900 border-white/10 overflow-hidden relative group">
            <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-acid-500 to-transparent" />
            <CardContent className="pt-8 flex flex-col items-center">
              <div className="relative mb-6">
                <Avatar className="w-32 h-32 border-2 border-white/10 group-hover:border-acid-500/50 transition-colors">
                  <AvatarImage src={avatarUrl || undefined} className="object-cover" />
                  <AvatarFallback className="bg-void text-2xl font-display font-bold text-muted-foreground">
                    {personalInfo.username?.[0]?.toUpperCase() || 'U'}
                  </AvatarFallback>
                </Avatar>
                <label htmlFor="avatar-upload" className="absolute bottom-0 right-0 p-2 bg-acid-500 text-black rounded-sm cursor-pointer hover:bg-white transition-colors">
                  <User size={16} />
                  <input id="avatar-upload" type="file" className="hidden" onChange={handleAvatarUpload} accept="image/*" />
                </label>
              </div>

              <h2 className="text-2xl font-display font-bold text-white mb-1">{personalInfo.username}</h2>
              <div className="flex items-center gap-2 mb-6">
                <span className="w-2 h-2 rounded-full bg-acid-500 animate-pulse" />
                <span className="text-xs font-mono text-acid-500 tracking-widest uppercase">Operative Active</span>
              </div>

              <div className="w-full space-y-2">
                <div className="flex justify-between text-xs font-mono border-b border-white/5 pb-2">
                  <span className="text-muted-foreground">ID</span>
                  <span className="text-white">#{user?.id?.toString().padStart(6, '0')}</span>
                </div>
                <div className="flex justify-between text-xs font-mono border-b border-white/5 pb-2">
                  <span className="text-muted-foreground">Joined</span>
                  <span className="text-white">2024-05-12</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <nav className="space-y-1">
            <TabButton active={activeTab === 'personal'} onClick={() => setActiveTab('personal')} icon={<User size={18} />} label="IDENTITY_MODULE" />
            <TabButton active={activeTab === 'security'} onClick={() => setActiveTab('security')} icon={<Shield size={18} />} label="SECURITY_PROTOCOL" />
            <TabButton active={activeTab === 'payment'} onClick={() => setActiveTab('payment')} icon={<CreditCard size={18} />} label="CREDITS_History" />
            <TabButton active={activeTab === 'preferences'} onClick={() => setActiveTab('preferences')} icon={<Bell size={18} />} label="SYSTEM_CONFIG" />
          </nav>
        </div>

        {/* Main Content Info */}
        <div className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            {activeTab === 'personal' && (
              <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} key="personal" className="space-y-6">
                <div className="mb-6">
                  <h3 className="text-xl font-display font-bold text-white mb-1">IDENTITY MODULE</h3>
                  <p className="text-sm font-mono text-muted-foreground">Manage personal identification data.</p>
                </div>

                <Card className="bg-metal-900/50 border-white/10">
                  <CardContent className="pt-6 space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <InputGroup label="First Name" value={personalInfo.first_name} onChange={(v) => handlePersonalInfoChange('first_name', v)} />
                      <InputGroup label="Last Name" value={personalInfo.last_name} onChange={(v) => handlePersonalInfoChange('last_name', v)} />
                      <InputGroup label="Username" value={personalInfo.username} onChange={(v) => handlePersonalInfoChange('username', v)} />
                      <InputGroup label="Email Contact" value={personalInfo.email} onChange={(v) => handlePersonalInfoChange('email', v)} type="email" />
                      <InputGroup label="Comm Link (Phone)" value={personalInfo.phone} onChange={(v) => handlePersonalInfoChange('phone', v)} type="tel" />
                      <InputGroup label="Inception Date" value={personalInfo.birth_date} onChange={(v) => handlePersonalInfoChange('birth_date', v)} type="date" />
                    </div>
                    <div className="flex justify-end pt-4 border-t border-white/5">
                      <Button onClick={handleSavePersonalInfo} disabled={isLoading} className="bg-acid-500 text-black hover:bg-white font-mono font-bold">
                        {isLoading ? 'SYNCING...' : 'SAVE_CHANGES'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {activeTab === 'security' && (
              <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} key="security" className="space-y-6">
                <div className="mb-6">
                  <h3 className="text-xl font-display font-bold text-white mb-1">SECURITY PROTOCOL</h3>
                  <p className="text-sm font-mono text-muted-foreground">Manage access credentials and 2FA.</p>
                </div>

                {/* Password Change */}
                <Card className="bg-metal-900/50 border-white/10">
                  <CardHeader><CardTitle className="text-sm font-mono text-white uppercase">Update Passkey</CardTitle></CardHeader>
                  <CardContent className="space-y-4">
                    <InputGroup label="Current Passkey" type="password" value={passwordData.current_password} onChange={(v) => handlePasswordChange('current_password', v)} />
                    <div className="grid grid-cols-2 gap-4">
                      <InputGroup label="New Passkey" type="password" value={passwordData.new_password} onChange={(v) => handlePasswordChange('new_password', v)} />
                      <InputGroup label="Confirm Passkey" type="password" value={passwordData.confirm_password} onChange={(v) => handlePasswordChange('confirm_password', v)} />
                    </div>
                    <Button onClick={handleChangePassword} disabled={isLoading} className="w-full bg-white/5 text-white hover:bg-white/10 border border-white/10 font-mono">
                      UPDATE CREDENTIALS
                    </Button>
                  </CardContent>
                </Card>

                {/* 2FA Section */}
                <Card className="bg-metal-900/50 border-white/10 relative overflow-hidden">
                  <div className={`absolute top-0 right-0 p-2 px-3 font-mono text-xs font-bold ${twoFactorStatus.is_enabled ? 'bg-acid-500 text-black' : 'bg-red-500 text-white'}`}>
                    {twoFactorStatus.is_enabled ? 'SECURE' : 'VULNERABLE'}
                  </div>
                  <CardHeader><CardTitle className="text-sm font-mono text-white uppercase">Two-Factor Authentication</CardTitle></CardHeader>
                  <CardContent className="space-y-6">
                    {!twoFactorStatus.is_enabled ? (
                      <>
                        <p className="text-sm text-muted-foreground">Enhance account security by enabling 2FA protocol.</p>
                        {!twoFactorSetup.qr_code_url ? (
                          <Button onClick={handleSetup2FA} disabled={isLoading} variant="outline" className="border-acid-500 text-acid-500 hover:bg-acid-500/10 w-full font-mono">
                            INITIALIZE 2FA SETUP
                          </Button>
                        ) : (
                          <div className="space-y-4 bg-black/30 p-4 rounded border border-white/10">
                            <div className="flex justify-center bg-white p-2 rounded w-fit mx-auto">
                              <img src={twoFactorSetup.qr_code_url} alt="QR" className="w-40 h-40" />
                            </div>
                            <div>
                              <Label className="text-xs uppercase text-muted-foreground mb-1 block">Verification Code</Label>
                              <div className="flex gap-2">
                                <Input
                                  value={twoFactorCode}
                                  onChange={(e) => setTwoFactorCode(e.target.value)}
                                  placeholder="000 000"
                                  className="font-mono text-center tracking-widest text-lg"
                                  maxLength={6}
                                />
                                <Button onClick={handleEnable2FA} className="bg-acid-500 text-black font-bold">ACTIVATE</Button>
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="space-y-4">
                        <div className="flex items-center gap-3 text-acid-500 bg-acid-500/5 p-3 rounded border border-acid-500/20">
                          <Shield size={20} />
                          <span className="font-mono font-bold">PROTOCOL ACTIVE</span>
                        </div>
                        <Separator className="bg-white/5" />
                        <div>
                          <Label className="text-xs uppercase text-muted-foreground mb-1 block">Password to Disable</Label>
                          <div className="flex gap-2">
                            <Input type="password" value={twoFactorDisablePassword} onChange={(e) => setTwoFactorDisablePassword(e.target.value)} className="bg-black/50" />
                            <Button onClick={handleDisable2FA} variant="destructive" className="font-mono">DISABLE</Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-mono uppercase tracking-wide transition-all border-l-2 ${active
        ? 'bg-acid-500/10 text-acid-500 border-acid-500'
        : 'text-muted-foreground border-transparent hover:bg-white/5 hover:text-white'
        }`}
    >
      {icon}
      {label}
      {active && <ChevronRight size={14} className="ml-auto" />}
    </button>
  )
}

function InputGroup({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-black/40 border-white/10 focus:border-acid-500 text-white font-mono h-10"
      />
    </div>
  )
}
