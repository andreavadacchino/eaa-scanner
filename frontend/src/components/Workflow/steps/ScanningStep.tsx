import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  PlayIcon,
  StopIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { useWebSocket } from '@services/websocket'
import { apiClient } from '@services/api'
import { ScanProgress } from '@components/common/ScanProgress'
import { ScanPhase } from '@types/index'
import toast from 'react-hot-toast'

export function ScanningStep() {
  const {
    configuration,
    selectedPages,
    scanProgress,
    setScanProgress,
    setScanResults,
    updateStepStatus,
    setError
  } = useScanStore()
  
  const webSocket = useWebSocket()
  const [scanId, setScanId] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  
  // Setup WebSocket event handlers for scan updates
  useEffect(() => {
    const handleScanUpdate = (data: any) => {
      setScanProgress(data.progress)
      
      // Show progress notifications
      if (data.progress.current_phase === ScanPhase.SCANNING_PAGES) {
        const completed = data.progress.pages_completed
        const total = data.progress.pages_total
        if (completed > 0 && completed % 3 === 0) { // Every 3 pages
          toast.success(`Completate ${completed}/${total} pagine`)
        }
      }
    }
    
    const handleScanComplete = (data: any) => {
      setScanResults(data.results)
      updateStepStatus(4, 'completed')
      toast.success('Scansione completata con successo!')
    }
    
    const handleError = (data: any) => {
      setError(data.message)
      updateStepStatus(4, 'error')
    }
    
    // Register event handlers
    webSocket.on('scan_update', handleScanUpdate)
    webSocket.on('scan_complete', handleScanComplete)
    webSocket.on('error', handleError)
    
    // Join scan room if we have a scanId
    if (scanId && webSocket.isConnected()) {
      webSocket.joinScanRoom(scanId)
    }
    
    return () => {
      webSocket.off('scan_update', handleScanUpdate)
      webSocket.off('scan_complete', handleScanComplete)
      webSocket.off('error', handleError)
      
      if (scanId) {
        webSocket.leaveScanRoom(scanId)
      }
    }
  }, [scanId, webSocket, setScanProgress, setScanResults, updateStepStatus, setError])
  
  const startScan = async () => {
    if (!configuration.url || selectedPages.length === 0) {
      toast.error('Configurazione o selezione pagine mancante')
      return
    }
    
    setIsStarting(true)
    try {
      const result = await apiClient.startScan(configuration as any, selectedPages)
      
      setScanId(result.scan_id)
      setScanProgress({
        scan_id: result.scan_id,
        status: 'starting',
        overall_progress: 0,
        current_phase: ScanPhase.INITIALIZING,
        pages_total: selectedPages.length,
        pages_completed: 0,
        page_progress: selectedPages.map(page => ({
          url: page.url,
          status: 'queued',
          progress: 0,
          scanner_results: {
            pa11y: 'pending',
            axe: 'pending',
            lighthouse: 'pending',
            ...(configuration.scanners?.wave && { wave: 'pending' })
          }
        })),
        scanner_status: {
          pa11y: { status: 'idle', progress: 0, pages_processed: 0, issues_found: 0 },
          axe: { status: 'idle', progress: 0, pages_processed: 0, issues_found: 0 },
          lighthouse: { status: 'idle', progress: 0, pages_processed: 0, issues_found: 0 },
          ...(configuration.scanners?.wave && {
            wave: { status: 'idle', progress: 0, pages_processed: 0, issues_found: 0 }
          })
        },
        start_time: new Date()
      })
      
      // Join scan room for real-time updates
      if (webSocket.isConnected()) {
        webSocket.joinScanRoom(result.scan_id)
      }
      
      toast.success('Scansione avviata')
      
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Errore avvio scansione'
      setError(message)
      toast.error(message)
      updateStepStatus(4, 'error')
    } finally {
      setIsStarting(false)
    }
  }
  
  const stopScan = async () => {
    if (!scanId) return
    
    try {
      await apiClient.stopScan(scanId)
      setScanProgress(prev => prev ? {
        ...prev,
        status: 'completed',
        current_phase: ScanPhase.FINALIZING
      } : null)
      
      if (webSocket.isConnected()) {
        webSocket.leaveScanRoom(scanId)
      }
      
      toast.success('Scansione interrotta')
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Errore interruzione scansione')
    }
  }
  
  const getStatusIcon = () => {
    if (!scanProgress) return <DocumentTextIcon className="h-6 w-6 text-gray-400" />
    
    switch (scanProgress.status) {
      case 'scanning':
      case 'processing':
        return <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
      case 'completed':
        return <CheckCircleIcon className="h-6 w-6 text-success-500" />
      case 'error':
        return <ExclamationTriangleIcon className="h-6 w-6 text-error-500" />
      default:
        return <ClockIcon className="h-6 w-6 text-warning-500" />
    }
  }
  
  const getStatusText = () => {
    if (!scanProgress) return 'Pronto per iniziare'
    
    switch (scanProgress.status) {
      case 'starting':
        return 'Inizializzazione in corso...'
      case 'scanning':
        return `Scansione in corso - ${scanProgress.pages_completed}/${scanProgress.pages_total} pagine`
      case 'processing':
        return 'Elaborazione risultati...'
      case 'completed':
        return 'Scansione completata con successo'
      case 'error':
        return 'Errore durante la scansione'
      default:
        return 'Stato sconosciuto'
    }
  }
  
  const canStart = () => {
    return !scanProgress || scanProgress.status === 'idle' || scanProgress.status === 'error'
  }
  
  const canStop = () => {
    return scanProgress && ['starting', 'scanning', 'processing'].includes(scanProgress.status)
  }
  
  const getScannerCount = () => {
    const scanners = configuration.scanners
    if (!scanners) return 0
    return Object.values(scanners).filter(Boolean).length
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto space-y-6"
    >
      {/* Header Card with Controls */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            {getStatusIcon()}
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Scansione Accessibilità</h3>
              <p className="text-sm text-gray-500">{getStatusText()}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {canStart() && (
              <button
                onClick={startScan}
                disabled={isStarting || selectedPages.length === 0}
                className="btn-primary flex items-center"
              >
                <PlayIcon className="h-4 w-4 mr-2" />
                {isStarting ? 'Avvio...' : 'Avvia Scansione'}
              </button>
            )}
            
            {canStop() && (
              <button
                onClick={stopScan}
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
          <h4 className="text-sm font-medium text-gray-900 mb-3">Configurazione Scansione</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Pagine selezionate:</span>
              <div className="font-medium text-gray-900">{selectedPages.length}</div>
            </div>
            <div>
              <span className="text-gray-500">Scanner attivi:</span>
              <div className="font-medium text-gray-900">{getScannerCount()}</div>
            </div>
            <div>
              <span className="text-gray-500">Modalità:</span>
              <div className="font-medium text-gray-900 capitalize">
                {configuration.methodology?.analysis_depth || 'Standard'}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Tempo stimato:</span>
              <div className="font-medium text-gray-900">
                {Math.ceil(selectedPages.length * 2.5)} min
              </div>
            </div>
          </div>
        </div>
        
        {/* Active Scanners Display */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {configuration.scanners?.pa11y && (
            <div className="flex items-center p-3 bg-primary-50 border border-primary-200 rounded-lg">
              <div className="w-3 h-3 bg-primary-500 rounded-full mr-3" />
              <span className="text-sm font-medium text-primary-700">Pa11y</span>
            </div>
          )}
          {configuration.scanners?.axe && (
            <div className="flex items-center p-3 bg-success-50 border border-success-200 rounded-lg">
              <div className="w-3 h-3 bg-success-500 rounded-full mr-3" />
              <span className="text-sm font-medium text-success-700">Axe-core</span>
            </div>
          )}
          {configuration.scanners?.lighthouse && (
            <div className="flex items-center p-3 bg-warning-50 border border-warning-200 rounded-lg">
              <div className="w-3 h-3 bg-warning-500 rounded-full mr-3" />
              <span className="text-sm font-medium text-warning-700">Lighthouse</span>
            </div>
          )}
          {configuration.scanners?.wave && (
            <div className="flex items-center p-3 bg-error-50 border border-error-200 rounded-lg">
              <div className="w-3 h-3 bg-error-500 rounded-full mr-3" />
              <span className="text-sm font-medium text-error-700">WAVE</span>
            </div>
          )}
        </div>
      </div>
      
      {/* Progress Display */}
      {scanProgress && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Progresso Scansione</h3>
            <span className="text-sm text-gray-500">ID: {scanProgress.scan_id}</span>
          </div>
          
          <ScanProgress progress={scanProgress} />
        </div>
      )}
      
      {/* Error Display */}
      {scanProgress?.status === 'error' && scanProgress.error_message && (
        <div className="card border-error-200 bg-error-50">
          <div className="flex items-start">
            <ExclamationTriangleIcon className="h-6 w-6 text-error-500 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-error-800">Errore durante la Scansione</h3>
              <p className="text-sm text-error-700 mt-1">{scanProgress.error_message}</p>
              <div className="mt-3">
                <button
                  onClick={startScan}
                  disabled={isStarting}
                  className="text-sm bg-error-100 hover:bg-error-200 text-error-800 font-medium px-3 py-2 rounded transition-colors"
                >
                  Riprova Scansione
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Pre-scan Info */}
      {!scanProgress && (
        <div className="card bg-primary-50 border-primary-200">
          <div className="flex items-start">
            <ClockIcon className="h-6 w-6 text-primary-600 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-primary-800">Informazioni sulla Scansione</h3>
              <div className="text-sm text-primary-700 mt-2 space-y-1">
                <p>• La scansione analizza ogni pagina con {getScannerCount()} scanner diversi</p>
                <p>• Tempo stimato: circa 2-3 minuti per pagina</p>
                <p>• Risultati vengono aggiornati in tempo reale</p>
                <p>• Puoi interrompere la scansione in qualsiasi momento</p>
                <p>• I risultati parziali vengono salvati automaticamente</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}