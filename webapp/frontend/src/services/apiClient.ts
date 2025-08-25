/**
 * API Client unificato per EAA Scanner
 * Gestisce tutte le comunicazioni con il backend FastAPI
 */

interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

const API_CONFIG: ApiConfig = {
  baseUrl: '/api',
  timeout: 60000, // 60 secondi per operazioni standard
  retryAttempts: 3,
  retryDelay: 2000,
};

// Tipi di richiesta/risposta
export interface ConfigData {
  url: string;
  company_name: string;
  email: string;
  scanners: string[];
}

export interface DiscoveryRequest {
  url: string;
  max_depth?: number;
  max_pages?: number;
}

export interface DiscoveryResponse {
  session_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  state?: 'pending' | 'running' | 'completed' | 'failed';
  pages?: PageInfo[];
  discovered_pages?: PageInfo[];
  pages_found?: number;
  pages_discovered?: number;
  error?: string;
  progress?: number;
  progress_percent?: number;
  message?: string;
}

export interface PageInfo {
  url: string;
  title: string;
  type: 'page' | 'form' | 'document' | 'other';
  depth: number;
}

export interface ScanRequest {
  pages: string[];
  company_name: string;
  email: string;
  scanners: string[];
}

export interface ScanResponse {
  session_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  current_page?: string;
  // Backend restituisce questi nomi:
  pages_scanned?: number;
  total_pages?: number;
  // Alias per retrocompatibilità:
  pages_completed?: number;
  pages_total?: number;
  results?: any;
  error?: string;
  // Proprietà aggiuntive dal backend:
  issues_found?: number;
}

export interface ReportData {
  session_id: string;
  company_name: string;
  url: string;
  scan_date: string;
  issues_total: number;
  issues_by_severity: Record<string, number>;
  pages_scanned: number;
  scanners_used: string[];
  compliance_score: number;
  detailed_results: any[];
}

class ApiClient {
  private abortController: AbortController | null = null;

  /**
   * Esegue una richiesta HTTP con timeout e retry
   */
  private async request<T>(
    url: string,
    options: RequestInit = {},
    customTimeout?: number
  ): Promise<T> {
    const timeout = customTimeout || API_CONFIG.timeout;
    
    for (let attempt = 1; attempt <= API_CONFIG.retryAttempts; attempt++) {
      try {
        this.abortController = new AbortController();
        
        // Setup timeout
        const timeoutId = setTimeout(() => {
          this.abortController?.abort();
        }, timeout);

        const response = await fetch(`${API_CONFIG.baseUrl}${url}`, {
          ...options,
          signal: this.abortController.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorText = await response.text();
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          
          try {
            const errorData = JSON.parse(errorText);
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch {
            // Usa il testo dell'errore se non è JSON
            if (errorText) errorMessage = errorText;
          }
          
          // Per errori 500 durante il polling, potrebbe essere che la scansione è completata
          // ma c'è un problema temporaneo con l'endpoint
          if (response.status === 500 && url.includes('/scan/status/')) {
            console.warn(`⚠️ HTTP 500 su scan status - potrebbe essere problema temporaneo:`, errorMessage);
            // Non lanciare immediatamente l'errore, lascia che il retry gestisca
          }
          
          throw new Error(errorMessage);
        }

        const data = await response.json();
        return data;
        
      } catch (error) {
        // Se è l'ultimo tentativo, rilancia l'errore
        if (attempt === API_CONFIG.retryAttempts) {
          if (error instanceof Error && error.name === 'AbortError') {
            throw new Error(`Timeout dopo ${timeout/1000} secondi`);
          }
          throw error;
        }
        
        // Aspetta prima di riprovare
        console.log(`Tentativo ${attempt} fallito, riprovo tra ${API_CONFIG.retryDelay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, API_CONFIG.retryDelay));
      }
    }
    
    throw new Error('Tutti i tentativi falliti');
  }

  /**
   * Health check del sistema
   */
  async healthCheck(): Promise<{ status: string; services: Record<string, boolean> }> {
    return this.request('/health');
  }

  /**
   * 1. DISCOVERY - Avvia il crawler per trovare tutte le pagine
   */
  async startDiscovery(url: string): Promise<DiscoveryResponse> {
    const request: DiscoveryRequest = {
      url,
      max_depth: 3,
      max_pages: 100,
    };
    
    return this.request<DiscoveryResponse>(
      '/discovery/start',
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      120000 // 2 minuti per discovery
    );
  }

  /**
   * Controlla lo stato del discovery
   */
  async getDiscoveryStatus(sessionId: string): Promise<DiscoveryResponse> {
    return this.request<DiscoveryResponse>(`/discovery/status/${sessionId}`);
  }

  /**
   * Ottieni i risultati del discovery
   */
  async getDiscoveryResults(sessionId: string): Promise<DiscoveryResponse> {
    return this.request<DiscoveryResponse>(`/discovery/results/${sessionId}`);
  }

  /**
   * Polling del discovery con callback di progresso
   */
  async pollDiscovery(
    sessionId: string,
    onProgress: (status: DiscoveryResponse) => void,
    pollInterval = 5000,
    maxAttempts = 60
  ): Promise<DiscoveryResponse> {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const status = await this.getDiscoveryStatus(sessionId);
        onProgress(status);
        
        const currentStatus = status.state || status.status;
        if (currentStatus === 'completed' || currentStatus === 'failed') {
          return status;
        }
        
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
        
      } catch (error) {
        console.error('Errore polling discovery:', error);
        attempts++;
        
        if (attempts >= maxAttempts) {
          throw new Error('Discovery timeout');
        }
        
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error('Discovery timeout: operazione troppo lunga');
  }

  /**
   * 2. SCAN - Avvia la scansione delle pagine selezionate
   */
  async startScan(request: ScanRequest): Promise<ScanResponse> {
    return this.request<ScanResponse>(
      '/scan/start',
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      180000 // 3 minuti per avviare scan
    );
  }

  /**
   * Controlla lo stato della scansione
   */
  async getScanStatus(sessionId: string): Promise<ScanResponse> {
    return this.request<ScanResponse>(`/scan/status/${sessionId}`);
  }

  /**
   * Polling della scansione con callback di progresso
   */
  async pollScan(
    sessionId: string,
    onProgress: (status: ScanResponse) => void,
    pollInterval = 8000, // 8 secondi tra un check e l'altro (più veloce)
    maxAttempts = 150 // 20 minuti max
  ): Promise<ScanResponse> {
    let attempts = 0;
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 5;
    
    while (attempts < maxAttempts) {
      try {
        const status = await this.getScanStatus(sessionId);
        
        // Normalizza le proprietà del backend per compatibilità frontend
        const normalizedStatus: ScanResponse = {
          ...status,
          // Mapping corretto dalle proprietà del backend
          pages_completed: status.pages_scanned || status.pages_completed || 0,
          pages_total: status.total_pages || status.pages_total || 0,
        };
        
        console.log(`📊 Scan Status - Attempt ${attempts + 1}:`, {
          status: normalizedStatus.status,
          progress: normalizedStatus.progress,
          pages: `${normalizedStatus.pages_completed}/${normalizedStatus.pages_total}`,
          current_page: normalizedStatus.current_page,
          has_results: !!normalizedStatus.results
        });
        
        onProgress(normalizedStatus);
        
        // Reset consecutive errors on success
        consecutiveErrors = 0;
        
        if (normalizedStatus.status === 'completed' || normalizedStatus.status === 'failed') {
          console.log(`✅ Scan ${normalizedStatus.status}:`, normalizedStatus);
          return normalizedStatus;
        }
        
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        attempts++;
        
      } catch (error) {
        consecutiveErrors++;
        console.error(`❌ Errore polling scan (tentativo ${attempts + 1}, errori consecutivi: ${consecutiveErrors}):`, error);
        
        // Se abbiamo troppi errori consecutivi, fallisci subito
        if (consecutiveErrors >= maxConsecutiveErrors) {
          throw new Error(`Troppi errori consecutivi (${consecutiveErrors}) durante il polling della scansione`);
        }
        
        attempts++;
        
        if (attempts >= maxAttempts) {
          throw new Error('Scan timeout: polling scaduto dopo tutti i tentativi');
        }
        
        // Backoff esponenziale per errori consecutivi
        const backoffDelay = Math.min(pollInterval * Math.pow(1.5, consecutiveErrors - 1), 30000);
        console.log(`⏳ Attendo ${backoffDelay/1000}s prima del prossimo tentativo...`);
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
      }
    }
    
    throw new Error('Scan timeout: operazione troppo lunga');
  }

  /**
   * 3. REPORT - Ottieni i risultati della scansione
   */
  async getScanResults(sessionId: string): Promise<ReportData> {
    return this.request<ReportData>(`/scan/results/${sessionId}`);
  }

  /**
   * Verifica se una scansione è completata anche se lo status endpoint fallisce
   */
  async checkScanCompletion(sessionId: string): Promise<boolean> {
    try {
      // Prova a ottenere i risultati direttamente
      await this.getScanResults(sessionId);
      return true; // Se non lancia errore, la scansione è completata
    } catch (error) {
      // Se fallisce, la scansione non è ancora completata
      return false;
    }
  }

  /**
   * Genera PDF del report
   */
  async generatePdf(sessionId: string): Promise<{ pdf_url: string }> {
    return this.request(
      `/generate_pdf/${sessionId}`,
      { method: 'POST' },
      60000
    );
  }

  /**
   * Scarica il report
   */
  async downloadReport(sessionId: string, format: 'html' | 'pdf' = 'pdf'): Promise<Blob> {
    const response = await fetch(
      `${API_CONFIG.baseUrl}/download_report/${sessionId}?format=${format}`
    );
    
    if (!response.ok) {
      throw new Error(`Download fallito: ${response.statusText}`);
    }
    
    return response.blob();
  }

  /**
   * Annulla richieste in corso
   */
  cancelRequests(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Verifica capabilities degli scanner
   */
  async getScannerCapabilities(): Promise<{
    available_scanners: string[];
    scanner_details: Record<string, any>;
  }> {
    return this.request('/scanner/capabilities');
  }
}

// Singleton instance
export const apiClient = new ApiClient();

// Helper per validazioni locali
export const validators = {
  isValidUrl: (url: string): boolean => {
    try {
      new URL(url.startsWith('http') ? url : `https://${url}`);
      return true;
    } catch {
      return false;
    }
  },
  
  isValidEmail: (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },
  
  formatUrl: (url: string): string => {
    if (!url.startsWith('http')) {
      return `https://${url}`;
    }
    return url;
  }
};