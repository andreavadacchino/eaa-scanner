import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  DocumentTextIcon,
  ArrowDownTrayIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon,
  EyeIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline'
import { useScanStore } from '@stores/scanStore'
import { apiClient } from '@services/api'
import { Issue, ComplianceAssessment } from '@types/index'
import toast from 'react-hot-toast'

export function ResultsStep() {
  const { scanResults, configuration } = useScanStore()
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false)
  const [selectedIssueType, setSelectedIssueType] = useState<'all' | 'Critical' | 'High' | 'Medium' | 'Low'>('all')
  const [selectedWcagLevel, setSelectedWcagLevel] = useState<'all' | 'A' | 'AA' | 'AAA'>('all')
  
  if (!scanResults) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <DocumentTextIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Nessun Risultato Disponibile</h3>
          <p className="text-gray-500">Completa la scansione per visualizzare i risultati</p>
        </div>
      </div>
    )
  }
  
  const generatePdf = async () => {
    setIsGeneratingPdf(true)
    try {
      const result = await apiClient.generatePdfReport(scanResults.scan_id)
      toast.success('Report PDF generato con successo')
      
      // Scarica automaticamente
      window.open(result.pdf_url, '_blank')
      
    } catch (error) {
      toast.error('Errore nella generazione del PDF')
    } finally {
      setIsGeneratingPdf(false)
    }
  }
  
  const downloadReport = async (format: 'html' | 'pdf' | 'json' | 'csv') => {
    try {
      const blob = await apiClient.downloadReport(scanResults.scan_id, format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `eaa-report-${scanResults.scan_id}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast.success(`Report ${format.toUpperCase()} scaricato`)
      
    } catch (error) {
      toast.error(`Errore download report ${format.toUpperCase()}`)
    }
  }
  
  const openHtmlReport = () => {
    if (scanResults.report_urls.html) {
      window.open(scanResults.report_urls.html, '_blank')
    }
  }
  
  const getComplianceColor = (level: string) => {
    switch (level) {
      case 'conforme':
        return 'text-success-600'
      case 'parzialmente_conforme':
        return 'text-warning-600'
      case 'non_conforme':
        return 'text-error-600'
      default:
        return 'text-gray-600'
    }
  }
  
  const getComplianceIcon = (level: string) => {
    switch (level) {
      case 'conforme':
        return <CheckCircleIcon className="h-6 w-6 text-success-500" />
      case 'parzialmente_conforme':
        return <ExclamationTriangleIcon className="h-6 w-6 text-warning-500" />
      case 'non_conforme':
        return <XCircleIcon className="h-6 w-6 text-error-500" />
      default:
        return <InformationCircleIcon className="h-6 w-6 text-gray-500" />
    }
  }
  
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'Critical':
        return 'text-error-600 bg-error-50 border-error-200'
      case 'High':
        return 'text-error-500 bg-error-50 border-error-100'
      case 'Medium':
        return 'text-warning-600 bg-warning-50 border-warning-200'
      case 'Low':
        return 'text-gray-600 bg-gray-50 border-gray-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }
  
  // Filter issues based on selected filters
  const filteredIssues = scanResults.issues.filter(issue => {
    const severityMatch = selectedIssueType === 'all' || issue.severity === selectedIssueType
    const wcagMatch = selectedWcagLevel === 'all' || issue.wcag_level === selectedWcagLevel
    return severityMatch && wcagMatch
  })
  
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }
  
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-6xl mx-auto space-y-6"
    >
      {/* Header Summary */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center">
            {getComplianceIcon(scanResults.compliance.overall_level)}
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Risultati Scansione Completata</h3>
              <p className={`text-sm ${getComplianceColor(scanResults.compliance.overall_level)}`}>
                Livello conformità: <span className="font-medium capitalize">{scanResults.compliance.overall_level.replace('_', ' ')}</span>
              </p>
            </div>
          </div>
          
          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={openHtmlReport}
              className="btn-outline flex items-center"
            >
              <EyeIcon className="h-4 w-4 mr-2" />
              Visualizza Report
            </button>
            
            <button
              onClick={generatePdf}
              disabled={isGeneratingPdf}
              className="btn-primary flex items-center"
            >
              {isGeneratingPdf ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
              ) : (
                <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
              )}
              {isGeneratingPdf ? 'Generazione...' : 'Scarica PDF'}
            </button>
          </div>
        </div>
        
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-primary-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-primary-600">{scanResults.summary.total_pages}</div>
            <div className="text-sm text-primary-700">Pagine Analizzate</div>
          </div>
          
          <div className="bg-error-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-error-600">{scanResults.summary.total_issues}</div>
            <div className="text-sm text-error-700">Problemi Trovati</div>
          </div>
          
          <div className="bg-success-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-success-600">{Math.round(scanResults.compliance.wcag_aa_score)}%</div>
            <div className="text-sm text-success-700">Score WCAG AA</div>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-gray-600">{formatDuration(scanResults.metadata.duration)}</div>
            <div className="text-sm text-gray-700">Durata Scansione</div>
          </div>
        </div>
        
        {/* Compliance Status */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Stato Conformità EAA</h4>
          <div className="flex items-center justify-between">
            <div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                scanResults.compliance.eaa_compliance ? 'bg-success-100 text-success-700' : 'bg-error-100 text-error-700'
              }`}>
                {scanResults.compliance.eaa_compliance ? 'Conforme EAA' : 'Non Conforme EAA'}
              </span>
              
              {scanResults.compliance.critical_issues > 0 && (
                <span className="ml-3 text-sm text-error-600">
                  {scanResults.compliance.critical_issues} problemi critici da risolvere
                </span>
              )}
            </div>
            
            <div className="text-sm text-gray-500">
              Scanner utilizzati: {scanResults.metadata.scanners_used.join(', ')}
            </div>
          </div>
        </div>
      </div>
      
      {/* Issues by Severity Breakdown */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Distribuzione Problemi per Severità</h3>
          <ChartBarIcon className="h-5 w-5 text-gray-400" />
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(scanResults.summary.issues_by_severity).map(([severity, count]) => (
            <div key={severity} className={`p-4 rounded-lg border ${getSeverityColor(severity)}`}>
              <div className="text-2xl font-bold">{count}</div>
              <div className="text-sm font-medium">{severity}</div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Issues List */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Problemi di Accessibilità</h3>
          
          {/* Filters */}
          <div className="flex items-center space-x-4">
            <select
              value={selectedIssueType}
              onChange={(e) => setSelectedIssueType(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-3 py-1"
            >
              <option value="all">Tutte le severità</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
            
            <select
              value={selectedWcagLevel}
              onChange={(e) => setSelectedWcagLevel(e.target.value as any)}
              className="text-sm border border-gray-300 rounded px-3 py-1"
            >
              <option value="all">Tutti i livelli WCAG</option>
              <option value="A">WCAG A</option>
              <option value="AA">WCAG AA</option>
              <option value="AAA">WCAG AAA</option>
            </select>
          </div>
        </div>
        
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredIssues.length > 0 ? (
            filteredIssues.map((issue, index) => (
              <motion.div
                key={`${issue.id}-${index}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.05 }}
                className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                        {issue.severity}
                      </span>
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-primary-50 text-primary-700">
                        WCAG {issue.wcag_level}
                      </span>
                      <span className="text-xs text-gray-500">
                        {issue.source_scanner}
                      </span>
                    </div>
                    
                    <h4 className="text-sm font-medium text-gray-900 mb-1">
                      {issue.title}
                    </h4>
                    
                    <p className="text-sm text-gray-600 mb-2">
                      {issue.description}
                    </p>
                    
                    <div className="text-xs text-gray-500 space-y-1">
                      <div>WCAG: {issue.wcag_criterion}</div>
                      <div>Pagina: <span className="font-mono">{issue.page_url}</span></div>
                      {issue.selector && (
                        <div>Selettore: <span className="font-mono">{issue.selector}</span></div>
                      )}
                    </div>
                  </div>
                  
                  <div className="ml-4">
                    {issue.help_url && (
                      <a
                        href={issue.help_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:text-primary-800 text-xs"
                      >
                        Aiuto
                      </a>
                    )}
                  </div>
                </div>
                
                {issue.recommendation && (
                  <div className="mt-3 p-3 bg-primary-50 rounded border-l-4 border-primary-400">
                    <div className="text-xs font-medium text-primary-800 mb-1">Raccomandazione:</div>
                    <div className="text-xs text-primary-700">{issue.recommendation}</div>
                  </div>
                )}
              </motion.div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-500">
              <ExclamationTriangleIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Nessun problema trovato con i filtri selezionati</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Download Options */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Download Report</h3>
          <ArrowDownTrayIcon className="h-5 w-5 text-gray-400" />
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button
            onClick={() => downloadReport('html')}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
          >
            <DocumentTextIcon className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <div className="text-sm font-medium">HTML</div>
            <div className="text-xs text-gray-500">Report completo</div>
          </button>
          
          <button
            onClick={() => downloadReport('pdf')}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
          >
            <DocumentArrowDownIcon className="h-8 w-8 mx-auto mb-2 text-error-500" />
            <div className="text-sm font-medium">PDF</div>
            <div className="text-xs text-gray-500">Per stampa/email</div>
          </button>
          
          <button
            onClick={() => downloadReport('json')}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
          >
            <div className="text-2xl mx-auto mb-2">{'{}'}</div>
            <div className="text-sm font-medium">JSON</div>
            <div className="text-xs text-gray-500">Dati strutturati</div>
          </button>
          
          <button
            onClick={() => downloadReport('csv')}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-center"
          >
            <ChartBarIcon className="h-8 w-8 mx-auto mb-2 text-success-500" />
            <div className="text-sm font-medium">CSV</div>
            <div className="text-xs text-gray-500">Per Excel</div>
          </button>
        </div>
      </div>
      
      {/* Scan Metadata */}
      <div className="card bg-gray-50">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Informazioni Scansione</h4>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">ID Scansione:</span>
            <div className="font-mono text-xs text-gray-900">{scanResults.scan_id}</div>
          </div>
          
          <div>
            <span className="text-gray-500">Data/Ora:</span>
            <div className="font-medium text-gray-900">
              {new Date(scanResults.metadata.timestamp).toLocaleString('it-IT')}
            </div>
          </div>
          
          <div>
            <span className="text-gray-500">Versione:</span>
            <div className="font-medium text-gray-900">{scanResults.metadata.version}</div>
          </div>
          
          <div>
            <span className="text-gray-500">Metodologia:</span>
            <div className="font-medium text-gray-900 capitalize">{scanResults.metadata.methodology_used}</div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}