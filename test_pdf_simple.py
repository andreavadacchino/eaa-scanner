#!/usr/bin/env python3
"""
Test semplificato per verificare la logica PDF senza dipendenze esterne
"""

from pathlib import Path
from eaa_scanner.pdf import get_pdf_engines_status, _determine_engines, _get_default_print_css

def test_pdf_logic():
    """Testa la logica PDF senza generazione effettiva"""
    print("🧪 Test Logica PDF (senza dipendenze esterne)")
    print("=" * 50)
    
    # Test 1: Status engine
    print("1️⃣ Test get_pdf_engines_status()...")
    status = get_pdf_engines_status()
    assert isinstance(status, dict)
    assert 'weasyprint' in status
    assert 'chrome' in status 
    assert 'wkhtmltopdf' in status
    print("✅ Status engine OK")
    
    # Test 2: Determinazione engine
    print("\n2️⃣ Test _determine_engines()...")
    
    # Auto mode (default)
    engines_auto = _determine_engines("auto")
    expected_auto = ["weasyprint", "chrome", "wkhtmltopdf"]
    assert engines_auto == expected_auto, f"Expected {expected_auto}, got {engines_auto}"
    print("✅ Auto mode OK")
    
    # Specific engines
    assert _determine_engines("weasyprint") == ["weasyprint"]
    assert _determine_engines("chrome") == ["chrome"] 
    assert _determine_engines("wkhtmltopdf") == ["wkhtmltopdf"]
    print("✅ Specific engines OK")
    
    # Test 3: CSS print
    print("\n3️⃣ Test _get_default_print_css()...")
    css = _get_default_print_css()
    assert isinstance(css, str)
    assert len(css) > 1000  # Should be substantial CSS
    assert "@page" in css
    assert "margin" in css
    assert "font-family" in css
    print(f"✅ CSS print OK ({len(css)} chars)")
    
    # Test 4: CSS content validation
    print("\n4️⃣ Test CSS content validation...")
    required_elements = [
        "@page",           # Page setup
        "@top-center",     # Header
        "@bottom-center",  # Footer  
        ".header",         # Report header
        ".score-section",  # Score cards
        ".issue-item",     # Issues
        ".compliance-badge", # Compliance status
        "page-break-inside: avoid", # Print optimization
        "Arial"            # Font specification
    ]
    
    for element in required_elements:
        assert element in css, f"Missing CSS element: {element}"
    
    print("✅ CSS content validation OK")
    
    print("\n" + "=" * 50)
    print("🎉 Tutti i test logici superati!")
    print("✨ Il sistema PDF è pronto per l'uso")
    print("\n📋 Note:")
    print("• Per uso reale, installare almeno un engine PDF")
    print("• WeasyPrint raccomandato: pip install weasyprint")
    print("• Chrome/Chromium supportati automaticamente")
    print("• Fallback chain: WeasyPrint → Chrome → wkhtmltopdf")
    
    return True

if __name__ == "__main__":
    test_pdf_logic()