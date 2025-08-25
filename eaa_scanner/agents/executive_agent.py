"""Executive Summary Agent - Genera sintesi esecutiva professionale"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentContext, AgentPriority

logger = logging.getLogger(__name__)


class ExecutiveSummaryAgent(BaseAgent):
    """Agent specializzato nella generazione di executive summary"""
    
    def __init__(self, priority: AgentPriority = AgentPriority.CRITICAL):
        super().__init__(
            name="executive",
            priority=priority,
            timeout=20
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        """Valida che il contesto contenga i dati necessari"""
        required_fields = [
            'scan_data',
            'company_info',
            'shared_metrics'
        ]
        
        for field in required_fields:
            if not hasattr(context, field):
                self.logger.error(f"Missing required field: {field}")
                return False
        
        # Valida dati company
        if not context.company_info.get('company_name'):
            self.logger.error("Missing company name")
            return False
        
        return True
    
    async def generate_section(self, context: AgentContext) -> str:
        """Genera la sezione executive summary"""
        
        # Estrai metriche chiave
        key_metrics = self._extract_key_metrics(context.scan_data)
        
        # Calcola business impact
        business_impact = self._calculate_business_impact(key_metrics, context)
        
        # Identifica top issues
        top_issues = self._identify_top_issues(context.scan_data)
        
        # Genera raccomandazioni strategiche
        strategic_recommendations = self._generate_strategic_recommendations(
            key_metrics, business_impact, top_issues
        )
        
        # Componi executive summary
        return self._compose_executive_summary(
            context,
            key_metrics,
            business_impact,
            top_issues,
            strategic_recommendations
        )
    
    def _extract_key_metrics(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae metriche chiave per executive"""
        
        # Estrai da compliance metrics se disponibili
        compliance = scan_data.get('compliance', {})
        violations = scan_data.get('all_violations', [])
        
        # Conta severità
        critical_count = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        high_count = len([v for v in violations if v.get('severity') == 'high'])
        medium_count = len([v for v in violations if v.get('severity') in ['moderate', 'medium']])
        low_count = len([v for v in violations if v.get('severity') in ['minor', 'low']])
        
        return {
            'overall_score': compliance.get('overall_score', 0),
            'compliance_level': compliance.get('compliance_level', 'unknown'),
            'total_issues': len(violations),
            'critical_issues': critical_count,
            'high_priority_issues': high_count,
            'medium_priority_issues': medium_count,
            'low_priority_issues': low_count,
            'affected_users_percentage': self._estimate_affected_users(violations),
            'wcag_coverage': compliance.get('wcag_coverage', 0),
            'eaa_compliance': compliance.get('eaa_compliance_percentage', 0)
        }
    
    def _calculate_business_impact(self, 
                                  metrics: Dict[str, Any],
                                  context: AgentContext) -> Dict[str, Any]:
        """Calcola l'impatto sul business"""
        
        score = metrics['overall_score']
        critical_issues = metrics['critical_issues']
        
        # Stima rischio legale
        legal_risk = 'Alto' if score < 60 or critical_issues > 5 else \
                    'Medio' if score < 80 or critical_issues > 0 else 'Basso'
        
        # Stima perdita potenziale utenti
        user_loss_risk = metrics['affected_users_percentage']
        
        # Stima impatto reputazionale
        reputation_impact = 'Critico' if score < 50 else \
                           'Significativo' if score < 70 else \
                           'Moderato' if score < 85 else 'Minimo'
        
        # Calcola urgenza intervento
        urgency = 'Immediata' if critical_issues > 10 or score < 50 else \
                 'Alta' if critical_issues > 5 or score < 70 else \
                 'Media' if critical_issues > 0 or score < 85 else 'Bassa'
        
        return {
            'legal_risk': legal_risk,
            'user_loss_percentage': user_loss_risk,
            'reputation_impact': reputation_impact,
            'intervention_urgency': urgency,
            'eaa_deadline_risk': critical_issues > 0,
            'competitive_disadvantage': score < 70
        }
    
    def _identify_top_issues(self, scan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identifica i top 3-5 problemi più critici"""
        
        violations = scan_data.get('all_violations', [])
        
        # Raggruppa per tipologia
        issue_groups = {}
        for violation in violations:
            code = violation.get('code', 'unknown')
            if code not in issue_groups:
                issue_groups[code] = {
                    'code': code,
                    'message': violation.get('message', ''),
                    'wcag': violation.get('wcag_criteria', ''),
                    'count': 0,
                    'severity': violation.get('severity', 'unknown'),
                    'impact': self._assess_issue_impact(violation)
                }
            issue_groups[code]['count'] += 1
        
        # Ordina per criticità e frequenza
        severity_weight = {'critical': 10, 'serious': 8, 'high': 6, 'moderate': 4, 'minor': 2, 'low': 1}
        
        sorted_issues = sorted(
            issue_groups.values(),
            key=lambda x: severity_weight.get(x['severity'], 0) * x['count'],
            reverse=True
        )
        
        return sorted_issues[:5]
    
    def _assess_issue_impact(self, violation: Dict[str, Any]) -> str:
        """Valuta l'impatto di un problema specifico"""
        
        code = violation.get('code', '').lower()
        severity = violation.get('severity', '').lower()
        
        if 'alt' in code or 'image' in code:
            return "Utenti non vedenti non possono accedere ai contenuti visuali"
        elif 'contrast' in code:
            return "Utenti ipovedenti hanno difficoltà a leggere i contenuti"
        elif 'keyboard' in code:
            return "Utenti che utilizzano solo tastiera non possono navigare"
        elif 'label' in code or 'form' in code:
            return "Utenti con screen reader non possono compilare moduli"
        elif 'heading' in code or 'structure' in code:
            return "Navigazione confusa per utenti di tecnologie assistive"
        elif severity in ['critical', 'serious']:
            return "Barriera critica all'accessibilità del sito"
        else:
            return "Impatto moderato sull'esperienza utente"
    
    def _generate_strategic_recommendations(self,
                                           metrics: Dict[str, Any],
                                           impact: Dict[str, Any],
                                           top_issues: List[Dict]) -> List[Dict[str, Any]]:
        """Genera raccomandazioni strategiche per il management"""
        
        recommendations = []
        
        # Raccomandazione basata su urgenza
        if impact['intervention_urgency'] in ['Immediata', 'Alta']:
            recommendations.append({
                'priority': 'Critica',
                'action': 'Attivare task force dedicata all\'accessibilità',
                'timeline': '1-2 settimane',
                'rationale': f"Score attuale {metrics['overall_score']:.1f}/100 richiede intervento immediato",
                'business_benefit': 'Mitigazione rischio legale e reputazionale'
            })
        
        # Raccomandazione per problemi critici
        if metrics['critical_issues'] > 0:
            recommendations.append({
                'priority': 'Alta',
                'action': f"Risolvere {metrics['critical_issues']} problemi critici identificati",
                'timeline': '30 giorni',
                'rationale': 'Problemi critici bloccano completamente alcuni utenti',
                'business_benefit': f"Recupero del {metrics['affected_users_percentage']:.1f}% di utenti esclusi"
            })
        
        # Raccomandazione per compliance EAA
        if metrics['eaa_compliance'] < 100:
            recommendations.append({
                'priority': 'Alta',
                'action': 'Implementare piano di conformità EAA',
                'timeline': '90 giorni',
                'rationale': 'Conformità obbligatoria per European Accessibility Act',
                'business_benefit': 'Evitare sanzioni e accedere a mercato EU completo'
            })
        
        # Raccomandazione per formazione
        if metrics['total_issues'] > 50:
            recommendations.append({
                'priority': 'Media',
                'action': 'Formazione team sviluppo su accessibilità',
                'timeline': '60 giorni',
                'rationale': 'Prevenire futuri problemi attraverso competenze interne',
                'business_benefit': 'Riduzione costi correzione del 60% a lungo termine'
            })
        
        # Raccomandazione per monitoraggio continuo
        recommendations.append({
            'priority': 'Media',
            'action': 'Implementare monitoraggio accessibilità continuo',
            'timeline': '120 giorni',
            'rationale': 'Mantenere conformità nel tempo',
            'business_benefit': 'Prevenzione regressioni e mantenimento standard'
        })
        
        return recommendations[:4]  # Limita a 4 raccomandazioni principali
    
    def _estimate_affected_users(self, violations: List[Dict]) -> float:
        """Stima la percentuale di utenti impattati"""
        
        if not violations:
            return 0.0
        
        # Stima basata su statistiche disabilità (circa 15% popolazione)
        base_percentage = 15.0
        
        # Aggiusta in base a severità problemi
        critical_violations = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        
        if critical_violations > 10:
            return base_percentage  # Tutti gli utenti con disabilità impattati
        elif critical_violations > 5:
            return base_percentage * 0.7
        elif critical_violations > 0:
            return base_percentage * 0.4
        else:
            return base_percentage * 0.2  # Solo alcuni gruppi impattati
    
    def _compose_executive_summary(self,
                                  context: AgentContext,
                                  metrics: Dict[str, Any],
                                  impact: Dict[str, Any],
                                  top_issues: List[Dict],
                                  recommendations: List[Dict]) -> str:
        """Compone l'executive summary finale"""
        
        company_name = context.company_info.get('company_name', 'N/A')
        url = context.company_info.get('url', 'N/A')
        
        # Determina classe CSS per stato
        status_class = self._get_status_class(metrics['compliance_level'])
        urgency_class = self._get_urgency_class(impact['intervention_urgency'])
        
        # Genera HTML
        html = f"""
        <section class="executive-summary">
            <h2>Executive Summary</h2>
            
            <div class="key-findings">
                <h3>Risultati Chiave</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <span class="metric-label">Score Complessivo</span>
                        <span class="metric-value {status_class}">{metrics['overall_score']:.1f}/100</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Stato Conformità</span>
                        <span class="metric-value {status_class}">{self._translate_compliance_level(metrics['compliance_level'])}</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Problemi Critici</span>
                        <span class="metric-value critical">{metrics['critical_issues']}</span>
                    </div>
                    <div class="metric-card">
                        <span class="metric-label">Utenti Impattati</span>
                        <span class="metric-value">{metrics['affected_users_percentage']:.1f}%</span>
                    </div>
                </div>
            </div>
            
            <div class="business-impact">
                <h3>Impatto sul Business</h3>
                <table class="impact-table">
                    <tbody>
                        <tr>
                            <th scope="row">Rischio Legale</th>
                            <td class="{self._get_risk_class(impact['legal_risk'])}">{impact['legal_risk']}</td>
                        </tr>
                        <tr>
                            <th scope="row">Impatto Reputazionale</th>
                            <td class="{self._get_risk_class(impact['reputation_impact'])}">{impact['reputation_impact']}</td>
                        </tr>
                        <tr>
                            <th scope="row">Urgenza Intervento</th>
                            <td class="{urgency_class}">{impact['intervention_urgency']}</td>
                        </tr>
                        <tr>
                            <th scope="row">Conformità EAA</th>
                            <td>{"A rischio" if impact['eaa_deadline_risk'] else "In linea"}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="top-issues">
                <h3>Problemi Principali da Risolvere</h3>
                <ol>
        """
        
        # Aggiungi top issues
        for issue in top_issues[:3]:
            severity_class = self._get_severity_class(issue['severity'])
            html += f"""
                    <li>
                        <strong>{issue['message'][:100]}...</strong>
                        <span class="issue-meta">
                            ({issue['count']} occorrenze, 
                            <span class="{severity_class}">{issue['severity']}</span>, 
                            WCAG {issue['wcag'] or 'N/A'})
                        </span>
                        <br>
                        <em>Impatto: {issue['impact']}</em>
                    </li>
            """
        
        html += """
                </ol>
            </div>
            
            <div class="strategic-recommendations">
                <h3>Raccomandazioni Strategiche</h3>
                <div class="recommendations-list">
        """
        
        # Aggiungi raccomandazioni
        for i, rec in enumerate(recommendations, 1):
            priority_class = self._get_priority_class(rec['priority'])
            html += f"""
                    <div class="recommendation-card">
                        <div class="rec-header">
                            <span class="rec-number">{i}</span>
                            <span class="rec-priority {priority_class}">{rec['priority']}</span>
                            <span class="rec-timeline">{rec['timeline']}</span>
                        </div>
                        <h4>{rec['action']}</h4>
                        <p class="rec-rationale">{rec['rationale']}</p>
                        <p class="rec-benefit"><strong>Beneficio:</strong> {rec['business_benefit']}</p>
                    </div>
            """
        
        html += """
                </div>
            </div>
            
            <div class="executive-conclusion">
                <h3>Conclusione</h3>
                <p>
        """
        
        # Genera conclusione basata sui dati
        if metrics['overall_score'] < 50:
            html += f"""Il sito di {company_name} presenta <strong>gravi problemi di accessibilità</strong> 
                       che richiedono un intervento immediato e strutturato. L'attuale score di 
                       {metrics['overall_score']:.1f}/100 espone l'azienda a significativi rischi legali 
                       e reputazionali, oltre a escludere circa il {metrics['affected_users_percentage']:.1f}% 
                       di potenziali utenti."""
        elif metrics['overall_score'] < 70:
            html += f"""Il sito di {company_name} presenta <strong>problemi di accessibilità significativi</strong> 
                       che necessitano di attenzione prioritaria. Con uno score di {metrics['overall_score']:.1f}/100, 
                       è essenziale implementare rapidamente le correzioni per raggiungere la conformità 
                       richiesta e migliorare l'esperienza per il {metrics['affected_users_percentage']:.1f}% 
                       di utenti attualmente impattati."""
        elif metrics['overall_score'] < 85:
            html += f"""Il sito di {company_name} mostra un <strong>livello di accessibilità discreto</strong> 
                       con uno score di {metrics['overall_score']:.1f}/100, ma richiede ancora interventi 
                       mirati per raggiungere la piena conformità. Le aree di miglioramento identificate 
                       permetteranno di servire meglio il {metrics['affected_users_percentage']:.1f}% 
                       di utenti attualmente con difficoltà di accesso."""
        else:
            html += f"""Il sito di {company_name} dimostra un <strong>buon livello di accessibilità</strong> 
                       con uno score di {metrics['overall_score']:.1f}/100. Con interventi mirati sui 
                       pochi problemi residui, è possibile raggiungere l'eccellenza nell'accessibilità 
                       e servire ottimalmente tutti gli utenti."""
        
        html += f"""
                </p>
                <p>
                    <strong>Prossimi passi consigliati:</strong> Implementare immediatamente le 
                    raccomandazioni prioritarie, stabilire un team dedicato all'accessibilità e 
                    pianificare una roadmap di miglioramento continuo.
                </p>
            </div>
        </section>
        """
        
        return html
    
    def _translate_compliance_level(self, level: str) -> str:
        """Traduce il livello di conformità"""
        translations = {
            'compliant': 'Conforme',
            'partially_compliant': 'Parzialmente Conforme',
            'non_compliant': 'Non Conforme',
            'unknown': 'Da Verificare'
        }
        return translations.get(level, level)
    
    def _get_status_class(self, compliance_level: str) -> str:
        """Determina classe CSS per stato"""
        if 'compliant' in compliance_level and 'non' not in compliance_level and 'partially' not in compliance_level:
            return 'status-good'
        elif 'partially' in compliance_level:
            return 'status-warning'
        else:
            return 'status-critical'
    
    def _get_urgency_class(self, urgency: str) -> str:
        """Determina classe CSS per urgenza"""
        if urgency in ['Immediata', 'Critica']:
            return 'urgency-critical'
        elif urgency == 'Alta':
            return 'urgency-high'
        elif urgency == 'Media':
            return 'urgency-medium'
        else:
            return 'urgency-low'
    
    def _get_risk_class(self, risk: str) -> str:
        """Determina classe CSS per rischio"""
        if risk in ['Alto', 'Critico']:
            return 'risk-high'
        elif risk in ['Medio', 'Significativo']:
            return 'risk-medium'
        else:
            return 'risk-low'
    
    def _get_severity_class(self, severity: str) -> str:
        """Determina classe CSS per severità"""
        if severity in ['critical', 'serious']:
            return 'severity-critical'
        elif severity in ['high']:
            return 'severity-high'
        elif severity in ['moderate', 'medium']:
            return 'severity-medium'
        else:
            return 'severity-low'
    
    def _get_priority_class(self, priority: str) -> str:
        """Determina classe CSS per priorità"""
        if priority in ['Critica', 'Critical']:
            return 'priority-critical'
        elif priority == 'Alta':
            return 'priority-high'
        elif priority == 'Media':
            return 'priority-medium'
        else:
            return 'priority-low'