import { ClockIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

export function ScanHistory() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Cronologia Scansioni</h1>
        <p className="text-gray-600 mt-2">Visualizza e gestisci le scansioni precedenti</p>
      </div>
      
      <div className="card text-center py-16">
        <ClockIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Cronologia Scansioni</h3>
        <p className="text-gray-500 mb-6">Qui potrai visualizzare tutte le scansioni precedenti</p>
        <p className="text-sm text-gray-400">Funzionalità in sviluppo...</p>
      </div>
    </div>
  )
}