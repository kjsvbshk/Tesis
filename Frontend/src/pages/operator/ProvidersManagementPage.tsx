/**
 * Providers Management Page
 * CRUD completo de proveedores externos y sus endpoints
 */

import { useReducer, useEffect } from 'react'
import { LazyMotion, domAnimation, m } from 'framer-motion'
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

interface ProvidersState {
  providers: Provider[]
  loading: boolean
  isCreateOpen: boolean
  isEditOpen: boolean
  isEndpointsOpen: boolean
  selectedProvider: Provider | null
  providerEndpoints: ProviderEndpoint[]
  createForm: {
    code: string
    name: string
    timeout_seconds: number
    max_retries: number
    circuit_breaker_threshold: number
    provider_metadata: string
  }
  editForm: {
    name: string
    is_active: boolean
    timeout_seconds: number
    max_retries: number
    circuit_breaker_threshold: number
    provider_metadata: string
  }
}

type ProvidersAction =
  | { type: 'SET_PROVIDERS'; payload: Provider[] }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_CREATE_OPEN'; payload: boolean }
  | { type: 'SET_EDIT_OPEN'; payload: boolean }
  | { type: 'SET_ENDPOINTS_OPEN'; payload: boolean }
  | { type: 'SET_SELECTED_PROVIDER'; payload: Provider | null }
  | { type: 'SET_PROVIDER_ENDPOINTS'; payload: ProviderEndpoint[] }
  | { type: 'SET_CREATE_FORM'; payload: Partial<ProvidersState['createForm']> }
  | { type: 'SET_EDIT_FORM'; payload: Partial<ProvidersState['editForm']> }
  | { type: 'RESET_CREATE_FORM' }

const initialCreateForm = {
  code: '',
  name: '',
  timeout_seconds: 30,
  max_retries: 3,
  circuit_breaker_threshold: 5,
  provider_metadata: '',
}

const initialState: ProvidersState = {
  providers: [],
  loading: true,
  isCreateOpen: false,
  isEditOpen: false,
  isEndpointsOpen: false,
  selectedProvider: null,
  providerEndpoints: [],
  createForm: initialCreateForm,
  editForm: {
    name: '',
    is_active: true,
    timeout_seconds: 30,
    max_retries: 3,
    circuit_breaker_threshold: 5,
    provider_metadata: '',
  },
}

function providersReducer(state: ProvidersState, action: ProvidersAction): ProvidersState {
  switch (action.type) {
    case 'SET_PROVIDERS': return { ...state, providers: action.payload }
    case 'SET_LOADING': return { ...state, loading: action.payload }
    case 'SET_CREATE_OPEN': return { ...state, isCreateOpen: action.payload }
    case 'SET_EDIT_OPEN': return { ...state, isEditOpen: action.payload }
    case 'SET_ENDPOINTS_OPEN': return { ...state, isEndpointsOpen: action.payload }
    case 'SET_SELECTED_PROVIDER': return { ...state, selectedProvider: action.payload }
    case 'SET_PROVIDER_ENDPOINTS': return { ...state, providerEndpoints: action.payload }
    case 'SET_CREATE_FORM': return { ...state, createForm: { ...state.createForm, ...action.payload } }
    case 'SET_EDIT_FORM': return { ...state, editForm: { ...state.editForm, ...action.payload } }
    case 'RESET_CREATE_FORM': return { ...state, createForm: initialCreateForm }
    default: return state
  }
}

export function ProvidersManagementPage() {
  const [state, dispatch] = useReducer(providersReducer, initialState)
  const {
    providers, loading, isCreateOpen, isEditOpen, isEndpointsOpen,
    selectedProvider, providerEndpoints, createForm, editForm,
  } = state
  const { toast } = useToast()

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true })
      const data = await providersService.getProviders()
      dispatch({ type: 'SET_PROVIDERS', payload: data })
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar proveedores',
        variant: 'destructive',
      })
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }

  const loadProviderEndpoints = async (providerId: number) => {
    try {
      const endpoints = await providersService.getProviderEndpoints(providerId)
      dispatch({ type: 'SET_PROVIDER_ENDPOINTS', payload: endpoints })
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
      dispatch({ type: 'SET_CREATE_OPEN', payload: false })
      dispatch({ type: 'RESET_CREATE_FORM' })
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
    dispatch({ type: 'SET_SELECTED_PROVIDER', payload: provider })
    dispatch({ type: 'SET_EDIT_FORM', payload: {
      name: provider.name,
      is_active: provider.is_active,
      timeout_seconds: provider.timeout_seconds,
      max_retries: provider.max_retries,
      circuit_breaker_threshold: provider.circuit_breaker_threshold,
      provider_metadata: provider.provider_metadata || '',
    } })
    dispatch({ type: 'SET_EDIT_OPEN', payload: true })
  }

  const handleUpdate = async () => {
    if (!selectedProvider) return
    try {
      await providersService.updateProvider(selectedProvider.id, editForm)
      toast({
        title: 'Éxito',
        description: 'Proveedor actualizado correctamente',
      })
      dispatch({ type: 'SET_EDIT_OPEN', payload: false })
      dispatch({ type: 'SET_SELECTED_PROVIDER', payload: null })
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
    dispatch({ type: 'SET_SELECTED_PROVIDER', payload: provider })
    await loadProviderEndpoints(provider.id)
    dispatch({ type: 'SET_ENDPOINTS_OPEN', payload: true })
  }

  return (
    <LazyMotion features={domAnimation}>
    <div className="space-y-6">
      <m.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-4xl font-heading font-semibold text-[#00FF73] mb-2">
            Gestión de Proveedores
          </h1>
          <p className="text-[#B0B3C5]">Administra proveedores externos y sus endpoints</p>
        </div>
        <Button
          onClick={() => dispatch({ type: 'SET_CREATE_OPEN', payload: true })}
          className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
        >
          <Plus size={20} className="mr-2" />
          Nuevo Proveedor
        </Button>
      </m.div>

      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white">Proveedores</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="inline-block size-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
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
      <Sheet open={isCreateOpen} onOpenChange={(v) => dispatch({ type: 'SET_CREATE_OPEN', payload: v })}>
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
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { code: e.target.value } })}
                placeholder="espn"
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Nombre</Label>
              <Input
                value={createForm.name}
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { name: e.target.value } })}
                placeholder="ESPN API"
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Timeout (segundos)</Label>
              <Input
                type="number"
                value={createForm.timeout_seconds}
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { timeout_seconds: parseInt(e.target.value) || 30 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Máximo de Reintentos</Label>
              <Input
                type="number"
                value={createForm.max_retries}
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { max_retries: parseInt(e.target.value) || 3 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Umbral Circuit Breaker</Label>
              <Input
                type="number"
                value={createForm.circuit_breaker_threshold}
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { circuit_breaker_threshold: parseInt(e.target.value) || 5 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Metadata (JSON opcional)</Label>
              <Input
                value={createForm.provider_metadata}
                onChange={(e) => dispatch({ type: 'SET_CREATE_FORM', payload: { provider_metadata: e.target.value } })}
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
      <Sheet open={isEditOpen} onOpenChange={(v) => dispatch({ type: 'SET_EDIT_OPEN', payload: v })}>
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
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { name: e.target.value } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { is_active: e.target.checked } })}
                className="size-4"
              />
              <Label className="text-white">Activo</Label>
            </div>
            <div>
              <Label className="text-white">Timeout (segundos)</Label>
              <Input
                type="number"
                value={editForm.timeout_seconds}
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { timeout_seconds: parseInt(e.target.value) || 30 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Máximo de Reintentos</Label>
              <Input
                type="number"
                value={editForm.max_retries}
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { max_retries: parseInt(e.target.value) || 3 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Umbral Circuit Breaker</Label>
              <Input
                type="number"
                value={editForm.circuit_breaker_threshold}
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { circuit_breaker_threshold: parseInt(e.target.value) || 5 } })}
                className="bg-[#1C2541] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label className="text-white">Metadata (JSON opcional)</Label>
              <Input
                value={editForm.provider_metadata}
                onChange={(e) => dispatch({ type: 'SET_EDIT_FORM', payload: { provider_metadata: e.target.value } })}
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
      <Sheet open={isEndpointsOpen} onOpenChange={(v) => dispatch({ type: 'SET_ENDPOINTS_OPEN', payload: v })}>
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
    </LazyMotion>
  )
}
