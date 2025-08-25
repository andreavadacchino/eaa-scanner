#!/usr/bin/env python3
"""
Test formato dati WAVE
"""

import json
from eaa_scanner.scanners.wave import WaveScanner

def test_wave_format():
    """Test formato dati WAVE"""
    
    print("\n" + "="*60)
    print("🔍 TEST WAVE DATA FORMAT")
    print("="*60)
    
    scanner = WaveScanner(api_key=None, timeout_ms=30000, simulate=True)
    result = scanner.scan("https://test.com")
    
    if result.ok and result.json:
        print(f"\n✅ Scan completato")
        print(f"\n📊 Struttura dati WAVE:")
        print(json.dumps(result.json, indent=2))
        
        print(f"\n🔑 Chiavi principali:")
        for key in result.json.keys():
            print(f"   - {key}")
        
        # Analizza categories
        categories = result.json.get('categories', {})
        if categories:
            print(f"\n📁 Categorie trovate:")
            for cat_name, cat_data in categories.items():
                print(f"   - {cat_name}")
                if 'items' in cat_data:
                    items = cat_data['items']
                    print(f"      Items: {len(items)}")
                    for item_key, item_data in items.items():
                        print(f"         - {item_key}: count={item_data.get('count')}, impact={item_data.get('impact')}")
        
        # Verifica se ci sono 'errors' o 'warnings'
        if 'errors' in result.json:
            print(f"\n⚠️ Campo 'errors' trovato: {len(result.json['errors'])} errori")
        else:
            print(f"\n❌ Campo 'errors' NON trovato")
            
        if 'warnings' in result.json:
            print(f"\n⚠️ Campo 'warnings' trovato: {len(result.json['warnings'])} warning")
        else:
            print(f"\n❌ Campo 'warnings' NON trovato")

if __name__ == "__main__":
    test_wave_format()