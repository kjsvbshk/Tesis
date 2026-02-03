import { Zap } from 'lucide-react'

export function Loader({ text = 'SYSTEM LOADING', className = '' }: { text?: string; className?: string }) {
    return (
        <div className={`flex flex-col items-center justify-center p-8 gap-4 ${className}`}>
            <div className="relative">
                <div className="w-12 h-12 border-2 border-acid-500 rounded-none animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                    <Zap size={16} className="text-acid-500 animate-pulse" />
                </div>
            </div>
            <div className="text-acid-500 font-mono text-xs uppercase tracking-widest animate-pulse">
                {text}...
            </div>
        </div>
    )
}
