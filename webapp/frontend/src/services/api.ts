import { 
  DiscoveryRequest, 
  DiscoveryResponse, 
  DiscoveryStatus,
  ScanRequest,
  MultiPageScanRequest,
  ScanResponse,
  ScanStatus,
  ApiError,
  ReportsListResponse,
  ReportFilters
} from '../types';

const API_BASE = '/api';

// Configurazione per timeouts e retry
const TIMEOUT_CONFIG = {
  short: 30000,   // 30s per request normali
  long: 120000,   // 2min per request lunghe (scan/discovery)
  polling: 5000   // 5s per polling iniziale
};

// Backoff esponenziale per polling
const calculateBackoff = (attempt: number): number => {
  const base = 1000; // 1 secondo base
  const max = 30000; // massimo 30 secondi
  return Math.min(base * Math.pow(2, attempt), max);
};

class ApiService {
  private abortController: AbortController | null = null;

  // Utility per fare richieste con timeout
  private async fetchWithTimeout(url: string, options: RequestInit = {}, timeout: number = TIMEOUT_CONFIG.short): Promise<Response> {
    this.abortController = new AbortController();
    
    const timeoutId = setTimeout(() => {
      if (this.abortController) {
        this.abortController.abort();
      }
    }, timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: this.abortController.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          // Gestisci diversi formati di errore dal backend
          if (Array.isArray(errorData)) {
            // Array di errori di validazione
            errorMessage = errorData.map((err: any) => 
              typeof err === 'string' ? err : (err.msg || err.message || JSON.stringify(err))
            ).join(', ');
          } else if (errorData.detail) {
            // Formato FastAPI standard
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map((d: any) => 
                typeof d === 'string' ? d : (d.msg || JSON.stringify(d))
              ).join(', ');
            } else {
              errorMessage = errorData.detail;
            }
          } else if (errorData.message) {
            errorMessage = errorData.message;
          }
        } catch {
          // Ignora errori nel parsing dell'errore
        }
        throw new Error(errorMessage);
      }

      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Richiesta interrotta per timeout');
      }
      throw error;
    } finally {
      this.abortController = null;
    }
  }

  // Health check
  async healthCheck(): Promise<{status: string}> {
    const response = await this.fetchWithTimeout(`${API_BASE}/health`);
    return response.json();
  }

  // Discovery API
  async startDiscovery(request: DiscoveryRequest): Promise<DiscoveryResponse> {
    const response = await this.fetchWithTimeout(
      `${API_BASE}/discovery/start`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      TIMEOUT_CONFIG.long
    );
    return response.json();
  }

  async getDiscoveryStatus(sessionId: string): Promise<DiscoveryStatus> {
    const response = await this.fetchWithTimeout(
      `${API_BASE}/discovery/status/${sessionId}`,
      { method: 'GET' },
      TIMEOUT_CONFIG.short
    );
    return response.json();
  }

  // Polling per discovery con backoff esponenziale
  async pollDiscoveryStatus(
    sessionId: string,
    onProgress: (status: DiscoveryStatus) => void,
    maxAttempts: number = 60 // circa 10 minuti con backoff
  ): Promise<DiscoveryStatus> {
    let attempts = 0;
    
    const poll = async (): Promise<DiscoveryStatus> => {
      attempts++;
      
      try {
        const status = await this.getDiscoveryStatus(sessionId);
        onProgress(status);

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        if (attempts >= maxAttempts) {
          throw new Error('Timeout: discovery durata troppo a lungo');
        }

        // Calcola il prossimo intervallo di polling con backoff esponenziale
        const delay = calculateBackoff(Math.floor(attempts / 5));
        console.log(`Polling discovery in ${delay}ms (tentativo ${attempts})`);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return poll();
        
      } catch (error) {
        if (attempts < 3) {
          // Riprova fino a 3 volte per errori di rete
          console.warn(`Errore polling discovery, riprova in 5s (tentativo ${attempts}/3)`, error);
          await new Promise(resolve => setTimeout(resolve, 5000));
          return poll();
        }
        throw error;
      }
    };

    return poll();
  }

  // Scan API
  async startScan(request: ScanRequest): Promise<ScanResponse> {
    const response = await this.fetchWithTimeout(
      `${API_BASE}/v2/scan`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      TIMEOUT_CONFIG.long
    );
    return response.json();
  }

  async startMultiPageScan(request: MultiPageScanRequest): Promise<ScanResponse> {
    // Il backend usa /api/scan/start per gestire sia scan singoli che multipli
    // Se la richiesta contiene 'pages', viene trattata come multi-page scan
    const response = await this.fetchWithTimeout(
      `${API_BASE}/scan/start`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      },
      TIMEOUT_CONFIG.long
    );
    return response.json();
  }

  async getScanStatus(scanId: string): Promise<ScanStatus> {
    const response = await this.fetchWithTimeout(
      `${API_BASE}/v2/scan/${scanId}`,
      { method: 'GET' },
      TIMEOUT_CONFIG.short
    );
    return response.json();
  }

  // Polling per scan con backoff esponenziale
  async pollScanStatus(
    scanId: string,
    onProgress: (status: ScanStatus) => void,
    maxAttempts: number = 120 // circa 20 minuti con backoff
  ): Promise<ScanStatus> {
    let attempts = 0;
    
    const poll = async (): Promise<ScanStatus> => {
      attempts++;
      
      try {
        const status = await this.getScanStatus(scanId);
        onProgress(status);

        if (status.status === 'completed' || status.status === 'failed') {
          return status;
        }

        if (attempts >= maxAttempts) {
          throw new Error('Timeout: scansione durata troppo a lungo');
        }

        // Calcola il prossimo intervallo di polling con backoff esponenziale
        const delay = calculateBackoff(Math.floor(attempts / 5));
        console.log(`Polling scan in ${delay}ms (tentativo ${attempts})`);
        
        await new Promise(resolve => setTimeout(resolve, delay));
        return poll();
        
      } catch (error) {
        if (attempts < 3) {
          // Riprova fino a 3 volte per errori di rete
          console.warn(`Errore polling scan, riprova in 5s (tentativo ${attempts}/3)`, error);
          await new Promise(resolve => setTimeout(resolve, 5000));
          return poll();
        }
        throw error;
      }
    };

    return poll();
  }

  // Report download
  async downloadReport(scanId: string, format: 'html' | 'pdf' = 'pdf'): Promise<Blob> {
    const response = await this.fetchWithTimeout(
      `${API_BASE}/scan/${scanId}/report?format=${format}`,
      { method: 'GET' },
      TIMEOUT_CONFIG.long
    );
    return response.blob();
  }

  // Get reports list
  async getReportsList(
    skip: number = 0,
    limit: number = 20,
    filters?: ReportFilters
  ): Promise<ReportsListResponse> {
    const params = new URLSearchParams({
      skip: skip.toString(),
      limit: limit.toString(),
      ...(filters?.status && { status: filters.status }),
      ...(filters?.order_by && { order_by: filters.order_by }),
      ...(filters?.order_dir && { order_dir: filters.order_dir })
    });

    const response = await this.fetchWithTimeout(
      `${API_BASE}/reports?${params}`,
      { method: 'GET' },
      TIMEOUT_CONFIG.short
    );

    return response.json();
  }

  // Utility per cancellare richieste in corso
  cancelRequest(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  // Validation endpoint
  async validateScanRequest(request: Partial<ScanRequest>): Promise<{valid: boolean; errors?: string[]}> {
    try {
      console.log('Sending validation request:', request);
      const response = await this.fetchWithTimeout(
        `${API_BASE}/scan/validate`,
        {
          method: 'POST',
          body: JSON.stringify(request),
        }
      );
      const result = await response.json();
      console.log('Validation response:', result);
      
      // Il backend restituisce un formato diverso, adattiamolo
      if (result.validation) {
        return {
          valid: result.validation.valid,
          errors: result.validation.errors || []
        };
      }
      return result;
    } catch (error) {
      console.error('Validation error:', error);
      return {
        valid: false,
        errors: [error instanceof Error ? error.message : 'Errore di validazione']
      };
    }
  }
}

// Singleton instance
export const apiService = new ApiService();

// Hook personalizzato per gestire errori API
export const handleApiError = (error: unknown): ApiError => {
  if (error instanceof Error) {
    return {
      message: error.message,
      details: error
    };
  }
  
  return {
    message: 'Errore sconosciuto',
    details: error
  };
};

// Helper per formattare URL
export const formatUrl = (url: string): string => {
  try {
    const urlObj = new URL(url);
    return urlObj.toString();
  } catch {
    // Se l'URL non è valido, prova ad aggiungere https://
    try {
      const urlObj = new URL(`https://${url}`);
      return urlObj.toString();
    } catch {
      return url; // Ritorna l'URL originale se non riesce a formattarlo
    }
  }
};

// Helper per validare URL
export const validateUrl = (url: string): boolean => {
  try {
    new URL(url.startsWith('http') ? url : `https://${url}`);
    return true;
  } catch {
    return false;
  }
};

// Helper per validare email
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};
