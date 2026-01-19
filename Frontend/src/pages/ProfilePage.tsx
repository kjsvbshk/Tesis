import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useToast } from '@/hooks/use-toast'
import { useAuth } from '@/contexts/AuthContext'
import { userService } from '@/services/user.service'
import { User, CreditCard, Bell, Shield, LogOut } from 'lucide-react'

export function ProfilePage() {
  const { toast } = useToast()
  const { logout, user, refreshUser } = useAuth()
  const [activeTab, setActiveTab] = useState('personal')
  const [isLoading, setIsLoading] = useState(false)
  
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
  const [avatarUploading, setAvatarUploading] = useState(false)

  // Sessions state
  const [sessions, setSessions] = useState<any[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)

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

        // Load avatar
        if (profileData.avatar_url) {
          const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
          setAvatarUrl(`${apiBaseUrl.replace('/api/v1', '')}${profileData.avatar_url}`)
        }

        // Load 2FA status
        try {
          const status = await userService.get2FAStatus()
          setTwoFactorStatus(status)
        } catch (error) {
          console.error('Error loading 2FA status:', error)
        }

        // Load sessions
        loadSessions()
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

  const loadSessions = async () => {
    try {
      setSessionsLoading(true)
      const sessionsData = await userService.getSessions()
      setSessions(sessionsData)
    } catch (error) {
      console.error('Error loading sessions:', error)
    } finally {
      setSessionsLoading(false)
    }
  }

  const handlePersonalInfoChange = (field: string, value: string) => {
    setPersonalInfo(prev => ({ ...prev, [field]: value }))
  }

  const handlePasswordChange = (field: string, value: string) => {
    setPasswordData(prev => ({ ...prev, [field]: value }))
  }

  const handleSavePersonalInfo = async () => {
    try {
      setIsLoading(true)
      // Map birth_date to date_of_birth for backend (though backend accepts both)
      const updateData = {
        ...personalInfo,
        birth_date: personalInfo.birth_date || undefined,
      }
      await userService.updateProfile(updateData)
      await refreshUser()
      // Reload profile data to get updated values
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
        title: 'Perfil actualizado',
        description: 'Tu información personal ha sido actualizada exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al actualizar el perfil',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePassword = async () => {
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast({
        title: 'Error',
        description: 'Las contraseñas no coinciden',
        variant: 'destructive',
      })
      return
    }

    if (passwordData.new_password.length < 6) {
      toast({
        title: 'Error',
        description: 'La nueva contraseña debe tener al menos 6 caracteres',
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
        title: 'Contraseña actualizada',
        description: 'Tu contraseña ha sido cambiada exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cambiar la contraseña. Verifica que la contraseña actual sea correcta.',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = (section: string) => {
    toast({
      title: 'Configuración guardada',
      description: `Los cambios en ${section} han sido guardados exitosamente.`,
    })
  }

  // 2FA handlers
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
        title: '2FA configurado',
        description: 'Escanea el código QR con tu aplicación de autenticación.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al configurar 2FA',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleEnable2FA = async () => {
    if (!twoFactorCode) {
      toast({
        title: 'Error',
        description: 'Por favor ingresa el código de verificación',
        variant: 'destructive',
      })
      return
    }

    try {
      setIsLoading(true)
      await userService.enable2FA(twoFactorCode)
      setTwoFactorStatus({ is_setup: true, is_enabled: true })
      setTwoFactorSetup({})
      setTwoFactorCode('')
      toast({
        title: '2FA activado',
        description: 'La autenticación de dos factores ha sido activada exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al activar 2FA',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisable2FA = async () => {
    if (!twoFactorDisablePassword) {
      toast({
        title: 'Error',
        description: 'Por favor ingresa tu contraseña',
        variant: 'destructive',
      })
      return
    }

    try {
      setIsLoading(true)
      await userService.disable2FA(twoFactorDisablePassword)
      setTwoFactorStatus({ is_setup: false, is_enabled: false })
      setTwoFactorDisablePassword('')
      toast({
        title: '2FA desactivado',
        description: 'La autenticación de dos factores ha sido desactivada.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al desactivar 2FA',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Avatar handlers
  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      toast({
        title: 'Error',
        description: 'Tipo de archivo no válido. Solo se permiten imágenes (JPG, PNG, GIF, WEBP)',
        variant: 'destructive',
      })
      return
    }

    // Validate file size (2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast({
        title: 'Error',
        description: 'El archivo es demasiado grande. Máximo 2MB',
        variant: 'destructive',
      })
      return
    }

    try {
      setAvatarUploading(true)
      const result = await userService.uploadAvatar(file)
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
      setAvatarUrl(`${apiBaseUrl.replace('/api/v1', '')}${result.avatar_url}`)
      await refreshUser()
      toast({
        title: 'Avatar actualizado',
        description: 'Tu foto de perfil ha sido actualizada exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al subir el avatar',
        variant: 'destructive',
      })
    } finally {
      setAvatarUploading(false)
      // Reset input
      event.target.value = ''
    }
  }

  const handleDeleteAvatar = async () => {
    try {
      setIsLoading(true)
      await userService.deleteAvatar()
      setAvatarUrl(null)
      await refreshUser()
      toast({
        title: 'Avatar eliminado',
        description: 'Tu foto de perfil ha sido eliminada.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al eliminar el avatar',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Session handlers
  const handleRevokeSession = async (sessionId: number) => {
    try {
      setIsLoading(true)
      await userService.revokeSession(sessionId)
      await loadSessions()
      toast({
        title: 'Sesión cerrada',
        description: 'La sesión ha sido cerrada exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cerrar la sesión',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleRevokeAllSessions = async () => {
    try {
      setIsLoading(true)
      await userService.revokeAllSessions()
      await loadSessions()
      toast({
        title: 'Sesiones cerradas',
        description: 'Todas las sesiones han sido cerradas exitosamente.',
      })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cerrar las sesiones',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-heading font-bold bg-gradient-to-r from-[#00FF73] via-[#00D95F] to-[#FFD700] bg-clip-text text-transparent mb-3 drop-shadow-[0_0_15px_rgba(0,255,115,0.5)]">
          👤 Mi Perfil
        </h1>
        <p className="text-[#B0B3C5] text-lg font-medium">Gestiona tu cuenta y configuraciones</p>
      </motion.div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-4 w-full">
          <TabsTrigger value="personal" className="flex items-center gap-2">
            <User size={16} />
            Personal
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-2">
            <Shield size={16} />
            Seguridad
          </TabsTrigger>
          <TabsTrigger value="payment" className="flex items-center gap-2">
            <CreditCard size={16} />
            Pagos
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <Bell size={16} />
            Preferencias
          </TabsTrigger>
        </TabsList>

        <TabsContent value="personal" className="space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <User size={20} className="text-[#00FF73]" />
                  Información Personal
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4 mb-6">
                  <Avatar className="w-20 h-20">
                    <AvatarImage src={avatarUrl || undefined} />
                    <AvatarFallback className="text-2xl">
                      {personalInfo.first_name?.[0] || personalInfo.username?.[0] || 'U'}
                      {personalInfo.last_name?.[0] || ''}
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <label htmlFor="avatar-upload">
                        <Button 
                          variant="outline" 
                          size="sm" 
                          asChild
                          disabled={avatarUploading}
                        >
                          <span>{avatarUploading ? 'Subiendo...' : 'Cambiar Foto'}</span>
                        </Button>
                        <input
                          id="avatar-upload"
                          type="file"
                          accept="image/jpeg,image/jpg,image/png,image/gif,image/webp"
                          onChange={handleAvatarUpload}
                          className="hidden"
                        />
                      </label>
                      {avatarUrl && (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={handleDeleteAvatar}
                          disabled={isLoading}
                        >
                          Eliminar
                        </Button>
                      )}
                    </div>
                    <p className="text-sm text-[#B0B3C5]">JPG, PNG, GIF, WEBP hasta 2MB</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">Nombre</Label>
                    <Input 
                      id="firstName" 
                      value={personalInfo.first_name}
                      onChange={(e) => handlePersonalInfoChange('first_name', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Apellido</Label>
                    <Input 
                      id="lastName" 
                      value={personalInfo.last_name}
                      onChange={(e) => handlePersonalInfoChange('last_name', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Nombre de Usuario</Label>
                    <Input 
                      id="username" 
                      value={personalInfo.username}
                      onChange={(e) => handlePersonalInfoChange('username', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input 
                      id="email" 
                      type="email" 
                      value={personalInfo.email}
                      onChange={(e) => handlePersonalInfoChange('email', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Teléfono</Label>
                    <Input 
                      id="phone" 
                      type="tel" 
                      value={personalInfo.phone}
                      onChange={(e) => handlePersonalInfoChange('phone', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="birthDate">Fecha de Nacimiento</Label>
                    <Input 
                      id="birthDate" 
                      type="date" 
                      value={personalInfo.birth_date}
                      onChange={(e) => handlePersonalInfoChange('birth_date', e.target.value)}
                      className="bg-[#0B132B] border-[#1C2541] text-white"
                    />
                  </div>
                </div>

                <Separator />
                <Button 
                  onClick={handleSavePersonalInfo} 
                  disabled={isLoading}
                  className="w-full"
                >
                  {isLoading ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <Shield size={20} className="text-[#00FF73]" />
                  Seguridad y Contraseña
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Cambiar Contraseña</h3>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="currentPassword">Contraseña Actual</Label>
                      <Input 
                        id="currentPassword" 
                        type="password" 
                        value={passwordData.current_password}
                        onChange={(e) => handlePasswordChange('current_password', e.target.value)}
                        className="bg-[#0B132B] border-[#1C2541] text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="newPassword">Nueva Contraseña</Label>
                      <Input 
                        id="newPassword" 
                        type="password" 
                        value={passwordData.new_password}
                        onChange={(e) => handlePasswordChange('new_password', e.target.value)}
                        className="bg-[#0B132B] border-[#1C2541] text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword">Confirmar Nueva Contraseña</Label>
                      <Input 
                        id="confirmPassword" 
                        type="password" 
                        value={passwordData.confirm_password}
                        onChange={(e) => handlePasswordChange('confirm_password', e.target.value)}
                        className="bg-[#0B132B] border-[#1C2541] text-white"
                      />
                    </div>
                  </div>
                  <Button 
                    onClick={handleChangePassword} 
                    disabled={isLoading || !passwordData.current_password || !passwordData.new_password || !passwordData.confirm_password}
                    className="w-full"
                  >
                    {isLoading ? 'Cambiando...' : 'Cambiar Contraseña'}
                  </Button>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Autenticación de Dos Factores</h3>
                  
                  {twoFactorStatus.is_enabled ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                        <div>
                          <p className="font-medium text-white">2FA Activado</p>
                          <p className="text-sm text-[#B0B3C5]">Protección adicional para tu cuenta</p>
                        </div>
                        <Badge variant="default" className="bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]/30">
                          Activo
                        </Badge>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="disable2FAPassword">Contraseña para desactivar</Label>
                        <Input
                          id="disable2FAPassword"
                          type="password"
                          value={twoFactorDisablePassword}
                          onChange={(e) => setTwoFactorDisablePassword(e.target.value)}
                          placeholder="Ingresa tu contraseña"
                          className="bg-[#0B132B] border-[#1C2541] text-white"
                        />
                        <Button 
                          variant="destructive" 
                          className="w-full"
                          onClick={handleDisable2FA}
                          disabled={isLoading || !twoFactorDisablePassword}
                        >
                          Desactivar 2FA
                        </Button>
                      </div>
                    </div>
                  ) : twoFactorSetup.qr_code_url ? (
                    <div className="space-y-4">
                      <div className="text-center">
                        <p className="text-sm text-[#B0B3C5] mb-4">
                          Escanea este código QR con tu aplicación de autenticación (Google Authenticator, Authy, etc.)
                        </p>
                        <div className="flex justify-center mb-4">
                          <img 
                            src={twoFactorSetup.qr_code_url} 
                            alt="QR Code" 
                            className="border border-[#1C2541] rounded-lg p-2 bg-white"
                          />
                        </div>
                        {twoFactorSetup.showBackupCodes && twoFactorSetup.backup_codes && (
                          <div className="mb-4 p-4 border border-yellow-500/30 rounded-lg bg-yellow-500/5">
                            <p className="text-sm font-medium text-yellow-400 mb-2">
                              ⚠️ Guarda estos códigos de respaldo en un lugar seguro:
                            </p>
                            <div className="grid grid-cols-2 gap-2">
                              {twoFactorSetup.backup_codes.map((code, idx) => (
                                <code key={idx} className="text-xs bg-[#0B132B] p-2 rounded text-yellow-300">
                                  {code}
                                </code>
                              ))}
                            </div>
                            <p className="text-xs text-[#B0B3C5] mt-2">
                              Estos códigos solo se mostrarán una vez. Úsalos si pierdes acceso a tu dispositivo.
                            </p>
                          </div>
                        )}
                        <div className="space-y-2">
                          <Label htmlFor="2faCode">Código de verificación</Label>
                          <Input
                            id="2faCode"
                            type="text"
                            value={twoFactorCode}
                            onChange={(e) => setTwoFactorCode(e.target.value)}
                            placeholder="000000"
                            maxLength={6}
                            className="bg-[#0B132B] border-[#1C2541] text-white text-center text-2xl tracking-widest"
                          />
                          <Button 
                            className="w-full"
                            onClick={handleEnable2FA}
                            disabled={isLoading || twoFactorCode.length !== 6}
                          >
                            Activar 2FA
                          </Button>
                          <Button 
                            variant="outline" 
                            className="w-full"
                            onClick={() => setTwoFactorSetup({})}
                          >
                            Cancelar
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                        <div>
                          <p className="font-medium text-white">2FA No Activado</p>
                          <p className="text-sm text-[#B0B3C5]">Protege tu cuenta con autenticación de dos factores</p>
                        </div>
                        <Badge variant="outline" className="border-[#FF4C4C]/30 text-[#FF4C4C]">
                          Inactivo
                        </Badge>
                      </div>
                      <Button 
                        variant="outline" 
                        className="w-full"
                        onClick={handleSetup2FA}
                        disabled={isLoading}
                      >
                        Configurar 2FA
                      </Button>
                    </div>
                  )}
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Cerrar Sesión</h3>
                  <div className="p-4 border border-[#FF4C4C]/30 rounded-lg bg-[#FF4C4C]/5">
                    <p className="text-sm text-[#B0B3C5] mb-4">
                      Al cerrar sesión, se desconectarán todas tus sesiones activas y deberás iniciar sesión nuevamente para acceder a tu cuenta.
                    </p>
                    <Button 
                      variant="destructive" 
                      className="w-full"
                      onClick={async () => {
                        try {
                          await logout()
                          toast({
                            title: 'Sesión cerrada',
                            description: 'Has cerrado sesión exitosamente.',
                          })
                        } catch (error) {
                          toast({
                            title: 'Error',
                            description: 'Hubo un problema al cerrar sesión.',
                            variant: 'destructive',
                          })
                        }
                      }}
                    >
                      <LogOut size={18} className="mr-2" />
                      Cerrar Sesión
                    </Button>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-heading font-semibold text-white">Sesiones Activas</h3>
                    {sessions.length > 1 && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={handleRevokeAllSessions}
                        disabled={isLoading}
                      >
                        Cerrar Todas
                      </Button>
                    )}
                  </div>
                  {sessionsLoading ? (
                    <p className="text-sm text-[#B0B3C5]">Cargando sesiones...</p>
                  ) : sessions.length === 0 ? (
                    <p className="text-sm text-[#B0B3C5]">No hay sesiones activas</p>
                  ) : (
                    <div className="space-y-2">
                      {sessions.map((session) => (
                        <div 
                          key={session.id} 
                          className="flex items-center justify-between p-3 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]"
                        >
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-white">
                                {session.device_info || 'Dispositivo desconocido'}
                                {session.is_current && (
                                  <Badge variant="default" className="ml-2 bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]/30 text-xs">
                                    Actual
                                  </Badge>
                                )}
                              </p>
                            </div>
                            <p className="text-sm text-[#B0B3C5]">
                              {session.location || session.ip_address || 'Ubicación desconocida'} • {
                                new Date(session.last_activity).toLocaleDateString('es-ES', {
                                  day: 'numeric',
                                  month: 'short',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })
                              }
                            </p>
                          </div>
                          {!session.is_current && (
                            <Button 
                              variant="destructive" 
                              size="sm"
                              onClick={() => handleRevokeSession(session.id)}
                              disabled={isLoading}
                            >
                              Cerrar Sesión
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="payment" className="space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <CreditCard size={20} className="text-[#00FF73]" />
                  Métodos de Pago
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Tarjetas Guardadas</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-4 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-blue-600 rounded flex items-center justify-center text-white text-xs font-bold">
                          V
                        </div>
                        <div>
                          <p className="font-medium text-white">**** **** **** 1234</p>
                          <p className="text-sm text-[#B0B3C5]">Visa • Expira 12/25</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm">Eliminar</Button>
                    </div>
                    <div className="flex items-center justify-between p-4 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-red-600 rounded flex items-center justify-center text-white text-xs font-bold">
                          M
                        </div>
                        <div>
                          <p className="font-medium text-white">**** **** **** 5678</p>
                          <p className="text-sm text-[#B0B3C5]">Mastercard • Expira 08/26</p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm">Eliminar</Button>
                    </div>
                  </div>
                  <Button className="w-full">Agregar Nueva Tarjeta</Button>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Límites de Apuesta</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="dailyLimit">Límite Diario</Label>
                      <Input id="dailyLimit" type="number" defaultValue="1000" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="weeklyLimit">Límite Semanal</Label>
                      <Input id="weeklyLimit" type="number" defaultValue="5000" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="monthlyLimit">Límite Mensual</Label>
                      <Input id="monthlyLimit" type="number" defaultValue="20000" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="depositLimit">Límite de Depósito</Label>
                      <Input id="depositLimit" type="number" defaultValue="10000" />
                    </div>
                  </div>
                  <Button onClick={() => handleSave('límites')} className="w-full">
                    Actualizar Límites
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="preferences" className="space-y-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-white font-heading">
                  <Bell size={20} className="text-[#00FF73]" />
                  Preferencias y Notificaciones
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Notificaciones por Email</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">Resultados de Apuestas</p>
                        <p className="text-sm text-[#B0B3C5]">Recibe notificaciones cuando tus apuestas se resuelvan</p>
                      </div>
                      <Button variant="outline" size="sm">Activar</Button>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">Promociones y Ofertas</p>
                        <p className="text-sm text-[#B0B3C5]">Ofertas especiales y bonificaciones</p>
                      </div>
                      <Button variant="outline" size="sm">Activar</Button>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">Recordatorios de Depósito</p>
                        <p className="text-sm text-[#B0B3C5]">Notificaciones sobre tu saldo</p>
                      </div>
                      <Button variant="outline" size="sm">Activar</Button>
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Preferencias de Apuesta</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="defaultStake">Apuesta por Defecto</Label>
                      <Input id="defaultStake" type="number" defaultValue="50" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="currency">Moneda</Label>
                      <Input id="currency" defaultValue="EUR" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="timezone">Zona Horaria</Label>
                      <Input id="timezone" defaultValue="Europe/Madrid" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="language">Idioma</Label>
                      <Input id="language" defaultValue="Español" />
                    </div>
                  </div>
                  <Button onClick={() => handleSave('preferencias')} className="w-full">
                    Guardar Preferencias
                  </Button>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Privacidad</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">Perfil Público</p>
                        <p className="text-sm text-[#B0B3C5]">Permitir que otros usuarios vean tu perfil</p>
                      </div>
                      <Button variant="outline" size="sm">Desactivar</Button>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">Estadísticas Públicas</p>
                        <p className="text-sm text-[#B0B3C5]">Mostrar tus estadísticas de apuestas</p>
                      </div>
                      <Button variant="outline" size="sm">Desactivar</Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

