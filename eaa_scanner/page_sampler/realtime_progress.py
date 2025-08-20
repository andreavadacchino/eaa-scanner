"""
Sistema di feedback real-time con WebSocket
Fornisce aggiornamenti live durante discovery e scansione
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from queue import Queue

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    WebSocketServerProtocol = Any  # Fallback per type hints
    print("WebSocket non disponibile. Installa con: pip install websockets")

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipi di messaggi WebSocket"""
    DISCOVERY_START = "DISCOVERY_START"
    DISCOVERY_PROGRESS = "DISCOVERY_PROGRESS"
    DISCOVERY_COMPLETE = "DISCOVERY_COMPLETE"
    
    TEMPLATE_START = "TEMPLATE_START"
    TEMPLATE_PROGRESS = "TEMPLATE_PROGRESS"
    TEMPLATE_COMPLETE = "TEMPLATE_COMPLETE"
    
    SCAN_START = "SCAN_START"
    SCAN_PROGRESS = "SCAN_PROGRESS"
    SCAN_PAGE_COMPLETE = "SCAN_PAGE_COMPLETE"
    SCAN_COMPLETE = "SCAN_COMPLETE"
    
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    
    ISSUE_FOUND = "ISSUE_FOUND"
    SCREENSHOT_TAKEN = "SCREENSHOT_TAKEN"


@dataclass
class ProgressMessage:
    """Messaggio di progresso"""
    type: MessageType
    timestamp: float
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        """Converti in JSON per WebSocket"""
        return json.dumps({
            'type': self.type.value,
            'timestamp': self.timestamp,
            'data': self.data
        })


class RealtimeProgress:
    """
    Gestore del progresso real-time con WebSocket
    """
    
    def __init__(self, port: int = 8765, host: str = 'localhost'):
        """
        Inizializza il sistema di progresso
        
        Args:
            port: Porta WebSocket
            host: Host WebSocket
        """
        self.port = port
        self.host = host
        self.clients: List[WebSocketServerProtocol] = []
        self.message_queue: Queue = Queue()
        self.server = None
        self.server_thread = None
        
        # Stato corrente
        self.current_phase = "idle"
        self.progress_data = {
            'discovery': {
                'pages_found': 0,
                'pages_visited': 0,
                'current_url': '',
                'progress': 0
            },
            'template': {
                'templates_found': 0,
                'pages_analyzed': 0,
                'progress': 0
            },
            'scan': {
                'pages_scanned': 0,
                'total_pages': 0,
                'current_page': '',
                'current_scanner': '',
                'issues_found': {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'progress': 0
            }
        }
    
    async def start_server(self):
        """Avvia server WebSocket asincrono"""
        if not WEBSOCKET_AVAILABLE:
            logger.warning("WebSocket non disponibile")
            return
        
        try:
            async with websockets.serve(
                self.handle_client,
                self.host,
                self.port
            ) as server:
                self.server = server
                logger.info(f"WebSocket server avviato su ws://{self.host}:{self.port}")
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Errore avvio WebSocket server: {e}")
    
    def start(self):
        """Avvia server in thread separato"""
        if not WEBSOCKET_AVAILABLE:
            return
        
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start_server())
            except:
                pass
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        time.sleep(1)  # Aspetta che server sia pronto
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Gestisce connessione client WebSocket
        
        Args:
            websocket: Connessione WebSocket
            path: Path richiesto
        """
        logger.info(f"Nuovo client connesso: {websocket.remote_address}")
        self.clients.append(websocket)
        
        try:
            # Invia stato iniziale
            await self.send_current_state(websocket)
            
            # Gestisci messaggi in arrivo
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnesso: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)
    
    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """
        Gestisce messaggio dal client
        
        Args:
            websocket: Connessione WebSocket
            message: Messaggio ricevuto
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            # Gestisci richieste client
            if msg_type == 'GET_STATE':
                await self.send_current_state(websocket)
            elif msg_type == 'PAUSE':
                await self.broadcast_message(ProgressMessage(
                    type=MessageType.INFO,
                    timestamp=time.time(),
                    data={'message': 'Scansione in pausa'}
                ))
            elif msg_type == 'RESUME':
                await self.broadcast_message(ProgressMessage(
                    type=MessageType.INFO,
                    timestamp=time.time(),
                    data={'message': 'Scansione ripresa'}
                ))
                
        except json.JSONDecodeError:
            logger.warning(f"Messaggio non valido: {message}")
    
    async def send_current_state(self, websocket: WebSocketServerProtocol):
        """
        Invia stato corrente al client
        
        Args:
            websocket: Connessione WebSocket
        """
        state_message = {
            'type': 'CURRENT_STATE',
            'timestamp': time.time(),
            'data': {
                'phase': self.current_phase,
                'progress': self.progress_data
            }
        }
        await websocket.send(json.dumps(state_message))
    
    async def broadcast_message(self, message: ProgressMessage):
        """
        Invia messaggio a tutti i client connessi
        
        Args:
            message: Messaggio da inviare
        """
        if not self.clients:
            return
        
        message_json = message.to_json()
        
        # Invia a tutti i client
        disconnected = []
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(client)
        
        # Rimuovi client disconnessi
        for client in disconnected:
            self.clients.remove(client)
    
    def send_message(self, message: ProgressMessage):
        """
        Invia messaggio (wrapper sincrono)
        
        Args:
            message: Messaggio da inviare
        """
        if not WEBSOCKET_AVAILABLE:
            return
        
        # Crea task asincrono per broadcast
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.broadcast_message(message))
        except:
            pass
    
    # Metodi di convenienza per fasi specifiche
    
    def start_discovery(self, base_url: str, max_pages: int):
        """Notifica inizio discovery"""
        self.current_phase = "discovery"
        self.progress_data['discovery'] = {
            'pages_found': 0,
            'pages_visited': 0,
            'current_url': base_url,
            'progress': 0,
            'max_pages': max_pages
        }
        
        self.send_message(ProgressMessage(
            type=MessageType.DISCOVERY_START,
            timestamp=time.time(),
            data={
                'base_url': base_url,
                'max_pages': max_pages,
                'message': f'Inizio discovery di {base_url}'
            }
        ))
    
    def update_discovery(self, pages_found: int, pages_visited: int, 
                        current_url: str, message: str = ""):
        """Aggiorna progresso discovery"""
        self.progress_data['discovery'].update({
            'pages_found': pages_found,
            'pages_visited': pages_visited,
            'current_url': current_url,
            'progress': int((pages_visited / self.progress_data['discovery'].get('max_pages', 50)) * 100)
        })
        
        self.send_message(ProgressMessage(
            type=MessageType.DISCOVERY_PROGRESS,
            timestamp=time.time(),
            data={
                'pages_found': pages_found,
                'pages_visited': pages_visited,
                'current_url': current_url,
                'progress': self.progress_data['discovery']['progress'],
                'message': message or f'Analizzando: {current_url}'
            }
        ))
    
    def complete_discovery(self, total_pages: int, templates_found: int):
        """Notifica fine discovery"""
        self.send_message(ProgressMessage(
            type=MessageType.DISCOVERY_COMPLETE,
            timestamp=time.time(),
            data={
                'total_pages': total_pages,
                'templates_found': templates_found,
                'message': f'Discovery completata: {total_pages} pagine in {templates_found} template'
            }
        ))
    
    def start_template_detection(self, pages_count: int):
        """Notifica inizio template detection"""
        self.current_phase = "template_detection"
        self.progress_data['template'] = {
            'templates_found': 0,
            'pages_analyzed': 0,
            'total_pages': pages_count,
            'progress': 0
        }
        
        self.send_message(ProgressMessage(
            type=MessageType.TEMPLATE_START,
            timestamp=time.time(),
            data={
                'pages_count': pages_count,
                'message': f'Analisi template su {pages_count} pagine...'
            }
        ))
    
    def update_template_detection(self, templates_found: int, pages_analyzed: int):
        """Aggiorna progresso template detection"""
        total = self.progress_data['template'].get('total_pages', 1)
        progress = int((pages_analyzed / total) * 100)
        
        self.progress_data['template'].update({
            'templates_found': templates_found,
            'pages_analyzed': pages_analyzed,
            'progress': progress
        })
        
        self.send_message(ProgressMessage(
            type=MessageType.TEMPLATE_PROGRESS,
            timestamp=time.time(),
            data={
                'templates_found': templates_found,
                'pages_analyzed': pages_analyzed,
                'progress': progress,
                'message': f'Identificati {templates_found} template'
            }
        ))
    
    def complete_template_detection(self, templates: Dict):
        """Notifica fine template detection"""
        self.send_message(ProgressMessage(
            type=MessageType.TEMPLATE_COMPLETE,
            timestamp=time.time(),
            data={
                'templates': templates,
                'message': f'Template detection completata'
            }
        ))
    
    def start_scan(self, pages_count: int):
        """Notifica inizio scansione"""
        self.current_phase = "scanning"
        self.progress_data['scan'] = {
            'pages_scanned': 0,
            'total_pages': pages_count,
            'current_page': '',
            'current_scanner': '',
            'issues_found': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'progress': 0
        }
        
        self.send_message(ProgressMessage(
            type=MessageType.SCAN_START,
            timestamp=time.time(),
            data={
                'pages_count': pages_count,
                'message': f'Inizio scansione di {pages_count} pagine'
            }
        ))
    
    def update_scan(self, current_page: str, current_scanner: str, 
                   scanner_progress: int = 0):
        """Aggiorna progresso scansione"""
        self.progress_data['scan'].update({
            'current_page': current_page,
            'current_scanner': current_scanner
        })
        
        self.send_message(ProgressMessage(
            type=MessageType.SCAN_PROGRESS,
            timestamp=time.time(),
            data={
                'current_page': current_page,
                'current_scanner': current_scanner,
                'scanner_progress': scanner_progress,
                'pages_scanned': self.progress_data['scan']['pages_scanned'],
                'total_pages': self.progress_data['scan']['total_pages'],
                'issues': self.progress_data['scan']['issues_found'],
                'message': f'Scansione con {current_scanner}: {current_page}'
            }
        ))
    
    def page_scan_complete(self, page_url: str, issues: Dict[str, int]):
        """Notifica completamento scansione pagina"""
        self.progress_data['scan']['pages_scanned'] += 1
        
        # Aggiorna conteggio issues
        for severity, count in issues.items():
            if severity in self.progress_data['scan']['issues_found']:
                self.progress_data['scan']['issues_found'][severity] += count
        
        progress = int((self.progress_data['scan']['pages_scanned'] / 
                       self.progress_data['scan']['total_pages']) * 100)
        self.progress_data['scan']['progress'] = progress
        
        self.send_message(ProgressMessage(
            type=MessageType.SCAN_PAGE_COMPLETE,
            timestamp=time.time(),
            data={
                'page_url': page_url,
                'issues': issues,
                'pages_scanned': self.progress_data['scan']['pages_scanned'],
                'total_pages': self.progress_data['scan']['total_pages'],
                'progress': progress,
                'total_issues': self.progress_data['scan']['issues_found'],
                'message': f'Completata: {page_url}'
            }
        ))
    
    def complete_scan(self, total_issues: Dict[str, int], report_path: str):
        """Notifica fine scansione"""
        self.current_phase = "complete"
        
        self.send_message(ProgressMessage(
            type=MessageType.SCAN_COMPLETE,
            timestamp=time.time(),
            data={
                'total_issues': total_issues,
                'report_path': report_path,
                'message': 'Scansione completata con successo!'
            }
        ))
    
    def send_error(self, error_message: str, details: Dict = None):
        """Invia messaggio di errore"""
        self.send_message(ProgressMessage(
            type=MessageType.ERROR,
            timestamp=time.time(),
            data={
                'message': error_message,
                'details': details or {}
            }
        ))
    
    def send_warning(self, warning_message: str, details: Dict = None):
        """Invia messaggio di warning"""
        self.send_message(ProgressMessage(
            type=MessageType.WARNING,
            timestamp=time.time(),
            data={
                'message': warning_message,
                'details': details or {}
            }
        ))
    
    def send_info(self, info_message: str, details: Dict = None):
        """Invia messaggio informativo"""
        self.send_message(ProgressMessage(
            type=MessageType.INFO,
            timestamp=time.time(),
            data={
                'message': info_message,
                'details': details or {}
            }
        ))
    
    def issue_found(self, issue_type: str, severity: str, page_url: str):
        """Notifica issue trovata"""
        self.send_message(ProgressMessage(
            type=MessageType.ISSUE_FOUND,
            timestamp=time.time(),
            data={
                'issue_type': issue_type,
                'severity': severity,
                'page_url': page_url,
                'message': f'{severity.upper()}: {issue_type} su {page_url}'
            }
        ))
    
    def screenshot_taken(self, page_url: str, screenshot_path: str):
        """Notifica screenshot catturato"""
        self.send_message(ProgressMessage(
            type=MessageType.SCREENSHOT_TAKEN,
            timestamp=time.time(),
            data={
                'page_url': page_url,
                'screenshot_path': screenshot_path,
                'message': f'Screenshot salvato per {page_url}'
            }
        ))