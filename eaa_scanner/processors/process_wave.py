"""
Processore per risultati WAVE API
"""
from typing import Dict, Any, List, Optional


def process_wave(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa i risultati raw di WAVE API
    
    Args:
        raw: Risposta JSON da WAVE API
        
    Returns:
        Dizionario con risultati processati
    """
    if not raw or not raw.get("status", {}).get("success", False):
        return {
            "scanner": "WAVE",
            "error": True,
            "message": raw.get("status", {}).get("error", "WAVE API non disponibile"),
            "raw_response": raw,
        }
    
    cat = raw.get("categories", {})
    stats = raw.get("statistics", {})
    
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    total_errors = 0
    total_warnings = 0
    
    # Mapping codici WAVE -> WCAG criteria
    wcag_mapping = {
        "alt_missing": "1.1.1",
        "alt_link_missing": "1.1.1",
        "alt_spacer_missing": "1.1.1",
        "alt_input_missing": "1.1.1",
        "alt_area_missing": "1.1.1",
        "alt_map_missing": "1.1.1",
        "contrast": "1.4.3",
        "contrast_large": "1.4.3",
        "label_missing": "1.3.1",
        "label_empty": "1.3.1",
        "heading_empty": "1.3.1",
        "button_empty": "1.3.1",
        "link_empty": "2.4.4",
        "language_missing": "3.1.1",
        "title_missing": "2.4.2",
        "th_empty": "1.3.1",
        "table_layout": "1.3.1",
        "table_caption_possible": "1.3.1",
    }
    
    # Mapping severità
    def get_severity(code: str) -> str:
        critical = {"alt_missing", "label_missing", "language_missing"}
        high = {"contrast", "heading_empty", "button_empty", "link_empty"}
        if code in critical:
            return "critical"
        elif code in high:
            return "high"
        return "medium"
    
    # Mapping remediation
    remediation_map = {
        "alt_missing": "Aggiungere attributo alt descrittivo alle immagini",
        "contrast": "Aumentare il contrasto colore (minimo 4.5:1 per testo normale, 3:1 per testo grande)",
        "label_missing": "Aggiungere label associata al campo form",
        "heading_empty": "Inserire contenuto testuale nell'heading",
        "button_empty": "Aggiungere testo o aria-label al pulsante",
        "link_empty": "Aggiungere testo descrittivo al link",
        "language_missing": "Specificare attributo lang nell'elemento html",
        "title_missing": "Aggiungere elemento title nella head",
    }
    
    # Processa errori
    for code, data in (cat.get("error", {}).get("items", {}) or {}).items():
        count = int(data.get("count", 1))
        total_errors += count
        errors.append({
            "type": "error",
            "severity": get_severity(code),
            "code": code,
            "description": data.get("description", "Errore WAVE"),
            "count": count,
            "wcag_criteria": wcag_mapping.get(code, ""),
            "remediation": remediation_map.get(code, "Consultare documentazione WCAG"),
            "source": "WAVE"
        })
    
    # Processa avvisi (alert)
    for code, data in (cat.get("alert", {}).get("items", {}) or {}).items():
        count = int(data.get("count", 1))
        total_warnings += count
        warnings.append({
            "type": "warning",
            "severity": "low",
            "code": code,
            "description": data.get("description", "Avviso WAVE"),
            "count": count,
            "wcag_criteria": wcag_mapping.get(code, ""),
            "remediation": remediation_map.get(code, "Verificare manualmente"),
            "source": "WAVE"
        })
    
    # Processa features (informativo)
    for code, data in (cat.get("feature", {}).get("items", {}) or {}).items():
        features.append({
            "type": "feature",
            "code": code,
            "description": data.get("description", "Feature WAVE"),
            "count": int(data.get("count", 1)),
            "source": "WAVE"
        })
    
    # Calcola score (100 - penalità)
    penalty = (total_errors * 10) + (total_warnings * 3)
    score = max(0, 100 - penalty)
    
    return {
        "scanner": "WAVE",
        "scan_time": stats.get("time", 0),
        "page_title": stats.get("pagetitle", ""),
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "errors": errors,
        "warnings": warnings,
        "features": features,
        "score": score,
        "raw_statistics": stats
    }