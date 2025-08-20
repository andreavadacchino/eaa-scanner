from __future__ import annotations

import html
import logging
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from .llm_integration import LLMIntegration
from .config import Config

logger = logging.getLogger(__name__)


def generate_html_report(data: Dict[str, Any], config: Config = None) -> str:
    """Genera un report HTML dai dati normalizzati usando Jinja2 con supporto LLM"""
    
    # Arricchisci i dati con contenuti LLM se disponibile
    if config:
        data = enhance_data_with_llm(data, config)
    
    # Prepara i dati per il template professionale
    data = prepare_professional_report_data(data)
    
    # Trova il path dei template - priorità al template professionale v2
    template_dir = Path(__file__).parent / "templates"
    if template_dir.exists():
        # Usa il nuovo template professionale v2
        try:
            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            # Usa il nuovo template professionale
            template = env.get_template("report_professional_v2.html")
            return template.render(**data)
        except Exception as e:
            logger.warning(f"Errore caricamento template professionale v2: {e}")
            # Prova con il template minimal come fallback
            try:
                template = env.get_template("report_minimal.html")
                return template.render(**data)
            except Exception as e2:
                logger.warning(f"Errore caricamento template minimal: {e2}")
    
    # Fallback: genera HTML inline
    return generate_html_report_inline(data)


def prepare_professional_report_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara i dati per il template professionale v2"""
    from datetime import datetime
    
    # Copia i dati esistenti
    prepared = dict(data)
    
    # Aggiungi campi mancanti con valori di default
    prepared.setdefault('company_name', 'N/A')
    prepared.setdefault('url', 'N/A')
    prepared.setdefault('scan_date', datetime.now().strftime('%d %B %Y'))
    prepared.setdefault('current_year', datetime.now().year)
    prepared.setdefault('provider', 'Team Accessibilità')
    prepared.setdefault('contact_email', prepared.get('email', 'info@accessibility.it'))
    
    # Prepara metriche principali
    compliance = prepared.get('compliance', {})
    
    # Conta errori e avvisi PRIMA di calcolare lo score
    detailed = prepared.get('detailed_results', {})
    error_list = detailed.get('errors', [])
    warning_list = detailed.get('warnings', [])
    
    # Conta errori totali (somma dei count di ogni errore)
    total_errors = sum(e.get('count', 1) for e in error_list)
    total_warnings = sum(w.get('count', 1) for w in warning_list)
    
    prepared['total_errors'] = total_errors
    prepared['total_warnings'] = total_warnings
    
    # Calcola score basato su errori e avvisi
    # Formula: 100 - (errori * 5) - (avvisi * 1), minimo 0
    calculated_score = max(0, 100 - (total_errors * 5) - (total_warnings * 1))
    
    # Usa lo score esistente se disponibile, altrimenti usa quello calcolato
    prepared['compliance_score'] = compliance.get('score', calculated_score)
    
    # Determina il livello di conformità basato su errori e score
    if total_errors == 0 and total_warnings == 0:
        compliance_level = 'conforme'
    elif total_errors == 0 and total_warnings > 0:
        compliance_level = 'parzialmente_conforme'
    elif prepared['compliance_score'] >= 60:
        compliance_level = 'parzialmente_conforme'
    else:
        compliance_level = 'non_conforme'
    
    # Usa il livello esistente se disponibile, altrimenti usa quello calcolato
    actual_level = compliance.get('level', compliance_level)
    prepared['compliance_status'] = actual_level.replace('_', '-')
    
    # Mappa il testo di conformità
    compliance_map = {
        'conforme': 'piena conformità',
        'parzialmente_conforme': 'parziale conformità', 
        'non_conforme': 'non conformità'
    }
    prepared['compliance_text'] = compliance_map.get(
        actual_level,
        'conformità da verificare'
    )
    prepared['pages_scanned'] = prepared.get('pages_analyzed', 1)
    
    # Prepara scanner usati
    scanners = prepared.get('scanners', [])
    if isinstance(scanners, list):
        prepared['scanners_used'] = scanners
    else:
        prepared['scanners_used'] = ['WAVE', 'Axe-core', 'Pa11y', 'Lighthouse']
    
    # Aggiungi informazioni specifiche sul test
    prepared['test_url'] = prepared.get('url', 'URL non specificato')
    prepared['test_datetime'] = prepared.get('scan_date', 'Data non specificata')
    prepared['test_scope'] = prepared.get('pages_analyzed', 1)
    
    # Descrizioni scanner
    prepared['scanner_descriptions'] = {
        'WAVE': 'WebAIM WAVE - Analisi accessibilità con focus su screen reader',
        'Axe-core': 'Deque Axe - Engine di test WCAG automatizzato',
        'Pa11y': 'Pa11y - Test di accessibilità da linea di comando',
        'Lighthouse': 'Google Lighthouse - Performance e accessibilità'
    }
    
    # Analisi P.O.U.R. con conteggio corretto basato su criteri WCAG
    pour_status = compliance.get('pour_status', {})
    
    # Mapping WCAG criteria to P.O.U.R. principles
    wcag_pour_mapping = {
        # Perceivable
        '1.1': 'perceivable', '1.2': 'perceivable', '1.3': 'perceivable', '1.4': 'perceivable',
        # Operable
        '2.1': 'operable', '2.2': 'operable', '2.3': 'operable', '2.4': 'operable', '2.5': 'operable',
        # Understandable
        '3.1': 'understandable', '3.2': 'understandable', '3.3': 'understandable',
        # Robust
        '4.1': 'robust'
    }
    
    # Conta errori per principio WCAG basandosi sui criteri reali
    perceivable_errors = 0
    operable_errors = 0
    understandable_errors = 0
    robust_errors = 0
    
    for error in error_list:
        count = error.get('count', 1)
        wcag_ref = error.get('wcag_criteria', '')
        description = error.get('description', '').lower()
        message = error.get('message', '').lower()
        
        # Prova prima con il criterio WCAG se disponibile
        principle_found = False
        if wcag_ref:
            for prefix, principle in wcag_pour_mapping.items():
                if wcag_ref.startswith(prefix):
                    if principle == 'perceivable':
                        perceivable_errors += count
                    elif principle == 'operable':
                        operable_errors += count
                    elif principle == 'understandable':
                        understandable_errors += count
                    elif principle == 'robust':
                        robust_errors += count
                    principle_found = True
                    break
        
        # Se non trovato, usa analisi delle parole chiave nel description/message
        if not principle_found:
            text_to_check = f"{description} {message}"
            
            if any(kw in text_to_check for kw in ['alt', 'image', 'contrast', 'color', 'visual', 'text alternative', 'caption', 'audio', 'video']):
                perceivable_errors += count
            elif any(kw in text_to_check for kw in ['keyboard', 'focus', 'navigation', 'click', 'mouse', 'pointer', 'gesture', 'motion']):
                operable_errors += count
            elif any(kw in text_to_check for kw in ['label', 'form', 'language', 'instruction', 'error', 'input', 'help']):
                understandable_errors += count
            elif any(kw in text_to_check for kw in ['aria', 'role', 'markup', 'parse', 'valid', 'semantic', 'name']):
                robust_errors += count
            else:
                # Default: se non categorizzato, consideralo un problema di robustezza
                robust_errors += count
    
    prepared['pour_analysis'] = [
        {
            'name': 'Percepibile (Perceivable)',
            'status': 'conforme' if perceivable_errors == 0 else ('partial' if perceivable_errors < 5 else 'non-conforme'),
            'status_text': 'Conforme' if perceivable_errors == 0 else ('Parzialmente Conforme' if perceivable_errors < 5 else 'Non Conforme'),
            'issue_count': perceivable_errors,
            'notes': 'Nessun problema rilevato' if perceivable_errors == 0 else 'Problemi con testi alternativi e contrasto colore'
        },
        {
            'name': 'Operabile (Operable)',
            'status': 'conforme' if operable_errors == 0 else ('partial' if operable_errors < 5 else 'non-conforme'),
            'status_text': 'Conforme' if operable_errors == 0 else ('Parzialmente Conforme' if operable_errors < 5 else 'Non Conforme'),
            'issue_count': operable_errors,
            'notes': 'Nessun problema rilevato' if operable_errors == 0 else 'Problemi di navigazione da tastiera'
        },
        {
            'name': 'Comprensibile (Understandable)',
            'status': 'conforme' if understandable_errors == 0 else ('partial' if understandable_errors < 5 else 'non-conforme'),
            'status_text': 'Conforme' if understandable_errors == 0 else ('Parzialmente Conforme' if understandable_errors < 5 else 'Non Conforme'),
            'issue_count': understandable_errors,
            'notes': 'Nessun problema rilevato' if understandable_errors == 0 else 'Problemi con etichette e linguaggio'
        },
        {
            'name': 'Robusto (Robust)',
            'status': 'conforme' if robust_errors == 0 else ('partial' if robust_errors < 5 else 'non-conforme'),
            'status_text': 'Conforme' if robust_errors == 0 else ('Parzialmente Conforme' if robust_errors < 5 else 'Non Conforme'),
            'issue_count': robust_errors,
            'notes': 'Nessun problema rilevato' if robust_errors == 0 else 'Problemi con markup e compatibilità'
        }
    ]
    
    # Prepara categorie di problemi
    categories = {}
    for error in detailed.get('errors', []):
        cat = error.get('category', 'Altri problemi')
        if cat not in categories:
            categories[cat] = {
                'name': cat,
                'key': cat.lower().replace(' ', '_'),
                'count': 0,
                'items': [],
                'impact': 'Alto',
                'wcag_criteria': set()
            }
        categories[cat]['count'] += 1
        categories[cat]['items'].append(error)
        if error.get('wcag_criteria'):
            categories[cat]['wcag_criteria'].add(error['wcag_criteria'])
    
    prepared['issue_categories'] = []
    for cat_name, cat_data in categories.items():
        prepared['issue_categories'].append({
            'name': cat_name,
            'key': cat_data['key'],
            'impact': cat_data['impact'],
            'description': f"Sono stati rilevati {cat_data['count']} problemi in questa categoria.",
            'wcag_criteria': list(cat_data['wcag_criteria']),
            'actions': [
                f"Correggere tutti i {cat_data['count']} problemi identificati",
                "Implementare controlli automatici per prevenire regressioni",
                "Formare il team sulle best practice correlate"
            ]
        })
    
    # Prepara problemi dettagliati con informazioni aggiuntive
    prepared['detailed_issues'] = []
    
    # Raggruppa errori simili per componente/pattern con logica intelligente
    error_groups = {}
    
    # Funzione helper per estrarre pattern comuni
    def extract_pattern_key(error):
        """Estrae una chiave di raggruppamento intelligente basata sul tipo di errore"""
        desc = error.get('description', '').lower()
        wcag = error.get('wcag_criteria', 'N/A')
        code = error.get('code', '').lower()
        
        # Identifica pattern comuni per raggruppamento più intelligente
        if 'alt' in desc or 'alternative text' in desc or 'alt attribute' in code:
            return f"images_alt_text_{wcag}"
        elif 'contrast' in desc or 'color' in desc:
            return f"color_contrast_{wcag}"
        elif 'label' in desc or 'form' in desc:
            return f"form_labels_{wcag}"
        elif 'heading' in desc or 'h1' in desc or 'h2' in desc or 'hierarchy' in desc:
            return f"heading_structure_{wcag}"
        elif 'keyboard' in desc or 'focus' in desc or 'tab' in desc:
            return f"keyboard_navigation_{wcag}"
        elif 'aria' in desc or 'role' in desc:
            return f"aria_attributes_{wcag}"
        elif 'link' in desc or 'anchor' in desc:
            return f"links_navigation_{wcag}"
        elif 'language' in desc or 'lang' in desc:
            return f"language_declaration_{wcag}"
        elif 'video' in desc or 'audio' in desc or 'media' in desc:
            return f"multimedia_accessibility_{wcag}"
        elif 'button' in desc:
            return f"button_accessibility_{wcag}"
        else:
            # Fallback: usa primi 30 caratteri della descrizione
            clean_desc = ''.join(c if c.isalnum() else '_' for c in desc[:30])
            return f"{clean_desc}_{wcag}"
    
    for error in detailed.get('errors', []):
        # Crea una chiave di raggruppamento intelligente
        group_key = extract_pattern_key(error)
        
        if group_key not in error_groups:
            error_groups[group_key] = {
                'errors': [],
                'total_count': 0,
                'selectors': set(),
                'pages': set(),
                'sources': set()  # Aggiungi tracciamento scanner
            }
        
        error_groups[group_key]['errors'].append(error)
        error_groups[group_key]['total_count'] += error.get('count', 1)
        
        # Aggiungi selettori se disponibili
        if error.get('selector'):
            error_groups[group_key]['selectors'].add(error['selector'])
        if error.get('page_url'):
            error_groups[group_key]['pages'].add(error['page_url'])
        if error.get('source'):
            error_groups[group_key]['sources'].add(error['source'])
    
    # Crea issues dettagliate con raggruppamento
    for group_key, group_data in list(error_groups.items())[:20]:  # Limita a 20 gruppi
        first_error = group_data['errors'][0]
        
        # Crea una descrizione più utile
        description = first_error.get('description', first_error.get('message', ''))
        if group_data['total_count'] > 1:
            description = f"{description} ({group_data['total_count']} occorrenze)"
        
        # Crea azione specifica basata sul tipo di errore
        action = first_error.get('remediation', '')
        if not action or action == 'Correggere secondo le linee guida WCAG':
            if 'contrast' in description.lower():
                action = 'Aumentare il contrasto a minimo 4.5:1 per testo normale, 3:1 per testo grande'
            elif 'alt' in description.lower():
                action = 'Aggiungere attributo alt descrittivo alle immagini'
            elif 'label' in description.lower():
                action = 'Associare label esplicite ai campi form usando for/id o aria-label'
            elif 'keyboard' in description.lower():
                action = 'Garantire accessibilità da tastiera con tabindex appropriato'
            else:
                action = 'Consultare WCAG ' + first_error.get('wcag_criteria', '2.1') + ' per i requisiti specifici'
        
        # Genera esempio corretto basato sul tipo di errore e codice
        code_snippet = first_error.get('code_snippet', '') or first_error.get('context', '')
        fixed_example = first_error.get('fixed_example', '')
        
        if code_snippet and not fixed_example:
            # Genera esempio corretto basato sul tipo di problema
            if 'alt' in description.lower() and '<img' in code_snippet:
                fixed_example = code_snippet.replace('<img', '<img alt="Descrizione significativa dell\'immagine"')
            elif 'contrast' in description.lower():
                fixed_example = '/* CSS con contrasto corretto */\ncolor: #212121; /* Contrasto 12.6:1 su sfondo bianco */\nbackground-color: #ffffff;'
            elif 'label' in description.lower() and '<input' in code_snippet:
                # Estrai id se presente
                import re
                id_match = re.search(r'id="([^"]*)"', code_snippet)
                if id_match:
                    input_id = id_match.group(1)
                    fixed_example = f'<label for="{input_id}">Etichetta descrittiva</label>\n{code_snippet}'
                else:
                    fixed_example = code_snippet.replace('<input', '<input aria-label="Etichetta descrittiva"')
            elif 'heading' in description.lower():
                fixed_example = '<!-- Struttura heading corretta -->\n<h1>Titolo principale pagina</h1>\n  <h2>Sezione principale</h2>\n    <h3>Sottosezione</h3>'
            elif 'aria' in description.lower():
                fixed_example = '<!-- Aggiungi attributi ARIA appropriati -->\n<div role="navigation" aria-label="Menu principale">\n  <!-- contenuto navigazione -->\n</div>'
        
        prepared['detailed_issues'].append({
            'category': first_error.get('category', 'Non categorizzato'),
            'description': description,
            'count': group_data['total_count'],
            'wcag_criterion': first_error.get('wcag_criteria', 'N/A'),
            'priority': first_error.get('severity', 'Medium').capitalize(),
            'action': action,
            'selectors': list(group_data['selectors'])[:3] if group_data['selectors'] else [],
            'pages': list(group_data['pages'])[:3] if group_data['pages'] else [],
            'code_snippet': code_snippet,
            'fixed_example': fixed_example
        })
    
    # Prepara piano di remediation dettagliato basato sugli errori trovati
    from datetime import datetime, timedelta
    today = datetime.now()
    
    remediation_actions = []
    
    # Crea azioni basate sugli errori reali trovati con dettagli operativi specifici
    if perceivable_errors > 0:
        # Analizza tipo di errori per dare note tecniche più specifiche
        tech_notes = []
        if any('alt' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Script automatico per audit immagini senza alt')
        if any('contrast' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Tool: Colour Contrast Analyser')
        if any('video' in str(e).lower() or 'audio' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Sottotitoli con formato WebVTT')
            
        remediation_actions.append({
            'intervention': f'Correzione {perceivable_errors} problemi di percezione (alt text, contrasto, multimedia)',
            'area': 'Percepibile',
            'impact': 'Critico' if perceivable_errors > 10 else 'Alto',
            'priority': 'Critica' if perceivable_errors > 20 else 'Alta',
            'owner': 'Frontend Developer + Content Team',
            'status': 'Da iniziare',
            'deadline': (today + timedelta(days=7 if perceivable_errors < 10 else 14)).strftime('%d/%m/%Y'),
            'technical_notes': '. '.join(tech_notes) if tech_notes else 'Axe DevTools per identificare elementi. Contrasto minimo 4.5:1 (AA) o 7:1 (AAA)'
        })
    
    if operable_errors > 0:
        tech_notes = []
        if any('keyboard' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Implementare roving tabindex per componenti complessi')
        if any('focus' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('CSS :focus-visible per indicatori visibili')
        if any('skip' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Skip links nascosti con classe .sr-only')
            
        remediation_actions.append({
            'intervention': f'Fix {operable_errors} problemi di navigazione e interazione',
            'area': 'Operabile',
            'impact': 'Critico' if operable_errors > 10 else 'Alto',
            'priority': 'Critica' if operable_errors > 15 else 'Alta',
            'owner': 'Frontend Developer + QA Team',
            'status': 'Da iniziare',
            'deadline': (today + timedelta(days=10 if operable_errors < 10 else 21)).strftime('%d/%m/%Y'),
            'technical_notes': '. '.join(tech_notes) if tech_notes else 'Test completo solo tastiera. Focus trap per modali. Shortcuts documentate'
        })
    
    if understandable_errors > 0:
        tech_notes = []
        if any('label' in str(e).lower() or 'form' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('React Hook Form con validazione accessibile')
        if any('language' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('Attributo lang su HTML e contenuti multilingua')
        if any('error' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('aria-live="polite" per messaggi di errore')
            
        remediation_actions.append({
            'intervention': f'Sistemazione {understandable_errors} problemi di comprensibilità e usabilità',
            'area': 'Comprensibile',
            'impact': 'Alto' if understandable_errors > 5 else 'Medio',
            'priority': 'Alta' if understandable_errors > 10 else 'Media',
            'owner': 'UX Writer + Frontend Dev + UX Designer',
            'status': 'Da iniziare',
            'deadline': (today + timedelta(days=14 if understandable_errors < 10 else 28)).strftime('%d/%m/%Y'),
            'technical_notes': '. '.join(tech_notes) if tech_notes else 'Form validation library accessibile. Microcopy review. Test con utenti'
        })
    
    if robust_errors > 0:
        tech_notes = []
        if any('aria' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('ARIA Authoring Practices Guide 1.2')
        if any('parse' in str(e).lower() or 'valid' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('W3C Validator + prettier per formatting')
        if any('semantic' in str(e).lower() for e in detailed.get('errors', [])):
            tech_notes.append('HTML5 semantic elements: main, nav, aside, section')
            
        remediation_actions.append({
            'intervention': f'Correzione {robust_errors} problemi di robustezza e compatibilità',
            'area': 'Robusto',
            'impact': 'Alto' if robust_errors > 10 else 'Medio',
            'priority': 'Alta' if robust_errors > 20 else 'Media',
            'owner': 'Senior Frontend Developer',
            'status': 'Da iniziare',
            'deadline': (today + timedelta(days=21 if robust_errors < 10 else 35)).strftime('%d/%m/%Y'),
            'technical_notes': '. '.join(tech_notes) if tech_notes else 'Validare con W3C. ARIA corretto. Test NVDA + JAWS + VoiceOver'
        })
    
    # Aggiungi sempre test e validazione finale
    remediation_actions.append({
        'intervention': 'Test completo con utenti con disabilità',
        'area': 'Tutte',
        'impact': 'Critico',
        'priority': 'Alta',
        'owner': 'QA Team + Accessibility Expert',
        'status': 'Da pianificare',
        'deadline': (today + timedelta(days=30)).strftime('%d/%m/%Y'),
        'technical_notes': 'Coinvolgere almeno 3 utenti con diverse disabilità. Test con screen reader multipli'
    })
    
    remediation_actions.append({
        'intervention': 'Implementazione monitoraggio continuo accessibilità',
        'area': 'Processo',
        'impact': 'Alto',
        'priority': 'Media',
        'owner': 'DevOps Team',
        'status': 'Da pianificare',
        'deadline': (today + timedelta(days=45)).strftime('%d/%m/%Y'),
        'technical_notes': 'Integrare axe-core in CI/CD pipeline. Setup monitoring dashboard'
    })
    
    prepared['remediation_actions'] = remediation_actions
    
    # Identifica aree principali dei problemi
    main_areas = set()
    for error in detailed.get('errors', [])[:10]:
        if 'alt' in error.get('description', '').lower() or 'image' in error.get('description', '').lower():
            main_areas.add('percezione')
        if 'contrast' in error.get('description', '').lower() or 'color' in error.get('description', '').lower():
            main_areas.add('contrasto')
        if 'keyboard' in error.get('description', '').lower() or 'focus' in error.get('description', '').lower():
            main_areas.add('operabilità')
        if 'label' in error.get('description', '').lower() or 'form' in error.get('description', '').lower():
            main_areas.add('comprensibilità')
    
    prepared['main_issue_areas'] = list(main_areas) if main_areas else ['accessibilità generale']
    
    # Distribuzione severità
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for error in detailed.get('errors', []):
        sev = error.get('severity', 'medium').lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    
    if severity_counts['critical'] > 0:
        prepared['severity_distribution'] = 'critica'
    elif severity_counts['high'] > 0:
        prepared['severity_distribution'] = 'alta'
    elif severity_counts['medium'] > 0:
        prepared['severity_distribution'] = 'media'
    else:
        prepared['severity_distribution'] = 'bassa'
    
    return prepared


def enhance_data_with_llm(data: Dict[str, Any], config: Config) -> Dict[str, Any]:
    """Arricchisce i dati con contenuti generati via LLM"""
    if not config or not config.llm_enabled:
        logger.debug("LLM non abilitato, skip enhancement")
        return data
    
    try:
        llm = LLMIntegration(config)
        
        # Copia i dati per non modificare l'originale
        enhanced_data = data.copy()
        
        # Genera executive summary se non presente
        if not enhanced_data.get("executive_summary"):
            logger.debug("Generazione executive summary via LLM")
            enhanced_data["executive_summary"] = llm.generate_executive_summary(data)
        
        # Genera raccomandazioni se non presenti o se LLM è abilitato per sovrascrivere
        if not enhanced_data.get("recommendations") or llm.is_enabled():
            logger.debug("Generazione raccomandazioni tecniche via LLM")
            enhanced_data["recommendations"] = llm.generate_technical_recommendations(data)
        
        # Genera piano di remediation
        if not enhanced_data.get("remediation_plan"):
            logger.debug("Generazione piano remediation via LLM")
            enhanced_data["remediation_plan"] = llm.generate_remediation_plan(data)
        
        # Flag per indicare che LLM è stato usato
        enhanced_data["llm_enhanced"] = llm.is_enabled()
        enhanced_data["llm_model"] = config.llm_model_primary if llm.is_enabled() else None
        
        logger.info(f"Dati arricchiti con LLM: {llm.is_enabled()}")
        return enhanced_data
        
    except Exception as e:
        logger.error(f"Errore durante enhancement LLM: {e}")
        return data


def generate_html_report_inline(data: Dict[str, Any]) -> str:
    """Genera un report HTML inline come fallback"""
    c = data.get("compliance", {})
    dr = data.get("detailed_results", {})

    def esc(x: Any) -> str:
        return html.escape(str(x) if x is not None else "")

    def compliance_badge(level: str) -> str:
        cls = {
            "conforme": "conforme",
            "parzialmente_conforme": "parzialmente_conforme",
            "non_conforme": "non_conforme",
        }.get(level, "unknown")
        label = {
            "conforme": "Conforme",
            "parzialmente_conforme": "Parzialmente Conforme",
            "non_conforme": "Non Conforme",
        }.get(level, "Da Verificare")
        return f'<span class="compliance-badge {esc(cls)}">{esc(label)}</span>'

    errors = dr.get("errors", [])
    warnings = dr.get("warnings", [])

    def issues_html(items, title, is_error=True):
        if not items:
            return ""
        out = [f"<div class=\"issues-section\"><h2>{esc(title)}</h2>"]
        for it in items[:10]:
            sev = esc(it.get("severity", "medium"))
            desc = esc(it.get("description", it.get("message", "Issue")))
            wcag = esc(it.get("wcag_criteria", "—"))
            src = esc(it.get("source", "—"))
            cnt = esc(it.get("count", 1))
            rem = esc(it.get("remediation", "—"))
            out.append(
                f"<div class=\"issue-item {sev}\"><div class=\"issue-header\"><strong>{desc}</strong><span>{'ERROR' if is_error else 'WARNING'}</span></div><div class=\"issue-content\"><p><strong>Remediation:</strong> {rem}</p><div class=\"issue-meta\"><span>WCAG: {wcag}</span><span>Scanner: {src}</span><span>Occorrenze: {cnt}</span></div></div></div>"
            )
        out.append("</div>")
        return "\n".join(out)

    # Contenuti LLM opzionali
    executive_summary = data.get("executive_summary", "")
    recommendations = data.get("recommendations", [])
    remediation_plan = data.get("remediation_plan", {})
    llm_enhanced = data.get("llm_enhanced", False)
    
    def render_executive_summary():
        if not executive_summary:
            return ""
        return f"""
        <div class="section">
          <h2>📋 Executive Summary</h2>
          <div class="executive-summary">
            <p>{esc(executive_summary)}</p>
            {f'<div class="llm-note">✨ Generato automaticamente via AI</div>' if llm_enhanced else ''}
          </div>
        </div>
        """
    
    def render_recommendations():
        if not recommendations:
            return ""
        out = ['<div class="section"><h2>💡 Raccomandazioni Tecniche</h2>']
        for rec in recommendations[:5]:
            priority_class = rec.get('priority', 'media').lower()
            effort_badge = rec.get('estimated_effort', 'medio')
            actions_html = ""
            if rec.get('actions'):
                actions_html = "<ul>" + "".join([f"<li>{esc(action)}</li>" for action in rec['actions'][:4]]) + "</ul>"
            
            out.append(f"""
            <div class="recommendation-item priority-{priority_class}">
              <div class="rec-header">
                <h3>{esc(rec.get('title', 'Raccomandazione'))}</h3>
                <div class="rec-badges">
                  <span class="priority-badge {priority_class}">{esc(rec.get('priority', 'Media'))}</span>
                  <span class="effort-badge">{esc(effort_badge)}</span>
                </div>
              </div>
              <p class="rec-description">{esc(rec.get('description', ''))}</p>
              {actions_html}
              {f'<div class="wcag-ref">📋 WCAG: {esc(rec.get("wcag_criteria", ""))}</div>' if rec.get('wcag_criteria') else ''}
            </div>
            """)
        out.append('</div>')
        return "\n".join(out)
    
    def render_remediation_plan():
        if not remediation_plan or not remediation_plan.get('fasi'):
            return ""
        
        phases_html = ""
        for fase in remediation_plan.get('fasi', [])[:4]:
            activities = ""
            if fase.get('attivita'):
                activities = "<ul>" + "".join([f"<li>{esc(att)}</li>" for att in fase['attivita'][:3]]) + "</ul>"
            
            phases_html += f"""
            <div class="phase-item">
              <div class="phase-header">
                <h4>{esc(fase.get('nome', 'Fase'))}</h4>
                <span class="phase-duration">{esc(fase.get('durata_stimata', 'N/A'))}</span>
              </div>
              <div class="phase-priority priority-{esc(fase.get('priorita', 'media'))}">Priorità: {esc(fase.get('priorita', 'Media'))}</div>
              <div class="phase-objectives">
                <strong>Obiettivi:</strong> {', '.join([esc(obj) for obj in fase.get('obiettivi', [])])}
              </div>
              {activities}
            </div>
            """
        
        return f"""
        <div class="section">
          <h2>🎯 Piano di Remediation</h2>
          <div class="remediation-plan">
            {phases_html}
            {f'<div class="llm-note">✨ Piano generato automaticamente via AI</div>' if llm_enhanced else ''}
          </div>
        </div>
        """
    
    html_doc = f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Report Accessibilità EAA - {esc(data.get('company_name','—'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #222; background: #f7f7f8; margin: 0; }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .header {{ background: linear-gradient(135deg, #2c3e50, #3498db); color: #fff; padding: 32px; border-radius: 12px; }}
    .header h1 {{ margin: 0 0 8px 0; }}
    .metadata {{ display: flex; gap: 12px; flex-wrap: wrap; opacity: .9; font-size: 14px; }}
    .score-section {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 16px; margin: 24px 0; }}
    .score-card {{ background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }}
    .score-card h3 {{ margin: 0 0 8px 0; font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: .5px; }}
    .value {{ font-size: 28px; color: #2c3e50; font-weight: bold; }}
    .compliance-badge {{ display:inline-block; padding: 8px 14px; border-radius: 999px; font-weight: 700; font-size: 12px; }}
    .compliance-badge.conforme {{ background:#d4edda; color:#155724; }}
    .compliance-badge.parzialmente_conforme {{ background:#fff3cd; color:#856404; }}
    .compliance-badge.non_conforme {{ background:#f8d7da; color:#721c24; }}
    .section {{ background:#fff; border-radius:10px; box-shadow: 0 2px 12px rgba(0,0,0,.06); padding:20px; margin-bottom:20px; }}
    .issues-section {{ background:#fff; border-radius:10px; box-shadow: 0 2px 12px rgba(0,0,0,.06); padding:20px; margin-bottom:20px; }}
    .issue-item {{ background:#f8f9fa; margin: 12px 0; border-radius:8px; border-left: 4px solid #3498db; }}
    .issue-item .issue-header {{ background:#3498db; color:#fff; display:flex; justify-content:space-between; align-items:center; padding:10px 14px; }}
    .issue-item.high .issue-header {{ background:#e74c3c; }}
    .issue-item.medium .issue-header {{ background:#f39c12; }}
    .issue-item.low .issue-header {{ background:#3498db; }}
    .issue-content {{ padding: 12px 14px; }}
    .issue-meta {{ display:flex; gap:10px; font-size: 12px; color:#555; margin-top:8px; }}
    .footer {{ text-align:center; color:#555; margin-top: 20px; }}
    .executive-summary {{ background:#e8f4f8; padding:16px; border-radius:8px; margin:12px 0; border-left:4px solid #3498db; }}
    .recommendation-item {{ background:#f8f9fa; margin:12px 0; border-radius:8px; padding:14px; border-left:4px solid #3498db; }}
    .recommendation-item.priority-alta {{ border-left-color:#e74c3c; }}
    .recommendation-item.priority-media {{ border-left-color:#f39c12; }}
    .recommendation-item.priority-bassa {{ border-left-color:#27ae60; }}
    .rec-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
    .rec-badges {{ display:flex; gap:8px; }}
    .priority-badge, .effort-badge {{ padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold; }}
    .priority-badge.alta {{ background:#ffebee; color:#c62828; }}
    .priority-badge.media {{ background:#fff3e0; color:#e65100; }}
    .priority-badge.bassa {{ background:#e8f5e8; color:#2e7d32; }}
    .effort-badge {{ background:#e3f2fd; color:#1565c0; }}
    .wcag-ref {{ font-size:12px; color:#666; margin-top:8px; }}
    .remediation-plan .phase-item {{ background:#f8f9fa; margin:12px 0; padding:14px; border-radius:8px; border-left:4px solid #2c3e50; }}
    .phase-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
    .phase-duration {{ background:#ecf0f1; padding:4px 8px; border-radius:4px; font-size:12px; }}
    .phase-priority {{ margin:8px 0; font-size:12px; padding:4px 8px; border-radius:4px; }}
    .phase-priority.priority-critica {{ background:#ffebee; color:#c62828; }}
    .phase-priority.priority-alta {{ background:#fff3e0; color:#e65100; }}
    .phase-priority.priority-media {{ background:#fff9c4; color:#f57c00; }}
    .phase-objectives {{ margin:8px 0; font-size:14px; }}
    .llm-note {{ background:#e8f5e8; color:#2e7d32; padding:8px 12px; border-radius:4px; font-size:12px; margin-top:12px; text-align:center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🏛️ Report Accessibilità EAA</h1>
      <div class="company">{esc(data.get('company_name','—'))}</div>
      <div class="metadata">
        <span>🌐 {esc(data.get('url','—'))}</span>
        <span>📊 Score: {esc(c.get('overall_score',0))}/100</span>
        <span>✅ Conformità: {compliance_badge(c.get('compliance_level','Da Verificare'))}</span>
      </div>
    </div>

    <div class="score-section">
      <div class="score-card"><h3>Score complessivo</h3><div class="value">{esc(c.get('overall_score',0))}</div></div>
      <div class="score-card"><h3>Errori unici</h3><div class="value">{esc(c.get('total_unique_errors',0))}</div></div>
      <div class="score-card"><h3>Avvisi unici</h3><div class="value">{esc(c.get('total_unique_warnings',0))}</div></div>
      <div class="score-card"><h3>WCAG</h3><div class="value">{esc(c.get('wcag_version',''))} {esc(c.get('wcag_level',''))}</div></div>
    </div>

    {render_executive_summary()}

    {render_recommendations()}

    {render_remediation_plan()}

    {issues_html(errors, '❌ Errori da risolvere', True)}
    {issues_html(warnings, '⚠️ Avvisi da verificare', False)}

    <div class="footer">Report generato automaticamente • EAA Scanner Python</div>
  </div>
</body>
</html>
"""
    return html_doc


def write_report(path: Path, html_text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")
    return path

