#!/usr/bin/env python3
"""
Test del sistema di Live Monitoring Dashboard
Verifica che tutti i componenti siano integrati correttamente
"""

import sys
from pathlib import Path

# Aggiungi il path del progetto
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test che tutti i moduli si importino correttamente"""
    print("🧪 Test importazioni...")
    
    try:
        from webapp.scan_monitor import ScanProgressEmitter, get_scan_monitor
        print("✅ webapp.scan_monitor - OK")
    except ImportError as e:
        print(f"❌ webapp.scan_monitor - FAIL: {e}")
        return False
    
    try:
        from eaa_scanner.scan_events import ScanEventHooks, MonitoredScanner
        print("✅ eaa_scanner.scan_events - OK")
    except ImportError as e:
        print(f"❌ eaa_scanner.scan_events - FAIL: {e}")
        return False
    
    return True

def test_monitor_functionality():
    """Test funzionalità base del monitor"""
    print("\n🧪 Test funzionalità monitor...")
    
    try:
        from webapp.scan_monitor import ScanProgressEmitter
        
        monitor = ScanProgressEmitter()
        scan_id = "test-scan-123"
        
        # Test emissione eventi
        monitor.emit_scan_start(scan_id, "https://example.com", "Test Company", {
            "wave": True, "pa11y": True, "axe": False, "lighthouse": False
        })
        
        monitor.emit_scanner_start(scan_id, "WAVE", "https://example.com", 30)
        
        monitor.emit_scanner_operation(scan_id, "WAVE", "Analizzando form", 50)
        
        monitor.emit_scanner_complete(scan_id, "WAVE", {
            "errors": 3, "warnings": 5, "features": 2
        })
        
        # Verifica che gli eventi siano stati memorizzati
        if scan_id in monitor.event_history:
            event_count = len(monitor.event_history[scan_id])
            print(f"✅ Monitor eventi memorizzati: {event_count}")
            
            # Mostra gli eventi
            for i, event in enumerate(monitor.event_history[scan_id]):
                print(f"   {i+1}. {event['event_type']}: {event['data'].get('message', 'N/A')}")
            
            return True
        else:
            print("❌ Eventi non memorizzati")
            return False
            
    except Exception as e:
        print(f"❌ Test monitor fallito: {e}")
        return False

def test_event_hooks():
    """Test del sistema di hook eventi"""
    print("\n🧪 Test event hooks...")
    
    try:
        from eaa_scanner.scan_events import ScanEventHooks, set_current_hooks
        from webapp.scan_monitor import get_scan_monitor
        
        scan_id = "test-hooks-456"
        monitor = get_scan_monitor()
        
        # Crea hooks e collega al monitor
        hooks = ScanEventHooks(scan_id)
        hooks.set_monitor(monitor)
        set_current_hooks(hooks)
        
        # Test emissione tramite hooks
        hooks.emit_scanner_start("Pa11y", "https://example.com/test")
        hooks.emit_processing_step("Generazione report", 90)
        
        # Verifica eventi
        if scan_id in monitor.event_history:
            event_count = len(monitor.event_history[scan_id])
            print(f"✅ Hook eventi memorizzati: {event_count}")
            return True
        else:
            print("❌ Hook eventi non funzionanti")
            return False
            
    except Exception as e:
        print(f"❌ Test hooks fallito: {e}")
        return False

def test_monitored_scanner():
    """Test del wrapper MonitoredScanner"""
    print("\n🧪 Test MonitoredScanner...")
    
    try:
        from eaa_scanner.scan_events import MonitoredScanner, ScanEventHooks, set_current_hooks
        from webapp.scan_monitor import get_scan_monitor
        
        # Mock scanner semplice
        class MockScanner:
            def scan(self, url):
                # Simula risultato scanner
                class MockResult:
                    def __init__(self):
                        self.json = {
                            "categories": {
                                "error": {"count": 2},
                                "alert": {"count": 3},
                                "feature": {"count": 1}
                            }
                        }
                return MockResult()
        
        scan_id = "test-wrapped-789"
        monitor = get_scan_monitor()
        
        # Setup hooks
        hooks = ScanEventHooks(scan_id)
        hooks.set_monitor(monitor)
        set_current_hooks(hooks)
        
        # Test scanner wrappato
        mock_scanner = MockScanner()
        monitored = MonitoredScanner(mock_scanner, "WAVE")
        
        result = monitored.scan("https://example.com/wrapped")
        
        # Verifica che abbia emesso eventi
        if scan_id in monitor.event_history and len(monitor.event_history[scan_id]) > 0:
            print("✅ MonitoredScanner eventi emessi")
            print(f"   Risultato: errors={result.json['categories']['error']['count']}")
            return True
        else:
            print("❌ MonitoredScanner eventi mancanti")
            return False
            
    except Exception as e:
        print(f"❌ Test MonitoredScanner fallito: {e}")
        return False

def test_css_and_js_files():
    """Test che i file CSS e JS esistano"""
    print("\n🧪 Test file frontend...")
    
    css_file = Path("webapp/static/css/app_v2.css")
    js_file = Path("webapp/static/js/scan_monitor.js")
    
    if css_file.exists():
        print("✅ File CSS trovato")
    else:
        print("❌ File CSS mancante")
        return False
    
    if js_file.exists():
        print("✅ File JS trovato")
        
        # Verifica che contenga la classe ScanMonitor
        content = js_file.read_text()
        if "class ScanMonitor" in content:
            print("✅ Classe ScanMonitor presente")
        else:
            print("❌ Classe ScanMonitor mancante")
            return False
    else:
        print("❌ File JS mancante")
        return False
        
    return True

def main():
    """Esegue tutti i test"""
    print("🚀 Test Live Monitoring Dashboard\n")
    
    all_passed = True
    
    # Test importazioni
    if not test_imports():
        all_passed = False
    
    # Test funzionalità
    if not test_monitor_functionality():
        all_passed = False
    
    if not test_event_hooks():
        all_passed = False
        
    if not test_monitored_scanner():
        all_passed = False
    
    if not test_css_and_js_files():
        all_passed = False
    
    # Risultato finale
    print("\n" + "="*50)
    if all_passed:
        print("🎉 Tutti i test sono passati!")
        print("✅ Sistema Live Monitoring Dashboard pronto!")
        print("\nPer testare:")
        print("1. Avvia webapp: python3 webapp/app.py")
        print("2. Vai su http://localhost:8000/v2")
        print("3. Avvia una scansione e osserva il monitoraggio live")
    else:
        print("❌ Alcuni test sono falliti!")
        print("🔧 Ricontrolla l'integrazione dei componenti")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)