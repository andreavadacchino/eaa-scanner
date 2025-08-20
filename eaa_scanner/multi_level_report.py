"""
Sistema di Report Multi-livello per EAA Scanner
Report navigabile con Executive Summary, Template Report e Dettagli Pagina
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ReportLevel:
    """Definisce un livello del report"""
    level: str  # 'executive', 'template', 'page'
    title: str
    content: Dict[str, Any]
    navigation: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    charts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiLevelReport:
    """Struttura completa del report multi-livello"""
    scan_id: str
    scan_date: str
    company_name: str
    base_url: str
    
    # Livelli del report
    executive_summary: ReportLevel
    template_reports: List[ReportLevel]
    page_reports: List[ReportLevel]
    
    # Dati globali
    total_issues: int = 0
    compliance_score: float = 0.0
    wcag_compliance: str = "non_conforme"
    methodology: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Converte in dizionario serializzabile"""
        return {
            'scan_id': self.scan_id,
            'scan_date': self.scan_date,
            'company_name': self.company_name,
            'base_url': self.base_url,
            'executive_summary': asdict(self.executive_summary),
            'template_reports': [asdict(r) for r in self.template_reports],
            'page_reports': [asdict(r) for r in self.page_reports],
            'total_issues': self.total_issues,
            'compliance_score': self.compliance_score,
            'wcag_compliance': self.wcag_compliance,
            'methodology': self.methodology
        }


class MultiLevelReportGenerator:
    """
    Generatore di report multi-livello navigabile
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Inizializza il generatore
        
        Args:
            output_dir: Directory di output per i report
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 templates
        template_dir = Path(__file__).parent.parent / "webapp" / "templates" / "reports"
        if not template_dir.exists():
            template_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_templates(template_dir)
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def generate_report(self, scan_results: Dict, sampler_results: Dict, 
                       remediation_plan: Dict) -> MultiLevelReport:
        """
        Genera report multi-livello completo
        
        Args:
            scan_results: Risultati della scansione
            sampler_results: Risultati del sampling
            remediation_plan: Piano di remediation
            
        Returns:
            MultiLevelReport completo
        """
        # Estrai dati base
        scan_id = scan_results.get('scan_id', self._generate_scan_id())
        scan_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        company_name = scan_results.get('company_name', 'Azienda')
        base_url = scan_results.get('url', '')
        
        # Calcola metriche aggregate
        metrics = self._calculate_aggregate_metrics(scan_results)
        
        # Genera Executive Summary
        executive_summary = self._generate_executive_summary(
            scan_results, sampler_results, remediation_plan, metrics
        )
        
        # Genera Template Reports
        template_reports = self._generate_template_reports(
            scan_results, sampler_results
        )
        
        # Genera Page Reports
        page_reports = self._generate_page_reports(
            scan_results, sampler_results
        )
        
        # Crea report completo
        report = MultiLevelReport(
            scan_id=scan_id,
            scan_date=scan_date,
            company_name=company_name,
            base_url=base_url,
            executive_summary=executive_summary,
            template_reports=template_reports,
            page_reports=page_reports,
            total_issues=metrics['total_issues'],
            compliance_score=metrics['compliance_score'],
            wcag_compliance=metrics['wcag_compliance'],
            methodology=sampler_results.get('methodology', {})
        )
        
        return report
    
    def _generate_executive_summary(self, scan_results: Dict, sampler_results: Dict,
                                   remediation_plan: Dict, metrics: Dict) -> ReportLevel:
        """
        Genera Executive Summary
        
        Args:
            scan_results: Risultati scansione
            sampler_results: Risultati sampling
            remediation_plan: Piano remediation
            metrics: Metriche aggregate
            
        Returns:
            ReportLevel con executive summary
        """
        # Calcola KPI principali
        kpis = {
            'compliance_score': metrics['compliance_score'],
            'wcag_compliance': self._translate_compliance(metrics['wcag_compliance']),
            'critical_issues': metrics['issues_by_severity'].get('critical', 0),
            'high_issues': metrics['issues_by_severity'].get('high', 0),
            'pages_scanned': len(scan_results.get('pages', [])),
            'templates_found': len(sampler_results.get('templates', {}).get('identified', {})),
            'estimated_remediation_hours': remediation_plan.get('total_estimated_hours', 0),
            'priority_actions': len(remediation_plan.get('priority_actions', []))
        }
        
        # Genera insights chiave
        insights = self._generate_executive_insights(metrics, remediation_plan)
        
        # Crea contenuto executive summary
        content = {
            'overview': {
                'description': f"Report di conformità EAA per {scan_results.get('company_name', 'il sito')}",
                'scan_date': datetime.now().strftime('%d/%m/%Y'),
                'methodology': 'WCAG-EM + Smart Page Sampling',
                'scanners_used': self._get_scanners_used(scan_results)
            },
            'kpis': kpis,
            'insights': insights,
            'compliance_status': {
                'level': metrics['wcag_compliance'],
                'score': metrics['compliance_score'],
                'description': self._get_compliance_description(metrics['compliance_score']),
                'certification_ready': metrics['compliance_score'] >= 90
            },
            'top_issues': self._get_top_issues(scan_results, limit=5),
            'recommendations': self._generate_recommendations(metrics, remediation_plan),
            'next_steps': remediation_plan.get('immediate_actions', [])
        }
        
        # Genera grafici per executive summary
        charts = {
            'compliance_gauge': self._generate_compliance_gauge(metrics['compliance_score']),
            'issues_by_severity': self._generate_severity_chart(metrics['issues_by_severity']),
            'issues_by_wcag': self._generate_wcag_chart(metrics['issues_by_wcag']),
            'remediation_timeline': self._generate_timeline_chart(remediation_plan)
        }
        
        # Navigazione
        navigation = {
            'next': '#templates',
            'details': '#page-details',
            'download_pdf': f'/download/pdf?scan_id={scan_results.get("scan_id", "")}',
            'download_json': f'/api/results?scan_id={scan_results.get("scan_id", "")}'
        }
        
        return ReportLevel(
            level='executive',
            title='Executive Summary',
            content=content,
            navigation=navigation,
            metrics=kpis,
            charts=charts
        )
    
    def _generate_template_reports(self, scan_results: Dict, 
                                  sampler_results: Dict) -> List[ReportLevel]:
        """
        Genera report per ogni template identificato
        
        Args:
            scan_results: Risultati scansione
            sampler_results: Risultati sampling
            
        Returns:
            Lista di ReportLevel per template
        """
        template_reports = []
        templates = sampler_results.get('templates', {}).get('identified', {})
        
        for template_id, template_info in templates.items():
            # Aggrega issues per template
            template_issues = self._aggregate_template_issues(
                template_info['pages'],
                scan_results.get('issues', [])
            )
            
            # Calcola metriche template
            template_metrics = {
                'page_count': template_info['page_count'],
                'total_issues': len(template_issues),
                'avg_issues_per_page': len(template_issues) / template_info['page_count'] if template_info['page_count'] > 0 else 0,
                'critical_issues': sum(1 for i in template_issues if i.get('severity') == 'critical'),
                'compliance_score': self._calculate_template_compliance(template_issues)
            }
            
            # Pattern di issues comuni
            common_patterns = self._identify_common_patterns(template_issues)
            
            # Contenuto template report
            content = {
                'template_info': {
                    'id': template_id,
                    'name': template_info['name'],
                    'page_count': template_info['page_count'],
                    'representative_url': template_info['representative_url'],
                    'page_types': template_info.get('page_types', [])
                },
                'metrics': template_metrics,
                'common_issues': common_patterns,
                'affected_pages': [
                    {
                        'url': p['url'],
                        'title': p.get('title', ''),
                        'issues_count': self._count_page_issues(p['url'], scan_results.get('issues', []))
                    }
                    for p in template_info['pages']
                ],
                'recommendations': self._generate_template_recommendations(common_patterns),
                'fix_once_apply_all': self._identify_fix_once_patterns(common_patterns)
            }
            
            # Grafici template
            charts = {
                'issues_distribution': self._generate_template_issues_chart(template_issues),
                'wcag_violations': self._generate_template_wcag_chart(template_issues)
            }
            
            # Navigazione
            navigation = {
                'up': '#executive-summary',
                'next': f'#template-{templates.get(template_id, {}).get("next_id", "")}',
                'pages': [f'#page-{p["url"]}' for p in template_info['pages']]
            }
            
            template_reports.append(ReportLevel(
                level='template',
                title=f'Template: {template_info["name"]}',
                content=content,
                navigation=navigation,
                metrics=template_metrics,
                charts=charts
            ))
        
        return template_reports
    
    def _generate_page_reports(self, scan_results: Dict, 
                              sampler_results: Dict) -> List[ReportLevel]:
        """
        Genera report dettagliato per ogni pagina scansionata
        
        Args:
            scan_results: Risultati scansione
            sampler_results: Risultati sampling
            
        Returns:
            Lista di ReportLevel per pagina
        """
        page_reports = []
        selected_pages = sampler_results.get('selection', {}).get('selected_pages', [])
        
        for page_info in selected_pages:
            page_url = page_info['url']
            
            # Estrai issues della pagina
            page_issues = self._get_page_issues(page_url, scan_results.get('issues', []))
            
            # Raggruppa per scanner
            issues_by_scanner = self._group_issues_by_scanner(page_issues)
            
            # Calcola metriche pagina
            page_metrics = {
                'total_issues': len(page_issues),
                'critical': sum(1 for i in page_issues if i.get('severity') == 'critical'),
                'high': sum(1 for i in page_issues if i.get('severity') == 'high'),
                'medium': sum(1 for i in page_issues if i.get('severity') == 'medium'),
                'low': sum(1 for i in page_issues if i.get('severity') == 'low'),
                'wcag_a': sum(1 for i in page_issues if 'Level A' in i.get('wcag_ref', '')),
                'wcag_aa': sum(1 for i in page_issues if 'Level AA' in i.get('wcag_ref', '')),
                'wcag_aaa': sum(1 for i in page_issues if 'Level AAA' in i.get('wcag_ref', ''))
            }
            
            # Contenuto page report
            content = {
                'page_info': {
                    'url': page_url,
                    'title': page_info.get('title', ''),
                    'page_type': page_info.get('page_type', 'general'),
                    'template': page_info.get('template_id', ''),
                    'scan_depth': page_info.get('depth_level', 'standard')
                },
                'metrics': page_metrics,
                'issues_by_scanner': issues_by_scanner,
                'detailed_issues': self._format_detailed_issues(page_issues),
                'screenshot': page_info.get('screenshot_path', ''),
                'remediation_priority': self._calculate_page_priority(page_metrics),
                'technical_details': {
                    'dom_elements': page_info.get('forms_count', 0) + page_info.get('inputs_count', 0),
                    'interactive_elements': page_info.get('buttons_count', 0),
                    'media_elements': page_info.get('images_count', 0) + page_info.get('videos_count', 0),
                    'semantic_structure': {
                        'has_h1': page_info.get('has_h1', False),
                        'has_nav': page_info.get('has_nav', False),
                        'has_main': page_info.get('has_main', False),
                        'has_footer': page_info.get('has_footer', False)
                    }
                }
            }
            
            # Grafici pagina
            charts = {
                'severity_breakdown': self._generate_page_severity_chart(page_metrics),
                'wcag_levels': self._generate_page_wcag_chart(page_metrics),
                'scanner_comparison': self._generate_scanner_comparison_chart(issues_by_scanner)
            }
            
            # Navigazione
            navigation = {
                'up': f'#template-{page_info.get("template_id", "")}',
                'previous': self._get_previous_page_url(page_url, selected_pages),
                'next': self._get_next_page_url(page_url, selected_pages),
                'executive': '#executive-summary'
            }
            
            page_reports.append(ReportLevel(
                level='page',
                title=f'Pagina: {page_info.get("title", page_url)}',
                content=content,
                navigation=navigation,
                metrics=page_metrics,
                charts=charts
            ))
        
        return page_reports
    
    def export_html(self, report: MultiLevelReport, output_path: Optional[Path] = None) -> Path:
        """
        Esporta report in HTML navigabile
        
        Args:
            report: Report multi-livello
            output_path: Path di output (opzionale)
            
        Returns:
            Path del file HTML generato
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"multi_level_report_{timestamp}.html"
        
        # Carica template HTML
        try:
            template = self.jinja_env.get_template('multi_level_report.html')
        except:
            # Usa template di fallback se non esiste
            template_content = self._get_fallback_template()
            template = self.jinja_env.from_string(template_content)
        
        # Renderizza HTML
        html_content = template.render(report=report)
        
        # Salva file
        output_path.write_text(html_content, encoding='utf-8')
        
        logger.info(f"Report multi-livello salvato in: {output_path}")
        return output_path
    
    def export_json(self, report: MultiLevelReport, output_path: Optional[Path] = None) -> Path:
        """
        Esporta report in JSON
        
        Args:
            report: Report multi-livello
            output_path: Path di output (opzionale)
            
        Returns:
            Path del file JSON generato
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = self.output_dir / f"multi_level_report_{timestamp}.json"
        
        # Converti in JSON
        report_dict = report.to_dict()
        
        # Salva file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report JSON salvato in: {output_path}")
        return output_path
    
    # Metodi helper privati
    
    def _calculate_aggregate_metrics(self, scan_results: Dict) -> Dict:
        """Calcola metriche aggregate dai risultati"""
        issues = scan_results.get('issues', [])
        
        # Conta per severità
        issues_by_severity = defaultdict(int)
        for issue in issues:
            severity = issue.get('severity', 'low').lower()
            issues_by_severity[severity] += 1
        
        # Conta per WCAG
        issues_by_wcag = defaultdict(int)
        for issue in issues:
            wcag_ref = issue.get('wcag_ref', '')
            if wcag_ref:
                criterion = wcag_ref.split('-')[0] if '-' in wcag_ref else wcag_ref
                issues_by_wcag[criterion] += 1
        
        # Calcola score di compliance
        total_issues = len(issues)
        critical_weight = issues_by_severity.get('critical', 0) * 10
        high_weight = issues_by_severity.get('high', 0) * 5
        medium_weight = issues_by_severity.get('medium', 0) * 2
        low_weight = issues_by_severity.get('low', 0) * 1
        
        total_weight = critical_weight + high_weight + medium_weight + low_weight
        max_possible_weight = total_issues * 10 if total_issues > 0 else 1
        
        compliance_score = max(0, 100 - (total_weight / max_possible_weight * 100)) if max_possible_weight > 0 else 100
        
        # Determina livello WCAG
        if compliance_score >= 90 and issues_by_severity.get('critical', 0) == 0:
            wcag_compliance = 'conforme'
        elif compliance_score >= 70:
            wcag_compliance = 'parzialmente_conforme'
        else:
            wcag_compliance = 'non_conforme'
        
        return {
            'total_issues': total_issues,
            'issues_by_severity': dict(issues_by_severity),
            'issues_by_wcag': dict(issues_by_wcag),
            'compliance_score': round(compliance_score, 2),
            'wcag_compliance': wcag_compliance
        }
    
    def _generate_scan_id(self) -> str:
        """Genera ID univoco per scan"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        return f"scan_{timestamp}_{random_part}"
    
    def _translate_compliance(self, level: str) -> str:
        """Traduce livello compliance"""
        translations = {
            'conforme': 'Conforme',
            'parzialmente_conforme': 'Parzialmente Conforme',
            'non_conforme': 'Non Conforme'
        }
        return translations.get(level, level)
    
    def _get_compliance_description(self, score: float) -> str:
        """Genera descrizione basata su score"""
        if score >= 90:
            return "Il sito presenta un ottimo livello di accessibilità con solo piccoli problemi da risolvere"
        elif score >= 70:
            return "Il sito ha un buon livello base di accessibilità ma richiede interventi significativi"
        elif score >= 50:
            return "Il sito presenta diverse criticità di accessibilità che richiedono attenzione immediata"
        else:
            return "Il sito ha gravi problemi di accessibilità che impediscono l'utilizzo a molti utenti"
    
    def _get_scanners_used(self, scan_results: Dict) -> List[str]:
        """Estrae lista scanner utilizzati"""
        scanners = []
        if scan_results.get('wave_results'):
            scanners.append('WAVE')
        if scan_results.get('axe_results'):
            scanners.append('Axe-core')
        if scan_results.get('pa11y_results'):
            scanners.append('Pa11y')
        if scan_results.get('lighthouse_results'):
            scanners.append('Lighthouse')
        return scanners
    
    def _get_top_issues(self, scan_results: Dict, limit: int = 5) -> List[Dict]:
        """Ottiene top issues per gravità"""
        issues = scan_results.get('issues', [])
        
        # Ordina per severità e frequenza
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_issues = sorted(
            issues,
            key=lambda x: (severity_order.get(x.get('severity', 'low').lower(), 4), -x.get('count', 1))
        )
        
        # Raggruppa issues simili
        grouped = defaultdict(lambda: {'count': 0, 'pages': set()})
        for issue in sorted_issues[:limit * 3]:  # Prendi più issues per raggruppamento
            key = (issue.get('code', ''), issue.get('wcag_ref', ''))
            grouped[key]['count'] += 1
            grouped[key]['pages'].add(issue.get('page_url', ''))
            grouped[key]['severity'] = issue.get('severity', 'low')
            grouped[key]['description'] = issue.get('description', '')
            grouped[key]['wcag_ref'] = issue.get('wcag_ref', '')
        
        # Converti in lista
        top_issues = []
        for (code, wcag), data in list(grouped.items())[:limit]:
            top_issues.append({
                'code': code,
                'wcag_ref': wcag,
                'severity': data['severity'],
                'description': data['description'],
                'occurrences': data['count'],
                'affected_pages': len(data['pages'])
            })
        
        return top_issues
    
    def _generate_recommendations(self, metrics: Dict, remediation_plan: Dict) -> List[Dict]:
        """Genera raccomandazioni basate su metriche"""
        recommendations = []
        
        # Raccomandazioni basate su severità
        if metrics['issues_by_severity'].get('critical', 0) > 0:
            recommendations.append({
                'priority': 'alta',
                'title': 'Risolvere problemi critici',
                'description': f"Ci sono {metrics['issues_by_severity']['critical']} problemi critici che impediscono l'accesso al sito",
                'effort': 'immediato'
            })
        
        if metrics['compliance_score'] < 70:
            recommendations.append({
                'priority': 'alta',
                'title': 'Piano di remediation urgente',
                'description': 'Il livello di compliance richiede un intervento strutturato e prioritario',
                'effort': '1-3 mesi'
            })
        
        # Aggiungi raccomandazioni dal piano
        for action in remediation_plan.get('priority_actions', [])[:3]:
            recommendations.append({
                'priority': action.get('priority', 'media'),
                'title': action.get('title', ''),
                'description': action.get('description', ''),
                'effort': action.get('estimated_hours', 0)
            })
        
        return recommendations
    
    def _generate_executive_insights(self, metrics: Dict, remediation_plan: Dict) -> List[str]:
        """Genera insights chiave per executive"""
        insights = []
        
        if metrics['compliance_score'] >= 90:
            insights.append("✅ Il sito è molto vicino alla piena conformità EAA")
        elif metrics['compliance_score'] >= 70:
            insights.append("⚠️ Il sito richiede miglioramenti per raggiungere la conformità EAA")
        else:
            insights.append("❌ Sono necessari interventi urgenti per la conformità EAA")
        
        critical_count = metrics['issues_by_severity'].get('critical', 0)
        if critical_count > 0:
            insights.append(f"🚨 {critical_count} barriere critiche impediscono l'uso del sito")
        
        total_hours = remediation_plan.get('total_estimated_hours', 0)
        if total_hours > 0:
            insights.append(f"⏱️ Stima {total_hours} ore per completare la remediation")
        
        return insights
    
    def _aggregate_template_issues(self, pages: List[Dict], all_issues: List[Dict]) -> List[Dict]:
        """Aggrega issues per template"""
        page_urls = {p['url'] for p in pages}
        return [i for i in all_issues if i.get('page_url') in page_urls]
    
    def _calculate_template_compliance(self, issues: List[Dict]) -> float:
        """Calcola compliance score per template"""
        if not issues:
            return 100.0
        
        severity_weights = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1}
        total_weight = sum(severity_weights.get(i.get('severity', 'low').lower(), 1) for i in issues)
        max_weight = len(issues) * 10
        
        return max(0, 100 - (total_weight / max_weight * 100)) if max_weight > 0 else 100
    
    def _identify_common_patterns(self, issues: List[Dict]) -> List[Dict]:
        """Identifica pattern comuni nelle issues"""
        patterns = defaultdict(lambda: {'count': 0, 'pages': set()})
        
        for issue in issues:
            key = (issue.get('code', ''), issue.get('wcag_ref', ''))
            patterns[key]['count'] += 1
            patterns[key]['pages'].add(issue.get('page_url', ''))
            patterns[key]['severity'] = issue.get('severity', 'low')
            patterns[key]['description'] = issue.get('description', '')
        
        # Converti in lista ordinata
        common_patterns = []
        for (code, wcag), data in patterns.items():
            if data['count'] >= 2:  # Solo pattern che appaiono almeno 2 volte
                common_patterns.append({
                    'code': code,
                    'wcag_ref': wcag,
                    'severity': data['severity'],
                    'description': data['description'],
                    'occurrences': data['count'],
                    'affected_pages': len(data['pages'])
                })
        
        return sorted(common_patterns, key=lambda x: x['occurrences'], reverse=True)
    
    def _generate_template_recommendations(self, patterns: List[Dict]) -> List[str]:
        """Genera raccomandazioni per template"""
        recommendations = []
        
        for pattern in patterns[:3]:
            if pattern['occurrences'] >= 3:
                recommendations.append(
                    f"Risolvere '{pattern['code']}' che appare {pattern['occurrences']} volte nel template"
                )
        
        return recommendations
    
    def _identify_fix_once_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """Identifica pattern risolvibili una volta per tutte"""
        fix_once = []
        
        for pattern in patterns:
            if pattern['affected_pages'] >= 3:
                fix_once.append({
                    'issue': pattern['code'],
                    'benefit': f"Risolve {pattern['occurrences']} occorrenze su {pattern['affected_pages']} pagine",
                    'priority': 'alta' if pattern['severity'] in ['critical', 'high'] else 'media'
                })
        
        return fix_once
    
    def _count_page_issues(self, url: str, all_issues: List[Dict]) -> int:
        """Conta issues per una pagina"""
        return sum(1 for i in all_issues if i.get('page_url') == url)
    
    def _get_page_issues(self, url: str, all_issues: List[Dict]) -> List[Dict]:
        """Ottiene issues di una pagina specifica"""
        return [i for i in all_issues if i.get('page_url') == url]
    
    def _group_issues_by_scanner(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Raggruppa issues per scanner"""
        by_scanner = defaultdict(list)
        for issue in issues:
            scanner = issue.get('source', 'unknown')
            by_scanner[scanner].append(issue)
        return dict(by_scanner)
    
    def _format_detailed_issues(self, issues: List[Dict]) -> List[Dict]:
        """Formatta issues per visualizzazione dettagliata"""
        formatted = []
        
        for issue in issues:
            formatted.append({
                'id': issue.get('id', ''),
                'code': issue.get('code', ''),
                'severity': issue.get('severity', 'low'),
                'wcag_ref': issue.get('wcag_ref', ''),
                'description': issue.get('description', ''),
                'element': issue.get('element', ''),
                'selector': issue.get('selector', ''),
                'recommendation': issue.get('recommendation', ''),
                'source': issue.get('source', '')
            })
        
        return formatted
    
    def _calculate_page_priority(self, metrics: Dict) -> str:
        """Calcola priorità remediation per pagina"""
        if metrics['critical'] > 0:
            return 'critica'
        elif metrics['high'] >= 3:
            return 'alta'
        elif metrics['medium'] >= 5:
            return 'media'
        else:
            return 'bassa'
    
    def _get_previous_page_url(self, current_url: str, pages: List[Dict]) -> str:
        """Ottiene URL pagina precedente"""
        for i, page in enumerate(pages):
            if page['url'] == current_url and i > 0:
                return f"#page-{pages[i-1]['url']}"
        return '#templates'
    
    def _get_next_page_url(self, current_url: str, pages: List[Dict]) -> str:
        """Ottiene URL pagina successiva"""
        for i, page in enumerate(pages):
            if page['url'] == current_url and i < len(pages) - 1:
                return f"#page-{pages[i+1]['url']}"
        return '#executive-summary'
    
    # Metodi per generazione grafici (placeholder)
    
    def _generate_compliance_gauge(self, score: float) -> Dict:
        """Genera dati per gauge compliance"""
        return {
            'type': 'gauge',
            'value': score,
            'min': 0,
            'max': 100,
            'thresholds': [70, 90],
            'colors': ['#ef4444', '#f59e0b', '#10b981']
        }
    
    def _generate_severity_chart(self, issues_by_severity: Dict) -> Dict:
        """Genera dati per grafico severità"""
        return {
            'type': 'bar',
            'labels': ['Critiche', 'Alte', 'Medie', 'Basse'],
            'data': [
                issues_by_severity.get('critical', 0),
                issues_by_severity.get('high', 0),
                issues_by_severity.get('medium', 0),
                issues_by_severity.get('low', 0)
            ],
            'colors': ['#dc3545', '#fd7e14', '#ffc107', '#6c757d']
        }
    
    def _generate_wcag_chart(self, issues_by_wcag: Dict) -> Dict:
        """Genera dati per grafico WCAG"""
        sorted_wcag = sorted(issues_by_wcag.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            'type': 'horizontal-bar',
            'labels': [k for k, v in sorted_wcag],
            'data': [v for k, v in sorted_wcag]
        }
    
    def _generate_timeline_chart(self, remediation_plan: Dict) -> Dict:
        """Genera timeline remediation"""
        phases = remediation_plan.get('phases', [])
        return {
            'type': 'timeline',
            'phases': [
                {
                    'name': phase.get('name', ''),
                    'start': phase.get('start_date', ''),
                    'end': phase.get('end_date', ''),
                    'progress': phase.get('progress', 0)
                }
                for phase in phases
            ]
        }
    
    def _generate_template_issues_chart(self, issues: List[Dict]) -> Dict:
        """Genera grafico issues per template"""
        severity_counts = defaultdict(int)
        for issue in issues:
            severity_counts[issue.get('severity', 'low')] += 1
        
        return self._generate_severity_chart(dict(severity_counts))
    
    def _generate_template_wcag_chart(self, issues: List[Dict]) -> Dict:
        """Genera grafico WCAG per template"""
        wcag_counts = defaultdict(int)
        for issue in issues:
            wcag = issue.get('wcag_ref', '')
            if wcag:
                wcag_counts[wcag.split('-')[0]] += 1
        
        return self._generate_wcag_chart(dict(wcag_counts))
    
    def _generate_page_severity_chart(self, metrics: Dict) -> Dict:
        """Genera grafico severità per pagina"""
        return {
            'type': 'pie',
            'labels': ['Critiche', 'Alte', 'Medie', 'Basse'],
            'data': [
                metrics.get('critical', 0),
                metrics.get('high', 0),
                metrics.get('medium', 0),
                metrics.get('low', 0)
            ],
            'colors': ['#dc3545', '#fd7e14', '#ffc107', '#6c757d']
        }
    
    def _generate_page_wcag_chart(self, metrics: Dict) -> Dict:
        """Genera grafico livelli WCAG per pagina"""
        return {
            'type': 'doughnut',
            'labels': ['Level A', 'Level AA', 'Level AAA'],
            'data': [
                metrics.get('wcag_a', 0),
                metrics.get('wcag_aa', 0),
                metrics.get('wcag_aaa', 0)
            ],
            'colors': ['#3b82f6', '#8b5cf6', '#ec4899']
        }
    
    def _generate_scanner_comparison_chart(self, issues_by_scanner: Dict) -> Dict:
        """Genera grafico comparazione scanner"""
        return {
            'type': 'bar',
            'labels': list(issues_by_scanner.keys()),
            'data': [len(issues) for issues in issues_by_scanner.values()]
        }
    
    def _create_default_templates(self, template_dir: Path):
        """Crea template di default se non esistono"""
        # Questo metodo creerebbe i template Jinja2 di default
        # Per ora usa il fallback template
        pass
    
    def _get_fallback_template(self) -> str:
        """Template HTML di fallback"""
        return '''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Multi-livello EAA - {{ report.company_name }}</title>
    <style>
        /* Stili base per il report */
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .section { margin-bottom: 40px; padding: 20px; background: #f9fafb; border-radius: 8px; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background: white; border-radius: 6px; }
        .severity-critical { color: #dc2626; }
        .severity-high { color: #ea580c; }
        .severity-medium { color: #d97706; }
        .severity-low { color: #4b5563; }
        nav { position: sticky; top: 0; background: white; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        nav a { margin: 0 10px; text-decoration: none; color: #3b82f6; }
    </style>
</head>
<body>
    <nav>
        <a href="#executive">Executive Summary</a>
        <a href="#templates">Template Reports</a>
        <a href="#pages">Page Details</a>
    </nav>
    
    <div class="container">
        <section id="executive" class="section">
            <h1>Executive Summary</h1>
            <p>Report generato il {{ report.scan_date }} per {{ report.company_name }}</p>
            <div class="metric">
                <h3>Compliance Score</h3>
                <p style="font-size: 2em;">{{ report.compliance_score }}%</p>
            </div>
            <div class="metric">
                <h3>Issues Totali</h3>
                <p style="font-size: 2em;">{{ report.total_issues }}</p>
            </div>
        </section>
        
        <section id="templates" class="section">
            <h2>Template Reports</h2>
            {% for template in report.template_reports %}
            <div class="template-report">
                <h3>{{ template.title }}</h3>
                <p>Pagine: {{ template.content.template_info.page_count }}</p>
            </div>
            {% endfor %}
        </section>
        
        <section id="pages" class="section">
            <h2>Page Details</h2>
            {% for page in report.page_reports %}
            <div class="page-report">
                <h3>{{ page.title }}</h3>
                <p>Issues: {{ page.content.metrics.total_issues }}</p>
            </div>
            {% endfor %}
        </section>
    </div>
</body>
</html>
        '''