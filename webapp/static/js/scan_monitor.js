/**
 * Sistema di monitoraggio live per scansioni accessibilità
 * Utilizza Server-Sent Events per aggiornamenti in tempo reale
 */

class ScanMonitor {
    constructor(scanId, containerId) {
        this.scanId = scanId;
        this.container = document.getElementById(containerId);
        this.eventSource = null;
        this.isConnected = false;
        this.events = [];
        this.scannerStates = {};
        
        // Configurazione UI
        this.config = {
            maxLogEntries: 100,
            heartbeatInterval: 30000,
            reconnectDelay: 5000,
            maxReconnectAttempts: 10
        };
        
        this.reconnectAttempts = 0;
        this.startTime = Date.now();
        
        this.init();
    }
    
    init() {
        this.createUI();
        this.connect();
    }
    
    createUI() {
        if (!this.container) {
            console.error('Container per monitor non trovato');
            return;
        }
        
        // Prima mostra uno stato di loading chiaro e visibile
        this.showLoadingState();
        
        // Dopo che l'animazione loading è completata, crea l'UI completa
        // L'animazione dura 300ms x 3 steps = 900ms, aggiungiamo un piccolo buffer
        setTimeout(() => {
            this.createMonitorUI();
        }, 1200);
    }
    
    showLoadingState() {
        this.container.innerHTML = `
            <div class="scan-initializing" id="scan-initializing">
                <div class="loading-container">
                    <div class="loading-spinner-large">
                        <div class="spinner-circle"></div>
                        <div class="spinner-circle"></div>
                        <div class="spinner-circle"></div>
                        <div class="spinner-circle"></div>
                    </div>
                    <h2 class="loading-title">🚀 Inizializzazione Scansione</h2>
                    <p class="loading-status" id="loading-status">Connessione ai servizi di accessibilità...</p>
                    <div class="loading-steps">
                        <div class="step" id="step-connect">🔗 Connessione monitor...</div>
                        <div class="step" id="step-scanners">🔍 Preparazione scanner...</div>
                        <div class="step" id="step-ready">✅ Avvio scansione...</div>
                    </div>
                    <div class="loading-progress">
                        <div class="loading-progress-bar" id="init-progress"></div>
                    </div>
                </div>
            </div>
        `;
        
        // Anima i passaggi di loading
        this.animateLoadingSteps();
    }
    
    animateLoadingSteps() {
        const steps = ['step-connect', 'step-scanners', 'step-ready'];
        let currentStep = 0;
        
        const interval = setInterval(() => {
            if (currentStep < steps.length) {
                const stepEl = document.getElementById(steps[currentStep]);
                if (stepEl) {
                    stepEl.classList.add('active');
                }
                
                const progressBar = document.getElementById('init-progress');
                if (progressBar) {
                    progressBar.style.width = `${((currentStep + 1) / steps.length) * 100}%`;
                }
                
                currentStep++;
            } else {
                clearInterval(interval);
            }
        }, 300);
    }
    
    createMonitorUI() {
        this.container.innerHTML = `
            <div class="scan-monitor-wrapper active">
                <!-- Header con informazioni generali -->
                <div class="monitor-header">
                    <div class="scan-info">
                        <h3><i class="fas fa-radar"></i> Monitoraggio Live Scansione</h3>
                        <div class="scan-meta">
                            <span class="scan-id">ID: ${this.scanId}</span>
                            <span class="connection-status" id="connection-status">
                                <i class="fas fa-circle text-warning"></i> Connessione...
                            </span>
                            <span class="scan-duration" id="scan-duration">00:00:00</span>
                        </div>
                    </div>
                    <div class="monitor-controls">
                        <button class="btn btn-sm btn-outline-secondary" onclick="scanMonitor.toggleAutoScroll()">
                            <i class="fas fa-scroll"></i> Auto Scroll
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="scanMonitor.clearLog()">
                            <i class="fas fa-trash"></i> Pulisci Log
                        </button>
                    </div>
                </div>
                
                <!-- Griglia scanner attivi -->
                <div class="scanners-grid" id="scanners-grid">
                    <!-- Le card dei scanner verranno aggiunte dinamicamente -->
                </div>
                
                <!-- Progress generale -->
                <div class="overall-progress">
                    <div class="progress-info">
                        <span id="current-operation">In attesa...</span>
                        <span id="pages-progress">0/0 pagine</span>
                    </div>
                    <div class="progress progress-main">
                        <div class="progress-bar progress-bar-animated" 
                             id="main-progress-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <!-- Log degli eventi -->
                <div class="event-log">
                    <div class="log-header">
                        <h4><i class="fas fa-terminal"></i> Log Eventi</h4>
                        <div class="log-filters">
                            <label class="filter-checkbox">
                                <input type="checkbox" checked data-filter="all"> Tutti
                            </label>
                            <label class="filter-checkbox">
                                <input type="checkbox" checked data-filter="scanner_start"> Inizio Scanner
                            </label>
                            <label class="filter-checkbox">
                                <input type="checkbox" checked data-filter="scanner_complete"> Completamento
                            </label>
                            <label class="filter-checkbox">
                                <input type="checkbox" checked data-filter="error"> Errori
                            </label>
                        </div>
                    </div>
                    <div class="log-content" id="log-content">
                        <!-- Gli eventi verranno aggiunti qui -->
                    </div>
                </div>
            </div>
        `;
        
        // Configura timer durata
        this.startDurationTimer();
        
        // Configura filtri log
        this.setupLogFilters();
        
        // Auto scroll attivo di default
        this.autoScroll = true;
    }
    
    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        const url = `/api/scan/stream/${this.scanId}`;
        this.eventSource = new EventSource(url);
        
        this.eventSource.onopen = () => {
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
            this.addLogEntry({
                event_type: 'connection',
                message: 'Connessione monitoraggio stabilita',
                timestamp: new Date().toISOString()
            });
        };
        
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (e) {
                console.error('Errore parsing evento SSE:', e);
                this.showUserError('Errore nel processamento dati. Alcuni eventi potrebbero non essere visualizzati.');
            }
        };
        
        this.eventSource.onerror = (error) => {
            this.isConnected = false;
            this.updateConnectionStatus('error');
            
            // Mostra errore all'utente
            this.showUserError(`Connessione interrotta. Tentativo ${this.reconnectAttempts + 1}/${this.config.maxReconnectAttempts}`);
            
            // Tentativo di riconnessione
            if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
                this.reconnectAttempts++;
                
                // Mostra countdown per riconnessione
                const delay = this.config.reconnectDelay * this.reconnectAttempts;
                this.showReconnectCountdown(delay / 1000);
                
                setTimeout(() => {
                    this.connect();
                }, delay);
            } else {
                this.showCriticalError('Impossibile connettersi al server. Ricarica la pagina per riprovare.');
            }
        };
    }
    
    showUserError(message) {
        // Crea un banner di errore visibile
        const errorBanner = document.createElement('div');
        errorBanner.className = 'error-banner';
        errorBanner.innerHTML = `
            <div class="error-content">
                <span class="error-icon">⚠️</span>
                <span class="error-message">${message}</span>
            </div>
        `;
        
        const container = document.querySelector('.scan-monitor-wrapper');
        if (container) {
            // Rimuovi banner precedenti
            const oldBanner = container.querySelector('.error-banner');
            if (oldBanner) oldBanner.remove();
            
            container.insertBefore(errorBanner, container.firstChild);
            
            // Rimuovi dopo 5 secondi
            setTimeout(() => {
                errorBanner.style.animation = 'fadeOut 0.5s';
                setTimeout(() => errorBanner.remove(), 500);
            }, 5000);
        }
    }
    
    showReconnectCountdown(seconds) {
        const statusText = document.querySelector('#connection-status .status-text');
        if (!statusText) return;
        
        let remaining = seconds;
        const interval = setInterval(() => {
            if (remaining > 0) {
                statusText.textContent = `Riconnessione tra ${remaining}s...`;
                remaining--;
            } else {
                clearInterval(interval);
                statusText.textContent = 'Riconnessione...';
            }
        }, 1000);
    }
    
    showCriticalError(message) {
        const container = document.querySelector('.scan-monitor-wrapper');
        if (!container) return;
        
        container.innerHTML = `
            <div class="critical-error-state">
                <div class="error-icon-large">❌</div>
                <h2>Errore di Connessione</h2>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="location.reload()">
                    🔄 Ricarica Pagina
                </button>
            </div>
        `;
    }
    
    handleEvent(event) {
        this.events.push(event);
        
        // Mantieni solo gli ultimi N eventi
        if (this.events.length > this.config.maxLogEntries) {
            this.events = this.events.slice(-this.config.maxLogEntries);
        }
        
        switch (event.event_type) {
            case 'scan_start':
                this.handleScanStart(event);
                break;
            case 'scanner_start':
                this.handleScannerStart(event);
                break;
            case 'scanner_operation':
                this.handleScannerOperation(event);
                break;
            case 'scanner_complete':
                this.handleScannerComplete(event);
                break;
            case 'scanner_error':
                this.handleScannerError(event);
                break;
            case 'page_progress':
                this.handlePageProgress(event);
                break;
            case 'processing_step':
                this.handleProcessingStep(event);
                break;
            case 'report_generation':
                this.handleReportGeneration(event);
                break;
            case 'scan_complete':
                this.handleScanComplete(event);
                break;
            case 'scan_failed':
                this.handleScanFailed(event);
                break;
            case 'heartbeat':
                // Ignora heartbeat nel log
                return;
            default:
                console.log('Evento non gestito:', event);
        }
        
        // Aggiungi al log
        this.addLogEntry(event);
    }
    
    handleScanStart(event) {
        const { url, company_name, scanners_enabled } = event.data;
        
        // Aggiorna UI principale
        this.updateCurrentOperation(`Scansione di ${company_name} (${url})`);
        
        // Crea cards per scanner abilitati
        this.createScannerCards(scanners_enabled);
    }
    
    handleScannerStart(event) {
        const { scanner, url } = event.data;
        
        // Mostra notifica visiva prominente
        this.showScannerNotification(scanner, 'started');
        
        this.updateScannerCard(scanner, {
            status: 'running',
            operation: `🔍 Analizzando ${url}`,
            progress: 0
        });
    }
    
    showScannerNotification(scanner, status) {
        const notifications = {
            'started': { icon: '🚀', message: `${scanner} avviato`, class: 'scanner-start' },
            'completed': { icon: '✅', message: `${scanner} completato`, class: 'scanner-success' },
            'error': { icon: '❌', message: `${scanner} errore`, class: 'scanner-error' }
        };
        
        const notif = notifications[status];
        if (!notif) return;
        
        // Crea toast notification
        const notification = document.createElement('div');
        notification.className = `scanner-notification ${notif.class}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideInRight 0.5s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        notification.innerHTML = `
            <span style="font-size: 24px;">${notif.icon}</span>
            <span style="font-weight: 600;">${notif.message}</span>
        `;
        
        document.body.appendChild(notification);
        
        // Rimuovi dopo 3 secondi
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.5s';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }
    
    handleScannerOperation(event) {
        const { scanner, operation, progress_percent } = event.data;
        this.updateScannerCard(scanner, {
            operation: operation,
            progress: progress_percent || 0
        });
    }
    
    handleScannerComplete(event) {
        const { scanner, results } = event.data;
        this.updateScannerCard(scanner, {
            status: 'completed',
            operation: 'Completato',
            progress: 100,
            results: results
        });
    }
    
    handleScannerError(event) {
        const { scanner, error, is_critical } = event.data;
        this.updateScannerCard(scanner, {
            status: is_critical ? 'critical-error' : 'error',
            operation: `Errore: ${error}`,
            progress: 0
        });
    }
    
    handlePageProgress(event) {
        const { current_page, total_pages, current_url } = event.data;
        const pagesEl = document.getElementById('pages-progress');
        if (pagesEl) {
            pagesEl.textContent = `${current_page}/${total_pages} pagine`;
        }
        
        this.updateCurrentOperation(`Pagina ${current_page}/${total_pages}: ${current_url}`);
    }
    
    handleProcessingStep(event) {
        const { step, progress_percent } = event.data;
        this.updateCurrentOperation(step);
        this.updateMainProgress(progress_percent || 0);
    }
    
    handleReportGeneration(event) {
        const { stage, progress_percent } = event.data;
        this.updateCurrentOperation(`Report: ${stage}`);
        this.updateMainProgress(progress_percent || 90);
    }
    
    handleScanComplete(event) {
        this.updateCurrentOperation('✅ Scansione completata con successo!');
        this.updateMainProgress(100);
        this.updateConnectionStatus('completed');
        
        // Aggiungi indicatore visivo di completamento
        const container = document.querySelector('.live-monitor-container');
        if (container) {
            container.classList.add('scan-completed');
            
            // Aggiungi banner di successo
            const banner = document.createElement('div');
            banner.className = 'completion-banner';
            banner.innerHTML = `
                <div style="
                    background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 12px;
                    text-align: center;
                    margin: 20px 0;
                    font-size: 18px;
                    font-weight: 600;
                    box-shadow: 0 5px 20px rgba(0,0,0,0.2);
                    animation: slideInUp 0.5s ease;
                ">
                    🎉 Scansione Completata con Successo! 🎉<br>
                    <small style="opacity: 0.9; font-weight: 400;">Procedi al report per visualizzare i risultati</small>
                </div>
            `;
            container.insertBefore(banner, container.firstChild);
        }
        
        // Aggiorna tutte le card scanner come completate
        document.querySelectorAll('.scanner-card').forEach(card => {
            if (!card.classList.contains('completed') && !card.classList.contains('error')) {
                card.classList.add('completed');
                card.classList.remove('running');
            }
        });
        
        // Chiudi connessione SSE
        if (this.eventSource) {
            this.eventSource.close();
        }
        
        // NON richiamare handleScanComplete() qui - il polling lo gestisce già
        // Questo causava una doppia chiamata che faceva tornare indietro l'UI
        // Il completamento è già gestito dal polling in scanner_v2.js
    }
    
    handleScanFailed(event) {
        const { error } = event.data;
        this.updateCurrentOperation(`Scansione fallita: ${error}`);
        this.updateConnectionStatus('failed');
        
        // Chiudi connessione SSE
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
    
    createScannerCards(scannersEnabled) {
        const grid = document.getElementById('scanners-grid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        const scanners = [
            { key: 'wave', name: 'WAVE', icon: 'fas fa-water', color: 'primary' },
            { key: 'pa11y', name: 'Pa11y', icon: 'fas fa-universal-access', color: 'success' },
            { key: 'axe', name: 'Axe-core', icon: 'fas fa-hammer', color: 'warning' },
            { key: 'lighthouse', name: 'Lighthouse', icon: 'fas fa-lighthouse', color: 'info' }
        ];
        
        scanners.forEach(scanner => {
            if (scannersEnabled[scanner.key]) {
                const card = this.createScannerCard(scanner);
                grid.appendChild(card);
            }
        });
    }
    
    createScannerCard(scanner) {
        const card = document.createElement('div');
        card.className = 'scanner-card';
        card.id = `scanner-${scanner.key}`;
        
        card.innerHTML = `
            <div class="scanner-header">
                <div class="scanner-info">
                    <i class="${scanner.icon} scanner-icon text-${scanner.color}"></i>
                    <span class="scanner-name">${scanner.name}</span>
                </div>
                <span class="scanner-status badge badge-secondary">In attesa</span>
            </div>
            <div class="scanner-operation">
                <span class="operation-text">Pronto</span>
            </div>
            <div class="scanner-progress">
                <div class="progress progress-sm">
                    <div class="progress-bar bg-${scanner.color}" style="width: 0%"></div>
                </div>
                <span class="progress-text">0%</span>
            </div>
            <div class="scanner-results" style="display: none;">
                <!-- Risultati verranno mostrati qui -->
            </div>
        `;
        
        return card;
    }
    
    updateScannerCard(scannerName, updates) {
        // Mappa nomi scanner
        const scannerMap = {
            'WAVE': 'wave',
            'Pa11y': 'pa11y',
            'Axe-core': 'axe',
            'Lighthouse': 'lighthouse'
        };
        
        const scannerKey = scannerMap[scannerName] || scannerName.toLowerCase();
        const card = document.getElementById(`scanner-${scannerKey}`);
        
        if (!card) return;
        
        // Aggiungi animazione alla card quando è attiva
        if (updates.status === 'running') {
            card.classList.add('scanner-active');
            card.style.animation = 'pulseGlow 2s infinite';
        } else {
            card.classList.remove('scanner-active');
            card.style.animation = '';
        }
        
        // Aggiorna status con icone
        if (updates.status) {
            const statusEl = card.querySelector('.scanner-status');
            const statusMap = {
                'running': { text: '🔄 In esecuzione', class: 'badge-primary', animated: true },
                'completed': { text: '✅ Completato', class: 'badge-success', animated: false },
                'error': { text: '⚠️ Errore', class: 'badge-warning', animated: false },
                'critical-error': { text: '❌ Errore Critico', class: 'badge-danger', animated: false }
            };
            
            const status = statusMap[updates.status];
            if (status) {
                statusEl.innerHTML = status.text;
                statusEl.className = `scanner-status badge ${status.class}`;
                
                if (status.animated) {
                    statusEl.style.animation = 'pulse 1.5s infinite';
                } else {
                    statusEl.style.animation = '';
                }
            }
        }
        
        // Aggiorna operazione
        if (updates.operation) {
            const opEl = card.querySelector('.operation-text');
            opEl.textContent = updates.operation;
        }
        
        // Aggiorna progress
        if (updates.progress !== undefined) {
            const progressBar = card.querySelector('.progress-bar');
            const progressText = card.querySelector('.progress-text');
            progressBar.style.width = `${updates.progress}%`;
            progressText.textContent = `${updates.progress}%`;
        }
        
        // Mostra risultati
        if (updates.results) {
            const resultsEl = card.querySelector('.scanner-results');
            resultsEl.innerHTML = this.formatScannerResults(updates.results);
            resultsEl.style.display = 'block';
        }
    }
    
    formatScannerResults(results) {
        let html = '<div class="results-summary">';
        
        if (results.errors !== undefined) {
            html += `<span class="result-item text-danger"><i class="fas fa-times-circle"></i> ${results.errors} errori</span>`;
        }
        if (results.warnings !== undefined) {
            html += `<span class="result-item text-warning"><i class="fas fa-exclamation-triangle"></i> ${results.warnings} warning</span>`;
        }
        if (results.violations !== undefined) {
            html += `<span class="result-item text-danger"><i class="fas fa-ban"></i> ${results.violations} violazioni</span>`;
        }
        if (results.accessibility_score !== undefined) {
            const score = Math.round(results.accessibility_score * 100);
            html += `<span class="result-item text-info"><i class="fas fa-star"></i> Score: ${score}%</span>`;
        }
        
        html += '</div>';
        return html;
    }
    
    updateCurrentOperation(operation) {
        const opEl = document.getElementById('current-operation');
        if (opEl) {
            opEl.textContent = operation;
        }
    }
    
    updateMainProgress(percent) {
        const progressBar = document.getElementById('main-progress-bar');
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
    }
    
    updateConnectionStatus(status) {
        const statusEl = document.getElementById('connection-status');
        if (!statusEl) return;
        
        const statusMap = {
            'connected': { icon: 'fas fa-circle text-success', text: 'Connesso' },
            'error': { icon: 'fas fa-circle text-danger', text: 'Errore Connessione' },
            'completed': { icon: 'fas fa-check-circle text-success', text: 'Completato' },
            'failed': { icon: 'fas fa-times-circle text-danger', text: 'Fallito' }
        };
        
        const statusInfo = statusMap[status];
        if (statusInfo) {
            statusEl.innerHTML = `<i class="${statusInfo.icon}"></i> ${statusInfo.text}`;
        }
    }
    
    addLogEntry(event) {
        const logContent = document.getElementById('log-content');
        if (!logContent) return;
        
        const entry = document.createElement('div');
        entry.className = `log-entry event-${event.event_type}`;
        
        const time = new Date(event.timestamp).toLocaleTimeString('it-IT');
        const eventTypeClass = this.getEventTypeClass(event.event_type);
        
        // Fix problema undefined - genera messaggio appropriato
        const message = event.message || this.getDefaultMessage(event);
        
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-event-type ${eventTypeClass}">${this.formatEventType(event.event_type)}</span>
            <span class="log-message">${message}</span>
        `;
        
        logContent.appendChild(entry);
        
        // Auto scroll
        if (this.autoScroll) {
            logContent.scrollTop = logContent.scrollHeight;
        }
        
        // Mantieni numero limitato di voci
        while (logContent.children.length > this.config.maxLogEntries) {
            logContent.removeChild(logContent.firstChild);
        }
    }
    
    getEventTypeClass(eventType) {
        const classMap = {
            'scan_start': 'text-primary',
            'scanner_start': 'text-info',
            'scanner_complete': 'text-success',
            'scanner_error': 'text-danger',
            'processing_step': 'text-secondary',
            'scan_complete': 'text-success font-weight-bold',
            'scan_failed': 'text-danger font-weight-bold'
        };
        return classMap[eventType] || 'text-muted';
    }
    
    formatEventType(eventType) {
        const typeMap = {
            'scan_start': 'INIZIO',
            'scanner_start': 'SCANNER',
            'scanner_operation': 'OP',
            'scanner_complete': 'COMPLETO',
            'scanner_error': 'ERRORE',
            'page_progress': 'PAGINA',
            'processing_step': 'PROCESSO',
            'report_generation': 'REPORT',
            'scan_complete': 'FINE',
            'scan_failed': 'FALLITO',
            'connection': 'CONN'
        };
        return typeMap[eventType] || eventType.toUpperCase();
    }
    
    getDefaultMessage(event) {
        // Genera messaggi appropriati basati sul tipo di evento e dati disponibili
        const messages = {
            'scan_start': `🚀 Avvio scansione per ${event.data?.company_name || 'sito web'}`,
            'scanner_start': `🔍 Avvio ${event.data?.scanner || 'scanner'} su ${event.data?.url || 'pagina'}`,
            'scanner_operation': `⚡ ${event.data?.operation || 'Operazione in corso'} - ${event.data?.scanner || 'Scanner'}`,
            'scanner_complete': `✅ ${event.data?.scanner || 'Scanner'} completato con successo`,
            'scanner_error': `⚠️ Errore in ${event.data?.scanner || 'scanner'}: ${event.data?.error || 'errore sconosciuto'}`,
            'page_progress': `📄 Analisi pagina ${event.data?.current_page || '?'}/${event.data?.total_pages || '?'}`,
            'processing_step': `⚙️ ${event.data?.step || 'Elaborazione in corso'}`,
            'report_generation': `📝 Generazione report: ${event.data?.stage || 'in corso'}`,
            'scan_complete': `🎉 Scansione completata con successo!`,
            'scan_failed': `❌ Scansione fallita: ${event.data?.error || 'errore sconosciuto'}`,
            'heartbeat': `💓 Connessione attiva`,
            'connection': `🔗 ${event.data?.status || 'Connessione stabilita'}`
        };
        
        return messages[event.event_type] || `🔄 ${event.event_type || 'Evento'} in corso...`;
    }
    
    setupLogFilters() {
        const filters = document.querySelectorAll('[data-filter]');
        filters.forEach(filter => {
            filter.addEventListener('change', () => {
                this.applyLogFilters();
            });
        });
    }
    
    applyLogFilters() {
        const activeFilters = Array.from(document.querySelectorAll('[data-filter]:checked'))
            .map(el => el.dataset.filter);
        
        const entries = document.querySelectorAll('.log-entry');
        entries.forEach(entry => {
            const eventType = entry.className.split(' ')[1].replace('event-', '');
            const show = activeFilters.includes('all') || activeFilters.includes(eventType);
            entry.style.display = show ? 'flex' : 'none';
        });
    }
    
    startDurationTimer() {
        setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            
            const durationEl = document.getElementById('scan-duration');
            if (durationEl) {
                durationEl.textContent = 
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        const btn = event.target.closest('button');
        btn.classList.toggle('active', this.autoScroll);
    }
    
    clearLog() {
        const logContent = document.getElementById('log-content');
        if (logContent) {
            logContent.innerHTML = '';
        }
    }
    
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');
    }
}

// Istanza globale
let scanMonitor = null;

// Funzioni di utilità globali
function initScanMonitor(scanId, containerId = 'scan-monitor') {
    if (scanMonitor) {
        scanMonitor.disconnect();
    }
    scanMonitor = new ScanMonitor(scanId, containerId);
    return scanMonitor;
}

function getScanMonitor() {
    return scanMonitor;
}

// Esponi le funzioni a window per essere usate da altri script
if (typeof window !== 'undefined') {
    window.initScanMonitor = initScanMonitor;
    window.getScanMonitor = getScanMonitor;
    window.ScanMonitor = ScanMonitor;
    console.log('✅ ScanMonitor functions registered globally');
}