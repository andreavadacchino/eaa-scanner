// Servizio API semplificato - NO DEBITO TECNICO
// Gestione robusta di polling e timeout per scansioni lunghe

interface ApiConfig {
  timeout?: number;
  retries?: number;
}

class SimpleApiService {
  private baseUrl = '/api';
  
  // Fetch con timeout e retry
  private async fetchWithTimeout(
    url: string, 
    options: RequestInit = {}, 
    config: ApiConfig = {}
  ): Promise<Response> {
    const { timeout = 30000, retries = 3 } = config;
    
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          }
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok && attempt < retries) {
          console.log(`Attempt ${attempt} failed, retrying...`);
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
          continue;
        }
        
        return response;
        
      } catch (error: any) {
        if (attempt === retries) {
          throw error;
        }
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
      }
    }
    
    throw new Error('Max retries reached');
  }

  // Discovery
  async startDiscovery(url: string, maxPages: number = 50) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/discovery/start`,
      {
        method: 'POST',
        body: JSON.stringify({ 
          url, 
          max_pages: maxPages,
          mode: 'smart'
        })
      },
      { timeout: 60000 }
    );
    
    const data = await response.json();
    return data.session_id;
  }

  async getDiscoveryStatus(sessionId: string) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/discovery/status/${sessionId}`,
      {},
      { timeout: 30000, retries: 1 }
    );
    return response.json();
  }

  async getDiscoveryResults(sessionId: string) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/discovery/results/${sessionId}`,
      {},
      { timeout: 30000, retries: 1 }
    );
    return response.json();
  }

  // Scan
  async startScan(pages: string[], companyName: string, email: string, scanners: any) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/scan/start`,
      {
        method: 'POST',
        body: JSON.stringify({
          pages,
          company_name: companyName,
          email,
          mode: 'real',
          scanners
        })
      },
      { timeout: 60000 }
    );
    
    const data = await response.json();
    return data.session_id || data.scan_id;
  }

  async getScanStatus(scanId: string) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/scan/status/${scanId}`,
      {},
      { timeout: 120000, retries: 1 } // Timeout lungo per scansioni reali
    );
    return response.json();
  }

  async getScanResults(scanId: string) {
    const response = await this.fetchWithTimeout(
      `${this.baseUrl}/scan/results/${scanId}`,
      {},
      { timeout: 30000 }
    );
    return response.json();
  }

  // Polling helper con backoff esponenziale
  async pollWithBackoff<T>(
    pollFn: () => Promise<T>,
    checkComplete: (data: T) => boolean,
    onUpdate?: (data: T) => void,
    maxWaitTime: number = 600000 // 10 minuti max
  ): Promise<T> {
    const startTime = Date.now();
    let backoffMs = 1000; // Start con 1 secondo
    const maxBackoff = 30000; // Max 30 secondi tra poll
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        const data = await pollFn();
        
        if (onUpdate) {
          onUpdate(data);
        }
        
        if (checkComplete(data)) {
          return data;
        }
        
        // Backoff esponenziale
        await new Promise(resolve => setTimeout(resolve, backoffMs));
        backoffMs = Math.min(backoffMs * 1.5, maxBackoff);
        
      } catch (error) {
        console.error('Polling error:', error);
        // Continua polling anche con errori
        await new Promise(resolve => setTimeout(resolve, backoffMs));
      }
    }
    
    throw new Error('Polling timeout exceeded');
  }
}

export const api = new SimpleApiService();