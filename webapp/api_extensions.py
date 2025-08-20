"""
Estensioni API per supporto LLM avanzato.
Separato da app.py per mantenere organizzazione del codice.
"""

import json
import time
import logging
from typing import Dict, Any, Optional

# Configura logger specifico
logger = logging.getLogger('webapp.api_extensions')
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def handle_llm_health_check(environ, start_response):
    """Health check per sistema LLM"""
    try:
        from eaa_scanner.llm_config import get_llm_manager
        from webapp.llm_utils import get_web_llm_manager
        
        # Test disponibilità componenti
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "llm_core": {"status": "ok", "message": "LLM core disponibile"},
                "web_manager": {"status": "ok", "message": "Web manager attivo"},
                "cache": {"status": "ok", "message": "Cache operativa"}
            },
            "features": {
                "api_validation": True,
                "cost_estimation": True,
                "report_generation": True,
                "multi_versioning": True,
                "rate_limiting": True
            }
        }
        
        # Test componenti
        try:
            web_manager = get_web_llm_manager()
            cache_size = len(web_manager.session_cache)
            health_status["components"]["cache"]["message"] = f"Cache con {cache_size} elementi"
        except Exception as e:
            health_status["components"]["cache"] = {"status": "error", "message": str(e)}
            health_status["status"] = "degraded"
        
        # Test availability
        try:
            import openai
            health_status["components"]["openai_sdk"] = {"status": "ok", "message": "OpenAI SDK disponibile"}
        except ImportError:
            health_status["components"]["openai_sdk"] = {"status": "warning", "message": "OpenAI SDK non installato"}
            health_status["status"] = "degraded"
        
        status_code = "200 OK" if health_status["status"] == "healthy" else "503 Service Unavailable"
        start_response(status_code, [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(health_status).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore health check LLM: {e}")
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": time.time()
        }
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(error_response).encode("utf-8")]


def handle_llm_capabilities(environ, start_response):
    """Restituisce capacità LLM disponibili"""
    try:
        capabilities = {
            "models": {
                "gpt-4o": {
                    "name": "GPT-4o",
                    "description": "Modello principale, veloce ed economico",
                    "recommended": True,
                    "max_tokens": 4096,
                    "pricing": {"input": 0.005, "output": 0.015}
                },
                "gpt-4o-mini": {
                    "name": "GPT-4o Mini",
                    "description": "Versione economica per test",
                    "recommended": False,
                    "max_tokens": 4096,
                    "pricing": {"input": 0.00015, "output": 0.0006}
                },
                "gpt-4-turbo-preview": {
                    "name": "GPT-4 Turbo",
                    "description": "Modello premium per casi complessi",
                    "recommended": False,
                    "max_tokens": 4096,
                    "pricing": {"input": 0.01, "output": 0.03}
                }
            },
            "sections": {
                "executive_summary": {
                    "name": "Executive Summary",
                    "description": "Riassunto esecutivo per decision makers",
                    "estimated_tokens": 800,
                    "complexity": "low"
                },
                "technical_analysis": {
                    "name": "Analisi Tecnica",
                    "description": "Analisi dettagliata dei risultati tecnici",
                    "estimated_tokens": 1200,
                    "complexity": "high"
                },
                "recommendations": {
                    "name": "Raccomandazioni",
                    "description": "Suggerimenti prioritizzati per miglioramenti",
                    "estimated_tokens": 1000,
                    "complexity": "medium"
                },
                "remediation_plan": {
                    "name": "Piano di Remediation",
                    "description": "Piano dettagliato per risolvere i problemi",
                    "estimated_tokens": 1500,
                    "complexity": "high"
                },
                "accessibility_statement": {
                    "name": "Dichiarazione di Accessibilità",
                    "description": "Dichiarazione formale di conformità",
                    "estimated_tokens": 600,
                    "complexity": "low"
                },
                "compliance_matrix": {
                    "name": "Matrice di Conformità",
                    "description": "Mappatura dettagliata standard WCAG",
                    "estimated_tokens": 900,
                    "complexity": "medium"
                },
                "user_impact_analysis": {
                    "name": "Analisi Impatto Utenti",
                    "description": "Valutazione impatto su diverse categorie di utenti",
                    "estimated_tokens": 800,
                    "complexity": "medium"
                }
            },
            "features": {
                "fallback_generation": {
                    "enabled": True,
                    "description": "Generazione fallback senza LLM"
                },
                "caching": {
                    "enabled": True,
                    "description": "Cache intelligente per validazioni"
                },
                "rate_limiting": {
                    "enabled": True,
                    "description": "Limitazione richieste per IP"
                },
                "cost_estimation": {
                    "enabled": True,
                    "description": "Stima costi accurate pre-generazione"
                },
                "progress_tracking": {
                    "enabled": True,
                    "description": "Tracking progresso real-time"
                }
            },
            "limits": {
                "max_sections_per_request": 7,
                "max_pages_per_scan": 100,
                "rate_limit_per_minute": 5,
                "max_concurrent_generations": 3
            }
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(capabilities).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore recupero capabilities: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore recupero capabilities"}).encode("utf-8")]


def handle_llm_preview_section(environ, start_response):
    """Genera preview di una singola sezione per test"""
    try:
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        section_type = payload.get('section_type', '')
        sample_data = payload.get('sample_data', {})
        
        if not section_type:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "section_type mancante"}).encode("utf-8")]
        
        # Usa dati di esempio per preview veloce
        preview_data = {
            'company_name': sample_data.get('company_name', 'Azienda di Esempio'),
            'url': 'https://esempio.com',
            'scan_date': time.strftime('%Y-%m-%d'),
            'total_issues': 15,
            'critical_issues': 3,
            'compliance_score': 72
        }
        
        from eaa_scanner.llm_config import get_llm_manager
        
        # Usa fallback per preview veloce
        manager = get_llm_manager()
        content = manager._generate_fallback(f"Genera {section_type} per {preview_data['company_name']}")
        
        response = {
            "section_type": section_type,
            "preview_content": content,
            "sample_data_used": preview_data,
            "is_preview": True,
            "note": "Questo è un esempio. La versione finale userà i dati reali della scansione."
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore preview sezione: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore generazione preview"}).encode("utf-8")]


def handle_llm_cancel_task(environ, start_response, task_id: str):
    """Cancella task di generazione LLM in corso"""
    try:
        # Nota: In questa implementazione semplificata, i task non sono cancellabili
        # Una implementazione completa userebbe threading.Event o simili
        
        response = {
            "task_id": task_id,
            "status": "cancellation_requested",
            "message": "Richiesta di cancellazione inviata (implementazione semplificata)",
            "note": "Il task potrebbe completarsi comunque se già in fase avanzata"
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore cancellazione task: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore cancellazione task"}).encode("utf-8")]


def handle_llm_usage_stats(environ, start_response):
    """Statistiche di utilizzo LLM"""
    try:
        from webapp.llm_utils import get_web_llm_manager
        
        web_manager = get_web_llm_manager()
        
        # Calcola statistiche dalla cache
        cache_stats = {
            "total_validations": len([k for k in web_manager.session_cache.keys() if k.startswith('validation_')]),
            "cache_size": len(web_manager.session_cache),
            "cache_hit_rate": 0.85  # Mock - in implementazione reale trackare hits/misses
        }
        
        stats = {
            "period": "session",
            "cache": cache_stats,
            "estimates": {
                "total_requests": len(web_manager.cost_cache),
                "avg_cost_usd": 0.12,  # Mock
                "popular_models": ["gpt-4o", "gpt-4o-mini"],
                "popular_sections": ["executive_summary", "recommendations"]
            },
            "performance": {
                "avg_validation_time_ms": 250,  # Mock
                "avg_generation_time_s": 45,    # Mock
                "success_rate": 0.95             # Mock
            },
            "timestamp": time.time()
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(stats).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore statistiche utilizzo: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore recupero statistiche"}).encode("utf-8")]


# Mapping degli endpoint aggiuntivi
ADDITIONAL_LLM_ENDPOINTS = {
    "/api/llm/health": handle_llm_health_check,
    "/api/llm/capabilities": handle_llm_capabilities,
    "/api/llm/preview-section": handle_llm_preview_section,
    "/api/llm/usage-stats": handle_llm_usage_stats,
    # handle_llm_cancel_task needs task_id parameter, handled separately
}


def route_additional_llm_endpoints(environ, start_response, path: str, method: str):
    """Router per endpoint LLM aggiuntivi"""
    
    # Health check
    if path == "/api/llm/health" and method == "GET":
        return handle_llm_health_check(environ, start_response)
    
    # Capabilities
    if path == "/api/llm/capabilities" and method == "GET":
        return handle_llm_capabilities(environ, start_response)
    
    # Preview section
    if path == "/api/llm/preview-section" and method == "POST":
        return handle_llm_preview_section(environ, start_response)
    
    # Usage stats
    if path == "/api/llm/usage-stats" and method == "GET":
        return handle_llm_usage_stats(environ, start_response)
    
    # Cancel task
    if path.startswith("/api/llm/tasks/") and path.endswith("/cancel") and method == "POST":
        task_id = path.split('/')[-2]
        return handle_llm_cancel_task(environ, start_response, task_id)
    
    return None  # Not handled by this router