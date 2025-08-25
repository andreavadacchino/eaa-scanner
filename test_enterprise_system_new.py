#!/usr/bin/env python3
"""
Test completo del sistema enterprise EAA Scanner
Verifica integrazione, real-time updates e report generation
"""

import time
import json
import requests
from datetime import datetime

def test_enterprise_scan():
    """Test completo del sistema enterprise con principiadv.com"""
    
    backend_url = "http://localhost:8000"
    
    print("🚀 TEST SISTEMA ENTERPRISE EAA SCANNER")
    print("=" * 60)
    
    # 1. Test single page scan con sistema enterprise
    print("\n📡 TEST 1: Single Page Scan Enterprise")
    scan_request = {
        "pages": ["https://www.principiadv.com"],
        "company_name": "Principia Advisory Enterprise",
        "email": "enterprise@test.com",
        "scanners": {
            "pa11y": True,
            "axe": True,
            "lighthouse": True,
            "wave": False  # Disabilitato se non c'è API key
        }
    }
    
    print(f"Avvio scansione enterprise...")
    response = requests.post(
        f"{backend_url}/api/scan/start",
        json=scan_request,
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"❌ Errore avvio scansione: {response.status_code}")
        print(response.text)
        return False
    
    scan_data = response.json()
    session_id = scan_data["session_id"]
    print(f"✅ Scansione avviata - Session ID: {session_id}")
    
    # 2. Monitor progress con polling
    print("\n📊 TEST 2: Real-time Progress Updates")
    print("-" * 40)
    
    max_attempts = 60
    attempts = 0
    last_progress = -1
    updates_received = 0
    
    while attempts < max_attempts:
        try:
            # Controlla status
            status_resp = requests.get(
                f"{backend_url}/api/scan/status/{session_id}",
                timeout=5
            )
            
            if status_resp.status_code == 200:
                status = status_resp.json()
                progress = status.get("progress", 0)
                
                if progress != last_progress:
                    updates_received += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {progress}% - Status: {status.get('status')}")
                    last_progress = progress
                
                if status.get("status") in ["completed", "failed"]:
                    print(f"\n🏁 Scansione {status.get('status')}")
                    break
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout attempt {attempts + 1}")
        except Exception as e:
            print(f"❌ Errore: {e}")
        
        time.sleep(3)
        attempts += 1
    
    # 3. Verifica risultati enterprise
    print("\n📈 TEST 3: Enterprise Results Validation")
    print("-" * 40)
    
    results_resp = requests.get(f"{backend_url}/api/scan/results/{session_id}")
    
    if results_resp.status_code == 200:
        results = results_resp.json()
        
        print(f"✅ Risultati enterprise ottenuti:")
        print(f"   - Compliance Score: {results.get('summary', {}).get('compliance_score', 0)}%")
        print(f"   - Total Issues: {results.get('summary', {}).get('total_issues', 0)}")
        print(f"   - Critical: {results.get('summary', {}).get('critical_issues', 0)}")
        print(f"   - High: {results.get('summary', {}).get('high_issues', 0)}")
        print(f"   - Medium: {results.get('summary', {}).get('medium_issues', 0)}")
        print(f"   - Low: {results.get('summary', {}).get('low_issues', 0)}")
        print(f"   - EAA Compliant: {results.get('summary', {}).get('eaa_compliant', False)}")
        
        # Verifica algoritmo enterprise
        score = results.get('summary', {}).get('compliance_score', 0)
        if 0 < score < 100:
            print(f"✅ Algoritmo enterprise funzionante (score bilanciato: {score})")
        else:
            print(f"⚠️ Score sospetto: {score} - verificare algoritmo")
    else:
        print(f"❌ Errore recupero risultati: {results_resp.status_code}")
        return False
    
    # 4. Test report generation
    print("\n📄 TEST 4: Report Generation")
    print("-" * 40)
    
    # HTML Report
    html_url = f"{backend_url}/api/download_report/{session_id}?format=html"
    html_resp = requests.get(html_url)
    
    if html_resp.status_code == 200:
        print(f"✅ Report HTML generato ({len(html_resp.content)} bytes)")
        # Salva report per ispezione
        with open(f"test_report_{session_id}.html", "wb") as f:
            f.write(html_resp.content)
        print(f"   Salvato come: test_report_{session_id}.html")
    else:
        print(f"❌ Errore generazione HTML: {html_resp.status_code}")
    
    # 5. Riepilogo test
    print("\n🎯 RIEPILOGO TEST ENTERPRISE")
    print("=" * 60)
    
    test_passed = True
    
    # Check real-time updates
    if updates_received > 2:
        print(f"✅ Real-time updates: {updates_received} aggiornamenti ricevuti")
    else:
        print(f"❌ Real-time updates: Solo {updates_received} aggiornamenti")
        test_passed = False
    
    # Check enterprise algorithm
    if 0 < score < 100:
        print(f"✅ Enterprise algorithm: Score bilanciato {score}%")
    else:
        print(f"❌ Enterprise algorithm: Score anomalo {score}%")
        test_passed = False
    
    # Check report generation
    if html_resp.status_code == 200:
        print(f"✅ Report generation: HTML generato correttamente")
    else:
        print(f"❌ Report generation: Errore generazione")
        test_passed = False
    
    return test_passed

if __name__ == "__main__":
    try:
        success = test_enterprise_scan()
        
        if success:
            print("\n🎉 SISTEMA ENTERPRISE COMPLETAMENTE FUNZIONANTE!")
        else:
            print("\n⚠️ SISTEMA ENTERPRISE CON PROBLEMI - VERIFICARE LOG")
            
    except Exception as e:
        print(f"\n💥 ERRORE CRITICO: {e}")
        import traceback
        traceback.print_exc()