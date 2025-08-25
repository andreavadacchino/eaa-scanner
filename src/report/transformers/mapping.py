"""
Mapping deterministico scanner → WCAG/P.O.U.R./Impatto disabilità
"""

from typing import Dict, List, Tuple, Optional
from ..schema import POURPrinciple, DisabilityType, Severity


class WCAGMapper:
    """Mapper per convertire regole scanner in criteri WCAG e principi POUR"""
    
    # Mapping completo delle regole comuni degli scanner
    SCANNER_TO_WCAG_MAPPING: Dict[str, Dict] = {
        # Immagini e contenuti non testuali
        "img-alt": {
            "wcag": ["1.1.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Immagini senza testo alternativo"
        },
        "image-alt": {
            "wcag": ["1.1.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Immagini senza testo alternativo"
        },
        "alt-text": {
            "wcag": ["1.1.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Testo alternativo mancante"
        },
        
        # Contrasto colori
        "color-contrast": {
            "wcag": ["1.4.3", "1.4.11"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.IPOVISIONE, DisabilityType.DALTONISMO],
            "description": "Contrasto colore insufficiente"
        },
        "contrast": {
            "wcag": ["1.4.3"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.IPOVISIONE, DisabilityType.DALTONISMO],
            "description": "Rapporto di contrasto inadeguato"
        },
        
        # Struttura e semantica
        "heading-order": {
            "wcag": ["1.3.1", "2.4.6"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Ordine intestazioni non corretto"
        },
        "empty-heading": {
            "wcag": ["1.3.1", "2.4.6"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Intestazione vuota"
        },
        "landmark": {
            "wcag": ["1.3.1", "2.4.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Landmark ARIA mancanti o errati"
        },
        
        # Navigazione da tastiera
        "keyboard": {
            "wcag": ["2.1.1", "2.1.2"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.MOTORIE],
            "description": "Elemento non accessibile da tastiera"
        },
        "focus-visible": {
            "wcag": ["2.4.7"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.MOTORIE, DisabilityType.IPOVISIONE],
            "description": "Focus tastiera non visibile"
        },
        "tabindex": {
            "wcag": ["2.1.1", "2.4.3"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.MOTORIE],
            "description": "Ordine di tabulazione errato"
        },
        
        # Link e navigazione
        "link-name": {
            "wcag": ["2.4.4", "2.4.9"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.NON_VEDENTI, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Link senza testo descrittivo"
        },
        "empty-link": {
            "wcag": ["2.4.4"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Link vuoto"
        },
        "link-in-text-block": {
            "wcag": ["1.4.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.DALTONISMO],
            "description": "Link non distinguibile nel testo"
        },
        
        # Form e input
        "label": {
            "wcag": ["3.3.2", "1.3.1"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.NON_VEDENTI, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Campo form senza etichetta"
        },
        "form-field-multiple-labels": {
            "wcag": ["3.3.2"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Campo con etichette multiple"
        },
        "input-image-alt": {
            "wcag": ["1.1.1", "3.3.2"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Pulsante immagine senza alt"
        },
        "autocomplete": {
            "wcag": ["1.3.5"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.MOTORIE, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Autocomplete mancante o errato"
        },
        
        # Errori e feedback
        "error-message": {
            "wcag": ["3.3.1", "3.3.3"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.COGNITIVE_LINGUISTICHE, DisabilityType.NON_VEDENTI],
            "description": "Messaggio di errore non chiaro"
        },
        "required": {
            "wcag": ["3.3.2", "3.3.3"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Campo obbligatorio non indicato"
        },
        
        # ARIA e robustezza
        "aria-valid-attr": {
            "wcag": ["4.1.2"],
            "pour": POURPrinciple.ROBUSTO,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Attributi ARIA non validi"
        },
        "aria-roles": {
            "wcag": ["4.1.2"],
            "pour": POURPrinciple.ROBUSTO,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Ruoli ARIA errati"
        },
        "duplicate-id": {
            "wcag": ["4.1.1"],
            "pour": POURPrinciple.ROBUSTO,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "ID duplicati nel DOM"
        },
        "valid-html": {
            "wcag": ["4.1.1"],
            "pour": POURPrinciple.ROBUSTO,
            "impact": [],
            "description": "HTML non valido"
        },
        
        # Lingua e contenuti
        "html-lang": {
            "wcag": ["3.1.1"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.NON_VEDENTI, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Lingua pagina non specificata"
        },
        "lang": {
            "wcag": ["3.1.2"],
            "pour": POURPrinciple.COMPRENSIBILE,
            "impact": [DisabilityType.NON_VEDENTI, DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Lingua sezione non specificata"
        },
        
        # Multimedia
        "video-caption": {
            "wcag": ["1.2.2", "1.2.4"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.UDITIVA],
            "description": "Video senza sottotitoli"
        },
        "audio-caption": {
            "wcag": ["1.2.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.UDITIVA],
            "description": "Audio senza trascrizione"
        },
        
        # Tabelle
        "table-headers": {
            "wcag": ["1.3.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Tabella senza intestazioni"
        },
        "scope": {
            "wcag": ["1.3.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Scope tabella mancante"
        },
        
        # Liste
        "list": {
            "wcag": ["1.3.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Struttura lista non corretta"
        },
        "listitem": {
            "wcag": ["1.3.1"],
            "pour": POURPrinciple.PERCEPIBILE,
            "impact": [DisabilityType.NON_VEDENTI],
            "description": "Elemento lista fuori contesto"
        },
        
        # Tempo e movimento
        "meta-refresh": {
            "wcag": ["2.2.1", "2.2.4"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.COGNITIVE_LINGUISTICHE, DisabilityType.MOTORIE],
            "description": "Refresh automatico pagina"
        },
        "blink": {
            "wcag": ["2.2.2"],
            "pour": POURPrinciple.OPERABILE,
            "impact": [DisabilityType.COGNITIVE_LINGUISTICHE],
            "description": "Contenuto lampeggiante"
        }
    }
    
    @classmethod
    def map_scanner_rule(cls, rule_id: str, scanner: str = "") -> Dict:
        """
        Mappa una regola scanner ai criteri WCAG e principi POUR
        
        Args:
            rule_id: ID della regola scanner
            scanner: Nome dello scanner (axe, pa11y, wave, lighthouse)
            
        Returns:
            Dict con wcag, pour, impact, description
        """
        # Normalizza rule_id
        rule_id_lower = rule_id.lower().replace("_", "-")
        
        # Cerca mapping diretto
        if rule_id_lower in cls.SCANNER_TO_WCAG_MAPPING:
            return cls.SCANNER_TO_WCAG_MAPPING[rule_id_lower]
        
        # Cerca per pattern parziale
        for key, mapping in cls.SCANNER_TO_WCAG_MAPPING.items():
            if key in rule_id_lower or rule_id_lower in key:
                return mapping
        
        # Default mapping per regole non mappate
        return {
            "wcag": ["4.1.1"],  # Default: parsing/validazione
            "pour": POURPrinciple.ROBUSTO,
            "impact": [],
            "description": f"Problema di accessibilità: {rule_id}"
        }
    
    @classmethod
    def determine_severity(cls, rule_id: str, scanner: str = "") -> Severity:
        """
        Determina la severità basandosi sulla regola e scanner
        
        Args:
            rule_id: ID della regola scanner
            scanner: Nome dello scanner
            
        Returns:
            Severity level
        """
        rule_id_lower = rule_id.lower()
        
        # Regole critiche
        critical_patterns = [
            "keyboard", "focus-trap", "aria-hidden-body",
            "bypass", "frame-title", "html-lang-valid"
        ]
        for pattern in critical_patterns:
            if pattern in rule_id_lower:
                return Severity.CRITICO
        
        # Regole alta priorità
        high_patterns = [
            "img-alt", "image-alt", "label", "link-name",
            "button-name", "color-contrast", "heading-order"
        ]
        for pattern in high_patterns:
            if pattern in rule_id_lower:
                return Severity.ALTO
        
        # Regole media priorità
        medium_patterns = [
            "landmark", "region", "list", "definition",
            "aria", "role", "scope", "caption"
        ]
        for pattern in medium_patterns:
            if pattern in rule_id_lower:
                return Severity.MEDIO
        
        # Default: bassa priorità
        return Severity.BASSO
    
    @classmethod
    def get_pour_from_wcag(cls, wcag_criteria: List[str]) -> POURPrinciple:
        """
        Deriva il principio POUR dai criteri WCAG
        
        Args:
            wcag_criteria: Lista di criteri WCAG (es. ["1.1.1", "1.4.3"])
            
        Returns:
            Principio POUR dominante
        """
        if not wcag_criteria:
            return POURPrinciple.ROBUSTO
        
        # Prendi il primo criterio per determinare il principio
        first_criterion = wcag_criteria[0]
        first_digit = first_criterion.split(".")[0] if "." in first_criterion else "4"
        
        mapping = {
            "1": POURPrinciple.PERCEPIBILE,
            "2": POURPrinciple.OPERABILE,
            "3": POURPrinciple.COMPRENSIBILE,
            "4": POURPrinciple.ROBUSTO
        }
        
        return mapping.get(first_digit, POURPrinciple.ROBUSTO)