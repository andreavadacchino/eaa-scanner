#!/usr/bin/env python3
"""
Test finale sistema Enterprise tramite API nel container Docker
Test completo con tutti e 4 gli scanner su siti reali
"""

import requests
import json
import time
import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_enterprise_api.log')
    ]
)
logger = logging.getLogger(__name__)

class EnterpriseAPITester:
    """Tester completo sistema enterprise tramite API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {
            "started_at": datetime.now().isoformat(),
            "base_url": base_url,
            "tests": {},
            "overall_status": "running"
        }
        
        # Timeout configurations
        self.request_timeout = 180  # 3 minuti per request
        self.scan_timeout = 300     # 5 minuti per scan completa
    
    def test_api_connectivity(self) -> bool:
        """Test connettività API"""
        
        logger.info("🔌 Testing API connectivity...")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                logger.info("✅ API connectivity OK")
                return True
            else:
                logger.error(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API connectivity failed: {e}")
            return False
    
    def run_enterprise_scan_api(self, url: str, company_name: str, email: str, 
                               wave_api_key: str = None, test_name: str = "unknown") -> dict:
        """Esegue scansione enterprise tramite API"""
        
        logger.info(f"🚀 Starting enterprise scan via API: {test_name}")
        logger.info(f"URL: {url}")
        logger.info(f"Company: {company_name}")
        
        # Payload per API
        payload = {
            "url": url,
            "company_name": company_name,
            "email": email,
            "simulate": False,  # DATI REALI - NO SIMULAZIONE
            "scanners": {
                "wave": wave_api_key is not None,
                "pa11y": True,
                "axe": True, 
                "lighthouse": True
            }
        }
        
        if wave_api_key:
            payload["wave_api_key"] = wave_api_key
        
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        start_time = time.time()
        
        try:
            # Chiamata API per avviare scan
            response = self.session.post(
                f"{self.base_url}/api/v2/scan",
                json=payload,
                timeout=self.request_timeout
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"❌ API scan failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "execution_time": execution_time
                }
            
            # Parse response
            result = response.json()
            
            logger.info(f"✅ API scan completed in {execution_time:.2f}s")
            logger.info(f"Scan ID: {result.get('scan_id', 'N/A')}")
            
            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "payload_sent": payload
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ API scan timed out after {self.request_timeout}s")
            return {
                "success": False,
                "error": "Request timeout",
                "execution_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"❌ API scan failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def analyze_scan_result(self, result: dict, test_name: str) -> dict:
        """Analizza risultato scansione per verificare dati reali"""
        
        logger.info(f"🔍 Analyzing scan result for {test_name}")
        
        analysis = {
            "test_name": test_name,
            "api_success": result.get("success", False),
            "has_real_data": False,
            "scanner_results": {},
            "violations_found": 0,
            "accessibility_score": None,
            "compliance_level": None,
            "enterprise_mode": False
        }
        
        if not result.get("success"):
            analysis["error"] = result.get("error", "Unknown error")
            return analysis
        
        api_result = result.get("result", {})
        
        # Controlla se è enterprise mode
        analysis["enterprise_mode"] = api_result.get("enterprise_mode", False)
        
        # Analizza compliance data
        if "compliance_summary" in api_result:
            compliance = api_result["compliance_summary"]
            analysis["accessibility_score"] = compliance.get("overall_score")
            analysis["compliance_level"] = compliance.get("compliance_level")
            analysis["violations_found"] = compliance.get("total_violations", 0)
            
        # Analizza execution info per scanner
        if "execution_info" in api_result:
            execution = api_result["execution_info"]
            analysis["successful_scanners"] = execution.get("successful_scanners", 0)
            analysis["failed_scanners"] = execution.get("failed_scanners", 0)
            analysis["success_rate"] = execution.get("success_rate", 0)
        
        # Verifica dati reali - controlla se abbiamo violazioni > 0 o score < 100
        if analysis["violations_found"] > 0 or (analysis["accessibility_score"] and analysis["accessibility_score"] < 100):
            analysis["has_real_data"] = True
            logger.info(f"✅ REAL DATA DETECTED: {analysis['violations_found']} violations, score {analysis['accessibility_score']}")
        else:
            logger.warning(f"⚠️ Suspicious data: 0 violations, score {analysis['accessibility_score']} - might be simulated")
        
        # Controlla paths per report
        if "report_html_path" in api_result and api_result["report_html_path"]:
            analysis["has_html_report"] = True
        if "report_pdf_path" in api_result and api_result["report_pdf_path"]:
            analysis["has_pdf_report"] = True
            
        return analysis
    
    def download_scan_report(self, scan_id: str, base_out: str) -> bool:
        """Download report HTML per verifica contenuto"""
        
        try:
            # Prova a scaricare il report HTML
            report_url = f"{self.base_url}/api/scan/{scan_id}/report"
            response = self.session.get(report_url, timeout=30)
            
            if response.status_code == 200:
                # Salva report localmente
                report_path = Path(f"downloaded_report_{scan_id}.html")
                report_path.write_text(response.text, encoding="utf-8")
                logger.info(f"✅ Report downloaded: {report_path}")
                
                # Verifica contenuto per dati reali
                content = response.text
                real_data_indicators = [
                    "violazioni rilevate", "errori trovati", "problemi di accessibilità",
                    "WCAG", "contrast", "alt", "heading", "aria"
                ]
                
                indicators_found = sum(1 for indicator in real_data_indicators if indicator.lower() in content.lower())
                if indicators_found > 2:
                    logger.info(f"✅ Real data confirmed in report ({indicators_found} indicators)")
                    return True
                else:
                    logger.warning(f"⚠️ Limited real data indicators in report ({indicators_found})")
                    return False
            else:
                logger.error(f"❌ Failed to download report: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Report download failed: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Esegue test completo tramite API"""
        
        logger.info("🚀 ENTERPRISE API COMPREHENSIVE TEST")
        logger.info("=" * 80)
        
        # Test 1: Connettività
        if not self.test_api_connectivity():
            logger.error("❌ API connectivity failed - aborting tests")
            return False
        
        # Test 2: Scan completa tutti i 4 scanner con beinat.com
        logger.info("\n" + "="*50)
        logger.info("🧪 TEST 1: All 4 scanners - beinat.com")
        logger.info("="*50)
        
        test1_result = self.run_enterprise_scan_api(
            url="https://beinat.com",
            company_name="Test Enterprise All Scanners", 
            email="test@enterprise.com",
            wave_api_key="9u8c2c8z5746",  # Usa chiave fornita
            test_name="all_scanners_beinat"
        )
        
        test1_analysis = self.analyze_scan_result(test1_result, "all_scanners_beinat")
        self.test_results["tests"]["all_scanners_beinat"] = {
            "result": test1_result,
            "analysis": test1_analysis
        }
        
        # Test 3: Scan con 3 scanner (no WAVE) con governo.it
        logger.info("\n" + "="*50)
        logger.info("🧪 TEST 2: 3 scanners (no WAVE) - governo.it")
        logger.info("="*50)
        
        test2_result = self.run_enterprise_scan_api(
            url="https://governo.it",
            company_name="Test Three Scanners",
            email="test@threescanners.com",
            wave_api_key=None,  # No WAVE
            test_name="three_scanners_governo"
        )
        
        test2_analysis = self.analyze_scan_result(test2_result, "three_scanners_governo")
        self.test_results["tests"]["three_scanners_governo"] = {
            "result": test2_result,
            "analysis": test2_analysis
        }
        
        # Test 4: Scan con sito più complesso - repubblica.it
        logger.info("\n" + "="*50)
        logger.info("🧪 TEST 3: Complex site - repubblica.it")
        logger.info("="*50)
        
        test3_result = self.run_enterprise_scan_api(
            url="https://repubblica.it",
            company_name="Test Complex Site",
            email="test@complex.com",
            wave_api_key="9u8c2c8z5746",
            test_name="complex_site_repubblica"
        )
        
        test3_analysis = self.analyze_scan_result(test3_result, "complex_site_repubblica")
        self.test_results["tests"]["complex_site_repubblica"] = {
            "result": test3_result,
            "analysis": test3_analysis
        }
        
        # Analisi finale
        self.analyze_overall_results()
        
        # Salva report finale
        self.save_comprehensive_report()
        
        return True
    
    def analyze_overall_results(self):
        """Analisi risultati complessivi"""
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 ANALISI RISULTATI FINALI")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results["tests"])
        successful_tests = 0
        real_data_tests = 0
        enterprise_mode_tests = 0
        
        for test_name, test_data in self.test_results["tests"].items():
            analysis = test_data["analysis"]
            
            logger.info(f"\n📋 {test_name.upper()}:")
            logger.info(f"  Success: {analysis['api_success']}")
            logger.info(f"  Real Data: {analysis['has_real_data']}")
            logger.info(f"  Enterprise Mode: {analysis['enterprise_mode']}")
            logger.info(f"  Score: {analysis['accessibility_score']}")
            logger.info(f"  Violations: {analysis['violations_found']}")
            logger.info(f"  Compliance: {analysis['compliance_level']}")
            logger.info(f"  Successful Scanners: {analysis.get('successful_scanners', 'N/A')}")
            
            if analysis["api_success"]:
                successful_tests += 1
            if analysis["has_real_data"]:
                real_data_tests += 1
            if analysis["enterprise_mode"]:
                enterprise_mode_tests += 1
        
        # Statistiche finali
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        real_data_rate = (real_data_tests / total_tests * 100) if total_tests > 0 else 0
        enterprise_rate = (enterprise_mode_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"\n🎯 STATISTICHE FINALI:")
        logger.info(f"  Test totali: {total_tests}")
        logger.info(f"  Test riusciti: {successful_tests} ({success_rate:.1f}%)")
        logger.info(f"  Con dati reali: {real_data_tests} ({real_data_rate:.1f}%)")
        logger.info(f"  Enterprise mode: {enterprise_mode_tests} ({enterprise_rate:.1f}%)")
        
        # Determina status finale
        if successful_tests == total_tests and real_data_tests == total_tests:
            self.test_results["overall_status"] = "ALL_PASSED_REAL_DATA"
            logger.info("🏆 RISULTATO: TUTTI I TEST PASSATI CON DATI REALI!")
        elif successful_tests == total_tests:
            self.test_results["overall_status"] = "ALL_PASSED_CHECK_DATA"
            logger.info("⚠️ RISULTATO: Tutti i test passati - verificare qualità dati")
        elif successful_tests > 0:
            self.test_results["overall_status"] = "PARTIAL_SUCCESS"
            logger.info("🟡 RISULTATO: Successo parziale")
        else:
            self.test_results["overall_status"] = "ALL_FAILED"
            logger.info("❌ RISULTATO: Tutti i test falliti")
    
    def save_comprehensive_report(self):
        """Salva report dettagliato completo"""
        
        self.test_results["completed_at"] = datetime.now().isoformat()
        
        # Report JSON dettagliato
        with open("enterprise_api_test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Report summary leggibile
        with open("enterprise_api_test_summary.md", "w", encoding="utf-8") as f:
            f.write("# ENTERPRISE EAA SCANNER - API TEST RESULTS\n\n")
            f.write(f"**Started:** {self.test_results['started_at']}\n")
            f.write(f"**Completed:** {self.test_results['completed_at']}\n")
            f.write(f"**Base URL:** {self.test_results['base_url']}\n")
            f.write(f"**Overall Status:** {self.test_results['overall_status']}\n\n")
            
            f.write("## Test Results\n\n")
            
            for test_name, test_data in self.test_results["tests"].items():
                analysis = test_data["analysis"]
                f.write(f"### {test_name.upper()}\n\n")
                f.write(f"- **Success:** {analysis['api_success']}\n")
                f.write(f"- **Real Data:** {analysis['has_real_data']}\n")
                f.write(f"- **Enterprise Mode:** {analysis['enterprise_mode']}\n")
                f.write(f"- **Accessibility Score:** {analysis['accessibility_score']}\n")
                f.write(f"- **Violations Found:** {analysis['violations_found']}\n")
                f.write(f"- **Compliance Level:** {analysis['compliance_level']}\n")
                f.write(f"- **Successful Scanners:** {analysis.get('successful_scanners', 'N/A')}\n")
                f.write(f"- **Execution Time:** {test_data['result'].get('execution_time', 'N/A'):.2f}s\n\n")
                
                if not analysis["api_success"] and "error" in analysis:
                    f.write(f"- **Error:** {analysis['error']}\n\n")
        
        logger.info("💾 Report salvati:")
        logger.info("  - enterprise_api_test_results.json (completo)")
        logger.info("  - enterprise_api_test_summary.md (leggibile)")


def main():
    """Entry point principale"""
    
    print("🚀 ENTERPRISE EAA SCANNER - FINAL API TEST")
    print("=" * 80)
    print("Test finale tramite API Docker container:")
    print("- Tutti e 4 gli scanner (WAVE, Pa11y, Axe, Lighthouse)")
    print("- Solo dati REALI da siti web reali")
    print("- Algoritmo aggregazione enterprise")
    print("- Report dettagliato finale")
    print("=" * 80)
    print()
    
    # Chiedi conferma
    if input("Procedere con i test API finali? (y/n): ").lower() != 'y':
        print("Test annullato.")
        return
    
    # Esegui test
    tester = EnterpriseAPITester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n" + "=" * 80)
        print("🏁 TEST API COMPLETATO!")
        print("Controlla i file di report per i risultati dettagliati.")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ TEST API FALLITO!")
        print("Controlla i log per dettagli.")
        print("=" * 80)


if __name__ == "__main__":
    main()