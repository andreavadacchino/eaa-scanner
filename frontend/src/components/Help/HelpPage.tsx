import { QuestionMarkCircleIcon } from '@heroicons/react/24/outline'

export function HelpPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Aiuto e Documentazione</h1>
        <p className="text-gray-600 mt-2">Guide e risorse per l'utilizzo del sistema</p>
      </div>
      
      <div className="card text-center py-16">
        <QuestionMarkCircleIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Centro Aiuto</h3>
        <p className="text-gray-500 mb-6">Guide, tutorial e FAQ per l'utilizzo del scanner EAA</p>
        <p className="text-sm text-gray-400">Funzionalità in sviluppo...</p>
      </div>
    </div>
  )
}