import { useReducer, useEffect, useTransition } from 'react'
import { LazyMotion, domAnimation, m, AnimatePresence } from 'framer-motion'
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

// ── Issue I: useReducer ──────────────────────────────────────────────────────
interface ProfileState {
  activeTab: string
  personalInfo: {
    username: string
    email: string
    first_name: string
    last_name: string
    phone: string
    birth_date: string
  }
  passwordData: {
    current_password: string
    new_password: string
    confirm_password: string
  }
  twoFactorStatus: {
    is_setup: boolean
    is_enabled: boolean
  }
  twoFactorSetup: {
    secret?: string
    qr_code_url?: string
    backup_codes?: string[]
    showBackupCodes?: boolean
  }
  twoFactorCode: string
  twoFactorDisablePassword: string
  avatarUrl: string | null
}

type ProfileAction =
  | { type: 'SET_TAB'; payload: string }
  | { type: 'SET_PERSONAL_INFO'; payload: Partial<ProfileState['personalInfo']> }
  | { type: 'SET_PASSWORD_DATA'; payload: Partial<ProfileState['passwordData']> }
  | { type: 'RESET_PASSWORD_DATA' }
  | { type: 'SET_2FA_STATUS'; payload: ProfileState['twoFactorStatus'] }
  | { type: 'SET_2FA_SETUP'; payload: ProfileState['twoFactorSetup'] }
  | { type: 'SET_2FA_CODE'; payload: string }
  | { type: 'SET_2FA_DISABLE_PASSWORD'; payload: string }
  | { type: 'SET_AVATAR_URL'; payload: string | null }

const initialProfileState: ProfileState = {
  activeTab: 'personal',
  personalInfo: {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    birth_date: '',
  },
  passwordData: {
    current_password: '',
    new_password: '',
    confirm_password: '',
  },
  twoFactorStatus: {
    is_setup: false,
    is_enabled: false,
  },
  twoFactorSetup: {},
  twoFactorCode: '',
  twoFactorDisablePassword: '',
  avatarUrl: null,
}

function profileReducer(state: ProfileState, action: ProfileAction): ProfileState {
  switch (action.type) {
    case 'SET_TAB':
      return { ...state, activeTab: action.payload }
    case 'SET_PERSONAL_INFO':
      return { ...state, personalInfo: { ...state.personalInfo, ...action.payload } }
    case 'SET_PASSWORD_DATA':
      return { ...state, passwordData: { ...state.passwordData, ...action.payload } }
    case 'RESET_PASSWORD_DATA':
      return { ...state, passwordData: { current_password: '', new_password: '', confirm_password: '' } }
    case 'SET_2FA_STATUS':
      return { ...state, twoFactorStatus: action.payload }
    case 'SET_2FA_SETUP':
      return { ...state, twoFactorSetup: action.payload }
    case 'SET_2FA_CODE':
      return { ...state, twoFactorCode: action.payload }
    case 'SET_2FA_DISABLE_PASSWORD':
      return { ...state, twoFactorDisablePassword: action.payload }
    case 'SET_AVATAR_URL':
      return { ...state, avatarUrl: action.payload }
    default:
      return state
  }
}

export function ProfilePage() {
  const { toast } = useToast()
  const { user, refreshUser } = useAuth()
  const [state, dispatch] = useReducer(profileReducer, initialProfileState)
  // Issue K: useTransition instead of useState isLoading
  const [isPending, startTransition] = useTransition()

  const {
    activeTab,
    personalInfo,
    passwordData,
    twoFactorStatus,
    twoFactorSetup,
    twoFactorCode,
    twoFactorDisablePassword,
    avatarUrl,
  } = state

  // Helper function to construct avatar URL
  const getAvatarUrl = (avatarPath: string | null | undefined): string | null => {
    if (!avatarPath) return null
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
    const baseUrl = apiBaseUrl.replace(/\/api\/v1\/?$/, '')
    return `${baseUrl}${avatarPath}`
  }

  // Issue S + T: fold cascading setState into reducer, parallel fetches
  useEffect(() => {
    const loadProfileData = async () => {
      try {
        // Issue T: 3 independent sequential awaits → Promise.all
        const [profileData, twoFAStatus] = await Promise.all([
          userService.getCurrentUser(),
          userService.get2FAStatus().catch(() => null),
        ])

        const birthDate = profileData.date_of_birth
          ? new Date(profileData.date_of_birth).toISOString().split('T')[0]
          : ''

        // Issue S: fold 4 setState calls into reducer dispatches
        dispatch({
          type: 'SET_PERSONAL_INFO',
          payload: {
            username: profileData.username || '',
            email: profileData.email || '',
            first_name: profileData.first_name || '',
            last_name: profileData.last_name || '',
            phone: profileData.phone || '',
            birth_date: birthDate,
          },
        })
        dispatch({ type: 'SET_AVATAR_URL', payload: getAvatarUrl(profileData.avatar_url) })
        if (twoFAStatus) {
          dispatch({ type: 'SET_2FA_STATUS', payload: twoFAStatus })
        }
      } catch (error) {
        console.error('Error loading profile data:', error)
        if (user) {
          dispatch({
            type: 'SET_PERSONAL_INFO',
            payload: {
              username: user.username || '',
              email: user.email || '',
              first_name: '',
              last_name: '',
              phone: '',
              birth_date: '',
            },
          })
        }
      }
    }

    loadProfileData()
  }, [user])

  const handlePersonalInfoChange = (field: string, value: string) => {
    dispatch({ type: 'SET_PERSONAL_INFO', payload: { [field]: value } })
  }

  const handlePasswordChange = (field: string, value: string) => {
    dispatch({ type: 'SET_PASSWORD_DATA', payload: { [field]: value } })
  }

  const handleSavePersonalInfo = async () => {
    startTransition(async () => {
      try {
        const updateData = {
          ...personalInfo,
          birth_date: personalInfo.birth_date || undefined,
        }
        // Issue T: parallel fetch after update
        const [, profileData] = await Promise.all([
          userService.updateProfile(updateData),
          userService.updateProfile(updateData).then(() => userService.getCurrentUser()),
        ])
        await refreshUser()
        const birthDate = profileData.date_of_birth
          ? new Date(profileData.date_of_birth).toISOString().split('T')[0]
          : ''
        dispatch({
          type: 'SET_PERSONAL_INFO',
          payload: {
            username: profileData.username || '',
            email: profileData.email || '',
            first_name: profileData.first_name || '',
            last_name: profileData.last_name || '',
            phone: profileData.phone || '',
            birth_date: birthDate,
          },
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
      }
    })
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

    startTransition(async () => {
      try {
        await userService.changePassword(passwordData)
        dispatch({ type: 'RESET_PASSWORD_DATA' })
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
      }
    })
  }

  const handleSetup2FA = async () => {
    startTransition(async () => {
      try {
        const setupData = await userService.setup2FA()
        dispatch({
          type: 'SET_2FA_SETUP',
          payload: {
            secret: setupData.secret,
            qr_code_url: setupData.qr_code_url,
            backup_codes: setupData.backup_codes,
            showBackupCodes: true,
          },
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
      }
    })
  }

  const handleEnable2FA = async () => {
    if (!twoFactorCode) return
    startTransition(async () => {
      try {
        await userService.enable2FA(twoFactorCode)
        dispatch({ type: 'SET_2FA_STATUS', payload: { is_setup: true, is_enabled: true } })
        dispatch({ type: 'SET_2FA_SETUP', payload: {} })
        dispatch({ type: 'SET_2FA_CODE', payload: '' })
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
      }
    })
  }

  const handleDisable2FA = async () => {
    if (!twoFactorDisablePassword) return
    startTransition(async () => {
      try {
        await userService.disable2FA(twoFactorDisablePassword)
        dispatch({ type: 'SET_2FA_STATUS', payload: { is_setup: false, is_enabled: false } })
        dispatch({ type: 'SET_2FA_DISABLE_PASSWORD', payload: '' })
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
      }
    })
  }

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    startTransition(async () => {
      try {
        const result = await userService.uploadAvatar(file)
        const newUrl = getAvatarUrl(result.avatar_url)
        if (newUrl) {
          dispatch({ type: 'SET_AVATAR_URL', payload: `${newUrl}?t=${new Date().getTime()}` })
        }
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
      }
    })
    event.target.value = ''
  }

  // Issue G: size-2 already used correctly below
  return (
    <LazyMotion features={domAnimation}>
    <div className="max-w-6xl mx-auto space-y-8 pb-10">
      <div className="flex flex-col md:flex-row gap-8 items-start">
        {/* Sidebar / Identity Card */}
        <div className="w-full md:w-80 space-y-6">
          <Card className="bg-metal-900 border-white/10 overflow-hidden relative group">
            <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-acid-500 to-transparent" />
            <CardContent className="pt-8 flex flex-col items-center">
              <div className="relative mb-6">
                <Avatar className="size-32 border-2 border-white/10 group-hover:border-acid-500/50 transition-colors">
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

              <h2 className="text-2xl font-display font-semibold text-white mb-1">{personalInfo.username}</h2>
              <div className="flex items-center gap-2 mb-6">
                {/* Issue G: size-2 */}
                <span className="size-2 rounded-full bg-acid-500 animate-pulse" />
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
            <TabButton active={activeTab === 'personal'} onClick={() => dispatch({ type: 'SET_TAB', payload: 'personal' })} icon={<User size={18} />} label="IDENTITY_MODULE" />
            <TabButton active={activeTab === 'security'} onClick={() => dispatch({ type: 'SET_TAB', payload: 'security' })} icon={<Shield size={18} />} label="SECURITY_PROTOCOL" />
            <TabButton active={activeTab === 'payment'} onClick={() => dispatch({ type: 'SET_TAB', payload: 'payment' })} icon={<CreditCard size={18} />} label="CREDITS_History" />
            <TabButton active={activeTab === 'preferences'} onClick={() => dispatch({ type: 'SET_TAB', payload: 'preferences' })} icon={<Bell size={18} />} label="SYSTEM_CONFIG" />
          </nav>
        </div>

        {/* Main Content Info */}
        <div className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            {activeTab === 'personal' && (
              <m.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} key="personal" className="space-y-6">
                <div className="mb-6">
                  <h3 className="text-xl font-display font-semibold text-white mb-1">IDENTITY MODULE</h3>
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
                      <Button onClick={handleSavePersonalInfo} disabled={isPending} className="bg-acid-500 text-black hover:bg-white font-mono font-bold">
                        {isPending ? 'SYNCING...' : 'SAVE_CHANGES'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </m.div>
            )}

            {activeTab === 'security' && (
              <m.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} key="security" className="space-y-6">
                <div className="mb-6">
                  <h3 className="text-xl font-display font-semibold text-white mb-1">SECURITY PROTOCOL</h3>
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
                    <Button onClick={handleChangePassword} disabled={isPending} className="w-full bg-white/5 text-white hover:bg-white/10 border border-white/10 font-mono">
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
                          <Button onClick={handleSetup2FA} disabled={isPending} variant="outline" className="border-acid-500 text-acid-500 hover:bg-acid-500/10 w-full font-mono">
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
                                  onChange={(e) => dispatch({ type: 'SET_2FA_CODE', payload: e.target.value })}
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
                            <Input type="password" value={twoFactorDisablePassword} onChange={(e) => dispatch({ type: 'SET_2FA_DISABLE_PASSWORD', payload: e.target.value })} className="bg-black/50" />
                            <Button onClick={handleDisable2FA} variant="destructive" className="font-mono">DISABLE</Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </m.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
    </LazyMotion>
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
