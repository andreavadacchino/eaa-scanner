"""
Depth Manager per configurazione profondità analisi
Gestisce la profondità di scansione per ogni tipo di pagina
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .page_categorizer import PageCategory

logger = logging.getLogger(__name__)


class AnalysisDepth(Enum):
    """Livelli di profondità analisi"""
    BASIC = "basic"
    STANDARD = "standard"
    FULL = "full"
    CUSTOM = "custom"


@dataclass
class DepthConfig:
    """Configurazione profondità per tipo di analisi"""
    level: AnalysisDepth
    viewports: List[str]  # desktop, tablet, mobile
    states: List[str]  # default, focus, hover, active, error
    content_areas: List[str]  # visible, hidden, modal, accordion
    interactions: List[str]  # forms, navigation, media
    scanners: List[str]  # wave, axe, pa11y, lighthouse
    estimated_time_minutes: int
    description: str


class DepthManager:
    """
    Gestisce la configurazione di profondità per ogni pagina
    """
    
    def __init__(self):
        """Inizializza il manager con configurazioni predefinite"""
        self.depth_configs = self._init_depth_configs()
        self.category_defaults = self._init_category_defaults()
        self.custom_configs: Dict[str, DepthConfig] = {}
    
    def _init_depth_configs(self) -> Dict[AnalysisDepth, DepthConfig]:
        """Inizializza configurazioni di profondità standard"""
        return {
            AnalysisDepth.BASIC: DepthConfig(
                level=AnalysisDepth.BASIC,
                viewports=["desktop"],
                states=["default"],
                content_areas=["visible"],
                interactions=[],
                scanners=["axe", "pa11y"],
                estimated_time_minutes=5,
                description="Analisi base del contenuto visibile desktop"
            ),
            AnalysisDepth.STANDARD: DepthConfig(
                level=AnalysisDepth.STANDARD,
                viewports=["desktop", "mobile"],
                states=["default", "focus", "hover"],
                content_areas=["visible"],
                interactions=["forms", "navigation"],
                scanners=["wave", "axe", "pa11y"],
                estimated_time_minutes=8,
                description="Analisi standard multi-device con stati interattivi"
            ),
            AnalysisDepth.FULL: DepthConfig(
                level=AnalysisDepth.FULL,
                viewports=["desktop", "tablet", "mobile"],
                states=["default", "focus", "hover", "active", "error"],
                content_areas=["visible", "hidden", "modal", "accordion"],
                interactions=["forms", "navigation", "media"],
                scanners=["wave", "axe", "pa11y", "lighthouse"],
                estimated_time_minutes=15,
                description="Analisi completa con tutti gli stati e interazioni"
            )
        }
    
    def _init_category_defaults(self) -> Dict[PageCategory, AnalysisDepth]:
        """Inizializza profondità default per categoria"""
        return {
            PageCategory.HOMEPAGE: AnalysisDepth.FULL,
            PageCategory.AUTHENTICATION: AnalysisDepth.FULL,
            PageCategory.CHECKOUT: AnalysisDepth.FULL,
            PageCategory.CONTACT: AnalysisDepth.FULL,
            PageCategory.FORM: AnalysisDepth.FULL,
            PageCategory.SEARCH: AnalysisDepth.STANDARD,
            PageCategory.PRODUCT: AnalysisDepth.STANDARD,
            PageCategory.ARTICLE: AnalysisDepth.BASIC,
            PageCategory.NAVIGATION: AnalysisDepth.STANDARD,
            PageCategory.MEDIA: AnalysisDepth.FULL,
            PageCategory.LEGAL: AnalysisDepth.BASIC,
            PageCategory.ABOUT: AnalysisDepth.BASIC,
            PageCategory.GENERAL: AnalysisDepth.BASIC
        }
    
    def get_depth_for_page(self, 
                           page_info: Dict,
                           category: Optional[PageCategory] = None) -> DepthConfig:
        """
        Ottiene configurazione profondità per una pagina
        
        Args:
            page_info: Informazioni pagina
            category: Categoria pagina (opzionale)
            
        Returns:
            DepthConfig appropriata
        """
        # Check se ha configurazione custom
        page_url = page_info.get('url', '')
        if page_url in self.custom_configs:
            return self.custom_configs[page_url]
        
        # Usa categoria se fornita
        if category:
            depth_level = self.category_defaults.get(category, AnalysisDepth.BASIC)
            return self.depth_configs[depth_level]
        
        # Determina profondità basandosi su caratteristiche
        return self._determine_depth_by_features(page_info)
    
    def _determine_depth_by_features(self, page_info: Dict) -> DepthConfig:
        """
        Determina profondità basandosi su caratteristiche pagina
        
        Args:
            page_info: Info pagina
            
        Returns:
            DepthConfig appropriata
        """
        # Conta elementi interattivi
        interactive_count = (
            page_info.get('forms_count', 0) +
            page_info.get('inputs_count', 0) // 3 +
            page_info.get('buttons_count', 0) // 5
        )
        
        # Conta media
        media_count = (
            page_info.get('videos_count', 0) +
            page_info.get('images_count', 0) // 10
        )
        
        # Determina livello
        if interactive_count >= 3 or media_count >= 2:
            return self.depth_configs[AnalysisDepth.FULL]
        elif interactive_count >= 1 or media_count >= 1:
            return self.depth_configs[AnalysisDepth.STANDARD]
        else:
            return self.depth_configs[AnalysisDepth.BASIC]
    
    def set_custom_depth(self, page_url: str, config: DepthConfig):
        """
        Imposta configurazione custom per una pagina
        
        Args:
            page_url: URL della pagina
            config: Configurazione custom
        """
        self.custom_configs[page_url] = config
    
    def create_custom_config(self,
                           viewports: List[str],
                           states: List[str],
                           content_areas: List[str],
                           interactions: List[str],
                           scanners: List[str],
                           description: str = "") -> DepthConfig:
        """
        Crea configurazione custom
        
        Args:
            viewports: Viewport da testare
            states: Stati da testare
            content_areas: Aree contenuto
            interactions: Interazioni da testare
            scanners: Scanner da usare
            description: Descrizione config
            
        Returns:
            DepthConfig custom
        """
        # Stima tempo basandosi su parametri
        time_estimate = self._estimate_time(
            len(viewports),
            len(states),
            len(content_areas),
            len(interactions),
            len(scanners)
        )
        
        return DepthConfig(
            level=AnalysisDepth.CUSTOM,
            viewports=viewports,
            states=states,
            content_areas=content_areas,
            interactions=interactions,
            scanners=scanners,
            estimated_time_minutes=time_estimate,
            description=description or "Configurazione personalizzata"
        )
    
    def _estimate_time(self,
                      viewports: int,
                      states: int,
                      content_areas: int,
                      interactions: int,
                      scanners: int) -> int:
        """
        Stima tempo di scansione
        
        Args:
            viewports: Numero viewport
            states: Numero stati
            content_areas: Numero aree
            interactions: Numero interazioni
            scanners: Numero scanner
            
        Returns:
            Tempo stimato in minuti
        """
        # Formula empirica per stima
        base_time = 2  # Tempo base per pagina
        
        # Aggiungi tempo per ogni dimensione
        viewport_time = viewports * 1.5
        state_time = states * 0.5
        area_time = content_areas * 0.5
        interaction_time = interactions * 1
        scanner_time = scanners * 1.5
        
        total = base_time + viewport_time + state_time + area_time + interaction_time + scanner_time
        
        return int(total)
    
    def calculate_total_time(self, 
                           pages_with_depth: List[Tuple[Dict, DepthConfig]]) -> Dict:
        """
        Calcola tempo totale per scansione
        
        Args:
            pages_with_depth: Lista di tuple (pagina, depth_config)
            
        Returns:
            Dizionario con statistiche tempo
        """
        total_minutes = 0
        breakdown = {
            AnalysisDepth.BASIC: 0,
            AnalysisDepth.STANDARD: 0,
            AnalysisDepth.FULL: 0,
            AnalysisDepth.CUSTOM: 0
        }
        
        for page, config in pages_with_depth:
            time = config.estimated_time_minutes
            total_minutes += time
            breakdown[config.level] += 1
        
        return {
            'total_minutes': total_minutes,
            'total_hours': round(total_minutes / 60, 1),
            'average_per_page': round(total_minutes / len(pages_with_depth), 1) if pages_with_depth else 0,
            'breakdown': {
                level.value: count
                for level, count in breakdown.items()
                if count > 0
            }
        }
    
    def optimize_depth_for_time_budget(self,
                                      pages: List[Dict],
                                      time_budget_minutes: int,
                                      categories: Dict[str, PageCategory]) -> List[Tuple[Dict, DepthConfig]]:
        """
        Ottimizza profondità per rispettare budget tempo
        
        Args:
            pages: Pagine da scansionare
            time_budget_minutes: Budget tempo in minuti
            categories: Mapping URL -> categoria
            
        Returns:
            Lista ottimizzata di (pagina, depth_config)
        """
        if not pages:
            return []
        
        # Inizia con profondità default
        pages_with_depth = []
        for page in pages:
            category = categories.get(page['url'], PageCategory.GENERAL)
            default_depth = self.get_depth_for_page(page, category)
            pages_with_depth.append((page, default_depth))
        
        # Calcola tempo totale
        stats = self.calculate_total_time(pages_with_depth)
        current_time = stats['total_minutes']
        
        # Se già dentro budget, ritorna
        if current_time <= time_budget_minutes:
            return pages_with_depth
        
        # Riduci profondità per pagine meno critiche
        optimized = []
        for page, config in pages_with_depth:
            category = categories.get(page['url'], PageCategory.GENERAL)
            
            # Mantieni full per pagine critiche
            if category in [PageCategory.HOMEPAGE, PageCategory.AUTHENTICATION, 
                          PageCategory.CHECKOUT, PageCategory.CONTACT]:
                optimized.append((page, config))
            else:
                # Riduci profondità
                if config.level == AnalysisDepth.FULL:
                    reduced = self.depth_configs[AnalysisDepth.STANDARD]
                elif config.level == AnalysisDepth.STANDARD:
                    reduced = self.depth_configs[AnalysisDepth.BASIC]
                else:
                    reduced = config
                
                optimized.append((page, reduced))
        
        # Verifica nuovo tempo
        new_stats = self.calculate_total_time(optimized)
        if new_stats['total_minutes'] <= time_budget_minutes:
            return optimized
        
        # Se ancora sopra budget, limita numero pagine
        pages_to_keep = int(time_budget_minutes / 
                           (new_stats['total_minutes'] / len(optimized)))
        
        # Mantieni le più importanti
        return optimized[:max(1, pages_to_keep)]
    
    def get_scan_configuration(self, depth_config: DepthConfig) -> Dict:
        """
        Ottiene configurazione dettagliata per scanner
        
        Args:
            depth_config: Configurazione profondità
            
        Returns:
            Dizionario con parametri per scanner
        """
        return {
            'viewports': [
                {'width': 1920, 'height': 1080} if v == 'desktop' else
                {'width': 768, 'height': 1024} if v == 'tablet' else
                {'width': 375, 'height': 667}  # mobile
                for v in depth_config.viewports
            ],
            'wait_for_states': depth_config.states,
            'scan_hidden_content': 'hidden' in depth_config.content_areas,
            'scan_modals': 'modal' in depth_config.content_areas,
            'test_interactions': depth_config.interactions,
            'scanners_enabled': {
                'wave': 'wave' in depth_config.scanners,
                'axe': 'axe' in depth_config.scanners,
                'pa11y': 'pa11y' in depth_config.scanners,
                'lighthouse': 'lighthouse' in depth_config.scanners
            },
            'timeout_per_scanner': depth_config.estimated_time_minutes * 60 * 1000 // 4  # ms
        }
    
    def get_depth_summary(self, pages_with_depth: List[Tuple[Dict, DepthConfig]]) -> Dict:
        """
        Genera sommario configurazioni profondità
        
        Args:
            pages_with_depth: Lista (pagina, config)
            
        Returns:
            Sommario
        """
        summary = {
            'total_pages': len(pages_with_depth),
            'depth_distribution': {},
            'estimated_time': self.calculate_total_time(pages_with_depth),
            'scanner_coverage': {},
            'viewport_coverage': {}
        }
        
        # Conta distribuzione profondità
        for _, config in pages_with_depth:
            level = config.level.value
            summary['depth_distribution'][level] = summary['depth_distribution'].get(level, 0) + 1
            
            # Conta scanner
            for scanner in config.scanners:
                summary['scanner_coverage'][scanner] = summary['scanner_coverage'].get(scanner, 0) + 1
            
            # Conta viewport
            for viewport in config.viewports:
                summary['viewport_coverage'][viewport] = summary['viewport_coverage'].get(viewport, 0) + 1
        
        return summary