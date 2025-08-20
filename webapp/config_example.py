"""
Configurazione esempio per LLM backend.
Copia questo file come config.py e personalizza i valori.
"""

import os

# ============ CONFIGURAZIONE LLM ============

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Lascia vuoto per input da UI
OPENAI_DEFAULT_MODEL = "gpt-4o"  # gpt-4o, gpt-4o-mini, gpt-4-turbo-preview
OPENAI_MAX_TOKENS = 2000
OPENAI_TEMPERATURE = 0.7

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 5  # Richieste per minuto per IP
RATE_LIMIT_WINDOW_SECONDS = 60

# Cache Settings
VALIDATION_CACHE_TTL = 600  # 10 minuti
CLEANUP_INTERVAL_HOURS = 1

# ============ CONFIGURAZIONE SICUREZZA ============

# Whitelist IP (opzionale, non implementato)
RATE_LIMIT_WHITELIST = [
    "127.0.0.1",
    "::1"
]

# Maximum costs per request (USD)
MAX_COST_PER_REQUEST = 5.0
MAX_COST_WARNING_THRESHOLD = 1.0

# Maximum sections per request
MAX_SECTIONS_PER_REQUEST = 7
MAX_PAGES_PER_SCAN = 100

# ============ CONFIGURAZIONE SEZIONI ============

# Sezioni disponibili con metadati
AVAILABLE_SECTIONS = {
    "executive_summary": {
        "name": "Executive Summary",
        "description": "Riassunto esecutivo per decision makers",
        "estimated_tokens": 800,
        "complexity": "low",
        "enabled": True
    },
    "technical_analysis": {
        "name": "Analisi Tecnica",
        "description": "Analisi dettagliata dei risultati tecnici",
        "estimated_tokens": 1200,
        "complexity": "high",
        "enabled": True
    },
    "recommendations": {
        "name": "Raccomandazioni",
        "description": "Suggerimenti prioritizzati per miglioramenti",
        "estimated_tokens": 1000,
        "complexity": "medium",
        "enabled": True
    },
    "remediation_plan": {
        "name": "Piano di Remediation",
        "description": "Piano dettagliato per risolvere i problemi",
        "estimated_tokens": 1500,
        "complexity": "high",
        "enabled": True
    },
    "accessibility_statement": {
        "name": "Dichiarazione di Accessibilità",
        "description": "Dichiarazione formale di conformità",
        "estimated_tokens": 600,
        "complexity": "low",
        "enabled": True
    },
    "compliance_matrix": {
        "name": "Matrice di Conformità",
        "description": "Mappatura dettagliata standard WCAG",
        "estimated_tokens": 900,
        "complexity": "medium",
        "enabled": False  # Sperimentale
    },
    "user_impact_analysis": {
        "name": "Analisi Impatto Utenti",
        "description": "Valutazione impatto su diverse categorie di utenti",
        "estimated_tokens": 800,
        "complexity": "medium",
        "enabled": False  # Sperimentale
    }
}

# ============ CONFIGURAZIONE MODELLI ============

# Modelli supportati con metadati
SUPPORTED_MODELS = {
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Modello principale, veloce ed economico",
        "recommended": True,
        "max_tokens": 4096,
        "pricing": {"input": 0.005, "output": 0.015},
        "enabled": True
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Versione economica per test",
        "recommended": False,
        "max_tokens": 4096,
        "pricing": {"input": 0.00015, "output": 0.0006},
        "enabled": True
    },
    "gpt-4-turbo-preview": {
        "name": "GPT-4 Turbo",
        "description": "Modello premium per casi complessi",
        "recommended": False,
        "max_tokens": 4096,
        "pricing": {"input": 0.01, "output": 0.03},
        "enabled": True
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "description": "Modello legacy economico",
        "recommended": False,
        "max_tokens": 4096,
        "pricing": {"input": 0.0005, "output": 0.0015},
        "enabled": False  # Deprecated
    }
}

# ============ CONFIGURAZIONE FALLBACK ============

# Abilita fallback locale quando LLM non disponibile
ENABLE_FALLBACK_GENERATION = True

# Template fallback personalizzati (opzionale)
FALLBACK_TEMPLATES = {
    "executive_summary": """
## Executive Summary

L'analisi di accessibilità per {company_name} ha identificato {total_issues} problemi
che richiedono attenzione per garantire la conformità agli standard WCAG 2.1 AA.

### Risultati Principali
- Sono stati identificati {critical_issues} problemi critici
- Score di conformità attuale: {compliance_score}%
- Miglioramenti necessari in tutte le aree WCAG

### Raccomandazioni
1. Priorità immediata sui problemi critici
2. Piano di remediation strutturato
3. Formazione team sviluppo
4. Monitoraggio continuo conformità
""",
    
    "recommendations": """
## Raccomandazioni Tecniche

### 1. Problemi Critici
- Correzione immediata errori bloccanti
- Implementazione testi alternativi
- Miglioramento navigazione tastiera

### 2. Miglioramenti Strutturali  
- Ottimizzazione contrasti colore
- Revisione gerarchia heading
- Implementazione ARIA labels

### 3. Monitoraggio Continuo
- Setup testing automatizzato
- Formazione team accessibilità
- Processo QA integrato
"""
}

# ============ CONFIGURAZIONE LOGGING ============

# Livello di logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# Formato log
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# File di log (opzionale)
LOG_FILE = None  # "/var/log/eaa-scanner-llm.log"

# ============ CONFIGURAZIONE SERVER ============

# Server settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", "8000"))

# CORS settings (se necessario)
ENABLE_CORS = False
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]

# ============ CONFIGURAZIONE AVANZATA ============

# Circuit breaker settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 3
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 60
CIRCUIT_BREAKER_HALF_OPEN_REQUESTS = 1

# Timeout settings
API_TIMEOUT_SECONDS = 30
GENERATION_TIMEOUT_SECONDS = 300  # 5 minuti max per generazione

# Memory limits (approssimativo)
MAX_CACHE_SIZE = 1000
MAX_CONCURRENT_GENERATIONS = 3

# ============ CONFIGURAZIONE MONITORAGGIO ============

# Health check settings
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_DEEP = False  # Test chiamate API reali

# Metrics collection
ENABLE_METRICS = True
METRICS_RETENTION_HOURS = 24

# ============ FUNZIONI HELPER ============

def get_config(key: str, default=None):
    """Ottiene valore configurazione"""
    return globals().get(key, default)

def is_section_enabled(section: str) -> bool:
    """Controlla se sezione è abilitata"""
    return AVAILABLE_SECTIONS.get(section, {}).get("enabled", False)

def is_model_enabled(model: str) -> bool:
    """Controlla se modello è abilitato"""
    return SUPPORTED_MODELS.get(model, {}).get("enabled", False)

def get_enabled_sections():
    """Restituisce lista sezioni abilitate"""
    return [k for k, v in AVAILABLE_SECTIONS.items() if v.get("enabled", False)]

def get_enabled_models():
    """Restituisce lista modelli abilitati"""
    return [k for k, v in SUPPORTED_MODELS.items() if v.get("enabled", False)]

def validate_request_limits(sections: list, pages: int, estimated_cost: float) -> tuple:
    """Valida limiti richiesta"""
    errors = []
    
    if len(sections) > MAX_SECTIONS_PER_REQUEST:
        errors.append(f"Troppe sezioni: max {MAX_SECTIONS_PER_REQUEST}")
    
    if pages > MAX_PAGES_PER_SCAN:
        errors.append(f"Troppe pagine: max {MAX_PAGES_PER_SCAN}")
    
    if estimated_cost > MAX_COST_PER_REQUEST:
        errors.append(f"Costo troppo elevato: max ${MAX_COST_PER_REQUEST}")
    
    warnings = []
    if estimated_cost > MAX_COST_WARNING_THRESHOLD:
        warnings.append(f"Costo elevato: ${estimated_cost:.2f}")
    
    return errors, warnings

# ============ ESEMPIO USO ============

if __name__ == "__main__":
    print("🔧 Configurazione LLM Backend")
    print(f"   Modelli abilitati: {get_enabled_models()}")
    print(f"   Sezioni abilitate: {get_enabled_sections()}")
    print(f"   Rate limit: {RATE_LIMIT_PER_MINUTE} req/min")
    print(f"   Max costo: ${MAX_COST_PER_REQUEST}")
    print(f"   Fallback: {'✅' if ENABLE_FALLBACK_GENERATION else '❌'}")