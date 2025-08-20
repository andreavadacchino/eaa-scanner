import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'

import { Layout } from '@components/Layout/Layout'
import { ScanWorkflow } from '@components/Workflow/ScanWorkflow'
import { ScanHistory } from '@components/History/ScanHistory'
import { SettingsPage } from '@components/Settings/SettingsPage'
import { HelpPage } from '@components/Help/HelpPage'
import { wsClient } from '@services/websocket'

// Create a client instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false
    }
  }
})

function App() {
  useEffect(() => {
    // Inizializza connessione WebSocket
    const initWebSocket = async () => {
      try {
        await wsClient.connect()
        console.log('WebSocket inizializzato con successo')
      } catch (error) {
        console.warn('WebSocket non disponibile, funzionalità real-time disabilitate:', error)
      }
    }
    
    initWebSocket()
    
    // Cleanup alla chiusura
    return () => {
      wsClient.disconnect()
    }
  }, [])
  
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <Layout>
            <Routes>
              <Route path="/" element={<ScanWorkflow />} />
              <Route path="/scan/:scanId?" element={<ScanWorkflow />} />
              <Route path="/history" element={<ScanHistory />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/help" element={<HelpPage />} />
            </Routes>
          </Layout>
          
          {/* Toast notifications */}
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              className: 'text-sm',
              success: {
                iconTheme: {
                  primary: '#22c55e',
                  secondary: '#ffffff'
                }
              },
              error: {
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#ffffff'
                }
              }
            }}
          />
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App