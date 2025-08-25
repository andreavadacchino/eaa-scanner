"""Intelligent Fallback Manager - Gestione fallback intelligenti basati su dati reali"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_agent import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class IntelligentFallbackManager:
    """Manager per generazione fallback intelligenti basati su dati reali"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fallback_templates = self._initialize_templates()
        
    def _initialize_templates(self) -> Dict[str, str]:
        """Inizializza template di fallback per ogni agent"""
        return {
            'executive': self._get_executive_template(),
            'technical': self._get_technical_template(),
            'compliance': self._get_compliance_template(),
            'remediation': self._get_remediation_template(),
            'recommendations': self._get_recommendations_template(),
            'default': self._get_default_template()
        }
    
    async def generate_intelligent_fallback(self,
                                          agent_name: str,
                                          context: AgentContext,
                                          failed_result: AgentResult) -> str:
        """Genera fallback intelligente basato sui dati disponibili
        
        Args:
            agent_name: Nome dell'agent che ha fallito
            context: Contesto con dati reali
            failed_result: Risultato fallito per analisi
            
        Returns:
            HTML con fallback personalizzato
        """
        
        self.logger.info(f"Generating intelligent fallback for {agent_name}")
        
        # Estrai dati chiave dal contesto
        company_name = context.company_info.get('company_name', 'N/A')
        url = context.company_info.get('url', 'N/A')
        overall_score = context.shared_metrics.get('overall_score', 0)
        total_violations = context.shared_metrics.get('total_violations', 0)
        critical_count = context.shared_metrics.get('critical_count', 0)
        
        # Seleziona template appropriato
        template = self.fallback_templates.get(agent_name, self.fallback_templates['default'])
        
        # Personalizza con dati reali
        fallback_content = template.format(
            company_name=company_name,
            url=url,
            overall_score=overall_score,
            total_violations=total_violations,
            critical_count=critical_count,
            date=datetime.now().strftime('%d/%m/%Y'),
            error_reason=failed_result.errors[0] if failed_result.errors else 'Errore sconosciuto'
        )
        
        # Aggiungi avviso che è fallback
        fallback_content = self._add_fallback_notice(fallback_content, agent_name)
        
        return fallback_content
    
    async def generate_complete_fallback(self,
                                        scan_data: Dict[str, Any],
                                        company_info: Dict[str, Any],
                                        error_message: str) -> str:
        """Genera report di fallback completo quando orchestrator fallisce
        
        Args:
            scan_data: Dati scansione disponibili
            company_info: Info azienda
            error_message: Messaggio errore
            
        Returns:
            HTML report completo di fallback
        """
        
        self.logger.warning(f"Generating complete fallback report due to: {error_message}")
        
        # Estrai dati essenziali
        company_name = company_info.get('company_name', 'N/A')
        url = company_info.get('url', 'N/A')
        email = company_info.get('email', '')
        
        # Calcola metriche base dai dati disponibili
        violations = scan_data.get('all_violations', [])
        total_violations = len(violations)
        critical = len([v for v in violations if v.get('severity') in ['critical', 'serious']])
        high = len([v for v in violations if v.get('severity') == 'high'])
        medium = len([v for v in violations if v.get('severity') in ['moderate', 'medium']])
        low = len([v for v in violations if v.get('severity') in ['minor', 'low']])
        
        # Stima score base
        if total_violations == 0:
            estimated_score = 100
        elif critical > 10:
            estimated_score = 30
        elif critical > 5:
            estimated_score = 50
        elif critical > 0:
            estimated_score = 70
        else:
            estimated_score = max(40, 100 - total_violations * 2)
        
        # Genera report minimo ma professionale
        return f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Report Accessibilità - {company_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }}
        h1, h2 {{ color: #1a5490; }}
        .warning {{
            background: #fff7e6;
            border-left: 4px solid #fd8d3c;
            padding: 1rem;
            margin: 1rem 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        .critical {{ color: #d7301f; font-weight: 600; }}
        .high {{ color: #fd8d3c; font-weight: 600; }}
        .medium {{ color: #fdb863; }}
        .low {{ color: #74add1; }}
    </style>
</head>
<body>
    <h1>Report di Accessibilità Web</h1>
    <p><strong>{company_name}</strong> - {url}</p>
    <p>Data analisi: {datetime.now().strftime('%d/%m/%Y')}</p>
    
    <div class="warning">
        <strong>⚠️ Nota:</strong> Questo è un report semplificato generato automaticamente 
        a causa di un problema tecnico nel sistema di analisi avanzato. I dati presentati sono 
        basati sull'analisi automatica disponibile ma potrebbero non essere completi.
    </div>
    
    <h2>Riepilogo Risultati</h2>
    <table>
        <tr>
            <th>Metrica</th>
            <th>Valore</th>
        </tr>
        <tr>
            <td>Punteggio Stimato</td>
            <td><strong>{estimated_score}/100</strong></td>
        </tr>
        <tr>
            <td>Problemi Totali</td>
            <td>{total_violations}</td>
        </tr>
        <tr>
            <td>Problemi Critici</td>
            <td class="critical">{critical}</td>
        </tr>
        <tr>
            <td>Problemi Alti</td>
            <td class="high">{high}</td>
        </tr>
        <tr>
            <td>Problemi Medi</td>
            <td class="medium">{medium}</td>
        </tr>
        <tr>
            <td>Problemi Bassi</td>
            <td class="low">{low}</td>
        </tr>
    </table>
    
    <h2>Valutazione Preliminare</h2>
    <p>
        {self._get_preliminary_assessment(estimated_score, critical, total_violations)}
    </p>
    
    <h2>Raccomandazioni Immediate</h2>
    <ol>
        {self._get_basic_recommendations(critical, high, medium, total_violations)}
    </ol>
    
    <h2>Prossimi Passi</h2>
    <p>
        Per un'analisi completa e dettagliata dell'accessibilità del vostro sito web, 
        vi consigliamo di:
    </p>
    <ul>
        <li>Ripetere la scansione quando il sistema sarà completamente operativo</li>
        <li>Effettuare test manuali con tecnologie assistive</li>
        <li>Consultare un esperto di accessibilità web</li>
        <li>Implementare le correzioni prioritarie identificate</li>
    </ul>
    
    <h2>Contatti</h2>
    <p>
        Per assistenza o domande su questo report, contattare: 
        {email if email else 'supporto tecnico'}
    </p>
    
    <hr>
    <p><small>
        Report generato automaticamente il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}.<br>
        Versione: Fallback Mode | Motivo: {error_message[:100]}
    </small></p>
</body>
</html>
        """
    
    def _get_executive_template(self) -> str:
        """Template fallback per Executive Summary"""
        return """
        <section class="executive-summary-fallback">
            <h2>Executive Summary</h2>
            <div class="fallback-content">
                <h3>Risultati Principali</h3>
                <p>L'analisi automatica del sito <strong>{company_name}</strong> ({url}) 
                ha identificato <strong>{total_violations}</strong> potenziali problemi di accessibilità, 
                di cui <strong class="critical">{critical_count}</strong> critici.</p>
                
                <p>Il punteggio complessivo stimato è <strong>{overall_score:.1f}/100</strong>, 
                che indica la necessità di interventi per migliorare l'accessibilità del sito.</p>
                
                <h3>Azioni Prioritarie</h3>
                <ol>
                    <li>Risolvere i {critical_count} problemi critici identificati</li>
                    <li>Implementare test di accessibilità nel processo di sviluppo</li>
                    <li>Formare il team su best practice di accessibilità</li>
                </ol>
                
                <p><em>Data analisi: {date}</em></p>
            </div>
        </section>
        """
    
    def _get_technical_template(self) -> str:
        """Template fallback per Technical Analysis"""
        return """
        <section class="technical-analysis-fallback">
            <h2>Analisi Tecnica</h2>
            <div class="fallback-content">
                <p>L'analisi tecnica dettagliata non è disponibile in questo momento.</p>
                
                <h3>Dati Disponibili</h3>
                <ul>
                    <li>Violazioni totali rilevate: {total_violations}</li>
                    <li>Problemi critici: {critical_count}</li>
                    <li>Score complessivo: {overall_score:.1f}/100</li>
                </ul>
                
                <p>Si raccomanda una verifica manuale approfondita per identificare:</p>
                <ul>
                    <li>Problemi di contrasto colore</li>
                    <li>Mancanza di testi alternativi</li>
                    <li>Problemi di navigazione da tastiera</li>
                    <li>Struttura semantica non corretta</li>
                </ul>
            </div>
        </section>
        """
    
    def _get_compliance_template(self) -> str:
        """Template fallback per Compliance Assessment"""
        return """
        <section class="compliance-fallback">
            <h2>Valutazione Conformità</h2>
            <div class="fallback-content">
                <p>Basandosi sui dati disponibili, il sito <strong>{company_name}</strong> 
                presenta un livello di conformità che richiede attenzione.</p>
                
                <h3>Standard di Riferimento</h3>
                <ul>
                    <li>WCAG 2.1 Livello AA</li>
                    <li>EN 301 549</li>
                    <li>European Accessibility Act (EAA)</li>
                </ul>
                
                <p>Con {total_violations} violazioni identificate, è necessario un piano 
                di remediation strutturato per raggiungere la conformità richiesta.</p>
            </div>
        </section>
        """
    
    def _get_remediation_template(self) -> str:
        """Template fallback per Remediation Plan"""
        return """
        <section class="remediation-fallback">
            <h2>Piano di Remediation</h2>
            <div class="fallback-content">
                <p>Piano di correzione basato sui {total_violations} problemi identificati:</p>
                
                <h3>Priorità Immediate (30 giorni)</h3>
                <ul>
                    <li>Risolvere i {critical_count} problemi critici</li>
                    <li>Implementare testi alternativi mancanti</li>
                    <li>Correggere problemi di navigazione da tastiera</li>
                </ul>
                
                <h3>Priorità Alta (90 giorni)</h3>
                <ul>
                    <li>Migliorare contrasto colore</li>
                    <li>Aggiungere etichette ai form</li>
                    <li>Correggere struttura heading</li>
                </ul>
                
                <h3>Priorità Media (180 giorni)</h3>
                <ul>
                    <li>Ottimizzare per screen reader</li>
                    <li>Implementare ARIA correttamente</li>
                    <li>Test con utenti reali</li>
                </ul>
            </div>
        </section>
        """
    
    def _get_recommendations_template(self) -> str:
        """Template fallback per Recommendations"""
        return """
        <section class="recommendations-fallback">
            <h2>Raccomandazioni</h2>
            <div class="fallback-content">
                <p>Basandosi sull'analisi preliminare:</p>
                
                <h3>Azioni Consigliate</h3>
                <ol>
                    <li><strong>Audit Manuale Completo</strong>: Effettuare test con tecnologie assistive</li>
                    <li><strong>Formazione Team</strong>: Workshop su accessibilità web per sviluppatori</li>
                    <li><strong>Processo di QA</strong>: Integrare test accessibilità nel workflow</li>
                    <li><strong>Monitoraggio Continuo</strong>: Implementare scansioni automatiche periodiche</li>
                    <li><strong>Documentazione</strong>: Creare linee guida interne per accessibilità</li>
                </ol>
                
                <p>Score attuale: {overall_score:.1f}/100 - Margine di miglioramento significativo</p>
            </div>
        </section>
        """
    
    def _get_default_template(self) -> str:
        """Template fallback generico"""
        return """
        <section class="generic-fallback">
            <h2>Sezione Non Disponibile</h2>
            <div class="fallback-content">
                <p>Questa sezione del report non è attualmente disponibile a causa di: {error_reason}</p>
                
                <p>Dati di base disponibili:</p>
                <ul>
                    <li>Azienda: {company_name}</li>
                    <li>URL: {url}</li>
                    <li>Problemi totali: {total_violations}</li>
                    <li>Score: {overall_score:.1f}/100</li>
                </ul>
                
                <p>Si prega di ripetere l'analisi o contattare il supporto tecnico.</p>
            </div>
        </section>
        """
    
    def _add_fallback_notice(self, content: str, agent_name: str) -> str:
        """Aggiunge avviso che si tratta di contenuto fallback"""
        notice = f"""
        <div class="fallback-notice" style="background: #fff3cd; border-left: 4px solid #ffc107; 
             padding: 0.75rem; margin: 1rem 0; font-size: 0.9em;">
            <strong>🛈 Nota:</strong> Questa sezione ({agent_name}) è stata generata 
            utilizzando un sistema di fallback a causa di un problema temporaneo. 
            I dati presentati sono basati sulle informazioni disponibili ma potrebbero 
            non essere completi o dettagliati come in condizioni normali.
        </div>
        """
        return notice + content
    
    def _get_preliminary_assessment(self, score: float, critical: int, total: int) -> str:
        """Genera valutazione preliminare basata sui dati"""
        if score >= 80:
            return f"""Il sito mostra un buon livello base di accessibilità con uno score 
                    stimato di {score}/100. Tuttavia, i {total} problemi identificati richiedono 
                    attenzione per raggiungere la piena conformità."""
        elif score >= 60:
            return f"""Il sito presenta problemi di accessibilità moderati con uno score 
                    stimato di {score}/100. I {critical} problemi critici devono essere risolti 
                    con priorità per garantire l'accesso a tutti gli utenti."""
        elif score >= 40:
            return f"""Il sito ha significativi problemi di accessibilità con uno score 
                    stimato di {score}/100. Con {critical} problemi critici e {total} totali, 
                    è necessario un intervento strutturato per migliorare l'accessibilità."""
        else:
            return f"""Il sito presenta gravi problemi di accessibilità con uno score 
                    stimato di {score}/100. I {critical} problemi critici impediscono l'accesso 
                    a molti utenti con disabilità. È urgente un piano di remediation completo."""
    
    def _get_basic_recommendations(self, critical: int, high: int, medium: int, total: int) -> str:
        """Genera raccomandazioni base"""
        recommendations = []
        
        if critical > 0:
            recommendations.append(
                f"<li><strong>Risolvere immediatamente i {critical} problemi critici</strong> "
                "che impediscono l'accesso agli utenti con disabilità</li>"
            )
        
        if high > 0:
            recommendations.append(
                f"<li><strong>Correggere i {high} problemi di priorità alta</strong> "
                "entro 30 giorni per migliorare significativamente l'accessibilità</li>"
            )
        
        if medium > 0:
            recommendations.append(
                f"<li><strong>Pianificare la risoluzione dei {medium} problemi medi</strong> "
                "nel prossimo trimestre</li>"
            )
        
        recommendations.append(
            "<li><strong>Implementare test di accessibilità automatici</strong> "
            "nel processo di sviluppo per prevenire nuovi problemi</li>"
        )
        
        recommendations.append(
            "<li><strong>Formare il team di sviluppo</strong> sulle best practice "
            "di accessibilità web e WCAG 2.1</li>"
        )
        
        return '\n'.join(recommendations[:5])  # Max 5 raccomandazioni