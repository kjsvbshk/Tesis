/**
 * Roles Management Page
 * CRUD completo de roles y permisos para administradores
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Edit, Trash2, Shield, Key } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { adminService, type Role, type Permission } from '@/services/admin.service'
import { useToast } from '@/hooks/use-toast'
import { Loader } from '@/components/ui/loader'

export function RolesManagementPage() {
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('roles')
  const [isRoleCreateOpen, setIsRoleCreateOpen] = useState(false)
  const [isRoleEditOpen, setIsRoleEditOpen] = useState(false)
  const [isPermissionCreateOpen, setIsPermissionCreateOpen] = useState(false)
  const [isPermissionEditOpen, setIsPermissionEditOpen] = useState(false)
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  const [selectedPermission, setSelectedPermission] = useState<Permission | null>(null)
  const { toast } = useToast()

  // Form states
  const [roleForm, setRoleForm] = useState({ code: '', name: '', description: '' })
  const [permissionForm, setPermissionForm] = useState({ code: '', name: '', description: '', scope: '' })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [rolesData, permissionsData] = await Promise.all([
        adminService.getRoles(),
        adminService.getPermissions(),
      ])
      setRoles(rolesData)
      setPermissions(permissionsData)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar datos',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreateRole = async () => {
    if (!roleForm.code || !roleForm.name) {
      toast({
        title: 'Error',
        description: 'Código y nombre son requeridos',
        variant: 'destructive',
      })
      return
    }

    try {
      await adminService.createRole(roleForm)
      toast({
        title: 'Éxito',
        description: 'Rol creado correctamente',
      })
      setIsRoleCreateOpen(false)
      setRoleForm({ code: '', name: '', description: '' })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al crear rol',
        variant: 'destructive',
      })
    }
  }

  const handleEditRole = async () => {
    if (!selectedRole) return

    try {
      await adminService.updateRole(selectedRole.id, {
        name: roleForm.name,
        description: roleForm.description,
      })
      toast({
        title: 'Éxito',
        description: 'Rol actualizado correctamente',
      })
      setIsRoleEditOpen(false)
      setSelectedRole(null)
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al actualizar rol',
        variant: 'destructive',
      })
    }
  }

  const handleDeleteRole = async (roleId: number) => {
    if (!confirm('¿Estás seguro de eliminar este rol?')) return

    try {
      await adminService.deleteRole(roleId)
      toast({
        title: 'Éxito',
        description: 'Rol eliminado correctamente',
      })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al eliminar rol',
        variant: 'destructive',
      })
    }
  }

  const handleCreatePermission = async () => {
    if (!permissionForm.code || !permissionForm.name) {
      toast({
        title: 'Error',
        description: 'Código y nombre son requeridos',
        variant: 'destructive',
      })
      return
    }

    try {
      await adminService.createPermission(permissionForm)
      toast({
        title: 'Éxito',
        description: 'Permiso creado correctamente',
      })
      setIsPermissionCreateOpen(false)
      setPermissionForm({ code: '', name: '', description: '', scope: '' })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al crear permiso',
        variant: 'destructive',
      })
    }
  }

  const handleEditPermission = async () => {
    if (!selectedPermission) return

    try {
      await adminService.updatePermission(selectedPermission.id, {
        name: permissionForm.name,
        description: permissionForm.description,
        scope: permissionForm.scope || undefined,
      })
      toast({
        title: 'Éxito',
        description: 'Permiso actualizado correctamente',
      })
      setIsPermissionEditOpen(false)
      setSelectedPermission(null)
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al actualizar permiso',
        variant: 'destructive',
      })
    }
  }

  const handleDeletePermission = async (permissionId: number) => {
    if (!confirm('¿Estás seguro de eliminar este permiso?')) return

    try {
      await adminService.deletePermission(permissionId)
      toast({
        title: 'Éxito',
        description: 'Permiso eliminado correctamente',
      })
      loadData()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al eliminar permiso',
        variant: 'destructive',
      })
    }
  }

  const handleOpenEditRole = (role: Role) => {
    setSelectedRole(role)
    setRoleForm({
      code: role.code,
      name: role.name,
      description: role.description || '',
    })
    setIsRoleEditOpen(true)
  }

  const handleOpenEditPermission = (permission: Permission) => {
    setSelectedPermission(permission)
    setPermissionForm({
      code: permission.code,
      name: permission.name,
      description: permission.description || '',
      scope: permission.scope || '',
    })
    setIsPermissionEditOpen(true)
  }

  // Group permissions by scope
  const permissionsByScope = permissions.reduce((acc, perm) => {
    const scope = perm.scope || 'other'
    if (!acc[scope]) acc[scope] = []
    acc[scope].push(perm)
    return acc
  }, {} as Record<string, Permission[]>)

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
            Gestión de Roles y Permisos
          </h1>
          <p className="text-[#B0B3C5] mt-2">
            Administra roles, permisos y sus asignaciones
          </p>
        </div>
        <Button
          className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
          onClick={() => {
            if (activeTab === 'roles') {
              setIsRoleCreateOpen(true)
            } else {
              setIsPermissionCreateOpen(true)
            }
          }}
        >
          <Plus size={20} className="mr-2" />
          Nuevo {activeTab === 'roles' ? 'Rol' : 'Permiso'}
        </Button>
      </motion.div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="bg-[#1C2541]/50 border-[#1C2541]">
          <TabsTrigger value="roles" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <Shield size={16} className="mr-2" />
            Roles ({roles.length})
          </TabsTrigger>
          <TabsTrigger value="permissions" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <Key size={16} className="mr-2" />
            Permisos ({permissions.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="roles" className="mt-6">
          <Card className="bg-[#1C2541]/50 border-[#1C2541]">
            <CardHeader>
              <CardTitle className="text-white">Roles del Sistema</CardTitle>
              <CardDescription className="text-[#B0B3C5]">
                Total: {roles.length} roles
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Loader text="LOADING ROLES" className="py-20" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1C2541]">
                      <TableHead className="text-[#B0B3C5]">ID</TableHead>
                      <TableHead className="text-[#B0B3C5]">Código</TableHead>
                      <TableHead className="text-[#B0B3C5]">Nombre</TableHead>
                      <TableHead className="text-[#B0B3C5]">Descripción</TableHead>
                      <TableHead className="text-[#B0B3C5]">Creado</TableHead>
                      <TableHead className="text-[#B0B3C5]">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {roles.map((role) => (
                      <TableRow key={role.id} className="border-[#1C2541] hover:bg-[#1C2541]/30">
                        <TableCell className="text-white">{role.id}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="border-[#00FF73] text-[#00FF73]">
                            {role.code}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-white font-medium">{role.name}</TableCell>
                        <TableCell className="text-[#B0B3C5]">{role.description || '-'}</TableCell>
                        <TableCell className="text-[#B0B3C5]">
                          {new Date(role.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-[#00FF73] hover:text-[#00D95F] hover:bg-[#1C2541]"
                              onClick={() => handleOpenEditRole(role)}
                            >
                              <Edit size={16} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-400 hover:bg-[#1C2541]"
                              onClick={() => handleDeleteRole(role.id)}
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
        </TabsContent>

        <TabsContent value="permissions" className="mt-6">
          <div className="space-y-4">
            {Object.entries(permissionsByScope).map(([scope, scopePermissions]) => (
              <Card key={scope} className="bg-[#1C2541]/50 border-[#1C2541]">
                <CardHeader>
                  <CardTitle className="text-white text-lg font-medium">
                    {scope.charAt(0).toUpperCase() + scope.slice(1)} Scope
                  </CardTitle>
                  <CardDescription className="text-[#B0B3C5]">
                    {scopePermissions.length} permisos
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {scopePermissions.map((permission) => (
                      <div
                        key={permission.id}
                        className="p-3 bg-[#0B132B] border border-[#1C2541] rounded-lg hover:border-[#00FF73]/30 transition-all"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline" className="border-[#00FF73] text-[#00FF73] text-xs">
                                {permission.code}
                              </Badge>
                            </div>
                            <p className="text-white font-medium text-sm">{permission.name}</p>
                            {permission.description && (
                              <p className="text-[#B0B3C5] text-xs mt-1">{permission.description}</p>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-[#00FF73] hover:text-[#00D95F] hover:bg-[#1C2541]"
                              onClick={() => handleOpenEditPermission(permission)}
                            >
                              <Edit size={14} />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-400 hover:bg-[#1C2541]"
                              onClick={() => handleDeletePermission(permission.id)}
                            >
                              <Trash2 size={14} />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Role Sheet */}
      <Sheet open={isRoleCreateOpen} onOpenChange={setIsRoleCreateOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Crear Nuevo Rol</SheetTitle>
            <SheetDescription>
              Completa los datos para crear un nuevo rol en el sistema
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="role-code">Código</Label>
              <Input
                id="role-code"
                value={roleForm.code}
                onChange={(e) => setRoleForm({ ...roleForm, code: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="admin"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-name">Nombre</Label>
              <Input
                id="role-name"
                value={roleForm.name}
                onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Administrador"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-description">Descripción</Label>
              <Textarea
                id="role-description"
                value={roleForm.description}
                onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Descripción del rol"
              />
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsRoleCreateOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleCreateRole}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Crear Rol
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Edit Role Sheet */}
      <Sheet open={isRoleEditOpen} onOpenChange={setIsRoleEditOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Editar Rol</SheetTitle>
            <SheetDescription>
              Modifica la información del rol
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-role-code">Código</Label>
              <Input
                id="edit-role-code"
                value={roleForm.code}
                disabled
                className="bg-[#0B132B] border-[#1C2541] text-[#B0B3C5]"
              />
              <p className="text-xs text-[#B0B3C5]">El código no se puede modificar</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role-name">Nombre</Label>
              <Input
                id="edit-role-name"
                value={roleForm.name}
                onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role-description">Descripción</Label>
              <Textarea
                id="edit-role-description"
                value={roleForm.description}
                onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsRoleEditOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleEditRole}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Guardar Cambios
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Create Permission Sheet */}
      <Sheet open={isPermissionCreateOpen} onOpenChange={setIsPermissionCreateOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Crear Nuevo Permiso</SheetTitle>
            <SheetDescription>
              Completa los datos para crear un nuevo permiso en el sistema
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="permission-code">Código</Label>
              <Input
                id="permission-code"
                value={permissionForm.code}
                onChange={(e) => setPermissionForm({ ...permissionForm, code: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="admin:write"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="permission-name">Nombre</Label>
              <Input
                id="permission-name"
                value={permissionForm.name}
                onChange={(e) => setPermissionForm({ ...permissionForm, name: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Escribir en Admin"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="permission-scope">Scope</Label>
              <Input
                id="permission-scope"
                value={permissionForm.scope}
                onChange={(e) => setPermissionForm({ ...permissionForm, scope: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="admin"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="permission-description">Descripción</Label>
              <Textarea
                id="permission-description"
                value={permissionForm.description}
                onChange={(e) => setPermissionForm({ ...permissionForm, description: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Descripción del permiso"
              />
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsPermissionCreateOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleCreatePermission}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Crear Permiso
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Edit Permission Sheet */}
      <Sheet open={isPermissionEditOpen} onOpenChange={setIsPermissionEditOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Editar Permiso</SheetTitle>
            <SheetDescription>
              Modifica la información del permiso
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-permission-code">Código</Label>
              <Input
                id="edit-permission-code"
                value={permissionForm.code}
                disabled
                className="bg-[#0B132B] border-[#1C2541] text-[#B0B3C5]"
              />
              <p className="text-xs text-[#B0B3C5]">El código no se puede modificar</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-permission-name">Nombre</Label>
              <Input
                id="edit-permission-name"
                value={permissionForm.name}
                onChange={(e) => setPermissionForm({ ...permissionForm, name: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-permission-scope">Scope</Label>
              <Input
                id="edit-permission-scope"
                value={permissionForm.scope}
                onChange={(e) => setPermissionForm({ ...permissionForm, scope: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-permission-description">Descripción</Label>
              <Textarea
                id="edit-permission-description"
                value={permissionForm.description}
                onChange={(e) => setPermissionForm({ ...permissionForm, description: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
          </div>
          <SheetFooter>
            <Button
              variant="outline"
              onClick={() => setIsPermissionEditOpen(false)}
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleEditPermission}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Guardar Cambios
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  )
}

