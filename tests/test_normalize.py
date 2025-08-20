"""
Test per il modulo di normalizzazione
"""
import unittest
from typing import Dict, Any, List

# Importa funzioni da testare
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from eaa_scanner.processors.normalize import (
    deduplicate_issues,
    categorize_by_pour,
    calculate_overall_score,
    determine_compliance_level,
    map_to_eaa_compliance,
    extract_wcag_from_tags,
    map_lighthouse_to_wcag,
    generate_recommendations
)


class TestNormalization(unittest.TestCase):
    """Test suite per la normalizzazione dei risultati scanner"""
    
    def test_deduplicate_issues(self):
        """Test deduplica issues con stesso code+wcag+source"""
        issues = [
            {"code": "alt_missing", "wcag_criteria": "1.1.1", "source": "WAVE", "count": 3},
            {"code": "alt_missing", "wcag_criteria": "1.1.1", "source": "WAVE", "count": 2},
            {"code": "contrast", "wcag_criteria": "1.4.3", "source": "WAVE", "count": 1},
            {"code": "alt_missing", "wcag_criteria": "1.1.1", "source": "Axe", "count": 1},
        ]
        
        result = deduplicate_issues(issues)
        
        # Dovrebbero esserci 3 issue uniche
        self.assertEqual(len(result), 3)
        
        # Il primo alt_missing WAVE dovrebbe avere count aggregato (3+2=5)
        wave_alt = next((i for i in result if i["code"] == "alt_missing" and i["source"] == "WAVE"), None)
        self.assertIsNotNone(wave_alt)
        self.assertEqual(wave_alt["count"], 5)
    
    def test_categorize_by_pour(self):
        """Test categorizzazione per principi WCAG (POUR)"""
        errors = [
            {"wcag_criteria": "1.1.1", "count": 2},  # Perceivable
            {"wcag_criteria": "1.4.3", "count": 1},  # Perceivable
            {"wcag_criteria": "2.1.1", "count": 3},  # Operable
            {"wcag_criteria": "3.1.1", "count": 1},  # Understandable
            {"wcag_criteria": "4.1.2", "count": 2},  # Robust
        ]
        warnings = [
            {"wcag_criteria": "1.3.1", "count": 1},  # Perceivable
            {"wcag_criteria": "2.4.4", "count": 2},  # Operable
        ]
        
        result = categorize_by_pour(errors, warnings)
        
        # Verifica conteggi per categoria
        self.assertEqual(result["perceivable"]["errors"], 3)  # 2+1
        self.assertEqual(result["perceivable"]["warnings"], 1)
        self.assertEqual(result["operable"]["errors"], 3)
        self.assertEqual(result["operable"]["warnings"], 2)
        self.assertEqual(result["understandable"]["errors"], 1)
        self.assertEqual(result["understandable"]["warnings"], 0)
        self.assertEqual(result["robust"]["errors"], 2)
        self.assertEqual(result["robust"]["warnings"], 0)
    
    def test_calculate_overall_score(self):
        """Test calcolo score complessivo con pesi per severità"""
        errors_high = [
            {"severity": "critical", "count": 1},  # 20 punti
            {"severity": "high", "count": 2},      # 15*2 = 30 punti
        ]
        warnings_low = [
            {"severity": "medium", "count": 2},    # 8*2 = 16 punti
            {"severity": "low", "count": 3},        # 3*3 = 9 punti
        ]
        
        # Totale penalità: 20 + 30 + 16 + 9 = 75
        # Score: 100 - 75 = 25
        score = calculate_overall_score(errors_high, warnings_low)
        self.assertEqual(score, 25)
        
        # Test con nessun errore
        score_perfect = calculate_overall_score([], [])
        self.assertEqual(score_perfect, 100)
        
        # Test con molti errori (score non può essere negativo)
        many_errors = [{"severity": "critical", "count": 10}] * 10
        score_zero = calculate_overall_score(many_errors, [])
        self.assertEqual(score_zero, 0)
    
    def test_determine_compliance_level(self):
        """Test determinazione livello di conformità"""
        # Con errori critici -> non_conforme
        errors_critical = [{"severity": "critical"}]
        level = determine_compliance_level(90, errors_critical)
        self.assertEqual(level, "non_conforme")
        
        # Score alto senza errori critici -> conforme
        level_good = determine_compliance_level(85, [])
        self.assertEqual(level_good, "conforme")
        
        # Score medio -> parzialmente_conforme
        level_partial = determine_compliance_level(70, [])
        self.assertEqual(level_partial, "parzialmente_conforme")
        
        # Score basso -> non_conforme
        level_bad = determine_compliance_level(50, [])
        self.assertEqual(level_bad, "non_conforme")
    
    def test_map_to_eaa_compliance(self):
        """Test mapping livelli di conformità IT->EN"""
        self.assertEqual(map_to_eaa_compliance("conforme"), "compliant")
        self.assertEqual(map_to_eaa_compliance("parzialmente_conforme"), "partially_compliant")
        self.assertEqual(map_to_eaa_compliance("non_conforme"), "non_compliant")
        self.assertEqual(map_to_eaa_compliance("altro"), "non_compliant")
    
    def test_extract_wcag_from_tags(self):
        """Test estrazione criterio WCAG da tag Axe-core"""
        tags = ["wcag143", "wcag2a", "section508"]
        wcag = extract_wcag_from_tags(tags)
        self.assertEqual(wcag, "1.4.3")
        
        tags_four_digit = ["wcag1411"]
        wcag_four = extract_wcag_from_tags(tags_four_digit)
        self.assertEqual(wcag_four, "1.4.11")
        
        tags_no_wcag = ["best-practice", "experimental"]
        wcag_none = extract_wcag_from_tags(tags_no_wcag)
        self.assertEqual(wcag_none, "")
    
    def test_map_lighthouse_to_wcag(self):
        """Test mapping audit ID Lighthouse -> WCAG"""
        self.assertEqual(map_lighthouse_to_wcag("color-contrast"), "1.4.3")
        self.assertEqual(map_lighthouse_to_wcag("image-alt"), "1.1.1")
        self.assertEqual(map_lighthouse_to_wcag("html-has-lang"), "3.1.1")
        self.assertEqual(map_lighthouse_to_wcag("bypass"), "2.4.1")
        self.assertEqual(map_lighthouse_to_wcag("unknown-audit"), "")
    
    def test_generate_recommendations(self):
        """Test generazione raccomandazioni basate su problemi"""
        errors_alt = [
            {"code": "alt_missing", "wcag_criteria": "1.1.1"},
            {"code": "alt_link_missing", "wcag_criteria": "1.1.1"},
        ]
        errors_contrast = [
            {"code": "contrast", "wcag_criteria": "1.4.3"},
        ]
        
        recommendations = generate_recommendations(errors_alt + errors_contrast, [])
        
        # Dovrebbero esserci raccomandazioni per alt text e contrasto
        self.assertTrue(len(recommendations) > 0)
        
        # Verifica che ci sia raccomandazione per testo alternativo
        alt_rec = next((r for r in recommendations if "alternativo" in r.get("title", "").lower()), None)
        self.assertIsNotNone(alt_rec)
        self.assertEqual(alt_rec["priority"], "alta")
        
        # Verifica che ci sia raccomandazione per contrasto
        contrast_rec = next((r for r in recommendations if "contrasto" in r.get("title", "").lower()), None)
        self.assertIsNotNone(contrast_rec)
        self.assertEqual(contrast_rec["priority"], "alta")
    
    def test_score_calculation_consistency(self):
        """Test che lo score sia coerente con severità e numero di problemi"""
        # Pochi errori di bassa severità
        few_low = [{"severity": "low", "count": 2}]
        score_few_low = calculate_overall_score(few_low, [])
        
        # Un errore critico
        one_critical = [{"severity": "critical", "count": 1}]
        score_one_critical = calculate_overall_score(one_critical, [])
        
        # Lo score con errori critici deve essere più basso
        self.assertLess(score_one_critical, score_few_low)
        
        # Molti errori di media severità
        many_medium = [{"severity": "medium", "count": 5}]
        score_many_medium = calculate_overall_score(many_medium, [])
        
        # Verifica ordine: few_low > many_medium > one_critical
        self.assertGreater(score_few_low, score_many_medium)
        self.assertGreater(score_many_medium, score_one_critical)


if __name__ == "__main__":
    unittest.main()