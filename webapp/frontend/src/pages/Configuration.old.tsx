import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { useScanContext, useStepNavigation } from '../contexts/ScanContext';
import { apiService, formatUrl, validateUrl, validateEmail } from '../services/api';
import { ScanRequest, ScannerConfig } from '../types';

export const Configuration: React.FC = () => {
  const navigate = useNavigate();
  const { setConfig } = useScanContext();
  const { goToNextStep } = useStepNavigation();
  
  const [formData, setFormData] = useState({
    url: '',
    company_name: '',
    email: '',
  });
  
  const [scannerConfig, setScannerConfig] = useState<ScannerConfig>({
    pa11y: true,
    axe: true,
    lighthouse: true,
    wave: false, // Disabilitato di default
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Rimuovi errore quando l'utente inizia a digitare
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleScannerChange = (scanner: keyof ScannerConfig) => {
    setScannerConfig(prev => ({ ...prev, [scanner]: !prev[scanner] }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Valida URL
    if (!formData.url.trim()) {
      newErrors.url = 'URL è obbligatorio';
    } else if (!validateUrl(formData.url)) {
      newErrors.url = 'Inserisci un URL valido (es. https://example.com)';
    }

    // Valida nome azienda
    if (!formData.company_name.trim()) {
      newErrors.company_name = 'Nome azienda è obbligatorio';
    } else if (formData.company_name.length < 2) {
      newErrors.company_name = 'Nome azienda deve essere almeno 2 caratteri';
    }

    // Valida email
    if (!formData.email.trim()) {
      newErrors.email = 'Email è obbligatoria';
    } else if (!validateEmail(formData.email)) {
      newErrors.email = 'Inserisci un indirizzo email valido';
    }

    // Valida che almeno uno scanner sia selezionato
    const selectedScanners = Object.values(scannerConfig).filter(Boolean);
    if (selectedScanners.length === 0) {
      newErrors.scanners = 'Seleziona almeno uno scanner';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const formattedUrl = formatUrl(formData.url);
      
      // Converti scannerConfig in array di stringhe per il backend
      const scanners = Object.entries(scannerConfig)
        .filter(([_, enabled]) => enabled)
        .map(([scanner]) => scanner);
      
      const config: ScanRequest = {
        url: formattedUrl,
        company_name: formData.company_name.trim(),
        email: formData.email.trim(),
        scanners, // Usa array di stringhe invece di oggetto
        simulate: false,
      };

      // Valida la configurazione con il backend
      const validation = await apiService.validateScanRequest(config);
      
      if (!validation.valid) {
        setErrors({ submit: validation.errors?.join(', ') || 'Errore di validazione' });
        return;
      }

      // Salva la configurazione nel context
      setConfig(config);
      
      // Procedi al passo successivo
      goToNextStep();
      navigate('/discovery');
      
    } catch (error) {
      console.error('Errore validazione:', error);
      setErrors({ 
        submit: error instanceof Error ? error.message : 'Errore durante la validazione' 
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Layout 
      title="Configurazione Scansione"
      subtitle="Configura i parametri per l'analisi di accessibilità del tuo sito web"
    >
      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* URL */}
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
            URL del sito web *
          </label>
          <input
            type="url"
            id="url"
            name="url"
            value={formData.url}
            onChange={handleInputChange}
            placeholder="https://example.com"
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
              ${errors.url ? 'border-danger' : 'border-gray-300'}
            `}
            disabled={isSubmitting}
          />
          {errors.url && (
            <p className="mt-1 text-sm text-danger">{errors.url}</p>
          )}
        </div>

        {/* Nome Azienda */}
        <div>
          <label htmlFor="company_name" className="block text-sm font-medium text-gray-700 mb-2">
            Nome Azienda *
          </label>
          <input
            type="text"
            id="company_name"
            name="company_name"
            value={formData.company_name}
            onChange={handleInputChange}
            placeholder="La tua azienda"
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
              ${errors.company_name ? 'border-danger' : 'border-gray-300'}
            `}
            disabled={isSubmitting}
          />
          {errors.company_name && (
            <p className="mt-1 text-sm text-danger">{errors.company_name}</p>
          )}
        </div>

        {/* Email */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Indirizzo Email *
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            placeholder="email@example.com"
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
              ${errors.email ? 'border-danger' : 'border-gray-300'}
            `}
            disabled={isSubmitting}
          />
          {errors.email && (
            <p className="mt-1 text-sm text-danger">{errors.email}</p>
          )}
        </div>

        {/* Scanner Selection */}
        <div>
          <fieldset>
            <legend className="block text-sm font-medium text-gray-700 mb-3">
              Scanner da utilizzare *
            </legend>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(scannerConfig).map(([scanner, enabled]) => (
                <label
                  key={scanner}
                  className={`
                    relative flex items-center p-3 border rounded-md cursor-pointer
                    ${enabled ? 'border-primary bg-primary/5' : 'border-gray-300'}
                    ${isSubmitting ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary/50'}
                  `}
                >
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={() => handleScannerChange(scanner as keyof ScannerConfig)}
                    disabled={isSubmitting}
                    className="sr-only"
                  />
                  <div className={`
                    flex-shrink-0 w-4 h-4 border-2 rounded mr-3
                    ${enabled ? 'border-primary bg-primary' : 'border-gray-300'}
                  `}>
                    {enabled && (
                      <svg className="w-full h-full text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900 capitalize">
                      {scanner}
                    </div>
                    <div className="text-sm text-gray-500">
                      {scanner === 'pa11y' && 'Scanner completo HTML5/ARIA'}
                      {scanner === 'axe' && 'Scanner automatizzato aXe-core'}
                      {scanner === 'lighthouse' && 'Audit di accessibilità Google'}
                      {scanner === 'wave' && 'WAVE WebAIM (richiede API key)'}
                    </div>
                  </div>
                </label>
              ))}
            </div>
            {errors.scanners && (
              <p className="mt-2 text-sm text-danger">{errors.scanners}</p>
            )}
          </fieldset>
        </div>

        {/* Errori di submit */}
        {errors.submit && (
          <div className="bg-danger/10 border border-danger/20 rounded-md p-4">
            <div className="text-sm text-danger">{errors.submit}</div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end pt-4 border-t">
          <button
            type="submit"
            disabled={isSubmitting}
            className={`
              px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2
              ${isSubmitting 
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed' 
                : 'bg-primary text-white hover:bg-primary-700 focus:ring-primary'
              }
            `}
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500 inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Validazione...
              </>
            ) : (
              'Avvia Discovery'
            )}
          </button>
        </div>
      </form>
    </Layout>
  );
};

export default Configuration;
