import React, { useState, useEffect } from 'react'
import { Settings, Database, CheckCircle2, AlertCircle, RefreshCw, Activity, Cpu } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { adminService, ModelVersion } from '@/services/admin.service'

const SettingsPage: React.FC = () => {
  const [models, setModels] = useState<ModelVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activating, setActivating] = useState<number | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const fetchModels = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminService.getModels()
      setModels(data)
    } catch (err: any) {
      setError('Error al cargar las versiones de los modelos')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchModels()
  }, [])

  const handleActivate = async (id: number) => {
    setActivating(id)
    setSuccessMsg(null)
    try {
      await adminService.activateModel(id)
      setSuccessMsg('Modelo activado correctamente')
      await fetchModels()
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMsg(null), 3000)
    } catch (err: any) {
      setError('Error al activar el modelo')
      console.error(err)
    } finally {
      setActivating(null)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-100 p-8">
      {/* Header section */}
      <div className="mb-10">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-lime-500/10 rounded-lg border border-lime-500/20">
            <Settings className="text-lime-400" size={24} />
          </div>
          <h1 className="text-3xl font-bold tracking-tighter uppercase">
            System <span className="text-lime-400">Configuration</span>
          </h1>
        </div>
        <p className="text-gray-400 max-w-2xl">
          Administra las versiones de los modelos de Machine Learning y la configuración central del motor de predicciones.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ML Models Management Card */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#111] border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Database className="text-lime-400" size={20} />
                <h2 className="text-xl font-bold uppercase tracking-tight">Model Versions</h2>
              </div>
              <button 
                onClick={fetchModels}
                className="p-2 hover:bg-white/5 rounded-full transition-colors text-gray-400 hover:text-white"
              >
                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="p-6">
              <AnimatePresence mode="wait">
                {loading && models.length === 0 ? (
                  <div className="py-20 flex flex-col items-center justify-center gap-4">
                    <div className="w-12 h-12 border-4 border-lime-500/20 border-t-lime-500 rounded-full animate-spin"></div>
                    <p className="text-gray-500 animate-pulse uppercase tracking-widest text-xs">Fetching registry...</p>
                  </div>
                ) : error ? (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3 text-red-400">
                    <AlertCircle size={20} className="shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold">Error</p>
                      <p className="text-sm">{error}</p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {models.map((model) => (
                      <motion.div
                        key={model.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`group relative p-4 rounded-xl border transition-all duration-300 ${
                          model.is_active 
                            ? 'bg-lime-500/5 border-lime-500/30 shadow-[0_0_20px_rgba(132,204,22,0.05)]' 
                            : 'bg-white/[0.02] border-white/5 hover:border-white/10'
                        }`}
                      >
                        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                          <div className="flex items-start gap-4">
                            <div className={`p-3 rounded-lg ${model.is_active ? 'bg-lime-500/10 text-lime-400' : 'bg-white/5 text-gray-400'}`}>
                              <Cpu size={20} />
                            </div>
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-bold text-lg">{model.version}</h3>
                                {model.is_active && (
                                  <span className="bg-lime-500 text-black text-[10px] font-black px-2 py-0.5 rounded-full uppercase">
                                    Active
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500 flex items-center gap-3">
                                <span>Trained: {model.model_metadata?.trained_at ? new Date(model.model_metadata.trained_at).toLocaleDateString() : 'N/A'}</span>
                                <span className="w-1 h-1 bg-gray-700 rounded-full"></span>
                                <span>Type: {model.model_metadata?.model_type || 'Unknown'}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-4">
                            {/* Short metrics preview */}
                            <div className="hidden sm:flex items-center gap-4 pr-4 border-r border-white/5">
                              <div className="text-center">
                                <p className="text-[10px] text-gray-500 uppercase tracking-tighter">ROC AUC</p>
                                <p className="text-sm font-mono text-lime-400/80">
                                  {model.model_metadata?.metrics?.roc_auc?.toFixed(3) || model.model_metadata?.roc_auc?.toFixed(3) || '0.000'}
                                </p>
                              </div>
                              <div className="text-center">
                                <p className="text-[10px] text-gray-500 uppercase tracking-tighter">ACC</p>
                                <p className="text-sm font-mono text-white/80">
                                  {model.model_metadata?.metrics?.accuracy?.toFixed(1) || model.model_metadata?.accuracy?.toFixed(1) || '0.0'}%
                                </p>
                              </div>
                            </div>

                            {!model.is_active && (
                              <button
                                onClick={() => handleActivate(model.id)}
                                disabled={activating !== null}
                                className="px-4 py-2 bg-white/5 hover:bg-lime-500 hover:text-black rounded-lg transition-all text-sm font-bold disabled:opacity-50 uppercase tracking-tight"
                              >
                                {activating === model.id ? 'Activating...' : 'Activate'}
                              </button>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
          
          {/* Audit Logs Quick View (Coming soon) */}
          <div className="bg-white/[0.01] border border-dashed border-white/10 rounded-2xl p-12 text-center">
             <Activity className="mx-auto text-gray-600 mb-4" size={32} />
             <h3 className="text-gray-400 font-bold uppercase tracking-widest text-sm mb-1">Audit Trail Sync</h3>
             <p className="text-gray-600 text-xs uppercase tracking-tight">Real-time action logging coming soon.</p>
          </div>
        </div>

        {/* Sidebar Info Panel */}
        <div className="space-y-6">
          <div className="bg-[#111] border border-white/5 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-lime-500/5 blur-3xl -mr-16 -mt-16 rounded-full"></div>
            
            <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
              <AlertCircle className="text-lime-400" size={18} />
              Información de Versiones
            </h3>
            <div className="space-y-4 text-sm text-gray-400">
              <p>
                Al activar una versión, el motor de predicciones cargará automáticamente el archivo <code className="text-lime-300">.joblib</code> correspondiente en el backend.
              </p>
              <p>
                Si el archivo no existe en el servidor, el sistema entrará en <span className="text-orange-400">Modo Simulado</span> para garantizar la disponibilidad del servicio.
              </p>
              <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                <p className="text-xs text-white font-bold mb-1 uppercase tracking-wider">Políticas de Cambio:</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>Atomicidad garantizada en BD</li>
                  <li>No requiere reinicio de API</li>
                  <li>Carga perezosa del nuevo modelo</li>
                </ul>
              </div>
            </div>
          </div>

          <AnimatePresence>
            {successMsg && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="bg-lime-500 text-black p-4 rounded-xl font-bold flex items-center gap-3 shadow-[0_0_20px_rgba(132,204,22,0.3)]"
              >
                <CheckCircle2 size={20} />
                {successMsg}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
