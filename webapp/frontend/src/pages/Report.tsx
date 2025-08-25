import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import { apiClient, ReportData } from '../services/apiClient';
import Layout from '../components/Layout';

export default function Report() {
  const navigate = useNavigate();
  const {
    config,
    scanSessionId,
    scanResults,
    setReportData,
    setLoading,
    setError,
    resetApp,
  } = useAppContext();

  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [reportFetched, setReportFetched] = useState(false);
  const [localReportData, setLocalReportData] = useState<ReportData | null>(null);

  // Redirect se mancano i dati necessari
  useEffect(() => {
    if (!config || !scanSessionId || !scanResults) {
      navigate('/');
    }
  }, [config, scanSessionId, scanResults, navigate]);

  // Carica i dati del report
  useEffect(() => {
    if (scanSessionId && scanResults?.status === 'completed' && !reportFetched) {
      fetchReportData();
      setReportFetched(true);
    }
  }, [scanSessionId, scanResults, reportFetched]);

  const fetchReportData = async () => {
    if (!scanSessionId) return;

    setIsLoadingReport(true);
    setLoading('report', true);
    setError('report', null);

    try {
      console.log('Recupero report per session:', scanSessionId);
      const report = await apiClient.getScanResults(scanSessionId);
      console.log('Report ricevuto:', report);
      
      setReportData(report);
      setLocalReportData(report);
    } catch (error) {
      console.error('Errore recupero report:', error);
      setError('report', error instanceof Error ? error.message : 'Errore durante il recupero del report');
    } finally {
      setIsLoadingReport(false);
      setLoading('report', false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!scanSessionId) return;

    try {
      setIsLoadingReport(true);
      console.log('Generazione PDF...');
      
      // Genera il PDF
      const pdfResponse = await apiClient.generatePdf(scanSessionId);
      console.log('PDF generato:', pdfResponse);
      
      // Scarica il PDF
      const blob = await apiClient.downloadReport(scanSessionId, 'pdf');
      
      // Crea un link di download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${config?.company_name?.replace(/\s+/g, '_') || 'accessibility'}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Errore download PDF:', error);
      alert('Errore durante il download del PDF');
    } finally {
      setIsLoadingReport(false);
    }
  };

  const handleDownloadHtml = async () => {
    if (!scanSessionId) return;

    try {
      setIsLoadingReport(true);
      
      // Scarica l'HTML
      const blob = await apiClient.downloadReport(scanSessionId, 'html');
      
      // Crea un link di download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${config?.company_name?.replace(/\s+/g, '_') || 'accessibility'}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Errore download HTML:', error);
      alert('Errore durante il download del report HTML');
    } finally {
      setIsLoadingReport(false);
    }
  };

  const handleNewScan = () => {
    resetApp();
    navigate('/');
  };

  if (!config || !scanSessionId || !scanResults) {
    return null;
  }

  // Statistiche del report
  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'text-red-700 bg-red-100';
      case 'high': return 'text-orange-700 bg-orange-100';
      case 'medium': return 'text-yellow-700 bg-yellow-100';
      case 'low': return 'text-blue-700 bg-blue-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  const getComplianceColor = (score: number) => {
    if (score >= 90) return 'text-green-700';
    if (score >= 70) return 'text-yellow-700';
    if (score >= 50) return 'text-orange-700';
    return 'text-red-700';
  };

  return (
    <Layout
      title="Report di Accessibilità"
      subtitle="Risultati dell'analisi di accessibilità del sito web"
      currentStep={5}
      totalSteps={5}
    >
      <div className="p-6 space-y-6">
        {/* Header con info base */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-600">Azienda</p>
              <p className="text-lg font-medium text-gray-900">{config.company_name}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Sito Web</p>
              <p className="text-lg font-medium text-gray-900">{config.url}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Data Scansione</p>
              <p className="text-lg font-medium text-gray-900">
                {localReportData?.scan_date ? new Date(localReportData.scan_date).toLocaleDateString('it-IT') : 'Oggi'}
              </p>
            </div>
          </div>
        </div>

        {isLoadingReport ? (
          // Loading state
          <div className="flex flex-col items-center py-12">
            <div className="w-16 h-16 border-4 border-blue-200 rounded-full animate-spin border-t-blue-600"></div>
            <p className="mt-4 text-gray-600">Caricamento report...</p>
          </div>
        ) : localReportData ? (
          <>
            {/* Score di conformità */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Score di Conformità WCAG 2.1
                </h2>
                <div className={`text-6xl font-bold ${getComplianceColor(localReportData.compliance_score || 0)}`}>
                  {localReportData.compliance_score || 0}%
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Basato sull'analisi di {localReportData.pages_scanned} pagine con {localReportData.scanners_used?.length || 0} scanner
                </p>
              </div>
            </div>

            {/* Statistiche problemi */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Riepilogo Problemi Rilevati
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center p-3 bg-gray-50 rounded">
                  <div className="text-3xl font-bold text-gray-700">
                    {localReportData.issues_total || 0}
                  </div>
                  <div className="text-xs text-gray-600">Totali</div>
                </div>
                {localReportData.issues_by_severity && Object.entries(localReportData.issues_by_severity).map(([severity, count]) => (
                  <div key={severity} className="text-center p-3 bg-gray-50 rounded">
                    <div className={`text-3xl font-bold ${getSeverityColor(severity).split(' ')[0]}`}>
                      {count}
                    </div>
                    <div className="text-xs text-gray-600 capitalize">{severity}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Dettagli per pagina (preview) */}
            {localReportData.detailed_results && localReportData.detailed_results.length > 0 && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Anteprima Risultati per Pagina
                </h3>
                <div className="space-y-3">
                  {localReportData.detailed_results.slice(0, 3).map((page: any, index: number) => (
                    <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                      <p className="font-medium text-gray-900 text-sm break-all">
                        {page.url || `Pagina ${index + 1}`}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        {page.issues_count || 0} problemi rilevati
                      </p>
                    </div>
                  ))}
                  {localReportData.detailed_results.length > 3 && (
                    <p className="text-sm text-gray-500 italic">
                      ...e altre {localReportData.detailed_results.length - 3} pagine
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Info scanner utilizzati */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-blue-900 mb-2">
                Scanner Utilizzati
              </h3>
              <div className="flex flex-wrap gap-2">
                {localReportData.scanners_used?.map(scanner => (
                  <span
                    key={scanner}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    {scanner === 'pa11y' && '🔍 Pa11y'}
                    {scanner === 'axe' && '⚡ Axe-core'}
                    {scanner === 'lighthouse' && '🏮 Lighthouse'}
                    {scanner === 'wave' && '🌊 WAVE'}
                  </span>
                ))}
              </div>
            </div>
          </>
        ) : (
          // No data state
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800">
              Nessun dato del report disponibile. Ricarica la pagina o avvia una nuova scansione.
            </p>
          </div>
        )}

        {/* Azioni */}
        <div className="flex flex-col sm:flex-row justify-between gap-4 pt-4 border-t">
          <button
            onClick={handleNewScan}
            className="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            🔄 Nuova Scansione
          </button>

          <div className="flex gap-3">
            <button
              onClick={handleDownloadHtml}
              disabled={isLoadingReport || !localReportData}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              📄 Scarica HTML
            </button>
            <button
              onClick={handleDownloadPdf}
              disabled={isLoadingReport || !localReportData}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              📑 Scarica PDF
            </button>
          </div>
        </div>

        {/* Info aggiuntive */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-2">
            ℹ️ Informazioni sul Report
          </h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Il report completo include tutti i dettagli delle problematiche rilevate</li>
            <li>• Ogni problema è categorizzato secondo gli standard WCAG 2.1</li>
            <li>• Il PDF contiene suggerimenti per la risoluzione di ogni problema</li>
            <li>• Lo score di conformità è calcolato in base alla severità e quantità dei problemi</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
}