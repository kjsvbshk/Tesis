/**
 * Advanced Search Page
 * Advanced search across requests, idempotency keys, audit logs, and events
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, FileText, Key, Activity, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { searchService, type RequestSearchResult, type IdempotencyKeySearchResult, type EventSearchResult } from '@/services/search.service'
import { useToast } from '@/hooks/use-toast'

export function AdvancedSearchPage() {
  const [activeTab, setActiveTab] = useState('requests')

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="text-4xl font-heading font-bold bg-gradient-to-r from-[#00FF73] to-[#FFD700] bg-clip-text text-transparent mb-2">
          Búsqueda Avanzada
        </h1>
        <p className="text-[#B0B3C5]">Buscar en requests, keys, logs y eventos</p>
      </motion.div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 bg-[#1C2541]/50">
          <TabsTrigger value="requests" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <FileText size={16} className="mr-2" />
            Requests
          </TabsTrigger>
          <TabsTrigger value="keys" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <Key size={16} className="mr-2" />
            Keys
          </TabsTrigger>
          <TabsTrigger value="logs" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <Activity size={16} className="mr-2" />
            Logs
          </TabsTrigger>
          <TabsTrigger value="events" className="data-[state=active]:bg-[#00FF73] data-[state=active]:text-black">
            <Calendar size={16} className="mr-2" />
            Events
          </TabsTrigger>
        </TabsList>

        <TabsContent value="requests">
          <RequestSearchTab />
        </TabsContent>
        <TabsContent value="keys">
          <KeySearchTab />
        </TabsContent>
        <TabsContent value="logs">
          <LogSearchTab />
        </TabsContent>
        <TabsContent value="events">
          <EventSearchTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function RequestSearchTab() {
  const [results, setResults] = useState<RequestSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    request_id: '',
    request_key: '',
    event_id: '',
    status: '',
    date_from: '',
    date_to: '',
  })
  const { toast } = useToast()

  const handleSearch = async () => {
    try {
      setLoading(true)
      const response = await searchService.searchRequests({
        request_id: filters.request_id ? parseInt(filters.request_id) : undefined,
        request_key: filters.request_key || undefined,
        event_id: filters.event_id ? parseInt(filters.event_id) : undefined,
        status: filters.status || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        limit: 50,
        offset: 0,
      })
      setResults(response.results)
      setTotal(response.total)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al buscar requests',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="bg-[#1C2541]/50 border-[#1C2541]">
      <CardHeader>
        <CardTitle className="text-white">Buscar Requests</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <Label className="text-[#B0B3C5]">Request ID</Label>
            <Input
              value={filters.request_id}
              onChange={(e) => setFilters({ ...filters, request_id: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Request Key</Label>
            <Input
              value={filters.request_key}
              onChange={(e) => setFilters({ ...filters, request_key: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Event ID</Label>
            <Input
              value={filters.event_id}
              onChange={(e) => setFilters({ ...filters, event_id: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Status</Label>
            <Input
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Desde</Label>
            <Input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Hasta</Label>
            <Input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
        </div>
        <Button onClick={handleSearch} className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
          <Search size={16} className="mr-2" />
          Buscar
        </Button>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          </div>
        ) : results.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-[#B0B3C5]">ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Key</TableHead>
                  <TableHead className="text-[#B0B3C5]">Event ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Status</TableHead>
                  <TableHead className="text-[#B0B3C5]">Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((result) => (
                  <TableRow key={result.id} className="border-[#1C2541]">
                    <TableCell className="text-white">{result.id}</TableCell>
                    <TableCell className="text-white font-mono text-xs">{result.request_key}</TableCell>
                    <TableCell className="text-white">{result.event_id || 'N/A'}</TableCell>
                    <TableCell>
                      <Badge className="bg-[#00FF73]/20 text-[#00FF73]">{result.status}</Badge>
                    </TableCell>
                    <TableCell className="text-[#B0B3C5]">
                      {result.created_at ? new Date(result.created_at).toLocaleString() : 'N/A'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <p className="text-sm text-[#B0B3C5] mt-4">Total: {total} resultados</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function KeySearchTab() {
  const [results, setResults] = useState<IdempotencyKeySearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    request_key: '',
    date_from: '',
    date_to: '',
  })
  const { toast } = useToast()

  const handleSearch = async () => {
    try {
      setLoading(true)
      const response = await searchService.searchIdempotencyKeys({
        request_key: filters.request_key || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        limit: 50,
        offset: 0,
      })
      setResults(response.results)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al buscar keys',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="bg-[#1C2541]/50 border-[#1C2541]">
      <CardHeader>
        <CardTitle className="text-white">Buscar Idempotency Keys</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <Label className="text-[#B0B3C5]">Request Key</Label>
            <Input
              value={filters.request_key}
              onChange={(e) => setFilters({ ...filters, request_key: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Desde</Label>
            <Input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Hasta</Label>
            <Input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
        </div>
        <Button onClick={handleSearch} className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
          <Search size={16} className="mr-2" />
          Buscar
        </Button>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          </div>
        ) : results.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-[#B0B3C5]">ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Request Key</TableHead>
                  <TableHead className="text-[#B0B3C5]">Request ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Creado</TableHead>
                  <TableHead className="text-[#B0B3C5]">Expira</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((result) => (
                  <TableRow key={result.id} className="border-[#1C2541]">
                    <TableCell className="text-white">{result.id}</TableCell>
                    <TableCell className="text-white font-mono text-xs">{result.request_key}</TableCell>
                    <TableCell className="text-white">{result.request_id || 'N/A'}</TableCell>
                    <TableCell className="text-[#B0B3C5]">
                      {result.created_at ? new Date(result.created_at).toLocaleString() : 'N/A'}
                    </TableCell>
                    <TableCell className="text-[#B0B3C5]">
                      {result.expires_at ? new Date(result.expires_at).toLocaleString() : 'N/A'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function LogSearchTab() {
  return (
    <Card className="bg-[#1C2541]/50 border-[#1C2541]">
      <CardHeader>
        <CardTitle className="text-white">Buscar Audit Logs</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-[#B0B3C5]">Usa la página de Auditoría para buscar logs</p>
      </CardContent>
    </Card>
  )
}

function EventSearchTab() {
  const [results, setResults] = useState<EventSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    event_id: '',
    date_from: '',
    date_to: '',
  })
  const { toast } = useToast()

  const handleSearch = async () => {
    try {
      setLoading(true)
      const response = await searchService.searchEvents({
        event_id: filters.event_id ? parseInt(filters.event_id) : undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        limit: 50,
        offset: 0,
      })
      setResults(response.results)
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Error al buscar eventos',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="bg-[#1C2541]/50 border-[#1C2541]">
      <CardHeader>
        <CardTitle className="text-white">Buscar Events</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <Label className="text-[#B0B3C5]">Event ID</Label>
            <Input
              value={filters.event_id}
              onChange={(e) => setFilters({ ...filters, event_id: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Desde</Label>
            <Input
              type="date"
              value={filters.date_from}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
          <div>
            <Label className="text-[#B0B3C5]">Fecha Hasta</Label>
            <Input
              type="date"
              value={filters.date_to}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
              className="bg-[#0B132B] border-[#1C2541] text-white"
            />
          </div>
        </div>
        <Button onClick={handleSearch} className="bg-[#00FF73] hover:bg-[#00D95F] text-black">
          <Search size={16} className="mr-2" />
          Buscar
        </Button>

        {loading ? (
          <div className="flex justify-center py-8">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-[#00FF73] border-r-transparent"></div>
          </div>
        ) : results.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[#1C2541]">
                  <TableHead className="text-[#B0B3C5]">Event ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Request ID</TableHead>
                  <TableHead className="text-[#B0B3C5]">Request Key</TableHead>
                  <TableHead className="text-[#B0B3C5]">Status</TableHead>
                  <TableHead className="text-[#B0B3C5]">Fecha</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((result, idx) => (
                  <TableRow key={idx} className="border-[#1C2541]">
                    <TableCell className="text-white">{result.event_id}</TableCell>
                    <TableCell className="text-white">{result.request_id}</TableCell>
                    <TableCell className="text-white font-mono text-xs">{result.request_key}</TableCell>
                    <TableCell>
                      <Badge className="bg-[#00FF73]/20 text-[#00FF73]">{result.status}</Badge>
                    </TableCell>
                    <TableCell className="text-[#B0B3C5]">
                      {result.created_at ? new Date(result.created_at).toLocaleString() : 'N/A'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

