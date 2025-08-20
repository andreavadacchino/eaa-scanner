"""
Endpoint API Flask/WSGI per workflow 2-fasi
Implementa REST API completa con gestione errori e validazione
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import json
import time
import logging
import mimetypes
from urllib.parse import parse_qs

from .models import (
    DiscoveryStartRequest, ScanStartRequest, DiscoveryConfiguration, 
    ScanConfiguration, SessionStatus
)
from .session_manager import get_session_manager
from .discovery_service import DiscoveryService
from .scan_service import ScanService
from .websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)


class APIEndpoints:
    """
    Gestore endpoint REST API per workflow 2-fasi
    Compatibile con WSGI per integrazione semplice
    """
    
    def __init__(self, output_dir: Path = None):
        """
        Inizializza APIEndpoints
        
        Args:
            output_dir: Directory base per output
        """
        self.output_dir = output_dir or Path("output")
        
        # Inizializza servizi
        self.session_manager = get_session_manager()
        self.discovery_service = DiscoveryService(self.session_manager, self.output_dir)
        self.scan_service = ScanService(self.session_manager, self.output_dir)
        self.websocket_manager = get_websocket_manager()
        
        logger.info("APIEndpoints inizializzato")
    
    def handle_request(self, environ: Dict[str, Any], start_response: callable) -> List[bytes]:
        """
        Handler principale per richieste WSGI
        
        Args:
            environ: Environment WSGI
            start_response: Callback WSGI response
            
        Returns:
            Risposta come lista di bytes
        """
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        
        try:
            # Routing delle richieste
            if path.startswith("/api/"):
                return self._handle_api_request(environ, start_response, path, method)
            else:
                return self._handle_404(start_response)
        
        except Exception as e:
            logger.error(f"Errore gestione richiesta {method} {path}: {e}", exc_info=True)
            return self._handle_500(start_response, str(e))
    
    def _handle_api_request(self, environ: Dict[str, Any], start_response: callable,
                          path: str, method: str) -> List[bytes]:
        """
        Gestisce richieste API
        
        Args:
            environ: Environment WSGI
            start_response: Callback response
            path: Path della richiesta
            method: Metodo HTTP
            
        Returns:
            Risposta API
        """
        # Health check
        if path == "/api/health" and method == "GET":
            return self._handle_health_check(start_response)
        
        # Statistics
        elif path == "/api/stats" and method == "GET":
            return self._handle_stats(start_response)
        
        # ========== DISCOVERY ENDPOINTS ==========
        
        # POST /api/discovery/start - Avvia discovery
        elif path == "/api/discovery/start" and method == "POST":
            return self._handle_discovery_start(environ, start_response)
        
        # GET /api/discovery/status/{discovery_id} - Status discovery
        elif path.startswith("/api/discovery/status/") and method == "GET":
            discovery_id = path.split("/")[-1]
            return self._handle_discovery_status(start_response, discovery_id)
        
        # GET /api/discovery/results/{discovery_id} - Risultati discovery
        elif path.startswith("/api/discovery/results/") and method == "GET":
            discovery_id = path.split("/")[-1]
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            include_unselected = query_params.get('include_unselected', ['true'])[0].lower() == 'true'
            return self._handle_discovery_results(start_response, discovery_id, include_unselected)
        
        # POST /api/discovery/{discovery_id}/select - Aggiorna selezione pagine
        elif path.startswith("/api/discovery/") and path.endswith("/select") and method == "POST":
            discovery_id = path.split("/")[3]
            return self._handle_discovery_select(environ, start_response, discovery_id)
        
        # DELETE /api/discovery/{discovery_id} - Cancella discovery
        elif path.startswith("/api/discovery/") and method == "DELETE":
            discovery_id = path.split("/")[3]
            return self._handle_discovery_cancel(start_response, discovery_id)
        
        # GET /api/discovery - Lista discovery sessions
        elif path == "/api/discovery" and method == "GET":
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            status_filter = query_params.get('status', [None])[0]
            return self._handle_discovery_list(start_response, status_filter)
        
        # ========== SCAN ENDPOINTS ==========
        
        # POST /api/scan/start - Avvia scan
        elif path == "/api/scan/start" and method == "POST":
            return self._handle_scan_start(environ, start_response)
        
        # GET /api/scan/status/{scan_id} - Status scan
        elif path.startswith("/api/scan/status/") and method == "GET":
            scan_id = path.split("/")[-1]
            return self._handle_scan_status(start_response, scan_id)
        
        # GET /api/scan/results/{scan_id} - Risultati scan
        elif path.startswith("/api/scan/results/") and method == "GET":
            scan_id = path.split("/")[-1]
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            include_issues = query_params.get('include_issues', ['true'])[0].lower() == 'true'
            return self._handle_scan_results(start_response, scan_id, include_issues)
        
        # DELETE /api/scan/{scan_id} - Cancella scan
        elif path.startswith("/api/scan/") and method == "DELETE":
            scan_id = path.split("/")[3]
            return self._handle_scan_cancel(start_response, scan_id)
        
        # GET /api/scan - Lista scan sessions
        elif path == "/api/scan" and method == "GET":
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            status_filter = query_params.get('status', [None])[0]
            return self._handle_scan_list(start_response, status_filter)
        
        # POST /api/scan/{scan_id}/generate-pdf - Genera PDF
        elif path.endswith("/generate-pdf") and method == "POST":
            scan_id = path.split("/")[3]
            return self._handle_generate_pdf(start_response, scan_id)
        
        # ========== FILE DOWNLOADS ==========
        
        # GET /api/download/html/{scan_id} - Scarica HTML
        elif path.startswith("/api/download/html/") and method == "GET":
            scan_id = path.split("/")[-1]
            return self._handle_download_html(start_response, scan_id)
        
        # GET /api/download/pdf/{scan_id} - Scarica PDF
        elif path.startswith("/api/download/pdf/") and method == "GET":
            scan_id = path.split("/")[-1]
            return self._handle_download_pdf(start_response, scan_id)
        
        # ========== WEBSOCKET INFO ==========
        
        # GET /api/websocket/info - Info WebSocket
        elif path == "/api/websocket/info" and method == "GET":
            return self._handle_websocket_info(start_response)
        
        # Endpoint non trovato
        else:
            return self._handle_404(start_response)
    
    # ========== DISCOVERY HANDLERS ==========
    
    def _handle_discovery_start(self, environ: Dict[str, Any], start_response: callable) -> List[bytes]:
        """
        POST /api/discovery/start
        Avvia nuova sessione discovery
        """
        try:
            # Parse richiesta
            request_data = self._parse_request_body(environ)
            
            base_url = request_data.get('base_url', '').strip()
            if not base_url:
                return self._handle_400(start_response, "base_url richiesto")
            
            # Valida URL
            if not self._is_valid_url(base_url):
                return self._handle_400(start_response, "base_url non valido")
            
            # Configurazione opzionale
            config = None
            if 'config' in request_data:
                try:
                    config = DiscoveryConfiguration.from_dict(request_data['config'])
                except Exception as e:
                    return self._handle_400(start_response, f"Configurazione non valida: {e}")
            
            # Avvia discovery
            session_id = self.discovery_service.start_discovery(base_url, config)
            
            response_data = {
                "success": True,
                "discovery_id": session_id,
                "message": "Discovery avviata",
                "base_url": base_url
            }
            
            return self._json_response(start_response, response_data, 201)
        
        except Exception as e:
            logger.error(f"Errore discovery start: {e}")
            return self._handle_500(start_response, "Errore avvio discovery")
    
    def _handle_discovery_status(self, start_response: callable, discovery_id: str) -> List[bytes]:
        """
        GET /api/discovery/status/{discovery_id}
        Ottiene status discovery
        """
        status = self.discovery_service.get_discovery_status(discovery_id)
        if not status:
            return self._handle_404(start_response, "Discovery session non trovata")
        
        return self._json_response(start_response, status)
    
    def _handle_discovery_results(self, start_response: callable, discovery_id: str, 
                                include_unselected: bool) -> List[bytes]:
        """
        GET /api/discovery/results/{discovery_id}
        Ottiene risultati discovery
        """
        results = self.discovery_service.get_discovery_results(discovery_id, include_unselected)
        if not results:
            return self._handle_404(start_response, "Discovery session non trovata o non completata")
        
        return self._json_response(start_response, results)
    
    def _handle_discovery_select(self, environ: Dict[str, Any], start_response: callable,
                               discovery_id: str) -> List[bytes]:
        """
        POST /api/discovery/{discovery_id}/select
        Aggiorna selezione pagine
        """
        try:
            request_data = self._parse_request_body(environ)
            selected_urls = request_data.get('selected_urls', [])
            
            if not isinstance(selected_urls, list):
                return self._handle_400(start_response, "selected_urls deve essere una lista")
            
            success = self.discovery_service.update_page_selection(discovery_id, selected_urls)
            if not success:
                return self._handle_404(start_response, "Discovery session non trovata")
            
            response_data = {
                "success": True,
                "message": f"Selezione aggiornata: {len(selected_urls)} pagine",
                "selected_count": len(selected_urls)
            }
            
            return self._json_response(start_response, response_data)
        
        except Exception as e:
            logger.error(f"Errore discovery select: {e}")
            return self._handle_500(start_response, "Errore aggiornamento selezione")
    
    def _handle_discovery_cancel(self, start_response: callable, discovery_id: str) -> List[bytes]:
        """
        DELETE /api/discovery/{discovery_id}
        Cancella discovery
        """
        success = self.discovery_service.cancel_discovery(discovery_id)
        if not success:
            return self._handle_404(start_response, "Discovery session non trovata")
        
        response_data = {
            "success": True,
            "message": "Discovery cancellata"
        }
        
        return self._json_response(start_response, response_data)
    
    def _handle_discovery_list(self, start_response: callable, status_filter: Optional[str]) -> List[bytes]:
        """
        GET /api/discovery
        Lista discovery sessions
        """
        try:
            status_enum = None
            if status_filter:
                try:
                    status_enum = SessionStatus(status_filter)
                except ValueError:
                    return self._handle_400(start_response, f"Status non valido: {status_filter}")
            
            sessions = self.session_manager.get_discovery_sessions_list(status_enum)
            
            response_data = {
                "success": True,
                "sessions": sessions,
                "total": len(sessions),
                "filter": status_filter
            }
            
            return self._json_response(start_response, response_data)
        
        except Exception as e:
            logger.error(f"Errore discovery list: {e}")
            return self._handle_500(start_response, "Errore recupero lista discovery")
    
    # ========== SCAN HANDLERS ==========
    
    def _handle_scan_start(self, environ: Dict[str, Any], start_response: callable) -> List[bytes]:
        """
        POST /api/scan/start
        Avvia nuova sessione scan
        """
        try:
            request_data = self._parse_request_body(environ)
            
            # Parametri richiesti
            discovery_session_id = request_data.get('discovery_session_id', '').strip()
            selected_urls = request_data.get('selected_page_urls', [])
            company_name = request_data.get('company_name', '').strip()
            email = request_data.get('email', '').strip()
            
            # Validazioni
            if not discovery_session_id:
                return self._handle_400(start_response, "discovery_session_id richiesto")
            
            if not selected_urls or not isinstance(selected_urls, list):
                return self._handle_400(start_response, "selected_page_urls deve essere una lista non vuota")
            
            if not company_name:
                return self._handle_400(start_response, "company_name richiesto")
            
            if not email or '@' not in email:
                return self._handle_400(start_response, "email valida richiesta")
            
            # Configurazione opzionale
            config = None
            if 'config' in request_data:
                try:
                    config = ScanConfiguration.from_dict(request_data['config'])
                except Exception as e:
                    return self._handle_400(start_response, f"Configurazione non valida: {e}")
            
            # Avvia scan
            scan_id = self.scan_service.start_scan(
                discovery_session_id=discovery_session_id,
                selected_urls=selected_urls,
                company_name=company_name,
                email=email,
                config=config
            )
            
            if not scan_id:
                return self._handle_400(start_response, "Impossibile avviare scan: discovery session non valida o pagine non disponibili")
            
            response_data = {
                "success": True,
                "scan_id": scan_id,
                "message": "Scan avviata",
                "discovery_session_id": discovery_session_id,
                "pages_selected": len(selected_urls)
            }
            
            return self._json_response(start_response, response_data, 201)
        
        except Exception as e:
            logger.error(f"Errore scan start: {e}")
            return self._handle_500(start_response, "Errore avvio scan")
    
    def _handle_scan_status(self, start_response: callable, scan_id: str) -> List[bytes]:
        """
        GET /api/scan/status/{scan_id}
        Ottiene status scan
        """
        status = self.scan_service.get_scan_status(scan_id)
        if not status:
            return self._handle_404(start_response, "Scan session non trovata")
        
        return self._json_response(start_response, status)
    
    def _handle_scan_results(self, start_response: callable, scan_id: str, 
                           include_issues: bool) -> List[bytes]:
        """
        GET /api/scan/results/{scan_id}
        Ottiene risultati scan
        """
        results = self.scan_service.get_scan_results(scan_id, include_issues)
        if not results:
            return self._handle_404(start_response, "Scan session non trovata o non completata")
        
        return self._json_response(start_response, results)
    
    def _handle_scan_cancel(self, start_response: callable, scan_id: str) -> List[bytes]:
        """
        DELETE /api/scan/{scan_id}
        Cancella scan
        """
        success = self.scan_service.cancel_scan(scan_id)
        if not success:
            return self._handle_404(start_response, "Scan session non trovata")
        
        response_data = {
            "success": True,
            "message": "Scan cancellata"
        }
        
        return self._json_response(start_response, response_data)
    
    def _handle_scan_list(self, start_response: callable, status_filter: Optional[str]) -> List[bytes]:
        """
        GET /api/scan
        Lista scan sessions
        """
        try:
            status_enum = None
            if status_filter:
                try:
                    status_enum = SessionStatus(status_filter)
                except ValueError:
                    return self._handle_400(start_response, f"Status non valido: {status_filter}")
            
            sessions = self.session_manager.get_scan_sessions_list(status_enum)
            
            response_data = {
                "success": True,
                "sessions": sessions,
                "total": len(sessions),
                "filter": status_filter
            }
            
            return self._json_response(start_response, response_data)
        
        except Exception as e:
            logger.error(f"Errore scan list: {e}")
            return self._handle_500(start_response, "Errore recupero lista scan")
    
    def _handle_generate_pdf(self, start_response: callable, scan_id: str) -> List[bytes]:
        """
        POST /api/scan/{scan_id}/generate-pdf
        Genera PDF da report HTML
        """
        try:
            pdf_path = self.scan_service.generate_pdf_report(scan_id)
            
            if pdf_path:
                response_data = {
                    "success": True,
                    "message": "PDF generato",
                    "pdf_path": pdf_path
                }
                return self._json_response(start_response, response_data)
            else:
                return self._handle_400(start_response, "Impossibile generare PDF: report HTML non disponibile o errore generazione")
        
        except Exception as e:
            logger.error(f"Errore generate PDF: {e}")
            return self._handle_500(start_response, "Errore generazione PDF")
    
    # ========== FILE DOWNLOAD HANDLERS ==========
    
    def _handle_download_html(self, start_response: callable, scan_id: str) -> List[bytes]:
        """
        GET /api/download/html/{scan_id}
        Scarica report HTML
        """
        session = self.session_manager.get_scan_session(scan_id)
        if not session or not session.report_html_path:
            return self._handle_404(start_response, "Report HTML non disponibile")
        
        html_path = Path(session.report_html_path)
        if not html_path.exists():
            return self._handle_404(start_response, "File report HTML non trovato")
        
        return self._file_response(start_response, html_path, "text/html")
    
    def _handle_download_pdf(self, start_response: callable, scan_id: str) -> List[bytes]:
        """
        GET /api/download/pdf/{scan_id}
        Scarica report PDF
        """
        session = self.session_manager.get_scan_session(scan_id)
        if not session or not session.report_pdf_path:
            return self._handle_404(start_response, "Report PDF non disponibile")
        
        pdf_path = Path(session.report_pdf_path)
        if not pdf_path.exists():
            return self._handle_404(start_response, "File report PDF non trovato")
        
        return self._file_response(start_response, pdf_path, "application/pdf")
    
    # ========== OTHER HANDLERS ==========
    
    def _handle_health_check(self, start_response: callable) -> List[bytes]:
        """
        GET /api/health
        Health check
        """
        # Cleanup thread completati
        self.discovery_service.cleanup_completed_threads()
        self.scan_service.cleanup_completed_threads()
        
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "session_manager": True,
                "discovery_service": True,
                "scan_service": True,
                "websocket_manager": True
            },
            "stats": {
                "running_discoveries": len(self.discovery_service.get_running_discoveries()),
                "running_scans": len(self.scan_service.get_running_scans()),
                "websocket_connections": self.websocket_manager.get_connection_count()
            }
        }
        
        return self._json_response(start_response, health_data)
    
    def _handle_stats(self, start_response: callable) -> List[bytes]:
        """
        GET /api/stats
        Statistiche sistema
        """
        stats = {
            "timestamp": time.time(),
            "session_manager": self.session_manager.get_stats(),
            "websocket_manager": self.websocket_manager.get_stats(),
            "services": {
                "discovery": {
                    "running": len(self.discovery_service.get_running_discoveries())
                },
                "scan": {
                    "running": len(self.scan_service.get_running_scans())
                }
            }
        }
        
        return self._json_response(start_response, stats)
    
    def _handle_websocket_info(self, start_response: callable) -> List[bytes]:
        """
        GET /api/websocket/info
        Informazioni WebSocket
        """
        try:
            from .websocket_manager import WEBSOCKETS_AVAILABLE
        except:
            WEBSOCKETS_AVAILABLE = False
        
        info = {
            "websockets_available": WEBSOCKETS_AVAILABLE,
            "websocket_url": "ws://localhost:8001",  # TODO: configurabile
            "supported_events": [
                "discovery_progress", "discovery_complete", "discovery_status_change",
                "scan_progress", "scan_complete", "scan_status_change"
            ],
            "client_commands": [
                "subscribe_discovery", "subscribe_scan", "unsubscribe", "ping", "get_status"
            ],
            "stats": self.websocket_manager.get_stats()
        }
        
        return self._json_response(start_response, info)
    
    # ========== UTILITY METHODS ==========
    
    def _parse_request_body(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON request body
        
        Args:
            environ: WSGI environment
            
        Returns:
            Dizionario con dati richiesta
        """
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError, TypeError):
            content_length = 0
        
        if content_length == 0:
            return {}
        
        body = environ['wsgi.input'].read(content_length)
        
        content_type = environ.get('CONTENT_TYPE', '')
        if 'application/json' in content_type:
            return json.loads(body.decode('utf-8'))
        else:
            # Fallback per form data
            from urllib.parse import parse_qs
            return {k: v[0] for k, v in parse_qs(body.decode('utf-8')).items()}
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Valida URL base
        
        Args:
            url: URL da validare
            
        Returns:
            True se valido
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
    
    def _json_response(self, start_response: callable, data: Dict[str, Any], 
                      status_code: int = 200) -> List[bytes]:
        """
        Crea risposta JSON
        
        Args:
            start_response: Callback WSGI
            data: Dati da serializzare
            status_code: Codice HTTP
            
        Returns:
            Risposta JSON come bytes
        """
        status_text = {
            200: "200 OK",
            201: "201 Created",
            400: "400 Bad Request",
            404: "404 Not Found",
            500: "500 Internal Server Error"
        }.get(status_code, f"{status_code} Unknown")
        
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization")
        ]
        
        start_response(status_text, headers)
        
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        return [json_data.encode('utf-8')]
    
    def _file_response(self, start_response: callable, file_path: Path, 
                      content_type: str) -> List[bytes]:
        """
        Crea risposta per download file
        
        Args:
            start_response: Callback WSGI
            file_path: Path del file
            content_type: Content type
            
        Returns:
            Contenuto file come bytes
        """
        headers = [
            ("Content-Type", content_type),
            ("Content-Disposition", f"attachment; filename={file_path.name}"),
            ("Content-Length", str(file_path.stat().st_size))
        ]
        
        start_response("200 OK", headers)
        
        return [file_path.read_bytes()]
    
    def _handle_400(self, start_response: callable, message: str) -> List[bytes]:
        """Gestisce errore 400"""
        return self._json_response(start_response, {
            "success": False,
            "error": message,
            "code": 400
        }, 400)
    
    def _handle_404(self, start_response: callable, message: str = "Risorsa non trovata") -> List[bytes]:
        """Gestisce errore 404"""
        return self._json_response(start_response, {
            "success": False,
            "error": message,
            "code": 404
        }, 404)
    
    def _handle_500(self, start_response: callable, message: str) -> List[bytes]:
        """Gestisce errore 500"""
        return self._json_response(start_response, {
            "success": False,
            "error": message,
            "code": 500
        }, 500)


# Factory function per integrazione WSGI
def create_api_application(output_dir: Path = None) -> callable:
    """
    Crea applicazione WSGI per API
    
    Args:
        output_dir: Directory output personalizzata
        
    Returns:
        Applicazione WSGI
    """
    api_endpoints = APIEndpoints(output_dir)
    
    def application(environ: Dict[str, Any], start_response: callable) -> List[bytes]:
        return api_endpoints.handle_request(environ, start_response)
    
    return application
