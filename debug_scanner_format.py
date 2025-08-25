#!/usr/bin/env python3
"""
Debug del formato dati scanner
"""

import json
from pathlib import Path
from eaa_scanner.scanners.pa11y import Pa11yScanner
from eaa_scanner.scanners.axe import AxeScanner
from eaa_scanner.scanners.lighthouse import LighthouseScanner
from eaa_scanner.scanners.wave import WaveScanner
from eaa_scanner.scan_events import MonitoredScanner

def debug_scanner_format():
    """Debug formato dati scanner"""
    
    url = "https://www.principiadv.com"
    
    # Test Pa11y
    print("\n" + "="*60)
    print("🔍 DEBUG PA11Y FORMAT")
    print("="*60)
    
    try:
        scanner = MonitoredScanner(
            Pa11yScanner(timeout_ms=30000, simulate=True),
            "Pa11y"
        )
        result = scanner.scan(url)
        
        print(f"Result type: {type(result)}")
        print(f"Result attributes: {dir(result)}")
        
        if hasattr(result, 'json'):
            print(f"result.json type: {type(result.json)}")
            if result.json:
                print(f"Keys: {list(result.json.keys())[:5]}")
                # Verifica struttura
                if 'issues' in result.json:
                    print(f"✅ Has 'issues' key")
                    issues = result.json.get('issues', [])
                    if issues and len(issues) > 0:
                        print(f"Sample issue: {json.dumps(issues[0], indent=2)[:500]}")
                else:
                    print(f"❌ No 'issues' key. Keys: {list(result.json.keys())}")
                    print(f"Full data: {json.dumps(result.json, indent=2)[:1000]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test Axe
    print("\n" + "="*60)
    print("🔍 DEBUG AXE FORMAT")
    print("="*60)
    
    try:
        scanner = MonitoredScanner(
            AxeScanner(timeout_ms=30000, simulate=True),
            "Axe"
        )
        result = scanner.scan(url)
        
        print(f"Result type: {type(result)}")
        
        if hasattr(result, 'json'):
            print(f"result.json type: {type(result.json)}")
            if result.json:
                print(f"Keys: {list(result.json.keys())[:5]}")
                # Verifica struttura
                if 'violations' in result.json:
                    print(f"✅ Has 'violations' key")
                    violations = result.json.get('violations', [])
                    if violations and len(violations) > 0:
                        print(f"Sample violation: {json.dumps(violations[0], indent=2)[:500]}")
                else:
                    print(f"❌ No 'violations' key. Keys: {list(result.json.keys())}")
                    print(f"Full data: {json.dumps(result.json, indent=2)[:1000]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test Lighthouse
    print("\n" + "="*60)
    print("🔍 DEBUG LIGHTHOUSE FORMAT")
    print("="*60)
    
    try:
        scanner = MonitoredScanner(
            LighthouseScanner(timeout_ms=30000, simulate=True),
            "Lighthouse"
        )
        result = scanner.scan(url)
        
        print(f"Result type: {type(result)}")
        
        if hasattr(result, 'json'):
            print(f"result.json type: {type(result.json)}")
            if result.json:
                print(f"Keys: {list(result.json.keys())[:5]}")
                # Verifica struttura
                if 'categories' in result.json:
                    print(f"✅ Has 'categories' key")
                    categories = result.json.get('categories', {})
                    if 'accessibility' in categories:
                        print(f"✅ Has 'accessibility' category")
                        acc = categories['accessibility']
                        print(f"Accessibility score: {acc.get('score')}")
                else:
                    print(f"❌ No 'categories' key. Keys: {list(result.json.keys())}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_scanner_format()