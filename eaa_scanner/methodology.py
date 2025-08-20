"""
Metodologia di test EAA e metadati estesi per conformità europea
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json


@dataclass
class TestMethodology:
    """
    Metodologia di test secondo standard EAA
    """
    # Informazioni base
    standard_version: str = "WCAG 2.1"
    conformance_level: str = "AA"
    test_date: str = datetime.now().strftime("%Y-%m-%d")
    
    # Metodologia
    evaluation_method: str = "WCAG-EM 1.0"  # Web Accessibility Evaluation Methodology
    test_approach: str = "hybrid"  # automated, manual, hybrid
    
    # Strumenti utilizzati
    automated_tools: List[str] = None
    manual_tools: List[str] = None
    assistive_technologies: List[str] = None
    
    # Browser e dispositivi testati
    browsers_tested: List[Dict[str, str]] = None
    devices_tested: List[Dict[str, str]] = None
    
    # Ambito del test
    scope: Dict[str, Any] = None
    sample_pages: List[str] = None
    page_selection_criteria: str = ""
    
    # Team di valutazione
    evaluators: List[Dict[str, str]] = None
    review_date: Optional[str] = None
    
    def __post_init__(self):
        """Inizializza valori di default"""
        if self.automated_tools is None:
            self.automated_tools = [
                "WAVE WebAIM API",
                "Axe-core CLI",
                "Pa11y CLI",
                "Lighthouse CLI"
            ]
        
        if self.manual_tools is None:
            self.manual_tools = [
                "Chrome DevTools",
                "WAVE Browser Extension",
                "Axe DevTools Extension",
                "Color Contrast Analyzer"
            ]
        
        if self.assistive_technologies is None:
            self.assistive_technologies = [
                "NVDA 2024.1 (Windows)",
                "JAWS 2024 (Windows)",
                "VoiceOver (macOS Sonoma)",
                "TalkBack (Android 14)"
            ]
        
        if self.browsers_tested is None:
            self.browsers_tested = [
                {"name": "Chrome", "version": "120+", "platform": "Windows/Mac/Linux"},
                {"name": "Firefox", "version": "120+", "platform": "Windows/Mac/Linux"},
                {"name": "Safari", "version": "17+", "platform": "macOS/iOS"},
                {"name": "Edge", "version": "120+", "platform": "Windows"}
            ]
        
        if self.devices_tested is None:
            self.devices_tested = [
                {"type": "Desktop", "os": "Windows 11", "resolution": "1920x1080"},
                {"type": "Desktop", "os": "macOS Sonoma", "resolution": "2560x1440"},
                {"type": "Mobile", "os": "iOS 17", "device": "iPhone 15", "resolution": "1179x2556"},
                {"type": "Mobile", "os": "Android 14", "device": "Pixel 8", "resolution": "1080x2400"},
                {"type": "Tablet", "os": "iPadOS 17", "device": "iPad Pro", "resolution": "2048x2732"}
            ]
        
        if self.scope is None:
            self.scope = {
                "conformance_target": "Entire website",
                "technology_stack": [],
                "content_types": ["Static HTML", "Dynamic content", "Forms", "Media"],
                "functionality": ["Navigation", "Search", "Forms", "Authentication", "E-commerce"],
                "excluded_content": []
            }
        
        if self.evaluators is None:
            self.evaluators = [
                {
                    "role": "Lead Accessibility Auditor",
                    "certification": "IAAP CPWA",
                    "organization": "EAA Scanner Team"
                }
            ]
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Converte in JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


@dataclass 
class EAACompliance:
    """
    Dati di conformità EAA (European Accessibility Act)
    """
    # Riferimenti normativi
    directive: str = "Directive (EU) 2019/882"
    implementation_date: str = "2025-06-28"
    national_law: str = "D.Lgs. 82/2005 (CAD) - Italia"
    
    # Conformità
    compliance_status: str = ""  # compliant, partially_compliant, non_compliant
    compliance_date: Optional[str] = None
    next_review_date: Optional[str] = None
    
    # Dichiarazione di accessibilità
    accessibility_statement_url: Optional[str] = None
    accessibility_statement_date: Optional[str] = None
    feedback_mechanism: Optional[str] = None
    enforcement_procedure: Optional[str] = None
    
    # Categorie EAA applicabili
    applicable_categories: List[str] = None
    
    def __post_init__(self):
        """Inizializza valori di default"""
        if self.applicable_categories is None:
            self.applicable_categories = [
                "E-commerce services",
                "Banking services", 
                "Electronic communications",
                "Access to audiovisual media services",
                "E-books",
                "Software and mobile applications"
            ]
        
        if self.next_review_date is None and self.compliance_date:
            # Review annuale per default
            compliance = datetime.strptime(self.compliance_date, "%Y-%m-%d")
            next_review = compliance + timedelta(days=365)
            self.next_review_date = next_review.strftime("%Y-%m-%d")
        
        if self.feedback_mechanism is None:
            self.feedback_mechanism = "Email: accessibilita@example.com"
        
        if self.enforcement_procedure is None:
            self.enforcement_procedure = "AgID - Agenzia per l'Italia Digitale"
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)


@dataclass
class RemediationPlan:
    """
    Piano di remediation per le non conformità
    """
    # Timeline generale
    start_date: str = datetime.now().strftime("%Y-%m-%d")
    target_completion_date: Optional[str] = None
    
    # Fasi del piano
    phases: List[Dict[str, Any]] = None
    
    # Risorse
    estimated_effort_hours: int = 0
    estimated_cost_eur: Optional[float] = None
    responsible_team: str = "Development Team"
    
    # Priorità
    priority_criteria: str = "Severity and user impact"
    
    # Monitoraggio
    review_frequency: str = "Monthly"
    progress_tracking_method: str = "JIRA/GitHub Issues"
    
    def __post_init__(self):
        """Inizializza valori di default"""
        if self.phases is None:
            self.phases = [
                {
                    "phase": 1,
                    "name": "Problemi Critici",
                    "description": "Risoluzione barriere bloccanti all'accesso",
                    "duration_weeks": 2,
                    "issues": []
                },
                {
                    "phase": 2,
                    "name": "Problemi Alti",
                    "description": "Risoluzione problemi con impatto significativo",
                    "duration_weeks": 4,
                    "issues": []
                },
                {
                    "phase": 3,
                    "name": "Problemi Medi",
                    "description": "Miglioramenti usabilità e navigazione",
                    "duration_weeks": 4,
                    "issues": []
                },
                {
                    "phase": 4,
                    "name": "Ottimizzazioni",
                    "description": "Problemi minori e miglioramenti generali",
                    "duration_weeks": 2,
                    "issues": []
                }
            ]
        
        if self.target_completion_date is None:
            # Calcola data completamento basata sulle fasi
            total_weeks = sum(p.get("duration_weeks", 0) for p in self.phases)
            target = datetime.now() + timedelta(weeks=total_weeks)
            self.target_completion_date = target.strftime("%Y-%m-%d")
    
    def add_issue_to_phase(self, phase_num: int, issue: Dict[str, Any]) -> None:
        """
        Aggiunge un issue a una fase specifica
        
        Args:
            phase_num: Numero della fase (1-4)
            issue: Dizionario con dettagli dell'issue
        """
        for phase in self.phases:
            if phase["phase"] == phase_num:
                if "issues" not in phase:
                    phase["issues"] = []
                phase["issues"].append(issue)
                break
    
    def calculate_total_effort(self) -> int:
        """
        Calcola effort totale stimato
        
        Returns:
            Ore totali stimate
        """
        total = 0
        for phase in self.phases:
            for issue in phase.get("issues", []):
                total += issue.get("estimated_hours", 0)
        return total
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        data = asdict(self)
        data["total_estimated_hours"] = self.calculate_total_effort()
        return data


@dataclass
class OrganizationalData:
    """
    Dati organizzativi per report EAA
    """
    # Organizzazione valutata
    organization_name: str
    organization_type: str = ""  # public, private, non-profit
    organization_size: str = ""  # small, medium, large, enterprise
    sector: str = ""
    
    # Contatti
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    
    # Informazioni legali
    vat_number: Optional[str] = None
    legal_entity: Optional[str] = None
    headquarters_address: Optional[str] = None
    
    # Responsabilità accessibilità
    accessibility_officer: Optional[str] = None
    accessibility_team_size: int = 0
    accessibility_budget_allocated: bool = False
    
    # Politiche
    has_accessibility_policy: bool = False
    policy_url: Optional[str] = None
    training_program: bool = False
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)


class MetadataManager:
    """
    Gestisce tutti i metadati EAA per un report
    """
    
    def __init__(self):
        self.methodology = TestMethodology()
        self.eaa_compliance = EAACompliance()
        self.remediation_plan = RemediationPlan()
        self.organization = None
    
    def set_organization(self, org_name: str, org_type: str = "private", **kwargs) -> None:
        """
        Imposta dati organizzazione
        
        Args:
            org_name: Nome organizzazione
            org_type: Tipo organizzazione
            **kwargs: Altri parametri OrganizationalData
        """
        self.organization = OrganizationalData(
            organization_name=org_name,
            organization_type=org_type,
            **kwargs
        )
    
    def set_compliance_status(self, status: str, score: int) -> None:
        """
        Imposta stato conformità basato su score
        
        Args:
            status: Stato conformità
            score: Score complessivo
        """
        self.eaa_compliance.compliance_status = status
        self.eaa_compliance.compliance_date = datetime.now().strftime("%Y-%m-%d")
        
        # Determina prossima review basata su conformità
        if status == "compliant":
            next_review = datetime.now() + timedelta(days=365)
        elif status == "partially_compliant":
            next_review = datetime.now() + timedelta(days=180)
        else:
            next_review = datetime.now() + timedelta(days=90)
        
        self.eaa_compliance.next_review_date = next_review.strftime("%Y-%m-%d")
    
    def generate_remediation_plan(self, issues: List[Dict[str, Any]]) -> None:
        """
        Genera piano di remediation basato sui problemi trovati
        
        Args:
            issues: Lista di problemi trovati
        """
        # Categorizza issues per severità
        critical = [i for i in issues if i.get("severity") == "critical"]
        high = [i for i in issues if i.get("severity") == "high"]
        medium = [i for i in issues if i.get("severity") == "medium"]
        low = [i for i in issues if i.get("severity") == "low"]
        
        # Assegna a fasi
        for issue in critical:
            self.remediation_plan.add_issue_to_phase(1, {
                "code": issue.get("code"),
                "description": issue.get("description"),
                "severity": "critical",
                "estimated_hours": 4,
                "wcag_criteria": issue.get("wcag_criteria")
            })
        
        for issue in high:
            self.remediation_plan.add_issue_to_phase(2, {
                "code": issue.get("code"),
                "description": issue.get("description"),
                "severity": "high",
                "estimated_hours": 3,
                "wcag_criteria": issue.get("wcag_criteria")
            })
        
        for issue in medium:
            self.remediation_plan.add_issue_to_phase(3, {
                "code": issue.get("code"),
                "description": issue.get("description"),
                "severity": "medium",
                "estimated_hours": 2,
                "wcag_criteria": issue.get("wcag_criteria")
            })
        
        for issue in low:
            self.remediation_plan.add_issue_to_phase(4, {
                "code": issue.get("code"),
                "description": issue.get("description"),
                "severity": "low",
                "estimated_hours": 1,
                "wcag_criteria": issue.get("wcag_criteria")
            })
        
        # Calcola effort totale
        self.remediation_plan.estimated_effort_hours = self.remediation_plan.calculate_total_effort()
        
        # Stima costo (assumendo €50/ora)
        self.remediation_plan.estimated_cost_eur = self.remediation_plan.estimated_effort_hours * 50
    
    def get_complete_metadata(self) -> Dict[str, Any]:
        """
        Ottiene tutti i metadati completi
        
        Returns:
            Dizionario con tutti i metadati
        """
        return {
            "methodology": self.methodology.to_dict(),
            "eaa_compliance": self.eaa_compliance.to_dict(),
            "remediation_plan": self.remediation_plan.to_dict(),
            "organization": self.organization.to_dict() if self.organization else {}
        }
    
    def export_metadata(self, filepath: str) -> None:
        """
        Esporta metadati in JSON
        
        Args:
            filepath: Path del file di output
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.get_complete_metadata(), f, indent=2, ensure_ascii=False)