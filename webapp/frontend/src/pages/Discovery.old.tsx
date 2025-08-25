import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import ProgressBar from '../components/ProgressBar';
import { useScanContext, useStepNavigation } from '../contexts/ScanContext';
import { apiService } from '../services/api';
import { DiscoveryRequest, DiscoveryStatus } from '../types';

export const Discovery: React.FC = () => {
  const navigate = useNavigate();
  const { 
    config, 
    discoveryId, 
    setDiscoveryId, 
    setDiscoveredPages 
  } = useScanContext();
  const { goToNextStep, goToPreviousStep } = useStepNavigation();
  
  const [discoveryStatus, setDiscoveryStatus] = useState<DiscoveryStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string>('');

  // Reindirizza alla configurazione se non c'è config
  useEffect(() => {
    if (!config) {
      navigate('/');
      return;
    }
  }, [config, navigate]);

  // Avvia discovery automaticamente se non è già in corso
  useEffect(() => {
    if (config && !discoveryId && !isStarting) {
      startDiscovery();
    }
  }, [config, discoveryId, isStarting]);

  const startDiscovery = async () => {
    if (!config) return;
    
    setIsStarting(true);
    setError('');
    
    try {
      const discoveryRequest: DiscoveryRequest = {
        url: config.url,
        discovery_mode: 'smart',
        max_pages: 50,
        max_depth: 3,
        include_external: false,
        include_media: true,
        focus_areas: ['forms', 'navigation', 'content'],
        company_name: config.company_name,
        email: config.email,
      };

      const response = await apiService.startDiscovery(discoveryRequest);
      setDiscoveryId(response.session_id);
      
      // Inizia il polling per lo stato
      await pollDiscoveryStatus(response.session_id);
      
    } catch (error) {
      console.error('Errore avvio discovery:', error);
      setError(
        error instanceof Error 
          ? error.message 
          : 'Errore durante l\'avvio della ricerca pagine'
      );
    } finally {
      setIsStarting(false);
    }
  };

  const pollDiscoveryStatus = async (sessionId: string) => {
    try {
      const finalStatus = await apiService.pollDiscoveryStatus(
        sessionId,
        (status) => {
          setDiscoveryStatus(status);
          console.log('Discovery status:', status);
        }
      );

      if (finalStatus.status === 'completed') {
        // Il backend può restituire le pagine in 'pages' o 'discovered_pages'
        const pages = finalStatus.pages || finalStatus.discovered_pages || [];
        console.log('Discovery completed, pages found:', pages);
        
        if (pages.length > 0) {
          setDiscoveredPages(pages);
          // Automaticamente procede al passo successivo
          setTimeout(() => {
            goToNextStep();
            navigate('/selection');
          }, 1500);
        } else {
          console.warn('No pages found in discovery result:', finalStatus);
          setError('Nessuna pagina trovata durante la discovery');
        }
      } else if (finalStatus.status === 'failed') {
        setError(finalStatus.error || 'Discovery fallita');
      }
      
    } catch (error) {
      console.error('Errore polling discovery:', error);
      setError(
        error instanceof Error 
          ? error.message 
          : 'Errore durante il monitoraggio della ricerca'
      );
    }
  };

  const handleRestart = () => {
    setDiscoveryId(null);
    setDiscoveryStatus(null);
    setError('');
    startDiscovery();
  };

  const handleBack = () => {
    goToPreviousStep();
    navigate('/');
  };

  if (!config) {
    return null; // Sarà reindirizzato dalla useEffect
  }

  const isCompleted = discoveryStatus?.status === 'completed';
  const isFailed = discoveryStatus?.status === 'failed' || !!error;
  const isRunning = discoveryStatus?.status === 'running' || isStarting;

  return (
    <Layout 
      title="Ricerca Pagine"
      subtitle="Stiamo analizzando il tuo sito per trovare tutte le pagine da scansionare"
    >
      <div className="p-6">
        {/* Info sito */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Sito in analisi
              </h3>
              <div className="mt-1 text-sm text-blue-700">
                <p><strong>URL:</strong> {config.url}</p>
                <p><strong>Azienda:</strong> {config.company_name}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Progress o stato */}
        {isRunning && (
          <div className="space-y-4 mb-6">
            <ProgressBar 
              progress={discoveryStatus?.progress || 0}
              message={discoveryStatus?.message || 'Avvio ricerca pagine...'}
              animated={true}
            />
            
            {discoveryStatus?.pages_found !== undefined && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-2xl font-bold text-gray-900">
                    {discoveryStatus.pages_found}
                  </div>
                  <div className="text-sm text-gray-600">Pagine trovate</div>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-2xl font-bold text-gray-900">
                    {discoveryStatus.progress}%
                  </div>
                  <div className="text-sm text-gray-600">Completamento</div>
                </div>
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-sm text-gray-600">Pagina corrente:</div>
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {discoveryStatus.current_page || 'N/A'}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Successo */}
        {isCompleted && (
          <div className="bg-success/10 border border-success/20 rounded-md p-4 mb-6">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-success mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-success-800">
                  Ricerca completata con successo!
                </h3>
                <p className="text-sm text-success-700 mt-1">
                  Trovate {discoveryStatus?.pages_found || 0} pagine. 
                  Verrai reindirizzato alla selezione tra poco...
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Errore */}
        {isFailed && (
          <div className="bg-danger/10 border border-danger/20 rounded-md p-4 mb-6">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-danger mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-danger-800">
                  Errore durante la ricerca
                </h3>
                <p className="text-sm text-danger-700 mt-1">
                  {error || discoveryStatus?.error || 'Errore sconosciuto'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loader per attese lunghe */}
        {isRunning && (
          <div className="text-center py-8">
            <div className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-700 bg-primary-100">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-primary-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Ricerca in corso... Questo processo può richiedere alcuni minuti
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t">
          <button
            onClick={handleBack}
            disabled={isRunning}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            ← Indietro
          </button>
          
          {isFailed && (
            <button
              onClick={handleRestart}
              className="px-6 py-2 bg-primary text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              Riprova
            </button>
          )}
          
          {isCompleted && (
            <button
              onClick={() => {
                goToNextStep();
                navigate('/selection');
              }}
              className="px-6 py-2 bg-success text-white rounded-md hover:bg-success-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success"
            >
              Continua →
            </button>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Discovery;
