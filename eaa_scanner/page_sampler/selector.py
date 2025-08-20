"""
Page Selector per selezione WCAG-EM compliant delle pagine
Implementa metodologia WCAG-EM per campionamento rappresentativo
"""

import logging
import random
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .page_categorizer import PageCategory, PageCategorizer
from .template_detector import TemplateDetector

logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Strategie di selezione pagine"""
    WCAG_EM = "wcag_em"  # Metodologia WCAG-EM standard
    QUICK = "quick"  # Selezione rapida essenziale
    COMPREHENSIVE = "comprehensive"  # Analisi completa
    CUSTOM = "custom"  # Selezione personalizzata


@dataclass
class SelectionConfig:
    """Configurazione per selezione pagine"""
    strategy: SelectionStrategy = SelectionStrategy.WCAG_EM
    max_pages: int = 10
    min_pages: int = 5
    include_all_critical: bool = True
    include_all_templates: bool = True
    random_sample_size: int = 2
    depth_limit: int = 3
    
    # Pesi per scoring
    priority_weight: float = 0.4
    importance_weight: float = 0.3
    template_weight: float = 0.2
    random_weight: float = 0.1


@dataclass  
class PageSelection:
    """Risultato selezione pagine"""
    selected_pages: List[Dict] = field(default_factory=list)
    strategy_used: SelectionStrategy = SelectionStrategy.WCAG_EM
    
    # Statistiche selezione
    total_available: int = 0
    total_selected: int = 0
    templates_covered: int = 0
    categories_covered: Set[PageCategory] = field(default_factory=set)
    
    # Breakdown per tipo
    structured_sample: List[Dict] = field(default_factory=list)
    random_sample: List[Dict] = field(default_factory=list)
    critical_pages: List[Dict] = field(default_factory=list)
    
    # Motivazioni selezione
    selection_reasons: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return {
            'selected_pages': self.selected_pages,
            'strategy': self.strategy_used.value,
            'statistics': {
                'total_available': self.total_available,
                'total_selected': self.total_selected,
                'templates_covered': self.templates_covered,
                'categories_covered': [c.value for c in self.categories_covered]
            },
            'breakdown': {
                'structured_sample': len(self.structured_sample),
                'random_sample': len(self.random_sample),
                'critical_pages': len(self.critical_pages)
            },
            'selection_reasons': self.selection_reasons
        }


class PageSelector:
    """
    Selettore di pagine WCAG-EM compliant
    """
    
    def __init__(self, config: Optional[SelectionConfig] = None):
        """
        Inizializza il selettore
        
        Args:
            config: Configurazione selezione
        """
        self.config = config or SelectionConfig()
        self.categorizer = PageCategorizer()
        self.template_detector = TemplateDetector()
    
    def select_pages(self, 
                    discovered_pages: List[Dict],
                    templates: Optional[Dict] = None) -> PageSelection:
        """
        Seleziona pagine per scansione secondo strategia
        
        Args:
            discovered_pages: Pagine scoperte dal crawler
            templates: Template identificati (opzionale)
            
        Returns:
            PageSelection con pagine selezionate
        """
        if not discovered_pages:
            return PageSelection(total_available=0)
        
        # Identifica template se non forniti
        if templates is None:
            templates = self.template_detector.detect_templates(discovered_pages)
        
        # Seleziona secondo strategia
        if self.config.strategy == SelectionStrategy.WCAG_EM:
            return self._select_wcag_em(discovered_pages, templates)
        elif self.config.strategy == SelectionStrategy.QUICK:
            return self._select_quick(discovered_pages, templates)
        elif self.config.strategy == SelectionStrategy.COMPREHENSIVE:
            return self._select_comprehensive(discovered_pages, templates)
        else:
            return self._select_custom(discovered_pages, templates)
    
    def _select_wcag_em(self, 
                        pages: List[Dict],
                        templates: Dict) -> PageSelection:
        """
        Selezione secondo metodologia WCAG-EM
        
        Metodologia:
        1. Pagine comuni (homepage, sitemap, contatti, etc.)
        2. Pagine rappresentative per template
        3. Processi completi (es. checkout)
        4. Campione casuale
        5. Pagine con funzionalità specifiche
        
        Args:
            pages: Pagine disponibili
            templates: Template identificati
            
        Returns:
            PageSelection
        """
        selection = PageSelection(
            strategy_used=SelectionStrategy.WCAG_EM,
            total_available=len(pages)
        )
        
        selected_urls = set()
        
        # 1. Pagine comuni obbligatorie
        common_pages = self._select_common_pages(pages)
        for page in common_pages:
            if page['url'] not in selected_urls:
                selection.structured_sample.append(page)
                selected_urls.add(page['url'])
                selection.selection_reasons[page['url']] = "Pagina comune WCAG-EM"
        
        # 2. Pagine rappresentative per template
        template_pages = self._select_template_representatives(templates)
        for page in template_pages:
            if page['url'] not in selected_urls and len(selection.selected_pages) < self.config.max_pages:
                selection.structured_sample.append(page)
                selected_urls.add(page['url'])
                selection.selection_reasons[page['url']] = f"Rappresentativa template {page.get('page_type', 'N/A')}"
        
        # 3. Processi completi critici
        process_pages = self._select_complete_processes(pages)
        for page in process_pages:
            if page['url'] not in selected_urls and len(selection.selected_pages) < self.config.max_pages:
                selection.critical_pages.append(page)
                selected_urls.add(page['url'])
                selection.selection_reasons[page['url']] = "Parte di processo critico"
        
        # 4. Campione casuale
        remaining_pages = [p for p in pages if p['url'] not in selected_urls]
        random_sample = self._select_random_sample(
            remaining_pages, 
            min(self.config.random_sample_size, self.config.max_pages - len(selected_urls))
        )
        for page in random_sample:
            if page['url'] not in selected_urls:
                selection.random_sample.append(page)
                selected_urls.add(page['url'])
                selection.selection_reasons[page['url']] = "Campione casuale WCAG-EM"
        
        # 5. Pagine con funzionalità specifiche
        special_pages = self._select_special_functionality_pages(pages)
        for page in special_pages:
            if page['url'] not in selected_urls and len(selection.selected_pages) < self.config.max_pages:
                selection.structured_sample.append(page)
                selected_urls.add(page['url'])
                selection.selection_reasons[page['url']] = "Funzionalità speciale"
        
        # Combina tutti i campioni
        selection.selected_pages = (
            selection.structured_sample + 
            selection.critical_pages + 
            selection.random_sample
        )[:self.config.max_pages]
        
        # Calcola statistiche
        selection.total_selected = len(selection.selected_pages)
        selection.templates_covered = len(set(
            p.get('template_id', 'unknown') 
            for p in selection.selected_pages
        ))
        
        for page in selection.selected_pages:
            category, _ = self.categorizer.categorize_page(page)
            selection.categories_covered.add(category)
        
        return selection
    
    def _select_quick(self, 
                     pages: List[Dict],
                     templates: Dict) -> PageSelection:
        """
        Selezione rapida essenziale
        
        Args:
            pages: Pagine disponibili
            templates: Template identificati
            
        Returns:
            PageSelection
        """
        selection = PageSelection(
            strategy_used=SelectionStrategy.QUICK,
            total_available=len(pages)
        )
        
        # Solo pagine critiche e homepage
        critical_categories = [
            PageCategory.HOMEPAGE,
            PageCategory.AUTHENTICATION,
            PageCategory.CHECKOUT,
            PageCategory.CONTACT,
            PageCategory.FORM
        ]
        
        selected_urls = set()
        
        for page in pages:
            if len(selection.selected_pages) >= min(5, self.config.max_pages):
                break
            
            category, _ = self.categorizer.categorize_page(page)
            if category in critical_categories and page['url'] not in selected_urls:
                selection.selected_pages.append(page)
                selected_urls.add(page['url'])
                selection.categories_covered.add(category)
                selection.selection_reasons[page['url']] = f"Categoria critica: {category.value}"
        
        selection.total_selected = len(selection.selected_pages)
        
        return selection
    
    def _select_comprehensive(self, 
                             pages: List[Dict],
                             templates: Dict) -> PageSelection:
        """
        Selezione completa per analisi approfondita
        
        Args:
            pages: Pagine disponibili
            templates: Template identificati
            
        Returns:
            PageSelection
        """
        selection = PageSelection(
            strategy_used=SelectionStrategy.COMPREHENSIVE,
            total_available=len(pages)
        )
        
        # Prendi almeno 2 pagine per template
        selected_urls = set()
        
        for template_id, template_info in templates.items():
            template_pages = template_info['pages']
            
            # Ordina per importanza
            sorted_pages = sorted(
                template_pages,
                key=lambda p: self.categorizer.calculate_page_importance(p),
                reverse=True
            )
            
            # Prendi le prime 2-3 per template
            pages_to_take = min(3, len(sorted_pages))
            for page in sorted_pages[:pages_to_take]:
                if len(selection.selected_pages) >= self.config.max_pages:
                    break
                
                if page['url'] not in selected_urls:
                    selection.selected_pages.append(page)
                    selected_urls.add(page['url'])
                    category, _ = self.categorizer.categorize_page(page)
                    selection.categories_covered.add(category)
                    selection.selection_reasons[page['url']] = f"Analisi completa template {template_id}"
        
        selection.total_selected = len(selection.selected_pages)
        selection.templates_covered = len(templates)
        
        return selection
    
    def _select_custom(self, 
                      pages: List[Dict],
                      templates: Dict) -> PageSelection:
        """
        Selezione personalizzata basata su scoring
        
        Args:
            pages: Pagine disponibili
            templates: Template identificati
            
        Returns:
            PageSelection
        """
        selection = PageSelection(
            strategy_used=SelectionStrategy.CUSTOM,
            total_available=len(pages)
        )
        
        # Calcola score per ogni pagina
        page_scores = []
        for page in pages:
            score = self._calculate_page_score(page, templates)
            page_scores.append((page, score))
        
        # Ordina per score
        page_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Seleziona top pages
        selected_urls = set()
        for page, score in page_scores[:self.config.max_pages]:
            if page['url'] not in selected_urls:
                selection.selected_pages.append(page)
                selected_urls.add(page['url'])
                category, _ = self.categorizer.categorize_page(page)
                selection.categories_covered.add(category)
                selection.selection_reasons[page['url']] = f"Score: {score:.2f}"
        
        selection.total_selected = len(selection.selected_pages)
        
        return selection
    
    def _select_common_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Seleziona pagine comuni richieste da WCAG-EM
        
        Args:
            pages: Pagine disponibili
            
        Returns:
            Lista pagine comuni
        """
        common_pages = []
        common_categories = [
            PageCategory.HOMEPAGE,
            PageCategory.CONTACT,
            PageCategory.NAVIGATION,
            PageCategory.LEGAL
        ]
        
        for category in common_categories:
            for page in pages:
                page_category, _ = self.categorizer.categorize_page(page)
                if page_category == category:
                    common_pages.append(page)
                    break  # Una per categoria
        
        return common_pages
    
    def _select_template_representatives(self, templates: Dict) -> List[Dict]:
        """
        Seleziona pagine rappresentative per template
        
        Args:
            templates: Template identificati
            
        Returns:
            Lista pagine rappresentative
        """
        representatives = []
        
        for template_id, template_info in templates.items():
            if template_info['page_count'] > 0:
                # Usa la pagina rappresentativa identificata dal template detector
                rep_url = template_info.get('representative_url')
                for page in template_info['pages']:
                    if page['url'] == rep_url:
                        representatives.append(page)
                        break
                else:
                    # Fallback: prendi la prima
                    representatives.append(template_info['pages'][0])
        
        return representatives
    
    def _select_complete_processes(self, pages: List[Dict]) -> List[Dict]:
        """
        Seleziona pagine che formano processi completi
        
        Args:
            pages: Pagine disponibili
            
        Returns:
            Lista pagine di processi
        """
        process_pages = []
        
        # Cerca processi comuni
        process_patterns = [
            ['login', 'dashboard'],
            ['cart', 'checkout', 'payment', 'confirmation'],
            ['search', 'results'],
            ['contact', 'thank']
        ]
        
        for pattern in process_patterns:
            pattern_pages = []
            for keyword in pattern:
                for page in pages:
                    if keyword in page['url'].lower():
                        pattern_pages.append(page)
                        break
            
            # Se trovato processo completo, aggiungilo
            if len(pattern_pages) == len(pattern):
                process_pages.extend(pattern_pages)
        
        return process_pages
    
    def _select_random_sample(self, pages: List[Dict], size: int) -> List[Dict]:
        """
        Seleziona campione casuale
        
        Args:
            pages: Pagine disponibili
            size: Dimensione campione
            
        Returns:
            Campione casuale
        """
        if len(pages) <= size:
            return pages
        
        return random.sample(pages, size)
    
    def _select_special_functionality_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Seleziona pagine con funzionalità speciali
        
        Args:
            pages: Pagine disponibili
            
        Returns:
            Pagine con funzionalità speciali
        """
        special_pages = []
        
        for page in pages:
            # Pagine con molti form
            if page.get('forms_count', 0) > 2:
                special_pages.append(page)
            # Pagine con video
            elif page.get('videos_count', 0) > 0:
                special_pages.append(page)
            # Pagine con molte immagini (gallerie)
            elif page.get('images_count', 0) > 10:
                special_pages.append(page)
        
        return special_pages[:3]  # Limita a 3
    
    def _calculate_page_score(self, page: Dict, templates: Dict) -> float:
        """
        Calcola score complessivo per una pagina
        
        Args:
            page: Pagina da valutare
            templates: Template identificati
            
        Returns:
            Score (0-100)
        """
        score = 0
        
        # Priority score
        priority = page.get('priority', 50)
        score += priority * self.config.priority_weight
        
        # Importance score
        importance = self.categorizer.calculate_page_importance(page)
        score += importance * self.config.importance_weight
        
        # Template uniqueness score
        template_score = 50  # Default
        for template_id, template_info in templates.items():
            if page in template_info['pages']:
                # Più unica = score più alto
                uniqueness = 100 / template_info['page_count']
                template_score = uniqueness
                break
        score += template_score * self.config.template_weight
        
        # Random factor
        score += random.randint(0, 100) * self.config.random_weight
        
        return score
    
    def validate_selection(self, selection: PageSelection) -> Tuple[bool, List[str]]:
        """
        Valida che la selezione sia WCAG-EM compliant
        
        Args:
            selection: Selezione da validare
            
        Returns:
            Tupla (valido, lista problemi)
        """
        issues = []
        
        # Check numero minimo pagine
        if selection.total_selected < self.config.min_pages:
            issues.append(f"Troppe poche pagine: {selection.total_selected} < {self.config.min_pages}")
        
        # Check presenza homepage
        has_homepage = any(
            cat == PageCategory.HOMEPAGE 
            for cat in selection.categories_covered
        )
        if not has_homepage:
            issues.append("Manca la homepage")
        
        # Check varietà template
        if selection.templates_covered < 2 and selection.total_available > 5:
            issues.append(f"Pochi template coperti: {selection.templates_covered}")
        
        # Check presenza form/interattività
        has_interactive = any(
            cat in [PageCategory.FORM, PageCategory.CONTACT, PageCategory.AUTHENTICATION]
            for cat in selection.categories_covered
        )
        if not has_interactive and selection.total_available > 3:
            issues.append("Mancano pagine interattive")
        
        return len(issues) == 0, issues