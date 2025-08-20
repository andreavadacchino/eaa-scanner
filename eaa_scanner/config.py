from __future__ import annotations

import dataclasses as dc
import os
import re
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class ScannerToggles(BaseModel):
    """Configurazione per abilitazione/disabilitazione scanner"""
    wave: bool = Field(default=True, description="Abilita scanner WAVE (richiede API key)")
    pa11y: bool = Field(default=True, description="Abilita scanner Pa11y")
    axe_core: bool = Field(default=True, description="Abilita scanner Axe-core")
    lighthouse: bool = Field(default=True, description="Abilita scanner Lighthouse")


class Config(BaseModel):
    """Configurazione principale per EAA Scanner"""
    url: str = Field(..., description="URL da scansionare")
    company_name: str = Field(default="", description="Nome azienda")
    email: str = Field(default="", description="Email di contatto")
    
    # API Keys
    wave_api_key: Optional[str] = Field(default="", description="WAVE API key (opzionale)")
    openai_api_key: Optional[str] = Field(default="", description="OpenAI API key (opzionale)")
    
    # LLM Configuration
    llm_model_primary: str = Field(default="gpt-4o", description="Modello LLM primario")
    llm_model_fallback: str = Field(default="gpt-3.5-turbo", description="Modello LLM di fallback")
    llm_enabled: bool = Field(default=True, description="Abilita generazione contenuti via LLM")
    
    # Notifiche
    telegram_bot_token: Optional[str] = Field(default="", description="Token bot Telegram")
    telegram_chat_id: Optional[str] = Field(default="", description="Chat ID Telegram")
    
    # SMTP
    smtp_host: Optional[str] = Field(default="", description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: Optional[str] = Field(default="", description="SMTP username")
    smtp_pass: Optional[str] = Field(default="", description="SMTP password")
    smtp_from: Optional[str] = Field(default="accessibility@azienda.it", description="Email mittente")
    notify_email_to: Optional[str] = Field(default="", description="Email destinatari notifiche")
    
    # Scanner config
    scanners_enabled: ScannerToggles = Field(default_factory=ScannerToggles)

    report_language: str = Field(default="it", description="Lingua del report")
    include_recommendations: bool = Field(default=True, description="Includi raccomandazioni")
    detailed_analysis: bool = Field(default=True, description="Analisi dettagliata")
    
    scanner_timeout_ms: int = Field(default=60000, description="Timeout scanner in ms")
    max_retries: int = Field(default=2, description="Numero massimo di retry")
    
    # PDF Generation
    pdf_engine: str = Field(default="auto", description="Engine PDF (auto, weasyprint, chrome, wkhtmltopdf)")
    pdf_page_format: str = Field(default="A4", description="Formato pagina PDF")
    pdf_margins: Optional[str] = Field(default=None, description="Margini PDF (formato: top,right,bottom,left in pollici)")
    
    wcag_version: str = Field(default="2.1", description="Versione WCAG")
    wcag_level: str = Field(default="AA", description="Livello WCAG")
    eaa_compliance: bool = Field(default=True, description="Verifica compliance EAA")
    
    simulate: bool = Field(default=True, description="Modalità simulata (offline)")
    
    # Runtime
    out_dir: str = Field(default="output", description="Directory output")
    log_level: str = Field(default="INFO", description="Livello di logging")

    @classmethod
    def from_env_or_args(cls, args: Dict[str, Any]) -> "Config":
        def pick(*keys: str, default: str = "") -> str:
            for k in keys:
                if k in args and args[k]:
                    return str(args[k])
                v = os.getenv(k.upper(), "")
                if v:
                    return v
            return default
        
        def pick_with_api_manager(*keys: str, default: str = "") -> str:
            """Pick value with API Key Manager fallback"""
            # Prima prova args e env variables
            value = pick(*keys, default=default)
            if value and value != default:
                return value
            
            # Fallback a API Key Manager se disponibile
            try:
                from webapp.api_key_manager import get_api_key_manager
                manager = get_api_key_manager()
                
                # Mappa le chiavi ai tipi del manager
                if any('wave' in k.lower() for k in keys):
                    api_key = manager.get_key('wave')
                    if api_key:
                        return api_key
                elif any('openai' in k.lower() for k in keys):
                    api_key = manager.get_key('openai')
                    if api_key:
                        return api_key
            except ImportError:
                # API Key Manager non disponibile
                pass
            
            return default

        # Auto-disabilita WAVE se non c'è API key
        wave_enabled = bool(pick_with_api_manager("wave_api_key", "wave_key")) and _parse_bool(pick("wave", default="true"))
        
        toggles = ScannerToggles(
            wave=wave_enabled,
            pa11y=_parse_bool(pick("pa11y", default="true")),
            axe_core=_parse_bool(pick("axe_core", default="true")),
            lighthouse=_parse_bool(pick("lighthouse", default="true")),
        )
        
        if not pick_with_api_manager("wave_api_key", "wave_key") and wave_enabled:
            logger.info("WAVE disabilitato: API key non presente")

        cfg = cls(
            url=pick("url"),
            company_name=pick("company_name", "company"),
            email=pick("email", "contact_email"),
            wave_api_key=pick_with_api_manager("wave_api_key", "wave_key"),
            openai_api_key=pick_with_api_manager("openai_api_key", "openai_key"),
            llm_model_primary=pick("llm_model_primary", "llm_model", default="gpt-4o"),
            llm_model_fallback=pick("llm_model_fallback", default="gpt-3.5-turbo"),
            llm_enabled=_parse_bool(pick("llm_enabled", default="true")),
            telegram_bot_token=pick("telegram_bot_token"),
            telegram_chat_id=pick("telegram_chat_id"),
            smtp_host=pick("smtp_host"),
            smtp_port=int(pick("smtp_port", default="587")),
            smtp_user=pick("smtp_user"),
            smtp_pass=pick("smtp_pass"),
            smtp_from=pick("smtp_from", default="accessibility@azienda.it"),
            notify_email_to=pick("notify_email_to"),
            scanners_enabled=toggles,
            report_language=pick("report_language", "language", default="it"),
            include_recommendations=_parse_bool(pick("include_recommendations", default="true")),
            detailed_analysis=_parse_bool(pick("detailed_analysis", default="true")),
            scanner_timeout_ms=int(pick("scanner_timeout_ms", "scanner_timeout", default="60000")),
            max_retries=int(pick("max_retries", default="2")),
            wcag_version=pick("wcag_version", default="2.1"),
            wcag_level=pick("wcag_level", default="AA"),
            eaa_compliance=_parse_bool(pick("eaa_compliance", default="true")),
            out_dir=pick("out_dir", default="output"),
            log_level=pick("log_level", default="INFO"),
            simulate=_parse_bool(pick("simulate", default=str(args.get("simulate", True)).lower())),
        )
        return cfg

    def validate(self) -> None:
        errors = []
        if not self.url or not _is_valid_url(self.url):
            errors.append("url mancante o non valida")
        if not self.company_name or len(self.company_name.strip()) < 2:
            errors.append("company_name mancante o troppo corto")
        if not self.email or not _looks_like_email(self.email):
            errors.append("email mancante o non valida")
        if errors:
            raise ValueError("Configurazione non valida: " + "; ".join(errors))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "company_name": self.company_name,
            "email": self.email,
            "wave_api_key": self.wave_api_key,
            "openai_api_key": bool(self.openai_api_key),
            "llm_model_primary": self.llm_model_primary,
            "llm_model_fallback": self.llm_model_fallback,
            "llm_enabled": self.llm_enabled,
            "telegram_bot_token": bool(self.telegram_bot_token),
            "telegram_chat_id": self.telegram_chat_id,
            "scanners_enabled": dc.asdict(self.scanners_enabled),
            "report_language": self.report_language,
            "include_recommendations": self.include_recommendations,
            "detailed_analysis": self.detailed_analysis,
            "scanner_timeout_ms": self.scanner_timeout_ms,
            "max_retries": self.max_retries,
            "wcag_version": self.wcag_version,
            "wcag_level": self.wcag_level,
            "eaa_compliance": self.eaa_compliance,
            "simulate": self.simulate,
        }
    
    def get_pdf_margins_dict(self) -> Dict[str, float]:
        """Converte stringa margini in dict per PDF engines"""
        if not self.pdf_margins:
            return {'top': 1, 'right': 0.75, 'bottom': 1, 'left': 0.75}
        
        try:
            parts = [float(x.strip()) for x in self.pdf_margins.split(',')]
            if len(parts) == 1:
                # Margini uniformi
                return {'top': parts[0], 'right': parts[0], 'bottom': parts[0], 'left': parts[0]}
            elif len(parts) == 4:
                # Top, Right, Bottom, Left
                return {'top': parts[0], 'right': parts[1], 'bottom': parts[2], 'left': parts[3]}
            else:
                logger.warning(f"Formato margini PDF non valido: {self.pdf_margins}, usando default")
                return {'top': 1, 'right': 0.75, 'bottom': 1, 'left': 0.75}
        except (ValueError, IndexError):
            logger.warning(f"Errore parsing margini PDF: {self.pdf_margins}, usando default")
            return {'top': 1, 'right': 0.75, 'bottom': 1, 'left': 0.75}


def _parse_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def _is_valid_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in {"http", "https"} and bool(u.netloc)
    except Exception:
        return False


def _looks_like_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def new_scan_id(prefix: str = "eaa") -> str:
    return f"{prefix}_{int(time.time()*1000)}"

