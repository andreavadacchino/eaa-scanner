"""
Sistema di monitoraggio live per le scansioni di accessibilità
Server-Sent Events (SSE) per aggiornamenti in tempo reale
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
import uuid


class ScanProgressEmitter:
    """
    Emettitore di eventi di progresso per scansioni accessibilità
    Utilizza Server-Sent Events per comunicazione real-time
    """
    
    def __init__(self):
        # Dizionario per memorizzare i client connessi {scan_id: [client_streams]}
        self.clients: Dict[str, List] = {}
        # Lock per thread safety
        self.lock = threading.Lock()
        # Memorizza eventi recenti per ogni scan_id
        self.event_history: Dict[str, List[Dict]] = {}
        
    def add_client(self, scan_id: str, client_stream):
        """Aggiunge un client connesso per ricevere eventi"""
        with self.lock:
            if scan_id not in self.clients:
                self.clients[scan_id] = []
            self.clients[scan_id].append(client_stream)
            
            # Invia eventi storici se disponibili
            if scan_id in self.event_history:
                for event in self.event_history[scan_id]:
                    self._send_to_client(client_stream, event)
                    
    def remove_client(self, scan_id: str, client_stream):
        """Rimuove un client connesso"""
        with self.lock:
            if scan_id in self.clients:
                try:
                    self.clients[scan_id].remove(client_stream)
                    if not self.clients[scan_id]:
                        del self.clients[scan_id]
                except ValueError:
                    pass
                    
    def cleanup_scan(self, scan_id: str):
        """Pulisce i dati di una scansione completata"""
        with self.lock:
            if scan_id in self.clients:
                del self.clients[scan_id]
            # Mantieni eventi per 1 ora
            if scan_id in self.event_history:
                del self.event_history[scan_id]
    
    def _emit_event(self, scan_id: str, event_type: str, data: Dict[str, Any]):
        """Emette un evento a tutti i client connessi per uno scan_id"""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "scan_id": scan_id,
            "data": data
        }
        
        # IMPORTANTE: Memorizza SEMPRE l'evento nella storia, anche senza client connessi
        with self.lock:
            if scan_id not in self.event_history:
                self.event_history[scan_id] = []
            self.event_history[scan_id].append(event)
            
            # Mantieni solo gli ultimi 500 eventi per scansioni lunghe
            if len(self.event_history[scan_id]) > 500:
                self.event_history[scan_id] = self.event_history[scan_id][-500:]
            
            # Log per debug
            import logging
            logger = logging.getLogger('webapp.monitor')
            logger.info(f"Evento emesso: {event_type} per scan {scan_id}, eventi totali: {len(self.event_history[scan_id])}")
        
        # Invia a tutti i client connessi (se ce ne sono)
        with self.lock:
            if scan_id in self.clients:
                clients_to_remove = []
                for client in self.clients[scan_id]:
                    try:
                        self._send_to_client(client, event)
                    except Exception:
                        # Client disconnesso, rimuovi dalla lista
                        clients_to_remove.append(client)
                
                # Rimuovi client disconnessi
                for client in clients_to_remove:
                    self.clients[scan_id].remove(client)
                    
                # Se non ci sono più client, rimuovi scan_id dalla lista client (ma NON dalla storia!)
                if not self.clients[scan_id]:
                    del self.clients[scan_id]
    
    def _send_to_client(self, client_stream, event: Dict):
        """Invia evento SSE a un singolo client"""
        sse_data = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        client_stream.write(sse_data.encode('utf-8'))
        
    # --- Eventi Specifici ---
    
    def emit_scan_start(self, scan_id: str, url: str, company_name: str, 
                       scanners_enabled: Dict[str, bool]):
        """Emette evento di inizio scansione"""
        self._emit_event(scan_id, "scan_start", {
            "url": url,
            "company_name": company_name,
            "scanners_enabled": scanners_enabled,
            "message": f"Avvio scansione per {company_name}"
        })
    
    def emit_scanner_start(self, scan_id: str, scanner_name: str, url: str, 
                          estimated_duration: Optional[int] = None):
        """Emette evento di inizio scanner"""
        self._emit_event(scan_id, "scanner_start", {
            "scanner": scanner_name,
            "url": url,
            "estimated_duration_seconds": estimated_duration,
            "message": f"Avvio {scanner_name} per {url}"
        })
    
    def emit_scanner_operation(self, scan_id: str, scanner_name: str, 
                             operation: str, progress: Optional[int] = None,
                             details: Optional[Dict] = None):
        """Emette evento di operazione scanner"""
        self._emit_event(scan_id, "scanner_operation", {
            "scanner": scanner_name,
            "operation": operation,
            "progress_percent": progress,
            "details": details or {},
            "message": f"{scanner_name}: {operation}"
        })
    
    def emit_scanner_complete(self, scan_id: str, scanner_name: str, 
                            results_summary: Dict[str, Any]):
        """Emette evento di completamento scanner"""
        self._emit_event(scan_id, "scanner_complete", {
            "scanner": scanner_name,
            "results": results_summary,
            "message": f"{scanner_name} completato"
        })
    
    def emit_scanner_error(self, scan_id: str, scanner_name: str, 
                         error_message: str, is_critical: bool = False):
        """Emette evento di errore scanner"""
        self._emit_event(scan_id, "scanner_error", {
            "scanner": scanner_name,
            "error": error_message,
            "is_critical": is_critical,
            "message": f"Errore {scanner_name}: {error_message}"
        })
    
    def emit_page_progress(self, scan_id: str, current_page: int, 
                          total_pages: int, current_url: str):
        """Emette evento di progresso multi-pagina"""
        progress = int((current_page / total_pages) * 100)
        self._emit_event(scan_id, "page_progress", {
            "current_page": current_page,
            "total_pages": total_pages,
            "current_url": current_url,
            "progress_percent": progress,
            "message": f"Pagina {current_page}/{total_pages}: {current_url}"
        })
    
    def emit_processing_step(self, scan_id: str, step_name: str, 
                           progress: Optional[int] = None):
        """Emette evento di step di processing"""
        self._emit_event(scan_id, "processing_step", {
            "step": step_name,
            "progress_percent": progress,
            "message": f"Elaborazione: {step_name}"
        })
    
    def emit_report_generation(self, scan_id: str, stage: str, 
                             progress: Optional[int] = None):
        """Emette evento di generazione report"""
        self._emit_event(scan_id, "report_generation", {
            "stage": stage,
            "progress_percent": progress,
            "message": f"Generazione report: {stage}"
        })
    
    def emit_scan_complete(self, scan_id: str, total_duration: float, 
                         report_paths: Dict[str, str], summary: Dict[str, Any]):
        """Emette evento di scansione completata"""
        self._emit_event(scan_id, "scan_complete", {
            "duration_seconds": total_duration,
            "report_paths": report_paths,
            "summary": summary,
            "message": "Scansione completata con successo"
        })
    
    def emit_scan_failed(self, scan_id: str, error_message: str, 
                        partial_results: Optional[Dict] = None):
        """Emette evento di scansione fallita"""
        self._emit_event(scan_id, "scan_failed", {
            "error": error_message,
            "partial_results": partial_results,
            "message": f"Scansione fallita: {error_message}"
        })


# Istanza globale del monitor
global_monitor = ScanProgressEmitter()


def get_scan_monitor() -> ScanProgressEmitter:
    """Restituisce l'istanza globale del monitor"""
    return global_monitor


# Classe per gestire connessioni SSE
class SSEStream:
    """Wrapper per gestire stream SSE con il client"""
    
    def __init__(self, start_response_func):
        self.start_response = start_response_func
        self.headers_sent = False
        self.buffer = io.BytesIO()
        
    def write(self, data: bytes):
        """Scrive dati al stream SSE"""
        if not self.headers_sent:
            self.start_response("200 OK", [
                ("Content-Type", "text/event-stream"),
                ("Cache-Control", "no-cache"),
                ("Connection", "keep-alive"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Cache-Control")
            ])
            self.headers_sent = True
            
        # Invia dati immediatamente
        yield data
        
    def send_initial_message(self):
        """Invia messaggio iniziale di connessione"""
        initial_data = {
            "event_type": "connection",
            "timestamp": datetime.now().isoformat(),
            "message": "Connessione monitoraggio stabilita"
        }
        sse_message = f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n"
        return sse_message.encode('utf-8')


import io