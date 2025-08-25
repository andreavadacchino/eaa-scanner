import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import Layout from '../components/Layout';

const LLM_MODELS = [
  {
    id: 'gpt-5',
    name: 'GPT-5',
    description: 'Ultima generazione - $1.25/$10.00 per 1M token (200k context)',
    recommended: true,
    cost_level: 'premium'
  },
  {
    id: 'gpt-5-mini',
    name: 'GPT-5 Mini',
    description: 'Efficiente next-gen - $0.25/$2.00 per 1M token (200k context)',
    recommended: false,
    cost_level: 'medium'
  },
  {
    id: 'gpt-5-nano',
    name: 'GPT-5 Nano',
    description: 'Ultra-efficiente - $0.05/$0.40 per 1M token (100k context)',
    recommended: false,
    cost_level: 'low'
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    description: 'Multimodale precedente - $2.50/$10.00 per 1M token (128k context)',
    recommended: false,
    cost_level: 'medium'
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'Economico veloce - $0.15/$0.60 per 1M token (128k context)',
    recommended: false,
    cost_level: 'low'
  },
];

export default function LLMConfiguration() {
  const navigate = useNavigate();
  const {
    scanResults,
    scanSessionId,
    config,
    setLLMModel,
    setLoading,
    setError,
    goToStep,
  } = useAppContext();

  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const [isProcessing, setIsProcessing] = useState(false);
  const [enrichmentComplete, setEnrichmentComplete] = useState(false);

  // Redirect se mancano i dati necessari
  if (!scanResults || !scanSessionId || !config) {
    navigate('/');
    return null;
  }

  const handleEnrichment = async () => {
    setIsProcessing(true);
    setLoading('report', true);
    setError('report', null);

    try {
      // Qui chiameremo l'endpoint per arricchire i dati con LLM
      console.log('Avvio arricchimento LLM con modello:', selectedModel);
      
      // Per ora simulo un delay
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      setLLMModel(selectedModel);
      setEnrichmentComplete(true);
      
      // Dopo l'arricchimento, vai al report
      setTimeout(() => {
        goToStep(WorkflowStep.REPORT);
        navigate('/report');
      }, 1500);
      
    } catch (error) {
      console.error('Errore arricchimento LLM:', error);
      setError('report', error instanceof Error ? error.message : 'Errore durante l\'arricchimento LLM');
    } finally {
      setIsProcessing(false);
      setLoading('report', false);
    }
  };

  const handleSkip = () => {
    console.log('Skip LLM enrichment');
    setLLMModel(null);
    goToStep(WorkflowStep.REPORT);
    navigate('/report');
  };

  return (
    <Layout
      title="Arricchimento Report con AI"
      subtitle="Migliora il report con suggerimenti e analisi avanzate tramite intelligenza artificiale"
      currentStep={4.5}
      totalSteps={5}
    >
      <div className="p-6 space-y-6">
        {/* Info sulla funzionalità */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-sm font-medium text-blue-900 mb-2">
            🤖 Arricchimento AI del Report
          </h3>
          <p className="text-sm text-blue-800">
            L'intelligenza artificiale può analizzare i risultati della scansione e fornire:
          </p>
          <ul className="mt-2 text-sm text-blue-700 space-y-1">
            <li>• Suggerimenti dettagliati per risolvere ogni problema</li>
            <li>• Prioritizzazione intelligente degli interventi</li>
            <li>• Stima del tempo necessario per le correzioni</li>
            <li>• Esempi di codice e best practices</li>
            <li>• Analisi dell'impatto sull'esperienza utente</li>
          </ul>
        </div>

        {/* Selezione modello */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">
            Seleziona il modello AI
          </h3>
          
          <div className="grid gap-4">
            {LLM_MODELS.map((model) => (
              <label
                key={model.id}
                className={`
                  relative flex items-start p-4 border rounded-lg cursor-pointer
                  transition-all duration-200
                  ${selectedModel === model.id 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                  }
                `}
              >
                <input
                  type="radio"
                  name="llm_model"
                  value={model.id}
                  checked={selectedModel === model.id}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="mt-0.5 mr-3"
                  disabled={isProcessing}
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">
                      {model.name}
                    </span>
                    {model.recommended && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                        Consigliato
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {model.description}
                  </p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Statistiche scansione */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Risultati da arricchire
          </h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-gray-700">
                {scanResults.pages_total || 0}
              </div>
              <div className="text-xs text-gray-600">Pagine Analizzate</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-700">
                {(scanResults as any).issues_total || scanResults.issues_found || 0}
              </div>
              <div className="text-xs text-blue-600">Problemi Trovati</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-700">
                {Math.round(((scanResults as any).compliance_score || 0) * 100) / 100}%
              </div>
              <div className="text-xs text-green-600">Conformità WCAG</div>
            </div>
          </div>
        </div>

        {/* Progress durante l'arricchimento */}
        {isProcessing && (
          <div className="space-y-4">
            <div className="flex flex-col items-center py-8">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-blue-200 rounded-full"></div>
                <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin absolute top-0"></div>
              </div>
              <p className="mt-4 text-gray-600 text-center">
                Arricchimento in corso con {LLM_MODELS.find(m => m.id === selectedModel)?.name}...
                <br />
                <span className="text-sm">Questo processo richiede circa 30-60 secondi</span>
              </p>
            </div>
          </div>
        )}

        {/* Successo */}
        {enrichmentComplete && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-green-600 mt-0.5 mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-green-900">
                  Arricchimento completato!
                </h3>
                <p className="text-sm text-green-700 mt-1">
                  Il report è stato arricchito con suggerimenti e analisi AI. Reindirizzamento al report...
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Azioni */}
        <div className="flex justify-between pt-4 border-t">
          <button
            onClick={handleSkip}
            disabled={isProcessing}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Salta Arricchimento
          </button>

          <button
            onClick={handleEnrichment}
            disabled={isProcessing || enrichmentComplete}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isProcessing ? 'Arricchimento in corso...' : 'Avvia Arricchimento AI'}
          </button>
        </div>

        {/* Info aggiuntive */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm text-amber-800">
            <strong>Nota:</strong> L'arricchimento AI richiede una chiave API OpenAI configurata.
            Il processo aggiunge circa 30-60 secondi al tempo totale ma migliora significativamente
            la qualità e l'utilità del report finale.
          </p>
        </div>
      </div>
    </Layout>
  );
}