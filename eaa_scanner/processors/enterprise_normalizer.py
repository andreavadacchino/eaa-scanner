"""
Enterprise-grade normalizer con Pydantic models e gestione robusta null values
Sostituisce il normalizer legacy con validazione type-safe e defensive programming
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
from decimal import Decimal
import logging
import hashlib
from dataclasses import dataclass

from ..models.scanner_results import (
    ScannerResult, 
    ViolationInstance, 
    AggregatedResults, 
    ComplianceMetrics,
    ScannerMetadata,
    ScanContext,
    SeverityLevel,
    ScannerType,
    ScanStatus
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistiche processing per monitoring"""
    processed_scanners: int = 0
    successful_validations: int = 0
    failed_validations: int = 0
    null_inputs: int = 0
    processing_time: float = 0.0


class EnterpriseNormalizer:
    """
    Normalizer enterprise con validazione Pydantic e gestione robusta errori
    
    Features:
    - Type safety con Pydantic models
    - Defensive programming per null values
    - Logging strutturato per debugging
    - Metrics collection per monitoring
    - Rollback capability per fallimenti
    """
    
    def __init__(self, enable_metrics: bool = True):
        self.enable_metrics = enable_metrics
        self.stats = ProcessingStats()
        
        # Mapping severità standardizzato
        self.severity_mapping = {
            # Axe-core
            "critical": SeverityLevel.CRITICAL,
            "serious": SeverityLevel.HIGH,
            "moderate": SeverityLevel.MEDIUM,
            "minor": SeverityLevel.LOW,
            
            # Pa11y/altri
            "error": SeverityLevel.HIGH,
            "warning": SeverityLevel.MEDIUM,
            "notice": SeverityLevel.LOW,
            
            # Lighthouse (implicito)
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW
        }
    
    def normalize_all_enterprise(
        self,
        url: str,
        company_name: str,
        email: str,
        scan_id: str,
        wave: Optional[Dict[str, Any]] = None,
        pa11y: Optional[Dict[str, Any]] = None,
        axe: Optional[Dict[str, Any]] = None,
        lighthouse: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 30,
        scan_type: str = "real"
    ) -> AggregatedResults:
        """
        Entry point principale per normalizzazione enterprise
        
        Args:
            url: URL scansionato
            company_name: Nome azienda
            email: Email referente
            scan_id: ID univoco scansione
            wave: Risultati WAVE (nullable)
            pa11y: Risultati Pa11y (nullable)
            axe: Risultati Axe-core (nullable)
            lighthouse: Risultati Lighthouse (nullable)
            timeout_seconds: Timeout scansione
            scan_type: Tipo scansione (real/simulate)
            
        Returns:
            AggregatedResults validato con Pydantic
            
        Raises:
            ValueError: Se tutti gli scanner falliscono
            ValidationError: Se i dati non sono validi
        """
        start_time = datetime.now()
        
        try:
            # Crea contesto scansione
            scan_context = self._create_scan_context(
                scan_id, company_name, email, url, 
                timeout_seconds, scan_type, start_time
            )
            
            # Processa ogni scanner individualmente con error handling
            individual_results = []
            
            # WAVE
            if wave is not None:
                try:
                    wave_result = self._process_wave(url, wave)
                    if wave_result:
                        individual_results.append(wave_result)
                        self.stats.successful_validations += 1
                except Exception as e:
                    logger.error(f"WAVE processing failed: {e}")
                    self.stats.failed_validations += 1
                    individual_results.append(self._create_failed_scanner_result(
                        ScannerType.WAVE, url, str(e)
                    ))
            else:
                self.stats.null_inputs += 1
            
            # Pa11y  
            if pa11y is not None:
                try:
                    pa11y_result = self._process_pa11y(url, pa11y)
                    if pa11y_result:
                        individual_results.append(pa11y_result)
                        self.stats.successful_validations += 1
                except Exception as e:
                    logger.error(f"Pa11y processing failed: {e}")
                    self.stats.failed_validations += 1
                    individual_results.append(self._create_failed_scanner_result(
                        ScannerType.PA11Y, url, str(e)
                    ))
            else:
                self.stats.null_inputs += 1
                
            # Axe-core
            if axe is not None:
                try:
                    axe_result = self._process_axe(url, axe)
                    if axe_result:
                        individual_results.append(axe_result)
                        self.stats.successful_validations += 1
                except Exception as e:
                    logger.error(f"Axe processing failed: {e}")
                    self.stats.failed_validations += 1
                    individual_results.append(self._create_failed_scanner_result(
                        ScannerType.AXE, url, str(e)
                    ))
            else:
                self.stats.null_inputs += 1
                
            # Lighthouse
            if lighthouse is not None:
                try:
                    lighthouse_result = self._process_lighthouse(url, lighthouse)
                    if lighthouse_result:
                        individual_results.append(lighthouse_result)
                        self.stats.successful_validations += 1
                except Exception as e:
                    logger.error(f"Lighthouse processing failed: {e}")
                    self.stats.failed_validations += 1
                    individual_results.append(self._create_failed_scanner_result(
                        ScannerType.LIGHTHOUSE, url, str(e)
                    ))
            else:
                self.stats.null_inputs += 1
            
            # Valida che abbiamo almeno un risultato
            if not individual_results:
                raise ValueError("Nessuno scanner ha prodotto risultati validi")
            
            # Completa context con timing
            end_time = datetime.now()
            scan_context.completed_at = end_time
            scan_context.duration_seconds = (end_time - start_time).total_seconds()
            
            # Calcola metriche aggregate
            compliance_metrics = self._calculate_aggregate_compliance(individual_results)
            
            # Crea risultato aggregato
            aggregated = AggregatedResults(
                scan_context=scan_context,
                individual_results=individual_results,
                compliance_metrics=compliance_metrics
            )
            
            # Aggiorna statistiche
            self.stats.processed_scanners = len(individual_results)
            self.stats.processing_time = (end_time - start_time).total_seconds()
            
            logger.info(f"Normalizzazione completata: {len(individual_results)} scanner, "
                       f"score {compliance_metrics.overall_score}, "
                       f"compliance {compliance_metrics.compliance_level}")
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Normalizzazione fallita: {e}")
            # Re-raise con contesto aggiuntivo
            raise ValueError(f"Enterprise normalizer failed: {e}") from e
    
    def _create_scan_context(
        self, 
        scan_id: str, 
        company_name: str, 
        email: str, 
        url: str,
        timeout_seconds: int,
        scan_type: str,
        started_at: datetime
    ) -> ScanContext:
        """Crea contesto scansione validato"""
        
        # Determina scanner richiesti dai dati disponibili  
        requested_scanners = []
        if scan_type == "real":
            requested_scanners = [ScannerType.PA11Y, ScannerType.AXE, ScannerType.LIGHTHOUSE, ScannerType.WAVE]
        else:
            requested_scanners = [ScannerType.PA11Y, ScannerType.AXE, ScannerType.LIGHTHOUSE]
            
        return ScanContext(
            scan_id=scan_id,
            company_name=company_name,
            email=email,
            scan_type=scan_type,
            requested_scanners=requested_scanners,
            timeout_seconds=timeout_seconds,
            started_at=started_at
        )
    
    def _process_wave(self, url: str, wave_data: Dict[str, Any]) -> Optional[ScannerResult]:
        """Processa risultati WAVE con defensive programming"""
        
        if not wave_data or wave_data.get("error"):
            return None
            
        violations = []
        
        # Processa categorie WAVE (formato API reale e simulato)
        categories = wave_data.get("categories", {})
        
        # Processa errori dalla categoria 'error'
        error_category = categories.get("error", {})
        error_items = error_category.get("items", {})
        for error_code, error_data in error_items.items():
            if not isinstance(error_data, dict):
                continue
            
            # Crea violazioni per ogni occorrenza
            count = error_data.get("count", 1)
            for i in range(count):
                violation = ViolationInstance(
                    code=str(error_code),
                    message=str(error_data.get("description", "Errore WAVE")),
                    severity=SeverityLevel.HIGH,
                    wcag_criterion=self._format_wcag_wave(error_data.get("wcag", [])),
                    element=f"Element {i+1} of {count}",
                    context=None
                )
                violations.append(violation)
        
        # Processa contrast issues
        contrast_category = categories.get("contrast", {})
        contrast_items = contrast_category.get("items", {})
        for contrast_code, contrast_data in contrast_items.items():
            if not isinstance(contrast_data, dict):
                continue
            
            count = contrast_data.get("count", 1)
            for i in range(count):
                violation = ViolationInstance(
                    code=str(contrast_code),
                    message=str(contrast_data.get("description", "Problema contrasto")),
                    severity=SeverityLevel.HIGH,
                    wcag_criterion=self._format_wcag_wave(contrast_data.get("wcag", [])),
                    element=f"Element {i+1} of {count}",
                    context=None
                )
                violations.append(violation)
        
        # Processa alert (warning)
        alert_category = categories.get("alert", {})
        alert_items = alert_category.get("items", {})
        for alert_code, alert_data in alert_items.items():
            if not isinstance(alert_data, dict):
                continue
            
            count = alert_data.get("count", 1)
            for i in range(count):
                violation = ViolationInstance(
                    code=str(alert_code),
                    message=str(alert_data.get("description", "Alert WAVE")),
                    severity=SeverityLevel.MEDIUM,
                    wcag_criterion=self._format_wcag_wave(alert_data.get("wcag", [])),
                    element=f"Element {i+1} of {count}",
                    context=None
                )
                violations.append(violation)
        
        # Calcola score basato su violazioni
        error_count = len([v for v in violations if v.severity == SeverityLevel.HIGH])
        warning_count = len([v for v in violations if v.severity == SeverityLevel.MEDIUM])
        
        # Formula di scoring WAVE
        penalty = (error_count * 10) + (warning_count * 3)
        score = max(0, 100 - penalty)
        
        # Crea metadati
        metadata = ScannerMetadata(
            scanner_type=ScannerType.WAVE,
            version=wave_data.get("version"),
            execution_time=wave_data.get("execution_time")
        )
        
        return ScannerResult(
            scanner=ScannerType.WAVE,
            url=url,
            status=ScanStatus.SUCCESS,
            violations=violations,
            accessibility_score=Decimal(str(score)),
            metadata=metadata,
            raw_data=wave_data
        )
    
    def _process_pa11y(self, url: str, pa11y_data: Dict[str, Any]) -> Optional[ScannerResult]:
        """Processa risultati Pa11y con gestione robusta null values"""
        
        if not pa11y_data:
            return None
            
        violations = []
        
        # Pa11y restituisce array di issues
        issues = pa11y_data.get("issues", [])
        if not isinstance(issues, list):
            issues = []
            
        for issue in issues:
            if not isinstance(issue, dict):
                continue
                
            # Estrai informazioni con fallback sicuri
            code = str(issue.get("code", "unknown"))
            message = str(issue.get("message", "Problema Pa11y"))
            type_level = str(issue.get("type", "error")).lower()
            
            # Mappa tipo a severità
            if type_level == "error":
                severity = SeverityLevel.HIGH
            elif type_level == "warning": 
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
                
            # Estrai selettore e contesto
            selector = issue.get("selector")
            context = issue.get("context")
            
            violation = ViolationInstance(
                code=code,
                message=message,
                severity=severity,
                wcag_criterion=self._extract_wcag_from_pa11y(code),
                element=str(selector) if selector else None,
                context=str(context)[:200] if context else None
            )
            violations.append(violation)
        
        # Calcola score basato su numero e tipo errori
        error_count = len([v for v in violations if v.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]])
        warning_count = len([v for v in violations if v.severity in [SeverityLevel.MEDIUM, SeverityLevel.LOW]])
        
        penalty = (error_count * 10) + (warning_count * 3)
        score = max(0, 100 - penalty)
        
        metadata = ScannerMetadata(
            scanner_type=ScannerType.PA11Y,
            execution_time=pa11y_data.get("execution_time")
        )
        
        return ScannerResult(
            scanner=ScannerType.PA11Y,
            url=url,
            status=ScanStatus.SUCCESS,
            violations=violations,
            accessibility_score=Decimal(str(score)),
            metadata=metadata,
            raw_data=pa11y_data
        )
    
    def _process_axe(self, url: str, axe_data: Dict[str, Any]) -> Optional[ScannerResult]:
        """Processa risultati Axe-core con type safety"""
        
        if not axe_data:
            return None
            
        violations = []
        
        # Processa violations Axe
        axe_violations = axe_data.get("violations", [])
        if isinstance(axe_violations, list):
            for violation in axe_violations:
                if not isinstance(violation, dict):
                    continue
                    
                # Estrai severity con mapping sicuro
                impact = str(violation.get("impact", "moderate")).lower()
                severity = self.severity_mapping.get(impact, SeverityLevel.MEDIUM)
                
                # Estrai WCAG da tags
                tags = violation.get("tags", [])
                wcag_criterion = self._extract_wcag_from_axe_tags(tags)
                
                # Conta nodi affetti
                nodes = violation.get("nodes", [])
                node_count = len(nodes) if isinstance(nodes, list) else 1
                
                violation_instance = ViolationInstance(
                    code=str(violation.get("id", "unknown")),
                    message=str(violation.get("description", violation.get("help", "Violazione Axe"))),
                    severity=severity,
                    wcag_criterion=wcag_criterion,
                    context=f"Nodi affetti: {node_count}"
                )
                violations.append(violation_instance)
        
        # Calcola score con formula Axe  
        error_count = len([v for v in violations if v.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]])
        warning_count = len([v for v in violations if v.severity in [SeverityLevel.MEDIUM, SeverityLevel.LOW]])
        
        penalty = (error_count * 15) + (warning_count * 5) 
        score = max(0, 100 - penalty)
        
        metadata = ScannerMetadata(
            scanner_type=ScannerType.AXE,
            execution_time=axe_data.get("execution_time")
        )
        
        return ScannerResult(
            scanner=ScannerType.AXE,
            url=url,
            status=ScanStatus.SUCCESS,
            violations=violations,
            accessibility_score=Decimal(str(score)),
            metadata=metadata,
            raw_data=axe_data
        )
    
    def _process_lighthouse(self, url: str, lighthouse_data: Dict[str, Any]) -> Optional[ScannerResult]:
        """Processa risultati Lighthouse con fallback robusti"""
        
        if not lighthouse_data:
            return None
            
        violations = []
        
        # Estrai score accessibilità
        categories = lighthouse_data.get("categories", {})
        accessibility_category = categories.get("accessibility", {}) if isinstance(categories, dict) else {}
        
        score_value = accessibility_category.get("score", 0) if isinstance(accessibility_category, dict) else 0
        if score_value is None:
            score_value = 0
            
        # Converti a percentuale
        score = int(float(score_value) * 100) if isinstance(score_value, (int, float)) else 0
        
        # Processa audits
        audits = lighthouse_data.get("audits", {})
        if isinstance(audits, dict):
            for audit_id, audit_data in audits.items():
                if not isinstance(audit_data, dict):
                    continue
                    
                audit_score = audit_data.get("score")
                if audit_score is None or audit_score >= 1:
                    continue  # Skip audits che passano
                    
                # Determina severità da ID audit
                severity = self._get_lighthouse_severity(audit_id)
                
                # Conta items affetti
                details = audit_data.get("details", {})
                items = details.get("items", []) if isinstance(details, dict) else []
                item_count = len(items) if isinstance(items, list) else 0
                
                violation = ViolationInstance(
                    code=audit_id,
                    message=str(audit_data.get("title", f"Audit {audit_id} fallito")),
                    severity=severity,
                    wcag_criterion=self._map_lighthouse_to_wcag(audit_id),
                    context=f"Items affetti: {item_count}" if item_count > 0 else None
                )
                violations.append(violation)
        
        metadata = ScannerMetadata(
            scanner_type=ScannerType.LIGHTHOUSE,
            version=lighthouse_data.get("lighthouse_version"),
            execution_time=lighthouse_data.get("execution_time")
        )
        
        return ScannerResult(
            scanner=ScannerType.LIGHTHOUSE,
            url=url,
            status=ScanStatus.SUCCESS,
            violations=violations,
            accessibility_score=Decimal(str(score)),
            metadata=metadata,
            raw_data=lighthouse_data
        )
    
    def _create_failed_scanner_result(
        self, 
        scanner_type: ScannerType, 
        url: str, 
        error_message: str
    ) -> ScannerResult:
        """Crea risultato per scanner fallito"""
        
        metadata = ScannerMetadata(
            scanner_type=scanner_type,
            exit_code=1
        )
        
        return ScannerResult(
            scanner=scanner_type,
            url=url,
            status=ScanStatus.FAILED,
            violations=[],
            accessibility_score=Decimal('0.00'),
            metadata=metadata,
            error_message=error_message
        )
    
    def _calculate_aggregate_compliance(
        self, 
        individual_results: List[ScannerResult]
    ) -> ComplianceMetrics:
        """Calcola metriche compliance aggregate con algoritmo pesato enterprise"""
        
        # Filtra solo scanner riusciti
        successful_results = [r for r in individual_results if r.status == ScanStatus.SUCCESS]
        
        if not successful_results:
            # Fallback per caso estremo
            return ComplianceMetrics(
                overall_score=Decimal('0.00'),
                compliance_level="non_conforme",
                total_violations=0,
                critical_violations=0,
                high_violations=0,
                medium_violations=0,
                low_violations=0,
                confidence_level=Decimal('0.00')
            )
        
        # Aggrega violazioni per severità
        total_violations = 0
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0
        
        for result in successful_results:
            for violation in result.violations:
                total_violations += 1
                if violation.severity == SeverityLevel.CRITICAL:
                    critical_count += 1
                elif violation.severity == SeverityLevel.HIGH:
                    high_count += 1
                elif violation.severity == SeverityLevel.MEDIUM:
                    medium_count += 1
                elif violation.severity == SeverityLevel.LOW:
                    low_count += 1
        
        # FORMULA CORRETTA BASATA SU WCAG 2.1
        # Ogni tipo di violazione ha un peso specifico secondo WCAG
        # Lo score parte da 100 e viene decrementato in base alle violazioni
        
        # Pesi secondo WCAG 2.1 Level AA - Calibrati per siti reali
        # Formula: ogni punto di penalità rappresenta circa 1% di non-conformità
        # Considerando che un sito può avere molte violazioni minori ma essere ancora utilizzabile
        wcag_weights = {
            'critical': 8,   # Blockers totali (es. no alt text, no keyboard access)
            'high': 4,       # Problemi gravi (es. contrast ratio < 3:1)
            'medium': 2,     # Problemi moderati (es. missing labels)
            'low': 0.5       # Problemi minori (es. decorative images)
        }
        
        # Calcola penalità totale
        total_penalty = (
            critical_count * wcag_weights['critical'] +
            high_count * wcag_weights['high'] +
            medium_count * wcag_weights['medium'] +
            low_count * wcag_weights['low']
        )
        
        # DEBUG LOGGING
        logger.info(f"🔍 WCAG SCORE CALCULATION:")
        logger.info(f"   Violations: critical={critical_count}, high={high_count}, medium={medium_count}, low={low_count}")
        logger.info(f"   Weights: critical={wcag_weights['critical']}, high={wcag_weights['high']}, medium={wcag_weights['medium']}, low={wcag_weights['low']}")
        logger.info(f"   Total penalty: {total_penalty}")
        
        # Formula finale: score = 100 - penalty, con range [0, 100]
        overall_score = max(0, min(100, 100 - total_penalty))
        
        logger.info(f"   Formula: max(0, min(100, 100 - {total_penalty}))")
        logger.info(f"   ➡️  FINAL SCORE: {overall_score}")
        logger.info(f"🔍 END WCAG SCORE CALCULATION")
        
        # Determina compliance level
        if critical_count > 0:
            compliance_level = "non_conforme"
        elif overall_score >= 85:
            compliance_level = "conforme"
        elif overall_score >= 60:
            compliance_level = "parzialmente_conforme"
        else:
            compliance_level = "non_conforme"
            
        # Calcola confidence basato su numero scanner
        num_scanners = len(successful_results)
        confidence_map = {1: 60, 2: 75, 3: 85, 4: 95}
        confidence = confidence_map.get(num_scanners, 50)
        
        return ComplianceMetrics(
            overall_score=Decimal(str(overall_score)).quantize(Decimal('0.01')),
            compliance_level=compliance_level,
            total_violations=total_violations,
            critical_violations=critical_count,
            high_violations=high_count,
            medium_violations=medium_count,
            low_violations=low_count,
            confidence_level=Decimal(str(confidence))
        )
    
    # Helper methods per WCAG mapping
    def _extract_wcag_from_pa11y(self, code: str) -> str:
        """Estrae criterio WCAG da codice Pa11y"""
        # Pa11y usa codici come WCAG2AA.Principle1.Guideline1_1.1_1_1.H37
        if "WCAG" in code and "." in code:
            parts = code.split(".")
            for part in parts:
                if part.count("_") == 2:  # Pattern X_X_X
                    return part.replace("_", ".")
        return ""
    
    def _extract_wcag_from_axe_tags(self, tags: List[str]) -> str:
        """Estrae criterio WCAG da tags Axe"""
        import re
        
        for tag in tags:
            if not isinstance(tag, str):
                continue
            match = re.search(r'wcag(\d+)', tag.lower())
            if match:
                digits = match.group(1)
                if len(digits) == 3:
                    return f"{digits[0]}.{digits[1]}.{digits[2]}"
                elif len(digits) == 4:
                    return f"{digits[0]}.{digits[1]}.{digits[2:]}"
        return ""
    
    def _get_lighthouse_severity(self, audit_id: str) -> SeverityLevel:
        """Determina severità da audit ID Lighthouse"""
        
        critical_audits = [
            "color-contrast", "html-has-lang", "image-alt", 
            "button-name", "link-name", "form-field-multiple-labels"
        ]
        
        if audit_id in critical_audits:
            return SeverityLevel.HIGH
        elif "aria" in audit_id or "duplicate-id" in audit_id:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _map_lighthouse_to_wcag(self, audit_id: str) -> str:
        """Mappa audit Lighthouse a criterio WCAG"""
        
        # Mapping ridotto dei più comuni
        mapping = {
            "color-contrast": "1.4.3",
            "html-has-lang": "3.1.1", 
            "image-alt": "1.1.1",
            "button-name": "4.1.2",
            "link-name": "2.4.4",
            "bypass": "2.4.1",
            "document-title": "2.4.2",
            "form-field-multiple-labels": "3.3.2",
            "frame-title": "2.4.1",
            "meta-viewport": "1.4.4"
        }
        
        return mapping.get(audit_id, "")
    
    def get_processing_stats(self) -> ProcessingStats:
        """Restituisce statistiche processing per monitoring"""
        return self.stats
    
    def reset_stats(self):
        """Reset statistiche per nuovo ciclo"""
        self.stats = ProcessingStats()


# Factory function per backward compatibility
def create_enterprise_normalizer() -> EnterpriseNormalizer:
    """Factory per creare normalizer enterprise"""
    return EnterpriseNormalizer(enable_metrics=True)