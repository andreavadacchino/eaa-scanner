import { Cog6ToothIcon } from '@heroicons/react/24/outline'

export function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Impostazioni</h1>
        <p className="text-gray-600 mt-2">Configura le preferenze del sistema</p>
      </div>
      
      <div className="card text-center py-16">
        <Cog6ToothIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Impostazioni Sistema</h3>
        <p className="text-gray-500 mb-6">Qui potrai configurare le impostazioni avanzate</p>
        <p className="text-sm text-gray-400">Funzionalità in sviluppo...</p>
      </div>
    </div>
  )
}