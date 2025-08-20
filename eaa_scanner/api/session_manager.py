"""
Gestione sessioni persistente per discovery e scanning
Supporta recovery, stato persistente e WebSocket events
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, List, Any
import json
import threading
import time
import logging

from .models import (
    DiscoverySession, ScanSession, SessionStatus, 
    WebSocketEvent, DiscoveredPage, AccessibilityIssue
)

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manager centralizato per gestione sessioni discovery e scan
    Thread-safe con persistenza su filesystem
    """
    
    def __init__(self, storage_dir: Path = None, enable_persistence: bool = True):
        """
        Inizializza SessionManager
        
        Args:
            storage_dir: Directory per persistenza sessioni
            enable_persistence: Se abilitare salvataggio su disco
        """
        self.storage_dir = storage_dir or Path("output/sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.enable_persistence = enable_persistence
        
        # Thread safety
        self._lock = threading.RLock()
        
        # In-memory storage
        self._discovery_sessions: Dict[str, DiscoverySession] = {}
        self._scan_sessions: Dict[str, ScanSession] = {}
        
        # WebSocket callbacks
        self._websocket_callbacks: List[callable] = []
        
        # Recovery: carica sessioni esistenti
        if enable_persistence:
            self._load_sessions_from_disk()
    
    # =================================
    # DISCOVERY SESSION MANAGEMENT
    # =================================
    
    def create_discovery_session(self, base_url: str, config: Dict[str, Any] = None) -> DiscoverySession:
        """
        Crea nuova sessione discovery
        
        Args:
            base_url: URL base da esplorare
            config: Configurazione discovery (opzionale)
            
        Returns:
            DiscoverySession creata
        """
        with self._lock:
            session = DiscoverySession(base_url=base_url)
            
            if config:
                from .models import DiscoveryConfiguration
                session.config = DiscoveryConfiguration.from_dict(config)
            
            self._discovery_sessions[session.session_id] = session
            
            if self.enable_persistence:
                self._save_discovery_session(session)
            
            logger.info(f"Discovery session creata: {session.session_id} per {base_url}")
            return session
    
    def get_discovery_session(self, session_id: str) -> Optional[DiscoverySession]:
        """
        Ottiene sessione discovery per ID
        
        Args:
            session_id: ID della sessione
            
        Returns:
            DiscoverySession o None se non trovata
        """
        with self._lock:
            return self._discovery_sessions.get(session_id)
    
    def update_discovery_session(self, session_id: str, **updates) -> bool:
        """
        Aggiorna sessione discovery
        
        Args:
            session_id: ID della sessione
            **updates: Campi da aggiornare
            
        Returns:
            True se aggiornata con successo
        """
        with self._lock:
            session = self._discovery_sessions.get(session_id)
            if not session:
                return False
            
            # Applica aggiornamenti
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            # Salva se persistenza abilitata
            if self.enable_persistence:
                self._save_discovery_session(session)
            
            return True
    
    def add_discovered_page(self, session_id: str, page: DiscoveredPage) -> bool:
        """
        Aggiunge pagina scoperta a sessione discovery
        
        Args:
            session_id: ID della sessione
            page: Pagina scoperta
            
        Returns:
            True se aggiunta con successo
        """
        with self._lock:
            session = self._discovery_sessions.get(session_id)
            if not session:
                return False
            
            session.discovered_pages.append(page)
            session.pages_discovered = len(session.discovered_pages)
            
            if self.enable_persistence:
                self._save_discovery_session(session)
            
            # Invia evento WebSocket
            self._emit_websocket_event(WebSocketEvent(
                event_type="discovery_progress",
                session_id=session_id,
                data={
                    "pages_discovered": session.pages_discovered,
                    "progress_percent": session.progress_percent,
                    "current_page": page.url,
                    "page_type": page.page_type.value
                }
            ))
            
            return True
    
    def set_discovery_status(self, session_id: str, status: SessionStatus, 
                           message: str = "", error: str = "") -> bool:
        """
        Aggiorna status di sessione discovery
        
        Args:
            session_id: ID della sessione
            status: Nuovo status
            message: Messaggio opzionale
            error: Errore opzionale
            
        Returns:
            True se aggiornata
        """
        with self._lock:
            session = self._discovery_sessions.get(session_id)
            if not session:
                return False
            
            old_status = session.status
            session.status = status
            
            if status == SessionStatus.RUNNING and not session.started_at:
                session.started_at = time.time()
            elif status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
                session.completed_at = time.time()
            
            if message:
                session.add_log(message)
            if error:
                session.add_error(error)
            
            if self.enable_persistence:
                self._save_discovery_session(session)
            
            # Eventi WebSocket per cambio stato
            if status != old_status:
                event_type = "discovery_complete" if status == SessionStatus.COMPLETED else "discovery_status_change"
                self._emit_websocket_event(WebSocketEvent(
                    event_type=event_type,
                    session_id=session_id,
                    data={
                        "status": status.value,
                        "message": message,
                        "error": error,
                        "pages_discovered": session.pages_discovered
                    }
                ))
            
            return True
    
    def get_discovery_sessions_list(self, status_filter: Optional[SessionStatus] = None) -> List[Dict[str, Any]]:
        """
        Ottiene lista sessioni discovery con filtro opzionale
        
        Args:
            status_filter: Filtra per status specifico
            
        Returns:
            Lista di summary delle sessioni
        """
        with self._lock:
            sessions = []
            for session in self._discovery_sessions.values():
                if status_filter and session.status != status_filter:
                    continue
                
                sessions.append({
                    "session_id": session.session_id,
                    "base_url": session.base_url,
                    "status": session.status.value,
                    "pages_discovered": session.pages_discovered,
                    "created_at": session.created_at,
                    "started_at": session.started_at,
                    "completed_at": session.completed_at,
                    "templates_detected": session.templates_detected,
                    "progress_percent": session.progress_percent
                })
            
            # Ordina per data creazione (più recenti prima)
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
            return sessions
    
    # =================================
    # SCAN SESSION MANAGEMENT  
    # =================================
    
    def create_scan_session(self, discovery_session_id: str, selected_urls: List[str],
                          company_name: str, email: str, config: Dict[str, Any] = None) -> Optional[ScanSession]:
        """
        Crea nuova sessione scan collegata a discovery session
        
        Args:
            discovery_session_id: ID sessione discovery
            selected_urls: URLs selezionate per scan
            company_name: Nome azienda
            email: Email contatto
            config: Configurazione scan (opzionale)
            
        Returns:
            ScanSession creata o None se errore
        """
        with self._lock:
            # Verifica che discovery session esista
            discovery_session = self._discovery_sessions.get(discovery_session_id)
            if not discovery_session:
                logger.error(f"Discovery session non trovata: {discovery_session_id}")
                return None
            
            # Filtra pagine selezionate
            selected_pages = []
            for page in discovery_session.discovered_pages:
                if page.url in selected_urls:
                    page.selected_for_scan = True
                    selected_pages.append(page)
            
            if not selected_pages:
                logger.error(f"Nessuna pagina valida selezionata per scan da {selected_urls}")
                return None
            
            # Crea sessione scan
            session = ScanSession(
                discovery_session_id=discovery_session_id,
                selected_pages=selected_pages,
                company_name=company_name,
                email=email,
                total_pages=len(selected_pages)
            )
            
            if config:
                from .models import ScanConfiguration
                session.config = ScanConfiguration.from_dict(config)
            
            self._scan_sessions[session.session_id] = session
            
            if self.enable_persistence:
                self._save_scan_session(session)
            
            logger.info(f"Scan session creata: {session.session_id} per {len(selected_pages)} pagine")
            return session
    
    def get_scan_session(self, session_id: str) -> Optional[ScanSession]:
        """
        Ottiene sessione scan per ID
        
        Args:
            session_id: ID della sessione
            
        Returns:
            ScanSession o None se non trovata
        """
        with self._lock:
            return self._scan_sessions.get(session_id)
    
    def update_scan_session(self, session_id: str, **updates) -> bool:
        """
        Aggiorna sessione scan
        
        Args:
            session_id: ID della sessione
            **updates: Campi da aggiornare
            
        Returns:
            True se aggiornata con successo
        """
        with self._lock:
            session = self._scan_sessions.get(session_id)
            if not session:
                return False
            
            # Applica aggiornamenti
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            if self.enable_persistence:
                self._save_scan_session(session)
            
            return True
    
    def add_scan_issue(self, session_id: str, issue: AccessibilityIssue) -> bool:
        """
        Aggiunge problema di accessibilità a sessione scan
        
        Args:
            session_id: ID della sessione
            issue: Problema di accessibilità
            
        Returns:
            True se aggiunto con successo
        """
        with self._lock:
            session = self._scan_sessions.get(session_id)
            if not session:
                return False
            
            session.add_issue(issue)
            
            if self.enable_persistence:
                self._save_scan_session(session)
            
            return True
    
    def set_scan_status(self, session_id: str, status: SessionStatus,
                       message: str = "", error: str = "") -> bool:
        """
        Aggiorna status di sessione scan
        
        Args:
            session_id: ID della sessione
            status: Nuovo status
            message: Messaggio opzionale
            error: Errore opzionale
            
        Returns:
            True se aggiornata
        """
        with self._lock:
            session = self._scan_sessions.get(session_id)
            if not session:
                return False
            
            old_status = session.status
            session.status = status
            
            if status == SessionStatus.RUNNING and not session.started_at:
                session.started_at = time.time()
            elif status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
                session.completed_at = time.time()
                # Calcola score finale se completato
                if status == SessionStatus.COMPLETED:
                    session.calculate_compliance_score()
            
            if message:
                session.add_log(message)
            if error:
                session.add_error(error)
            
            if self.enable_persistence:
                self._save_scan_session(session)
            
            # Eventi WebSocket
            if status != old_status:
                event_type = "scan_complete" if status == SessionStatus.COMPLETED else "scan_status_change"
                self._emit_websocket_event(WebSocketEvent(
                    event_type=event_type,
                    session_id=session_id,
                    data={
                        "status": status.value,
                        "message": message,
                        "error": error,
                        "overall_score": session.overall_score,
                        "compliance_level": session.compliance_level,
                        "total_issues": session.total_issues
                    }
                ))
            
            return True
    
    def update_scan_progress(self, session_id: str, pages_scanned: int, 
                           current_page: str = "", current_scanner: str = "",
                           message: str = "") -> bool:
        """
        Aggiorna progresso di sessione scan
        
        Args:
            session_id: ID sessione
            pages_scanned: Numero pagine completate
            current_page: Pagina corrente
            current_scanner: Scanner corrente
            message: Messaggio di progresso
            
        Returns:
            True se aggiornata
        """
        with self._lock:
            session = self._scan_sessions.get(session_id)
            if not session:
                return False
            
            session.pages_scanned = pages_scanned
            
            # Calcola percentuale
            if session.total_pages > 0:
                progress_percent = int((pages_scanned / session.total_pages) * 100)
                session.update_progress(progress_percent, message, current_page, current_scanner)
            
            if self.enable_persistence:
                self._save_scan_session(session)
            
            # Evento WebSocket per progresso
            self._emit_websocket_event(WebSocketEvent(
                event_type="scan_progress",
                session_id=session_id,
                data={
                    "pages_scanned": pages_scanned,
                    "total_pages": session.total_pages,
                    "progress_percent": session.progress_percent,
                    "current_page": current_page,
                    "current_scanner": current_scanner,
                    "message": message
                }
            ))
            
            return True
    
    def get_scan_sessions_list(self, status_filter: Optional[SessionStatus] = None) -> List[Dict[str, Any]]:
        """
        Ottiene lista sessioni scan con filtro opzionale
        
        Args:
            status_filter: Filtra per status specifico
            
        Returns:
            Lista di summary delle sessioni
        """
        with self._lock:
            sessions = []
            for session in self._scan_sessions.values():
                if status_filter and session.status != status_filter:
                    continue
                
                sessions.append({
                    "session_id": session.session_id,
                    "discovery_session_id": session.discovery_session_id,
                    "company_name": session.company_name,
                    "status": session.status.value,
                    "pages_scanned": session.pages_scanned,
                    "total_pages": session.total_pages,
                    "overall_score": session.overall_score,
                    "compliance_level": session.compliance_level,
                    "total_issues": session.total_issues,
                    "created_at": session.created_at,
                    "started_at": session.started_at,
                    "completed_at": session.completed_at,
                    "progress_percent": session.progress_percent
                })
            
            # Ordina per data creazione
            sessions.sort(key=lambda x: x['created_at'], reverse=True)
            return sessions
    
    # =================================
    # WEBSOCKET EVENT MANAGEMENT
    # =================================
    
    def register_websocket_callback(self, callback: callable) -> None:
        """
        Registra callback per eventi WebSocket
        
        Args:
            callback: Funzione da chiamare per ogni evento
        """
        self._websocket_callbacks.append(callback)
    
    def unregister_websocket_callback(self, callback: callable) -> None:
        """
        Rimuove callback WebSocket
        
        Args:
            callback: Funzione da rimuovere
        """
        if callback in self._websocket_callbacks:
            self._websocket_callbacks.remove(callback)
    
    def _emit_websocket_event(self, event: WebSocketEvent) -> None:
        """
        Emette evento WebSocket a tutti i callback registrati
        
        Args:
            event: Evento da emettere
        """
        for callback in self._websocket_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Errore callback WebSocket: {e}")
    
    # =================================
    # PERSISTENCE MANAGEMENT
    # =================================
    
    def _save_discovery_session(self, session: DiscoverySession) -> None:
        """
        Salva sessione discovery su disco
        
        Args:
            session: Sessione da salvare
        """
        try:
            file_path = self.storage_dir / f"discovery_{session.session_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Errore salvataggio discovery session {session.session_id}: {e}")
    
    def _save_scan_session(self, session: ScanSession) -> None:
        """
        Salva sessione scan su disco
        
        Args:
            session: Sessione da salvare
        """
        try:
            file_path = self.storage_dir / f"scan_{session.session_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Errore salvataggio scan session {session.session_id}: {e}")
    
    def _load_sessions_from_disk(self) -> None:
        """
        Carica sessioni salvate dal disco per recovery
        """
        try:
            # Carica discovery sessions
            for file_path in self.storage_dir.glob("discovery_*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = DiscoverySession.from_dict(data)
                    self._discovery_sessions[session.session_id] = session
                    logger.debug(f"Discovery session caricata: {session.session_id}")
                except Exception as e:
                    logger.error(f"Errore caricamento {file_path}: {e}")
            
            # Carica scan sessions
            for file_path in self.storage_dir.glob("scan_*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    session = ScanSession.from_dict(data)
                    self._scan_sessions[session.session_id] = session
                    logger.debug(f"Scan session caricata: {session.session_id}")
                except Exception as e:
                    logger.error(f"Errore caricamento {file_path}: {e}")
            
            logger.info(f"Recovery completato: {len(self._discovery_sessions)} discovery, {len(self._scan_sessions)} scan sessions")
            
        except Exception as e:
            logger.error(f"Errore recovery sessioni: {e}")
    
    # =================================
    # CLEANUP & MAINTENANCE
    # =================================
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Rimuove sessioni vecchie per liberare memoria
        
        Args:
            max_age_hours: Età massima sessioni in ore
            
        Returns:
            Numero di sessioni rimosse
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        removed = 0
        
        with self._lock:
            # Discovery sessions
            to_remove = []
            for session_id, session in self._discovery_sessions.items():
                if session.created_at < cutoff_time and session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                del self._discovery_sessions[session_id]
                # Rimuovi file se esiste
                file_path = self.storage_dir / f"discovery_{session_id}.json"
                if file_path.exists():
                    file_path.unlink()
                removed += 1
            
            # Scan sessions
            to_remove = []
            for session_id, session in self._scan_sessions.items():
                if session.created_at < cutoff_time and session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                del self._scan_sessions[session_id]
                # Rimuovi file se esiste
                file_path = self.storage_dir / f"scan_{session_id}.json"
                if file_path.exists():
                    file_path.unlink()
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleanup completato: {removed} sessioni vecchie rimosse")
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Ottiene statistiche sessioni
        
        Returns:
            Dizionario con statistiche
        """
        with self._lock:
            # Conta discovery sessions per status
            discovery_stats = {}
            for session in self._discovery_sessions.values():
                status = session.status.value
                discovery_stats[status] = discovery_stats.get(status, 0) + 1
            
            # Conta scan sessions per status  
            scan_stats = {}
            for session in self._scan_sessions.values():
                status = session.status.value
                scan_stats[status] = scan_stats.get(status, 0) + 1
            
            return {
                "discovery_sessions": {
                    "total": len(self._discovery_sessions),
                    "by_status": discovery_stats
                },
                "scan_sessions": {
                    "total": len(self._scan_sessions),
                    "by_status": scan_stats
                },
                "storage_enabled": self.enable_persistence,
                "websocket_callbacks": len(self._websocket_callbacks)
            }


# Singleton instance per uso globale
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> SessionManager:
    """
    Ottiene istanza singleton di SessionManager
    
    Returns:
        SessionManager globale
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

def init_session_manager(storage_dir: Path = None, enable_persistence: bool = True) -> SessionManager:
    """
    Inizializza SessionManager con configurazione specifica
    
    Args:
        storage_dir: Directory storage personalizzata
        enable_persistence: Se abilitare persistenza
        
    Returns:
        SessionManager configurato
    """
    global _session_manager
    _session_manager = SessionManager(storage_dir, enable_persistence)
    return _session_manager
