import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import { apiClient, ScanResponse } from '../services/apiClient';
import Layout from '../components/Layout';
import ProgressBar from '../components/ProgressBar';

export default function Scanning() {
  const navigate = useNavigate();
  const {
    config,
    selectedPages,
    setScanSessionId,
    setScanResults,
    setLoading,
    setError,
    goToStep,
    resetFromStep,
  } = useAppContext();

  const [scanStatus, setScanStatus] = useState<ScanResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Redirect se mancano i dati necessari
  useEffect(() => {
    if (!config || selectedPages.length === 0) {
      navigate('/');
    }
  }, [config, selectedPages, navigate]);

  // Avvia scan automaticamente
  useEffect(() => {
    if (config && selectedPages.length > 0 && !hasStarted) {
      startScan();
      setHasStarted(true);
    }
  }, [config, selectedPages, hasStarted]);

  const startScan = async () => {
    if (!config || selectedPages.length === 0) return;

    setIsStarting(true);
    setLoading('scan', true);
    setError('scan', null);

    try {
      console.log('Avvio scansione per:', selectedPages.length, 'pagine');

      // Prepara la richiesta
      const scanRequest = {
        pages: selectedPages,
        company_name: config.company_name,
        email: config.email,
        scanners: config.scanners,
      };

      // Avvia la scansione
      const response = await apiClient.startScan(scanRequest);
      console.log('Scansione avviata:', response);

      setScanSessionId(response.session_id);
      setCurrentSessionId(response.session_id); // Salva anche localmente per fallback

      // Inizia il polling dello stato
      console.log('🚀 Avvio polling per session:', response.session_id);
      const finalStatus = await apiClient.pollScan(
        response.session_id,
        (status) => {
          console.log('📡 Scan status update:', {
            session_id: status.session_id,
            status: status.status,
            progress: status.progress,
            pages_scanned: status.pages_scanned,
            total_pages: status.total_pages,
            pages_completed: status.pages_completed,
            pages_total: status.pages_total,
            issues_found: status.issues_found
          });
          setScanStatus(status);
        },
        8000, // Check ogni 8 secondi (più veloce)
        150   // Max 20 minuti
      );

      console.log('Scansione completata:', finalStatus);

      if (finalStatus.status === 'completed') {
        setScanResults(finalStatus);

        // Scansione completata - l'utente può scegliere se procedere
      } else if (finalStatus.status === 'failed') {
        throw new Error(finalStatus.error || 'Scansione fallita');
      }

    } catch (error) {
      console.error('❌ Errore scansione:', error);
      
      // Se il polling fallisce ma la scansione potrebbe essere completata,
      // prova a verificare direttamente i risultati
      const sessionToCheck = currentSessionId || scanStatus?.session_id;
      if (error instanceof Error && sessionToCheck) {
        console.log('🔍 Tentativo di verifica completamento scansione per session:', sessionToCheck);
        try {
          // Prima prova con checkScanCompletion
          const isCompleted = await apiClient.checkScanCompletion(sessionToCheck);
          if (isCompleted) {
            console.log('✅ Scansione completata! Ottengo i risultati...');
            const results = await apiClient.getScanResults(sessionToCheck);
            setScanResults({
              session_id: sessionToCheck,
              status: 'completed',
              results
            } as any);
            
            // Risultati ottenuti - l'utente può scegliere se procedere
            
            return; // Exit early, scansione completata
          }
        } catch (fallbackError) {
          console.error('⚠️ Fallback check failed:', fallbackError);
          
          // Ultimo tentativo: prova a fare una richiesta diretta allo status
          try {
            console.log('🔄 Ultimo tentativo: check diretto status...');
            const finalCheck = await apiClient.getScanStatus(sessionToCheck);
            if (finalCheck.status === 'completed') {
              console.log('✅ Scansione confermata come completata!');
              setScanResults(finalCheck);
              
              // Scansione confermata - l'utente può scegliere se procedere
              
              return;
            }
          } catch (lastError) {
            console.error('❌ Anche ultimo tentativo fallito:', lastError);
          }
        }
      }
      
      setError('scan', error instanceof Error ? error.message : 'Errore durante la scansione');
    } finally {
      setIsStarting(false);
      setLoading('scan', false);
    }
  };

  const handleRetry = () => {
    setHasStarted(false);
    setScanStatus(null);
    setError('scan', null);
    startScan();
  };

  const handleBack = () => {
    resetFromStep(WorkflowStep.SELECTION);
    navigate('/selection');
  };

  if (!config || selectedPages.length === 0) {
    return null;
  }

  const isRunning = scanStatus?.status === 'running' || scanStatus?.status === 'pending' || isStarting;
  const isCompleted = scanStatus?.status === 'completed';
  const isFailed = scanStatus?.status === 'failed';
  const hasError = !!scanStatus?.error;

  // Calcola progresso dettagliato (usando mapping corretto)
  const pagesCompleted = scanStatus?.pages_completed || scanStatus?.pages_scanned || 0;
  const pagesTotal = scanStatus?.pages_total || scanStatus?.total_pages || selectedPages.length;
  const progressPercent = pagesTotal > 0 ? Math.round((pagesCompleted / pagesTotal) * 100) : 0;
  
  // Debug progresso per troubleshooting
  console.log('📊 Progress Debug:', {
    scanStatus_status: scanStatus?.status,
    pagesCompleted,
    pagesTotal,
    progressPercent,
    raw_pages_completed: scanStatus?.pages_completed,
    raw_pages_scanned: scanStatus?.pages_scanned,
    raw_pages_total: scanStatus?.pages_total,
    raw_total_pages: scanStatus?.total_pages
  });

  return (
    <Layout
      title="Scansione in Corso"
      subtitle="Analisi di accessibilità delle pagine selezionate"
      currentStep={4}
      totalSteps={5}
    >
      <div className="p-6 space-y-6">
        {/* Info scansione */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-700">{selectedPages.length}</div>
              <div className="text-xs text-gray-600">Pagine Totali</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-700">{pagesCompleted}</div>
              <div className="text-xs text-blue-600">Completate</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-700">{config.scanners.length}</div>
              <div className="text-xs text-green-600">Scanner Attivi</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-700">{progressPercent}%</div>
              <div className="text-xs text-purple-600">Progresso</div>
            </div>
          </div>
        </div>

        {/* Scanner attivi */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h3 className="text-sm font-medium text-blue-900 mb-2">Scanner Attivi</h3>
          <div className="flex flex-wrap gap-2">
            {config.scanners.map(scanner => (
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

        {/* Debug Panel - solo in development */}
        {process.env.NODE_ENV === 'development' && scanStatus && (
          <div className="bg-gray-100 border border-gray-300 rounded-lg p-3 text-xs">
            <h3 className="font-medium text-gray-700 mb-2">🔧 Debug Info</h3>
            <div className="space-y-1 font-mono text-gray-600">
              <div>Session ID: {currentSessionId || 'N/A'}</div>
              <div>Status: {scanStatus.status}</div>
              <div>Progress: {scanStatus.progress}%</div>
              <div>Pages (backend): {scanStatus.pages_scanned}/{scanStatus.total_pages}</div>
              <div>Pages (mapped): {pagesCompleted}/{pagesTotal}</div>
              <div>Current Page: {scanStatus.current_page || 'N/A'}</div>
              <div>Issues Found: {scanStatus.issues_found || 0}</div>
              <div>Has Results: {scanStatus.results ? 'Yes' : 'No'}</div>
            </div>
          </div>
        )}

        {/* Progress */}
        {isRunning && (
          <div className="space-y-4">
            <ProgressBar
              progress={progressPercent}
              message={scanStatus?.message || `Scansione pagina ${pagesCompleted + 1} di ${pagesTotal}...`}
              animated={true}
            />

            {/* Pagina corrente */}
            {scanStatus?.current_page && (
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-2">
                  Pagina in scansione:
                </h3>
                <p className="text-sm text-gray-600 break-all">
                  {scanStatus.current_page}
                </p>
              </div>
            )}

            {/* Stima tempo rimanente e debug info */}
            {pagesCompleted > 0 && (
              <div className="text-center text-sm text-gray-600">
                <p>
                  Tempo stimato rimanente: {Math.ceil((pagesTotal - pagesCompleted) * 30 / 60)} minuti
                </p>
                <p className="text-xs mt-1">
                  (circa 30 secondi per pagina per scanner)
                </p>
                {/* Debug info in sviluppo */}
                <p className="text-xs mt-2 text-gray-400 font-mono">
                  Debug: {pagesCompleted}/{pagesTotal} ({progressPercent}%) - Status: {scanStatus?.status}
                </p>
              </div>
            )}

            {/* Loader animato */}
            <div className="flex flex-col items-center py-8">
              <div className="relative">
                <div className="w-20 h-20 border-4 border-blue-200 rounded-full"></div>
                <div className="w-20 h-20 border-4 border-blue-600 border-t-transparent rounded-full animate-spin absolute top-0"></div>
              </div>
              <p className="mt-4 text-gray-600 text-center max-w-md">
                Stiamo analizzando l'accessibilità di ogni pagina selezionata.
                <br />
                Questa operazione richiede tempo per garantire un'analisi completa e accurata.
              </p>
            </div>
          </div>
        )}

        {/* Successo */}
        {isCompleted && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-green-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-900">
                    Scansione completata con successo!
                  </h3>
                  <p className="text-sm text-green-700 mt-1">
                    Tutte le {pagesTotal} pagine sono state analizzate. Verrai reindirizzato al report...
                  </p>
                </div>
              </div>
            </div>

            {/* Riepilogo risultati preliminari */}
            {scanStatus?.results && (
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-3">
                  Riepilogo Preliminare
                </h3>
                <p className="text-sm text-gray-600">
                  L'analisi è stata completata. Il report dettagliato è pronto per la visualizzazione.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Errore */}
        {(isFailed || hasError) && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <h3 className="text-sm font-medium text-red-900">
                  Errore durante la scansione
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  {scanStatus?.error || 'Si è verificato un errore durante l\'analisi'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Warning per scansioni lunghe */}
        {isRunning && pagesTotal > 10 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <p className="text-sm text-amber-800">
              <strong>Nota:</strong> Stai scansionando {pagesTotal} pagine con {config.scanners.length} scanner.
              L'operazione potrebbe richiedere circa {Math.ceil(pagesTotal * config.scanners.length * 30 / 60)} minuti.
              Puoi lasciare questa pagina aperta mentre la scansione procede in background.
            </p>
          </div>
        )}

        {/* Azioni */}
        <div className="flex justify-between pt-4 border-t">
          <button
            onClick={handleBack}
            disabled={isRunning}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            ← Indietro
          </button>

          {(isFailed || hasError) && (
            <button
              onClick={handleRetry}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Riprova Scansione
            </button>
          )}

          {isCompleted && (
            <button
              onClick={() => {
                goToStep(WorkflowStep.LLM_CONFIGURATION);
                navigate('/llm-configuration');
              }}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              Procedi →
            </button>
          )}
        </div>
      </div>
    </Layout>
  );
}