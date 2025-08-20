import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  CheckCircleIcon,
  XCircleIcon,
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  InformationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { PagesList } from '@components/common/PagesList'
import { SmartSelectionConfig, PageCategory, PageType } from '@types/index'
import toast from 'react-hot-toast'

export function SelectionStep() {
  const {
    discoveredPages,
    selectedPages,
    togglePageSelection,
    selectAllPages,
    selectNonePages,
    applySmartSelection,
    smartSelectionConfig,
    smartSelectionResult,
    updateStepStatus,
    isLoading
  } = useScanStore()
  
  const [showSmartConfig, setShowSmartConfig] = useState(false)
  const [localSmartConfig, setLocalSmartConfig] = useState<SmartSelectionConfig>(smartSelectionConfig)
  
  // Auto-complete step when pages are selected
  useEffect(() => {
    if (selectedPages.length > 0) {
      updateStepStatus(3, 'completed')
    } else {
      updateStepStatus(3, 'pending')
    }
  }, [selectedPages.length, updateStepStatus])
  
  const handleSmartSelection = async () => {
    try {
      await applySmartSelection(localSmartConfig)
      setShowSmartConfig(false)
      toast.success(`Selezionate ${selectedPages.length} pagine automaticamente`)
    } catch (error) {
      toast.error('Errore nella selezione automatica')
    }
  }
  
  const handleSelectByCategory = (category: PageCategory) => {
    const pagesInCategory = discoveredPages.filter(p => p.category === category)
    pagesInCategory.forEach(page => {
      if (!page.selected) {
        togglePageSelection(page.url)
      }
    })
    toast.success(`Selezionate ${pagesInCategory.length} pagine ${category}`)
  }
  
  const handleSelectByType = (type: PageType) => {
    const pagesOfType = discoveredPages.filter(p => p.page_type === type)
    pagesOfType.forEach(page => {
      if (!page.selected) {
        togglePageSelection(page.url)
      }
    })
    toast.success(`Selezionate ${pagesOfType.length} pagine di tipo ${type}`)
  }
  
  const getSelectionStats = () => {
    const stats = {
      total: selectedPages.length,
      byCategory: {
        critical: selectedPages.filter(p => p.category === PageCategory.CRITICAL).length,
        important: selectedPages.filter(p => p.category === PageCategory.IMPORTANT).length,
        representative: selectedPages.filter(p => p.category === PageCategory.REPRESENTATIVE).length,
        optional: selectedPages.filter(p => p.category === PageCategory.OPTIONAL).length
      },
      byType: {
        home: selectedPages.filter(p => p.page_type === PageType.HOME).length,
        category: selectedPages.filter(p => p.page_type === PageType.CATEGORY).length,
        product: selectedPages.filter(p => p.page_type === PageType.PRODUCT).length,
        content: selectedPages.filter(p => p.page_type === PageType.CONTENT).length,
        form: selectedPages.filter(p => p.page_type === PageType.FORM).length,
        media: selectedPages.filter(p => p.page_type === PageType.MEDIA).length,
        document: selectedPages.filter(p => p.page_type === PageType.DOCUMENT).length
      }
    }
    
    const estimatedTime = selectedPages.length * 2.5 // 2.5 min per page estimate
    const hours = Math.floor(estimatedTime / 60)
    const minutes = Math.ceil(estimatedTime % 60)
    
    return { ...stats, estimatedTime: { hours, minutes } }
  }
  
  const stats = getSelectionStats()
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      {/* Selection Controls */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Selezione Pagine per Scansione</h3>
            <p className="text-sm text-gray-500">
              Seleziona le pagine da analizzare per l'audit di accessibilità
            </p>
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-bold text-primary-600">{stats.total}</div>
            <div className="text-sm text-gray-500">pagine selezionate</div>
          </div>
        </div>
        
        {/* Quick Actions */}
        <div className="flex flex-wrap gap-3 mb-6">
          <button
            onClick={selectAllPages}
            className="btn-outline flex items-center"
          >
            <CheckCircleIcon className="h-4 w-4 mr-2" />
            Seleziona Tutto
          </button>
          
          <button
            onClick={selectNonePages}
            className="btn-outline flex items-center"
          >
            <XCircleIcon className="h-4 w-4 mr-2" />
            Deseleziona Tutto
          </button>
          
          <button
            onClick={() => setShowSmartConfig(true)}
            disabled={isLoading}
            className="btn-primary flex items-center"
          >
            <SparklesIcon className="h-4 w-4 mr-2" />
            Selezione Intelligente
          </button>
        </div>
        
        {/* Quick Selection by Category */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <button
            onClick={() => handleSelectByCategory(PageCategory.CRITICAL)}
            className="p-3 text-left border border-error-200 bg-error-50 rounded-lg hover:bg-error-100 transition-colors"
          >
            <div className="font-medium text-error-700">Critiche</div>
            <div className="text-sm text-error-600">
              {discoveredPages.filter(p => p.category === PageCategory.CRITICAL).length} pagine
            </div>
          </button>
          
          <button
            onClick={() => handleSelectByCategory(PageCategory.IMPORTANT)}
            className="p-3 text-left border border-warning-200 bg-warning-50 rounded-lg hover:bg-warning-100 transition-colors"
          >
            <div className="font-medium text-warning-700">Importanti</div>
            <div className="text-sm text-warning-600">
              {discoveredPages.filter(p => p.category === PageCategory.IMPORTANT).length} pagine
            </div>
          </button>
          
          <button
            onClick={() => handleSelectByType(PageType.FORM)}
            className="p-3 text-left border border-primary-200 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
          >
            <div className="font-medium text-primary-700">Form</div>
            <div className="text-sm text-primary-600">
              {discoveredPages.filter(p => p.page_type === PageType.FORM).length} pagine
            </div>
          </button>
          
          <button
            onClick={() => handleSelectByType(PageType.HOME)}
            className="p-3 text-left border border-success-200 bg-success-50 rounded-lg hover:bg-success-100 transition-colors"
          >
            <div className="font-medium text-success-700">Homepage</div>
            <div className="text-sm text-success-600">
              {discoveredPages.filter(p => p.page_type === PageType.HOME).length} pagine
            </div>
          </button>
        </div>
        
        {/* Selection Statistics */}
        {stats.total > 0 && (
          <div className="bg-primary-50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-primary-900 mb-3">Riepilogo Selezione</h4>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="space-y-1">
                <div className="text-primary-700 font-medium">Per Categoria</div>
                <div className="space-y-0.5 text-primary-600">
                  {stats.byCategory.critical > 0 && <div>Critiche: {stats.byCategory.critical}</div>}
                  {stats.byCategory.important > 0 && <div>Importanti: {stats.byCategory.important}</div>}
                  {stats.byCategory.representative > 0 && <div>Rappresentative: {stats.byCategory.representative}</div>}
                  {stats.byCategory.optional > 0 && <div>Opzionali: {stats.byCategory.optional}</div>}
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="text-primary-700 font-medium">Per Tipo</div>
                <div className="space-y-0.5 text-primary-600">
                  {stats.byType.home > 0 && <div>Homepage: {stats.byType.home}</div>}
                  {stats.byType.form > 0 && <div>Form: {stats.byType.form}</div>}
                  {stats.byType.category > 0 && <div>Categorie: {stats.byType.category}</div>}
                  {stats.byType.content > 0 && <div>Contenuti: {stats.byType.content}</div>}
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="text-primary-700 font-medium">Stima Tempi</div>
                <div className="text-primary-600">
                  {stats.estimatedTime.hours > 0 ? (
                    <div>{stats.estimatedTime.hours}h {stats.estimatedTime.minutes}m</div>
                  ) : (
                    <div>{stats.estimatedTime.minutes} minuti</div>
                  )}
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="text-primary-700 font-medium">Copertura</div>
                <div className="text-primary-600">
                  {Math.round((stats.total / discoveredPages.length) * 100)}% del sito
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Smart Selection Results */}
      {smartSelectionResult && (
        <div className="card bg-success-50 border-success-200">
          <div className="card-header">
            <div className="flex items-center">
              <SparklesIcon className="h-6 w-6 text-success-600 mr-3" />
              <div>
                <h3 className="text-lg font-medium text-success-900">Risultati Selezione Intelligente</h3>
                <p className="text-sm text-success-700">Selezione ottimizzata basata su metodologia WCAG-EM</p>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-success-700 font-medium">Copertura Stimata</div>
                <div className="text-success-900 text-lg font-semibold">
                  {Math.round(smartSelectionResult.coverage_analysis.estimated_wcag_coverage)}%
                </div>
              </div>
              
              <div>
                <div className="text-success-700 font-medium">Tipologie Coperte</div>
                <div className="text-success-900">
                  {smartSelectionResult.coverage_analysis.page_types_covered.length} di {Object.keys(PageType).length}
                </div>
              </div>
              
              <div>
                <div className="text-success-700 font-medium">Template Coperti</div>
                <div className="text-success-900">
                  {smartSelectionResult.coverage_analysis.template_groups_covered.length} gruppi
                </div>
              </div>
            </div>
            
            {/* Rationale Summary */}
            <div className="bg-white rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Criteri di Selezione</h4>
              <div className="space-y-1 text-xs text-gray-600">
                {smartSelectionResult.rationale.slice(0, 3).map((item, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <div className="w-1 h-1 bg-gray-400 rounded-full" />
                    <span>{item.reason} (Score: {item.score.toFixed(1)})</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Pages Selection List */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Lista Pagine</h3>
          <span className="text-sm text-gray-500">
            {discoveredPages.length} pagine disponibili
          </span>
        </div>
        
        <PagesList
          pages={discoveredPages}
          showSelection={true}
          showMetadata={true}
          onPageSelect={togglePageSelection}
          maxHeight="600px"
        />
      </div>
      
      {/* Smart Selection Configuration Modal */}
      {showSmartConfig && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <AdjustmentsHorizontalIcon className="h-6 w-6 text-primary-600 mr-3" />
                  <h3 className="text-lg font-medium text-gray-900">Configurazione Selezione Intelligente</h3>
                </div>
                <button
                  onClick={() => setShowSmartConfig(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>
              
              <div className="space-y-6">
                {/* Strategy Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Strategia di Selezione</label>
                  <select
                    value={localSmartConfig.strategy}
                    onChange={(e) => setLocalSmartConfig(prev => ({ ...prev, strategy: e.target.value as any }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="wcag_em">WCAG-EM (Raccomandato)</option>
                    <option value="risk_based">Basata su Rischio</option>
                    <option value="coverage_optimal">Copertura Ottimale</option>
                    <option value="user_journey">Journey Utente</option>
                  </select>
                </div>
                
                {/* Max Pages */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Numero Massimo Pagine: {localSmartConfig.max_pages}
                  </label>
                  <input
                    type="range"
                    min="5"
                    max="50"
                    value={localSmartConfig.max_pages}
                    onChange={(e) => setLocalSmartConfig(prev => ({ ...prev, max_pages: parseInt(e.target.value) }))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>5 pagine</span>
                    <span>50 pagine</span>
                  </div>
                </div>
                
                {/* Options */}
                <div className="space-y-3">
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={localSmartConfig.include_critical}
                      onChange={(e) => setLocalSmartConfig(prev => ({ ...prev, include_critical: e.target.checked }))}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <div>
                      <div className="text-sm font-medium text-gray-900">Includi tutte le pagine critiche</div>
                      <div className="text-xs text-gray-500">Seleziona automaticamente pagine con alta priorità</div>
                    </div>
                  </label>
                  
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={localSmartConfig.balance_templates}
                      onChange={(e) => setLocalSmartConfig(prev => ({ ...prev, balance_templates: e.target.checked }))}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <div>
                      <div className="text-sm font-medium text-gray-900">Bilancia template</div>
                      <div className="text-xs text-gray-500">Assicura copertura equilibrata dei tipi di pagina</div>
                    </div>
                  </label>
                  
                  <label className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      checked={localSmartConfig.prioritize_complex}
                      onChange={(e) => setLocalSmartConfig(prev => ({ ...prev, prioritize_complex: e.target.checked }))}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <div>
                      <div className="text-sm font-medium text-gray-900">Priorità a pagine complesse</div>
                      <div className="text-xs text-gray-500">Seleziona pagine con maggiore complessità</div>
                    </div>
                  </label>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex justify-end space-x-3 mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={() => setShowSmartConfig(false)}
                  className="btn-outline"
                >
                  Annulla
                </button>
                <button
                  onClick={handleSmartSelection}
                  disabled={isLoading}
                  className="btn-primary flex items-center"
                >
                  {isLoading && <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />}
                  Applica Selezione
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
      
      {/* Guidelines */}
      {stats.total === 0 && (
        <div className="card bg-primary-50 border-primary-200">
          <div className="flex items-start">
            <InformationCircleIcon className="h-6 w-6 text-primary-600 flex-shrink-0 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-primary-800">Linee Guida per la Selezione</h3>
              <div className="text-sm text-primary-700 mt-2 space-y-1">
                <p>• <strong>Homepage</strong>: Sempre inclusa per l'analisi iniziale</p>
                <p>• <strong>Pagine critiche</strong>: Funzionalità core e processi business</p>
                <p>• <strong>Form</strong>: Essenziali per l'accessibilità delle interazioni</p>
                <p>• <strong>Template diversi</strong>: Assicura copertura completa del sito</p>
                <p>• <strong>5-15 pagine</strong>: Numero ottimale per audit completo</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  )
}