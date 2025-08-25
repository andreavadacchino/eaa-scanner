"""Recommendations Agent - Genera raccomandazioni strategiche"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentContext, AgentPriority

logger = logging.getLogger(__name__)


class RecommendationsAgent(BaseAgent):
    """Agent specializzato nelle raccomandazioni strategiche"""
    
    def __init__(self, priority: AgentPriority = AgentPriority.NORMAL):
        super().__init__(
            name="recommendations",
            priority=priority,
            timeout=15
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return True
    
    async def generate_section(self, context: AgentContext) -> str:
        """Genera raccomandazioni strategiche"""
        
        violations = context.scan_data.get('all_violations', [])
        compliance = context.scan_data.get('compliance', {})
        score = compliance.get('overall_score', 0)
        
        # Genera diversi tipi di raccomandazioni
        immediate_actions = self._get_immediate_actions(violations, score)
        strategic_recommendations = self._get_strategic_recommendations(score, len(violations))
        best_practices = self._get_best_practices(violations)
        tools_recommendations = self._get_tools_recommendations()
        
        return self._compose_recommendations_section(
            context,
            immediate_actions,
            strategic_recommendations,
            best_practices,
            tools_recommendations
        )
    
    def _get_immediate_actions(self, violations: List[Dict], score: float) -> List[Dict]:
        """Ottiene azioni immediate basate sui dati"""
        
        actions = []
        
        critical = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        
        if critical > 10:
            actions.append({
                'action': 'Costituire task force accessibilità immediata',
                'rationale': f'{critical} problemi critici richiedono intervento urgente',
                'timeline': 'Entro 1 settimana',
                'priority': 'Critica'
            })
        
        if score < 50:
            actions.append({
                'action': 'Audit professionale completo con esperti',
                'rationale': f'Score {score:.0f}/100 richiede valutazione esperta',
                'timeline': 'Entro 2 settimane',
                'priority': 'Alta'
            })
        
        # Analizza pattern comuni
        alt_issues = len([v for v in violations if 'alt' in v.get('code', '').lower()])
        if alt_issues > 5:
            actions.append({
                'action': 'Implementare processo per testi alternativi',
                'rationale': f'{alt_issues} immagini senza alt text',
                'timeline': 'Entro 30 giorni',
                'priority': 'Alta'
            })
        
        return actions[:3]  # Max 3 azioni immediate
    
    def _get_strategic_recommendations(self, score: float, total_violations: int) -> List[Dict]:
        """Genera raccomandazioni strategiche"""
        
        recommendations = []
        
        if score < 70:
            recommendations.append({
                'title': 'Implementare Design System Accessibile',
                'description': 'Creare componenti UI accessibili by default per prevenire futuri problemi',
                'benefit': 'Riduzione 70% problemi futuri',
                'effort': 'Medio-Alto',
                'roi': 'Alto'
            })
        
        if total_violations > 50:
            recommendations.append({
                'title': 'Formazione Team Sviluppo',
                'description': 'Workshop WCAG 2.1 e best practice accessibilità',
                'benefit': 'Prevenzione problemi alla fonte',
                'effort': 'Basso',
                'roi': 'Molto Alto'
            })
        
        recommendations.append({
            'title': 'CI/CD con Test Accessibilità',
            'description': 'Integrare test automatici nel pipeline di sviluppo',
            'benefit': 'Identificazione precoce problemi',
            'effort': 'Medio',
            'roi': 'Alto'
        })
        
        recommendations.append({
            'title': 'Monitoraggio Continuo',
            'description': 'Implementare scansioni periodiche automatiche',
            'benefit': 'Mantenimento conformità nel tempo',
            'effort': 'Basso',
            'roi': 'Alto'
        })
        
        return recommendations[:4]
    
    def _get_best_practices(self, violations: List[Dict]) -> List[str]:
        """Ottiene best practice basate sui problemi trovati"""
        
        practices = []
        
        # Analizza tipi di problemi
        has_contrast = any('contrast' in v.get('code', '').lower() for v in violations)
        has_keyboard = any('keyboard' in v.get('code', '').lower() for v in violations)
        has_aria = any('aria' in v.get('code', '').lower() for v in violations)
        
        if has_contrast:
            practices.append('Utilizzare tool di verifica contrasto in fase di design')
        
        if has_keyboard:
            practices.append('Testare navigazione con sola tastiera per ogni release')
        
        if has_aria:
            practices.append('Utilizzare ARIA solo quando necessario, preferire HTML semantico')
        
        # Aggiungi pratiche generali
        practices.extend([
            'Coinvolgere utenti con disabilità nei test',
            'Documentare pattern accessibili per il team',
            'Includere accessibilità nei criteri di accettazione'
        ])
        
        return practices[:5]
    
    def _get_tools_recommendations(self) -> List[Dict]:
        """Raccomandazioni strumenti"""
        
        return [
            {
                'category': 'Sviluppo',
                'tools': ['axe DevTools', 'WAVE', 'Lighthouse'],
                'purpose': 'Test durante sviluppo'
            },
            {
                'category': 'CI/CD',
                'tools': ['Pa11y CI', 'axe-core', 'jest-axe'],
                'purpose': 'Test automatici'
            },
            {
                'category': 'Design',
                'tools': ['Stark (Figma)', 'Able', 'Color Oracle'],
                'purpose': 'Validazione design'
            },
            {
                'category': 'Testing',
                'tools': ['NVDA', 'JAWS', 'VoiceOver'],
                'purpose': 'Test con screen reader'
            }
        ]
    
    def _compose_recommendations_section(self,
                                        context: AgentContext,
                                        immediate: List[Dict],
                                        strategic: List[Dict],
                                        practices: List[str],
                                        tools: List[Dict]) -> str:
        """Compone sezione raccomandazioni"""
        
        return f"""
        <section class="recommendations">
            <h2>Raccomandazioni</h2>
            
            {self._generate_immediate_actions_html(immediate) if immediate else ''}
            
            <div class="strategic-recommendations">
                <h3>Raccomandazioni Strategiche</h3>
                <div class="recommendations-grid">
                    {self._generate_strategic_cards(strategic)}
                </div>
            </div>
            
            <div class="best-practices">
                <h3>Best Practice Consigliate</h3>
                <ul>
                    {''.join(f'<li>{practice}</li>' for practice in practices)}
                </ul>
            </div>
            
            <div class="tools-recommendations">
                <h3>Strumenti Consigliati</h3>
                <table>
                    <thead>
                        <tr>
                            <th scope="col">Categoria</th>
                            <th scope="col">Strumenti</th>
                            <th scope="col">Scopo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {self._generate_tools_rows(tools)}
                    </tbody>
                </table>
            </div>
            
            <div class="next-steps">
                <h3>Prossimi Passi Consigliati</h3>
                <ol>
                    <li><strong>Immediato:</strong> Correggere problemi critici identificati</li>
                    <li><strong>Breve termine (30gg):</strong> Implementare processo di test accessibilità</li>
                    <li><strong>Medio termine (90gg):</strong> Formare team e implementare best practice</li>
                    <li><strong>Lungo termine:</strong> Cultura aziendale di accessibilità by design</li>
                </ol>
            </div>
        </section>
        """
    
    def _generate_immediate_actions_html(self, actions: List[Dict]) -> str:
        """Genera HTML per azioni immediate"""
        
        if not actions:
            return ''
        
        items = []
        for action in actions:
            priority_class = 'priority-' + action['priority'].lower()
            items.append(f"""
                <div class="immediate-action">
                    <div class="action-header">
                        <span class="{priority_class}">{action['priority']}</span>
                        <span class="timeline">{action['timeline']}</span>
                    </div>
                    <h4>{action['action']}</h4>
                    <p>{action['rationale']}</p>
                </div>
            """)
        
        return f"""
        <div class="immediate-actions">
            <h3>🚨 Azioni Immediate Necessarie</h3>
            <div class="actions-list">
                {''.join(items)}
            </div>
        </div>
        """
    
    def _generate_strategic_cards(self, recommendations: List[Dict]) -> str:
        """Genera card per raccomandazioni strategiche"""
        
        cards = []
        for rec in recommendations:
            cards.append(f"""
                <div class="recommendation-card">
                    <h4>{rec['title']}</h4>
                    <p>{rec['description']}</p>
                    <div class="rec-meta">
                        <span class="benefit">📊 Beneficio: {rec['benefit']}</span>
                        <span class="effort">💪 Effort: {rec['effort']}</span>
                        <span class="roi">💰 ROI: {rec['roi']}</span>
                    </div>
                </div>
            """)
        
        return ''.join(cards)
    
    def _generate_tools_rows(self, tools: List[Dict]) -> str:
        """Genera righe tabella strumenti"""
        
        rows = []
        for tool_cat in tools:
            tools_list = ', '.join(tool_cat['tools'])
            rows.append(f"""
                <tr>
                    <th scope="row">{tool_cat['category']}</th>
                    <td>{tools_list}</td>
                    <td>{tool_cat['purpose']}</td>
                </tr>
            """)
        
        return ''.join(rows)