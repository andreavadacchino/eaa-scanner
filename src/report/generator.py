"""
Generatore report accessibilità con P.O.U.R. e impatto disabilità
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schema import (
    ScanResult, Issue, POURPrinciple, DisabilityType, Severity,
    Methodology, Sampling, SamplingPage, ContinuousProcess,
    DeclarationAndFeedback
)
from .transformers.mapping import WCAGMapper
from .validators import ComplianceValidator, NoDateValidator, MethodologyValidator
from .ai_content_generator import generate_ai_content


class EnhancedReportGenerator:
    """Generatore report professionale con P.O.U.R. e validazione automatica"""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Inizializza il generatore
        
        Args:
            template_dir: Directory con i template Jinja2
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
    
    def transform_scanner_results(self, scanner_data: Dict[str, Any]) -> List[Issue]:
        """
        Trasforma i risultati degli scanner in Issue con P.O.U.R. e impatto
        
        Args:
            scanner_data: Dati grezzi dagli scanner
            
        Returns:
            Lista di Issue trasformate
        """
        issues = []
        issue_id = 1
        
        # Prova prima all_violations, poi violations (formato legacy)
        violations_list = scanner_data.get('all_violations', [])
        if not violations_list:
            violations_list = scanner_data.get('violations', [])
        
        # Se ancora vuoto, prova a costruire da issues
        if not violations_list and 'issues' in scanner_data:
            violations_list = scanner_data['issues']
        
        # Se ancora vuoto, processa per scanner
        if not violations_list:
            # Processa dati per ogni scanner
            for scanner_name, scanner_results in scanner_data.items():
                if isinstance(scanner_results, dict) and 'violations' in scanner_results:
                    for violation in scanner_results['violations']:
                        violation['scanner'] = scanner_name
                        violations_list.append(violation)
        
        # Processa violazioni da ogni scanner
        for violation in violations_list:
            # Mappa a WCAG/POUR/Impatto
            mapping = WCAGMapper.map_scanner_rule(
                violation.get('code', violation.get('rule', '')),
                violation.get('scanner', '')
            )
            
            # Determina severità
            severity = WCAGMapper.determine_severity(
                violation.get('code', violation.get('rule', '')),
                violation.get('scanner', '')
            )
            
            # Crea Issue
            issue = Issue(
                id=f"ISSUE-{issue_id:04d}",
                description=violation.get('message', mapping['description']),
                element=violation.get('element', violation.get('selector', '')),
                wcag_criteria=mapping['wcag'],
                pour=mapping['pour'],
                severity=severity,
                disability_impact=mapping['impact'],
                remediation=self._generate_remediation(violation, mapping),
                selector=violation.get('selector', ''),
                url=violation.get('url', scanner_data.get('url', '')),
                scanner_source=violation.get('scanner', ''),
                count=violation.get('count', 1)
            )
            
            issues.append(issue)
            issue_id += 1
        
        return issues
    
    def _generate_remediation(self, violation: Dict, mapping: Dict) -> str:
        """
        Genera suggerimento di remediation basato sul problema
        
        Args:
            violation: Dati violazione
            mapping: Mapping WCAG/POUR
            
        Returns:
            Testo remediation
        """
        remediation_map = {
            'img-alt': "Aggiungere attributo alt descrittivo a tutte le immagini",
            'color-contrast': "Aumentare il contrasto colore a minimo 4.5:1 per testo normale, 3:1 per testo grande",
            'label': "Associare etichetta descrittiva al campo form tramite attributo 'for' o aria-label",
            'heading-order': "Correggere struttura heading seguendo ordine gerarchico (h1 → h2 → h3)",
            'link-name': "Fornire testo descrittivo per il link che indichi chiaramente la destinazione",
            'keyboard': "Garantire che l'elemento sia raggiungibile e utilizzabile da tastiera",
            'aria-valid-attr': "Correggere attributi ARIA non validi secondo specifica WAI-ARIA",
            'html-lang': "Specificare lingua della pagina con attributo lang nell'elemento html",
            'focus-visible': "Garantire indicatore di focus visibile per navigazione da tastiera",
            'form-field-multiple-labels': "Utilizzare una sola etichetta per campo form"
        }
        
        rule_id = violation.get('code', '').lower()
        
        # Cerca remediation specifica
        for key, remediation in remediation_map.items():
            if key in rule_id:
                return remediation
        
        # Remediation generica basata su POUR
        if mapping['pour'] == POURPrinciple.PERCEPIBILE:
            return "Garantire che l'informazione sia percepibile attraverso diversi canali sensoriali"
        elif mapping['pour'] == POURPrinciple.OPERABILE:
            return "Garantire che l'elemento sia utilizzabile da tutti gli utenti"
        elif mapping['pour'] == POURPrinciple.COMPRENSIBILE:
            return "Rendere l'interfaccia e l'informazione comprensibile agli utenti"
        else:  # ROBUSTO
            return "Garantire compatibilità con tecnologie assistive e browser"
    
    def generate_scan_result(
        self,
        scanner_data: Dict[str, Any],
        company_name: str,
        url: str,
        scan_id: Optional[str] = None
    ) -> ScanResult:
        """
        Genera ScanResult completo dai dati scanner
        
        Args:
            scanner_data: Dati grezzi scanner
            company_name: Nome azienda
            url: URL scansionato
            scan_id: ID scansione
            
        Returns:
            ScanResult popolato
        """
        # Trasforma issues
        issues = self.transform_scanner_results(scanner_data)
        
        # Crea sampling con pagine scansionate
        sampling = Sampling(
            pages=[
                SamplingPage(
                    url=url,
                    template="Home page",
                    included=True
                )
            ]
        )
        
        # Crea risultato
        result = ScanResult(
            url=url,
            company_name=company_name,
            methodology=Methodology(),
            sampling=sampling,
            continuous_process=ContinuousProcess(),
            declaration_and_feedback=DeclarationAndFeedback(),
            issues=issues,
            scan_id=scan_id or f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return result
    
    def generate_html_report(
        self,
        scan_result: ScanResult,
        template_name: str = 'professional_report.html',
        use_ai: bool = True
    ) -> str:
        """
        Genera report HTML dal ScanResult con contenuti AI opzionali
        
        Args:
            scan_result: Risultati scansione strutturati
            template_name: Nome template da usare
            use_ai: Se True, genera contenuti testuali con IA
            
        Returns:
            HTML del report
        """
        template = self.env.get_template(template_name)
        
        # Prepara context per template
        context = {
            'report': scan_result,
            'company_name': scan_result.company_name,
            'url': scan_result.url,
            'scan_id': scan_result.scan_id,
            'compliance_score': scan_result.compliance_score,
            'total_issues': scan_result.total_issues,
            'critical_issues': scan_result.critical_issues,
            'high_issues': scan_result.high_issues,
            'medium_issues': scan_result.medium_issues,
            'low_issues': scan_result.low_issues,
            'issues': scan_result.issues,
            
            # Issues per POUR
            'perceivable_issues': scan_result.get_issues_by_pour(POURPrinciple.PERCEPIBILE),
            'operable_issues': scan_result.get_issues_by_pour(POURPrinciple.OPERABILE),
            'understandable_issues': scan_result.get_issues_by_pour(POURPrinciple.COMPRENSIBILE),
            'robust_issues': scan_result.get_issues_by_pour(POURPrinciple.ROBUSTO),
            
            # Impatti disabilità
            'disability_impacts': scan_result.get_unique_disability_impacts(),
            
            # Metadata
            'generated_at': datetime.now().isoformat(),
            'methodology': scan_result.methodology,
            'sampling': scan_result.sampling,
            'continuous_process': scan_result.continuous_process,
            'declaration': scan_result.declaration_and_feedback
        }
        
        # Genera contenuti AI se richiesto
        if use_ai:
            try:
                print("   🤖 Generazione contenuti testuali con IA...")
                ai_content = generate_ai_content(scan_result)
                context['ai_content'] = ai_content
                context['has_ai_content'] = True
            except Exception as e:
                print(f"   ⚠️ Fallback a contenuti statici: {e}")
                context['has_ai_content'] = False
        else:
            context['has_ai_content'] = False
        
        html = template.render(**context)
        
        # Valida output
        is_valid, violations = NoDateValidator.validate_content(html)
        if not is_valid:
            print(f"⚠️ WARNING: Report contiene {len(violations)} riferimenti temporali")
        
        return html
    
    def save_report(
        self,
        scan_result: ScanResult,
        output_dir: Path,
        validate: bool = True
    ) -> Dict[str, Path]:
        """
        Salva report e dati strutturati
        
        Args:
            scan_result: Risultati scansione
            output_dir: Directory output
            validate: Se eseguire validazione automatica
            
        Returns:
            Dict con path dei file generati
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        paths = {}
        
        # Genera e salva HTML
        html = self.generate_html_report(scan_result)
        html_path = output_dir / f"report_{scan_result.company_name.replace(' ', '_')}.html"
        html_path.write_text(html, encoding='utf-8')
        paths['html'] = html_path
        
        # Salva JSON strutturato
        json_data = {
            'scan_id': scan_result.scan_id,
            'url': scan_result.url,
            'company_name': scan_result.company_name,
            'compliance_score': scan_result.compliance_score,
            'total_issues': scan_result.total_issues,
            'issues_by_severity': {
                'critical': scan_result.critical_issues,
                'high': scan_result.high_issues,
                'medium': scan_result.medium_issues,
                'low': scan_result.low_issues
            },
            'issues_by_pour': {
                'perceivable': len(scan_result.get_issues_by_pour(POURPrinciple.PERCEPIBILE)),
                'operable': len(scan_result.get_issues_by_pour(POURPrinciple.OPERABILE)),
                'understandable': len(scan_result.get_issues_by_pour(POURPrinciple.COMPRENSIBILE)),
                'robust': len(scan_result.get_issues_by_pour(POURPrinciple.ROBUSTO))
            },
            'disability_impacts': [d.value for d in scan_result.get_unique_disability_impacts()],
            'issues': [
                {
                    'id': issue.id,
                    'description': issue.description,
                    'wcag': issue.wcag_criteria,
                    'pour': issue.pour.value,
                    'severity': issue.severity.value,
                    'disability_impact': [d.value for d in issue.disability_impact],
                    'remediation': issue.remediation
                }
                for issue in scan_result.issues
            ]
        }
        
        json_path = output_dir / f"report_{scan_result.scan_id}.json"
        json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
        paths['json'] = json_path
        
        # Esegui validazione se richiesta
        if validate:
            validation_results = ComplianceValidator.validate_report(html_path)
            validation_paths = ComplianceValidator.save_validation_reports(
                validation_results,
                output_dir / 'validation'
            )
            paths.update(validation_paths)
            
            if not validation_results['valid']:
                print("⚠️ ATTENZIONE: Il report non passa la validazione compliance")
                print(f"   Vedi dettagli in: {paths.get('summary_report')}")
        
        return paths


class ReportFactory:
    """Factory per generazione report con diversi livelli di dettaglio"""
    
    @staticmethod
    def create_basic_report(scanner_data: Dict, company_info: Dict) -> str:
        """Genera report base AgID-compliant (12KB)"""
        generator = EnhancedReportGenerator()
        scan_result = generator.generate_scan_result(
            scanner_data,
            company_info['company_name'],
            company_info['url']
        )
        return generator.generate_html_report(scan_result, 'basic_report.html')
    
    @staticmethod
    def create_professional_report(scanner_data: Dict, company_info: Dict) -> str:
        """Genera report professionale (23KB)"""
        generator = EnhancedReportGenerator()
        scan_result = generator.generate_scan_result(
            scanner_data,
            company_info['company_name'],
            company_info['url']
        )
        return generator.generate_html_report(scan_result, 'professional_report.html')
    
    @staticmethod
    def create_enterprise_report(scanner_data: Dict, company_info: Dict) -> str:
        """Genera report enterprise avanzato (53KB)"""
        generator = EnhancedReportGenerator()
        scan_result = generator.generate_scan_result(
            scanner_data,
            company_info['company_name'],
            company_info['url']
        )
        return generator.generate_html_report(scan_result, 'enterprise_report.html')