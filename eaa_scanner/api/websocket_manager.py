"""
Gestore WebSocket per real-time updates del workflow 2-fasi
Supporta eventi discovery e scanning con broadcasting multi-client
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Callable, Any
import asyncio
import json
import time
import logging
from weakref import WeakSet

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any
    print("Attenzione: websockets non installato. Installa con: pip install websockets")

from .models import WebSocketEvent, SessionStatus
from .session_manager import SessionManager, get_session_manager

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """
    Rappresenta una connessione WebSocket client
    """
    
    def __init__(self, websocket: WebSocketServerProtocol, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = time.time()
        self.subscribed_sessions: Set[str] = set()
        self.is_active = True
    
    async def send_event(self, event: WebSocketEvent) -> bool:
        """
        Invia evento al client
        
        Args:
            event: Evento da inviare
            
        Returns:
            True se inviato con successo
        """
        if not self.is_active or self.websocket.closed:
            return False
        
        try:
            message = json.dumps(event.to_dict(), ensure_ascii=False)
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.warning(f"Errore invio WebSocket a {self.client_id}: {e}")
            self.is_active = False
            return False
    
    def subscribe_to_session(self, session_id: str) -> None:
        """Iscrive client agli eventi di una sessione"""
        self.subscribed_sessions.add(session_id)
    
    def unsubscribe_from_session(self, session_id: str) -> None:
        """Disiscrive client dagli eventi di una sessione"""
        self.subscribed_sessions.discard(session_id)
    
    def is_subscribed_to(self, session_id: str) -> bool:
        """Verifica se client è iscritto alla sessione"""
        return session_id in self.subscribed_sessions


class WebSocketManager:
    """
    Gestisce connessioni WebSocket e broadcasting eventi
    Thread-safe con supporto per subscriptions selettive
    """
    
    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Inizializza WebSocketManager
        
        Args:
            session_manager: Manager sessioni per integrazione
        """
        self.session_manager = session_manager or get_session_manager()
        
        # Connessioni attive
        self._connections: Dict[str, WebSocketConnection] = {}
        
        # Server WebSocket
        self._server: Optional[Any] = None
        self._server_task: Optional[asyncio.Task] = None
        
        # Event loop
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Statistiche
        self._total_connections = 0
        self._events_sent = 0
        
        # Registra callback nel session manager
        self.session_manager.register_websocket_callback(self._handle_session_event)
        
        logger.info("WebSocketManager inizializzato")
    
    async def start_server(self, host: str = "localhost", port: int = 8001) -> None:
        """
        Avvia server WebSocket
        
        Args:
            host: Host su cui ascoltare
            port: Porta su cui ascoltare
        """
        if not WEBSOCKETS_AVAILABLE:
            logger.error("WebSockets non disponibile, server non avviato")
            return
        
        if self._server:
            logger.warning("Server WebSocket già avviato")
            return
        
        try:
            self._server = await websockets.serve(
                self._handle_websocket_connection,
                host,
                port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            self._loop = asyncio.get_running_loop()
            
            logger.info(f"Server WebSocket avviato su ws://{host}:{port}")
            
        except Exception as e:
            logger.error(f"Errore avvio server WebSocket: {e}")
            raise
    
    async def stop_server(self) -> None:
        """Ferma server WebSocket"""
        if not self._server:
            return
        
        try:
            # Chiudi tutte le connessioni
            await self._disconnect_all_clients()
            
            # Ferma server
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            
            logger.info("Server WebSocket fermato")
            
        except Exception as e:
            logger.error(f"Errore ferma server WebSocket: {e}")
    
    async def _handle_websocket_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Gestisce connessione WebSocket client
        
        Args:
            websocket: Connessione WebSocket
            path: Path della connessione
        """
        client_id = f"client_{self._total_connections}_{int(time.time())}"
        self._total_connections += 1
        
        connection = WebSocketConnection(websocket, client_id)
        self._connections[client_id] = connection
        
        logger.info(f"Client WebSocket connesso: {client_id} da {websocket.remote_address}")
        
        try:
            # Invia messaggio di benvenuto
            welcome_event = WebSocketEvent(
                event_type="connection_established",
                session_id="system",
                data={
                    "client_id": client_id,
                    "server_time": time.time(),
                    "available_commands": [
                        "subscribe_discovery", "subscribe_scan", "unsubscribe", "ping"
                    ]
                }
            )
            await connection.send_event(welcome_event)
            
            # Loop gestione messaggi
            async for message in websocket:
                await self._handle_client_message(client_id, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnesso")
        except Exception as e:
            logger.error(f"Errore gestione client {client_id}: {e}")
        finally:
            # Cleanup connessione
            if client_id in self._connections:
                del self._connections[client_id]
            logger.debug(f"Connessione {client_id} rimossa")
    
    async def _handle_client_message(self, client_id: str, message: str) -> None:
        """
        Gestisce messaggio da client WebSocket
        
        Args:
            client_id: ID del client
            message: Messaggio ricevuto
        """
        connection = self._connections.get(client_id)
        if not connection:
            return
        
        try:
            data = json.loads(message)
            command = data.get("command")
            payload = data.get("payload", {})
            
            # Gestisci comandi
            if command == "subscribe_discovery":
                session_id = payload.get("session_id")
                if session_id:
                    connection.subscribe_to_session(session_id)
                    await self._send_response(connection, "subscribed", {
                        "session_id": session_id,
                        "type": "discovery"
                    })
            
            elif command == "subscribe_scan":
                session_id = payload.get("session_id")
                if session_id:
                    connection.subscribe_to_session(session_id)
                    await self._send_response(connection, "subscribed", {
                        "session_id": session_id,
                        "type": "scan"
                    })
            
            elif command == "unsubscribe":
                session_id = payload.get("session_id")
                if session_id:
                    connection.unsubscribe_from_session(session_id)
                    await self._send_response(connection, "unsubscribed", {
                        "session_id": session_id
                    })
            
            elif command == "ping":
                await self._send_response(connection, "pong", {
                    "server_time": time.time()
                })
            
            elif command == "get_status":
                session_id = payload.get("session_id")
                if session_id:
                    # Invia status corrente della sessione
                    await self._send_session_status(connection, session_id)
            
            else:
                await self._send_response(connection, "error", {
                    "message": f"Comando non riconosciuto: {command}"
                })
        
        except json.JSONDecodeError:
            await self._send_response(connection, "error", {
                "message": "Messaggio JSON non valido"
            })
        except Exception as e:
            logger.error(f"Errore elaborazione messaggio da {client_id}: {e}")
            await self._send_response(connection, "error", {
                "message": f"Errore server: {str(e)}"
            })
    
    async def _send_response(self, connection: WebSocketConnection, 
                           response_type: str, data: Dict[str, Any]) -> None:
        """
        Invia risposta a client
        
        Args:
            connection: Connessione client
            response_type: Tipo risposta
            data: Dati da inviare
        """
        event = WebSocketEvent(
            event_type=response_type,
            session_id="system",
            data=data
        )
        await connection.send_event(event)
    
    async def _send_session_status(self, connection: WebSocketConnection, session_id: str) -> None:
        """
        Invia status corrente di una sessione
        
        Args:
            connection: Connessione client
            session_id: ID della sessione
        """
        # Prova prima come discovery session
        discovery_session = self.session_manager.get_discovery_session(session_id)
        if discovery_session:
            event = WebSocketEvent(
                event_type="discovery_status",
                session_id=session_id,
                data={
                    "status": discovery_session.status.value,
                    "progress_percent": discovery_session.progress_percent,
                    "pages_discovered": discovery_session.pages_discovered,
                    "current_page": discovery_session.current_page
                }
            )
            await connection.send_event(event)
            return
        
        # Prova come scan session
        scan_session = self.session_manager.get_scan_session(session_id)
        if scan_session:
            event = WebSocketEvent(
                event_type="scan_status",
                session_id=session_id,
                data={
                    "status": scan_session.status.value,
                    "progress_percent": scan_session.progress_percent,
                    "pages_scanned": scan_session.pages_scanned,
                    "total_pages": scan_session.total_pages,
                    "total_issues": scan_session.total_issues
                }
            )
            await connection.send_event(event)
            return
        
        # Sessione non trovata
        await self._send_response(connection, "error", {
            "message": f"Sessione non trovata: {session_id}"
        })
    
    def _handle_session_event(self, event: WebSocketEvent) -> None:
        """
        Gestisce eventi dal SessionManager (callback)
        
        Args:
            event: Evento da processare
        """
        if not self._loop or not self._connections:
            return
        
        # Schedule su event loop asincrono
        asyncio.run_coroutine_threadsafe(
            self._broadcast_event(event),
            self._loop
        )
    
    async def _broadcast_event(self, event: WebSocketEvent) -> None:
        """
        Invia evento a tutti i client interessati
        
        Args:
            event: Evento da broadcastare
        """
        session_id = event.session_id
        
        # Trova client iscritti alla sessione
        interested_clients = [
            conn for conn in self._connections.values()
            if conn.is_subscribed_to(session_id) and conn.is_active
        ]
        
        if not interested_clients:
            return
        
        # Invia evento a tutti i client interessati
        successful_sends = 0
        for connection in interested_clients:
            success = await connection.send_event(event)
            if success:
                successful_sends += 1
        
        self._events_sent += successful_sends
        
        if successful_sends > 0:
            logger.debug(
                f"Evento {event.event_type} per sessione {session_id} "
                f"inviato a {successful_sends} client"
            )
    
    async def broadcast_to_all(self, event: WebSocketEvent) -> int:
        """
        Invia evento a tutti i client connessi
        
        Args:
            event: Evento da inviare
            
        Returns:
            Numero di client che hanno ricevuto l'evento
        """
        active_connections = [
            conn for conn in self._connections.values() if conn.is_active
        ]
        
        successful_sends = 0
        for connection in active_connections:
            success = await connection.send_event(event)
            if success:
                successful_sends += 1
        
        self._events_sent += successful_sends
        
        if successful_sends > 0:
            logger.info(f"Evento broadcast {event.event_type} inviato a {successful_sends} client")
        
        return successful_sends
    
    async def send_to_client(self, client_id: str, event: WebSocketEvent) -> bool:
        """
        Invia evento a client specifico
        
        Args:
            client_id: ID del client
            event: Evento da inviare
            
        Returns:
            True se inviato con successo
        """
        connection = self._connections.get(client_id)
        if not connection or not connection.is_active:
            return False
        
        return await connection.send_event(event)
    
    async def _disconnect_all_clients(self) -> None:
        """Disconnette tutti i client"""
        disconnect_tasks = []
        
        for connection in self._connections.values():
            if connection.is_active and not connection.websocket.closed:
                # Invia messaggio di chiusura
                goodbye_event = WebSocketEvent(
                    event_type="server_shutdown",
                    session_id="system",
                    data={"message": "Server in chiusura"}
                )
                disconnect_tasks.append(connection.send_event(goodbye_event))
        
        # Aspetta invio messaggi di chiusura
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        # Chiudi connessioni
        for connection in list(self._connections.values()):
            try:
                await connection.websocket.close()
            except:
                pass
        
        self._connections.clear()
    
    def get_connection_count(self) -> int:
        """Ottiene numero connessioni attive"""
        return len([c for c in self._connections.values() if c.is_active])
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche WebSocket
        
        Returns:
            Dizionario con statistiche
        """
        active_connections = [c for c in self._connections.values() if c.is_active]
        
        # Conta subscriptions per tipo
        discovery_subs = set()
        scan_subs = set()
        
        for conn in active_connections:
            for session_id in conn.subscribed_sessions:
                if self.session_manager.get_discovery_session(session_id):
                    discovery_subs.add(session_id)
                elif self.session_manager.get_scan_session(session_id):
                    scan_subs.add(session_id)
        
        return {
            "server_running": self._server is not None,
            "active_connections": len(active_connections),
            "total_connections": self._total_connections,
            "events_sent": self._events_sent,
            "discovery_subscriptions": len(discovery_subs),
            "scan_subscriptions": len(scan_subs),
            "websockets_available": WEBSOCKETS_AVAILABLE
        }
    
    def cleanup_inactive_connections(self) -> int:
        """
        Rimuove connessioni inattive
        
        Returns:
            Numero di connessioni rimosse
        """
        to_remove = [
            client_id for client_id, conn in self._connections.items()
            if not conn.is_active or conn.websocket.closed
        ]
        
        for client_id in to_remove:
            del self._connections[client_id]
        
        return len(to_remove)


# Singleton instance per uso globale
_websocket_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    """
    Ottiene istanza singleton di WebSocketManager
    
    Returns:
        WebSocketManager globale
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager

def init_websocket_manager(session_manager: Optional[SessionManager] = None) -> WebSocketManager:
    """
    Inizializza WebSocketManager con configurazione specifica
    
    Args:
        session_manager: SessionManager personalizzato
        
    Returns:
        WebSocketManager configurato
    """
    global _websocket_manager
    _websocket_manager = WebSocketManager(session_manager)
    return _websocket_manager
