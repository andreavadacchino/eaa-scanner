#!/usr/bin/env python3
"""
Test integrazione OpenAI per generazione contenuti report
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carica variabili dal .env
load_dotenv()

sys.path.append(str(Path(__file__).parent))

from src.report.generator import EnhancedReportGenerator
from src.report.validators import ComplianceValidator


def test_openai_content():
    """Test generazione contenuti con OpenAI"""
    
    print("=" * 70)
    print("TEST INTEGRAZIONE OPENAI PER REPORT ACCESSIBILITÀ")
    print("=" * 70)
    
    # Verifica API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n⚠️  OPENAI_API_KEY non configurata!")
        print("   Per utilizzare OpenAI, configura la variabile d'ambiente:")
        print("   export OPENAI_API_KEY='your-api-key'")
        print("\n   Il sistema userà contenuti fallback senza AI.")
    else:
        print(f"\n✅ OpenAI API Key configurata (****{api_key[-4:]})")
    
    # Dati di test minimali
    scanner_data = {
        'wave': {
            'violations': [
                {'code': 'img-alt', 'description': 'Immagine senza testo alternativo', 'selector': 'img', 'count': 5},
                {'code': 'label_missing', 'description': 'Campo form senza etichetta', 'selector': 'input', 'count': 3}
            ]
        },
        'axe': {
            'violations': [
                {'id': 'color-contrast', 'description': 'Contrasto insufficiente', 'nodes': [{'html': '<p>'}], 'impact': 'serious'}
            ]
        }
    }
    
    # Genera report con AI
    print("\n📝 Generazione report con contenuti AI...")
    generator = EnhancedReportGenerator()
    
    scan_result = generator.generate_scan_result(
        scanner_data,
        "Test Company SRL",
        "https://test-company.it"
    )
    
    print(f"   ✅ Scan result generato: {scan_result.total_issues} issues")
    
    # Genera HTML con AI attivato
    print("\n🤖 Generazione contenuti testuali con AI...")
    html = generator.generate_html_report(
        scan_result, 
        template_name='minimal_audit_report.html',
        use_ai=True  # Forza uso AI
    )
    
    # Salva report
    output_dir = Path("output/test_openai")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "test_openai_report.html"
    report_path.write_text(html, encoding='utf-8')
    
    print(f"   ✅ Report salvato: {report_path}")
    
    # Verifica presenza contenuti AI
    if api_key:
        print("\n🔍 Verifica contenuti generati:")
        
        # Cerca indicatori di contenuto AI vs fallback
        if "Il sito web di" in html and "presenta un punteggio" in html:
            print("   ⚠️  Probabilmente usando contenuti fallback")
        else:
            print("   ✅ Contenuti sembrano generati da AI")
    
    # Validazione
    print("\n🔍 Validazione conformità...")
    validation = ComplianceValidator.validate_report(report_path)
    
    if validation['valid']:
        print("   ✅ Report conforme alle linee guida")
    else:
        print("   ⚠️  Alcune validazioni non passate")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETATO")
    print("=" * 70)
    
    if api_key:
        print("\n💡 Suggerimento: Apri il report per verificare i contenuti AI:")
    else:
        print("\n💡 Per abilitare la generazione AI, configura OPENAI_API_KEY:")
        print("   export OPENAI_API_KEY='your-api-key'")
    
    print(f"   open {report_path}")
    
    return True


if __name__ == "__main__":
    try:
        # Installa openai se necessario
        try:
            import openai
        except ImportError:
            print("📦 Installazione libreria OpenAI...")
            os.system("pip install openai")
            print("   ✅ OpenAI installato")
        
        test_openai_content()
        
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)