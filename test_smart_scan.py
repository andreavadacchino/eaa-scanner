#!/usr/bin/env python3
"""
Script di test per Smart Page Sampler e Smart Scan
Testa il nuovo sistema di selezione intelligente delle pagine
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Aggiungi directory al path
sys.path.insert(0, str(Path(__file__).parent))

from eaa_scanner.config import Config
from eaa_scanner.core import run_smart_scan
from eaa_scanner.page_sampler import SamplerConfig, SelectionStrategy, AnalysisDepth


def test_smart_scan():
    """Test scansione con Smart Page Sampler"""
    
    print("=" * 80)
    print("TEST SMART PAGE SAMPLER - EAA Scanner")
    print("=" * 80)
    print()
    
    # Configurazione base scanner
    config = Config(
        url="https://www.example.com",
        company_name="Test Company",
        email="test@example.com",
        simulate=True  # Usa dati simulati per test
    )
    
    # Configurazione Smart Page Sampler
    sampler_config = {
        # Discovery
        'max_pages': 30,
        'max_depth': 2,
        'follow_external': False,
        'use_playwright': False,  # Per test veloce usa requests
        
        # Template Detection
        'similarity_threshold': 0.85,
        
        # Selection
        'selection_strategy': SelectionStrategy.WCAG_EM,
        'max_selected_pages': 10,
        'min_selected_pages': 5,
        'include_all_critical': True,
        
        # Depth Analysis
        'default_depth': AnalysisDepth.STANDARD,
        'time_budget_minutes': 60,
        'optimize_for_budget': True,
        
        # Real-time feedback
        'enable_websocket': False,  # Disabilita per test
        
        # Output
        'save_screenshots': False
    }
    
    try:
        print("🚀 Avvio Smart Scan con le seguenti configurazioni:")
        print(f"   - URL: {config.url}")
        print(f"   - Max pagine discovery: {sampler_config['max_pages']}")
        print(f"   - Max pagine selezionate: {sampler_config['max_selected_pages']}")
        print(f"   - Strategia: {sampler_config['selection_strategy'].value}")
        print(f"   - Budget tempo: {sampler_config['time_budget_minutes']} minuti")
        print()
        
        # Esegui Smart Scan
        result = run_smart_scan(
            cfg=config,
            sampler_config=sampler_config,
            report_type="standard"
        )
        
        print("\n" + "=" * 80)
        print("✅ SMART SCAN COMPLETATO CON SUCCESSO!")
        print("=" * 80)
        print()
        print("📊 Risultati:")
        print(f"   - Scan ID: {result['scan_id']}")
        print(f"   - Pagine scansionate: {result['pages_scanned']}")
        print(f"   - Report HTML: {result['report_html_path']}")
        print(f"   - Directory output: {result['base_out']}")
        print()
        
        # Carica e mostra dettagli sampler
        sampler_path = Path(result['sampler_path'])
        if sampler_path.exists():
            with open(sampler_path, 'r', encoding='utf-8') as f:
                sampler_data = json.load(f)
            
            print("🔍 Dettagli Smart Sampling:")
            print(f"   - Pagine scoperte: {sampler_data['discovery']['total_discovered']}")
            print(f"   - Template identificati: {len(sampler_data['templates']['identified'])}")
            print(f"   - Pagine selezionate: {sampler_data['selection']['total_selected']}")
            print(f"   - Tempo stimato: {sampler_data['depth_analysis']['estimated_total_time']['total_hours']:.1f} ore")
            print()
            
            # Mostra template trovati
            if sampler_data['templates']['summary']['templates']:
                print("📋 Template identificati:")
                for template in sampler_data['templates']['summary']['templates']:
                    print(f"   - {template['name']}: {template['page_count']} pagine")
                print()
            
            # Mostra ragioni selezione
            if sampler_data['selection']['reasons']:
                print("📝 Ragioni selezione pagine:")
                for url, reason in list(sampler_data['selection']['reasons'].items())[:5]:
                    print(f"   - {url}: {reason}")
                if len(sampler_data['selection']['reasons']) > 5:
                    print(f"   ... e altre {len(sampler_data['selection']['reasons']) - 5} pagine")
                print()
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERRORE DURANTE IL TEST")
        print("=" * 80)
        print(f"Errore: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_sampler_only():
    """Test solo il Smart Page Sampler senza scansione"""
    
    print("=" * 80)
    print("TEST SOLO SMART PAGE SAMPLER")
    print("=" * 80)
    print()
    
    from eaa_scanner.page_sampler import SmartPageSamplerCoordinator, SamplerConfig
    
    # Configura sampler
    config = SamplerConfig(
        max_pages=20,
        max_depth=2,
        selection_strategy=SelectionStrategy.WCAG_EM,
        max_selected_pages=8,
        enable_websocket=False,
        use_playwright=False,
        output_dir="output/test_sampler"
    )
    
    # Esegui sampling
    sampler = SmartPageSamplerCoordinator(config)
    
    try:
        print("🔍 Test discovery e selezione per: https://www.example.com")
        result = sampler.execute("https://www.example.com")
        
        print(f"\n✅ Sampling completato:")
        print(f"   - Pagine scoperte: {result.total_discovered}")
        print(f"   - Template identificati: {len(result.templates)}")
        print(f"   - Pagine selezionate: {len(result.selected_pages)}")
        print(f"   - Tempo stimato: {result.estimated_scan_time.get('total_hours', 0):.1f} ore")
        
        if result.errors:
            print(f"\n⚠️ Errori: {', '.join(result.errors)}")
        if result.warnings:
            print(f"⚠️ Warning: {', '.join(result.warnings)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print(f"📅 Data test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Controlla argomenti
    if len(sys.argv) > 1 and sys.argv[1] == "--sampler-only":
        # Test solo sampler
        success = test_sampler_only()
    else:
        # Test completo con scansione
        success = test_smart_scan()
    
    if success:
        print("\n🎉 Tutti i test passati con successo!")
        sys.exit(0)
    else:
        print("\n❌ Test falliti. Verifica gli errori sopra.")
        sys.exit(1)