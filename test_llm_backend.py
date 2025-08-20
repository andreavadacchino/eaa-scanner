#!/usr/bin/env python3
"""
Test script per verificare le funzionalità LLM del backend Flask.
Esegue test funzionali contro il server locale.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check LLM"""
    print("🏥 Testing LLM health check...")
    try:
        response = requests.get(f"{BASE_URL}/api/llm/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Status: {data['status']}")
            print(f"   📊 Components: {len(data['components'])}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_capabilities():
    """Test capabilities endpoint"""
    print("⚙️ Testing LLM capabilities...")
    try:
        response = requests.get(f"{BASE_URL}/api/llm/capabilities")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Models: {len(data['models'])}")
            print(f"   📝 Sections: {len(data['sections'])}")
            print(f"   🛠️ Features: {len(data['features'])}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_cost_estimation():
    """Test cost estimation"""
    print("💰 Testing cost estimation...")
    try:
        payload = {
            "model": "gpt-4o",
            "num_pages": 2,
            "sections": ["executive_summary", "recommendations"],
            "complexity": "medium"
        }
        response = requests.post(
            f"{BASE_URL}/api/llm/estimate-costs",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Estimated cost: ${data['estimated_cost_usd']}")
            print(f"   ⏱️ Estimated time: {data.get('estimated_minutes', 0)} min")
            print(f"   🧮 Total tokens: {data['estimated_input_tokens'] + data['estimated_output_tokens']}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_api_key_validation():
    """Test API key validation (con chiave fake)"""
    print("🔑 Testing API key validation...")
    try:
        payload = {"api_key": "sk-test-fake-key-for-testing"}
        response = requests.post(
            f"{BASE_URL}/api/llm/validate-key",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Validation response: {data['valid']}")
            print(f"   📝 Message: {data['message']}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_preview_section():
    """Test section preview"""
    print("👁️ Testing section preview...")
    try:
        payload = {
            "section_type": "executive_summary",
            "sample_data": {
                "company_name": "Test Company",
                "url": "https://test.com"
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/llm/preview-section",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            preview = data.get('preview_content', '')
            print(f"   ✅ Preview generated: {len(preview)} chars")
            print(f"   📄 Section: {data['section_type']}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_rate_limiting():
    """Test rate limiting (5 richieste rapide)"""
    print("🚦 Testing rate limiting...")
    try:
        payload = {"api_key": "test-key"}
        success_count = 0
        rate_limited_count = 0
        
        for i in range(7):  # Più del limite di 5
            response = requests.post(
                f"{BASE_URL}/api/llm/validate-key",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1
            time.sleep(0.1)  # Piccola pausa
        
        print(f"   ✅ Successful requests: {success_count}")
        print(f"   🛑 Rate limited: {rate_limited_count}")
        
        if rate_limited_count > 0:
            print("   ✅ Rate limiting is working!")
            return True
        else:
            print("   ⚠️ Rate limiting might not be working")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_usage_stats():
    """Test usage statistics"""
    print("📊 Testing usage statistics...")
    try:
        response = requests.get(f"{BASE_URL}/api/llm/usage-stats")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Cache size: {data['cache']['cache_size']}")
            print(f"   📈 Success rate: {data['performance']['success_rate']}")
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Esegue tutti i test"""
    print("🧪 EAA Scanner LLM Backend Test Suite")
    print("=" * 50)
    
    # Check server availability
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server non raggiungibile su http://localhost:8000")
            print("   Assicurati che il server sia avviato con: python webapp/app.py")
            sys.exit(1)
    except:
        print("❌ Server non raggiungibile su http://localhost:8000")
        print("   Assicurati che il server sia avviato con: python webapp/app.py")
        sys.exit(1)
    
    print("✅ Server raggiungibile, avvio test...\n")
    
    tests = [
        test_health_check,
        test_capabilities,
        test_cost_estimation,
        test_api_key_validation,
        test_preview_section,
        test_usage_stats,
        test_rate_limiting  # Ultimo perché modifica stato
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"   💥 Test crashed: {e}\n")
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 Tutti i test sono passati! Il backend LLM è funzionante.")
    elif passed >= total * 0.8:
        print("⚠️ La maggior parte dei test è passata, sistema funzionale con avvertimenti.")
    else:
        print("❌ Molti test falliti, controllare configurazione e dipendenze.")
    
    print("\n💡 Per test più approfonditi:")
    print("   1. Configura una vera API key OpenAI")
    print("   2. Esegui una scansione completa")
    print("   3. Testa la rigenerazione report con LLM")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)