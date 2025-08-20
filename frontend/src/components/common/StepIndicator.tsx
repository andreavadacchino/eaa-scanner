import { CheckIcon } from '@heroicons/react/24/solid'
import { WorkflowStep } from '@types/index'
import { motion } from 'framer-motion'

interface StepIndicatorProps {
  steps: WorkflowStep[]
  currentStep: number
  orientation?: 'horizontal' | 'vertical'
  showLabels?: boolean
}

export function StepIndicator({ 
  steps, 
  currentStep, 
  orientation = 'vertical', 
  showLabels = false 
}: StepIndicatorProps) {
  
  if (orientation === 'horizontal') {
    return (
      <div className="flex items-center justify-between w-full">
        {steps.map((step, index) => {
          const isActive = step.id === currentStep
          const isCompleted = step.status === 'completed'
          const isError = step.status === 'error'
          const isPast = step.id < currentStep
          
          return (
            <div key={step.id} className="flex items-center flex-1">
              <div className="flex flex-col items-center flex-1">
                {/* Step Circle */}
                <motion.div
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={`relative flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-300 ${
                    isCompleted || isPast
                      ? 'bg-success-600 border-success-600'
                      : isActive
                      ? 'bg-primary-600 border-primary-600'
                      : isError
                      ? 'bg-error-600 border-error-600'
                      : 'bg-white border-gray-300'
                  }`}
                >
                  {(isCompleted || isPast) ? (
                    <CheckIcon className="h-4 w-4 text-white" />
                  ) : (
                    <span className={`text-sm font-medium ${
                      isActive ? 'text-white' : 
                      isError ? 'text-white' :
                      'text-gray-500'
                    }`}>
                      {step.id}
                    </span>
                  )}
                  
                  {/* Active indicator */}
                  {isActive && !isCompleted && (
                    <div className="absolute -inset-1 rounded-full border-2 border-primary-200 animate-pulse" />
                  )}
                </motion.div>
                
                {/* Step Label */}
                {showLabels && (
                  <div className="mt-2 text-center">
                    <p className={`text-sm font-medium ${
                      isActive ? 'text-primary-600' :
                      isCompleted || isPast ? 'text-success-600' :
                      isError ? 'text-error-600' :
                      'text-gray-500'
                    }`}>
                      {step.title}
                    </p>
                    {isActive && (
                      <p className="text-xs text-gray-500 mt-1">
                        {step.description}
                      </p>
                    )}
                  </div>
                )}
              </div>
              
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className={`flex-1 h-0.5 mx-4 transition-all duration-300 ${
                  step.id < currentStep || isCompleted
                    ? 'bg-success-600'
                    : 'bg-gray-300'
                }`} />
              )}
            </div>
          )
        })}
      </div>
    )
  }
  
  // Vertical orientation
  return (
    <div className="space-y-4">
      {steps.map((step) => {
        const isActive = step.id === currentStep
        const isCompleted = step.status === 'completed'
        const isError = step.status === 'error'
        const isPast = step.id < currentStep
        
        return (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: step.id * 0.1 }}
            className="flex items-start"
          >
            {/* Step Circle */}
            <div className={`relative flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300 ${
              isCompleted || isPast
                ? 'bg-success-600 border-success-600'
                : isActive
                ? 'bg-primary-600 border-primary-600'
                : isError
                ? 'bg-error-600 border-error-600'
                : 'bg-white border-gray-300'
            }`}>
              {(isCompleted || isPast) ? (
                <CheckIcon className="h-4 w-4 text-white" />
              ) : (
                <span className={`text-sm font-medium ${
                  isActive ? 'text-white' : 
                  isError ? 'text-white' :
                  'text-gray-500'
                }`}>
                  {step.id}
                </span>
              )}
              
              {/* Active indicator */}
              {isActive && !isCompleted && (
                <div className="absolute -inset-1 rounded-full border-2 border-primary-200 animate-pulse" />
              )}
            </div>
            
            {/* Step Content */}
            <div className="ml-3 min-w-0 flex-1">
              <p className={`text-sm font-medium ${
                isActive ? 'text-primary-600' :
                isCompleted || isPast ? 'text-success-600' :
                isError ? 'text-error-600' :
                'text-gray-500'
              }`}>
                {step.title}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {step.description}
              </p>
              
              {/* Status indicators */}
              {isError && (
                <p className="text-xs text-error-600 mt-1 font-medium">
                  Errore - Riprova
                </p>
              )}
              {isActive && !isError && (
                <p className="text-xs text-primary-600 mt-1 font-medium">
                  In corso...
                </p>
              )}
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}