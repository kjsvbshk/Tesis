/**
 * Audit Management Page
 * Displays and filters audit logs
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, Search } from 'lucide-react'
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
import { searchService, type AuditLogSearchResult } from '@/services/search.service'
import { useToast } from '@/hooks/use-toast'

export function AuditManagementPage() {
  const [logs, setLogs] = useState<AuditLogSearchResult[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    actor_user_id: '',
    action: '',
    resource_type: '',
    resource_id: '',
    date_from: '',
    date_to: '',
  })
  const [offset, setOffset] = useState(0)
  const limit = 50
  const { toast } = useToast()

  useEffect(() => {
    loadLogs()
  }, [offset])

  const loadLogs = async () => {
    try {
      setLoading(true)
      const response = await searchService.searchAuditLogs({
        actor_user_id: filters.actor_user_id ? parseInt(filters.actor_user_id) : undefined,
        action: filters.action || undefined,
        resource_type: filters.resource_type || undefined,
        resource_id: filters.resource_id ? parseInt(filters.resource_id) : undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        limit,
        offset,
      })
      setLogs(response.results)
      setTotal(response.total)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al cargar logs de auditoría',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFilter = () => {
    setOffset(0)
    loadLogs()
  }

  const handleReset = () => {
    setFilters({
      actor_user_id: '',
      action: '',
      resource_type: '',
      resource_id: '',
      date_from: '',
      date_to: '',
    })
    setOffset(0)
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('es-ES')
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
          Gestión de Auditoría
        </h1>
        <p className="text-[#B0B3C5]">Registros de auditoría y actividad del sistema</p>
      </motion.div>

      {/* Filters */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Search size={20} />
            Filtros de Búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="actor_user_id" className="text-[#B0B3C5]">
                ID Usuario
              </Label>
              <Input
                id="actor_user_id"
                type="number"
                value={filters.actor_user_id}
                onChange={(e) => setFilters({ ...filters, actor_user_id: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Filtrar por usuario"
              />
            </div>
            <div>
              <Label htmlFor="action" className="text-[#B0B3C5]">
                Acción
              </Label>
              <Input
                id="action"
                value={filters.action}
                onChange={(e) => setFilters({ ...filters, action: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Ej: create, update, delete"
              />
            </div>
            <div>
              <Label htmlFor="resource_type" className="text-[#B0B3C5]">
                Tipo de Recurso
              </Label>
              <Input
                id="resource_type"
                value={filters.resource_type}
                onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="Ej: user, role, bet"
              />
            </div>
            <div>
              <Label htmlFor="resource_id" className="text-[#B0B3C5]">
                ID Recurso
              </Label>
              <Input
                id="resource_id"
                type="number"
                value={filters.resource_id}
                onChange={(e) => setFilters({ ...filters, resource_id: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
                placeholder="ID del recurso"
              />
            </div>
            <div>
              <Label htmlFor="date_from" className="text-[#B0B3C5]">
                Fecha Desde
              </Label>
              <Input
                id="date_from"
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
            <div>
              <Label htmlFor="date_to" className="text-[#B0B3C5]">
                Fecha Hasta
              </Label>
              <Input
                id="date_to"
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
                className="bg-[#0B132B] border-[#1C2541] text-white"
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={handleFilter} className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
              <Search size={16} className="mr-2" />
              Buscar
            </Button>
            <Button onClick={handleReset} variant="outline" className="border-[#1C2541] text-[#B0B3C5]">
              Limpiar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card className="bg-[#1C2541]/50 border-[#1C2541]">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <FileText size={20} />
            Resultados ({total})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-[#B0B3C5]">
              No se encontraron logs de auditoría
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1C2541]">
                      <TableHead className="text-[#B0B3C5]">ID</TableHead>
                      <TableHead className="text-[#B0B3C5]">Usuario</TableHead>
                      <TableHead className="text-[#B0B3C5]">Acción</TableHead>
                      <TableHead className="text-[#B0B3C5]">Recurso</TableHead>
                      <TableHead className="text-[#B0B3C5]">Fecha</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id} className="border-[#1C2541] hover:bg-[#1C2541]/30">
                        <TableCell className="text-white">{log.id}</TableCell>
                        <TableCell className="text-white">
                          {log.actor_user_id || 'N/A'}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              log.action.includes('delete')
                                ? 'destructive'
                                : log.action.includes('create')
                                ? 'default'
                                : 'secondary'
                            }
                            className="bg-[#00FF73]/20 text-[#00FF73] border-[#00FF73]"
                          >
                            {log.action}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-white">
                          {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                        </TableCell>
                        <TableCell className="text-[#B0B3C5]">{formatDate(log.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <div className="flex justify-between items-center mt-4">
                <p className="text-sm text-[#B0B3C5]">
                  Mostrando {offset + 1} - {Math.min(offset + limit, total)} de {total}
                </p>
                <div className="flex gap-2">
                  <Button
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    variant="outline"
                    className="border-[#1C2541] text-[#B0B3C5]"
                  >
                    Anterior
                  </Button>
                  <Button
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                    variant="outline"
                    className="border-[#1C2541] text-[#B0B3C5]"
                  >
                    Siguiente
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

