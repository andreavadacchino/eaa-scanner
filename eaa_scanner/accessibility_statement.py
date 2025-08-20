"""
Generatore di Dichiarazione di Accessibilità conforme EAA/AgID
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class AccessibilityStatement:
    """
    Dichiarazione di Accessibilità secondo modello EAA/AgID
    """
    # Sezione 1: Informazioni generali
    organization_name: str
    organization_type: str  # pubblico, privato
    website_name: str
    website_url: str
    statement_url: str
    last_updated: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    # Sezione 2: Stato di conformità
    compliance_status: str = ""  # fully_compliant, partially_compliant, non_compliant
    non_compliant_content: List[Dict[str, str]] = field(default_factory=list)
    disproportionate_burden: List[Dict[str, str]] = field(default_factory=list)
    non_applicable_content: List[Dict[str, str]] = field(default_factory=list)
    
    # Sezione 3: Preparazione della dichiarazione
    evaluation_method: str = "Autovalutazione effettuata direttamente dal soggetto erogatore"
    evaluation_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    evaluation_report_url: Optional[str] = None
    last_review_date: Optional[str] = None
    
    # Sezione 4: Feedback e contatti
    feedback_email: str = ""
    feedback_phone: Optional[str] = None
    feedback_url: Optional[str] = None
    response_time_days: int = 30
    
    # Sezione 5: Procedura di attuazione
    enforcement_procedure: str = "AgID - Agenzia per l'Italia Digitale"
    enforcement_email: str = "protocollo@pec.agid.gov.it"
    enforcement_url: str = "https://www.agid.gov.it/it/design-servizi/accessibilita"
    
    # Sezione 6: Informazioni supplementari
    accessibility_measures: List[str] = field(default_factory=list)
    compatibility_info: Dict[str, List[str]] = field(default_factory=dict)
    known_issues: List[Dict[str, str]] = field(default_factory=list)
    alternatives_provided: List[Dict[str, str]] = field(default_factory=list)
    
    # Metadati tecnici
    wcag_version: str = "2.1"
    wcag_level: str = "AA"
    technologies_used: List[str] = field(default_factory=list)
    testing_tools: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Inizializza valori di default"""
        if not self.accessibility_measures:
            self.accessibility_measures = [
                "Il sito è stato progettato seguendo le linee guida WCAG 2.1",
                "Utilizzo di HTML semantico per strutturare i contenuti",
                "Contrasto colore verificato per garantire leggibilità",
                "Navigazione completamente accessibile da tastiera",
                "Compatibilità con i principali screen reader",
                "Testi alternativi per tutte le immagini informative",
                "Form con label e istruzioni chiare",
                "Contenuti multimediali con sottotitoli e trascrizioni"
            ]
        
        if not self.compatibility_info:
            self.compatibility_info = {
                "browsers": [
                    "Chrome 120+",
                    "Firefox 120+",
                    "Safari 17+",
                    "Edge 120+"
                ],
                "screen_readers": [
                    "NVDA 2024.1",
                    "JAWS 2024",
                    "VoiceOver (macOS/iOS)",
                    "TalkBack (Android)"
                ],
                "operating_systems": [
                    "Windows 10/11",
                    "macOS 13+",
                    "iOS 16+",
                    "Android 12+"
                ]
            }
        
        if not self.technologies_used:
            self.technologies_used = [
                "HTML5",
                "CSS3",
                "JavaScript ES6+",
                "WAI-ARIA 1.2"
            ]
        
        if not self.testing_tools:
            self.testing_tools = [
                "WAVE WebAIM",
                "Axe DevTools",
                "Pa11y",
                "Lighthouse",
                "Screen reader testing manuale"
            ]
    
    def generate_html(self) -> str:
        """
        Genera dichiarazione in formato HTML
        
        Returns:
            HTML della dichiarazione
        """
        compliance_text = self._get_compliance_text()
        compliance_class = self._get_compliance_class()
        
        html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dichiarazione di Accessibilità - {self.website_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #0066cc;
            margin-bottom: 10px;
            font-size: 2em;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        h2 {{ 
            color: #004080;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 5px;
        }}
        h3 {{ 
            color: #333;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #0066cc;
        }}
        .compliance-status {{
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-weight: bold;
            text-align: center;
            font-size: 1.1em;
        }}
        .fully-compliant {{
            background: #d4edda;
            color: #155724;
            border: 2px solid #28a745;
        }}
        .partially-compliant {{
            background: #fff3cd;
            color: #856404;
            border: 2px solid #ffc107;
        }}
        .non-compliant {{
            background: #f8d7da;
            color: #721c24;
            border: 2px solid #dc3545;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        ul, ol {{
            margin-left: 30px;
            margin-top: 10px;
        }}
        li {{
            margin: 8px 0;
        }}
        .contact-box {{
            background: #e8f4f8;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #b8daff;
        }}
        .warning {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
        }}
        .success {{
            background: #d4edda;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #0066cc;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #666;
        }}
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            h1 {{
                font-size: 1.5em;
            }}
            table {{
                font-size: 0.9em;
            }}
        }}
        @media print {{
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚖️ Dichiarazione di Accessibilità</h1>
            <div class="metadata">
                <p><strong>Sito web:</strong> {self.website_name}</p>
                <p><strong>URL:</strong> <a href="{self.website_url}">{self.website_url}</a></p>
                <p><strong>Aggiornata il:</strong> {self.last_updated}</p>
            </div>
        </header>

        <div class="compliance-status {compliance_class}">
            {compliance_text}
        </div>

        <section class="section">
            <h2>1. Informazioni Generali</h2>
            <p><strong>{self.organization_name}</strong> si impegna a rendere il proprio sito web accessibile, 
            conformemente alla Direttiva UE 2019/882 (European Accessibility Act) e alle Linee guida 
            per l'accessibilità dei contenuti Web (WCAG) {self.wcag_version} Livello {self.wcag_level}.</p>
            
            <p>La presente dichiarazione di accessibilità si applica a: 
            <strong><a href="{self.website_url}">{self.website_url}</a></strong></p>
        </section>

        <section class="section">
            <h2>2. Stato di Conformità</h2>
            {self._generate_compliance_section()}
        </section>

        <section class="section">
            <h2>3. Preparazione della Dichiarazione</h2>
            <p>La presente dichiarazione è stata preparata il <strong>{self.evaluation_date}</strong>.</p>
            <p>Il metodo utilizzato per la preparazione della dichiarazione è stato: 
            <strong>{self.evaluation_method}</strong></p>
            
            {self._generate_evaluation_details()}
        </section>

        <section class="section">
            <h2>4. Feedback e Contatti</h2>
            <div class="contact-box">
                <h3>📧 Meccanismo di Feedback</h3>
                <p>Puoi notificare eventuali problemi di accessibilità o richiedere informazioni 
                e contenuti esclusi dall'ambito di applicazione della direttiva.</p>
                
                <ul>
                    <li><strong>Email:</strong> <a href="mailto:{self.feedback_email}">{self.feedback_email}</a></li>
                    {f'<li><strong>Telefono:</strong> {self.feedback_phone}</li>' if self.feedback_phone else ''}
                    {f'<li><strong>Form online:</strong> <a href="{self.feedback_url}">{self.feedback_url}</a></li>' if self.feedback_url else ''}
                </ul>
                
                <p>Garantiamo una risposta entro <strong>{self.response_time_days} giorni</strong>.</p>
            </div>
        </section>

        <section class="section">
            <h2>5. Procedura di Attuazione</h2>
            <div class="warning">
                <p>Nel caso in cui non sia possibile ottenere una risposta soddisfacente, 
                è possibile inviare una segnalazione attraverso il meccanismo di feedback all'autorità competente:</p>
                
                <ul>
                    <li><strong>Autorità:</strong> {self.enforcement_procedure}</li>
                    <li><strong>Email PEC:</strong> <a href="mailto:{self.enforcement_email}">{self.enforcement_email}</a></li>
                    <li><strong>Sito web:</strong> <a href="{self.enforcement_url}" target="_blank">{self.enforcement_url}</a></li>
                </ul>
            </div>
        </section>

        <section class="section">
            <h2>6. Informazioni Tecniche</h2>
            {self._generate_technical_info()}
        </section>

        <section class="section">
            <h2>7. Misure di Accessibilità</h2>
            <p>Abbiamo adottato le seguenti misure per garantire l'accessibilità del nostro sito:</p>
            <ul>
                {''.join(f'<li>{measure}</li>' for measure in self.accessibility_measures)}
            </ul>
        </section>

        {self._generate_known_issues_section()}

        <section class="section">
            <h2>9. Compatibilità</h2>
            {self._generate_compatibility_section()}
        </section>

        <footer class="footer">
            <p>Questa dichiarazione è stata creata utilizzando il modello conforme alle linee guida 
            dell'European Accessibility Act (EAA) e dell'Agenzia per l'Italia Digitale (AgID).</p>
            <p>Ultimo aggiornamento: {self.last_updated}</p>
        </footer>
    </div>
</body>
</html>
"""
        return html
    
    def _get_compliance_text(self) -> str:
        """Ottiene testo stato conformità"""
        if self.compliance_status == "fully_compliant":
            return "✅ Questo sito web è PIENAMENTE CONFORME ai requisiti di accessibilità"
        elif self.compliance_status == "partially_compliant":
            return "⚠️ Questo sito web è PARZIALMENTE CONFORME ai requisiti di accessibilità"
        else:
            return "❌ Questo sito web NON È CONFORME ai requisiti di accessibilità"
    
    def _get_compliance_class(self) -> str:
        """Ottiene classe CSS per stato conformità"""
        if self.compliance_status == "fully_compliant":
            return "fully-compliant"
        elif self.compliance_status == "partially_compliant":
            return "partially-compliant"
        else:
            return "non-compliant"
    
    def _generate_compliance_section(self) -> str:
        """Genera sezione conformità"""
        html = ""
        
        if self.compliance_status == "fully_compliant":
            html = """
            <div class="success">
                <p>✅ Il sito web rispetta tutti i requisiti delle WCAG 2.1 Livello AA senza eccezioni.</p>
            </div>
            """
        else:
            html = f"""
            <p>Il sito web è <strong>{self.compliance_status.replace('_', ' ')}</strong> 
            a causa dei seguenti elementi:</p>
            """
            
            if self.non_compliant_content:
                html += """
                <h3>Contenuti non conformi</h3>
                <p>I contenuti sotto elencati sono non conformi per i seguenti motivi:</p>
                <ul>
                """
                for item in self.non_compliant_content:
                    html += f"""
                    <li>
                        <strong>{item.get('content', '')}</strong>: 
                        {item.get('reason', '')} 
                        (WCAG {item.get('wcag_criteria', '')})
                    </li>
                    """
                html += "</ul>"
            
            if self.disproportionate_burden:
                html += """
                <h3>Onere sproporzionato</h3>
                <p>I seguenti contenuti sono esclusi per onere sproporzionato:</p>
                <ul>
                """
                for item in self.disproportionate_burden:
                    html += f"<li>{item.get('content', '')}: {item.get('justification', '')}</li>"
                html += "</ul>"
        
        return html
    
    def _generate_evaluation_details(self) -> str:
        """Genera dettagli valutazione"""
        html = ""
        
        if self.evaluation_report_url:
            html += f"""
            <p>Il report completo di valutazione è disponibile all'indirizzo: 
            <a href="{self.evaluation_report_url}">{self.evaluation_report_url}</a></p>
            """
        
        if self.last_review_date:
            html += f"<p>Ultima revisione della dichiarazione: <strong>{self.last_review_date}</strong></p>"
        
        html += f"""
        <h3>Strumenti di testing utilizzati:</h3>
        <ul>
            {''.join(f'<li>{tool}</li>' for tool in self.testing_tools)}
        </ul>
        """
        
        return html
    
    def _generate_technical_info(self) -> str:
        """Genera informazioni tecniche"""
        return f"""
        <table>
            <tr>
                <th>Aspetto</th>
                <th>Dettagli</th>
            </tr>
            <tr>
                <td>Standard WCAG</td>
                <td>Versione {self.wcag_version} - Livello {self.wcag_level}</td>
            </tr>
            <tr>
                <td>Tecnologie utilizzate</td>
                <td>{', '.join(self.technologies_used)}</td>
            </tr>
            <tr>
                <td>Metodo di valutazione</td>
                <td>{self.evaluation_method}</td>
            </tr>
            <tr>
                <td>Data ultima valutazione</td>
                <td>{self.evaluation_date}</td>
            </tr>
        </table>
        """
    
    def _generate_known_issues_section(self) -> str:
        """Genera sezione problemi noti"""
        if not self.known_issues:
            return ""
        
        html = """
        <section class="section">
            <h2>8. Problemi Noti e Alternative</h2>
            <p>Siamo consapevoli dei seguenti problemi di accessibilità:</p>
            <table>
                <tr>
                    <th>Problema</th>
                    <th>Impatto</th>
                    <th>Soluzione Alternativa</th>
                </tr>
        """
        
        for issue in self.known_issues:
            html += f"""
                <tr>
                    <td>{issue.get('problem', '')}</td>
                    <td>{issue.get('impact', '')}</td>
                    <td>{issue.get('workaround', 'In corso di risoluzione')}</td>
                </tr>
            """
        
        html += """
            </table>
        </section>
        """
        
        return html
    
    def _generate_compatibility_section(self) -> str:
        """Genera sezione compatibilità"""
        return f"""
        <h3>Browser supportati:</h3>
        <ul>
            {''.join(f'<li>{browser}</li>' for browser in self.compatibility_info.get('browsers', []))}
        </ul>
        
        <h3>Screen reader testati:</h3>
        <ul>
            {''.join(f'<li>{sr}</li>' for sr in self.compatibility_info.get('screen_readers', []))}
        </ul>
        
        <h3>Sistemi operativi:</h3>
        <ul>
            {''.join(f'<li>{os}</li>' for os in self.compatibility_info.get('operating_systems', []))}
        </ul>
        """
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Converte in JSON"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    def save_html(self, filepath: Path) -> None:
        """
        Salva dichiarazione come HTML
        
        Args:
            filepath: Path del file HTML
        """
        html = self.generate_html()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"Dichiarazione accessibilità salvata in {filepath}")


def generate_statement_from_scan(scan_results: Dict[str, Any], 
                                organization_data: Dict[str, Any]) -> AccessibilityStatement:
    """
    Genera dichiarazione da risultati scansione
    
    Args:
        scan_results: Risultati normalizzati scansione
        organization_data: Dati organizzazione
        
    Returns:
        AccessibilityStatement configurata
    """
    # Determina stato conformità
    compliance = scan_results.get("compliance", {})
    score = compliance.get("overall_score", 0)
    
    if score >= 95:
        compliance_status = "fully_compliant"
    elif score >= 60:
        compliance_status = "partially_compliant"
    else:
        compliance_status = "non_compliant"
    
    # Crea statement
    statement = AccessibilityStatement(
        organization_name=organization_data.get("name", ""),
        organization_type=organization_data.get("type", "privato"),
        website_name=organization_data.get("website_name", "Sito Web"),
        website_url=scan_results.get("url", ""),
        statement_url=f"{scan_results.get('url', '')}/accessibilita",
        compliance_status=compliance_status,
        feedback_email=organization_data.get("email", "accessibilita@example.com"),
        wcag_version=compliance.get("wcag_version", "2.1"),
        wcag_level=compliance.get("wcag_level", "AA")
    )
    
    # Aggiungi contenuti non conformi
    errors = scan_results.get("detailed_results", {}).get("errors", [])
    for error in errors[:10]:  # Top 10 errori
        if error.get("severity") in ["critical", "high"]:
            statement.non_compliant_content.append({
                "content": error.get("description", ""),
                "reason": f"Non rispetta il criterio di successo",
                "wcag_criteria": error.get("wcag_criteria", "")
            })
    
    # Aggiungi problemi noti
    for error in errors[:5]:  # Top 5 per problemi noti
        statement.known_issues.append({
            "problem": error.get("description", ""),
            "impact": f"Impatta utenti con {_get_user_impact(error)}",
            "workaround": error.get("remediation", "In corso di risoluzione")
        })
    
    return statement


def _get_user_impact(error: Dict) -> str:
    """
    Determina impatto utenti da tipo errore
    
    Args:
        error: Dizionario errore
        
    Returns:
        Descrizione impatto
    """
    code = error.get("code", "").lower()
    
    if "alt" in code or "image" in code:
        return "disabilità visive"
    elif "contrast" in code or "color" in code:
        return "ipovisione"
    elif "keyboard" in code or "focus" in code:
        return "disabilità motorie"
    elif "caption" in code or "audio" in code:
        return "disabilità uditive"
    elif "heading" in code or "structure" in code:
        return "disabilità cognitive"
    else:
        return "diverse disabilità"