import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'
import { 
  ScanConfiguration, 
  DiscoveryStatus, 
  DiscoveredPage, 
  ScanProgress, 
  ScanResults,
  WorkflowStep,
  SmartSelectionConfig,
  SmartSelectionResult
} from '@types/index'

interface ScanState {
  // Workflow State
  currentStep: number
  steps: WorkflowStep[]
  isLoading: boolean
  error: string | null
  
  // Configuration
  configuration: Partial<ScanConfiguration>
  
  // Discovery Phase
  discoveryStatus: DiscoveryStatus
  discoveredPages: DiscoveredPage[]
  selectedPages: DiscoveredPage[]
  
  // Smart Selection
  smartSelectionConfig: SmartSelectionConfig
  smartSelectionResult: SmartSelectionResult | null
  
  // Scanning Phase
  scanProgress: ScanProgress | null
  scanResults: ScanResults | null
  
  // Actions
  setCurrentStep: (step: number) => void
  updateStepStatus: (stepId: number, status: WorkflowStep['status']) => void
  setConfiguration: (config: Partial<ScanConfiguration>) => void
  setDiscoveryStatus: (status: DiscoveryStatus) => void
  addDiscoveredPage: (page: DiscoveredPage) => void
  updateDiscoveredPages: (pages: DiscoveredPage[]) => void
  togglePageSelection: (pageUrl: string) => void
  selectAllPages: () => void
  selectNonePages: () => void
  applySmartSelection: (config: SmartSelectionConfig) => Promise<void>
  setScanProgress: (progress: ScanProgress) => void
  setScanResults: (results: ScanResults) => void
  resetScan: () => void
  setError: (error: string | null) => void
  setLoading: (loading: boolean) => void
}

const initialSteps: WorkflowStep[] = [
  {
    id: 1,
    name: 'configuration',
    title: 'Configurazione',
    description: 'Imposta URL e parametri di scansione',
    status: 'active'
  },
  {
    id: 2,
    name: 'discovery',
    title: 'Discovery URL',
    description: 'Scoperta automatica delle pagine del sito',
    status: 'pending'
  },
  {
    id: 3,
    name: 'selection',
    title: 'Selezione Pagine',
    description: 'Seleziona le pagine da analizzare',
    status: 'pending'
  },
  {
    id: 4,
    name: 'scanning',
    title: 'Scansione',
    description: 'Analisi accessibilità delle pagine selezionate',
    status: 'pending'
  },
  {
    id: 5,
    name: 'results',
    title: 'Risultati',
    description: 'Report finale e risultati della scansione',
    status: 'pending'
  }
]

const initialDiscoveryStatus: DiscoveryStatus = {
  status: 'idle',
  progress: 0,
  discovered_count: 0
}

const initialSmartSelectionConfig: SmartSelectionConfig = {
  strategy: 'wcag_em',
  max_pages: 10,
  include_critical: true,
  balance_templates: true,
  prioritize_complex: false
}

export const useScanStore = create<ScanState>()(devtools(
  subscribeWithSelector((set, get) => ({
    // Initial State
    currentStep: 1,
    steps: initialSteps,
    isLoading: false,
    error: null,
    
    configuration: {
      scanners: {
        wave: false,
        pa11y: true,
        axe: true,
        lighthouse: true
      },
      methodology: {
        sample_methodology: 'wcag_em',
        analysis_depth: 'standard',
        max_pages: 10,
        include_pdfs: false,
        smart_selection: true
      },
      crawler: {
        max_pages: 50,
        max_depth: 3,
        follow_external: false,
        timeout_ms: 30000,
        use_playwright: true
      }
    },
    
    discoveryStatus: initialDiscoveryStatus,
    discoveredPages: [],
    selectedPages: [],
    
    smartSelectionConfig: initialSmartSelectionConfig,
    smartSelectionResult: null,
    
    scanProgress: null,
    scanResults: null,
    
    // Actions
    setCurrentStep: (step) => {
      set((state) => {
        const newSteps = state.steps.map(s => ({
          ...s,
          status: s.id === step ? 'active' as const : 
                 s.id < step ? 'completed' as const : 'pending' as const
        }))
        
        return {
          currentStep: step,
          steps: newSteps
        }
      })
    },
    
    updateStepStatus: (stepId, status) => {
      set((state) => ({
        steps: state.steps.map(step => 
          step.id === stepId ? { ...step, status } : step
        )
      }))
    },
    
    setConfiguration: (config) => {
      set((state) => ({
        configuration: { ...state.configuration, ...config }
      }))
    },
    
    setDiscoveryStatus: (status) => {
      set({ discoveryStatus: status })
    },
    
    addDiscoveredPage: (page) => {
      set((state) => {
        const exists = state.discoveredPages.find(p => p.url === page.url)
        if (exists) return state
        
        return {
          discoveredPages: [...state.discoveredPages, page]
        }
      })
    },
    
    updateDiscoveredPages: (pages) => {
      set({ discoveredPages: pages })
    },
    
    togglePageSelection: (pageUrl) => {
      set((state) => {
        const page = state.discoveredPages.find(p => p.url === pageUrl)
        if (!page) return state
        
        const updatedPages = state.discoveredPages.map(p => 
          p.url === pageUrl ? { ...p, selected: !p.selected } : p
        )
        
        const selectedPages = updatedPages.filter(p => p.selected)
        
        return {
          discoveredPages: updatedPages,
          selectedPages
        }
      })
    },
    
    selectAllPages: () => {
      set((state) => {
        const updatedPages = state.discoveredPages.map(p => ({ ...p, selected: true }))
        return {
          discoveredPages: updatedPages,
          selectedPages: [...updatedPages]
        }
      })
    },
    
    selectNonePages: () => {
      set((state) => ({
        discoveredPages: state.discoveredPages.map(p => ({ ...p, selected: false })),
        selectedPages: []
      }))
    },
    
    applySmartSelection: async (config) => {
      const state = get()
      set({ isLoading: true, smartSelectionConfig: config })
      
      try {
        const response = await fetch('/api/smart-selection', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pages: state.discoveredPages,
            config
          })
        })
        
        if (!response.ok) throw new Error('Errore nella selezione intelligente')
        
        const result: SmartSelectionResult = await response.json()
        
        // Aggiorna le pagine selezionate
        const selectedUrls = new Set(result.selected_pages.map(p => p.url))
        const updatedPages = state.discoveredPages.map(p => ({
          ...p,
          selected: selectedUrls.has(p.url)
        }))
        
        set({
          discoveredPages: updatedPages,
          selectedPages: result.selected_pages,
          smartSelectionResult: result,
          isLoading: false
        })
        
      } catch (error) {
        set({ 
          error: error instanceof Error ? error.message : 'Errore sconosciuto',
          isLoading: false 
        })
      }
    },
    
    setScanProgress: (progress) => {
      set({ scanProgress: progress })
    },
    
    setScanResults: (results) => {
      set({ scanResults: results })
    },
    
    resetScan: () => {
      set({
        currentStep: 1,
        steps: initialSteps,
        isLoading: false,
        error: null,
        discoveryStatus: initialDiscoveryStatus,
        discoveredPages: [],
        selectedPages: [],
        smartSelectionResult: null,
        scanProgress: null,
        scanResults: null
      })
    },
    
    setError: (error) => {
      set({ error, isLoading: false })
    },
    
    setLoading: (loading) => {
      set({ isLoading: loading })
    }
    
  })),
  {
    name: 'scan-store'
  }
))