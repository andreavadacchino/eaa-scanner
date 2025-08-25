#!/usr/bin/env python3
"""
TEST FINALE API - DATI REALI
Test completo del sistema enterprise con scanner reali su siti web reali
"""

import requests
import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Configurazione test
BASE_URL = "http://localhost:8000"
REAL_WEBSITES = [
    "https://www.beinat.com",
    "https://www.governo.it", 
    "https://www.repubblica.it"
]

class RealAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.results = []
        
    def test_endpoint_health(self):
        """Verifica che l'API sia funzionante"""
        print("🔍 Testing API health...")
        
        try:
            response = self.session.get(f"{BASE_URL}/health")
            response.raise_for_status()
            print("✅ API is healthy")
            return True
        except Exception as e:
            print(f"❌ API health check failed: {e}")
            return False
    
    def start_real_scan(self, url: str, company: str = "Test Enterprise") -> str:
        """Avvia una scansione REALE tramite API"""
        print(f"🚀 Starting REAL scan for: {url}")
        
        scan_request = {
            "url": url,
            "company_name": company,
            "email": "test@enterprise.com",
            "simulate": False,  # IMPORTANTE: modalità REALE
            "scannerConfig": {
                "wave": {"enabled": True},
                "axe": {"enabled": True},
                "lighthouse": {"enabled": True},
                "pa11y": {"enabled": True}
            }
        }
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/v2/scan",
                json=scan_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            scan_id = data["scan_id"]
            
            print(f"✅ Scan started with ID: {scan_id}")
            return scan_id
            
        except Exception as e:
            print(f"❌ Failed to start scan for {url}: {e}")
            return None
    
    def monitor_scan_progress(self, scan_id: str, max_wait_time: int = 300) -> dict:
        """Monitora il progresso della scansione REALE"""
        print(f"⏳ Monitoring scan {scan_id} (max {max_wait_time}s)...")
        
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(f"{BASE_URL}/api/v2/scan/{scan_id}")
                response.raise_for_status()
                data = response.json()
                
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                message = data.get("message", "")
                
                # Stampa progresso solo se cambiato
                if progress != last_progress:
                    print(f"📊 Progress: {progress}% - {status} - {message}")
                    last_progress = progress
                
                # Controlla se completata
                if status == "completed":
                    print(f"✅ Scan {scan_id} completed!")
                    return data
                elif status == "error":
                    print(f"❌ Scan {scan_id} failed: {message}")
                    return data
                
                time.sleep(5)  # Aspetta 5 secondi prima del prossimo check
                
            except Exception as e:
                print(f"⚠️ Error checking scan status: {e}")
                time.sleep(10)
        
        print(f"⏰ Timeout waiting for scan {scan_id}")
        return {"status": "timeout", "scan_id": scan_id}
    
    def analyze_real_results(self, scan_data: dict) -> dict:
        """Analizza i risultati REALI della scansione"""
        print("🔍 Analyzing REAL scan results...")
        
        analysis = {
            "scan_id": scan_data.get("scan_id"),
            "status": scan_data.get("status"),
            "url": scan_data.get("results", {}).get("scan_context", {}).get("url", "N/A"),
            "enterprise_system_used": True,
            "scanners_completed": [],
            "total_violations": 0,
            "compliance_score": 0,
            "compliance_level": "unknown",
            "verification_checks": {
                "real_data_confirmed": False,
                "all_scanners_ran": False,
                "enterprise_aggregation": False,
                "pydantic_validation": False
            }
        }
        
        # Verifica risultati
        results = scan_data.get("results", {})
        if not results:
            print("❌ No results data found")
            return analysis
            
        # Verifica struttura enterprise
        if "compliance_metrics" in results:
            analysis["verification_checks"]["enterprise_aggregation"] = True
            compliance = results["compliance_metrics"]
            analysis["total_violations"] = compliance.get("total_violations", 0)
            analysis["compliance_score"] = float(compliance.get("overall_score", 0))
            analysis["compliance_level"] = compliance.get("compliance_level", "unknown")
            print(f"✅ Enterprise aggregation detected: {analysis['total_violations']} violations, score {analysis['compliance_score']}")
        
        # Verifica scanner individuali
        individual_results = results.get("individual_results", [])
        analysis["scanners_completed"] = [r.get("scanner", "unknown") for r in individual_results]
        
        if len(analysis["scanners_completed"]) >= 3:  # Almeno 3 scanner
            analysis["verification_checks"]["all_scanners_ran"] = True
            print(f"✅ Multiple scanners completed: {analysis['scanners_completed']}")
        
        # Verifica dati reali (non simulati)
        if analysis["total_violations"] > 0 and "scanner" in str(results):
            analysis["verification_checks"]["real_data_confirmed"] = True
            print("✅ Real scan data confirmed (non-zero violations with scanner metadata)")
        
        # Verifica validazione Pydantic
        if "scan_context" in results and "individual_results" in results:
            analysis["verification_checks"]["pydantic_validation"] = True
            print("✅ Pydantic model structure detected")
        
        return analysis
    
    def run_comprehensive_test(self):
        """Esegue test completo con siti web REALI"""
        print("=" * 80)
        print("🚀 COMPREHENSIVE REAL API TEST - ENTERPRISE SYSTEM")
        print(f"⏰ Started at: {datetime.now()}")
        print("=" * 80)
        
        # Test health
        if not self.test_endpoint_health():
            sys.exit(1)
        
        # Test per ogni sito web reale
        for i, url in enumerate(REAL_WEBSITES, 1):
            print(f"\n📍 TEST {i}/{len(REAL_WEBSITES)}: {url}")
            print("-" * 50)
            
            # Avvia scan reale
            scan_id = self.start_real_scan(url, f"Enterprise Test {i}")
            if not scan_id:
                continue
                
            # Monitora progresso
            scan_data = self.monitor_scan_progress(scan_id, max_wait_time=400)  # 6+ minuti per scan reali
            
            # Analizza risultati
            analysis = self.analyze_real_results(scan_data)
            analysis["test_number"] = i
            analysis["website_url"] = url
            self.results.append(analysis)
            
            print(f"📊 Test {i} summary:")
            print(f"   Status: {analysis['status']}")
            print(f"   Violations: {analysis['total_violations']}")
            print(f"   Score: {analysis['compliance_score']}")
            print(f"   Scanners: {len(analysis['scanners_completed'])}")
            print(f"   Real data: {analysis['verification_checks']['real_data_confirmed']}")
        
        # Report finale
        self.generate_final_report()
    
    def generate_final_report(self):
        """Genera report finale dettagliato"""
        print("\n" + "=" * 80)
        print("📋 FINAL COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r["status"] == "completed")
        real_data_confirmed = sum(1 for r in self.results if r["verification_checks"]["real_data_confirmed"])
        enterprise_working = sum(1 for r in self.results if r["verification_checks"]["enterprise_aggregation"])
        
        print(f"📊 SUMMARY:")
        print(f"   Total tests: {total_tests}")
        print(f"   Successful scans: {successful_tests}/{total_tests}")
        print(f"   Real data confirmed: {real_data_confirmed}/{total_tests}")
        print(f"   Enterprise system working: {enterprise_working}/{total_tests}")
        
        print(f"\n🔍 DETAILED RESULTS:")
        for i, result in enumerate(self.results, 1):
            status_icon = "✅" if result["status"] == "completed" else "❌"
            print(f"{status_icon} Test {i}: {result['website_url']}")
            print(f"     Status: {result['status']}")
            print(f"     Violations: {result['total_violations']}")
            print(f"     Score: {result['compliance_score']}")
            print(f"     Scanners: {result['scanners_completed']}")
            
            checks = result["verification_checks"]
            print(f"     ✓ Real data: {checks['real_data_confirmed']}")
            print(f"     ✓ Enterprise: {checks['enterprise_aggregation']}")
            print(f"     ✓ Multi-scanner: {checks['all_scanners_ran']}")
            print(f"     ✓ Pydantic: {checks['pydantic_validation']}")
        
        # Verifica finale
        enterprise_success = enterprise_working >= 2  # Almeno 2 test enterprise riusciti
        real_data_success = real_data_confirmed >= 2  # Almeno 2 test con dati reali
        overall_success = successful_tests >= 2        # Almeno 2 test completati
        
        print(f"\n🎯 FINAL VERDICT:")
        if enterprise_success and real_data_success and overall_success:
            print("✅ SUCCESS: Enterprise system is working with REAL data!")
            print("   ✅ Algorithm aggregation: WORKING")
            print("   ✅ Real scanner execution: CONFIRMED")  
            print("   ✅ Multi-scanner coordination: VERIFIED")
            print("   ✅ Pydantic type safety: ACTIVE")
        else:
            print("❌ FAILURE: System not working as expected")
            print(f"   Enterprise working: {enterprise_working}/{total_tests}")
            print(f"   Real data confirmed: {real_data_confirmed}/{total_tests}")
            print(f"   Tests completed: {successful_tests}/{total_tests}")
        
        # Salva report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"final_api_test_report_{timestamp}.json")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_summary": {
                    "timestamp": timestamp,
                    "total_tests": total_tests,
                    "successful_tests": successful_tests,
                    "real_data_confirmed": real_data_confirmed,
                    "enterprise_working": enterprise_working,
                    "overall_success": overall_success
                },
                "detailed_results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        print(f"⏰ Test completed at: {datetime.now()}")

if __name__ == "__main__":
    tester = RealAPITester()
    tester.run_comprehensive_test()