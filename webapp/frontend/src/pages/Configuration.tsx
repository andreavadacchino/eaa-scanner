import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import { validators } from '../services/apiClient';
import Layout from '../components/Layout';

const AVAILABLE_SCANNERS = [
  { id: 'pa11y', name: 'Pa11y', description: 'Scanner completo HTML5/ARIA', available: true },
  { id: 'axe', name: 'Axe-core', description: 'Scanner automatizzato aXe-core', available: true },
  { id: 'lighthouse', name: 'Lighthouse', description: 'Audit di accessibilità Google', available: true },
  { id: 'wave', name: 'WAVE', description: 'WebAIM Scanner (richiede API key)', available: false },
];

export default function Configuration() {
  const navigate = useNavigate();
  const { setConfig, goToStep } = useAppContext();
  
  const [formData, setFormData] = useState({
    url: '',
    company_name: '',
    email: '',
    scanners: ['pa11y', 'axe', 'lighthouse'], // Scanner di default
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validazione locale del form
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    // Validazione URL
    if (!formData.url) {
      newErrors.url = 'URL obbligatorio';
    } else if (!validators.isValidUrl(formData.url)) {
      newErrors.url = 'URL non valido';
    }
    
    // Validazione nome azienda
    if (!formData.company_name) {
      newErrors.company_name = 'Nome azienda obbligatorio';
    } else if (formData.company_name.length < 2) {
      newErrors.company_name = 'Nome azienda troppo corto';
    }
    
    // Validazione email
    if (!formData.email) {
      newErrors.email = 'Email obbligatoria';
    } else if (!validators.isValidEmail(formData.email)) {
      newErrors.email = 'Email non valida';
    }
    
    // Validazione scanner
    if (formData.scanners.length === 0) {
      newErrors.scanners = 'Seleziona almeno uno scanner';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Gestione cambio input
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Rimuovi errore quando l'utente modifica il campo
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  // Gestione selezione scanner
  const handleScannerToggle = (scannerId: string) => {
    setFormData(prev => {
      const isSelected = prev.scanners.includes(scannerId);
      const newScanners = isSelected
        ? prev.scanners.filter(id => id !== scannerId)
        : [...prev.scanners, scannerId];
      return { ...prev, scanners: newScanners };
    });
    // Rimuovi errore scanner
    if (errors.scanners) {
      setErrors(prev => ({ ...prev, scanners: '' }));
    }
  };

  // Submit del form
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      // Formatta l'URL correttamente
      const formattedUrl = validators.formatUrl(formData.url);
      
      // Salva la configurazione nel contesto
      setConfig({
        url: formattedUrl,
        company_name: formData.company_name,
        email: formData.email,
        scanners: formData.scanners,
      });
      
      // Vai al prossimo step (Discovery)
      goToStep(WorkflowStep.DISCOVERY);
      navigate('/discovery');
      
    } catch (error) {
      console.error('Errore configurazione:', error);
      setErrors({ 
        submit: error instanceof Error ? error.message : 'Errore durante la configurazione' 
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout
      title="Configurazione Scansione"
      subtitle="Configura i parametri per l'analisi di accessibilità del tuo sito web"
      currentStep={1}
      totalSteps={5}
    >
      <form onSubmit={handleSubmit} className="space-y-6 p-6">
        {/* URL del sito */}
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
            URL del sito web *
          </label>
          <input
            type="url"
            id="url"
            name="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://example.com"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.url ? 'border-red-500' : 'border-gray-300'
            }`}
            disabled={isSubmitting}
          />
          {errors.url && (
            <p className="mt-1 text-sm text-red-600">{errors.url}</p>
          )}
        </div>

        {/* Nome Azienda */}
        <div>
          <label htmlFor="company_name" className="block text-sm font-medium text-gray-700 mb-1">
            Nome Azienda *
          </label>
          <input
            type="text"
            id="company_name"
            name="company_name"
            value={formData.company_name}
            onChange={handleInputChange}
            placeholder="La tua azienda"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.company_name ? 'border-red-500' : 'border-gray-300'
            }`}
            disabled={isSubmitting}
          />
          {errors.company_name && (
            <p className="mt-1 text-sm text-red-600">{errors.company_name}</p>
          )}
        </div>

        {/* Email */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Indirizzo Email *
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            placeholder="email@example.com"
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.email ? 'border-red-500' : 'border-gray-300'
            }`}
            disabled={isSubmitting}
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email}</p>
          )}
        </div>

        {/* Scanner */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Scanner da utilizzare *
          </label>
          <div className="space-y-2">
            {AVAILABLE_SCANNERS.map(scanner => (
              <label
                key={scanner.id}
                className={`flex items-start p-3 border rounded-md cursor-pointer transition-colors ${
                  !scanner.available ? 'opacity-50 cursor-not-allowed bg-gray-50' : 
                  formData.scanners.includes(scanner.id) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={formData.scanners.includes(scanner.id)}
                  onChange={() => handleScannerToggle(scanner.id)}
                  disabled={!scanner.available || isSubmitting}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">
                    {scanner.name}
                    {!scanner.available && (
                      <span className="ml-2 text-xs text-red-600">(Non disponibile)</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">{scanner.description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.scanners && (
            <p className="mt-1 text-sm text-red-600">{errors.scanners}</p>
          )}
        </div>

        {/* Errore generale */}
        {errors.submit && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-800">{errors.submit}</p>
          </div>
        )}

        {/* Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <h3 className="text-sm font-medium text-blue-800 mb-1">
            Informazioni sul processo
          </h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Il crawler analizzerà il sito per trovare tutte le pagine pubbliche</li>
            <li>• Potrai selezionare quali pagine sottoporre a scansione</li>
            <li>• La scansione verificherà l'accessibilità secondo gli standard WCAG 2.1</li>
            <li>• Riceverai un report dettagliato con tutte le problematiche rilevate</li>
          </ul>
        </div>

        {/* Bottoni */}
        <div className="flex justify-end space-x-3 pt-4 border-t">
          <button
            type="submit"
            disabled={isSubmitting}
            className={`px-6 py-2 rounded-md font-medium transition-colors ${
              isSubmitting
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500'
            }`}
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Elaborazione...
              </span>
            ) : (
              'Avvia Discovery →'
            )}
          </button>
        </div>
      </form>
    </Layout>
  );
}