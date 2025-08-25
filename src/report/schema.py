"""
Schema dati per report di accessibilità
WCAG 2.1 AA + principi P.O.U.R. + Impatto disabilità
"""

from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class POURPrinciple(Enum):
    """Principi P.O.U.R. delle WCAG"""
    PERCEPIBILE = "Percepibile"
    OPERABILE = "Operabile" 
    COMPRENSIBILE = "Comprensibile"
    ROBUSTO = "Robusto"


class DisabilityType(Enum):
    """Tipologie di disabilità impattate"""
    NON_VEDENTI = "non_vedenti"
    IPOVISIONE = "ipovisione"
    DALTONISMO = "daltonismo"
    MOTORIE = "motorie"
    COGNITIVE_LINGUISTICHE = "cognitive_linguistiche"
    UDITIVA = "uditiva"


class Severity(Enum):
    """Livelli di severità"""
    CRITICO = "critico"
    ALTO = "alto"
    MEDIO = "medio"
    BASSO = "basso"


@dataclass
class Methodology:
    """Metodologia di valutazione"""
    baseline: Literal["automatic"] = "automatic"
    manual_tests_supported: bool = True
    statement: str = (
        "Questo report si basa su verifiche automatiche standardizzate "
        "(baseline valida e replicabile). Le verifiche manuali e i test "
        "con utenti con disabilità sono un complemento che innalza il grado "
        "'audit-grade', ma non sono una precondizione alla validità del presente report."
    )


@dataclass
class SamplingPage:
    """Pagina nel campione di test"""
    url: str
    template: str
    included: bool = True


@dataclass
class Sampling:
    """Criteri di campionamento"""
    criteria: List[str] = field(default_factory=lambda: [
        "Home e top task",
        "Template chiave (lista, dettaglio, ricerca, form/checkout, media)",
        "Pagine ad alto impatto",
        "Varianti mobile e componenti interattivi",
        "1-3 istanze reali per template"
    ])
    pages: List[SamplingPage] = field(default_factory=list)


@dataclass
class ContinuousProcess:
    """Processo di conformità continua"""
    enabled: bool = True
    practices: List[str] = field(default_factory=lambda: [
        "CI/CD checks",
        "Design System accessibile",
        "Formazione team",
        "Monitoraggio continuo",
        "Review periodiche"
    ])


@dataclass
class DeclarationAndFeedback:
    """Dichiarazione accessibilità e canali feedback"""
    mode: Literal["private", "pa"] = "private"
    page_internal: bool = True
    channels: List[str] = field(default_factory=lambda: ["form", "email"])
    notes: str = "Canali dedicati per segnalazioni e supporto accessibilità"


@dataclass
class Issue:
    """Singola problematica di accessibilità"""
    id: str
    description: str
    element: str
    wcag_criteria: List[str]
    pour: POURPrinciple
    severity: Severity
    disability_impact: List[DisabilityType]
    remediation: str
    selector: str = ""
    url: str = ""
    scanner_source: str = ""
    count: int = 1
    
    def pour_string(self) -> str:
        """Ritorna principio POUR come stringa"""
        return self.pour.value
    
    def disability_impact_string(self) -> str:
        """Ritorna impatti disabilità come stringa"""
        impacts = [d.value.replace("_", " ").title() for d in self.disability_impact]
        return ", ".join(impacts) if impacts else "Generale"
    
    def wcag_criteria_string(self) -> str:
        """Ritorna criteri WCAG come stringa"""
        return ", ".join(self.wcag_criteria)


@dataclass
class ScanResult:
    """Risultato completo della scansione"""
    url: str
    company_name: str
    methodology: Methodology = field(default_factory=Methodology)
    sampling: Sampling = field(default_factory=Sampling)
    continuous_process: ContinuousProcess = field(default_factory=ContinuousProcess)
    declaration_and_feedback: DeclarationAndFeedback = field(default_factory=DeclarationAndFeedback)
    issues: List[Issue] = field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    compliance_score: float = 0.0
    scan_id: str = ""
    
    def __post_init__(self):
        """Calcola statistiche dopo inizializzazione"""
        if self.issues:
            self.total_issues = len(self.issues)
            self.critical_issues = sum(1 for i in self.issues if i.severity == Severity.CRITICO)
            self.high_issues = sum(1 for i in self.issues if i.severity == Severity.ALTO)
            self.medium_issues = sum(1 for i in self.issues if i.severity == Severity.MEDIO)
            self.low_issues = sum(1 for i in self.issues if i.severity == Severity.BASSO)
            
            # Calcolo compliance score (100 - penalità)
            penalties = (
                self.critical_issues * 25 +
                self.high_issues * 10 +
                self.medium_issues * 3 +
                self.low_issues * 1
            )
            self.compliance_score = max(0, 100 - penalties)
    
    def get_issues_by_pour(self, principle: POURPrinciple) -> List[Issue]:
        """Ritorna issues filtrate per principio POUR"""
        return [i for i in self.issues if i.pour == principle]
    
    def get_issues_by_severity(self, severity: Severity) -> List[Issue]:
        """Ritorna issues filtrate per severità"""
        return [i for i in self.issues if i.severity == severity]
    
    def get_unique_disability_impacts(self) -> List[DisabilityType]:
        """Ritorna lista unica di impatti disabilità"""
        impacts = set()
        for issue in self.issues:
            impacts.update(issue.disability_impact)
        return list(impacts)
    
    @property
    def compliance_level(self) -> str:
        """Determina il livello di conformità basato sul punteggio"""
        if self.compliance_score >= 90:
            return "Sostanzialmente Conforme"
        elif self.compliance_score >= 50:
            return "Parzialmente Conforme"
        else:
            return "Non Conforme"