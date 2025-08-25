import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import { apiClient, DiscoveryResponse } from '../services/apiClient';
import Layout from '../components/Layout';
import ProgressBar from '../components/ProgressBar';

export default function Discovery() {
  const navigate = useNavigate();
  const { 
    config, 
    setDiscoverySessionId, 
    setDiscoveredPages,
    setLoading,
    setError,
    goToStep,
    resetFromStep
  } = useAppContext();
  
  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryResponse | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  // Redirect se manca la configurazione
  useEffect(() => {
    if (!config) {
      navigate('/');
    }
  }, [config, navigate]);

  // Avvia discovery automaticamente
  useEffect(() => {
    if (config && !hasStarted) {
      startDiscovery();
      setHasStarted(true);
    }
  }, [config, hasStarted]);

  const startDiscovery = async () => {
    if (!config) return;
    
    setIsStarting(true);
    setLoading('discovery', true);
    setError('discovery', null);
    
    try {
      console.log('Avvio discovery per:', config.url);
      
      // Avvia il discovery
      const response = await apiClient.startDiscovery(config.url);
      console.log('Discovery avviato:', response);
      
      setDiscoverySessionId(response.session_id);
      
      // Inizia il polling dello stato
      const finalStatus = await apiClient.pollDiscovery(
        response.session_id,
        (status) => {
          console.log('Discovery status update:', status);
          setDiscoveryStatus(status);
        },
        5000, // Check ogni 5 secondi
        60    // Max 5 minuti
      );
      
      console.log('Discovery completato:', finalStatus);
      
      const pages = finalStatus.discovered_pages || finalStatus.pages;
      if ((finalStatus.status === 'completed' || finalStatus.state === 'completed') && pages && pages.length > 0) {
        setDiscoveredPages(pages);
        
        // Auto-naviga alla selezione dopo 2 secondi
        setTimeout(() => {
          goToStep(WorkflowStep.SELECTION);
          navigate('/selection');
        }, 2000);
      } else if (finalStatus.status === 'failed' || finalStatus.state === 'failed') {
        throw new Error(finalStatus.error || 'Discovery fallito');
      }
      
    } catch (error) {
      console.error('Errore discovery:', error);
      setError('discovery', error instanceof Error ? error.message : 'Errore durante il discovery');
    } finally {
      setIsStarting(false);
      setLoading('discovery', false);
    }
  };

  const handleRetry = () => {
    setHasStarted(false);
    setDiscoveryStatus(null);
    setError('discovery', null);
    startDiscovery();
  };

  const handleBack = () => {
    resetFromStep(WorkflowStep.CONFIGURATION);
    navigate('/');
  };

  if (!config) {
    return null;
  }

  const isRunning = discoveryStatus?.status === 'running' || discoveryStatus?.status === 'pending' || isStarting;
  const isCompleted = discoveryStatus?.status === 'completed';
  const isFailed = discoveryStatus?.status === 'failed';
  const hasError = !!discoveryStatus?.error;

  return (
    <Layout
      title="Discovery Pagine"
      subtitle="Stiamo analizzando il sito per trovare tutte le pagine pubbliche"
      currentStep={2}
      totalSteps={5}
    >
      <div className="p-6 space-y-6">
        {/* Info sito */}
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Sito in analisi</p>
              <p className="text-lg font-medium text-gray-900">{config.url}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Azienda</p>
              <p className="text-lg font-medium text-gray-900">{config.company_name}</p>
            </div>
          </div>
        </div>

        {/* Progress */}
        {isRunning && (
          <div className="space-y-4">
            <ProgressBar
              progress={discoveryStatus?.progress || 0}
              message={discoveryStatus?.message || 'Avvio crawler...'}
              animated={true}
            />

            {/* Statistiche discovery */}
            {discoveryStatus?.pages && discoveryStatus.pages.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-sm font-medium text-blue-900 mb-2">
                  Pagine trovate finora: {discoveryStatus.pages.length}
                </h3>
                <div className="grid grid-cols-3 gap-3 mt-3">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {discoveryStatus.pages.filter(p => p.type === 'page').length}
                    </div>
                    <div className="text-xs text-blue-700">Pagine</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {discoveryStatus.pages.filter(p => p.type === 'form').length}
                    </div>
                    <div className="text-xs text-blue-700">Form</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {discoveryStatus.pages.filter(p => p.type === 'document').length}
                    </div>
                    <div className="text-xs text-blue-700">Documenti</div>
                  </div>
                </div>
              </div>
            )}

            {/* Loader animato */}
            <div className="flex flex-col items-center py-8">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-blue-200 rounded-full"></div>
                <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin absolute top-0"></div>
              </div>
              <p className="mt-4 text-gray-600 text-center">
                Sto analizzando il sito web per trovare tutte le pagine accessibili pubblicamente.
                <br />
                Questa operazione può richiedere alcuni minuti...
              </p>
            </div>
          </div>
        )}

        {/* Successo */}
        {isCompleted && discoveryStatus?.pages && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-green-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-green-900">
                    Discovery completato con successo!
                  </h3>
                  <p className="text-sm text-green-700 mt-1">
                    Trovate {discoveryStatus.pages.length} pagine. Verrai reindirizzato alla selezione...
                  </p>
                </div>
              </div>
            </div>

            {/* Riepilogo pagine trovate */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <h3 className="text-sm font-medium text-gray-900 mb-3">
                Riepilogo pagine trovate
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-gray-50 rounded">
                  <div className="text-2xl font-bold text-gray-700">
                    {discoveryStatus.pages.length}
                  </div>
                  <div className="text-xs text-gray-600">Totale</div>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded">
                  <div className="text-2xl font-bold text-blue-700">
                    {discoveryStatus.pages.filter(p => p.type === 'page').length}
                  </div>
                  <div className="text-xs text-blue-600">Pagine Web</div>
                </div>
                <div className="text-center p-3 bg-purple-50 rounded">
                  <div className="text-2xl font-bold text-purple-700">
                    {discoveryStatus.pages.filter(p => p.type === 'form').length}
                  </div>
                  <div className="text-xs text-purple-600">Form</div>
                </div>
                <div className="text-center p-3 bg-orange-50 rounded">
                  <div className="text-2xl font-bold text-orange-700">
                    {discoveryStatus.pages.filter(p => p.depth <= 1).length}
                  </div>
                  <div className="text-xs text-orange-600">Pagine Principali</div>
                </div>
              </div>
            </div>
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
                  Errore durante il discovery
                </h3>
                <p className="text-sm text-red-700 mt-1">
                  {discoveryStatus?.error || 'Si è verificato un errore durante l\'analisi del sito'}
                </p>
              </div>
            </div>
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
              Riprova Discovery
            </button>
          )}

          {isCompleted && (
            <button
              onClick={() => {
                goToStep(WorkflowStep.SELECTION);
                navigate('/selection');
              }}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
            >
              Procedi alla Selezione →
            </button>
          )}
        </div>
      </div>
    </Layout>
  );
}