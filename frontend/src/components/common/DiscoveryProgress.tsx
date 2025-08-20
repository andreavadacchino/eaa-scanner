import { ClockIcon, GlobeAltIcon } from '@heroicons/react/24/outline'
import { DiscoveryStatus } from '@types/index'
import { motion } from 'framer-motion'

interface DiscoveryProgressProps {
  status: DiscoveryStatus
  totalDiscovered: number
}

export function DiscoveryProgress({ status, totalDiscovered }: DiscoveryProgressProps) {
  const formatDuration = (start?: Date) => {
    if (!start) return '00:00'
    const now = new Date()
    const diff = Math.floor((now.getTime() - start.getTime()) / 1000)
    const minutes = Math.floor(diff / 60)
    const seconds = diff % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  
  const getEstimatedCompletion = () => {
    if (!status.start_time || status.progress === 0) return null
    
    const elapsed = new Date().getTime() - status.start_time.getTime()
    const estimatedTotal = (elapsed / status.progress) * 100
    const remaining = estimatedTotal - elapsed
    
    const remainingMinutes = Math.ceil(remaining / (1000 * 60))
    return remainingMinutes > 0 ? `≈ ${remainingMinutes} min rimanenti` : 'Quasi completato'
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Progresso Discovery</span>
          <span className="font-medium text-gray-900">{Math.round(status.progress)}%</span>
        </div>
        
        <div className="progress-bar h-3">
          <motion.div 
            className="progress-fill h-full"
            initial={{ width: 0 }}
            animate={{ width: `${status.progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
      </div>
      
      {/* Status Info Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="flex items-center space-x-2 text-gray-600 mb-1">
            <GlobeAltIcon className="h-4 w-4" />
            <span>Pagine Scoperte</span>
          </div>
          <div className="text-lg font-semibold text-gray-900">{totalDiscovered}</div>
        </div>
        
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="flex items-center space-x-2 text-gray-600 mb-1">
            <ClockIcon className="h-4 w-4" />
            <span>Durata</span>
          </div>
          <div className="text-lg font-semibold text-gray-900">
            {formatDuration(status.start_time)}
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="text-gray-600 mb-1">Pagina Corrente</div>
          <div className="text-sm font-mono truncate text-gray-900">
            {status.current_url ? 
              status.current_url.split('/').pop() || 'Homepage' : 
              'In attesa...'
            }
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="text-gray-600 mb-1">Stima Completamento</div>
          <div className="text-sm text-gray-900">
            {getEstimatedCompletion() || 'Calcolando...'}
          </div>
        </div>
      </div>
      
      {/* Live URL being processed */}
      {status.current_url && status.status === 'discovering' && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-3">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
            <span className="text-sm text-primary-700 font-medium">Analizzando:</span>
          </div>
          <div className="text-sm font-mono text-primary-800 mt-1 break-all">
            {status.current_url}
          </div>
        </div>
      )}
    </motion.div>
  )
}