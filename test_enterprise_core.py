#!/usr/bin/env python3
"""
Test core sistema enterprise - senza dipendenze matplotlib
Test principale per verificare funzionamento normalizer e Pydantic models
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_enterprise_normalizer():
    """Test completo del normalizer enterprise con dati reali simulati"""
    
    print("🧪 Testing Enterprise Normalizer...")
    
    try:
        from eaa_scanner.processors.enterprise_normalizer import EnterpriseNormalizer
        
        # Crea normalizer
        normalizer = EnterpriseNormalizer()
        print("✅ Normalizer created")
        
        # Simula dati scanner come quelli reali che abbiamo ottenuto
        mock_pa11y_data = {
            "issues": [
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                    "message": "Img element missing alt attribute. Add an alt attribute.",
                    "type": "error",
                    "selector": "img",
                    "context": "<img src=\"logo.png\">"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18",
                    "message": "Check contrast. Ensure sufficient color contrast.", 
                    "type": "warning",
                    "selector": ".text",
                    "context": "<span class=\"text\">Low contrast text</span>"
                }
            ]
        }
        
        mock_axe_data = {
            "violations": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "description": "Elements must have sufficient color contrast",
                    "help": "Ensure elements have sufficient color contrast",
                    "nodes": [{}, {}],  # 2 nodi affetti
                    "tags": ["cat.color", "wcag2aa", "wcag143"]
                },
                {
                    "id": "image-alt",
                    "impact": "critical", 
                    "description": "Images must have alternate text",
                    "help": "Images must have alternate text",
                    "nodes": [{}],  # 1 nodo affetto
                    "tags": ["cat.text-alternatives", "wcag2a", "wcag111"]
                }
            ]
        }
        
        mock_lighthouse_data = {
            "categories": {
                "accessibility": {
                    "score": 0.78  # 78%
                }
            },
            "audits": {
                "color-contrast": {
                    "score": 0.5,
                    "title": "Background and foreground colors have a sufficient contrast ratio",
                    "details": {
                        "items": [{"node": {"selector": "span"}}]
                    }
                },
                "image-alt": {
                    "score": 0,
                    "title": "Image elements have [alt] attributes", 
                    "details": {
                        "items": [{"node": {"selector": "img"}}, {"node": {"selector": "img"}}]
                    }
                }
            }
        }
        
        mock_wave_data = {
            "errors": [
                {
                    "code": "alt_missing",
                    "description": "Missing alternative text",
                    "selector": "img",
                    "wcag_criteria": "1.1.1"
                }
            ],
            "warnings": [
                {
                    "code": "contrast",
                    "description": "Very low contrast",
                    "selector": ".low-contrast", 
                    "wcag_criteria": "1.4.3"
                }
            ],
            "score": 72
        }
        
        # Testa normalizzazione
        result = normalizer.normalize_all_enterprise(
            url="https://test-example.com",
            company_name="Test Enterprise",
            email="test@example.com",
            scan_id="test-123",
            wave=mock_wave_data,
            pa11y=mock_pa11y_data,
            axe=mock_axe_data,
            lighthouse=mock_lighthouse_data
        )
        
        print("✅ Normalization completed")
        
        # Verifica risultato
        print(f"  Scanner riusciti: {len(result.successful_scanners)}")
        print(f"  Score generale: {result.compliance_metrics.overall_score}")
        print(f"  Compliance level: {result.compliance_metrics.compliance_level}")
        print(f"  Totale violazioni: {result.compliance_metrics.total_violations}")
        
        # Verifica che abbiamo dati validati
        assert len(result.individual_results) > 0, "Nessun risultato individuale"
        assert result.compliance_metrics.overall_score > 0, "Score non calcolato"
        assert result.compliance_metrics.total_violations > 0, "Violazioni non aggregate"
        
        print("✅ All validations passed")
        return True
        
    except Exception as e:
        print(f"❌ Enterprise normalizer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pydantic_models_comprehensive():
    """Test completo dei Pydantic models"""
    
    print("\n🔍 Testing Pydantic Models Comprehensive...")
    
    try:
        from eaa_scanner.models.scanner_results import (
            ScannerResult, ViolationInstance, AggregatedResults, ComplianceMetrics,
            ScannerMetadata, ScanContext, SeverityLevel, ScannerType, ScanStatus
        )
        
        # Test 1: ViolationInstance con tutti i campi
        violation1 = ViolationInstance(
            code="test-violation-1",
            message="Test violation with all fields",
            severity=SeverityLevel.CRITICAL,
            wcag_criterion="1.1.1",
            element="img[src='test.jpg']",
            context="<img src='test.jpg' />",
            line=42,
            column=15
        )
        
        violation2 = ViolationInstance(
            code="test-violation-2",
            message="Test violation minimal",
            severity=SeverityLevel.MEDIUM,
            wcag_criterion="1.4.3"
        )
        
        print("✅ ViolationInstance models created")
        
        # Test 2: ScannerMetadata
        metadata = ScannerMetadata(
            scanner_type=ScannerType.PA11Y,
            version="6.2.3",
            execution_time=15.5,
            memory_usage=128,
            exit_code=0,
            command_used="pa11y --standard WCAG2AA https://example.com"
        )
        
        print("✅ ScannerMetadata created")
        
        # Test 3: ScannerResult con auto-validation
        scanner_result = ScannerResult(
            scanner=ScannerType.PA11Y,
            url="https://example.com",
            status=ScanStatus.SUCCESS,
            violations=[violation1, violation2],
            accessibility_score=Decimal('78.5'),
            metadata=metadata
        )
        
        # Verifica auto-validazione conteggi
        assert scanner_result.total_violations == 2, f"Expected 2 violations, got {scanner_result.total_violations}"
        assert scanner_result.critical_count == 1, f"Expected 1 critical, got {scanner_result.critical_count}"
        assert scanner_result.medium_count == 1, f"Expected 1 medium, got {scanner_result.medium_count}"
        
        print("✅ ScannerResult with auto-validation passed")
        
        # Test 4: ComplianceMetrics
        compliance = ComplianceMetrics(
            overall_score=Decimal('78.5'),
            compliance_level="parzialmente_conforme",
            total_violations=5,
            critical_violations=1,
            high_violations=2,
            medium_violations=1,
            low_violations=1,
            confidence_level=Decimal('85.0')
        )
        
        print("✅ ComplianceMetrics created")
        
        # Test 5: ScanContext
        scan_context = ScanContext(
            scan_id="test-scan-123",
            company_name="Test Company",
            email="test@company.com",
            scan_type="real",
            requested_scanners=[ScannerType.PA11Y, ScannerType.AXE],
            timeout_seconds=60
        )
        
        print("✅ ScanContext created")
        
        # Test 6: AggregatedResults completo
        aggregated = AggregatedResults(
            scan_context=scan_context,
            individual_results=[scanner_result],
            compliance_metrics=compliance
        )
        
        # Verifica auto-validazione
        assert len(aggregated.successful_scanners) == 1, "Expected 1 successful scanner"
        assert ScannerType.PA11Y in aggregated.successful_scanners, "Pa11y should be in successful scanners"
        
        print("✅ AggregatedResults with auto-validation passed")
        
        # Test 7: Serializzazione JSON
        json_data = aggregated.model_dump()
        assert isinstance(json_data, dict), "Should serialize to dict"
        assert "scan_context" in json_data, "Should contain scan_context"
        assert "compliance_metrics" in json_data, "Should contain compliance_metrics"
        
        print("✅ JSON serialization passed")
        
        # Test 8: Proprietà calcolate
        success_rate = aggregated.success_rate
        assert success_rate == Decimal('100.00'), f"Expected 100% success rate, got {success_rate}"
        
        violations_pa11y = aggregated.get_violations_by_scanner(ScannerType.PA11Y)
        assert len(violations_pa11y) == 2, f"Expected 2 violations for Pa11y, got {len(violations_pa11y)}"
        
        score_pa11y = aggregated.get_scanner_score(ScannerType.PA11Y)
        assert score_pa11y == Decimal('78.5'), f"Expected score 78.5, got {score_pa11y}"
        
        print("✅ Calculated properties passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic models test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_null_value_handling():
    """Test gestione null values robusta"""
    
    print("\n🧪 Testing Null Value Handling...")
    
    try:
        from eaa_scanner.processors.enterprise_normalizer import EnterpriseNormalizer
        
        normalizer = EnterpriseNormalizer()
        
        # Test con tutti i dati nulli
        result_all_null = normalizer.normalize_all_enterprise(
            url="https://test-null.com",
            company_name="Test Null Values",
            email="test@null.com",
            scan_id="null-test-123",
            wave=None,
            pa11y=None,
            axe=None,
            lighthouse=None
        )
        
        # Dovrebbe fallire perché non abbiamo nessun risultato
        assert False, "Should have raised ValueError for no scanner results"
        
    except ValueError as e:
        if "Nessuno scanner ha prodotto risultati validi" in str(e):
            print("✅ Null handling: correctly rejected all-null input")
        else:
            print(f"❌ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected exception: {e}")
        return False
    
    try:
        # Test con dati parzialmente nulli
        partial_null_data = {
            "issues": []  # Pa11y senza violazioni
        }
        
        result_partial = normalizer.normalize_all_enterprise(
            url="https://test-partial.com",
            company_name="Test Partial Null",
            email="test@partial.com", 
            scan_id="partial-test-123",
            wave=None,  # NULL
            pa11y=partial_null_data,  # Dati ma vuoti
            axe=None,  # NULL
            lighthouse=None  # NULL
        )
        
        # Dovrebbe funzionare con almeno un scanner
        assert len(result_partial.individual_results) == 1, "Expected 1 scanner result"
        assert result_partial.compliance_metrics.total_violations == 0, "Expected 0 violations"
        
        print("✅ Null handling: correctly processed partial null input")
        return True
        
    except Exception as e:
        print(f"❌ Partial null test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 ENTERPRISE CORE SYSTEM TEST")
    print("=" * 60)
    print("Testing the core enterprise functionality without matplotlib dependencies")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Enterprise Normalizer
    if test_enterprise_normalizer():
        success_count += 1
    
    # Test 2: Pydantic Models
    if test_pydantic_models_comprehensive():
        success_count += 1
    
    # Test 3: Null Value Handling  
    if test_null_value_handling():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"🏁 RESULTS: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("✅ All core tests passed! Enterprise system is working correctly.")
        print("📝 The mathematical null-value errors have been resolved.")
        print("🎯 System is ready for full integration with FastAPI.")
        return 0
    else:
        print("❌ Some core tests failed. Check implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())