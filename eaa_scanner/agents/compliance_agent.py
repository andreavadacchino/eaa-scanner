"""Compliance Assessment Agent - Valutazione conformità WCAG/EAA"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentContext, AgentPriority

logger = logging.getLogger(__name__)


class ComplianceAssessmentAgent(BaseAgent):
    """Agent specializzato nella valutazione di conformità"""
    
    def __init__(self, priority: AgentPriority = AgentPriority.HIGH):
        super().__init__(
            name="compliance",
            priority=priority,
            timeout=20
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return True  # Sempre valido
    
    async def generate_section(self, context: AgentContext) -> str:
        """Genera sezione conformità"""
        
        compliance = context.scan_data.get('compliance', {})
        violations = context.scan_data.get('all_violations', [])
        
        # Valuta conformità per standard
        wcag_assessment = self._assess_wcag_compliance(compliance, violations)
        eaa_assessment = self._assess_eaa_compliance(compliance, violations)
        en301549_assessment = self._assess_en301549_compliance(compliance, violations)
        
        return self._compose_compliance_section(
            context,
            wcag_assessment,
            eaa_assessment,
            en301549_assessment
        )
    
    def _assess_wcag_compliance(self, compliance: Dict, violations: List) -> Dict[str, Any]:
        """Valuta conformità WCAG 2.1 AA"""
        
        critical_violations = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        
        # Determina livello conformità
        if critical_violations == 0 and len(violations) < 10:
            level = "Conforme"
            status = "success"
        elif critical_violations <= 5:
            level = "Parzialmente Conforme"
            status = "warning"
        else:
            level = "Non Conforme"
            status = "error"
        
        return {
            'level': level,
            'status': status,
            'score': compliance.get('overall_score', 0),
            'critical_violations': critical_violations,
            'total_violations': len(violations),
            'principles': compliance.get('by_principle', {})
        }
    
    def _assess_eaa_compliance(self, compliance: Dict, violations: List) -> Dict[str, Any]:
        """Valuta conformità European Accessibility Act"""
        
        eaa_score = compliance.get('eaa_compliance_percentage', 0)
        critical = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        
        if eaa_score >= 90 and critical == 0:
            status = "Conforme EAA"
        elif eaa_score >= 70:
            status = "Parzialmente Conforme EAA"
        else:
            status = "Non Conforme EAA - Intervento Urgente"
        
        return {
            'status': status,
            'score': eaa_score,
            'deadline_risk': critical > 0,
            'required_actions': self._get_eaa_required_actions(critical, len(violations))
        }
    
    def _assess_en301549_compliance(self, compliance: Dict, violations: List) -> Dict[str, Any]:
        """Valuta conformità EN 301 549"""
        
        # EN 301 549 allineato con WCAG 2.1 AA
        wcag_score = compliance.get('overall_score', 0)
        
        return {
            'status': "Conforme" if wcag_score >= 85 else "Parzialmente Conforme" if wcag_score >= 60 else "Non Conforme",
            'score': wcag_score,
            'applicable_clauses': [
                "9.1 - Percepibile",
                "9.2 - Utilizzabile",
                "9.3 - Comprensibile",
                "9.4 - Robusto"
            ]
        }
    
    def _get_eaa_required_actions(self, critical: int, total: int) -> List[str]:
        """Ottiene azioni richieste per conformità EAA"""
        actions = []
        
        if critical > 0:
            actions.append(f"Risolvere {critical} violazioni critiche immediatamente")
        if total > 20:
            actions.append("Implementare piano remediation strutturato")
        actions.append("Documentare conformità per autorità competenti")
        actions.append("Implementare monitoraggio continuo")
        
        return actions
    
    def _compose_compliance_section(self,
                                   context: AgentContext,
                                   wcag: Dict,
                                   eaa: Dict,
                                   en301549: Dict) -> str:
        """Compone sezione HTML conformità"""
        
        return f"""
        <section class="compliance-assessment">
            <h2>Valutazione di Conformità</h2>
            
            <div class="compliance-summary">
                <h3>Stato Generale di Conformità</h3>
                <table class="compliance-table">
                    <thead>
                        <tr>
                            <th scope="col">Standard</th>
                            <th scope="col">Stato</th>
                            <th scope="col">Score</th>
                            <th scope="col">Note</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th scope="row">WCAG 2.1 AA</th>
                            <td class="status-{wcag['status']}">{wcag['level']}</td>
                            <td>{wcag['score']:.1f}/100</td>
                            <td>{wcag['critical_violations']} violazioni critiche</td>
                        </tr>
                        <tr>
                            <th scope="row">EAA</th>
                            <td>{eaa['status']}</td>
                            <td>{eaa['score']:.1f}%</td>
                            <td>{'Deadline a rischio' if eaa['deadline_risk'] else 'In linea'}</td>
                        </tr>
                        <tr>
                            <th scope="row">EN 301 549</th>
                            <td>{en301549['status']}</td>
                            <td>{en301549['score']:.1f}/100</td>
                            <td>Standard EU applicabile</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="wcag-principles">
                <h3>Conformità per Principio WCAG</h3>
                <table>
                    <thead>
                        <tr>
                            <th scope="col">Principio</th>
                            <th scope="col">Score</th>
                            <th scope="col">Valutazione</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <th scope="row">Percepibile</th>
                            <td>{wcag['principles'].get('perceivable', 0):.1f}%</td>
                            <td>{self._get_principle_assessment(wcag['principles'].get('perceivable', 0))}</td>
                        </tr>
                        <tr>
                            <th scope="row">Utilizzabile</th>
                            <td>{wcag['principles'].get('operable', 0):.1f}%</td>
                            <td>{self._get_principle_assessment(wcag['principles'].get('operable', 0))}</td>
                        </tr>
                        <tr>
                            <th scope="row">Comprensibile</th>
                            <td>{wcag['principles'].get('understandable', 0):.1f}%</td>
                            <td>{self._get_principle_assessment(wcag['principles'].get('understandable', 0))}</td>
                        </tr>
                        <tr>
                            <th scope="row">Robusto</th>
                            <td>{wcag['principles'].get('robust', 0):.1f}%</td>
                            <td>{self._get_principle_assessment(wcag['principles'].get('robust', 0))}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="eaa-requirements">
                <h3>Requisiti European Accessibility Act</h3>
                <p>Lo stato attuale è: <strong>{eaa['status']}</strong></p>
                
                <h4>Azioni Richieste per Conformità EAA:</h4>
                <ol>
                    {''.join(f'<li>{action}</li>' for action in eaa['required_actions'])}
                </ol>
                
                {self._generate_eaa_warning(eaa) if eaa['deadline_risk'] else ''}
            </div>
            
            <div class="compliance-notes">
                <h3>Note sulla Valutazione</h3>
                <p>Questa valutazione automatica copre circa il 30-40% dei criteri di conformità. 
                Una valutazione completa richiede:</p>
                <ul>
                    <li>Test manuali con tecnologie assistive</li>
                    <li>Valutazione con utenti reali con disabilità</li>
                    <li>Verifica processi e transazioni complete</li>
                    <li>Test su dispositivi mobili</li>
                    <li>Valutazione contenuti multimediali</li>
                </ul>
            </div>
        </section>
        """
    
    def _get_principle_assessment(self, score: float) -> str:
        """Valuta principio WCAG"""
        if score >= 90:
            return "✅ Buono"
        elif score >= 70:
            return "⚠️ Da migliorare"
        else:
            return "❌ Critico"
    
    def _generate_eaa_warning(self, eaa: Dict) -> str:
        """Genera warning EAA se necessario"""
        return """
        <div class="eaa-warning" style="background: #ffe6e6; border-left: 4px solid #d7301f; 
             padding: 1rem; margin: 1rem 0;">
            <strong>⚠️ Attenzione Conformità EAA:</strong> 
            Il sito presenta problemi critici che mettono a rischio la conformità con 
            l'European Accessibility Act. È necessario un intervento immediato per evitare 
            possibili sanzioni e garantire l'accesso a tutti gli utenti.
        </div>
        """