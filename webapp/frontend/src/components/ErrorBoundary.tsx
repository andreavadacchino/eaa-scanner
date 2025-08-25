import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary per gestire errori React in produzione
 * Cattura errori nei componenti figli e mostra UI di fallback
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Aggiorna lo state per mostrare UI di fallback
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log errore per monitoring
    console.error('🚨 ErrorBoundary ha catturato un errore:', error, errorInfo);
    
    // Salva dettagli errore nello state
    this.setState({
      error,
      errorInfo,
    });

    // Qui potresti inviare l'errore a un servizio di monitoring
    // come Sentry, LogRocket, etc.
    if (window.location.hostname !== 'localhost') {
      // reportErrorToService(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // UI di fallback personalizzata
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // UI di fallback di default
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
            <div className="flex items-center mb-4">
              <svg 
                className="w-8 h-8 text-red-500 mr-3" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
                />
              </svg>
              <h2 className="text-xl font-semibold text-gray-900">
                Si è verificato un errore
              </h2>
            </div>
            
            <p className="text-gray-600 mb-4">
              Qualcosa è andato storto durante il caricamento dell'applicazione.
              Prova a ricaricare la pagina.
            </p>

            {/* Mostra dettagli errore solo in development */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4">
                <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-700">
                  Dettagli errore (solo in development)
                </summary>
                <div className="mt-2 p-3 bg-gray-100 rounded text-xs">
                  <p className="font-mono text-red-600 mb-2">
                    {this.state.error.toString()}
                  </p>
                  {this.state.errorInfo && (
                    <pre className="text-gray-600 overflow-auto">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => window.location.reload()}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Ricarica Pagina
              </button>
              
              <button
                onClick={this.handleReset}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
              >
                Riprova
              </button>
            </div>

            <div className="mt-4 pt-4 border-t">
              <a
                href="/"
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                ← Torna alla configurazione
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;