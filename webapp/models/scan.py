"""
Pydantic models for scan validation
Following WCAG 2.2 and EAA compliance standards
"""

from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator, ConfigDict

# ==================== SCANNER CONFIGURATION ====================

class ScannerConfig(BaseModel):
    """Individual scanner configuration"""
    enabled: bool = True
    timeout: int = Field(default=60, ge=10, le=300)
    options: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra="forbid")

class ScannerToggles(BaseModel):
    """Scanner enable/disable configuration"""
    wave: ScannerConfig = Field(default_factory=lambda: ScannerConfig(enabled=False))
    axe: ScannerConfig = Field(default_factory=ScannerConfig)
    lighthouse: ScannerConfig = Field(default_factory=ScannerConfig)
    pa11y: ScannerConfig = Field(default_factory=ScannerConfig)
    
    @validator('*')
    def validate_scanner_config(cls, v):
        if not isinstance(v, ScannerConfig):
            raise ValueError("Invalid scanner configuration")
        return v

# ==================== SCAN REQUESTS ====================

class ScanOptions(BaseModel):
    """Advanced scan options"""
    max_pages: int = Field(default=10, ge=1, le=100)
    crawl_depth: int = Field(default=2, ge=1, le=5)
    include_subdomains: bool = False
    follow_redirects: bool = True
    user_agent: Optional[str] = None
    viewport_width: int = Field(default=1920, ge=320, le=3840)
    viewport_height: int = Field(default=1080, ge=240, le=2160)
    wait_for_selector: Optional[str] = None
    extra_headers: Dict[str, str] = Field(default_factory=dict)
    
    model_config = ConfigDict(extra="forbid")

class ScanRequest(BaseModel):
    """Main scan request model"""
    url: HttpUrl
    company_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    scannerConfig: ScannerToggles = Field(default_factory=ScannerToggles)
    options: ScanOptions = Field(default_factory=ScanOptions)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('url')
    def validate_url(cls, v):
        url_str = str(v)
        if not url_str.startswith(('http://', 'https://')):
            raise ValueError('URL must use HTTP or HTTPS protocol')
        if 'localhost' in url_str and not url_str.startswith('http://localhost'):
            raise ValueError('Localhost URLs must use HTTP protocol')
        return v
    
    @validator('company_name')
    def clean_company_name(cls, v):
        return v.strip()
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "company_name": "ACME Corporation",
                "email": "compliance@example.com",
                "scannerConfig": {
                    "wave": {"enabled": True},
                    "axe": {"enabled": True},
                    "lighthouse": {"enabled": True},
                    "pa11y": {"enabled": True}
                }
            }
        }
    )

class BulkScanRequest(BaseModel):
    """Request for scanning multiple URLs"""
    urls: List[HttpUrl] = Field(..., min_items=1, max_items=10)
    company_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    scannerConfig: ScannerToggles = Field(default_factory=ScannerToggles)
    options: ScanOptions = Field(default_factory=ScanOptions)
    
    @validator('urls')
    def validate_unique_urls(cls, v):
        if len(v) != len(set(str(url) for url in v)):
            raise ValueError('Duplicate URLs not allowed')
        return v

class PageScanRequest(BaseModel):
    """Request for scanning a specific page"""
    page_url: HttpUrl
    parent_scan_id: str
    page_number: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=1)

# ==================== SCAN STATUS & RESULTS ====================

class ScanStatus(BaseModel):
    """Scan status response"""
    scan_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress: int = Field(..., ge=0, le=100)
    message: Optional[str] = None
    current_phase: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scan_id": "abc123",
                "status": "running",
                "progress": 45,
                "message": "Scanning with Lighthouse",
                "current_phase": "accessibility_testing",
                "created_at": "2025-01-01T10:00:00",
                "updated_at": "2025-01-01T10:05:00"
            }
        }
    )

class IssueDetail(BaseModel):
    """Individual accessibility issue"""
    code: str
    message: str
    severity: Literal["critical", "high", "medium", "low"]
    wcag_criterion: str
    element: Optional[str] = None
    selector: Optional[str] = None
    context: Optional[str] = None
    recommendation: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")

class ScannerResult(BaseModel):
    """Result from individual scanner"""
    scanner_name: str
    status: Literal["success", "failed", "timeout", "skipped"]
    duration_ms: int
    issues_found: int
    issues: List[IssueDetail] = Field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ComplianceMetrics(BaseModel):
    """EAA compliance metrics"""
    compliance_score: float = Field(..., ge=0, le=100)
    compliance_level: Literal["compliant", "partially_compliant", "non_compliant"]
    total_issues: int = Field(..., ge=0)
    critical_issues: int = Field(..., ge=0)
    high_issues: int = Field(..., ge=0)
    medium_issues: int = Field(..., ge=0)
    low_issues: int = Field(..., ge=0)
    wcag_aa_pass: bool
    wcag_aaa_pass: bool
    
    @validator('compliance_level')
    def validate_compliance_level(cls, v, values):
        score = values.get('compliance_score', 0)
        if score >= 90 and v != 'compliant':
            raise ValueError('Score >= 90 should be compliant')
        elif 70 <= score < 90 and v != 'partially_compliant':
            raise ValueError('Score 70-89 should be partially_compliant')
        elif score < 70 and v != 'non_compliant':
            raise ValueError('Score < 70 should be non_compliant')
        return v

class ScanResult(BaseModel):
    """Complete scan results"""
    scan_id: str
    url: str
    company_name: str
    scan_date: datetime
    pages_scanned: int = Field(..., ge=1)
    total_time_ms: int = Field(..., ge=0)
    
    # Scanner results
    scanner_results: List[ScannerResult]
    
    # Aggregated metrics
    metrics: ComplianceMetrics
    
    # Detailed issues
    all_issues: List[IssueDetail]
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scan_id": "abc123",
                "url": "https://example.com",
                "company_name": "ACME Corporation",
                "scan_date": "2025-01-01T10:00:00",
                "pages_scanned": 5,
                "total_time_ms": 45000,
                "metrics": {
                    "compliance_score": 85.5,
                    "compliance_level": "partially_compliant",
                    "total_issues": 42,
                    "critical_issues": 2,
                    "high_issues": 8,
                    "medium_issues": 15,
                    "low_issues": 17,
                    "wcag_aa_pass": False,
                    "wcag_aaa_pass": False
                }
            }
        }
    )

# ==================== REPORT GENERATION ====================

class ReportSection(BaseModel):
    """Report section configuration"""
    name: Literal[
        "summary",
        "issues",
        "recommendations",
        "technical_details",
        "wcag_compliance",
        "remediation_plan"
    ]
    enabled: bool = True
    language: Literal["it", "en", "es", "fr", "de"] = "it"

class ReportGenerationRequest(BaseModel):
    """Request for AI-enhanced report generation"""
    scan_id: str
    model: Literal[
        "gpt-5",            # Latest generation, 200k context - $1.25/$10.00 per 1M tokens
        "gpt-5-mini",       # Efficient next-gen, 200k context - $0.25/$2.00 per 1M tokens
        "gpt-5-nano",       # Ultra-efficient, 100k context - $0.05/$0.40 per 1M tokens
        "gpt-5-chat-latest",# Latest conversational - $1.25/$10.00 per 1M tokens
        "gpt-4o",           # Previous multimodal model, 128k context - $2.50/$10.00 per 1M tokens
        "gpt-4o-mini",      # Cost-efficient, 128k context - $0.15/$0.60 per 1M tokens  
        "gpt-4-turbo",      # High performance, 128k context - $10.00/$30.00 per 1M tokens
        "gpt-4",            # Previous generation, 8k context - $30.00/$60.00 per 1M tokens
        "gpt-3.5-turbo"     # Legacy model, 16k context - $0.50/$1.50 per 1M tokens
    ] = "gpt-4o"
    api_key: str = Field(..., min_length=20)
    sections: List[ReportSection] = Field(
        default_factory=lambda: [
            ReportSection(name="summary"),
            ReportSection(name="issues"),
            ReportSection(name="recommendations")
        ]
    )
    output_format: Literal["html", "pdf", "json", "markdown"] = "html"
    include_technical_details: bool = False
    include_remediation_costs: bool = False
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v
    
    model_config = ConfigDict(extra="forbid")