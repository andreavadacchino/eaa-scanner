"""Remediation Planner Agent - Piano di correzione prioritizzato"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_agent import BaseAgent, AgentContext, AgentPriority

logger = logging.getLogger(__name__)


class RemediationPlannerAgent(BaseAgent):
    """Agent specializzato nella pianificazione remediation"""
    
    def __init__(self, priority: AgentPriority = AgentPriority.NORMAL):
        super().__init__(
            name="remediation",
            priority=priority,  
            timeout=20
        )
    
    def validate_input(self, context: AgentContext) -> bool:
        return 'all_violations' in context.scan_data
    
    async def generate_section(self, context: AgentContext) -> str:
        """Genera piano di remediation prioritizzato"""
        
        violations = context.scan_data.get('all_violations', [])
        
        if not violations:
            return self._generate_no_issues_plan()
        
        # Categorizza e prioritizza
        categorized = self._categorize_by_priority(violations)
        timeline = self._create_timeline(categorized)
        effort_estimation = self._estimate_effort(categorized)
        quick_wins = self._identify_quick_wins(violations)
        
        return self._compose_remediation_plan(
            context,
            categorized,
            timeline,
            effort_estimation,
            quick_wins
        )
    
    def _categorize_by_priority(self, violations: List[Dict]) -> Dict[str, List]:
        """Categorizza violazioni per priorità"""
        
        categories = {
            'immediate': [],  # Critiche - 30 giorni
            'high': [],      # Alta - 60 giorni  
            'medium': [],    # Media - 90 giorni
            'low': []        # Bassa - 180 giorni
        }
        
        for violation in violations:
            severity = violation.get('severity', 'moderate')
            wcag = violation.get('wcag_criteria', '')
            
            # Priorità basata su severità e impatto
            if severity in ['critical', 'serious'] or '1.1.1' in wcag or '2.1.1' in wcag:
                categories['immediate'].append(violation)
            elif severity == 'high' or '1.4.3' in wcag or '3.3.2' in wcag:
                categories['high'].append(violation)
            elif severity in ['moderate', 'medium']:
                categories['medium'].append(violation)
            else:
                categories['low'].append(violation)
        
        return categories
    
    def _create_timeline(self, categorized: Dict[str, List]) -> List[Dict]:
        """Crea timeline di intervento"""
        
        now = datetime.now()
        timeline = []
        
        if categorized['immediate']:
            timeline.append({
                'phase': 'Fase 1 - Intervento Immediato',
                'deadline': (now + timedelta(days=30)).strftime('%d/%m/%Y'),
                'issues_count': len(categorized['immediate']),
                'priority': 'Critica',
                'description': 'Problemi che bloccano completamente l\'accesso'
            })
        
        if categorized['high']:
            timeline.append({
                'phase': 'Fase 2 - Priorità Alta',
                'deadline': (now + timedelta(days=60)).strftime('%d/%m/%Y'),
                'issues_count': len(categorized['high']),
                'priority': 'Alta',
                'description': 'Problemi che limitano significativamente l\'accesso'
            })
        
        if categorized['medium']:
            timeline.append({
                'phase': 'Fase 3 - Priorità Media',
                'deadline': (now + timedelta(days=90)).strftime('%d/%m/%Y'),
                'issues_count': len(categorized['medium']),
                'priority': 'Media',
                'description': 'Problemi che creano difficoltà moderate'
            })
        
        if categorized['low']:
            timeline.append({
                'phase': 'Fase 4 - Ottimizzazioni',
                'deadline': (now + timedelta(days=180)).strftime('%d/%m/%Y'),
                'issues_count': len(categorized['low']),
                'priority': 'Bassa',
                'description': 'Miglioramenti per esperienza ottimale'
            })
        
        return timeline
    
    def _estimate_effort(self, categorized: Dict[str, List]) -> Dict[str, Any]:
        """Stima effort richiesto"""
        
        # Ore stimate per categoria (basate su esperienza reale)
        hours_per_issue = {
            'immediate': 2.0,  # Problemi critici richiedono più test
            'high': 1.0,
            'medium': 0.5,
            'low': 0.25
        }
        
        total_hours = 0
        for priority, issues in categorized.items():
            total_hours += len(issues) * hours_per_issue[priority]
        
        # Aggiungi overhead per test e QA (30%)
        total_hours *= 1.3
        
        return {
            'total_hours': round(total_hours, 1),
            'total_days': round(total_hours / 8, 1),
            'team_size': 1 if total_hours < 80 else 2 if total_hours < 240 else 3,
            'estimated_cost': round(total_hours * 100, 0),  # 100€/ora
            'complexity': 'Bassa' if total_hours < 40 else 'Media' if total_hours < 160 else 'Alta'
        }
    
    def _identify_quick_wins(self, violations: List[Dict]) -> List[Dict]:
        """Identifica quick wins - correzioni facili con alto impatto"""
        
        quick_wins = []
        
        # Pattern di quick wins comuni
        patterns = {
            'alt': 'Aggiungere testi alternativi alle immagini',
            'label': 'Aggiungere etichette ai campi form',
            'heading': 'Correggere struttura heading',
            'lang': 'Specificare lingua della pagina',
            'title': 'Aggiungere titoli descrittivi'
        }
        
        seen_patterns = set()
        
        for violation in violations[:50]:  # Analizza prime 50 violazioni
            code = violation.get('code', '').lower()
            
            for pattern, description in patterns.items():
                if pattern in code and pattern not in seen_patterns:
                    quick_wins.append({
                        'action': description,
                        'impact': 'Alto',
                        'effort': 'Basso',
                        'time': '1-2 ore'
                    })
                    seen_patterns.add(pattern)
        
        return quick_wins[:5]  # Max 5 quick wins
    
    def _compose_remediation_plan(self,
                                 context: AgentContext,
                                 categorized: Dict[str, List],
                                 timeline: List[Dict],
                                 effort: Dict[str, Any],
                                 quick_wins: List[Dict]) -> str:
        """Compone piano remediation HTML"""
        
        total_issues = sum(len(issues) for issues in categorized.values())
        
        return f"""
        <section class="remediation-plan">
            <h2>Piano di Remediation</h2>
            
            <div class="plan-summary">
                <h3>Riepilogo Piano</h3>
                <div class="summary-grid">
                    <div class="metric">
                        <span class="label">Problemi Totali</span>
                        <span class="value">{total_issues}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Effort Stimato</span>
                        <span class="value">{effort['total_hours']} ore</span>
                    </div>
                    <div class="metric">
                        <span class="label">Team Consigliato</span>
                        <span class="value">{effort['team_size']} persone</span>
                    </div>
                    <div class="metric">
                        <span class="label">Costo Stimato</span>
                        <span class="value">€{effort['estimated_cost']:,.0f}</span>
                    </div>
                </div>
            </div>
            
            {self._generate_quick_wins_section(quick_wins) if quick_wins else ''}
            
            <div class="timeline">
                <h3>Timeline di Intervento</h3>
                <table>
                    <thead>
                        <tr>
                            <th scope="col">Fase</th>
                            <th scope="col">Deadline</th>
                            <th scope="col">N° Problemi</th>
                            <th scope="col">Priorità</th>
                            <th scope="col">Descrizione</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(self._generate_timeline_row(phase) for phase in timeline)}
                    </tbody>
                </table>
            </div>
            
            <div class="detailed-actions">
                <h3>Azioni Dettagliate per Priorità</h3>
                
                {self._generate_priority_section('Critiche', categorized['immediate'])}
                {self._generate_priority_section('Alta', categorized['high'])}
                {self._generate_priority_section('Media', categorized['medium'])}
                {self._generate_priority_section('Bassa', categorized['low'])}
            </div>
            
            <div class="implementation-notes">
                <h3>Note di Implementazione</h3>
                <ul>
                    <li><strong>Test Continui:</strong> Verificare ogni correzione con screen reader</li>
                    <li><strong>Documentazione:</strong> Documentare tutte le modifiche apportate</li>
                    <li><strong>Formazione:</strong> Formare il team durante l'implementazione</li>
                    <li><strong>Monitoraggio:</strong> Implementare scansioni automatiche periodiche</li>
                    <li><strong>Validazione:</strong> Test con utenti reali prima del rilascio</li>
                </ul>
            </div>
        </section>
        """
    
    def _generate_quick_wins_section(self, quick_wins: List[Dict]) -> str:
        """Genera sezione quick wins"""
        
        if not quick_wins:
            return ''
        
        rows = ''.join([
            f"""
            <tr>
                <td>{qw['action']}</td>
                <td>{qw['impact']}</td>
                <td>{qw['effort']}</td>
                <td>{qw['time']}</td>
            </tr>
            """
            for qw in quick_wins
        ])
        
        return f"""
        <div class="quick-wins">
            <h3>🎯 Quick Wins - Correzioni Rapide ad Alto Impatto</h3>
            <p>Queste correzioni possono essere implementate rapidamente con risultati significativi:</p>
            <table>
                <thead>
                    <tr>
                        <th scope="col">Azione</th>
                        <th scope="col">Impatto</th>
                        <th scope="col">Effort</th>
                        <th scope="col">Tempo</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_timeline_row(self, phase: Dict) -> str:
        """Genera riga timeline"""
        
        priority_class = {
            'Critica': 'priority-critical',
            'Alta': 'priority-high',
            'Media': 'priority-medium',
            'Bassa': 'priority-low'
        }.get(phase['priority'], '')
        
        return f"""
        <tr>
            <td>{phase['phase']}</td>
            <td><strong>{phase['deadline']}</strong></td>
            <td>{phase['issues_count']}</td>
            <td class="{priority_class}">{phase['priority']}</td>
            <td>{phase['description']}</td>
        </tr>
        """
    
    def _generate_priority_section(self, priority: str, issues: List[Dict]) -> str:
        """Genera sezione per priorità specifica"""
        
        if not issues:
            return ''
        
        # Raggruppa per tipo
        issue_types = {}
        for issue in issues:
            code = issue.get('code', 'unknown')
            if code not in issue_types:
                issue_types[code] = {
                    'count': 0,
                    'message': issue.get('message', ''),
                    'wcag': issue.get('wcag_criteria', '')
                }
            issue_types[code]['count'] += 1
        
        # Genera lista
        items = []
        for code, data in list(issue_types.items())[:10]:  # Max 10 tipi
            items.append(
                f"<li><strong>{data['message'][:100]}...</strong> "
                f"({data['count']} occorrenze, WCAG {data['wcag'] or 'N/A'})</li>"
            )
        
        return f"""
        <div class="priority-section priority-{priority.lower()}">
            <h4>Priorità {priority} ({len(issues)} problemi)</h4>
            <ul>
                {''.join(items)}
            </ul>
        </div>
        """
    
    def _generate_no_issues_plan(self) -> str:
        """Piano quando non ci sono problemi"""
        return """
        <section class="remediation-plan">
            <h2>Piano di Remediation</h2>
            <div class="no-issues">
                <p>✅ <strong>Nessun problema rilevato</strong></p>
                <p>L'analisi automatica non ha identificato problemi di accessibilità.</p>
                <h3>Raccomandazioni per il Mantenimento:</h3>
                <ul>
                    <li>Continuare il monitoraggio periodico</li>
                    <li>Testare nuove funzionalità prima del rilascio</li>
                    <li>Mantenere la formazione del team aggiornata</li>
                    <li>Verificare con utenti reali periodicamente</li>
                </ul>
            </div>
        </section>
        """