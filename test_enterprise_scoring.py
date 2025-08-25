#!/usr/bin/env python3
"""
Test del sistema di scoring enterprise
"""

import json
from pathlib import Path
from eaa_scanner.config import Config
from eaa_scanner.enterprise_core import EnterpriseScanOrchestrator

def test_enterprise_scoring():
    """Test sistema scoring enterprise"""
    
    print("\n" + "="*60)
    print("🔬 TEST ENTERPRISE SCORING SYSTEM")
    print("="*60)
    
    # Configurazione test
    cfg = Config(
        url="https://www.principiadv.com",
        company_name="Test Company",
        email="test@example.com",
        wave_api_key=None,
        simulate=True  # Usa dati simulati
    )
    
    print(f"\n📊 Configurazione:")
    print(f"   URL: {cfg.url}")
    print(f"   Simulate: {cfg.simulate}")
    
    # Crea orchestrator
    orchestrator = EnterpriseScanOrchestrator(enable_parallel=False)
    
    print(f"\n🚀 Avvio scansione enterprise...")
    
    try:
        # Esegui scansione
        result = orchestrator.run_enterprise_scan(
            cfg=cfg,
            output_root=Path("output"),
            event_monitor=None,
            enable_pdf=False,
            max_retries=0
        )
        
        print(f"\n✅ Scansione completata!")
        print(f"\n📈 Risultati:")
        print(f"   Scan ID: {result.get('scan_id')}")
        print(f"   Timestamp: {result.get('timestamp')}")
        
        # Analizza compliance
        compliance = result.get('compliance', {})
        print(f"\n🏆 Compliance:")
        print(f"   Overall Score: {compliance.get('overall_score')}%")
        print(f"   Compliance Level: {compliance.get('compliance_level')}")
        print(f"   Total Violations: {compliance.get('total_violations')}")
        print(f"   Critical Issues: {compliance.get('critical_issues')}")
        print(f"   High Issues: {compliance.get('high_issues')}")
        print(f"   Medium Issues: {compliance.get('medium_issues')}")
        print(f"   Low Issues: {compliance.get('low_issues')}")
        print(f"   Confidence: {compliance.get('confidence')}%")
        
        # Analizza execution
        execution = result.get('execution', {})
        print(f"\n⚙️ Execution:")
        print(f"   Successful Scanners: {execution.get('successful_scanners')}")
        print(f"   Failed Scanners: {execution.get('failed_scanners')}")
        print(f"   Success Rate: {execution.get('success_rate')}%")
        
        # Verifica presenza risultati individuali
        print(f"\n🔍 Analisi dettagliata dei risultati:")
        
        # Leggi il summary generato
        paths = result.get('paths', {})
        summary_path = paths.get('enterprise_summary')
        if summary_path and Path(summary_path).exists():
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            # Analizza risultati individuali
            individual_results = summary_data.get('individual_results', [])
            print(f"   Numero risultati scanner: {len(individual_results)}")
            
            for idx, scanner_result in enumerate(individual_results, 1):
                scanner_name = scanner_result.get('scanner')
                score = scanner_result.get('accessibility_score')
                violations = scanner_result.get('violations', [])
                status = scanner_result.get('status')
                
                print(f"\n   Scanner {idx}: {scanner_name}")
                print(f"      Status: {status}")
                print(f"      Score: {score}")
                print(f"      Violations: {len(violations)}")
                
                # Mostra prime 2 violazioni
                for v_idx, violation in enumerate(violations[:2], 1):
                    print(f"      Violation {v_idx}:")
                    print(f"         Code: {violation.get('code')}")
                    print(f"         Severity: {violation.get('severity')}")
                    print(f"         WCAG: {violation.get('wcag_criterion')}")
        
        # Diagnosi problema score 0
        print(f"\n⚠️ DIAGNOSI PROBLEMA SCORE 0:")
        
        if compliance.get('overall_score') == 0:
            print(f"   ❌ Score è 0 - Verificare:")
            print(f"      1. I scanner stanno restituendo dati?")
            print(f"      2. Il normalizer sta processando i dati?")
            print(f"      3. L'algoritmo di scoring è corretto?")
            
            # Verifica se ci sono violazioni
            if compliance.get('total_violations', 0) > 0:
                print(f"   ✅ Ci sono {compliance['total_violations']} violazioni rilevate")
                print(f"   ❌ Ma lo score è 0 - problema nell'algoritmo di calcolo")
            else:
                print(f"   ❌ Nessuna violazione rilevata - problema nel processing")
        else:
            print(f"   ✅ Score calcolato correttamente: {compliance.get('overall_score')}%")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Errore durante test: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_enterprise_scoring()
    
    if result:
        print(f"\n" + "="*60)
        print("✅ TEST COMPLETATO")
        print("="*60)
    else:
        print(f"\n" + "="*60)
        print("❌ TEST FALLITO")
        print("="*60)