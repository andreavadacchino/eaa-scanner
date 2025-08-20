import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  MagnifyingGlassIcon, 
  PlayIcon,
  StopIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { useWebSocket } from '@services/websocket'
import { apiClient } from '@services/api'
import { DiscoveredPage, PageType, PageCategory, Priority } from '@types/index'
import { DiscoveryProgress } from '@components/common/DiscoveryProgress'
import { PagesList } from '@components/common/PagesList'
import toast from 'react-hot-toast'

export function DiscoveryStep() {
  const {
    configuration,
    discoveryStatus,
    discoveredPages,
    setDiscoveryStatus,
    addDiscoveredPage,
    updateDiscoveredPages,
    updateStepStatus,
    setError
  } = useScanStore()
  
  const webSocket = useWebSocket()
  const [discoveryId, setDiscoveryId] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  
  // Setup WebSocket event handlers
  useEffect(() => {
    const handleDiscoveryUpdate = (data: any) => {
      if (data.status) {
        setDiscoveryStatus({
          ...discoveryStatus,
          ...data.status
        })
      }
      
      if (data.discovered_pages) {
        updateDiscoveredPages(data.discovered_pages)
      }
      
      if (data.new_page) {
        addDiscoveredPage(data.new_page)
      }
    }
    
    webSocket.on('discovery_update', handleDiscoveryUpdate)
    
    return () => {
      webSocket.off('discovery_update', handleDiscoveryUpdate)
    }
  }, [webSocket, discoveryStatus, setDiscoveryStatus, updateDiscoveredPages, addDiscoveredPage])
  
  // Auto-complete step when discovery finishes
  useEffect(() => {
    if (discoveryStatus.status === 'completed' && discoveredPages.length > 0) {
      updateStepStatus(2, 'completed')
      toast.success(`Scoperte ${discoveredPages.length} pagine`)
    }
  }, [discoveryStatus.status, discoveredPages.length, updateStepStatus])
  
  const startDiscovery = async () => {
    if (!configuration.url || !configuration.crawler) return
    
    setIsStarting(true)
    try {
      const result = await apiClient.startDiscovery({
        url: configuration.url,
        crawler: configuration.crawler
      })
      
      setDiscoveryId(result.discovery_id)
      setDiscoveryStatus({
        status: 'discovering',
        progress: 0,
        discovered_count: 0,
        start_time: new Date()
      })
      
      // Join discovery room for real-time updates
      if (webSocket.isConnected()) {
        webSocket.joinDiscoveryRoom(result.discovery_id)
      }
      
      toast.success('Discovery avviato')
      
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Errore avvio discovery'
      setError(message)
      setDiscoveryStatus({
        ...discoveryStatus,
        status: 'error',
        error_message: message
      })
    } finally {
      setIsStarting(false)
    }
  }
  
  const stopDiscovery = async () => {
    if (!discoveryId) return
    
    try {
      await apiClient.stopDiscovery(discoveryId)
      setDiscoveryStatus({
        ...discoveryStatus,
        status: 'completed'
      })
      
      if (webSocket.isConnected()) {
        webSocket.leaveDiscoveryRoom(discoveryId)
      }
      
      toast.success('Discovery interrotto')
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Errore interruzione discovery')
    }
  }
  
  const getStatusIcon = () => {
    switch (discoveryStatus.status) {
      case 'discovering':
        return <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-success-500" />
      case 'error':
        return <ExclamationTriangleIcon className="h-6 w-6 text-error-500" />
      default:
        return <MagnifyingGlassIcon className="h-6 w-6 text-gray-400" />
    }
  }
  
  const getStatusText = () => {
    switch (discoveryStatus.status) {
      case 'discovering':
        return 'Scansione in corso...'
      case 'completed':
        return `Completato - ${discoveredPages.length} pagine trovate`
      case 'error':
        return 'Errore durante la scansione'
      default:
        return 'Pronto per iniziare'
    }
  }
  
  const canStart = () => {
    return discoveryStatus.status === 'idle' && 
           configuration.url && 
           !isStarting
  }
  
  const canStop = () => {
    return discoveryStatus.status === 'discovering'
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      {/* Header Card with Controls */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            {getStatusIcon()}
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Discovery Pagine del Sito</h3>
              <p className="text-sm text-gray-500">{getStatusText()}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {canStart() && (
              <button
                onClick={startDiscovery}
                disabled={isStarting}
                className="btn-primary flex items-center"
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                {isStarting ? 'Avvio...' : 'Avvia Discovery'}
              </button>
            )}
            
            {canStop() && (
              <button
                onClick={stopDiscovery}
                className="btn-secondary flex items-center"
              >
                <StopIcon className="h-4 w-4 mr-2" />
                Interrompi
              </button>
            )}
          </div>
        </div>
        
        {/* Configuration Summary */}
        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Configurazione Discovery</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">URL base:</span>
              <div className="font-mono text-xs bg-white px-2 py-1 rounded mt-1 truncate">
                {configuration.url}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Max pagine:</span>
              <div className="font-medium text-gray-900">{configuration.crawler?.max_pages}</div>
            </div>
            <div>
              <span className="text-gray-500">Profondità:</span>
              <div className="font-medium text-gray-900">{configuration.crawler?.max_depth} livelli</div>
            </div>
            <div>
              <span className="text-gray-500">Timeout:</span>
              <div className="font-medium text-gray-900">{(configuration.crawler?.timeout_ms || 30000) / 1000}s</div>
            </div>
          </div>
        </div>
        
        {/* Progress Display */}
        {discoveryStatus.status !== 'idle' && (
          <DiscoveryProgress 
            status={discoveryStatus}
            totalDiscovered={discoveredPages.length}
          />
        )}
      </div>
      
      {/* Error Display */}
      {discoveryStatus.status === 'error' && discoveryStatus.error_message && (
        <div className="card border-error-200 bg-error-50">
          <div className="flex items-start">
            <ExclamationTriangleIcon className="h-6 w-6 text-error-500 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-error-800">Errore durante il Discovery</h3>
              <p className="text-sm text-error-700 mt-1">{discoveryStatus.error_message}</p>
              <div className="mt-3">
                <button
                  onClick={startDiscovery}
                  disabled={isStarting}
                  className="text-sm bg-error-100 hover:bg-error-200 text-error-800 font-medium px-3 py-2 rounded transition-colors"
                >
                  Riprova Discovery
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Results Display */}
      {discoveredPages.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="text-lg font-medium text-gray-900">Pagine Scoperte</h3>
              <p className="text-sm text-gray-500">
                {discoveredPages.length} pagine trovate - 
                <span className="text-primary-600 font-medium">pronto per la selezione</span>
              </p>
            </div>
            
            {/* Quick Stats */}
            <div className="flex items-center space-x-4 text-sm">
              <div className="text-center">
                <div className="font-semibold text-gray-900">{discoveredPages.filter(p => p.category === PageCategory.CRITICAL).length}</div>
                <div className="text-gray-500">Critiche</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-gray-900">{discoveredPages.filter(p => p.category === PageCategory.IMPORTANT).length}</div>
                <div className="text-gray-500">Importanti</div>
              </div>
              <div className="text-center">
                <div className="font-semibold text-gray-900">{discoveredPages.filter(p => p.page_type === PageType.FORM).length}</div>
                <div className="text-gray-500">Form</div>
              </div>
            </div>
          </div>
          
          <PagesList 
            pages={discoveredPages}
            showSelection={false}
            showMetadata={true}
            maxHeight="400px"
          />
        </div>
      )}
      
      {/* Tips for Discovery */}
      {discoveryStatus.status === 'idle' && (
        <div className="card bg-primary-50 border-primary-200">
          <div className="flex items-start">
            <ClockIcon className="h-6 w-6 text-primary-600 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-primary-800">Suggerimenti per il Discovery</h3>
              <div className="text-sm text-primary-700 mt-2 space-y-1">
                <p>• Il processo può richiedere alcuni minuti a seconda della dimensione del sito</p>
                <p>• Verranno analizzate automaticamente struttura e tipologie di pagine</p>
                <p>• Puoi interrompere il processo in qualsiasi momento</p>
                <p>• Solo pagine pubblicamente accessibili verranno scoperte</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}