import { Link, useLocation } from 'react-router-dom'
import { MagnifyingGlassIcon, ClockIcon, Cog6ToothIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { ConnectionStatus } from '@components/common/ConnectionStatus'

export function Header() {
  const location = useLocation()
  const { currentStep, steps } = useScanStore()
  
  const navigation = [
    { name: 'Nuova Scansione', href: '/', icon: MagnifyingGlassIcon, current: location.pathname === '/' },
    { name: 'Cronologia', href: '/history', icon: ClockIcon, current: location.pathname === '/history' },
    { name: 'Impostazioni', href: '/settings', icon: Cog6ToothIcon, current: location.pathname === '/settings' },
    { name: 'Aiuto', href: '/help', icon: QuestionMarkCircleIcon, current: location.pathname === '/help' }
  ]
  
  const currentStepInfo = steps.find(step => step.id === currentStep)
  
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo e titolo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <MagnifyingGlassIcon className="w-5 h-5 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">EAA Scanner</h1>
                <p className="text-xs text-gray-500">Sistema di Analisi Accessibilità</p>
              </div>
            </Link>
          </div>
          
          {/* Status workflow (solo se siamo nella pagina principale) */}
          {location.pathname === '/' && currentStepInfo && (
            <div className="hidden md:flex items-center space-x-2 text-sm">
              <span className="text-gray-500">Fase corrente:</span>
              <span className="font-medium text-gray-900">{currentStepInfo.title}</span>
              <div className={`w-2 h-2 rounded-full ${
                currentStepInfo.status === 'active' ? 'bg-primary-500 animate-pulse' :
                currentStepInfo.status === 'completed' ? 'bg-success-500' :
                currentStepInfo.status === 'error' ? 'bg-error-500' :
                'bg-gray-300'
              }`} />
            </div>
          )}
          
          {/* Navigazione e connection status */}
          <div className="flex items-center space-x-4">
            <nav className="hidden md:flex space-x-1">
              {navigation.map((item) => {
                const IconComponent = item.icon
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      item.current
                        ? 'bg-primary-50 text-primary-600'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <IconComponent className="w-4 h-4 mr-2" />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
            
            <ConnectionStatus />
          </div>
        </div>
      </div>
    </header>
  )
}