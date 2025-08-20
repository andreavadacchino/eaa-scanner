"""
Modelli dati per API backend workflow 2-fasi
Supporta discovery e scanning separati con gestione stato persistente
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Set
import time
import uuid
from pathlib import Path


class SessionStatus(Enum):
    """Stati possibili per sessioni discovery e scan"""
    PENDING = "pending"           # In attesa di avvio
    RUNNING = "running"           # In esecuzione
    PAUSED = "paused"             # Pausato (recovery possibile)
    COMPLETED = "completed"       # Completato con successo
    FAILED = "failed"             # Fallito con errori
    CANCELLED = "cancelled"       # Cancellato dall'utente


class PageType(Enum):
    """Tipi di pagina identificati durante discovery"""
    HOMEPAGE = "homepage"
    AUTHENTICATION = "authentication"
    CONTACT = "contact"
    FORM = "form"
    SEARCH = "search"
    ECOMMERCE = "ecommerce"
    ARTICLE = "article"
    ABOUT = "about"
    LEGAL = "legal"
    GENERAL = "general"


class SeverityLevel(Enum):
    """Livelli severità per problemi accessibilità"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class DiscoveredPage:
    """Pagina scoperta durante fase discovery"""
    url: str
    title: str = ""
    description: str = ""
    page_type: PageType = PageType.GENERAL
    priority: int = 50
    depth: int = 0
    discovered_at: float = field(default_factory=time.time)
    
    # Metadati struttura pagina
    forms_count: int = 0
    inputs_count: int = 0
    buttons_count: int = 0
    images_count: int = 0
    videos_count: int = 0
    links_count: int = 0
    
    # Metadati accessibilità
    has_h1: bool = False
    has_nav: bool = False
    has_main: bool = False
    has_footer: bool = False
    lang: str = "it"
    
    # Template detection
    template_hash: str = ""
    dom_structure: str = ""
    
    # Screenshot per preview
    screenshot_path: Optional[str] = None
    
    # Selezione per scanning
    selected_for_scan: bool = False
    selection_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario"""
        data = asdict(self)
        data['page_type'] = self.page_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscoveredPage':
        """Deserializza da dizionario"""
        if 'page_type' in data and isinstance(data['page_type'], str):
            data['page_type'] = PageType(data['page_type'])
        return cls(**data)


@dataclass
class DiscoveryConfiguration:
    """Configurazione per fase discovery"""
    max_pages: int = 50
    max_depth: int = 3
    timeout_per_page: int = 10000  # ms
    follow_external: bool = False
    use_sitemap: bool = True
    use_smart_crawler: bool = True  # Playwright-based
    screenshot_enabled: bool = True
    
    # Pattern esclusioni
    excluded_patterns: List[str] = field(default_factory=lambda: [
        r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
        r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', 
        r'\.mp3$', r'\.mp4$', r'\.avi$', r'\.mov$',
        r'mailto:', r'tel:', r'javascript:', r'#$',
        r'/logout', r'/signout', r'/api/', r'/admin/'
    ])
    
    # Domini permessi aggiuntivi
    allowed_domains: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscoveryConfiguration':
        return cls(**data)


@dataclass
class ScanConfiguration:
    """Configurazione per fase scanning"""
    # Scanner abilitati
    scanners_enabled: Dict[str, bool] = field(default_factory=lambda: {
        'wave': True,
        'pa11y': True,
        'axe_core': True,
        'lighthouse': True
    })
    
    # Timeout e performance
    scanner_timeout_ms: int = 30000
    parallel_scans: int = 3
    
    # Report configuration
    report_type: str = "standard"  # standard|professional
    include_screenshots: bool = True
    
    # Chiavi API
    wave_api_key: Optional[str] = None
    
    # Modalità simulazione
    simulate: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanConfiguration':
        return cls(**data)


@dataclass
class DiscoverySession:
    """Sessione discovery con stato persistente"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    base_url: str = ""
    status: SessionStatus = SessionStatus.PENDING
    
    # Configurazione
    config: DiscoveryConfiguration = field(default_factory=DiscoveryConfiguration)
    
    # Metadati sessione
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Progress tracking
    pages_discovered: int = 0
    pages_processed: int = 0
    current_page: str = ""
    progress_message: str = ""
    progress_percent: int = 0
    
    # Risultati
    discovered_pages: List[DiscoveredPage] = field(default_factory=list)
    templates_detected: int = 0
    sitemap_urls_found: int = 0
    
    # Log degli eventi
    log_messages: List[str] = field(default_factory=list)
    
    # Errori
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Path output
    output_dir: Optional[str] = None
    
    def add_log(self, message: str) -> None:
        """Aggiunge messaggio al log"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_messages.append(f"[{timestamp}] {message}")
    
    def add_error(self, error: str) -> None:
        """Aggiunge errore"""
        self.errors.append(error)
        self.add_log(f"ERRORE: {error}")
    
    def add_warning(self, warning: str) -> None:
        """Aggiunge warning"""
        self.warnings.append(warning)
        self.add_log(f"AVVISO: {warning}")
    
    def update_progress(self, percent: int, message: str = "") -> None:
        """Aggiorna progresso"""
        self.progress_percent = max(0, min(100, percent))
        if message:
            self.progress_message = message
            self.add_log(message)
    
    def get_pages_by_type(self, page_type: PageType) -> List[DiscoveredPage]:
        """Ottiene pagine di tipo specifico"""
        return [p for p in self.discovered_pages if p.page_type == page_type]
    
    def get_selected_pages(self) -> List[DiscoveredPage]:
        """Ottiene pagine selezionate per scan"""
        return [p for p in self.discovered_pages if p.selected_for_scan]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario"""
        data = asdict(self)
        data['status'] = self.status.value
        data['config'] = self.config.to_dict()
        data['discovered_pages'] = [p.to_dict() for p in self.discovered_pages]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiscoverySession':
        """Deserializza da dizionario"""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = SessionStatus(data['status'])
        if 'config' in data and isinstance(data['config'], dict):
            data['config'] = DiscoveryConfiguration.from_dict(data['config'])
        if 'discovered_pages' in data:
            data['discovered_pages'] = [
                DiscoveredPage.from_dict(p) for p in data['discovered_pages']
            ]
        return cls(**data)


@dataclass
class AccessibilityIssue:
    """Problema di accessibilità trovato durante scan"""
    code: str
    description: str
    severity: SeverityLevel
    wcag_criteria: str
    wcag_level: str  # A, AA, AAA
    selector: str = ""
    context: str = ""
    help_url: str = ""
    
    # Informazioni pagina
    page_url: str = ""
    page_title: str = ""
    
    # Scanner che ha trovato il problema
    source_scanner: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessibilityIssue':
        if 'severity' in data and isinstance(data['severity'], str):
            data['severity'] = SeverityLevel(data['severity'])
        return cls(**data)


@dataclass
class ScanSession:
    """Sessione scanning con stato persistente"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    discovery_session_id: str = ""  # Riferimento a discovery session
    
    # URLs da scansionare
    selected_pages: List[DiscoveredPage] = field(default_factory=list)
    
    # Configurazione scan
    config: ScanConfiguration = field(default_factory=ScanConfiguration)
    
    # Metadati sessione
    company_name: str = ""
    email: str = ""
    status: SessionStatus = SessionStatus.PENDING
    
    # Timestamps
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # Progress tracking
    pages_scanned: int = 0
    total_pages: int = 0
    current_page_url: str = ""
    current_scanner: str = ""
    progress_message: str = ""
    progress_percent: int = 0
    
    # Risultati aggregati
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    
    # Score compliance
    overall_score: int = 0
    compliance_level: str = "non_conforme"  # conforme|parzialmente_conforme|non_conforme
    
    # Issues trovati
    issues: List[AccessibilityIssue] = field(default_factory=list)
    
    # Log degli eventi
    log_messages: List[str] = field(default_factory=list)
    
    # Errori e warning
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Output paths
    output_dir: Optional[str] = None
    report_html_path: Optional[str] = None
    report_pdf_path: Optional[str] = None
    
    def add_log(self, message: str) -> None:
        """Aggiunge messaggio al log"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_messages.append(f"[{timestamp}] {message}")
    
    def add_error(self, error: str) -> None:
        """Aggiunge errore"""
        self.errors.append(error)
        self.add_log(f"ERRORE: {error}")
    
    def add_warning(self, warning: str) -> None:
        """Aggiunge warning"""
        self.warnings.append(warning)
        self.add_log(f"AVVISO: {warning}")
    
    def update_progress(self, percent: int, message: str = "", current_page: str = "", current_scanner: str = "") -> None:
        """Aggiorna progresso"""
        self.progress_percent = max(0, min(100, percent))
        if message:
            self.progress_message = message
            self.add_log(message)
        if current_page:
            self.current_page_url = current_page
        if current_scanner:
            self.current_scanner = current_scanner
    
    def add_issue(self, issue: AccessibilityIssue) -> None:
        """Aggiunge problema di accessibilità"""
        self.issues.append(issue)
        self.total_issues += 1
        
        # Aggiorna contatori per severità
        if issue.severity == SeverityLevel.CRITICAL:
            self.critical_issues += 1
        elif issue.severity == SeverityLevel.HIGH:
            self.high_issues += 1
        elif issue.severity == SeverityLevel.MEDIUM:
            self.medium_issues += 1
        elif issue.severity == SeverityLevel.LOW:
            self.low_issues += 1
    
    def calculate_compliance_score(self) -> None:
        """Calcola score compliance basato su problemi trovati"""
        if self.total_issues == 0:
            self.overall_score = 100
            self.compliance_level = "conforme"
            return
        
        # Formula pesata per severità
        penalty = (
            self.critical_issues * 15 +
            self.high_issues * 10 +
            self.medium_issues * 5 +
            self.low_issues * 2
        )
        
        self.overall_score = max(0, 100 - penalty)
        
        if self.overall_score >= 90:
            self.compliance_level = "conforme"
        elif self.overall_score >= 70:
            self.compliance_level = "parzialmente_conforme"
        else:
            self.compliance_level = "non_conforme"
    
    def get_issues_by_severity(self, severity: SeverityLevel) -> List[AccessibilityIssue]:
        """Ottiene problemi di severità specifica"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_wcag_level(self, wcag_level: str) -> List[AccessibilityIssue]:
        """Ottiene problemi di livello WCAG specifico"""
        return [issue for issue in self.issues if issue.wcag_level == wcag_level]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializza in dizionario"""
        data = asdict(self)
        data['status'] = self.status.value
        data['config'] = self.config.to_dict()
        data['selected_pages'] = [p.to_dict() for p in self.selected_pages]
        data['issues'] = [i.to_dict() for i in self.issues]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanSession':
        """Deserializza da dizionario"""
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = SessionStatus(data['status'])
        if 'config' in data and isinstance(data['config'], dict):
            data['config'] = ScanConfiguration.from_dict(data['config'])
        if 'selected_pages' in data:
            data['selected_pages'] = [
                DiscoveredPage.from_dict(p) for p in data['selected_pages']
            ]
        if 'issues' in data:
            data['issues'] = [
                AccessibilityIssue.from_dict(i) for i in data['issues']
            ]
        return cls(**data)


@dataclass
class WebSocketEvent:
    """Evento WebSocket per real-time updates"""
    event_type: str  # discovery_progress|discovery_complete|scan_progress|scan_complete|error
    session_id: str
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketEvent':
        return cls(**data)


# Modelli per richieste API
@dataclass
class DiscoveryStartRequest:
    """Richiesta avvio discovery"""
    base_url: str
    config: Optional[Dict[str, Any]] = None
    
    def get_config(self) -> DiscoveryConfiguration:
        if self.config:
            return DiscoveryConfiguration.from_dict(self.config)
        return DiscoveryConfiguration()


@dataclass
class ScanStartRequest:
    """Richiesta avvio scan"""
    discovery_session_id: str
    selected_page_urls: List[str]  # URLs delle pagine da scansionare
    company_name: str
    email: str
    config: Optional[Dict[str, Any]] = None
    
    def get_config(self) -> ScanConfiguration:
        if self.config:
            return ScanConfiguration.from_dict(self.config)
        return ScanConfiguration()
