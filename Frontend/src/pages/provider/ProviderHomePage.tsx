import { motion } from 'framer-motion'
import { Activity, Server, Clock, Database, CheckCircle, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { Link } from 'react-router-dom'

export function ProviderHomePage() {
    const { user } = useAuth()

    // Provider theme colors
    const themeColor = "text-[#00F0FF]"
    const themeBg = "bg-[#00F0FF]"
    const themeBorder = "border-[#00F0FF]"
    const gradient = "from-[#00F0FF] to-[#0099FF]"

    return (
        <div className="space-y-6">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
                <div>
                    <Link to="/provider">
                        <h1 className={`text-4xl font-heading font-bold bg-gradient-to-r ${gradient} bg-clip-text text-transparent mb-2 hover:opacity-80 transition-opacity`}>
                            Provider Portal
                        </h1>
                    </Link>
                    <p className="text-[#B0B3C5]">Welcome back, <span className="text-white font-medium">{user?.username}</span></p>
                </div>

                <div className={`px-4 py-2 bg-[#00F0FF]/10 ${themeBorder} border rounded-sm flex items-center gap-3`}>
                    <div className={`w-2 h-2 rounded-full ${themeBg} animate-pulse`} />
                    <span className={`font-mono text-xs ${themeColor} font-bold`}>SYSTEM STATUS: OPERATIONAL</span>
                </div>
            </motion.div>

            {/* Metrics Grid */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
                <StatCard
                    title="Daily Requests"
                    value="45,231"
                    icon={<Activity size={24} />}
                    description="+12% from yesterday"
                    themeColor={themeColor}
                />
                <StatCard
                    title="Avg Latency"
                    value="42ms"
                    icon={<Clock size={24} />}
                    description="Within optimal range"
                    themeColor={themeColor}
                />
                <StatCard
                    title="Success Rate"
                    value="99.9%"
                    icon={<CheckCircle size={24} />}
                    description="0.1% error rate"
                    themeColor={themeColor}
                />
                <StatCard
                    title="Active Endpoints"
                    value="12"
                    icon={<Server size={24} />}
                    description="All endpoints healthy"
                    themeColor={themeColor}
                />
            </motion.div>

            {/* Main Status Area */}
            <div className="grid gap-6 md:grid-cols-3">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                    className="md:col-span-2"
                >
                    <Card className={`bg-[#1C2541]/50 border-white/5`}>
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <Activity className={themeColor} size={20} />
                                Traffic Overview
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="h-[300px] flex items-center justify-center border border-dashed border-white/10 rounded-md bg-black/20">
                                <div className="text-center">
                                    <Database size={48} className={`mx-auto mb-4 ${themeColor} opacity-50`} />
                                    <p className="text-muted-foreground font-mono text-sm">Real-time traffic visualization would appear here.</p>
                                    <p className="text-xs text-[#B0B3C5] mt-1">(Mock Data for UI Demo)</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6, delay: 0.5 }}
                >
                    <Card className={`bg-[#1C2541]/50 border-white/5 h-full`}>
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <AlertTriangle className="text-yellow-500" size={20} />
                                Recent Alerts
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="p-3 bg-black/30 border-l-2 border-yellow-500 rounded-r-sm">
                                <div className="flex justify-between items-start mb-1">
                                    <span className="text-yellow-500 font-bold text-xs font-mono">WARNING</span>
                                    <span className="text-muted-foreground text-[10px]">10m ago</span>
                                </div>
                                <p className="text-sm text-white">High latency detected on endpoint /api/v2/odds</p>
                            </div>

                            <div className="p-3 bg-black/30 border-l-2 border-[#00F0FF] rounded-r-sm">
                                <div className="flex justify-between items-start mb-1">
                                    <span className={`${themeColor} font-bold text-xs font-mono`}>INFO</span>
                                    <span className="text-muted-foreground text-[10px]">1h ago</span>
                                </div>
                                <p className="text-sm text-white">Daily sync completed successfully</p>
                            </div>

                            <div className="p-3 bg-black/30 border-l-2 border-green-500 rounded-r-sm">
                                <div className="flex justify-between items-start mb-1">
                                    <span className="text-green-500 font-bold text-xs font-mono">RESOLVED</span>
                                    <span className="text-muted-foreground text-[10px]">2h ago</span>
                                </div>
                                <p className="text-sm text-white">Connection restored to backup server</p>
                            </div>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>
        </div>
    )
}

function StatCard({
    title,
    value,
    icon,
    description,
    themeColor
}: {
    title: string
    value: string
    icon: React.ReactNode
    description: string
    themeColor: string
}) {
    return (
        <Card className={`bg-[#1C2541]/50 border-[#1C2541] hover:border-[#00F0FF]/30 transition-all group`}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-[#B0B3C5]">{title}</CardTitle>
                <div className={`${themeColor} group-hover:scale-110 transition-transform`}>{icon}</div>
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold text-white">{value}</div>
                <p className="text-xs text-[#B0B3C5] mt-1 font-mono">{description}</p>
            </CardContent>
        </Card>
    )
}
