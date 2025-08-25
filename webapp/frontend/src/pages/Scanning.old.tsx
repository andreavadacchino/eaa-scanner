import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import ProgressBar from '../components/ProgressBar';
import { useScanContext, usePageSelection, useStepNavigation } from '../contexts/ScanContext';
import { apiService } from '../services/api';
import { MultiPageScanRequest, ScanStatus } from '../types';

export const Scanning: React.FC = () => {
  const navigate = useNavigate();
  const { 
    config,
    discoveryId,  // Aggiungi discoveryId per passarlo al backend
    scanId, 
    setScanId, 
    setScanResult 
  } = useScanContext();
  const { selectedPages, selectedCount } = usePageSelection();
  const { goToNextStep, goToPreviousStep } = useStepNavigation();
  
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string>('');

  // Reindirizza se mancano dati
  useEffect(() => {
    if (!config) {
      navigate('/');
      return;
    }
    if (selectedPages.length === 0) {
      navigate('/selection');
      return;
    }
  }, [config, selectedPages, navigate]);

  // Avvia scansione automaticamente se non è già in corso
  useEffect(() => {
    if (config && selectedPages.length > 0 && !scanId && !isStarting) {
      startScan();
    }
  }, [config, selectedPages, scanId, isStarting]);

  const startScan = async () => {
    if (!config || selectedPages.length === 0) return;
    
    setIsStarting(true);
    setError('');
    
    try {
      // Usa multi-page scan se multiple pagine, altrimenti single scan
      let response;
      
      if (selectedPages.length === 1) {
        // Single page scan
        response = await apiService.startScan({
          ...config,
          url: selectedPages[0], // Override URL con la pagina selezionata
        });
      } else {
        // Multi-page scan - il backend richiede array di URL complete
        // Converti scannerConfig in array di scanner names
        const enabledScanners = config.scannerConfig 
          ? Object.entries(config.scannerConfig)
              .filter(([_, enabled]) => enabled)
              .map(([scanner]) => scanner)
          : ['pa11y', 'axe', 'lighthouse'];  // Default scanners
        
        const multiPageRequest: MultiPageScanRequest = {
          pages: selectedPages,  // Array di URL complete
          company_name: config.company_name,
          email: config.email,
          scanners: enabledScanners,
          mode: 'real',  // Sempre modalità reale, non simulazione
          discovery_session_id: discoveryId || undefined,
        };
        
        response = await apiService.startMultiPageScan(multiPageRequest);
      }
      
      setScanId(response.scan_id);
      
      // Inizia il polling per lo stato
      await pollScanStatus(response.scan_id);
      
    } catch (error) {
      console.error('Errore avvio scansione:', error);
      setError(
        error instanceof Error 
          ? error.message 
          : 'Errore durante l\'avvio della scansione'
      );
    } finally {
      setIsStarting(false);
    }
  };

  const pollScanStatus = async (scanId: string) => {
    try {
      const finalStatus = await apiService.pollScanStatus(
        scanId,
        (status) => {
          setScanStatus(status);
          console.log('Scan status:', status);
        }
      );

      if (finalStatus.status === 'completed' && finalStatus.result) {
        setScanResult(finalStatus.result);
        // Automaticamente procede al passo successivo
        setTimeout(() => {
          goToNextStep();
          navigate('/report');
        }, 1500);
      } else if (finalStatus.status === 'failed') {
        setError(finalStatus.error || 'Scansione fallita');
      }
      
    } catch (error) {
      console.error('Errore polling scansione:', error);
      setError(
        error instanceof Error 
          ? error.message 
          : 'Errore durante il monitoraggio della scansione'
      );
    }
  };

  const handleRestart = () => {
    setScanId(null);
    setScanStatus(null);
    setError('');
    startScan();
  };

  const handleBack = () => {
    goToPreviousStep();
    navigate('/selection');
  };

  if (!config || selectedPages.length === 0) {
    return null; // Sarà reindirizzato dalle useEffect
  }

  const isCompleted = scanStatus?.status === 'completed';
  const isFailed = scanStatus?.status === 'failed' || !!error;
  const isRunning = scanStatus?.status === 'running' || scanStatus?.status === 'pending' || isStarting;

  return (
    <Layout 
      title="Scansione in Corso"
      subtitle="Stiamo analizzando l'accessibilità delle pagine selezionate"
    >
      <div className="p-6">
        {/* Info scansione */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-blue-800">
                Dettagli Scansione
              </h3>
              <div className="mt-1 text-sm text-blue-700">
                <p><strong>Pagine da scansionare:</strong> {selectedCount}</p>
                <p><strong>Scanner attivi:</strong> {
                  config.scannerConfig ? Object.entries(config.scannerConfig)
                    .filter(([_, enabled]) => enabled)
                    .map(([scanner]) => scanner)
                    .join(', ') : 'N/A'
                }</p>
                {scanStatus?.scan_id && (
                  <p><strong>ID Scansione:</strong> {scanStatus.scan_id}</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Progress o stato */}
        {isRunning && (
          <div className="space-y-4 mb-6">
            <ProgressBar 
              progress={scanStatus?.progress || 0}
              message={scanStatus?.message || 'Avvio scansione...'}
              animated={true}
            />
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-center">
              <div className="bg-gray-50 rounded-md p-3">
                <div className="text-2xl font-bold text-gray-900">
                  {scanStatus?.progress || 0}%
                </div>
                <div className="text-sm text-gray-600">Completamento</div>
              </div>
              
              {scanStatus?.current_scanner && (
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-lg font-bold text-gray-900 capitalize">
                    {scanStatus.current_scanner}
                  </div>
                  <div className="text-sm text-gray-600">Scanner attuale</div>
                </div>
              )}
              
              {scanStatus?.scanners_completed && (
                <div className="bg-gray-50 rounded-md p-3">
                  <div className="text-2xl font-bold text-gray-900">
                    {scanStatus.scanners_completed.length}
                  </div>
                  <div className="text-sm text-gray-600">Scanner completati</div>
                </div>
              )}
              
              <div className="bg-gray-50 rounded-md p-3">
                <div className="text-2xl font-bold text-gray-900">
                  {selectedCount}
                </div>
                <div className="text-sm text-gray-600">Pagine totali</div>
              </div>
            </div>
            
            {/* Scanner completati */}
            {scanStatus?.scanners_completed && scanStatus.scanners_completed.length > 0 && (
              <div className="bg-green-50 border border-green-200 rounded-md p-3">
                <div className="text-sm font-medium text-green-800 mb-2">
                  Scanner completati:
                </div>
                <div className="flex flex-wrap gap-1">
                  {scanStatus.scanners_completed.map(scanner => (
                    <span
                      key={scanner}
                      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
                    >
                      ✓ {scanner}
                    </span>
                  ))}
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
                  Scansione completata con successo!
                </h3>
                <p className="text-sm text-success-700 mt-1">
                  L'analisi di accessibilità è stata completata per tutte le pagine selezionate. 
                  Verrai reindirizzato al report tra poco...
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
                  Errore durante la scansione
                </h3>
                <p className="text-sm text-danger-700 mt-1">
                  {error || scanStatus?.error || 'Errore sconosciuto'}
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
              Scansione in corso... Le scansioni possono richiedere diversi minuti
            </div>
            
            <div className="mt-4 text-sm text-gray-600 max-w-md mx-auto">
              <p>
                Stiamo eseguendo un'analisi completa dell'accessibilità. 
                Il processo può richiedere tempo in base al numero di pagine e scanner selezionati.
              </p>
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
              Riprova Scansione
            </button>
          )}
          
          {isCompleted && (
            <button
              onClick={() => {
                goToNextStep();
                navigate('/report');
              }}
              className="px-6 py-2 bg-success text-white rounded-md hover:bg-success-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success"
            >
              Visualizza Report →
            </button>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Scanning;
