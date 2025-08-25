"""Technical Analysis Agent - Analisi tecnica dettagliata delle violazioni"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
from .base_agent import BaseAgent, AgentContext, AgentPriority

logger = logging.getLogger(__name__)


class TechnicalAnalysisAgent(BaseAgent):
    """Agent specializzato nell'analisi tecnica dettagliata"""
    
    def __init__(self, priority: AgentPriority = AgentPriority.HIGH):
        super().__init__(
            name="technical",
            priority=priority,
            timeout=25
        )
        
    def validate_input(self, context: AgentContext) -> bool:
        """Valida presenza dati tecnici necessari"""
        if not context.scan_data:
            self.logger.error("Missing scan_data")
            return False
            
        if 'all_violations' not in context.scan_data:
            self.logger.error("Missing violations data")
            return False
            
        return True
    
    async def generate_section(self, context: AgentContext) -> str:
        """Genera analisi tecnica dettagliata"""
        
        violations = context.scan_data.get('all_violations', [])
        
        if not violations:
            return self._generate_no_issues_section()
        
        # Analisi approfondita
        categorized = self._categorize_violations(violations)
        patterns = self._identify_patterns(violations)
        wcag_analysis = self._analyze_wcag_compliance(violations)
        technical_debt = self._calculate_technical_debt(categorized, patterns)
        root_causes = self._identify_root_causes(patterns, categorized)
        
        return self._compose_technical_section(
            context,
            categorized,
            patterns,
            wcag_analysis,
            technical_debt,
            root_causes
        )
    
    def _categorize_violations(self, violations: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorizza violazioni per area tecnica"""
        categories = defaultdict(list)
        
        for violation in violations:
            category = self._determine_category(violation)
            categories[category].append(violation)
        
        return dict(categories)
    
    def _determine_category(self, violation: Dict) -> str:
        """Determina categoria tecnica di una violazione"""
        code = violation.get('code', '').lower()
        message = violation.get('message', '').lower()
        wcag = violation.get('wcag_criteria', '').lower()
        
        # Categorizzazione basata su pattern
        if any(x in code + message for x in ['alt', 'img', 'image', 'graphic']):
            return 'images_media'
        elif any(x in code + message for x in ['heading', 'h1', 'h2', 'h3', 'structure', 'landmark']):
            return 'structure_semantics'
        elif any(x in code + message for x in ['contrast', 'color', 'visible']):
            return 'visual_design'
        elif any(x in code + message for x in ['keyboard', 'focus', 'tab']):
            return 'keyboard_navigation'
        elif any(x in code + message for x in ['aria', 'role', 'state', 'property']):
            return 'aria_attributes'
        elif any(x in code + message for x in ['form', 'input', 'label', 'field']):
            return 'forms_inputs'
        elif any(x in code + message for x in ['link', 'button', 'click']):
            return 'interactive_elements'
        elif any(x in code + message for x in ['lang', 'language', 'i18n']):
            return 'language_i18n'
        else:
            return 'other_technical'
    
    def _identify_patterns(self, violations: List[Dict]) -> Dict[str, Any]:
        """Identifica pattern ricorrenti nei problemi"""
        patterns = {
            'systematic_issues': [],
            'localized_issues': [],
            'widespread_issues': [],
            'component_specific': defaultdict(list)
        }
        
        # Analizza selettori per pattern
        selector_counts = defaultdict(int)
        component_issues = defaultdict(list)
        
        for violation in violations:
            selector = violation.get('selector', '')
            
            # Conta occorrenze selettori simili
            base_selector = self._extract_base_selector(selector)
            selector_counts[base_selector] += 1
            
            # Raggruppa per componente
            component = self._extract_component_name(selector)
            if component:
                component_issues[component].append(violation)
        
        # Classifica pattern
        for selector, count in selector_counts.items():
            if count > 10:
                patterns['widespread_issues'].append({
                    'selector': selector,
                    'count': count,
                    'type': 'widespread'
                })
            elif count > 5:
                patterns['systematic_issues'].append({
                    'selector': selector,
                    'count': count,
                    'type': 'systematic'
                })
            elif count == 1:
                patterns['localized_issues'].append({
                    'selector': selector,
                    'count': count,
                    'type': 'localized'
                })
        
        patterns['component_specific'] = dict(component_issues)
        
        return patterns
    
    def _analyze_wcag_compliance(self, violations: List[Dict]) -> Dict[str, Any]:
        """Analizza conformità WCAG dettagliata"""
        wcag_analysis = {
            'by_level': {'A': [], 'AA': [], 'AAA': []},
            'by_principle': {
                'perceivable': [],
                'operable': [],
                'understandable': [],
                'robust': []
            },
            'by_guideline': defaultdict(list),
            'missing_criteria': [],
            'most_violated': []
        }
        
        criteria_counts = defaultdict(int)
        
        for violation in violations:
            wcag = violation.get('wcag_criteria', '')
            if wcag:
                # Determina livello (A, AA, AAA)
                level = self._get_wcag_level(wcag)
                if level:
                    wcag_analysis['by_level'][level].append(violation)
                
                # Determina principio
                principle = self._get_wcag_principle(wcag)
                if principle:
                    wcag_analysis['by_principle'][principle].append(violation)
                
                # Raggruppa per guideline
                guideline = self._get_wcag_guideline(wcag)
                wcag_analysis['by_guideline'][guideline].append(violation)
                
                criteria_counts[wcag] += 1
            else:
                wcag_analysis['missing_criteria'].append(violation)
        
        # Identifica criteri più violati
        wcag_analysis['most_violated'] = sorted(
            criteria_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return wcag_analysis
    
    def _calculate_technical_debt(self, 
                                 categorized: Dict[str, List],
                                 patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Calcola debito tecnico stimato"""
        
        # Stima ore per categoria (basata su esperienza reale)
        hours_per_category = {
            'images_media': 0.25,  # 15 min per immagine
            'structure_semantics': 0.5,  # 30 min per problema strutturale
            'visual_design': 0.75,  # 45 min per problema contrasto
            'keyboard_navigation': 1.0,  # 1 ora per problema navigazione
            'aria_attributes': 0.5,  # 30 min per attributo ARIA
            'forms_inputs': 0.75,  # 45 min per campo form
            'interactive_elements': 0.5,  # 30 min per elemento
            'language_i18n': 1.5,  # 1.5 ore per problema i18n
            'other_technical': 0.5  # 30 min default
        }
        
        total_hours = 0
        category_hours = {}
        
        for category, violations in categorized.items():
            hours = len(violations) * hours_per_category.get(category, 0.5)
            category_hours[category] = hours
            total_hours += hours
        
        # Aggiungi overhead per pattern sistemici
        if patterns['systematic_issues']:
            total_hours *= 1.3  # +30% per problemi sistemici
        if patterns['widespread_issues']:
            total_hours *= 1.5  # +50% per problemi diffusi
        
        # Calcola costi stimati (100€/ora sviluppatore senior)
        hourly_rate = 100
        total_cost = total_hours * hourly_rate
        
        return {
            'total_hours': round(total_hours, 1),
            'total_cost_eur': round(total_cost, 0),
            'category_breakdown': category_hours,
            'complexity_multiplier': 1.3 if patterns['systematic_issues'] else 1.0,
            'estimated_days': round(total_hours / 8, 1),
            'team_size_recommended': 1 if total_hours < 40 else 2 if total_hours < 160 else 3
        }
    
    def _identify_root_causes(self, 
                             patterns: Dict[str, Any],
                             categorized: Dict[str, List]) -> List[Dict[str, Any]]:
        """Identifica cause root dei problemi"""
        root_causes = []
        
        # Analizza pattern per cause comuni
        if len(patterns['systematic_issues']) > 5:
            root_causes.append({
                'cause': 'Mancanza di standard di sviluppo accessibili',
                'evidence': f"{len(patterns['systematic_issues'])} problemi sistematici ricorrenti",
                'impact': 'high',
                'solution': 'Implementare design system accessibile e code review'
            })
        
        if 'images_media' in categorized and len(categorized['images_media']) > 10:
            root_causes.append({
                'cause': 'Processo editoriale non include accessibilità',
                'evidence': f"{len(categorized['images_media'])} immagini senza alt text",
                'impact': 'medium',
                'solution': 'Formazione team content e CMS con validazione automatica'
            })
        
        if 'forms_inputs' in categorized and len(categorized['forms_inputs']) > 5:
            root_causes.append({
                'cause': 'Framework form non accessibile by default',
                'evidence': f"{len(categorized['forms_inputs'])} problemi nei form",
                'impact': 'high',
                'solution': 'Adottare libreria form accessibile (es. react-hook-form con a11y)'
            })
        
        if 'visual_design' in categorized and len(categorized['visual_design']) > 5:
            root_causes.append({
                'cause': 'Design system non validato per contrasto',
                'evidence': f"{len(categorized['visual_design'])} problemi di contrasto",
                'impact': 'medium',
                'solution': 'Audit design tokens e implementazione tema accessibile'
            })
        
        if patterns['component_specific']:
            components_with_issues = len(patterns['component_specific'])
            if components_with_issues > 3:
                root_causes.append({
                    'cause': 'Componenti UI non testati per accessibilità',
                    'evidence': f"{components_with_issues} componenti con problemi",
                    'impact': 'high',
                    'solution': 'Implementare test automatici accessibilità (jest-axe, cypress-axe)'
                })
        
        return root_causes
    
    def _compose_technical_section(self,
                                  context: AgentContext,
                                  categorized: Dict[str, List],
                                  patterns: Dict[str, Any],
                                  wcag_analysis: Dict[str, Any],
                                  technical_debt: Dict[str, Any],
                                  root_causes: List[Dict]) -> str:
        """Compone sezione tecnica completa"""
        
        total_violations = sum(len(v) for v in categorized.values())
        
        html = f"""
        <section class="technical-analysis">
            <h2>Analisi Tecnica Dettagliata</h2>
            
            <div class="technical-summary">
                <h3>Riepilogo Tecnico</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-label">Violazioni Totali</span>
                        <span class="stat-value">{total_violations}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Categorie Impattate</span>
                        <span class="stat-value">{len(categorized)}</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Debito Tecnico</span>
                        <span class="stat-value">{technical_debt['total_hours']:.1f}h</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-label">Costo Stimato</span>
                        <span class="stat-value">€{technical_debt['total_cost_eur']:,.0f}</span>
                    </div>
                </div>
            </div>
            
            <div class="violations-by-category">
                <h3>Distribuzione Problemi per Area Tecnica</h3>
                <table class="category-table">
                    <thead>
                        <tr>
                            <th scope="col">Area Tecnica</th>
                            <th scope="col">N° Problemi</th>
                            <th scope="col">% del Totale</th>
                            <th scope="col">Effort Stimato</th>
                            <th scope="col">Criticità</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Ordina categorie per numero di problemi
        sorted_categories = sorted(
            categorized.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for category, violations in sorted_categories:
            percentage = (len(violations) / total_violations) * 100
            hours = technical_debt['category_breakdown'].get(category, 0)
            criticality = self._get_category_criticality(category, len(violations))
            criticality_class = self._get_criticality_class(criticality)
            
            html += f"""
                        <tr>
                            <th scope="row">{self._translate_category(category)}</th>
                            <td>{len(violations)}</td>
                            <td>{percentage:.1f}%</td>
                            <td>{hours:.1f}h</td>
                            <td class="{criticality_class}">{criticality}</td>
                        </tr>
            """
        
        html += """
                    </tbody>
                </table>
            </div>
            
            <div class="pattern-analysis">
                <h3>Pattern e Problemi Ricorrenti</h3>
        """
        
        if patterns['systematic_issues']:
            html += f"""
                <div class="pattern-card systematic">
                    <h4>Problemi Sistematici ({len(patterns['systematic_issues'])})</h4>
                    <p>Problemi che si ripetono in modo consistente attraverso il sito, 
                    indicando mancanza di standard o processi.</p>
                    <ul>
        """
            for issue in patterns['systematic_issues'][:3]:
                html += f"<li>Pattern: <code>{issue['selector'][:50]}...</code> ({issue['count']} occorrenze)</li>"
            html += "</ul></div>"
        
        if patterns['widespread_issues']:
            html += f"""
                <div class="pattern-card widespread">
                    <h4>Problemi Diffusi ({len(patterns['widespread_issues'])})</h4>
                    <p>Problemi presenti in molte aree del sito, richiedono intervento globale.</p>
                    <ul>
        """
            for issue in patterns['widespread_issues'][:3]:
                html += f"<li>Pattern: <code>{issue['selector'][:50]}...</code> ({issue['count']} occorrenze)</li>"
            html += "</ul></div>"
        
        html += """
            </div>
            
            <div class="wcag-compliance-analysis">
                <h3>Analisi Conformità WCAG 2.1</h3>
                
                <div class="wcag-by-level">
                    <h4>Violazioni per Livello WCAG</h4>
                    <table class="wcag-level-table">
                        <thead>
                            <tr>
                                <th scope="col">Livello</th>
                                <th scope="col">Violazioni</th>
                                <th scope="col">Stato</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th scope="row">Livello A</th>
                                <td>{len(wcag_analysis['by_level']['A'])}</td>
                                <td class="{self._get_wcag_status_class(len(wcag_analysis['by_level']['A']))}">
                                    {self._get_wcag_status(len(wcag_analysis['by_level']['A']))}
                                </td>
                            </tr>
                            <tr>
                                <th scope="row">Livello AA</th>
                                <td>{len(wcag_analysis['by_level']['AA'])}</td>
                                <td class="{self._get_wcag_status_class(len(wcag_analysis['by_level']['AA']))}">
                                    {self._get_wcag_status(len(wcag_analysis['by_level']['AA']))}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="wcag-most-violated">
                    <h4>Criteri WCAG Più Violati</h4>
                    <ol>
        """
        
        for criteria, count in wcag_analysis['most_violated'][:5]:
            html += f"""
                        <li>
                            <strong>{criteria}</strong> - {count} violazioni
                            <br><em>{self._get_wcag_description(criteria)}</em>
                        </li>
            """
        
        html += """
                    </ol>
                </div>
            </div>
            
            <div class="root-cause-analysis">
                <h3>Analisi delle Cause Root</h3>
                <p>Identificazione delle cause sistemiche dei problemi di accessibilità:</p>
                
                <div class="root-causes-list">
        """
        
        for i, cause in enumerate(root_causes, 1):
            impact_class = self._get_impact_class(cause['impact'])
            html += f"""
                    <div class="root-cause-card">
                        <div class="cause-header">
                            <span class="cause-number">{i}</span>
                            <span class="cause-impact {impact_class}">{cause['impact'].upper()}</span>
                        </div>
                        <h4>{cause['cause']}</h4>
                        <p class="cause-evidence">📊 {cause['evidence']}</p>
                        <p class="cause-solution">💡 <strong>Soluzione:</strong> {cause['solution']}</p>
                    </div>
            """
        
        html += f"""
                </div>
            </div>
            
            <div class="technical-debt-estimation">
                <h3>Stima Debito Tecnico</h3>
                <div class="debt-summary">
                    <p><strong>Effort Totale Stimato:</strong> {technical_debt['total_hours']:.1f} ore 
                    ({technical_debt['estimated_days']:.1f} giorni lavorativi)</p>
                    <p><strong>Team Consigliato:</strong> {technical_debt['team_size_recommended']} 
                    sviluppatori senior</p>
                    <p><strong>Costo Stimato:</strong> €{technical_debt['total_cost_eur']:,.0f} 
                    (tariffa €100/ora)</p>
                    
                    {self._generate_debt_warning(technical_debt)}
                </div>
            </div>
        </section>
        """
        
        return html
    
    def _generate_no_issues_section(self) -> str:
        """Genera sezione quando non ci sono problemi"""
        return """
        <section class="technical-analysis">
            <h2>Analisi Tecnica</h2>
            <div class="no-issues-found">
                <p>✅ <strong>Nessun problema tecnico rilevato</strong></p>
                <p>L'analisi automatica non ha identificato violazioni di accessibilità. 
                Si raccomanda comunque una verifica manuale per confermare la piena conformità.</p>
            </div>
        </section>
        """
    
    def _extract_base_selector(self, selector: str) -> str:
        """Estrae selettore base rimuovendo indici e dettagli"""
        import re
        # Rimuove indici numerici e pseudo-classi
        base = re.sub(r'\[\d+\]', '', selector)
        base = re.sub(r':\w+', '', base)
        base = re.sub(r'\s+', ' ', base)
        return base.strip()
    
    def _extract_component_name(self, selector: str) -> Optional[str]:
        """Estrae nome componente dal selettore"""
        # Cerca pattern comuni di componenti
        if 'header' in selector.lower():
            return 'Header'
        elif 'footer' in selector.lower():
            return 'Footer'
        elif 'nav' in selector.lower():
            return 'Navigation'
        elif 'form' in selector.lower():
            return 'Form'
        elif 'modal' in selector.lower():
            return 'Modal'
        elif 'card' in selector.lower():
            return 'Card'
        elif 'button' in selector.lower():
            return 'Button'
        return None
    
    def _get_wcag_level(self, criteria: str) -> Optional[str]:
        """Determina livello WCAG da criterio"""
        # Mappatura semplificata - in produzione usare database completo
        if '1.1.1' in criteria or '2.1.1' in criteria or '3.3.2' in criteria or '4.1.2' in criteria:
            return 'A'
        elif '1.4.3' in criteria or '1.4.5' in criteria or '2.4.7' in criteria:
            return 'AA'
        elif '1.4.6' in criteria or '2.1.3' in criteria:
            return 'AAA'
        return 'AA'  # Default
    
    def _get_wcag_principle(self, criteria: str) -> Optional[str]:
        """Determina principio WCAG da criterio"""
        if criteria.startswith('1.'):
            return 'perceivable'
        elif criteria.startswith('2.'):
            return 'operable'
        elif criteria.startswith('3.'):
            return 'understandable'
        elif criteria.startswith('4.'):
            return 'robust'
        return None
    
    def _get_wcag_guideline(self, criteria: str) -> str:
        """Estrae guideline WCAG da criterio"""
        parts = criteria.split('.')
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return criteria
    
    def _get_wcag_description(self, criteria: str) -> str:
        """Ottiene descrizione criterio WCAG"""
        descriptions = {
            '1.1.1': 'Contenuti non testuali',
            '1.3.1': 'Informazioni e relazioni',
            '1.4.3': 'Contrasto minimo',
            '2.1.1': 'Tastiera',
            '2.4.1': 'Salto di blocchi',
            '3.3.2': 'Etichette o istruzioni',
            '4.1.2': 'Nome, ruolo, valore'
        }
        return descriptions.get(criteria, 'Criterio WCAG')
    
    def _translate_category(self, category: str) -> str:
        """Traduce categoria in italiano"""
        translations = {
            'images_media': 'Immagini e Media',
            'structure_semantics': 'Struttura e Semantica',
            'visual_design': 'Design Visivo',
            'keyboard_navigation': 'Navigazione Tastiera',
            'aria_attributes': 'Attributi ARIA',
            'forms_inputs': 'Form e Input',
            'interactive_elements': 'Elementi Interattivi',
            'language_i18n': 'Lingua e Localizzazione',
            'other_technical': 'Altri Problemi Tecnici'
        }
        return translations.get(category, category)
    
    def _get_category_criticality(self, category: str, count: int) -> str:
        """Determina criticità di una categoria"""
        critical_categories = ['keyboard_navigation', 'forms_inputs', 'structure_semantics']
        
        if category in critical_categories and count > 5:
            return 'Critica'
        elif count > 10:
            return 'Alta'
        elif count > 5:
            return 'Media'
        else:
            return 'Bassa'
    
    def _get_criticality_class(self, criticality: str) -> str:
        """Classe CSS per criticità"""
        return f"criticality-{criticality.lower()}"
    
    def _get_wcag_status(self, violations: int) -> str:
        """Determina stato WCAG"""
        if violations == 0:
            return 'Conforme'
        elif violations <= 5:
            return 'Parzialmente Conforme'
        else:
            return 'Non Conforme'
    
    def _get_wcag_status_class(self, violations: int) -> str:
        """Classe CSS per stato WCAG"""
        if violations == 0:
            return 'status-compliant'
        elif violations <= 5:
            return 'status-partial'
        else:
            return 'status-non-compliant'
    
    def _get_impact_class(self, impact: str) -> str:
        """Classe CSS per impatto"""
        return f"impact-{impact.lower()}"
    
    def _generate_debt_warning(self, technical_debt: Dict) -> str:
        """Genera warning per debito tecnico elevato"""
        if technical_debt['total_hours'] > 160:
            return """
                <div class="debt-warning">
                    <strong>⚠️ Attenzione:</strong> Il debito tecnico stimato è significativo. 
                    Si consiglia di pianificare l'intervento in fasi incrementali con priorità 
                    sui problemi critici per l'utente.
                </div>
            """
        return ""