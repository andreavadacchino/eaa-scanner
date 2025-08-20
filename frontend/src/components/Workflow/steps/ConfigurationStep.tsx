import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { motion } from 'framer-motion'
import { 
  GlobeAltIcon, 
  BuildingOfficeIcon, 
  EnvelopeIcon,
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { apiClient } from '@services/api'
import { ScanConfiguration } from '@types/index'
import toast from 'react-hot-toast'

interface ConfigurationFormData {
  url: string
  company_name: string
  email: string
  wave_enabled: boolean
  pa11y_enabled: boolean
  axe_enabled: boolean
  lighthouse_enabled: boolean
  max_pages: number
  max_depth: number
  sample_methodology: 'manual' | 'wcag_em' | 'smart' | 'comprehensive'
  analysis_depth: 'quick' | 'standard' | 'thorough' | 'comprehensive'
}

export function ConfigurationStep() {
  const { configuration, setConfiguration, updateStepStatus, setError } = useScanStore()
  const [isValidatingUrl, setIsValidatingUrl] = useState(false)
  const [urlValidation, setUrlValidation] = useState<{
    valid: boolean
    accessible: boolean
    redirect_url?: string
    error?: string
  } | null>(null)
  
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid, isSubmitting }
  } = useForm<ConfigurationFormData>({
    defaultValues: {
      url: configuration.url || '',
      company_name: configuration.company_name || '',
      email: configuration.email || '',
      wave_enabled: configuration.scanners?.wave || false,
      pa11y_enabled: configuration.scanners?.pa11y || true,
      axe_enabled: configuration.scanners?.axe || true,
      lighthouse_enabled: configuration.scanners?.lighthouse || true,
      max_pages: configuration.crawler?.max_pages || 50,
      max_depth: configuration.crawler?.max_depth || 3,
      sample_methodology: configuration.methodology?.sample_methodology || 'wcag_em',
      analysis_depth: configuration.methodology?.analysis_depth || 'standard'
    },
    mode: 'onChange'
  })
  
  const watchedUrl = watch('url')
  
  // Validate URL when it changes
  useEffect(() => {
    const validateUrl = async (url: string) => {
      if (!url || url.length < 10) {
        setUrlValidation(null)
        return
      }
      
      setIsValidatingUrl(true)
      try {
        const result = await apiClient.validateUrl(url)
        setUrlValidation(result)
        
        if (!result.valid) {
          toast.error('URL non valido')
        } else if (!result.accessible) {
          toast.error('Sito non raggiungibile')
        }
      } catch (error) {
        setUrlValidation({ valid: false, accessible: false, error: 'Errore di validazione' })
      } finally {
        setIsValidatingUrl(false)
      }
    }
    
    const debounceTimer = setTimeout(() => {
      if (watchedUrl) {
        validateUrl(watchedUrl)
      }
    }, 1000)
    
    return () => clearTimeout(debounceTimer)
  }, [watchedUrl])
  
  const onSubmit = async (data: ConfigurationFormData) => {
    try {
      const config: Partial<ScanConfiguration> = {
        url: data.url,
        company_name: data.company_name,
        email: data.email,
        scanners: {
          wave: data.wave_enabled,
          pa11y: data.pa11y_enabled,
          axe: data.axe_enabled,
          lighthouse: data.lighthouse_enabled
        },
        methodology: {
          sample_methodology: data.sample_methodology,
          analysis_depth: data.analysis_depth,
          max_pages: data.max_pages,
          include_pdfs: false,
          smart_selection: true
        },
        crawler: {
          max_pages: data.max_pages,
          max_depth: data.max_depth,
          follow_external: false,
          timeout_ms: 30000,
          use_playwright: true
        }
      }
      
      setConfiguration(config)
      updateStepStatus(1, 'completed')
      toast.success('Configurazione salvata con successo')
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Errore nella configurazione')
    }
  }
  
  const getUrlValidationIcon = () => {
    if (isValidatingUrl) {
      return <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600" />
    }
    if (!urlValidation) return null
    
    if (urlValidation.valid && urlValidation.accessible) {
      return <CheckCircleIcon className="h-5 w-5 text-success-500" />
    }
    return <ExclamationTriangleIcon className="h-5 w-5 text-warning-500" />
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-4xl mx-auto"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
        {/* URL e informazioni di base */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <GlobeAltIcon className="h-6 w-6 text-primary-600 mr-3" />
              <div>
                <h3 className="text-lg font-medium text-gray-900">Sito Web da Analizzare</h3>
                <p className="text-sm text-gray-500">Inserisci l'URL del sito e le informazioni aziendali</p>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                URL del sito web *
              </label>
              <div className="relative">
                <input
                  type="url"
                  {...register('url', {
                    required: 'URL obbligatorio',
                    pattern: {
                      value: /^https?:\/\/.+/,
                      message: 'URL deve iniziare con http:// o https://'
                    }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 pr-10"
                  placeholder="https://esempio.com"
                />
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  {getUrlValidationIcon()}
                </div>
              </div>
              {errors.url && (
                <p className="mt-1 text-sm text-error-600">{errors.url.message}</p>
              )}
              {urlValidation && !urlValidation.valid && (
                <p className="mt-1 text-sm text-warning-600">{urlValidation.error}</p>
              )}
              {urlValidation?.redirect_url && (
                <p className="mt-1 text-sm text-primary-600">
                  Redirect rilevato: {urlValidation.redirect_url}
                </p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <BuildingOfficeIcon className="h-4 w-4 inline mr-1" />
                Nome Azienda *
              </label>
              <input
                type="text"
                {...register('company_name', { required: 'Nome azienda obbligatorio' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="ACME S.r.l."
              />
              {errors.company_name && (
                <p className="mt-1 text-sm text-error-600">{errors.company_name.message}</p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <EnvelopeIcon className="h-4 w-4 inline mr-1" />
                Email di contatto *
              </label>
              <input
                type="email"
                {...register('email', {
                  required: 'Email obbligatoria',
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: 'Email non valida'
                  }
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="email@azienda.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-error-600">{errors.email.message}</p>
              )}
            </div>
          </div>
        </div>
        
        {/* Scanner Configuration */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center">
              <Cog6ToothIcon className="h-6 w-6 text-primary-600 mr-3" />
              <div>
                <h3 className="text-lg font-medium text-gray-900">Scanner di Accessibilità</h3>
                <p className="text-sm text-gray-500">Seleziona gli strumenti di analisi da utilizzare</p>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                {...register('pa11y_enabled')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-900">Pa11y</span>
                <p className="text-xs text-gray-500">Scanner CLI per test automatici WCAG</p>
              </div>
              <span className="badge-success">Consigliato</span>
            </label>
            
            <label className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                {...register('axe_enabled')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-900">Axe-core</span>
                <p className="text-xs text-gray-500">Motore di test accessibilità di Deque</p>
              </div>
              <span className="badge-success">Consigliato</span>
            </label>
            
            <label className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                {...register('lighthouse_enabled')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-900">Lighthouse</span>
                <p className="text-xs text-gray-500">Audit di Google per performance e accessibilità</p>
              </div>
            </label>
            
            <label className="flex items-center space-x-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                {...register('wave_enabled')}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-900">WAVE</span>
                <p className="text-xs text-gray-500">Web Accessibility Evaluation Tool</p>
              </div>
              <span className="badge-warning">API Key</span>
            </label>
          </div>
        </div>
        
        {/* Advanced Configuration */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Configurazione Avanzata</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Metodologia di campionamento
              </label>
              <select
                {...register('sample_methodology')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="wcag_em">WCAG-EM (Raccomandato)</option>
                <option value="smart">Selezione Intelligente</option>
                <option value="comprehensive">Analisi Completa</option>
                <option value="manual">Selezione Manuale</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Profondità di analisi
              </label>
              <select
                {...register('analysis_depth')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="quick">Veloce (5-10 min)</option>
                <option value="standard">Standard (15-30 min)</option>
                <option value="thorough">Approfondita (30-60 min)</option>
                <option value="comprehensive">Completa (60+ min)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Massimo pagine da scoprire
              </label>
              <input
                type="number"
                {...register('max_pages', { min: 1, max: 1000 })}
                min="1"
                max="1000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Profondità di crawling
              </label>
              <input
                type="number"
                {...register('max_depth', { min: 1, max: 10 })}
                min="1"
                max="10"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
        </div>
        
        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!isValid || isSubmitting || isValidatingUrl}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed px-8 py-3 text-base"
          >
            {isSubmitting ? 'Salvataggio...' : 'Salva Configurazione'}
          </button>
        </div>
      </form>
    </motion.div>
  )
}