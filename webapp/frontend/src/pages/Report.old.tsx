import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { useScanContext } from '../contexts/ScanContext';
import { apiService } from '../services/api';
import { ScanIssue } from '../types';

export const Report: React.FC = () => {
  const navigate = useNavigate();
  const { config, scanResult, scanId, resetAll } = useScanContext();
  
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');

  // Reindirizza se non ci sono risultati
  useEffect(() => {
    if (!config) {
      navigate('/');
      return;
    }
    if (!scanResult) {
      navigate('/scanning');
      return;
    }
  }, [config, scanResult, navigate]);

  const handleDownloadReport = async (format: 'html' | 'pdf' = 'pdf') => {
    if (!scanId) {
      setDownloadError('ID scansione non disponibile');
      return;
    }

    setIsDownloading(true);
    setDownloadError('');
    
    try {
      const blob = await apiService.downloadReport(scanId, format);
      
      // Crea il link per il download
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `eaa-report-${config?.company_name || 'report'}.${format}`;
      document.body.appendChild(link);
      link.click();
      
      // Cleanup
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Errore download report:', error);
      setDownloadError(
        error instanceof Error 
          ? error.message 
          : 'Errore durante il download del report'
      );
    } finally {
      setIsDownloading(false);
    }
  };

  const handleNewScan = () => {
    resetAll();
    navigate('/');
  };

  if (!config || !scanResult) {
    return null; // Sarà reindirizzato dalle useEffect
  }

  // Filtra le issues per severità
  const filteredIssues = selectedSeverity === 'all' 
    ? scanResult.issues
    : scanResult.issues.filter(issue => issue.severity === selectedSeverity);

  const getSeverityColor = (severity: ScanIssue['severity']) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getComplianceColor = (level: string) => {
    switch (level) {
      case 'conforme': return 'bg-green-100 text-green-800';
      case 'parzialmente_conforme': return 'bg-yellow-100 text-yellow-800';
      case 'non_conforme': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getComplianceText = (level: string) => {
    switch (level) {
      case 'conforme': return 'Conforme';
      case 'parzialmente_conforme': return 'Parzialmente Conforme';
      case 'non_conforme': return 'Non Conforme';
      default: return level;
    }
  };

  return (
    <Layout 
      title="Report di Accessibilità"
      subtitle="Risultati dell'analisi di accessibilità completata"
    >
      <div className="p-6">
        {/* Header con info generali */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-800">
                Report generato per {config.company_name}
              </h3>
              <p className="text-sm text-blue-700">
                URL: {scanResult.url} • {new Date(scanResult.timestamp).toLocaleString('it-IT')}
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => handleDownloadReport('pdf')}
                disabled={isDownloading}
                className="inline-flex items-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 disabled:opacity-50"
              >
                {isDownloading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Download...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                    PDF
                  </>
                )}
              </button>
              <button
                onClick={() => handleDownloadReport('html')}
                disabled={isDownloading}
                className="inline-flex items-center px-3 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-white hover:bg-blue-50 disabled:opacity-50"
              >
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 11-1.414 1.414L10 4.414 7.707 6.707a1 1 0 01-1.414 0zM10 18a1 1 0 01-1-1v-7.586L7.707 10.707a1 1 0 01-1.414-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 11-1.414 1.414L11 9.293V17a1 1 0 01-1 1z" clipRule="evenodd" />
                </svg>
                HTML
              </button>
            </div>
          </div>
        </div>

        {/* Errore download */}
        {downloadError && (
          <div className="bg-danger/10 border border-danger/20 rounded-md p-4 mb-6">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-danger mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-danger-800">
                  Errore Download
                </h3>
                <p className="text-sm text-danger-700 mt-1">
                  {downloadError}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Metriche principali */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <div className="bg-white border border-gray-200 rounded-md p-4 text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {scanResult.compliance_score}%
            </div>
            <div className="text-sm text-gray-600 mb-2">Punteggio Conformità</div>
            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getComplianceColor(scanResult.compliance_level)}`}>
              {getComplianceText(scanResult.compliance_level)}
            </span>
          </div>

          <div className="bg-white border border-gray-200 rounded-md p-4 text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {scanResult.total_issues}
            </div>
            <div className="text-sm text-gray-600">Problemi Totali</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-md p-4 text-center">
            <div className="text-3xl font-bold text-red-600 mb-2">
              {scanResult.issues_by_severity.critical + scanResult.issues_by_severity.high}
            </div>
            <div className="text-sm text-gray-600">Problemi Critici/Alti</div>
          </div>

          <div className="bg-white border border-gray-200 rounded-md p-4 text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {scanResult.scanners_used.length}
            </div>
            <div className="text-sm text-gray-600">Scanner Utilizzati</div>
            <div className="text-xs text-gray-500 mt-1">
              {scanResult.scanners_used.join(', ')}
            </div>
          </div>
        </div>

        {/* Distribuzione severità */}
        <div className="bg-white border border-gray-200 rounded-md p-4 mb-6">
          <h4 className="text-lg font-medium text-gray-900 mb-4">
            Distribuzione Problemi per Severità
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(scanResult.issues_by_severity).map(([severity, count]) => (
              <div key={severity} className="text-center">
                <div className={`text-2xl font-bold mb-1 ${
                  severity === 'critical' ? 'text-red-600' :
                  severity === 'high' ? 'text-orange-600' :
                  severity === 'medium' ? 'text-yellow-600' :
                  'text-gray-600'
                }`}>
                  {count}
                </div>
                <div className="text-sm text-gray-600 capitalize">
                  {severity === 'critical' ? 'Critici' :
                   severity === 'high' ? 'Alti' :
                   severity === 'medium' ? 'Medi' :
                   'Bassi'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Filtro e lista problemi */}
        <div className="bg-white border border-gray-200 rounded-md">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-medium text-gray-900">
                Dettagli Problemi ({filteredIssues.length})
              </h4>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              >
                <option value="all">Tutti i livelli</option>
                <option value="critical">Solo Critici</option>
                <option value="high">Solo Alti</option>
                <option value="medium">Solo Medi</option>
                <option value="low">Solo Bassi</option>
              </select>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {filteredIssues.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Nessun problema trovato per il filtro selezionato
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredIssues.map((issue, index) => (
                  <div key={index} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSeverityColor(issue.severity)}`}>
                            {issue.severity.toUpperCase()}
                          </span>
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                            {issue.source.toUpperCase()}
                          </span>
                          {issue.wcag && (
                            <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded">
                              {issue.wcag}
                            </span>
                          )}
                        </div>
                        
                        <h5 className="font-medium text-gray-900 mb-1">
                          {issue.code}
                        </h5>
                        
                        <p className="text-sm text-gray-700 mb-2">
                          {issue.message}
                        </p>
                        
                        {issue.selector && (
                          <div className="text-xs text-gray-500 mb-1">
                            <strong>Selettore:</strong> <code className="bg-gray-100 px-1 rounded">{issue.selector}</code>
                          </div>
                        )}
                        
                        {issue.context && (
                          <div className="text-xs text-gray-500">
                            <strong>Contesto:</strong> {issue.context}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t mt-6">
          <button
            onClick={handleNewScan}
            className="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            Nuova Scansione
          </button>
          
          <div className="text-sm text-gray-500">
            Report completato • {scanResult.scanners_used.join(', ')} • {new Date(scanResult.timestamp).toLocaleString('it-IT')}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Report;
