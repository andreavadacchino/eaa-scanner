"""
Normalizzatore principale per unificare risultati da tutti gli scanner
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import hashlib


def normalize_all(
    url: str,
    company_name: Optional[str] = None,
    wave: Optional[Dict[str, Any]] = None,
    pa11y: Optional[Dict[str, Any]] = None,
    axe: Optional[Dict[str, Any]] = None,
    lighthouse: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Normalizza e unifica i risultati da tutti gli scanner
    
    Args:
        url: URL scansionato
        company_name: Nome azienda
        wave: Risultati processati WAVE
        pa11y: Risultati processati Pa11y
        axe: Risultati raw Axe-core
        lighthouse: Risultati raw Lighthouse
        
    Returns:
        Dizionario con schema unificato
    """
    
    # Raccogli tutti gli errori e warning
    all_errors: List[Dict[str, Any]] = []
    all_warnings: List[Dict[str, Any]] = []
    scanner_scores = {}
    
    # Aggiungi risultati WAVE
    if wave and not wave.get("error"):
        all_errors.extend(wave.get("errors", []))
        all_warnings.extend(wave.get("warnings", []))
        scanner_scores["wave"] = wave.get("score", 0)
    
    # Aggiungi risultati Pa11y
    if pa11y:
        all_errors.extend(pa11y.get("errors", []))
        all_warnings.extend(pa11y.get("warnings", []))
        scanner_scores["pa11y"] = pa11y.get("score", 0)
    
    # Processa Axe-core
    if axe:
        axe_errors, axe_warnings, axe_score = process_axe_results(axe)
        all_errors.extend(axe_errors)
        all_warnings.extend(axe_warnings)
        scanner_scores["axe_core"] = axe_score
    
    # Processa Lighthouse
    if lighthouse:
        lh_errors, lh_warnings, lh_score = process_lighthouse_results(lighthouse)
        all_errors.extend(lh_errors)
        all_warnings.extend(lh_warnings)
        scanner_scores["lighthouse"] = lh_score
    
    # Deduplica issues
    deduplicated_errors = deduplicate_issues(all_errors)
    deduplicated_warnings = deduplicate_issues(all_warnings)
    
    # Categorizza per principi WCAG (POUR)
    categories = categorize_by_pour(deduplicated_errors, deduplicated_warnings)
    
    # Calcola score complessivo con pesi per severità
    overall_score = calculate_overall_score(deduplicated_errors, deduplicated_warnings)
    
    # Determina livello di conformità
    compliance_level = determine_compliance_level(overall_score, deduplicated_errors)
    
    # Genera raccomandazioni
    recommendations = generate_recommendations(deduplicated_errors, deduplicated_warnings)
    
    # Costruisci output normalizzato
    return {
        "scan_id": "",  # Verrà impostato da core.py
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "url": url,
        "company_name": company_name or "",
        "compliance": {
            "wcag_version": "2.1",
            "wcag_level": "AA",
            "compliance_level": compliance_level,
            "eaa_compliance": map_to_eaa_compliance(compliance_level),
            "overall_score": overall_score,
            "categories": categories
        },
        "detailed_results": {
            "errors": deduplicated_errors[:50],  # Limita a top 50
            "warnings": deduplicated_warnings[:30],  # Limita a top 30
            "scanner_scores": scanner_scores
        },
        "recommendations": recommendations,
        "scan_metadata": {
            "scan_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "scanners_used": list(scanner_scores.keys()),
            "total_issues": len(deduplicated_errors) + len(deduplicated_warnings)
        },
        "raw_scanner_data": {
            "wave": wave if wave else {},
            "pa11y": pa11y if pa11y else {},
            "axe_core": axe if axe else {},
            "lighthouse": lighthouse if lighthouse else {}
        }
    }


def process_axe_results(axe: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], int]:
    """
    Processa risultati Axe-core
    
    Returns:
        Tuple di (errors, warnings, score)
    """
    errors = []
    warnings = []
    
    # Mapping impact -> severity
    severity_map = {
        "critical": "critical",
        "serious": "high",
        "moderate": "medium",
        "minor": "low"
    }
    
    # Processa violations
    for violation in axe.get("violations", []):
        severity = severity_map.get(violation.get("impact", "moderate"), "medium")
        wcag_tags = [tag for tag in violation.get("tags", []) if "wcag" in tag.lower()]
        wcag_criteria = extract_wcag_from_tags(wcag_tags)
        
        nodes = violation.get("nodes", [])
        if isinstance(nodes, int):
            node_count = nodes
        else:
            node_count = len(nodes) if isinstance(nodes, list) else 1
            
        error = {
            "type": "error",
            "severity": severity,
            "code": violation.get("id", ""),
            "description": violation.get("description", violation.get("help", "")),
            "count": node_count,
            "wcag_criteria": wcag_criteria,
            "remediation": violation.get("helpUrl", ""),
            "source": "Axe-Core"
        }
        
        if severity in ["critical", "high"]:
            errors.append(error)
        else:
            warnings.append(error)
    
    # Calcola score
    penalty = (len(errors) * 15) + (len(warnings) * 5)
    score = max(0, 100 - penalty)
    
    return errors, warnings, score


def process_lighthouse_results(lighthouse: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], int]:
    """
    Processa risultati Lighthouse
    
    Returns:
        Tuple di (errors, warnings, score)
    """
    errors = []
    warnings = []
    
    # Estrai categoria accessibilità
    categories = lighthouse.get("categories", {})
    if isinstance(categories, dict):
        accessibility = categories.get("accessibility", {})
        if isinstance(accessibility, dict):
            score_value = accessibility.get("score", 0)
            if score_value is not None:
                score = int(score_value * 100)
            else:
                score = 0
        else:
            score = 0
    else:
        score = 0
    
    # Processa audits
    audits = lighthouse.get("audits", {})
    
    # Audit critici per accessibilità
    critical_audits = [
        "aria-allowed-attr", "aria-command-name", "aria-hidden-body",
        "aria-hidden-focus", "aria-input-field-name", "aria-meter-name",
        "aria-progressbar-name", "aria-required-attr", "aria-required-children",
        "aria-required-parent", "aria-roles", "aria-toggle-field-name",
        "aria-tooltip-name", "aria-treeitem-name", "aria-valid-attr-value",
        "aria-valid-attr", "button-name", "bypass", "color-contrast",
        "definition-list", "dlitem", "document-title", "duplicate-id-active",
        "duplicate-id-aria", "form-field-multiple-labels", "frame-title",
        "html-has-lang", "html-lang-valid", "html-xml-lang-mismatch",
        "image-alt", "input-image-alt", "label", "link-name", "list",
        "listitem", "meta-refresh", "meta-viewport", "object-alt",
        "scrollable-region-focusable", "select-name", "skip-link",
        "tabindex", "td-headers-attr", "th-has-data-cells",
        "valid-lang", "video-caption"
    ]
    
    for audit_id, audit_data in audits.items():
        if audit_id not in critical_audits:
            continue
            
        score = audit_data.get("score", 1)
        if score is not None and score < 1:
            # Determina severità basata sul tipo di audit
            severity = "high" if "aria" in audit_id or "contrast" in audit_id else "medium"
            
            details = audit_data.get("details", {})
            if isinstance(details, dict):
                items = details.get("items", [])
                item_count = len(items) if isinstance(items, list) else 0
            else:
                item_count = 0
                
            issue = {
                "type": "error" if severity == "high" else "warning",
                "severity": severity,
                "code": audit_id,
                "description": audit_data.get("title", ""),
                "count": item_count,
                "wcag_criteria": map_lighthouse_to_wcag(audit_id),
                "remediation": audit_data.get("description", ""),
                "source": "Lighthouse"
            }
            
            if severity == "high":
                errors.append(issue)
            else:
                warnings.append(issue)
    
    return errors, warnings, score


def deduplicate_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplica issues basandosi su code + wcag_criteria + source
    Aggrega i count
    
    Args:
        issues: Lista di issues da deduplicare
        
    Returns:
        Lista deduplicated con count aggregati
    """
    seen = {}
    
    for issue in issues:
        # Crea chiave univoca
        key = f"{issue.get('code', '')}_{issue.get('wcag_criteria', '')}_{issue.get('source', '')}"
        
        if key in seen:
            # Aggrega count
            seen[key]["count"] = seen[key].get("count", 1) + issue.get("count", 1)
        else:
            seen[key] = issue.copy()
    
    # Ordina per severità e count
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    result = list(seen.values())
    result.sort(key=lambda x: (severity_order.get(x.get("severity", "low"), 3), -x.get("count", 0)))
    
    return result


def categorize_by_pour(errors: List[Dict], warnings: List[Dict]) -> Dict[str, Dict[str, int]]:
    """
    Categorizza issues per principi WCAG (Perceivable, Operable, Understandable, Robust)
    
    Args:
        errors: Lista errori
        warnings: Lista warning
        
    Returns:
        Dizionario con conteggi per categoria
    """
    categories = {
        "perceivable": {"errors": 0, "warnings": 0},
        "operable": {"errors": 0, "warnings": 0},
        "understandable": {"errors": 0, "warnings": 0},
        "robust": {"errors": 0, "warnings": 0}
    }
    
    def get_pour_category(wcag_criteria: str) -> str:
        """Mappa criterio WCAG a principio POUR basandosi sulla prima cifra"""
        if not wcag_criteria:
            return "robust"  # Default
        
        first_digit = wcag_criteria.split(".")[0] if "." in wcag_criteria else wcag_criteria[0]
        mapping = {
            "1": "perceivable",
            "2": "operable",
            "3": "understandable",
            "4": "robust"
        }
        return mapping.get(first_digit, "robust")
    
    # Conta errori
    for error in errors:
        category = get_pour_category(error.get("wcag_criteria", ""))
        categories[category]["errors"] += error.get("count", 1)
    
    # Conta warning
    for warning in warnings:
        category = get_pour_category(warning.get("wcag_criteria", ""))
        categories[category]["warnings"] += warning.get("count", 1)
    
    return categories


def calculate_overall_score(errors: List[Dict], warnings: List[Dict]) -> int:
    """
    Calcola score complessivo con pesi per severità
    
    Pesi:
    - critical: 20
    - high: 15
    - medium: 8
    - low: 3
    
    Args:
        errors: Lista errori
        warnings: Lista warning
        
    Returns:
        Score 0-100
    """
    severity_weights = {
        "critical": 20,
        "high": 15,
        "medium": 8,
        "low": 3
    }
    
    total_penalty = 0
    
    for error in errors:
        weight = severity_weights.get(error.get("severity", "medium"), 8)
        count = error.get("count", 1) or 1
        if not isinstance(count, (int, float)):
            count = 1
        total_penalty += weight * min(count, 5)  # Cap a 5 per evitare penalità eccessive
    
    for warning in warnings:
        weight = severity_weights.get(warning.get("severity", "low"), 3)
        count = warning.get("count", 1) or 1
        if not isinstance(count, (int, float)):
            count = 1
        total_penalty += weight * min(count, 3)  # Cap a 3 per warning
    
    score = max(0, 100 - total_penalty)
    return score


def determine_compliance_level(score: Optional[int], errors: List[Dict]) -> str:
    """
    Determina il livello di conformità basato su score e presenza di errori critici
    
    Args:
        score: Score complessivo (può essere None)
        errors: Lista errori
        
    Returns:
        Livello di conformità (conforme/parzialmente_conforme/non_conforme)
    """
    # Gestisci score None
    if score is None:
        score = 0
        
    critical_errors = [e for e in errors if e.get("severity") == "critical"]
    
    if critical_errors:
        return "non_conforme"
    elif score >= 85:
        return "conforme"
    elif score >= 60:
        return "parzialmente_conforme"
    else:
        return "non_conforme"


def map_to_eaa_compliance(compliance_level: str) -> str:
    """
    Mappa livello di conformità italiano a inglese per EAA
    
    Args:
        compliance_level: Livello in italiano
        
    Returns:
        Livello in inglese
    """
    mapping = {
        "conforme": "compliant",
        "parzialmente_conforme": "partially_compliant",
        "non_conforme": "non_compliant"
    }
    return mapping.get(compliance_level, "non_compliant")


def generate_recommendations(errors: List[Dict], warnings: List[Dict]) -> List[Dict[str, Any]]:
    """
    Genera raccomandazioni prioritizzate basate sui problemi trovati
    
    Args:
        errors: Lista errori
        warnings: Lista warning
        
    Returns:
        Lista di raccomandazioni
    """
    recommendations = []
    
    # Analizza pattern di problemi
    has_alt_issues = any("alt" in e.get("code", "").lower() or "1.1.1" in e.get("wcag_criteria", "") for e in errors)
    has_contrast_issues = any("contrast" in e.get("code", "").lower() or "1.4.3" in e.get("wcag_criteria", "") for e in errors)
    has_label_issues = any("label" in e.get("code", "").lower() or "1.3.1" in e.get("wcag_criteria", "") for e in errors)
    has_heading_issues = any("heading" in e.get("code", "").lower() or "1.3.1" in e.get("wcag_criteria", "") for e in errors)
    has_language_issues = any("lang" in e.get("code", "").lower() or "3.1.1" in e.get("wcag_criteria", "") for e in errors)
    
    # Genera raccomandazioni basate sui pattern
    if has_alt_issues:
        recommendations.append({
            "priority": "alta",
            "title": "Testo alternativo per immagini",
            "description": "Molte immagini mancano di testo alternativo descrittivo, rendendo il contenuto inaccessibile agli screen reader",
            "actions": [
                "Aggiungere attributi alt descrittivi a tutte le immagini informative",
                "Usare alt=\"\" per immagini decorative",
                "Verificare che il testo alternativo descriva il contenuto, non solo l'immagine"
            ]
        })
    
    if has_contrast_issues:
        recommendations.append({
            "priority": "alta",
            "title": "Contrasto colore insufficiente",
            "description": "Il contrasto tra testo e sfondo non rispetta i requisiti minimi WCAG",
            "actions": [
                "Aumentare il contrasto a minimo 4.5:1 per testo normale",
                "Garantire contrasto 3:1 per testo grande (18pt o 14pt bold)",
                "Utilizzare strumenti di verifica contrasto nella fase di design"
            ]
        })
    
    if has_label_issues:
        recommendations.append({
            "priority": "alta",
            "title": "Etichette form mancanti",
            "description": "Campi form senza label associate impediscono la corretta identificazione degli input",
            "actions": [
                "Associare ogni campo input con un elemento label",
                "Utilizzare attributi aria-label dove le label visibili non sono possibili",
                "Raggruppare campi correlati con fieldset e legend"
            ]
        })
    
    if has_heading_issues:
        recommendations.append({
            "priority": "media",
            "title": "Struttura heading non corretta",
            "description": "La gerarchia degli heading non segue un ordine logico",
            "actions": [
                "Utilizzare heading in ordine gerarchico (h1, h2, h3...)",
                "Non saltare livelli di heading",
                "Usare un solo h1 per pagina come titolo principale"
            ]
        })
    
    if has_language_issues:
        recommendations.append({
            "priority": "media",
            "title": "Lingua documento non specificata",
            "description": "L'attributo lang mancante impedisce agli screen reader di pronunciare correttamente il contenuto",
            "actions": [
                "Aggiungere attributo lang=\"it\" all'elemento html",
                "Specificare lang per contenuti in lingue diverse",
                "Verificare che il valore lang sia valido (es. it, en, fr)"
            ]
        })
    
    # Se non ci sono problemi specifici ma lo score è basso
    if not recommendations and len(errors) > 0:
        recommendations.append({
            "priority": "media",
            "title": "Verifica manuale raccomandata",
            "description": "Sono stati rilevati diversi problemi di accessibilità che richiedono revisione manuale",
            "actions": [
                "Eseguire test con screen reader reali",
                "Verificare navigazione solo da tastiera",
                "Condurre test con utenti con disabilità"
            ]
        })
    
    # Ordina per priorità
    priority_order = {"alta": 0, "media": 1, "bassa": 2}
    recommendations.sort(key=lambda x: priority_order.get(x.get("priority", "bassa"), 2))
    
    return recommendations[:5]  # Limita a top 5 raccomandazioni


def extract_wcag_from_tags(tags: List[str]) -> str:
    """
    Estrae criterio WCAG da tags Axe-core
    
    Args:
        tags: Lista di tag (es. ["wcag2a", "wcag143"])
        
    Returns:
        Criterio WCAG formattato (es. "1.4.3")
    """
    import re
    
    for tag in tags:
        # Cerca pattern wcagXXX dove X sono numeri
        match = re.search(r'wcag(\d+)', tag.lower())
        if match:
            digits = match.group(1)
            if len(digits) == 3:
                return f"{digits[0]}.{digits[1]}.{digits[2]}"
            elif len(digits) == 4:
                return f"{digits[0]}.{digits[1]}.{digits[2:]}"
    
    return ""


def map_lighthouse_to_wcag(audit_id: str) -> str:
    """
    Mappa audit ID di Lighthouse a criterio WCAG
    
    Args:
        audit_id: ID dell'audit Lighthouse
        
    Returns:
        Criterio WCAG
    """
    mapping = {
        "aria-allowed-attr": "4.1.2",
        "aria-command-name": "4.1.2",
        "aria-hidden-body": "4.1.2",
        "aria-hidden-focus": "4.1.2",
        "aria-input-field-name": "4.1.2",
        "aria-meter-name": "1.1.1",
        "aria-progressbar-name": "1.1.1",
        "aria-required-attr": "4.1.2",
        "aria-required-children": "1.3.1",
        "aria-required-parent": "1.3.1",
        "aria-roles": "4.1.2",
        "aria-toggle-field-name": "4.1.2",
        "aria-tooltip-name": "4.1.2",
        "aria-treeitem-name": "4.1.2",
        "aria-valid-attr-value": "4.1.2",
        "aria-valid-attr": "4.1.2",
        "button-name": "4.1.2",
        "bypass": "2.4.1",
        "color-contrast": "1.4.3",
        "definition-list": "1.3.1",
        "dlitem": "1.3.1",
        "document-title": "2.4.2",
        "duplicate-id-active": "4.1.1",
        "duplicate-id-aria": "4.1.1",
        "form-field-multiple-labels": "3.3.2",
        "frame-title": "2.4.1",
        "html-has-lang": "3.1.1",
        "html-lang-valid": "3.1.1",
        "html-xml-lang-mismatch": "3.1.1",
        "image-alt": "1.1.1",
        "input-image-alt": "1.1.1",
        "label": "1.3.1",
        "link-name": "2.4.4",
        "list": "1.3.1",
        "listitem": "1.3.1",
        "meta-refresh": "2.2.1",
        "meta-viewport": "1.4.4",
        "object-alt": "1.1.1",
        "scrollable-region-focusable": "2.1.1",
        "select-name": "1.3.1",
        "skip-link": "2.4.1",
        "tabindex": "2.4.3",
        "td-headers-attr": "1.3.1",
        "th-has-data-cells": "1.3.1",
        "valid-lang": "3.1.2",
        "video-caption": "1.2.2"
    }
    
    return mapping.get(audit_id, "")