"""
Validatori per report di accessibilità
Garantisce conformità e coerenza dei contenuti
"""

import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


class NoDateValidator:
    """Validatore per garantire assenza di date/timeline nei report"""
    
    # Pattern per individuare date e riferimenti temporali
    DATE_PATTERNS = [
        # Date esplicite
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 01/01/2024, 1-1-24
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',     # 2024-01-01
        r'\d{1,2}\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{2,4}',
        r'(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\.?\s+\d{2,4}',
        
        # Timeline e deadline
        r'entro\s+(il\s+)?\d+\s+(giorni|settimane|mesi)',
        r'deadline',
        r'scadenza',
        r'data\s+di\s+(consegna|completamento|inizio|fine)',
        r'timeline',
        r'roadmap\s+temporale',
        r'pianificazione\s+temporale',
        r'milestone\s+\d+',
        
        # Riferimenti temporali specifici
        r'\d+\s+(giorni|settimane|mesi|anni)\s+(fa|prima)',
        r'(prossimi|prossime)\s+\d+\s+(giorni|settimane|mesi)',
        r'Q[1-4]\s+\d{4}',  # Q1 2024
        r'trimestre\s+\d+',
        r'semestre\s+\d+',
        
        # Tempi di implementazione
        r'tempo\s+stimato',
        r'durata\s+prevista',
        r'effort\s+stimato',
        r'\d+\s+(ore|giorni|settimane)\s+uomo',
        r'man-days?',
        r'person-days?',
    ]
    
    # Pattern permessi (da escludere dal check)
    ALLOWED_PATTERNS = [
        r'WCAG\s+2\.\d',  # WCAG 2.1, 2.2
        r'ISO\s+\d+',     # ISO 30071
        r'EN\s+\d+',      # EN 301 549
        r'tempo\s+di\s+caricamento',  # Performance metrics
        r'tempo\s+di\s+risposta',
        r'\d+ms',         # Millisecondi per performance
        r'\d+s\s+\(performance\)',
    ]
    
    @classmethod
    def validate_content(cls, content: str) -> Tuple[bool, List[str]]:
        """
        Valida contenuto per assenza di date/timeline
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_violations)
        """
        violations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Skip se è un pattern permesso
            if any(re.search(pattern, line_lower) for pattern in cls.ALLOWED_PATTERNS):
                continue
            
            # Cerca violazioni
            for pattern in cls.DATE_PATTERNS:
                matches = re.finditer(pattern, line_lower)
                for match in matches:
                    violations.append(
                        f"Linea {line_num}: '{match.group()}' - Pattern: {pattern}"
                    )
        
        return len(violations) == 0, violations
    
    @classmethod
    def validate_file(cls, filepath: Path) -> Dict[str, any]:
        """
        Valida un file per conformità no-date
        
        Returns:
            Dict con risultati validazione
        """
        if not filepath.exists():
            return {
                'valid': False,
                'error': f'File non trovato: {filepath}',
                'violations': []
            }
        
        content = filepath.read_text(encoding='utf-8')
        is_valid, violations = cls.validate_content(content)
        
        return {
            'valid': is_valid,
            'file': str(filepath),
            'violations': violations,
            'total_violations': len(violations)
        }
    
    @classmethod
    def generate_report(cls, validation_results: List[Dict]) -> str:
        """Genera report di validazione no-date"""
        
        report = []
        report.append("=" * 60)
        report.append("VALIDAZIONE NO-DATE/TIMELINE")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        total_files = len(validation_results)
        valid_files = sum(1 for r in validation_results if r['valid'])
        total_violations = sum(r.get('total_violations', 0) for r in validation_results)
        
        report.append(f"File analizzati: {total_files}")
        report.append(f"File validi: {valid_files}")
        report.append(f"File con violazioni: {total_files - valid_files}")
        report.append(f"Totale violazioni: {total_violations}")
        report.append("")
        
        if total_violations > 0:
            report.append("DETTAGLIO VIOLAZIONI:")
            report.append("-" * 40)
            
            for result in validation_results:
                if not result['valid'] and 'violations' in result:
                    report.append(f"\nFile: {result.get('file', 'N/A')}")
                    report.append(f"Violazioni: {result.get('total_violations', 0)}")
                    
                    for violation in result['violations'][:10]:  # Max 10 per file
                        report.append(f"  - {violation}")
                    
                    if result['total_violations'] > 10:
                        report.append(f"  ... e altre {result['total_violations'] - 10} violazioni")
        else:
            report.append("✅ NESSUNA VIOLAZIONE TROVATA")
            report.append("Tutti i file sono conformi al requisito no-date/timeline")
        
        report.append("")
        report.append("=" * 60)
        
        return '\n'.join(report)


class MethodologyValidator:
    """Validatore per coerenza metodologia e baseline"""
    
    REQUIRED_ELEMENTS = {
        'baseline': {
            'keywords': ['baseline', 'metodologia', 'automatica', 'automatic'],
            'required': True,
            'description': 'Definizione del baseline di valutazione'
        },
        'manual_tests': {
            'keywords': ['test manuali', 'verifiche manuali', 'manual testing'],
            'required': False,
            'description': 'Riferimento a test manuali come complemento'
        },
        'continuous_process': {
            'keywords': ['processo continuo', 'continuous', 'CI/CD', 'monitoraggio'],
            'required': True,
            'description': 'Processo di conformità continua'
        },
        'declaration': {
            'keywords': ['dichiarazione', 'declaration', 'statement'],
            'required': True,
            'description': 'Dichiarazione di accessibilità'
        },
        'feedback_channels': {
            'keywords': ['feedback', 'segnalazioni', 'contatti', 'supporto'],
            'required': True,
            'description': 'Canali di feedback e supporto'
        },
        'wcag_reference': {
            'keywords': ['WCAG 2.1', 'WCAG 2.2', 'Web Content Accessibility Guidelines'],
            'required': True,
            'description': 'Riferimento esplicito alle WCAG'
        },
        'pour_principles': {
            'keywords': ['percepibile', 'operabile', 'comprensibile', 'robusto', 'P.O.U.R.'],
            'required': True,
            'description': 'Principi P.O.U.R. delle WCAG'
        },
        'disability_impact': {
            'keywords': ['disabilità', 'impatto', 'utenti con', 'non vedenti', 'ipovisione'],
            'required': True,
            'description': 'Analisi impatto su disabilità'
        }
    }
    
    @classmethod
    def validate_content(cls, content: str) -> Tuple[bool, Dict[str, bool], List[str]]:
        """
        Valida contenuto per coerenza metodologia
        
        Returns:
            Tuple[bool, Dict[str, bool], List[str]]: (is_valid, elements_found, missing_elements)
        """
        content_lower = content.lower()
        elements_found = {}
        missing_elements = []
        
        for element_id, element_spec in cls.REQUIRED_ELEMENTS.items():
            found = any(keyword in content_lower for keyword in element_spec['keywords'])
            elements_found[element_id] = found
            
            if element_spec['required'] and not found:
                missing_elements.append(
                    f"{element_spec['description']} (cercato: {', '.join(element_spec['keywords'])})"
                )
        
        is_valid = len(missing_elements) == 0
        
        return is_valid, elements_found, missing_elements
    
    @classmethod
    def check_consistency(cls, content: str) -> Dict[str, any]:
        """
        Verifica coerenza interna del documento
        
        Returns:
            Dict con risultati check coerenza
        """
        issues = []
        
        # Check 1: Se menziona "audit-grade", deve includere test manuali
        if 'audit-grade' in content.lower() and 'test manuali' not in content.lower():
            issues.append("Incoerenza: Menziona 'audit-grade' ma non specifica test manuali")
        
        # Check 2: Se dichiara conformità, deve avere processo continuo
        if 'conforme' in content.lower() and 'processo continuo' not in content.lower():
            issues.append("Incoerenza: Dichiara conformità senza processo continuo")
        
        # Check 3: Se menziona EAA, deve includere EN 301 549
        if 'european accessibility act' in content.lower() and 'EN 301 549' not in content:
            issues.append("Incoerenza: Riferimento EAA senza EN 301 549")
        
        # Check 4: Se include remediation, deve avere priorità
        if 'remediation' in content.lower() or 'correzione' in content.lower():
            if not any(word in content.lower() for word in ['priorità', 'critico', 'alto', 'medio', 'basso']):
                issues.append("Incoerenza: Piano remediation senza priorità definite")
        
        return {
            'consistent': len(issues) == 0,
            'issues': issues
        }
    
    @classmethod
    def generate_report(cls, validation_results: List[Dict]) -> str:
        """Genera report di validazione metodologia"""
        
        report = []
        report.append("=" * 60)
        report.append("VALIDAZIONE COERENZA METODOLOGIA")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        for result in validation_results:
            report.append(f"File: {result.get('file', 'N/A')}")
            report.append("-" * 40)
            
            if 'error' in result:
                report.append(f"❌ ERRORE: {result['error']}")
            else:
                # Elementi trovati
                report.append("Elementi metodologia:")
                for element_id, found in result['elements_found'].items():
                    element_spec = cls.REQUIRED_ELEMENTS[element_id]
                    status = "✅" if found else "❌"
                    required = "(RICHIESTO)" if element_spec['required'] else "(opzionale)"
                    report.append(f"  {status} {element_spec['description']} {required}")
                
                # Elementi mancanti
                if result['missing_elements']:
                    report.append("\n⚠️ ELEMENTI MANCANTI:")
                    for missing in result['missing_elements']:
                        report.append(f"  - {missing}")
                
                # Check coerenza
                if 'consistency' in result:
                    consistency = result['consistency']
                    if consistency['issues']:
                        report.append("\n⚠️ PROBLEMI DI COERENZA:")
                        for issue in consistency['issues']:
                            report.append(f"  - {issue}")
                    else:
                        report.append("\n✅ Documento coerente")
                
                # Risultato finale
                report.append(f"\nRISULTATO: {'✅ VALIDO' if result['valid'] else '❌ NON VALIDO'}")
            
            report.append("")
        
        report.append("=" * 60)
        
        return '\n'.join(report)


class ComplianceValidator:
    """Validatore principale per conformità report"""
    
    @classmethod
    def validate_report(cls, report_path: Path) -> Dict[str, any]:
        """
        Esegue validazione completa del report
        
        Returns:
            Dict con tutti i risultati di validazione
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'report': str(report_path),
            'validations': {}
        }
        
        if not report_path.exists():
            results['error'] = f'Report non trovato: {report_path}'
            return results
        
        content = report_path.read_text(encoding='utf-8')
        
        # Validazione no-date
        no_date_valid, date_violations = NoDateValidator.validate_content(content)
        results['validations']['no_date'] = {
            'valid': no_date_valid,
            'violations': date_violations,
            'total_violations': len(date_violations)
        }
        
        # Validazione metodologia
        method_valid, elements_found, missing_elements = MethodologyValidator.validate_content(content)
        consistency = MethodologyValidator.check_consistency(content)
        
        results['validations']['methodology'] = {
            'valid': method_valid and consistency['consistent'],
            'elements_found': elements_found,
            'missing_elements': missing_elements,
            'consistency': consistency
        }
        
        # Risultato complessivo
        results['valid'] = (
            results['validations']['no_date']['valid'] and
            results['validations']['methodology']['valid']
        )
        
        return results
    
    @classmethod
    def save_validation_reports(cls, results: Dict[str, any], output_dir: Path = Path('./docs')):
        """Salva report di validazione su file"""
        
        output_dir.mkdir(exist_ok=True)
        
        # Report no-date
        no_date_report = NoDateValidator.generate_report([results['validations']['no_date']])
        (output_dir / 'check-no-dates.txt').write_text(no_date_report, encoding='utf-8')
        
        # Report metodologia
        method_report = MethodologyValidator.generate_report([results['validations']['methodology']])
        (output_dir / 'check-methodology.txt').write_text(method_report, encoding='utf-8')
        
        # Report complessivo
        summary = []
        summary.append("=" * 60)
        summary.append("VALIDAZIONE COMPLIANCE REPORT")
        summary.append("=" * 60)
        summary.append(f"Report: {results['report']}")
        summary.append(f"Timestamp: {results['timestamp']}")
        summary.append("")
        summary.append(f"✅ No-Date Validation: {'PASSED' if results['validations']['no_date']['valid'] else 'FAILED'}")
        summary.append(f"✅ Methodology Validation: {'PASSED' if results['validations']['methodology']['valid'] else 'FAILED'}")
        summary.append("")
        summary.append(f"RISULTATO FINALE: {'✅ CONFORME' if results['valid'] else '❌ NON CONFORME'}")
        summary.append("=" * 60)
        
        (output_dir / 'validation-summary.txt').write_text('\n'.join(summary), encoding='utf-8')
        
        return {
            'no_date_report': str(output_dir / 'check-no-dates.txt'),
            'methodology_report': str(output_dir / 'check-methodology.txt'),
            'summary_report': str(output_dir / 'validation-summary.txt')
        }


# Funzione di utilità per validazione rapida
def validate_report_file(filepath: str) -> bool:
    """
    Valida rapidamente un report
    
    Args:
        filepath: Path al file da validare
        
    Returns:
        bool: True se valido, False altrimenti
    """
    report_path = Path(filepath)
    results = ComplianceValidator.validate_report(report_path)
    
    # Salva report di validazione
    ComplianceValidator.save_validation_reports(results)
    
    return results.get('valid', False)