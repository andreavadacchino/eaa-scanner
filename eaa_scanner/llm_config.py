"""
Configurazione e gestione LLM per generazione report intelligenti.
Supporta OpenAI con fallback multi-modello e circuit breaker pattern.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    print("⚠️ OpenAI SDK non installato. Installare con: pip install openai")

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Livelli di modello con priorità decrescente - Aggiornato Agosto 2025"""
    # GPT-5 Series (Latest 2025)
    GPT5 = "gpt-5"  # $1.25/$10 per 1M tokens
    GPT5_MINI = "gpt-5-mini"  # Più economico
    GPT5_NANO = "gpt-5-nano"  # Il più veloce ed economico
    
    # O-Series Reasoning Models (2025)
    O3 = "o3"  # Premium reasoning, 200K context
    O4_MINI = "o4-mini"  # Economico per math/coding
    
    # GPT-4.1 Series (Extended Context)
    GPT41 = "gpt-4.1"  # 1M tokens context
    GPT41_MINI = "gpt-4.1-mini"  # 83% più economico
    
    # Legacy Models (Backward compatibility)
    PRIMARY = "gpt-4o"  # Compatibilità esistente
    SECONDARY = "gpt-4-turbo-preview"  # Fallback premium
    TERTIARY = "gpt-4o-mini"  # $0.15/$0.60 per 1M tokens
    QUATERNARY = "gpt-3.5-turbo"  # Ultimo fallback


# Model information and pricing (August 2025)
MODEL_INFO = {
    "gpt-5": {
        "name": "GPT-5",
        "context": 400000,
        "max_output": 128000,
        "input_price": 1.25,  # per 1M tokens
        "output_price": 10.0,
        "description": "Modello unificato più avanzato con reasoning integrato"
    },
    "gpt-5-mini": {
        "name": "GPT-5 Mini",
        "context": 272000,
        "max_output": 128000,
        "input_price": 0.5,
        "output_price": 2.0,
        "description": "Versione ottimizzata per velocità e costi"
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "context": 272000,
        "max_output": 128000,
        "input_price": 0.25,
        "output_price": 1.0,
        "description": "Il più veloce ed economico della serie GPT-5"
    },
    "o3": {
        "name": "O3 Reasoning",
        "context": 200000,
        "max_output": 100000,
        "input_price": 5.0,
        "output_price": 15.0,
        "description": "Premium reasoning model, 20% meno errori"
    },
    "o4-mini": {
        "name": "O4 Mini",
        "context": 200000,
        "max_output": 100000,
        "input_price": 1.0,
        "output_price": 4.0,
        "description": "Reasoning economico per math e coding"
    },
    "gpt-4.1": {
        "name": "GPT-4.1",
        "context": 1000000,
        "max_output": 100000,
        "input_price": 2.0,
        "output_price": 8.0,
        "description": "Context esteso fino a 1M tokens"
    },
    "gpt-4.1-mini": {
        "name": "GPT-4.1 Mini",
        "context": 1000000,
        "max_output": 100000,
        "input_price": 0.3,
        "output_price": 1.2,
        "description": "83% più economico di GPT-4o"
    },
    "gpt-4o": {
        "name": "GPT-4o",
        "context": 128000,
        "max_output": 4096,
        "input_price": 5.0,
        "output_price": 15.0,
        "description": "Modello legacy, in fase di sostituzione"
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "context": 128000,
        "max_output": 16384,
        "input_price": 0.15,
        "output_price": 0.60,
        "description": "Opzione economica per casi semplici"
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "context": 16385,
        "max_output": 4096,
        "input_price": 0.5,
        "output_price": 1.5,
        "description": "Modello base veloce ed economico"
    }
}


@dataclass
class CircuitBreakerConfig:
    """Configurazione circuit breaker per resilienza"""
    failure_threshold: int = 3
    recovery_timeout: int = 60  # secondi
    half_open_requests: int = 1


class CircuitBreaker:
    """Circuit breaker per gestire errori API"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def record_success(self):
        """Registra successo e resetta contatori"""
        self.failure_count = 0
        self.state = "closed"
        
    def record_failure(self):
        """Registra fallimento e aggiorna stato"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker aperto dopo {self.failure_count} fallimenti")
    
    def can_attempt(self) -> bool:
        """Verifica se possiamo tentare una chiamata"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            # Controlla se è tempo di provare recovery
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed > self.config.recovery_timeout:
                    self.state = "half-open"
                    logger.info("Circuit breaker in stato half-open per test recovery")
                    return True
            return False
            
        # half-open: permettiamo un tentativo
        return True


class LLMManager:
    """Gestore principale per interazioni LLM"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Prova in ordine: parametro, env var, API Key Manager
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Fallback ad API Key Manager se disponibile
        if not self.api_key:
            try:
                from webapp.api_key_manager import get_api_key_manager
                manager = get_api_key_manager()
                manager_key = manager.get_key('openai')
                if manager_key:
                    self.api_key = manager_key
                    logger.info("API key OpenAI caricata da API Key Manager")
            except ImportError:
                pass  # API Key Manager non disponibile
        
        self.client = None
        self.circuit_breakers = {}
        self.prompt_cache = {}
        self.init_client()
        
    def init_client(self):
        """Inizializza client OpenAI"""
        if not self.api_key:
            logger.warning("API key OpenAI non configurata")
            return
            
        if not OpenAI:
            logger.error("OpenAI SDK non disponibile")
            return
            
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("Client OpenAI inizializzato con successo")
        except Exception as e:
            logger.error(f"Errore inizializzazione OpenAI: {e}")
            
    def get_circuit_breaker(self, model: str) -> CircuitBreaker:
        """Ottiene o crea circuit breaker per modello"""
        if model not in self.circuit_breakers:
            self.circuit_breakers[model] = CircuitBreaker(CircuitBreakerConfig())
        return self.circuit_breakers[model]
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model_tier: Optional[ModelTier] = None
    ) -> Optional[str]:
        """
        Genera testo con fallback automatico tra modelli.
        
        Args:
            prompt: Prompt utente
            system_prompt: Prompt di sistema opzionale
            temperature: Creatività (0.0-1.0)
            max_tokens: Lunghezza massima risposta
            model_tier: Tier specifico o None per cascata
            
        Returns:
            Testo generato o None se errore
        """
        if not self.client:
            logger.warning("Client OpenAI non disponibile, uso fallback locale")
            return self._generate_fallback(prompt)
        
        # Ordine modelli da provare
        models_to_try = [model_tier.value] if model_tier else [
            ModelTier.PRIMARY.value,
            ModelTier.SECONDARY.value,
            ModelTier.TERTIARY.value,
            ModelTier.QUATERNARY.value
        ]
        
        for model in models_to_try:
            breaker = self.get_circuit_breaker(model)
            
            if not breaker.can_attempt():
                logger.debug(f"Circuit breaker aperto per {model}, skip")
                continue
                
            try:
                logger.info(f"Tentativo generazione con {model}")
                
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=30
                )
                
                result = response.choices[0].message.content
                breaker.record_success()
                logger.info(f"Generazione completata con {model}")
                return result
                
            except Exception as e:
                logger.error(f"Errore con {model}: {e}")
                breaker.record_failure()
                
                # Se è rate limit, aspetta un po'
                if "rate_limit" in str(e).lower():
                    time.sleep(2)
                continue
        
        # Tutti i modelli falliti, usa fallback locale
        logger.warning("Tutti i modelli LLM falliti, uso generazione locale")
        return self._generate_fallback(prompt)
    
    def _generate_fallback(self, prompt: str) -> str:
        """Generazione fallback senza LLM"""
        logger.info("Uso template fallback senza LLM")
        
        # Analizza tipo di contenuto richiesto
        if "executive summary" in prompt.lower():
            return self._fallback_executive_summary()
        elif "raccomandazioni" in prompt.lower():
            return self._fallback_recommendations()
        elif "piano" in prompt.lower() and "remediation" in prompt.lower():
            return self._fallback_remediation_plan()
        else:
            return self._fallback_generic()
    
    def _fallback_executive_summary(self) -> str:
        """Template fallback per executive summary"""
        return """
## Executive Summary

L'analisi di accessibilità condotta ha identificato diverse aree che richiedono attenzione 
per garantire la piena conformità agli standard WCAG 2.1 AA e alla normativa europea EAA.

### Risultati Principali
- Il sito presenta barriere significative per utenti con disabilità
- Sono stati identificati problemi critici che impediscono l'accesso ai contenuti principali
- La navigazione da tastiera risulta compromessa in diverse sezioni
- I contenuti multimediali mancano di alternative accessibili

### Priorità di Intervento
1. **Immediato**: Correzione errori critici di navigazione
2. **Breve termine**: Implementazione alternative testuali
3. **Medio termine**: Ottimizzazione contrasti e leggibilità
4. **Lungo termine**: Revisione completa architettura informativa

L'implementazione delle raccomandazioni proposte permetterà di raggiungere
un livello di conformità adeguato e migliorare significativamente l'esperienza
per tutti gli utenti.
"""
    
    def _fallback_recommendations(self) -> str:
        """Template fallback per raccomandazioni"""
        return """
## Raccomandazioni Tecniche

### 1. Struttura e Semantica
- Implementare una gerarchia corretta degli heading (h1-h6)
- Utilizzare elementi HTML semantici appropriati
- Aggiungere landmark ARIA per migliorare la navigazione

### 2. Navigazione da Tastiera
- Garantire che tutti gli elementi interattivi siano raggiungibili via tastiera
- Implementare indicatori di focus visibili
- Rispettare l'ordine logico di tabulazione

### 3. Contenuti Multimediali
- Fornire trascrizioni per contenuti audio
- Aggiungere sottotitoli ai video
- Implementare descrizioni audio per contenuti visivi complessi

### 4. Form e Input
- Associare label a tutti i campi form
- Fornire istruzioni chiare e messaggi di errore descrittivi
- Implementare validazione accessibile lato client

### 5. Contrasto e Leggibilità
- Verificare rapporti di contrasto minimi (4.5:1 per testo normale)
- Evitare l'uso del colore come unico mezzo di comunicazione
- Garantire leggibilità con zoom fino al 200%
"""
    
    def _fallback_remediation_plan(self) -> str:
        """Template fallback per piano remediation"""
        return """
## Piano di Remediation

### Fase 1: Interventi Critici (0-30 giorni)
- **Settimana 1-2**: Correzione errori bloccanti
  - Fix navigazione tastiera
  - Aggiunta alt text mancanti
  - Correzione heading structure
  
- **Settimana 3-4**: Test e validazione
  - Test con screen reader
  - Validazione WCAG automatica
  - User testing con utenti disabili

### Fase 2: Miglioramenti Strutturali (30-90 giorni)
- **Mese 2**: Ottimizzazione form e interazioni
  - Revisione tutti i form
  - Implementazione ARIA labels
  - Miglioramento feedback utente
  
- **Mese 3**: Contenuti multimediali
  - Aggiunta sottotitoli
  - Creazione trascrizioni
  - Implementazione player accessibili

### Fase 3: Ottimizzazione Continua (90+ giorni)
- Monitoraggio continuo conformità
- Formazione team sviluppo
- Implementazione processo QA accessibilità
- Aggiornamento documentazione

### Risorse Necessarie
- **Team**: 2 sviluppatori frontend, 1 UX designer, 1 accessibility specialist
- **Tools**: Screen reader, automated testing tools, user testing platform
- **Budget stimato**: Da definire in base alla complessità
- **Tempi**: 3-6 mesi per conformità completa
"""
    
    def _fallback_generic(self) -> str:
        """Template generico fallback"""
        return """
Il contenuto richiesto non può essere generato automaticamente in questo momento.
Si consiglia di consultare un esperto di accessibilità per una valutazione dettagliata
e raccomandazioni personalizzate basate sui risultati specifici della scansione.

Per assistenza, contattare il team di supporto tecnico.
"""
    
    def load_prompt_template(self, template_name: str, variables: Dict[str, Any] = None) -> str:
        """
        Carica e processa template prompt da file markdown.
        
        Args:
            template_name: Nome del template (senza estensione)
            variables: Dizionario con variabili da sostituire
            
        Returns:
            Prompt processato
        """
        # Check cache first
        cache_key = f"{template_name}_{hash(str(variables))}"
        if cache_key in self.prompt_cache:
            logger.debug(f"Uso prompt da cache: {template_name}")
            return self.prompt_cache[cache_key]
        
        # Load template
        template_path = Path(__file__).parent / "prompts" / f"{template_name}.md"
        
        if not template_path.exists():
            logger.error(f"Template non trovato: {template_path}")
            return f"[Template {template_name} non trovato]"
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Replace variables
            if variables:
                for key, value in variables.items():
                    placeholder = f"{{{{{key}}}}}"
                    template = template.replace(placeholder, str(value))
            
            # Cache processed template
            self.prompt_cache[cache_key] = template
            
            return template
            
        except Exception as e:
            logger.error(f"Errore caricamento template {template_name}: {e}")
            return f"[Errore caricamento template {template_name}]"
    
    def generate_report_section(
        self,
        section_type: str,
        scan_data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Genera una sezione specifica del report.
        
        Args:
            section_type: Tipo di sezione (executive_summary, recommendations, etc.)
            scan_data: Dati della scansione
            **kwargs: Parametri aggiuntivi per generazione
            
        Returns:
            Contenuto HTML/Markdown della sezione
        """
        logger.info(f"Generazione sezione report: {section_type}")
        
        # Prepara variabili per template
        variables = {
            "company_name": scan_data.get("company_name", "Azienda"),
            "url": scan_data.get("url", ""),
            "scan_date": scan_data.get("scan_date", ""),
            "total_issues": scan_data.get("total_issues", 0),
            "critical_issues": scan_data.get("critical_issues", 0),
            "compliance_score": scan_data.get("compliance_score", 0),
            "wcag_level": scan_data.get("wcag_level", "AA"),
            **kwargs
        }
        
        # Carica prompt template
        prompt = self.load_prompt_template(f"{section_type}_prompt", variables)
        
        # Genera con LLM
        system_prompt = """Sei un esperto di accessibilità web e conformità WCAG.
Genera contenuti professionali in italiano per report di accessibilità.
Usa un tono professionale ma comprensibile, evita tecnicismi eccessivi.
Formatta l'output in Markdown pulito."""
        
        content = self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=kwargs.get("max_tokens", 2000)
        )
        
        return content or f"[Sezione {section_type} non disponibile]"
    
    def estimate_tokens(self, text: str) -> int:
        """Stima approssimativa dei token"""
        # Approssimazione: ~4 caratteri per token
        return len(text) // 4
    
    def validate_api_key(self) -> bool:
        """Valida che l'API key sia configurata e funzionante"""
        if not self.api_key:
            return False
            
        if not self.client:
            return False
            
        try:
            # Test minimo con modello economico
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error(f"Validazione API key fallita: {e}")
            return False


# Singleton globale
_llm_manager = None


def get_llm_manager(api_key: Optional[str] = None) -> LLMManager:
    """Factory per ottenere istanza singleton di LLMManager"""
    global _llm_manager
    
    if _llm_manager is None:
        _llm_manager = LLMManager(api_key)
    
    return _llm_manager


# Funzioni di utilità per uso diretto
def generate_executive_summary(scan_data: Dict[str, Any]) -> str:
    """Genera executive summary per report"""
    manager = get_llm_manager()
    return manager.generate_report_section("executive_summary", scan_data)


def generate_recommendations(scan_data: Dict[str, Any], issues: List[Dict]) -> str:
    """Genera raccomandazioni basate sui problemi trovati"""
    manager = get_llm_manager()
    return manager.generate_report_section(
        "recommendations", 
        scan_data,
        issues_summary=json.dumps(issues[:10], ensure_ascii=False)  # Prime 10 issue
    )


def generate_remediation_plan(scan_data: Dict[str, Any], timeline: str = "3_months") -> str:
    """Genera piano di remediation dettagliato"""
    manager = get_llm_manager()
    return manager.generate_report_section(
        "remediation_plan",
        scan_data,
        timeline=timeline,
        priority_issues=scan_data.get("priority_issues", [])
    )


def generate_accessibility_statement(scan_data: Dict[str, Any]) -> str:
    """Genera dichiarazione di accessibilità"""
    manager = get_llm_manager()
    return manager.generate_report_section(
        "accessibility_statement",
        scan_data,
        conformity_status=scan_data.get("conformity_status", "parzialmente_conforme")
    )