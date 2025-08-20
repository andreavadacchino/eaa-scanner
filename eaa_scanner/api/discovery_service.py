"""
Servizio per gestione fase DISCOVERY
Orchestra SmartCrawler e WebCrawler per scoperta intelligente pagine
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
import asyncio
import threading
import time
import logging

from ..page_sampler.smart_crawler import SmartCrawler, PageInfo
from ..crawler import WebCrawler
from .models import (
    DiscoverySession, DiscoveredPage, PageType, SessionStatus,
    DiscoveryConfiguration
)
from .session_manager import SessionManager, get_session_manager

logger = logging.getLogger(__name__)


class DiscoveryService:
    """
    Servizio per orchestrare discovery di pagine web
    Supporta SmartCrawler (Playwright) e WebCrawler (requests) con fallback
    """
    
    def __init__(self, session_manager: Optional[SessionManager] = None,
                 output_dir: Path = None):
        """
        Inizializza DiscoveryService
        
        Args:
            session_manager: Manager per gestione sessioni
            output_dir: Directory base per output
        """
        self.session_manager = session_manager or get_session_manager()
        self.output_dir = output_dir or Path("output")
        
        # Thread pool per esecuzione asincrona
        self._running_threads: Dict[str, threading.Thread] = {}
        
        logger.info("DiscoveryService inizializzato")
    
    def start_discovery(self, base_url: str, config: Optional[DiscoveryConfiguration] = None,
                       progress_callback: Optional[Callable] = None) -> str:
        """
        Avvia processo di discovery asincrono
        
        Args:
            base_url: URL base da esplorare
            config: Configurazione discovery (opzionale)
            progress_callback: Callback per aggiornamenti progress
            
        Returns:
            ID della sessione discovery creata
        """
        # Crea sessione
        session = self.session_manager.create_discovery_session(
            base_url=base_url,
            config=config.to_dict() if config else None
        )
        
        # Imposta directory output
        session_output_dir = self.output_dir / "discovery" / session.session_id
        session_output_dir.mkdir(parents=True, exist_ok=True)
        session.output_dir = str(session_output_dir)
        
        self.session_manager.update_discovery_session(
            session.session_id,
            output_dir=str(session_output_dir)
        )
        
        logger.info(f"Avvio discovery per {base_url}, session: {session.session_id}")
        
        # Avvia thread worker
        thread = threading.Thread(
            target=self._discovery_worker,
            args=(session.session_id, progress_callback),
            daemon=True,
            name=f"discovery-{session.session_id[:8]}"
        )
        
        self._running_threads[session.session_id] = thread
        thread.start()
        
        return session.session_id
    
    def get_discovery_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene status corrente di sessione discovery
        
        Args:
            session_id: ID della sessione
            
        Returns:
            Dizionario con status e metadati o None se non trovata
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            return None
        
        # Determina se thread è ancora attivo
        thread = self._running_threads.get(session_id)
        is_running = thread is not None and thread.is_alive()
        
        return {
            "session_id": session_id,
            "base_url": session.base_url,
            "status": session.status.value,
            "progress_percent": session.progress_percent,
            "progress_message": session.progress_message,
            "current_page": session.current_page,
            "pages_discovered": session.pages_discovered,
            "pages_processed": session.pages_processed,
            "templates_detected": session.templates_detected,
            "sitemap_urls_found": session.sitemap_urls_found,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "is_thread_active": is_running,
            "errors": session.errors,
            "warnings": session.warnings,
            "log_messages": session.log_messages[-20:],  # Ultimi 20 messaggi
            "config": session.config.to_dict()
        }
    
    def get_discovery_results(self, session_id: str, include_unselected: bool = True) -> Optional[Dict[str, Any]]:
        """
        Ottiene risultati completi di discovery session
        
        Args:
            session_id: ID della sessione
            include_unselected: Se includere pagine non selezionate
            
        Returns:
            Dizionario con risultati completi o None se non trovata
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            return None
        
        # Filtra pagine se richiesto
        pages = session.discovered_pages
        if not include_unselected:
            pages = [p for p in pages if p.selected_for_scan]
        
        # Raggruppa per tipo
        pages_by_type = {}
        for page in pages:
            page_type = page.page_type.value
            if page_type not in pages_by_type:
                pages_by_type[page_type] = []
            pages_by_type[page_type].append(page.to_dict())
        
        # Statistiche
        total_pages = len(pages)
        selected_pages = len([p for p in session.discovered_pages if p.selected_for_scan])
        
        return {
            "session_id": session_id,
            "base_url": session.base_url,
            "status": session.status.value,
            "total_pages_discovered": session.pages_discovered,
            "total_pages_returned": total_pages,
            "selected_for_scan": selected_pages,
            "templates_detected": session.templates_detected,
            "sitemap_urls_found": session.sitemap_urls_found,
            "pages": [p.to_dict() for p in pages],
            "pages_by_type": pages_by_type,
            "type_counts": {k: len(v) for k, v in pages_by_type.items()},
            "created_at": session.created_at,
            "completed_at": session.completed_at,
            "duration_seconds": (
                session.completed_at - session.created_at 
                if session.completed_at else time.time() - session.created_at
            ),
            "config": session.config.to_dict()
        }
    
    def cancel_discovery(self, session_id: str) -> bool:
        """
        Cancella discovery in corso
        
        Args:
            session_id: ID della sessione da cancellare
            
        Returns:
            True se cancellata con successo
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            return False
        
        # Segnala cancellazione
        self.session_manager.set_discovery_status(
            session_id,
            SessionStatus.CANCELLED,
            message="Discovery cancellata dall'utente"
        )
        
        # Il thread dovrebbe terminare controllando lo status
        logger.info(f"Discovery {session_id} cancellata")
        return True
    
    def update_page_selection(self, session_id: str, selected_urls: List[str]) -> bool:
        """
        Aggiorna selezione pagine per scanning
        
        Args:
            session_id: ID della sessione
            selected_urls: Lista URL da selezionare per scan
            
        Returns:
            True se aggiornata con successo
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            return False
        
        # Reset selezioni precedenti
        for page in session.discovered_pages:
            page.selected_for_scan = False
            page.selection_reason = ""
        
        # Applica nuove selezioni
        selected_count = 0
        for page in session.discovered_pages:
            if page.url in selected_urls:
                page.selected_for_scan = True
                page.selection_reason = "user_selected"
                selected_count += 1
        
        # Salva aggiornamento
        self.session_manager.update_discovery_session(session_id)
        
        logger.info(f"Selezione aggiornata per session {session_id}: {selected_count} pagine")
        return True
    
    def _discovery_worker(self, session_id: str, progress_callback: Optional[Callable] = None) -> None:
        """
        Worker thread per esecuzione discovery
        
        Args:
            session_id: ID della sessione
            progress_callback: Callback per progress updates
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            logger.error(f"Session {session_id} non trovata in worker")
            return
        
        try:
            # Avvia sessione
            self.session_manager.set_discovery_status(
                session_id,
                SessionStatus.RUNNING,
                message="Inizializzazione crawler..."
            )
            
            logger.info(f"Discovery worker avviato per {session.base_url}")
            
            # Crea callback progress interno
            def internal_progress_callback(data: Dict[str, Any]) -> None:
                # Controlla se sessione è stata cancellata
                current_session = self.session_manager.get_discovery_session(session_id)
                if not current_session or current_session.status == SessionStatus.CANCELLED:
                    return  # Termina silenziosamente
                
                # Aggiorna progresso
                message = data.get('message', '')
                pages_found = data.get('pages_found', current_session.pages_discovered)
                
                self.session_manager.update_discovery_session(
                    session_id,
                    pages_discovered=pages_found,
                    current_page=data.get('current_page', ''),
                    progress_message=message
                )
                
                # Chiama callback esterno se presente
                if progress_callback:
                    try:
                        progress_callback({
                            'session_id': session_id,
                            'type': 'discovery_progress',
                            **data
                        })
                    except Exception as e:
                        logger.warning(f"Errore progress callback: {e}")
            
            # Configura crawler
            config = session.config
            
            # Prova SmartCrawler se abilitato
            discovered_pages = []
            
            if config.use_smart_crawler:
                try:
                    discovered_pages = self._run_smart_crawler(
                        session, internal_progress_callback
                    )
                    logger.info(f"SmartCrawler completato: {len(discovered_pages)} pagine")
                except Exception as e:
                    logger.warning(f"SmartCrawler fallito: {e}, fallback a WebCrawler")
                    session.add_warning(f"SmartCrawler non disponibile: {e}")
            
            # Fallback a WebCrawler se SmartCrawler fallito o disabilitato
            if not discovered_pages:
                try:
                    discovered_pages = self._run_web_crawler(
                        session, internal_progress_callback
                    )
                    logger.info(f"WebCrawler completato: {len(discovered_pages)} pagine")
                except Exception as e:
                    logger.error(f"Anche WebCrawler fallito: {e}")
                    self.session_manager.set_discovery_status(
                        session_id,
                        SessionStatus.FAILED,
                        error=f"Entrambi i crawler falliti: {e}"
                    )
                    return
            
            # Controlla se cancellato durante esecuzione
            current_session = self.session_manager.get_discovery_session(session_id)
            if not current_session or current_session.status == SessionStatus.CANCELLED:
                logger.info(f"Discovery {session_id} cancellata durante esecuzione")
                return
            
            # Processa risultati
            self._process_discovery_results(session_id, discovered_pages)
            
            # Completa con successo
            self.session_manager.set_discovery_status(
                session_id,
                SessionStatus.COMPLETED,
                message=f"Discovery completata: {len(discovered_pages)} pagine scoperte"
            )
            
            logger.info(f"Discovery {session_id} completata con successo")
            
        except Exception as e:
            logger.error(f"Errore in discovery worker {session_id}: {e}", exc_info=True)
            self.session_manager.set_discovery_status(
                session_id,
                SessionStatus.FAILED,
                error=f"Errore worker: {str(e)}"
            )
        finally:
            # Cleanup thread reference
            if session_id in self._running_threads:
                del self._running_threads[session_id]
    
    def _run_smart_crawler(self, session: DiscoverySession, 
                          progress_callback: Callable) -> List[PageInfo]:
        """
        Esegue SmartCrawler con Playwright
        
        Args:
            session: Sessione discovery
            progress_callback: Callback per progress
            
        Returns:
            Lista di PageInfo scoperte
        """
        config = session.config
        
        # Controlla se Playwright è disponibile
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise Exception("Playwright non installato")
        
        crawler = SmartCrawler(
            base_url=session.base_url,
            max_pages=config.max_pages,
            max_depth=config.max_depth,
            timeout_per_page=config.timeout_per_page,
            screenshot_enabled=config.screenshot_enabled,
            progress_callback=progress_callback
        )
        
        # Pattern esclusioni personalizzati
        if config.excluded_patterns:
            crawler.excluded_patterns = config.excluded_patterns
        
        logger.info(f"Avvio SmartCrawler per {session.base_url}")
        session.add_log("Avvio SmartCrawler con Playwright...")
        
        # Esegui crawling
        pages = crawler.crawl()
        
        session.add_log(f"SmartCrawler completato: {len(pages)} pagine scoperte")
        return pages
    
    def _run_web_crawler(self, session: DiscoverySession,
                        progress_callback: Callable) -> List[Dict[str, Any]]:
        """
        Esegue WebCrawler con requests (fallback)
        
        Args:
            session: Sessione discovery
            progress_callback: Callback per progress
            
        Returns:
            Lista di dizionari pagine scoperte
        """
        config = session.config
        
        crawler = WebCrawler(
            base_url=session.base_url,
            max_pages=config.max_pages,
            max_depth=config.max_depth,
            follow_external=config.follow_external,
            allowed_domains=config.allowed_domains,
            excluded_patterns=config.excluded_patterns
        )
        
        logger.info(f"Avvio WebCrawler per {session.base_url}")
        session.add_log("Avvio WebCrawler con requests...")
        
        # Esegui crawling
        pages = crawler.crawl()
        
        session.add_log(f"WebCrawler completato: {len(pages)} pagine scoperte")
        return pages
    
    def _process_discovery_results(self, session_id: str, 
                                  raw_pages: List[Any]) -> None:
        """
        Processa e normalizza risultati discovery
        
        Args:
            session_id: ID della sessione
            raw_pages: Pagine raw dal crawler
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session:
            return
        
        session.add_log("Processamento risultati discovery...")
        
        # Converti in DiscoveredPage
        processed_pages = []
        templates_detected = set()
        
        for raw_page in raw_pages:
            try:
                if isinstance(raw_page, PageInfo):  # SmartCrawler result
                    discovered_page = DiscoveredPage(
                        url=raw_page.url,
                        title=raw_page.title,
                        description=raw_page.description,
                        page_type=self._map_page_type(raw_page.page_type),
                        priority=raw_page.priority,
                        depth=raw_page.depth,
                        discovered_at=raw_page.discovered_at,
                        forms_count=raw_page.forms_count,
                        inputs_count=raw_page.inputs_count,
                        buttons_count=raw_page.buttons_count,
                        images_count=raw_page.images_count,
                        videos_count=raw_page.videos_count,
                        links_count=raw_page.links_count,
                        has_h1=raw_page.has_h1,
                        has_nav=raw_page.has_nav,
                        has_main=raw_page.has_main,
                        has_footer=raw_page.has_footer,
                        lang=raw_page.lang,
                        template_hash=raw_page.template_hash,
                        dom_structure=raw_page.dom_structure,
                        screenshot_path=raw_page.screenshot_path
                    )
                    
                    # Template detection
                    if raw_page.template_hash:
                        templates_detected.add(raw_page.template_hash)
                
                elif isinstance(raw_page, dict):  # WebCrawler result
                    discovered_page = DiscoveredPage(
                        url=raw_page['url'],
                        title=raw_page.get('title', ''),
                        description=raw_page.get('description', ''),
                        page_type=self._map_page_type(raw_page.get('page_type', 'general')),
                        priority=raw_page.get('priority', 50),
                        depth=raw_page.get('depth', 0),
                        discovered_at=raw_page.get('discovered_at', time.time()),
                        forms_count=raw_page.get('elements', {}).get('forms', 0),
                        inputs_count=raw_page.get('elements', {}).get('inputs', 0),
                        buttons_count=raw_page.get('elements', {}).get('buttons', 0),
                        images_count=raw_page.get('elements', {}).get('images', 0),
                        videos_count=raw_page.get('elements', {}).get('videos', 0),
                        lang=raw_page.get('language', 'it')
                    )
                
                else:
                    logger.warning(f"Tipo pagina non riconosciuto: {type(raw_page)}")
                    continue
                
                processed_pages.append(discovered_page)
                
            except Exception as e:
                logger.warning(f"Errore processamento pagina {raw_page}: {e}")
                continue
        
        # Applica selezione automatica intelligente
        self._apply_smart_selection(processed_pages)
        
        # Aggiorna sessione
        for page in processed_pages:
            self.session_manager.add_discovered_page(session_id, page)
        
        self.session_manager.update_discovery_session(
            session_id,
            templates_detected=len(templates_detected),
            pages_processed=len(processed_pages)
        )
        
        session.add_log(f"Processamento completato: {len(processed_pages)} pagine, {len(templates_detected)} template")
        
        # Salva report discovery
        self._save_discovery_report(session_id)
    
    def _map_page_type(self, raw_type: str) -> PageType:
        """
        Mappa tipo pagina da string a enum PageType
        
        Args:
            raw_type: Tipo raw dal crawler
            
        Returns:
            PageType corrispondente
        """
        type_mapping = {
            'homepage': PageType.HOMEPAGE,
            'authentication': PageType.AUTHENTICATION,
            'contact': PageType.CONTACT,
            'form': PageType.FORM,
            'search': PageType.SEARCH,
            'ecommerce': PageType.ECOMMERCE,
            'checkout': PageType.ECOMMERCE,
            'product': PageType.ECOMMERCE,
            'article': PageType.ARTICLE,
            'content': PageType.ARTICLE,
            'about': PageType.ABOUT,
            'legal': PageType.LEGAL,
            'general': PageType.GENERAL
        }
        
        return type_mapping.get(raw_type.lower(), PageType.GENERAL)
    
    def _apply_smart_selection(self, pages: List[DiscoveredPage]) -> None:
        """
        Applica selezione intelligente automatica delle pagine
        
        Args:
            pages: Lista pagine da processare
        """
        # Ordina per priorità
        pages.sort(key=lambda p: (-p.priority, p.depth))
        
        # Selezione prioritaria per tipo
        priority_types = [PageType.HOMEPAGE, PageType.AUTHENTICATION, PageType.CONTACT, 
                         PageType.FORM, PageType.SEARCH]
        
        selected_count = 0
        max_selected = min(15, len(pages))  # Massimo 15 pagine selezionate di default
        
        # Prima selezione: tipi prioritari
        for page in pages:
            if selected_count >= max_selected:
                break
            if page.page_type in priority_types:
                page.selected_for_scan = True
                page.selection_reason = f"high_priority_{page.page_type.value}"
                selected_count += 1
        
        # Seconda selezione: riempi fino al limite con altre pagine
        for page in pages:
            if selected_count >= max_selected:
                break
            if not page.selected_for_scan and page.priority >= 50:
                page.selected_for_scan = True
                page.selection_reason = "balanced_selection"
                selected_count += 1
        
        logger.info(f"Selezione intelligente applicata: {selected_count}/{len(pages)} pagine")
    
    def _save_discovery_report(self, session_id: str) -> None:
        """
        Salva report discovery su file
        
        Args:
            session_id: ID della sessione
        """
        session = self.session_manager.get_discovery_session(session_id)
        if not session or not session.output_dir:
            return
        
        try:
            output_dir = Path(session.output_dir)
            report_path = output_dir / "discovery_report.json"
            
            report_data = {
                "session_id": session_id,
                "base_url": session.base_url,
                "discovery_date": time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": session.status.value,
                "config": session.config.to_dict(),
                "summary": {
                    "total_pages": len(session.discovered_pages),
                    "selected_pages": len([p for p in session.discovered_pages if p.selected_for_scan]),
                    "templates_detected": session.templates_detected,
                    "sitemap_urls": session.sitemap_urls_found,
                    "duration_seconds": (
                        session.completed_at - session.started_at
                        if session.completed_at and session.started_at else 0
                    )
                },
                "pages_by_type": {},
                "selected_pages": [],
                "all_pages": []
            }
            
            # Raggruppa per tipo
            for page in session.discovered_pages:
                page_type = page.page_type.value
                if page_type not in report_data["pages_by_type"]:
                    report_data["pages_by_type"][page_type] = []
                
                page_dict = page.to_dict()
                report_data["pages_by_type"][page_type].append(page_dict)
                report_data["all_pages"].append(page_dict)
                
                if page.selected_for_scan:
                    report_data["selected_pages"].append(page_dict)
            
            # Salva report
            import json
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Discovery report salvato: {report_path}")
            
        except Exception as e:
            logger.error(f"Errore salvataggio discovery report: {e}")
    
    def get_running_discoveries(self) -> List[str]:
        """
        Ottiene lista delle discovery in corso
        
        Returns:
            Lista di session_id delle discovery attive
        """
        return [
            session_id for session_id, thread in self._running_threads.items()
            if thread.is_alive()
        ]
    
    def cleanup_completed_threads(self) -> int:
        """
        Pulisce thread completati dalla memoria
        
        Returns:
            Numero di thread rimossi
        """
        to_remove = [
            session_id for session_id, thread in self._running_threads.items()
            if not thread.is_alive()
        ]
        
        for session_id in to_remove:
            del self._running_threads[session_id]
        
        return len(to_remove)
