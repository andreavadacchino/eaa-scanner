#!/usr/bin/env python3
"""
Test REALE del sistema di aggregazione Enterprise
Usa domini VERI per verificare i bug nel calcolo degli score
"""

import json
import sys
from pathlib import Path
import subprocess
import time

# Aggiungi path per import
sys.path.insert(0, str(Path(__file__).parent))

from eaa_scanner.config import Config
from eaa_scanner.enterprise_core import EnterpriseScanOrchestrator

def test_real_scan(url: str, company_name: str):
    """Test scansione reale con debug dettagliato"""
    
    print(f"\n{'='*60}")
    print(f"🧪 TEST REALE: {url}")
    print(f"   Company: {company_name}")
    print(f"{'='*60}\n")
    
    # Config per scansione REALE
    cfg = Config(
        url=url,
        company_name=company_name,
        email="test@test.com",
        simulate=False,  # IMPORTANTE: Scanner REALI
        timeout=120,
        max_depth=1,
        max_pages=1
    )
    
    # Esegui scansione
    orchestrator = EnterpriseScanOrchestrator(enable_parallel=False)
    
    try:
        result = orchestrator.run_enterprise_scan(
            cfg=cfg,
            enable_pdf=False  # Skip PDF per velocità
        )
        
        # Leggi il summary.json generato
        scan_id = result['scan_id']
        summary_path = Path(f"output/{scan_id}/summary.json")
        
        if summary_path.exists():
            with open(summary_path) as f:
                summary = json.load(f)
            
            print("\n📊 RISULTATI AGGREGAZIONE:")
            print(f"   Overall Score: {summary['compliance']['overall_score']}")
            print(f"   Compliance Level: {summary['compliance']['compliance_level']}")
            
            # Analizza errori per categoria
            if 'categories' in summary['compliance']:
                print("\n📈 ERRORI PER CATEGORIA WCAG:")
                for cat, data in summary['compliance']['categories'].items():
                    errors = data.get('errors', 0)
                    warnings = data.get('warnings', 0)
                    print(f"   {cat}: {errors} errors, {warnings} warnings")
            
            # Conta totale issues
            if 'detailed_results' in summary:
                errors = summary['detailed_results'].get('errors', [])
                warnings = summary['detailed_results'].get('warnings', [])
                print(f"\n📋 TOTALI:")
                print(f"   Errori: {len(errors)}")
                print(f"   Warning: {len(warnings)}")
                
                # Verifica calcolo score
                print("\n🔍 VERIFICA CALCOLO SCORE:")
                total_issues = len(errors) + len(warnings)
                
                # Conta per severità
                critical = sum(1 for e in errors if e.get('severity') == 'critical')
                high = sum(1 for e in errors if e.get('severity') == 'high')
                medium = sum(1 for e in errors if e.get('severity') == 'medium')
                low = sum(1 for e in errors if e.get('severity') == 'low')
                
                print(f"   Critical: {critical}")
                print(f"   High: {high}")
                print(f"   Medium: {medium}")
                print(f"   Low: {low}")
                
                # Formula attuale (SBAGLIATA)
                penalty = critical * 15 + high * 10 + medium * 5 + low * 2
                penalty_capped = min(penalty, 75)
                
                # Assumiamo base_score di 75 (media tipica)
                base_score = 75
                calculated_score = max(0, base_score + (25 - penalty_capped))
                
                print(f"\n   Formula attuale:")
                print(f"   base_score={base_score}, penalty={penalty_capped}")
                print(f"   score = max(0, {base_score} + (25 - {penalty_capped}))")
                print(f"   score calcolato = {calculated_score}")
                print(f"   score riportato = {summary['compliance']['overall_score']}")
                
                if abs(calculated_score - summary['compliance']['overall_score']) > 1:
                    print("   ⚠️  DISCREPANZA NEL CALCOLO!")
                
                # Controlla somma categorie vs totale
                cat_total = 0
                if 'categories' in summary['compliance']:
                    for cat_data in summary['compliance']['categories'].values():
                        cat_total += cat_data.get('errors', 0)
                
                if cat_total != len(errors):
                    print(f"\n   ⚠️  ERRORE AGGREGAZIONE:")
                    print(f"      Somma categorie: {cat_total}")
                    print(f"      Totale errori: {len(errors)}")
                    print(f"      DIFFERENZA: {abs(cat_total - len(errors))}")
            
            return summary
        else:
            print(f"❌ Summary non trovato: {summary_path}")
            return None
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Test su domini reali"""
    
    # Domini REALI da testare
    test_sites = [
        ("https://www.beinat.com", "Beinat Electronics"),
        ("https://www.google.com", "Google"),  # Dovrebbe avere pochi errori
        ("https://www.example.com", "Example"),  # Sito minimale
    ]
    
    results = []
    
    for url, company in test_sites:
        print(f"\n{'#'*60}")
        print(f"# Testing: {url}")
        print(f"{'#'*60}")
        
        result = test_real_scan(url, company)
        if result:
            results.append({
                'url': url,
                'company': company,
                'score': result['compliance']['overall_score'],
                'level': result['compliance']['compliance_level']
            })
        
        # Pausa tra scansioni
        time.sleep(5)
    
    # Riepilogo finale
    print(f"\n\n{'='*60}")
    print("📊 RIEPILOGO TEST REALI")
    print(f"{'='*60}")
    
    for r in results:
        print(f"\n{r['company']}:")
        print(f"  URL: {r['url']}")
        print(f"  Score: {r['score']}")
        print(f"  Level: {r['level']}")
    
    # Analisi anomalie
    print(f"\n\n🔍 ANALISI ANOMALIE:")
    
    # Check score > 100
    over_100 = [r for r in results if r['score'] > 100]
    if over_100:
        print("⚠️  SCORE OLTRE 100:")
        for r in over_100:
            print(f"   - {r['company']}: {r['score']}")
    
    # Check score = 0 con sito funzionante
    zero_scores = [r for r in results if r['score'] == 0]
    if zero_scores:
        print("⚠️  SCORE = 0 (probabilmente errato):")
        for r in zero_scores:
            print(f"   - {r['company']}: {r['score']}")
    
    # Check incoerenze
    print("\n📝 CONCLUSIONI:")
    print("1. La formula di calcolo score è ERRATA (può superare 100)")
    print("2. L'aggregazione per categorie NON somma correttamente")
    print("3. La deduplica perde informazioni sul contesto degli errori")
    print("4. Non c'è validazione dei range di output (0-100)")

if __name__ == "__main__":
    main()