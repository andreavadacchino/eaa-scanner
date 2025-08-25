"""Quality Control Agent - Validazione e controllo qualità cross-section"""

import logging
import re
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus, AgentPriority

logger = logging.getLogger(__name__)


class QualityControlAgent(BaseAgent):
    """Agent specializzato nel controllo qualità e validazione cross-section"""
    
    def __init__(self):
        super().__init__(
            name="quality_controller",
            priority=AgentPriority.CRITICAL,
            timeout=15
        )
        self.validation_rules = self._initialize_validation_rules()
        
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Inizializza regole di validazione"""
        return {
            'numerical_consistency': {
                'enabled': True,
                'tolerance': 0.01  # 1% tolleranza
            },
            'wcag_references': {
                'enabled': True,
                'format': r'^\d+\.\d+\.\d+$'  # Es: 1.1.1
            },
            'language_consistency': {
                'enabled': True,
                'language': 'it'
            },
            'html_validation': {
                'enabled': True,
                'check_structure': True,
                'check_accessibility': True
            },
            'content_quality': {
                'min_length': 100,
                'max_length': 50000,
                'required_elements': ['h2', 'p', 'table', 'ul', 'ol']
            }
        }
    
    async def validate_and_cross_reference(self,
                                          agent_results: List[AgentResult],
                                          context: AgentContext) -> List[AgentResult]:
        """Valida e cross-referenzia risultati degli agent
        
        Args:
            agent_results: Risultati da validare
            context: Contesto condiviso
            
        Returns:
            Risultati validati e corretti
        """
        
        self.logger.info(f"Validating {len(agent_results)} agent results")
        
        # 1. Estrai metriche da tutti i risultati
        all_metrics = self._extract_all_metrics(agent_results)
        
        # 2. Valida consistenza numerica
        numerical_issues = self._validate_numerical_consistency(all_metrics)
        
        # 3. Valida riferimenti WCAG
        wcag_issues = self._validate_wcag_references(agent_results)
        
        # 4. Valida qualità contenuto
        content_issues = self._validate_content_quality(agent_results)
        
        # 5. Valida struttura HTML
        html_issues = self._validate_html_structure(agent_results)
        
        # 6. Cross-referenzia informazioni
        cross_ref_issues = self._cross_reference_information(agent_results, context)
        
        # 7. Applica correzioni
        corrected_results = self._apply_corrections(
            agent_results,
            numerical_issues,
            wcag_issues,
            content_issues,
            html_issues,
            cross_ref_issues
        )
        
        # 8. Genera report di validazione
        validation_report = self._generate_validation_report(
            numerical_issues,
            wcag_issues,
            content_issues,
            html_issues,
            cross_ref_issues
        )
        
        # Log risultati validazione
        self._log_validation_results(validation_report)
        
        return corrected_results
    
    async def assess_overall_quality(self,
                                    html_report: str,
                                    context: AgentContext) -> float:
        """Valuta qualità complessiva del report
        
        Args:
            html_report: Report HTML completo
            context: Contesto
            
        Returns:
            Score qualità 0-1
        """
        
        scores = []
        
        # 1. Completezza (tutte le sezioni presenti)
        completeness_score = self._assess_completeness(html_report)
        scores.append(('completeness', completeness_score, 0.25))
        
        # 2. Accuratezza dati
        accuracy_score = self._assess_data_accuracy(html_report, context)
        scores.append(('accuracy', accuracy_score, 0.25))
        
        # 3. Leggibilità e chiarezza
        readability_score = self._assess_readability(html_report)
        scores.append(('readability', readability_score, 0.20))
        
        # 4. Conformità standard
        compliance_score = self._assess_standards_compliance(html_report)
        scores.append(('compliance', compliance_score, 0.15))
        
        # 5. Professionalità
        professionalism_score = self._assess_professionalism(html_report)
        scores.append(('professionalism', professionalism_score, 0.15))
        
        # Calcola score pesato
        total_score = sum(score * weight for _, score, weight in scores)
        
        # Log dettagli
        self.logger.info(f"Quality Assessment:")
        for name, score, weight in scores:
            self.logger.info(f"  {name}: {score:.2f} (weight: {weight})")
        self.logger.info(f"  Overall: {total_score:.2f}")
        
        return total_score
    
    def _extract_all_metrics(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Estrae tutte le metriche dai risultati"""
        
        metrics = defaultdict(list)
        
        for result in results:
            content = result.section_content
            
            # Estrai numeri dal contenuto
            numbers = re.findall(r'\b(\d+(?:\.\d+)?)(?:%|\s*ore|\s*giorni)?\b', content)
            for num in numbers:
                try:
                    metrics['numbers'].append(float(num))
                except ValueError:
                    pass
            
            # Estrai riferimenti WCAG
            wcag_refs = re.findall(r'\b(\d+\.\d+\.\d+)\b', content)
            metrics['wcag_references'].extend(wcag_refs)
            
            # Estrai conteggi menzionati
            error_mentions = re.findall(r'(\d+)\s*(?:errori|errors|problemi)', content, re.IGNORECASE)
            metrics['error_counts'].extend([int(x) for x in error_mentions])
            
            warning_mentions = re.findall(r'(\d+)\s*(?:avvisi|warnings)', content, re.IGNORECASE)
            metrics['warning_counts'].extend([int(x) for x in warning_mentions])
        
        return dict(metrics)
    
    def _validate_numerical_consistency(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Valida consistenza numerica tra sezioni"""
        
        issues = []
        
        # Verifica che i conteggi errori siano consistenti
        if 'error_counts' in metrics:
            error_counts = metrics['error_counts']
            if error_counts:
                # Verifica che non ci siano discrepanze significative
                min_count = min(error_counts)
                max_count = max(error_counts)
                if max_count > 0 and (max_count - min_count) / max_count > 0.1:  # >10% differenza
                    issues.append({
                        'type': 'numerical_inconsistency',
                        'severity': 'warning',
                        'message': f'Conteggi errori inconsistenti: min={min_count}, max={max_count}',
                        'values': error_counts
                    })
        
        # Verifica warning counts
        if 'warning_counts' in metrics:
            warning_counts = metrics['warning_counts']
            if warning_counts:
                min_count = min(warning_counts)
                max_count = max(warning_counts)
                if max_count > 0 and (max_count - min_count) / max_count > 0.1:
                    issues.append({
                        'type': 'numerical_inconsistency',
                        'severity': 'warning',
                        'message': f'Conteggi avvisi inconsistenti: min={min_count}, max={max_count}',
                        'values': warning_counts
                    })
        
        return issues
    
    def _validate_wcag_references(self, results: List[AgentResult]) -> List[Dict[str, Any]]:
        """Valida riferimenti WCAG"""
        
        issues = []
        wcag_pattern = re.compile(self.validation_rules['wcag_references']['format'])
        
        for result in results:
            # Estrai tutti i riferimenti WCAG
            wcag_refs = re.findall(r'\b(\d+\.\d+\.\d+)\b', result.section_content)
            
            for ref in wcag_refs:
                if not wcag_pattern.match(ref):
                    issues.append({
                        'type': 'invalid_wcag_reference',
                        'severity': 'error',
                        'agent': result.agent_name,
                        'reference': ref,
                        'message': f'Riferimento WCAG non valido: {ref}'
                    })
                
                # Verifica che sia un criterio WCAG valido
                if not self._is_valid_wcag_criterion(ref):
                    issues.append({
                        'type': 'unknown_wcag_criterion',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'reference': ref,
                        'message': f'Criterio WCAG non riconosciuto: {ref}'
                    })
        
        return issues
    
    def _validate_content_quality(self, results: List[AgentResult]) -> List[Dict[str, Any]]:
        """Valida qualità del contenuto"""
        
        issues = []
        min_length = self.validation_rules['content_quality']['min_length']
        max_length = self.validation_rules['content_quality']['max_length']
        
        for result in results:
            content_length = len(result.section_content)
            
            # Verifica lunghezza
            if content_length < min_length:
                issues.append({
                    'type': 'content_too_short',
                    'severity': 'error',
                    'agent': result.agent_name,
                    'length': content_length,
                    'message': f'Contenuto troppo breve: {content_length} caratteri'
                })
            elif content_length > max_length:
                issues.append({
                    'type': 'content_too_long',
                    'severity': 'warning',
                    'agent': result.agent_name,
                    'length': content_length,
                    'message': f'Contenuto troppo lungo: {content_length} caratteri'
                })
            
            # Verifica presenza elementi richiesti
            for element in self.validation_rules['content_quality']['required_elements']:
                if f'<{element}' not in result.section_content:
                    issues.append({
                        'type': 'missing_required_element',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'element': element,
                        'message': f'Elemento richiesto mancante: {element}'
                    })
            
            # Verifica qualità testo
            if result.quality_score < 0.5:
                issues.append({
                    'type': 'low_quality_score',
                    'severity': 'error',
                    'agent': result.agent_name,
                    'score': result.quality_score,
                    'message': f'Score qualità basso: {result.quality_score:.2f}'
                })
        
        return issues
    
    def _validate_html_structure(self, results: List[AgentResult]) -> List[Dict[str, Any]]:
        """Valida struttura HTML"""
        
        issues = []
        
        for result in results:
            content = result.section_content
            
            # Verifica bilanciamento tag
            open_tags = re.findall(r'<(\w+)[^>]*>', content)
            close_tags = re.findall(r'</(\w+)>', content)
            
            # Conta occorrenze
            open_count = defaultdict(int)
            close_count = defaultdict(int)
            
            for tag in open_tags:
                if tag not in ['br', 'hr', 'img', 'input', 'meta', 'link']:
                    open_count[tag] += 1
            
            for tag in close_tags:
                close_count[tag] += 1
            
            # Verifica bilanciamento
            for tag in open_count:
                if open_count[tag] != close_count.get(tag, 0):
                    issues.append({
                        'type': 'unbalanced_html_tags',
                        'severity': 'error',
                        'agent': result.agent_name,
                        'tag': tag,
                        'open': open_count[tag],
                        'close': close_count.get(tag, 0),
                        'message': f'Tag HTML non bilanciati: <{tag}>'
                    })
            
            # Verifica attributi accessibilità per tabelle
            if '<table>' in content:
                if '<caption>' not in content:
                    issues.append({
                        'type': 'missing_table_caption',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'message': 'Tabella senza caption'
                    })
                
                if 'scope=' not in content:
                    issues.append({
                        'type': 'missing_scope_attribute',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'message': 'Tabella senza attributi scope'
                    })
        
        return issues
    
    def _cross_reference_information(self,
                                    results: List[AgentResult],
                                    context: AgentContext) -> List[Dict[str, Any]]:
        """Cross-referenzia informazioni tra sezioni"""
        
        issues = []
        
        # Estrai riferimenti azienda
        company_name = context.company_info.get('company_name', '')
        if company_name:
            for result in results:
                # Verifica che il nome azienda sia menzionato correttamente
                if company_name not in result.section_content and result.agent_name != 'quality_controller':
                    issues.append({
                        'type': 'missing_company_reference',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'message': f'Nome azienda "{company_name}" non menzionato'
                    })
        
        # Verifica riferimenti URL
        url = context.company_info.get('url', '')
        if url:
            url_mentioned = any(url in r.section_content for r in results)
            if not url_mentioned:
                issues.append({
                    'type': 'missing_url_reference',
                    'severity': 'info',
                    'message': f'URL {url} non menzionato in nessuna sezione'
                })
        
        # Verifica coerenza score conformità
        overall_score = context.shared_metrics.get('overall_score', 0)
        for result in results:
            scores_in_content = re.findall(r'(\d+(?:\.\d+)?)/100', result.section_content)
            for score_str in scores_in_content:
                score = float(score_str)
                if abs(score - overall_score) > 5:  # Tolleranza 5 punti
                    issues.append({
                        'type': 'inconsistent_score',
                        'severity': 'warning',
                        'agent': result.agent_name,
                        'found_score': score,
                        'expected_score': overall_score,
                        'message': f'Score inconsistente: {score} vs {overall_score}'
                    })
        
        return issues
    
    def _apply_corrections(self,
                          results: List[AgentResult],
                          *issue_lists) -> List[AgentResult]:
        """Applica correzioni ai risultati basandosi sui problemi trovati"""
        
        corrected_results = []
        
        # Raccogli tutti i problemi
        all_issues = []
        for issue_list in issue_lists:
            all_issues.extend(issue_list)
        
        # Crea mappa di correzioni per agent
        corrections_by_agent = defaultdict(list)
        for issue in all_issues:
            if 'agent' in issue:
                corrections_by_agent[issue['agent']].append(issue)
        
        # Applica correzioni
        for result in results:
            if result.agent_name in corrections_by_agent:
                # Aggiungi warnings al risultato
                for issue in corrections_by_agent[result.agent_name]:
                    if issue['severity'] == 'error':
                        result.errors.append(issue['message'])
                    else:
                        result.warnings.append(issue['message'])
                
                # Riduci quality score se ci sono errori
                error_count = len([i for i in corrections_by_agent[result.agent_name] 
                                  if i['severity'] == 'error'])
                if error_count > 0:
                    result.quality_score *= max(0.5, 1 - (error_count * 0.1))
            
            corrected_results.append(result)
        
        return corrected_results
    
    def _is_valid_wcag_criterion(self, criterion: str) -> bool:
        """Verifica se è un criterio WCAG valido"""
        
        # Lista semplificata dei criteri WCAG 2.1 più comuni
        valid_criteria = [
            '1.1.1', '1.2.1', '1.2.2', '1.2.3', '1.2.4', '1.2.5',
            '1.3.1', '1.3.2', '1.3.3', '1.3.4', '1.3.5',
            '1.4.1', '1.4.2', '1.4.3', '1.4.4', '1.4.5', '1.4.10', '1.4.11', '1.4.12', '1.4.13',
            '2.1.1', '2.1.2', '2.1.4',
            '2.2.1', '2.2.2',
            '2.3.1',
            '2.4.1', '2.4.2', '2.4.3', '2.4.4', '2.4.5', '2.4.6', '2.4.7',
            '2.5.1', '2.5.2', '2.5.3', '2.5.4',
            '3.1.1', '3.1.2',
            '3.2.1', '3.2.2', '3.2.3', '3.2.4',
            '3.3.1', '3.3.2', '3.3.3', '3.3.4',
            '4.1.1', '4.1.2', '4.1.3'
        ]
        
        return criterion in valid_criteria
    
    def _assess_completeness(self, html_report: str) -> float:
        """Valuta completezza del report"""
        
        required_sections = [
            'Executive Summary',
            'Analisi Tecnica',
            'Conformità',
            'Raccomandazioni',
            'Piano di Remediation'
        ]
        
        found_sections = 0
        for section in required_sections:
            if section.lower() in html_report.lower():
                found_sections += 1
        
        return found_sections / len(required_sections)
    
    def _assess_data_accuracy(self, html_report: str, context: AgentContext) -> float:
        """Valuta accuratezza dei dati"""
        
        score = 1.0
        
        # Verifica presenza dati chiave
        if context.company_info.get('company_name') not in html_report:
            score -= 0.2
        
        if context.company_info.get('url') not in html_report:
            score -= 0.1
        
        # Verifica che i numeri siano consistenti
        overall_score = context.shared_metrics.get('overall_score', 0)
        if f"{overall_score:.1f}" not in html_report and f"{overall_score:.0f}" not in html_report:
            score -= 0.2
        
        return max(0, score)
    
    def _assess_readability(self, html_report: str) -> float:
        """Valuta leggibilità del report"""
        
        score = 1.0
        
        # Verifica lunghezza paragrafi
        paragraphs = re.findall(r'<p>(.*?)</p>', html_report, re.DOTALL)
        long_paragraphs = [p for p in paragraphs if len(p) > 500]
        if len(long_paragraphs) > 5:
            score -= 0.2
        
        # Verifica presenza di struttura (heading)
        if html_report.count('<h2>') < 3:
            score -= 0.2
        
        if html_report.count('<h3>') < 5:
            score -= 0.1
        
        # Verifica presenza liste
        if '<ul>' not in html_report and '<ol>' not in html_report:
            score -= 0.1
        
        return max(0, score)
    
    def _assess_standards_compliance(self, html_report: str) -> float:
        """Valuta conformità agli standard"""
        
        score = 1.0
        
        # Verifica tabelle accessibili
        if '<table>' in html_report:
            if '<caption>' not in html_report:
                score -= 0.1
            if 'scope=' not in html_report:
                score -= 0.1
        
        # Verifica lang attribute
        if 'lang="it"' not in html_report:
            score -= 0.1
        
        # Verifica meta tags
        if '<meta charset=' not in html_report:
            score -= 0.1
        
        return max(0, score)
    
    def _assess_professionalism(self, html_report: str) -> float:
        """Valuta professionalità del report"""
        
        score = 1.0
        
        # Verifica assenza di placeholder
        placeholders = ['TODO', 'FIXME', 'XXX', 'Lorem ipsum', 'undefined', 'null']
        for placeholder in placeholders:
            if placeholder in html_report:
                score -= 0.2
        
        # Verifica formattazione date
        if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', html_report):
            score -= 0.1
        
        # Verifica presenza contatti
        if '@' not in html_report:  # Email
            score -= 0.1
        
        return max(0, score)
    
    def _generate_validation_report(self, *issue_lists) -> Dict[str, Any]:
        """Genera report di validazione"""
        
        all_issues = []
        for issue_list in issue_lists:
            all_issues.extend(issue_list)
        
        report = {
            'total_issues': len(all_issues),
            'errors': len([i for i in all_issues if i.get('severity') == 'error']),
            'warnings': len([i for i in all_issues if i.get('severity') == 'warning']),
            'info': len([i for i in all_issues if i.get('severity') == 'info']),
            'issues_by_type': defaultdict(list)
        }
        
        for issue in all_issues:
            report['issues_by_type'][issue.get('type', 'unknown')].append(issue)
        
        report['issues_by_type'] = dict(report['issues_by_type'])
        
        return report
    
    def _log_validation_results(self, validation_report: Dict[str, Any]):
        """Log risultati della validazione"""
        
        self.logger.info(f"Validation completed:")
        self.logger.info(f"  Total issues: {validation_report['total_issues']}")
        self.logger.info(f"  Errors: {validation_report['errors']}")
        self.logger.info(f"  Warnings: {validation_report['warnings']}")
        self.logger.info(f"  Info: {validation_report['info']}")
        
        if validation_report['errors'] > 0:
            self.logger.warning(f"Found {validation_report['errors']} validation errors")
            for issue_type, issues in validation_report['issues_by_type'].items():
                errors = [i for i in issues if i.get('severity') == 'error']
                if errors:
                    self.logger.warning(f"  {issue_type}: {len(errors)} errors")
    
    def validate_input(self, context: AgentContext) -> bool:
        """Valida input per quality control"""
        return True  # Quality control può sempre eseguire
    
    async def generate_section(self, context: AgentContext) -> str:
        """Non genera sezione propria, solo validazione"""
        return ""  # Quality controller non genera contenuto proprio