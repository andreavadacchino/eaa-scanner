"""Context Manager - Gestione contesto condiviso tra agent"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from .base_agent import AgentContext

logger = logging.getLogger(__name__)


class ContextManager:
    """Gestore del contesto condiviso tra agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._context_cache = {}
        self._shared_metrics = {}
        
    async def prepare_context(self,
                             scan_data: Dict[str, Any],
                             company_info: Dict[str, Any],
                             requirements: Dict[str, Any]) -> AgentContext:
        """Prepara contesto arricchito per gli agent
        
        Args:
            scan_data: Dati grezzi della scansione
            company_info: Info azienda
            requirements: Requisiti del report
            
        Returns:
            AgentContext con dati normalizzati e arricchiti
        """
        
        self.logger.info(f"Preparing context for {company_info.get('company_name', 'Unknown')}")
        
        # Normalizza e valida scan_data
        normalized_scan_data = self._normalize_scan_data(scan_data)
        
        # Valida e arricchisci company_info
        validated_company_info = self._validate_company_info(company_info)
        
        # Prepara metriche condivise
        shared_metrics = self._prepare_shared_metrics(normalized_scan_data)
        
        # Determina target audience e preferences
        target_audience = requirements.get('target_audience', 'mixed')
        format_preferences = self._determine_format_preferences(requirements)
        
        # Crea contesto
        context = AgentContext(
            scan_data=normalized_scan_data,
            company_info=validated_company_info,
            requirements=requirements,
            shared_metrics=shared_metrics,
            generation_timestamp=datetime.now(),
            target_audience=target_audience,
            language=requirements.get('language', 'it'),
            format_preferences=format_preferences
        )
        
        # Cache per riuso
        cache_key = f"{validated_company_info.get('company_name')}_{datetime.now().date()}"
        self._context_cache[cache_key] = context
        
        return context
    
    def _normalize_scan_data(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizza i dati della scansione
        
        Gestisce diversi formati di input e assicura struttura consistente
        """
        
        normalized = {
            'all_violations': [],
            'compliance': {},
            'scanner_results': {},
            'metadata': {}
        }
        
        # Gestisci diversi formati di input
        if 'aggregated_results' in scan_data:
            # Formato nuovo con AggregatedResults
            agg = scan_data['aggregated_results']
            normalized['all_violations'] = agg.get('all_violations', [])
            normalized['compliance'] = agg.get('compliance', {})
            normalized['scanner_results'] = agg.get('by_scanner', {})
            normalized['metadata'] = agg.get('scan_metadata', {})
            
        elif 'all_violations' in scan_data:
            # Formato diretto
            normalized = scan_data
            
        elif 'detailed_results' in scan_data:
            # Formato legacy n8n
            detailed = scan_data['detailed_results']
            
            # Converti errors e warnings in violations
            violations = []
            
            if 'errors' in detailed:
                for error in detailed['errors']:
                    violations.append({
                        'code': error.get('code', 'unknown'),
                        'message': error.get('message', ''),
                        'severity': 'serious',
                        'wcag_criteria': error.get('wcag', ''),
                        'selector': error.get('selector', ''),
                        'source': error.get('source', 'unknown')
                    })
            
            if 'warnings' in detailed:
                for warning in detailed['warnings']:
                    violations.append({
                        'code': warning.get('code', 'unknown'),
                        'message': warning.get('message', ''),
                        'severity': 'moderate',
                        'wcag_criteria': warning.get('wcag', ''),
                        'selector': warning.get('selector', ''),
                        'source': warning.get('source', 'unknown')
                    })
            
            normalized['all_violations'] = violations
            normalized['compliance'] = scan_data.get('compliance', {})
            
        # Assicura che compliance abbia struttura minima
        if not normalized['compliance']:
            normalized['compliance'] = self._calculate_basic_compliance(normalized['all_violations'])
        
        # Valida e pulisci violations
        normalized['all_violations'] = self._validate_violations(normalized['all_violations'])
        
        return normalized
    
    def _validate_company_info(self, company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e arricchisce informazioni azienda"""
        
        validated = {
            'company_name': company_info.get('company_name', 'Non Specificato'),
            'url': company_info.get('url', company_info.get('website', '')),
            'email': company_info.get('email', company_info.get('contact_email', '')),
            'country': company_info.get('country', 'Italia'),
            'industry': company_info.get('industry', 'Non Specificato'),
            'company_size': company_info.get('company_size', 'Non Specificato')
        }
        
        # Pulisci URL
        if validated['url'] and not validated['url'].startswith('http'):
            validated['url'] = f"https://{validated['url']}"
        
        # Valida email
        if validated['email'] and '@' not in validated['email']:
            self.logger.warning(f"Invalid email format: {validated['email']}")
            validated['email'] = ''
        
        return validated
    
    def _prepare_shared_metrics(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara metriche condivise per tutti gli agent"""
        
        violations = scan_data.get('all_violations', [])
        compliance = scan_data.get('compliance', {})
        
        # Calcola metriche base
        metrics = {
            'total_violations': len(violations),
            'critical_count': len([v for v in violations if v.get('severity') in ['critical', 'serious']]),
            'high_count': len([v for v in violations if v.get('severity') == 'high']),
            'medium_count': len([v for v in violations if v.get('severity') in ['moderate', 'medium']]),
            'low_count': len([v for v in violations if v.get('severity') in ['minor', 'low']]),
            'unique_codes': len(set(v.get('code', '') for v in violations)),
            'affected_pages': len(set(v.get('page', 'main') for v in violations)),
            'overall_score': compliance.get('overall_score', 0),
            'compliance_level': compliance.get('compliance_level', 'unknown'),
            'wcag_coverage': compliance.get('wcag_coverage', 0),
            'timestamp': datetime.now().isoformat()
        }
        
        # Calcola percentuali
        if metrics['total_violations'] > 0:
            metrics['critical_percentage'] = (metrics['critical_count'] / metrics['total_violations']) * 100
            metrics['high_percentage'] = (metrics['high_count'] / metrics['total_violations']) * 100
        else:
            metrics['critical_percentage'] = 0
            metrics['high_percentage'] = 0
        
        # Stima impatto utenti
        metrics['estimated_user_impact'] = self._estimate_user_impact(violations)
        
        # Aggiungi analisi per scanner se disponibile
        if 'scanner_results' in scan_data:
            metrics['scanner_coverage'] = self._analyze_scanner_coverage(scan_data['scanner_results'])
        
        return metrics
    
    def _determine_format_preferences(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Determina preferenze di formattazione basate sui requisiti"""
        
        target_audience = requirements.get('target_audience', 'mixed')
        
        if target_audience == 'executive':
            return {
                'style': 'executive',
                'detail_level': 'summary',
                'include_technical': False,
                'include_costs': True,
                'include_timeline': True,
                'max_sections': 5
            }
        elif target_audience == 'technical':
            return {
                'style': 'technical',
                'detail_level': 'comprehensive',
                'include_technical': True,
                'include_code_samples': True,
                'include_wcag_details': True,
                'max_sections': 10
            }
        else:  # mixed
            return {
                'style': 'professional',
                'detail_level': 'balanced',
                'include_technical': True,
                'include_executive_summary': True,
                'include_recommendations': True,
                'max_sections': 8
            }
    
    def _calculate_basic_compliance(self, violations: list) -> Dict[str, Any]:
        """Calcola compliance di base quando non disponibile"""
        
        total = len(violations)
        critical = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        
        # Formula semplice per score
        if total == 0:
            score = 100
        elif critical > 10:
            score = max(0, 40 - critical)
        elif critical > 5:
            score = max(20, 60 - critical * 2)
        elif critical > 0:
            score = max(40, 80 - critical * 4)
        else:
            score = max(50, 100 - total * 2)
        
        # Determina livello
        if score >= 90:
            level = 'compliant'
        elif score >= 70:
            level = 'partially_compliant'
        else:
            level = 'non_compliant'
        
        return {
            'overall_score': score,
            'compliance_level': level,
            'by_principle': {
                'perceivable': max(30, score - 10),
                'operable': max(30, score - 5),
                'understandable': max(40, score),
                'robust': max(35, score - 8)
            },
            'wcag_coverage': min(40, 100 - critical * 5),
            'eaa_compliance_percentage': max(0, score - 20)
        }
    
    def _validate_violations(self, violations: list) -> list:
        """Valida e pulisce lista violazioni"""
        
        validated = []
        seen = set()
        
        for violation in violations:
            # Crea chiave unica per deduplicazione
            key = f"{violation.get('code', '')}_{violation.get('selector', '')}_{violation.get('wcag_criteria', '')}"
            
            if key not in seen:
                seen.add(key)
                
                # Assicura campi minimi
                validated_violation = {
                    'code': violation.get('code', 'unknown'),
                    'message': violation.get('message', 'Problema di accessibilità'),
                    'severity': violation.get('severity', 'moderate'),
                    'wcag_criteria': violation.get('wcag_criteria', ''),
                    'selector': violation.get('selector', ''),
                    'source': violation.get('source', 'unknown'),
                    'help': violation.get('help', ''),
                    'help_url': violation.get('help_url', '')
                }
                
                # Normalizza severity
                severity_map = {
                    'error': 'serious',
                    'warning': 'moderate',
                    'notice': 'minor',
                    'critical': 'critical',
                    'serious': 'serious',
                    'moderate': 'moderate',
                    'minor': 'minor'
                }
                
                validated_violation['severity'] = severity_map.get(
                    validated_violation['severity'].lower(),
                    'moderate'
                )
                
                validated.append(validated_violation)
        
        return validated
    
    def _estimate_user_impact(self, violations: list) -> float:
        """Stima percentuale utenti impattati"""
        
        if not violations:
            return 0.0
        
        critical = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        high = len([v for v in violations if v.get('severity') == 'high'])
        
        # Base: 15% popolazione ha disabilità
        base = 15.0
        
        # Aggiungi utenti con difficoltà temporanee o situazionali
        if critical > 10:
            return base + 10  # 25% totale
        elif critical > 5:
            return base + 5   # 20% totale
        elif critical > 0:
            return base + 2   # 17% totale
        elif high > 10:
            return base      # 15% totale
        else:
            return base * 0.5  # 7.5% totale
    
    def _analyze_scanner_coverage(self, scanner_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analizza copertura dei diversi scanner"""
        
        coverage = {
            'total_scanners': 0,
            'successful_scanners': 0,
            'failed_scanners': [],
            'coverage_percentage': 0
        }
        
        expected_scanners = ['wave', 'axe', 'lighthouse', 'pa11y']
        
        for scanner in expected_scanners:
            if scanner in scanner_results:
                coverage['total_scanners'] += 1
                if scanner_results[scanner].get('status') == 'success':
                    coverage['successful_scanners'] += 1
                else:
                    coverage['failed_scanners'].append(scanner)
        
        if coverage['total_scanners'] > 0:
            coverage['coverage_percentage'] = \
                (coverage['successful_scanners'] / len(expected_scanners)) * 100
        
        return coverage
    
    def update_shared_metrics(self, agent_name: str, metrics: Dict[str, Any]):
        """Aggiorna metriche condivise dopo esecuzione agent
        
        Args:
            agent_name: Nome dell'agent
            metrics: Metriche da aggiungere
        """
        self._shared_metrics[agent_name] = {
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_shared_metrics(self) -> Dict[str, Any]:
        """Ottiene tutte le metriche condivise"""
        return self._shared_metrics.copy()
    
    def clear_cache(self):
        """Pulisce cache del contesto"""
        self._context_cache.clear()
        self._shared_metrics.clear()
        self.logger.info("Context cache cleared")