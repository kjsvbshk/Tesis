import { LazyMotion, domAnimation, m } from 'framer-motion'
import { Card, CardContent } from '@/components/ui/card'
import { Database } from 'lucide-react'

export function ProviderIntegrationPage() {
    return (
        <LazyMotion features={domAnimation}>
        <div className="space-y-6">
            <m.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                <h1 className="text-4xl font-heading font-semibold text-[#00F0FF] mb-2">Integration Status</h1>
                <p className="text-[#B0B3C5]">Manage your API connections and webhooks</p>
            </m.div>

            <Card className="bg-[#1C2541]/50 border-white/5">
                <CardContent className="flex flex-col items-center justify-center py-20">
                    <Database size={64} className="text-[#00F0FF] opacity-20 mb-4" />
                    <h2 className="text-xl text-white font-semibold">Integration Module</h2>
                    <p className="text-[#B0B3C5] mt-2">API Endpoint configuration coming soon.</p>
                </CardContent>
            </Card>
        </div>
        </LazyMotion>
    )
}
