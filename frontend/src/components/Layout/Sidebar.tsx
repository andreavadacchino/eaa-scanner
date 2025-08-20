import { useScanStore } from '@stores/scanStore'
import { StepIndicator } from '@components/common/StepIndicator'
import { ScanProgress } from '@components/common/ScanProgress'
import { motion, AnimatePresence } from 'framer-motion'

export function Sidebar() {
  const { 
    currentStep, 
    steps, 
    discoveryStatus, 
    scanProgress, 
    selectedPages,
    discoveredPages 
  } = useScanStore()
  
  const showProgressInfo = currentStep >= 2
  
  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex-shrink-0">
      <div className="h-full flex flex-col">
        {/* Step indicator */}
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Progresso Workflow</h2>
          <StepIndicator steps={steps} currentStep={currentStep} />
        </div>
        
        {/* Dynamic content based on current step */}
        <div className="flex-1 overflow-auto p-6">
          <AnimatePresence mode="wait">
            {showProgressInfo && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Discovery info */}
                {currentStep >= 2 && (
                  <div className="space-y-3">
                    <h3 className="font-medium text-gray-900">Discovery Pagine</h3>
                    
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Pagine scoperte:</span>
                        <span className="font-medium text-gray-900">{discoveredPages.length}</span>
                      </div>
                      
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Stato:</span>
                        <span className={`font-medium capitalize ${
                          discoveryStatus.status === 'completed' ? 'text-success-600' :
                          discoveryStatus.status === 'discovering' ? 'text-primary-600' :
                          discoveryStatus.status === 'error' ? 'text-error-600' :
                          'text-gray-600'
                        }`}>
                          {discoveryStatus.status === 'discovering' ? 'In corso...' :
                           discoveryStatus.status === 'completed' ? 'Completato' :
                           discoveryStatus.status === 'error' ? 'Errore' :
                           'In attesa'}
                        </span>
                      </div>
                      
                      {discoveryStatus.status === 'discovering' && (
                        <div className="mt-3">
                          <div className="flex justify-between text-xs text-gray-500 mb-1">
                            <span>Progresso</span>
                            <span>{Math.round(discoveryStatus.progress)}%</span>
                          </div>
                          <div className="progress-bar">
                            <div 
                              className="progress-fill"
                              style={{ width: `${discoveryStatus.progress}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Selection info */}
                {currentStep >= 3 && discoveredPages.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-medium text-gray-900">Selezione Pagine</h3>
                    
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Selezionate:</span>
                        <span className="font-medium text-gray-900">
                          {selectedPages.length} / {discoveredPages.length}
                        </span>
                      </div>
                      
                      {selectedPages.length > 0 && (
                        <div className="mt-2">
                          <div className="text-xs text-gray-500 mb-1">Copertura</div>
                          <div className="progress-bar">
                            <div 
                              className="progress-fill bg-success-500"
                              style={{ width: `${(selectedPages.length / discoveredPages.length) * 100}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Scan progress */}
                {currentStep >= 4 && scanProgress && (
                  <div className="space-y-3">
                    <h3 className="font-medium text-gray-900">Scansione in Corso</h3>
                    <ScanProgress progress={scanProgress} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {/* Footer info */}
        <div className="p-6 border-t border-gray-100 bg-gray-50">
          <div className="text-xs text-gray-500 space-y-1">
            <div>EAA Scanner v1.0</div>
            <div>Conforme WCAG 2.2 AA</div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
              <span>Sistema operativo</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}