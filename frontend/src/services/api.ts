import { 
  ScanConfiguration, 
  DiscoveredPage, 
  SmartSelectionConfig, 
  SmartSelectionResult,
  ScanResults 
} from '@types/index'

class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseUrl = '/api'
  
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    }
    
    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          errorData.message || `HTTP ${response.status}`,
          response.status,
          errorData.code
        )
      }
      
      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      
      throw new ApiError(
        error instanceof Error ? error.message : 'Errore di rete',
        0,
        'NETWORK_ERROR'
      )
    }
  }
  
  // Discovery APIs
  async startDiscovery(config: Pick<ScanConfiguration, 'url' | 'crawler'>): Promise<{ discovery_id: string }> {
    return this.request('/discovery/start', {
      method: 'POST',
      body: JSON.stringify(config)
    })
  }
  
  async getDiscoveryStatus(discoveryId: string): Promise<{
    status: string
    progress: number
    discovered_pages: DiscoveredPage[]
    error?: string
  }> {
    return this.request(`/discovery/${discoveryId}/status`)
  }
  
  async stopDiscovery(discoveryId: string): Promise<void> {
    return this.request(`/discovery/${discoveryId}/stop`, {
      method: 'POST'
    })
  }
  
  // Smart Selection APIs
  async getSmartSelection(
    pages: DiscoveredPage[],
    config: SmartSelectionConfig
  ): Promise<SmartSelectionResult> {
    return this.request('/selection/smart', {
      method: 'POST',
      body: JSON.stringify({ pages, config })
    })
  }
  
  async validateSelection(pages: DiscoveredPage[]): Promise<{
    valid: boolean
    warnings: string[]
    recommendations: string[]
  }> {
    return this.request('/selection/validate', {
      method: 'POST',
      body: JSON.stringify({ pages })
    })
  }
  
  // Scan APIs
  async startScan(config: ScanConfiguration, selectedPages: DiscoveredPage[]): Promise<{ scan_id: string }> {
    return this.request('/scan/start', {
      method: 'POST',
      body: JSON.stringify({
        configuration: config,
        selected_pages: selectedPages
      })
    })
  }
  
  async getScanStatus(scanId: string): Promise<{
    status: string
    progress: number
    phase: string
    pages_completed: number
    pages_total: number
    error?: string
  }> {
    return this.request(`/scan/${scanId}/status`)
  }
  
  async getScanResults(scanId: string): Promise<ScanResults> {
    return this.request(`/scan/${scanId}/results`)
  }
  
  async stopScan(scanId: string): Promise<void> {
    return this.request(`/scan/${scanId}/stop`, {
      method: 'POST'
    })
  }
  
  // Report APIs
  async generatePdfReport(scanId: string): Promise<{ pdf_url: string }> {
    return this.request(`/scan/${scanId}/pdf`, {
      method: 'POST'
    })
  }
  
  async downloadReport(scanId: string, format: 'html' | 'pdf' | 'json' | 'csv'): Promise<Blob> {
    const response = await fetch(`${this.baseUrl}/scan/${scanId}/download/${format}`)
    if (!response.ok) {
      throw new ApiError(`Errore download report: ${response.status}`)
    }
    return response.blob()
  }
  
  // Utility APIs
  async validateUrl(url: string): Promise<{
    valid: boolean
    accessible: boolean
    redirect_url?: string
    error?: string
  }> {
    return this.request('/validate-url', {
      method: 'POST',
      body: JSON.stringify({ url })
    })
  }
  
  async getPresets(): Promise<{
    methodologies: Array<{ id: string; name: string; description: string }>
    scanners: Array<{ id: string; name: string; description: string; available: boolean }>
  }> {
    return this.request('/presets')
  }
  
  // Health check
  async healthCheck(): Promise<{
    status: string
    version: string
    scanners_available: string[]
  }> {
    return this.request('/health')
  }
}

export const apiClient = new ApiClient()
export { ApiError }