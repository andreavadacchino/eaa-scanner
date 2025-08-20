"""
Smart Crawler con Playwright per discovery pagine avanzata
Gestisce siti JavaScript-heavy e SPA con template detection
"""

import asyncio
import logging
import time
from typing import List, Dict, Set, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
import json
import re
from dataclasses import dataclass, field, asdict

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = Any  # Usa Any come fallback per type hints
    Browser = Any
    BrowserContext = Any
    print("Attenzione: Playwright non installato. Installa con: pip install playwright && playwright install")

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Informazioni dettagliate su una pagina scoperta"""
    url: str
    title: str = ""
    description: str = ""
    page_type: str = "general"
    template_hash: str = ""
    depth: int = 0
    priority: int = 50
    discovered_at: float = field(default_factory=time.time)
    
    # Metriche pagina
    forms_count: int = 0
    inputs_count: int = 0
    buttons_count: int = 0
    images_count: int = 0
    videos_count: int = 0
    links_count: int = 0
    
    # Info accessibilità
    has_h1: bool = False
    has_nav: bool = False
    has_main: bool = False
    has_footer: bool = False
    lang: str = ""
    
    # Screenshot
    screenshot_path: Optional[str] = None
    
    # DOM fingerprint per template detection
    dom_structure: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartCrawler:
    """
    Crawler avanzato con Playwright per gestire siti moderni
    """
    
    def __init__(self,
                 base_url: str,
                 max_pages: int = 50,
                 max_depth: int = 3,
                 timeout_per_page: int = 10000,
                 screenshot_enabled: bool = True,
                 headless: bool = True,
                 progress_callback: Optional[callable] = None):
        """
        Inizializza il crawler
        
        Args:
            base_url: URL di partenza
            max_pages: Numero massimo di pagine da scoprire
            max_depth: Profondità massima di crawling
            timeout_per_page: Timeout per pagina in ms
            screenshot_enabled: Se salvare screenshot
            headless: Se eseguire browser in headless
            progress_callback: Callback per aggiornamenti real-time
        """
        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout_per_page = timeout_per_page
        self.screenshot_enabled = screenshot_enabled
        self.headless = headless
        self.progress_callback = progress_callback
        
        # Stato del crawling
        self.visited_urls: Set[str] = set()
        self.discovered_pages: List[PageInfo] = []
        self.page_queue: List[tuple[str, int]] = []  # (url, depth)
        self.sitemap_urls: Set[str] = set()
        
        # Pattern da escludere
        self.excluded_patterns = [
            r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', 
            r'\.mp3$', r'\.mp4$', r'\.avi$', r'\.mov$',
            r'\.doc$', r'\.docx$', r'\.xls$', r'\.xlsx$',
            r'mailto:', r'tel:', r'javascript:', r'#$',
            r'/logout', r'/signout', r'/api/', r'/admin/'
        ]
        
        # Browser context
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def crawl_async(self) -> List[PageInfo]:
        """
        Esegue crawling asincrono con Playwright
        
        Returns:
            Lista di PageInfo per le pagine scoperte
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright non disponibile. Installa con: pip install playwright")
            return []
        
        logger.info(f"Inizio Smart Crawling di {self.base_url}")
        
        async with async_playwright() as p:
            # Lancia browser
            self.browser = await p.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (compatible; EAA-Scanner/2.0; +https://eaa-scanner.it)'
            )
            
            # Prima cerca sitemap
            await self._discover_sitemap_async()
            
            # Inizia dal base URL
            self.page_queue.append((self.base_url, 0))
            
            # Crawl iterativo con gestione coda
            while self.page_queue and len(self.discovered_pages) < self.max_pages:
                url, depth = self.page_queue.pop(0)
                
                if depth > self.max_depth:
                    continue
                
                if url in self.visited_urls:
                    continue
                
                # Crawl della pagina
                page_info = await self._crawl_page_async(url, depth)
                if page_info:
                    self.discovered_pages.append(page_info)
                    self._report_progress(f"Scoperta pagina {len(self.discovered_pages)}/{self.max_pages}: {page_info.title}")
            
            # Chiudi browser
            await self.browser.close()
        
        # Ordina per priorità
        self.discovered_pages.sort(key=lambda x: (-x.priority, x.depth))
        
        logger.info(f"Crawling completato: {len(self.discovered_pages)} pagine scoperte")
        return self.discovered_pages
    
    def crawl(self) -> List[PageInfo]:
        """
        Wrapper sincrono per crawling
        
        Returns:
            Lista di PageInfo
        """
        # Esegui in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.crawl_async())
        finally:
            loop.close()
    
    async def _crawl_page_async(self, url: str, depth: int) -> Optional[PageInfo]:
        """
        Crawl singola pagina con Playwright
        
        Args:
            url: URL da processare
            depth: Profondità corrente
            
        Returns:
            PageInfo o None se errore
        """
        normalized_url = self._normalize_url(url)
        
        if not self._is_valid_url(normalized_url):
            return None
        
        self.visited_urls.add(normalized_url)
        
        try:
            # Crea nuova pagina
            page = await self.context.new_page()
            
            # Naviga con timeout
            response = await page.goto(
                normalized_url,
                wait_until='networkidle',
                timeout=self.timeout_per_page
            )
            
            if not response or response.status >= 400:
                await page.close()
                return None
            
            # Attendi che DOM sia pronto
            await page.wait_for_load_state('domcontentloaded')
            
            # Estrai HTML
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Crea PageInfo
            page_info = await self._extract_page_info_async(
                normalized_url, soup, page, depth
            )
            
            # Estrai e aggiungi link alla coda
            links = self._extract_links(soup, normalized_url)
            for link in links[:20]:  # Limita link per pagina
                if link not in self.visited_urls:
                    self.page_queue.append((link, depth + 1))
            
            # Screenshot se abilitato
            if self.screenshot_enabled:
                screenshot_path = await self._take_screenshot_async(page, normalized_url)
                if screenshot_path:
                    page_info.screenshot_path = screenshot_path
            
            await page.close()
            return page_info
            
        except Exception as e:
            logger.warning(f"Errore crawling {normalized_url}: {e}")
            return None
    
    async def _extract_page_info_async(self, url: str, soup: BeautifulSoup,
                                       page: Page, depth: int) -> PageInfo:
        """
        Estrae informazioni dettagliate dalla pagina
        
        Args:
            url: URL della pagina
            soup: BeautifulSoup object
            page: Playwright Page object
            depth: Profondità nel crawling
            
        Returns:
            PageInfo con tutti i dettagli
        """
        # Titolo
        title = await page.title() or "Senza titolo"
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        # Lingua
        html_tag = soup.find('html')
        lang = html_tag.get('lang', 'it') if html_tag else 'it'
        
        # Conta elementi
        forms = len(soup.find_all('form'))
        inputs = len(soup.find_all(['input', 'textarea', 'select']))
        buttons = len(soup.find_all(['button', 'input[type="submit"]', 'input[type="button"]']))
        images = len(soup.find_all('img'))
        videos = len(soup.find_all(['video', 'iframe']))
        links = len(soup.find_all('a'))
        
        # Check struttura semantica
        has_h1 = bool(soup.find('h1'))
        has_nav = bool(soup.find('nav'))
        has_main = bool(soup.find('main'))
        has_footer = bool(soup.find('footer'))
        
        # Determina tipo di pagina
        page_type = self._determine_page_type(url, soup)
        
        # Calcola priorità
        priority = self._calculate_priority(url, page_type, depth)
        
        # Genera DOM fingerprint per template detection
        dom_structure = self._generate_dom_fingerprint(soup)
        
        return PageInfo(
            url=url,
            title=title,
            description=description,
            page_type=page_type,
            depth=depth,
            priority=priority,
            forms_count=forms,
            inputs_count=inputs,
            buttons_count=buttons,
            images_count=images,
            videos_count=videos,
            links_count=links,
            has_h1=has_h1,
            has_nav=has_nav,
            has_main=has_main,
            has_footer=has_footer,
            lang=lang,
            dom_structure=dom_structure
        )
    
    def _generate_dom_fingerprint(self, soup: BeautifulSoup) -> str:
        """
        Genera fingerprint della struttura DOM per template detection
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Stringa fingerprint
        """
        # Estrai struttura principale ignorando contenuti
        structure_tags = []
        
        for tag in soup.find_all(True, recursive=True)[:100]:  # Limita profondità
            if tag.name in ['script', 'style', 'noscript']:
                continue
            
            # Aggiungi tag e classi principali
            tag_sig = tag.name
            if tag.get('class'):
                main_class = tag['class'][0] if isinstance(tag['class'], list) else tag['class']
                # Rimuovi numeri per generalizzare
                main_class = re.sub(r'\d+', 'N', main_class)
                tag_sig += f".{main_class}"
            
            structure_tags.append(tag_sig)
        
        # Crea fingerprint
        return "|".join(structure_tags[:50])  # Primi 50 elementi
    
    def _determine_page_type(self, url: str, soup: BeautifulSoup) -> str:
        """
        Determina il tipo di pagina con euristiche avanzate
        
        Args:
            url: URL della pagina
            soup: BeautifulSoup object
            
        Returns:
            Tipo di pagina
        """
        url_lower = url.lower()
        
        # Homepage
        if url == self.base_url or url == self.base_url + '/':
            return 'homepage'
        
        # Check URL patterns
        patterns = {
            'contact': ['contact', 'contatti', 'contatto'],
            'about': ['about', 'chi-siamo', 'chi_siamo', 'about-us'],
            'authentication': ['login', 'signin', 'register', 'signup', 'auth'],
            'search': ['search', 'ricerca', 'cerca', 'find'],
            'checkout': ['cart', 'carrello', 'checkout', 'payment', 'pagamento'],
            'product': ['product', 'prodotto', 'item', 'articolo', 'shop'],
            'article': ['blog', 'news', 'article', 'post', 'articolo'],
            'legal': ['privacy', 'terms', 'cookie', 'legal', 'gdpr'],
            'form': ['form', 'modulo', 'application', 'richiesta']
        }
        
        for page_type, keywords in patterns.items():
            if any(kw in url_lower for kw in keywords):
                return page_type
        
        # Check contenuto pagina
        # Form di autenticazione
        password_inputs = soup.find_all('input', type='password')
        if password_inputs:
            return 'authentication'
        
        # E-commerce
        if soup.find(class_=re.compile('product|price|cart|add-to-cart', re.I)):
            return 'product'
        
        # Articolo/Blog
        if soup.find('article') or soup.find(class_=re.compile('article|post|blog', re.I)):
            return 'article'
        
        # Form generico
        if soup.find('form'):
            return 'form'
        
        return 'general'
    
    def _calculate_priority(self, url: str, page_type: str, depth: int) -> int:
        """
        Calcola priorità con algoritmo avanzato
        
        Args:
            url: URL della pagina
            page_type: Tipo di pagina
            depth: Profondità nel crawling
            
        Returns:
            Score di priorità (0-100)
        """
        # Score base per tipo
        type_scores = {
            'homepage': 100,
            'authentication': 95,
            'checkout': 90,
            'contact': 85,
            'form': 80,
            'search': 75,
            'product': 70,
            'about': 65,
            'article': 50,
            'legal': 40,
            'general': 30
        }
        
        priority = type_scores.get(page_type, 50)
        
        # Penalità per profondità
        priority -= (depth * 15)
        
        # Bonus se dalla sitemap
        if url in self.sitemap_urls:
            priority += 15
        
        # Bonus se path corto
        path_length = len(urlparse(url).path.split('/'))
        if path_length <= 2:
            priority += 10
        
        return max(0, min(100, priority))
    
    async def _take_screenshot_async(self, page: Page, url: str) -> Optional[str]:
        """
        Cattura screenshot della pagina
        
        Args:
            page: Playwright Page
            url: URL per naming
            
        Returns:
            Path dello screenshot o None
        """
        try:
            # Crea directory screenshots
            screenshots_dir = Path("output/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Nome file da URL
            safe_name = re.sub(r'[^\w\-_]', '_', urlparse(url).path or 'home')
            timestamp = int(time.time())
            filename = f"{safe_name}_{timestamp}.png"
            filepath = screenshots_dir / filename
            
            # Cattura screenshot
            await page.screenshot(
                path=str(filepath),
                full_page=False,  # Solo viewport per velocità
                type='png'
            )
            
            return str(filepath)
            
        except Exception as e:
            logger.warning(f"Errore screenshot per {url}: {e}")
            return None
    
    async def _discover_sitemap_async(self) -> None:
        """
        Scopre URL dalla sitemap con Playwright
        """
        sitemap_urls = [
            urljoin(self.base_url, 'sitemap.xml'),
            urljoin(self.base_url, 'sitemap_index.xml'),
            urljoin(self.base_url, 'sitemap.txt')
        ]
        
        page = await self.context.new_page()
        
        for sitemap_url in sitemap_urls:
            try:
                response = await page.goto(sitemap_url, timeout=5000)
                if response and response.status == 200:
                    content = await page.content()
                    
                    if sitemap_url.endswith('.xml'):
                        self._parse_xml_sitemap(content)
                    else:
                        self._parse_txt_sitemap(content)
                    
                    logger.info(f"Trovate {len(self.sitemap_urls)} URL dalla sitemap")
                    break
            except:
                continue
        
        await page.close()
    
    def _parse_xml_sitemap(self, content: str) -> None:
        """Parse sitemap XML"""
        try:
            soup = BeautifulSoup(content, 'xml')
            
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                if self._is_valid_url(url):
                    self.sitemap_urls.add(self._normalize_url(url))
        except Exception as e:
            logger.warning(f"Errore parsing sitemap: {e}")
    
    def _parse_txt_sitemap(self, content: str) -> None:
        """Parse sitemap TXT"""
        for line in content.split('\n'):
            url = line.strip()
            if url and self._is_valid_url(url):
                self.sitemap_urls.add(self._normalize_url(url))
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Estrae link validi dalla pagina
        
        Args:
            soup: BeautifulSoup object
            base_url: URL base per risolvere link relativi
            
        Returns:
            Lista di URL assoluti
        """
        links = []
        
        for tag in soup.find_all(['a', 'area']):
            href = tag.get('href')
            if not href:
                continue
            
            # Risolvi URL relativo
            absolute_url = urljoin(base_url, href)
            normalized = self._normalize_url(absolute_url)
            
            if self._is_valid_url(normalized) and normalized not in self.visited_urls:
                links.append(normalized)
        
        # Aggiungi URL dalla sitemap
        for sitemap_url in list(self.sitemap_urls)[:10]:
            if sitemap_url not in self.visited_urls:
                links.append(sitemap_url)
        
        return links
    
    def _normalize_url(self, url: str) -> str:
        """Normalizza URL per confronti"""
        parsed = urlparse(url.lower())
        
        # Rimuovi frammenti
        parsed = parsed._replace(fragment='')
        
        # Rimuovi trailing slash
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path[:-1]
        parsed = parsed._replace(path=path)
        
        # Rimuovi porta default
        netloc = parsed.netloc
        if netloc.endswith(':80') and parsed.scheme == 'http':
            netloc = netloc[:-3]
        elif netloc.endswith(':443') and parsed.scheme == 'https':
            netloc = netloc[:-4]
        parsed = parsed._replace(netloc=netloc)
        
        return urlunparse(parsed)
    
    def _is_valid_url(self, url: str) -> bool:
        """Verifica se URL è valido per crawling"""
        # Verifica pattern esclusi
        for pattern in self.excluded_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Verifica dominio
        parsed = urlparse(url)
        if parsed.netloc != self.base_domain:
            return False
        
        # Verifica schema
        if parsed.scheme not in ['http', 'https']:
            return False
        
        return True
    
    def _report_progress(self, message: str) -> None:
        """Riporta progresso se callback disponibile"""
        if self.progress_callback:
            self.progress_callback({
                'type': 'discovery',
                'pages_found': len(self.discovered_pages),
                'pages_visited': len(self.visited_urls),
                'queue_size': len(self.page_queue),
                'message': message
            })
    
    def get_priority_pages(self, limit: int = 10) -> List[PageInfo]:
        """
        Ottiene pagine con priorità più alta
        
        Args:
            limit: Numero massimo di pagine
            
        Returns:
            Lista di PageInfo ordinate per priorità
        """
        return self.discovered_pages[:limit]
    
    def get_pages_by_type(self, page_type: str) -> List[PageInfo]:
        """
        Ottiene pagine di un tipo specifico
        
        Args:
            page_type: Tipo di pagina
            
        Returns:
            Lista di PageInfo del tipo specificato
        """
        return [p for p in self.discovered_pages if p.page_type == page_type]
    
    def export_discovery_report(self, output_path: Path) -> None:
        """
        Esporta report completo della discovery
        
        Args:
            output_path: Path del file di output
        """
        report = {
            'base_url': self.base_url,
            'crawl_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_pages': len(self.discovered_pages),
            'pages_by_type': {},
            'pages': [p.to_dict() for p in self.discovered_pages]
        }
        
        # Conta per tipo
        for page in self.discovered_pages:
            page_type = page.page_type
            if page_type not in report['pages_by_type']:
                report['pages_by_type'][page_type] = 0
            report['pages_by_type'][page_type] += 1
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Discovery report esportato in {output_path}")