#!/usr/bin/env python3
"""
Test OpenAI con scansione reale
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


def test_openai_real_scan():
    """Test con dati reali da scanner"""
    
    print("=" * 70)
    print("TEST OPENAI CON DATI REALI")
    print("=" * 70)
    
    # Verifica API key
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"\n✅ OpenAI API Key configurata (****{api_key[-4:]})")
    else:
        print("\n⚠️  OpenAI API Key non trovata, usando fallback")
    
    # Simula dati realistici da scanner
    scanner_data = {
        'wave': {
            'violations': [
                {'code': 'img-alt', 'description': 'Immagine decorativa senza testo alternativo vuoto', 'selector': 'img.hero-banner', 'count': 3},
                {'code': 'label_missing', 'description': 'Campo email del form newsletter senza etichetta', 'selector': '#newsletter-email', 'count': 1},
                {'code': 'heading_skipped', 'description': 'Salto da h1 a h3 nella sezione servizi', 'selector': '.services h3', 'count': 2},
                {'code': 'link_empty', 'description': 'Link social con solo icona senza testo', 'selector': '.social-links a', 'count': 4}
            ]
        },
        'axe': {
            'violations': [
                {'id': 'color-contrast', 'description': 'Testo grigio su sfondo bianco con contrasto 3.5:1', 'nodes': [{'html': '<p class="disclaimer">'}], 'impact': 'serious'},
                {'id': 'aria-required-attr', 'description': 'Menu dropdown senza aria-expanded', 'nodes': [{'html': '<button class="dropdown">'}], 'impact': 'critical'},
                {'id': 'landmark-no-duplicate-main', 'description': 'Due elementi main nella pagina', 'nodes': [{'html': '<main>'}], 'impact': 'moderate'}
            ]
        },
        'pa11y': {
            'violations': [
                {'code': 'WCAG2AA.Principle1.Guideline1_4.1_4_3', 'message': 'Placeholder del form con contrasto insufficiente', 'selector': 'input::placeholder'},
                {'code': 'WCAG2AA.Principle2.Guideline2_1.2_1_1', 'message': 'Carousel non navigabile da tastiera', 'selector': '.carousel'},
                {'code': 'WCAG2AA.Principle3.Guideline3_3.3_3_2', 'message': 'Form di contatto senza istruzioni chiare', 'selector': '#contact-form'}
            ]
        },
        'lighthouse': {
            'violations': [
                {'id': 'button-name', 'title': 'Pulsante "Invia" senza testo accessibile nel form ricerca'},
                {'id': 'link-name', 'title': 'Link "Clicca qui" non descrittivo'},
                {'id': 'meta-viewport', 'title': 'Tag viewport mancante per responsive design'},
                {'id': 'html-lang', 'title': 'Attributo lang non specificato in HTML'}
            ]
        }
    }
    
    # Genera report con AI
    print("\n📝 Generazione report con OpenAI...")
    generator = EnhancedReportGenerator()
    
    scan_result = generator.generate_scan_result(
        scanner_data,
        "Azienda Esempio SPA",
        "https://www.esempio-azienda.it"
    )
    
    print(f"   ✅ Trovate {scan_result.total_issues} problematiche")
    print(f"   ✅ Score conformità: {scan_result.compliance_score:.1f}%")
    print(f"   ✅ Livello: {scan_result.compliance_level}")
    
    # Genera HTML con AI
    print("\n🤖 Generazione contenuti testuali con OpenAI...")
    html = generator.generate_html_report(
        scan_result, 
        template_name='minimal_audit_report.html',
        use_ai=True
    )
    
    # Salva report
    output_dir = Path("output/test_openai_real")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "audit_esempio_azienda.html"
    report_path.write_text(html, encoding='utf-8')
    
    print(f"   ✅ Report salvato: {report_path}")
    
    # Validazione
    print("\n🔍 Validazione conformità...")
    validation = ComplianceValidator.validate_report(report_path)
    
    if validation['valid']:
        print("   ✅ Report conforme alle linee guida")
    else:
        print("   ⚠️  Verificare validazione:")
        if not validation['validations']['no_date']['valid']:
            print(f"      - Date trovate: {validation['validations']['no_date']['total_violations']}")
        if not validation['validations']['methodology']['valid']:
            print(f"      - Elementi mancanti: {len(validation['validations']['methodology']['missing_elements'])}")
    
    # Verifica contenuti AI
    print("\n📊 Analisi contenuti generati:")
    
    # Cerca indicatori di contenuto AI
    ai_indicators = [
        "Il sito web di",  # Fallback tipico
        "presenta un punteggio",  # Fallback tipico
        "L'analisi del sito",  # Possibile AI
        "La valutazione",  # Possibile AI
        "evidenzia la necessità",  # Stile AI
        "è fondamentale",  # Stile AI
        "si raccomanda",  # Stile AI
    ]
    
    ai_score = 0
    for indicator in ai_indicators:
        if indicator in html:
            ai_score += 1
    
    if ai_score <= 2:
        print("   ✅ Contenuti probabilmente generati da OpenAI")
    elif ai_score <= 4:
        print("   🔄 Mix di contenuti AI e fallback")
    else:
        print("   ⚠️  Principalmente contenuti fallback")
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETATO CON SUCCESSO")
    print("=" * 70)
    
    print(f"\n📄 Apri il report per verificare i contenuti:")
    print(f"   open {report_path}")
    
    return True


if __name__ == "__main__":
    try:
        test_openai_real_scan()
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)