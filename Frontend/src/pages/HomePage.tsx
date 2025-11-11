import { motion } from 'framer-motion'
import { FaWallet, FaBullseye, FaTrophy } from 'react-icons/fa'

export function HomePage() {
  return (
    <div className="space-y-6">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h1 className="text-5xl font-heading font-bold bg-gradient-to-r from-[#00FF73] via-[#00D95F] to-[#FFD700] bg-clip-text text-transparent mb-3 drop-shadow-[0_0_15px_rgba(0,255,115,0.5)]">
          House Always Wins
        </h1>
        <p className="text-[#B0B3C5] text-lg font-medium">Bienvenido a HAW. Explora partidos y arma tu boleta.</p>
      </motion.div>
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      >
        <StatCard title="Saldo" value="$1,250.00" icon={<FaWallet size={24} />} />
        <StatCard title="Apuestas" value="12" icon={<FaBullseye size={24} />} />
        <StatCard title="Ganancias" value="$320.50" icon={<FaTrophy size={24} />} />
      </motion.div>
    </div>
  )
}

function StatCard({ title, value, icon }: { title: string; value: string; icon: React.ReactNode }) {
  return (
    <motion.div 
      whileHover={{ scale: 1.05, y: -5 }}
      transition={{ duration: 0.3 }}
      className="rounded-lg border border-[#1C2541]/50 bg-[#1C2541] p-6 shadow-lg hover:shadow-[0_0_25px_rgba(0,255,115,0.2)] hover:border-[#00FF73]/30 transition-all duration-300 card-glow"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-[#B0B3C5] font-medium uppercase tracking-wider">{title}</div>
        <div className="text-[#00FF73] neon-glow-green rounded-full p-2 bg-[#00FF73]/10">{icon}</div>
      </div>
      <div className="text-3xl font-mono font-bold text-neon-green">{value}</div>
    </motion.div>
  )
}