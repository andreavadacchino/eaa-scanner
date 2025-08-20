/**
 * Smart Scan Dashboard - Real-time monitoring per EAA Scanner
 * Connessione WebSocket per feedback live durante discovery e scansione
 */

class SmartScanDashboard {
    constructor(config = {}) {
        this.wsUrl = config.wsUrl || 'ws://localhost:8765';
        this.ws = null;
        this.reconnectInterval = 5000;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        
        // Stato corrente
        this.currentPhase = 'idle';
        this.scanData = {
            discovery: {},
            template: {},
            scan: {},
            issues: {
                critical: 0,
                high: 0,
                medium: 0,
                low: 0
            }
        };
        
        // Chart instances
        this.charts = {};
        
        // Inizializza UI
        this.initializeUI();
        this.connectWebSocket();
    }
    
    initializeUI() {
        // Verifica elementi DOM esistano
        this.elements = {
            // Status principale
            statusBadge: document.getElementById('scan-status'),
            currentPhase: document.getElementById('current-phase'),
            progressBar: document.getElementById('main-progress'),
            progressText: document.getElementById('progress-text'),
            
            // Discovery
            discoveryCard: document.getElementById('discovery-card'),
            pagesFound: document.getElementById('pages-found'),
            pagesVisited: document.getElementById('pages-visited'),
            currentUrl: document.getElementById('current-url'),
            discoveryProgress: document.getElementById('discovery-progress'),
            
            // Template Detection
            templateCard: document.getElementById('template-card'),
            templatesFound: document.getElementById('templates-found'),
            pagesAnalyzed: document.getElementById('pages-analyzed'),
            templateProgress: document.getElementById('template-progress'),
            templateList: document.getElementById('template-list'),
            
            // Scanning
            scanCard: document.getElementById('scan-card'),
            pagesScanned: document.getElementById('pages-scanned'),
            totalPages: document.getElementById('total-pages'),
            currentPage: document.getElementById('current-page'),
            currentScanner: document.getElementById('current-scanner'),
            scanProgress: document.getElementById('scan-progress'),
            
            // Issues
            issuesChart: document.getElementById('issues-chart'),
            criticalCount: document.getElementById('critical-count'),
            highCount: document.getElementById('high-count'),
            mediumCount: document.getElementById('medium-count'),
            lowCount: document.getElementById('low-count'),
            
            // Activity log
            activityLog: document.getElementById('activity-log'),
            
            // Connection status
            connectionStatus: document.getElementById('connection-status')
        };
        
        // Inizializza grafici se Chart.js disponibile
        if (typeof Chart !== 'undefined') {
            this.initializeCharts();
        }
    }
    
    initializeCharts() {
        // Grafico issues per severità
        const issuesCtx = this.elements.issuesChart?.getContext('2d');
        if (issuesCtx) {
            this.charts.issues = new Chart(issuesCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Critici', 'Alti', 'Medi', 'Bassi'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: [
                            '#dc3545',  // Rosso per critici
                            '#fd7e14',  // Arancione per alti
                            '#ffc107',  // Giallo per medi
                            '#6c757d'   // Grigio per bassi
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connesso');
                this.reconnectAttempts = 0;
                this.updateConnectionStatus('connected');
                this.requestCurrentState();
                this.addLogEntry('Connesso al server di monitoraggio', 'success');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (e) {
                    console.error('Errore parsing messaggio:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket errore:', error);
                this.updateConnectionStatus('error');
                this.addLogEntry('Errore connessione WebSocket', 'error');
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnesso');
                this.updateConnectionStatus('disconnected');
                this.addLogEntry('Disconnesso dal server', 'warning');
                this.attemptReconnect();
            };
            
        } catch (e) {
            console.error('Errore creazione WebSocket:', e);
            this.updateConnectionStatus('error');
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.addLogEntry(`Tentativo riconnessione ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`, 'info');
            setTimeout(() => this.connectWebSocket(), this.reconnectInterval);
        } else {
            this.addLogEntry('Impossibile riconnettersi al server', 'error');
        }
    }
    
    requestCurrentState() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'GET_STATE'
            }));
        }
    }
    
    handleMessage(message) {
        const { type, data, timestamp } = message;
        
        switch (type) {
            case 'CURRENT_STATE':
                this.updateFullState(data);
                break;
                
            case 'DISCOVERY_START':
                this.handleDiscoveryStart(data);
                break;
                
            case 'DISCOVERY_PROGRESS':
                this.handleDiscoveryProgress(data);
                break;
                
            case 'DISCOVERY_COMPLETE':
                this.handleDiscoveryComplete(data);
                break;
                
            case 'TEMPLATE_START':
                this.handleTemplateStart(data);
                break;
                
            case 'TEMPLATE_PROGRESS':
                this.handleTemplateProgress(data);
                break;
                
            case 'TEMPLATE_COMPLETE':
                this.handleTemplateComplete(data);
                break;
                
            case 'SCAN_START':
                this.handleScanStart(data);
                break;
                
            case 'SCAN_PROGRESS':
                this.handleScanProgress(data);
                break;
                
            case 'SCAN_PAGE_COMPLETE':
                this.handleScanPageComplete(data);
                break;
                
            case 'SCAN_COMPLETE':
                this.handleScanComplete(data);
                break;
                
            case 'ERROR':
                this.handleError(data);
                break;
                
            case 'WARNING':
                this.handleWarning(data);
                break;
                
            case 'INFO':
                this.handleInfo(data);
                break;
                
            case 'ISSUE_FOUND':
                this.handleIssueFound(data);
                break;
                
            case 'SCREENSHOT_TAKEN':
                this.handleScreenshot(data);
                break;
        }
    }
    
    updateFullState(state) {
        this.currentPhase = state.phase;
        this.scanData = state.progress;
        
        // Aggiorna UI con stato completo
        this.updatePhaseUI();
        this.updateDiscoveryUI();
        this.updateTemplateUI();
        this.updateScanUI();
        this.updateIssuesUI();
    }
    
    // Handlers per Discovery
    handleDiscoveryStart(data) {
        this.currentPhase = 'discovery';
        this.updatePhaseUI();
        this.showCard('discovery');
        
        this.updateElement('pages-found', '0');
        this.updateElement('pages-visited', '0');
        this.updateElement('current-url', data.base_url);
        
        this.addLogEntry(`🔍 Inizio discovery di ${data.base_url} (max ${data.max_pages} pagine)`, 'info');
    }
    
    handleDiscoveryProgress(data) {
        this.updateElement('pages-found', data.pages_found);
        this.updateElement('pages-visited', data.pages_visited);
        this.updateElement('current-url', data.current_url);
        this.updateProgressBar('discovery-progress', data.progress);
        this.updateMainProgress(data.progress * 0.3); // Discovery è 30% del totale
        
        // Aggiorna log ogni 5 pagine
        if (data.pages_found % 5 === 0) {
            this.addLogEntry(`📄 ${data.pages_found} pagine scoperte`, 'success');
        }
    }
    
    handleDiscoveryComplete(data) {
        this.addLogEntry(`✅ Discovery completata: ${data.total_pages} pagine trovate`, 'success');
        this.updateProgressBar('discovery-progress', 100);
    }
    
    // Handlers per Template Detection
    handleTemplateStart(data) {
        this.currentPhase = 'template_detection';
        this.updatePhaseUI();
        this.showCard('template');
        
        this.updateElement('templates-found', '0');
        this.updateElement('pages-analyzed', `0/${data.pages_count}`);
        
        this.addLogEntry(`🔎 Analisi template su ${data.pages_count} pagine...`, 'info');
    }
    
    handleTemplateProgress(data) {
        this.updateElement('templates-found', data.templates_found);
        this.updateElement('pages-analyzed', `${data.pages_analyzed}/${this.scanData.template?.total_pages || data.pages_analyzed}`);
        this.updateProgressBar('template-progress', data.progress);
        this.updateMainProgress(30 + (data.progress * 0.2)); // Template è 20% del totale
    }
    
    handleTemplateComplete(data) {
        this.addLogEntry(`✅ Template detection completata`, 'success');
        this.updateProgressBar('template-progress', 100);
        
        // Mostra template trovati
        if (data.templates && this.elements.templateList) {
            this.displayTemplates(data.templates);
        }
    }
    
    // Handlers per Scanning
    handleScanStart(data) {
        this.currentPhase = 'scanning';
        this.updatePhaseUI();
        this.showCard('scan');
        
        this.updateElement('pages-scanned', '0');
        this.updateElement('total-pages', data.pages_count);
        
        this.addLogEntry(`🚀 Inizio scansione di ${data.pages_count} pagine`, 'info');
    }
    
    handleScanProgress(data) {
        this.updateElement('pages-scanned', data.pages_scanned);
        this.updateElement('total-pages', data.total_pages);
        this.updateElement('current-page', data.current_page);
        this.updateElement('current-scanner', data.current_scanner);
        this.updateProgressBar('scan-progress', data.pages_scanned / data.total_pages * 100);
        this.updateMainProgress(50 + ((data.pages_scanned / data.total_pages) * 50)); // Scan è 50% del totale
        
        // Aggiorna issues
        if (data.issues) {
            this.updateIssuesCount(data.issues);
        }
    }
    
    handleScanPageComplete(data) {
        this.addLogEntry(`✓ Completata: ${this.truncateUrl(data.page_url)}`, 'success');
        
        // Aggiorna conteggio issues
        if (data.total_issues) {
            this.updateIssuesCount(data.total_issues);
        }
        
        this.updateProgressBar('scan-progress', data.progress);
        this.updateMainProgress(50 + (data.progress * 0.5));
    }
    
    handleScanComplete(data) {
        this.currentPhase = 'complete';
        this.updatePhaseUI();
        this.updateMainProgress(100);
        
        this.addLogEntry(`🎉 Scansione completata! Report salvato in: ${data.report_path}`, 'success');
        
        // Mostra riepilogo finale
        if (data.total_issues) {
            const total = Object.values(data.total_issues).reduce((a, b) => a + b, 0);
            this.addLogEntry(`📊 Totale issues trovate: ${total}`, 'info');
        }
    }
    
    // Handlers per messaggi generici
    handleError(data) {
        this.addLogEntry(`❌ ${data.message}`, 'error');
    }
    
    handleWarning(data) {
        this.addLogEntry(`⚠️ ${data.message}`, 'warning');
    }
    
    handleInfo(data) {
        this.addLogEntry(`ℹ️ ${data.message}`, 'info');
    }
    
    handleIssueFound(data) {
        // Incrementa contatore per severità
        if (this.scanData.issues[data.severity.toLowerCase()]) {
            this.scanData.issues[data.severity.toLowerCase()]++;
            this.updateIssuesUI();
        }
        
        // Log solo issues critiche e alte
        if (data.severity.toLowerCase() === 'critical' || data.severity.toLowerCase() === 'high') {
            this.addLogEntry(`🔴 ${data.severity}: ${data.issue_type}`, 'warning');
        }
    }
    
    handleScreenshot(data) {
        this.addLogEntry(`📸 Screenshot: ${this.truncateUrl(data.page_url)}`, 'info');
    }
    
    // UI Update Methods
    updatePhaseUI() {
        const phaseNames = {
            'idle': 'In attesa',
            'discovery': 'Discovery pagine',
            'template_detection': 'Rilevamento template',
            'scanning': 'Scansione in corso',
            'complete': 'Completato'
        };
        
        const phaseColors = {
            'idle': 'secondary',
            'discovery': 'info',
            'template_detection': 'warning',
            'scanning': 'primary',
            'complete': 'success'
        };
        
        if (this.elements.currentPhase) {
            this.elements.currentPhase.textContent = phaseNames[this.currentPhase] || this.currentPhase;
        }
        
        if (this.elements.statusBadge) {
            this.elements.statusBadge.className = `badge bg-${phaseColors[this.currentPhase] || 'secondary'}`;
            this.elements.statusBadge.textContent = phaseNames[this.currentPhase] || this.currentPhase;
        }
    }
    
    updateDiscoveryUI() {
        const data = this.scanData.discovery || {};
        this.updateElement('pages-found', data.pages_found || 0);
        this.updateElement('pages-visited', data.pages_visited || 0);
        this.updateElement('current-url', data.current_url || '-');
        this.updateProgressBar('discovery-progress', data.progress || 0);
    }
    
    updateTemplateUI() {
        const data = this.scanData.template || {};
        this.updateElement('templates-found', data.templates_found || 0);
        this.updateElement('pages-analyzed', data.pages_analyzed || 0);
        this.updateProgressBar('template-progress', data.progress || 0);
    }
    
    updateScanUI() {
        const data = this.scanData.scan || {};
        this.updateElement('pages-scanned', data.pages_scanned || 0);
        this.updateElement('total-pages', data.total_pages || 0);
        this.updateElement('current-page', data.current_page || '-');
        this.updateElement('current-scanner', data.current_scanner || '-');
        this.updateProgressBar('scan-progress', data.progress || 0);
    }
    
    updateIssuesUI() {
        const issues = this.scanData.issues || {};
        this.updateIssuesCount(issues);
    }
    
    updateIssuesCount(issues) {
        // Aggiorna contatori
        this.updateElement('critical-count', issues.critical || 0);
        this.updateElement('high-count', issues.high || 0);
        this.updateElement('medium-count', issues.medium || 0);
        this.updateElement('low-count', issues.low || 0);
        
        // Aggiorna grafico
        if (this.charts.issues) {
            this.charts.issues.data.datasets[0].data = [
                issues.critical || 0,
                issues.high || 0,
                issues.medium || 0,
                issues.low || 0
            ];
            this.charts.issues.update();
        }
    }
    
    updateElement(id, value) {
        const element = this.elements[id];
        if (element) {
            element.textContent = value;
        }
    }
    
    updateProgressBar(id, progress) {
        const element = this.elements[id];
        if (element) {
            element.style.width = `${progress}%`;
            element.setAttribute('aria-valuenow', progress);
            
            // Aggiorna testo se presente
            const textElement = element.querySelector('.progress-text');
            if (textElement) {
                textElement.textContent = `${Math.round(progress)}%`;
            }
        }
    }
    
    updateMainProgress(progress) {
        this.updateProgressBar('main-progress', progress);
        this.updateElement('progress-text', `${Math.round(progress)}%`);
    }
    
    updateConnectionStatus(status) {
        if (!this.elements.connectionStatus) return;
        
        const statusConfig = {
            'connected': { class: 'success', text: 'Connesso', icon: '🟢' },
            'disconnected': { class: 'warning', text: 'Disconnesso', icon: '🟡' },
            'error': { class: 'danger', text: 'Errore', icon: '🔴' }
        };
        
        const config = statusConfig[status] || statusConfig.error;
        this.elements.connectionStatus.className = `badge bg-${config.class}`;
        this.elements.connectionStatus.textContent = `${config.icon} ${config.text}`;
    }
    
    showCard(cardType) {
        // Mostra card specifica con animazione
        const cardMap = {
            'discovery': this.elements.discoveryCard,
            'template': this.elements.templateCard,
            'scan': this.elements.scanCard
        };
        
        const card = cardMap[cardType];
        if (card) {
            card.classList.add('highlight');
            setTimeout(() => card.classList.remove('highlight'), 2000);
        }
    }
    
    displayTemplates(templates) {
        if (!this.elements.templateList) return;
        
        this.elements.templateList.innerHTML = '';
        
        Object.values(templates).forEach(template => {
            const item = document.createElement('div');
            item.className = 'template-item mb-2 p-2 border rounded';
            item.innerHTML = `
                <strong>${template.name}</strong>
                <span class="badge bg-secondary ms-2">${template.page_count} pagine</span>
                <div class="small text-muted mt-1">${template.representative_url}</div>
            `;
            this.elements.templateList.appendChild(item);
        });
    }
    
    addLogEntry(message, type = 'info') {
        if (!this.elements.activityLog) return;
        
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type} p-2 mb-1 rounded`;
        
        const timestamp = new Date().toLocaleTimeString('it-IT');
        entry.innerHTML = `
            <span class="timestamp text-muted me-2">[${timestamp}]</span>
            <span class="message">${message}</span>
        `;
        
        // Inserisci all'inizio (più recente in alto)
        this.elements.activityLog.insertBefore(entry, this.elements.activityLog.firstChild);
        
        // Limita a 100 entries
        while (this.elements.activityLog.children.length > 100) {
            this.elements.activityLog.removeChild(this.elements.activityLog.lastChild);
        }
        
        // Scroll to top per vedere nuovo messaggio
        this.elements.activityLog.scrollTop = 0;
    }
    
    truncateUrl(url, maxLength = 50) {
        if (url.length <= maxLength) return url;
        
        try {
            const urlObj = new URL(url);
            const path = urlObj.pathname + urlObj.search;
            if (path.length > 30) {
                return urlObj.hostname + path.substring(0, 27) + '...';
            }
            return urlObj.hostname + path;
        } catch {
            return url.substring(0, maxLength - 3) + '...';
        }
    }
    
    // Public methods
    pause() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'PAUSE' }));
        }
    }
    
    resume() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'RESUME' }));
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Auto-inizializza quando DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    // Verifica se siamo nella pagina giusta
    if (document.getElementById('smart-scan-dashboard')) {
        window.smartScanDashboard = new SmartScanDashboard({
            wsUrl: window.WS_URL || 'ws://localhost:8765'
        });
    }
});