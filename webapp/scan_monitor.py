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
    
    def _emit_event(self, scan_id: str, event_type: str, data: Dict[str, Any], message: Optional[str] = None):
        """Emette un evento a tutti i client connessi per uno scan_id secondo il contratto SSE.

        - Aggiunge sempre campi top-level: event_type, timestamp, scan_id, data, message(opzionale)
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "scan_id": scan_id,
            "data": data,
        }
        if message:
            event["message"] = message
        
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
                       scanners_enabled: Dict[str, bool], total_pages: Optional[int] = None):
        """Emette evento di inizio scansione conforme al contratto."""
        scanners_list = [k for k, v in (scanners_enabled or {}).items() if v]
        payload = {
            "company_name": company_name,
            "url": url,
            # total_pages può non essere noto all'avvio
            **({"total_pages": int(total_pages)} if total_pages is not None else {}),
            "scanners": scanners_list,
        }
        self._emit_event(scan_id, "scan_start", payload, message=f"Scansione avviata")
    
    def emit_scanner_start(self, scan_id: str, scanner_name: str, url: str,
                          estimated_duration: Optional[int] = None):
        """Emette evento di inizio scanner (stimare durata in ms se nota)."""
        payload = {
            "scanner": scanner_name,
            "url": url,
        }
        if estimated_duration is not None:
            payload["estimated_duration"] = int(estimated_duration)
        self._emit_event(scan_id, "scanner_start", payload, message=f"Avvio scanner {scanner_name}")
    
    def emit_scanner_operation(self, scan_id: str, scanner_name: str,
                             operation: str, progress: Optional[int] = None,
                             details: Optional[Dict] = None):
        """Emette evento di operazione scanner."""
        payload = {
            "scanner": scanner_name,
            "operation": operation,
            # Manteniamo entrambi i campi per retrocompatibilità
            **({"progress": int(progress), "progress_percent": int(progress)} if progress is not None else {}),
            "details": details or {},
        }
        self._emit_event(scan_id, "scanner_operation", payload, message=f"{scanner_name}: {operation}")
    
    def emit_scanner_complete(self, scan_id: str, scanner_name: str,
                            results_summary: Dict[str, Any]):
        """Emette evento di completamento scanner.

        Mappa campi standard (success, errors, warnings, duration_ms, issues_found) se disponibili
        e include comunque il payload completo in 'results'.
        """
        payload = {"scanner": scanner_name, "results": results_summary or {}}
        # mapping best-effort
        if isinstance(results_summary, dict):
            if "success" in results_summary:
                payload["success"] = bool(results_summary.get("success"))
            if "errors" in results_summary:
                payload["errors"] = int(results_summary.get("errors", 0))
            if "warnings" in results_summary:
                payload["warnings"] = int(results_summary.get("warnings", 0))
            if "duration_ms" in results_summary:
                payload["duration_ms"] = int(results_summary.get("duration_ms", 0))
            if "issues_found" in results_summary:
                payload["issues_found"] = results_summary.get("issues_found", [])
        self._emit_event(scan_id, "scanner_complete", payload, message=f"Scanner {scanner_name} completato")
    
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
            "current_page": int(current_page),
            "total_pages": int(total_pages),
            "current_url": current_url,
            "progress_percent": int(progress),
        }, message=f"Scansione pagina {current_page} di {total_pages}")
    
    def emit_processing_step(self, scan_id: str, step_name: str,
                           progress: Optional[int] = None):
        """Emette evento di step di processing"""
        payload = {"step": step_name}
        if progress is not None:
            payload["progress_percent"] = int(progress)
        self._emit_event(scan_id, "processing_step", payload, message=f"Elaborazione: {step_name}")
    
    def emit_report_generation(self, scan_id: str, stage: str,
                             progress: Optional[int] = None):
        """Emette evento di generazione report"""
        payload = {"stage": stage}
        if progress is not None:
            payload["progress_percent"] = int(progress)
        self._emit_event(scan_id, "report_generation", payload, message=f"Generazione report: {stage}")
    
    def emit_scan_complete(self, scan_id: str, *args, **kwargs):
        """Emette evento di scansione completata.

        Supporta sia la vecchia firma (scan_id, total_duration, report_paths, summary)
        sia chiamate con singolo dict (retrocompatibilità in app.py).
        """
        data: Dict[str, Any] = {}
        # Vecchia firma: (duration, report_paths, summary)
        if len(args) >= 3 and isinstance(args[0], (int, float)):
            total_duration = float(args[0])
            report_paths = args[1] or {}
            summary = args[2] or {}
            data.update({
                "scan_duration_ms": int(total_duration * 1000),
            })
            # report_url se presente
            if isinstance(report_paths, dict):
                # prova a derivare url da eventuale html_path
                html_path = report_paths.get("html_path")
                if html_path:
                    data["report_url"] = f"/v2/preview?scan_id={scan_id}"
            # metrics from summary
            if isinstance(summary, dict):
                if "pages_scanned" in summary:
                    data["total_pages_scanned"] = int(summary.get("pages_scanned", 0))
                if "total_errors" in summary:
                    data["total_errors"] = int(summary.get("total_errors", 0))
                if "total_warnings" in summary:
                    data["total_warnings"] = int(summary.get("total_warnings", 0))
                if "compliance_score" in summary:
                    data["compliance_score"] = int(summary.get("compliance_score", 0))
                data["scan_results"] = summary
        # Nuova chiamata con singolo dict (es. metriche)
        elif len(args) == 1 and isinstance(args[0], dict):
            metrics = args[0]
            # Copia best-effort
            if "compliance_score" in metrics:
                data["compliance_score"] = int(metrics.get("compliance_score", 0))
            if "total_errors" in metrics:
                data["total_errors"] = int(metrics.get("total_errors", 0))
            if "total_warnings" in metrics:
                data["total_warnings"] = int(metrics.get("total_warnings", 0))
            if "pages_scanned" in metrics:
                data["total_pages_scanned"] = int(metrics.get("pages_scanned", 0))
            if "report_url" in metrics:
                data["report_url"] = metrics.get("report_url")
            data["scan_results"] = metrics
        else:
            # Nessun dato utile: invia almeno evento terminale
            data = {"scan_results": {}}

        self._emit_event(scan_id, "scan_complete", data, message="Scansione completata con successo")
    
    def emit_scan_failed(self, scan_id: str, error_message: str,
                        partial_results: Optional[Dict] = None,
                        error_code: Optional[str] = None,
                        failed_url: Optional[str] = None,
                        pages_completed: Optional[int] = None):
        """Emette evento di scansione fallita conforme al contratto."""
        payload = {
            "error": error_message,
            "partial_results": bool(partial_results is not None),
        }
        if error_code:
            payload["error_code"] = error_code
        if failed_url:
            payload["failed_url"] = failed_url
        if pages_completed is not None:
            payload["pages_completed"] = int(pages_completed)
        if isinstance(partial_results, dict):
            payload["partial_results_details"] = partial_results
        self._emit_event(scan_id, "scan_failed", payload, message="Scansione fallita")


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
