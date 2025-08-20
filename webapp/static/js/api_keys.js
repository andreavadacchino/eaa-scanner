/**
 * Gestione API Keys per EAA Scanner
 * Sistema per configurazione, validazione e storage sicuro delle chiavi API
 */

class APIKeyManager {
    constructor() {
        this.modal = null;
        this.keys = {
            openai: '',
            wave: ''
        };
        this.validationStatus = {
            openai: null,
            wave: null
        };
        
        this.init();
    }
    
    init() {
        // Carica stato delle chiavi all'avvio
        this.loadKeysStatus();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Crea il modal
        this.createModal();
    }
    
    setupEventListeners() {
        // Click sul pulsante API Keys nell'header
        document.addEventListener('click', (e) => {
            if (e.target.closest('#api-keys-btn')) {
                this.showModal();
            }
            
            if (e.target.closest('#api-keys-modal-close')) {
                this.hideModal();
            }
            
            if (e.target.closest('#save-api-keys')) {
                this.saveKeys();
            }
            
            if (e.target.closest('.test-api-key')) {
                const keyType = e.target.dataset.keyType;
                this.validateSingleKey(keyType);
            }
            
            if (e.target.closest('.toggle-key-visibility')) {
                const keyType = e.target.dataset.keyType;
                this.toggleKeyVisibility(keyType);
            }
        });
        
        // Escape per chiudere modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal?.classList.contains('active')) {
                this.hideModal();
            }
        });
        
        // Input validation in tempo reale
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('api-key-input')) {
                this.onKeyInput(e.target);
            }
        });
    }
    
    async loadKeysStatus() {
        try {
            const response = await fetch('/api/keys/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateHeaderStatus(data.data);
                this.validationStatus = data.data.validation || {};
                
                // Salva lo stato delle chiavi per quando si apre il modal
                if (data.data.keys) {
                    this.storedKeys = {
                        openai: data.data.keys.openai,
                        wave: data.data.keys.wave
                    };
                }
            }
        } catch (error) {
            console.error('Errore caricamento stato chiavi:', error);
        }
    }
    
    updateHeaderStatus(statusData) {
        const btn = document.getElementById('api-keys-btn');
        if (!btn) return;
        
        const openaiValid = statusData.validation?.openai?.valid || false;
        const waveValid = statusData.validation?.wave?.valid || false;
        
        // Aggiorna indicatore visivo
        let status = 'none';
        if (openaiValid && waveValid) {
            status = 'all';
        } else if (openaiValid || waveValid) {
            status = 'partial';
        }
        
        btn.className = `api-keys-btn status-${status}`;
        
        // Aggiorna tooltip
        const tooltipText = this.getStatusTooltip(openaiValid, waveValid);
        btn.setAttribute('title', tooltipText);
    }
    
    getStatusTooltip(openaiValid, waveValid) {
        if (openaiValid && waveValid) {
            return '✅ Tutte le API keys sono configurate e valide';
        } else if (openaiValid) {
            return '🟡 Solo OpenAI configurata - WAVE mancante';
        } else if (waveValid) {
            return '🟡 Solo WAVE configurata - OpenAI mancante';
        } else {
            return '❌ Nessuna API key configurata';
        }
    }
    
    createModal() {
        const modalHTML = `
            <div id="api-keys-modal" class="api-keys-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>🔑 Gestione API Keys</h2>
                        <button id="api-keys-modal-close" class="modal-close">&times;</button>
                    </div>
                    
                    <div class="modal-body">
                        <p class="modal-description">
                            Configura le chiavi API per abilitare funzionalità avanzate del sistema.
                            Le chiavi vengono salvate in modo sicuro e crittografato.
                        </p>
                        
                        <!-- OpenAI API Key -->
                        <div class="api-key-section">
                            <div class="key-header">
                                <h3>OpenAI API Key</h3>
                                <div class="key-status" id="openai-status"></div>
                            </div>
                            
                            <div class="key-description">
                                Necessaria per funzionalità AI: analisi intelligente, raccomandazioni, generazione contenuti
                            </div>
                            
                            <div class="key-input-group">
                                <input 
                                    type="password" 
                                    id="openai-key-input" 
                                    class="api-key-input"
                                    placeholder="sk-..."
                                    data-key-type="openai"
                                >
                                <button 
                                    type="button" 
                                    class="toggle-key-visibility" 
                                    data-key-type="openai"
                                    title="Mostra/Nascondi chiave"
                                >
                                    👁️
                                </button>
                                <button 
                                    type="button" 
                                    class="test-api-key" 
                                    data-key-type="openai"
                                    title="Testa validità chiave"
                                >
                                    ⚡ Test
                                </button>
                            </div>
                            
                            <div class="key-validation" id="openai-validation"></div>
                        </div>
                        
                        <!-- WAVE API Key -->
                        <div class="api-key-section">
                            <div class="key-header">
                                <h3>WAVE API Key</h3>
                                <div class="key-status" id="wave-status"></div>
                            </div>
                            
                            <div class="key-description">
                                Necessaria per scanner WAVE professionale di WebAIM. 
                                <a href="https://wave.webaim.org/api/" target="_blank">Ottieni chiave →</a>
                            </div>
                            
                            <div class="key-input-group">
                                <input 
                                    type="password" 
                                    id="wave-key-input" 
                                    class="api-key-input"
                                    placeholder="Inserisci chiave WAVE..."
                                    data-key-type="wave"
                                >
                                <button 
                                    type="button" 
                                    class="toggle-key-visibility" 
                                    data-key-type="wave"
                                    title="Mostra/Nascondi chiave"
                                >
                                    👁️
                                </button>
                                <button 
                                    type="button" 
                                    class="test-api-key" 
                                    data-key-type="wave"
                                    title="Testa validità chiave"
                                >
                                    ⚡ Test
                                </button>
                            </div>
                            
                            <div class="key-validation" id="wave-validation"></div>
                        </div>
                        
                        <div class="modal-footer">
                            <button id="save-api-keys" class="btn btn-primary">
                                💾 Salva Chiavi
                            </button>
                            <button id="api-keys-modal-close" class="btn btn-secondary">
                                Annulla
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('api-keys-modal');
    }
    
    async showModal() {
        if (!this.modal) return;
        
        // Carica stato corrente
        await this.loadCurrentKeys();
        
        this.modal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        // Focus sul primo input vuoto
        const firstEmptyInput = this.modal.querySelector('.api-key-input[value=""]');
        if (firstEmptyInput) {
            firstEmptyInput.focus();
        }
    }
    
    hideModal() {
        if (!this.modal) return;
        
        this.modal.classList.remove('active');
        document.body.style.overflow = '';
    }
    
    async loadCurrentKeys() {
        try {
            const response = await fetch('/api/keys/status');
            const data = await response.json();
            
            if (data.success) {
                const keysData = data.data;
                
                // Aggiorna input fields con chiavi mascherate
                if (keysData.keys.openai?.present) {
                    const input = document.getElementById('openai-key-input');
                    input.value = keysData.keys.openai.masked_value;
                    input.dataset.isStored = 'true';
                }
                
                if (keysData.keys.wave?.present) {
                    const input = document.getElementById('wave-key-input');
                    input.value = keysData.keys.wave.masked_value;
                    input.dataset.isStored = 'true';
                }
                
                // Aggiorna status delle chiavi
                this.updateKeyStatus('openai', keysData.validation?.openai);
                this.updateKeyStatus('wave', keysData.validation?.wave);
            }
        } catch (error) {
            console.error('Errore caricamento chiavi:', error);
        }
    }
    
    updateKeyStatus(keyType, validationData) {
        const statusElement = document.getElementById(`${keyType}-status`);
        const validationElement = document.getElementById(`${keyType}-validation`);
        
        if (!statusElement || !validationElement) return;
        
        if (!validationData) {
            statusElement.innerHTML = '<span class="status-unknown">⚪ Non configurata</span>';
            validationElement.innerHTML = '';
            return;
        }
        
        if (validationData.valid) {
            statusElement.innerHTML = '<span class="status-valid">✅ Valida</span>';
            validationElement.innerHTML = `
                <div class="validation-success">
                    <strong>✅ Validazione riuscita</strong><br>
                    ${validationData.details || 'Chiave API funzionante'}
                </div>
            `;
        } else {
            statusElement.innerHTML = '<span class="status-invalid">❌ Non valida</span>';
            validationElement.innerHTML = `
                <div class="validation-error">
                    <strong>❌ ${validationData.error || 'Validazione fallita'}</strong><br>
                    ${validationData.details || 'Verifica la chiave inserita'}
                </div>
            `;
        }
    }
    
    async validateSingleKey(keyType) {
        const input = document.getElementById(`${keyType}-key-input`);
        const button = document.querySelector(`.test-api-key[data-key-type="${keyType}"]`);
        
        if (!input || !input.value.trim()) {
            alert('Inserisci prima una chiave API da validare');
            return;
        }
        
        // UI feedback
        const originalText = button.textContent;
        button.textContent = '⏳ Test...';
        button.disabled = true;
        
        try {
            const response = await fetch('/api/keys/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    key_type: keyType,
                    key_value: input.value.trim()
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateKeyStatus(keyType, data.validation);
            } else {
                this.updateKeyStatus(keyType, {
                    valid: false,
                    error: data.message || 'Errore di validazione',
                    details: data.details || ''
                });
            }
            
        } catch (error) {
            console.error(`Errore validazione ${keyType}:`, error);
            this.updateKeyStatus(keyType, {
                valid: false,
                error: 'Errore di connessione',
                details: 'Impossibile connettersi al server'
            });
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }
    
    async saveKeys() {
        const openaiInput = document.getElementById('openai-key-input');
        const waveInput = document.getElementById('wave-key-input');
        const saveButton = document.getElementById('save-api-keys');
        
        const openaiValue = openaiInput.value.trim();
        const waveValue = waveInput.value.trim();
        
        // Skip se sono chiavi mascherate e non modificate
        const openaiToSend = (openaiInput.dataset.isStored && openaiValue.includes('...')) ? null : openaiValue;
        const waveToSend = (waveInput.dataset.isStored && waveValue.includes('...')) ? null : waveValue;
        
        if (!openaiToSend && !waveToSend) {
            alert('Nessuna modifica da salvare');
            return;
        }
        
        // UI feedback
        const originalText = saveButton.textContent;
        saveButton.textContent = '💾 Salvataggio...';
        saveButton.disabled = true;
        
        try {
            const payload = {};
            if (openaiToSend) payload.openai_key = openaiToSend;
            if (waveToSend) payload.wave_key = waveToSend;
            
            const response = await fetch('/api/keys/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Aggiorna status delle chiavi
                if (data.validation) {
                    Object.keys(data.validation).forEach(keyType => {
                        this.updateKeyStatus(keyType, data.validation[keyType]);
                    });
                }
                
                // Aggiorna header
                await this.loadKeysStatus();
                
                // Feedback positivo
                this.showNotification('✅ Chiavi API salvate con successo!', 'success');
                
                // Chiudi modal dopo un breve delay
                setTimeout(() => {
                    this.hideModal();
                }, 1500);
                
            } else {
                this.showNotification(`❌ ${data.message || 'Errore durante il salvataggio'}`, 'error');
            }
            
        } catch (error) {
            console.error('Errore salvataggio:', error);
            this.showNotification('❌ Errore di connessione al server', 'error');
        } finally {
            saveButton.textContent = originalText;
            saveButton.disabled = false;
        }
    }
    
    toggleKeyVisibility(keyType) {
        const input = document.getElementById(`${keyType}-key-input`);
        const button = document.querySelector(`.toggle-key-visibility[data-key-type="${keyType}"]`);
        
        if (input.type === 'password') {
            input.type = 'text';
            button.textContent = '🙈';
            button.title = 'Nascondi chiave';
        } else {
            input.type = 'password';
            button.textContent = '👁️';
            button.title = 'Mostra chiave';
        }
    }
    
    onKeyInput(input) {
        // Rimuovi il flag "stored" quando l'utente modifica
        if (input.dataset.isStored) {
            delete input.dataset.isStored;
            
            // Reset validation status
            const keyType = input.dataset.keyType;
            this.updateKeyStatus(keyType, null);
        }
        
        // Validation pattern feedback
        const keyType = input.dataset.keyType;
        const value = input.value.trim();
        
        let isValidFormat = false;
        if (keyType === 'openai') {
            isValidFormat = value.startsWith('sk-') && value.length > 20;
        } else if (keyType === 'wave') {
            isValidFormat = value.length > 8; // Formato generico per WAVE
        }
        
        input.classList.toggle('valid-format', isValidFormat);
    }
    
    showNotification(message, type = 'info') {
        // Crea notification toast
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Posiziona in alto a destra
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 500;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        // Rimuovi dopo 4 secondi
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }
}

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.apiKeyManager = new APIKeyManager();
});

// Animazioni CSS per notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .notification-success {
        background-color: #10b981;
        color: white;
    }
    
    .notification-error {
        background-color: #ef4444;
        color: white;
    }
    
    .notification-info {
        background-color: #3b82f6;
        color: white;
    }
`;
document.head.appendChild(style);