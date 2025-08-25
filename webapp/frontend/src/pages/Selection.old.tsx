import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { useScanContext, usePageSelection, useStepNavigation } from '../contexts/ScanContext';
import { DiscoveredPage } from '../types';

export const Selection: React.FC = () => {
  const navigate = useNavigate();
  const { config } = useScanContext();
  const { 
    discoveredPages, 
    selectedPages,
    selectAll,
    deselectAll,
    togglePage,
    selectedCount,
    totalCount,
    hasSelection
  } = usePageSelection();
  const { goToNextStep, goToPreviousStep } = useStepNavigation();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'page' | 'form' | 'navigation' | 'media'>('all');

  // Reindirizza se non ci sono dati
  useEffect(() => {
    if (!config) {
      navigate('/');
      return;
    }
    if (discoveredPages.length === 0) {
      navigate('/discovery');
      return;
    }
  }, [config, discoveredPages, navigate]);

  // Filtra le pagine
  const filteredPages = discoveredPages.filter(page => {
    const matchesSearch = page.url.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (page.title && page.title.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesType = filterType === 'all' || page.type === filterType;
    return matchesSearch && matchesType;
  });

  const handleContinue = () => {
    if (!hasSelection) {
      alert('Seleziona almeno una pagina per continuare');
      return;
    }
    goToNextStep();
    navigate('/scanning');
  };

  const handleBack = () => {
    goToPreviousStep();
    navigate('/discovery');
  };

  const getTypeIcon = (type: DiscoveredPage['type']) => {
    switch (type) {
      case 'page':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
          </svg>
        );
      case 'form':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'navigation':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'media':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        );
      default:
        return null;
    }
  };

  const getTypeColor = (type: DiscoveredPage['type']) => {
    switch (type) {
      case 'page': return 'text-blue-600';
      case 'form': return 'text-green-600';
      case 'navigation': return 'text-purple-600';
      case 'media': return 'text-orange-600';
      default: return 'text-gray-600';
    }
  };

  if (!config || discoveredPages.length === 0) {
    return null; // Sarà reindirizzato dalle useEffect
  }

  return (
    <Layout 
      title="Seleziona Pagine"
      subtitle="Scegli quali pagine includere nell'analisi di accessibilità"
    >
      <div className="p-6">
        {/* Header con contatori */}
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-blue-800">
                Pagine trovate: {totalCount}
              </h3>
              <p className="text-sm text-blue-700">
                Selezionate: {selectedCount} pagine
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={selectAll}
                className="text-sm bg-white px-3 py-1 border border-blue-300 rounded text-blue-700 hover:bg-blue-50"
              >
                Seleziona tutto
              </button>
              <button
                onClick={deselectAll}
                className="text-sm bg-white px-3 py-1 border border-blue-300 rounded text-blue-700 hover:bg-blue-50"
              >
                Deseleziona tutto
              </button>
            </div>
          </div>
        </div>

        {/* Filtri */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          {/* Ricerca */}
          <div className="flex-1">
            <input
              type="text"
              placeholder="Cerca nelle pagine..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          
          {/* Filtro tipo */}
          <div className="sm:w-48">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              <option value="all">Tutti i tipi</option>
              <option value="page">Pagine</option>
              <option value="form">Form</option>
              <option value="navigation">Navigazione</option>
              <option value="media">Media</option>
            </select>
          </div>
        </div>

        {/* Lista pagine */}
        <div className="space-y-2 mb-6 max-h-96 overflow-y-auto border border-gray-200 rounded-md">
          {filteredPages.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Nessuna pagina trovata con i filtri attuali
            </div>
          ) : (
            filteredPages.map((page, index) => (
              <label
                key={`${page.url}-${index}`}
                className={`
                  flex items-start p-3 cursor-pointer hover:bg-gray-50 border-b border-gray-100 last:border-b-0
                  ${selectedPages.includes(page.url) ? 'bg-primary/5' : ''}
                `}
              >
                <input
                  type="checkbox"
                  checked={selectedPages.includes(page.url)}
                  onChange={() => togglePage(page.url)}
                  className="mt-1 h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                />
                <div className="ml-3 flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className={`flex-shrink-0 ${getTypeColor(page.type)}`}>
                      {getTypeIcon(page.type)}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded capitalize">
                      {page.type}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      Profondità: {page.depth}
                    </span>
                  </div>
                  
                  <div className="mt-1">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      {page.title || 'Senza titolo'}
                    </div>
                    <div className="text-sm text-gray-500 truncate">
                      {page.url}
                    </div>
                    {page.description && (
                      <div className="text-xs text-gray-400 mt-1 line-clamp-2">
                        {page.description}
                      </div>
                    )}
                  </div>
                </div>
              </label>
            ))
          )}
        </div>

        {/* Warning se nessuna selezione */}
        {!hasSelection && (
          <div className="bg-warning/10 border border-warning/20 rounded-md p-4 mb-6">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-warning mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-warning-800">
                  Nessuna pagina selezionata
                </h3>
                <p className="text-sm text-warning-700 mt-1">
                  Seleziona almeno una pagina per procedere con la scansione.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-between pt-6 border-t">
          <button
            onClick={handleBack}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            ← Indietro
          </button>
          
          <button
            onClick={handleContinue}
            disabled={!hasSelection}
            className={`
              px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2
              ${hasSelection 
                ? 'bg-primary text-white hover:bg-primary-700 focus:ring-primary' 
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            Avvia Scansione →
          </button>
        </div>
      </div>
    </Layout>
  );
};

export default Selection;
