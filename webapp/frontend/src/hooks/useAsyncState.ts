import { useState, useCallback } from 'react';

// Definizione locale di LoadingState
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

interface AsyncStateReturn<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  loadingState: LoadingState;
  execute: (asyncFunction: () => Promise<T>) => Promise<T | null>;
  reset: () => void;
  setData: (data: T | null) => void;
  setError: (error: string | null) => void;
}

export function useAsyncState<T = any>(initialData: T | null = null): AsyncStateReturn<T> {
  const [data, setData] = useState<T | null>(initialData);
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (asyncFunction: () => Promise<T>): Promise<T | null> => {
    try {
      setLoadingState('loading');
      setError(null);
      
      const result = await asyncFunction();
      
      setData(result);
      setLoadingState('success');
      return result;
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Errore sconosciuto';
      setError(errorMessage);
      setLoadingState('error');
      console.error('AsyncState error:', err);
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setData(initialData);
    setLoadingState('idle');
    setError(null);
  }, [initialData]);

  return {
    data,
    loading: loadingState === 'loading',
    error,
    loadingState,
    execute,
    reset,
    setData,
    setError,
  };
}

export default useAsyncState;