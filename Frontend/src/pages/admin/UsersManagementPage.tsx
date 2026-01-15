/**
 * Users Management Page
 * CRUD completo de usuarios para administradores
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Edit, Trash2, Shield, Search, X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { usersService, type User, type UserCreate, type UserUpdate } from '@/services/users.service'
import { adminService, type Role, type UserRole } from '@/services/admin.service'
import { useToast } from '@/hooks/use-toast'

export function UsersManagementPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isRolesOpen, setIsRolesOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [userRoles, setUserRoles] = useState<UserRole[]>([])
  const [allRoles, setAllRoles] = useState<Role[]>([])
  const [loadingRoles, setLoadingRoles] = useState(false)
  const { toast } = useToast()

  // Form states
  const [createForm, setCreateForm] = useState<UserCreate>({
    username: '',
    email: '',
    password: '',
  })
  const [editForm, setEditForm] = useState<UserUpdate>({
    username: '',
    email: '',
    credits: 0,
    is_active: true,
  })

  useEffect(() => {
    loadUsers()
    loadAllRoles()
  }, [])

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await usersService.getAllUsers(100, 0)
      setUsers(data)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar usuarios',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadAllRoles = async () => {
    try {
      const roles = await adminService.getRoles()
      setAllRoles(roles)
    } catch (error: any) {
      console.error('Error loading roles:', error)
    }
  }

  const loadUserRoles = async (userId: number) => {
    try {
      setLoadingRoles(true)
      const roles = await adminService.getUserRoles(userId)
      setUserRoles(roles)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar roles del usuario',
        variant: 'destructive',
      })
    } finally {
      setLoadingRoles(false)
    }
  }

  const handleCreateUser = async () => {
    if (!createForm.username || !createForm.email || !createForm.password) {
      toast({
        title: 'Error',
        description: 'Todos los campos son requeridos',
        variant: 'destructive',
      })
      return
    }

    try {
      await usersService.createUser(createForm)
      toast({
        title: 'Éxito',
        description: 'Usuario creado correctamente',
      })
      setIsCreateOpen(false)
      setCreateForm({ username: '', email: '', password: '' })
      loadUsers()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al crear usuario',
        variant: 'destructive',
      })
    }
  }

  const handleEditUser = async () => {
    if (!selectedUser) return

    try {
      await usersService.updateUser(selectedUser.id, editForm)
      toast({
        title: 'Éxito',
        description: 'Usuario actualizado correctamente',
      })
      setIsEditOpen(false)
      setSelectedUser(null)
      loadUsers()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al actualizar usuario',
        variant: 'destructive',
      })
    }
  }

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('¿Estás seguro de eliminar este usuario?')) return

    try {
      await usersService.deleteUser(userId)
      toast({
        title: 'Éxito',
        description: 'Usuario eliminado correctamente',
      })
      loadUsers()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al eliminar usuario',
        variant: 'destructive',
      })
    }
  }

  const handleOpenEdit = (user: User) => {
    setSelectedUser(user)
    setEditForm({
      username: user.username,
      email: user.email,
      credits: user.credits ?? 0,
      is_active: user.is_active,
    })
    setIsEditOpen(true)
  }

  const handleOpenRoles = async (user: User) => {
    setSelectedUser(user)
    setIsRolesOpen(true)
    await loadUserRoles(user.id)
  }

  const handleAssignRole = async (roleId: number) => {
    if (!selectedUser) return

    try {
      await adminService.assignRoleToUser(selectedUser.id, roleId)
      toast({
        title: 'Éxito',
        description: 'Rol asignado correctamente',
      })
      await loadUserRoles(selectedUser.id)
      loadUsers() // Refresh to update role display
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al asignar rol',
        variant: 'destructive',
      })
    }
  }

  const handleRemoveRole = async (roleId: number) => {
    if (!selectedUser) return

    try {
      await adminService.removeRoleFromUser(selectedUser.id, roleId)
      toast({
        title: 'Éxito',
        description: 'Rol removido correctamente',
      })
      await loadUserRoles(selectedUser.id)
      loadUsers() // Refresh to update role display
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al remover rol',
        variant: 'destructive',
      })
    }
  }

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const availableRoles = allRoles.filter(
    (role) => !userRoles.some((ur) => ur.role_id === role.id)
  )

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent">
            Gestión de Usuarios
          </h1>
          <p className="text-[#B0B3C5] mt-2">Administra usuarios, roles y permisos del sistema</p>
        </div>
        <Button 
          className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
          onClick={() => setIsCreateOpen(true)}
        >
          <Plus size={20} className="mr-2" />
          Nuevo Usuario
        </Button>
      </motion.div>

      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Usuarios del Sistema</CardTitle>
              <CardDescription className="text-[#B0B3C5]">
                Total: {filteredUsers.length} usuarios
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#B0B3C5] size-4" />
                <Input
                  placeholder="Buscar usuarios..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-[#0B132B] border-[#1C2541] text-white w-64"
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-[#B0B3C5]">Cargando usuarios...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-[#B0B3C5]">ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Usuario</TableHead>
                  <TableHead className="text-[#B0B3C5]">Email</TableHead>
                  <TableHead className="text-[#B0B3C5]">Rol</TableHead>
                  <TableHead className="text-[#B0B3C5]">Créditos</TableHead>
                  <TableHead className="text-[#B0B3C5]">Estado</TableHead>
                  <TableHead className="text-[#B0B3C5]">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id} className="border-[#1C2541] hover:bg-[#1C2541]/30">
                    <TableCell className="text-white">{user.id}</TableCell>
                    <TableCell className="text-white font-medium">{user.username}</TableCell>
                    <TableCell className="text-[#B0B3C5]">{user.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-[#00FF73] text-[#00FF73]">
                        {user.rol}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-white">
                      {user.credits !== null && user.credits !== undefined 
                        ? `$${user.credits.toFixed(2)}` 
                        : 'N/A'}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={user.is_active ? 'default' : 'destructive'}
                        className={user.is_active ? 'bg-[#00FF73] text-black' : ''}
                      >
                        {user.is_active ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[#00FF73] hover:text-[#00D95F] hover:bg-[#1C2541]"
                          onClick={() => handleOpenEdit(user)}
                        >
                          <Edit size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[#00FF73] hover:text-[#00D95F] hover:bg-[#1C2541]"
                          onClick={() => handleOpenRoles(user)}
                        >
                          <Shield size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-400 hover:bg-[#1C2541]"
                          onClick={() => handleDeleteUser(user.id)}
                        >
                          <Trash2 size={16} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create User Sheet */}
      <Sheet open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Crear Nuevo Usuario</SheetTitle>
            <SheetDescription>
              Completa los datos para crear un nuevo usuario en el sistema
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-username">Nombre de Usuario</Label>
              <Input
                id="create-username"
                value={createForm.username}
                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="usuario123"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-email">Email</Label>
              <Input
                id="create-email"
                type="email"
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="usuario@ejemplo.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-password">Contraseña</Label>
              <Input
                id="create-password"
                type="password"
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="••••••••"
              />
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleCreateUser}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Crear Usuario
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Edit User Sheet */}
      <Sheet open={isEditOpen} onOpenChange={setIsEditOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Editar Usuario</SheetTitle>
            <SheetDescription>
              Modifica la información del usuario
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-username">Nombre de Usuario</Label>
              <Input
                id="edit-username"
                value={editForm.username}
                onChange={(e) => setEditForm({ ...editForm, username: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-email">Email</Label>
              <Input
                id="edit-email"
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-credits">Créditos</Label>
              <Input
                id="edit-credits"
                type="number"
                step="0.01"
                value={editForm.credits}
                onChange={(e) => setEditForm({ ...editForm, credits: parseFloat(e.target.value) || 0 })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="edit-active"
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                className="rounded border-[#1C2541] bg-[#0B132B] text-[#00FF73]"
              />
              <Label htmlFor="edit-active" className="cursor-pointer">
                Usuario Activo
              </Label>
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleEditUser}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Guardar Cambios
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Manage Roles Sheet */}
      <Sheet open={isRolesOpen} onOpenChange={setIsRolesOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Gestionar Roles de Usuario</SheetTitle>
            <SheetDescription>
              {selectedUser && `Roles asignados a ${selectedUser.username}`}
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            {loadingRoles ? (
              <div className="text-center py-8 text-[#B0B3C5]">Cargando roles...</div>
            ) : (
              <>
                <div>
                  <h3 className="text-white font-semibold mb-2">Roles Asignados</h3>
                  {userRoles.length === 0 ? (
                    <p className="text-[#B0B3C5] text-sm">No hay roles asignados</p>
                  ) : (
                    <div className="space-y-2">
                      {userRoles.map((userRole) => (
                        <div
                          key={userRole.id}
                          className="flex items-center justify-between p-3 bg-[#0B132B] border border-[#1C2541] rounded-lg"
                        >
                          <div>
                            <Badge variant="outline" className="border-[#00FF73] text-[#00FF73] mr-2">
                              {userRole.role?.code || 'N/A'}
                            </Badge>
                            <span className="text-white">{userRole.role?.name || 'Sin nombre'}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveRole(userRole.role_id)}
                            className="text-red-500 hover:text-red-400"
                          >
                            <X size={16} />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div>
                  <h3 className="text-white font-semibold mb-2">Roles Disponibles</h3>
                  {availableRoles.length === 0 ? (
                    <p className="text-[#B0B3C5] text-sm">Todos los roles están asignados</p>
                  ) : (
                    <div className="space-y-2">
                      {availableRoles.map((role) => (
                        <div
                          key={role.id}
                          className="flex items-center justify-between p-3 bg-[#0B132B] border border-[#1C2541] rounded-lg"
                        >
                          <div>
                            <Badge variant="outline" className="border-[#00FF73] text-[#00FF73] mr-2">
                              {role.code}
                            </Badge>
                            <span className="text-white">{role.name}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleAssignRole(role.id)}
                            className="text-[#00FF73] hover:text-[#00D95F]"
                          >
                            <Plus size={16} />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}

