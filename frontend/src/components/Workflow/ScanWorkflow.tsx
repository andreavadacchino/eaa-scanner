import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useScanStore } from '@stores/scanStore'
import { useWebSocket } from '@services/websocket'

// Step Components
import { ConfigurationStep } from './steps/ConfigurationStep'
import { DiscoveryStep } from './steps/DiscoveryStep'
import { SelectionStep } from './steps/SelectionStep'
import { ScanningStep } from './steps/ScanningStep'
import { ResultsStep } from './steps/ResultsStep'

// Common Components
import { WorkflowHeader } from './WorkflowHeader'
import { WorkflowNavigation } from './WorkflowNavigation'

export function ScanWorkflow() {
  const { scanId } = useParams<{ scanId?: string }>()
  const navigate = useNavigate()
  const { currentStep, setCurrentStep, resetScan, setScanProgress, setScanResults, setError } = useScanStore()
  const webSocket = useWebSocket()
  
  // Initialize WebSocket event handlers
  useEffect(() => {
    const handleScanUpdate = (data: any) => {
      setScanProgress(data.progress)
    }
    
    const handleScanComplete = (data: any) => {
      setScanResults(data.results)
      setCurrentStep(5) // Move to results step
      navigate(`/scan/${data.scan_id}`, { replace: true })
    }
    
    const handleError = (data: any) => {
      setError(data.message)
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
  }, [scanId, webSocket, setScanProgress, setScanResults, setCurrentStep, setError, navigate])
  
  // Reset workflow when navigating to root without scanId
  useEffect(() => {
    if (!scanId && currentStep > 1) {
      resetScan()
    }
  }, [scanId, currentStep, resetScan])
  
  const renderCurrentStep = () => {
    switch (currentStep) {
      case 1:
        return <ConfigurationStep />
      case 2:
        return <DiscoveryStep />
      case 3:
        return <SelectionStep />
      case 4:
        return <ScanningStep />
      case 5:
        return <ResultsStep />
      default:
        return <ConfigurationStep />
    }
  }
  
  return (
    <div className="h-full flex flex-col">
      {/* Workflow Header */}
      <WorkflowHeader />
      
      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              {renderCurrentStep()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
      
      {/* Navigation Footer */}
      <WorkflowNavigation />
    </div>
  )
}