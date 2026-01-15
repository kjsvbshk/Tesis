/**
 * Requests Page
 * User page to view their request history
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, Search, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { requestsService } from '@/services/requests.service'
import { useToast } from '@/hooks/use-toast'

export function RequestsPage() {
  const [requests, setRequests] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [searchKey, setSearchKey] = useState('')
  const { toast } = useToast()

  useEffect(() => {
    loadRequests()
  }, [])

  const loadRequests = async () => {
    try {
      setLoading(true)
      const response = await requestsService.getMyRequests(50, 0)
      setRequests(response.results || [])
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar requests',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchKey) {
      loadRequests()
      return
    }

    try {
      setLoading(true)
      const response = await requestsService.getRequestByKey(searchKey)
      setRequests([response])
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Request no encontrado',
        variant: 'destructive',
      })
      setRequests([])
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, string> = {
      completed: 'bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]',
      failed: 'bg-red-500/20 text-red-500 border-red-500',
      processing: 'bg-yellow-500/20 text-yellow-500 border-yellow-500',
    }
    return variants[status] || 'bg-[#1C2541] text-[#B0B3C5] border-[#1C2541]'
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
          Mis Requests
        </h1>
        <p className="text-[#B0B3C5]">Historial de tus solicitudes y predicciones</p>
      </motion.div>

      {/* Search */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Search size={20} />
            Buscar Request
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                placeholder="Ingresa el Request Key"
                className="bg-[#0B132B] border-[#1C2541] text-white"
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </div>
            <Button
              onClick={handleSearch}
              className="bg-[#00FF73] hover:bg-[#00D95F] text-black"
            >
              <Search size={16} className="mr-2" />
              Buscar
            </Button>
            <Button
              onClick={() => {
                setSearchKey('')
                loadRequests()
              }}
              variant="outline"
              className="border-[#1C2541] text-[#B0B3C5]"
            >
              Limpiar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-white flex items-center gap-2">
              <FileText size={20} />
              Requests ({requests.length})
            </CardTitle>
            <Button
              onClick={loadRequests}
              disabled={loading}
              variant="outline"
              size="sm"
              className="border-[#1C2541] text-[#B0B3C5] hover:bg-[#1C2541]"
            >
              <RefreshCw size={16} className={`mr-2 ${loading ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-8 text-[#B0B3C5]">
              No se encontraron requests
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-[#1C2541]">
                    <TableHead className="text-[#B0B3C5]">ID</TableHead>
                    <TableHead className="text-[#B0B3C5]">Request Key</TableHead>
                    <TableHead className="text-[#B0B3C5]">Event ID</TableHead>
                    <TableHead className="text-[#B0B3C5]">Status</TableHead>
                    <TableHead className="text-[#B0B3C5]">Creado</TableHead>
                    <TableHead className="text-[#B0B3C5]">Completado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.map((request) => (
                    <TableRow key={request.id} className="border-[#1C2541] hover:bg-[#1C2541]/30">
                      <TableCell className="text-white">{request.id}</TableCell>
                      <TableCell className="text-white font-mono text-xs">
                        {request.request_key}
                      </TableCell>
                      <TableCell className="text-white">{request.event_id || 'N/A'}</TableCell>
                      <TableCell>
                        <Badge className={getStatusBadge(request.status)}>
                          {request.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-[#B0B3C5]">
                        {request.created_at
                          ? new Date(request.created_at).toLocaleString()
                          : 'N/A'}
                      </TableCell>
                      <TableCell className="text-[#B0B3C5]">
                        {request.completed_at
                          ? new Date(request.completed_at).toLocaleString()
                          : 'N/A'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

