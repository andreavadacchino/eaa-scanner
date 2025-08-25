import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { 
  ScanRequest, 
  PageInfo as DiscoveredPage, 
  ScanResponse as ScanResult
} from '../services/apiClient';

// Definizioni locali per il context
export interface ScannerConfig {
  pa11y: boolean;
  axe: boolean;
  lighthouse: boolean;
  wave: boolean;
}

export interface AppContextValue {
  // Step management
  currentStep: number;
  setCurrentStep: (step: number) => void;
  goToNextStep: () => void;
  goToPreviousStep: () => void;
  
  // Configuration
  config: ScanRequest | null;
  setConfig: (config: ScanRequest) => void;
  
  // Discovery
  discoveryId: string | null;
  setDiscoveryId: (id: string | null) => void;
  discoveredPages: DiscoveredPage[];
  setDiscoveredPages: (pages: DiscoveredPage[]) => void;
  selectedPages: string[];
  setSelectedPages: (pages: string[]) => void;
  
  // Scan
  scanId: string | null;
  setScanId: (id: string | null) => void;
  scanResult: ScanResult | null;
  setScanResult: (result: ScanResult | null) => void;
  
  // Reset
  resetContext: () => void;
}

const ScanContext = createContext<AppContextValue | null>(null);

export const useScanContext = () => {
  const context = useContext(ScanContext);
  if (!context) {
    throw new Error('useScanContext deve essere usato all\'interno di ScanProvider');
  }
  return context;
};

interface ScanProviderProps {
  children: ReactNode;
}

const defaultScannerConfig: ScannerConfig = {
  pa11y: true,
  axe: true,
  lighthouse: true,
  wave: false, // Disabilitato di default perché richiede API key
};

export const ScanProvider: React.FC<ScanProviderProps> = ({ children }) => {
  // Step management
  const [currentStep, setCurrentStep] = useState(0);
  
  // Configuration
  const [config, setConfigState] = useState<ScanRequest | null>(null);
  
  // Discovery
  const [discoveryId, setDiscoveryId] = useState<string | null>(null);
  const [discoveredPages, setDiscoveredPages] = useState<DiscoveredPage[]>([]);
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  
  // Scan
  const [scanId, setScanId] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);

  // Enhanced config setter with defaults
  const setConfig = useCallback((newConfig: ScanRequest) => {
    const configWithDefaults: ScanRequest = {
      ...newConfig,
      scannerConfig: {
        ...defaultScannerConfig,
        ...newConfig.scannerConfig
      },
      simulate: false // Sempre false per scansioni reali
    };
    setConfigState(configWithDefaults);
  }, []);

  // Reset all state
  const resetAll = useCallback(() => {
    setCurrentStep(0);
    setConfigState(null);
    setDiscoveryId(null);
    setDiscoveredPages([]);
    setSelectedPages([]);
    setScanId(null);
    setScanResult(null);
  }, []);

  // Enhanced setSelectedPages with validation
  const setSelectedPagesEnhanced = useCallback((pages: string[]) => {
    // Valida che le pagine selezionate esistano tra quelle scoperte
    const validPages = pages.filter(page => 
      discoveredPages.some(discovered => discovered.url === page)
    );
    setSelectedPages(validPages);
  }, [discoveredPages]);

  // Enhanced setDiscoveredPages with auto-selection
  const setDiscoveredPagesEnhanced = useCallback((pages: DiscoveredPage[]) => {
    setDiscoveredPages(pages);
    
    // Auto-seleziona pagine importanti se non ci sono selezioni
    if (selectedPages.length === 0 && pages.length > 0) {
      const importantPages = pages
        .filter(page => 
          page.type === 'page' || 
          page.type === 'form' || 
          page.depth <= 2
        )
        .slice(0, 10) // Massimo 10 pagine auto-selezionate
        .map(page => page.url);
      
      setSelectedPages(importantPages);
    }
  }, [selectedPages.length]);

  const contextValue: AppContextValue = {
    currentStep,
    setCurrentStep,
    config,
    setConfig,
    discoveryId,
    setDiscoveryId,
    discoveredPages,
    setDiscoveredPages: setDiscoveredPagesEnhanced,
    selectedPages,
    setSelectedPages: setSelectedPagesEnhanced,
    scanId,
    setScanId,
    scanResult,
    setScanResult,
    resetAll,
  };

  return (
    <ScanContext.Provider value={contextValue}>
      {children}
    </ScanContext.Provider>
  );
};

// Hook helper per passi specifici
export const useStepNavigation = () => {
  const { currentStep, setCurrentStep } = useScanContext();
  
  const goToNextStep = useCallback(() => {
    setCurrentStep(Math.min(currentStep + 1, 4)); // Max 4 step (0-4)
  }, [currentStep]);
  
  const goToPreviousStep = useCallback(() => {
    setCurrentStep(Math.max(currentStep - 1, 0)); // Min 0 step
  }, [currentStep]);
  
  const goToStep = useCallback((step: number) => {
    if (step >= 0 && step <= 4) {
      setCurrentStep(step);
    }
  }, [setCurrentStep]);
  
  return {
    currentStep,
    goToNextStep,
    goToPreviousStep,
    goToStep,
    isFirstStep: currentStep === 0,
    isLastStep: currentStep === 4,
  };
};

// Hook helper per la configurazione
export const useConfigValidation = () => {
  const { config } = useScanContext();
  
  const isConfigValid = useCallback(() => {
    if (!config) return false;
    
    // Validazioni base
    if (!config.url || !config.company_name || !config.email) {
      return false;
    }
    
    // Valida URL
    try {
      new URL(config.url);
    } catch {
      return false;
    }
    
    // Valida email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(config.email)) {
      return false;
    }
    
    // Valida che almeno uno scanner sia abilitato
    if (config.scannerConfig) {
      const enabledScanners = Object.values(config.scannerConfig).filter(Boolean);
      if (enabledScanners.length === 0) {
        return false;
      }
    }
    
    return true;
  }, [config]);
  
  return {
    config,
    isConfigValid: isConfigValid(),
  };
};

// Hook helper per le pagine selezionate
export const usePageSelection = () => {
  const { 
    discoveredPages, 
    selectedPages, 
    setSelectedPages 
  } = useScanContext();
  
  const selectPage = useCallback((url: string) => {
    setSelectedPages(
      selectedPages.includes(url) ? selectedPages : [...selectedPages, url]
    );
  }, [selectedPages]);
  
  const deselectPage = useCallback((url: string) => {
    setSelectedPages(selectedPages.filter((page: string) => page !== url));
  }, [selectedPages]);
  
  const togglePage = useCallback((url: string) => {
    setSelectedPages(
      selectedPages.includes(url) 
        ? selectedPages.filter((page: string) => page !== url)
        : [...selectedPages, url]
    );
  }, [selectedPages]);
  
  const selectAll = useCallback(() => {
    const allUrls = discoveredPages.map(page => page.url);
    setSelectedPages(allUrls);
  }, [discoveredPages, setSelectedPages]);
  
  const deselectAll = useCallback(() => {
    setSelectedPages([]);
  }, [setSelectedPages]);
  
  return {
    discoveredPages,
    selectedPages,
    selectPage,
    deselectPage,
    togglePage,
    selectAll,
    deselectAll,
    selectedCount: selectedPages.length,
    totalCount: discoveredPages.length,
    hasSelection: selectedPages.length > 0,
  };
};