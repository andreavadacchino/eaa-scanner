/**
 * EAA Scanner - History Page JavaScript
 * Manages scan history display, filtering, and bulk actions
 */

class ScanHistory {
  constructor() {
    this.scans = [];
    this.filteredScans = [];
    this.currentSort = { field: 'date', direction: 'desc' };
    this.currentPage = 1;
    this.itemsPerPage = 20;
    this.selectedScans = new Set();
    
    // UI Elements
    this.searchInput = document.getElementById('search');
    this.dateFromInput = document.getElementById('date-from');
    this.dateToInput = document.getElementById('date-to');
    this.statusFilter = document.getElementById('status-filter');
    this.complianceFilter = document.getElementById('compliance-filter');
    this.applyFiltersBtn = document.getElementById('apply-filters');
    this.resetFiltersBtn = document.getElementById('reset-filters');
    this.exportDataBtn = document.getElementById('export-data');
    this.refreshBtn = document.getElementById('refresh-data');
    
    this.loadingState = document.getElementById('loading-state');
    this.tableContainer = document.getElementById('table-container');
    this.emptyState = document.getElementById('empty-state');
    this.scansBody = document.getElementById('scans-tbody');
    
    this.totalScansEl = document.getElementById('total-scans');
    this.completedScansEl = document.getElementById('completed-scans');
    this.avgScoreEl = document.getElementById('avg-score');
    this.compliantSitesEl = document.getElementById('compliant-sites');
    
    this.prevPageBtn = document.getElementById('prev-page');
    this.nextPageBtn = document.getElementById('next-page');
    this.pageInfo = document.getElementById('page-info');
    
    this.bulkModal = document.getElementById('bulk-modal');
    this.selectedCount = document.getElementById('selected-count');
    
    this.init();
  }
  
  init() {
    this.bindEvents();
    this.initTheme();
    this.loadHistory();
  }
  
  bindEvents() {
    // Filter events
    if (this.applyFiltersBtn) {
      this.applyFiltersBtn.addEventListener('click', this.applyFilters.bind(this));
    }
    
    if (this.resetFiltersBtn) {
      this.resetFiltersBtn.addEventListener('click', this.resetFilters.bind(this));
    }
    
    if (this.exportDataBtn) {
      this.exportDataBtn.addEventListener('click', this.exportData.bind(this));
    }
    
    if (this.refreshBtn) {
      this.refreshBtn.addEventListener('click', this.loadHistory.bind(this));
    }
    
    // Search input with debouncing
    if (this.searchInput) {
      let searchTimeout;
      this.searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          this.applyFilters();
        }, 300);
      });
    }
    
    // Pagination
    if (this.prevPageBtn) {
      this.prevPageBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.currentPage--;
          this.renderTable();
        }
      });
    }
    
    if (this.nextPageBtn) {
      this.nextPageBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(this.filteredScans.length / this.itemsPerPage);
        if (this.currentPage < totalPages) {
          this.currentPage++;
          this.renderTable();
        }
      });
    }
    
    // Sort buttons (delegated)
    document.addEventListener('click', (e) => {
      if (e.target.closest('.sort-btn')) {
        const sortField = e.target.closest('.sort-btn').dataset.sort;
        this.sortScans(sortField);
      }
    });
    
    // Bulk selection
    document.addEventListener('change', (e) => {
      if (e.target.classList.contains('scan-checkbox')) {
        this.handleScanSelection(e.target);
      } else if (e.target.id === 'select-all') {
        this.handleSelectAll(e.target);
      }
    });
    
    // Modal close
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-close') || e.target === this.bulkModal) {
        this.closeBulkModal();
      }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.bulkModal.style.display !== 'none') {
        this.closeBulkModal();
      }
    });
  }
  
  initTheme() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    const currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    this.updateThemeIcon(currentTheme);
    
    themeToggle.addEventListener('click', () => {
      const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      this.updateThemeIcon(newTheme);
    });
  }
  
  updateThemeIcon(theme) {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    themeToggle.innerHTML = theme === 'dark' 
      ? '<span class="icon">☀️</span>' 
      : '<span class="icon">🌙</span>';
  }
  
  async loadHistory() {
    try {
      this.showLoading(true);
      
      // Simulate API call - replace with actual endpoint
      const response = await fetch('/api/history');
      
      if (response.ok) {
        const data = await response.json();
        this.scans = data.scans || [];
      } else {
        // Fallback to mock data for demo
        this.scans = this.generateMockData();
      }
      
      this.filteredScans = [...this.scans];
      this.updateStatistics();
      this.renderTable();
      this.showLoading(false);
      
    } catch (error) {
      console.error('Failed to load history:', error);
      // Use mock data as fallback
      this.scans = this.generateMockData();
      this.filteredScans = [...this.scans];
      this.updateStatistics();
      this.renderTable();
      this.showLoading(false);
    }
  }
  
  generateMockData() {
    const companies = ['Acme Corp', 'TechStart SRL', 'WebAgency', 'DigitalFirst', 'Innovation Hub'];
    const urls = ['https://acme.com', 'https://techstart.it', 'https://webagency.eu', 'https://digitalfirst.net', 'https://innovhub.org'];
    const statuses = ['completed', 'error', 'running'];
    const scanners = [
      ['WAVE', 'Pa11y'],
      ['WAVE', 'Axe', 'Lighthouse'],
      ['Pa11y', 'Axe'],
      ['WAVE', 'Pa11y', 'Axe', 'Lighthouse']
    ];
    
    const mockScans = [];
    
    for (let i = 0; i < 50; i++) {
      const date = new Date();
      date.setDate(date.getDate() - Math.floor(Math.random() * 30));
      
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      const score = status === 'completed' ? Math.floor(Math.random() * 100) : null;
      const compliance = score >= 85 ? 'conforme' : score >= 60 ? 'parzialmente_conforme' : 'non_conforme';
      
      mockScans.push({
        id: `scan_${i + 1}`,
        date: date.toISOString(),
        company: companies[Math.floor(Math.random() * companies.length)],
        url: urls[Math.floor(Math.random() * urls.length)],
        status: status,
        score: score,
        compliance: status === 'completed' ? compliance : null,
        scanners: scanners[Math.floor(Math.random() * scanners.length)],
        duration: Math.floor(Math.random() * 300) + 30, // 30-330 seconds
        issues: {
          errors: Math.floor(Math.random() * 20),
          warnings: Math.floor(Math.random() * 50),
          total: 0
        }
      });
      
      // Calculate total issues
      const scan = mockScans[mockScans.length - 1];
      scan.issues.total = scan.issues.errors + scan.issues.warnings;
    }
    
    return mockScans.sort((a, b) => new Date(b.date) - new Date(a.date));
  }
  
  showLoading(show) {
    if (this.loadingState) {
      this.loadingState.style.display = show ? 'block' : 'none';
    }
    
    if (this.tableContainer) {
      this.tableContainer.style.display = show ? 'none' : 'block';
    }
    
    if (this.emptyState) {
      this.emptyState.style.display = 'none';
    }
  }
  
  updateStatistics() {
    const totalScans = this.scans.length;
    const completedScans = this.scans.filter(s => s.status === 'completed').length;
    const compliantSites = this.scans.filter(s => s.compliance === 'conforme').length;
    
    const scores = this.scans.filter(s => s.score !== null).map(s => s.score);
    const avgScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
    
    if (this.totalScansEl) this.totalScansEl.textContent = totalScans;
    if (this.completedScansEl) this.completedScansEl.textContent = completedScans;
    if (this.avgScoreEl) this.avgScoreEl.textContent = avgScore || '--';
    if (this.compliantSitesEl) this.compliantSitesEl.textContent = compliantSites;
  }
  
  applyFilters() {
    const searchTerm = this.searchInput?.value.toLowerCase() || '';
    const dateFrom = this.dateFromInput?.value || '';
    const dateTo = this.dateToInput?.value || '';
    const statusFilter = this.statusFilter?.value || '';
    const complianceFilter = this.complianceFilter?.value || '';
    
    this.filteredScans = this.scans.filter(scan => {
      // Search filter
      if (searchTerm) {
        const searchMatch = scan.company.toLowerCase().includes(searchTerm) ||
                           scan.url.toLowerCase().includes(searchTerm);
        if (!searchMatch) return false;
      }
      
      // Date filters
      if (dateFrom) {
        const scanDate = new Date(scan.date).toISOString().split('T')[0];
        if (scanDate < dateFrom) return false;
      }
      
      if (dateTo) {
        const scanDate = new Date(scan.date).toISOString().split('T')[0];
        if (scanDate > dateTo) return false;
      }
      
      // Status filter
      if (statusFilter && scan.status !== statusFilter) {
        return false;
      }
      
      // Compliance filter
      if (complianceFilter && scan.compliance !== complianceFilter) {
        return false;
      }
      
      return true;
    });
    
    this.currentPage = 1;
    this.renderTable();
  }
  
  resetFilters() {
    if (this.searchInput) this.searchInput.value = '';
    if (this.dateFromInput) this.dateFromInput.value = '';
    if (this.dateToInput) this.dateToInput.value = '';
    if (this.statusFilter) this.statusFilter.value = '';
    if (this.complianceFilter) this.complianceFilter.value = '';
    
    this.filteredScans = [...this.scans];
    this.currentPage = 1;
    this.renderTable();
  }
  
  sortScans(field) {
    // Toggle direction if same field, otherwise default to desc
    if (this.currentSort.field === field) {
      this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
      this.currentSort.field = field;
      this.currentSort.direction = 'desc';
    }
    
    this.filteredScans.sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];
      
      // Handle different data types
      if (field === 'date') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      } else if (field === 'score') {
        aVal = aVal || 0;
        bVal = bVal || 0;
      } else if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (aVal < bVal) return this.currentSort.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return this.currentSort.direction === 'asc' ? 1 : -1;
      return 0;
    });
    
    this.currentPage = 1;
    this.renderTable();
  }
  
  renderTable() {
    if (!this.scansBody) return;
    
    if (this.filteredScans.length === 0) {
      this.showEmptyState();
      return;
    }
    
    this.hideEmptyState();
    
    // Calculate pagination
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    const pageScans = this.filteredScans.slice(startIndex, endIndex);
    
    // Render table rows
    this.scansBody.innerHTML = pageScans.map(scan => this.renderScanRow(scan)).join('');
    
    // Update pagination
    this.updatePagination();
    
    // Update sort indicators
    this.updateSortIndicators();
  }
  
  renderScanRow(scan) {
    const date = new Date(scan.date).toLocaleDateString('it-IT');
    const time = new Date(scan.date).toLocaleTimeString('it-IT', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    
    const statusBadge = this.getStatusBadge(scan.status);
    const scoreBadge = scan.score !== null ? this.getScoreBadge(scan.score) : '--';
    
    return `
      <tr>
        <td>
          <input type="checkbox" class="scan-checkbox" value="${scan.id}">
        </td>
        <td>
          <div>
            <strong>${date}</strong><br>
            <small style="color: var(--text-secondary);">${time}</small>
          </div>
        </td>
        <td>
          <div>
            <strong>${this.escapeHtml(scan.company)}</strong>
          </div>
        </td>
        <td>
          <a href="${scan.url}" target="_blank" class="url-link">
            ${this.truncateUrl(scan.url)}
          </a>
        </td>
        <td>${statusBadge}</td>
        <td>${scoreBadge}</td>
        <td>
          <div class="scanner-tags">
            ${scan.scanners.map(s => `<span class="scanner-tag">${s}</span>`).join('')}
          </div>
        </td>
        <td>
          <div class="action-btns">
            ${scan.status === 'completed' ? `
              <button class="btn btn-sm btn-secondary" onclick="viewReport('${scan.id}')" title="Visualizza Report">
                <span class="icon">👁️</span>
              </button>
              <button class="btn btn-sm btn-secondary" onclick="downloadPdf('${scan.id}')" title="Scarica PDF">
                <span class="icon">📄</span>
              </button>
            ` : ''}
            <button class="btn btn-sm btn-secondary" onclick="viewDetails('${scan.id}')" title="Dettagli">
              <span class="icon">ℹ️</span>
            </button>
          </div>
        </td>
      </tr>
    `;
  }
  
  getStatusBadge(status) {
    const badges = {
      completed: '<span class="status-badge status-completed">✅ Completata</span>',
      error: '<span class="status-badge status-error">❌ Errore</span>',
      running: '<span class="status-badge status-running">🔄 In corso</span>'
    };
    
    return badges[status] || '<span class="status-badge">❓ Sconosciuto</span>';
  }
  
  getScoreBadge(score) {
    let className = 'score-low';
    if (score >= 85) className = 'score-high';
    else if (score >= 60) className = 'score-medium';
    
    return `<span class="score-badge ${className}">${score}/100</span>`;
  }
  
  truncateUrl(url) {
    if (url.length <= 40) return url;
    return url.substring(0, 37) + '...';
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  showEmptyState() {
    if (this.tableContainer) this.tableContainer.style.display = 'none';
    if (this.emptyState) this.emptyState.style.display = 'block';
  }
  
  hideEmptyState() {
    if (this.tableContainer) this.tableContainer.style.display = 'block';
    if (this.emptyState) this.emptyState.style.display = 'none';
  }
  
  updatePagination() {
    const totalPages = Math.ceil(this.filteredScans.length / this.itemsPerPage);
    
    if (this.prevPageBtn) {
      this.prevPageBtn.disabled = this.currentPage <= 1;
    }
    
    if (this.nextPageBtn) {
      this.nextPageBtn.disabled = this.currentPage >= totalPages;
    }
    
    if (this.pageInfo) {
      this.pageInfo.textContent = `Pagina ${this.currentPage} di ${totalPages}`;
    }
  }
  
  updateSortIndicators() {
    // Reset all sort indicators
    document.querySelectorAll('.sort-btn').forEach(btn => {
      btn.classList.remove('active');
      const icon = btn.querySelector('.sort-icon');
      if (icon) icon.textContent = '⇅';
    });
    
    // Set active sort indicator
    const activeBtn = document.querySelector(`[data-sort="${this.currentSort.field}"]`);
    if (activeBtn) {
      activeBtn.classList.add('active');
      const icon = activeBtn.querySelector('.sort-icon');
      if (icon) {
        icon.textContent = this.currentSort.direction === 'asc' ? '↑' : '↓';
      }
    }
  }
  
  handleScanSelection(checkbox) {
    if (checkbox.checked) {
      this.selectedScans.add(checkbox.value);
    } else {
      this.selectedScans.delete(checkbox.value);
    }
    
    this.updateBulkActions();
  }
  
  handleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.scan-checkbox');
    
    checkboxes.forEach(cb => {
      cb.checked = checkbox.checked;
      if (checkbox.checked) {
        this.selectedScans.add(cb.value);
      } else {
        this.selectedScans.delete(cb.value);
      }
    });
    
    this.updateBulkActions();
  }
  
  updateBulkActions() {
    if (this.selectedCount) {
      this.selectedCount.textContent = this.selectedScans.size;
    }
    
    if (this.selectedScans.size > 0) {
      this.showBulkModal();
    } else {
      this.closeBulkModal();
    }
  }
  
  showBulkModal() {
    if (this.bulkModal) {
      this.bulkModal.style.display = 'flex';
    }
  }
  
  closeBulkModal() {
    if (this.bulkModal) {
      this.bulkModal.style.display = 'none';
    }
  }
  
  exportData() {
    const dataToExport = this.filteredScans.map(scan => ({
      Data: new Date(scan.date).toLocaleDateString('it-IT'),
      Azienda: scan.company,
      URL: scan.url,
      Stato: scan.status,
      Punteggio: scan.score || 'N/A',
      'Livello Conformità': scan.compliance || 'N/A',
      Scanner: scan.scanners.join(', '),
      Errori: scan.issues?.errors || 0,
      Avvisi: scan.issues?.warnings || 0,
      'Problemi Totali': scan.issues?.total || 0
    }));
    
    this.downloadCSV(dataToExport, 'eaa-scanner-history.csv');
  }
  
  downloadCSV(data, filename) {
    if (data.length === 0) return;
    
    const headers = Object.keys(data[0]);
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => {
          const value = row[header];
          // Escape quotes and wrap in quotes if contains comma
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }
}

// Global functions for action buttons
window.viewReport = function(scanId) {
  window.open(`/preview?scan_id=${scanId}`, '_blank');
};

window.downloadPdf = function(scanId) {
  window.location.href = `/download/pdf?scan_id=${scanId}`;
};

window.viewDetails = function(scanId) {
  // TODO: Implement details modal
  alert(`Dettagli per scan ${scanId} - da implementare`);
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.scanHistory = new ScanHistory();
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ScanHistory;
}