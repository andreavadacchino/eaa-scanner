"""
Coordinatore principale del sistema Smart Page Sampler
Orchestrazione discovery, template detection, selezione e configurazione profondità
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

from .smart_crawler import SmartCrawler
from .template_detector import TemplateDetector
from .page_categorizer import PageCategorizer, PageCategory
from .selector import PageSelector, SelectionStrategy, SelectionConfig
from .depth_manager import DepthManager, AnalysisDepth, DepthConfig
from .realtime_progress import RealtimeProgress

logger = logging.getLogger(__name__)


@dataclass
class SamplerConfig:
    """Configurazione completa per il sampler"""
    # Discovery
    max_pages: int = 50
    max_depth: int = 3
    follow_external: bool = False
    timeout_ms: int = 30000
    use_playwright: bool = True
    
    # Template Detection
    similarity_threshold: float = 0.85
    min_template_pages: int = 2
    
    # Selection
    selection_strategy: SelectionStrategy = SelectionStrategy.WCAG_EM
    max_selected_pages: int = 10
    min_selected_pages: int = 5
    include_all_critical: bool = True
    
    # Depth Analysis
    default_depth: AnalysisDepth = AnalysisDepth.STANDARD
    time_budget_minutes: Optional[int] = None
    optimize_for_budget: bool = True
    
    # Real-time Feedback
    enable_websocket: bool = True
    websocket_port: int = 8765
    
    # Output
    save_screenshots: bool = True
    output_dir: str = "output/page_sampler"


@dataclass
class SamplerResult:
    """Risultato completo del sampling"""
    # Discovery
    discovered_pages: List[Dict] = field(default_factory=list)
    total_discovered: int = 0
    discovery_time_seconds: float = 0
    
    # Templates
    templates: Dict[str, Dict] = field(default_factory=dict)
    template_summary: Dict = field(default_factory=dict)
    
    # Selection
    selected_pages: List[Dict] = field(default_factory=list)
    selection_strategy: str = ""
    selection_reasons: Dict[str, str] = field(default_factory=dict)
    
    # Depth Configuration
    depth_configs: List[Tuple[Dict, DepthConfig]] = field(default_factory=list)
    depth_summary: Dict = field(default_factory=dict)
    estimated_scan_time: Dict = field(default_factory=dict)
    
    # Categories
    category_distribution: Dict[str, int] = field(default_factory=dict)
    priority_pages: List[Dict] = field(default_factory=list)
    
    # Errors/Warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Converte in dizionario serializzabile"""
        result = {
            'discovery': {
                'total_discovered': self.total_discovered,
                'discovery_time_seconds': self.discovery_time_seconds,
                'pages': self.discovered_pages
            },
            'templates': {
                'identified': self.templates,
                'summary': self.template_summary
            },
            'selection': {
                'strategy': self.selection_strategy,
                'selected_pages': self.selected_pages,
                'reasons': self.selection_reasons,
                'total_selected': len(self.selected_pages)
            },
            'depth_analysis': {
                'configurations': [
                    {
                        'page_url': page['url'],
                        'depth_level': config.level.value,
                        'estimated_minutes': config.estimated_time_minutes
                    }
                    for page, config in self.depth_configs
                ],
                'summary': self.depth_summary,
                'estimated_total_time': self.estimated_scan_time
            },
            'categories': {
                'distribution': self.category_distribution,
                'priority_pages': self.priority_pages
            },
            'status': {
                'errors': self.errors,
                'warnings': self.warnings,
                'success': len(self.errors) == 0
            }
        }
        return result


class SmartPageSamplerCoordinator:
    """
    Coordinatore principale del sistema Smart Page Sampler
    Orchestrazione completa del processo di discovery e selezione
    """
    
    def __init__(self, config: Optional[SamplerConfig] = None):
        """
        Inizializza il coordinatore
        
        Args:
            config: Configurazione del sampler
        """
        self.config = config or SamplerConfig()
        
        # Inizializza componenti (SmartCrawler verrà inizializzato in execute con URL)
        self.crawler = None
        
        self.template_detector = TemplateDetector(
            similarity_threshold=self.config.similarity_threshold
        )
        
        self.categorizer = PageCategorizer()
        
        self.selector = PageSelector(
            SelectionConfig(
                strategy=self.config.selection_strategy,
                max_pages=self.config.max_selected_pages,
                min_pages=self.config.min_selected_pages,
                include_all_critical=self.config.include_all_critical
            )
        )
        
        self.depth_manager = DepthManager()
        
        # Inizializza progress tracker se abilitato
        self.progress = None
        if self.config.enable_websocket:
            self.progress = RealtimeProgress(
                port=self.config.websocket_port
            )
    
    def execute(self, url: str) -> SamplerResult:
        """
        Esegue il processo completo di sampling
        
        Args:
            url: URL base del sito da analizzare
            
        Returns:
            SamplerResult con tutti i dati
        """
        result = SamplerResult()
        
        # Inizializza crawler con URL
        self.crawler = SmartCrawler(
            base_url=url,
            max_pages=self.config.max_pages,
            max_depth=self.config.max_depth,
            timeout_per_page=self.config.timeout_ms,
            screenshot_enabled=self.config.save_screenshots,
            headless=True
        )
        
        # Avvia progress tracker
        if self.progress:
            self.progress.start()
            time.sleep(1)  # Aspetta che WebSocket sia pronto
        
        try:
            # FASE 1: Discovery
            logger.info(f"Inizio discovery di {url}")
            if self.progress:
                self.progress.start_discovery(url, self.config.max_pages)
            
            start_time = time.time()
            discovered_pages = self._execute_discovery(result)
            result.discovery_time_seconds = time.time() - start_time
            
            if self.progress:
                self.progress.complete_discovery(
                    len(discovered_pages),
                    0  # Templates verranno calcolati dopo
                )
            
            # FASE 2: Template Detection
            logger.info("Inizio template detection")
            if self.progress:
                self.progress.start_template_detection(len(discovered_pages))
            
            templates = self._execute_template_detection(discovered_pages, result)
            
            if self.progress:
                self.progress.complete_template_detection(templates)
            
            # FASE 3: Categorizzazione
            logger.info("Categorizzazione pagine")
            categories = self._execute_categorization(discovered_pages, result)
            
            # FASE 4: Selezione WCAG-EM
            logger.info("Selezione pagine WCAG-EM")
            selected_pages = self._execute_selection(discovered_pages, templates, result)
            
            # FASE 5: Configurazione Profondità
            logger.info("Configurazione profondità analisi")
            depth_configs = self._execute_depth_configuration(
                selected_pages, 
                categories, 
                result
            )
            
            # FASE 6: Salvataggio risultati
            self._save_results(result)
            
            # Notifica completamento
            if self.progress:
                self.progress.send_info(
                    f"Sampling completato: {len(selected_pages)} pagine selezionate",
                    {
                        'total_discovered': len(discovered_pages),
                        'templates_found': len(templates),
                        'pages_selected': len(selected_pages)
                    }
                )
            
        except Exception as e:
            error_msg = f"Errore durante sampling: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            
            if self.progress:
                self.progress.send_error(error_msg)
        
        return result
    
    def _execute_discovery(self, result: SamplerResult) -> List[Dict]:
        """
        Esegue fase di discovery
        
        Args:
            result: Oggetto risultato da aggiornare
            
        Returns:
            Lista pagine scoperte
        """
        try:
            # Callback per progress updates
            def on_page_discovered(page_info):
                if self.progress:
                    self.progress.update_discovery(
                        pages_found=len(self.crawler.discovered_pages),
                        pages_visited=len(self.crawler.visited),
                        current_url=page_info.url,
                        message=f"Scoperta: {page_info.url}"
                    )
            
            # Esegui crawling
            discovered = self.crawler.crawl()
            
            # Converti PageInfo in dizionari
            discovered_dicts = [p.to_dict() for p in discovered]
            
            result.discovered_pages = discovered_dicts
            result.total_discovered = len(discovered_dicts)
            
            logger.info(f"Discovery completata: {len(discovered_dicts)} pagine trovate")
            
            # Se nessuna pagina trovata, usa almeno l'URL base
            if not discovered_dicts:
                logger.warning("Nessuna pagina scoperta, uso URL base")
                # Crea PageInfo di fallback per URL base
                from .smart_crawler import PageInfo
                base_page = PageInfo(
                    url=self.crawler.base_url,
                    title="Homepage",
                    page_type="homepage",
                    priority=100,
                    depth=0
                )
                discovered_dicts = [base_page.to_dict()]
                result.discovered_pages = discovered_dicts
                result.total_discovered = 1
            
            return discovered_dicts
            
        except Exception as e:
            error_msg = f"Errore in discovery: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return []
    
    def _execute_template_detection(self, pages: List[Dict], 
                                   result: SamplerResult) -> Dict[str, Dict]:
        """
        Esegue template detection
        
        Args:
            pages: Pagine scoperte
            result: Oggetto risultato
            
        Returns:
            Template identificati
        """
        try:
            if self.progress:
                # Simula progresso per template detection
                for i, page in enumerate(pages):
                    self.progress.update_template_detection(
                        templates_found=0,
                        pages_analyzed=i + 1
                    )
                    time.sleep(0.01)  # Piccolo delay per simulazione
            
            # Identifica template
            templates = self.template_detector.detect_templates(pages)
            
            # Genera sommario
            summary = self.template_detector.get_template_summary(templates)
            
            result.templates = templates
            result.template_summary = summary
            
            logger.info(f"Template detection completata: {len(templates)} template trovati")
            
            return templates
            
        except Exception as e:
            error_msg = f"Errore in template detection: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return {}
    
    def _execute_categorization(self, pages: List[Dict], 
                               result: SamplerResult) -> Dict[str, PageCategory]:
        """
        Esegue categorizzazione pagine
        
        Args:
            pages: Pagine da categorizzare
            result: Oggetto risultato
            
        Returns:
            Mapping URL -> categoria
        """
        try:
            categories = {}
            category_counts = {}
            
            for page in pages:
                category, info = self.categorizer.categorize_page(page)
                categories[page['url']] = category
                
                # Conta categorie
                cat_name = category.value
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
                
                # Identifica pagine prioritarie
                if info.priority >= 80:
                    result.priority_pages.append({
                        'url': page['url'],
                        'category': cat_name,
                        'priority': info.priority
                    })
            
            result.category_distribution = category_counts
            
            # Ordina pagine prioritarie
            result.priority_pages.sort(key=lambda x: x['priority'], reverse=True)
            
            logger.info(f"Categorizzazione completata: {len(category_counts)} categorie identificate")
            
            return categories
            
        except Exception as e:
            error_msg = f"Errore in categorizzazione: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            return {}
    
    def _execute_selection(self, pages: List[Dict], templates: Dict[str, Dict],
                          result: SamplerResult) -> List[Dict]:
        """
        Esegue selezione pagine WCAG-EM
        
        Args:
            pages: Tutte le pagine
            templates: Template identificati
            result: Oggetto risultato
            
        Returns:
            Pagine selezionate
        """
        try:
            # Esegui selezione
            selection = self.selector.select_pages(pages, templates)
            
            # Valida selezione
            is_valid, issues = self.selector.validate_selection(selection)
            
            if not is_valid:
                for issue in issues:
                    result.warnings.append(f"Selezione: {issue}")
            
            # Aggiorna risultato
            result.selected_pages = selection.selected_pages
            result.selection_strategy = selection.strategy_used.value
            result.selection_reasons = selection.selection_reasons
            
            logger.info(f"Selezione completata: {len(selection.selected_pages)} pagine selezionate")
            
            return selection.selected_pages
            
        except Exception as e:
            error_msg = f"Errore in selezione: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            
            # Fallback: usa prime N pagine
            fallback_pages = pages[:self.config.max_selected_pages]
            result.selected_pages = fallback_pages
            result.warnings.append("Usato fallback per selezione")
            return fallback_pages
    
    def _execute_depth_configuration(self, pages: List[Dict], 
                                    categories: Dict[str, PageCategory],
                                    result: SamplerResult) -> List[Tuple[Dict, DepthConfig]]:
        """
        Configura profondità analisi per ogni pagina
        
        Args:
            pages: Pagine selezionate
            categories: Mapping URL -> categoria
            result: Oggetto risultato
            
        Returns:
            Lista di (pagina, config profondità)
        """
        try:
            pages_with_depth = []
            
            # Se c'è budget tempo, ottimizza
            if self.config.time_budget_minutes and self.config.optimize_for_budget:
                pages_with_depth = self.depth_manager.optimize_depth_for_time_budget(
                    pages,
                    self.config.time_budget_minutes,
                    categories
                )
            else:
                # Assegna profondità basandosi su categoria
                for page in pages:
                    category = categories.get(page['url'], PageCategory.GENERAL)
                    depth_config = self.depth_manager.get_depth_for_page(page, category)
                    pages_with_depth.append((page, depth_config))
            
            # Calcola sommario
            depth_summary = self.depth_manager.get_depth_summary(pages_with_depth)
            time_estimate = self.depth_manager.calculate_total_time(pages_with_depth)
            
            result.depth_configs = pages_with_depth
            result.depth_summary = depth_summary
            result.estimated_scan_time = time_estimate
            
            logger.info(f"Configurazione profondità completata: {time_estimate['total_hours']} ore stimate")
            
            return pages_with_depth
            
        except Exception as e:
            error_msg = f"Errore in configurazione profondità: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            
            # Fallback: usa profondità standard per tutte
            fallback_configs = []
            default_config = self.depth_manager.depth_configs[self.config.default_depth]
            for page in pages:
                fallback_configs.append((page, default_config))
            
            result.depth_configs = fallback_configs
            result.warnings.append("Usato fallback per configurazione profondità")
            return fallback_configs
    
    def _save_results(self, result: SamplerResult):
        """
        Salva risultati su file
        
        Args:
            result: Risultati da salvare
        """
        try:
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Salva risultato completo
            result_file = output_dir / "sampler_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Risultati salvati in {result_file}")
            
            # Salva configurazione usata
            config_file = output_dir / "sampler_config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.config), f, indent=2, default=str)
            
            # Salva lista URL per scanner
            urls_file = output_dir / "selected_urls.txt"
            with open(urls_file, 'w', encoding='utf-8') as f:
                for page in result.selected_pages:
                    f.write(f"{page['url']}\n")
            
            logger.info(f"Lista URL salvata in {urls_file}")
            
        except Exception as e:
            error_msg = f"Errore salvataggio risultati: {str(e)}"
            logger.error(error_msg)
            result.errors.append(error_msg)
    
    def get_scan_configuration(self) -> Dict[str, Any]:
        """
        Genera configurazione per lo scanner basata su risultati sampling
        
        Returns:
            Configurazione per scanner EAA
        """
        # Carica ultimo risultato se esiste
        result_file = Path(self.config.output_dir) / "sampler_result.json"
        if not result_file.exists():
            raise FileNotFoundError("Nessun risultato sampling disponibile. Esegui prima execute()")
        
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        
        # Genera configurazione scanner
        scan_config = {
            'urls': [p['url'] for p in result_data['selection']['selected_pages']],
            'depth_configs': {},
            'estimated_time_hours': result_data['depth_analysis']['estimated_total_time']['total_hours'],
            'templates': result_data['templates']['summary'],
            'methodology': {
                'selection_strategy': result_data['selection']['strategy'],
                'pages_selected': result_data['selection']['total_selected'],
                'templates_covered': len(result_data['templates']['identified']),
                'wcag_em_compliant': result_data['selection']['strategy'] == 'wcag_em'
            }
        }
        
        # Aggiungi configurazioni profondità per URL
        for config in result_data['depth_analysis']['configurations']:
            scan_config['depth_configs'][config['page_url']] = {
                'level': config['depth_level'],
                'estimated_minutes': config['estimated_minutes']
            }
        
        return scan_config