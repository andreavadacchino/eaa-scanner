# LLM API Integration Example
# Questo file mostra come implementare gli endpoint per l'integrazione LLM

from flask import Blueprint, request, jsonify
import openai
import time
import threading
from typing import Dict, Any

llm_bp = Blueprint('llm', __name__, url_prefix='/api')

# Store per sessioni di rigenerazione attive
regeneration_sessions: Dict[str, Dict[str, Any]] = {}

@llm_bp.route('/validate_openai_key', methods=['POST'])
def validate_openai_key():
    """Valida una chiave API OpenAI"""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        
        if not api_key or len(api_key) < 20:
            return jsonify({'valid': False, 'error': 'Chiave API troppo corta'})
        
        # Test con una chiamata minimale
        client = openai.OpenAI(api_key=api_key)
        
        # Tentativo di chiamata semplice per validare la chiave
        response = client.models.list()
        
        return jsonify({
            'valid': True,
            'organization': getattr(response, 'organization', None)
        })
        
    except openai.AuthenticationError:
        return jsonify({'valid': False, 'error': 'Chiave API non valida'})
    except openai.RateLimitError:
        return jsonify({'valid': False, 'error': 'Limite di rate superato'})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@llm_bp.route('/llm/regenerate', methods=['POST'])
def start_llm_regeneration():
    """Avvia la rigenerazione del report con LLM"""
    try:
        data = request.get_json()
        scan_session_id = data.get('scan_session_id')
        model = data.get('model', 'gpt-4o')
        api_key = data.get('api_key')
        
        if not all([scan_session_id, api_key]):
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        # Genera ID rigenerazione
        regeneration_id = f"regen_{int(time.time())}_{scan_session_id}"
        
        # Inizializza sessione
        regeneration_sessions[regeneration_id] = {
            'state': 'started',
            'progress_percent': 0,
            'current_step': 'analyzing',
            'scan_session_id': scan_session_id,
            'model': model,
            'created_at': time.time()
        }
        
        # Avvia rigenerazione in background
        thread = threading.Thread(
            target=process_llm_regeneration,
            args=(regeneration_id, scan_session_id, model, api_key)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'regeneration_id': regeneration_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@llm_bp.route('/llm/regeneration_status/<regeneration_id>')
def get_regeneration_status(regeneration_id):
    """Ottiene lo stato della rigenerazione"""
    session = regeneration_sessions.get(regeneration_id)
    
    if not session:
        return jsonify({'error': 'Sessione non trovata'}), 404
    
    return jsonify(session)

def process_llm_regeneration(regeneration_id: str, scan_session_id: str, model: str, api_key: str):
    """Processa la rigenerazione in background"""
    try:
        session = regeneration_sessions[regeneration_id]
        client = openai.OpenAI(api_key=api_key)
        
        # Step 1: Analisi dati (25%)
        session.update({
            'current_step': 'analyzing',
            'progress_percent': 25
        })
        
        # Simula caricamento dati originali
        time.sleep(2)
        original_data = load_scan_results(scan_session_id)
        
        # Step 2: Generazione (50%)
        session.update({
            'current_step': 'generating',
            'progress_percent': 50
        })
        
        # Chiamata OpenAI per analisi
        enhanced_analysis = generate_enhanced_analysis(client, model, original_data)
        
        # Step 3: Miglioramento (75%)
        session.update({
            'current_step': 'enhancing',
            'progress_percent': 75
        })
        
        # Genera report migliorato
        enhanced_report = create_enhanced_report(original_data, enhanced_analysis)
        
        # Step 4: Finalizzazione (100%)
        session.update({
            'current_step': 'finalizing',
            'progress_percent': 100
        })
        
        time.sleep(1)
        
        # Salva risultati
        report_url = save_enhanced_report(scan_session_id, enhanced_report)
        
        session.update({
            'state': 'completed',
            'enhanced_report': enhanced_report,
            'enhanced_report_url': report_url,
            'download_url': f'/api/download_enhanced/{scan_session_id}'
        })
        
    except Exception as e:
        session.update({
            'state': 'failed',
            'error': str(e)
        })

def load_scan_results(scan_session_id: str) -> Dict[str, Any]:
    """Carica i risultati della scansione originale"""
    # Implementazione specifica per caricare i dati dal database
    # Questo è un esempio - sostituire con la logica reale
    return {
        'scan_id': scan_session_id,
        'issues': [],
        'compliance_score': 75,
        'pages_scanned': 10
    }

def generate_enhanced_analysis(client, model: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
    """Genera analisi migliorata con OpenAI"""
    
    # Costruisci prompt per l'analisi
    prompt = f"""
    Analizza questi risultati di accessibilità web e fornisci:
    
    1. Analisi contestuale dei problemi più critici
    2. Raccomandazioni specifiche per il settore
    3. Piano di remediation prioritizzato
    4. Suggerimenti per migliorare l'esperienza utente
    5. Pattern nascosti nei dati
    
    Dati originali:
    {original_data}
    
    Fornisci una risposta strutturata in JSON con le sezioni:
    - critical_analysis
    - sector_recommendations  
    - remediation_plan
    - ux_improvements
    - hidden_patterns
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Sei un esperto di accessibilità web che fornisce analisi approfondite e raccomandazioni pratiche."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parsing della risposta
        analysis_text = response.choices[0].message.content
        
        # Tentativo di parsing JSON, fallback a testo
        try:
            import json
            enhanced_analysis = json.loads(analysis_text)
        except:
            enhanced_analysis = {
                'critical_analysis': analysis_text,
                'raw_response': analysis_text
            }
        
        return enhanced_analysis
        
    except Exception as e:
        return {
            'error': str(e),
            'fallback_analysis': 'Analisi automatica non disponibile'
        }

def create_enhanced_report(original_data: Dict[str, Any], enhanced_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Combina dati originali con analisi migliorata"""
    return {
        'original_data': original_data,
        'enhanced_analysis': enhanced_analysis,
        'generated_at': time.time(),
        'version': '2.0_ai_enhanced'
    }

def save_enhanced_report(scan_session_id: str, enhanced_report: Dict[str, Any]) -> str:
    """Salva il report migliorato e ritorna l'URL"""
    # Implementazione specifica per salvare nel filesystem/database
    # Questo è un esempio - sostituire con la logica reale
    
    filename = f"enhanced_report_{scan_session_id}.html"
    filepath = f"/reports/enhanced/{filename}"
    
    # Genera HTML del report migliorato
    html_content = generate_enhanced_html_report(enhanced_report)
    
    # Salva il file (esempio)
    # with open(filepath, 'w', encoding='utf-8') as f:
    #     f.write(html_content)
    
    return f"/v2/enhanced_preview?scan_id={scan_session_id}"

def generate_enhanced_html_report(enhanced_report: Dict[str, Any]) -> str:
    """Genera il contenuto HTML del report migliorato"""
    
    template = """
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <title>Report Accessibilità Migliorato con AI</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .ai-section { background: #f0f9ff; padding: 20px; margin: 20px 0; border-radius: 8px; }
            .critical { background: #fef2f2; border-left: 4px solid #dc2626; }
            .recommendation { background: #f0fdf4; border-left: 4px solid #059669; }
        </style>
    </head>
    <body>
        <h1>🤖 Report Accessibilità Migliorato con AI</h1>
        
        <div class="ai-section critical">
            <h2>🎯 Analisi Critica AI</h2>
            <p>{critical_analysis}</p>
        </div>
        
        <div class="ai-section recommendation">
            <h2>💡 Raccomandazioni Settoriali</h2>
            <p>{sector_recommendations}</p>
        </div>
        
        <div class="ai-section">
            <h2>📋 Piano di Remediation</h2>
            <p>{remediation_plan}</p>
        </div>
        
        <div class="ai-section">
            <h2>✨ Miglioramenti UX</h2>
            <p>{ux_improvements}</p>
        </div>
        
        <div class="ai-section">
            <h2>🔍 Pattern Identificati</h2>
            <p>{hidden_patterns}</p>
        </div>
        
        <footer>
            <p><em>Report generato con intelligenza artificiale il {timestamp}</em></p>
        </footer>
    </body>
    </html>
    """
    
    import datetime
    
    enhanced_analysis = enhanced_report.get('enhanced_analysis', {})
    
    return template.format(
        critical_analysis=enhanced_analysis.get('critical_analysis', 'Analisi non disponibile'),
        sector_recommendations=enhanced_analysis.get('sector_recommendations', 'Raccomandazioni non disponibili'),
        remediation_plan=enhanced_analysis.get('remediation_plan', 'Piano non disponibile'),
        ux_improvements=enhanced_analysis.get('ux_improvements', 'Suggerimenti non disponibili'),
        hidden_patterns=enhanced_analysis.get('hidden_patterns', 'Pattern non identificati'),
        timestamp=datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    )

# Cleanup automatico sessioni scadute
def cleanup_expired_sessions():
    """Rimuove sessioni scadute (>1 ora)"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, session in regeneration_sessions.items()
        if current_time - session.get('created_at', 0) > 3600
    ]
    
    for session_id in expired_sessions:
        del regeneration_sessions[session_id]

# Registra il blueprint nell'app principale
# app.register_blueprint(llm_bp)