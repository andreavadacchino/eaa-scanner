import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { ConfigData, PageInfo, ScanResponse, ReportData } from '../services/apiClient';

// Definizione degli step del workflow
export enum WorkflowStep {
  CONFIGURATION = 0,
  DISCOVERY = 1,
  SELECTION = 2,
  SCANNING = 3,
  LLM_CONFIGURATION = 4,
  REPORT = 5,
}

// Stato globale dell'applicazione
interface AppState {
  // Step corrente del workflow
  currentStep: WorkflowStep;
  
  // Configurazione iniziale
  config: ConfigData | null;
  
  // Discovery
  discoverySessionId: string | null;
  discoveredPages: PageInfo[];
  
  // Selezione pagine
  selectedPages: string[];
  
  // Scansione
  scanSessionId: string | null;
  scanResults: ScanResponse | null;
  
  // LLM Configuration
  llmModel: string | null;
  
  // Report
  reportData: ReportData | null;
  
  // Stati UI
  loading: {
    discovery: boolean;
    scan: boolean;
    report: boolean;
  };
  
  errors: {
    discovery: string | null;
    scan: string | null;
    report: string | null;
  };
}

// Azioni disponibili nel contesto
interface AppContextValue extends AppState {
  // Navigazione
  goToStep: (step: WorkflowStep) => void;
  canNavigateToStep: (step: WorkflowStep) => boolean;
  
  // Configurazione
  setConfig: (config: ConfigData) => void;
  
  // Discovery
  setDiscoverySessionId: (id: string) => void;
  setDiscoveredPages: (pages: PageInfo[]) => void;
  
  // Selezione
  setSelectedPages: (pages: string[]) => void;
  togglePageSelection: (pageUrl: string) => void;
  selectAllPages: () => void;
  deselectAllPages: () => void;
  
  // Scansione
  setScanSessionId: (id: string) => void;
  setScanResults: (results: ScanResponse) => void;
  
  // LLM
  setLLMModel: (model: string | null) => void;
  
  // Report
  setReportData: (data: ReportData) => void;
  
  // Stati UI
  setLoading: (key: keyof AppState['loading'], value: boolean) => void;
  setError: (key: keyof AppState['errors'], value: string | null) => void;
  
  // Reset
  resetApp: () => void;
  resetFromStep: (step: WorkflowStep) => void;
}

// Stato iniziale
const initialState: AppState = {
  currentStep: WorkflowStep.CONFIGURATION,
  config: null,
  discoverySessionId: null,
  discoveredPages: [],
  selectedPages: [],
  scanSessionId: null,
  scanResults: null,
  llmModel: null,
  reportData: null,
  loading: {
    discovery: false,
    scan: false,
    report: false,
  },
  errors: {
    discovery: null,
    scan: null,
    report: null,
  },
};

// Creazione del contesto
const AppContext = createContext<AppContextValue | undefined>(undefined);

// Provider del contesto
export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AppState>(initialState);

  // Verifica se è possibile navigare a uno step - VALIDAZIONE RIGOROSA
  const canNavigateToStep = useCallback((step: WorkflowStep): boolean => {
    const { currentStep, config, discoveredPages, selectedPages, scanResults } = state;
    
    // Non permettere di saltare passi
    if (step > currentStep + 1) {
      console.warn(`❌ Non puoi saltare dal passo ${currentStep} al passo ${step}`);
      return false;
    }
    
    // Permetti sempre di tornare indietro
    if (step <= currentStep) {
      return true;
    }
    
    // Validazione per passo successivo
    switch (step) {
      case WorkflowStep.CONFIGURATION:
        return true;
        
      case WorkflowStep.DISCOVERY:
        return config !== null && 
               config.url !== '' && 
               config.company_name !== '' && 
               config.email !== '';
               
      case WorkflowStep.SELECTION:
        return currentStep === WorkflowStep.DISCOVERY && 
               discoveredPages.length > 0;
               
      case WorkflowStep.SCANNING:
        return currentStep === WorkflowStep.SELECTION && 
               selectedPages.length > 0;
               
      case WorkflowStep.LLM_CONFIGURATION:
        return currentStep === WorkflowStep.SCANNING && 
               scanResults?.status === 'completed' &&
               (scanResults.pages_scanned > 0 || scanResults.pages_total > 0);
               
      case WorkflowStep.REPORT:
        return (currentStep === WorkflowStep.SCANNING || 
                currentStep === WorkflowStep.LLM_CONFIGURATION) && 
               scanResults?.status === 'completed';
               
      default:
        return false;
    }
  }, [state]);

  // Navigazione tra step con validazione
  const goToStep = useCallback((step: WorkflowStep) => {
    if (canNavigateToStep(step)) {
      console.log(`✅ Navigazione autorizzata al passo ${WorkflowStep[step]}`);
      setState(prev => ({ ...prev, currentStep: step }));
    } else {
      console.error(`❌ Navigazione negata al passo ${WorkflowStep[step]}`, {
        currentStep: state.currentStep,
        targetStep: step,
        hasConfig: !!state.config,
        discoveredPages: state.discoveredPages.length,
        selectedPages: state.selectedPages.length,
        scanStatus: state.scanResults?.status
      });
    }
  }, [canNavigateToStep, state]);

  // Set configurazione
  const setConfig = useCallback((config: ConfigData) => {
    setState(prev => ({ ...prev, config }));
  }, []);

  // Discovery
  const setDiscoverySessionId = useCallback((id: string) => {
    setState(prev => ({ ...prev, discoverySessionId: id }));
  }, []);

  const setDiscoveredPages = useCallback((pages: PageInfo[]) => {
    setState(prev => ({ ...prev, discoveredPages: pages }));
  }, []);

  // Selezione pagine
  const setSelectedPages = useCallback((pages: string[]) => {
    setState(prev => ({ ...prev, selectedPages: pages }));
  }, []);

  const togglePageSelection = useCallback((pageUrl: string) => {
    setState(prev => {
      const isSelected = prev.selectedPages.includes(pageUrl);
      const newSelected = isSelected
        ? prev.selectedPages.filter(url => url !== pageUrl)
        : [...prev.selectedPages, pageUrl];
      return { ...prev, selectedPages: newSelected };
    });
  }, []);

  const selectAllPages = useCallback(() => {
    setState(prev => ({
      ...prev,
      selectedPages: prev.discoveredPages.map(p => p.url),
    }));
  }, []);

  const deselectAllPages = useCallback(() => {
    setState(prev => ({ ...prev, selectedPages: [] }));
  }, []);

  // Scansione
  const setScanSessionId = useCallback((id: string) => {
    setState(prev => ({ ...prev, scanSessionId: id }));
  }, []);

  const setScanResults = useCallback((results: ScanResponse) => {
    setState(prev => ({ ...prev, scanResults: results }));
  }, []);

  // LLM
  const setLLMModel = useCallback((model: string | null) => {
    setState(prev => ({ ...prev, llmModel: model }));
  }, []);

  // Report
  const setReportData = useCallback((data: ReportData) => {
    setState(prev => ({ ...prev, reportData: data }));
  }, []);

  // Stati UI
  const setLoading = useCallback((key: keyof AppState['loading'], value: boolean) => {
    setState(prev => ({
      ...prev,
      loading: { ...prev.loading, [key]: value },
    }));
  }, []);

  const setError = useCallback((key: keyof AppState['errors'], value: string | null) => {
    setState(prev => ({
      ...prev,
      errors: { ...prev.errors, [key]: value },
    }));
  }, []);

  // Reset completo
  const resetApp = useCallback(() => {
    setState(initialState);
  }, []);

  // Reset da uno step specifico
  const resetFromStep = useCallback((step: WorkflowStep) => {
    setState(prev => {
      const newState = { ...prev };
      
      if (step <= WorkflowStep.DISCOVERY) {
        newState.discoverySessionId = null;
        newState.discoveredPages = [];
        newState.errors.discovery = null;
      }
      
      if (step <= WorkflowStep.SELECTION) {
        newState.selectedPages = [];
      }
      
      if (step <= WorkflowStep.SCANNING) {
        newState.scanSessionId = null;
        newState.scanResults = null;
        newState.errors.scan = null;
      }
      
      if (step <= WorkflowStep.REPORT) {
        newState.reportData = null;
        newState.errors.report = null;
      }
      
      newState.currentStep = step;
      return newState;
    });
  }, []);

  const contextValue: AppContextValue = {
    ...state,
    goToStep,
    canNavigateToStep,
    setConfig,
    setDiscoverySessionId,
    setDiscoveredPages,
    setSelectedPages,
    togglePageSelection,
    selectAllPages,
    deselectAllPages,
    setScanSessionId,
    setScanResults,
    setLLMModel,
    setReportData,
    setLoading,
    setError,
    resetApp,
    resetFromStep,
  };

  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Hook per usare il contesto
export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext deve essere usato dentro AppProvider');
  }
  return context;
};

// Export di utilità per i componenti
export const useWorkflowNavigation = () => {
  const { currentStep, goToStep, canNavigateToStep } = useAppContext();
  
  const goToNextStep = useCallback(() => {
    const nextStep = currentStep + 1;
    if (nextStep <= WorkflowStep.REPORT && canNavigateToStep(nextStep as WorkflowStep)) {
      goToStep(nextStep as WorkflowStep);
    }
  }, [currentStep, goToStep, canNavigateToStep]);
  
  const goToPreviousStep = useCallback(() => {
    const prevStep = currentStep - 1;
    if (prevStep >= WorkflowStep.CONFIGURATION) {
      goToStep(prevStep as WorkflowStep);
    }
  }, [currentStep, goToStep]);
  
  return {
    currentStep,
    goToStep,
    goToNextStep,
    goToPreviousStep,
    canNavigateToStep,
  };
};