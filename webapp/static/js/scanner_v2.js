/**
 * EAA Scanner v2 - 2-Phase Workflow Implementation
 * Phase 1: URL Discovery
 * Phase 2: Accessibility Scanning
 */

class EAAScannerV2 {
  constructor() {
    this.currentPhase = 1;
    this.discoverySession = null;
    this.scanSession = null;
    this.discoveredUrls = [];
    this.selectedUrls = [];
    this.scanResults = null;
    
    // Timers
    this.discoveryTimer = null;
    this.scanTimer = null;
    this.discoveryStartTime = null;
    this.scanStartTime = null;
    
    // Polling intervals
    this.discoveryPollInterval = null;
    this.scanPollInterval = null;
    
    // SSE Monitor
    this.sseMonitor = null;
    this.sseConnected = false;
    this.scanCompleteProcessed = false;
    
    // LLM Configuration
    this.llmConfig = {
      enabled: false,
      model: 'gpt-4o',
      apiKey: '',
      apiKeyValid: false
    };
    
    // LLM Regeneration
    this.originalReport = null;
    this.enhancedReport = null;
    this.regenerationInProgress = false;
    
    this.init();
  }
  
  init() {
    this.setupGlobalErrorHandling();
    this.bindEvents();
    this.initTooltips();
    this.loadSavedConfig();
    this.initializePhase(1);
    this.initKeyboardNavigation();
    this.setupCleanupHandlers();
  }
  
  setupCleanupHandlers() {
    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });
    
    // Cleanup on page visibility change (mobile/tab switch)
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        // Don't cleanup on hide, just pause
      } else {
        // Resume if needed
      }
    });
  }
  
  cleanup() {
    console.log('🗑️ EAA Scanner cleanup');
    
    // Clear all intervals
    clearInterval(this.discoveryPollInterval);
    clearInterval(this.scanPollInterval);
    clearTimeout(this.discoveryTimer);
    clearTimeout(this.scanTimer);
    
    // Cleanup SSE
    this.cleanupSSE();
    
    // Reset state flags
    this.scanCompleteProcessed = false;
    this.sseConnected = false;
  }
  
  setupGlobalErrorHandling() {
    // Store original alert function
    this.originalAlert = window.alert;
    
    // Global error handler to prevent unwanted alerts
    window.addEventListener('error', (event) => {
      console.error('Global error caught:', event.error);
      // Don't show alert for network errors during report generation
      if (event.error?.message?.includes('Failed to fetch') || 
          event.error?.message?.includes('Network Error') ||
          event.error?.message?.includes('ERR_CONNECTION_TIMED_OUT')) {
        event.preventDefault();
        this.showNotification('⚠️ Errore di connessione temporaneo', 'warning');
        return false;
      }
    });
    
    // Override alert during critical operations
    this.preventAlerts = false;
  }
  
  setAlertPrevention(prevent) {
    this.preventAlerts = prevent;
    if (prevent) {
      window.alert = (msg) => {
        console.warn('Alert prevented:', msg);
        this.showNotification(msg, 'error');
        return;
      };
    } else {
      window.alert = this.originalAlert;
    }
  }
  
  bindEvents() {
    // Configuration phase
    document.getElementById('start-discovery')?.addEventListener('click', () => this.startDiscovery());
    
    // LLM Configuration events (now after scanning)
    document.getElementById('llm_enabled_post')?.addEventListener('change', (e) => this.toggleLLMConfigPost(e.target.checked));
    document.getElementById('llm_model_post')?.addEventListener('change', (e) => this.updateModelInfoPost(e.target.value));
    document.getElementById('openai_api_key_post')?.addEventListener('input', (e) => {
      // Debounce API key validation
      clearTimeout(this.apiKeyValidationTimeoutPost);
      this.apiKeyValidationTimeoutPost = setTimeout(() => {
        this.validateApiKeyPost(e.target.value);
      }, 800);
    });
    document.getElementById('regeneration_model')?.addEventListener('change', (e) => this.updateRegenerationCost(e.target.value));
    document.getElementById('modal_regeneration_model')?.addEventListener('change', (e) => this.updateModalCost(e.target.value));
    
    // Generate report button
    window.generateReport = () => this.generateReportWithConfig();
    window.toggleApiKeyVisibilityPost = () => this.toggleApiKeyVisibilityPost();
    window.proceedToReport = () => this.proceedToReport();
    
    // Selection phase
    document.getElementById('select-all-cb')?.addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));
    document.getElementById('start-scan')?.addEventListener('click', () => this.startAccessibilityScan());
    document.getElementById('url-search')?.addEventListener('input', (e) => this.filterUrls(e.target.value));
    document.getElementById('page-type-filter')?.addEventListener('change', (e) => this.filterByType(e.target.value));
    
    // Smart selection
    window.selectAll = () => this.selectAllUrls();
    window.deselectAll = () => this.deselectAllUrls();
    window.smartSelect = () => this.performSmartSelection();
    window.addManualUrls = () => this.addManualUrls();
    window.backToConfig = () => this.initializePhase(1);
    
    // Report actions
    window.generatePDF = () => this.generatePDF();
    window.downloadHTML = () => this.downloadHTML();
    window.sendEmail = () => this.sendReportEmail();
    window.viewFullscreen = () => this.viewReportFullscreen();
    window.startNewScan = () => this.resetAndRestart();
    
    // LLM functions
    window.toggleApiKeyVisibility = () => this.toggleApiKeyVisibility();
    window.regenerateWithLLM = () => this.showRegenerationModal();
    window.startLLMRegeneration = () => this.startLLMRegeneration();
    window.toggleReportComparison = () => this.toggleReportComparison();
    window.syncScrolling = (enable) => this.syncScrolling(enable);
    window.downloadBothReports = () => this.downloadBothReports();
    
    // Advanced actions
    window.viewAnalytics = () => this.viewAnalytics();
    window.viewRemediation = () => this.viewRemediation();
    window.viewStatement = () => this.viewStatement();
    window.exportData = () => this.exportData();
    
    // Modal actions
    window.closeModal = () => this.closeModal();
    window.applySmartSelection = () => this.applySmartSelection();
    
    // Auto-save configuration
    document.querySelectorAll('input, select, textarea').forEach(element => {
      element.addEventListener('change', () => this.saveConfig());
    });
    
    // Setup real-time validation
    this.setupRealTimeValidation();
    
    // Enhance form with progressive features
    this.enhanceFormWithProgressiveFeatures();
  }
  
  // ============= PHASE MANAGEMENT =============
  
  initializePhase(phase) {
    console.log('Initializing phase:', phase);
    this.currentPhase = phase;
    
    // Hide all phases
    document.querySelectorAll('.phase-section').forEach(section => {
      section.classList.remove('active');
    });
    
    // Show current phase
    const phaseId = this.getPhaseId(phase);
    console.log('Phase ID:', phaseId);
    const phaseSection = document.getElementById(phaseId);
    if (phaseSection) {
      phaseSection.classList.add('active');
      console.log('Phase activated:', phaseId);
    } else {
      console.error('Phase section not found:', phaseId);
    }
    
    // Update stepper
    this.updateStepper(phase);
  }
  
  getPhaseId(phase) {
    const phaseMap = {
      1: 'phase-config',
      2: 'phase-discovery',
      3: 'phase-selection',
      4: 'phase-scanning',
      5: 'phase-report'
    };
    return phaseMap[phase];
  }
  
  updateStepper(currentStep) {
    document.querySelectorAll('.step').forEach((step, index) => {
      const stepNum = index + 1;
      step.classList.remove('active', 'completed');
      
      if (stepNum < currentStep) {
        step.classList.add('completed');
      } else if (stepNum === currentStep) {
        step.classList.add('active');
      }
    });
  }
  
  // ============= PHASE 1: DISCOVERY =============
  
  async startDiscovery() {
    const config = this.getDiscoveryConfig();
    
    if (!this.validateDiscoveryConfig(config)) {
      return;
    }
    
    // Save configuration
    this.saveConfig();
    
    // Move to discovery phase
    this.initializePhase(2);
    
    // Start discovery timer
    this.discoveryStartTime = Date.now();
    this.startDiscoveryTimer();
    
    try {
      // Call backend to start discovery
      const response = await fetch('/api/discovery/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          base_url: config.url,
          max_pages: config.max_pages,
          max_depth: config.max_depth,
          discovery_mode: config.discovery_mode,
          company_name: config.company_name,
          email: config.email
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to start discovery');
      }
      
      const result = await response.json();
      this.discoverySession = result.session_id;
      
      // Start polling for discovery status
      this.startDiscoveryPolling();
      
    } catch (error) {
      console.error('Discovery error:', error);
      this.showNotification('Errore avvio discovery: ' + error.message, 'error');
      this.initializePhase(1);
    }
  }
  
  getDiscoveryConfig() {
    return {
      url: document.getElementById('url')?.value?.trim(),
      company_name: document.getElementById('company_name')?.value?.trim(),
      email: document.getElementById('email')?.value?.trim(),
      discovery_mode: document.getElementById('discovery_mode')?.value || 'smart',
      max_pages: parseInt(document.getElementById('max_pages')?.value) || 50,
      max_depth: parseInt(document.getElementById('max_depth')?.value) || 3,
      scan_mode: document.getElementById('scan_mode')?.value || 'simulate',
      scanners: {
        wave: document.querySelector('input[value="wave"]')?.checked || false,
        pa11y: document.querySelector('input[value="pa11y"]')?.checked || false,
        axe_core: document.querySelector('input[value="axe_core"]')?.checked || false,
        lighthouse: document.querySelector('input[value="lighthouse"]')?.checked || false
      },
      llm: {
        enabled: document.getElementById('llm_enabled')?.checked || false,
        model: document.getElementById('llm_model')?.value || 'gpt-4o',
        api_key: document.getElementById('openai_api_key')?.value?.trim() || ''
      }
    };
  }
  
  validateDiscoveryConfig(config) {
    const errors = [];
    
    if (!config.url) {
      errors.push('URL è obbligatorio');
    } else if (!this.isValidUrl(config.url)) {
      errors.push('URL non valido');
    }
    
    if (!config.company_name) {
      errors.push('Nome azienda è obbligatorio');
    }
    
    if (!config.email) {
      errors.push('Email è obbligatoria');
    } else if (!this.isValidEmail(config.email)) {
      errors.push('Email non valida');
    }
    
    if (errors.length > 0) {
      this.showNotification(errors.join(', '), 'error');
      return false;
    }
    
    return true;
  }
  
  startDiscoveryTimer() {
    this.discoveryTimer = setInterval(() => {
      const elapsed = Date.now() - this.discoveryStartTime;
      const seconds = Math.floor(elapsed / 1000);
      document.getElementById('discovery-time').textContent = `Tempo: ${seconds}s`;
    }, 1000);
  }
  
  startDiscoveryPolling() {
    this.discoveryPollInterval = setInterval(() => {
      this.pollDiscoveryStatus();
    }, 1000);
  }
  
  async pollDiscoveryStatus() {
    if (!this.discoverySession) return;
    
    try {
      const response = await fetch(`/api/discovery/status/${this.discoverySession}`);
      
      if (!response.ok) {
        throw new Error('Failed to get discovery status');
      }
      
      const status = await response.json();
      this.updateDiscoveryProgress(status);
      
      if (status.state === 'completed') {
        this.handleDiscoveryComplete();
      } else if (status.state === 'failed') {
        this.handleDiscoveryError(status.error);
      }
      
    } catch (error) {
      console.error('Discovery poll error:', error);
    }
  }
  
  updateDiscoveryProgress(status) {
    // Update progress bar
    const progressFill = document.querySelector('#phase-discovery .progress-fill');
    const progressPercentage = document.querySelector('#phase-discovery .progress-percentage');
    const pagesFound = document.getElementById('pages-found');
    
    if (progressFill) {
      progressFill.style.width = `${status.progress_percent || 0}%`;
    }
    
    if (progressPercentage) {
      progressPercentage.textContent = `${status.progress_percent || 0}%`;
    }
    
    if (pagesFound) {
      pagesFound.textContent = `${status.pages_discovered || 0} pagine trovate`;
    }
    
    // Update live feed with discovered URLs
    if (status.discovered_pages) {
      this.updateLiveFeed(status.discovered_pages);
    }
  }
  
  updateLiveFeed(pages) {
    const liveUrlsList = document.getElementById('live-urls');
    if (!liveUrlsList) return;
    
    // Clear and rebuild the list
    liveUrlsList.innerHTML = pages.slice(-10).map(page => `
      <div class="live-url-item">
        <span class="url-path">${this.escapeHtml(page.url)}</span>
        <span class="url-type">${page.page_type || 'general'}</span>
      </div>
    `).join('');
    
    // Store discovered URLs
    this.discoveredUrls = pages;
  }
  
  async handleDiscoveryComplete() {
    // Stop polling and timer
    clearInterval(this.discoveryPollInterval);
    clearInterval(this.discoveryTimer);
    
    // Get final results
    try {
      const response = await fetch(`/api/discovery/results/${this.discoverySession}`);
      
      if (!response.ok) {
        throw new Error('Failed to get discovery results');
      }
      
      const results = await response.json();
      this.discoveredUrls = results.discovered_pages || [];
      
      // Move to selection phase
      this.initializePhase(3);
      this.populateUrlsTable();
      
      this.showNotification(`Discovery completato! ${this.discoveredUrls.length} pagine trovate`, 'success');
      
    } catch (error) {
      console.error('Error getting discovery results:', error);
      this.showNotification('Errore recupero risultati discovery', 'error');
    }
  }
  
  handleDiscoveryError(error) {
    clearInterval(this.discoveryPollInterval);
    clearInterval(this.discoveryTimer);
    
    this.showNotification(`Errore discovery: ${error}`, 'error');
    this.initializePhase(1);
  }
  
  // ============= PHASE 2: SELECTION =============
  
  populateUrlsTable() {
    const tbody = document.getElementById('urls-list');
    if (!tbody) return;
    
    const totalUrls = document.getElementById('total-urls');
    if (totalUrls) {
      totalUrls.textContent = `${this.discoveredUrls.length} pagine trovate`;
    }
    
    tbody.innerHTML = this.discoveredUrls.map((page, index) => `
      <tr data-url="${this.escapeHtml(page.url)}" data-type="${page.page_type}">
        <td>
          <input type="checkbox" class="url-checkbox" value="${index}" onchange="scanner.updateSelection()">
        </td>
        <td class="url-cell">${this.escapeHtml(page.url)}</td>
        <td>${this.escapeHtml(page.title || 'Senza titolo')}</td>
        <td>
          <span class="url-type">${page.page_type || 'general'}</span>
        </td>
        <td>
          <span class="url-priority priority-${this.getPriorityClass(page.priority)}">
            ${this.getPriorityLabel(page.priority)}
          </span>
        </td>
        <td>
          ${this.renderPageElements(page.elements)}
        </td>
      </tr>
    `).join('');
  }
  
  getPriorityClass(priority) {
    if (priority >= 80) return 'high';
    if (priority >= 50) return 'medium';
    return 'low';
  }
  
  getPriorityLabel(priority) {
    if (priority >= 80) return 'Alta';
    if (priority >= 50) return 'Media';
    return 'Bassa';
  }
  
  renderPageElements(elements) {
    if (!elements) return '-';
    
    const parts = [];
    if (elements.forms > 0) parts.push(`${elements.forms} form`);
    if (elements.inputs > 0) parts.push(`${elements.inputs} input`);
    if (elements.images > 0) parts.push(`${elements.images} img`);
    
    return parts.join(', ') || '-';
  }
  
  updateSelection() {
    const checkboxes = document.querySelectorAll('.url-checkbox:checked');
    this.selectedUrls = Array.from(checkboxes).map(cb => {
      const index = parseInt(cb.value);
      return this.discoveredUrls[index];
    });
    
    // Update counter
    document.getElementById('selected-urls').textContent = `${this.selectedUrls.length} selezionate`;
    document.getElementById('scan-count').textContent = this.selectedUrls.length;
    
    // Enable/disable scan button
    const scanButton = document.getElementById('start-scan');
    if (scanButton) {
      scanButton.disabled = this.selectedUrls.length === 0;
    }
  }
  
  toggleSelectAll(checked) {
    document.querySelectorAll('.url-checkbox').forEach(cb => {
      cb.checked = checked;
    });
    this.updateSelection();
  }
  
  selectAllUrls() {
    this.toggleSelectAll(true);
  }
  
  deselectAllUrls() {
    this.toggleSelectAll(false);
  }
  
  performSmartSelection() {
    // Use WCAG-EM methodology to select representative pages
    const smartSelection = this.calculateSmartSelection();
    
    // Show modal with smart selection
    const modal = document.getElementById('smart-selection-modal');
    const list = document.getElementById('smart-selection-list');
    
    if (modal && list) {
      list.innerHTML = smartSelection.map(page => `
        <li>${this.escapeHtml(page.url)} - ${page.reason}</li>
      `).join('');
      
      modal.classList.add('active');
      
      // Store smart selection for later
      this.pendingSmartSelection = smartSelection;
    }
  }
  
  calculateSmartSelection() {
    const selection = [];
    const pageTypes = {};
    
    // Always include homepage
    const homepage = this.discoveredUrls.find(p => p.page_type === 'homepage');
    if (homepage) {
      selection.push({...homepage, reason: 'Homepage (obbligatoria)'});
    }
    
    // Include high priority pages
    const highPriority = this.discoveredUrls
      .filter(p => p.priority >= 80 && p.page_type !== 'homepage')
      .slice(0, 3);
    
    highPriority.forEach(page => {
      selection.push({...page, reason: 'Alta priorità'});
    });
    
    // Include one of each page type
    this.discoveredUrls.forEach(page => {
      if (!pageTypes[page.page_type] && !selection.find(p => p.url === page.url)) {
        pageTypes[page.page_type] = page;
      }
    });
    
    Object.values(pageTypes).forEach(page => {
      if (!selection.find(p => p.url === page.url)) {
        selection.push({...page, reason: `Tipo: ${page.page_type}`});
      }
    });
    
    // Include pages with forms
    const formPages = this.discoveredUrls
      .filter(p => p.elements?.forms > 0 && !selection.find(s => s.url === p.url))
      .slice(0, 2);
    
    formPages.forEach(page => {
      selection.push({...page, reason: 'Contiene form'});
    });
    
    // Limit to max 10-15 pages for efficiency
    return selection.slice(0, 15);
  }
  
  applySmartSelection() {
    if (!this.pendingSmartSelection) return;
    
    // Deselect all first
    this.deselectAllUrls();
    
    // Select smart selection
    this.pendingSmartSelection.forEach(page => {
      const index = this.discoveredUrls.findIndex(p => p.url === page.url);
      if (index >= 0) {
        const checkbox = document.querySelector(`.url-checkbox[value="${index}"]`);
        if (checkbox) {
          checkbox.checked = true;
        }
      }
    });
    
    this.updateSelection();
    this.closeModal();
    this.showNotification('Selezione smart applicata', 'success');
  }
  
  closeModal() {
    document.querySelectorAll('.modal').forEach(modal => {
      modal.classList.remove('active');
    });
  }
  
  filterUrls(searchTerm) {
    const rows = document.querySelectorAll('#urls-list tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
      const url = row.dataset.url?.toLowerCase() || '';
      const visible = url.includes(term);
      row.style.display = visible ? '' : 'none';
    });
  }
  
  filterByType(type) {
    const rows = document.querySelectorAll('#urls-list tr');
    
    rows.forEach(row => {
      const pageType = row.dataset.type;
      const visible = !type || pageType === type;
      row.style.display = visible ? '' : 'none';
    });
  }
  
  addManualUrls() {
    const textarea = document.getElementById('manual-urls-input');
    if (!textarea) return;
    
    const urls = textarea.value
      .split('\n')
      .map(url => url.trim())
      .filter(url => url && this.isValidUrl(url));
    
    urls.forEach(url => {
      // Check if URL already exists
      if (!this.discoveredUrls.find(p => p.url === url)) {
        this.discoveredUrls.push({
          url: url,
          title: 'Manuale',
          page_type: 'manual',
          priority: 50,
          elements: {}
        });
      }
    });
    
    // Refresh table
    this.populateUrlsTable();
    textarea.value = '';
    
    this.showNotification(`${urls.length} URL aggiunti manualmente`, 'success');
  }
  
  // ============= PHASE 3: SCANNING =============
  
  async startAccessibilityScan() {
    if (this.selectedUrls.length === 0) {
      this.showNotification('Seleziona almeno una pagina da scansionare', 'warning');
      return;
    }
    
    // Move to scanning phase
    try {
      this.initializePhase(4);
    } catch (error) {
      console.error('Error initializing phase 4:', error);
    }
    
    // Initialize scan UI
    this.initializeScanProgress();
    
    // Start scan timer
    this.scanStartTime = Date.now();
    
    try {
      const config = this.getDiscoveryConfig();
      
      // Send selected URLs to backend for scanning
      const response = await fetch('/api/scan/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          pages: this.selectedUrls.map(p => p.url),
          company_name: config.company_name,
          email: config.email,
          mode: config.scan_mode,
          scanners: config.scanners,
          discovery_session_id: this.discoverySession
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to start scan');
      }
      
      const result = await response.json();
      this.scanSession = result.session_id;
      
      // Initialize SSE monitor as primary system
      this.initializeSSEMonitor();
      
      // Start polling as fallback only if SSE fails
      setTimeout(() => {
        if (!this.sseConnected) {
          console.warn('SSE failed to connect, falling back to polling');
          this.startScanPolling();
        }
      }, 5000);
      
    } catch (error) {
      console.error('Scan error:', error);
      this.showNotification('Errore avvio scansione: ' + error.message, 'error');
      this.initializePhase(3);
    }
  }
  
  initializeScanProgress() {
    // Clear previous progress
    document.getElementById('pages-status').innerHTML = '';
    document.getElementById('scan-log-content').innerHTML = '';
    
    // Reset metrics
    document.getElementById('errors-found').textContent = '0';
    document.getElementById('warnings-found').textContent = '0';
    document.getElementById('pages-completed').textContent = '0';
    document.getElementById('compliance-score').textContent = '--';
    
    // Create progress cards for each selected URL
    const pagesStatus = document.getElementById('pages-status');
    if (pagesStatus) {
      this.selectedUrls.forEach((page, index) => {
        const card = document.createElement('div');
        card.className = 'page-status-card';
        card.id = `page-status-${index}`;
        card.innerHTML = `
          <div class="page-url">${this.escapeHtml(this.truncateUrl(page.url))}</div>
          <div class="page-progress">
            <span class="status-icon">⏳</span>
            <span class="status-text">In attesa...</span>
          </div>
        `;
        pagesStatus.appendChild(card);
      });
    }
  }
  
  // ============= SSE MONITOR METHODS =============
  
  initializeSSEMonitor() {
    // Initialize the SSE monitor
    if (typeof window.initScanMonitor === 'function') {
      try {
        console.log(`🔌 Initializing SSE monitor for scan: ${this.scanSession}`);
        this.sseMonitor = window.initScanMonitor(this.scanSession, 'scan-monitor');
        
        // Setup SSE event handlers
        this.setupSSEHandlers();
        
      } catch (error) {
        console.error('Failed to initialize SSE monitor:', error);
        this.sseConnected = false;
      }
    } else {
      console.error('initScanMonitor function not available');
      this.sseConnected = false;
    }
  }
  
  setupSSEHandlers() {
    if (!this.sseMonitor) return;
    
    // Override the handleEvent method to integrate with our UI
    const originalHandleEvent = this.sseMonitor.handleEvent.bind(this.sseMonitor);
    
    this.sseMonitor.handleEvent = (event) => {
      // Call the original handler first
      originalHandleEvent(event);
      
      // Now handle our specific events
      this.handleSSEEvent(event);
    };
    
    // Monitor connection status
    const originalConnect = this.sseMonitor.connect.bind(this.sseMonitor);
    this.sseMonitor.connect = () => {
      originalConnect();
      
      // Setup connection monitoring
      setTimeout(() => {
        if (this.sseMonitor && this.sseMonitor.isConnected) {
          this.sseConnected = true;
          console.log('✅ SSE monitor connected successfully');
        } else {
          this.sseConnected = false;
          console.warn('⚠️ SSE monitor failed to connect');
        }
      }, 2000);
    };
    
    // Reconnect the monitor
    this.sseMonitor.connect();
  }
  
  handleSSEEvent(event) {
    const { event_type, data, message } = event;
    
    console.log(`📵 SSE Event: ${event_type}`, { data, message });
    
    switch (event_type) {
      case 'scan_start':
        this.handleScanStartEvent(data);
        break;
        
      case 'page_progress':
        this.handlePageProgressEvent(data);
        break;
        
      case 'scanner_operation':
        this.handleScannerOperationEvent(data);
        break;
        
      case 'scanner_complete':
        this.handleScannerCompleteEvent(data);
        break;
        
      case 'scan_complete':
        this.handleScanComplete(data);
        break;
        
      case 'scan_failed':
        this.handleScanFailedEvent(data);
        break;
        
      default:
        console.log(`Unhandled SSE event: ${event_type}`);
    }
  }
  
  handleScanStartEvent(data) {
    const { company_name, url } = data || {};
    this.showNotification(`🚀 Avvio scansione: ${company_name || 'sito web'}`, 'info');
  }
  
  handlePageProgressEvent(data) {
    const { current_page, total_pages, current_url } = data || {};
    
    // Update main progress
    const progressPercent = total_pages > 0 ? Math.round((current_page / total_pages) * 100) : 0;
    this.updateMainProgress(progressPercent);
    
    // Update pages count
    const pagesProgressEl = document.getElementById('pages-progress');
    if (pagesProgressEl) {
      pagesProgressEl.textContent = `${current_page}/${total_pages} pagine`;
    }
    
    // Update current page status
    if (current_url) {
      this.updatePageStatus(current_url, 'scanning');
    }
  }
  
  handleScannerOperationEvent(data) {
    const { scanner, operation, url } = data || {};
    
    // Update scanner card if it exists in the monitor
    if (scanner && operation) {
      this.showNotification(`🔍 ${scanner}: ${operation}`, 'info');
    }
  }
  
  handleScannerCompleteEvent(data) {
    const { scanner, url, success } = data || {};
    
    if (url) {
      this.updatePageStatus(url, success ? 'completed' : 'error');
    }
    
    // Update metrics
    if (success && data.errors !== undefined) {
      this.updateMetrics(data);
    }
  }
  
  handleScanFailedEvent(data) {
    const { error } = data || {};
    this.cleanupSSE();
    clearInterval(this.scanPollInterval);
    
    this.showNotification(`❌ Scansione fallita: ${error || 'Errore sconosciuto'}`, 'error');
    
    // Reset flag to allow retry
    this.scanCompleteProcessed = false;
  }
  
  updateMainProgress(percent) {
    const progressBar = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-percentage');
    
    if (progressBar) {
      progressBar.style.width = `${percent}%`;
    }
    
    if (progressText) {
      progressText.textContent = `${percent}%`;
    }
  }
  
  updatePageStatus(url, status) {
    // Find the page card and update its status
    const pageCards = document.querySelectorAll('.page-status-card');
    
    pageCards.forEach(card => {
      const pageUrl = card.querySelector('.page-url')?.textContent;
      if (pageUrl && url.includes(pageUrl.replace('...', ''))) {
        const statusIcon = card.querySelector('.status-icon');
        const statusText = card.querySelector('.status-text');
        
        if (statusIcon && statusText) {
          switch (status) {
            case 'scanning':
              statusIcon.textContent = '🔍';
              statusText.textContent = 'Scansione...';
              card.className = 'page-status-card scanning';
              break;
            case 'completed':
              statusIcon.textContent = '✅';
              statusText.textContent = 'Completata';
              card.className = 'page-status-card completed';
              break;
            case 'error':
              statusIcon.textContent = '❌';
              statusText.textContent = 'Errore';
              card.className = 'page-status-card error';
              break;
          }
        }
      }
    });
  }
  
  updateMetrics(data) {
    const { errors = 0, warnings = 0, compliance_score } = data;
    
    const errorsEl = document.getElementById('errors-found');
    const warningsEl = document.getElementById('warnings-found');
    const complianceEl = document.getElementById('compliance-score');
    
    if (errorsEl) errorsEl.textContent = errors;
    if (warningsEl) warningsEl.textContent = warnings;
    if (complianceEl && compliance_score !== undefined) {
      complianceEl.textContent = `${compliance_score}%`;
    }
    
    // Update pages completed count
    const completedPages = document.querySelectorAll('.page-status-card.completed').length;
    const pagesCompletedEl = document.getElementById('pages-completed');
    if (pagesCompletedEl) {
      pagesCompletedEl.textContent = completedPages;
    }
  }
  
  cleanupSSE() {
    if (this.sseMonitor) {
      console.log('🗑️ Cleaning up SSE monitor');
      if (typeof this.sseMonitor.disconnect === 'function') {
        this.sseMonitor.disconnect();
      }
      this.sseMonitor = null;
      this.sseConnected = false;
    }
  }
  
  sseFailure() {
    console.warn('⚠️ SSE failed completely, enabling polling fallback');
    this.sseConnected = false;
    if (!this.scanPollInterval) {
      this.startScanPolling();
    }
  }
  
  // ============= POLLING FALLBACK =============
  
  startScanPolling() {
    console.log('🔄 Starting polling fallback');
    this.scanPollInterval = setInterval(() => {
      this.pollScanStatus();
    }, 2000); // Slower polling when used as fallback
  }
  
  async pollScanStatus() {
    if (!this.scanSession) return;
    
    try {
      const response = await fetch(`/api/scan/status/${this.scanSession}`);
      
      if (!response.ok) {
        throw new Error('Failed to get scan status');
      }
      
      const status = await response.json();
      this.updateScanProgress(status);
      
      if (status.state === 'completed') {
        this.handleScanComplete();
      } else if (status.state === 'failed') {
        this.handleScanError(status.error);
      }
      
    } catch (error) {
      console.error('Scan poll error:', error);
    }
  }
  
  updateScanProgress(status) {
    // Update main progress
    const progressFill = document.querySelector('#phase-scanning .main-progress .progress-fill');
    const progressPercentage = document.querySelector('#phase-scanning .main-progress .progress-percentage');
    const currentPage = document.getElementById('current-page');
    const scanEta = document.getElementById('scan-eta');
    
    if (progressFill) {
      progressFill.style.width = `${status.progress_percent || 0}%`;
    }
    
    if (progressPercentage) {
      progressPercentage.textContent = `${status.progress_percent || 0}%`;
    }
    
    if (currentPage) {
      currentPage.textContent = `Pagina ${status.current_page || 0} di ${this.selectedUrls.length}`;
    }
    
    // Calculate ETA
    if (this.scanStartTime && status.progress_percent > 0) {
      const elapsed = Date.now() - this.scanStartTime;
      const total = elapsed / (status.progress_percent / 100);
      const remaining = total - elapsed;
      const seconds = Math.ceil(remaining / 1000);
      
      if (scanEta) {
        scanEta.textContent = `Tempo stimato: ${seconds}s`;
      }
    }
    
    // Update page statuses
    if (status.page_statuses) {
      Object.entries(status.page_statuses).forEach(([url, pageStatus]) => {
        const index = this.selectedUrls.findIndex(p => p.url === url);
        if (index >= 0) {
          this.updatePageStatus(index, pageStatus);
        }
      });
    }
    
    // Update metrics
    if (status.metrics) {
      this.updateScanMetrics(status.metrics);
    }
    
    // Update log
    if (status.log) {
      this.updateScanLog(status.log);
    }
  }
  
  updatePageStatus(index, status) {
    const card = document.getElementById(`page-status-${index}`);
    if (!card) return;
    
    const statusIcon = card.querySelector('.status-icon');
    const statusText = card.querySelector('.status-text');
    
    const statusMap = {
      'pending': { icon: '⏳', text: 'In attesa...', class: 'pending' },
      'scanning': { icon: '🔄', text: 'Scansione...', class: 'scanning' },
      'completed': { icon: '✅', text: 'Completato', class: 'completed' },
      'failed': { icon: '❌', text: 'Errore', class: 'failed' }
    };
    
    const statusInfo = statusMap[status] || statusMap['pending'];
    
    if (statusIcon) statusIcon.textContent = statusInfo.icon;
    if (statusText) statusText.textContent = statusInfo.text;
    
    card.className = `page-status-card ${statusInfo.class}`;
  }
  
  updateScanMetrics(metrics) {
    if (metrics.errors !== undefined) {
      document.getElementById('errors-found').textContent = metrics.errors;
    }
    
    if (metrics.warnings !== undefined) {
      document.getElementById('warnings-found').textContent = metrics.warnings;
    }
    
    if (metrics.pages_completed !== undefined) {
      document.getElementById('pages-completed').textContent = metrics.pages_completed;
    }
    
    if (metrics.compliance_score !== undefined) {
      document.getElementById('compliance-score').textContent = `${metrics.compliance_score}%`;
    }
  }
  
  updateScanLog(log) {
    const logContent = document.getElementById('scan-log-content');
    if (!logContent) return;
    
    // Keep only last 50 entries
    const entries = log.slice(-50);
    
    logContent.innerHTML = entries.map(entry => `
      <div class="log-entry">${this.escapeHtml(entry)}</div>
    `).join('');
    
    // Auto-scroll to bottom
    logContent.scrollTop = logContent.scrollHeight;
  }
  
  async handleScanComplete(eventData = null) {
    // Protezione contro chiamate multiple
    if (this.scanCompleteProcessed) {
      console.log('handleScanComplete già processato, ignoro chiamata duplicata');
      return;
    }
    this.scanCompleteProcessed = true;
    
    // Stop polling and cleanup SSE
    clearInterval(this.scanPollInterval);
    this.cleanupSSE();
    
    // Get final results
    try {
      let results;
      
      // If we have event data, use it, otherwise fetch
      if (eventData && eventData.scan_results) {
        results = eventData.scan_results;
      } else {
        const response = await fetch(`/api/scan/results/${this.scanSession}`);
        if (!response.ok) {
          throw new Error('Failed to get scan results');
        }
        results = await response.json();
      }
      
      this.scanResults = results;
      
      // Show notification
      this.showNotification('✅ Scansione completata con successo!', 'success');
      
      // Check if user wants LLM enhancement
      const llmEnabled = document.getElementById('llm_enabled_post')?.checked;
      
      if (llmEnabled) {
        // Show LLM configuration section
        const llmConfigSection = document.getElementById('llm-config-post-scan');
        if (llmConfigSection) {
          llmConfigSection.style.display = 'block';
          this.showNotification('🤖 Configura l\'AI per potenziare il report', 'info');
        }
      } else {
        // Auto-advance to report phase after 3 seconds
        setTimeout(() => {
          this.proceedToReport();
        }, 3000);
      }
      
      // Always show a button to proceed manually
      this.showProceedToReportButton();
      
    } catch (error) {
      console.error('Error getting scan results:', error);
      this.showNotification('Errore recupero risultati scansione', 'error');
      
      // Mantieni nella fase scansione e mostra comunque il pulsante per procedere
      this.showProceedToReportButton();
      
      // Reset flag per permettere retry se necessario
      this.scanCompleteProcessed = false;
    }
  }
  
  proceedToReport() {
    if (this.scanResults) {
      this.initializePhase(5);
      this.displayReport(this.scanResults);
      this.showNotification('📊 Report generato', 'success');
    }
  }
  
  showProceedToReportButton() {
    // Add a prominent button to proceed to report
    const scanPhase = document.getElementById('phase-scanning');
    if (!scanPhase) return;
    
    // Check if button already exists
    if (document.getElementById('proceed-to-report-btn')) return;
    
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'proceed-button-container';
    buttonContainer.style.cssText = `
      text-align: center;
      margin: 30px 0;
      padding: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    `;
    
    buttonContainer.innerHTML = `
      <h3 style="color: white; margin-bottom: 15px;">🎉 Scansione Completata!</h3>
      <button id="proceed-to-report-btn" class="btn btn-large" style="
        background: white;
        color: #667eea;
        padding: 15px 40px;
        font-size: 18px;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        transition: all 0.3s;
      " onclick="window.scannerApp.proceedToReport()">
        📊 Procedi al Report Finale
      </button>
      <p style="color: white; margin-top: 10px; opacity: 0.9;">
        Oppure configura l'AI per un report potenziato
      </p>
    `;
    
    // Insert after scan progress section
    const progressSection = scanPhase.querySelector('.scan-progress');
    if (progressSection) {
      progressSection.after(buttonContainer);
    } else {
      scanPhase.appendChild(buttonContainer);
    }
  }
  
  proceedToReport() {
    if (!this.scanResults) {
      this.showNotification('⚠️ Attendere il caricamento dei risultati', 'warning');
      return;
    }
    
    this.initializePhase(5);
    this.displayReport(this.scanResults);
    this.showNotification('📊 Visualizzazione report', 'success');
  }
  
  handleScanError(error) {
    clearInterval(this.scanPollInterval);
    
    this.showNotification(`Errore scansione: ${error}`, 'error');
    
    // Per ora procedi comunque al report con dati simulati
    console.warn('Scan failed but proceeding with simulated data');
    
    // Simula risultati per testing
    const simulatedResults = {
      total_errors: 15,
      total_warnings: 23,
      compliance_score: 75,
      scan_id: this.scanSession,
      report_url: '#'
    };
    
    // Procedi al report
    this.initializePhase(5);
    this.displayReport(simulatedResults);
  }
  
  // ============= PHASE 4: REPORT =============
  
  displayReport(results) {
    // Store original report
    this.originalReport = results;
    
    // Update compliance status
    const complianceStatus = document.getElementById('compliance-status');
    if (complianceStatus) {
      const status = results.compliance_status || 'unknown';
      const statusMap = {
        'compliant': { text: 'CONFORME', class: 'compliant' },
        'partially_compliant': { text: 'PARZIALMENTE CONFORME', class: 'partial' },
        'non_compliant': { text: 'NON CONFORME', class: 'non-compliant' }
      };
      
      const statusInfo = statusMap[status] || { text: 'SCONOSCIUTO', class: 'unknown' };
      complianceStatus.innerHTML = statusInfo.text;
      complianceStatus.className = `compliance-badge ${statusInfo.class}`;
    }
    
    // Update score
    const finalScore = document.getElementById('final-score');
    if (finalScore) {
      finalScore.textContent = `${results.compliance_score || 0}/100`;
    }
    
    // Update summary stats
    document.getElementById('total-errors').textContent = results.total_errors || 0;
    document.getElementById('total-warnings').textContent = results.total_warnings || 0;
    document.getElementById('total-pages').textContent = this.selectedUrls.length;
    
    // Load report in iframe with error handling
    this.loadReportInIframe();
    
    // Show LLM regeneration section if enabled
    this.updateLLMRegenerationVisibility();
  }
  
  loadReportInIframe() {
    const reportFrame = document.getElementById('report-frame');
    if (!reportFrame || !this.scanSession) return;
    
    // Prevent alerts during iframe loading
    this.setAlertPrevention(true);
    
    // Add error handling for iframe
    reportFrame.addEventListener('error', (e) => {
      console.error('Report iframe error:', e);
      this.showReportErrorMessage('Errore caricamento report. Riprova più tardi.');
      this.setAlertPrevention(false);
    });
    
    reportFrame.addEventListener('load', () => {
      console.log('Report iframe loaded successfully');
      this.setAlertPrevention(false);
      
      // Try to override alert in iframe context
      try {
        if (reportFrame.contentWindow) {
          reportFrame.contentWindow.alert = function(msg) {
            console.warn('Iframe alert prevented:', msg);
            return;
          };
        }
      } catch(e) {
        // Cross-origin restriction, ignore
      }
    });
    
    // Set iframe source with error prevention
    try {
      reportFrame.src = `/v2/preview?scan_id=${this.scanSession}`;
    } catch(e) {
      console.error('Error setting iframe src:', e);
      this.showReportErrorMessage('Errore caricamento report.');
      this.setAlertPrevention(false);
    }
  }
  
  showReportErrorMessage(message) {
    const reportFrame = document.getElementById('report-frame');
    if (reportFrame) {
      reportFrame.style.display = 'none';
      
      // Create error message
      let errorDiv = document.getElementById('report-error-message');
      if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'report-error-message';
        errorDiv.style.cssText = `
          padding: 20px;
          background: #fff3cd;
          border: 1px solid #ffeaa7;
          border-radius: 5px;
          color: #856404;
          text-align: center;
          font-weight: bold;
        `;
        reportFrame.parentNode.insertBefore(errorDiv, reportFrame);
      }
      
      errorDiv.innerHTML = `
        <div>⚠️ ${message}</div>
        <button onclick="location.reload()" style="margin-top: 10px; padding: 5px 15px;">
          🔄 Ricarica Pagina
        </button>
      `;
    }
  }
  
  async generatePDF() {
    if (!this.scanSession) return;
    
    try {
      const response = await fetch(`/api/generate_pdf/${this.scanSession}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }
      
      const result = await response.json();
      
      if (result.pdf_url) {
        window.open(result.pdf_url, '_blank');
        this.showNotification('PDF generato con successo', 'success');
      }
      
    } catch (error) {
      console.error('PDF generation error:', error);
      this.showNotification('Errore generazione PDF', 'error');
    }
  }
  
  downloadHTML() {
    if (this.scanResults?.report_html_url) {
      window.open(this.scanResults.report_html_url, '_blank');
    }
  }
  
  sendReportEmail() {
    // TODO: Implement email sending
    this.showNotification('Funzione email in sviluppo', 'info');
  }
  
  viewReportFullscreen() {
    const frame = document.getElementById('report-frame');
    if (frame && frame.requestFullscreen) {
      frame.requestFullscreen();
    }
  }
  
  viewAnalytics() {
    if (this.scanResults?.analytics_url) {
      window.open(this.scanResults.analytics_url, '_blank');
    }
  }
  
  viewRemediation() {
    if (this.scanResults?.remediation_url) {
      window.open(this.scanResults.remediation_url, '_blank');
    }
  }
  
  viewStatement() {
    if (this.scanResults?.statement_url) {
      window.open(this.scanResults.statement_url, '_blank');
    }
  }
  
  exportData() {
    if (this.scanResults?.json_url) {
      window.open(this.scanResults.json_url, '_blank');
    }
  }
  
  resetAndRestart() {
    // Reset all data
    this.currentPhase = 1;
    this.discoverySession = null;
    this.scanSession = null;
    this.discoveredUrls = [];
    this.selectedUrls = [];
    this.scanResults = null;
    
    // Clear timers
    clearInterval(this.discoveryTimer);
    clearInterval(this.scanTimer);
    clearInterval(this.discoveryPollInterval);
    clearInterval(this.scanPollInterval);
    
    // Reset to configuration phase
    this.initializePhase(1);
    
    this.showNotification('Pronto per una nuova scansione', 'info');
  }
  
  // ============= LLM CONFIGURATION (POST-SCAN) =============
  
  toggleLLMConfigPost(enabled) {
    const configSection = document.getElementById('llm-config-section-post');
    if (configSection) {
      configSection.style.display = enabled ? 'block' : 'none';
    }
    
    this.llmConfig.enabled = enabled;
    
    if (enabled) {
      // Update cost estimation for selected model
      const model = document.getElementById('llm_model_post')?.value || 'gpt-4o';
      this.updateModelInfoPost(model);
    }
  }
  
  updateModelInfoPost(model) {
    const modelInfo = document.getElementById('model-info-post');
    const costEstimate = document.getElementById('estimated-cost-post');
    const costDetail = document.getElementById('cost-detail-post');
    
    const models = {
      'gpt-5': {
        info: 'GPT-5: Modello unificato più avanzato con reasoning integrato',
        cost: '€2.00 - €5.00',
        tokens: '~20K-50K token per analisi completa'
      },
      'gpt-5-mini': {
        info: 'GPT-5 Mini: Versione ottimizzata per velocità e costi',
        cost: '€0.80 - €2.00',
        tokens: '~20K-50K token per analisi completa'
      },
      'gpt-5-nano': {
        info: 'GPT-5 Nano: Il più veloce ed economico della serie GPT-5',
        cost: '€0.40 - €1.00',
        tokens: '~20K-50K token per analisi completa'
      },
      'o3': {
        info: 'O3: Premium reasoning model, 20% meno errori',
        cost: '€8.00 - €15.00',
        tokens: '~20K-50K token per analisi completa'
      },
      'o4-mini': {
        info: 'O4 Mini: Reasoning economico per math e coding',
        cost: '€1.60 - €4.00',
        tokens: '~20K-50K token per analisi completa'
      },
      'gpt-4.1': {
        info: 'GPT-4.1: Context esteso fino a 1M tokens',
        cost: '€3.00 - €8.00',
        tokens: '~20K-100K token per analisi completa'
      },
      'gpt-4.1-mini': {
        info: 'GPT-4.1 Mini: 83% più economico di GPT-4o',
        cost: '€0.50 - €1.20',
        tokens: '~20K-50K token per analisi completa'
      },
      'gpt-4o': {
        info: 'GPT-4o: Modello standard affidabile e bilanciato',
        cost: '€0.80 - €2.50',
        tokens: '~10K-50K token per analisi'
      },
      'gpt-4-turbo-preview': {
        info: 'GPT-4 Turbo: Veloce con buona qualità',
        cost: '€1.50 - €3.00',
        tokens: '~10K-30K token per analisi'
      },
      'gpt-4o-mini': {
        info: 'GPT-4o Mini: Economico per casi semplici',
        cost: '€0.15 - €0.60',
        tokens: '~10K-30K token per analisi'
      },
      'gpt-3.5-turbo': {
        info: 'GPT-3.5 Turbo: Base veloce ed economico',
        cost: '€0.10 - €0.30',
        tokens: '~5K-20K token per analisi'
      }
    };
    
    const modelData = models[model] || models['gpt-4o'];
    
    if (modelInfo) modelInfo.textContent = modelData.info;
    if (costEstimate) costEstimate.textContent = modelData.cost;
    if (costDetail) costDetail.textContent = modelData.tokens;
    
    this.llmConfig.model = model;
  }
  
  async validateApiKeyPost(apiKey) {
    const statusDiv = document.getElementById('api-key-status-post');
    
    if (!apiKey || apiKey.length < 20) {
      if (statusDiv) {
        statusDiv.textContent = '';
        statusDiv.className = 'api-key-status';
        statusDiv.style.display = 'none';
      }
      this.llmConfig.apiKeyValid = false;
      return;
    }
    
    // Simple validation for format
    if (!apiKey.startsWith('sk-')) {
      if (statusDiv) {
        statusDiv.textContent = '❌ Formato chiave non valido';
        statusDiv.className = 'api-key-status error';
        statusDiv.style.display = 'block';
      }
      this.llmConfig.apiKeyValid = false;
      return;
    }
    
    // Show validating status
    if (statusDiv) {
      statusDiv.textContent = '🔄 Validazione chiave API...';
      statusDiv.className = 'api-key-status validating';
      statusDiv.style.display = 'block';
    }
    
    try {
      // Valida con il server usando l'endpoint corretto
      const response = await fetch('/api/llm/validate-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
      });
      
      const result = await response.json();
      
      if (result.valid) {
        this.llmConfig.apiKey = apiKey;
        this.llmConfig.apiKeyValid = true;
        
        if (statusDiv) {
          statusDiv.textContent = '✅ Chiave API valida';
          statusDiv.className = 'api-key-status success';
        }
      } else {
        this.llmConfig.apiKeyValid = false;
        
        if (statusDiv) {
          statusDiv.textContent = '❌ Chiave API non valida';
          statusDiv.className = 'api-key-status error';
        }
      }
    } catch (error) {
      console.error('API key validation error:', error);
      this.llmConfig.apiKeyValid = false;
      
      if (statusDiv) {
        statusDiv.textContent = '❌ Errore validazione';
        statusDiv.className = 'api-key-status error';
      }
    }
  }
  
  toggleApiKeyVisibilityPost() {
    const input = document.getElementById('openai_api_key_post');
    const button = event.target;
    
    if (input.type === 'password') {
      input.type = 'text';
      button.textContent = '🙈';
    } else {
      input.type = 'password';
      button.textContent = '👁️';
    }
  }
  
  // Generate report with optional LLM
  async generateReportWithConfig() {
    const llmEnabled = document.getElementById('llm_enabled_post')?.checked;
    const llmModel = document.getElementById('llm_model_post')?.value;
    const apiKey = document.getElementById('openai_api_key_post')?.value;
    
    // Update button to show loading
    const btn = document.getElementById('generate-report-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '⏳ Generazione report...';
    }
    
    try {
      // Prima recupera i risultati esistenti della scansione
      const scanResponse = await fetch(`/api/scan/results/${this.scanSession}`);
      
      if (!scanResponse.ok) {
        throw new Error('Impossibile recuperare risultati scansione');
      }
      
      const scanResults = await scanResponse.json();
      
      // Se LLM è abilitata E c'è una API key valida, avvia la rigenerazione
      if (llmEnabled && apiKey && apiKey.trim() && this.llmConfig.apiKeyValid) {
        // Avvia rigenerazione LLM
        const regenResponse = await fetch('/api/reports/regenerate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            scan_id: this.scanSession,
            llm_config: {
              enabled: true,
              model: llmModel || 'gpt-4o',
              api_key: apiKey
            },
            sections: ['executive_summary', 'detailed_analysis', 'recommendations'],
            version: 'v2.0'
          })
        });
        
        if (!regenResponse.ok) {
          throw new Error('Errore avvio rigenerazione LLM');
        }
        
        const regenResult = await regenResponse.json();
        
        // Mostra notifica e avvia polling per rigenerazione
        this.showNotification('🤖 Rigenerazione report con AI avviata...', 'info');
        this.pollLLMRegeneration(regenResult.task_id);
      }
      
      // Mostra sempre il report base (sarà aggiornato se c'è rigenerazione LLM)
      this.initializePhase(5);
      this.displayReport(scanResults);
      
      if (!llmEnabled) {
        this.showNotification('✅ Report generato con successo', 'success');
      }
      
    } catch (error) {
      console.error('Report generation error:', error);
      this.showNotification('❌ Errore generazione report: ' + error.message, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = '📊 Genera Report';
      }
    }
  }
  
  // ============= LLM CONFIGURATION (ORIGINAL) =============
  
  toggleLLMConfig(enabled) {
    this.llmConfig.enabled = enabled;
    const section = document.getElementById('llm-config-section');
    
    if (section) {
      section.style.display = enabled ? 'block' : 'none';
    }
    
    // Update cost estimation
    this.updateCostEstimation();
    
    // Save config
    this.saveConfig();
  }
  
  updateModelInfo(model) {
    this.llmConfig.model = model;
    const modelInfo = document.getElementById('model-info');
    
    const modelDescriptions = {
      'gpt-4o': 'Modello bilanciato per qualità e costi - Raccomandato',
      'gpt-4-turbo-preview': 'Prestazioni elevate con velocità ottimizzata',
      'gpt-4o-mini': 'Soluzione economica con buone prestazioni',
      'gpt-3.5-turbo': 'Veloce ed economico per analisi di base'
    };
    
    if (modelInfo) {
      modelInfo.textContent = modelDescriptions[model] || 'Modello selezionato';
    }
    
    this.updateCostEstimation();
  }
  
  async validateApiKey(apiKey) {
    this.llmConfig.apiKey = apiKey;
    const status = document.getElementById('api-key-status');
    
    if (!apiKey || apiKey.length < 20) {
      if (status) {
        status.className = 'api-key-status';
        status.style.display = 'none';
      }
      this.llmConfig.apiKeyValid = false;
      return;
    }
    
    // Show validating status
    if (status) {
      status.className = 'api-key-status validating';
      status.textContent = '🔄 Validazione chiave API...';
    }
    
    try {
      // Debounce validation
      clearTimeout(this.apiKeyValidationTimeout);
      this.apiKeyValidationTimeout = setTimeout(async () => {
        const response = await fetch('/api/validate_openai_key', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ api_key: apiKey })
        });
        
        const result = await response.json();
        
        if (result.valid) {
          this.llmConfig.apiKeyValid = true;
          if (status) {
            status.className = 'api-key-status valid';
            status.textContent = '✅ Chiave API valida';
          }
        } else {
          this.llmConfig.apiKeyValid = false;
          if (status) {
            status.className = 'api-key-status invalid';
            status.textContent = '❌ Chiave API non valida';
          }
        }
      }, 1000);
      
    } catch (error) {
      this.llmConfig.apiKeyValid = false;
      if (status) {
        status.className = 'api-key-status invalid';
        status.textContent = '❌ Errore validazione';
      }
    }
  }
  
  toggleApiKeyVisibility() {
    const input = document.getElementById('openai_api_key');
    const button = document.querySelector('.btn-toggle-password');
    
    if (input && button) {
      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';
      button.textContent = isPassword ? '🙈' : '👁️';
      button.setAttribute('aria-label', isPassword ? 'Nascondi chiave API' : 'Mostra chiave API');
    }
  }
  
  updateCostEstimation() {
    const costValue = document.getElementById('estimated-cost');
    const costDetail = document.getElementById('cost-detail');
    
    if (!this.llmConfig.enabled) {
      if (costValue) costValue.textContent = 'LLM disabilitato';
      if (costDetail) costDetail.textContent = 'Abilita LLM per vedere i costi';
      return;
    }
    
    const costs = {
      'gpt-4o': { min: 0.50, max: 2.00, tokens: '500-2000' },
      'gpt-4-turbo-preview': { min: 0.75, max: 2.50, tokens: '500-2000' },
      'gpt-4o-mini': { min: 0.30, max: 1.50, tokens: '500-2000' },
      'gpt-3.5-turbo': { min: 0.10, max: 0.50, tokens: '500-2000' }
    };
    
    const cost = costs[this.llmConfig.model] || costs['gpt-4o'];
    
    if (costValue) {
      costValue.textContent = `€${cost.min.toFixed(2)} - €${cost.max.toFixed(2)}`;
    }
    
    if (costDetail) {
      costDetail.textContent = `~${cost.tokens} token per analisi`;
    }
  }
  
  updateRegenerationCost(model) {
    const costElement = document.getElementById('regeneration-cost');
    
    const costs = {
      'gpt-4o': '€1.50 - €3.00',
      'gpt-4-turbo-preview': '€2.00 - €4.00',
      'gpt-4o-mini': '€1.00 - €2.50',
      'gpt-3.5-turbo': '€0.50 - €1.50'
    };
    
    if (costElement) {
      costElement.textContent = `Costo stimato: ${costs[model] || costs['gpt-4o']}`;
    }
  }
  
  updateModalCost(model) {
    const costElement = document.getElementById('modal-cost-estimate');
    
    const costs = {
      'gpt-4o': '€1.50 - €3.00',
      'gpt-4-turbo-preview': '€2.00 - €4.00',
      'gpt-4o-mini': '€1.00 - €2.50',
      'gpt-3.5-turbo': '€0.50 - €1.50'
    };
    
    if (costElement) {
      costElement.textContent = costs[model] || costs['gpt-4o'];
    }
  }
  
  updateLLMRegenerationVisibility() {
    const section = document.getElementById('llm-regeneration-section');
    
    if (section) {
      // Show if LLM is enabled and API key is valid
      const showSection = this.llmConfig.enabled && this.llmConfig.apiKeyValid && this.scanResults;
      section.style.display = showSection ? 'block' : 'none';
    }
  }
  
  // ============= LLM REGENERATION =============
  
  showRegenerationModal() {
    if (!this.llmConfig.apiKeyValid) {
      this.showAdvancedNotification(
        'Chiave API non valida',
        'Configura una chiave API OpenAI valida prima di procedere.',
        'warning'
      );
      return;
    }
    
    const modal = document.getElementById('llm-regeneration-modal');
    if (modal) {
      // Reset modal state
      document.getElementById('regeneration-progress').style.display = 'none';
      document.getElementById('regeneration-options').style.display = 'block';
      
      // Set current model
      const modalSelect = document.getElementById('modal_regeneration_model');
      if (modalSelect) {
        modalSelect.value = this.llmConfig.model;
      }
      
      this.updateModalCost(this.llmConfig.model);
      modal.classList.add('active');
    }
  }
  
  async startLLMRegeneration() {
    if (this.regenerationInProgress) return;
    
    this.regenerationInProgress = true;
    
    // Hide options, show progress
    document.getElementById('regeneration-options').style.display = 'none';
    document.getElementById('regeneration-progress').style.display = 'block';
    
    const model = document.getElementById('modal_regeneration_model')?.value || this.llmConfig.model;
    
    try {
      // Start regeneration
      const response = await fetch('/api/llm/regenerate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scan_session_id: this.scanSession,
          model: model,
          api_key: this.llmConfig.apiKey
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to start LLM regeneration');
      }
      
      const result = await response.json();
      
      // Start polling for regeneration progress
      this.pollLLMRegeneration(result.regeneration_id);
      
    } catch (error) {
      console.error('LLM regeneration error:', error);
      this.showAdvancedNotification(
        'Errore rigenerazione',
        error.message || 'Errore durante la rigenerazione del report',
        'error'
      );
      this.closeModal();
      this.regenerationInProgress = false;
    }
  }
  
  async pollLLMRegeneration(regenerationId) {
    const poll = async () => {
      try {
        const response = await fetch(`/api/llm/regeneration_status/${regenerationId}`);
        
        if (!response.ok) {
          throw new Error('Failed to get regeneration status');
        }
        
        const status = await response.json();
        this.updateRegenerationProgress(status);
        
        if (status.state === 'completed') {
          this.handleRegenerationComplete(status);
        } else if (status.state === 'failed') {
          this.handleRegenerationError(status.error);
        } else {
          setTimeout(poll, 2000);
        }
        
      } catch (error) {
        console.error('Regeneration poll error:', error);
        this.handleRegenerationError(error.message);
      }
    };
    
    poll();
  }
  
  updateRegenerationProgress(status) {
    const progressFill = document.getElementById('llm-progress-fill');
    const progressPercent = document.getElementById('llm-progress-percent');
    const currentStep = document.getElementById('llm-current-step');
    
    if (progressFill) {
      progressFill.style.width = `${status.progress_percent || 0}%`;
    }
    
    if (progressPercent) {
      progressPercent.textContent = `${status.progress_percent || 0}%`;
    }
    
    if (currentStep) {
      const steps = {
        'analyzing': 'Analisi dati di accessibilità...',
        'generating': 'Generazione raccomandazioni AI...',
        'enhancing': 'Miglioramento report...',
        'finalizing': 'Finalizzazione...',
        'completed': 'Completato!'
      };
      
      currentStep.textContent = steps[status.current_step] || 'Elaborazione...';
    }
  }
  
  async handleRegenerationComplete(status) {
    this.regenerationInProgress = false;
    this.enhancedReport = status.enhanced_report;
    
    // Close modal
    this.closeModal();
    
    // Show success notification
    this.showAdvancedNotification(
      'Report migliorato!',
      'Il report è stato rigenerato con successo utilizzando l\'intelligenza artificiale.',
      'success'
    );
    
    // Update report viewer with enhanced version
    const reportFrame = document.getElementById('report-frame');
    if (reportFrame && status.enhanced_report_url) {
      reportFrame.src = status.enhanced_report_url;
    }
    
    // Show comparison button
    const compareBtn = document.getElementById('compare-btn');
    if (compareBtn) {
      compareBtn.style.display = 'inline-flex';
    }
  }
  
  handleRegenerationError(error) {
    this.regenerationInProgress = false;
    this.closeModal();
    
    this.showAdvancedNotification(
      'Errore rigenerazione',
      error || 'Si è verificato un errore durante la rigenerazione del report.',
      'error'
    );
  }
  
  // ============= REPORT COMPARISON =============
  
  toggleReportComparison() {
    const modal = document.getElementById('report-comparison-modal');
    if (!modal || !this.originalReport || !this.enhancedReport) return;
    
    // Load both reports in comparison frames
    const originalFrame = document.getElementById('original-report-frame');
    const enhancedFrame = document.getElementById('enhanced-report-frame');
    
    if (originalFrame && this.scanSession) {
      originalFrame.src = `/v2/preview?scan_id=${this.scanSession}&version=original`;
    }
    
    if (enhancedFrame && this.enhancedReport.report_url) {
      enhancedFrame.src = this.enhancedReport.report_url;
    }
    
    modal.classList.add('active');
  }
  
  syncScrolling(enable) {
    const originalFrame = document.getElementById('original-report-frame');
    const enhancedFrame = document.getElementById('enhanced-report-frame');
    const syncBtn = document.getElementById('sync-btn');
    
    if (!originalFrame || !enhancedFrame) return;
    
    if (enable) {
      // Enable scroll synchronization
      this.scrollSyncEnabled = true;
      
      originalFrame.addEventListener('scroll', () => {
        if (this.scrollSyncEnabled) {
          enhancedFrame.scrollTop = originalFrame.scrollTop;
        }
      });
      
      enhancedFrame.addEventListener('scroll', () => {
        if (this.scrollSyncEnabled) {
          originalFrame.scrollTop = enhancedFrame.scrollTop;
        }
      });
      
      if (syncBtn) {
        syncBtn.textContent = '🔗 Sincronizzato';
        syncBtn.onclick = () => this.syncScrolling(false);
      }
      
    } else {
      // Disable scroll synchronization
      this.scrollSyncEnabled = false;
      
      if (syncBtn) {
        syncBtn.textContent = '🔗 Sincronizza Scroll';
        syncBtn.onclick = () => this.syncScrolling(true);
      }
    }
  }
  
  downloadBothReports() {
    // Download original report
    if (this.scanSession) {
      window.open(`/api/download_report/${this.scanSession}?version=original`, '_blank');
    }
    
    // Download enhanced report
    if (this.enhancedReport?.download_url) {
      window.open(this.enhancedReport.download_url, '_blank');
    }
  }
  
  // ============= ADVANCED NOTIFICATIONS =============
  
  showAdvancedNotification(title, message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    
    notification.innerHTML = `
      <span class="icon">${icons[type] || icons.info}</span>
      <div class="notification-content">
        <div class="notification-title">${this.escapeHtml(title)}</div>
        <div class="notification-message">${this.escapeHtml(message)}</div>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 8 seconds for advanced notifications
    setTimeout(() => {
      notification.remove();
    }, 8000);
    
    // Click to dismiss
    notification.addEventListener('click', () => {
      notification.remove();
    });
  }
  
  // ============= ACCESSIBILITY & UX ENHANCEMENTS =============
  
  initTooltips() {
    // Initialize tooltips with keyboard support
    document.querySelectorAll('.tooltip').forEach(tooltip => {
      tooltip.setAttribute('tabindex', '0');
      
      // Show on focus (keyboard)
      tooltip.addEventListener('focus', () => {
        this.showTooltip(tooltip);
      });
      
      // Hide on blur
      tooltip.addEventListener('blur', () => {
        this.hideTooltip(tooltip);
      });
      
      // Show on mouse enter
      tooltip.addEventListener('mouseenter', () => {
        this.showTooltip(tooltip);
      });
      
      // Hide on mouse leave
      tooltip.addEventListener('mouseleave', () => {
        this.hideTooltip(tooltip);
      });
      
      // Handle escape key
      tooltip.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.hideTooltip(tooltip);
          tooltip.blur();
        }
      });
    });
  }
  
  showTooltip(element) {
    element.classList.add('tooltip-visible');
  }
  
  hideTooltip(element) {
    element.classList.remove('tooltip-visible');
  }
  
  initKeyboardNavigation() {
    // Enhanced keyboard navigation for modals
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeModal();
      }
      
      // Trap focus in modals
      const activeModal = document.querySelector('.modal.active');
      if (activeModal && e.key === 'Tab') {
        this.trapFocus(activeModal, e);
      }
    });
  }
  
  trapFocus(modal, event) {
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }
  
  announceToScreenReader(message, priority = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }
  
  // ============= ENHANCED LOADING STATES =============
  
  showSmartLoading(element, message = 'Caricamento in corso...') {
    if (!element) return;
    
    element.classList.add('smart-loading');
    element.setAttribute('aria-busy', 'true');
    element.setAttribute('aria-label', message);
    
    // Update text content if it's a button
    if (element.tagName === 'BUTTON') {
      element.dataset.originalText = element.textContent;
      element.textContent = message;
      element.disabled = true;
    }
  }
  
  hideSmartLoading(element) {
    if (!element) return;
    
    element.classList.remove('smart-loading');
    element.removeAttribute('aria-busy');
    
    if (element.tagName === 'BUTTON') {
      element.textContent = element.dataset.originalText || element.textContent;
      element.disabled = false;
    }
  }
  
  addLoadingPulse(element) {
    if (element) {
      element.classList.add('pulse-loading');
    }
  }
  
  removeLoadingPulse(element) {
    if (element) {
      element.classList.remove('pulse-loading');
    }
  }
  
  // ============= SMART VALIDATION =============
  
  setupRealTimeValidation() {
    // API Key validation with debouncing
    const apiKeyField = document.getElementById('openai_api_key');
    if (apiKeyField) {
      let validationTimeout;
      
      apiKeyField.addEventListener('input', (e) => {
        clearTimeout(validationTimeout);
        const value = e.target.value;
        
        if (value.length < 20) {
          this.clearApiKeyStatus();
          return;
        }
        
        validationTimeout = setTimeout(() => {
          this.validateApiKey(value);
        }, 800);
      });
    }
    
    // URL validation
    const urlField = document.getElementById('url');
    if (urlField) {
      urlField.addEventListener('blur', (e) => {
        this.validateUrl(e.target.value);
      });
    }
    
    // Email validation
    const emailField = document.getElementById('email');
    if (emailField) {
      emailField.addEventListener('blur', (e) => {
        this.validateEmail(e.target.value);
      });
    }
  }
  
  validateUrl(url) {
    const urlField = document.getElementById('url');
    if (!urlField) return;
    
    if (url && !this.isValidUrl(url)) {
      this.showFieldError(urlField, 'URL non valido. Usa il formato: https://esempio.com');
    } else {
      this.clearFieldError(urlField);
    }
  }
  
  validateEmail(email) {
    const emailField = document.getElementById('email');
    if (!emailField) return;
    
    if (email && !this.isValidEmail(email)) {
      this.showFieldError(emailField, 'Indirizzo email non valido');
    } else {
      this.clearFieldError(emailField);
    }
  }
  
  showFieldError(field, message) {
    this.clearFieldError(field);
    
    field.classList.add('error');
    field.setAttribute('aria-invalid', 'true');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.textContent = message;
    errorDiv.setAttribute('role', 'alert');
    
    field.parentNode.appendChild(errorDiv);
  }
  
  clearFieldError(field) {
    field.classList.remove('error');
    field.removeAttribute('aria-invalid');
    
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
      existingError.remove();
    }
  }
  
  clearApiKeyStatus() {
    const status = document.getElementById('api-key-status');
    if (status) {
      status.className = 'api-key-status';
      status.style.display = 'none';
      status.textContent = '';
    }
  }
  
  // ============= PROGRESSIVE ENHANCEMENT =============
  
  enhanceFormWithProgressiveFeatures() {
    // Add auto-save indicators
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
      input.addEventListener('change', () => {
        this.showAutoSaveIndicator();
        setTimeout(() => this.hideAutoSaveIndicator(), 1500);
      });
    });
    
    // Add intelligent defaults based on URL
    const urlField = document.getElementById('url');
    if (urlField) {
      urlField.addEventListener('blur', (e) => {
        this.suggestConfigFromUrl(e.target.value);
      });
    }
  }
  
  showAutoSaveIndicator() {
    let indicator = document.getElementById('autosave-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'autosave-indicator';
      indicator.className = 'autosave-indicator';
      indicator.innerHTML = '✓ Configurazione salvata';
      document.body.appendChild(indicator);
    }
    
    indicator.style.display = 'block';
  }
  
  hideAutoSaveIndicator() {
    const indicator = document.getElementById('autosave-indicator');
    if (indicator) {
      indicator.style.display = 'none';
    }
  }
  
  suggestConfigFromUrl(url) {
    if (!this.isValidUrl(url)) return;
    
    try {
      const urlObj = new URL(url);
      const domain = urlObj.hostname;
      
      // Suggest company name based on domain
      const companyField = document.getElementById('company_name');
      if (companyField && !companyField.value) {
        const suggestedName = domain.replace('www.', '').split('.')[0];
        const capitalizedName = suggestedName.charAt(0).toUpperCase() + suggestedName.slice(1);
        
        companyField.value = capitalizedName;
        companyField.style.backgroundColor = '#f0fdf4';
        
        setTimeout(() => {
          companyField.style.backgroundColor = '';
        }, 2000);
        
        this.announceToScreenReader(`Nome azienda suggerito: ${capitalizedName}`);
      }
      
    } catch (error) {
      // URL parsing failed, ignore
    }
  }
  
  // ============= UTILITY FUNCTIONS =============
  
  isValidUrl(string) {
    try {
      const url = new URL(string);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
      return false;
    }
  }
  
  isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }
  
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  truncateUrl(url, maxLength = 50) {
    if (url.length <= maxLength) return url;
    
    const parsed = new URL(url);
    const path = parsed.pathname + parsed.search;
    
    if (path.length > 30) {
      return parsed.hostname + '/...' + path.slice(-27);
    }
    
    return parsed.hostname + path;
  }
  
  showNotification(message, type = 'info') {
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    const icons = {
      success: '✅',
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️'
    };
    
    notification.innerHTML = `
      <span class="icon">${icons[type] || icons.info}</span>
      <span>${this.escapeHtml(message)}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Add styles if not present
    if (!document.querySelector('#notification-styles')) {
      const style = document.createElement('style');
      style.id = 'notification-styles';
      style.textContent = `
        .notification {
          position: fixed;
          top: 20px;
          right: 20px;
          padding: 12px 20px;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          display: flex;
          align-items: center;
          gap: 10px;
          z-index: 10000;
          animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        .notification-success { border-left: 4px solid #10b981; }
        .notification-error { border-left: 4px solid #ef4444; }
        .notification-warning { border-left: 4px solid #f59e0b; }
        .notification-info { border-left: 4px solid #3b82f6; }
      `;
      document.head.appendChild(style);
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
      notification.remove();
    }, 5000);
    
    // Click to dismiss
    notification.addEventListener('click', () => {
      notification.remove();
    });
  }
  
  saveConfig() {
    const config = this.getDiscoveryConfig();
    localStorage.setItem('eaa-scanner-config', JSON.stringify(config));
  }
  
  loadSavedConfig() {
    const saved = localStorage.getItem('eaa-scanner-config');
    if (!saved) return;
    
    try {
      const config = JSON.parse(saved);
      
      // Restore form values
      if (config.url) document.getElementById('url').value = config.url;
      if (config.company_name) document.getElementById('company_name').value = config.company_name;
      if (config.email) document.getElementById('email').value = config.email;
      if (config.discovery_mode) document.getElementById('discovery_mode').value = config.discovery_mode;
      if (config.max_pages) document.getElementById('max_pages').value = config.max_pages;
      if (config.max_depth) document.getElementById('max_depth').value = config.max_depth;
      if (config.scan_mode) document.getElementById('scan_mode').value = config.scan_mode;
      
      // Restore scanner checkboxes
      if (config.scanners) {
        Object.entries(config.scanners).forEach(([scanner, checked]) => {
          const checkbox = document.querySelector(`input[value="${scanner}"]`);
          if (checkbox) checkbox.checked = checked;
        });
      }
      
      // Restore LLM configuration
      if (config.llm) {
        const llmEnabled = document.getElementById('llm_enabled');
        const llmModel = document.getElementById('llm_model');
        const apiKey = document.getElementById('openai_api_key');
        
        if (llmEnabled && config.llm.enabled !== undefined) {
          llmEnabled.checked = config.llm.enabled;
          this.toggleLLMConfig(config.llm.enabled);
        }
        
        if (llmModel && config.llm.model) {
          llmModel.value = config.llm.model;
          this.updateModelInfo(config.llm.model);
        }
        
        if (apiKey && config.llm.api_key) {
          apiKey.value = config.llm.api_key;
          this.validateApiKey(config.llm.api_key);
        }
      }
      
    } catch (error) {
      console.error('Error loading saved config:', error);
    }
  }
}

// Initialize scanner when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.scanner = new EAAScannerV2();
  window.scannerApp = window.scanner; // Alias for compatibility
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EAAScannerV2;
}