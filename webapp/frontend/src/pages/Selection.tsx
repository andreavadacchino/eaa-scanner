import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppContext, WorkflowStep } from '../contexts/AppContext';
import Layout from '../components/Layout';

export default function Selection() {
  const navigate = useNavigate();
  const {
    config,
    discoveredPages,
    selectedPages,
    togglePageSelection,
    selectAllPages,
    deselectAllPages,
    goToStep,
    resetFromStep,
  } = useAppContext();

  const [filter, setFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  // Redirect se mancano i dati necessari
  if (!config || discoveredPages.length === 0) {
    navigate('/');
    return null;
  }

  // Filtra le pagine in base ai criteri
  const filteredPages = useMemo(() => {
    return discoveredPages.filter(page => {
      const matchesSearch = page.url.toLowerCase().includes(filter.toLowerCase()) ||
                           page.title.toLowerCase().includes(filter.toLowerCase());
      const matchesType = typeFilter === 'all' || page.type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [discoveredPages, filter, typeFilter]);

  // Statistiche
  const stats = useMemo(() => ({
    total: discoveredPages.length,
    selected: selectedPages.length,
    pages: discoveredPages.filter(p => p.type === 'page').length,
    forms: discoveredPages.filter(p => p.type === 'form').length,
    documents: discoveredPages.filter(p => p.type === 'document').length,
    other: discoveredPages.filter(p => p.type === 'other').length,
  }), [discoveredPages, selectedPages]);

  const handleProceed = () => {
    if (selectedPages.length === 0) {
      alert('Seleziona almeno una pagina da scansionare');
      return;
    }
    goToStep(WorkflowStep.SCANNING);
    navigate('/scanning');
  };

  const handleBack = () => {
    resetFromStep(WorkflowStep.DISCOVERY);
    navigate('/discovery');
  };

  // Auto-selezione intelligente
  const autoSelectImportant = () => {
    const important = discoveredPages
      .filter(page => 
        page.depth <= 1 || 
        page.type === 'form' || 
        page.url.includes('contact') ||
        page.url.includes('about') ||
        page.url.includes('accessibility')
      )
      .slice(0, 10)
      .map(p => p.url);
    
    // Deseleziona tutto e seleziona solo le importanti
    deselectAllPages();
    important.forEach(url => togglePageSelection(url));
  };

  return (
    <Layout
      title="Selezione Pagine"
      subtitle="Seleziona le pagine da sottoporre a scansione di accessibilità"
      currentStep={3}
      totalSteps={5}
    >
      <div className="p-6 space-y-6">
        {/* Header con statistiche */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-700">{stats.total}</div>
              <div className="text-xs text-blue-600">Totali</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-700">{stats.selected}</div>
              <div className="text-xs text-green-600">Selezionate</div>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-700">{stats.pages}</div>
              <div className="text-xs text-gray-600">Pagine</div>
            </div>
            <div>
              <div className="text-xl font-bold text-purple-700">{stats.forms}</div>
              <div className="text-xs text-purple-600">Form</div>
            </div>
            <div>
              <div className="text-xl font-bold text-orange-700">{stats.documents}</div>
              <div className="text-xs text-orange-600">Documenti</div>
            </div>
            <div>
              <div className="text-xl font-bold text-gray-700">{stats.other}</div>
              <div className="text-xs text-gray-600">Altri</div>
            </div>
          </div>
        </div>

        {/* Controlli */}
        <div className="flex flex-col md:flex-row gap-4">
          {/* Ricerca */}
          <div className="flex-1">
            <input
              type="text"
              placeholder="Cerca nelle pagine..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* Filtro tipo */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">Tutti i tipi</option>
            <option value="page">Solo Pagine</option>
            <option value="form">Solo Form</option>
            <option value="document">Solo Documenti</option>
            <option value="other">Altri</option>
          </select>

          {/* Azioni rapide */}
          <div className="flex gap-2">
            <button
              onClick={selectAllPages}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              Seleziona Tutto
            </button>
            <button
              onClick={deselectAllPages}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              Deseleziona Tutto
            </button>
            <button
              onClick={autoSelectImportant}
              className="px-4 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors"
            >
              Auto-Selezione
            </button>
          </div>
        </div>

        {/* Info auto-selezione */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-sm text-amber-800">
            <strong>Suggerimento:</strong> L'auto-selezione sceglierà automaticamente le pagine più importanti 
            (homepage, form, contatti, accessibilità) fino a un massimo di 10 pagine.
          </p>
        </div>

        {/* Lista pagine */}
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="max-h-96 overflow-y-auto">
            {filteredPages.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Nessuna pagina trovata con i criteri di ricerca
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredPages.map((page) => {
                  const isSelected = selectedPages.includes(page.url);
                  return (
                    <label
                      key={page.url}
                      className={`flex items-start p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                        isSelected ? 'bg-blue-50' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => togglePageSelection(page.url)}
                        className="mt-1 mr-3"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            page.type === 'page' ? 'bg-blue-100 text-blue-800' :
                            page.type === 'form' ? 'bg-purple-100 text-purple-800' :
                            page.type === 'document' ? 'bg-orange-100 text-orange-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {page.type === 'page' ? 'Pagina' :
                             page.type === 'form' ? 'Form' :
                             page.type === 'document' ? 'Documento' :
                             'Altro'}
                          </span>
                          <span className="text-xs text-gray-500">
                            Profondità: {page.depth}
                          </span>
                        </div>
                        <div className="font-medium text-gray-900">
                          {page.title || 'Senza titolo'}
                        </div>
                        <div className="text-sm text-gray-600 break-all">
                          {page.url}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Warning se troppe pagine */}
        {selectedPages.length > 20 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-sm text-yellow-800">
              <strong>Attenzione:</strong> Hai selezionato {selectedPages.length} pagine. 
              La scansione di molte pagine potrebbe richiedere tempo considerevole.
            </p>
          </div>
        )}

        {/* Azioni */}
        <div className="flex justify-between pt-4 border-t">
          <button
            onClick={handleBack}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            ← Indietro
          </button>

          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">
              {selectedPages.length} pagine selezionate
            </span>
            <button
              onClick={handleProceed}
              disabled={selectedPages.length === 0}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                selectedPages.length === 0
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              Avvia Scansione →
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}