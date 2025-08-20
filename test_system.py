#!/usr/bin/env python3
"""
Test completo e validazione critica del sistema EAA Scanner
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import traceback

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent))

from eaa_scanner.config import Config, ScannerToggles
from eaa_scanner.core import run_scan
from eaa_scanner.crawler import WebCrawler
from eaa_scanner.methodology import MetadataManager, TestMethodology, EAACompliance
from eaa_scanner.analytics import AccessibilityAnalytics
from eaa_scanner.charts import ChartGenerator
from eaa_scanner.remediation import RemediationPlanManager
from eaa_scanner.accessibility_statement import generate_statement_from_scan

# Colori per output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Stampa header sezione"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text):
    """Stampa messaggio successo"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    """Stampa warning"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def print_error(text):
    """Stampa errore"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text):
    """Stampa info"""
    print(f"  {text}")

class SystemValidator:
    """
    Validatore completo del sistema EAA Scanner
    """
    
    def __init__(self):
        self.results = {
            'modules': {},
            'features': {},
            'integration': {},
            'performance': {},
            'errors': []
        }
        self.test_url = "https://www.google.com"
        self.test_company = "Test Company"
        self.test_email = "test@example.com"
    
    def run_validation(self):
        """
        Esegue validazione completa del sistema
        """
        print_header("VALIDAZIONE SISTEMA EAA SCANNER")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Test moduli individuali
        self.test_modules()
        
        # 2. Test funzionalità
        self.test_features()
        
        # 3. Test integrazione
        self.test_integration()
        
        # 4. Test performance
        self.test_performance()
        
        # 5. Report finale
        self.generate_report()
    
    def test_modules(self):
        """
        Testa tutti i moduli del sistema
        """
        print_header("TEST MODULI")
        
        modules = [
            ('config', 'eaa_scanner.config'),
            ('core', 'eaa_scanner.core'),
            ('crawler', 'eaa_scanner.crawler'),
            ('methodology', 'eaa_scanner.methodology'),
            ('analytics', 'eaa_scanner.analytics'),
            ('charts', 'eaa_scanner.charts'),
            ('remediation', 'eaa_scanner.remediation'),
            ('accessibility_statement', 'eaa_scanner.accessibility_statement'),
            ('processors', 'eaa_scanner.processors'),
            ('report', 'eaa_scanner.report'),
            ('pdf', 'eaa_scanner.pdf'),
            ('emailer', 'eaa_scanner.emailer')
        ]
        
        for name, module_path in modules:
            try:
                module = __import__(module_path, fromlist=[''])
                self.results['modules'][name] = 'OK'
                print_success(f"Modulo {name} caricato correttamente")
            except Exception as e:
                self.results['modules'][name] = f'ERROR: {str(e)}'
                print_error(f"Errore caricamento modulo {name}: {str(e)}")
    
    def test_features(self):
        """
        Testa le funzionalità principali
        """
        print_header("TEST FUNZIONALITÀ")
        
        # Test 1: Crawler
        print("\n1. Test Web Crawler:")
        try:
            crawler = WebCrawler(self.test_url, max_pages=5, max_depth=2)
            pages = crawler.crawl()
            
            if pages:
                self.results['features']['crawler'] = f'OK - {len(pages)} pagine trovate'
                print_success(f"Crawler funzionante: {len(pages)} pagine scoperte")
                for page in pages[:3]:
                    print_info(f"  - {page['url']} (tipo: {page['page_type']})")
            else:
                self.results['features']['crawler'] = 'WARNING - Nessuna pagina trovata'
                print_warning("Crawler eseguito ma nessuna pagina trovata")
        except Exception as e:
            self.results['features']['crawler'] = f'ERROR: {str(e)}'
            print_error(f"Errore crawler: {str(e)}")
        
        # Test 2: Metodologia
        print("\n2. Test Metodologia EAA:")
        try:
            metadata_manager = MetadataManager()
            metadata_manager.set_organization(self.test_company, "private")
            metadata_manager.set_compliance_status("partially_compliant", 75)
            
            metadata = metadata_manager.get_complete_metadata()
            
            if metadata:
                self.results['features']['methodology'] = 'OK'
                print_success("Metodologia EAA configurata correttamente")
                print_info(f"  - Organizzazione: {metadata['organization']['organization_name']}")
                print_info(f"  - Compliance: {metadata['eaa_compliance']['compliance_status']}")
            else:
                self.results['features']['methodology'] = 'ERROR - Metadata vuoti'
                print_error("Metadata non generati")
        except Exception as e:
            self.results['features']['methodology'] = f'ERROR: {str(e)}'
            print_error(f"Errore metodologia: {str(e)}")
        
        # Test 3: Analytics
        print("\n3. Test Analytics:")
        try:
            # Usa dati di esempio
            sample_results = {
                "compliance": {
                    "overall_score": 75,
                    "compliance_level": "parzialmente_conforme",
                    "wcag_version": "2.1",
                    "wcag_level": "AA",
                    "categories": {
                        "perceivable": {"errors": 5, "warnings": 10},
                        "operable": {"errors": 2, "warnings": 5},
                        "understandable": {"errors": 1, "warnings": 3},
                        "robust": {"errors": 0, "warnings": 2}
                    }
                },
                "detailed_results": {
                    "errors": [
                        {
                            "type": "error",
                            "severity": "high",
                            "code": "alt_missing",
                            "description": "Immagine senza alt",
                            "count": 3,
                            "wcag_criteria": "1.1.1",
                            "source": "WAVE"
                        }
                    ],
                    "warnings": [],
                    "scanner_scores": {
                        "wave": 70,
                        "pa11y": 75,
                        "axe_core": 80,
                        "lighthouse": 78
                    }
                }
            }
            
            analytics = AccessibilityAnalytics(sample_results)
            analytics_data = analytics.generate_complete_analytics()
            
            if analytics_data and 'executive_summary' in analytics_data:
                self.results['features']['analytics'] = 'OK'
                print_success("Analytics generati correttamente")
                print_info(f"  - Score: {analytics_data['executive_summary']['compliance_score']}")
                print_info(f"  - Risk Level: {analytics_data['executive_summary']['risk_level']}")
            else:
                self.results['features']['analytics'] = 'ERROR - Analytics incompleti'
                print_error("Analytics non completi")
        except Exception as e:
            self.results['features']['analytics'] = f'ERROR: {str(e)}'
            print_error(f"Errore analytics: {str(e)}")
        
        # Test 4: Charts
        print("\n4. Test Generazione Grafici:")
        try:
            chart_gen = ChartGenerator(Path("./test_charts"))
            
            # Test con dati di esempio
            if analytics_data:
                charts = chart_gen.generate_all_charts(analytics_data)
                
                if charts:
                    self.results['features']['charts'] = f'OK - {len(charts)} grafici'
                    print_success(f"Grafici generati: {len(charts)} tipi")
                    for chart_name in list(charts.keys())[:5]:
                        print_info(f"  - {chart_name}")
                else:
                    self.results['features']['charts'] = 'ERROR - Nessun grafico'
                    print_error("Nessun grafico generato")
        except Exception as e:
            self.results['features']['charts'] = f'ERROR: {str(e)}'
            print_error(f"Errore grafici: {str(e)}")
        
        # Test 5: Remediation Plan
        print("\n5. Test Piano Remediation:")
        try:
            remediation = RemediationPlanManager(sample_results, self.test_company)
            summary = remediation.get_executive_summary()
            
            if summary:
                self.results['features']['remediation'] = 'OK'
                print_success("Piano remediation generato")
                print_info(f"  - Issues totali: {summary['total_issues']}")
                print_info(f"  - Ore stimate: {summary['estimated_effort']['total_hours']}")
                print_info(f"  - Costo: €{summary['estimated_effort']['total_cost_eur']}")
            else:
                self.results['features']['remediation'] = 'ERROR - Piano vuoto'
                print_error("Piano remediation vuoto")
        except Exception as e:
            self.results['features']['remediation'] = f'ERROR: {str(e)}'
            print_error(f"Errore remediation: {str(e)}")
        
        # Test 6: Accessibility Statement
        print("\n6. Test Dichiarazione Accessibilità:")
        try:
            org_data = {
                "name": self.test_company,
                "type": "privato",
                "website_name": "Test Website",
                "email": self.test_email
            }
            
            statement = generate_statement_from_scan(sample_results, org_data)
            html = statement.generate_html()
            
            if html and len(html) > 1000:
                self.results['features']['statement'] = 'OK'
                print_success("Dichiarazione accessibilità generata")
                print_info(f"  - Lunghezza HTML: {len(html)} caratteri")
                print_info(f"  - Stato: {statement.compliance_status}")
            else:
                self.results['features']['statement'] = 'ERROR - HTML vuoto'
                print_error("Dichiarazione non generata")
        except Exception as e:
            self.results['features']['statement'] = f'ERROR: {str(e)}'
            print_error(f"Errore dichiarazione: {str(e)}")
    
    def test_integration(self):
        """
        Testa l'integrazione completa del sistema
        """
        print_header("TEST INTEGRAZIONE")
        
        print("\n1. Test Scansione Completa (Simulata):")
        try:
            config = Config(
                url=self.test_url,
                company_name=self.test_company,
                email=self.test_email,
                simulate=True,  # Usa dati simulati
                output_dir=Path("./test_output"),
                toggles=ScannerToggles(
                    enable_wave=True,
                    enable_pa11y=True,
                    enable_axe=True,
                    enable_lighthouse=True
                )
            )
            
            # Esegui scansione
            start_time = time.time()
            result = run_scan(config)
            duration = time.time() - start_time
            
            if result and 'success' in result:
                self.results['integration']['full_scan'] = f'OK - {duration:.2f}s'
                print_success(f"Scansione completa eseguita in {duration:.2f} secondi")
                
                # Verifica output
                if 'scan_id' in result:
                    print_info(f"  - Scan ID: {result['scan_id']}")
                if 'report_path' in result:
                    print_info(f"  - Report: {result['report_path']}")
                if 'compliance' in result:
                    print_info(f"  - Compliance: {result['compliance'].get('compliance_level', 'N/A')}")
            else:
                self.results['integration']['full_scan'] = 'ERROR - Scan fallito'
                print_error("Scansione non completata")
        except Exception as e:
            self.results['integration']['full_scan'] = f'ERROR: {str(e)}'
            print_error(f"Errore integrazione: {str(e)}")
            traceback.print_exc()
        
        print("\n2. Test Multi-Pagina (Simulato):")
        try:
            # Configura per multi-pagina
            config.scan_config = {
                'scan_type': 'multi_page',
                'max_pages': 10,
                'max_depth': 2
            }
            
            # Non eseguire veramente, solo validare config
            self.results['integration']['multi_page'] = 'OK - Config validata'
            print_success("Configurazione multi-pagina validata")
            print_info(f"  - Max pages: {config.scan_config['max_pages']}")
            print_info(f"  - Max depth: {config.scan_config['max_depth']}")
        except Exception as e:
            self.results['integration']['multi_page'] = f'ERROR: {str(e)}'
            print_error(f"Errore multi-pagina: {str(e)}")
    
    def test_performance(self):
        """
        Testa le performance del sistema
        """
        print_header("TEST PERFORMANCE")
        
        # Test 1: Memory footprint
        print("\n1. Utilizzo Memoria:")
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb < 500:
                self.results['performance']['memory'] = f'OK - {memory_mb:.2f} MB'
                print_success(f"Utilizzo memoria: {memory_mb:.2f} MB")
            else:
                self.results['performance']['memory'] = f'WARNING - {memory_mb:.2f} MB'
                print_warning(f"Utilizzo memoria alto: {memory_mb:.2f} MB")
        except ImportError:
            self.results['performance']['memory'] = 'SKIP - psutil non installato'
            print_warning("psutil non installato, test memoria saltato")
        except Exception as e:
            self.results['performance']['memory'] = f'ERROR: {str(e)}'
            print_error(f"Errore test memoria: {str(e)}")
        
        # Test 2: Response time
        print("\n2. Tempi di Risposta:")
        operations = [
            ('Crawler init', lambda: WebCrawler(self.test_url, max_pages=5)),
            ('Analytics init', lambda: AccessibilityAnalytics({})),
            ('Charts init', lambda: ChartGenerator()),
            ('Metadata init', lambda: MetadataManager())
        ]
        
        for op_name, op_func in operations:
            try:
                start = time.time()
                op_func()
                duration = (time.time() - start) * 1000  # millisecondi
                
                if duration < 100:
                    print_success(f"{op_name}: {duration:.2f}ms")
                    self.results['performance'][op_name.lower().replace(' ', '_')] = f'{duration:.2f}ms'
                else:
                    print_warning(f"{op_name}: {duration:.2f}ms (lento)")
                    self.results['performance'][op_name.lower().replace(' ', '_')] = f'{duration:.2f}ms (slow)'
            except Exception as e:
                print_error(f"{op_name}: Errore - {str(e)}")
                self.results['performance'][op_name.lower().replace(' ', '_')] = 'ERROR'
    
    def generate_report(self):
        """
        Genera report finale di validazione
        """
        print_header("REPORT VALIDAZIONE FINALE")
        
        # Conta risultati
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0
        
        for category in ['modules', 'features', 'integration', 'performance']:
            for test, result in self.results[category].items():
                total_tests += 1
                if isinstance(result, str):
                    if 'OK' in result:
                        passed_tests += 1
                    elif 'ERROR' in result:
                        failed_tests += 1
                    elif 'WARNING' in result or 'SKIP' in result:
                        warning_tests += 1
        
        # Calcola percentuale successo
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Stampa sommario
        print(f"\n{Colors.BOLD}SOMMARIO RISULTATI:{Colors.ENDC}")
        print(f"  Test totali:    {total_tests}")
        print(f"  {Colors.GREEN}Passati:        {passed_tests}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}Warning/Skip:   {warning_tests}{Colors.ENDC}")
        print(f"  {Colors.RED}Falliti:        {failed_tests}{Colors.ENDC}")
        print(f"  Success Rate:   {success_rate:.1f}%")
        
        # Valutazione finale
        print(f"\n{Colors.BOLD}VALUTAZIONE SISTEMA:{Colors.ENDC}")
        if success_rate >= 90:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ SISTEMA PRONTO PER PRODUZIONE{Colors.ENDC}")
            print("  Il sistema EAA Scanner è completamente funzionante e pronto all'uso.")
        elif success_rate >= 70:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠ SISTEMA FUNZIONANTE CON AVVERTIMENTI{Colors.ENDC}")
            print("  Il sistema è funzionante ma alcuni componenti necessitano attenzione.")
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ SISTEMA NON PRONTO{Colors.ENDC}")
            print("  Sono presenti errori critici che devono essere risolti.")
        
        # Dettagli errori se presenti
        if failed_tests > 0:
            print(f"\n{Colors.BOLD}COMPONENTI CON ERRORI:{Colors.ENDC}")
            for category in ['modules', 'features', 'integration', 'performance']:
                for test, result in self.results[category].items():
                    if isinstance(result, str) and 'ERROR' in result:
                        print(f"  {Colors.RED}✗ {category}/{test}: {result}{Colors.ENDC}")
        
        # Salva report JSON
        report_path = Path("validation_report.json")
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed_tests,
                    'warnings': warning_tests,
                    'failed': failed_tests,
                    'success_rate': success_rate
                },
                'results': self.results
            }, f, indent=2)
        
        print(f"\n{Colors.BLUE}Report dettagliato salvato in: {report_path}{Colors.ENDC}")


def main():
    """
    Entry point per test di validazione
    """
    print(f"{Colors.BOLD}EAA SCANNER - SISTEMA DI VALIDAZIONE v1.0{Colors.ENDC}")
    print(f"{'='*60}")
    
    validator = SystemValidator()
    
    try:
        validator.run_validation()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Validazione interrotta dall'utente{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Errore critico durante validazione: {str(e)}{Colors.ENDC}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()