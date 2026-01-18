/**
 * Providers Management Page
 * CRUD completo de proveedores externos y sus endpoints
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Edit, Trash2, Settings, CheckCircle, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { providersService, type Provider, type ProviderEndpoint } from '@/services/providers.service'
import { useToast } from '@/hooks/use-toast'

export function ProvidersManagementPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [isEndpointsOpen, setIsEndpointsOpen] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null)
  const [providerEndpoints, setProviderEndpoints] = useState<ProviderEndpoint[]>([])
  const { toast } = useToast()

  // Form states
  const [createForm, setCreateForm] = useState({
    code: '',
    name: '',
    timeout_seconds: 30,
    max_retries: 3,
    circuit_breaker_threshold: 5,
    provider_metadata: '',
  })
  const [editForm, setEditForm] = useState({
    name: '',
    is_active: true,
    timeout_seconds: 30,
    max_retries: 3,
    circuit_breaker_threshold: 5,
    provider_metadata: '',
  })

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      setLoading(true)
      const data = await providersService.getProviders()
      setProviders(data)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar proveedores',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadProviderEndpoints = async (providerId: number) => {
    try {
      const endpoints = await providersService.getProviderEndpoints(providerId)
      setProviderEndpoints(endpoints)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar endpoints',
        variant: 'destructive',
      })
    }
  }

  const handleCreate = async () => {
    try {
      await providersService.createProvider(createForm)
      toast({
        title: 'Éxito',
        description: 'Proveedor creado correctamente',
      })
      setIsCreateOpen(false)
      setCreateForm({
        code: '',
        name: '',
        timeout_seconds: 30,
        max_retries: 3,
        circuit_breaker_threshold: 5,
        provider_metadata: '',
      })
      loadProviders()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al crear proveedor',
        variant: 'destructive',
      })
    }
  }

  const handleEdit = (provider: Provider) => {
    setSelectedProvider(provider)
    setEditForm({
      name: provider.name,
      is_active: provider.is_active,
      timeout_seconds: provider.timeout_seconds,
      max_retries: provider.max_retries,
      circuit_breaker_threshold: provider.circuit_breaker_threshold,
      provider_metadata: provider.provider_metadata || '',
    })
    setIsEditOpen(true)
  }

  const handleUpdate = async () => {
    if (!selectedProvider) return
    try {
      await providersService.updateProvider(selectedProvider.id, editForm)
      toast({
        title: 'Éxito',
        description: 'Proveedor actualizado correctamente',
      })
      setIsEditOpen(false)
      setSelectedProvider(null)
      loadProviders()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al actualizar proveedor',
        variant: 'destructive',
      })
    }
  }

  const handleDelete = async (providerId: number) => {
    if (!confirm('¿Estás seguro de eliminar este proveedor?')) return
    try {
      await providersService.deleteProvider(providerId)
      toast({
        title: 'Éxito',
        description: 'Proveedor eliminado correctamente',
      })
      loadProviders()
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al eliminar proveedor',
        variant: 'destructive',
      })
    }
  }

  const handleViewEndpoints = async (provider: Provider) => {
    setSelectedProvider(provider)
    await loadProviderEndpoints(provider.id)
    setIsEndpointsOpen(true)
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
            Gestión de Proveedores
          </h1>
          <p className="text-[#B0B3C5]">Administra proveedores externos y sus endpoints</p>
        </div>
        <Button
          onClick={() => setIsCreateOpen(true)}
          className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
        >
          <Plus size={20} className="mr-2" />
          Nuevo Proveedor
        </Button>
      </motion.div>

      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white">Proveedores</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
            </div>
          ) : providers.length === 0 ? (
            <p className="text-center text-[#B0B3C5] py-8">No hay proveedores registrados</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-white">Código</TableHead>
                  <TableHead className="text-white">Nombre</TableHead>
                  <TableHead className="text-white">Estado</TableHead>
                  <TableHead className="text-white">Timeout</TableHead>
                  <TableHead className="text-white">Reintentos</TableHead>
                  <TableHead className="text-white">Circuit Breaker</TableHead>
                  <TableHead className="text-white">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {providers.map((provider) => (
                  <TableRow key={provider.id} className="border-[#1C2541]">
                    <TableCell className="text-white font-mono">{provider.code}</TableCell>
                    <TableCell className="text-white">{provider.name}</TableCell>
                    <TableCell>
                      {provider.is_active ? (
                        <Badge className="bg-[#00FF73] text-black">
                          <CheckCircle size={12} className="mr-1" />
                          Activo
                        </Badge>
                      ) : (
                        <Badge variant="destructive">
                          <XCircle size={12} className="mr-1" />
                          Inactivo
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5]">{provider.timeout_seconds}s</TableCell>
                    <TableCell className="text-[#B0B3C5]">{provider.max_retries}</TableCell>
                    <TableCell className="text-[#B0B3C5]">{provider.circuit_breaker_threshold}</TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewEndpoints(provider)}
                          className="text-[#00FF73] hover:text-[#00D95F]"
                        >
                          <Settings size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(provider)}
                          className="text-blue-500 hover:text-blue-400"
                        >
                          <Edit size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(provider.id)}
                          className="text-red-500 hover:text-red-400"
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

      {/* Create Provider Sheet */}
      <Sheet open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <SheetContent className="bg-[#0B132B] border-[#1C2541] text-white overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-white">Crear Proveedor</SheetTitle>
            <SheetDescription className="text-[#B0B3C5]">
              Agrega un nuevo proveedor externo al sistema
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 mt-6">
            <div>
              <Label className="text-white">Código</Label>
              <Input
                value={createForm.code}
                onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
                placeholder="espn"
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Nombre</Label>
              <Input
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                placeholder="ESPN API"
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Timeout (segundos)</Label>
              <Input
                type="number"
                value={createForm.timeout_seconds}
                onChange={(e) => setCreateForm({ ...createForm, timeout_seconds: parseInt(e.target.value) || 30 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Máximo de Reintentos</Label>
              <Input
                type="number"
                value={createForm.max_retries}
                onChange={(e) => setCreateForm({ ...createForm, max_retries: parseInt(e.target.value) || 3 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Umbral Circuit Breaker</Label>
              <Input
                type="number"
                value={createForm.circuit_breaker_threshold}
                onChange={(e) => setCreateForm({ ...createForm, circuit_breaker_threshold: parseInt(e.target.value) || 5 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Metadata (JSON opcional)</Label>
              <Input
                value={createForm.provider_metadata}
                onChange={(e) => setCreateForm({ ...createForm, provider_metadata: e.target.value })}
                placeholder='{"api_key": "..."}'
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
          </div>
          <SheetFooter className="mt-6">
            <Button
              onClick={handleCreate}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Crear
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Edit Provider Sheet */}
      <Sheet open={isEditOpen} onOpenChange={setIsEditOpen}>
        <SheetContent className="bg-[#0B132B] border-[#1C2541] text-white overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-white">Editar Proveedor</SheetTitle>
            <SheetDescription className="text-[#B0B3C5]">
              Modifica la configuración del proveedor
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 mt-6">
            <div>
              <Label className="text-white">Nombre</Label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                className="w-4 h-4"
              />
              <Label className="text-white">Activo</Label>
            </div>
            <div>
              <Label className="text-white">Timeout (segundos)</Label>
              <Input
                type="number"
                value={editForm.timeout_seconds}
                onChange={(e) => setEditForm({ ...editForm, timeout_seconds: parseInt(e.target.value) || 30 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Máximo de Reintentos</Label>
              <Input
                type="number"
                value={editForm.max_retries}
                onChange={(e) => setEditForm({ ...editForm, max_retries: parseInt(e.target.value) || 3 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Umbral Circuit Breaker</Label>
              <Input
                type="number"
                value={editForm.circuit_breaker_threshold}
                onChange={(e) => setEditForm({ ...editForm, circuit_breaker_threshold: parseInt(e.target.value) || 5 })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Metadata (JSON opcional)</Label>
              <Input
                value={editForm.provider_metadata}
                onChange={(e) => setEditForm({ ...editForm, provider_metadata: e.target.value })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
          </div>
          <SheetFooter className="mt-6">
            <Button
              onClick={handleUpdate}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              Guardar
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Endpoints Sheet */}
      <Sheet open={isEndpointsOpen} onOpenChange={setIsEndpointsOpen}>
        <SheetContent className="bg-[#0B132B] border-[#1C2541] text-white overflow-y-auto w-full sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle className="text-white">
              Endpoints de {selectedProvider?.name}
            </SheetTitle>
            <SheetDescription className="text-[#B0B3C5]">
              Gestiona los endpoints del proveedor
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            {providerEndpoints.length === 0 ? (
              <p className="text-[#B0B3C5] text-sm">No hay endpoints configurados</p>
            ) : (
              <div className="space-y-2">
                {providerEndpoints.map((endpoint) => (
                  <div
                    key={endpoint.id}
                    className="p-3 bg-[#1C2541] border border-[#1C2541] rounded-lg"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">{endpoint.purpose}</p>
                        <p className="text-sm text-[#B0B3C5]">{endpoint.method} {endpoint.url}</p>
                      </div>
                      <CheckCircle className="text-[#00FF73]" size={20} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
