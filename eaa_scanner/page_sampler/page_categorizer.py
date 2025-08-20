"""
Page Categorizer per classificazione intelligente delle pagine
Categorizza pagine per tipo e importanza per l'accessibilità
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class PageCategory(Enum):
    """Categorie di pagine per priorità accessibilità"""
    HOMEPAGE = "homepage"
    AUTHENTICATION = "authentication"
    CHECKOUT = "checkout"
    CONTACT = "contact"
    FORM = "form"
    SEARCH = "search"
    PRODUCT = "product"
    ARTICLE = "article"
    NAVIGATION = "navigation"
    MEDIA = "media"
    LEGAL = "legal"
    ABOUT = "about"
    GENERAL = "general"


@dataclass
class CategoryInfo:
    """Informazioni sulla categoria"""
    category: PageCategory
    priority: int  # 0-100, più alto = più importante
    icon: str
    description: str
    wcag_relevance: List[str] = field(default_factory=list)
    testing_focus: List[str] = field(default_factory=list)


class PageCategorizer:
    """
    Categorizza pagine per tipo e importanza accessibilità
    """
    
    def __init__(self):
        """Inizializza il categorizer con definizioni categorie"""
        self.categories = self._init_categories()
        self.url_patterns = self._init_url_patterns()
        self.content_patterns = self._init_content_patterns()
    
    def _init_categories(self) -> Dict[PageCategory, CategoryInfo]:
        """Inizializza definizioni categorie"""
        return {
            PageCategory.HOMEPAGE: CategoryInfo(
                category=PageCategory.HOMEPAGE,
                priority=100,
                icon="🏠",
                description="Pagina principale del sito",
                wcag_relevance=["1.1.1", "2.4.2", "2.4.6", "3.1.1"],
                testing_focus=["navigazione", "struttura", "landmark"]
            ),
            PageCategory.AUTHENTICATION: CategoryInfo(
                category=PageCategory.AUTHENTICATION,
                priority=95,
                icon="🔐",
                description="Login, registrazione, autenticazione",
                wcag_relevance=["1.3.1", "2.1.1", "3.3.1", "3.3.2", "4.1.2"],
                testing_focus=["form", "validazione", "errori", "keyboard"]
            ),
            PageCategory.CHECKOUT: CategoryInfo(
                category=PageCategory.CHECKOUT,
                priority=90,
                icon="🛒",
                description="Carrello e processo di acquisto",
                wcag_relevance=["1.3.1", "2.2.1", "3.3.1", "3.3.3", "3.3.4"],
                testing_focus=["form multi-step", "session", "errori"]
            ),
            PageCategory.CONTACT: CategoryInfo(
                category=PageCategory.CONTACT,
                priority=85,
                icon="📧",
                description="Form di contatto e informazioni",
                wcag_relevance=["1.3.1", "3.3.1", "3.3.2", "4.1.2"],
                testing_focus=["form", "label", "validazione"]
            ),
            PageCategory.FORM: CategoryInfo(
                category=PageCategory.FORM,
                priority=80,
                icon="📝",
                description="Moduli e form generici",
                wcag_relevance=["1.3.1", "2.1.1", "3.3.1", "3.3.2", "4.1.2"],
                testing_focus=["input", "label", "fieldset", "errori"]
            ),
            PageCategory.SEARCH: CategoryInfo(
                category=PageCategory.SEARCH,
                priority=75,
                icon="🔍",
                description="Ricerca e risultati",
                wcag_relevance=["1.3.1", "2.4.3", "3.3.1", "4.1.3"],
                testing_focus=["form ricerca", "risultati", "filtri"]
            ),
            PageCategory.PRODUCT: CategoryInfo(
                category=PageCategory.PRODUCT,
                priority=70,
                icon="📦",
                description="Pagine prodotto o servizio",
                wcag_relevance=["1.1.1", "1.4.3", "2.4.6", "4.1.2"],
                testing_focus=["immagini", "prezzi", "azioni"]
            ),
            PageCategory.ARTICLE: CategoryInfo(
                category=PageCategory.ARTICLE,
                priority=60,
                icon="📄",
                description="Articoli, blog, contenuti editoriali",
                wcag_relevance=["1.3.1", "1.4.3", "2.4.2", "3.1.1"],
                testing_focus=["struttura", "heading", "lettura"]
            ),
            PageCategory.NAVIGATION: CategoryInfo(
                category=PageCategory.NAVIGATION,
                priority=70,
                icon="🗺️",
                description="Menu, sitemap, indici",
                wcag_relevance=["2.4.1", "2.4.3", "2.4.5", "2.4.8"],
                testing_focus=["navigazione", "skip link", "breadcrumb"]
            ),
            PageCategory.MEDIA: CategoryInfo(
                category=PageCategory.MEDIA,
                priority=65,
                icon="🎬",
                description="Video, audio, gallerie",
                wcag_relevance=["1.2.1", "1.2.2", "1.2.3", "1.4.2"],
                testing_focus=["media", "controlli", "alternative"]
            ),
            PageCategory.LEGAL: CategoryInfo(
                category=PageCategory.LEGAL,
                priority=40,
                icon="⚖️",
                description="Privacy, termini, cookie policy",
                wcag_relevance=["1.3.1", "1.4.3", "2.4.2"],
                testing_focus=["lettura", "struttura"]
            ),
            PageCategory.ABOUT: CategoryInfo(
                category=PageCategory.ABOUT,
                priority=50,
                icon="ℹ️",
                description="Chi siamo, informazioni azienda",
                wcag_relevance=["1.3.1", "1.4.3", "2.4.2"],
                testing_focus=["contenuto", "struttura"]
            ),
            PageCategory.GENERAL: CategoryInfo(
                category=PageCategory.GENERAL,
                priority=30,
                icon="📋",
                description="Pagine generiche",
                wcag_relevance=["1.3.1", "1.4.3", "2.4.2", "4.1.1"],
                testing_focus=["generale"]
            )
        }
    
    def _init_url_patterns(self) -> Dict[PageCategory, List[str]]:
        """Inizializza pattern URL per categorie"""
        return {
            PageCategory.HOMEPAGE: [r'^/$', r'^/index', r'^/home'],
            PageCategory.AUTHENTICATION: [r'/login', r'/signin', r'/register', r'/signup', r'/auth', r'/account'],
            PageCategory.CHECKOUT: [r'/cart', r'/checkout', r'/payment', r'/basket', r'/order'],
            PageCategory.CONTACT: [r'/contact', r'/contatti', r'/support', r'/help'],
            PageCategory.FORM: [r'/form', r'/application', r'/apply', r'/submit'],
            PageCategory.SEARCH: [r'/search', r'/find', r'/results', r'/ricerca'],
            PageCategory.PRODUCT: [r'/product', r'/item', r'/shop', r'/store', r'/catalog'],
            PageCategory.ARTICLE: [r'/blog', r'/news', r'/article', r'/post'],
            PageCategory.NAVIGATION: [r'/sitemap', r'/menu', r'/navigation', r'/index'],
            PageCategory.MEDIA: [r'/gallery', r'/video', r'/media', r'/photos'],
            PageCategory.LEGAL: [r'/privacy', r'/terms', r'/legal', r'/cookie', r'/gdpr'],
            PageCategory.ABOUT: [r'/about', r'/chi-siamo', r'/company', r'/team']
        }
    
    def _init_content_patterns(self) -> Dict[PageCategory, Dict[str, List[str]]]:
        """Inizializza pattern contenuto per categorie"""
        return {
            PageCategory.AUTHENTICATION: {
                'inputs': ['password', 'username', 'email'],
                'text': ['login', 'sign in', 'register', 'accedi'],
                'buttons': ['login', 'submit', 'register']
            },
            PageCategory.CHECKOUT: {
                'text': ['cart', 'checkout', 'payment', 'shipping'],
                'classes': ['cart', 'checkout', 'basket', 'order']
            },
            PageCategory.CONTACT: {
                'inputs': ['name', 'email', 'message', 'subject'],
                'text': ['contact', 'get in touch', 'contattaci']
            },
            PageCategory.SEARCH: {
                'inputs': ['search', 'q', 'query'],
                'text': ['search', 'find', 'cerca', 'risultati']
            },
            PageCategory.PRODUCT: {
                'classes': ['product', 'price', 'add-to-cart'],
                'text': ['price', 'buy', 'add to cart', 'acquista']
            },
            PageCategory.MEDIA: {
                'tags': ['video', 'audio', 'iframe'],
                'classes': ['gallery', 'carousel', 'slider']
            }
        }
    
    def categorize_page(self, page_info: Dict) -> Tuple[PageCategory, CategoryInfo]:
        """
        Categorizza una pagina basandosi su URL e contenuto
        
        Args:
            page_info: Dizionario con info pagina
            
        Returns:
            Tupla (categoria, info categoria)
        """
        url = page_info.get('url', '')
        page_type = page_info.get('page_type', '')
        
        # Prima prova con page_type se disponibile
        if page_type:
            for category in PageCategory:
                if category.value == page_type:
                    return category, self.categories[category]
        
        # Poi analizza URL
        category = self._categorize_by_url(url)
        if category != PageCategory.GENERAL:
            return category, self.categories[category]
        
        # Infine analizza contenuto
        category = self._categorize_by_content(page_info)
        return category, self.categories[category]
    
    def _categorize_by_url(self, url: str) -> PageCategory:
        """
        Categorizza basandosi su pattern URL
        
        Args:
            url: URL della pagina
            
        Returns:
            Categoria identificata
        """
        url_lower = url.lower()
        
        for category, patterns in self.url_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return category
        
        return PageCategory.GENERAL
    
    def _categorize_by_content(self, page_info: Dict) -> PageCategory:
        """
        Categorizza basandosi su contenuto pagina
        
        Args:
            page_info: Info pagina
            
        Returns:
            Categoria identificata
        """
        # Check per form di autenticazione
        if page_info.get('forms_count', 0) > 0:
            # Se ha password input probabilmente è auth
            dom_structure = page_info.get('dom_structure', '')
            if 'password' in dom_structure.lower():
                return PageCategory.AUTHENTICATION
            
            # Molti input = probabilmente form importante
            if page_info.get('inputs_count', 0) > 5:
                return PageCategory.FORM
            elif page_info.get('inputs_count', 0) > 2:
                return PageCategory.CONTACT
        
        # Check per media
        if page_info.get('videos_count', 0) > 0:
            return PageCategory.MEDIA
        
        # Check per e-commerce
        if 'product' in page_info.get('dom_structure', '').lower():
            return PageCategory.PRODUCT
        
        # Check per articoli
        if 'article' in page_info.get('dom_structure', '').lower():
            return PageCategory.ARTICLE
        
        return PageCategory.GENERAL
    
    def categorize_pages(self, pages: List[Dict]) -> Dict[PageCategory, List[Dict]]:
        """
        Categorizza lista di pagine
        
        Args:
            pages: Lista di pagine
            
        Returns:
            Dizionario categoria -> lista pagine
        """
        categorized = {}
        
        for page in pages:
            category, _ = self.categorize_page(page)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(page)
        
        return categorized
    
    def get_priority_categories(self) -> List[PageCategory]:
        """
        Ottiene categorie ordinate per priorità
        
        Returns:
            Lista categorie ordinate
        """
        sorted_categories = sorted(
            self.categories.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        return [cat for cat, _ in sorted_categories]
    
    def get_wcag_criteria_for_page(self, page_info: Dict) -> List[str]:
        """
        Ottiene criteri WCAG rilevanti per una pagina
        
        Args:
            page_info: Info pagina
            
        Returns:
            Lista criteri WCAG
        """
        category, info = self.categorize_page(page_info)
        return info.wcag_relevance
    
    def get_testing_focus_for_page(self, page_info: Dict) -> List[str]:
        """
        Ottiene focus di testing per una pagina
        
        Args:
            page_info: Info pagina
            
        Returns:
            Lista focus di testing
        """
        category, info = self.categorize_page(page_info)
        return info.testing_focus
    
    def calculate_page_importance(self, page_info: Dict) -> int:
        """
        Calcola importanza di una pagina per accessibilità
        
        Args:
            page_info: Info pagina
            
        Returns:
            Score importanza (0-100)
        """
        category, info = self.categorize_page(page_info)
        base_score = info.priority
        
        # Bonus per elementi interattivi
        interactive_score = 0
        interactive_score += min(page_info.get('forms_count', 0) * 10, 20)
        interactive_score += min(page_info.get('inputs_count', 0) * 2, 10)
        interactive_score += min(page_info.get('buttons_count', 0) * 2, 10)
        
        # Bonus per media
        media_score = 0
        media_score += min(page_info.get('videos_count', 0) * 5, 10)
        media_score += min(page_info.get('images_count', 0), 5)
        
        # Bonus per struttura semantica
        structure_score = 0
        if page_info.get('has_h1'):
            structure_score += 5
        if page_info.get('has_nav'):
            structure_score += 5
        if page_info.get('has_main'):
            structure_score += 3
        if page_info.get('has_footer'):
            structure_score += 2
        
        # Penalità per profondità
        depth_penalty = page_info.get('depth', 0) * 5
        
        total_score = base_score + interactive_score + media_score + structure_score - depth_penalty
        
        return max(0, min(100, total_score))