/**
 * Users Management Page
 * CRUD completo de usuarios para administradores
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Edit, Trash2, Shield, Search } from 'lucide-react'
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
import { usersService, type User } from '@/services/users.service'
import { adminService } from '@/services/admin.service'
import { useToast } from '@/hooks/use-toast'

export function UsersManagementPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const { toast } = useToast()

  useEffect(() => {
    loadUsers()
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

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase())
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
        <Button className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
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
                    <TableCell className="text-white">${user.credits.toFixed(2)}</TableCell>
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
                          onClick={() => {
                            // TODO: Open edit dialog
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
                          className="text-[#00FF73] hover:text-[#00D95F] hover:bg-[#1C2541]"
                          onClick={() => {
                            // TODO: Open roles dialog
                            toast({
                              title: 'Próximamente',
                              description: 'Gestión de roles en desarrollo',
                            })
                          }}
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
    </div>
  )
}

