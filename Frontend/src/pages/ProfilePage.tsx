import { useState } from 'react'
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
import { User, Lock, Mail, Phone, MapPin, CreditCard, Bell, Shield, Palette, LogOut } from 'lucide-react'

export function ProfilePage() {
  const { toast } = useToast()
  const { logout } = useAuth()
  const [activeTab, setActiveTab] = useState('personal')

  const handleSave = (section: string) => {
    toast({
      title: 'Configuración guardada',
      description: `Los cambios en ${section} han sido guardados exitosamente.`,
    })
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
                    <AvatarImage src="/placeholder-avatar.jpg" />
                    <AvatarFallback className="text-2xl">JD</AvatarFallback>
                  </Avatar>
                  <div>
                    <Button variant="outline" size="sm">Cambiar Foto</Button>
                    <p className="text-sm text-[#B0B3C5] mt-1">JPG, PNG hasta 2MB</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">Nombre</Label>
                    <Input id="firstName" defaultValue="Juan" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Apellido</Label>
                    <Input id="lastName" defaultValue="Díaz" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Nombre de Usuario</Label>
                    <Input id="username" defaultValue="juan_diaz" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" defaultValue="juan@email.com" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Teléfono</Label>
                    <Input id="phone" type="tel" defaultValue="+34 600 123 456" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="birthDate">Fecha de Nacimiento</Label>
                    <Input id="birthDate" type="date" defaultValue="1990-05-15" />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address">Dirección</Label>
                  <Input id="address" defaultValue="Calle Mayor 123, Madrid" />
                </div>

                <Separator />
                <Button onClick={() => handleSave('información personal')} className="w-full">
                  Guardar Cambios
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
                      <Input id="currentPassword" type="password" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="newPassword">Nueva Contraseña</Label>
                      <Input id="newPassword" type="password" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword">Confirmar Nueva Contraseña</Label>
                      <Input id="confirmPassword" type="password" />
                    </div>
                  </div>
                  <Button onClick={() => handleSave('contraseña')} className="w-full">
                    Cambiar Contraseña
                  </Button>
                </div>

                <Separator />

                <div className="space-y-4">
                  <h3 className="text-lg font-heading font-semibold text-white">Autenticación de Dos Factores</h3>
                  <div className="flex items-center justify-between p-4 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                    <div>
                      <p className="font-medium text-white">2FA Activado</p>
                      <p className="text-sm text-[#B0B3C5]">Protección adicional para tu cuenta</p>
                    </div>
                    <Badge variant="default" className="bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]/30">
                      Activo
                    </Badge>
                  </div>
                  <Button variant="outline" className="w-full">
                    Configurar 2FA
                  </Button>
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
                  <h3 className="text-lg font-heading font-semibold text-white">Sesiones Activas</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                      <div>
                        <p className="font-medium text-white">Chrome - Windows</p>
                        <p className="text-sm text-[#B0B3C5]">Madrid, España • Ahora</p>
                      </div>
                      <Button variant="destructive" size="sm">Cerrar Sesión</Button>
                    </div>
                    <div className="flex items-center justify-between p-3 border border-[#1C2541]/50 rounded-lg bg-[#0B132B]">
                      <div>
                        <p className="font-medium text-white">Safari - iPhone</p>
                        <p className="text-sm text-[#B0B3C5]">Barcelona, España • Hace 2 horas</p>
                      </div>
                      <Button variant="destructive" size="sm">Cerrar Sesión</Button>
                    </div>
                  </div>
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

