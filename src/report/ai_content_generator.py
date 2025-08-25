"""
Generatore di contenuti testuali con IA per report accessibilità
Integra OpenAI API per generare testi professionali e contestualizzati in italiano
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Aggiungi path per importare moduli eaa_scanner
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    
from .schema import ScanResult, Issue, POURPrinciple, DisabilityType, Severity

logger = logging.getLogger(__name__)


class AIContentGenerator:
    """Genera contenuti testuali professionali usando OpenAI API o sistema multi-agent"""
    
    def __init__(self):
        """Inizializza il generatore di contenuti AI con OpenAI e fallback multi-agent"""
        self.client = None
        self.model = "gpt-4-turbo-preview"  # Migliore per contenuti in italiano
        self.orchestrator = None
        
        # Prova prima OpenAI
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                try:
                    self.client = OpenAI(api_key=api_key)
                    logger.info("✅ OpenAI API inizializzata con successo")
                except Exception as e:
                    logger.error(f"Errore inizializzazione OpenAI: {e}")
                    self.client = None
            else:
                logger.info("OPENAI_API_KEY non configurata, provo sistema multi-agent")
        else:
            logger.info("Libreria OpenAI non installata, uso sistema multi-agent")
        
        # Se OpenAI non disponibile, prova multi-agent come fallback
        if not self.client:
            try:
                from eaa_scanner.agents.orchestrator import AIReportOrchestrator
                self.orchestrator = AIReportOrchestrator({
                    'language': 'it',
                    'report_style': 'professional',
                    'parallel_execution': True,
                    'quality_threshold': 0.8
                })
                logger.info("✅ Sistema multi-agent inizializzato come fallback")
            except ImportError:
                logger.warning("⚠️ Sistema multi-agent non disponibile")
                self.orchestrator = None
        
    async def generate_executive_summary(self, scan_result: ScanResult) -> str:
        """
        Genera sintesi esecutiva professionale usando OpenAI o multi-agent
        
        Args:
            scan_result: Risultati della scansione
            
        Returns:
            Testo HTML della sintesi esecutiva
        """
        context = {
            'company_name': scan_result.company_name,
            'url': scan_result.url,
            'compliance_score': scan_result.compliance_score,
            'compliance_level': scan_result.compliance_level,
            'total_issues': len(scan_result.issues),
            'critical_issues': len([i for i in scan_result.issues if i.severity == Severity.CRITICO]),
            'high_issues': len([i for i in scan_result.issues if i.severity == Severity.ALTO]),
            'pour_distribution': self._get_pour_distribution(scan_result.issues)
        }
        
        # Prova prima con OpenAI
        if self.client:
            try:
                prompt = f"""
                Scrivi una sintesi esecutiva professionale per un audit di accessibilità web in italiano.
                Usa uno stile formale ma chiaro, simile a Semrush o altri tool professionali.
                
                Dati del sito:
                - Azienda: {context['company_name']}
                - URL: {context['url']}
                - Punteggio conformità: {context['compliance_score']:.1f}%
                - Livello: {context['compliance_level']}
                - Problemi totali: {context['total_issues']}
                - Critici: {context['critical_issues']}
                - Alta priorità: {context['high_issues']}
                
                La sintesi deve:
                1. Presentare lo stato attuale di conformità
                2. Evidenziare i rischi principali  
                3. Indicare l'impatto sugli utenti
                4. Suggerire le priorità di intervento
                
                Genera SOLO contenuto HTML con tag <p>, <strong>, <em>.
                NON includere date, timeline o scadenze temporali.
                Mantieni un tono professionale e orientato all'azione.
                Lunghezza: 3-4 paragrafi.
                """
                
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Sei un esperto di accessibilità web e conformità WCAG 2.1 AA. Scrivi in italiano professionale."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                logger.error(f"Errore OpenAI: {e}")
                # Fallback a multi-agent o contenuti statici
        
        # Se OpenAI non disponibile, prova multi-agent
        if self.orchestrator:
            try:
                from eaa_scanner.agents.base_agent import AgentContext
                
                agent_result = await self.orchestrator.specialist_agents['executive'].process(
                    AgentContext(
                        scan_data={'summary': context},
                        company_info={'company_name': scan_result.company_name},
                        shared_context={}
                    )
                )
                
                if agent_result.status == 'completed':
                    return agent_result.data.get('executive_summary', self._get_fallback_executive_summary(context))
                    
            except Exception as e:
                logger.error(f"Errore multi-agent: {e}")
        
        # Fallback finale a contenuti statici
        return self._get_fallback_executive_summary(context)
    
    async def generate_pour_analysis(self, issues: List[Issue]) -> Dict[str, str]:
        """
        Genera analisi dettagliata per ogni principio P.O.U.R.
        
        Args:
            issues: Lista delle problematiche
            
        Returns:
            Dizionario con analisi per ogni principio
        """
        pour_analysis = {}
        
        for principle in POURPrinciple:
            principle_issues = [i for i in issues if i.pour == principle]
            
            if principle_issues:
                context = {
                    'principle': principle.value,
                    'issue_count': len(principle_issues),
                    'critical_count': len([i for i in principle_issues if i.severity == Severity.CRITICO]),
                    'disabilities_affected': self._get_affected_disabilities(principle_issues),
                    'common_problems': self._get_common_problems(principle_issues)[:3]
                }
                
                pour_analysis[principle.value] = self._generate_pour_description(context)
        
        return pour_analysis
    
    async def generate_disability_impact_analysis(self, issues: List[Issue]) -> Dict[str, str]:
        """
        Genera analisi dell'impatto per ogni tipo di disabilità
        
        Args:
            issues: Lista delle problematiche
            
        Returns:
            Dizionario con analisi per ogni disabilità
        """
        disability_analysis = {}
        
        for disability in DisabilityType:
            affected_issues = [i for i in issues if disability in i.disability_impact]
            
            if affected_issues:
                context = {
                    'disability': disability.value,
                    'issue_count': len(affected_issues),
                    'severity_distribution': self._get_severity_distribution(affected_issues),
                    'pour_principles': self._get_pour_principles_for_disability(affected_issues),
                    'top_barriers': self._get_top_barriers(affected_issues, disability)
                }
                
                disability_analysis[disability.value] = self._generate_disability_description(context)
        
        return disability_analysis
    
    async def generate_remediation_narrative(self, issues: List[Issue]) -> str:
        """
        Genera narrativa per il piano di remediation
        
        Args:
            issues: Lista delle problematiche
            
        Returns:
            Testo HTML del piano di remediation
        """
        critical_issues = [i for i in issues if i.severity == Severity.CRITICO]
        high_issues = [i for i in issues if i.severity == Severity.ALTO]
        
        context = {
            'critical_count': len(critical_issues),
            'high_count': len(high_issues),
            'total_effort': self._estimate_total_effort(issues),
            'priority_areas': self._identify_priority_areas(issues),
            'quick_wins': self._identify_quick_wins(issues)
        }
        
        try:
            agent_result = await self.orchestrator.specialist_agents['remediation'].process(
                AgentContext(
                    scan_data={'issues': [self._issue_to_dict(i) for i in issues[:10]]},  # Top 10 issues
                    company_info={},
                    shared_context=context
                )
            )
            
            if agent_result.status == 'completed':
                return agent_result.data.get('remediation_plan', self._get_fallback_remediation(context))
            else:
                return self._get_fallback_remediation(context)
                
        except Exception as e:
            logger.error(f"Errore generazione remediation: {e}")
            return self._get_fallback_remediation(context)
    
    async def generate_strategic_recommendations(self, scan_result: ScanResult) -> str:
        """
        Genera raccomandazioni strategiche personalizzate
        
        Args:
            scan_result: Risultati della scansione
            
        Returns:
            Testo HTML delle raccomandazioni
        """
        context = {
            'compliance_score': scan_result.compliance_score,
            'main_issues': self._get_main_issue_categories(scan_result.issues),
            'affected_users': self._get_most_affected_users(scan_result.issues),
            'industry': 'digital services',  # Potrebbe essere parametrizzato
            'company_size': 'medium'  # Potrebbe essere parametrizzato
        }
        
        try:
            agent_result = await self.orchestrator.specialist_agents['recommendations'].process(
                AgentContext(
                    scan_data={'summary': context},
                    company_info={'company_name': scan_result.company_name},
                    shared_context={}
                )
            )
            
            if agent_result.status == 'completed':
                return agent_result.data.get('recommendations', self._get_fallback_recommendations(context))
            else:
                return self._get_fallback_recommendations(context)
                
        except Exception as e:
            logger.error(f"Errore generazione raccomandazioni: {e}")
            return self._get_fallback_recommendations(context)
    
    # Metodi di supporto privati
    
    def _get_pour_distribution(self, issues: List[Issue]) -> Dict[str, int]:
        """Calcola distribuzione issues per principio P.O.U.R."""
        distribution = {}
        for principle in POURPrinciple:
            distribution[principle.value] = len([i for i in issues if i.pour == principle])
        return distribution
    
    def _get_affected_disabilities(self, issues: List[Issue]) -> List[str]:
        """Identifica disabilità affette da un set di issues"""
        disabilities = set()
        for issue in issues:
            disabilities.update(issue.disability_impact)
        return [d.value for d in disabilities]
    
    def _get_common_problems(self, issues: List[Issue]) -> List[str]:
        """Identifica i problemi più comuni"""
        problem_counts = {}
        for issue in issues:
            key = issue.description[:50]  # Primi 50 caratteri come chiave
            problem_counts[key] = problem_counts.get(key, 0) + 1
        
        sorted_problems = sorted(problem_counts.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_problems]
    
    async def _generate_pour_description_openai(self, context: Dict[str, Any]) -> str:
        """Genera descrizione P.O.U.R. con OpenAI"""
        try:
            prompt = f"""
            Descrivi l'impatto del principio {context['principle']} nell'audit di accessibilità.
            
            Dati:
            - Problemi trovati: {context['issue_count']}
            - Critici: {context['critical_count']}
            - Disabilità impattate: {', '.join(context['disabilities_affected'])}
            
            Scrivi 2-3 frasi professionali che spieghino:
            1. Cosa significa questo principio per gli utenti
            2. L'impatto dei problemi trovati
            3. Le conseguenze per l'accessibilità
            
            Stile: professionale, specifico, orientato all'impatto utente.
            NON usare date o timeline.
            """
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Esperto WCAG 2.1. Rispondi in italiano professionale."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Errore OpenAI per P.O.U.R.: {e}")
            return self._generate_pour_description(context)
    
    def _generate_pour_description(self, context: Dict[str, Any]) -> str:
        """Genera descrizione per un principio P.O.U.R."""
        principle = context['principle']
        count = context['issue_count']
        critical = context['critical_count']
        
        descriptions = {
            'Percepibile': f"Sono stati rilevati {count} problemi di percepibilità che impediscono agli utenti di percepire correttamente i contenuti. {critical} di questi sono critici e richiedono intervento immediato per garantire che le informazioni siano accessibili attraverso diversi canali sensoriali.",
            
            'Operabile': f"L'analisi ha identificato {count} barriere all'operabilità che limitano l'interazione con il sito. {critical} problemi critici impediscono completamente l'uso di alcune funzionalità, particolarmente per utenti che navigano solo da tastiera.",
            
            'Comprensibile': f"Sono presenti {count} problematiche di comprensibilità che rendono difficile per gli utenti capire e utilizzare il sito. {critical} di questi sono critici e compromettono la comprensione delle funzionalità principali.",
            
            'Robusto': f"Rilevati {count} problemi di robustezza che compromettono la compatibilità con tecnologie assistive. {critical} criticità impediscono il corretto funzionamento con screen reader e altri strumenti assistivi."
        }
        
        return descriptions.get(principle, f"Rilevati {count} problemi per il principio {principle}.")
    
    async def _generate_disability_description_openai(self, context: Dict[str, Any]) -> str:
        """Genera descrizione impatto disabilità con OpenAI"""
        try:
            disability_names = {
                'non_vedenti': 'persone non vedenti',
                'ipovisione': 'persone con ipovisione',
                'daltonismo': 'persone con daltonismo',
                'motorie': 'persone con disabilità motorie',
                'cognitive_linguistiche': 'persone con difficoltà cognitive o linguistiche',
                'uditiva': 'persone con disabilità uditive'
            }
            
            prompt = f"""
            Descrivi l'impatto delle barriere di accessibilità per {disability_names.get(context['disability'], context['disability'])}.
            
            Dati:
            - Barriere trovate: {context['issue_count']}
            - Principi P.O.U.R. coinvolti: {', '.join(context['pour_principles'])}
            
            Scrivi 2-3 frasi che spieghino:
            1. Come queste barriere impattano questa categoria di utenti
            2. Le difficoltà concrete che incontrano
            3. L'importanza di rimuovere queste barriere
            
            Usa linguaggio professionale ma empatico.
            Focalizzati sull'esperienza utente reale.
            """
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": "Esperto di accessibilità e user experience inclusiva."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Errore OpenAI per disabilità: {e}")
            return self._generate_disability_description(context)
    
    def _generate_disability_description(self, context: Dict[str, Any]) -> str:
        """Genera descrizione per impatto su disabilità"""
        disability = context['disability']
        count = context['issue_count']
        
        descriptions = {
            'non_vedenti': f"Gli utenti non vedenti che utilizzano screen reader incontrano {count} barriere significative. Le principali problematiche riguardano immagini senza testo alternativo, struttura non semantica e form non etichettati correttamente.",
            
            'ipovisione': f"Persone con ipovisione affrontano {count} difficoltà principalmente legate a contrasto insufficiente, testo non ridimensionabile e layout non responsivi che non si adattano all'ingrandimento.",
            
            'daltonismo': f"Utenti con daltonismo possono incontrare {count} problemi dove il colore è l'unico mezzo per trasmettere informazioni, rendendo difficile distinguere stati, errori o elementi interattivi.",
            
            'motorie': f"Persone con disabilità motorie trovano {count} ostacoli nell'uso del sito, principalmente elementi non accessibili da tastiera, target troppo piccoli e timeout insufficienti.",
            
            'cognitive_linguistiche': f"Utenti con difficoltà cognitive o linguistiche affrontano {count} barriere legate a complessità di navigazione, linguaggio non chiaro e mancanza di istruzioni adeguate.",
            
            'uditiva': f"Persone con disabilità uditive incontrano {count} problemi principalmente con contenuti audio/video privi di sottotitoli o trascrizioni."
        }
        
        return descriptions.get(disability, f"Rilevati {count} problemi che impattano questa categoria di utenti.")
    
    def _get_fallback_executive_summary(self, context: Dict[str, Any]) -> str:
        """Fallback per executive summary"""
        return f"""
        <p>Il sito web di <strong>{context['company_name']}</strong> presenta un punteggio di conformità 
        del <strong>{context['compliance_score']:.1f}%</strong>, classificandolo come 
        <strong>{context['compliance_level']}</strong> rispetto agli standard WCAG 2.1 AA.</p>
        
        <p>L'analisi ha identificato <strong>{context['total_issues']} problematiche totali</strong>, 
        di cui <strong class="prio-critical">{context['critical_issues']} critiche</strong> e 
        <strong class="prio-high">{context['high_issues']} ad alta priorità</strong> che richiedono 
        intervento tempestivo per garantire l'accessibilità del sito.</p>
        
        <p>Le problematiche sono distribuite tra i quattro principi P.O.U.R., con particolare 
        concentrazione nelle aree di percepibilità e operabilità, che rappresentano le barriere 
        più significative per gli utenti con disabilità.</p>
        """
    
    def _get_fallback_remediation(self, context: Dict[str, Any]) -> str:
        """Fallback per piano remediation"""
        return f"""
        <p>Il piano di remediation deve affrontare prioritariamente le <strong>{context['critical_count']} 
        criticità</strong> che impediscono completamente l'accesso a funzionalità essenziali, 
        seguito dalle <strong>{context['high_count']} problematiche ad alta priorità</strong>.</p>
        
        <p>Si stima un effort complessivo di circa <strong>{context['total_effort']} ore/uomo</strong> 
        per raggiungere la piena conformità, distribuito in fasi progressive per minimizzare 
        l'impatto operativo e massimizzare i benefici per gli utenti.</p>
        
        <p>Le aree prioritarie di intervento includono: {', '.join(context['priority_areas'])}. 
        Alcuni interventi possono essere implementati rapidamente per ottenere miglioramenti 
        immediati nell'esperienza utente.</p>
        """
    
    def _get_fallback_recommendations(self, context: Dict[str, Any]) -> str:
        """Fallback per raccomandazioni strategiche"""
        return f"""
        <p>Per migliorare il punteggio di conformità attuale del {context['compliance_score']:.1f}%, 
        si raccomanda un approccio strutturato che combini interventi tecnici immediati con 
        una strategia di accessibilità a lungo termine.</p>
        
        <p>Le principali aree di intervento riguardano: {', '.join(context['main_issues'])}. 
        Questi interventi beneficeranno principalmente gli utenti {', '.join(context['affected_users'])}.</p>
        
        <p>È fondamentale implementare processi di controllo qualità continui, formazione del team 
        di sviluppo sulle best practice di accessibilità, e coinvolgimento di utenti con disabilità 
        nel processo di testing e validazione.</p>
        """
    
    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """Converte Issue in dizionario per serializzazione"""
        return {
            'id': issue.id,
            'description': issue.description,
            'wcag_criteria': issue.wcag_criteria,
            'pour': issue.pour.value,
            'severity': issue.severity.value,
            'disability_impact': [d.value for d in issue.disability_impact],
            'remediation': issue.remediation,
            'source': issue.source,
            'element': issue.element,
            'code': issue.code
        }
    
    def _get_severity_distribution(self, issues: List[Issue]) -> Dict[str, int]:
        """Calcola distribuzione per severità"""
        distribution = {}
        for severity in Severity:
            distribution[severity.value] = len([i for i in issues if i.severity == severity])
        return distribution
    
    def _get_pour_principles_for_disability(self, issues: List[Issue]) -> List[str]:
        """Identifica principi P.O.U.R. che impattano una disabilità"""
        principles = set()
        for issue in issues:
            principles.add(issue.pour.value)
        return list(principles)
    
    def _get_top_barriers(self, issues: List[Issue], disability: DisabilityType) -> List[str]:
        """Identifica le barriere principali per una disabilità"""
        barriers = []
        for issue in issues[:5]:  # Top 5
            if disability in issue.disability_impact:
                barriers.append(issue.description[:100])
        return barriers
    
    def _estimate_total_effort(self, issues: List[Issue]) -> int:
        """Stima effort totale in ore"""
        effort_map = {
            Severity.CRITICO: 4,
            Severity.ALTO: 2,
            Severity.MEDIO: 1,
            Severity.BASSO: 0.5
        }
        
        total = 0
        for issue in issues:
            total += effort_map.get(issue.severity, 1)
        
        return int(total)
    
    def _identify_priority_areas(self, issues: List[Issue]) -> List[str]:
        """Identifica aree prioritarie"""
        areas = set()
        for issue in issues:
            if issue.severity in [Severity.CRITICO, Severity.ALTO]:
                if 'immagini' in issue.description.lower():
                    areas.add('Testi alternativi')
                elif 'contrasto' in issue.description.lower():
                    areas.add('Contrasto colori')
                elif 'tastiera' in issue.description.lower():
                    areas.add('Navigazione tastiera')
                elif 'form' in issue.description.lower() or 'etichett' in issue.description.lower():
                    areas.add('Form e etichette')
                elif 'aria' in issue.description.lower():
                    areas.add('ARIA e semantica')
        
        return list(areas)[:5]
    
    def _identify_quick_wins(self, issues: List[Issue]) -> List[str]:
        """Identifica quick wins"""
        quick_wins = []
        for issue in issues:
            if issue.severity == Severity.BASSO or 'alt' in issue.description.lower():
                quick_wins.append(issue.description[:80])
        
        return quick_wins[:5]
    
    def _get_main_issue_categories(self, issues: List[Issue]) -> List[str]:
        """Identifica categorie principali di problemi"""
        categories = set()
        for issue in issues:
            categories.add(issue.pour.value)
        return list(categories)
    
    def _get_most_affected_users(self, issues: List[Issue]) -> List[str]:
        """Identifica utenti più colpiti"""
        disability_counts = {}
        for issue in issues:
            for disability in issue.disability_impact:
                disability_counts[disability.value] = disability_counts.get(disability.value, 0) + 1
        
        sorted_disabilities = sorted(disability_counts.items(), key=lambda x: x[1], reverse=True)
        return [d[0] for d in sorted_disabilities[:3]]


# Funzione helper per uso sincrono
def generate_ai_content(scan_result: ScanResult) -> Dict[str, Any]:
    """
    Wrapper sincrono per generazione contenuti AI
    
    Args:
        scan_result: Risultati della scansione
        
    Returns:
        Dizionario con tutti i contenuti generati
    """
    generator = AIContentGenerator()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        content = {
            'executive_summary': loop.run_until_complete(
                generator.generate_executive_summary(scan_result)
            ),
            'pour_analysis': loop.run_until_complete(
                generator.generate_pour_analysis(scan_result.issues)
            ),
            'disability_analysis': loop.run_until_complete(
                generator.generate_disability_impact_analysis(scan_result.issues)
            ),
            'remediation_narrative': loop.run_until_complete(
                generator.generate_remediation_narrative(scan_result.issues)
            ),
            'strategic_recommendations': loop.run_until_complete(
                generator.generate_strategic_recommendations(scan_result)
            )
        }
        
        return content
        
    finally:
        loop.close()