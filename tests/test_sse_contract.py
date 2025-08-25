import os
import json
import threading
import time
from wsgiref.simple_server import make_server

import requests
import pytest

# Skip dell'intero modulo se SSE è disabilitato a livello progetto
if str(os.getenv("EAA_ENABLE_SSE", "false")).lower() not in ("1", "true", "yes"):
    pytest.skip("SSE disabilitato nel progetto", allow_module_level=True)


def run_server(app, port):
    httpd = make_server("127.0.0.1", port, app)
    httpd.serve_forever()


def test_sse_event_shapes():
    # Lazy import to ensure module paths are set
    from webapp.app import app as wsgi_app
    from webapp.scan_monitor import get_scan_monitor

    port = 8765
    server_thread = threading.Thread(target=run_server, args=(wsgi_app, port), daemon=True)
    server_thread.start()

    scan_id = "TEST_SSE_123"
    monitor = get_scan_monitor()

    # Preload a scan_start event in history
    monitor.emit_scan_start(scan_id, url="https://example.com", company_name="Acme Inc", scanners_enabled={"wave": True, "pa11y": False, "axe": True, "lighthouse": True})

    # Connect to SSE endpoint
    url = f"http://127.0.0.1:{port}/api/scan/stream/{scan_id}"
    resp = requests.get(url, stream=True, headers={"Accept": "text/event-stream"}, timeout=10)
    assert resp.status_code == 200

    got_scan_start = False
    got_heartbeat = False

    start = time.time()
    for line in resp.iter_lines():
        if not line:
            # empty separator between events
            if time.time() - start > 5:
                break
            continue
        if line.startswith(b"data: "):
            payload = json.loads(line[6:].decode("utf-8"))
            assert "event_type" in payload
            assert "timestamp" in payload
            assert payload.get("scan_id") == scan_id

            if payload["event_type"] == "scan_start":
                got_scan_start = True
                assert "message" in payload  # top-level message per contract
                data = payload.get("data", {})
                assert data.get("company_name") == "Acme Inc"
                assert data.get("url") == "https://example.com"
                assert isinstance(data.get("scanners"), list)

            if payload["event_type"] == "heartbeat":
                got_heartbeat = True
                hb = payload.get("data", {})
                assert "uptime_ms" in hb
                assert isinstance(hb.get("uptime_ms"), int)

            if got_scan_start and got_heartbeat:
                break

    assert got_scan_start, "Expected to receive scan_start event"
    assert got_heartbeat, "Expected to receive at least one heartbeat event"


def test_sse_terminal_events():
    # This test ensures terminal events follow the contract
    from webapp.app import app as wsgi_app
    from webapp.scan_monitor import get_scan_monitor

    port = 8766
    server_thread = threading.Thread(target=run_server, args=(wsgi_app, port), daemon=True)
    server_thread.start()

    scan_id = "TEST_SSE_TERM_1"
    monitor = get_scan_monitor()

    # Connect first, then emit events
    url = f"http://127.0.0.1:{port}/api/scan/stream/{scan_id}"
    resp = requests.get(url, stream=True, headers={"Accept": "text/event-stream"}, timeout=10)
    assert resp.status_code == 200

    # Emit a scan_complete minimal payload
    monitor.emit_scan_complete(scan_id, {
        'compliance_score': 80,
        'total_errors': 10,
        'total_warnings': 20,
        'pages_scanned': 3,
        'report_url': f'/v2/preview?scan_id={scan_id}'
    })

    got_complete = False
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith(b'data: '):
            payload = json.loads(line[6:].decode('utf-8'))
            if payload.get('event_type') == 'scan_complete':
                got_complete = True
                data = payload.get('data', {})
                assert data.get('compliance_score') == 80
                assert 'report_url' in data
                break

    assert got_complete, 'Expected scan_complete event'

    # New connection for failure scenario
    scan_id2 = 'TEST_SSE_TERM_2'
    resp2 = requests.get(f"http://127.0.0.1:{port}/api/scan/stream/{scan_id2}", stream=True,
                         headers={"Accept": "text/event-stream"}, timeout=10)
    assert resp2.status_code == 200
    monitor.emit_scan_failed(scan_id2, 'Network error', error_code='NETWORK_ERROR', pages_completed=1)

    got_failed = False
    for line in resp2.iter_lines():
        if not line:
            continue
        if line.startswith(b'data: '):
            payload = json.loads(line[6:].decode('utf-8'))
            if payload.get('event_type') == 'scan_failed':
                got_failed = True
                data = payload.get('data', {})
                assert data.get('error_code') == 'NETWORK_ERROR'
                break

    assert got_failed, 'Expected scan_failed event'
