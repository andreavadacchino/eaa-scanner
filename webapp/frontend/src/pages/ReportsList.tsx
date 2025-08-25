import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Report, ReportsListResponse, ReportFilters } from '../types';
import { apiService } from '../services/api';
import { useAppContext } from '../contexts/AppContext';
import Layout from '../components/Layout';
import LoadingSpinner from '../components/common/LoadingSpinner';

const ReportsListPage: React.FC = () => {
  const navigate = useNavigate();
  const { setScanSessionId, setScanResults } = useAppContext();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalReports, setTotalReports] = useState(0);
  const [filters, setFilters] = useState<ReportFilters>({
    order_by: 'created_at',
    order_dir: 'desc'
  });
  
  const ITEMS_PER_PAGE = 20;

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const skip = (currentPage - 1) * ITEMS_PER_PAGE;
      const data: ReportsListResponse = await apiService.getReportsList(skip, ITEMS_PER_PAGE, filters);
      setReports(data.reports);
      setTotalReports(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore nel caricamento dei report');
      console.error('Error loading reports:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, filters]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleSort = (field: 'created_at' | 'completed_at' | 'company_name' | 'url') => {
    setFilters(prev => ({
      ...prev,
      order_by: field,
      order_dir: prev.order_by === field && prev.order_dir === 'desc' ? 'asc' : 'desc'
    }));
    setCurrentPage(1);
  };

  const handleStatusFilter = (status?: string) => {
    setFilters(prev => ({ ...prev, status }));
    setCurrentPage(1);
  };

  const handleViewReport = (report: Report) => {
    // Apri il report HTML in una nuova scheda
    window.open(`/api/reports/${report.id}/view`, '_blank');
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'completed': { 
        color: 'bg-green-100 text-green-800 border-green-200', 
        label: '✅ Completato',
        icon: '✅'
      },
      'failed': { 
        color: 'bg-red-100 text-red-800 border-red-200', 
        label: '❌ Fallito',
        icon: '❌'
      },
      'in_progress': { 
        color: 'bg-yellow-100 text-yellow-800 border-yellow-200', 
        label: '⏳ In Corso',
        icon: '⏳'
      },
      'pending': { 
        color: 'bg-gray-100 text-gray-800 border-gray-200', 
        label: '⏸️ In Attesa',
        icon: '⏸️'
      }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.color}`}>
        {config.label}
      </span>
    );
  };

  const getComplianceBadge = (level: string | null) => {
    if (!level || level === 'unknown') return <span className="text-gray-400 text-sm">-</span>;
    
    const colors = {
      'conforme': 'bg-green-100 text-green-800 border-green-200',
      'parzialmente_conforme': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'non_conforme': 'bg-red-100 text-red-800 border-red-200'
    };
    
    const labels = {
      'conforme': '✅ Conforme',
      'parzialmente_conforme': '⚠️ Parzialmente',
      'non_conforme': '❌ Non Conforme'
    };
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[level as keyof typeof colors]}`}>
        {labels[level as keyof typeof labels]}
      </span>
    );
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const totalPages = Math.ceil(totalReports / ITEMS_PER_PAGE);

  const SortIcon = ({ field, currentField, direction }: { field: string; currentField?: string; direction?: string }) => {
    if (currentField !== field) {
      return <span className="text-gray-400 ml-1">↕</span>;
    }
    return direction === 'desc' ? 
      <span className="text-blue-600 ml-1">↓</span> : 
      <span className="text-blue-600 ml-1">↑</span>;
  };

  if (loading && reports.length === 0) {
    return (
      <Layout
        title="Report di Accessibilità"
        subtitle="Caricamento report in corso..."
      >
        <div className="flex items-center justify-center min-h-[400px]">
          <LoadingSpinner />
        </div>
      </Layout>
    );
  }

  return (
    <Layout
      title="Report di Accessibilità"
      subtitle="Gestisci e visualizza tutti i report di scansione"
    >
      <div className="p-6 space-y-6">
        {/* Statistiche Rapide */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-2xl font-bold text-gray-900">{totalReports}</div>
            <div className="text-xs text-gray-600">Report Totali</div>
          </div>
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-bold text-green-600">
              {reports.filter(r => r.status === 'completed').length}
            </div>
            <div className="text-xs text-gray-600">Completati</div>
          </div>
          <div className="text-center p-3 bg-yellow-50 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600">
              {reports.filter(r => r.status === 'in_progress').length}
            </div>
            <div className="text-xs text-gray-600">In Corso</div>
          </div>
          <div className="text-center p-3 bg-red-50 rounded-lg">
            <div className="text-2xl font-bold text-red-600">
              {reports.filter(r => r.status === 'failed').length}
            </div>
            <div className="text-xs text-gray-600">Falliti</div>
          </div>
        </div>

        {/* Filtri e Azioni */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">🔍 Filtra per stato:</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleStatusFilter(undefined)}
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  !filters.status 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                Tutti ({totalReports})
              </button>
              <button
                onClick={() => handleStatusFilter('completed')}
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  filters.status === 'completed' 
                    ? 'bg-green-600 text-white hover:bg-green-700' 
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                ✅ Completati
              </button>
              <button
                onClick={() => handleStatusFilter('in_progress')}
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  filters.status === 'in_progress' 
                    ? 'bg-yellow-600 text-white hover:bg-yellow-700' 
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                ⏳ In Corso
              </button>
              <button
                onClick={() => handleStatusFilter('failed')}
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  filters.status === 'failed' 
                    ? 'bg-red-600 text-white hover:bg-red-700' 
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                ❌ Falliti
              </button>
            </div>
            <div className="ml-auto flex gap-2">
              <button
                onClick={loadReports}
                className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2"
              >
                🔄 Aggiorna
              </button>
              <button
                onClick={() => navigate('/')}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center gap-2"
              >
                ⚡ Nuova Scansione
              </button>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Tabella Report */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Stato
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleSort('company_name')}
                  >
                    <div className="flex items-center">
                      Azienda
                      <SortIcon field="company_name" currentField={filters.order_by} direction={filters.order_dir} />
                    </div>
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleSort('url')}
                  >
                    <div className="flex items-center">
                      URL
                      <SortIcon field="url" currentField={filters.order_by} direction={filters.order_dir} />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Punteggio
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Conformità
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Problemi
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center">
                      Data
                      <SortIcon field="created_at" currentField={filters.order_by} direction={filters.order_dir} />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Azioni
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(report.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{report.company_name || 'N/D'}</div>
                      <div className="text-xs text-gray-500">{report.email || 'N/D'}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 truncate max-w-xs" title={report.url}>
                        {report.url}
                      </div>
                      <div className="text-xs text-gray-500">
                        {report.scan_type === 'real' ? '🌐 Reale' : report.scan_type === 'simulate' ? '🔧 Simulato' : '❓ N/D'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {report.score > 0 ? (
                        <div className="flex items-center">
                          <div className={`text-sm font-bold ${
                            report.score >= 80 ? 'text-green-600' : 
                            report.score >= 60 ? 'text-yellow-600' : 'text-red-600'
                          }`}>
                            {report.score}%
                          </div>
                          <div className="ml-2 w-20 bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                report.score >= 80 ? 'bg-green-500' : 
                                report.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}
                              style={{ width: `${report.score}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getComplianceBadge(report.compliance_level)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {report.status === 'completed' ? (
                        <div className="flex gap-1">
                          {report.critical_issues > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                              C:{report.critical_issues}
                            </span>
                          )}
                          {report.high_issues > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">
                              A:{report.high_issues}
                            </span>
                          )}
                          {report.medium_issues > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                              M:{report.medium_issues}
                            </span>
                          )}
                          {report.low_issues > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                              B:{report.low_issues}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600">
                      {formatDate(report.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center gap-1">
                        {report.status === 'completed' && report.html_report_path && (
                          <>
                            <button
                              onClick={() => handleViewReport(report)}
                              className="p-2 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded transition-all"
                              title="Visualizza Report"
                            >
                              📊
                            </button>
                            <a
                              href={`/api/reports/${report.id}/download?format=pdf`}
                              className="p-2 text-green-600 hover:text-green-900 hover:bg-green-50 rounded transition-all"
                              title="Scarica PDF"
                              download
                            >
                              📥
                            </a>
                            <a
                              href={`/api/reports/${report.id}/download?format=html`}
                              className="p-2 text-purple-600 hover:text-purple-900 hover:bg-purple-50 rounded transition-all"
                              title="Scarica HTML"
                              download
                            >
                              📄
                            </a>
                            <a
                              href={report.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded transition-all"
                              title="Apri Sito Web"
                            >
                              🔗
                            </a>
                          </>
                        )}
                        {report.status === 'in_progress' && (
                          <button
                            onClick={() => navigate(`/scanning?scan_id=${report.id}`)}
                            className="p-2 text-yellow-600 hover:text-yellow-900 hover:bg-yellow-50 rounded transition-all"
                            title="Visualizza Progresso"
                          >
                            ⏳
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Nessun risultato */}
          {reports.length === 0 && !loading && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-gray-500 mb-4">Nessun report trovato</p>
              <button
                onClick={() => navigate('/')}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                ⚡ Avvia Nuova Scansione
              </button>
            </div>
          )}

          {/* Paginazione */}
          {totalPages > 1 && (
            <div className="bg-gray-50 px-6 py-3 flex items-center justify-between border-t border-gray-200">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  ← Precedente
                </button>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Successivo →
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Mostrando <span className="font-medium">{(currentPage - 1) * ITEMS_PER_PAGE + 1}</span> a{' '}
                    <span className="font-medium">
                      {Math.min(currentPage * ITEMS_PER_PAGE, totalReports)}
                    </span>{' '}
                    di <span className="font-medium">{totalReports}</span> risultati
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                    <button
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      title="Prima pagina"
                    >
                      ««
                    </button>
                    <button
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      ←
                    </button>
                    {[...Array(Math.min(5, totalPages))].map((_, idx) => {
                      let pageNum = idx + 1;
                      if (totalPages > 5) {
                        if (currentPage > 3) {
                          pageNum = currentPage - 2 + idx;
                        }
                        if (currentPage > totalPages - 3) {
                          pageNum = totalPages - 4 + idx;
                        }
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium transition-colors ${
                            currentPage === pageNum
                              ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                              : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      →
                    </button>
                    <button
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      title="Ultima pagina"
                    >
                      »»
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default ReportsListPage;