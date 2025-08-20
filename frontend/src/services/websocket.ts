import { io, Socket } from 'socket.io-client'
import { 
  WebSocketEvent, 
  DiscoveryUpdateEvent, 
  ScanUpdateEvent, 
  ScanCompleteEvent 
} from '@types/index'

type EventHandler<T = any> = (data: T) => void

interface WebSocketEvents {
  'discovery_update': DiscoveryUpdateEvent['data']
  'scan_update': ScanUpdateEvent['data']
  'scan_complete': ScanCompleteEvent['data']
  'error': { message: string; code?: string }
  'connection_status': { connected: boolean; error?: string }
}

class WebSocketClient {
  private socket: Socket | null = null
  private eventHandlers: Map<string, Set<EventHandler>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnected = false
  
  connect(url = 'ws://localhost:8000'): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket?.connected) {
        resolve()
        return
      }
      
      this.socket = io(url, {
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay
      })
      
      this.socket.on('connect', () => {
        console.log('WebSocket connesso')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.emit('connection_status', { connected: true })
        resolve()
      })
      
      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnesso:', reason)
        this.isConnected = false
        this.emit('connection_status', { connected: false })
      })
      
      this.socket.on('connect_error', (error) => {
        console.error('Errore connessione WebSocket:', error)
        this.reconnectAttempts++
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
          this.emit('connection_status', { 
            connected: false, 
            error: 'Impossibile stabilire la connessione'
          })
          reject(new Error('Connessione WebSocket fallita'))
        }
      })
      
      this.socket.on('reconnect', (attemptNumber) => {
        console.log(`WebSocket riconnesso dopo ${attemptNumber} tentativi`)
        this.isConnected = true
        this.emit('connection_status', { connected: true })
      })
      
      this.socket.on('reconnect_failed', () => {
        console.error('Riconnessione WebSocket fallita')
        this.emit('connection_status', { 
          connected: false,
          error: 'Riconnessione fallita'
        })
      })
      
      // Registra listeners per eventi specifici
      this.setupEventListeners()
    })
  }
  
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.isConnected = false
    }
  }
  
  private setupEventListeners(): void {
    if (!this.socket) return
    
    // Discovery events
    this.socket.on('discovery_started', (data) => {
      this.emit('discovery_update', {
        status: { ...data, status: 'discovering' },
        discovered_pages: []
      })
    })
    
    this.socket.on('discovery_progress', (data) => {
      this.emit('discovery_update', data)
    })
    
    this.socket.on('discovery_page_found', (data) => {
      this.emit('discovery_update', {
        new_page: data.page,
        status: data.status
      })
    })
    
    this.socket.on('discovery_completed', (data) => {
      this.emit('discovery_update', {
        status: { ...data.status, status: 'completed' },
        discovered_pages: data.pages
      })
    })
    
    this.socket.on('discovery_error', (data) => {
      this.emit('discovery_update', {
        status: { ...data, status: 'error' }
      })
    })
    
    // Scan events
    this.socket.on('scan_started', (data) => {
      this.emit('scan_update', {
        scan_id: data.scan_id,
        progress: { ...data, status: 'starting' }
      })
    })
    
    this.socket.on('scan_progress', (data) => {
      this.emit('scan_update', data)
    })
    
    this.socket.on('scan_page_completed', (data) => {
      this.emit('scan_update', {
        scan_id: data.scan_id,
        progress: data.progress
      })
    })
    
    this.socket.on('scan_completed', (data) => {
      this.emit('scan_complete', data)
    })
    
    this.socket.on('scan_error', (data) => {
      this.emit('scan_update', {
        scan_id: data.scan_id,
        progress: { ...data.progress, status: 'error', error_message: data.error }
      })
    })
    
    // Generic error handling
    this.socket.on('error', (data) => {
      this.emit('error', data)
    })
  }
  
  on<K extends keyof WebSocketEvents>(
    event: K, 
    handler: EventHandler<WebSocketEvents[K]>
  ): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)
  }
  
  off<K extends keyof WebSocketEvents>(
    event: K, 
    handler: EventHandler<WebSocketEvents[K]>
  ): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.delete(handler)
    }
  }
  
  private emit<K extends keyof WebSocketEvents>(
    event: K, 
    data: WebSocketEvents[K]
  ): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach(handler => handler(data))
    }
  }
  
  // Utility methods
  isSocketConnected(): boolean {
    return this.isConnected && this.socket?.connected === true
  }
  
  getConnectionState(): {
    connected: boolean
    connecting: boolean
    reconnecting: boolean
  } {
    const socket = this.socket
    return {
      connected: socket?.connected ?? false,
      connecting: socket?.connecting ?? false,
      reconnecting: socket?.disconnected && this.reconnectAttempts > 0
    }
  }
  
  // Room management for scan sessions
  joinScanRoom(scanId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('join_scan_room', { scan_id: scanId })
    }
  }
  
  leaveScanRoom(scanId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('leave_scan_room', { scan_id: scanId })
    }
  }
  
  // Discovery room management
  joinDiscoveryRoom(discoveryId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('join_discovery_room', { discovery_id: discoveryId })
    }
  }
  
  leaveDiscoveryRoom(discoveryId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('leave_discovery_room', { discovery_id: discoveryId })
    }
  }
}

// Singleton instance
export const wsClient = new WebSocketClient()

// Hook per utilizzo in React components
export const useWebSocket = () => {
  return {
    connect: wsClient.connect.bind(wsClient),
    disconnect: wsClient.disconnect.bind(wsClient),
    on: wsClient.on.bind(wsClient),
    off: wsClient.off.bind(wsClient),
    isConnected: wsClient.isSocketConnected.bind(wsClient),
    getConnectionState: wsClient.getConnectionState.bind(wsClient),
    joinScanRoom: wsClient.joinScanRoom.bind(wsClient),
    leaveScanRoom: wsClient.leaveScanRoom.bind(wsClient),
    joinDiscoveryRoom: wsClient.joinDiscoveryRoom.bind(wsClient),
    leaveDiscoveryRoom: wsClient.leaveDiscoveryRoom.bind(wsClient)
  }
}