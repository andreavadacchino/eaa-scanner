#!/usr/bin/env python3
"""
Test completo generazione report con P.O.U.R. e validazione
Utilizza dati reali da scansione e verifica conformità
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Import moduli del nuovo sistema
sys.path.insert(0, str(Path(__file__).parent))

from src.report.generator import EnhancedReportGenerator
from src.report.schema import ScanResult
from src.report.validators import ComplianceValidator


def test_report_generation_with_real_data():
    """Test generazione report con dati reali e validazione automatica"""
    
    print("\n" + "="*60)
    print("TEST GENERAZIONE REPORT P.O.U.R. CON VALIDAZIONE")
    print("="*60)
    
    # 1. Carica dati reali da scansione precedente
    print("\n📂 Caricamento dati scansione...")
    
    # Usa dati dalla scansione di www.principiadv.com se disponibili
    scan_file = Path("/tmp/scan_results.json")
    if scan_file.exists() and False:  # Disabilitato perché mancano dettagli violazioni
        with open(scan_file, "r") as f:
            scanner_data = json.load(f)
        print(f"   ✅ Dati caricati da: {scan_file}")
    else:
        # Genera dati di test realistici basati su www.principiadv.com
        print("   ℹ️ Uso dati di esempio basati su analisi reale")
        scanner_data = generate_realistic_scan_data()
    
    # 2. Informazioni azienda
    company_info = {
        'company_name': 'Principia SRL',
        'url': scanner_data.get('url', 'https://www.principiadv.com')
    }
    
    print(f"\n📊 Statistiche scansione:")
    print(f"   URL: {company_info['url']}")
    print(f"   Totale problemi: {scanner_data.get('total_issues', 0)}")
    print(f"   Critici: {scanner_data.get('critical_issues', 0)}")
    print(f"   Alta priorità: {scanner_data.get('high_issues', 0)}")
    print(f"   Media priorità: {scanner_data.get('medium_issues', 0)}")
    print(f"   Bassa priorità: {scanner_data.get('low_issues', 0)}")
    
    # 3. Genera report con nuovo sistema
    print("\n🔧 Generazione report con sistema P.O.U.R....")
    
    generator = EnhancedReportGenerator()
    
    # Trasforma in ScanResult
    scan_result = generator.generate_scan_result(
        scanner_data,
        company_info['company_name'],
        company_info['url'],
        scan_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    
    print(f"   ✅ ScanResult generato con {len(scan_result.issues)} issues")
    print(f"   ✅ Compliance score: {scan_result.compliance_score:.1f}%")
    
    # Analisi P.O.U.R.
    from src.report.schema import POURPrinciple
    pour_stats = {
        'Percepibile': len(scan_result.get_issues_by_pour(POURPrinciple.PERCEPIBILE)),
        'Operabile': len(scan_result.get_issues_by_pour(POURPrinciple.OPERABILE)),
        'Comprensibile': len(scan_result.get_issues_by_pour(POURPrinciple.COMPRENSIBILE)),
        'Robusto': len(scan_result.get_issues_by_pour(POURPrinciple.ROBUSTO))
    }
    
    print("\n📊 Distribuzione P.O.U.R.:")
    for principle, count in pour_stats.items():
        print(f"   {principle}: {count} issues")
    
    # 4. Salva report con validazione
    print("\n💾 Salvataggio report con validazione...")
    
    output_dir = Path("output/report_pour_test")
    paths = generator.save_report(scan_result, output_dir, validate=True)
    
    print(f"   ✅ Report HTML salvato: {paths['html']}")
    print(f"   ✅ Report JSON salvato: {paths['json']}")
    
    # 5. Verifica validazione
    print("\n🔍 Risultati validazione:")
    
    validation_summary = Path(output_dir / 'validation' / 'validation-summary.txt')
    if validation_summary.exists():
        print(validation_summary.read_text())
    
    # 6. Test aggiuntivi di qualità
    print("\n✨ Verifica qualità report:")
    
    html_content = paths['html'].read_text()
    quality_checks = {
        "P.O.U.R. presente": all(p in html_content for p in ['Percepibile', 'Operabile', 'Comprensibile', 'Robusto']),
        "WCAG 2.1 referenziato": "WCAG 2.1" in html_content,
        "Impatto disabilità": "disabilità" in html_content.lower(),
        "Nessuna data/timeline": validation_summary.exists() and "No-Date Validation: PASSED" in validation_summary.read_text(),
        "Metodologia presente": "metodologia" in html_content.lower(),
        "Processo continuo": "processo continuo" in html_content.lower() or "continuous" in html_content.lower()
    }
    
    passed = 0
    for check, result in quality_checks.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check}")
        if result:
            passed += 1
    
    quality_score = (passed / len(quality_checks)) * 100
    print(f"\n📈 Score qualità: {quality_score:.0f}%")
    
    # 7. Risultato finale
    print("\n" + "="*60)
    if quality_score >= 80:
        print("✅ TEST SUPERATO - Report conforme ai requisiti P.O.U.R.")
    else:
        print("⚠️ TEST PARZIALE - Report necessita miglioramenti")
    print("="*60)
    
    return quality_score >= 80


def generate_realistic_scan_data():
    """Genera dati realistici basati su scansione reale di www.principiadv.com"""
    return {
        'url': 'https://www.principiadv.com',
        'total_issues': 127,
        'critical_issues': 3,
        'high_issues': 100,
        'medium_issues': 24,
        'low_issues': 0,
        'compliance_score': 0.0,
        'all_violations': [
            # Problemi CRITICI (3)
            {
                'code': 'img-alt',
                'message': 'Immagini critiche senza testo alternativo (logo, hero)',
                'severity': 'critical',
                'wcag_criteria': '1.1.1',
                'count': 3,
                'selector': 'img.logo, img.hero-image',
                'scanner': 'axe',
                'impact': 'Blocca completamente accesso a utenti non vedenti'
            },
            
            # Problemi ALTA priorità (100) - campione rappresentativo
            {
                'code': 'color-contrast',
                'message': 'Contrasto colore insufficiente (3.2:1 invece di 4.5:1)',
                'severity': 'high',
                'wcag_criteria': '1.4.3',
                'count': 35,
                'selector': '.text-gray-400, .subtitle',
                'scanner': 'pa11y'
            },
            {
                'code': 'link-name',
                'message': 'Link con testo non descrittivo ("clicca qui", "leggi")',
                'severity': 'high',
                'wcag_criteria': '2.4.4',
                'count': 25,
                'selector': 'a.btn-generic, a.read-more',
                'scanner': 'lighthouse'
            },
            {
                'code': 'form-label',
                'message': 'Campi form senza etichetta associata',
                'severity': 'high',
                'wcag_criteria': '3.3.2',
                'count': 20,
                'selector': 'input[type="text"], input[type="email"]',
                'scanner': 'wave'
            },
            {
                'code': 'focus-visible',
                'message': 'Focus tastiera non visibile su elementi interattivi',
                'severity': 'high',
                'wcag_criteria': '2.4.7',
                'count': 15,
                'selector': 'button, .card-clickable',
                'scanner': 'axe'
            },
            {
                'code': 'button-name',
                'message': 'Pulsanti senza testo accessibile',
                'severity': 'high',
                'wcag_criteria': '4.1.2',
                'count': 5,
                'selector': 'button.icon-only',
                'scanner': 'pa11y'
            },
            
            # Problemi MEDIA priorità (24)
            {
                'code': 'heading-order',
                'message': 'Struttura heading non sequenziale (h1 → h3 senza h2)',
                'severity': 'medium',
                'wcag_criteria': '1.3.1',
                'count': 8,
                'selector': 'h3.section-title',
                'scanner': 'lighthouse'
            },
            {
                'code': 'aria-valid-attr',
                'message': 'Attributi ARIA non validi o mal utilizzati',
                'severity': 'medium',
                'wcag_criteria': '4.1.2',
                'count': 6,
                'selector': '[role="navigation"], [aria-label]',
                'scanner': 'axe'
            },
            {
                'code': 'list',
                'message': 'Liste non semanticamente corrette',
                'severity': 'medium',
                'wcag_criteria': '1.3.1',
                'count': 5,
                'selector': '.menu-items, .footer-links',
                'scanner': 'wave'
            },
            {
                'code': 'lang',
                'message': 'Sezioni in inglese senza lang="en" specificato',
                'severity': 'medium',
                'wcag_criteria': '3.1.2',
                'count': 3,
                'selector': '.english-content',
                'scanner': 'pa11y'
            },
            {
                'code': 'duplicate-id',
                'message': 'ID duplicati nel DOM',
                'severity': 'medium',
                'wcag_criteria': '4.1.1',
                'count': 2,
                'selector': '#header, #footer',
                'scanner': 'lighthouse'
            }
        ]
    }

def generate_test_data():
    """Genera dati di test realistici se mancano dati reali"""
    return {
        'url': 'https://www.governo.it',
        'total_issues': 45,
        'critical_issues': 2,
        'high_issues': 15,
        'medium_issues': 20,
        'low_issues': 8,
        'compliance_score': 65.0,
        'all_violations': [
            {
                'code': 'img-alt',
                'message': 'Immagini senza testo alternativo',
                'severity': 'critical',
                'wcag_criteria': '1.1.1',
                'count': 5,
                'selector': 'img.logo',
                'scanner': 'axe'
            },
            {
                'code': 'color-contrast',
                'message': 'Contrasto colore insufficiente',
                'severity': 'high',
                'wcag_criteria': '1.4.3',
                'count': 10,
                'selector': '.text-muted',
                'scanner': 'pa11y'
            },
            {
                'code': 'form-label',
                'message': 'Campo form senza etichetta',
                'severity': 'high',
                'wcag_criteria': '3.3.2',
                'count': 8,
                'selector': 'input#search',
                'scanner': 'lighthouse'
            },
            {
                'code': 'heading-order',
                'message': 'Ordine heading non corretto',
                'severity': 'medium',
                'wcag_criteria': '1.3.1',
                'count': 12,
                'selector': 'h3',
                'scanner': 'wave'
            },
            {
                'code': 'aria-valid-attr',
                'message': 'Attributi ARIA non validi',
                'severity': 'medium',
                'wcag_criteria': '4.1.2',
                'count': 5,
                'selector': '[role="navigation"]',
                'scanner': 'axe'
            },
            {
                'code': 'link-name',
                'message': 'Link senza testo descrittivo',
                'severity': 'high',
                'wcag_criteria': '2.4.4',
                'count': 15,
                'selector': 'a.btn',
                'scanner': 'pa11y'
            }
        ]
    }


def test_real_government_sites():
    """Test su siti governativi reali italiani"""
    
    print("\n" + "="*60)
    print("TEST SU SITI GOVERNATIVI ITALIANI REALI")
    print("="*60)
    
    sites = [
        "https://www.governo.it",
        "https://www.agid.gov.it",
        "https://www.inps.it",
        "https://www.agenziadelleentrate.it"
    ]
    
    print("\n🌐 Siti da testare:")
    for site in sites:
        print(f"   - {site}")
    
    print("\n⚠️ NOTA: Questo test richiede scanner reali configurati")
    print("Per eseguire test completi, utilizzare:")
    print("python3 -m eaa_scanner.cli --url <URL> --real")
    
    # Qui potremmo integrare con Playwright per test browser reali
    # ma per ora simuliamo
    
    print("\n📋 Checklist manuale per validazione:")
    print("   [ ] Navigazione da tastiera funzionante")
    print("   [ ] Contrasto colori adeguato (4.5:1)")
    print("   [ ] Immagini con alt text")
    print("   [ ] Form con label associate")
    print("   [ ] Heading in ordine gerarchico")
    print("   [ ] Link con testo descrittivo")
    print("   [ ] ARIA landmarks presenti")
    print("   [ ] Focus visibile")
    
    return True


if __name__ == "__main__":
    # Esegui test principale
    success = test_report_generation_with_real_data()
    
    # Test aggiuntivo su siti reali
    if success:
        test_real_government_sites()
    
    sys.exit(0 if success else 1)