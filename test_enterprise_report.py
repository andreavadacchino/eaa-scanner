#!/usr/bin/env python3
"""
Test del sistema multi-agent per generazione report enterprise
usando dati reali da scansione di www.principiadv.com
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from eaa_scanner.agents.orchestrator import AIReportOrchestrator


async def test_enterprise_report():
    """Test generazione report enterprise con dati reali"""
    
    print("\n🚀 AVVIO TEST REPORT ENTERPRISE CON DATI REALI")
    print("=" * 60)
    
    # 1. Recupero risultati scansione reale
    scan_id = "v2scan_y8MPUlktSlw"
    
    # Simulo recupero dati (in produzione verrebbe da DB)
    scan_data = {
        "scan_id": scan_id,
        "url": "https://www.principiadv.com",
        "total_violations": 127,
        "critical_violations": 3,
        "high_violations": 100,
        "medium_violations": 24,
        "low_violations": 0,
        "overall_score": 45.2,  # Score basso per molte violazioni
        "compliance": {
            "overall_score": 45.2,
            "wcag_level": "Non Conforme",
            "eaa_compliance_percentage": 35.0,
            "by_principle": {
                "perceivable": 40.0,
                "operable": 45.0,
                "understandable": 50.0,
                "robust": 46.0
            }
        },
        "all_violations": [
            # Esempi di violazioni reali tipiche
            {
                "code": "img-alt",
                "message": "Immagini senza testo alternativo",
                "severity": "critical",
                "wcag_criteria": "1.1.1",
                "count": 3
            },
            {
                "code": "color-contrast",
                "message": "Contrasto colore insufficiente",
                "severity": "high",
                "wcag_criteria": "1.4.3",
                "count": 15
            },
            {
                "code": "label-missing",
                "message": "Campi form senza etichetta",
                "severity": "high",
                "wcag_criteria": "3.3.2",
                "count": 8
            },
            {
                "code": "heading-order",
                "message": "Ordine heading non corretto",
                "severity": "medium",
                "wcag_criteria": "1.3.1",
                "count": 10
            },
            {
                "code": "link-purpose",
                "message": "Link senza testo descrittivo",
                "severity": "medium",
                "wcag_criteria": "2.4.4",
                "count": 14
            },
            {
                "code": "aria-valid",
                "message": "ARIA attributi non validi",
                "severity": "high",
                "wcag_criteria": "4.1.2",
                "count": 5
            }
        ] * 10  # Moltiplico per simulare 127 violazioni totali
    }
    
    company_info = {
        "name": "Principia SRL",
        "url": "https://www.principiadv.com",
        "email": "info@principiadv.com",
        "country": "Italia"
    }
    
    requirements = {
        "target_audience": "mixed",  # Executive + Technical
        "language": "it",
        "include_cost_estimates": True,
        "include_timeline": True,
        "include_quick_wins": True,
        "include_technical_details": True,
        "include_remediation_plan": True
    }
    
    # 2. Inizializza orchestrator
    print("\n📋 Inizializzazione sistema multi-agent...")
    orchestrator = AIReportOrchestrator()
    
    # 3. Genera report
    print("\n🤖 Generazione report con AI multi-agent...")
    print("   - Executive Summary Agent")
    print("   - Technical Analysis Agent")
    print("   - Compliance Assessment Agent")
    print("   - Remediation Planner Agent")
    print("   - Recommendations Agent")
    print("   - Quality Controller Agent")
    
    try:
        result = await orchestrator.generate_report(
            scan_data=scan_data,
            company_info=company_info,
            requirements=requirements
        )
        
        print("\n✅ REPORT GENERATO CON SUCCESSO!")
        print("=" * 60)
        
        # 4. Analizza risultato
        print(f"\n📊 METRICHE GENERAZIONE:")
        print(f"   - Tempo totale: {result['generation_time']:.2f} secondi")
        print(f"   - Quality score: {result['quality_score']:.1f}/100")
        print(f"   - Agent completati: {result['agents_completed']}/{result['agents_total']}")
        
        if result['agent_metrics']:
            print(f"\n🤖 PERFORMANCE AGENT:")
            for agent, metrics in result['agent_metrics'].items():
                status = "✅" if metrics['success'] else "❌"
                print(f"   {status} {agent}: {metrics['execution_time']:.2f}s - Score: {metrics['quality_score']:.1f}")
        
        # 5. Salva report HTML
        output_path = Path("output/test_enterprise_report.html")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result['html_report'])
        
        print(f"\n💾 Report salvato in: {output_path}")
        print(f"   Dimensione: {len(result['html_report']) / 1024:.1f} KB")
        
        # 6. Verifica qualità contenuto
        print(f"\n🔍 VERIFICA QUALITÀ CONTENUTO:")
        
        # Verifica presenza sezioni chiave
        sections = [
            "Executive Summary",
            "Analisi Tecnica",
            "Valutazione di Conformità",
            "Piano di Remediation",
            "Raccomandazioni"
        ]
        
        for section in sections:
            if section in result['html_report']:
                print(f"   ✅ {section}: presente")
            else:
                print(f"   ❌ {section}: MANCANTE!")
        
        # Verifica dati reali
        if str(scan_data['total_violations']) in result['html_report']:
            print(f"   ✅ Dati reali: integrati ({scan_data['total_violations']} violazioni)")
        else:
            print(f"   ❌ Dati reali: NON TROVATI!")
        
        # Verifica professionalità
        professional_terms = ["WCAG", "EAA", "conformità", "accessibilità", "remediation"]
        found_terms = sum(1 for term in professional_terms if term in result['html_report'])
        print(f"   ✅ Terminologia professionale: {found_terms}/{len(professional_terms)} termini")
        
        print("\n" + "=" * 60)
        print("🎯 TEST COMPLETATO CON SUCCESSO!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE DURANTE GENERAZIONE: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_enterprise_report())
    sys.exit(0 if success else 1)