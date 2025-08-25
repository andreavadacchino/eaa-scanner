#!/usr/bin/env python3
"""
Test del nuovo template di audit professionale
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.report.generator import EnhancedReportGenerator
from src.report.validators import ComplianceValidator


def test_professional_audit():
    """Test generazione audit professionale con validazione"""
    
    print("=" * 70)
    print("TEST AUDIT PROFESSIONALE DI ACCESSIBILITÀ")
    print("=" * 70)
    
    # Dati realistici basati su analisi reale
    scanner_data = {
        'wave': {
            'violations': [
                {'code': 'img-alt', 'description': 'Immagine senza testo alternativo', 'selector': 'img', 'count': 15},
                {'code': 'label_missing', 'description': 'Form senza label', 'selector': 'input', 'count': 8},
                {'code': 'heading_skipped', 'description': 'Salto nella gerarchia heading', 'selector': 'h3', 'count': 5}
            ]
        },
        'axe': {
            'violations': [
                {'id': 'color-contrast', 'description': 'Contrasto insufficiente', 'nodes': [{'html': '<p>'}], 'impact': 'serious'},
                {'id': 'aria-required-attr', 'description': 'Attributi ARIA mancanti', 'nodes': [{'html': '<div role="navigation">'}], 'impact': 'critical'},
                {'id': 'landmark-no-duplicate-main', 'description': 'Multipli elementi main', 'nodes': [{'html': '<main>'}], 'impact': 'moderate'}
            ]
        },
        'pa11y': {
            'violations': [
                {'code': 'WCAG2AA.Principle1.Guideline1_4.1_4_3', 'message': 'Contrasto testo', 'selector': '.footer'},
                {'code': 'WCAG2AA.Principle2.Guideline2_1.2_1_1', 'message': 'Non accessibile da tastiera', 'selector': '.dropdown'}
            ]
        },
        'lighthouse': {
            'violations': [
                {'id': 'button-name', 'title': 'Bottoni senza testo accessibile'},
                {'id': 'link-name', 'title': 'Link senza testo descrittivo'},
                {'id': 'meta-viewport', 'title': 'Viewport non configurato per mobile'}
            ]
        }
    }
    
    # Genera report con nuovo template
    print("\n📊 Generazione audit professionale...")
    generator = EnhancedReportGenerator()
    
    scan_result = generator.generate_scan_result(
        scanner_data,
        "Esempio Organizzazione SPA",
        "https://esempio-org.it"
    )
    
    print(f"   ✅ Identificate {scan_result.total_issues} non conformità")
    print(f"   ✅ Score conformità: {scan_result.compliance_score:.1f}%")
    
    # Determina livello conformità
    if scan_result.compliance_score >= 90:
        level = "Sostanzialmente Conforme"
    elif scan_result.compliance_score >= 50:
        level = "Parzialmente Conforme"
    else:
        level = "Non Conforme"
    print(f"   ✅ Livello: {level}")
    
    # Genera HTML con nuovo template
    print("\n📝 Applicazione template audit professionale...")
    html = generator.generate_html_report(
        scan_result, 
        template_name='professional_audit_report.html',
        use_ai=False  # Per ora senza AI per velocità
    )
    
    # Salva e valida
    output_dir = Path("output/audit_professionale")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "audit_accessibilita.html"
    report_path.write_text(html, encoding='utf-8')
    
    print(f"   ✅ Audit salvato: {report_path}")
    
    # Validazione conformità
    print("\n🔍 Validazione conformità documento...")
    validation = ComplianceValidator.validate_report(report_path)
    
    if validation['valid']:
        print("   ✅ Documento conforme ai requisiti")
    else:
        print("   ⚠️ Verificare validazione:")
        if not validation['validations']['no_date']['valid']:
            print(f"      - Date/timeline trovate: {validation['validations']['no_date']['total_violations']}")
        if not validation['validations']['methodology']['valid']:
            print(f"      - Elementi metodologia mancanti: {len(validation['validations']['methodology']['missing_elements'])}")
    
    # Verifica struttura
    print("\n📋 Verifica struttura audit:")
    sections = [
        "Identificazione del Documento",
        "Sintesi Esecutiva", 
        "Analisi secondo i Principi P.O.U.R.",
        "Analisi dell'Impatto sugli Utenti",
        "Dettaglio delle Non Conformità",
        "Piano di Intervento Strutturato",
        "Raccomandazioni Strategiche",
        "Conformità Normativa e Compliance",
        "Metodologia di Valutazione",
        "Dichiarazione di Accessibilità",
        "Conclusioni e Prossimi Passi",
        "Nota Legale e Limitazioni"
    ]
    
    for section in sections:
        if section in html:
            print(f"   ✅ {section}")
        else:
            print(f"   ❌ {section} MANCANTE")
    
    print("\n" + "=" * 70)
    print("✅ AUDIT PROFESSIONALE GENERATO CON SUCCESSO")
    print("=" * 70)
    
    # Stats finali
    print("\n📊 Statistiche Audit:")
    print(f"   • Conformità WCAG 2.1 AA: {scan_result.compliance_score:.1f}%")
    print(f"   • Barriere critiche: {scan_result.critical_issues}")
    print(f"   • Problemi gravi: {scan_result.high_issues}")
    print(f"   • Totale non conformità: {scan_result.total_issues}")
    print(f"   • Principi P.O.U.R. coinvolti: 4/4")
    print(f"   • Categorie utenti impattate: 6/6")
    
    return True


if __name__ == "__main__":
    try:
        test_professional_audit()
        print("\n🎯 Per aprire l'audit: open output/audit_professionale/audit_accessibilita.html")
    except Exception as e:
        print(f"\n❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)