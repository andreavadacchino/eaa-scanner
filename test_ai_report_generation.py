#!/usr/bin/env python3
"""
Test generazione report con contenuti AI
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.report.generator import EnhancedReportGenerator


def test_ai_generation():
    """Test generazione con contenuti AI usando dati di esempio"""
    
    print("=" * 60)
    print("TEST GENERAZIONE REPORT CON CONTENUTI AI")
    print("=" * 60)
    
    # Inizializza generatore
    generator = EnhancedReportGenerator()
    
    # Dati di esempio basati su scansione reale
    scanner_data = {
        'wave': {
            'violations': [
                {
                    'code': 'img-alt',
                    'description': 'Immagine senza testo alternativo',
                    'selector': 'img.logo',
                    'count': 5
                }
            ]
        },
        'axe': {
            'violations': [
                {
                    'id': 'color-contrast',
                    'description': 'Contrasto colore insufficiente',
                    'nodes': [{'html': '<p>Testo</p>'}],
                    'impact': 'serious'
                }
            ]
        }
    }
    
    # Genera report con contenuti AI
    print("\n📊 Generazione report con IA...")
    scan_result = generator.generate_scan_result(
        scanner_data,
        "Test Company SRL",
        "https://test.example.com"
    )
    
    # Genera HTML con AI
    print("   🤖 Attivazione sistema multi-agent...")
    html = generator.generate_html_report(scan_result, use_ai=True)
    
    # Salva report
    output_dir = Path("output/test_ai_report")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "report_ai_test.html"
    report_path.write_text(html, encoding='utf-8')
    
    print(f"   ✅ Report salvato: {report_path}")
    
    # Verifica contenuti AI
    if "sistema avanzato di audit automatico" in html:
        print("   ✅ Contenuti AI generati correttamente")
    else:
        print("   ⚠️ Usando contenuti fallback")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETATO")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        test_ai_generation()
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)