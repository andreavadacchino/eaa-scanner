"""
Sistema di analytics e report quantitativo per conformità EAA
"""
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import statistics
import json
import logging

logger = logging.getLogger(__name__)


class AccessibilityAnalytics:
    """
    Analisi quantitative dettagliate per report di accessibilità
    """
    
    def __init__(self, scan_results: Dict[str, Any]):
        """
        Inizializza analytics con risultati scansione
        
        Args:
            scan_results: Risultati normalizzati della scansione
        """
        self.scan_results = scan_results
        
        # Gestisci struttura dati con controlli robusti
        detailed = scan_results.get("detailed_results", {})
        if detailed is None:
            detailed = {}
            
        # Assicura che errors e warnings siano sempre liste
        self.errors = detailed.get("errors", []) if isinstance(detailed, dict) else []
        self.warnings = detailed.get("warnings", []) if isinstance(detailed, dict) else []
        
        # Assicura che siano liste valide
        if not isinstance(self.errors, list):
            self.errors = []
        if not isinstance(self.warnings, list):
            self.warnings = []
            
        self.compliance = scan_results.get("compliance", {}) or {}
        self.scanner_scores = detailed.get("scanner_scores", {}) if isinstance(detailed, dict) else {}
    
    def generate_complete_analytics(self) -> Dict[str, Any]:
        """
        Genera analytics complete per il report
        
        Returns:
            Dizionario con tutte le metriche analitiche
        """
        return {
            "executive_summary": self._generate_executive_summary(),
            "quantitative_analysis": self._generate_quantitative_analysis(),
            "wcag_analysis": self._analyze_wcag_compliance(),
            "severity_distribution": self._analyze_severity_distribution(),
            "category_analysis": self._analyze_by_category(),
            "scanner_comparison": self._compare_scanners(),
            "trend_indicators": self._calculate_trends(),
            "benchmarks": self._generate_benchmarks(),
            "risk_assessment": self._assess_risks(),
            "effort_estimation": self._estimate_remediation_effort()
        }
    
    def _generate_executive_summary(self) -> Dict[str, Any]:
        """
        Genera sommario esecutivo con KPI principali
        
        Returns:
            Dizionario con metriche executive
        """
        total_issues = len(self.errors) + len(self.warnings)
        critical_count = sum(1 for e in self.errors if e.get("severity") == "critical")
        high_count = sum(1 for e in self.errors if e.get("severity") == "high")
        
        # Calcola impatto utenti
        user_impact = self._calculate_user_impact()
        
        # Determina stato generale
        if critical_count > 0:
            overall_status = "CRITICO - Intervento Urgente Richiesto"
            risk_level = "ALTO"
        elif high_count > 5:
            overall_status = "PROBLEMATICO - Azione Prioritaria"
            risk_level = "MEDIO-ALTO"
        elif total_issues > 20:
            overall_status = "DA MIGLIORARE - Piano di Intervento Necessario"
            risk_level = "MEDIO"
        else:
            overall_status = "BUONO - Ottimizzazioni Consigliate"
            risk_level = "BASSO"
        
        return {
            "overall_status": overall_status,
            "risk_level": risk_level,
            "compliance_score": self.compliance.get("overall_score", 0),
            "compliance_level": self.compliance.get("compliance_level", "non_conforme"),
            "total_issues": total_issues,
            "critical_issues": critical_count,
            "high_priority_issues": high_count,
            "estimated_users_affected": user_impact["total_affected_percentage"],
            "key_metrics": {
                "perceivable_score": self._calculate_principle_score("perceivable"),
                "operable_score": self._calculate_principle_score("operable"),
                "understandable_score": self._calculate_principle_score("understandable"),
                "robust_score": self._calculate_principle_score("robust")
            },
            "compliance_gap": 100 - self.compliance.get("overall_score", 0),
            "estimated_effort_days": self._estimate_total_effort_days()
        }
    
    def _generate_quantitative_analysis(self) -> Dict[str, Any]:
        """
        Genera analisi quantitativa dettagliata
        
        Returns:
            Dizionario con metriche quantitative
        """
        all_issues = self.errors + self.warnings
        
        # Statistiche base
        severity_counts = Counter(i.get("severity", "unknown") for i in all_issues)
        type_counts = Counter(i.get("type", "unknown") for i in all_issues)
        source_counts = Counter(i.get("source", "unknown") for i in all_issues)
        
        # Statistiche avanzate
        issue_counts = [i.get("count", 1) for i in all_issues]
        
        return {
            "total_statistics": {
                "total_unique_issues": len(all_issues),
                "total_issue_instances": sum(issue_counts),
                "average_instances_per_issue": statistics.mean(issue_counts) if issue_counts else 0,
                "median_instances_per_issue": statistics.median(issue_counts) if issue_counts else 0,
                "max_instances_single_issue": max(issue_counts) if issue_counts else 0
            },
            "severity_breakdown": {
                "critical": {
                    "count": severity_counts.get("critical", 0),
                    "percentage": self._calculate_percentage(severity_counts.get("critical", 0), len(all_issues))
                },
                "high": {
                    "count": severity_counts.get("high", 0),
                    "percentage": self._calculate_percentage(severity_counts.get("high", 0), len(all_issues))
                },
                "medium": {
                    "count": severity_counts.get("medium", 0),
                    "percentage": self._calculate_percentage(severity_counts.get("medium", 0), len(all_issues))
                },
                "low": {
                    "count": severity_counts.get("low", 0),
                    "percentage": self._calculate_percentage(severity_counts.get("low", 0), len(all_issues))
                }
            },
            "type_distribution": dict(type_counts),
            "scanner_distribution": dict(source_counts),
            "density_metrics": {
                "issues_per_page": len(all_issues),  # Assumendo singola pagina per ora
                "critical_density": severity_counts.get("critical", 0),
                "high_density": severity_counts.get("high", 0)
            }
        }
    
    def _analyze_wcag_compliance(self) -> Dict[str, Any]:
        """
        Analizza conformità WCAG dettagliata
        
        Returns:
            Dizionario con analisi WCAG
        """
        all_issues = self.errors + self.warnings
        
        # Estrai tutti i criteri WCAG
        wcag_criteria = defaultdict(list)
        for issue in all_issues:
            criteria = issue.get("wcag_criteria", "")
            if criteria:
                wcag_criteria[criteria].append(issue)
        
        # Analizza per livello WCAG
        level_a = []
        level_aa = []
        level_aaa = []
        
        for criteria, issues in wcag_criteria.items():
            # Determina livello basato su criterio
            if criteria:
                parts = criteria.split(".")
                if len(parts) >= 3:
                    # Euristica semplice per livello
                    if any(i.get("severity") == "critical" for i in issues):
                        level_a.extend(issues)
                    elif any(i.get("severity") == "high" for i in issues):
                        level_aa.extend(issues)
                    else:
                        level_aaa.extend(issues)
        
        # Criteri più violati
        most_violated = sorted(
            [(k, len(v)) for k, v in wcag_criteria.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "wcag_version": self.compliance.get("wcag_version", "2.1"),
            "target_level": self.compliance.get("wcag_level", "AA"),
            "criteria_violations": {
                "total_criteria_violated": len(wcag_criteria),
                "level_a_violations": len(level_a),
                "level_aa_violations": len(level_aa),
                "level_aaa_violations": len(level_aaa)
            },
            "most_violated_criteria": [
                {
                    "criteria": criteria,
                    "violations": count,
                    "description": self._get_wcag_description(criteria)
                }
                for criteria, count in most_violated
            ],
            "principle_distribution": {
                "perceivable": self.compliance.get("categories", {}).get("perceivable", {}),
                "operable": self.compliance.get("categories", {}).get("operable", {}),
                "understandable": self.compliance.get("categories", {}).get("understandable", {}),
                "robust": self.compliance.get("categories", {}).get("robust", {})
            },
            "compliance_gaps": self._identify_compliance_gaps()
        }
    
    def _analyze_severity_distribution(self) -> Dict[str, Any]:
        """
        Analizza distribuzione severità con dettagli
        
        Returns:
            Dizionario con analisi severità
        """
        severity_details = defaultdict(list)
        
        for issue in self.errors + self.warnings:
            severity = issue.get("severity", "unknown")
            severity_details[severity].append({
                "code": issue.get("code", ""),
                "description": issue.get("description", ""),
                "count": issue.get("count", 1),
                "wcag": issue.get("wcag_criteria", "")
            })
        
        # Calcola statistiche per severità
        severity_stats = {}
        for severity, issues in severity_details.items():
            total_instances = sum(i["count"] for i in issues)
            severity_stats[severity] = {
                "unique_issues": len(issues),
                "total_instances": total_instances,
                "average_instances": total_instances / len(issues) if issues else 0,
                "top_issues": sorted(issues, key=lambda x: x["count"], reverse=True)[:5]
            }
        
        return severity_stats
    
    def _analyze_by_category(self) -> Dict[str, Any]:
        """
        Analizza problemi per categoria funzionale
        
        Returns:
            Dizionario con analisi per categoria
        """
        categories = {
            "images": {"keywords": ["alt", "image", "img"], "issues": []},
            "forms": {"keywords": ["form", "input", "label", "field"], "issues": []},
            "navigation": {"keywords": ["nav", "menu", "link", "anchor"], "issues": []},
            "structure": {"keywords": ["heading", "h1", "h2", "landmark", "region"], "issues": []},
            "color": {"keywords": ["contrast", "color"], "issues": []},
            "language": {"keywords": ["lang", "language"], "issues": []},
            "aria": {"keywords": ["aria", "role"], "issues": []},
            "media": {"keywords": ["video", "audio", "caption"], "issues": []},
            "tables": {"keywords": ["table", "th", "td"], "issues": []},
            "keyboard": {"keywords": ["keyboard", "focus", "tab"], "issues": []}
        }
        
        # Categorizza issues
        for issue in self.errors + self.warnings:
            code = issue.get("code", "").lower()
            desc = issue.get("description", "").lower()
            
            for cat_name, cat_data in categories.items():
                if any(kw in code or kw in desc for kw in cat_data["keywords"]):
                    cat_data["issues"].append(issue)
        
        # Genera statistiche per categoria
        category_stats = {}
        for cat_name, cat_data in categories.items():
            if cat_data["issues"]:
                category_stats[cat_name] = {
                    "total_issues": len(cat_data["issues"]),
                    "critical_count": sum(1 for i in cat_data["issues"] if i.get("severity") == "critical"),
                    "high_count": sum(1 for i in cat_data["issues"] if i.get("severity") == "high"),
                    "impact_score": self._calculate_category_impact(cat_data["issues"]),
                    "top_issues": cat_data["issues"][:3]
                }
        
        return category_stats
    
    def _compare_scanners(self) -> Dict[str, Any]:
        """
        Confronta risultati tra scanner diversi
        
        Returns:
            Dizionario con confronto scanner
        """
        scanner_stats = {}
        
        # Raggruppa issues per scanner
        scanner_issues = defaultdict(list)
        for issue in self.errors + self.warnings:
            source = issue.get("source", "unknown")
            scanner_issues[source].append(issue)
        
        # Calcola statistiche per scanner
        for scanner, issues in scanner_issues.items():
            scanner_stats[scanner] = {
                "score": self.scanner_scores.get(scanner.lower().replace("-", "_"), 0),
                "total_issues": len(issues),
                "critical_found": sum(1 for i in issues if i.get("severity") == "critical"),
                "high_found": sum(1 for i in issues if i.get("severity") == "high"),
                "unique_issues": len(set(i.get("code", "") for i in issues)),
                "effectiveness": self._calculate_scanner_effectiveness(scanner, issues)
            }
        
        # Calcola concordanza tra scanner
        concordance = self._calculate_scanner_concordance(scanner_issues)
        
        return {
            "scanner_performance": scanner_stats,
            "concordance_matrix": concordance,
            "recommended_scanners": self._recommend_scanners(scanner_stats),
            "coverage_analysis": self._analyze_scanner_coverage(scanner_issues)
        }
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """
        Calcola indicatori di trend (per confronti futuri)
        
        Returns:
            Dizionario con indicatori trend
        """
        # Per ora restituisce baseline, in futuro confronterà con scan precedenti
        return {
            "baseline_established": datetime.now().isoformat(),
            "improvement_potential": {
                "quick_wins": self._identify_quick_wins(),
                "high_impact_fixes": self._identify_high_impact_fixes(),
                "estimated_score_improvement": self._estimate_score_improvement()
            },
            "priority_areas": self._identify_priority_areas(),
            "risk_trajectory": "baseline"  # increasing, stable, decreasing
        }
    
    def _generate_benchmarks(self) -> Dict[str, Any]:
        """
        Genera benchmark rispetto a standard industria
        
        Returns:
            Dizionario con benchmark
        """
        score = self.compliance.get("overall_score", 0)
        
        # Benchmark industria (valori tipici)
        industry_benchmarks = {
            "government": 85,
            "finance": 80,
            "e-commerce": 75,
            "media": 70,
            "general": 65
        }
        
        # Determina posizione relativa
        if score >= 90:
            percentile = "Top 5%"
            rating = "Eccellente"
        elif score >= 80:
            percentile = "Top 20%"
            rating = "Molto Buono"
        elif score >= 70:
            percentile = "Top 40%"
            rating = "Buono"
        elif score >= 60:
            percentile = "Media"
            rating = "Sufficiente"
        else:
            percentile = "Sotto Media"
            rating = "Insufficiente"
        
        return {
            "current_score": score,
            "industry_average": industry_benchmarks.get("general", 65),
            "percentile": percentile,
            "rating": rating,
            "comparison": {
                sector: {
                    "benchmark": benchmark,
                    "difference": score - benchmark,
                    "status": "sopra media" if score > benchmark else "sotto media"
                }
                for sector, benchmark in industry_benchmarks.items()
            },
            "maturity_level": self._determine_maturity_level(score),
            "certification_readiness": score >= 85
        }
    
    def _assess_risks(self) -> Dict[str, Any]:
        """
        Valuta rischi legali e reputazionali
        
        Returns:
            Dizionario con valutazione rischi
        """
        critical_count = sum(1 for e in self.errors if e.get("severity") == "critical")
        high_count = sum(1 for e in self.errors if e.get("severity") == "high")
        
        # Calcola rischio legale
        if critical_count > 0:
            legal_risk = "ALTO"
            legal_description = "Presenza di barriere bloccanti - rischio azioni legali"
        elif high_count > 10:
            legal_risk = "MEDIO-ALTO"
            legal_description = "Numerosi problemi significativi - possibili reclami"
        elif high_count > 5:
            legal_risk = "MEDIO"
            legal_description = "Alcuni problemi importanti - rischio moderato"
        else:
            legal_risk = "BASSO"
            legal_description = "Problemi minori - rischio contenuto"
        
        # Calcola rischio reputazionale
        score = self.compliance.get("overall_score", 0)
        if score < 50:
            reputation_risk = "ALTO"
            reputation_description = "Accessibilità molto scarsa - danno reputazionale probabile"
        elif score < 70:
            reputation_risk = "MEDIO"
            reputation_description = "Accessibilità insufficiente - possibile impatto negativo"
        else:
            reputation_risk = "BASSO"
            reputation_description = "Accessibilità accettabile - rischio reputazionale minimo"
        
        return {
            "legal_risk": {
                "level": legal_risk,
                "description": legal_description,
                "factors": [
                    f"{critical_count} problemi critici",
                    f"{high_count} problemi ad alta severità",
                    f"Score conformità: {score}/100"
                ],
                "mitigation": "Risolvere immediatamente problemi critici e alti"
            },
            "reputation_risk": {
                "level": reputation_risk,
                "description": reputation_description,
                "factors": [
                    f"Score complessivo: {score}/100",
                    f"Livello conformità: {self.compliance.get('compliance_level', 'non_conforme')}"
                ],
                "mitigation": "Implementare piano di miglioramento progressivo"
            },
            "business_impact": {
                "potential_users_excluded": self._calculate_user_impact()["total_affected_percentage"],
                "market_loss_risk": "Alto" if score < 60 else "Medio" if score < 80 else "Basso",
                "competitive_disadvantage": score < 70
            },
            "compliance_deadline": "2025-06-28",
            "time_to_compliance": self._calculate_time_to_compliance()
        }
    
    def _estimate_remediation_effort(self) -> Dict[str, Any]:
        """
        Stima effort per remediation
        
        Returns:
            Dizionario con stime effort
        """
        effort_by_severity = {
            "critical": 4,  # ore per issue
            "high": 3,
            "medium": 2,
            "low": 1
        }
        
        total_hours = 0
        effort_breakdown = {}
        
        for severity, hours in effort_by_severity.items():
            count = sum(1 for i in self.errors + self.warnings if i.get("severity") == severity)
            severity_hours = count * hours
            total_hours += severity_hours
            effort_breakdown[severity] = {
                "issues": count,
                "hours_per_issue": hours,
                "total_hours": severity_hours
            }
        
        # Aggiungi overhead per testing e review (20%)
        overhead = total_hours * 0.2
        total_with_overhead = total_hours + overhead
        
        # Calcola costi (€50/ora)
        hourly_rate = 50
        total_cost = total_with_overhead * hourly_rate
        
        # Calcola timeline
        hours_per_day = 6
        days_needed = total_with_overhead / hours_per_day
        
        return {
            "effort_breakdown": effort_breakdown,
            "development_hours": total_hours,
            "testing_hours": overhead,
            "total_hours": total_with_overhead,
            "estimated_days": round(days_needed, 1),
            "estimated_weeks": round(days_needed / 5, 1),
            "estimated_cost_eur": round(total_cost, 2),
            "team_size_recommendation": self._recommend_team_size(days_needed),
            "priority_schedule": self._generate_priority_schedule()
        }
    
    # Metodi helper privati
    
    def _calculate_percentage(self, value: int, total: int) -> float:
        """Calcola percentuale"""
        return round((value / total * 100) if total > 0 else 0, 1)
    
    def _calculate_principle_score(self, principle: str) -> int:
        """Calcola score per principio WCAG"""
        category = self.compliance.get("categories", {}).get(principle, {})
        errors = category.get("errors", 0)
        warnings = category.get("warnings", 0)
        
        # Formula semplice per score
        penalty = (errors * 15) + (warnings * 5)
        return max(0, 100 - penalty)
    
    def _calculate_user_impact(self) -> Dict[str, Any]:
        """Calcola impatto stimato sugli utenti"""
        # Stime basate su statistiche disabilità
        impact = {
            "visual_impairment": 0,
            "motor_impairment": 0,
            "hearing_impairment": 0,
            "cognitive_impairment": 0
        }
        
        for issue in self.errors:
            code = issue.get("code", "").lower()
            if "alt" in code or "contrast" in code:
                impact["visual_impairment"] += issue.get("count", 1)
            if "keyboard" in code or "focus" in code:
                impact["motor_impairment"] += issue.get("count", 1)
            if "caption" in code or "audio" in code:
                impact["hearing_impairment"] += issue.get("count", 1)
            if "heading" in code or "label" in code:
                impact["cognitive_impairment"] += issue.get("count", 1)
        
        # Percentuali popolazione (stime WHO)
        population_percentages = {
            "visual_impairment": 2.2,
            "motor_impairment": 1.0,
            "hearing_impairment": 0.5,
            "cognitive_impairment": 1.0
        }
        
        total_affected = sum(
            population_percentages[imp] for imp, count in impact.items() if count > 0
        )
        
        return {
            "total_affected_percentage": min(total_affected, 15),  # Cap al 15%
            "breakdown": impact
        }
    
    def _estimate_total_effort_days(self) -> float:
        """Stima giorni totali di effort"""
        hours = sum(
            4 if i.get("severity") == "critical" else
            3 if i.get("severity") == "high" else
            2 if i.get("severity") == "medium" else 1
            for i in self.errors + self.warnings
        )
        return round(hours / 6, 1)  # 6 ore produttive al giorno
    
    def _get_wcag_description(self, criteria: str) -> str:
        """Ottiene descrizione criterio WCAG"""
        descriptions = {
            "1.1.1": "Non-text Content",
            "1.3.1": "Info and Relationships",
            "1.4.3": "Contrast (Minimum)",
            "2.1.1": "Keyboard",
            "2.4.1": "Bypass Blocks",
            "2.4.2": "Page Titled",
            "2.4.4": "Link Purpose",
            "3.1.1": "Language of Page",
            "3.3.2": "Labels or Instructions",
            "4.1.1": "Parsing",
            "4.1.2": "Name, Role, Value"
        }
        return descriptions.get(criteria, "")
    
    def _identify_compliance_gaps(self) -> List[str]:
        """Identifica gap di conformità principali"""
        gaps = []
        
        if sum(1 for e in self.errors if e.get("severity") == "critical") > 0:
            gaps.append("Presenza di barriere critiche all'accesso")
        
        categories = self.compliance.get("categories", {})
        for principle, data in categories.items():
            if data.get("errors", 0) > 5:
                gaps.append(f"Principio {principle}: {data['errors']} errori")
        
        return gaps[:5]  # Top 5 gaps
    
    def _calculate_category_impact(self, issues: List[Dict]) -> int:
        """Calcola impatto di una categoria di issues"""
        severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
        total = sum(
            severity_weights.get(i.get("severity", "low"), 1) * i.get("count", 1)
            for i in issues
        )
        return min(total, 100)  # Cap a 100
    
    def _calculate_scanner_effectiveness(self, scanner: str, issues: List[Dict]) -> float:
        """Calcola effectiveness di uno scanner"""
        critical_found = sum(1 for i in issues if i.get("severity") == "critical")
        high_found = sum(1 for i in issues if i.get("severity") == "high")
        
        # Formula pesata
        effectiveness = (critical_found * 10 + high_found * 5 + len(issues)) / max(len(issues), 1)
        return round(min(effectiveness, 10), 1)  # Score 0-10
    
    def _calculate_scanner_concordance(self, scanner_issues: Dict) -> Dict:
        """Calcola concordanza tra scanner"""
        # Semplificato per ora
        return {
            "agreement_percentage": 75,
            "unique_findings_per_scanner": {
                scanner: len(issues)
                for scanner, issues in scanner_issues.items()
            }
        }
    
    def _recommend_scanners(self, scanner_stats: Dict) -> List[str]:
        """Raccomanda scanner più efficaci"""
        sorted_scanners = sorted(
            scanner_stats.items(),
            key=lambda x: x[1].get("effectiveness", 0),
            reverse=True
        )
        return [s[0] for s in sorted_scanners[:3]]
    
    def _analyze_scanner_coverage(self, scanner_issues: Dict) -> Dict:
        """Analizza copertura degli scanner"""
        all_codes = set()
        scanner_codes = {}
        
        for scanner, issues in scanner_issues.items():
            codes = set(i.get("code", "") for i in issues)
            scanner_codes[scanner] = codes
            all_codes.update(codes)
        
        return {
            "total_unique_issues": len(all_codes),
            "coverage_by_scanner": {
                scanner: len(codes) / len(all_codes) * 100 if all_codes else 0
                for scanner, codes in scanner_codes.items()
            }
        }
    
    def _identify_quick_wins(self) -> List[Dict]:
        """Identifica quick wins"""
        quick_wins = []
        
        for issue in self.warnings:
            if issue.get("severity") == "low":
                quick_wins.append({
                    "issue": issue.get("code"),
                    "effort": "Basso",
                    "impact": "Medio"
                })
        
        return quick_wins[:10]
    
    def _identify_high_impact_fixes(self) -> List[Dict]:
        """Identifica fix ad alto impatto"""
        return [
            {
                "issue": issue.get("code"),
                "description": issue.get("description"),
                "impact": "Alto",
                "instances": issue.get("count", 1)
            }
            for issue in self.errors
            if issue.get("severity") in ["critical", "high"]
        ][:10]
    
    def _estimate_score_improvement(self) -> int:
        """Stima miglioramento score possibile"""
        current = self.compliance.get("overall_score", 0)
        
        # Rimuovendo critici: +20 punti
        # Rimuovendo high: +15 punti  
        # Rimuovendo medium: +10 punti
        
        critical_count = sum(1 for e in self.errors if e.get("severity") == "critical")
        high_count = sum(1 for e in self.errors if e.get("severity") == "high")
        
        potential_improvement = (critical_count * 20) + (high_count * 10)
        return min(current + potential_improvement, 95)
    
    def _identify_priority_areas(self) -> List[str]:
        """Identifica aree prioritarie"""
        areas = []
        
        # Analizza per categoria
        category_issues = defaultdict(int)
        for issue in self.errors:
            if "alt" in issue.get("code", "").lower():
                category_issues["Immagini"] += issue.get("count", 1)
            elif "contrast" in issue.get("code", "").lower():
                category_issues["Contrasto"] += issue.get("count", 1)
            elif "form" in issue.get("code", "").lower() or "label" in issue.get("code", "").lower():
                category_issues["Form"] += issue.get("count", 1)
            elif "heading" in issue.get("code", "").lower():
                category_issues["Struttura"] += issue.get("count", 1)
        
        # Ordina per impatto
        sorted_categories = sorted(category_issues.items(), key=lambda x: x[1], reverse=True)
        
        return [cat[0] for cat in sorted_categories[:5]]
    
    def _determine_maturity_level(self, score: int) -> str:
        """Determina livello di maturità accessibilità"""
        if score >= 90:
            return "Livello 5 - Ottimizzato"
        elif score >= 80:
            return "Livello 4 - Gestito"
        elif score >= 70:
            return "Livello 3 - Definito"
        elif score >= 60:
            return "Livello 2 - Ripetibile"
        else:
            return "Livello 1 - Iniziale"
    
    def _calculate_time_to_compliance(self) -> str:
        """Calcola tempo stimato per conformità"""
        days = self._estimate_total_effort_days()
        
        if days <= 30:
            return "1 mese"
        elif days <= 60:
            return "2 mesi"
        elif days <= 90:
            return "3 mesi"
        else:
            return "3-6 mesi"
    
    def _recommend_team_size(self, days_needed: float) -> str:
        """Raccomanda dimensione team"""
        if days_needed <= 10:
            return "1 sviluppatore"
        elif days_needed <= 30:
            return "2 sviluppatori"
        elif days_needed <= 60:
            return "3-4 sviluppatori"
        else:
            return "Team dedicato (4+ sviluppatori)"
    
    def _generate_priority_schedule(self) -> List[Dict]:
        """Genera schedule prioritizzato"""
        return [
            {
                "week": 1,
                "focus": "Problemi Critici",
                "description": "Risoluzione barriere bloccanti"
            },
            {
                "week": 2,
                "focus": "Problemi Alta Severità",
                "description": "Fix problemi ad alto impatto"
            },
            {
                "week": 3,
                "focus": "Form e Navigazione",
                "description": "Miglioramento interattività"
            },
            {
                "week": 4,
                "focus": "Testing e Validazione",
                "description": "Verifica con screen reader"
            }
        ]