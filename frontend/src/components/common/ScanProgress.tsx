import { ClockIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline'
import { ScanProgress as ScanProgressType, ScanPhase } from '@types/index'
import { motion } from 'framer-motion'

interface ScanProgressProps {
  progress: ScanProgressType
}

export function ScanProgress({ progress }: ScanProgressProps) {
  const formatDuration = (start?: Date) => {
    if (!start) return '00:00'
    const now = new Date()
    const diff = Math.floor((now.getTime() - start.getTime()) / 1000)
    const minutes = Math.floor(diff / 60)
    const seconds = diff % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }
  
  const getPhaseText = (phase: ScanPhase) => {
    switch (phase) {
      case ScanPhase.INITIALIZING:
        return 'Inizializzazione'
      case ScanPhase.SCANNING_PAGES:
        return 'Scansione pagine'
      case ScanPhase.PROCESSING_RESULTS:
        return 'Elaborazione risultati'
      case ScanPhase.GENERATING_REPORT:
        return 'Generazione report'
      case ScanPhase.FINALIZING:
        return 'Finalizzazione'
      default:
        return 'In elaborazione'
    }
  }
  
  const getEstimatedCompletion = () => {
    if (!progress.start_time || progress.overall_progress === 0) return null
    
    const elapsed = new Date().getTime() - progress.start_time.getTime()
    const estimatedTotal = (elapsed / progress.overall_progress) * 100
    const remaining = estimatedTotal - elapsed
    
    const remainingMinutes = Math.ceil(remaining / (1000 * 60))
    return remainingMinutes > 0 ? `≈ ${remainingMinutes} min rimanenti` : 'Quasi completato'
  }
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-4"
    >
      {/* Main Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600">Progresso Scansione</span>
          <span className="font-medium text-gray-900">{Math.round(progress.overall_progress)}%</span>
        </div>
        
        <div className="progress-bar h-3">
          <motion.div 
            className="progress-fill h-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress.overall_progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        
        <div className="flex justify-between text-xs text-gray-500">
          <span>Fase: {getPhaseText(progress.current_phase)}</span>
          <span>{getEstimatedCompletion()}</span>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="text-gray-600 mb-1">Pagine</div>
          <div className="text-lg font-semibold text-gray-900">
            {progress.pages_completed}/{progress.pages_total}
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="text-gray-600 mb-1">Durata</div>
          <div className="text-lg font-semibold text-gray-900">
            {formatDuration(progress.start_time)}
          </div>
        </div>
        
        <div className="bg-white rounded-lg p-3 border border-gray-100">
          <div className="text-gray-600 mb-1">Stato</div>
          <div className={`text-sm font-medium capitalize ${
            progress.status === 'completed' ? 'text-success-600' :
            progress.status === 'error' ? 'text-error-600' :
            'text-primary-600'
          }`}>
            {progress.status === 'scanning' ? 'In corso' :
             progress.status === 'completed' ? 'Completato' :
             progress.status === 'error' ? 'Errore' :
             progress.status}
          </div>
        </div>
      </div>
      
      {/* Scanner Status */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Stato Scanner</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(progress.scanner_status).map(([scanner, status]) => {
            const getStatusIcon = () => {
              switch (status.status) {
                case 'completed':
                  return <CheckCircleIcon className="h-4 w-4 text-success-500" />
                case 'error':
                  return <ExclamationCircleIcon className="h-4 w-4 text-error-500" />
                case 'running':
                  return <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                default:
                  return <div className="w-4 h-4 bg-gray-300 rounded-full" />
              }
            }
            
            return (
              <div key={scanner} className="flex items-center space-x-2 text-sm">
                {getStatusIcon()}
                <span className="capitalize font-medium">{scanner}</span>
                <span className="text-gray-500">({status.pages_processed})</span>
              </div>
            )
          })}
        </div>
      </div>
      
      {/* Page Progress Detail */}
      {progress.page_progress.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Dettaglio Pagine</h4>
          <div className="space-y-2 max-h-32 overflow-y-auto scrollbar-thin">
            {progress.page_progress.map((pageProgress) => (
              <div key={pageProgress.url} className="flex items-center justify-between text-xs">
                <span className="truncate flex-1 mr-2 font-mono">
                  {pageProgress.url.split('/').pop() || 'Homepage'}
                </span>
                <div className="flex items-center space-x-2">
                  <div className={`px-2 py-1 rounded text-xs ${
                    pageProgress.status === 'completed' ? 'bg-success-100 text-success-700' :
                    pageProgress.status === 'scanning' ? 'bg-primary-100 text-primary-700' :
                    pageProgress.status === 'error' ? 'bg-error-100 text-error-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {pageProgress.status === 'scanning' ? 'Scansione' :
                     pageProgress.status === 'completed' ? 'Completata' :
                     pageProgress.status === 'error' ? 'Errore' :
                     'In attesa'}
                  </div>
                  {pageProgress.issues_found !== undefined && (
                    <span className="text-gray-600">{pageProgress.issues_found} issues</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Error Display */}
      {progress.error_message && (
        <div className="bg-error-50 border border-error-200 rounded-lg p-4">
          <div className="flex items-start">
            <ExclamationCircleIcon className="h-5 w-5 text-error-500 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-error-800">Errore durante la scansione</h3>
              <p className="text-sm text-error-700 mt-1">{progress.error_message}</p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}