from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def process_wave(raw: Dict[str, Any]) -> Dict[str, Any]:
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

    def map_wcag(code: str) -> str | None:
        mapping = {
            "alt_missing": "1.1.1",
            "contrast": "1.4.3",
        }
        return mapping.get(code)

    def get_impact(code: str) -> str:
        high = {"alt_missing", "contrast"}
        if code in high:
            return "high"
        return "medium"

    def get_rem(code: str) -> str:
        mapping = {
            "alt_missing": "Aggiungere testo alternativo alle immagini",
            "contrast": "Aumentare il contrasto (≥4.5:1)",
        }
        return mapping.get(code, "Vedi WCAG")

    for code, d in (cat.get("error", {}).get("items", {}) or {}).items():
        # Fix: gestisci il caso in cui d possa essere un intero o un dict
        if isinstance(d, dict):
            cnt = int(d.get("count", 1))
        else:
            cnt = int(d) if isinstance(d, (int, str)) else 1
        total_errors += cnt
        errors.append(
            {
                "type": "error",
                "severity": "high",
                "code": code,
                "description": d.get("description", "Errore WAVE") if isinstance(d, dict) else "Errore WAVE",
                "count": cnt,
                "wcag_criteria": map_wcag(code) or "—",
                "impact": get_impact(code),
                "remediation": get_rem(code),
            }
        )

    for code, d in (cat.get("alert", {}).get("items", {}) or {}).items():
        # Fix: gestisci il caso in cui d possa essere un intero o un dict
        if isinstance(d, dict):
            cnt = int(d.get("count", 1))
        else:
            cnt = int(d) if isinstance(d, (int, str)) else 1
        total_warnings += cnt
        warnings.append(
            {
                "type": "warning",
                "severity": "medium",
                "code": code,
                "description": d.get("description", "Avviso WAVE") if isinstance(d, dict) else "Avviso WAVE",
                "count": cnt,
                "wcag_criteria": map_wcag(code) or "—",
                "remediation": get_rem(code),
            }
        )

    for code, d in (cat.get("feature", {}).get("items", {}) or {}).items():
        features.append({"type": "feature", "code": code, "description": d.get("description", "Feature")})

    wave = {
        "scanner": "WAVE",
        "scan_time": stats.get("time", 0),
        "page_title": stats.get("pagetitle"),
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "errors": errors,
        "warnings": warnings,
        "features": features,
        "raw_statistics": stats,
        "error_count": total_errors,
        "contrast_count": (cat.get("contrast", {}).get("items", {}) and sum(
            int(v.get("count", 0)) for v in cat.get("contrast", {}).get("items", {}).values()
        )) or 0,
    }
    return wave


def process_pa11y(raw: Dict[str, Any]) -> Dict[str, Any]:
    # Gestisci diversi formati di input
    if isinstance(raw, list):
        # Se raw è direttamente una lista di issues
        issues = raw
    elif isinstance(raw, dict):
        # Se raw è un dizionario con stdout (formato errore), prova a parsare stdout
        if "stdout" in raw and "issues" not in raw:
            try:
                stdout_data = json.loads(raw["stdout"])
                if isinstance(stdout_data, list):
                    issues = stdout_data
                else:
                    issues = stdout_data.get("issues", []) if isinstance(stdout_data, dict) else []
            except:
                issues = []
        else:
            # Altrimenti cerca issues normalmente
            issues = raw.get("issues", []) or []
    else:
        issues = []
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    total_errors = 0
    total_warnings = 0

    def extract_wcag(code: str) -> str:
        import re

        m = re.search(r"Guideline(\d+)_(\d+)\.(\d+)_", code)
        if m:
            return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        return "—"

    def remediation(code: str) -> str:
        if "1_4_3" in code:
            return "Migliorare il contrasto (≥4.5:1)"
        if "1_1_1" in code:
            return "Aggiungere testo alternativo"
        if "4_1_2" in code:
            return "Fornire nome/ruolo/valore con ARIA/HTML"
        return "Consultare WCAG"

    for i in issues:
        norm = {
            "scanner": "Pa11y",
            "code": i.get("code", ""),
            "type": "error" if i.get("type") == "error" else "warning",
            "severity": "high" if i.get("type") == "error" else "medium",
            "message": i.get("message", ""),
            "context": i.get("context", ""),
            "selector": i.get("selector", ""),
            "wcag_criteria": extract_wcag(i.get("code", "")),
            "remediation": remediation(i.get("code", "")),
            "count": 1,
        }
        if norm["type"] == "error":
            errors.append(norm)
            total_errors += 1
        else:
            warnings.append(norm)
            total_warnings += 1

    return {
        "scanner": "Pa11y",
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "errors": errors,
        "warnings": warnings,
        "compliance_percentage": 100 - min(50, total_errors * 15 + total_warnings * 5),
    }


def normalize_all(
    url: str,
    company_name: str,
    wave: Dict[str, Any] | None,
    pa11y: Dict[str, Any] | None,
    axe: Dict[str, Any] | None,
    lighthouse: Dict[str, Any] | None,
) -> Dict[str, Any]:
    all_errors: List[Dict[str, Any]] = []
    all_warnings: List[Dict[str, Any]] = []
    all_features: List[Dict[str, Any]] = []

    if wave:
        all_errors += [{**e, "source": "WAVE"} for e in wave.get("errors", [])]
        all_warnings += [{**w, "source": "WAVE"} for w in wave.get("warnings", [])]
        all_features += [{**f, "source": "WAVE"} for f in wave.get("features", [])]

    if pa11y:
        all_errors += [{**e, "source": "Pa11y"} for e in pa11y.get("errors", [])]
        all_warnings += [{**w, "source": "Pa11y"} for w in pa11y.get("warnings", [])]

    if axe:
        for v in axe.get("violations", []) or []:
            sev = (
                "critical"
                if v.get("impact") == "critical"
                else "high"
                if v.get("impact") == "serious"
                else "medium"
                if v.get("impact") == "moderate"
                else "low"
            )
            
            # Estrai selettori e HTML dai nodi Axe
            selectors = []
            code_snippets = []
            if v.get("nodes"):
                for node in v.get("nodes", [])[:3]:  # Prendi max 3 esempi
                    if node.get("target"):
                        selectors.extend(node.get("target", []))
                    if node.get("html"):
                        code_snippets.append(node.get("html", ""))
            
            issue = {
                "source": "Axe-Core",
                "type": "error" if sev != "low" else "warning",
                "severity": sev,
                "code": v.get("id"),
                "description": v.get("description"),
                "count": len(v.get("nodes", [])) if v.get("nodes") else 1,
                "wcag_criteria": ", ".join(v.get("wcag", []) or []) or "—",
                "remediation": axe_remediation(v.get("id", "")),
                "selector": " | ".join(selectors[:3]) if selectors else "",
                "code_snippet": code_snippets[0] if code_snippets else "",
            }
            (all_errors if issue["type"] == "error" else all_warnings).append(issue)

    if lighthouse:
        audits = lighthouse.get("audits", {}) or {}
        for aid, a in audits.items():
            score = a.get("score")
            if isinstance(score, (int, float)) and score < 1:
                t = "error" if score < 0.5 else "warning"
                severity = "high" if score < 0.3 else "medium" if score < 0.7 else "low"
                issue = {
                    "source": "Lighthouse",
                    "type": t,
                    "severity": severity,
                    "code": aid,
                    "description": a.get("title", aid),
                    "count": 1,
                    "wcag_criteria": map_lighthouse_wcag(aid),
                    "remediation": "Consultare dettagli audit Lighthouse",
                }
                (all_errors if t == "error" else all_warnings).append(issue)

    def dedup(arr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for i in arr:
            key = f"{i.get('code','')}-{i.get('type','')}-{i.get('wcag_criteria','')}"
            if key in seen:
                continue
            seen.add(key)
            out.append(i)
        return out

    errors_u = dedup(all_errors)
    warnings_u = dedup(all_warnings)

    weights = {"critical": 20, "high": 15, "medium": 8, "low": 3}
    penalty = 0
    for e in errors_u:
        penalty += weights.get(e.get("severity", "low"), 3)
    for w in warnings_u:
        penalty += max(1, weights.get("medium", 8) // 2)
    overall = max(0, 100 - penalty)

    if len(errors_u) == 0 and len(warnings_u) <= 2:
        compliance_level = "conforme"
        eaa_status = "compliant"
    elif len(errors_u) <= 2 and overall >= 70:
        compliance_level = "parzialmente_conforme"
        eaa_status = "partially_compliant"
    else:
        compliance_level = "non_conforme"
        eaa_status = "non_compliant"

    # WCAG principle buckets
    wcag_categories = {
        "perceivable": {"errors": 0, "warnings": 0},
        "operable": {"errors": 0, "warnings": 0},
        "understandable": {"errors": 0, "warnings": 0},
        "robust": {"errors": 0, "warnings": 0},
    }

    def cat_for_wcag(codes: str) -> str | None:
        if not codes or codes == "—":
            return None
        c = codes.split(",")[0].strip()
        if not c:
            return None
        if c.startswith("1."):
            return "perceivable"
        if c.startswith("2."):
            return "operable"
        if c.startswith("3."):
            return "understandable"
        if c.startswith("4."):
            return "robust"
        return None

    for i in errors_u + warnings_u:
        cat = cat_for_wcag(i.get("wcag_criteria", ""))
        if not cat:
            continue
        wcag_categories[cat]["errors" if i.get("type") == "error" else "warnings"] += i.get("count", 1)

    return {
        "url": url,
        "company_name": company_name,
        "conformityStatus": compliance_level,
        "compliance": {
            "wcag_version": "2.1",
            "wcag_level": "AA",
            "compliance_level": compliance_level,
            "eaa_compliance": eaa_status,
            "overall_score": overall,
            "categories": wcag_categories,
            "total_unique_errors": len(errors_u),
            "total_unique_warnings": len(warnings_u),
            "total_issues": len(errors_u) + len(warnings_u),
        },
        "detailed_results": {
            "errors": errors_u,
            "warnings": warnings_u,
            "features": all_features,
            "scanner_scores": {
                "wave": _score_wave(wave),
                "pa11y": (pa11y or {}).get("compliance_percentage", 0),
                "axe_core": (axe or {}).get("compliance_score", 0),
                "lighthouse": (lighthouse or {}).get("accessibility_score", 0),
            },
        },
    }


def axe_remediation(rule: str) -> str:
    return {
        "color-contrast": "Aumentare contrasto testo/sfondo",
        "heading-order": "Usare intestazioni in ordine logico",
        "image-alt": "Aggiungere attributi alt descrittivi",
        "link-name": "Fornire testo link descrittivo",
    }.get(rule, "Vedi documentazione axe-core")


def map_lighthouse_wcag(audit_id: str) -> str:
    return {
        "color-contrast": "1.4.3",
        "heading-order": "1.3.1",
        "image-alt": "1.1.1",
        "link-name": "2.4.4",
        "bypass": "2.4.1",
    }.get(audit_id, "—")


def _score_wave(wave: Dict[str, Any] | None) -> int:
    if not wave:
        return 0
    errors = int(wave.get("error_count", 0))
    contrast = int(wave.get("contrast_count", 0))
    return max(0, 100 - (errors * 5 + contrast * 2))

