import { useScanStore } from '@stores/scanStore'
import { StepIndicator } from '@components/common/StepIndicator'

export function WorkflowHeader() {
  const { steps, currentStep, configuration } = useScanStore()
  const currentStepInfo = steps.find(step => step.id === currentStep)
  
  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {currentStepInfo?.title || 'Configurazione'}
            </h1>
            <p className="text-gray-600 mt-1">
              {currentStepInfo?.description || 'Imposta i parametri per la scansione'}
            </p>
            
            {/* Show URL if configured */}
            {configuration.url && currentStep > 1 && (
              <div className="mt-2 flex items-center text-sm text-gray-500">
                <span className="mr-2">Target:</span>
                <code className="bg-gray-100 px-2 py-1 rounded text-xs">
                  {configuration.url}
                </code>
              </div>
            )}
          </div>
          
          <div className="text-right">
            <div className="text-sm text-gray-500 mb-1">Progresso</div>
            <div className="text-lg font-semibold text-gray-900">
              {currentStep}/5
            </div>
          </div>
        </div>
        
        {/* Horizontal step indicator */}
        <div className="w-full">
          <StepIndicator 
            steps={steps} 
            currentStep={currentStep} 
            orientation="horizontal"
            showLabels={true}
          />
        </div>
      </div>
    </div>
  )
}