"""
Servizio per gestione fase SCANNING
Orchestra esecuzione scanner accessibilità su pagine selezionate
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
import threading
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..scanners import WaveScanner, Pa11yScanner, AxeScanner, LighthouseScanner
from ..processors import process_wave, process_pa11y, normalize_all
from ..report import generate_html_report, write_report
from ..pdf import html_to_pdf
from .models import (
    ScanSession, DiscoveredPage, AccessibilityIssue, SessionStatus, SeverityLevel,
    ScanConfiguration
)
from .session_manager import SessionManager, get_session_manager

logger = logging.getLogger(__name__)


class ScanService:
    """
    Servizio per orchestrare scanning di accessibilità
    Supporta esecuzione parallela di multiple scanner su pagine selezionate
    """
    
    def __init__(self, session_manager: Optional[SessionManager] = None,
                 output_dir: Path = None):
        """
        Inizializza ScanService
        
        Args:
            session_manager: Manager per gestione sessioni
            output_dir: Directory base per output
        """
        self.session_manager = session_manager or get_session_manager()
        self.output_dir = output_dir or Path("output")
        
        # Thread pool per esecuzione asincrona
        self._running_threads: Dict[str, threading.Thread] = {}
        
        logger.info("ScanService inizializzato")
    
    def start_scan(self, discovery_session_id: str, selected_urls: List[str],
                  company_name: str, email: str, config: Optional[ScanConfiguration] = None,
                  progress_callback: Optional[Callable] = None) -> Optional[str]:
        """
        Avvia processo di scanning asincrono
        
        Args:
            discovery_session_id: ID sessione discovery di riferimento
            selected_urls: URLs delle pagine da scansionare
            company_name: Nome azienda per report
            email: Email di contatto
            config: Configurazione scan (opzionale)
            progress_callback: Callback per aggiornamenti progress
            
        Returns:
            ID della sessione scan creata o None se errore
        """
        # Crea sessione scan
        scan_session = self.session_manager.create_scan_session(
            discovery_session_id=discovery_session_id,
            selected_urls=selected_urls,
            company_name=company_name,
            email=email,
            config=config.to_dict() if config else None
        )
        
        if not scan_session:
            logger.error(f"Impossibile creare scan session per discovery {discovery_session_id}")
            return None
        
        # Imposta directory output
        session_output_dir = self.output_dir / "scans" / scan_session.session_id
        session_output_dir.mkdir(parents=True, exist_ok=True)
        scan_session.output_dir = str(session_output_dir)
        
        self.session_manager.update_scan_session(
            scan_session.session_id,
            output_dir=str(session_output_dir)
        )
        
        logger.info(f"Avvio scan per {len(selected_urls)} pagine, session: {scan_session.session_id}")
        
        # Avvia thread worker
        thread = threading.Thread(
            target=self._scan_worker,
            args=(scan_session.session_id, progress_callback),
            daemon=True,
            name=f"scan-{scan_session.session_id[:8]}"
        )
        
        self._running_threads[scan_session.session_id] = thread
        thread.start()
        
        return scan_session.session_id
    
    def get_scan_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene status corrente di sessione scan
        
        Args:
            session_id: ID della sessione
            
        Returns:
            Dizionario con status e metadati o None se non trovata
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            return None
        
        # Determina se thread è ancora attivo
        thread = self._running_threads.get(session_id)
        is_running = thread is not None and thread.is_alive()
        
        return {
            "session_id": session_id,
            "discovery_session_id": session.discovery_session_id,
            "company_name": session.company_name,
            "email": session.email,
            "status": session.status.value,
            "progress_percent": session.progress_percent,
            "progress_message": session.progress_message,
            "current_page_url": session.current_page_url,
            "current_scanner": session.current_scanner,
            "pages_scanned": session.pages_scanned,
            "total_pages": session.total_pages,
            "total_issues": session.total_issues,
            "critical_issues": session.critical_issues,
            "high_issues": session.high_issues,
            "medium_issues": session.medium_issues,
            "low_issues": session.low_issues,
            "overall_score": session.overall_score,
            "compliance_level": session.compliance_level,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "is_thread_active": is_running,
            "errors": session.errors,
            "warnings": session.warnings,
            "log_messages": session.log_messages[-20:],  # Ultimi 20 messaggi
            "config": session.config.to_dict(),
            "reports": {
                "html_available": bool(session.report_html_path and Path(session.report_html_path).exists()),
                "pdf_available": bool(session.report_pdf_path and Path(session.report_pdf_path).exists()),
                "html_path": session.report_html_path,
                "pdf_path": session.report_pdf_path
            }
        }
    
    def get_scan_results(self, session_id: str, include_issues: bool = True) -> Optional[Dict[str, Any]]:
        """
        Ottiene risultati completi di scan session
        
        Args:
            session_id: ID della sessione
            include_issues: Se includere lista dettagliata problemi
            
        Returns:
            Dizionario con risultati completi o None se non trovata
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            return None
        
        # Raggruppa issues per severità e WCAG
        issues_by_severity = {}
        issues_by_wcag = {}
        issues_by_page = {}
        
        for issue in session.issues:
            # Per severità
            severity = issue.severity.value
            if severity not in issues_by_severity:
                issues_by_severity[severity] = []
            if include_issues:
                issues_by_severity[severity].append(issue.to_dict())
            
            # Per livello WCAG
            wcag_level = issue.wcag_level
            if wcag_level not in issues_by_wcag:
                issues_by_wcag[wcag_level] = 0
            issues_by_wcag[wcag_level] += 1
            
            # Per pagina
            page_url = issue.page_url
            if page_url not in issues_by_page:
                issues_by_page[page_url] = 0
            issues_by_page[page_url] += 1
        
        # Statistiche per scanner
        scanners_used = list(set(issue.source_scanner for issue in session.issues))
        
        result = {
            "session_id": session_id,
            "discovery_session_id": session.discovery_session_id,
            "company_name": session.company_name,
            "email": session.email,
            "status": session.status.value,
            "pages_scanned": session.pages_scanned,
            "total_pages": session.total_pages,
            "scanned_pages": [p.to_dict() for p in session.selected_pages],
            "compliance": {
                "overall_score": session.overall_score,
                "compliance_level": session.compliance_level,
                "total_issues": session.total_issues,
                "critical_issues": session.critical_issues,
                "high_issues": session.high_issues,
                "medium_issues": session.medium_issues,
                "low_issues": session.low_issues
            },
            "statistics": {
                "issues_by_severity": {k: len(v) if isinstance(v, list) else v for k, v in issues_by_severity.items()},
                "issues_by_wcag_level": issues_by_wcag,
                "issues_by_page": issues_by_page,
                "scanners_used": scanners_used,
                "pages_with_issues": len([url for url, count in issues_by_page.items() if count > 0])
            },
            "created_at": session.created_at,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "duration_seconds": (
                session.completed_at - session.created_at
                if session.completed_at else time.time() - session.created_at
            ),
            "config": session.config.to_dict(),
            "reports": {
                "html_path": session.report_html_path,
                "pdf_path": session.report_pdf_path,
                "html_available": bool(session.report_html_path and Path(session.report_html_path).exists()),
                "pdf_available": bool(session.report_pdf_path and Path(session.report_pdf_path).exists())
            }
        }
        
        if include_issues:
            result["issues_by_severity"] = issues_by_severity
            result["all_issues"] = [issue.to_dict() for issue in session.issues]
        
        return result
    
    def cancel_scan(self, session_id: str) -> bool:
        """
        Cancella scan in corso
        
        Args:
            session_id: ID della sessione da cancellare
            
        Returns:
            True se cancellata con successo
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            return False
        
        # Segnala cancellazione
        self.session_manager.set_scan_status(
            session_id,
            SessionStatus.CANCELLED,
            message="Scan cancellata dall'utente"
        )
        
        logger.info(f"Scan {session_id} cancellata")
        return True
    
    def generate_pdf_report(self, session_id: str) -> Optional[str]:
        """
        Genera report PDF da HTML esistente
        
        Args:
            session_id: ID della sessione
            
        Returns:
            Path del PDF generato o None se errore
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session or not session.report_html_path:
            return None
        
        html_path = Path(session.report_html_path)
        if not html_path.exists():
            return None
        
        pdf_path = html_path.with_suffix('.pdf')
        
        try:
            success = html_to_pdf(html_path, pdf_path)
            if success and pdf_path.exists():
                # Aggiorna sessione con path PDF
                self.session_manager.update_scan_session(
                    session_id,
                    report_pdf_path=str(pdf_path)
                )
                logger.info(f"PDF generato per scan {session_id}: {pdf_path}")
                return str(pdf_path)
            else:
                logger.error(f"Generazione PDF fallita per scan {session_id}")
                return None
        except Exception as e:
            logger.error(f"Errore generazione PDF per scan {session_id}: {e}")
            return None
    
    def _scan_worker(self, session_id: str, progress_callback: Optional[Callable] = None) -> None:
        """
        Worker thread per esecuzione scan
        
        Args:
            session_id: ID della sessione
            progress_callback: Callback per progress updates
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            logger.error(f"Scan session {session_id} non trovata in worker")
            return
        
        try:
            # Avvia sessione
            self.session_manager.set_scan_status(
                session_id,
                SessionStatus.RUNNING,
                message="Inizializzazione scanner..."
            )
            
            logger.info(f"Scan worker avviato per {len(session.selected_pages)} pagine")
            
            # Crea callback progress interno
            def internal_progress_callback(data: Dict[str, Any]) -> None:
                # Controlla se sessione è stata cancellata
                current_session = self.session_manager.get_scan_session(session_id)
                if not current_session or current_session.status == SessionStatus.CANCELLED:
                    return
                
                # Chiama callback esterno se presente
                if progress_callback:
                    try:
                        progress_callback({
                            'session_id': session_id,
                            'type': 'scan_progress',
                            **data
                        })
                    except Exception as e:
                        logger.warning(f"Errore progress callback: {e}")
            
            # Esegui scansione
            all_results = self._execute_scan(session_id, internal_progress_callback)
            
            # Controlla se cancellato durante esecuzione
            current_session = self.session_manager.get_scan_session(session_id)
            if not current_session or current_session.status == SessionStatus.CANCELLED:
                logger.info(f"Scan {session_id} cancellata durante esecuzione")
                return
            
            # Processa risultati e genera report
            self._process_scan_results(session_id, all_results)
            
            # Completa con successo
            self.session_manager.set_scan_status(
                session_id,
                SessionStatus.COMPLETED,
                message=f"Scan completata: {current_session.total_issues} problemi trovati"
            )
            
            logger.info(f"Scan {session_id} completata con successo")
            
        except Exception as e:
            logger.error(f"Errore in scan worker {session_id}: {e}", exc_info=True)
            self.session_manager.set_scan_status(
                session_id,
                SessionStatus.FAILED,
                error=f"Errore worker: {str(e)}"
            )
        finally:
            # Cleanup thread reference
            if session_id in self._running_threads:
                del self._running_threads[session_id]
    
    def _execute_scan(self, session_id: str, progress_callback: Callable) -> List[Dict[str, Any]]:
        """
        Esegue scansione di tutte le pagine selezionate
        
        Args:
            session_id: ID della sessione
            progress_callback: Callback per progress
            
        Returns:
            Lista risultati per ogni pagina
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            return []
        
        config = session.config
        all_results = []
        
        # Progresso iniziale
        self.session_manager.update_scan_progress(
            session_id, 0, message="Avvio scansione pagine..."
        )
        
        # Esegui scan per ogni pagina
        for i, page in enumerate(session.selected_pages):
            # Controlla cancellazione
            current_session = self.session_manager.get_scan_session(session_id)
            if not current_session or current_session.status == SessionStatus.CANCELLED:
                break
            
            logger.info(f"Scansione pagina {i+1}/{len(session.selected_pages)}: {page.url}")
            
            # Aggiorna progresso
            progress_percent = int((i / len(session.selected_pages)) * 90)  # 90% per scan, 10% per report
            self.session_manager.update_scan_progress(
                session_id, 
                pages_scanned=i,
                current_page=page.url,
                message=f"Scansione {page.title or page.url}..."
            )
            
            # Esegui scanner su questa pagina
            page_results = self._scan_single_page(session_id, page, config, progress_callback)
            
            if page_results:
                all_results.append(page_results)
                
                # Processa problemi trovati
                self._process_page_issues(session_id, page, page_results)
            
            # Aggiorna progresso pagina completata
            self.session_manager.update_scan_progress(
                session_id,
                pages_scanned=i+1,
                current_page="",
                current_scanner=""
            )
            
            # Piccola pausa tra pagine
            time.sleep(0.5)
        
        return all_results
    
    def _scan_single_page(self, session_id: str, page: DiscoveredPage, 
                         config: ScanConfiguration, progress_callback: Callable) -> Optional[Dict[str, Any]]:
        """
        Esegue scansione di una singola pagina con tutti gli scanner abilitati
        
        Args:
            session_id: ID sessione
            page: Pagina da scansionare
            config: Configurazione scan
            progress_callback: Callback progresso
            
        Returns:
            Risultati normalizzati per la pagina
        """
        results = {
            'url': page.url,
            'page_title': page.title,
            'page_type': page.page_type.value,
            'scanners_results': {}
        }
        
        # Directory per risultati pagina
        session = self.session_manager.get_scan_session(session_id)
        if session and session.output_dir:
            page_dir = Path(session.output_dir) / f"page_{page.url.replace('://', '_').replace('/', '_')[:50]}"
            page_dir.mkdir(exist_ok=True)
        else:
            page_dir = None
        
        # Esegui scanner in parallelo se configurato
        if config.parallel_scans > 1:
            results['scanners_results'] = self._run_scanners_parallel(page, config, session_id, page_dir)
        else:
            results['scanners_results'] = self._run_scanners_sequential(page, config, session_id, page_dir)
        
        return results
    
    def _run_scanners_sequential(self, page: DiscoveredPage, config: ScanConfiguration,
                               session_id: str, page_dir: Optional[Path]) -> Dict[str, Any]:
        """
        Esegue scanner in sequenza
        
        Args:
            page: Pagina da scansionare
            config: Configurazione
            session_id: ID sessione
            page_dir: Directory output per pagina
            
        Returns:
            Risultati per scanner
        """
        scanners_results = {}
        
        # WAVE Scanner
        if config.scanners_enabled.get('wave', False):
            try:
                self.session_manager.update_scan_progress(
                    session_id, current_scanner="WAVE"
                )
                
                wave = WaveScanner(
                    api_key=config.wave_api_key,
                    timeout_ms=config.scanner_timeout_ms,
                    simulate=config.simulate
                )
                wave_result = wave.scan(page.url)
                scanners_results['wave'] = process_wave(wave_result.json)
                
                # Salva risultato raw
                if page_dir:
                    import json
                    with open(page_dir / "wave.json", 'w', encoding='utf-8') as f:
                        json.dump(wave_result.json, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"WAVE scan completato per {page.url}")
                
            except Exception as e:
                logger.warning(f"WAVE scan fallito per {page.url}: {e}")
                scanners_results['wave'] = None
        
        # Pa11y Scanner
        if config.scanners_enabled.get('pa11y', False):
            try:
                self.session_manager.update_scan_progress(
                    session_id, current_scanner="Pa11y"
                )
                
                pa11y = Pa11yScanner(
                    timeout_ms=config.scanner_timeout_ms,
                    simulate=config.simulate
                )
                pa11y_result = pa11y.scan(page.url)
                scanners_results['pa11y'] = process_pa11y(pa11y_result.json)
                
                # Salva risultato raw
                if page_dir:
                    import json
                    with open(page_dir / "pa11y.json", 'w', encoding='utf-8') as f:
                        json.dump(pa11y_result.json, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Pa11y scan completato per {page.url}")
                
            except Exception as e:
                logger.warning(f"Pa11y scan fallito per {page.url}: {e}")
                scanners_results['pa11y'] = None
        
        # Axe Scanner
        if config.scanners_enabled.get('axe_core', False):
            try:
                self.session_manager.update_scan_progress(
                    session_id, current_scanner="Axe-core"
                )
                
                axe = AxeScanner(
                    timeout_ms=config.scanner_timeout_ms,
                    simulate=config.simulate
                )
                axe_result = axe.scan(page.url)
                scanners_results['axe'] = axe_result.json
                
                # Salva risultato raw
                if page_dir:
                    import json
                    with open(page_dir / "axe.json", 'w', encoding='utf-8') as f:
                        json.dump(axe_result.json, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Axe scan completato per {page.url}")
                
            except Exception as e:
                logger.warning(f"Axe scan fallito per {page.url}: {e}")
                scanners_results['axe'] = None
        
        # Lighthouse Scanner
        if config.scanners_enabled.get('lighthouse', False):
            try:
                self.session_manager.update_scan_progress(
                    session_id, current_scanner="Lighthouse"
                )
                
                lighthouse = LighthouseScanner(
                    timeout_ms=config.scanner_timeout_ms,
                    simulate=config.simulate
                )
                lighthouse_result = lighthouse.scan(page.url)
                scanners_results['lighthouse'] = lighthouse_result.json
                
                # Salva risultato raw
                if page_dir:
                    import json
                    with open(page_dir / "lighthouse.json", 'w', encoding='utf-8') as f:
                        json.dump(lighthouse_result.json, f, indent=2, ensure_ascii=False)
                
                logger.debug(f"Lighthouse scan completato per {page.url}")
                
            except Exception as e:
                logger.warning(f"Lighthouse scan fallito per {page.url}: {e}")
                scanners_results['lighthouse'] = None
        
        return scanners_results
    
    def _run_scanners_parallel(self, page: DiscoveredPage, config: ScanConfiguration,
                             session_id: str, page_dir: Optional[Path]) -> Dict[str, Any]:
        """
        Esegue scanner in parallelo (implementazione futura)
        
        Args:
            page: Pagina da scansionare
            config: Configurazione
            session_id: ID sessione
            page_dir: Directory output
            
        Returns:
            Risultati per scanner
        """
        # Per ora fallback a sequenziale
        # TODO: Implementare esecuzione parallela con ThreadPoolExecutor
        logger.warning("Esecuzione parallela non ancora implementata, uso sequenziale")
        return self._run_scanners_sequential(page, config, session_id, page_dir)
    
    def _process_page_issues(self, session_id: str, page: DiscoveredPage, 
                           page_results: Dict[str, Any]) -> None:
        """
        Processa e converte problemi di una pagina in AccessibilityIssue
        
        Args:
            session_id: ID sessione
            page: Pagina scansionata
            page_results: Risultati scanner per la pagina
        """
        scanner_results = page_results.get('scanners_results', {})
        
        # Normalizza risultati usando il processore esistente
        try:
            normalized = normalize_all(
                url=page.url,
                company_name="",  # Non necessario per singola pagina
                wave=scanner_results.get('wave'),
                pa11y=scanner_results.get('pa11y'),
                axe=scanner_results.get('axe'),
                lighthouse=scanner_results.get('lighthouse')
            )
            
            # Estrai problemi normalizzati
            detailed_results = normalized.get('detailed_results', {})
            
            # Processa errori (critical/high)
            for error in detailed_results.get('errors', []):
                issue = AccessibilityIssue(
                    code=error.get('code', 'unknown'),
                    description=error.get('description', ''),
                    severity=SeverityLevel.CRITICAL if error.get('severity') == 'critical' else SeverityLevel.HIGH,
                    wcag_criteria=error.get('wcag_criteria', ''),
                    wcag_level=error.get('wcag_level', 'A'),
                    selector=error.get('selector', ''),
                    context=error.get('context', ''),
                    help_url=error.get('help_url', ''),
                    page_url=page.url,
                    page_title=page.title,
                    source_scanner=error.get('source', 'unknown')
                )
                self.session_manager.add_scan_issue(session_id, issue)
            
            # Processa warning (medium/low)
            for warning in detailed_results.get('warnings', []):
                issue = AccessibilityIssue(
                    code=warning.get('code', 'unknown'),
                    description=warning.get('description', ''),
                    severity=SeverityLevel.MEDIUM if warning.get('severity') == 'medium' else SeverityLevel.LOW,
                    wcag_criteria=warning.get('wcag_criteria', ''),
                    wcag_level=warning.get('wcag_level', 'A'),
                    selector=warning.get('selector', ''),
                    context=warning.get('context', ''),
                    help_url=warning.get('help_url', ''),
                    page_url=page.url,
                    page_title=page.title,
                    source_scanner=warning.get('source', 'unknown')
                )
                self.session_manager.add_scan_issue(session_id, issue)
        
        except Exception as e:
            logger.error(f"Errore processamento problemi per {page.url}: {e}")
    
    def _process_scan_results(self, session_id: str, all_results: List[Dict[str, Any]]) -> None:
        """
        Processa risultati finali e genera report
        
        Args:
            session_id: ID sessione
            all_results: Risultati di tutte le pagine
        """
        session = self.session_manager.get_scan_session(session_id)
        if not session:
            return
        
        session.add_log("Generazione report finale...")
        
        # Aggiorna progresso per report generation
        self.session_manager.update_scan_progress(
            session_id,
            pages_scanned=session.total_pages,
            current_page="",
            current_scanner="",
            message="Generazione report HTML..."
        )
        
        try:
            # Crea dati aggregati per report usando struttura esistente
            aggregated_data = self._create_aggregated_data(session, all_results)
            
            # Genera report HTML
            html_report = generate_html_report(aggregated_data)
            
            # Salva report
            if session.output_dir:
                output_dir = Path(session.output_dir)
                report_filename = f"report_{session.company_name.replace(' ', '_')}.html"
                report_path = write_report(output_dir / report_filename, html_report)
                
                # Aggiorna sessione
                self.session_manager.update_scan_session(
                    session_id,
                    report_html_path=str(report_path)
                )
                
                session.add_log(f"Report HTML salvato: {report_path}")
                
                # Salva anche dati aggregati
                import json
                with open(output_dir / "scan_summary.json", 'w', encoding='utf-8') as f:
                    json.dump(aggregated_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Errore generazione report per scan {session_id}: {e}")
            session.add_error(f"Errore generazione report: {str(e)}")
    
    def _create_aggregated_data(self, session: ScanSession, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crea dati aggregati compatibili con il sistema di report esistente
        
        Args:
            session: Sessione scan
            all_results: Risultati di tutte le pagine
            
        Returns:
            Dati aggregati per report
        """
        # Converti issues in formato compatibile
        errors = []
        warnings = []
        
        for issue in session.issues:
            issue_dict = {
                'code': issue.code,
                'description': issue.description,
                'severity': issue.severity.value,
                'wcag_criteria': issue.wcag_criteria,
                'wcag_level': issue.wcag_level,
                'selector': issue.selector,
                'context': issue.context,
                'help_url': issue.help_url,
                'page_url': issue.page_url,
                'source': issue.source_scanner
            }
            
            if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                errors.append(issue_dict)
            else:
                warnings.append(issue_dict)
        
        return {
            'scan_id': session.session_id,
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'url': session.selected_pages[0].url if session.selected_pages else '',
            'company_name': session.company_name,
            'email': session.email,
            'compliance': {
                'overall_score': session.overall_score,
                'compliance_level': session.compliance_level
            },
            'detailed_results': {
                'errors': errors,
                'warnings': warnings,
                'notices': []  # Non gestiamo notices per ora
            },
            'pages_scanned': session.pages_scanned,
            'multi_page_scan': session.total_pages > 1,
            'selected_pages': [p.to_dict() for p in session.selected_pages],
            'scan_config': session.config.to_dict()
        }
    
    def get_running_scans(self) -> List[str]:
        """
        Ottiene lista delle scan in corso
        
        Returns:
            Lista di session_id delle scan attive
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
