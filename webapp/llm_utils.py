"""
Utilità per operazioni LLM nell'interfaccia web.
Estende il sistema LLM esistente con funzionalità specifiche per webapp.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from eaa_scanner.llm_config import get_llm_manager, LLMManager

# Configura logger specifico
logger = logging.getLogger('webapp.llm_utils')
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class WebLLMManager:
    """Gestore LLM specializzato per webapp con cache e sessioni"""
    
    def __init__(self):
        self.session_cache = {}
        self.cost_cache = {}
        
    def validate_api_key_cached(self, api_key: str) -> Dict[str, Any]:
        """Valida API key con cache risultati"""
        cache_key = f"validation_{hash(api_key)}"
        
        # Controlla cache (valida per 10 minuti)
        if cache_key in self.session_cache:
            cached = self.session_cache[cache_key]
            if time.time() - cached['timestamp'] < 600:  # 10 min
                logger.info("Validation da cache")
                return cached['result']
        
        # Validazione reale
        try:
            manager = LLMManager(api_key=api_key)
            is_valid = manager.validate_api_key()
            
            result = {
                "valid": is_valid,
                "message": "API key valida" if is_valid else "API key non valida o scaduta",
                "timestamp": time.time()
            }
            
            # Cache risultato
            self.session_cache[cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Errore validazione API key: {e}")
            return {
                "valid": False,
                "message": f"Errore validazione: {str(e)}",
                "timestamp": time.time()
            }
    
    def estimate_costs_advanced(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Calcola stima costi con algoritmo migliorato"""
        model = config.get('model', 'gpt-4o')
        num_pages = config.get('num_pages', 1)
        sections = config.get('sections', [])
        complexity = config.get('complexity', 'medium')  # low, medium, high
        
        # Token estimates basati su analisi reale
        base_estimates = {
            'executive_summary': {'input': 600, 'output': 800},
            'technical_analysis': {'input': 1000, 'output': 1200},
            'recommendations': {'input': 800, 'output': 1000},
            'remediation_plan': {'input': 900, 'output': 1500},
            'accessibility_statement': {'input': 500, 'output': 600},
            'compliance_matrix': {'input': 700, 'output': 900},
            'user_impact_analysis': {'input': 600, 'output': 800}
        }
        
        # Fattori di complessità
        complexity_factors = {
            'low': 0.8,
            'medium': 1.0,
            'high': 1.3
        }
        
        complexity_factor = complexity_factors.get(complexity, 1.0)
        
        # Calcola token totali
        total_input_tokens = 0
        total_output_tokens = 0
        
        for section in sections:
            if section in base_estimates:
                base = base_estimates[section]
                total_input_tokens += base['input'] * complexity_factor
                total_output_tokens += base['output'] * complexity_factor
            else:
                # Fallback per sezioni sconosciute
                total_input_tokens += 600 * complexity_factor
                total_output_tokens += 800 * complexity_factor
        
        # Fattore pagine con sconto volumetrico progressivo
        if num_pages > 1:
            if num_pages <= 5:
                page_factor = num_pages * 0.9  # 10% sconto
            elif num_pages <= 20:
                page_factor = 5 * 0.9 + (num_pages - 5) * 0.8  # 20% sconto aggiuntivo
            else:
                page_factor = 5 * 0.9 + 15 * 0.8 + (num_pages - 20) * 0.7  # 30% sconto
            
            total_input_tokens *= page_factor
            total_output_tokens *= page_factor
        
        # Prezzi aggiornati (USD per 1K token)
        pricing = {
            'gpt-4o': {'input': 0.005, 'output': 0.015},
            'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03},
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
        }
        
        model_pricing = pricing.get(model, pricing['gpt-4o'])
        
        input_cost = (total_input_tokens / 1000) * model_pricing['input']
        output_cost = (total_output_tokens / 1000) * model_pricing['output']
        total_cost_usd = input_cost + output_cost
        
        # Stima tempo generazione (basata su esperienza reale)
        base_time_per_section = {
            'executive_summary': 45,  # secondi
            'technical_analysis': 90,
            'recommendations': 60,
            'remediation_plan': 120,
            'accessibility_statement': 30,
            'compliance_matrix': 75,
            'user_impact_analysis': 60
        }
        
        estimated_time = sum(base_time_per_section.get(s, 60) for s in sections)
        estimated_time *= complexity_factor
        
        if num_pages > 1:
            estimated_time *= min(num_pages * 0.7, num_pages)  # Parallellizzazione parziale
        
        return {
            "model": model,
            "estimated_input_tokens": int(total_input_tokens),
            "estimated_output_tokens": int(total_output_tokens),
            "estimated_cost_usd": round(total_cost_usd, 4),
            "estimated_cost_eur": round(total_cost_usd * 0.92, 4),
            "estimated_time_minutes": round(estimated_time / 60, 1),
            "breakdown": {
                "input_cost": round(input_cost, 4),
                "output_cost": round(output_cost, 4),
                "sections_count": len(sections),
                "pages_count": num_pages,
                "complexity": complexity,
                "volume_discount": max(0, num_pages - 1) * 0.1
            },
            "recommendations": self._get_cost_recommendations(total_cost_usd, model, sections)
        }
    
    def _get_cost_recommendations(self, cost_usd: float, model: str, sections: List[str]) -> List[str]:
        """Genera raccomandazioni per ottimizzare costi"""
        recommendations = []
        
        if cost_usd > 2.0:
            recommendations.append("💡 Considera l'uso di gpt-4o-mini per ridurre i costi del 90%")
        
        if cost_usd > 5.0:
            recommendations.append("⚠️ Costo elevato: valuta di selezionare solo le sezioni essenziali")
        
        if len(sections) > 4:
            recommendations.append("📝 Per la prima volta, prova con 2-3 sezioni per testare la qualità")
        
        if model == 'gpt-4-turbo-preview':
            recommendations.append("💰 gpt-4o è più economico e veloce di gpt-4-turbo-preview")
        
        if cost_usd < 0.5:
            recommendations.append("✅ Costo ottimale per test e valutazione")
        
        return recommendations
    
    def generate_enhanced_report(
        self,
        scan_data: Dict[str, Any],
        llm_config: Dict[str, Any],
        sections: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Genera report potenziato con LLM e tracking progresso"""
        try:
            api_key = llm_config.get('api_key')
            if not api_key:
                raise ValueError("API key mancante")
            
            manager = LLMManager(api_key=api_key)
            
            # Verifica API key prima di iniziare
            if not manager.validate_api_key():
                raise ValueError("API key non valida")
            
            results = {
                'sections': {},
                'metadata': {
                    'model_used': [],
                    'total_tokens': 0,
                    'generation_time': 0,
                    'errors': []
                }
            }
            
            start_time = time.time()
            total_sections = len(sections)
            
            for i, section in enumerate(sections):
                if progress_callback:
                    progress_callback(int((i / total_sections) * 90), f"Generazione {section}")
                
                section_start = time.time()
                
                try:
                    # Prepara dati sezione con più contesto
                    section_data = self._prepare_section_data(scan_data, section)
                    
                    # Genera contenuto
                    content = manager.generate_report_section(
                        section_type=section,
                        scan_data=section_data,
                        max_tokens=llm_config.get('max_tokens', 2000),
                        model_tier=llm_config.get('model_preference')
                    )
                    
                    if content:
                        results['sections'][section] = {
                            'content': content,
                            'generated_at': time.time(),
                            'generation_time': time.time() - section_start,
                            'tokens_estimated': manager.estimate_tokens(content)
                        }
                        
                        results['metadata']['total_tokens'] += manager.estimate_tokens(content)
                    else:
                        raise ValueError(f"Generazione fallita per sezione {section}")
                        
                except Exception as e:
                    logger.error(f"Errore generazione {section}: {e}")
                    results['metadata']['errors'].append({
                        'section': section,
                        'error': str(e),
                        'timestamp': time.time()
                    })
                    
                    # Genera fallback
                    results['sections'][section] = {
                        'content': self._generate_fallback_section(section, scan_data),
                        'generated_at': time.time(),
                        'is_fallback': True
                    }
            
            results['metadata']['generation_time'] = time.time() - start_time
            
            if progress_callback:
                progress_callback(100, "Finalizzazione report")
            
            return results
            
        except Exception as e:
            logger.error(f"Errore generazione report: {e}")
            raise
    
    def _prepare_section_data(self, scan_data: Dict[str, Any], section: str) -> Dict[str, Any]:
        """Prepara dati specifici per ogni sezione"""
        base_data = {
            'company_name': scan_data.get('company_name', 'Azienda'),
            'url': scan_data.get('url', ''),
            'scan_date': time.strftime('%Y-%m-%d'),
            'wcag_level': 'AA'
        }
        
        # Aggiungi dati specifici per sezione
        if section == 'executive_summary':
            base_data.update({
                'total_issues': scan_data.get('total_issues', 0),
                'critical_issues': scan_data.get('critical_issues', 0),
                'compliance_score': scan_data.get('compliance_score', 75)
            })
        elif section == 'technical_analysis':
            base_data.update({
                'scanners_used': scan_data.get('scanners_used', ['pa11y', 'axe-core']),
                'pages_scanned': scan_data.get('pages_scanned', 1),
                'scan_duration': scan_data.get('scan_duration', 0)
            })
        elif section == 'recommendations':
            base_data.update({
                'priority_issues': scan_data.get('priority_issues', []),
                'issue_categories': scan_data.get('issue_categories', {})
            })
        
        return base_data
    
    def _generate_fallback_section(self, section: str, scan_data: Dict[str, Any]) -> str:
        """Genera contenuto fallback per sezione"""
        company = scan_data.get('company_name', 'Azienda')
        
        fallbacks = {
            'executive_summary': f"""
## Executive Summary

L'analisi di accessibilità per {company} ha identificato diverse aree di miglioramento
per garantire la conformità agli standard WCAG 2.1 AA.

### Punti Chiave
- Sono stati identificati problemi che richiedono attenzione immediata
- La maggior parte delle barriere sono risolvibili con interventi mirati
- Si raccomanda un approccio graduale per l'implementazione delle correzioni

### Prossimi Passi
1. Revisione dettagliata delle raccomandazioni tecniche
2. Pianificazione degli interventi di correzione
3. Implementazione delle soluzioni prioritarie
""",
            'recommendations': f"""
## Raccomandazioni Tecniche

### Priorità Alta
- Correzione degli errori critici identificati dai scanner
- Implementazione di testi alternativi per immagini
- Miglioramento della navigazione da tastiera

### Priorità Media
- Ottimizzazione dei contrasti colore
- Strutturazione semantica dei contenuti
- Implementazione di skip links

### Priorità Bassa
- Miglioramenti di usabilità generale
- Ottimizzazioni per screen reader avanzati
""",
            'accessibility_statement': f"""
## Dichiarazione di Accessibilità

{company} si impegna a garantire l'accessibilità del proprio sito web
in conformità alla normativa vigente.

### Stato di Conformità
Lo stato di conformità è attualmente in fase di valutazione e miglioramento.

### Metodologia di Valutazione
La valutazione è stata condotta utilizzando strumenti automatizzati
e linee guida WCAG 2.1 livello AA.

### Data di Preparazione
Questa dichiarazione è stata preparata il {time.strftime('%d/%m/%Y')}.
"""
        }
        
        return fallbacks.get(section, f"Contenuto per sezione {section} non disponibile.")
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """Pulisce cache vecchie"""
        cutoff = time.time() - (max_age_hours * 3600)
        
        # Pulisci validation cache
        to_remove = []
        for key, data in self.session_cache.items():
            if data['timestamp'] < cutoff:
                to_remove.append(key)
        
        for key in to_remove:
            del self.session_cache[key]
        
        logger.info(f"Cache cleanup: rimossi {len(to_remove)} elementi")


# Singleton globale per webapp
_web_llm_manager = None

def get_web_llm_manager() -> WebLLMManager:
    """Factory per WebLLMManager singleton"""
    global _web_llm_manager
    if _web_llm_manager is None:
        _web_llm_manager = WebLLMManager()
    return _web_llm_manager


def estimate_processing_time(sections: List[str], pages: int, complexity: str = 'medium') -> Dict[str, Any]:
    """Stima tempo di elaborazione per UI"""
    base_times = {
        'executive_summary': 30,
        'technical_analysis': 60,
        'recommendations': 45,
        'remediation_plan': 90,
        'accessibility_statement': 20
    }
    
    complexity_multipliers = {
        'low': 0.7,
        'medium': 1.0,
        'high': 1.4
    }
    
    base_time = sum(base_times.get(s, 40) for s in sections)
    total_time = base_time * complexity_multipliers.get(complexity, 1.0)
    
    if pages > 1:
        total_time *= min(pages * 0.8, pages)  # Sconto parallelismo
    
    return {
        'estimated_seconds': int(total_time),
        'estimated_minutes': round(total_time / 60, 1),
        'sections_count': len(sections),
        'complexity': complexity,
        'pages': pages
    }