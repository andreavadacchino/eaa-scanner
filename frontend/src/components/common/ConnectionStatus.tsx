import { useState, useEffect } from 'react'
import { WifiIcon, SignalIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { useWebSocket } from '@services/websocket'

export function ConnectionStatus() {
  const webSocket = useWebSocket()
  const [connectionState, setConnectionState] = useState({
    connected: false,
    connecting: false,
    reconnecting: false
  })
  
  useEffect(() => {
    const updateConnectionState = () => {
      setConnectionState(webSocket.getConnectionState())
    }
    
    // Update every second
    const interval = setInterval(updateConnectionState, 1000)
    
    // Initial update
    updateConnectionState()
    
    // Setup WebSocket connection status listener
    const handleConnectionStatus = (data: any) => {
      setConnectionState(prev => ({
        ...prev,
        connected: data.connected,
        connecting: false,
        reconnecting: !data.connected && prev.connected
      }))
    }
    
    webSocket.on('connection_status', handleConnectionStatus)
    
    return () => {
      clearInterval(interval)
      webSocket.off('connection_status', handleConnectionStatus)
    }
  }, [webSocket])
  
  const getStatusInfo = () => {
    if (connectionState.connected) {
      return {
        icon: SignalIcon,
        text: 'Online',
        className: 'text-success-600',
        bgClassName: 'bg-success-50 border-success-200'
      }
    }
    
    if (connectionState.connecting || connectionState.reconnecting) {
      return {
        icon: WifiIcon,
        text: connectionState.reconnecting ? 'Riconnessione...' : 'Connessione...',
        className: 'text-warning-600',
        bgClassName: 'bg-warning-50 border-warning-200'
      }
    }
    
    return {
      icon: ExclamationTriangleIcon,
      text: 'Offline',
      className: 'text-gray-500',
      bgClassName: 'bg-gray-50 border-gray-200'
    }
  }
  
  const statusInfo = getStatusInfo()
  const IconComponent = statusInfo.icon
  
  return (
    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-medium transition-all ${statusInfo.bgClassName} ${statusInfo.className}`}>
      <IconComponent className={`h-3 w-3 ${connectionState.connecting || connectionState.reconnecting ? 'animate-pulse' : ''}`} />
      <span>{statusInfo.text}</span>
      
      {/* Real-time indicator dot */}
      {connectionState.connected && (
        <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
      )}
    </div>
  )
}