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
        <h1 className="text-4xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent mb-2">
          House Always Wins
        </h1>
        <p className="text-muted-foreground text-lg">Bienvenido a HAW. Explora partidos y arma tu boleta.</p>
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
      transition={{ duration: 0.2 }}
      className="rounded-lg border bg-card/60 backdrop-blur p-4 shadow-sm hover:shadow-lg transition-all duration-200"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm text-muted-foreground">{title}</div>
        <div className="text-primary">{icon}</div>
      </div>
      <div className="text-2xl font-bold text-green-400">{value}</div>
    </motion.div>
  )
}