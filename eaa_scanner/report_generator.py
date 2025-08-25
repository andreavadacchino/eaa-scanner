"""Professional HTML Report Generator for EAA Scanner

Generates minimal, professional HTML reports for accessibility compliance.
Based on established workflow with improvements.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import html

from .models import AggregatedResults, ComplianceMetrics

logger = logging.getLogger(__name__)


class ProfessionalReportGenerator:
    """Generatore di report HTML professionale per conformità accessibilità."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def generate_report(self, 
                       aggregated_results: AggregatedResults,
                       company_name: str,
                       url: str,
                       email: Optional[str] = None,
                       country: str = "Italia") -> str:
        """Genera report HTML professionale basato sui risultati aggregati.
        
        Args:
            aggregated_results: Risultati aggregati dell'analisi
            company_name: Nome dell'azienda
            url: URL analizzato
            email: Email di contatto (opzionale)
            country: Paese per applicazione normativa
            
        Returns:
            HTML string del report completo
        """
        
        # Prepara i dati per il template
        context = self._prepare_context(
            aggregated_results, 
            company_name, 
            url, 
            email, 
            country
        )
        
        # Genera il contenuto principale
        content = self._generate_content(context)
        
        # Inserisce nel template HTML
        html_report = self._apply_template(content, context)
        
        return html_report
    
    def _prepare_context(self, 
                        results: AggregatedResults,
                        company_name: str,
                        url: str,
                        email: Optional[str],
                        country: str) -> Dict[str, Any]:
        """Prepara il contesto dei dati per il template."""
        
        # Calcola totali coerenti
        error_total = len([v for v in results.all_violations if v.severity in ['critical', 'serious']])
        warning_total = len([v for v in results.all_violations if v.severity in ['moderate', 'minor']])
        
        # Determina stato conformità
        compliance_status = self._determine_compliance_status(
            results.compliance,
            error_total,
            warning_total
        )
        
        # Raggruppa problematiche per categoria
        categories = self._group_by_category(results.all_violations)
        
        # Prepara piano remediation
        remediation_plan = self._create_remediation_plan(categories)
        
        return {
            'company_name': company_name,
            'url': url,
            'email': email or '—',
            'country': country,
            'scan_date': datetime.now().strftime('%d/%m/%Y'),
            'error_total': error_total,
            'warning_total': warning_total,
            'compliance_status': compliance_status,
            'overall_score': results.compliance.overall_score,
            'categories': categories,
            'remediation_plan': remediation_plan,
            'violations': results.all_violations[:50],  # Limita a 50 per leggibilità
            'compliance': results.compliance
        }
    
    def _determine_compliance_status(self,
                                    compliance: ComplianceMetrics,
                                    error_total: int,
                                    warning_total: int) -> str:
        """Determina lo stato di conformità."""
        
        if compliance.compliance_level:
            if compliance.compliance_level == 'compliant':
                return 'Conforme'
            elif compliance.compliance_level == 'partially_compliant':
                return 'Parzialmente conforme'
            else:
                return 'Non conforme'
        
        # Fallback basato su errori
        if error_total == 0 and warning_total == 0:
            return 'Conforme'
        elif error_total > 10 or compliance.overall_score < 60:
            return 'Non conforme'
        else:
            return 'Parzialmente conforme'
    
    def _group_by_category(self, violations: List) -> Dict[str, Dict]:
        """Raggruppa violazioni per categoria."""
        
        categories = {
            'testi_alternativi': {
                'label': 'Testi alternativi mancanti',
                'wcag': '1.1.1',
                'violations': [],
                'priority': 'high'
            },
            'etichette_form': {
                'label': 'Etichette modulo mancanti',
                'wcag': '3.3.2',
                'violations': [],
                'priority': 'high'
            },
            'contrasto': {
                'label': 'Contrasto colore insufficiente',
                'wcag': '1.4.3',
                'violations': [],
                'priority': 'medium'
            },
            'struttura': {
                'label': 'Struttura non semantica',
                'wcag': '1.3.1',
                'violations': [],
                'priority': 'medium'
            },
            'aria': {
                'label': 'Problemi ARIA',
                'wcag': '4.1.2',
                'violations': [],
                'priority': 'low'
            },
            'altri': {
                'label': 'Altri problemi',
                'wcag': 'Vari',
                'violations': [],
                'priority': 'low'
            }
        }
        
        # Categorizza violazioni
        for violation in violations:
            category = self._categorize_violation(violation)
            if category in categories:
                categories[category]['violations'].append(violation)
            else:
                categories['altri']['violations'].append(violation)
        
        # Rimuove categorie vuote
        return {k: v for k, v in categories.items() if v['violations']}
    
    def _categorize_violation(self, violation) -> str:
        """Categorizza una violazione."""
        
        code = violation.code.lower()
        wcag = violation.wcag_criteria.lower() if violation.wcag_criteria else ''
        
        if 'alt' in code or 'image' in code or '1.1.1' in wcag:
            return 'testi_alternativi'
        elif 'label' in code or 'form' in code or 'input' in code or '3.3' in wcag:
            return 'etichette_form'
        elif 'contrast' in code or 'color' in code or '1.4.3' in wcag:
            return 'contrasto'
        elif 'heading' in code or 'structure' in code or 'semantic' in code or '1.3' in wcag:
            return 'struttura'
        elif 'aria' in code or 'role' in code or '4.1' in wcag:
            return 'aria'
        else:
            return 'altri'
    
    def _create_remediation_plan(self, categories: Dict) -> List[Dict]:
        """Crea piano di remediation prioritizzato."""
        
        plan = []
        priority_map = {
            'high': {'days': 30, 'label': 'Alta'},
            'medium': {'days': 90, 'label': 'Media'},
            'low': {'days': 180, 'label': 'Bassa'}
        }
        
        for cat_key, cat_data in categories.items():
            priority = cat_data['priority']
            plan.append({
                'categoria': cat_data['label'],
                'violazioni': len(cat_data['violations']),
                'priorita': priority_map[priority]['label'],
                'deadline': f"{priority_map[priority]['days']} giorni",
                'wcag': cat_data['wcag']
            })
        
        # Ordina per priorità
        priority_order = {'Alta': 0, 'Media': 1, 'Bassa': 2}
        plan.sort(key=lambda x: priority_order[x['priorita']])
        
        return plan
    
    def _generate_content(self, context: Dict[str, Any]) -> str:
        """Genera il contenuto HTML del report."""
        
        sections = []
        
        # 1. Header e introduzione
        sections.append(self._generate_header(context))
        
        # 2. Metadati
        sections.append(self._generate_metadata(context))
        
        # 3. Sintesi esecutiva
        sections.append(self._generate_executive_summary(context))
        
        # 4. Contesto e ambito
        sections.append(self._generate_context_section(context))
        
        # 5. Quadro normativo
        sections.append(self._generate_regulatory_framework())
        
        # 6. Metodologia
        sections.append(self._generate_methodology())
        
        # 7. Stato di conformità
        sections.append(self._generate_compliance_status(context))
        
        # 8. Sintesi livello conformità
        sections.append(self._generate_compliance_summary(context))
        
        # 9. Analisi per categoria
        sections.append(self._generate_category_analysis(context))
        
        # 10. Piano di remediation
        sections.append(self._generate_remediation_table(context))
        
        # 11. Elenco dettagliato problemi (limitato)
        sections.append(self._generate_detailed_issues(context))
        
        # 12. Note metodologiche
        sections.append(self._generate_methodology_notes())
        
        # 13. Contatti e supporto
        sections.append(self._generate_contacts(context))
        
        return '\n'.join(sections)
    
    def _generate_header(self, context: Dict) -> str:
        """Genera header del report."""
        return f"""
        <header>
            <h1>Relazione di Conformità all'Accessibilità</h1>
            <p><strong>{context['company_name']}</strong></p>
            <p>{context['url']}</p>
            <p>Data analisi: {context['scan_date']}</p>
        </header>
        """
    
    def _generate_metadata(self, context: Dict) -> str:
        """Genera tabella metadati."""
        return f"""
        <section>
            <h2>Informazioni del Report</h2>
            <table>
                <caption>Dettagli della valutazione di accessibilità</caption>
                <thead>
                    <tr>
                        <th scope="col">Campo</th>
                        <th scope="col">Valore</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th scope="row">Azienda</th>
                        <td>{context['company_name']}</td>
                    </tr>
                    <tr>
                        <th scope="row">Sito web</th>
                        <td><a href="{context['url']}">{context['url']}</a></td>
                    </tr>
                    <tr>
                        <th scope="row">Paese</th>
                        <td>{context['country']}</td>
                    </tr>
                    <tr>
                        <th scope="row">Data valutazione</th>
                        <td>{context['scan_date']}</td>
                    </tr>
                    <tr>
                        <th scope="row">Email contatto</th>
                        <td>{context['email']}</td>
                    </tr>
                    <tr>
                        <th scope="row">Standard di riferimento</th>
                        <td>WCAG 2.1 AA, EN 301 549, EAA</td>
                    </tr>
                </tbody>
            </table>
        </section>
        """
    
    def _generate_executive_summary(self, context: Dict) -> str:
        """Genera sintesi esecutiva."""
        
        # Determina colore stato
        status_class = 'prio-low' if 'Conforme' in context['compliance_status'] else \
                      'prio-medium' if 'Parzialmente' in context['compliance_status'] else 'prio-high'
        
        # Top 3 azioni
        top_actions = []
        for item in context['remediation_plan'][:3]:
            top_actions.append(f"<li>{item['categoria']} ({item['violazioni']} problemi) - Priorità {item['priorita']}</li>")
        
        return f"""
        <section>
            <h2>Sintesi Esecutiva</h2>
            <div class="summary-box">
                <p><strong>Stato di conformità:</strong> <span class="{status_class}">{context['compliance_status']}</span></p>
                <p><strong>Punteggio complessivo:</strong> {context['overall_score']:.1f}/100</p>
                <p><strong>Errori critici:</strong> {context['error_total']}</p>
                <p><strong>Avvisi:</strong> {context['warning_total']}</p>
            </div>
            
            <h3>Azioni prioritarie immediate</h3>
            <ol>
                {''.join(top_actions)}
            </ol>
        </section>
        """
    
    def _generate_context_section(self, context: Dict) -> str:
        """Genera sezione contesto."""
        return f"""
        <section>
            <h2>Contesto e Ambito della Valutazione</h2>
            <p>La presente valutazione di accessibilità è stata condotta sul sito web 
            <strong>{context['url']}</strong> per conto di <strong>{context['company_name']}</strong>.</p>
            
            <p>L'analisi è stata effettuata utilizzando strumenti automatizzati conformi agli standard 
            internazionali e richiede una successiva verifica manuale per una valutazione completa.</p>
            
            <h3>Limitazioni della valutazione automatica</h3>
            <ul>
                <li>Verifica solo aspetti tecnici misurabili automaticamente</li>
                <li>Non valuta la qualità semantica dei contenuti</li>
                <li>Non testa l'esperienza utente con tecnologie assistive reali</li>
                <li>Non verifica contenuti multimediali complessi</li>
            </ul>
        </section>
        """
    
    def _generate_regulatory_framework(self) -> str:
        """Genera quadro normativo."""
        return """
        <section>
            <h2>Quadro Normativo di Riferimento</h2>
            <ul>
                <li><strong>European Accessibility Act (EAA)</strong> - Direttiva (UE) 2019/882</li>
                <li><strong>Web Content Accessibility Guidelines (WCAG) 2.1</strong> - Livello AA</li>
                <li><strong>EN 301 549</strong> - Standard europeo per l'accessibilità ICT</li>
                <li><strong>Linee Guida AgID</strong> - Accessibilità degli strumenti informatici</li>
            </ul>
            
            <p>La conformità a questi standard è obbligatoria per garantire l'accessibilità 
            dei servizi digitali a tutte le persone, incluse quelle con disabilità.</p>
        </section>
        """
    
    def _generate_methodology(self) -> str:
        """Genera sezione metodologia."""
        return f"""
        <section>
            <h2>Metodologia di Valutazione</h2>
            <p>La valutazione è stata condotta utilizzando una combinazione di strumenti automatizzati leader del settore:</p>
            
            <table>
                <caption>Strumenti di analisi utilizzati</caption>
                <thead>
                    <tr>
                        <th scope="col">Strumento</th>
                        <th scope="col">Focus principale</th>
                        <th scope="col">Standard</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th scope="row">WAVE</th>
                        <td>Errori di accessibilità e struttura</td>
                        <td>WCAG 2.1</td>
                    </tr>
                    <tr>
                        <th scope="row">Axe DevTools</th>
                        <td>Conformità tecnica e ARIA</td>
                        <td>WCAG 2.1 AA</td>
                    </tr>
                    <tr>
                        <th scope="row">Lighthouse</th>
                        <td>Performance e best practice</td>
                        <td>WCAG 2.1</td>
                    </tr>
                    <tr>
                        <th scope="row">Pa11y</th>
                        <td>Test automatici di accessibilità</td>
                        <td>WCAG 2.1 AA</td>
                    </tr>
                </tbody>
            </table>
        </section>
        """
    
    def _generate_compliance_status(self, context: Dict) -> str:
        """Genera stato conformità dettagliato."""
        
        status_description = {
            'Conforme': 'Il sito rispetta tutti i criteri di accessibilità verificati automaticamente.',
            'Parzialmente conforme': 'Il sito presenta alcune barriere all\'accessibilità che richiedono interventi correttivi.',
            'Non conforme': 'Il sito presenta gravi problemi di accessibilità che impediscono l\'utilizzo a molti utenti con disabilità.'
        }
        
        description = status_description.get(
            context['compliance_status'], 
            'Stato di conformità da determinare con verifica manuale.'
        )
        
        return f"""
        <section>
            <h2>Stato di Conformità</h2>
            <p><strong>Valutazione: {context['compliance_status']}</strong></p>
            <p>{description}</p>
            
            <div class="warning-box">
                <p><strong>⚠️ Nota importante:</strong> Questa è una valutazione automatizzata che copre 
                circa il 30-40% dei criteri WCAG. Una valutazione completa richiede test manuali, 
                test con utenti reali e verifica con tecnologie assistive.</p>
            </div>
        </section>
        """
    
    def _generate_compliance_summary(self, context: Dict) -> str:
        """Genera tabella sintesi conformità per principio WCAG."""
        
        compliance = context['compliance']
        
        return f"""
        <section>
            <h2>Sintesi del Livello di Conformità</h2>
            <table>
                <caption>Conformità per principio WCAG</caption>
                <thead>
                    <tr>
                        <th scope="col">Principio</th>
                        <th scope="col">Punteggio</th>
                        <th scope="col">Stato</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th scope="row">Percepibile</th>
                        <td>{compliance.by_principle.get('perceivable', 0):.1f}%</td>
                        <td>{self._get_status_label(compliance.by_principle.get('perceivable', 0))}</td>
                    </tr>
                    <tr>
                        <th scope="row">Utilizzabile</th>
                        <td>{compliance.by_principle.get('operable', 0):.1f}%</td>
                        <td>{self._get_status_label(compliance.by_principle.get('operable', 0))}</td>
                    </tr>
                    <tr>
                        <th scope="row">Comprensibile</th>
                        <td>{compliance.by_principle.get('understandable', 0):.1f}%</td>
                        <td>{self._get_status_label(compliance.by_principle.get('understandable', 0))}</td>
                    </tr>
                    <tr>
                        <th scope="row">Robusto</th>
                        <td>{compliance.by_principle.get('robust', 0):.1f}%</td>
                        <td>{self._get_status_label(compliance.by_principle.get('robust', 0))}</td>
                    </tr>
                </tbody>
            </table>
        </section>
        """
    
    def _get_status_label(self, score: float) -> str:
        """Converte punteggio in etichetta stato."""
        if score >= 90:
            return '✅ Buono'
        elif score >= 70:
            return '⚠️ Da migliorare'
        else:
            return '❌ Critico'
    
    def _generate_category_analysis(self, context: Dict) -> str:
        """Genera analisi per categoria."""
        
        sections = ['<section><h2>Analisi Dettagliata per Categoria</h2>']
        
        for cat_key, cat_data in context['categories'].items():
            count = len(cat_data['violations'])
            priority_class = f"prio-{cat_data['priority']}"
            
            # Esempi limitati
            examples = []
            for v in cat_data['violations'][:3]:
                selector = html.escape(v.selector[:80] + '...' if len(v.selector) > 80 else v.selector)
                examples.append(f"<li><code>{selector}</code></li>")
            
            sections.append(f"""
            <article>
                <h3>{cat_data['label']}</h3>
                <p><strong>Problemi trovati:</strong> {count}</p>
                <p><strong>Criterio WCAG:</strong> {cat_data['wcag']}</p>
                <p><strong>Priorità:</strong> <span class="{priority_class}">{cat_data['priority'].title()}</span></p>
                
                <h4>Esempi di elementi interessati:</h4>
                <ul>
                    {''.join(examples)}
                </ul>
                
                <h4>Impatto sugli utenti</h4>
                <p>{self._get_impact_description(cat_key)}</p>
                
                <h4>Come risolvere</h4>
                <p>{self._get_solution_description(cat_key)}</p>
            </article>
            """)
        
        sections.append('</section>')
        return ''.join(sections)
    
    def _get_impact_description(self, category: str) -> str:
        """Descrizione impatto per categoria."""
        impacts = {
            'testi_alternativi': 'Gli utenti non vedenti non possono comprendere il contenuto delle immagini.',
            'etichette_form': 'Gli utenti con screen reader non possono compilare correttamente i moduli.',
            'contrasto': 'Gli utenti ipovedenti hanno difficoltà a leggere i contenuti.',
            'struttura': 'La navigazione risulta confusa per gli utenti di screen reader.',
            'aria': 'Le tecnologie assistive non interpretano correttamente gli elementi interattivi.',
            'altri': 'Vari impatti sull\'accessibilità a seconda del problema specifico.'
        }
        return impacts.get(category, 'Impatto variabile sull\'accessibilità.')
    
    def _get_solution_description(self, category: str) -> str:
        """Descrizione soluzione per categoria."""
        solutions = {
            'testi_alternativi': 'Aggiungere attributi alt descrittivi a tutte le immagini informative.',
            'etichette_form': 'Associare label esplicite a tutti i campi del modulo.',
            'contrasto': 'Aumentare il contrasto tra testo e sfondo (minimo 4.5:1 per testo normale).',
            'struttura': 'Utilizzare correttamente i tag heading (h1-h6) e landmark ARIA.',
            'aria': 'Correggere ruoli e attributi ARIA secondo le specifiche W3C.',
            'altri': 'Consultare la documentazione WCAG specifica per ogni problema.'
        }
        return solutions.get(category, 'Verificare le linee guida WCAG pertinenti.')
    
    def _generate_remediation_table(self, context: Dict) -> str:
        """Genera tabella piano remediation."""
        
        rows = []
        for item in context['remediation_plan']:
            rows.append(f"""
            <tr>
                <th scope="row">{item['categoria']}</th>
                <td>{item['violazioni']}</td>
                <td>{item['wcag']}</td>
                <td class="prio-{item['priorita'].lower()}">{item['priorita']}</td>
                <td>{item['deadline']}</td>
            </tr>
            """)
        
        return f"""
        <section>
            <h2>Piano di Remediation Prioritizzato</h2>
            <table>
                <caption>Interventi correttivi ordinati per priorità</caption>
                <thead>
                    <tr>
                        <th scope="col">Categoria</th>
                        <th scope="col">N° Problemi</th>
                        <th scope="col">WCAG</th>
                        <th scope="col">Priorità</th>
                        <th scope="col">Deadline suggerita</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </section>
        """
    
    def _generate_detailed_issues(self, context: Dict) -> str:
        """Genera elenco dettagliato problemi (limitato)."""
        
        rows = []
        for v in context['violations'][:20]:  # Limita a 20
            selector = html.escape(v.selector[:60] + '...' if len(v.selector) > 60 else v.selector)
            wcag = v.wcag_criteria or '—'
            severity_class = 'prio-high' if v.severity in ['critical', 'serious'] else \
                           'prio-medium' if v.severity == 'moderate' else 'prio-low'
            
            rows.append(f"""
            <tr>
                <td>{html.escape(v.code)}</td>
                <td>{html.escape(v.message[:100])}...</td>
                <td><code>{selector}</code></td>
                <td>{wcag}</td>
                <td class="{severity_class}">{v.severity.title()}</td>
            </tr>
            """)
        
        return f"""
        <section>
            <h2>Dettaglio Problemi Principali</h2>
            <p>Mostrando i primi 20 problemi di {context['error_total'] + context['warning_total']} totali.</p>
            
            <table>
                <caption>Elenco dettagliato dei problemi di accessibilità</caption>
                <thead>
                    <tr>
                        <th scope="col">Codice</th>
                        <th scope="col">Descrizione</th>
                        <th scope="col">Elemento</th>
                        <th scope="col">WCAG</th>
                        <th scope="col">Severità</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </section>
        """
    
    def _generate_methodology_notes(self) -> str:
        """Genera note metodologiche."""
        return """
        <section>
            <h2>Note Metodologiche</h2>
            <h3>Preparazione alla valutazione completa</h3>
            <p>Per una valutazione completa di conformità WCAG 2.1 AA si raccomanda:</p>
            <ol>
                <li>Test manuali con navigazione da tastiera</li>
                <li>Verifica con screen reader (NVDA, JAWS, VoiceOver)</li>
                <li>Test con utenti reali con disabilità</li>
                <li>Valutazione contenuti multimediali</li>
                <li>Verifica processi e transazioni complete</li>
                <li>Test su dispositivi mobili</li>
            </ol>
            
            <h3>Risorse utili</h3>
            <ul>
                <li><a href="https://www.w3.org/WAI/WCAG21/quickref/">WCAG 2.1 Quick Reference</a></li>
                <li><a href="https://www.agid.gov.it/it/design-servizi/accessibilita">Linee Guida AgID</a></li>
                <li><a href="https://webaim.org/resources/">WebAIM Resources</a></li>
            </ul>
        </section>
        """
    
    def _generate_contacts(self, context: Dict) -> str:
        """Genera sezione contatti."""
        return f"""
        <section>
            <h2>Contatti e Supporto</h2>
            <p>Per domande su questa valutazione o assistenza nell'implementazione delle correzioni:</p>
            <ul>
                <li>Email: {context['email']}</li>
                <li>Riferimento: Report accessibilità {context['company_name']} - {context['scan_date']}</li>
            </ul>
            
            <h3>Procedura di reclamo</h3>
            <p>In caso di problemi di accessibilità non risolti, gli utenti possono presentare reclamo 
            seguendo la procedura prevista dalla normativa europea sull'accessibilità.</p>
            
            <h3>Dichiarazione di accessibilità</h3>
            <p>Si raccomanda di pubblicare una dichiarazione di accessibilità aggiornata sul sito web, 
            includendo lo stato di conformità, i problemi noti e il piano di remediation.</p>
        </section>
        """
    
    def _apply_template(self, content: str, context: Dict) -> str:
        """Applica il template HTML minimal."""
        
        title = f"Report Accessibilità - {context['company_name']} - {context['scan_date']}"
        
        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{
    --primary: #1a5490;
    --secondary: #2c7fb8;
    --success: #41ab5d;
    --warning: #fd8d3c;
    --danger: #d7301f;
    --light: #f7f7f7;
    --dark: #252525;
    --border: #d9d9d9;
  }}
  
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}
  
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: var(--dark);
    background: white;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }}
  
  header {{
    border-bottom: 3px solid var(--primary);
    padding-bottom: 1.5rem;
    margin-bottom: 2rem;
  }}
  
  h1 {{
    color: var(--primary);
    font-size: 2rem;
    margin-bottom: 0.5rem;
  }}
  
  h2 {{
    color: var(--secondary);
    font-size: 1.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  
  h3 {{
    color: var(--dark);
    font-size: 1.2rem;
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
  }}
  
  h4 {{
    color: var(--dark);
    font-size: 1.1rem;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
  }}
  
  p {{
    margin-bottom: 1rem;
  }}
  
  a {{
    color: var(--primary);
    text-decoration: none;
  }}
  
  a:hover {{
    text-decoration: underline;
  }}
  
  a:focus {{
    outline: 3px solid var(--warning);
    outline-offset: 2px;
  }}
  
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}
  
  caption {{
    text-align: left;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--secondary);
  }}
  
  th, td {{
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  
  th {{
    background: var(--light);
    font-weight: 600;
    color: var(--dark);
  }}
  
  tbody tr:hover {{
    background: #fafafa;
  }}
  
  code {{
    background: var(--light);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }}
  
  ul, ol {{
    margin-left: 2rem;
    margin-bottom: 1rem;
  }}
  
  li {{
    margin-bottom: 0.5rem;
  }}
  
  .summary-box {{
    background: var(--light);
    padding: 1.5rem;
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 4px solid var(--primary);
  }}
  
  .warning-box {{
    background: #fff7e6;
    border-left: 4px solid var(--warning);
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 4px;
  }}
  
  .prio-high {{
    color: var(--danger);
    font-weight: 600;
  }}
  
  .prio-medium {{
    color: var(--warning);
    font-weight: 600;
  }}
  
  .prio-low {{
    color: var(--success);
    font-weight: 600;
  }}
  
  .visually-hidden {{
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0,0,0,0);
    white-space: nowrap;
    border: 0;
  }}
  
  article {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1.5rem 0;
  }}
  
  section {{
    margin-bottom: 2rem;
  }}
  
  @media print {{
    body {{
      padding: 0;
      max-width: 100%;
    }}
    
    .warning-box {{
      border: 1px solid var(--warning);
    }}
    
    table {{
      box-shadow: none;
    }}
  }}
  
  @media (max-width: 768px) {{
    body {{
      padding: 1rem;
    }}
    
    table {{
      font-size: 0.9rem;
    }}
    
    th, td {{
      padding: 0.5rem;
    }}
  }}
</style>
</head>
<body>
<a class="visually-hidden" href="#main">Salta al contenuto principale</a>
<main id="main" tabindex="-1">
{content}
</main>
<footer>
  <p><a href="#top">Torna all'inizio</a></p>
  <p><small>Report generato automaticamente - {context['scan_date']}</small></p>
</footer>
</body>
</html>"""


def generate_json_response(html_report: str, 
                          aggregated_results: AggregatedResults,
                          company_name: str) -> Dict[str, Any]:
    """Genera risposta JSON nel formato richiesto dal workflow.
    
    Args:
        html_report: Report HTML generato
        aggregated_results: Risultati aggregati
        company_name: Nome azienda
        
    Returns:
        Dizionario con formato JSON richiesto
    """
    
    # Calcola totali
    error_total = len([v for v in aggregated_results.all_violations 
                       if v.severity in ['critical', 'serious']])
    warning_total = len([v for v in aggregated_results.all_violations 
                        if v.severity in ['moderate', 'minor']])
    
    return {
        "Accessibility Technical Report": html_report,
        "error_total": error_total,
        "warning_total": warning_total,
        "overall_score": aggregated_results.compliance.overall_score,
        "compliance_status": aggregated_results.compliance.compliance_level,
        "company_name": company_name,
        "report_generated": True,
        "generation_timestamp": datetime.now().isoformat()
    }