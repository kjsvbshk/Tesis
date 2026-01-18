/**
 * Sync Records Page
 * Historial de sincronizaciones y logs de errores
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Search, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
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

interface SyncRecord {
  id: number
  request_key: string
  status: string
  created_at: string
  completed_at: string | null
  error_message: string | null
  user_id: number
}

export function SyncRecordsPage() {
  const [records, setRecords] = useState<SyncRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const { toast } = useToast()

  useEffect(() => {
    loadRecords()
  }, [])

  const loadRecords = async () => {
    try {
      setLoading(true)
      const data = await requestsService.getMyRequests(100, 0, statusFilter !== 'all' ? statusFilter : undefined)
      setRecords(data.items as SyncRecord[])
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar registros de sincronización',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const filteredRecords = records.filter((record) => {
    const matchesSearch = searchTerm === '' || 
      record.request_key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (record.error_message && record.error_message.toLowerCase().includes(searchTerm.toLowerCase()))
    return matchesSearch
  })

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <Badge className="bg-[#00FF73] text-black"><CheckCircle size={12} className="mr-1" />Completado</Badge>
      case 'failed':
        return <Badge variant="destructive"><AlertCircle size={12} className="mr-1" />Fallido</Badge>
      case 'processing':
        return <Badge className="bg-yellow-500 text-black"><RefreshCw size={12} className="mr-1 animate-spin" />Procesando</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const stats = {
    total: records.length,
    completed: records.filter(r => r.status === 'completed').length,
    failed: records.filter(r => r.status === 'failed').length,
    processing: records.filter(r => r.status === 'processing').length,
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
            Registros de Sincronización
          </h1>
          <p className="text-[#B0B3C5]">Historial y logs de sincronizaciones con proveedores</p>
        </div>
        <Button onClick={loadRecords} variant="outline" className="border-[#1C2541] text-[#B0B3C5]">
          <RefreshCw size={16} className="mr-2" />
          Actualizar
        </Button>
      </motion.div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats.total}</div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Completados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-[#00FF73]">{stats.completed}</div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Fallidos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">{stats.failed}</div>
          </CardContent>
        </Card>
        <Card className="bg-[#1C2541]/50 border-[#1C2541]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#B0B3C5]">Procesando</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-500">{stats.processing}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#B0B3C5]" size={20} />
                <Input
                  placeholder="Buscar por request key o error..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-[#0B132B] border-[#1C2541] text-white"
                />
              </div>
            </div>
            <div className="w-48">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value)
                  loadRecords()
                }}
                className="w-full rounded-lg bg-[#0B132B] border border-[#1C2541] px-3 py-2 text-white"
              >
                <option value="all">Todos los estados</option>
                <option value="completed">Completados</option>
                <option value="failed">Fallidos</option>
                <option value="processing">Procesando</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Records Table */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white">Registros</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
            </div>
          ) : filteredRecords.length === 0 ? (
            <p className="text-center text-[#B0B3C5] py-8">No hay registros disponibles</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-white">Request Key</TableHead>
                  <TableHead className="text-white">Estado</TableHead>
                  <TableHead className="text-white">Creado</TableHead>
                  <TableHead className="text-white">Completado</TableHead>
                  <TableHead className="text-white">Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRecords.map((record) => (
                  <TableRow key={record.id} className="border-[#1C2541]">
                    <TableCell className="text-white font-mono text-sm">{record.request_key}</TableCell>
                    <TableCell>{getStatusBadge(record.status)}</TableCell>
                    <TableCell className="text-[#B0B3C5] text-sm">
                      {new Date(record.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5] text-sm">
                      {record.completed_at ? new Date(record.completed_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="text-red-400 text-sm max-w-md truncate">
                      {record.error_message || '-'}
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
