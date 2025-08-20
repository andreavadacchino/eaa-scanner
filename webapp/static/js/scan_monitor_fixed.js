/**
 * Sistema di monitoraggio live per scansioni accessibilità - VERSIONE FIXED
 * Utilizza Server-Sent Events per aggiornamenti in tempo reale
 */

(function() {
    'use strict';
    
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
                reconnectDelay: 1000, // Start with 1s
                maxReconnectAttempts: 8, // Reduced for faster fallback
                maxReconnectDelay: 30000 // Max 30s delay
            };
            
            this.reconnectAttempts = 0;
            this.startTime = Date.now();
            this.reconnectScheduled = false;
            
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
            setTimeout(() => {
                this.createMonitorUI();
            }, 1200);
        }
        
        showLoadingState() {
            this.container.innerHTML = [
                '<div class="scan-initializing" id="scan-initializing">',
                '    <div class="loading-container">',
                '        <div class="loading-spinner-large">',
                '            <div class="spinner-circle"></div>',
                '            <div class="spinner-circle"></div>',
                '            <div class="spinner-circle"></div>',
                '            <div class="spinner-circle"></div>',
                '        </div>',
                '        <h2 class="loading-title">🚀 Inizializzazione Scansione</h2>',
                '        <p class="loading-status" id="loading-status">Connessione ai servizi di accessibilità...</p>',
                '        <div class="loading-steps">',
                '            <div class="step" id="step-connect">🔗 Connessione monitor...</div>',
                '            <div class="step" id="step-scanners">🔍 Preparazione scanner...</div>',
                '            <div class="step" id="step-ready">✅ Avvio scansione...</div>',
                '        </div>',
                '        <div class="loading-progress">',
                '            <div class="loading-progress-bar" id="init-progress"></div>',
                '        </div>',
                '    </div>',
                '</div>'
            ].join('\n');
            
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
                        progressBar.style.width = ((currentStep + 1) / steps.length) * 100 + '%';
                    }
                    
                    currentStep++;
                } else {
                    clearInterval(interval);
                }
            }, 300);
        }
        
        createMonitorUI() {
            const html = [
                '<div class="scan-monitor-wrapper active">',
                '    <div class="monitor-header">',
                '        <div class="scan-info">',
                '            <h3><i class="fas fa-radar"></i> Monitoraggio Live Scansione</h3>',
                '            <div class="scan-meta">',
                '                <span class="scan-id">ID: ' + this.scanId + '</span>',
                '                <span class="connection-status" id="connection-status" data-testid="sse-status">',
                '                    <i class="fas fa-circle text-warning"></i> Connessione...',
                '                </span>',
                '                <span class="scan-duration" id="scan-duration">00:00:00</span>',
                '            </div>',
                '        </div>',
                '    </div>',
                '    <div class="scanners-grid" id="scanners-grid"></div>',
                '    <div class="overall-progress">',
                '        <div class="progress-info">',
                '            <span id="current-operation">In attesa...</span>',
                '            <span id="pages-progress">0/0 pagine</span>',
                '        </div>',
                '        <div class="progress progress-main">',
                '            <div class="progress-bar progress-bar-animated" id="main-progress-bar" data-testid="sse-progress" style="width: 0%"></div>',
                '        </div>',
                '    </div>',
                '    <div class="event-log">',
                '        <div class="log-header">',
                '            <h4><i class="fas fa-terminal"></i> Log Eventi</h4>',
                '        </div>',
                '        <div class="log-content" id="log-content"></div>',
                '    </div>',
                '</div>'
            ].join('\n');
            
            this.container.innerHTML = html;
            this.startDurationTimer();
        }
        
        connect() {
            const url = '/api/scan/stream/' + this.scanId;
            
            console.log('🔌 SSE: Tentativo connessione a', url);
            
            try {
                this.eventSource = new EventSource(url);
                
                this.eventSource.onopen = () => {
                    console.log('✅ SSE: Connessione stabilita');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.reconnectScheduled = false;
                    this.updateConnectionStatus('connected');
                };
                
                this.eventSource.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        console.log('📩 SSE Event:', data);
                        this.handleEvent(data);
                    } catch (e) {
                        console.error('Errore parsing evento SSE:', e);
                    }
                };
                
                this.eventSource.onerror = (error) => {
                    console.error('❌ SSE Error:', error);
                    this.handleConnectionError();
                };
                
            } catch (error) {
                console.error('Errore creazione EventSource:', error);
                this.handleConnectionError();
            }
        }
        
        handleConnectionError() {
            this.isConnected = false;
            this.updateConnectionStatus('error');
            
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
            
            if (this.reconnectAttempts < this.config.maxReconnectAttempts && !this.reconnectScheduled) {
                this.reconnectAttempts++;
                this.reconnectScheduled = true;
                const delay = this.calculateBackoffDelay(this.reconnectAttempts);
                
                console.log(`🔄 Tentativo riconnessione ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${delay}ms`);
                
                setTimeout(() => {
                    this.reconnectScheduled = false;
                    this.connect();
                }, delay);
            } else if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
                console.error('❌ SSE max retry attempts reached, switching to polling fallback');
                this.showCriticalError('Connessione SSE fallita. Sistema fallback attivo.');
                
                // Notify parent about SSE failure
                if (window.scanner && typeof window.scanner.sseFailure === 'function') {
                    window.scanner.sseFailure();
                }
            }
        }

        // Utility per test: calcolo backoff esponenziale con cap
        calculateBackoffDelay(attempt) {
            const a = Math.max(1, Number(attempt || 1));
            const base = this.config.reconnectDelay || 1000;
            const cap = this.config.maxReconnectDelay || 30000;
            return Math.min(base * Math.pow(2, a - 1), cap);
        }
        
        handleEvent(event) {
            this.events.push(event);
            
            // Mantieni solo gli ultimi N eventi
            if (this.events.length > this.config.maxLogEntries) {
                this.events = this.events.slice(-this.config.maxLogEntries);
            }
            
            // Gestisci eventi specifici
            switch (event.event_type) {
                case 'scan_start':
                    this.handleScanStart(event);
                    break;
                case 'scanner_start':
                case 'scanner_operation':
                case 'scanner_complete':
                case 'scanner_error':
                    this.handleScannerEvent(event);
                    break;
                case 'page_progress':
                    this.handlePageProgress(event);
                    break;
                case 'scan_complete':
                    this.handleScanComplete(event);
                    break;
                case 'scan_failed':
                    this.handleScanFailed(event);
                    break;
            }
            
            // Aggiungi al log
            this.addToLog(event);
        }
        
        handleScanStart(event) {
            const company_name = event.data?.company_name || 'sito web';
            const url = event.data?.url || '';
            this.updateCurrentOperation('Scansione di ' + company_name + ' (' + url + ')');
        }
        
        handleScannerEvent(event) {
            const scanner = event.data?.scanner || 'Unknown';
            const status = event.data?.status || event.event_type;
            
            this.updateScannerCard(scanner, status, event.data);
        }
        
        handlePageProgress(event) {
            const current = event.data?.current_page || 0;
            const total = event.data?.total_pages || 0;
            const pagesEl = document.getElementById('pages-progress');
            if (pagesEl) {
                pagesEl.textContent = current + '/' + total + ' pagine';
            }
            
            const percent = total > 0 ? (current / total * 100) : 0;
            this.updateProgress(percent);
        }
        
        handleScanComplete(event) {
            this.updateCurrentOperation('Scansione completata con successo!');
            this.updateProgress(100);
            
            // Reindirizza al report dopo 2 secondi
            if (event.data?.report_url) {
                setTimeout(() => {
                    window.location.href = event.data.report_url;
                }, 2000);
            }
        }
        
        handleScanFailed(event) {
            const error = event.data?.error || 'Errore sconosciuto';
            this.updateCurrentOperation('Scansione fallita: ' + error);
            this.showCriticalError('Scansione fallita: ' + error);
        }
        
        updateScannerCard(scanner, status, data) {
            const grid = document.getElementById('scanners-grid');
            if (!grid) return;
            
            let card = document.getElementById('scanner-card-' + scanner.toLowerCase());
            if (!card) {
                card = document.createElement('div');
                card.id = 'scanner-card-' + scanner.toLowerCase();
                card.className = 'scanner-card';
                grid.appendChild(card);
            }
            
            const statusClass = status === 'completed' ? 'success' : 
                               status === 'error' ? 'error' : 'active';
            
            card.className = 'scanner-card scanner-' + statusClass;
            card.innerHTML = [
                '<div class="scanner-name">' + scanner + '</div>',
                '<div class="scanner-status">' + (data?.operation || status) + '</div>'
            ].join('\n');
        }
        
        updateCurrentOperation(text) {
            const el = document.getElementById('current-operation');
            if (el) el.textContent = text;
        }
        
        updateProgress(percent) {
            const progressBar = document.getElementById('main-progress-bar');
            if (progressBar) {
                progressBar.style.width = percent + '%';
            }
        }
        
        updateConnectionStatus(status) {
            const statusEl = document.getElementById('connection-status');
            if (!statusEl) return;
            
            const statusInfo = {
                'connected': { icon: 'fas fa-circle text-success', text: 'Connesso' },
                'error': { icon: 'fas fa-circle text-danger', text: 'Disconnesso' },
                'reconnecting': { icon: 'fas fa-circle text-warning', text: 'Riconnessione...' }
            };
            
            const info = statusInfo[status] || statusInfo['error'];
            statusEl.innerHTML = '<i class="' + info.icon + '"></i> ' + info.text;
            // also expose plain text content for testing
            statusEl.setAttribute('data-status-text', info.text);
        }
        
        addToLog(event) {
            const logContent = document.getElementById('log-content');
            if (!logContent) return;
            
            const entry = document.createElement('div');
            entry.className = 'log-entry event-' + event.event_type;
            
            const time = new Date().toLocaleTimeString();
            const message = event.message || this.getDefaultMessage(event);
            
            entry.innerHTML = [
                '<span class="log-time">' + time + '</span>',
                '<span class="log-event-type">' + this.formatEventType(event.event_type) + '</span>',
                '<span class="log-message">' + message + '</span>'
            ].join(' ');
            
            logContent.appendChild(entry);
            
            // Auto scroll
            logContent.scrollTop = logContent.scrollHeight;
        }
        
        formatEventType(type) {
            return type ? type.replace(/_/g, ' ').toUpperCase() : 'EVENTO';
        }
        
        getDefaultMessage(event) {
            const messages = {
                'scan_start': '🚀 Avvio scansione',
                'scanner_start': '🔍 Avvio scanner',
                'scanner_complete': '✅ Scanner completato',
                'scanner_error': '⚠️ Errore scanner',
                'scan_complete': '🎉 Scansione completata!',
                'scan_failed': '❌ Scansione fallita',
                'heartbeat': '💓 Connessione attiva'
            };
            
            return messages[event.event_type] || '🔄 ' + (event.event_type || 'Evento') + ' in corso...';
        }
        
        showCriticalError(message) {
            const container = document.querySelector('.scan-monitor-wrapper');
            if (!container) return;
            
            container.innerHTML = [
                '<div class="critical-error-state">',
                '    <div class="error-icon-large">❌</div>',
                '    <h2>Errore di Connessione</h2>',
                '    <p>' + message + '</p>',
                '    <button class="btn btn-primary" onclick="location.reload()">',
                '        🔄 Ricarica Pagina',
                '    </button>',
                '</div>'
            ].join('\n');
        }
        
        startDurationTimer() {
            setInterval(() => {
                const elapsed = Date.now() - this.startTime;
                const hours = Math.floor(elapsed / 3600000);
                const minutes = Math.floor((elapsed % 3600000) / 60000);
                const seconds = Math.floor((elapsed % 60000) / 1000);
                
                const durationEl = document.getElementById('scan-duration');
                if (durationEl) {
                    durationEl.textContent = [
                        hours.toString().padStart(2, '0'),
                        minutes.toString().padStart(2, '0'),
                        seconds.toString().padStart(2, '0')
                    ].join(':');
                }
            }, 1000);
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
    window.initScanMonitor = function(scanId, containerId) {
        containerId = containerId || 'scan-monitor';
        if (scanMonitor) {
            scanMonitor.disconnect();
        }
        scanMonitor = new ScanMonitor(scanId, containerId);
        return scanMonitor;
    };
    
    window.getScanMonitor = function() {
        return scanMonitor;
    };
    
    window.ScanMonitor = ScanMonitor;
    
    console.log('✅ ScanMonitor functions registered globally');
    
})();
