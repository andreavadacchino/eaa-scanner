"""
Scan-only mode for EAA Scanner - NO report generation, NO charts, NO PDF
Solo raccolta e normalizzazione dati per velocità massima
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import Config
from .scanners.pa11y import Pa11yScanner
from .scanners.axe import AxeScanner
from .scanners.lighthouse import LighthouseScanner
from .scanners.wave import WaveScanner
# Le funzioni di normalizzazione non esistono ancora, le creiamo inline

logger = logging.getLogger(__name__)

def normalize_issues(issues: List[Dict], scanner: str) -> List[Dict]:
    """Normalizza le issues da uno scanner specifico"""
    normalized = []
    
    # Assicurati che issues sia una lista
    if not isinstance(issues, list):
        issues = []
    
    for issue in issues:
        # Gestisci diversi formati per scanner
        if scanner == 'pa11y':
            normalized_issue = {
                "scanner": scanner,
                "title": issue.get("message", "Issue"),
                "description": issue.get("context", ""),
                "severity": _map_severity(issue.get("type", "notice")),
                "wcag_criterion": issue.get("code", ""),
                "selector": issue.get("selector", ""),
                "html": issue.get("context", ""),
                "fix": ""
            }
        elif scanner == 'axe':
            # Gestisci nodes in modo sicuro
            nodes = issue.get("nodes", [])
            first_node = nodes[0] if isinstance(nodes, list) and len(nodes) > 0 else {}
            
            normalized_issue = {
                "scanner": scanner,
                "title": issue.get("description", issue.get("id", "Issue")),
                "description": issue.get("help", ""),
                "severity": _map_severity(issue.get("impact", "minor")),
                "wcag_criterion": ", ".join(issue.get("tags", [])),
                "selector": str(first_node.get("target", [])) if isinstance(first_node, dict) else "",
                "html": first_node.get("html", "") if isinstance(first_node, dict) else "",
                "fix": issue.get("helpUrl", "")
            }
        elif scanner == 'lighthouse':
            normalized_issue = {
                "scanner": scanner,
                "title": issue.get("id", "Issue"),
                "description": issue.get("title", ""),
                "severity": _map_severity(issue.get("score", 0)),
                "wcag_criterion": "",
                "selector": "",
                "html": "",
                "fix": ""
            }
        else:
            # Formato generico
            normalized_issue = {
                "scanner": scanner,
                "title": issue.get("title", issue.get("message", "Issue")),
                "description": issue.get("description", issue.get("help", "")),
                "severity": _map_severity(issue.get("severity", issue.get("impact", "low"))),
                "wcag_criterion": issue.get("wcag", issue.get("code", "")),
                "selector": issue.get("selector", issue.get("target", "")),
                "html": issue.get("html", ""),
                "fix": issue.get("fix", issue.get("helpUrl", ""))
            }
        
        normalized.append(normalized_issue)
    
    return normalized

def _map_severity(severity: Any) -> str:
    """Mappa le severità ai nostri livelli standard"""
    if isinstance(severity, (int, float)):
        # Per Lighthouse scores
        if severity < 0.5:
            return "critical"
        elif severity < 0.7:
            return "high"
        elif severity < 0.9:
            return "medium"
        else:
            return "low"
    
    severity = str(severity).lower()
    if severity in ["critical", "serious", "error"]:
        return "critical"
    elif severity in ["high", "error"]:
        return "high"
    elif severity in ["medium", "moderate", "warning"]:
        return "medium"
    elif severity in ["notice", "minor", "low"]:
        return "low"
    else:
        return "low"

def aggregate_results(issues: List[Dict]) -> Dict:
    """Aggrega i risultati normalizzati"""
    return {
        "total_issues": len(issues),
        "by_severity": _count_by_field(issues, "severity"),
        "by_wcag": _count_by_field(issues, "wcag_criterion"),
        "by_scanner": _count_by_field(issues, "scanner")
    }

def _count_by_field(issues: List[Dict], field: str) -> Dict[str, int]:
    """Conta issues per campo specifico"""
    counts = {}
    for issue in issues:
        value = issue.get(field, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts

def calculate_compliance_score(aggregated: Dict) -> float:
    """Calcola il punteggio di compliance basato sulle issues"""
    total = aggregated.get("total_issues", 0)
    if total == 0:
        return 100.0
    
    severity_weights = {
        "critical": 10,
        "high": 5,
        "medium": 2,
        "low": 1
    }
    
    by_severity = aggregated.get("by_severity", {})
    weighted_score = 0
    
    for severity, weight in severity_weights.items():
        count = by_severity.get(severity, 0)
        weighted_score += count * weight
    
    # Formula per il punteggio (100 - penalità, min 0)
    penalty = min(100, weighted_score * 2)  # Scalamento della penalità
    return max(0, 100 - penalty)

class ScanOnlyRunner:
    """Runner ottimizzato per sola scansione senza generazione report"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scanners = self._init_scanners()
        self.progress_callback = None  # Callback per aggiornamenti progresso
        
    def _init_scanners(self) -> Dict[str, Any]:
        """Inizializza solo gli scanner abilitati"""
        scanners = {}
        
        if self.config.scanners_enabled.pa11y:
            # Pa11yScanner si aspetta timeout_ms e simulate come parametri
            scanners['pa11y'] = Pa11yScanner(
                timeout_ms=60000, 
                simulate=self.config.simulate
            )
            
        if self.config.scanners_enabled.axe_core:
            # AxeScanner si aspetta simulate come parametro 
            scanners['axe'] = AxeScanner(simulate=self.config.simulate)
            
        if self.config.scanners_enabled.lighthouse:
            # LighthouseScanner si aspetta simulate come parametro
            scanners['lighthouse'] = LighthouseScanner(simulate=self.config.simulate)
            
        if self.config.scanners_enabled.wave and self.config.wave_api_key:
            # WaveScanner si aspetta api_key e simulate
            scanners['wave'] = WaveScanner(
                api_key=self.config.wave_api_key,
                simulate=self.config.simulate
            )
            
        return scanners
    
    def run_scan(self, url: str) -> Dict[str, Any]:
        """
        Esegue SOLO la scansione di accessibilità senza generare report
        Restituisce i dati normalizzati pronti per il frontend
        """
        logger.info(f"🚀 SCAN-ONLY MODE: Avvio scansione per {url}")
        
        # Crea directory output minimale
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"output/scan_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Risultati degli scanner
        scan_results = {}
        raw_results = {}
        
        # Esegui scanner in parallelo per velocità
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for name, scanner in self.scanners.items():
                logger.info(f"▶️ Avvio scanner {name} per {url}")
                # Notifica inizio scanner
                if self.progress_callback:
                    try:
                        self.progress_callback(name, 0)
                    except Exception as e:
                        logger.error(f"Errore callback progresso {name}: {e}")
                
                future = executor.submit(self._run_single_scanner, name, scanner, url)
                futures[future] = name
            
            # Raccogli risultati
            completed_scanners = 0
            total_scanners = len(futures)
            
            for future in as_completed(futures):
                scanner_name = futures[future]
                try:
                    # Notifica progresso scanner al 50% (inizio elaborazione)
                    if self.progress_callback:
                        try:
                            self.progress_callback(scanner_name, 50)
                        except Exception as e:
                            logger.error(f"Errore callback progresso {scanner_name}: {e}")
                    
                    result = future.result(timeout=60)  # Max 60 secondi per scanner
                    if result:
                        scan_results[scanner_name] = result
                        raw_results[scanner_name] = result
                        logger.info(f"✅ Scanner {scanner_name} completato")
                    else:
                        logger.warning(f"⚠️ Scanner {scanner_name} non ha restituito risultati")
                    
                    # Notifica completamento scanner
                    completed_scanners += 1
                    if self.progress_callback:
                        try:
                            self.progress_callback(scanner_name, 100)
                        except Exception as e:
                            logger.error(f"Errore callback progresso {scanner_name}: {e}")
                    
                except Exception as e:
                    logger.error(f"❌ Errore scanner {scanner_name}: {e}")
                    completed_scanners += 1
                    
                    # Notifica errore scanner
                    if self.progress_callback:
                        try:
                            self.progress_callback(scanner_name, -1)  # -1 indica errore
                        except Exception as e:
                            logger.error(f"Errore callback progresso {scanner_name}: {e}")
        
        # Normalizza i risultati
        logger.info("🔧 Normalizzazione risultati...")
        normalized_issues = []
        
        for scanner, data in scan_results.items():
            # Gestisci i diversi formati di risultati degli scanner
            issues = []
            
            # Pa11yResult e AxeResult hanno un attributo 'json' con i dati
            if hasattr(data, 'json') and isinstance(data.json, dict):
                json_data = data.json
                if 'issues' in json_data:
                    issues = json_data['issues']
                elif 'violations' in json_data:  # Axe format
                    issues = json_data['violations']
                elif 'results' in json_data:  # Alternative format
                    issues = json_data['results']
                elif 'audits' in json_data and scanner == 'lighthouse':  # Lighthouse format
                    # Estrai solo gli audits falliti (score < 1)
                    audits = json_data['audits']
                    for audit_id, audit_data in audits.items():
                        if isinstance(audit_data, dict):
                            score = audit_data.get('score', 1)
                            if score is not None and score < 1:
                                issues.append({
                                    'id': audit_id,
                                    'title': audit_data.get('title', ''),
                                    'description': audit_data.get('description', ''),
                                    'score': score,
                                    'details': audit_data.get('details', {})
                                })
            # Dati già in formato dizionario
            elif isinstance(data, dict):
                if 'issues' in data:
                    issues = data['issues']
                elif 'violations' in data:  # Axe format
                    issues = data['violations']
                elif 'results' in data:  # Alternative format
                    issues = data['results']
                elif 'audits' in data and scanner == 'lighthouse':  # Lighthouse format
                    # Estrai solo gli audits falliti (score < 1)
                    audits = data['audits']
                    for audit_id, audit_data in audits.items():
                        if isinstance(audit_data, dict):
                            score = audit_data.get('score', 1)
                            if score is not None and score < 1:
                                issues.append({
                                    'id': audit_id,
                                    'title': audit_data.get('title', ''),
                                    'description': audit_data.get('description', ''),
                                    'score': score,
                                    'details': audit_data.get('details', {})
                                })
            
            if issues:
                logger.info(f"📋 Scanner {scanner} trovate {len(issues)} issues")
                normalized = normalize_issues(issues, scanner)
                normalized_issues.extend(normalized)
            else:
                logger.warning(f"⚠️ Scanner {scanner} nessuna issue trovata")
        
        # Notifica completamento normalizzazione
        if self.progress_callback:
            try:
                self.progress_callback("normalizing", 90)
            except Exception as e:
                logger.error(f"Errore callback normalizzazione: {e}")
        
        # Aggrega risultati
        aggregated = aggregate_results(normalized_issues)
        
        # Calcola compliance score
        compliance_score = calculate_compliance_score(aggregated)
        
        # Notifica completamento finale
        if self.progress_callback:
            try:
                self.progress_callback("completed", 100)
            except Exception as e:
                logger.error(f"Errore callback finale: {e}")
        
        # Prepara risposta ottimizzata per frontend
        response = {
            "url": url,
            "scan_date": datetime.now().isoformat(),
            "scanners_used": list(scan_results.keys()),
            "compliance_score": compliance_score,
            "issues_total": len(normalized_issues),
            "issues_by_severity": self._count_by_severity(normalized_issues),
            "issues_by_wcag": self._count_by_wcag(normalized_issues),
            "normalized_issues": normalized_issues[:100],  # Limita per performance
            "raw_data": {
                "pa11y": raw_results.get('pa11y', {}),
                "axe": raw_results.get('axe', {}),
                "lighthouse": raw_results.get('lighthouse', {}),
                "wave": raw_results.get('wave', {})
            },
            "output_dir": str(output_dir)
        }
        
        # Salva solo i dati essenziali
        summary_path = output_dir / "scan_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(response, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✨ Scansione completata! Score: {compliance_score}%, Issues: {len(normalized_issues)}")
        
        return response
    
    def _run_single_scanner(self, name: str, scanner: Any, url: str) -> Optional[Dict]:
        """Esegue un singolo scanner con error handling"""
        try:
            if hasattr(scanner, 'scan'):
                return scanner.scan(url)
            elif hasattr(scanner, 'run'):
                return scanner.run(url)
            else:
                logger.error(f"Scanner {name} non ha metodo scan() o run()")
                return None
        except Exception as e:
            logger.error(f"Errore esecuzione scanner {name}: {e}")
            return None
    
    def _count_by_severity(self, issues: List[Dict]) -> Dict[str, int]:
        """Conta issues per severità"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get('severity', 'low').lower()
            if severity in counts:
                counts[severity] += 1
        return counts
    
    def _count_by_wcag(self, issues: List[Dict]) -> Dict[str, int]:
        """Conta issues per criterio WCAG"""
        wcag_counts = {}
        for issue in issues:
            wcag = issue.get('wcag_criterion', 'unknown')
            wcag_counts[wcag] = wcag_counts.get(wcag, 0) + 1
        return wcag_counts


def run_scan_only(config: Config, url: str) -> Dict[str, Any]:
    """
    Entry point per scan-only mode
    """
    runner = ScanOnlyRunner(config)
    return runner.run_scan(url)

def run_scan_only_with_callback(config: Config, url: str, progress_callback=None) -> Dict[str, Any]:
    """
    Entry point per scan-only mode con callback di progresso
    """
    runner = ScanOnlyRunner(config)
    runner.progress_callback = progress_callback  # Aggiungi callback al runner
    return runner.run_scan(url)