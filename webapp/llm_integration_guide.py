# Guida all'integrazione LLM nell'app Flask esistente
# Questo file mostra come integrare le nuove funzionalità LLM nell'app principale

"""
Per integrare le funzionalità LLM nell'app Flask esistente, seguire questi passaggi:

1. AGGIUNGERE IMPORT:
"""

# Aggiungere in cima al file app.py:
from llm_api_example import llm_bp, cleanup_expired_sessions
import threading
import schedule

"""
2. REGISTRARE IL BLUEPRINT:
"""

# Dopo aver creato l'app Flask, aggiungere:
# app.register_blueprint(llm_bp)

"""
3. AGGIUNGERE CLEANUP AUTOMATICO:
"""

def setup_llm_cleanup():
    """Setup automatico pulizia sessioni LLM scadute"""
    
    def run_cleanup():
        while True:
            try:
                cleanup_expired_sessions()
                time.sleep(3600)  # Ogni ora
            except Exception as e:
                print(f"Errore cleanup LLM: {e}")
                time.sleep(300)  # Riprova dopo 5 minuti
    
    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

"""
4. AGGIORNARE ROUTE ESISTENTI:
"""

def serve_index_v2():
    """Serve la nuova interfaccia v2 con funzionalità LLM"""
    template_content = serve_template("index_v2.html")
    if template_content:
        return template_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    return "Template non trovato", 404

"""
5. AGGIUNGERE ROUTE PER ANTEPRIMA ENHANCED:
"""

def serve_enhanced_preview():
    """Serve anteprima report migliorato con AI"""
    scan_id = request.args.get('scan_id')
    version = request.args.get('version', 'enhanced')
    
    if not scan_id:
        return "Scan ID mancante", 400
    
    # Percorso report migliorato
    enhanced_path = Path(f"output/enhanced/report_{scan_id}.html")
    
    if enhanced_path.exists():
        content = enhanced_path.read_text(encoding='utf-8')
        return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    else:
        return "Report migliorato non trovato", 404

"""
6. CONFIGURAZIONE AMBIENTE:
"""

# Aggiungere variabili ambiente per LLM
import os

LLM_CONFIG = {
    'OPENAI_API_RATE_LIMIT': int(os.getenv('OPENAI_API_RATE_LIMIT', '100')),
    'LLM_REPORTS_PATH': os.getenv('LLM_REPORTS_PATH', './output/enhanced'),
    'LLM_SESSION_TIMEOUT': int(os.getenv('LLM_SESSION_TIMEOUT', '3600')),
    'LLM_MAX_TOKENS': int(os.getenv('LLM_MAX_TOKENS', '2000')),
    'LLM_TEMPERATURE': float(os.getenv('LLM_TEMPERATURE', '0.7'))
}

"""
7. MIDDLEWARE PER RATE LIMITING:
"""

from functools import wraps
from flask import request, jsonify
import time

# Rate limiting semplice per API LLM
request_times = {}

def rate_limit(max_requests=100, window=3600):
    """Decorator per rate limiting API LLM"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            if client_ip not in request_times:
                request_times[client_ip] = []
            
            # Rimuovi richieste fuori dalla finestra temporale
            request_times[client_ip] = [
                req_time for req_time in request_times[client_ip]
                if current_time - req_time < window
            ]
            
            # Controlla limite
            if len(request_times[client_ip]) >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }), 429
            
            # Aggiungi richiesta corrente
            request_times[client_ip].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

"""
8. MIDDLEWARE PER SICUREZZA API KEY:
"""

def sanitize_api_key(api_key: str) -> str:
    """Sanitizza e valida formato API key OpenAI"""
    if not api_key:
        return ""
    
    # Rimuovi spazi e caratteri indesiderati
    clean_key = api_key.strip()
    
    # Verifica formato base OpenAI
    if not clean_key.startswith('sk-'):
        return ""
    
    # Verifica lunghezza approssimativa
    if len(clean_key) < 45 or len(clean_key) > 60:
        return ""
    
    return clean_key

"""
9. LOGGING SPECIFICO PER LLM:
"""

import logging

# Setup logger per operazioni LLM
llm_logger = logging.getLogger('eaa_scanner.llm')
llm_handler = logging.FileHandler('logs/llm_operations.log')
llm_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
llm_handler.setFormatter(llm_formatter)
llm_logger.addHandler(llm_handler)
llm_logger.setLevel(logging.INFO)

def log_llm_operation(operation: str, scan_id: str, model: str, status: str, **kwargs):
    """Log operazioni LLM per audit e debugging"""
    llm_logger.info(
        f"LLM_OP: {operation} | Scan: {scan_id} | Model: {model} | Status: {status} | Extra: {kwargs}"
    )

"""
10. ESEMPIO INTEGRAZIONE COMPLETA NEL MAIN:
"""

def create_llm_enhanced_app():
    """Crea app Flask con funzionalità LLM integrate"""
    
    # Importa l'app base esistente
    from webapp.app import app
    
    # Registra blueprint LLM
    app.register_blueprint(llm_bp)
    
    # Setup cleanup automatico
    setup_llm_cleanup()
    
    # Aggiungi route per enhanced preview
    @app.route('/v2/enhanced_preview')
    def enhanced_preview():
        return serve_enhanced_preview()
    
    # Applica rate limiting alle route LLM
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/api/llm/'):
            # Applica rate limiting
            view_func = app.view_functions[rule.endpoint]
            app.view_functions[rule.endpoint] = rate_limit()(view_func)
    
    # Setup logging
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    return app

"""
11. VARIABILI AMBIENTE DA CONFIGURARE:
"""

# File .env per sviluppo:
"""
# Configurazione LLM
OPENAI_API_RATE_LIMIT=100
LLM_REPORTS_PATH=./output/enhanced
LLM_SESSION_TIMEOUT=3600
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7

# Configurazione sicurezza
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Configurazione CORS per frontend
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
"""

"""
12. SCRIPT DI AVVIO AGGIORNATO:
"""

if __name__ == "__main__":
    # Carica configurazione ambiente
    from dotenv import load_dotenv
    load_dotenv()
    
    # Crea app con LLM
    app = create_llm_enhanced_app()
    
    # Avvia server
    print("🚀 EAA Scanner v2.1 con funzionalità LLM avviato!")
    print("📊 Interfaccia web: http://localhost:8000/v2")
    print("🤖 API LLM: http://localhost:8000/api/llm/")
    
    app.run(
        host='localhost',
        port=8000,
        debug=True,
        threaded=True
    )

"""
NOTA IMPORTANTE:
- Testare sempre le funzionalità LLM in ambiente di sviluppo prima del deploy
- Monitorare i costi API OpenAI attraverso il dashboard
- Implementare logging dettagliato per audit delle operazioni LLM
- Considerare backup/fallback per quando l'API OpenAI non è disponibile
- Implementare cache per ridurre chiamate API ripetitive
"""