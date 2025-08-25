#!/usr/bin/env python3
"""
Test per verificare che il polling del sistema EAA Scanner funzioni correttamente
con aggiornamenti di stato in tempo reale durante la scansione.
"""

import time
import json
import requests
from datetime import datetime

def test_scan_status_updates():
    """Test che verifica gli aggiornamenti di stato durante la scansione"""
    
    backend_url = "http://localhost:8000"
    
    print("🚀 INIZIO TEST POLLING CON AGGIORNAMENTI STATO")
    print("=" * 50)
    
    # 1. Avvia scansione
    scan_request = {
        "pages": [
            "https://www.principiadv.com",
            "https://www.principiadv.com/about"
        ],
        "company_name": "Principia Advisory",
        "email": "test@example.com",
        "scanners": ["pa11y", "axe"]
    }
    
    print("📡 Avvio scansione su principiadv.com...")
    response = requests.post(
        f"{backend_url}/api/scan/start",
        json=scan_request,
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"❌ Errore avvio scansione: {response.status_code} - {response.text}")
        return False
    
    scan_data = response.json()
    session_id = scan_data["session_id"]
    print(f"✅ Scansione avviata - Session ID: {session_id}")
    
    # 2. Monitora status con polling
    print("\n📊 MONITORAGGIO STATUS (polling ogni 3 secondi)")
    print("-" * 50)
    
    attempts = 0
    max_attempts = 60  # 3 minuti max
    last_progress = -1
    status_changes = []
    
    while attempts < max_attempts:
        try:
            # Richiedi status con timeout più corto
            status_response = requests.get(
                f"{backend_url}/api/scan/status/{session_id}",
                timeout=3
            )
            
            if status_response.status_code == 200:
                status = status_response.json()
                current_progress = status.get("progress", 0)
                current_status = status.get("status", "unknown")
                current_page = status.get("current_page", "")
                pages_scanned = status.get("pages_scanned", 0)
                total_pages = status.get("total_pages", 0)
                
                # Registra cambiamenti di stato
                if current_progress != last_progress:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    status_change = {
                        "timestamp": timestamp,
                        "progress": current_progress,
                        "status": current_status,
                        "pages": f"{pages_scanned}/{total_pages}",
                        "current_page": current_page[:50] + "..." if len(current_page) > 50 else current_page
                    }
                    status_changes.append(status_change)
                    
                    print(f"[{timestamp}] Progress: {current_progress}% | Status: {current_status} | Pages: {pages_scanned}/{total_pages}")
                    if current_page:
                        print(f"    Current Page: {current_page}")
                    
                    last_progress = current_progress
                
                # Controlla se completato
                if current_status in ["completed", "failed"]:
                    print(f"\n🏁 Scansione {current_status}!")
                    break
                    
            else:
                print(f"⚠️ Status HTTP {status_response.status_code}: {status_response.text[:100]}...")
        
        except Exception as e:
            print(f"❌ Errore polling tentativo {attempts + 1}: {e}")
        
        time.sleep(3)
        attempts += 1
    
    # 3. Analizza risultati
    print("\n📈 ANALISI RISULTATI")
    print("=" * 50)
    
    if len(status_changes) <= 2:
        print(f"❌ PROBLEMA: Solo {len(status_changes)} aggiornamenti di stato rilevati!")
        print("   Il backend NON sta aggiornando lo stato durante la scansione")
        print("\n📋 Aggiornamenti rilevati:")
        for change in status_changes:
            print(f"  [{change['timestamp']}] {change['progress']}% - {change['status']} - {change['pages']}")
        return False
    else:
        print(f"✅ SUCCESSO: {len(status_changes)} aggiornamenti di stato rilevati")
        print("   Il backend STA aggiornando lo stato correttamente!")
        print("\n📋 Timeline aggiornamenti:")
        for change in status_changes:
            print(f"  [{change['timestamp']}] {change['progress']}% - {change['status']} - {change['pages']}")
            if change['current_page']:
                print(f"      Page: {change['current_page']}")
        
        # Verifica anche i risultati finali
        if current_status == "completed":
            print("\n📦 RECUPERO RISULTATI FINALI...")
            results_response = requests.get(f"{backend_url}/api/scan/results/{session_id}")
            if results_response.status_code == 200:
                results = results_response.json()
                print(f"✅ Risultati ottenuti:")
                print(f"   - Issues totali: {results.get('issues_total', 0)}")
                print(f"   - Pagine scansionate: {results.get('pages_scanned', 0)}")
                print(f"   - Compliance score: {results.get('compliance_score', 0)}%")
                print(f"   - Scanner usati: {results.get('scanners_used', [])}")
        
        return True

if __name__ == "__main__":
    try:
        success = test_scan_status_updates()
        if success:
            print("\n🎉 TEST COMPLETATO CON SUCCESSO - Il polling funziona!")
        else:
            print("\n💥 TEST FALLITO - Il polling NON funziona correttamente")
    except Exception as e:
        print(f"\n💥 ERRORE CRITICO DEL TEST: {e}")
        import traceback
        traceback.print_exc()