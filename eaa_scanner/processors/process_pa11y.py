"""
Processore per risultati Pa11y
"""
from typing import Dict, Any, List


def process_pa11y(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processa i risultati raw di Pa11y
    
    Args:
        raw: Output JSON da Pa11y
        
    Returns:
        Dizionario con risultati processati
    """
    issues = raw.get("issues", []) if isinstance(raw, dict) else []
    if isinstance(raw, list):
        issues = raw
    
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    notices: List[Dict[str, Any]] = []
    
    # Mapping Pa11y type -> severity
    severity_map = {
        "error": "high",
        "warning": "medium",
        "notice": "low"
    }
    
    # Mapping Pa11y code -> WCAG criteria (estratto dal codice)
    def extract_wcag_from_code(code: str) -> str:
        """
        Estrae il criterio WCAG dal codice Pa11y
        Es: "WCAG2AA.Principle1.Guideline1_1.1_1_1" -> "1.1.1"
        """
        parts = code.split(".")
        if len(parts) >= 4:
            # Prendi l'ultima parte e formatta
            criterion = parts[-1]
            # Rimuovi underscore e formatta come X.X.X
            criterion = criterion.replace("_", ".")
            # Rimuovi lettere iniziali se presenti
            import re
            match = re.search(r'(\d+\.\d+\.\d+)', criterion)
            if match:
                return match.group(1)
            # Prova formato alternativo
            match = re.search(r'(\d+)_(\d+)_(\d+)', criterion)
            if match:
                return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
        return ""
    
    # Processa issues
    for issue in issues:
        issue_type = issue.get("type", "notice").lower()
        code = issue.get("code", "")
        wcag = extract_wcag_from_code(code)
        
        issue_data = {
            "type": issue_type,
            "severity": severity_map.get(issue_type, "low"),
            "code": code,
            "description": issue.get("message", ""),
            "selector": issue.get("selector", ""),
            "context": issue.get("context", ""),
            "wcag_criteria": wcag,
            "source": "Pa11y",
            "count": 1  # Pa11y non aggrega, ogni issue è singola
        }
        
        if issue_type == "error":
            errors.append(issue_data)
        elif issue_type == "warning":
            warnings.append(issue_data)
        else:
            notices.append(issue_data)
    
    # Calcola score
    penalty = (len(errors) * 10) + (len(warnings) * 5) + (len(notices) * 2)
    score = max(0, 100 - penalty)
    
    return {
        "scanner": "Pa11y",
        "page_url": raw.get("pageUrl", "") if isinstance(raw, dict) else "",
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "total_notices": len(notices),
        "errors": errors,
        "warnings": warnings,
        "notices": notices,
        "score": score,
        "raw_issues": issues
    }