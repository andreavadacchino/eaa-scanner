#!/usr/bin/env python3
"""
Script di test per verificare il supporto WeasyPrint e gli engine PDF
"""

import sys
from pathlib import Path
from eaa_scanner.pdf import get_pdf_engines_status, create_pdf_with_options, html_to_pdf
from eaa_scanner.report import generate_html_report_inline

def test_pdf_engines():
    """Testa tutti gli engine PDF disponibili"""
    print("🔍 Verifica status engine PDF...")
    print("-" * 50)
    
    status = get_pdf_engines_status()
    
    for engine_name, info in status.items():
        if info['available']:
            print(f"✅ {engine_name.upper()}")
            if 'version' in info and info['version']:
                print(f"   Versione: {info['version']}")
            if 'path' in info and info['path']:
                print(f"   Path: {info['path']}")
            print(f"   Descrizione: {info['description']}")
        else:
            print(f"❌ {engine_name.upper()}")
            print(f"   Status: {info['description']}")
            if 'install_cmd' in info:
                print(f"   Installazione: {info['install_cmd']}")
        print()
    
    # Conta engine disponibili
    available_engines = sum(1 for info in status.values() if info['available'])
    print(f"📊 Engine disponibili: {available_engines}/{len(status)}")
    
    return status

def test_pdf_generation():
    """Testa la generazione PDF con un report di esempio"""
    print("\n🧪 Test generazione PDF...")
    print("-" * 50)
    
    # Dati di esempio per il report
    test_data = {
        "url": "https://example.com",
        "company_name": "Test Company",
        "compliance": {
            "overall_score": 75,
            "compliance_level": "parzialmente_conforme",
            "total_unique_errors": 5,
            "total_unique_warnings": 12,
            "wcag_version": "2.1",
            "wcag_level": "AA"
        },
        "detailed_results": {
            "errors": [
                {
                    "description": "Immagine senza testo alternativo",
                    "severity": "high",
                    "wcag_criteria": "WCAG 2.1 - 1.1.1 Non-text Content",
                    "source": "axe-core",
                    "count": 3,
                    "remediation": "Aggiungere attributo alt alle immagini"
                }
            ],
            "warnings": [
                {
                    "description": "Contrasto colori potenzialmente insufficiente", 
                    "severity": "medium",
                    "wcag_criteria": "WCAG 2.1 - 1.4.3 Contrast (Minimum)",
                    "source": "wave",
                    "count": 2,
                    "remediation": "Verificare e migliorare il contrasto"
                }
            ]
        },
        "executive_summary": "Il sito presenta alcune problematiche di accessibilità che richiedono attenzione.",
        "recommendations": [
            {
                "title": "Migliorare testi alternativi",
                "description": "Aggiungere descrizioni appropriate alle immagini",
                "priority": "alta",
                "estimated_effort": "basso",
                "wcag_criteria": "1.1.1",
                "actions": ["Aggiungere alt a tutte le immagini", "Rivedere immagini decorative"]
            }
        ],
        "llm_enhanced": True
    }
    
    # Genera HTML
    print("📄 Generazione HTML di test...")
    html_content = generate_html_report_inline(test_data)
    
    # Salva HTML temporaneo
    temp_dir = Path("temp_pdf_test")
    temp_dir.mkdir(exist_ok=True)
    
    html_path = temp_dir / "test_report.html"
    html_path.write_text(html_content, encoding='utf-8')
    print(f"   HTML salvato: {html_path}")
    
    # Testa ogni engine disponibile
    status = get_pdf_engines_status()
    
    for engine_name, info in status.items():
        if not info['available']:
            print(f"⏭️  Saltando {engine_name.upper()} (non disponibile)")
            continue
            
        print(f"\n🔄 Test {engine_name.upper()}...")
        pdf_path = temp_dir / f"test_report_{engine_name}.pdf"
        
        try:
            success = create_pdf_with_options(
                html_path=html_path,
                pdf_path=pdf_path,
                engine=engine_name,
                page_format="A4",
                margins={'top': 1, 'right': 0.75, 'bottom': 1, 'left': 0.75},
                timeout=60
            )
            
            if success and pdf_path.exists():
                size_kb = pdf_path.stat().st_size / 1024
                print(f"✅ {engine_name.upper()}: PDF generato ({size_kb:.1f} KB)")
                print(f"   Output: {pdf_path}")
            else:
                print(f"❌ {engine_name.upper()}: Generazione fallita")
                
        except Exception as e:
            print(f"💥 {engine_name.upper()}: Errore - {e}")
    
    print(f"\n📁 File di test salvati in: {temp_dir}")
    return temp_dir

def main():
    print("🧪 EAA Scanner - Test Supporto PDF")
    print("=" * 50)
    
    # Test 1: Verifica engine disponibili
    status = test_pdf_engines()
    
    # Test 2: Generazione PDF se almeno un engine è disponibile
    available_engines = [name for name, info in status.items() if info['available']]
    
    if available_engines:
        print(f"✨ Procedo con test di generazione usando: {', '.join(available_engines)}")
        test_dir = test_pdf_generation()
        
        print("\n" + "=" * 50)
        print("🎉 Test completati!")
        print(f"📊 Engine testati: {len(available_engines)}")
        print(f"📁 Output directory: {test_dir}")
        
    else:
        print("\n⚠️  Nessun engine PDF disponibile!")
        print("📦 Installazione raccomandazioni:")
        print("   • WeasyPrint: pip install weasyprint")
        print("   • Chrome/Chromium: installare browser")
        print("   • wkhtmltopdf: installare da sistema package manager")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())