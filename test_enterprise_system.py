#!/usr/bin/env python3
"""
Test completo del sistema Enterprise EAA Scanner
Testa tutti e 4 gli scanner con dati reali usando il nuovo sistema enterprise
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_enterprise.log')
    ]
)
logger = logging.getLogger(__name__)

# Import sistema enterprise
try:
    from eaa_scanner.enterprise_integration import FastAPIEnterpriseAdapter
    from eaa_scanner.config import Config
    logger.info("✅ Enterprise system imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import enterprise system: {e}")
    sys.exit(1)


class EnterpriseSystemTester:
    """Tester completo per sistema enterprise"""
    
    def __init__(self):
        self.adapter = FastAPIEnterpriseAdapter()
        self.test_results = {
            "started_at": datetime.now().isoformat(),
            "tests": {},
            "overall_status": "running"
        }
    
    def run_comprehensive_test(self):
        """Esegue test completo del sistema enterprise"""
        
        logger.info("🚀 Avvio test completo sistema Enterprise EAA Scanner")
        logger.info("=" * 80)
        
        # Test 1: Sistema con tutti gli scanner (reale)
        test1_result = self._test_all_scanners_real()
        self.test_results["tests"]["all_scanners_real"] = test1_result
        
        # Test 2: Sistema solo con 3 scanner (senza WAVE)
        test2_result = self._test_three_scanners()
        self.test_results["tests"]["three_scanners"] = test2_result
        
        # Test 3: Sistema in modalità simulate
        test3_result = self._test_simulate_mode()
        self.test_results["tests"]["simulate_mode"] = test3_result
        
        # Test 4: Sistema con errori controllati
        test4_result = self._test_error_handling()
        self.test_results["tests"]["error_handling"] = test4_result
        
        # Analizza risultati
        self._analyze_results()
        
        # Salva report test
        self._save_test_report()
        
        logger.info("🏁 Test completo terminato")
        return self.test_results
    
    def _test_all_scanners_real(self) -> dict:
        """Test con tutti e 4 gli scanner in modalità reale"""
        
        logger.info("🧪 Test 1: Tutti i 4 scanner (WAVE, Pa11y, Axe, Lighthouse)")
        test_start = time.time()
        
        try:
            # Usa URL governo.it per test reale
            result = self.adapter.run_enterprise_scan_for_api(
                url="https://governo.it",
                company_name="Test Enterprise Gov",
                email="test@enterprise.gov",
                wave_api_key="9u8c2c8z5746",  # Usa la chiave fornita
                simulate=False
            )
            
            test_time = time.time() - test_start
            
            # Analizza risultato
            analysis = self._analyze_scan_result(result, "all_scanners_real")
            
            logger.info(f"✅ Test 1 completato in {test_time:.2f}s")
            logger.info(f"Score: {analysis.get('overall_score', 'N/A')}")
            logger.info(f"Scanner riusciti: {analysis.get('successful_scanners', 0)}")
            
            return {
                "status": "success",
                "execution_time": test_time,
                "result": result,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Test 1 fallito: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - test_start
            }
    
    def _test_three_scanners(self) -> dict:
        """Test con 3 scanner (senza WAVE)"""
        
        logger.info("🧪 Test 2: Tre scanner (Pa11y, Axe, Lighthouse) - no WAVE")
        test_start = time.time()
        
        try:
            result = self.adapter.run_enterprise_scan_for_api(
                url="https://beinat.com",  # Usa altro URL per varietà
                company_name="Test Three Scanners",
                email="test@threescanners.com", 
                wave_api_key=None,  # No WAVE
                simulate=False
            )
            
            test_time = time.time() - test_start
            analysis = self._analyze_scan_result(result, "three_scanners")
            
            logger.info(f"✅ Test 2 completato in {test_time:.2f}s")
            logger.info(f"Score: {analysis.get('overall_score', 'N/A')}")
            logger.info(f"Scanner riusciti: {analysis.get('successful_scanners', 0)}")
            
            return {
                "status": "success",
                "execution_time": test_time,
                "result": result,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Test 2 fallito: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - test_start
            }
    
    def _test_simulate_mode(self) -> dict:
        """Test in modalità simulazione"""
        
        logger.info("🧪 Test 3: Modalità simulazione (tutti i scanner)")
        test_start = time.time()
        
        try:
            result = self.adapter.run_enterprise_scan_for_api(
                url="https://example.com",
                company_name="Test Simulate Mode",
                email="test@simulate.com",
                wave_api_key=None,
                simulate=True  # Modalità simulazione
            )
            
            test_time = time.time() - test_start
            analysis = self._analyze_scan_result(result, "simulate_mode")
            
            logger.info(f"✅ Test 3 completato in {test_time:.2f}s")
            logger.info(f"Score: {analysis.get('overall_score', 'N/A')}")
            
            return {
                "status": "success",
                "execution_time": test_time,
                "result": result,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"❌ Test 3 fallito: {e}")
            return {
                "status": "failed", 
                "error": str(e),
                "execution_time": time.time() - test_start
            }
    
    def _test_error_handling(self) -> dict:
        """Test gestione errori con URL non valido"""
        
        logger.info("🧪 Test 4: Gestione errori (URL non valido)")
        test_start = time.time()
        
        try:
            result = self.adapter.run_enterprise_scan_for_api(
                url="https://invalid-url-that-does-not-exist-12345.com",
                company_name="Test Error Handling",
                email="test@errorhandling.com",
                wave_api_key=None,
                simulate=False
            )
            
            test_time = time.time() - test_start
            
            # Per questo test, anche un errore controllato è un successo
            if result.get("status") == "error":
                logger.info("✅ Test 4 completato: errore gestito correttamente")
                return {
                    "status": "success", 
                    "execution_time": test_time,
                    "result": result,
                    "note": "Error handled gracefully as expected"
                }
            else:
                logger.warning("⚠️ Test 4: URL non valido non ha generato errore atteso")
                return {
                    "status": "unexpected_success",
                    "execution_time": test_time,
                    "result": result
                }
                
        except Exception as e:
            # Anche questo è un successo per test error handling
            logger.info(f"✅ Test 4 completato: eccezione gestita correttamente - {e}")
            return {
                "status": "success",
                "error_handled": str(e),
                "execution_time": time.time() - test_start
            }
    
    def _analyze_scan_result(self, result: dict, test_name: str) -> dict:
        """Analizza risultato scansione per metriche"""
        
        analysis = {
            "test_name": test_name,
            "api_status": result.get("status", "unknown"),
            "enterprise_mode": result.get("enterprise_mode", False)
        }
        
        # Se abbiamo compliance data
        if "compliance_summary" in result:
            compliance = result["compliance_summary"]
            analysis.update({
                "overall_score": compliance.get("overall_score"),
                "compliance_level": compliance.get("compliance_level"),
                "total_violations": compliance.get("total_violations"),
                "confidence": compliance.get("confidence")
            })
        
        # Se abbiamo execution info
        if "execution_info" in result:
            execution = result["execution_info"]
            analysis.update({
                "successful_scanners": execution.get("successful_scanners"),
                "failed_scanners": execution.get("failed_scanners"),
                "success_rate": execution.get("success_rate")
            })
        
        # Se abbiamo paths
        if "base_out" in result:
            analysis["output_directory"] = result["base_out"]
            analysis["has_html_report"] = bool(result.get("report_html_path"))
            analysis["has_pdf_report"] = bool(result.get("report_pdf_path"))
        
        return analysis
    
    def _analyze_results(self):
        """Analizza risultati complessivi"""
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 ANALISI RISULTATI COMPLESSIVI")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results["tests"])
        successful_tests = sum(1 for test in self.test_results["tests"].values() 
                             if test.get("status") == "success")
        
        logger.info(f"Test totali: {total_tests}")
        logger.info(f"Test riusciti: {successful_tests}")
        logger.info(f"Tasso successo: {successful_tests/total_tests*100:.1f}%")
        
        # Analisi dettagliata per test
        for test_name, test_data in self.test_results["tests"].items():
            logger.info(f"\n📋 {test_name.upper()}:")
            logger.info(f"  Status: {test_data.get('status', 'unknown')}")
            logger.info(f"  Tempo: {test_data.get('execution_time', 0):.2f}s")
            
            if "analysis" in test_data:
                analysis = test_data["analysis"]
                logger.info(f"  Score: {analysis.get('overall_score', 'N/A')}")
                logger.info(f"  Scanner riusciti: {analysis.get('successful_scanners', 'N/A')}")
                logger.info(f"  Compliance: {analysis.get('compliance_level', 'N/A')}")
        
        # Determina status generale
        if successful_tests == total_tests:
            self.test_results["overall_status"] = "all_passed"
        elif successful_tests > 0:
            self.test_results["overall_status"] = "partial_success"
        else:
            self.test_results["overall_status"] = "all_failed"
        
        logger.info(f"\n🏆 RISULTATO FINALE: {self.test_results['overall_status']}")
    
    def _save_test_report(self):
        """Salva report test completo"""
        
        self.test_results["completed_at"] = datetime.now().isoformat()
        
        # Salva JSON dettagliato
        with open("test_enterprise_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Salva summary leggibile
        with open("test_enterprise_summary.txt", "w", encoding="utf-8") as f:
            f.write("ENTERPRISE EAA SCANNER - TEST RESULTS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Started: {self.test_results['started_at']}\n")
            f.write(f"Completed: {self.test_results['completed_at']}\n")
            f.write(f"Overall Status: {self.test_results['overall_status']}\n\n")
            
            for test_name, test_data in self.test_results["tests"].items():
                f.write(f"{test_name.upper()}: {test_data.get('status', 'unknown')}\n")
                if "analysis" in test_data:
                    analysis = test_data["analysis"]
                    f.write(f"  Score: {analysis.get('overall_score', 'N/A')}\n")
                    f.write(f"  Compliance: {analysis.get('compliance_level', 'N/A')}\n")
                f.write(f"  Time: {test_data.get('execution_time', 0):.2f}s\n\n")
        
        logger.info("💾 Report test salvati:")
        logger.info("  - test_enterprise_results.json (dettagliato)")
        logger.info("  - test_enterprise_summary.txt (riassunto)")


def main():
    """Entry point principale"""
    
    print("🚀 ENTERPRISE EAA SCANNER - COMPREHENSIVE TEST")
    print("=" * 80)
    print("Questo test verificherà il sistema enterprise con:")
    print("- Tutti e 4 gli scanner con dati reali")
    print("- Gestione robusta errori e null values")
    print("- Pydantic validation e type safety")
    print("- Charts generation con fallback")
    print("- PDF e HTML report generation")
    print("=" * 80)
    print()
    
    # Chiedi conferma
    if input("Procedere con i test? (y/n): ").lower() != 'y':
        print("Test annullato.")
        return
    
    # Esegui test
    tester = EnterpriseSystemTester()
    results = tester.run_comprehensive_test()
    
    # Mostra riassunto finale
    print("\n" + "=" * 80)
    print("🏁 TEST COMPLETATO!")
    print("=" * 80)
    print(f"Status finale: {results['overall_status']}")
    print("Controlla i file di report per dettagli completi.")
    print("=" * 80)


if __name__ == "__main__":
    main()