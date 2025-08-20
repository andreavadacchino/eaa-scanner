import { ArrowLeftIcon, ArrowRightIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { useNavigate } from 'react-router-dom'

export function WorkflowNavigation() {
  const { 
    currentStep, 
    setCurrentStep, 
    steps, 
    resetScan,
    discoveryStatus,
    selectedPages,
    scanProgress,
    isLoading
  } = useScanStore()
  
  const navigate = useNavigate()
  const currentStepInfo = steps.find(step => step.id === currentStep)
  
  // Determine if we can proceed to next step
  const canProceed = () => {
    switch (currentStep) {
      case 1: // Configuration
        return currentStepInfo?.status === 'completed'
      case 2: // Discovery
        return discoveryStatus.status === 'completed'
      case 3: // Selection
        return selectedPages.length > 0
      case 4: // Scanning
        return scanProgress?.status === 'completed'
      case 5: // Results
        return false // No next step
      default:
        return false
    }
  }
  
  const canGoBack = () => {
    // Can't go back during active operations
    if (discoveryStatus.status === 'discovering' || scanProgress?.status === 'scanning') {
      return false
    }
    return currentStep > 1
  }
  
  const handleNext = () => {
    if (canProceed() && currentStep < 5) {
      setCurrentStep(currentStep + 1)
    }
  }
  
  const handleBack = () => {
    if (canGoBack()) {
      setCurrentStep(currentStep - 1)
    }
  }
  
  const handleCancel = () => {
    resetScan()
    navigate('/')
  }
  
  const getNextButtonText = () => {
    switch (currentStep) {
      case 1:
        return 'Avvia Discovery'
      case 2:
        return 'Seleziona Pagine'
      case 3:
        return 'Avvia Scansione'
      case 4:
        return 'Visualizza Risultati'
      default:
        return 'Avanti'
    }
  }
  
  return (
    <div className="bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          {/* Left side - Back and Cancel */}
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={handleBack}
              disabled={!canGoBack() || isLoading}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowLeftIcon className="w-4 h-4 mr-2" />
              Indietro
            </button>
            
            <button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XMarkIcon className="w-4 h-4 mr-2" />
              Annulla
            </button>
          </div>
          
          {/* Center - Step info */}
          <div className="text-center">
            <div className="text-sm text-gray-500">
              Fase {currentStep} di 5: {currentStepInfo?.title}
            </div>
            
            {/* Show loading state */}
            {isLoading && (
              <div className="flex items-center justify-center mt-1">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600" />
                <span className="ml-2 text-xs text-gray-600">Elaborazione...</span>
              </div>
            )}
          </div>
          
          {/* Right side - Next */}
          <div>
            {currentStep < 5 ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={!canProceed() || isLoading}
                className="flex items-center px-6 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {getNextButtonText()}
                <ArrowRightIcon className="w-4 h-4 ml-2" />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => navigate('/history')}
                className="flex items-center px-6 py-2 text-sm font-medium text-white bg-success-600 border border-transparent rounded-md hover:bg-success-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success-500"
              >
                Vai alla Cronologia
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}