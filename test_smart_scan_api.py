#!/usr/bin/env python3
"""
Test Smart Scan via API
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_smart_scan():
    """Test scansione smart via API"""
    
    print("🚀 Test Smart Scan via API")
    print("=" * 60)
    
    # Parametri scansione
    scan_params = {
        "url": "https://www.w3.org",
        "company_name": "W3C Test",
        "email": "test@w3.org",
        "mode": "simulate",
        "smart_scan": True,
        "wave": True,
        "pa11y": True,
        "axe_core": True,
        "lighthouse": True,
        "sampler_config": {
            "max_pages": 20,
            "max_selected_pages": 5,
            "selection_strategy": "wcag_em"
        }
    }
    
    print(f"📍 URL Target: {scan_params['url']}")
    print(f"🏢 Company: {scan_params['company_name']}")
    print(f"📧 Email: {scan_params['email']}")
    print(f"🔍 Smart Scan: Enabled")
    print(f"   - Max Discovery: {scan_params['sampler_config']['max_pages']} pagine")
    print(f"   - Max Selected: {scan_params['sampler_config']['max_selected_pages']} pagine")
    print(f"   - Strategy: {scan_params['sampler_config']['selection_strategy']}")
    print()
    
    # Avvia scansione
    print("⏳ Avvio scansione...")
    response = requests.post(f"{BASE_URL}/start", json=scan_params)
    
    if response.status_code != 200:
        print(f"❌ Errore avvio scansione: {response.text}")
        return False
    
    result = response.json()
    scan_id = result.get("scan_id")
    print(f"✅ Scansione avviata - ID: {scan_id}")
    print()
    
    # Monitora progresso
    print("📊 Monitoraggio progresso:")
    print("-" * 40)
    
    last_percent = -1
    last_stage = ""
    
    for i in range(60):  # Max 60 secondi
        time.sleep(1)
        
        # Controlla stato
        status_response = requests.get(f"{BASE_URL}/status", params={"scan_id": scan_id})
        if status_response.status_code != 200:
            continue
        
        status = status_response.json()
        
        # Mostra aggiornamenti
        current_percent = status.get("percent", 0)
        current_stage = status.get("stage", "")
        
        if current_percent != last_percent or current_stage != last_stage:
            progress_bar = "█" * (current_percent // 5) + "░" * (20 - current_percent // 5)
            print(f"[{progress_bar}] {current_percent}% - {current_stage}")
            last_percent = current_percent
            last_stage = current_stage
        
        # Verifica completamento
        if status.get("status") == "done":
            print()
            print("✅ Scansione completata!")
            print()
            
            # Mostra risultati
            print("📈 Risultati:")
            print("-" * 40)
            
            # Report disponibili
            report = status.get("report", {})
            if report.get("html"):
                print("   ✅ Report HTML generato")
            if report.get("analytics"):
                print("   ✅ Analytics disponibili")
            if report.get("charts"):
                print("   ✅ Grafici generati")
            if report.get("remediation"):
                print("   ✅ Piano remediation creato")
            
            # Log finale
            print()
            print("📝 Log scansione:")
            for log_entry in status.get("log", []):
                print(f"   {log_entry}")
            
            # Link ai risultati
            print()
            print("🔗 Link utili:")
            print(f"   - Preview report: {BASE_URL}/preview?scan_id={scan_id}")
            print(f"   - Download HTML: {BASE_URL}/download/html?scan_id={scan_id}")
            print(f"   - Analytics: {BASE_URL}/api/analytics?scan_id={scan_id}")
            print(f"   - Dashboard: {BASE_URL}/smart-dashboard")
            
            return True
        
        # Errore
        if status.get("status") == "error":
            print()
            print(f"❌ Errore: {status.get('message', 'Errore sconosciuto')}")
            return False
    
    print()
    print("⚠️ Timeout - scansione non completata in 60 secondi")
    return False

if __name__ == "__main__":
    success = test_smart_scan()
    sys.exit(0 if success else 1)