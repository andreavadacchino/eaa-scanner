"""
Enterprise-grade Pydantic models per risultati scanner
Validazione type-safe e gestione robusta null values
"""

from __future__ import annotations
from typing import Dict, List, Optional, Union, Any, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal


class SeverityLevel(str, Enum):
    """Livelli severità standardizzati"""
    CRITICAL = "critical"
    HIGH = "high" 
    MEDIUM = "medium"
    LOW = "low"


class ScannerType(str, Enum):
    """Scanner supportati"""
    PA11Y = "pa11y"
    AXE = "axe"
    LIGHTHOUSE = "lighthouse"
    WAVE = "wave"


class ScanStatus(str, Enum):
    """Stati scansione"""
    SUCCESS = "success"
    PARTIAL = "partial" 
    FAILED = "failed"
    TIMEOUT = "timeout"


class ViolationInstance(BaseModel):
    """Singola violazione rilevata"""
    code: str = Field(..., description="Codice identificativo violazione")
    message: str = Field(..., description="Messaggio descrittivo")
    severity: SeverityLevel = Field(..., description="Livello severità")
    wcag_criterion: Optional[str] = Field(None, description="Criterio WCAG 2.1/2.2")
    element: Optional[str] = Field(None, description="Selettore elemento")
    context: Optional[str] = Field(None, description="Contesto HTML")
    line: Optional[int] = Field(None, ge=0, description="Numero riga")
    column: Optional[int] = Field(None, ge=0, description="Numero colonna")
    
    @field_validator('wcag_criterion')
    @classmethod
    def validate_wcag(cls, v):
        """Valida formato criterio WCAG"""
        if v and not v.startswith(('WCAG', 'wcag')):
            return f"WCAG 2.1 - {v}" if v else None
        return v


class ScannerMetadata(BaseModel):
    """Metadati scanner execution"""
    scanner_type: ScannerType = Field(..., description="Tipo scanner")
    version: Optional[str] = Field(None, description="Versione scanner")
    execution_time: Optional[float] = Field(None, ge=0, description="Tempo esecuzione (secondi)")
    memory_usage: Optional[int] = Field(None, ge=0, description="Uso memoria (MB)")
    exit_code: Optional[int] = Field(None, description="Codice uscita")
    command_used: Optional[str] = Field(None, description="Comando eseguito")
    
    class Config:
        use_enum_values = True


class ScannerResult(BaseModel):
    """Risultato singolo scanner con validazione enterprise"""
    scanner: ScannerType = Field(..., description="Tipo scanner")
    url: str = Field(..., description="URL scansionato")
    status: ScanStatus = Field(..., description="Stato scansione")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp scansione")
    
    # Risultati validati
    violations: List[ViolationInstance] = Field(default_factory=list, description="Violazioni rilevate")
    total_violations: int = Field(0, ge=0, description="Numero totale violazioni")
    accessibility_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score accessibilità")
    
    # Breakdown per severità con default sicuri
    critical_count: int = Field(0, ge=0, description="Violazioni critiche")
    high_count: int = Field(0, ge=0, description="Violazioni high")
    medium_count: int = Field(0, ge=0, description="Violazioni medium") 
    low_count: int = Field(0, ge=0, description="Violazioni low")
    
    # Metadati e dati raw
    metadata: Optional[ScannerMetadata] = Field(None, description="Metadati esecuzione")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Dati raw completi")
    error_message: Optional[str] = Field(None, description="Messaggio errore se applicabile")
    
    @model_validator(mode='after')
    def validate_counts(self):
        """Valida coerenza conteggi"""
        violations = self.violations or []
        total = self.total_violations or 0
        
        # Auto-calcolo se non specificato
        if not total and violations:
            self.total_violations = len(violations)
        
        # Auto-calcolo breakdown severità 
        if violations:
            severity_counts = {
                SeverityLevel.CRITICAL: 0,
                SeverityLevel.HIGH: 0, 
                SeverityLevel.MEDIUM: 0,
                SeverityLevel.LOW: 0
            }
            
            for violation in violations:
                severity_counts[violation.severity] += 1
            
            # Aggiorna solo se non specificati
            if not any([self.critical_count, self.high_count, 
                       self.medium_count, self.low_count]):
                self.critical_count = severity_counts[SeverityLevel.CRITICAL]
                self.high_count = severity_counts[SeverityLevel.HIGH]
                self.medium_count = severity_counts[SeverityLevel.MEDIUM]
                self.low_count = severity_counts[SeverityLevel.LOW]
        
        return self
    
    @field_validator('accessibility_score')
    @classmethod
    def validate_score(cls, v):
        """Valida score accessibilità"""
        if v is not None:
            return Decimal(str(v)).quantize(Decimal('0.01'))  # 2 decimali
        return v


class ComplianceMetrics(BaseModel):
    """Metriche compliance aggregate e pesate"""
    overall_score: Decimal = Field(..., ge=0, le=100, description="Score generale pesato")
    compliance_level: Literal["conforme", "parzialmente_conforme", "non_conforme"] = Field(
        ..., description="Livello compliance EAA"
    )
    
    # Breakdown dettagliato
    total_violations: int = Field(0, ge=0, description="Totale violazioni")
    critical_violations: int = Field(0, ge=0, description="Violazioni critiche")
    high_violations: int = Field(0, ge=0, description="Violazioni high")
    medium_violations: int = Field(0, ge=0, description="Violazioni medium")
    low_violations: int = Field(0, ge=0, description="Violazioni low")
    
    # Score per categorie WCAG
    perceivable_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score Perceivable")
    operable_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score Operable") 
    understandable_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score Understandable")
    robust_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Score Robust")
    
    # Confidence intervals
    confidence_level: Decimal = Field(Decimal('0.0'), ge=0, le=100, description="Livello confidenza %")
    margin_of_error: Optional[Decimal] = Field(None, ge=0, le=50, description="Margine errore %")
    
    @field_validator('overall_score', 'perceivable_score', 'operable_score', 'understandable_score', 'robust_score')
    @classmethod
    def quantize_scores(cls, v):
        """Arrotonda scores a 2 decimali"""
        if v is not None:
            return Decimal(str(v)).quantize(Decimal('0.01'))
        return v


class ScanContext(BaseModel):
    """Contesto scansione per traceability"""
    scan_id: str = Field(..., description="ID univoco scansione")
    company_name: str = Field(..., description="Nome azienda")
    email: str = Field(..., description="Email referente")
    scan_type: Literal["real", "simulate"] = Field("real", description="Tipo scansione")
    requested_scanners: List[ScannerType] = Field(..., description="Scanner richiesti")
    
    # Parametri tecnici
    timeout_seconds: int = Field(30, ge=5, le=300, description="Timeout scansione")
    max_retries: int = Field(3, ge=0, le=10, description="Retry massimi")
    parallel_execution: bool = Field(False, description="Esecuzione parallela")
    
    # Tracking
    started_at: datetime = Field(default_factory=datetime.now, description="Inizio scansione")
    completed_at: Optional[datetime] = Field(None, description="Fine scansione")
    duration_seconds: Optional[float] = Field(None, ge=0, description="Durata totale")


class AggregatedResults(BaseModel):
    """Risultati aggregati enterprise con validazione robusta"""
    
    # Context e metadata
    scan_context: ScanContext = Field(..., description="Contesto scansione")
    individual_results: List[ScannerResult] = Field(..., description="Risultati individuali")
    
    # Metriche aggregate
    compliance_metrics: ComplianceMetrics = Field(..., description="Metriche compliance")
    
    # Statistiche esecuzione
    successful_scanners: List[ScannerType] = Field(default_factory=list, description="Scanner riusciti")
    failed_scanners: List[ScannerType] = Field(default_factory=list, description="Scanner falliti")
    execution_summary: Dict[str, Any] = Field(default_factory=dict, description="Riassunto esecuzione")
    
    # Output finale
    html_report_path: Optional[str] = Field(None, description="Path report HTML")
    json_summary_path: Optional[str] = Field(None, description="Path summary JSON")
    
    @model_validator(mode='after')
    def validate_aggregation(self):
        """Valida coerenza aggregazione"""
        individual = self.individual_results or []
        context = self.scan_context
        
        if not individual:
            raise ValueError("Almeno un risultato scanner richiesto")
        
        # Auto-popolamento scanner status
        successful = []
        failed = []
        
        for result in individual:
            if result.status == ScanStatus.SUCCESS:
                successful.append(result.scanner)
            else:
                failed.append(result.scanner)
        
        self.successful_scanners = successful
        self.failed_scanners = failed
        
        # Valida completion time se disponibile
        if context and context.completed_at and context.started_at:
            duration = (context.completed_at - context.started_at).total_seconds()
            context.duration_seconds = max(0.0, duration)
        
        return self
    
    @property
    def success_rate(self) -> Decimal:
        """Calcola tasso successo scanner"""
        total = len(self.successful_scanners) + len(self.failed_scanners)
        if total == 0:
            return Decimal('0.00')
        return Decimal(len(self.successful_scanners) / total * 100).quantize(Decimal('0.01'))
    
    def get_violations_by_scanner(self, scanner_type: ScannerType) -> List[ViolationInstance]:
        """Ottieni violazioni per scanner specifico"""
        for result in self.individual_results:
            if result.scanner == scanner_type:
                return result.violations
        return []
    
    def get_scanner_score(self, scanner_type: ScannerType) -> Optional[Decimal]:
        """Ottieni score per scanner specifico"""
        for result in self.individual_results:
            if result.scanner == scanner_type:
                return result.accessibility_score
        return None


class Config:
    """Configurazione globale Pydantic"""
    use_enum_values = True
    validate_assignment = True
    arbitrary_types_allowed = False
    extra = "forbid"  # Blocca campi extra per sicurezza