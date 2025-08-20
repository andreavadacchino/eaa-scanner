"""
Sistema di gestione piano di remediation per conformità EAA
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class RemediationIssue:
    """
    Singolo issue da risolvere nel piano di remediation
    """
    issue_id: str
    code: str
    description: str
    severity: str
    wcag_criteria: str
    affected_elements: List[str] = field(default_factory=list)
    pages_affected: List[str] = field(default_factory=list)
    
    # Remediation details
    remediation_approach: str = ""
    code_example: str = ""
    testing_approach: str = ""
    
    # Effort estimation
    estimated_hours: float = 0
    complexity: str = "medium"  # low, medium, high
    dependencies: List[str] = field(default_factory=list)
    
    # Tracking
    status: str = "pending"  # pending, in_progress, completed, verified
    assigned_to: Optional[str] = None
    started_date: Optional[str] = None
    completed_date: Optional[str] = None
    verified_date: Optional[str] = None
    notes: str = ""
    
    def calculate_priority_score(self) -> int:
        """
        Calcola score di priorità per ordinamento
        
        Returns:
            Score priorità (0-100)
        """
        severity_scores = {
            "critical": 40,
            "high": 30,
            "medium": 20,
            "low": 10
        }
        
        complexity_scores = {
            "low": 10,
            "medium": 5,
            "high": 0
        }
        
        # Base score da severità
        score = severity_scores.get(self.severity, 0)
        
        # Bonus per bassa complessità (quick wins)
        score += complexity_scores.get(self.complexity, 0)
        
        # Bonus per numero di pagine impattate
        score += min(len(self.pages_affected) * 5, 30)
        
        # Bonus per numero di elementi impattati
        score += min(len(self.affected_elements) * 2, 20)
        
        return min(score, 100)
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)


@dataclass
class RemediationPhase:
    """
    Fase del piano di remediation
    """
    phase_number: int
    name: str
    description: str
    start_date: str
    end_date: str
    duration_days: int
    issues: List[RemediationIssue] = field(default_factory=list)
    
    # Tracking
    status: str = "pending"  # pending, in_progress, completed
    progress_percentage: int = 0
    
    # Metriche
    total_hours: float = 0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    
    def add_issue(self, issue: RemediationIssue) -> None:
        """
        Aggiunge issue alla fase
        
        Args:
            issue: Issue da aggiungere
        """
        self.issues.append(issue)
        self.total_issues = len(self.issues)
        self.total_hours += issue.estimated_hours
        
        if issue.severity == "critical":
            self.critical_issues += 1
        elif issue.severity == "high":
            self.high_issues += 1
    
    def calculate_progress(self) -> int:
        """
        Calcola percentuale di progresso
        
        Returns:
            Percentuale completamento (0-100)
        """
        if not self.issues:
            return 0
        
        completed = sum(1 for i in self.issues if i.status == "completed")
        verified = sum(1 for i in self.issues if i.status == "verified")
        
        return int(((completed + verified) / self.total_issues) * 100)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Ottiene statistiche della fase
        
        Returns:
            Dizionario con statistiche
        """
        return {
            "phase_number": self.phase_number,
            "name": self.name,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "total_hours": self.total_hours,
            "progress": self.calculate_progress(),
            "status": self.status,
            "duration_days": self.duration_days,
            "issues_by_status": {
                "pending": sum(1 for i in self.issues if i.status == "pending"),
                "in_progress": sum(1 for i in self.issues if i.status == "in_progress"),
                "completed": sum(1 for i in self.issues if i.status == "completed"),
                "verified": sum(1 for i in self.issues if i.status == "verified")
            }
        }
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        data = asdict(self)
        data["progress_percentage"] = self.calculate_progress()
        return data


class RemediationPlanManager:
    """
    Gestore completo del piano di remediation
    """
    
    def __init__(self, scan_results: Dict[str, Any], organization_name: str):
        """
        Inizializza il manager
        
        Args:
            scan_results: Risultati della scansione normalizzati
            organization_name: Nome organizzazione
        """
        self.scan_results = scan_results
        self.organization_name = organization_name
        self.phases: List[RemediationPhase] = []
        self.all_issues: List[RemediationIssue] = []
        
        # Configurazione
        self.hourly_rate_eur = 50  # Tariffa oraria sviluppatore
        self.hours_per_day = 6  # Ore produttive al giorno
        self.team_size = 2  # Dimensione team di default
        
        # Genera piano automaticamente
        self._generate_plan()
    
    def _generate_plan(self) -> None:
        """
        Genera piano di remediation automatico basato sui risultati
        """
        # Converti errori in RemediationIssue
        self._convert_errors_to_issues()
        
        # Ordina per priorità
        self.all_issues.sort(key=lambda x: x.calculate_priority_score(), reverse=True)
        
        # Crea fasi
        self._create_phases()
        
        # Distribuisci issues nelle fasi
        self._distribute_issues()
    
    def _convert_errors_to_issues(self) -> None:
        """
        Converte errori del report in RemediationIssue
        """
        errors = self.scan_results.get("detailed_results", {}).get("errors", [])
        warnings = self.scan_results.get("detailed_results", {}).get("warnings", [])
        
        issue_counter = 1
        
        # Processa errori
        for error in errors:
            issue = RemediationIssue(
                issue_id=f"ISSUE-{issue_counter:04d}",
                code=error.get("code", ""),
                description=error.get("description", ""),
                severity=error.get("severity", "medium"),
                wcag_criteria=error.get("wcag_criteria", ""),
                remediation_approach=error.get("remediation", ""),
                estimated_hours=self._estimate_hours(error.get("severity", "medium")),
                complexity=self._determine_complexity(error)
            )
            
            # Aggiungi esempio di codice per problemi comuni
            issue.code_example = self._get_code_example(error.get("code", ""))
            issue.testing_approach = self._get_testing_approach(error.get("code", ""))
            
            self.all_issues.append(issue)
            issue_counter += 1
        
        # Processa warning ad alta priorità
        high_priority_warnings = [w for w in warnings if w.get("severity") in ["high", "medium"]]
        for warning in high_priority_warnings[:20]:  # Limita a top 20
            issue = RemediationIssue(
                issue_id=f"ISSUE-{issue_counter:04d}",
                code=warning.get("code", ""),
                description=warning.get("description", ""),
                severity=warning.get("severity", "low"),
                wcag_criteria=warning.get("wcag_criteria", ""),
                remediation_approach=warning.get("remediation", ""),
                estimated_hours=self._estimate_hours(warning.get("severity", "low")),
                complexity="low"
            )
            
            self.all_issues.append(issue)
            issue_counter += 1
    
    def _create_phases(self) -> None:
        """
        Crea fasi del piano di remediation
        """
        start_date = datetime.now()
        
        phases_config = [
            {
                "name": "Fase 1: Barriere Critiche",
                "description": "Risoluzione immediata di problemi bloccanti che impediscono l'accesso al contenuto",
                "duration_days": 10,
                "severity_filter": ["critical"]
            },
            {
                "name": "Fase 2: Problemi ad Alto Impatto",
                "description": "Risoluzione di problemi significativi che impattano gravemente l'usabilità",
                "duration_days": 15,
                "severity_filter": ["high"]
            },
            {
                "name": "Fase 3: Miglioramenti Funzionali",
                "description": "Ottimizzazione di elementi che migliorano l'esperienza utente",
                "duration_days": 20,
                "severity_filter": ["medium"]
            },
            {
                "name": "Fase 4: Ottimizzazioni e Quick Wins",
                "description": "Problemi minori e miglioramenti rapidi per raggiungere piena conformità",
                "duration_days": 10,
                "severity_filter": ["low"]
            },
            {
                "name": "Fase 5: Testing e Validazione",
                "description": "Test completo con tecnologie assistive e validazione conformità",
                "duration_days": 5,
                "severity_filter": []
            }
        ]
        
        current_date = start_date
        
        for i, config in enumerate(phases_config, 1):
            end_date = current_date + timedelta(days=config["duration_days"])
            
            phase = RemediationPhase(
                phase_number=i,
                name=config["name"],
                description=config["description"],
                start_date=current_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                duration_days=config["duration_days"]
            )
            
            self.phases.append(phase)
            current_date = end_date
    
    def _distribute_issues(self) -> None:
        """
        Distribuisce issues nelle fasi appropriate
        """
        # Mappa severità -> fase
        severity_phase_map = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        
        for issue in self.all_issues:
            phase_num = severity_phase_map.get(issue.severity, 3)
            
            # Trova la fase corrispondente
            for phase in self.phases:
                if phase.phase_number == phase_num:
                    phase.add_issue(issue)
                    break
    
    def _estimate_hours(self, severity: str) -> float:
        """
        Stima ore necessarie basate su severità
        
        Args:
            severity: Livello di severità
            
        Returns:
            Ore stimate
        """
        estimates = {
            "critical": 4.0,
            "high": 3.0,
            "medium": 2.0,
            "low": 1.0
        }
        return estimates.get(severity, 2.0)
    
    def _determine_complexity(self, error: Dict) -> str:
        """
        Determina complessità di un errore
        
        Args:
            error: Dizionario errore
            
        Returns:
            Livello complessità
        """
        code = error.get("code", "").lower()
        
        # Pattern per complessità
        low_complexity = ["alt", "title", "label", "lang"]
        high_complexity = ["aria", "role", "keyboard", "focus"]
        
        if any(pattern in code for pattern in high_complexity):
            return "high"
        elif any(pattern in code for pattern in low_complexity):
            return "low"
        else:
            return "medium"
    
    def _get_code_example(self, issue_code: str) -> str:
        """
        Ottiene esempio di codice per fix comune
        
        Args:
            issue_code: Codice dell'issue
            
        Returns:
            Esempio di codice
        """
        examples = {
            "alt_missing": """
<!-- PRIMA (Errato) -->
<img src="logo.jpg">

<!-- DOPO (Corretto) -->
<img src="logo.jpg" alt="Logo aziendale ACME Corporation">
""",
            "contrast": """
/* PRIMA (Contrasto insufficiente) */
.text {
    color: #999999;
    background: #ffffff;
}

/* DOPO (Contrasto corretto 4.5:1) */
.text {
    color: #595959;
    background: #ffffff;
}
""",
            "label_missing": """
<!-- PRIMA (Errato) -->
<input type="text" id="email">

<!-- DOPO (Corretto) -->
<label for="email">Indirizzo Email</label>
<input type="text" id="email" aria-required="true">
""",
            "heading": """
<!-- PRIMA (Ordine errato) -->
<h1>Titolo</h1>
<h3>Sottotitolo</h3>

<!-- DOPO (Ordine corretto) -->
<h1>Titolo</h1>
<h2>Sottotitolo</h2>
""",
            "lang": """
<!-- PRIMA (Lingua mancante) -->
<html>

<!-- DOPO (Lingua specificata) -->
<html lang="it">
"""
        }
        
        # Cerca match parziale
        for key, example in examples.items():
            if key in issue_code.lower():
                return example
        
        return "// Implementare fix appropriato secondo linee guida WCAG"
    
    def _get_testing_approach(self, issue_code: str) -> str:
        """
        Ottiene approccio di testing per validare il fix
        
        Args:
            issue_code: Codice dell'issue
            
        Returns:
            Approccio di testing
        """
        testing_approaches = {
            "alt": "Testare con NVDA/JAWS che l'immagine venga annunciata correttamente",
            "contrast": "Verificare contrasto con Color Contrast Analyzer (minimo 4.5:1)",
            "label": "Verificare che il campo sia annunciato correttamente dallo screen reader",
            "heading": "Verificare struttura heading con HeadingsMap extension",
            "keyboard": "Navigare solo con tastiera verificando tutti gli elementi interattivi",
            "aria": "Testare con screen reader che i ruoli ARIA siano annunciati correttamente",
            "lang": "Verificare pronuncia corretta con screen reader in italiano"
        }
        
        # Cerca match parziale
        for key, approach in testing_approaches.items():
            if key in issue_code.lower():
                return approach
        
        return "Testare con screen reader e navigazione da tastiera"
    
    def get_executive_summary(self) -> Dict[str, Any]:
        """
        Genera sommario esecutivo del piano
        
        Returns:
            Dizionario con sommario
        """
        total_issues = len(self.all_issues)
        total_hours = sum(issue.estimated_hours for issue in self.all_issues)
        total_days = total_hours / self.hours_per_day
        total_cost = total_hours * self.hourly_rate_eur
        
        # Calcola durata totale
        total_duration_days = sum(phase.duration_days for phase in self.phases)
        
        # Conta per severità
        severity_counts = {
            "critical": sum(1 for i in self.all_issues if i.severity == "critical"),
            "high": sum(1 for i in self.all_issues if i.severity == "high"),
            "medium": sum(1 for i in self.all_issues if i.severity == "medium"),
            "low": sum(1 for i in self.all_issues if i.severity == "low")
        }
        
        return {
            "organization": self.organization_name,
            "plan_created": datetime.now().strftime("%Y-%m-%d"),
            "total_issues": total_issues,
            "severity_breakdown": severity_counts,
            "total_phases": len(self.phases),
            "estimated_effort": {
                "total_hours": round(total_hours, 1),
                "total_days": round(total_days, 1),
                "duration_calendar_days": total_duration_days,
                "team_size": self.team_size,
                "hourly_rate_eur": self.hourly_rate_eur,
                "total_cost_eur": round(total_cost, 2)
            },
            "timeline": {
                "start_date": self.phases[0].start_date if self.phases else "",
                "end_date": self.phases[-1].end_date if self.phases else "",
                "critical_issues_resolved_by": self.phases[0].end_date if self.phases else ""
            },
            "success_criteria": {
                "wcag_level": "AA",
                "target_score": 85,
                "compliance_level": "conforme"
            }
        }
    
    def get_phase_details(self, phase_number: int) -> Optional[Dict[str, Any]]:
        """
        Ottiene dettagli di una fase specifica
        
        Args:
            phase_number: Numero della fase
            
        Returns:
            Dizionario con dettagli fase o None
        """
        for phase in self.phases:
            if phase.phase_number == phase_number:
                return phase.to_dict()
        return None
    
    def generate_comprehensive_plan(self) -> Dict[str, Any]:
        """
        Genera piano di remediation completo
        
        Returns:
            Dizionario con piano completo
        """
        return {
            "executive_summary": self.get_executive_summary(),
            "phases": [phase.to_dict() for phase in self.phases],
            "issues_by_phase": {
                f"phase_{i+1}": [issue.to_dict() for issue in phase.issues]
                for i, phase in enumerate(self.phases)
            },
            "timeline": {
                "gantt_data": self.get_gantt_chart_data(),
                "milestones": self._generate_milestones(),
                "critical_path": self._identify_critical_path()
            },
            "resources": {
                "team_required": self._calculate_team_requirements(),
                "skills_needed": self._identify_required_skills(),
                "tools_required": self._list_required_tools()
            },
            "risk_assessment": self._assess_risks(),
            "success_metrics": self._define_success_metrics(),
            "export_formats": {
                "jira": self.export_to_jira_csv('jira_export.csv') if hasattr(self, 'export_to_jira_csv') else None,
                "json": True,
                "html": True,
                "pdf": True
            }
        }
    
    def _generate_milestones(self) -> List[Dict[str, Any]]:
        """Genera milestone del progetto"""
        milestones = []
        for phase in self.phases:
            milestones.append({
                "name": f"Completamento {phase.name}",
                "date": phase.end_date,
                "deliverables": f"{len(phase.issues)} issues risolte",
                "success_criteria": f"Tutte le issues di severità {phase.name.lower()} risolte"
            })
        return milestones
    
    def _identify_critical_path(self) -> List[str]:
        """Identifica il percorso critico"""
        return [f"Fase {i+1}: {phase.name}" for i, phase in enumerate(self.phases) if phase.phase_number <= 2]
    
    def _calculate_team_requirements(self) -> Dict[str, int]:
        """Calcola requisiti del team"""
        total_hours = sum(issue.estimated_hours for issue in self.all_issues)
        return {
            "developers": max(1, int(total_hours / 160)),  # 160 ore/mese per developer
            "testers": max(1, int(total_hours / 320)),     # 1 tester ogni 2 developer
            "project_manager": 1 if total_hours > 160 else 0
        }
    
    def _identify_required_skills(self) -> List[str]:
        """Identifica competenze necessarie"""
        skills = set()
        for issue in self.all_issues:
            if "alt" in issue.code or "img" in issue.code:
                skills.add("HTML semantico")
            if "contrast" in issue.code:
                skills.add("CSS e design accessibile")
            if "aria" in issue.code:
                skills.add("WAI-ARIA")
            if "keyboard" in issue.code:
                skills.add("JavaScript accessibile")
        skills.add("WCAG 2.1 Level AA")
        skills.add("Screen reader testing")
        return list(skills)
    
    def _list_required_tools(self) -> List[str]:
        """Lista tools necessari"""
        return [
            "NVDA o JAWS (screen reader)",
            "Color Contrast Analyzer",
            "axe DevTools",
            "WAVE extension",
            "Keyboard navigation tester",
            "Browser DevTools",
            "Lighthouse"
        ]
    
    def _assess_risks(self) -> List[Dict[str, Any]]:
        """Valuta i rischi del progetto"""
        risks = []
        total_issues = len(self.all_issues)
        
        if total_issues > 100:
            risks.append({
                "type": "Volume elevato",
                "probability": "Alta",
                "impact": "Medio",
                "mitigation": "Suddividere in sprint più piccoli"
            })
        
        critical_count = sum(1 for i in self.all_issues if i.severity == "critical")
        if critical_count > 10:
            risks.append({
                "type": "Molte issues critiche",
                "probability": "Media",
                "impact": "Alto",
                "mitigation": "Prioritizzare issues bloccanti"
            })
        
        return risks
    
    def _define_success_metrics(self) -> Dict[str, Any]:
        """Definisce metriche di successo"""
        return {
            "compliance_score": {
                "current": self.scan_results.get("compliance", {}).get("overall_score", 0),
                "target": 85,
                "minimum_acceptable": 75
            },
            "wcag_level": {
                "current": "Non conforme",
                "target": "AA",
                "deadline": self.phases[-1].end_date if self.phases else None
            },
            "issues_resolved": {
                "critical": "100%",
                "high": "100%",
                "medium": "80%",
                "low": "60%"
            },
            "testing_coverage": {
                "automated": "100%",
                "manual": "Key user flows",
                "screen_reader": "All interactive elements"
            }
        }
    
    def get_gantt_chart_data(self) -> List[Dict[str, Any]]:
        """
        Genera dati per Gantt chart
        
        Returns:
            Lista di task per Gantt
        """
        gantt_data = []
        
        for phase in self.phases:
            gantt_data.append({
                "task": phase.name,
                "start": phase.start_date,
                "end": phase.end_date,
                "progress": phase.calculate_progress(),
                "dependencies": [],
                "custom_class": f"phase-{phase.phase_number}"
            })
            
            # Aggiungi milestone per fasi critiche
            if phase.phase_number == 1:
                gantt_data.append({
                    "task": "🎯 Barriere Critiche Risolte",
                    "start": phase.end_date,
                    "milestone": True
                })
            elif phase.phase_number == len(self.phases):
                gantt_data.append({
                    "task": "✅ Conformità WCAG AA Raggiunta",
                    "start": phase.end_date,
                    "milestone": True
                })
        
        return gantt_data
    
    def export_to_jira_csv(self, filepath: Path) -> None:
        """
        Esporta issues in formato CSV per JIRA
        
        Args:
            filepath: Path del file CSV
        """
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Issue Type', 'Summary', 'Description', 'Priority', 
                'Labels', 'Story Points', 'Fix Version', 'Component'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for issue in self.all_issues:
                priority_map = {
                    "critical": "Highest",
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low"
                }
                
                writer.writerow({
                    'Issue Type': 'Bug',
                    'Summary': f"[A11Y] {issue.description}",
                    'Description': f"""
h3. Problema
{issue.description}

h3. Criterio WCAG
{issue.wcag_criteria}

h3. Approccio Remediation
{issue.remediation_approach}

h3. Esempio Codice
{{code}}
{issue.code_example}
{{code}}

h3. Testing
{issue.testing_approach}
""",
                    'Priority': priority_map.get(issue.severity, "Medium"),
                    'Labels': f"accessibility,wcag,{issue.severity}",
                    'Story Points': int(issue.estimated_hours),
                    'Fix Version': f"Accessibility Phase {self._get_phase_for_issue(issue)}",
                    'Component': 'Frontend'
                })
        
        logger.info(f"Esportato piano remediation in {filepath}")
    
    def _get_phase_for_issue(self, issue: RemediationIssue) -> int:
        """
        Trova fase per un issue
        
        Args:
            issue: Issue da cercare
            
        Returns:
            Numero fase
        """
        for phase in self.phases:
            if issue in phase.issues:
                return phase.phase_number
        return 1
    
    def generate_html_report(self) -> str:
        """
        Genera report HTML del piano di remediation
        
        Returns:
            HTML del report
        """
        summary = self.get_executive_summary()
        
        html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano di Remediation Accessibilità - {self.organization_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #2E5266; }}
        h2 {{ color: #6E8898; margin-top: 30px; }}
        .summary-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2E5266; }}
        .metric-label {{ font-size: 12px; color: #666; }}
        .phase {{ border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .phase-header {{ background: #2E5266; color: white; padding: 10px; margin: -15px -15px 15px -15px; border-radius: 5px 5px 0 0; }}
        .critical {{ color: #D62828; font-weight: bold; }}
        .high {{ color: #F77F00; font-weight: bold; }}
        .medium {{ color: #FFC107; }}
        .low {{ color: #52B788; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #6E8898; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
        .timeline {{ background: linear-gradient(to right, #2E5266, #52B788); height: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>🎯 Piano di Remediation Accessibilità</h1>
    <p><strong>Organizzazione:</strong> {self.organization_name}</p>
    <p><strong>Data Creazione Piano:</strong> {summary['plan_created']}</p>
    
    <div class="summary-box">
        <h2>Sommario Esecutivo</h2>
        <div class="metric">
            <div class="metric-value">{summary['total_issues']}</div>
            <div class="metric-label">PROBLEMI TOTALI</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['estimated_effort']['total_hours']:.0f}</div>
            <div class="metric-label">ORE STIMATE</div>
        </div>
        <div class="metric">
            <div class="metric-value">€{summary['estimated_effort']['total_cost_eur']:,.0f}</div>
            <div class="metric-label">COSTO STIMATO</div>
        </div>
        <div class="metric">
            <div class="metric-value">{summary['estimated_effort']['duration_calendar_days']}</div>
            <div class="metric-label">GIORNI CALENDARIO</div>
        </div>
    </div>
    
    <h2>📊 Distribuzione Severità</h2>
    <ul>
        <li class="critical">Critici: {summary['severity_breakdown']['critical']}</li>
        <li class="high">Alti: {summary['severity_breakdown']['high']}</li>
        <li class="medium">Medi: {summary['severity_breakdown']['medium']}</li>
        <li class="low">Bassi: {summary['severity_breakdown']['low']}</li>
    </ul>
    
    <h2>📅 Fasi del Piano</h2>
    <div class="timeline"></div>
"""
        
        for phase in self.phases:
            stats = phase.get_statistics()
            html += f"""
    <div class="phase">
        <div class="phase-header">
            <h3>{phase.name}</h3>
        </div>
        <p><strong>Descrizione:</strong> {phase.description}</p>
        <p><strong>Periodo:</strong> {phase.start_date} - {phase.end_date} ({phase.duration_days} giorni)</p>
        <p><strong>Issues:</strong> {stats['total_issues']} totali 
           (Critici: {stats['critical_issues']}, Alti: {stats['high_issues']})</p>
        <p><strong>Effort:</strong> {stats['total_hours']:.0f} ore</p>
    </div>
"""
        
        html += """
    <h2>✅ Criteri di Successo</h2>
    <ul>
        <li>Raggiungimento conformità WCAG 2.1 Livello AA</li>
        <li>Score di accessibilità ≥ 85/100</li>
        <li>Zero barriere critiche all'accesso</li>
        <li>Test positivo con tecnologie assistive</li>
        <li>Dichiarazione di accessibilità pubblicata</li>
    </ul>
    
    <h2>👥 Team e Risorse</h2>
    <p>Team consigliato: {summary['estimated_effort']['team_size']} sviluppatori</p>
    <p>Competenze richieste: HTML/CSS accessibile, ARIA, JavaScript, Testing con screen reader</p>
    
</body>
</html>
"""
        return html
    
    def to_json(self) -> str:
        """
        Esporta piano completo in JSON
        
        Returns:
            JSON string
        """
        data = {
            "summary": self.get_executive_summary(),
            "phases": [phase.to_dict() for phase in self.phases],
            "issues": [issue.to_dict() for issue in self.all_issues],
            "gantt_data": self.get_gantt_chart_data()
        }
        return json.dumps(data, indent=2, ensure_ascii=False)