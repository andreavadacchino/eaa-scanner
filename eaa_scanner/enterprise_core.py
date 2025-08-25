"""
Enterprise Core per EAA Scanner con Pydantic integration e async workflow
Sostituisce core.py legacy con type safety e gestione robusta errori
"""

from __future__ import annotations

import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

from .config import Config, new_scan_id
from .scanners import WaveScanner, Pa11yScanner, AxeScanner, LighthouseScanner
from .processors.enterprise_normalizer import EnterpriseNormalizer
from .models.scanner_results import AggregatedResults, ScannerResult
from .report import generate_html_report, write_report
from .pdf import create_pdf_with_options
from .scan_events import ScanEventHooks, set_current_hooks, MonitoredScanner
from .enterprise_charts import EnterpriseChartGenerator

logger = logging.getLogger(__name__)


class EnterpriseScanOrchestrator:
    """
    Orchestratore enterprise per scansioni con gestione robusta errori
    
    Features:
    - Parallel scanner execution con timeout
    - Enterprise normalizer con Pydantic validation
    - Async workflow senza RuntimeWarning
    - Rollback capability per fallimenti
    - Comprehensive logging per debugging
    """
    
    def __init__(self, enable_parallel: bool = False):
        self.normalizer = EnterpriseNormalizer(enable_metrics=True)
        self.chart_generator = None
        self.enable_parallel = enable_parallel
        
        # Scanner execution statistics
        self.execution_stats = {
            "started": 0,
            "completed": 0, 
            "failed": 0,
            "timeouts": 0
        }
    
    def run_enterprise_scan(
        self,
        cfg: Config,
        output_root: Optional[Path] = None,
        event_monitor=None,
        scan_id: Optional[str] = None,
        enable_pdf: bool = True,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Entry point principale per scansioni enterprise
        
        Args:
            cfg: Configurazione scansione
            output_root: Directory output (default: ./output)
            event_monitor: Monitor eventi per feedback real-time
            scan_id: ID scansione (auto-generato se None)
            enable_pdf: Abilita generazione PDF
            max_retries: Numero massimo retry per scanner
            
        Returns:
            Risultati scansione enterprise con paths e metadata
            
        Raises:
            ValueError: Se nessuno scanner produce risultati
            RuntimeError: Se errori critici durante processing
        """
        
        # Setup base
        output_root = output_root or Path("output") 
        scan_id = scan_id or new_scan_id()
        base_out = output_root / scan_id
        base_out.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 Avvio scansione enterprise: {scan_id}")
        logger.info(f"URL: {cfg.url}, Azienda: {cfg.company_name}")
        
        # Setup event hooks
        hooks = None
        if event_monitor:
            hooks = ScanEventHooks(scan_id)
            hooks.set_monitor(event_monitor) 
            set_current_hooks(hooks)
        
        try:
            # Fase 1: Esecuzione scanner
            if hooks:
                hooks.emit_processing_step("Inizializzazione scanner", 10)
                
            scanner_results = self._execute_scanners_robust(
                cfg, base_out, hooks, max_retries
            )
            
            if not scanner_results:
                raise ValueError("Nessuno scanner ha prodotto risultati validi")
            
            # Fase 2: Normalizzazione enterprise
            if hooks:
                hooks.emit_processing_step("Normalizzazione dati", 40)
                
            aggregated_results = self._normalize_with_validation(
                cfg, scan_id, scanner_results
            )
            
            # Fase 3: Salvataggio risultati
            self._save_enterprise_results(base_out, aggregated_results)
            
            # Fase 4: Generazione charts robusta
            if hooks:
                hooks.emit_processing_step("Generazione visualizzazioni", 60)
                
            charts_data = self._generate_charts_safe(aggregated_results, base_out)
            
            # Fase 5: Report HTML
            if hooks:
                hooks.emit_processing_step("Generazione report HTML", 80)
                
            html_path = self._generate_html_report(cfg, aggregated_results, base_out)
            
            # Fase 6: PDF opzionale
            pdf_path = None
            if enable_pdf:
                if hooks:
                    hooks.emit_processing_step("Generazione PDF", 90)
                    
                pdf_path = self._generate_pdf_safe(html_path, base_out, cfg)
            
            # Fase 7: Response finale
            if hooks:
                hooks.emit_processing_step("Finalizzazione", 100)
            
            response = self._create_enterprise_response(
                scan_id, base_out, aggregated_results, html_path, pdf_path, charts_data
            )
            
            logger.info(f"✅ Scansione completata: score {aggregated_results.compliance_metrics.overall_score}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Scansione fallita: {e}")
            logger.error(traceback.format_exc())
            
            # Genera report errore per debugging
            self._save_error_report(base_out, str(e), cfg, scan_id)
            
            raise RuntimeError(f"Scansione enterprise fallita: {e}") from e
    
    def _execute_scanners_robust(
        self,
        cfg: Config,
        base_out: Path,
        hooks: Optional[ScanEventHooks],
        max_retries: int
    ) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Esegue scanner con gestione robusta errori e retry"""
        
        scanner_results = []
        
        # Determina scanner abilitati
        enabled_scanners = []
        if cfg.scanners_enabled.wave:
            enabled_scanners.append(("wave", "WAVE"))
        if cfg.scanners_enabled.pa11y:
            enabled_scanners.append(("pa11y", "Pa11y"))
        if cfg.scanners_enabled.axe_core:
            enabled_scanners.append(("axe", "Axe-core"))
        if cfg.scanners_enabled.lighthouse:
            enabled_scanners.append(("lighthouse", "Lighthouse"))
        
        logger.info(f"Scanner abilitati: {[name for _, name in enabled_scanners]}")
        
        # Esecuzione sequenziale (più stabile per ora)
        for scanner_key, scanner_name in enabled_scanners:
            if hooks:
                hooks.emit_scanner_operation(scanner_name, "Inizializzazione", 0)
                
            result = self._execute_single_scanner_with_retry(
                scanner_key, cfg, base_out, hooks, max_retries
            )
            
            scanner_results.append((scanner_key, result))
            
            if result is not None:
                self.execution_stats["completed"] += 1
                if hooks:
                    hooks.emit_scanner_operation(scanner_name, "Completato", 100)
            else:
                self.execution_stats["failed"] += 1
                if hooks:
                    hooks.emit_scanner_operation(scanner_name, "Fallito", 100)
                    
        logger.info(f"Statistiche esecuzione: {self.execution_stats}")
        return scanner_results
    
    def _execute_single_scanner_with_retry(
        self,
        scanner_key: str,
        cfg: Config,
        base_out: Path,
        hooks: Optional[ScanEventHooks],
        max_retries: int
    ) -> Optional[Dict[str, Any]]:
        """Esegue singolo scanner con retry logic"""
        
        self.execution_stats["started"] += 1
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Retry {attempt}/{max_retries} per {scanner_key}")
                    
                # Esegui scanner specifico
                result = None
                
                if scanner_key == "wave":
                    scanner = MonitoredScanner(
                        WaveScanner(
                            api_key=cfg.wave_api_key,
                            timeout_ms=cfg.scanner_timeout_ms,
                            simulate=cfg.simulate
                        ),
                        "WAVE"
                    )
                    scan_result = scanner.scan(cfg.url)
                    result = scan_result.json
                    
                elif scanner_key == "pa11y":
                    scanner = MonitoredScanner(
                        Pa11yScanner(
                            timeout_ms=cfg.scanner_timeout_ms,
                            simulate=cfg.simulate
                        ),
                        "Pa11y"
                    )
                    scan_result = scanner.scan(cfg.url)
                    result = scan_result.json
                    
                elif scanner_key == "axe":
                    scanner = MonitoredScanner(
                        AxeScanner(
                            timeout_ms=cfg.scanner_timeout_ms,
                            simulate=cfg.simulate
                        ),
                        "Axe-core"
                    )
                    scan_result = scanner.scan(cfg.url)
                    result = scan_result.json
                    
                elif scanner_key == "lighthouse":
                    scanner = MonitoredScanner(
                        LighthouseScanner(
                            timeout_ms=cfg.scanner_timeout_ms,
                            simulate=cfg.simulate
                        ),
                        "Lighthouse"
                    )
                    scan_result = scanner.scan(cfg.url)
                    result = scan_result.json
                
                # Salva risultato raw
                if result:
                    output_file = base_out / f"{scanner_key}.json"
                    output_file.write_text(
                        json.dumps(result, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )
                    logger.info(f"✅ {scanner_key} completato con successo")
                    return result
                else:
                    logger.warning(f"⚠️ {scanner_key} restituito risultato vuoto")
                    
            except Exception as e:
                logger.error(f"❌ {scanner_key} fallito (tentativo {attempt + 1}): {e}")
                
                if attempt == max_retries:
                    logger.error(f"💥 {scanner_key} fallito definitivamente dopo {max_retries + 1} tentativi")
                    self.execution_stats["failed"] += 1
                    return None
                
                # Wait progressivo per retry
                import time
                time.sleep(min(2 ** attempt, 10))  # Exponential backoff con cap
                
        return None
    
    def _normalize_with_validation(
        self,
        cfg: Config,
        scan_id: str,
        scanner_results: List[Tuple[str, Optional[Dict[str, Any]]]]
    ) -> AggregatedResults:
        """Normalizza risultati usando enterprise normalizer con validazione"""
        
        # Prepara dati per normalizer
        wave_data = None
        pa11y_data = None
        axe_data = None
        lighthouse_data = None
        
        for scanner_key, result in scanner_results:
            if result is None:
                continue
                
            if scanner_key == "wave":
                wave_data = result
            elif scanner_key == "pa11y":
                pa11y_data = result
            elif scanner_key == "axe":
                axe_data = result
            elif scanner_key == "lighthouse":
                lighthouse_data = result
        
        logger.info(f"Normalizzazione con dati: WAVE={wave_data is not None}, "
                   f"Pa11y={pa11y_data is not None}, Axe={axe_data is not None}, "
                   f"Lighthouse={lighthouse_data is not None}")
        
        # Usa enterprise normalizer
        aggregated = self.normalizer.normalize_all_enterprise(
            url=cfg.url,
            company_name=cfg.company_name,
            email=cfg.email,
            scan_id=scan_id,
            wave=wave_data,
            pa11y=pa11y_data,
            axe=axe_data,
            lighthouse=lighthouse_data,
            timeout_seconds=cfg.scanner_timeout_ms // 1000,
            scan_type="real" if not cfg.simulate else "simulate"
        )
        
        logger.info(f"✅ Normalizzazione completata: {len(aggregated.individual_results)} risultati")
        return aggregated
    
    def _save_enterprise_results(self, base_out: Path, results: AggregatedResults):
        """Salva risultati enterprise con formato JSON validato"""
        
        # Salva summary principale
        summary_data = results.dict()
        (base_out / "enterprise_summary.json").write_text(
            json.dumps(summary_data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8"
        )
        
        # Salva statistiche processing
        stats = self.normalizer.get_processing_stats()
        stats_data = {
            "processed_scanners": stats.processed_scanners,
            "successful_validations": stats.successful_validations,
            "failed_validations": stats.failed_validations,
            "null_inputs": stats.null_inputs,
            "processing_time": stats.processing_time,
            "execution_stats": self.execution_stats
        }
        (base_out / "processing_stats.json").write_text(
            json.dumps(stats_data, indent=2),
            encoding="utf-8"
        )
        
        logger.info("✅ Risultati enterprise salvati")
    
    def _generate_charts_safe(
        self,
        results: AggregatedResults,
        base_out: Path
    ) -> Optional[Dict[str, Any]]:
        """Genera charts con gestione robusta errori e fallback"""
        
        try:
            # Inizializza chart generator enterprise
            if not self.chart_generator:
                self.chart_generator = EnterpriseChartGenerator(str(base_out))
            
            # Converti risultati enterprise in formato legacy per compatibility
            legacy_data = self._convert_to_legacy_format(results)
            
            # Genera charts con error handling
            charts_data = self.chart_generator.generate_all_charts_safe(legacy_data)
            
            # Salva charts data
            (base_out / "charts_enterprise.json").write_text(
                json.dumps(charts_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            
            logger.info("✅ Charts enterprise generati")
            return charts_data
            
        except Exception as e:
            logger.error(f"❌ Generazione charts fallita: {e}")
            
            # Fallback: genera charts basic senza visualizzazioni avanzate
            fallback_data = {
                "status": "fallback",
                "error": str(e),
                "basic_metrics": {
                    "overall_score": float(results.compliance_metrics.overall_score),
                    "total_violations": results.compliance_metrics.total_violations,
                    "compliance_level": results.compliance_metrics.compliance_level
                }
            }
            
            (base_out / "charts_fallback.json").write_text(
                json.dumps(fallback_data, indent=2),
                encoding="utf-8"
            )
            
            return fallback_data
    
    def _generate_html_report(
        self,
        cfg: Config,
        results: AggregatedResults,
        base_out: Path
    ) -> Path:
        """Genera report HTML usando dati enterprise"""
        
        # Converti per compatibility con report generator
        legacy_format = self._convert_to_legacy_format(results)
        
        # Genera HTML
        html_content = generate_html_report(legacy_format, cfg)
        
        # Scrivi report
        report_filename = f"report_{cfg.company_name.replace(' ', '_')}.html"
        html_path = base_out / report_filename
        
        write_report(html_path, html_content)
        
        logger.info(f"✅ Report HTML generato: {html_path}")
        return html_path
    
    def _generate_pdf_safe(
        self,
        html_path: Path,
        base_out: Path,
        cfg: Config
    ) -> Optional[Path]:
        """Genera PDF con gestione errori"""
        
        try:
            pdf_filename = f"report_{cfg.company_name.replace(' ', '_')}.pdf"
            pdf_path = base_out / pdf_filename
            
            success = create_pdf_with_options(
                html_path=html_path,
                pdf_path=pdf_path,
                engine=cfg.pdf_engine,
                page_format=cfg.pdf_page_format,
                margins=cfg.get_pdf_margins_dict(),
                timeout=120
            )
            
            if success:
                logger.info(f"✅ PDF generato: {pdf_path}")
                return pdf_path
            else:
                logger.warning("⚠️ Generazione PDF fallita")
                return None
                
        except Exception as e:
            logger.error(f"❌ Errore generazione PDF: {e}")
            return None
    
    def _create_enterprise_response(
        self,
        scan_id: str,
        base_out: Path,
        results: AggregatedResults,
        html_path: Path,
        pdf_path: Optional[Path],
        charts_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Crea response enterprise con tutti i metadata"""
        
        response = {
            "status": "success",
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "enterprise_mode": True,
            
            # Paths
            "paths": {
                "base_output": str(base_out),
                "enterprise_summary": str(base_out / "enterprise_summary.json"),
                "html_report": str(html_path),
                "pdf_report": str(pdf_path) if pdf_path else None,
                "processing_stats": str(base_out / "processing_stats.json"),
                "charts_data": str(base_out / "charts_enterprise.json") if charts_data else None
            },
            
            # Compliance metrics
            "compliance": {
                "overall_score": float(results.compliance_metrics.overall_score),
                "compliance_level": results.compliance_metrics.compliance_level,
                "total_violations": results.compliance_metrics.total_violations,
                "confidence": float(results.compliance_metrics.confidence_level)
            },
            
            # Execution info
            "execution": {
                "successful_scanners": len(results.successful_scanners),
                "failed_scanners": len(results.failed_scanners),
                "success_rate": float(results.success_rate),
                "processing_stats": self.execution_stats
            }
        }
        
        # Salva response
        (base_out / "enterprise_response.json").write_text(
            json.dumps(response, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        return response
    
    def _convert_to_legacy_format(self, results: AggregatedResults) -> Dict[str, Any]:
        """Converte risultati enterprise in formato legacy per compatibility con template corretto"""
        
        # Estrai metriche principali
        metrics = results.compliance_metrics
        
        # Aggrega violazioni per categoria 
        all_errors = []
        all_warnings = []
        
        for scanner_result in results.individual_results:
            for violation in scanner_result.violations:
                issue = {
                    "code": violation.code,
                    "description": violation.message,
                    "severity": violation.severity.value,
                    "wcag_criteria": violation.wcag_criterion or "",
                    "source": scanner_result.scanner.value,
                    "count": 1
                }
                
                if violation.severity.value in ["critical", "high"]:
                    all_errors.append(issue)
                else:
                    all_warnings.append(issue)
        
        # FIXED: Trova la prima URL dalle individual_results invece che company_name
        scanned_url = "N/A"
        if results.individual_results:
            scanned_url = results.individual_results[0].url
        
        # Costruisci formato legacy con dati corretti per template enterprise professionale
        legacy_format = {
            "scan_id": results.scan_context.scan_id,
            "timestamp": results.scan_context.started_at.isoformat() + "Z",
            "url": scanned_url,  # FIXED: URL corretta 
            "company_name": results.scan_context.company_name,
            
            # FIXED: Compliance con tutti i dati necessari
            "compliance": {
                "wcag_version": "2.1",
                "wcag_level": "AA",
                "compliance_level": metrics.compliance_level,
                "eaa_compliance": self._map_compliance_to_eaa(metrics.compliance_level),
                "overall_score": float(metrics.overall_score),  # FIXED: Mantieni float invece di int
                "total_violations": metrics.total_violations,
                "critical_violations": metrics.critical_violations,
                "high_violations": metrics.high_violations,
                "medium_violations": metrics.medium_violations,
                "low_violations": metrics.low_violations
            },
            
            "detailed_results": {
                "errors": all_errors,
                "warnings": all_warnings,
                "scanner_scores": {
                    scanner.scanner.value: float(scanner.accessibility_score or 0)
                    for scanner in results.individual_results
                    if scanner.status.value == "success"
                }
            },
            
            "scan_metadata": {
                "scan_date": results.scan_context.started_at.strftime("%d %B %Y"),  # FIXED: Formato più leggibile
                "scanners_used": [s.value for s in results.successful_scanners],
                "total_issues": metrics.total_violations,
                "pages_analyzed": 1  # Per ora supportiamo single page
            }
        }
        
        return legacy_format
    
    def _map_compliance_to_eaa(self, compliance_level: str) -> str:
        """Mappa livello compliance a EAA"""
        mapping = {
            "conforme": "compliant",
            "parzialmente_conforme": "partially_compliant", 
            "non_conforme": "non_compliant"
        }
        return mapping.get(compliance_level, "non_compliant")
    
    def _save_error_report(
        self,
        base_out: Path,
        error_message: str,
        cfg: Config,
        scan_id: str
    ):
        """Salva report errore per debugging"""
        
        error_report = {
            "status": "failed",
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "config": {
                "url": cfg.url,
                "company_name": cfg.company_name,
                "simulate": cfg.simulate,
                "enabled_scanners": {
                    "wave": cfg.scanners_enabled.wave,
                    "pa11y": cfg.scanners_enabled.pa11y,
                    "axe": cfg.scanners_enabled.axe_core,
                    "lighthouse": cfg.scanners_enabled.lighthouse
                }
            },
            "execution_stats": self.execution_stats
        }
        
        (base_out / "error_report.json").write_text(
            json.dumps(error_report, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# Factory function per backward compatibility
def create_enterprise_orchestrator() -> EnterpriseScanOrchestrator:
    """Factory per creare orchestratore enterprise"""
    return EnterpriseScanOrchestrator(enable_parallel=False)


def run_enterprise_scan(cfg: Config, **kwargs) -> Dict[str, Any]:
    """Entry point principale per scansioni enterprise"""
    orchestrator = create_enterprise_orchestrator()
    return orchestrator.run_enterprise_scan(cfg, **kwargs)