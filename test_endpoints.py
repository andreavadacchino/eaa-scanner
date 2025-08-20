#!/usr/bin/env python3
"""
Test script per verificare che gli endpoint necessari per il fix LLM siano funzionanti.
"""

import json
import requests
import sys
from pathlib import Path

# Aggiungi il path del progetto
sys.path.append(str(Path(__file__).parent))

def test_endpoint(url, method='GET', data=None, description=""):
    """Testa un endpoint e stampa il risultato"""
    print(f"\n🧪 Test: {description}")
    print(f"📍 {method} {url}")
    
    try:
        if method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        else:
            response = requests.get(url, timeout=5)
            
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
            try:
                json_data = response.json()
                print(f"📝 Response keys: {list(json_data.keys()) if isinstance(json_data, dict) else type(json_data)}")
            except:
                print("📝 Response: Non-JSON")
        elif response.status_code == 404:
            print("⚠️  NOT FOUND (normale per test)")
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"📝 Response: {response.text[:200]}...")
            
    except requests.exceptions.ConnectionError:
        print("🔌 CONNESSIONE RIFIUTATA - Server non in esecuzione?")
    except requests.exceptions.Timeout:
        print("⏰ TIMEOUT - Server lento o bloccato?")
    except Exception as e:
        print(f"❌ ERRORE: {e}")

def main():
    print("🚀 Test Endpoints per Fix LLM Report Generation")
    print("="*60)
    
    BASE_URL = "http://localhost:8000"
    
    # Test 1: Health check
    test_endpoint(
        f"{BASE_URL}/health", 
        description="Health check server"
    )
    
    # Test 2: Endpoint principale v2
    test_endpoint(
        f"{BASE_URL}/v2", 
        description="Pagina principale v2 workflow"
    )
    
    # Test 3: API Key validation (con chiave fake)
    test_endpoint(
        f"{BASE_URL}/api/llm/validate-key",
        method='POST',
        data={'api_key': 'sk-test-fake-key-for-testing'},
        description="Validazione API key (chiave fake)"
    )
    
    # Test 4: Scan results (scan ID inesistente)
    test_endpoint(
        f"{BASE_URL}/api/scan/results/test_scan_123",
        description="Recupero risultati scansione (ID fake)"
    )
    
    # Test 5: Reports regenerate (senza dati)
    test_endpoint(
        f"{BASE_URL}/api/reports/regenerate",
        method='POST', 
        data={},
        description="Endpoint rigenerazione report"
    )
    
    print("\n" + "="*60)
    print("📋 RIEPILOGO TEST ENDPOINTS")
    print("✅ Se tutti gli endpoint rispondono (anche con errori 400/404), il fix funzionerà")
    print("🔌 Se c'è 'CONNESSIONE RIFIUTATA', avvia il server con: make web")
    print("❌ Se ci sono errori 500, controlla i log del server")
    
    print("\n🎯 PROSSIMI PASSI:")
    print("1. Avvia server: make web")
    print("2. Apri: http://localhost:8000/test_llm_fix.html")
    print("3. Testa il workflow completo v2")
    print("4. Verifica che non ci siano più errori 'Failed to generate report'")

if __name__ == "__main__":
    main()