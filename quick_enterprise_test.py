#!/usr/bin/env python3
"""
Quick test del sistema enterprise - verifica configurazione base
"""

import sys
import logging
from pathlib import Path

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test import dei moduli enterprise"""
    
    print("🔍 Testing imports...")
    
    try:
        from eaa_scanner.models.scanner_results import ScannerResult, AggregatedResults
        print("✅ Pydantic models imported")
    except ImportError as e:
        print(f"❌ Pydantic models failed: {e}")
        return False
    
    try:
        from eaa_scanner.processors.enterprise_normalizer import EnterpriseNormalizer
        print("✅ Enterprise normalizer imported")
    except ImportError as e:
        print(f"❌ Enterprise normalizer failed: {e}")
        return False
    
    try:
        from eaa_scanner.enterprise_core import EnterpriseScanOrchestrator
        print("✅ Enterprise core imported")
    except ImportError as e:
        print(f"❌ Enterprise core failed: {e}")
        return False
    
    try:
        from eaa_scanner.enterprise_charts import EnterpriseChartGenerator
        print("✅ Enterprise charts imported")
    except ImportError as e:
        print(f"❌ Enterprise charts failed: {e}")
        return False
    
    try:
        from eaa_scanner.enterprise_integration import FastAPIEnterpriseAdapter
        print("✅ Enterprise integration imported")
    except ImportError as e:
        print(f"❌ Enterprise integration failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test funzionalità base"""
    
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test normalizer creation
        from eaa_scanner.processors.enterprise_normalizer import EnterpriseNormalizer
        normalizer = EnterpriseNormalizer()
        print("✅ Enterprise normalizer created")
        
        # Test orchestrator creation
        from eaa_scanner.enterprise_core import EnterpriseScanOrchestrator
        orchestrator = EnterpriseScanOrchestrator()
        print("✅ Enterprise orchestrator created")
        
        # Test adapter creation
        from eaa_scanner.enterprise_integration import FastAPIEnterpriseAdapter
        adapter = FastAPIEnterpriseAdapter()
        print("✅ FastAPI adapter created")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_pydantic_validation():
    """Test Pydantic validation"""
    
    print("\n🔍 Testing Pydantic validation...")
    
    try:
        from eaa_scanner.models.scanner_results import (
            ScannerResult, ViolationInstance, ScannerType, SeverityLevel, ScanStatus
        )
        from datetime import datetime
        from decimal import Decimal
        
        # Test ViolationInstance
        violation = ViolationInstance(
            code="test-code",
            message="Test violation message",
            severity=SeverityLevel.HIGH,
            wcag_criterion="1.1.1"
        )
        print("✅ ViolationInstance validation passed")
        
        # Test ScannerResult
        scanner_result = ScannerResult(
            scanner=ScannerType.PA11Y,
            url="https://example.com",
            status=ScanStatus.SUCCESS,
            violations=[violation],
            accessibility_score=Decimal('85.5')
        )
        print("✅ ScannerResult validation passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic validation test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 QUICK ENTERPRISE SYSTEM TEST")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Imports
    if test_imports():
        success_count += 1
    
    # Test 2: Basic functionality
    if test_basic_functionality():
        success_count += 1
    
    # Test 3: Pydantic validation
    if test_pydantic_validation():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"🏁 RESULTS: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("✅ All tests passed! Enterprise system ready.")
        return 0
    else:
        print("❌ Some tests failed. Check configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())