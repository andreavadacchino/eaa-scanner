import React from 'react';
import { useAppContext } from '../contexts/AppContext';

interface LayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  currentStep?: number;
  totalSteps?: number;
}

const STEPS = [
  { id: 0, name: 'Configurazione', description: 'Impostazioni base' },
  { id: 1, name: 'Discovery', description: 'Ricerca pagine' },
  { id: 2, name: 'Selezione', description: 'Scelta pagine' },
  { id: 3, name: 'Scansione', description: 'Analisi in corso' },
  { id: 4, name: 'Report', description: 'Risultati' },
];

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  title, 
  subtitle,
  currentStep: propCurrentStep,
  totalSteps = 5
}) => {
  const { currentStep: contextStep } = useAppContext();
  const currentStep = propCurrentStep !== undefined ? propCurrentStep : contextStep;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                EAA Scanner
              </h1>
              <p className="text-sm text-gray-600">
                Sistema di analisi accessibilità web
              </p>
            </div>
            
            {/* Progress Indicator */}
            <div className="hidden sm:flex items-center space-x-2">
              {STEPS.map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <div className={`
                    flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium
                    ${currentStep === step.id 
                      ? 'bg-primary text-white' 
                      : currentStep > step.id 
                        ? 'bg-success text-white'
                        : 'bg-gray-200 text-gray-600'
                    }
                  `}>
                    {currentStep > step.id ? (
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      step.id + 1
                    )}
                  </div>
                  {index < STEPS.length - 1 && (
                    <div className={`
                      w-12 h-0.5 mx-2
                      ${currentStep > step.id ? 'bg-success' : 'bg-gray-200'}
                    `} />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Step indicator mobile */}
      <div className="sm:hidden bg-white border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {STEPS[currentStep]?.name}
            </h2>
            <p className="text-sm text-gray-600">
              Passo {currentStep + 1} di {STEPS.length}
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-primary">
              {Math.round(((currentStep + 1) / STEPS.length) * 100)}%
            </div>
            <div className="w-20 bg-gray-200 rounded-full h-2 mt-1">
              <div 
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="mb-6">
          <h2 className="text-3xl font-bold text-gray-900">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-2 text-lg text-gray-600">
              {subtitle}
            </p>
          )}
        </div>
        
        <div className="bg-white rounded-eaa shadow-eaa-md">
          {children}
        </div>
      </main>
    </div>
  );
};

export default Layout;
