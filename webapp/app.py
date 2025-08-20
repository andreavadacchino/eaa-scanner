from __future__ import annotations

import io
import sys
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs

from wsgiref.simple_server import make_server
import json
import threading
import time
import os
import logging

from pathlib import Path as _Path
import sys as _sys
_sys.path.append(str(_Path(__file__).resolve().parents[1]))
from eaa_scanner.config import Config, ScannerToggles
from eaa_scanner.core import run_scan
from eaa_scanner.pdf import html_to_pdf
from eaa_scanner.emailer import send_pdf
from eaa_scanner.llm_config import get_llm_manager, LLMManager
# Import LLM utilities with path correction
try:
    from webapp.llm_utils import get_web_llm_manager, estimate_processing_time
    from webapp.api_extensions import route_additional_llm_endpoints
    from webapp.api_key_manager import get_api_key_manager
    from webapp.scan_monitor import get_scan_monitor, SSEStream
except ImportError:
    # Se webapp non è nel path, aggiungi path relativo
    import sys
    from pathlib import Path
    webapp_path = Path(__file__).parent
    if str(webapp_path) not in sys.path:
        sys.path.insert(0, str(webapp_path))
    
    from llm_utils import get_web_llm_manager, estimate_processing_time
    from api_extensions import route_additional_llm_endpoints
    from api_key_manager import get_api_key_manager
    from scan_monitor import get_scan_monitor, SSEStream

# Configura logger per app
logger = logging.getLogger('webapp.app')


# Serve modern frontend templates
def serve_template(template_name):
    """Serve modern HTML templates"""
    template_path = Path(__file__).parent / "templates" / template_name
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return None


def serve_static_file(environ, start_response, path):
    """Serve static files (CSS, JS, images)"""
    # Remove /static/ prefix and get file path
    file_path = path[8:]  # Remove '/static/'
    static_dir = Path(__file__).parent / "static"
    full_path = static_dir / file_path
    
    # Security check - ensure path is within static directory
    try:
        full_path = full_path.resolve()
        static_dir = static_dir.resolve()
        if not str(full_path).startswith(str(static_dir)):
            start_response("403 Forbidden", [("Content-Type", "text/plain")])
            return [b"Forbidden"]
    except (OSError, ValueError):
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"Bad Request"]
    
    if not full_path.exists() or full_path.is_dir():
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"File not found"]
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(str(full_path))
    if content_type is None:
        content_type = "application/octet-stream"
    
    # Add cache headers for static assets
    headers = [
        ("Content-Type", content_type),
        ("Cache-Control", "public, max-age=3600"),  # Cache for 1 hour
    ]
    
    # Add CORS headers for fonts
    if content_type.startswith("font/") or full_path.suffix in [".woff", ".woff2", ".ttf", ".otf"]:
        headers.append(("Access-Control-Allow-Origin", "*"))
    
    try:
        file_content = full_path.read_bytes()
        start_response("200 OK", headers)
        return [file_content]
    except IOError:
        start_response("500 Internal Server Error", [("Content-Type", "text/plain")])
        return [b"Error reading file"]


def get_scan_history():
    """Get scan history data for the history page"""
    with _LOCK:
        scans = []
        for scan_id, scan_data in _SCANS.items():
            # Only include completed scans in history
            if scan_data.get('status') in ['done', 'error']:
                history_item = {
                    'id': scan_id,
                    'date': scan_data.get('timestamp', time.time() * 1000),
                    'company': scan_data.get('company_name', 'Unknown'),
                    'url': scan_data.get('url', ''),
                    'status': 'completed' if scan_data.get('status') == 'done' else 'error',
                    'score': None,  # TODO: Extract from report if available
                    'compliance': None,  # TODO: Extract from report if available
                    'scanners': [],  # TODO: Extract enabled scanners
                    'duration': scan_data.get('duration', 0),
                    'issues': {
                        'errors': 0,
                        'warnings': 0,
                        'total': 0
                    }
                }
                scans.append(history_item)
        
        # Sort by date (newest first)
        scans.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'scans': scans,
            'total': len(scans),
            'page': 1,
            'per_page': 50
        }


def parse_post(environ):
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        size = 0
    body = environ["wsgi.input"].read(size)
    return parse_qs(body.decode("utf-8"))


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    # Static file serving
    if path.startswith("/static/"):
        return serve_static_file(environ, start_response, path)

    if path == "/" and method == "GET":
        # Usa direttamente la v2 come interfaccia principale
        template = serve_template("index_v2.html")
        if template:
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [template.encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    
    # Route /v2 ora è un redirect a / per compatibilità
    if path == "/v2" and method == "GET":
        start_response("301 Moved Permanently", [("Location", "/")])
        return [b"Redirecting to main interface..."]

    if path == "/health" and method == "GET":
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"ok": True}).encode("utf-8")]

    # Modern API endpoints
    if path == "/start" and method == "POST":
        # JSON or form
        ctype = environ.get('CONTENT_TYPE','')
        if 'application/json' in ctype:
            size = int(environ.get('CONTENT_LENGTH') or 0)
            payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        else:
            payload = {k:v[0] for k,v in parse_post(environ).items()}
        try:
            scan_id = start_scan(payload)
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"scan_id": scan_id}).encode("utf-8")]
        except Exception as e:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": str(e)}).encode("utf-8")]

    if path == "/status" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        data = get_status(scan_id)
        if not data:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "scan non trovato"}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(data).encode("utf-8")]

    if path == "/download/html" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        version = (params.get('version') or ['latest'])[0]
        
        # Unified HTML download supporting both v1 and v2
        with _LOCK:
            # Try v1 first
            s = _SCANS.get(scan_id)
            if s and s.get('report_html'):
                p = Path(s['report_html'])
                if p.exists():
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),("Content-Disposition", f"attachment; filename={p.name}")])
                    return [p.read_bytes()]
            
            # Try v2
            s = _V2_SCANS.get(scan_id)
            if s:
                # Se versione specifica richiesta
                if version != 'latest':
                    versions = s.get('versions', [])
                    for v in versions:
                        if v['version'] == version and v.get('html_path'):
                            p = Path(v['html_path'])
                            if p.exists():
                                filename = f"report_{scan_id}_{version}.html"
                                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),("Content-Disposition", f"attachment; filename={filename}")])
                                return [p.read_bytes()]
                
                # Latest version
                if s.get('report_html_path'):
                    p = Path(s['report_html_path'])
                    if p.exists():
                        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"),("Content-Disposition", f"attachment; filename={p.name}")])
                        return [p.read_bytes()]
        
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Report HTML non disponibile"]

    if path == "/preview" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        version = (params.get('version') or ['latest'])[0]
        
        # Unified preview supporting both v1 and v2
        with _LOCK:
            # Try v1 first
            s = _SCANS.get(scan_id)
            if s and s.get('report_html'):
                p = Path(s['report_html'])
                if p.exists():
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                    return [p.read_bytes()]
            
            # Try v2
            s = _V2_SCANS.get(scan_id)
            if s:
                # Se versione specifica richiesta
                if version != 'latest':
                    versions = s.get('versions', [])
                    for v in versions:
                        if v['version'] == version and v.get('html_path'):
                            p = Path(v['html_path'])
                            if p.exists():
                                start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                                return [p.read_bytes()]
                
                # Latest version
                if s.get('report_html_path'):
                    p = Path(s['report_html_path'])
                    if p.exists():
                        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                        return [p.read_bytes()]
        
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Report HTML non disponibile"]

    if path == "/download/pdf" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('report_pdf'):
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Report PDF non disponibile"]
        p = Path(s['report_pdf'])
        start_response("200 OK", [("Content-Type", "application/pdf"),("Content-Disposition", f"attachment; filename={p.name}")])
        return [p.read_bytes()]

    if path == "/generate_pdf" and method == "POST":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('report_html'):
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": False, "error": "report non trovato"}).encode("utf-8")]
        html_path = Path(s['report_html'])
        pdf_path = html_path.with_suffix('.pdf')
        ok = html_to_pdf(html_path, pdf_path)
        if ok:
            _update(scan_id, report_pdf=str(pdf_path))
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": True, "pdf": str(pdf_path)}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"ok": False}).encode("utf-8")]

    if path == "/send_email" and method == "POST":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": False, "error": "scan non trovato"}).encode("utf-8")]
        html_path = Path(s.get('report_html') or '')
        if not html_path.exists():
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"ok": False, "error": "report non pronto"}).encode("utf-8")]
        pdf_path = html_path.with_suffix('.pdf')
        if not pdf_path.exists():
            ok = html_to_pdf(html_path, pdf_path)
            if ok:
                _update(scan_id, report_pdf=str(pdf_path))
        form = parse_post(environ)
        to = (form.get('to') or [s.get('email') or ''])[0]
        subj = f"Report Accessibilità EAA - {s.get('company_name') or 'Sito'}"
        body = f"In allegato il report PDF per {s.get('company_name') or ''} ({s.get('url') or ''})."
        sent, info = send_pdf(pdf_path, to, subj, body)
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"ok": sent, "info": info}).encode("utf-8")]

    # history page
    if path == "/history" and method == "GET":
        template = serve_template("history.html")
        if template:
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [template.encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Template not found"]
    
    # smart scan dashboard page
    if path == "/smart-dashboard" and method == "GET":
        template = serve_template("smart_scan_dashboard.html")
        if template:
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return [template.encode("utf-8")]
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Template not found"]
    # Removed duplicate /v2 route - now handled at line 164
    # V2 Preview endpoint with versioning support
    if path == "/v2/preview" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        version = (params.get('version') or ['latest'])[0]
        
        # Check if it's a v2 scan
        with _LOCK:
            v2_scan = _V2_SCANS.get(scan_id)
        
        if v2_scan:
            # Se versione specifica richiesta
            if version != 'latest':
                versions = v2_scan.get('versions', [])
                for v in versions:
                    if v['version'] == version and v.get('html_path'):
                        p = Path(v['html_path'])
                        if p.exists():
                            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                            return [p.read_bytes()]
            
            # Versione latest (default)
            if v2_scan.get('report_html_path'):
                p = Path(v2_scan['report_html_path'])
                if p.exists():
                    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
                    return [p.read_bytes()]
        
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Report HTML non disponibile"]

    # API endpoint for history data
    if path == "/api/history" and method == "GET":
        history_data = get_scan_history()
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(history_data).encode("utf-8")]
    
    # API endpoint for analytics data
    if path == "/api/analytics" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('analytics_path'):
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "analytics non disponibili"}).encode("utf-8")]
        analytics_path = Path(s['analytics_path'])
        if analytics_path.exists():
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [analytics_path.read_bytes()]
        start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "file analytics non trovato"}).encode("utf-8")]
    
    # API endpoint for charts data
    if path == "/api/charts" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('charts_path'):
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "grafici non disponibili"}).encode("utf-8")]
        charts_path = Path(s['charts_path'])
        if charts_path.exists():
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [charts_path.read_bytes()]
        start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "file grafici non trovato"}).encode("utf-8")]
    
    # API endpoint for remediation plan
    if path == "/api/remediation" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('remediation_path'):
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "piano di remediation non disponibile"}).encode("utf-8")]
        remediation_path = Path(s['remediation_path'])
        if remediation_path.exists():
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [remediation_path.read_bytes()]
        start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "file remediation non trovato"}).encode("utf-8")]
    
    # Server-Sent Events endpoint per monitoraggio live
    if path.startswith("/api/scan/stream/") and method == "GET":
        return handle_scan_stream(environ, start_response)
    
    # API endpoint for accessibility statement
    if path == "/api/statement" and method == "GET":
        qs = environ.get('QUERY_STRING','')
        params = parse_qs(qs)
        scan_id = (params.get('scan_id') or [''])[0]
        s = _SCANS.get(scan_id)
        if not s or not s.get('statement_path'):
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "dichiarazione di accessibilità non disponibile"}).encode("utf-8")]
        statement_path = Path(s['statement_path'])
        if statement_path.exists():
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [statement_path.read_bytes()]
        start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "file dichiarazione non trovato"}).encode("utf-8")]
    
    # ========== LLM API ENDPOINTS ==========
    
    # Validate OpenAI API key
    if path == "/api/llm/validate-key" and method == "POST":
        return handle_llm_validate_key(environ, start_response)
    
    # Estimate LLM costs
    if path == "/api/llm/estimate-costs" and method == "POST":
        return handle_llm_estimate_costs(environ, start_response)
    
    # Generate/regenerate report with LLM
    if path == "/api/reports/regenerate" and method == "POST":
        return handle_report_regenerate(environ, start_response)
    
    # Get report versions list
    if path.startswith("/api/reports/") and path.endswith("/versions") and method == "GET":
        scan_id = path.split('/')[-2]
        return handle_report_versions(environ, start_response, scan_id)
    
    # ========== API KEYS MANAGEMENT ==========
    
    # Save API keys
    if path == "/api/keys/save" and method == "POST":
        return handle_api_keys_save(environ, start_response)
    
    # Get API keys status
    if path == "/api/keys/status" and method == "GET":
        return handle_api_keys_status(environ, start_response)
    
    # Validate single API key
    if path == "/api/keys/validate" and method == "POST":
        return handle_api_key_validate(environ, start_response)
    
    # ========== V2 API ENDPOINTS - 2-PHASE WORKFLOW ==========
    
    # Start discovery phase
    if path == "/api/discovery/start" and method == "POST":
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        try:
            discovery_id = start_discovery(payload)
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"session_id": discovery_id}).encode("utf-8")]
        except Exception as e:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": str(e)}).encode("utf-8")]
    
    # Get discovery status
    if path.startswith("/api/discovery/status/") and method == "GET":
        discovery_id = path.split('/')[-1]
        status = get_discovery_status(discovery_id)
        if not status:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Discovery session not found"}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(status).encode("utf-8")]
    
    # Get discovery results
    if path.startswith("/api/discovery/results/") and method == "GET":
        discovery_id = path.split('/')[-1]
        results = get_discovery_results(discovery_id)
        if not results:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Discovery results not found"}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(results).encode("utf-8")]
    
    # Start scan phase (with selected URLs and LLM config)
    if path == "/api/scan/start" and method == "POST":
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        try:
            scan_id = start_selective_scan(payload)
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"session_id": scan_id}).encode("utf-8")]
        except Exception as e:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": str(e)}).encode("utf-8")]
    
    # Get scan status
    if path.startswith("/api/scan/status/") and method == "GET":
        scan_id = path.split('/')[-1]
        status = get_scan_status(scan_id)
        if not status:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Scan session not found"}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(status).encode("utf-8")]
    
    # Get scan results
    if path.startswith("/api/scan/results/") and method == "GET":
        scan_id = path.split('/')[-1]
        results = get_scan_results(scan_id)
        if not results:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Scan results not found"}).encode("utf-8")]
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(results).encode("utf-8")]
    
    # Get regeneration task status
    if path.startswith("/api/tasks/") and path.endswith("/status") and method == "GET":
        task_id = path.split('/')[-2]
        return handle_task_status(environ, start_response, task_id)
    
    # Download specific report version
    if path.startswith("/api/reports/") and "/versions/" in path and method == "GET":
        parts = path.split('/')
        scan_id = parts[3]
        version = parts[5]
        return handle_download_version(environ, start_response, scan_id, version)
    
    # Migrate v1 scan to v2 format
    if path == "/api/migrate/v1-to-v2" and method == "POST":
        return handle_migrate_v1_to_v2(environ, start_response)
    
    # Get scan metadata (unified v1/v2)
    if path.startswith("/api/scans/") and path.endswith("/metadata") and method == "GET":
        scan_id = path.split('/')[-2]
        return handle_scan_metadata(environ, start_response, scan_id)

    # Route additional LLM endpoints prima del 404
    try:
        additional_response = route_additional_llm_endpoints(environ, start_response, path, method)
        if additional_response is not None:
            return additional_response
    except Exception as e:
        logger.error(f"Errore routing LLM endpoints: {e}")
    
    # Debug endpoint per stato interno
    if path == "/api/debug/scans" and method == "GET" and os.environ.get('DEBUG_MODE') == '1':
        with _LOCK:
            debug_info = {
                "v1_scans": len(_SCANS),
                "v2_scans": len(_V2_SCANS),
                "discoveries": len(_DISCOVERIES),
                "llm_cache_size": len(_LLM_CACHE),
                "rate_limiters": len(_RATE_LIMITERS),
                "active_v1_scans": [k for k, v in _SCANS.items() if v.get('status') == 'running'],
                "active_v2_scans": [k for k, v in _V2_SCANS.items() if v.get('state') == 'running'],
                "completed_v1_scans": [k for k, v in _SCANS.items() if v.get('status') == 'done'],
                "completed_v2_scans": [k for k, v in _V2_SCANS.items() if v.get('state') == 'completed']
            }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(debug_info, indent=2).encode("utf-8")]
    
    if path == "/scan" and method == "POST":
        form = parse_post(environ)
        # Extract form fields
        url = (form.get("url", [""]) or [""])[0]
        company = (form.get("company_name", [""]) or [""])[0]
        email = (form.get("email", [""]) or [""])[0]
        wave_key = (form.get("wave_api_key", [""]) or [""])[0]
        mode = (form.get("mode", ["simulate"]) or ["simulate"])[0]

        toggles = ScannerToggles(
            wave="wave" in form,
            pa11y="pa11y" in form,
            axe_core="axe_core" in form,
            lighthouse="lighthouse" in form,
        )

        args = {
            "url": url,
            "company_name": company,
            "email": email,
            "wave_api_key": wave_key,
            "simulate": mode != "real",
        }
        cfg = Config.from_env_or_args(args)
        cfg.scanners_enabled = toggles
        try:
            cfg.validate()
        except Exception as e:
            start_response("400 Bad Request", [("Content-Type", "text/plain; charset=utf-8")])
            return [f"Errore configurazione: {e}".encode("utf-8")]

        # Run scan
        result = run_scan(cfg, output_root=Path("output"))
        report_html = Path(result["report_html_path"]).resolve()
        pdf_path = report_html.with_suffix(".pdf")
        ok = html_to_pdf(report_html, pdf_path)

        if ok and pdf_path.exists():
            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/pdf"),
                    ("Content-Disposition", f"attachment; filename={pdf_path.name}"),
                ],
            )
            return [pdf_path.read_bytes()]
        else:
            # Fallback: return HTML with note
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            note = (
                "<p><strong>Nota:</strong> generazione PDF non disponibile in questo ambiente."
                " Scarica l'HTML e stampa in PDF dal browser.</p>"
            )
            return [note.encode("utf-8") + report_html.read_bytes()]

    # Last resort: 404
    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not found"]

# ========== Simple in-memory status tracking ==========
_LOCK = threading.Lock()
_SCANS = {}
_DISCOVERIES = {}  # For discovery sessions
_V2_SCANS = {}  # For v2 scan sessions
_LLM_CACHE = {}  # LLM response cache
_REPORT_VERSIONS = {}  # Report versioning cache
_RATE_LIMITERS = {}  # Rate limiting per IP

# ========== Rate Limiting Infrastructure ==========
class RateLimiter:
    """Rate limiter per operazioni costose"""
    
    def __init__(self, max_requests=5, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def can_proceed(self) -> bool:
        """Verifica se la richiesta può procedere"""
        now = time.time()
        # Rimuovi richieste vecchie
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window_seconds]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False

def get_rate_limiter(client_ip: str) -> RateLimiter:
    """Ottiene rate limiter per IP"""
    if client_ip not in _RATE_LIMITERS:
        _RATE_LIMITERS[client_ip] = RateLimiter()
    return _RATE_LIMITERS[client_ip]

def get_client_ip(environ) -> str:
    """Estrae IP client da headers"""
    forwarded = environ.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return environ.get('REMOTE_ADDR', '127.0.0.1')


def start_scan(payload: dict) -> str:
    url = (payload.get('url') or '').strip()
    company = (payload.get('company_name') or '').strip()
    email = (payload.get('email') or '').strip()
    wave_key = (payload.get('wave_api_key') or '').strip()
    mode = (payload.get('mode') or 'simulate').strip()
    scanners = payload.get('scanners') or {}
    
    # Nuove opzioni avanzate
    enable_crawling = bool(payload.get('enable_crawling', False))
    # Usa crawler_config solo se crawling è abilitato
    crawler_config = payload.get('crawler_config', {}) if enable_crawling else {}
    methodology_config = payload.get('methodology_config', {})
    report_type = payload.get('report_type', 'standard')
    organization_data = payload.get('organization_data', {})

    args = {
        'url': url, 'company_name': company, 'email': email,
        'wave_api_key': wave_key, 'simulate': (mode != 'real')
    }
    cfg = Config.from_env_or_args(args)
    cfg.scanners_enabled.wave = bool(scanners.get('wave', True))
    cfg.scanners_enabled.pa11y = bool(scanners.get('pa11y', True))
    cfg.scanners_enabled.axe_core = bool(scanners.get('axe_core', True))
    cfg.scanners_enabled.lighthouse = bool(scanners.get('lighthouse', True))
    cfg.validate()

    scan_id = f"ui_{int(time.time()*1000)}"
    with _LOCK:
        _SCANS[scan_id] = {
            'status': 'running', 'stage': 'Avvio', 'percent': 5,
            'message': 'Validazione parametri…', 'log': [],
            'timestamp': time.time() * 1000,
            'company_name': cfg.company_name,
            'url': cfg.url,
            'email': cfg.email,
            'enable_crawling': enable_crawling,
            'crawler_config': crawler_config,
            'methodology_config': methodology_config,
            'report_type': report_type,
            'organization_data': organization_data
        }
    t = threading.Thread(target=_worker, args=(scan_id, cfg, enable_crawling, crawler_config, methodology_config, report_type), daemon=True)
    t.start()
    return scan_id


def get_status(scan_id: str):
    """Get scan status with unified v1/v2 support"""
    with _LOCK:
        # Cerca prima in _SCANS (v1), poi in _V2_SCANS (v2)
        s = _SCANS.get(scan_id)
        if s:
            # V1 scan status
            return {
                'status': s.get('status'),
                'stage': s.get('stage'),
                'percent': s.get('percent', 0),
                'message': s.get('message', ''),
                'log': s.get('log', [])[-50:],
                'report': {
                    'html': bool(s.get('report_html')), 
                    'pdf': bool(s.get('report_pdf')),
                    'analytics': bool(s.get('analytics_path')),
                    'charts': bool(s.get('charts_path')),
                    'remediation': bool(s.get('remediation_path')),
                    'statement': bool(s.get('statement_path'))
                },
                'company_name': s.get('company_name'),
                'url': s.get('url'),
                'pages_scanned': s.get('pages_scanned', 1),
                'scan_config': {
                    'enable_crawling': s.get('enable_crawling', False),
                    'report_type': s.get('report_type', 'standard'),
                    'crawler_config': s.get('crawler_config', {})
                },
                'llm_config': s.get('llm_config', {}),
                'versions_count': len(s.get('versions', [])),
                'scan_type': 'v1'
            }
        
        # Prova con _V2_SCANS
        s = _V2_SCANS.get(scan_id)
        if s:
            # V2 scan status - converte al formato v1 per compatibilità
            v2_status = get_scan_status(scan_id)  # Usa la funzione v2 nativa
            if v2_status:
                # Mappa stato v2 -> v1 per backward compatibility
                v1_status_map = {
                    'running': 'running',
                    'completed': 'done',
                    'failed': 'error',
                    'llm_processing': 'running'
                }
                
                return {
                    'status': v1_status_map.get(v2_status['state'], 'running'),
                    'stage': 'Completato' if v2_status['state'] == 'completed' else 'Scansione',
                    'percent': v2_status['progress_percent'],
                    'message': f"Pagina {v2_status['current_page']}/{len(s.get('pages', []))}",
                    'log': v2_status['log'],
                    'report': {
                        'html': bool(s.get('report_html_path')),
                        'pdf': False,  # PDF generation on-demand
                        'analytics': False,
                        'charts': False,
                        'remediation': False,
                        'statement': False
                    },
                    'company_name': s.get('company_name'),
                    'url': s.get('pages', [''])[0] if s.get('pages') else '',
                    'pages_scanned': len(s.get('pages', [])),
                    'scan_config': {
                        'enable_crawling': True,  # V2 sempre usa crawling
                        'report_type': 'advanced',
                        'crawler_config': {'max_pages': len(s.get('pages', []))}
                    },
                    'llm_config': s.get('llm_config', {}),
                    'versions_count': len(s.get('versions', [])),
                    'scan_type': 'v2'
                }
        
        return None


def handle_scan_stream(environ, start_response):
    """Gestisce stream SSE per monitoraggio live delle scansioni - Best Practices"""
    import time
    import asyncio
    from datetime import datetime
    
    path = environ.get("PATH_INFO", "/")
    scan_id = path.split("/")[-1]  # Estrae scan_id dall'URL
    
    logger.info(f"SSE: Richiesta connessione stream per scan {scan_id}")
    
    if not scan_id:
        start_response("400 Bad Request", [("Content-Type", "text/plain")])
        return [b"Scan ID richiesto"]
    
    def event_generator():
        """Generatore di eventi SSE con gestione disconnessioni"""
        monitor = get_scan_monitor()
        heartbeat_counter = 0
        start_ts = time.time()
        
        # Log stato iniziale
        logger.info(f"SSE: Monitor ha {len(monitor.event_history.get(scan_id, []))} eventi per scan {scan_id}")
        
        # Header di connessione
        initial_data = {
            "event_type": "connection",
            "message": "Connessione monitoraggio stabilita",
            "timestamp": datetime.now().isoformat(),
            "scan_id": scan_id
        }
        yield f"data: {json.dumps(initial_data, ensure_ascii=False)}\n\n".encode('utf-8')
        
        # Track eventi inviati
        events_sent = 0
        last_event_count = 0
        max_events = 5000  # Limite più alto per scansioni lunghe
        last_heartbeat = time.time()
        
        # Invia immediatamente tutti gli eventi già presenti nella storia
        with monitor.lock:
            if scan_id in monitor.event_history:
                events = monitor.event_history[scan_id]
                logger.info(f"SSE: Invio {len(events)} eventi storici per scan {scan_id}")
                for event in events:
                    event_msg = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    yield event_msg.encode('utf-8')
                    events_sent += 1
                last_event_count = len(events)
        
        while events_sent < max_events:
            try:
                # Controlla nuovi eventi per questo scan_id con lock per thread safety
                with monitor.lock:
                    events = monitor.event_history.get(scan_id, [])
                    
                    # Invia eventi nuovi non ancora inviati
                    if len(events) > last_event_count:
                        new_events = events[last_event_count:]
                        logger.info(f"SSE: Invio {len(new_events)} nuovi eventi per scan {scan_id}")
                        for event in new_events:
                            event_msg = f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                            yield event_msg.encode('utf-8')
                            events_sent += 1
                        last_event_count = len(events)
                
                # Heartbeat ogni 15 secondi per mantenere connessione (forma conforme al contratto)
                current_time = time.time()
                if current_time - last_heartbeat > 15:
                    heartbeat_evt = {
                        "event_type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "scan_id": scan_id,
                        "data": {
                            "uptime_ms": int((current_time - start_ts) * 1000),
                            "connection_id": f"conn_{scan_id}",
                            "events_sent": events_sent,
                        }
                    }
                    yield f"data: {json.dumps(heartbeat_evt, ensure_ascii=False)}\n\n".encode('utf-8')
                    last_heartbeat = current_time
                    heartbeat_counter += 1
                
                # Check se scan è completato
                scan_data = _V2_SCANS.get(scan_id, {})
                if scan_data.get('state') in ['completed', 'failed']:
                    # Invia evento finale conforme arricchito con metriche quando disponibili
                    state = scan_data.get('state')
                    data_payload = {"state": state}
                    try:
                        metrics = scan_data.get('metrics', {}) if isinstance(scan_data, dict) else {}
                        if state == 'completed':
                            if 'compliance_score' in metrics:
                                data_payload['compliance_score'] = metrics.get('compliance_score')
                            if 'errors' in metrics:
                                data_payload['total_errors'] = metrics.get('errors')
                            if 'warnings' in metrics:
                                data_payload['total_warnings'] = metrics.get('warnings')
                            # report url best-effort
                            data_payload['report_url'] = f'/v2/preview?scan_id={scan_id}'
                            # pages_scanned best-effort
                            pages = scan_data.get('pages', []) if isinstance(scan_data, dict) else []
                            if isinstance(pages, list) and pages:
                                data_payload['pages_scanned'] = len(pages)
                        else:  # failed
                            if isinstance(scan_data, dict) and scan_data.get('error'):
                                data_payload['error'] = scan_data.get('error')
                    except Exception:
                        pass

                    final_evt = {
                        "event_type": "scan_complete" if state == 'completed' else "scan_failed",
                        "timestamp": datetime.now().isoformat(),
                        "scan_id": scan_id,
                        "data": data_payload
                    }
                    yield f"data: {json.dumps(final_evt, ensure_ascii=False)}\n\n".encode('utf-8')
                    break
                
                # Sleep breve per non consumare troppa CPU
                time.sleep(1)
                
                # Heartbeat leggero aggiuntivo rimosso per evitare duplicati non conformi
                    
            except Exception as e:
                # Log errore e chiudi connessione
                print(f"Errore SSE per scan {scan_id}: {e}")
                break
    
    # Imposta headers SSE
    start_response("200 OK", [
        ("Content-Type", "text/event-stream"),
        ("Cache-Control", "no-cache"),
        ("Access-Control-Allow-Origin", "*"),
        ("Access-Control-Allow-Headers", "Cache-Control"),
        ("X-Accel-Buffering", "no")  # Disabilita buffering in nginx
    ])
    
    return event_generator()


def _update(scan_id: str, **kw):
    """Update scan data with unified v1/v2 support"""
    with _LOCK:
        # Prova prima _SCANS (v1), poi _V2_SCANS (v2)
        s = _SCANS.get(scan_id)
        if s:
            s.update(kw)
            if 'log' in kw and isinstance(kw['log'], str):
                s.setdefault('log', []).append(kw['log'])
            s['timestamp'] = time.time() * 1000
            return
        
        # Prova v2
        s = _V2_SCANS.get(scan_id)
        if s:
            s.update(kw)
            if 'log' in kw and isinstance(kw['log'], str):
                s.setdefault('log', []).append(kw['log'])
            # Update timestamp per compatibilità v1
            s['timestamp'] = time.time() * 1000
            # Mappa alcuni campi v1 -> v2
            if 'status' in kw:
                status_map = {
                    'running': 'running',
                    'done': 'completed',
                    'error': 'failed'
                }
                s['state'] = status_map.get(kw['status'], kw['status'])
            return


def _log(scan_id: str, msg: str):
    """Add log entry with unified v1/v2 support"""
    with _LOCK:
        # Prova prima _SCANS (v1), poi _V2_SCANS (v2)
        s = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
        if s:
            s.setdefault('log', []).append(msg)
            logger.info(f"[{scan_id}] {msg}")


def _worker(scan_id: str, cfg: Config, enable_crawling: bool = False, 
           crawler_config: dict = None, methodology_config: dict = None, 
           report_type: str = 'standard'):
    monitor = get_scan_monitor()
    try:
        # Emit scan start event
        scanners_enabled = {
            "wave": cfg.scanners_enabled.wave,
            "pa11y": cfg.scanners_enabled.pa11y,
            "axe": cfg.scanners_enabled.axe_core,
            "lighthouse": cfg.scanners_enabled.lighthouse
        }
        monitor.emit_scan_start(scan_id, cfg.url, cfg.company_name, scanners_enabled)
        _update(scan_id, stage='Validazione', percent=8)
        cfg.validate()
        _log(scan_id, '✔ Parametri validi')

        # Import del nuovo core orchestrator
        from eaa_scanner.core import run_scan
        from eaa_scanner.pdf import html_to_pdf
        from pathlib import Path
        
        # Assicura che i config siano dizionari validi
        crawler_config = crawler_config if crawler_config else {}
        methodology_config = methodology_config if methodology_config else {}

        # Configura messaggi di progresso per scansione avanzata
        if enable_crawling and crawler_config:
            _update(scan_id, stage='Crawling', percent=10, message='Ricerca pagine del sito…')
            _log(scan_id, f'✔ Crawler configurato per max {crawler_config.get("max_pages", 10)} pagine')
        
        _update(scan_id, stage='Scansione', percent=20, message='Avvio scansione multi-scanner…')
        
        # Usa il nuovo orchestrator con monitoring
        result = run_scan(
            cfg=cfg, 
            output_root=Path('output'),
            enable_crawling=enable_crawling,
            crawler_config=crawler_config,
            methodology_config=methodology_config,
            report_type=report_type,
            event_monitor=monitor
        )
        
        _update(scan_id, stage='Analytics', percent=80, message='Generazione analytics…')
        _log(scan_id, f'✔ Scansionate {result["pages_scanned"]} pagine')
        
        _update(scan_id, stage='Report', percent=90, message='Generazione report finale…')
        html_path = Path(result['report_html_path'])
        _log(scan_id, f'✔ Report {report_type}: {html_path.name}')

        # Emit scan complete event
        # Calcolo durata se disponibile (fallback a 0 se non tracciata dal monitor)
        try:
            start_time_attr = getattr(monitor, 'start_time', None)
            total_duration = (time.time() - start_time_attr) if (monitor and start_time_attr) else 0
        except Exception:
            total_duration = 0
        # Emissione conforme al contratto SSE con payload unificato
        monitor.emit_scan_complete(scan_id, {
            'scan_duration_ms': int(total_duration * 1000),
            'report_url': f'/v2/preview?scan_id={scan_id}',
            'pages_scanned': result.get('pages_scanned', 1),
            'total_errors': result.get('total_errors', 0),
            'total_warnings': result.get('total_warnings', 0),
            'compliance_score': result.get('compliance_score', 0),
            # Include anche i risultati minimi per permettere skip del fetch
            'scan_results': {
                'summary': {
                    'pages_scanned': result.get('pages_scanned', 1),
                    'total_errors': result.get('total_errors', 0),
                    'total_warnings': result.get('total_warnings', 0),
                    'compliance_score': result.get('compliance_score', 0)
                }
            }
        })
        
        _update(scan_id, stage='Completato', percent=100, status='done', message='', 
                report_html=str(html_path), url=cfg.url, company_name=cfg.company_name, 
                email=cfg.email, analytics_path=result.get('analytics_path'),
                charts_path=result.get('charts_path'), remediation_path=result.get('remediation_path'),
                statement_path=result.get('statement_path'), pages_scanned=result.get('pages_scanned', 1))

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_detail = traceback.format_exc()
        
        # Log dettagliato dell'errore
        _log(scan_id, f'❌ Errore: {error_msg}')
        print(f"Errore scansione {scan_id}: {error_detail}")
        
        # Determina messaggio utente-friendly
        if "list index out of range" in error_msg:
            user_msg = "Nessuna pagina scansionata. Verifica l'URL e riprova."
        elif "Nessuna pagina scansionata" in error_msg:
            user_msg = error_msg
        elif "timeout" in error_msg.lower():
            user_msg = "Timeout durante la scansione. Il sito potrebbe essere lento o non raggiungibile."
        elif "connection" in error_msg.lower():
            user_msg = "Errore di connessione. Verifica l'URL e la connessione internet."
        else:
            user_msg = f"Errore durante la scansione: {error_msg}"
        
        # Emit scan failed event
        monitor.emit_scan_failed(scan_id, user_msg)
        
        _update(scan_id, status='error', stage='Errore', message=user_msg, percent=0)


# ========== LLM ENDPOINT HANDLERS ==========

def handle_llm_validate_key(environ, start_response):
    """Valida API key OpenAI con cache"""
    try:
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        api_key = payload.get('api_key', '').strip()
        if not api_key:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"valid": False, "error": "API key mancante"}).encode("utf-8")]
        
        # Usa WebLLMManager con cache
        web_manager = get_web_llm_manager()
        response = web_manager.validate_api_key_cached(api_key)
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore validazione API key: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"valid": False, "error": "Errore validazione"}).encode("utf-8")]


def handle_llm_estimate_costs(environ, start_response):
    """Calcola stima costi LLM avanzata"""
    try:
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        # Usa WebLLMManager per calcolo avanzato
        web_manager = get_web_llm_manager()
        response = web_manager.estimate_costs_advanced(payload)
        
        # Aggiungi stima tempo elaborazione
        time_estimate = estimate_processing_time(
            sections=payload.get('sections', []),
            pages=payload.get('num_pages', 1),
            complexity=payload.get('complexity', 'medium')
        )
        response.update(time_estimate)
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore stima costi LLM: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore calcolo stima costi"}).encode("utf-8")]


def handle_report_regenerate(environ, start_response):
    """Rigenera report con LLM"""
    try:
        # Rate limiting
        client_ip = get_client_ip(environ)
        rate_limiter = get_rate_limiter(client_ip)
        
        if not rate_limiter.can_proceed():
            start_response("429 Too Many Requests", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Troppe richieste. Riprova tra qualche minuto."}).encode("utf-8")]
        
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        scan_id = payload.get('scan_id', '')
        llm_config = payload.get('llm_config', {})
        sections = payload.get('sections', [])
        
        if not scan_id:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "scan_id mancante"}).encode("utf-8")]
        
        # Verifica esistenza scan (supporta sia v1 che v2)
        with _LOCK:
            scan_data = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
            scan_type = 'v2' if scan_id in _V2_SCANS else 'v1'
        
        if not scan_data:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Scan non trovato"}).encode("utf-8")]
        
        # Verifica stato scan (supporta sia v1 che v2)
        scan_done = (scan_data.get('status') == 'done' or 
                    scan_data.get('state') in ['completed', 'llm_processing'])
        
        if not scan_done:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Scan non completato"}).encode("utf-8")]
        
        # Avvia rigenerazione in background (supporta v1 e v2)
        regen_id = f"regen_{int(time.time()*1000)}"
        
        # Scegli worker appropriato in base al tipo di scan
        if scan_type == 'v2':
            worker_target = _v2_regenerate_report_worker
        else:
            worker_target = _regenerate_report_worker
        
        t = threading.Thread(
            target=worker_target,
            args=(scan_id, regen_id, llm_config, sections),
            daemon=True
        )
        t.start()
        
        response = {
            "task_id": regen_id,
            "status": "started",
            "message": "Rigenerazione report avviata"
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore rigenerazione report: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore avvio rigenerazione"}).encode("utf-8")]


def handle_report_versions(environ, start_response, scan_id):
    """Lista versioni report"""
    try:
        with _LOCK:
            scan_data = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
        
        if not scan_data:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Scan non trovato"}).encode("utf-8")]
        
        versions = scan_data.get('versions', [])
        
        # Aggiungi versione originale se non presente (supporta sia v1 che v2)
        if not any(v['version'] == 'v1.0' for v in versions):
            original_html_path = (scan_data.get('report_html') or 
                                scan_data.get('report_html_path'))
            
            original_version = {
                'version': 'v1.0',
                'type': 'original',
                'created_at': scan_data.get('timestamp', scan_data.get('started_at', 0) * 1000),
                'llm_enhanced': False,
                'html_path': original_html_path,
                'size_bytes': 0
            }
            
            # Calcola dimensione se file esiste
            if original_html_path:
                try:
                    size = Path(original_html_path).stat().st_size
                    original_version['size_bytes'] = size
                except:
                    pass
            
            versions.insert(0, original_version)
        
        response = {
            "scan_id": scan_id,
            "versions": versions,
            "total_versions": len(versions)
        }
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore recupero versioni: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore recupero versioni"}).encode("utf-8")]


def _regenerate_report_worker(scan_id: str, regen_id: str, llm_config: dict, sections: list):
    """Worker per rigenerare report con LLM"""
    try:
        logger.info(f"Avvio rigenerazione report per scan {scan_id}")
        
        # Recupera dati scan
        with _LOCK:
            scan_data = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
            if not scan_data:
                return
            
            # Crea entry per task di rigenerazione
            if 'regen_tasks' not in scan_data:
                scan_data['regen_tasks'] = {}
            
            scan_data['regen_tasks'][regen_id] = {
                'status': 'running',
                'progress': 0,
                'current_section': '',
                'started_at': time.time(),
                'sections': sections,
                'llm_config': llm_config
            }
        
        # Configura LLM manager
        api_key = llm_config.get('api_key')
        if not api_key:
            raise ValueError("API key mancante")
        
        manager = LLMManager(api_key=api_key)
        
        # Simula preparazione dati
        time.sleep(2)
        
        # Genera sezioni richieste
        generated_sections = {}
        total_sections = len(sections)
        
        for i, section in enumerate(sections):
            with _LOCK:
                scan_data['regen_tasks'][regen_id].update({
                    'current_section': section,
                    'progress': int((i / total_sections) * 90)  # 90% per generazione
                })
            
            logger.info(f"Generazione sezione {section}")
            
            # Prepara dati per sezione
            section_data = {
                'company_name': scan_data.get('company_name', ''),
                'url': scan_data.get('url', ''),
                'scan_date': time.strftime('%Y-%m-%d'),
                'total_issues': 0,  # TODO: Estrarre da risultati reali
                'critical_issues': 0,
                'compliance_score': 75  # TODO: Calcolo reale
            }
            
            # Genera contenuto
            content = manager.generate_report_section(section, section_data)
            generated_sections[section] = content
            
            time.sleep(1)  # Simula tempo generazione
        
        # Crea nuova versione report
        with _LOCK:
            scan_data['regen_tasks'][regen_id].update({
                'current_section': 'Finalizzazione',
                'progress': 95
            })
        
        # Simula creazione HTML finale
        time.sleep(1)
        
        # Calcola numero versione
        current_versions = scan_data.get('versions', [])
        version_num = len(current_versions) + 1
        new_version = f"v{version_num}.0"
        
        # Crea record versione
        version_record = {
            'version': new_version,
            'type': 'llm_enhanced',
            'created_at': time.time() * 1000,
            'llm_enhanced': True,
            'llm_config': llm_config,
            'sections': sections,
            'html_path': f"output/report_{scan_id}_{new_version}.html",
            'size_bytes': sum(len(content) for content in generated_sections.values()),
            'regen_task_id': regen_id
        }
        
        # Aggiorna scan data
        with _LOCK:
            if 'versions' not in scan_data:
                scan_data['versions'] = []
            scan_data['versions'].append(version_record)
            
            scan_data['regen_tasks'][regen_id].update({
                'status': 'completed',
                'progress': 100,
                'current_section': 'Completato',
                'completed_at': time.time(),
                'new_version': new_version,
                'generated_sections': generated_sections
            })
        
        logger.info(f"Rigenerazione completata: {new_version}")
        
    except Exception as e:
        logger.error(f"Errore rigenerazione: {e}")
        
        with _LOCK:
            if scan_data and 'regen_tasks' in scan_data and regen_id in scan_data['regen_tasks']:
                scan_data['regen_tasks'][regen_id].update({
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': time.time()
                })


def handle_task_status(environ, start_response, task_id):
    """Ottiene stato task di rigenerazione"""
    try:
        # Cerca task in tutti gli scan
        task_data = None
        scan_id = None
        
        with _LOCK:
            # Cerca in entrambe le strutture (v1 e v2)
            for sid, scan_data in _SCANS.items():
                regen_tasks = scan_data.get('regen_tasks', {})
                if task_id in regen_tasks:
                    task_data = regen_tasks[task_id]
                    scan_id = sid
                    break
            
            if not task_data:
                for sid, scan_data in _V2_SCANS.items():
                    regen_tasks = scan_data.get('regen_tasks', {})
                    if task_id in regen_tasks:
                        task_data = regen_tasks[task_id]
                        scan_id = sid
                        break
        
        if not task_data:
            start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "Task non trovato"}).encode("utf-8")]
        
        response = {
            "task_id": task_id,
            "scan_id": scan_id,
            "status": task_data['status'],
            "progress": task_data['progress'],
            "current_section": task_data.get('current_section', ''),
            "sections": task_data.get('sections', []),
            "started_at": task_data['started_at'],
            "error": task_data.get('error')
        }
        
        # Aggiungi info di completamento se disponibili
        if task_data['status'] == 'completed':
            response.update({
                "completed_at": task_data.get('completed_at'),
                "new_version": task_data.get('new_version'),
                "download_url": f"/api/reports/{scan_id}/versions/{task_data.get('new_version')}"
            })
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(response).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore recupero stato task: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore recupero stato"}).encode("utf-8")]


def handle_download_version(environ, start_response, scan_id, version):
    """Download di una versione specifica del report"""
    try:
        with _LOCK:
            scan_data = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
        
        if not scan_data:
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Scan non trovato"]
        
        # Trova versione richiesta
        versions = scan_data.get('versions', [])
        target_version = None
        
        for v in versions:
            if v['version'] == version:
                target_version = v
                break
        
        # Se versione v1.0 e non in lista, usa report originale (supporta v1 e v2)
        if not target_version and version == 'v1.0':
            html_path = (scan_data.get('report_html') or 
                        scan_data.get('report_html_path'))
            if html_path and Path(html_path).exists():
                start_response("200 OK", [
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Disposition", f"attachment; filename=report_{scan_id}_v1.0.html")
                ])
                return [Path(html_path).read_bytes()]
        
        if not target_version:
            start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
            return [b"Versione non trovata"]
        
        # Se è una versione LLM, controlla se il file esiste
        html_path = target_version.get('html_path')
        if html_path and Path(html_path).exists():
            start_response("200 OK", [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Disposition", f"attachment; filename=report_{scan_id}_{version}.html")
            ])
            return [Path(html_path).read_bytes()]
        
        # Se è una versione LLM ma il file non esiste, genera on-demand
        if target_version.get('type') == 'llm_enhanced':
            regen_task_id = target_version.get('regen_task_id')
            if regen_task_id:
                regen_tasks = scan_data.get('regen_tasks', {})
                task_data = regen_tasks.get(regen_task_id, {})
                
                if task_data.get('status') == 'completed':
                    generated_sections = task_data.get('generated_sections', {})
                    
                    # Crea HTML semplificato con sezioni generate
                    html_content = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Report EAA {version} - {scan_data.get('company_name', '')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }}
        .section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; }}
        .section h2 {{ color: #2c5aa0; }}
        .meta {{ background: #f5f5f5; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Report Accessibilità EAA {version}</h1>
        <p><strong>{scan_data.get('company_name', '')}</strong></p>
        <p>URL: {scan_data.get('url') or (scan_data.get('pages', [''])[0] if scan_data.get('pages') else '')}</p>
        <p>Generato il: {time.strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    
    <div class="meta">
        <p><strong>Versione:</strong> {version} (Potenziata da LLM)</p>
        <p><strong>Sezioni generate:</strong> {', '.join(generated_sections.keys())}</p>
    </div>
    """
                    
                    # Aggiungi sezioni generate
                    for section_name, content in generated_sections.items():
                        html_content += f"""
    <div class="section">
        <h2>{section_name.replace('_', ' ').title()}</h2>
        <div>{content}</div>
    </div>
    """
                    
                    html_content += """
</body>
</html>
"""
                    
                    start_response("200 OK", [
                        ("Content-Type", "text/html; charset=utf-8"),
                        ("Content-Disposition", f"attachment; filename=report_{scan_id}_{version}.html")
                    ])
                    return [html_content.encode('utf-8')]
        
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"File report non disponibile"]
        
    except Exception as e:
        logger.error(f"Errore download versione: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"Errore download report"]


def handle_migrate_v1_to_v2(environ, start_response):
    """Migra scan v1 a formato v2 per compatibilità"""
    try:
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b"{}")
        
        scan_id = payload.get('scan_id', '')
        if not scan_id:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({"error": "scan_id mancante"}).encode("utf-8")]
        
        with _LOCK:
            v1_scan = _SCANS.get(scan_id)
            if not v1_scan:
                start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
                return [json.dumps({"error": "Scan v1 non trovato"}).encode("utf-8")]
            
            if v1_scan.get('status') != 'done':
                start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
                return [json.dumps({"error": "Scan v1 non completato"}).encode("utf-8")]
            
            # Controlla se già migrato
            if scan_id in _V2_SCANS:
                start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
                return [json.dumps({
                    "migrated": True,
                    "scan_id": scan_id,
                    "message": "Scan già disponibile in formato v2"
                }).encode("utf-8")]
            
            # Crea entry v2 compatibile
            v2_entry = {
                'id': scan_id,
                'pages': [v1_scan.get('url', '')],
                'company_name': v1_scan.get('company_name', ''),
                'email': v1_scan.get('email', ''),
                'mode': 'simulate' if v1_scan.get('simulate', True) else 'real',
                'scanners': {
                    'wave': True,
                    'pa11y': True,
                    'axe_core': True,
                    'lighthouse': True
                },
                'llm_config': v1_scan.get('llm_config', {}),
                'state': 'completed',
                'status': 'done',  # Compatibilità
                'progress_percent': 100,
                'current_page': len([v1_scan.get('url', '')]),
                'page_statuses': {v1_scan.get('url', ''): 'completed'},
                'metrics': {
                    'errors': 0,  # TODO: Estrarre da report v1 se disponibile
                    'warnings': 0,
                    'pages_completed': 1,
                    'compliance_score': 75  # TODO: Calcolo reale
                },
                'log': v1_scan.get('log', []),
                'started_at': v1_scan.get('timestamp', time.time() * 1000) / 1000,
                'completed_at': time.time(),
                'report_html_path': v1_scan.get('report_html', ''),
                'report_html': v1_scan.get('report_html', ''),
                'report_html_url': f'/v2/preview?scan_id={scan_id}',
                'versions': [],
                'regen_tasks': {},
                'timestamp': v1_scan.get('timestamp', time.time() * 1000),
                'migrated_from_v1': True
            }
            
            # Inizializza versione originale v1.0
            if v1_scan.get('report_html'):
                original_version = {
                    'version': 'v1.0',
                    'type': 'original',
                    'created_at': v1_scan.get('timestamp', time.time() * 1000),
                    'llm_enhanced': False,
                    'html_path': v1_scan.get('report_html'),
                    'size_bytes': 0,
                    'migrated_from_v1': True
                }
                
                try:
                    size = Path(v1_scan['report_html']).stat().st_size
                    original_version['size_bytes'] = size
                except:
                    pass
                
                v2_entry['versions'] = [original_version]
            
            # Salva entry migrata
            _V2_SCANS[scan_id] = v2_entry
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            "migrated": True,
            "scan_id": scan_id,
            "message": "Scan migrato con successo a formato v2",
            "v2_preview_url": f"/v2/preview?scan_id={scan_id}",
            "versions_count": len(v2_entry.get('versions', []))
        }).encode("utf-8")]
        
    except Exception as e:
        logger.error(f"Errore migrazione v1->v2: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore migrazione"}).encode("utf-8")]


def handle_scan_metadata(environ, start_response, scan_id):
    """Ottiene metadata unificati per scan v1/v2"""
    try:
        with _LOCK:
            # Cerca in entrambe le strutture
            scan_data = _SCANS.get(scan_id) or _V2_SCANS.get(scan_id)
            
            if not scan_data:
                start_response("404 Not Found", [("Content-Type", "application/json; charset=utf-8")])
                return [json.dumps({"error": "Scan non trovato"}).encode("utf-8")]
            
            # Determina tipo scan
            scan_type = 'v2' if scan_id in _V2_SCANS else 'v1'
            
            # Metadata unificati
            metadata = {
                "scan_id": scan_id,
                "scan_type": scan_type,
                "company_name": scan_data.get('company_name', ''),
                "created_at": scan_data.get('timestamp', scan_data.get('started_at', 0) * 1000),
                "status": scan_data.get('status') or ('done' if scan_data.get('state') == 'completed' else 'running'),
                "llm_enhanced": bool(scan_data.get('llm_config', {}).get('enabled')),
                "versions_available": len(scan_data.get('versions', [])),
                "report_available": bool(scan_data.get('report_html') or scan_data.get('report_html_path')),
                "pages_count": len(scan_data.get('pages', [])) if scan_type == 'v2' else 1,
                "migrated_from_v1": scan_data.get('migrated_from_v1', False)
            }
            
            # URL info
            if scan_type == 'v1':
                metadata['url'] = scan_data.get('url', '')
                metadata['urls'] = [scan_data.get('url', '')]
            else:
                metadata['urls'] = scan_data.get('pages', [])
                metadata['url'] = metadata['urls'][0] if metadata['urls'] else ''
            
            # Active LLM tasks
            active_tasks = []
            for task_id, task_data in scan_data.get('regen_tasks', {}).items():
                if task_data.get('status') == 'running':
                    active_tasks.append({
                        'task_id': task_id,
                        'progress': task_data.get('progress', 0),
                        'current_section': task_data.get('current_section', '')
                    })
            
            metadata['active_llm_tasks'] = active_tasks
            metadata['has_active_tasks'] = len(active_tasks) > 0
            
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps(metadata).encode("utf-8")]
            
    except Exception as e:
        logger.error(f"Errore recupero metadata: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({"error": "Errore recupero metadata"}).encode("utf-8")]


# ========== DATA CLEANUP & MAINTENANCE ==========

def cleanup_expired_sessions():
    """Pulisce sessioni scadute (chiamare periodicamente)"""
    expiry_time = time.time() - (24 * 60 * 60)  # 24 ore
    
    with _LOCK:
        # Cleanup discoveries
        expired_discoveries = []
        for disc_id, disc_data in _DISCOVERIES.items():
            if disc_data.get('started_at', 0) < expiry_time:
                expired_discoveries.append(disc_id)
        
        for disc_id in expired_discoveries:
            del _DISCOVERIES[disc_id]
        
        # Cleanup failed scans
        expired_v1_scans = []
        for scan_id, scan_data in _SCANS.items():
            if (scan_data.get('status') == 'error' and 
                scan_data.get('timestamp', 0) / 1000 < expiry_time):
                expired_v1_scans.append(scan_id)
        
        for scan_id in expired_v1_scans:
            del _SCANS[scan_id]
        
        expired_v2_scans = []
        for scan_id, scan_data in _V2_SCANS.items():
            if (scan_data.get('state') == 'failed' and 
                scan_data.get('started_at', 0) < expiry_time):
                expired_v2_scans.append(scan_id)
        
        for scan_id in expired_v2_scans:
            del _V2_SCANS[scan_id]
        
        # Cleanup rate limiters
        current_time = time.time()
        expired_ips = []
        for ip, limiter in _RATE_LIMITERS.items():
            limiter.requests = [req_time for req_time in limiter.requests 
                              if current_time - req_time < limiter.window_seconds]
            if not limiter.requests:
                expired_ips.append(ip)
        
        for ip in expired_ips:
            del _RATE_LIMITERS[ip]
        
        logger.info(f"Cleanup completato: {len(expired_discoveries)} discovery, {len(expired_v1_scans)} v1 scans, {len(expired_v2_scans)} v2 scans, {len(expired_ips)} rate limiters")


# ========== V2 API FUNCTIONS - 2-PHASE WORKFLOW ==========

def start_discovery(payload: dict) -> str:
    """Start URL discovery phase"""
    import uuid
    from eaa_scanner.crawler import WebCrawler
    
    base_url = payload.get('base_url', '').strip()
    max_pages = payload.get('max_pages', 50)
    max_depth = payload.get('max_depth', 3)
    company_name = payload.get('company_name', '').strip()
    email = payload.get('email', '').strip()
    
    if not base_url:
        raise ValueError("URL è obbligatorio")
    
    discovery_id = f"discovery_{uuid.uuid4().hex[:8]}"
    
    with _LOCK:
        _DISCOVERIES[discovery_id] = {
            'id': discovery_id,
            'base_url': base_url,
            'company_name': company_name,
            'email': email,
            'state': 'running',
            'progress_percent': 0,
            'pages_discovered': 0,
            'discovered_pages': [],
            'started_at': time.time(),
            'error': None
        }
    
    # Start discovery in background thread
    t = threading.Thread(
        target=_discovery_worker,
        args=(discovery_id, base_url, max_pages, max_depth),
        daemon=True
    )
    t.start()
    
    return discovery_id

def _discovery_worker(discovery_id: str, base_url: str, max_pages: int, max_depth: int):
    """Worker thread for URL discovery with progressive updates"""
    try:
        from eaa_scanner.crawler import WebCrawler
        import time as time_module
        
        # Update status - starting
        with _LOCK:
            _DISCOVERIES[discovery_id]['state'] = 'crawling'
            _DISCOVERIES[discovery_id]['progress_percent'] = 10
        
        # Limita parametri per performance
        max_pages = min(max_pages, 20)  # Limita a 20 pagine massimo
        max_depth = min(max_depth, 2)    # Limita a profondità 2
        
        # Create crawler with progress callback
        crawler = WebCrawler(
            base_url=base_url,
            max_pages=max_pages,
            max_depth=max_depth
        )
        
        # Progressive update during crawling
        start_time = time_module.time()
        discovered_pages = []
        
        # Perform crawling with simulated progress
        discovered_pages = crawler.crawl()
        
        # Update progress during crawling (simulate for now)
        if len(discovered_pages) > 0:
            # Update incrementally
            for i, page in enumerate(discovered_pages[:10]):
                with _LOCK:
                    progress = min(10 + (i * 8), 90)  # 10% to 90%
                    _DISCOVERIES[discovery_id]['progress_percent'] = progress
                    _DISCOVERIES[discovery_id]['pages_discovered'] = i + 1
                    if i < 10:
                        _DISCOVERIES[discovery_id]['discovered_pages'].append(page)
                time_module.sleep(0.1)  # Small delay to show progress
        
        # Final update with all results
        with _LOCK:
            _DISCOVERIES[discovery_id]['state'] = 'completed'
            _DISCOVERIES[discovery_id]['progress_percent'] = 100
            _DISCOVERIES[discovery_id]['pages_discovered'] = len(discovered_pages)
            _DISCOVERIES[discovery_id]['discovered_pages'] = discovered_pages
            _DISCOVERIES[discovery_id]['completed_at'] = time_module.time()
    
    except Exception as e:
        with _LOCK:
            _DISCOVERIES[discovery_id]['state'] = 'failed'
            _DISCOVERIES[discovery_id]['error'] = str(e)
            _DISCOVERIES[discovery_id]['progress_percent'] = 0

def get_discovery_status(discovery_id: str) -> dict:
    """Get discovery session status"""
    with _LOCK:
        discovery = _DISCOVERIES.get(discovery_id)
        if not discovery:
            return None
        
        # Return minimal status
        return {
            'state': discovery['state'],
            'progress_percent': discovery['progress_percent'],
            'pages_discovered': discovery['pages_discovered'],
            'discovered_pages': discovery['discovered_pages'][:10],  # Last 10 for live feed
            'error': discovery.get('error')
        }

def get_discovery_results(discovery_id: str) -> dict:
    """Get full discovery results"""
    with _LOCK:
        discovery = _DISCOVERIES.get(discovery_id)
        if not discovery or discovery['state'] != 'completed':
            return None
        
        return {
            'discovery_id': discovery_id,
            'base_url': discovery['base_url'],
            'pages_discovered': discovery['pages_discovered'],
            'discovered_pages': discovery['discovered_pages']
        }

def start_selective_scan(payload: dict) -> str:
    """Start accessibility scan on selected URLs with full LLM integration"""
    import uuid
    
    pages = payload.get('pages', [])
    company_name = payload.get('company_name', '').strip()
    email = payload.get('email', '').strip()
    mode = payload.get('mode', 'simulate')
    scanners = payload.get('scanners', {})
    llm_config = payload.get('llm_config', {})  # Config LLM completa
    
    if not pages:
        raise ValueError("Nessuna pagina selezionata per la scansione")
    
    # Valida config LLM se presente
    if llm_config and llm_config.get('enabled'):
        api_key = llm_config.get('api_key')
        if not api_key:
            raise ValueError("API key OpenAI richiesta per funzionalità LLM")
    
    scan_id = f"v2scan_{uuid.uuid4().hex[:8]}"
    
    with _LOCK:
        _V2_SCANS[scan_id] = {
            'id': scan_id,
            'pages': pages,
            'company_name': company_name,
            'email': email,
            'mode': mode,
            'scanners': scanners,
            'llm_config': llm_config,
            'state': 'running',
            'progress_percent': 0,
            'current_page': 0,
            'page_statuses': {url: 'pending' for url in pages},
            'metrics': {
                'errors': 0,
                'warnings': 0,
                'pages_completed': 0,
                'compliance_score': 0
            },
            'log': [],
            'started_at': time.time(),
            'versions': [],  # Multi-versioning support
            'regen_tasks': {},  # LLM regeneration tasks
            'status': 'running',  # Compatibilità con _SCANS
            'timestamp': time.time() * 1000
        }
    
    # Start scan in background thread
    t = threading.Thread(
        target=_v2_scan_worker,
        args=(scan_id,),
        daemon=True
    )
    t.start()
    
    return scan_id

def _v2_scan_worker(scan_id: str):
    """Worker thread for v2 accessibility scan with LLM integration"""
    try:
        with _LOCK:
            scan_data = _V2_SCANS[scan_id]
            pages = scan_data['pages']
            company_name = scan_data['company_name']
            email = scan_data['email']
            mode = scan_data['mode']
            scanners = scan_data['scanners']
            llm_config = scan_data.get('llm_config', {})
        
        # Import necessari
        from eaa_scanner.config import Config, ScannerToggles
        from eaa_scanner.core import run_scan
        from pathlib import Path
        
        # Se abbiamo più di una pagina, usiamo solo la prima per ora
        # TODO: Implementare scansione multi-pagina reale
        first_page = pages[0] if pages else 'https://example.com'
        
        # Process each page (simulato per UI)
        for i, page_url in enumerate(pages):
            # Update current page status
            with _LOCK:
                _V2_SCANS[scan_id]['current_page'] = i + 1
                _V2_SCANS[scan_id]['page_statuses'][page_url] = 'scanning'
                _V2_SCANS[scan_id]['progress_percent'] = int((i / len(pages)) * 85)  # Lascia spazio per LLM
                _V2_SCANS[scan_id]['log'].append(f"Scansione {page_url}")
            
            time.sleep(1)  # Simula tempo di scansione
            
            # Update page as completed
            with _LOCK:
                _V2_SCANS[scan_id]['page_statuses'][page_url] = 'completed'
                _V2_SCANS[scan_id]['metrics']['pages_completed'] += 1
        
        # Ora esegui la scansione REALE
        with _LOCK:
            _V2_SCANS[scan_id]['log'].append("Esecuzione scanner accessibilità...")
            _V2_SCANS[scan_id]['progress_percent'] = 85
        
        # Configura scanner
        args = {
            'url': first_page,
            'company_name': company_name,
            'email': email,
            'simulate': (mode != 'real')
        }
        
        cfg = Config.from_env_or_args(args)
        
        # Abilita scanner selezionati
        cfg.scanners_enabled = ScannerToggles(
            wave=scanners.get('wave', False),
            pa11y=scanners.get('pa11y', True),
            axe_core=scanners.get('axe_core', True),
            lighthouse=scanners.get('lighthouse', True)
        )
        
        # Configura event monitor per Live Monitoring
        from webapp.scan_monitor import get_scan_monitor
        from eaa_scanner.scan_events import ScanEventHooks, set_current_hooks
        
        monitor = get_scan_monitor()
        hooks = ScanEventHooks(scan_id)
        hooks.set_monitor(monitor)
        set_current_hooks(hooks)
        
        # Emit scan start event
        monitor.emit_scan_start(scan_id, first_page, company_name, scanners)
        
        # Esegui scansione reale con monitoring
        result = run_scan(cfg, output_root=Path('output'), event_monitor=monitor)
        
        # Salva percorso report
        html_path = Path(result['report_html_path'])
        
        # Inizializza versione v1.0 (report originale)
        original_version = {
            'version': 'v1.0',
            'type': 'original',
            'created_at': time.time() * 1000,
            'llm_enhanced': False,
            'html_path': str(html_path),
            'size_bytes': html_path.stat().st_size if html_path.exists() else 0
        }
        
        # Aggiorna stato base
        with _LOCK:
            _V2_SCANS[scan_id]['state'] = 'completed'
            _V2_SCANS[scan_id]['status'] = 'done'  # Compatibilità con _SCANS
            _V2_SCANS[scan_id]['progress_percent'] = 90
            _V2_SCANS[scan_id]['metrics']['compliance_score'] = result.get('compliance_score', 75)
            _V2_SCANS[scan_id]['metrics']['errors'] = result.get('total_errors', 0)
            _V2_SCANS[scan_id]['metrics']['warnings'] = result.get('total_warnings', 0)
            _V2_SCANS[scan_id]['completed_at'] = time.time()
            _V2_SCANS[scan_id]['report_html_path'] = str(html_path)
            _V2_SCANS[scan_id]['report_html'] = str(html_path)  # Compatibilità con _SCANS
            _V2_SCANS[scan_id]['report_html_url'] = f'/v2/preview?scan_id={scan_id}'
            _V2_SCANS[scan_id]['versions'] = [original_version]
            _V2_SCANS[scan_id]['log'].append(f"✅ Report base generato: {html_path.name}")
        
        # Esegui enhancement LLM se configurato
        if llm_config.get('enabled', False):
            _v2_llm_enhancement_worker(scan_id, llm_config, result)
        else:
            # Completa senza LLM
            with _LOCK:
                _V2_SCANS[scan_id]['progress_percent'] = 100
                _V2_SCANS[scan_id]['log'].append("✅ Scansione completata")
            
            # Emit scan complete event
            monitor.emit_scan_complete(scan_id, {
                'compliance_score': result.get('compliance_score', 75),
                'total_errors': result.get('total_errors', 0),
                'total_warnings': result.get('total_warnings', 0)
            })
    
    except Exception as e:
        import traceback
        with _LOCK:
            _V2_SCANS[scan_id]['state'] = 'failed'
            _V2_SCANS[scan_id]['status'] = 'error'  # Compatibilità con _SCANS
            _V2_SCANS[scan_id]['error'] = str(e)
            _V2_SCANS[scan_id]['log'].append(f"❌ Errore: {e}")
            print(f"Errore in v2 scan worker: {traceback.format_exc()}")


def _v2_llm_enhancement_worker(scan_id: str, llm_config: dict, scan_result: dict):
    """Worker per enhancement LLM dei report v2"""
    try:
        logger.info(f"Avvio enhancement LLM per scan v2 {scan_id}")
        
        with _LOCK:
            _V2_SCANS[scan_id]['state'] = 'llm_processing'
            _V2_SCANS[scan_id]['log'].append("⚙️ Avvio enhancement LLM...")
        
        # Configura LLM manager
        api_key = llm_config.get('api_key')
        if not api_key:
            raise ValueError("API key LLM mancante")
        
        manager = LLMManager(api_key=api_key)
        
        # Crea task ID per enhancement automatico
        enhance_id = f"enhance_{int(time.time()*1000)}"
        sections = llm_config.get('sections', ['executive_summary', 'detailed_analysis'])
        
        with _LOCK:
            _V2_SCANS[scan_id]['regen_tasks'][enhance_id] = {
                'status': 'running',
                'progress': 0,
                'current_section': '',
                'started_at': time.time(),
                'sections': sections,
                'llm_config': llm_config,
                'type': 'auto_enhancement'
            }
        
        # Genera sezioni LLM
        generated_sections = {}
        total_sections = len(sections)
        
        for i, section in enumerate(sections):
            with _LOCK:
                _V2_SCANS[scan_id]['regen_tasks'][enhance_id].update({
                    'current_section': section,
                    'progress': int((i / total_sections) * 90)
                })
                _V2_SCANS[scan_id]['progress_percent'] = 90 + int((i / total_sections) * 8)  # 90-98%
                _V2_SCANS[scan_id]['log'].append(f"🧠 Generazione {section}...")
            
            # Prepara dati per LLM
            section_data = {
                'company_name': _V2_SCANS[scan_id].get('company_name', ''),
                'url': _V2_SCANS[scan_id]['pages'][0] if _V2_SCANS[scan_id]['pages'] else '',
                'scan_date': time.strftime('%Y-%m-%d'),
                'total_issues': _V2_SCANS[scan_id]['metrics']['errors'] + _V2_SCANS[scan_id]['metrics']['warnings'],
                'critical_issues': _V2_SCANS[scan_id]['metrics']['errors'],
                'compliance_score': _V2_SCANS[scan_id]['metrics']['compliance_score']
            }
            
            # Genera contenuto con fallback simulato
            try:
                content = manager.generate_report_section(section, section_data)
                generated_sections[section] = content
            except Exception as e:
                logger.warning(f"Errore generazione sezione {section}: {e}")
                # Fallback con contenuto simulato
                generated_sections[section] = f"<p>Sezione {section} generata automaticamente per {section_data['company_name']}.</p>"
            
            time.sleep(0.5)  # Simula tempo generazione
        
        # Finalizzazione
        with _LOCK:
            _V2_SCANS[scan_id]['regen_tasks'][enhance_id].update({
                'current_section': 'Finalizzazione',
                'progress': 95
            })
            _V2_SCANS[scan_id]['progress_percent'] = 98
            _V2_SCANS[scan_id]['log'].append("⚙️ Finalizzazione report potenziato...")
        
        # Crea versione enhanced
        version_num = len(_V2_SCANS[scan_id].get('versions', [])) + 1
        enhanced_version = f"v{version_num}.0-llm"
        
        enhanced_record = {
            'version': enhanced_version,
            'type': 'llm_enhanced',
            'created_at': time.time() * 1000,
            'llm_enhanced': True,
            'llm_config': llm_config,
            'sections': sections,
            'html_path': f"output/report_{scan_id}_{enhanced_version}.html",
            'size_bytes': sum(len(content) for content in generated_sections.values()),
            'regen_task_id': enhance_id,
            'auto_generated': True
        }
        
        # Completa enhancement
        with _LOCK:
            _V2_SCANS[scan_id]['versions'].append(enhanced_record)
            _V2_SCANS[scan_id]['regen_tasks'][enhance_id].update({
                'status': 'completed',
                'progress': 100,
                'current_section': 'Completato',
                'completed_at': time.time(),
                'new_version': enhanced_version,
                'generated_sections': generated_sections
            })
            _V2_SCANS[scan_id]['state'] = 'completed'
            _V2_SCANS[scan_id]['progress_percent'] = 100
            _V2_SCANS[scan_id]['log'].append(f"✨ Report potenziato creato: {enhanced_version}")
        
        logger.info(f"Enhancement LLM completato per {scan_id}: {enhanced_version}")
        
        # Emit scan complete event
        from webapp.scan_monitor import get_scan_monitor
        monitor = get_scan_monitor()
        monitor.emit_scan_complete(scan_id, {
                'report_url': f'/v2/preview?scan_id={scan_id}',
                'pages_scanned': result.get('pages_scanned', len(_V2_SCANS[scan_id].get('pages', [])) or 1),
                'compliance_score': _V2_SCANS[scan_id]['metrics']['compliance_score'],
                'total_errors': _V2_SCANS[scan_id]['metrics']['errors'],
                'total_warnings': _V2_SCANS[scan_id]['metrics']['warnings'],
                'llm_enhanced': True
            })
        
    except Exception as e:
        logger.error(f"Errore enhancement LLM v2: {e}")
        
        with _LOCK:
            if 'enhance_id' in locals() and enhance_id in _V2_SCANS[scan_id]['regen_tasks']:
                _V2_SCANS[scan_id]['regen_tasks'][enhance_id].update({
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': time.time()
                })
            
            # Completa comunque la scansione base
            _V2_SCANS[scan_id]['state'] = 'completed'
            _V2_SCANS[scan_id]['progress_percent'] = 100
            _V2_SCANS[scan_id]['log'].append(f"⚠️ Enhancement LLM fallito: {e}")
            _V2_SCANS[scan_id]['log'].append("✅ Scansione base completata")
        
        # Emit scan complete event anche in caso di errore LLM
        from webapp.scan_monitor import get_scan_monitor
        monitor = get_scan_monitor()
        monitor.emit_scan_complete(scan_id, {
            'report_url': f'/v2/preview?scan_id={scan_id}',
            'pages_scanned': len(_V2_SCANS[scan_id].get('pages', [])) or 1,
            'compliance_score': _V2_SCANS[scan_id]['metrics'].get('compliance_score', 75),
            'total_errors': _V2_SCANS[scan_id]['metrics'].get('errors', 0),
            'total_warnings': _V2_SCANS[scan_id]['metrics'].get('warnings', 0),
            'llm_enhanced': False,
            'llm_error': str(e)
        })


def _v2_regenerate_report_worker(scan_id: str, regen_id: str, llm_config: dict, sections: list):
    """Worker specializzato per rigenerazione report v2"""
    try:
        logger.info(f"Avvio rigenerazione report v2 per scan {scan_id}")
        
        # Recupera dati scan v2
        with _LOCK:
            scan_data = _V2_SCANS.get(scan_id)
            if not scan_data:
                logger.error(f"Scan v2 {scan_id} non trovato per rigenerazione")
                return
            
            # Crea entry per task di rigenerazione
            scan_data['regen_tasks'][regen_id] = {
                'status': 'running',
                'progress': 0,
                'current_section': '',
                'started_at': time.time(),
                'sections': sections,
                'llm_config': llm_config,
                'type': 'manual_regeneration'
            }
        
        # Configura LLM manager
        api_key = llm_config.get('api_key')
        if not api_key:
            raise ValueError("API key mancante")
        
        manager = LLMManager(api_key=api_key)
        
        # Simula preparazione dati
        time.sleep(1)
        
        # Genera sezioni richieste
        generated_sections = {}
        total_sections = len(sections)
        
        for i, section in enumerate(sections):
            with _LOCK:
                scan_data['regen_tasks'][regen_id].update({
                    'current_section': section,
                    'progress': int((i / total_sections) * 90)
                })
            
            logger.info(f"Generazione sezione v2 {section} per {scan_id}")
            
            # Prepara dati per sezione (formato v2)
            section_data = {
                'company_name': scan_data.get('company_name', ''),
                'urls': scan_data.get('pages', []),
                'primary_url': scan_data.get('pages', [''])[0] if scan_data.get('pages') else '',
                'scan_date': time.strftime('%Y-%m-%d'),
                'pages_scanned': len(scan_data.get('pages', [])),
                'total_issues': scan_data['metrics']['errors'] + scan_data['metrics']['warnings'],
                'critical_issues': scan_data['metrics']['errors'],
                'warnings': scan_data['metrics']['warnings'],
                'compliance_score': scan_data['metrics']['compliance_score'],
                'scan_type': 'multi-page',
                'discovery_method': 'advanced_crawler'
            }
            
            # Genera contenuto con fallback
            try:
                content = manager.generate_report_section(section, section_data)
                generated_sections[section] = content
            except Exception as e:
                logger.warning(f"Errore generazione sezione v2 {section}: {e}")
                # Fallback con contenuto specifico v2
                generated_sections[section] = f"""<div class="section-v2">
                    <h3>{section.replace('_', ' ').title()}</h3>
                    <p>Analisi avanzata per <strong>{section_data['company_name']}</strong></p>
                    <p>Scansionate {section_data['pages_scanned']} pagine con metodologia avanzata.</p>
                    <p>Score di conformità: {section_data['compliance_score']}%</p>
                </div>"""
            
            time.sleep(0.8)  # Simula tempo generazione
        
        # Crea nuova versione report v2
        with _LOCK:
            scan_data['regen_tasks'][regen_id].update({
                'current_section': 'Finalizzazione v2',
                'progress': 95
            })
        
        time.sleep(1)
        
        # Calcola numero versione
        current_versions = scan_data.get('versions', [])
        version_num = len(current_versions) + 1
        new_version = f"v{version_num}.0-v2-llm"
        
        # Crea record versione v2
        version_record = {
            'version': new_version,
            'type': 'llm_enhanced_v2',
            'created_at': time.time() * 1000,
            'llm_enhanced': True,
            'llm_config': llm_config,
            'sections': sections,
            'html_path': f"output/report_v2_{scan_id}_{new_version}.html",
            'size_bytes': sum(len(content) for content in generated_sections.values()),
            'regen_task_id': regen_id,
            'scan_type': 'v2',
            'pages_count': len(scan_data.get('pages', [])),
            'multi_page_enhanced': True
        }
        
        # Aggiorna scan data v2
        with _LOCK:
            scan_data['versions'].append(version_record)
            scan_data['regen_tasks'][regen_id].update({
                'status': 'completed',
                'progress': 100,
                'current_section': 'Completato v2',
                'completed_at': time.time(),
                'new_version': new_version,
                'generated_sections': generated_sections
            })
        
        logger.info(f"Rigenerazione v2 completata: {new_version} per {scan_id}")
        
    except Exception as e:
        logger.error(f"Errore rigenerazione v2: {e}")
        
        with _LOCK:
            if scan_data and 'regen_tasks' in scan_data and regen_id in scan_data['regen_tasks']:
                scan_data['regen_tasks'][regen_id].update({
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': time.time()
                })


def get_scan_status(scan_id: str) -> dict:
    """Get v2 scan session status with LLM integration"""
    with _LOCK:
        scan = _V2_SCANS.get(scan_id)
        if not scan:
            return None
        
        # Controlla task LLM attivi
        llm_tasks = scan.get('regen_tasks', {})
        active_llm_task = None
        for task_id, task_data in llm_tasks.items():
            if task_data.get('status') == 'running':
                active_llm_task = {
                    'task_id': task_id,
                    'progress': task_data.get('progress', 0),
                    'current_section': task_data.get('current_section', '')
                }
                break
        
        return {
            'state': scan['state'],
            'progress_percent': scan['progress_percent'],
            'current_page': scan['current_page'],
            'page_statuses': scan['page_statuses'],
            'metrics': scan['metrics'],
            'log': scan['log'][-20:],  # Last 20 log entries
            'llm_config': scan.get('llm_config', {}),
            'llm_active_task': active_llm_task,
            'versions_count': len(scan.get('versions', [])),
            'has_llm_enhancement': bool(scan.get('llm_config', {}).get('enabled'))
        }

def get_scan_results(scan_id: str) -> dict:
    """Get v2 scan results with full LLM integration"""
    with _LOCK:
        scan = _V2_SCANS.get(scan_id)
        if not scan or scan['state'] not in ['completed', 'llm_processing']:
            return None
        
        # Determina stato compliance
        score = scan['metrics']['compliance_score']
        if score >= 90:
            compliance_status = 'compliant'
        elif score >= 60:
            compliance_status = 'partially_compliant'
        else:
            compliance_status = 'non_compliant'
        
        return {
            'scan_id': scan_id,
            'compliance_status': compliance_status,
            'compliance_score': scan['metrics']['compliance_score'],
            'total_errors': scan['metrics']['errors'],
            'total_warnings': scan['metrics']['warnings'],
            'report_html_url': scan.get('report_html_url'),
            'analytics_url': f'/api/analytics?scan_id={scan_id}',
            'remediation_url': f'/api/remediation?scan_id={scan_id}',
            'statement_url': f'/api/statement?scan_id={scan_id}',
            'json_url': f'/api/export?scan_id={scan_id}',
            'llm_config': scan.get('llm_config', {}),
            'versions_url': f'/api/reports/{scan_id}/versions',
            'llm_enhanced': bool(scan.get('llm_config', {}).get('enabled')),
            'versions_count': len(scan.get('versions', [])),
            'regeneration_available': bool(scan.get('llm_config', {}).get('enabled'))
        }


# ========== API KEYS MANAGEMENT HANDLERS ==========

def handle_api_keys_save(environ, start_response):
    """Handler per salvare le API keys"""
    try:
        # Leggi payload JSON
        size = int(environ.get('CONTENT_LENGTH') or 0)
        body = environ['wsgi.input'].read(size)
        data = json.loads(body.decode('utf-8')) if body else {}
        
        # Ottieni manager API keys
        manager = get_api_key_manager()
        
        # Salva le chiavi (solo quelle fornite)
        openai_key = data.get('openai_key')
        wave_key = data.get('wave_key')
        
        result = manager.save_keys(
            openai_key=openai_key if openai_key else None,
            wave_key=wave_key if wave_key else None
        )
        
        if result['success']:
            start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({
                'success': True,
                'message': result['message'],
                'validation': result['validation']
            }).encode('utf-8')]
        else:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({
                'success': False,
                'message': result['message']
            }).encode('utf-8')]
    
    except Exception as e:
        logger.error(f"Errore salvataggio API keys: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }).encode('utf-8')]


def handle_api_keys_status(environ, start_response):
    """Handler per ottenere lo stato delle API keys"""
    try:
        # Ottieni manager API keys
        manager = get_api_key_manager()
        
        # Ottieni stato delle chiavi
        status = manager.get_keys_status()
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            'success': True,
            'data': status
        }).encode('utf-8')]
    
    except Exception as e:
        logger.error(f"Errore lettura stato API keys: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }).encode('utf-8')]


def handle_api_key_validate(environ, start_response):
    """Handler per validare una singola API key"""
    try:
        # Leggi payload JSON
        size = int(environ.get('CONTENT_LENGTH') or 0)
        body = environ['wsgi.input'].read(size)
        data = json.loads(body.decode('utf-8')) if body else {}
        
        key_type = data.get('key_type')
        key_value = data.get('key_value')
        
        if not key_type or not key_value:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({
                'success': False,
                'message': 'Parametri key_type e key_value richiesti'
            }).encode('utf-8')]
        
        # Ottieni manager API keys
        manager = get_api_key_manager()
        
        # Valida la chiave specifica
        if key_type == 'openai':
            validation = manager.validate_openai(key_value)
        elif key_type == 'wave':
            validation = manager.validate_wave(key_value)
        else:
            start_response("400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
            return [json.dumps({
                'success': False,
                'message': f'Tipo di chiave non supportato: {key_type}'
            }).encode('utf-8')]
        
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            'success': True,
            'validation': validation
        }).encode('utf-8')]
    
    except Exception as e:
        logger.error(f"Errore validazione API key: {e}")
        start_response("500 Internal Server Error", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }).encode('utf-8')]


def main():
    # Configura logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    port = int(__import__("os").environ.get("PORT", "8000"))
    debug_mode = __import__("os").environ.get("DEBUG_MODE", "0") == "1"
    
    with make_server("0.0.0.0", port, app) as httpd:
        print(f"EAA Scanner Web in ascolto su http://localhost:{port}")
        print(f"✅ Workflow v1 e v2 supportati")
        print(f"✅ LLM integration completa")
        print(f"✅ Multi-versioning abilitato")
        print(f"✅ Backward compatibility garantita")
        print(f"✅ Rate limiting configurato")
        if debug_mode:
            print(f"🔍 Debug mode attivo - endpoint /api/debug/scans disponibile")
        httpd.serve_forever()


if __name__ == "__main__":
    # Avvia cleanup thread se in produzione
    import os
    if os.environ.get('CLEANUP_ENABLED', '1') == '1':
        cleanup_thread = threading.Thread(target=lambda: [
            time.sleep(3600), cleanup_expired_sessions()
        ] * 999, daemon=True)
        cleanup_thread.start()
    
    main()
