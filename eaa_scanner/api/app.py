"""
Applicazione Flask/WSGI integrata per workflow 2-fasi
Combina API REST e WebSocket server per soluzione completa
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import threading
import time
import logging
import signal
import sys

# WSGI server
from wsgiref.simple_server import make_server, WSGIServer
from wsgiref.util import setup_testing_defaults

from .endpoints import create_api_application
from .websocket_manager import get_websocket_manager, init_websocket_manager
from .session_manager import init_session_manager

logger = logging.getLogger(__name__)


class AccessibilityAPIServer:
    """
    Server completo per API workflow 2-fasi
    Gestisce sia REST API che WebSocket server
    """
    
    def __init__(self, 
                 api_host: str = "0.0.0.0",
                 api_port: int = 8000,
                 websocket_host: str = "localhost",
                 websocket_port: int = 8001,
                 output_dir: Path = None,
                 storage_dir: Path = None,
                 enable_persistence: bool = True):
        """
        Inizializza server API
        
        Args:
            api_host: Host per API REST
            api_port: Porta per API REST
            websocket_host: Host per WebSocket
            websocket_port: Porta per WebSocket
            output_dir: Directory output scansioni
            storage_dir: Directory storage sessioni
            enable_persistence: Se abilitare persistenza
        """
        self.api_host = api_host
        self.api_port = api_port
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port
        
        # Directory
        self.output_dir = output_dir or Path("output")
        self.storage_dir = storage_dir or Path("output/sessions")
        
        # Crea directory se non esistono
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Inizializza componenti
        self.session_manager = init_session_manager(self.storage_dir, enable_persistence)
        self.websocket_manager = init_websocket_manager(self.session_manager)
        
        # Server
        self.wsgi_server: Optional[WSGIServer] = None
        self.websocket_task: Optional[asyncio.Task] = None
        self.websocket_loop: Optional[asyncio.AbstractEventLoop] = None
        self.websocket_thread: Optional[threading.Thread] = None
        
        # Stato
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        logger.info(f"AccessibilityAPIServer inizializzato")
        logger.info(f"  - API: {api_host}:{api_port}")
        logger.info(f"  - WebSocket: {websocket_host}:{websocket_port}")
        logger.info(f"  - Output: {self.output_dir}")
        logger.info(f"  - Storage: {self.storage_dir}")
    
    def start(self) -> None:
        """
        Avvia entrambi i server (API REST + WebSocket)
        """
        if self.is_running:
            logger.warning("Server già in esecuzione")
            return
        
        logger.info("Avvio AccessibilityAPIServer...")
        
        try:
            # Avvia WebSocket server in thread separato
            self._start_websocket_server()
            
            # Avvia API REST server
            self._start_api_server()
            
            self.is_running = True
            logger.info("AccessibilityAPIServer avviato con successo")
            
        except Exception as e:
            logger.error(f"Errore avvio server: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """
        Ferma entrambi i server
        """
        if not self.is_running:
            return
        
        logger.info("Arresto AccessibilityAPIServer...")
        
        # Segnala shutdown
        self.shutdown_event.set()
        self.is_running = False
        
        try:
            # Ferma API server
            if self.wsgi_server:
                self.wsgi_server.shutdown()
                self.wsgi_server = None
                logger.info("API server fermato")
            
            # Ferma WebSocket server
            self._stop_websocket_server()
            
            # Cleanup sessioni
            if hasattr(self, 'session_manager'):
                cleanup_count = self.session_manager.cleanup_old_sessions()
                if cleanup_count > 0:
                    logger.info(f"Cleanup: {cleanup_count} sessioni rimosse")
        
        except Exception as e:
            logger.error(f"Errore durante shutdown: {e}")
        
        logger.info("AccessibilityAPIServer fermato")
    
    def _start_api_server(self) -> None:
        """
        Avvia server API REST
        """
        # Crea applicazione WSGI
        wsgi_app = create_api_application(self.output_dir)
        
        # Wrapper per gestione CORS e logging
        def application(environ, start_response):
            # Setup testing per development
            setup_testing_defaults(environ)
            
            # Log richiesta
            method = environ.get('REQUEST_METHOD', 'GET')
            path = environ.get('PATH_INFO', '/')
            remote = environ.get('REMOTE_ADDR', 'unknown')
            
            start_time = time.time()
            
            try:
                # Gestisce OPTIONS per CORS
                if method == 'OPTIONS':
                    start_response('200 OK', [
                        ('Access-Control-Allow-Origin', '*'),
                        ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
                        ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
                        ('Content-Type', 'text/plain')
                    ])
                    return [b'OK']
                
                # Delega a applicazione principale
                result = wsgi_app(environ, start_response)
                
                duration = (time.time() - start_time) * 1000
                logger.debug(f"{method} {path} da {remote} - {duration:.1f}ms")
                
                return result
            
            except Exception as e:
                logger.error(f"Errore WSGI {method} {path}: {e}")
                start_response('500 Internal Server Error', [
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*')
                ])
                error_response = '{"success": false, "error": "Errore server interno"}'
                return [error_response.encode('utf-8')]
        
        # Crea e avvia server WSGI
        self.wsgi_server = make_server(self.api_host, self.api_port, application)
        
        logger.info(f"API server avviato su http://{self.api_host}:{self.api_port}")
        
        # Avvia in thread per non bloccare
        server_thread = threading.Thread(
            target=self._run_api_server,
            daemon=True,
            name="api-server"
        )
        server_thread.start()
    
    def _run_api_server(self) -> None:
        """
        Esegue server API in thread separato
        """
        try:
            # Serve requests fino a shutdown
            while not self.shutdown_event.is_set():
                try:
                    self.wsgi_server.handle_request()
                except Exception as e:
                    if not self.shutdown_event.is_set():
                        logger.error(f"Errore handling request API: {e}")
        except Exception as e:
            logger.error(f"Errore in API server thread: {e}")
    
    def _start_websocket_server(self) -> None:
        """
        Avvia WebSocket server in thread separato
        """
        def websocket_thread_func():
            # Crea nuovo event loop per thread
            self.websocket_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.websocket_loop)
            
            try:
                # Avvia server WebSocket
                self.websocket_task = self.websocket_loop.create_task(
                    self._run_websocket_server()
                )
                
                # Esegui loop fino a shutdown
                self.websocket_loop.run_until_complete(self.websocket_task)
                
            except Exception as e:
                if not self.shutdown_event.is_set():
                    logger.error(f"Errore WebSocket server: {e}")
            finally:
                self.websocket_loop.close()
        
        # Avvia thread WebSocket
        self.websocket_thread = threading.Thread(
            target=websocket_thread_func,
            daemon=True,
            name="websocket-server"
        )
        self.websocket_thread.start()
        
        # Attendi un po' per setup
        time.sleep(0.5)
    
    async def _run_websocket_server(self) -> None:
        """
        Esegue WebSocket server asincrono
        """
        try:
            await self.websocket_manager.start_server(
                self.websocket_host, 
                self.websocket_port
            )
            logger.info(f"WebSocket server avviato su ws://{self.websocket_host}:{self.websocket_port}")
            
            # Mantieni server attivo
            while not self.shutdown_event.is_set():
                await asyncio.sleep(1)
                
                # Cleanup connessioni inattive
                cleanup_count = self.websocket_manager.cleanup_inactive_connections()
                if cleanup_count > 0:
                    logger.debug(f"WebSocket cleanup: {cleanup_count} connessioni rimosse")
        
        except Exception as e:
            logger.error(f"Errore esecuzione WebSocket server: {e}")
        finally:
            await self.websocket_manager.stop_server()
    
    def _stop_websocket_server(self) -> None:
        """
        Ferma WebSocket server
        """
        if self.websocket_task and self.websocket_loop:
            try:
                # Cancella task
                self.websocket_task.cancel()
                
                # Aspetta thread
                if self.websocket_thread and self.websocket_thread.is_alive():
                    self.websocket_thread.join(timeout=5)
                
                logger.info("WebSocket server fermato")
            
            except Exception as e:
                logger.error(f"Errore stop WebSocket: {e}")
    
    def serve_forever(self) -> None:
        """
        Avvia server e rimane in attesa (blocca thread principale)
        Gestisce SIGINT/SIGTERM per shutdown graceful
        """
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Ricevuto segnale {signum}, shutdown in corso...")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Avvia server
        self.start()
        
        try:
            logger.info("Server in ascolto. Premi Ctrl+C per fermare.")
            logger.info(f"API disponibile su: http://{self.api_host}:{self.api_port}/api/")
            logger.info(f"WebSocket disponibile su: ws://{self.websocket_host}:{self.websocket_port}")
            
            # Mantieni processo vivo
            while self.is_running:
                time.sleep(1)
                
                # Periodiche operazioni di manutenzione
                if int(time.time()) % 300 == 0:  # Ogni 5 minuti
                    self._periodic_maintenance()
        
        except KeyboardInterrupt:
            logger.info("Shutdown richiesto tramite Ctrl+C")
        finally:
            self.stop()
    
    def _periodic_maintenance(self) -> None:
        """
        Operazioni di manutenzione periodiche
        """
        try:
            # Cleanup sessioni vecchie (24 ore)
            cleanup_count = self.session_manager.cleanup_old_sessions(24)
            if cleanup_count > 0:
                logger.info(f"Manutenzione: {cleanup_count} sessioni vecchie rimosse")
            
            # Cleanup connessioni WebSocket inattive
            ws_cleanup = self.websocket_manager.cleanup_inactive_connections()
            if ws_cleanup > 0:
                logger.debug(f"Manutenzione: {ws_cleanup} connessioni WebSocket rimosse")
            
            # Log statistiche
            stats = self.get_stats()
            logger.info(f"Stats: {stats['sessions']['discovery']['total']} discovery, {stats['sessions']['scan']['total']} scan, {stats['websocket']['active_connections']} WS")
        
        except Exception as e:
            logger.error(f"Errore manutenzione periodica: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche complete del server
        
        Returns:
            Dizionario con statistiche
        """
        return {
            "server": {
                "running": self.is_running,
                "api_endpoint": f"http://{self.api_host}:{self.api_port}",
                "websocket_endpoint": f"ws://{self.websocket_host}:{self.websocket_port}",
                "output_dir": str(self.output_dir),
                "storage_dir": str(self.storage_dir)
            },
            "sessions": self.session_manager.get_stats(),
            "websocket": self.websocket_manager.get_stats()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica salute del server
        
        Returns:
            Stato di salute
        """
        health = {
            "status": "healthy" if self.is_running else "stopped",
            "timestamp": time.time(),
            "components": {
                "api_server": bool(self.wsgi_server),
                "websocket_server": bool(self.websocket_task and not self.websocket_task.cancelled()),
                "session_manager": True,
                "websocket_manager": True
            }
        }
        
        # Verifica componenti critici
        all_healthy = all(health["components"].values()) and self.is_running
        health["status"] = "healthy" if all_healthy else "degraded"
        
        return health


# Entry point per development
def main():
    """
    Entry point principale per development/testing
    """
    import os
    
    # Configurazione da environment
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8000"))
    ws_host = os.getenv("WS_HOST", "localhost")
    ws_port = int(os.getenv("WS_PORT", "8001"))
    
    output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
    storage_dir = Path(os.getenv("STORAGE_DIR", "output/sessions"))
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crea e avvia server
    server = AccessibilityAPIServer(
        api_host=api_host,
        api_port=api_port,
        websocket_host=ws_host,
        websocket_port=ws_port,
        output_dir=output_dir,
        storage_dir=storage_dir
    )
    
    print(f"\n=== EAA Scanner API Server ===")
    print(f"API REST: http://{api_host}:{api_port}/api/")
    print(f"WebSocket: ws://{ws_host}:{ws_port}")
    print(f"Output: {output_dir}")
    print(f"Storage: {storage_dir}")
    print(f"================================\n")
    
    server.serve_forever()


if __name__ == "__main__":
    main()
