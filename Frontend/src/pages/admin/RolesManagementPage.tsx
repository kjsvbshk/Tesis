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
import { adminService, type Role, type Permission } from '@/services/admin.service'
import { useToast } from '@/hooks/use-toast'

export function RolesManagementPage() {
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('roles')
  const { toast } = useToast()

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

  const handleDeleteRole = async (roleId: number) => {
    if (!confirm('¿Estás seguro de eliminar este rol?')) return

    try {
      // TODO: Implement delete role endpoint
      toast({
        title: 'Próximamente',
        description: 'Funcionalidad de eliminación en desarrollo',
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

  const handleDeletePermission = async (permissionId: number) => {
    if (!confirm('¿Estás seguro de eliminar este permiso?')) return

    try {
      // TODO: Implement delete permission endpoint
      toast({
        title: 'Próximamente',
        description: 'Funcionalidad de eliminación en desarrollo',
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
        <Button className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
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
                <div className="text-center py-8 text-[#B0B3C5]">Cargando roles...</div>
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
                              onClick={() => {
                                toast({
                                  title: 'Próximamente',
                                  description: 'Funcionalidad de edición en desarrollo',
                                })
                              }}
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
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-400 hover:bg-[#1C2541] ml-2"
                            onClick={() => handleDeletePermission(permission.id)}
                          >
                            <Trash2 size={14} />
                          </Button>
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
    </div>
  )
}

