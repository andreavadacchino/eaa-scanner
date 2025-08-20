"""
Crawler multi-pagina per scansione completa siti web
"""
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import requests
import logging
from pathlib import Path
import re
import time
from collections import deque
import json

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Crawler per scoprire e scansionare multiple pagine di un sito
    """
    
    def __init__(self, 
                 base_url: str,
                 max_pages: int = 50,
                 max_depth: int = 3,
                 follow_external: bool = False,
                 allowed_domains: Optional[List[str]] = None,
                 excluded_patterns: Optional[List[str]] = None):
        """
        Inizializza il crawler
        
        Args:
            base_url: URL di partenza
            max_pages: Numero massimo di pagine da scansionare
            max_depth: Profondità massima di crawling
            follow_external: Se seguire link esterni
            allowed_domains: Domini permessi oltre al principale
            excluded_patterns: Pattern regex da escludere
        """
        self.base_url = self._normalize_url(base_url)
        self.base_domain = urlparse(self.base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.follow_external = follow_external
        
        # Domini permessi
        self.allowed_domains = set([self.base_domain])
        if allowed_domains:
            self.allowed_domains.update(allowed_domains)
        
        # Pattern da escludere (file binari, etc)
        self.excluded_patterns = excluded_patterns or [
            r'\.pdf$', r'\.zip$', r'\.exe$', r'\.dmg$',
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$',
            r'\.mp3$', r'\.mp4$', r'\.avi$', r'\.mov$',
            r'\.doc$', r'\.docx$', r'\.xls$', r'\.xlsx$',
            r'mailto:', r'tel:', r'javascript:', r'#'
        ]
        
        # Stato del crawling
        self.visited_urls: Set[str] = set()
        self.discovered_pages: List[Dict[str, any]] = []
        self.sitemap_urls: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; EAA-Scanner/1.0; +https://eaa-scanner.it)'
        })
        # Timeout più aggressivo per migliorare performance
        self.session.timeout = 5  # 5 secondi invece di default
    
    def crawl(self) -> List[Dict[str, any]]:
        """
        Esegue il crawling del sito
        
        Returns:
            Lista di pagine scoperte con metadati
        """
        logger.info(f"Inizio crawling di {self.base_url}")
        
        # Prima prova a trovare la sitemap
        self._discover_from_sitemap()
        
        # Poi esegui crawling ricorsivo
        self._crawl_recursive(self.base_url, depth=0)
        
        # Ordina per priorità (homepage prima, poi per profondità)
        self.discovered_pages.sort(key=lambda x: (x['depth'], x['url']))
        
        logger.info(f"Crawling completato: {len(self.discovered_pages)} pagine trovate")
        return self.discovered_pages
    
    def _crawl_recursive(self, url: str, depth: int) -> None:
        """
        Crawling ricorsivo delle pagine
        
        Args:
            url: URL da processare
            depth: Profondità corrente
        """
        if depth > self.max_depth:
            return
        
        if len(self.visited_urls) >= self.max_pages:
            return
        
        normalized_url = self._normalize_url(url)
        
        if normalized_url in self.visited_urls:
            return
        
        if not self._is_valid_url(normalized_url):
            return
        
        self.visited_urls.add(normalized_url)
        
        try:
            response = self.session.get(normalized_url, timeout=3)
            response.raise_for_status()
            
            # Verifica che sia HTML
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Estrai metadati della pagina
            page_info = self._extract_page_info(normalized_url, soup, depth)
            self.discovered_pages.append(page_info)
            
            # Trova tutti i link
            links = self._extract_links(soup, normalized_url)
            
            # Crawl link figli
            for link in links:
                if len(self.visited_urls) >= self.max_pages:
                    break
                self._crawl_recursive(link, depth + 1)
            
        except requests.RequestException as e:
            logger.warning(f"Errore crawling {normalized_url}: {e}")
        except Exception as e:
            logger.error(f"Errore inaspettato crawling {normalized_url}: {e}")
    
    def _discover_from_sitemap(self) -> None:
        """
        Scopre URL dalla sitemap se disponibile
        """
        sitemap_urls = [
            urljoin(self.base_url, 'sitemap.xml'),
            urljoin(self.base_url, 'sitemap_index.xml'),
            urljoin(self.base_url, 'sitemap.txt')
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                response = self.session.get(sitemap_url, timeout=2)
                if response.status_code == 200:
                    if sitemap_url.endswith('.xml'):
                        self._parse_xml_sitemap(response.text)
                    else:
                        self._parse_txt_sitemap(response.text)
                    logger.info(f"Trovate {len(self.sitemap_urls)} URL dalla sitemap")
                    break
            except:
                continue
    
    def _parse_xml_sitemap(self, content: str) -> None:
        """
        Parse sitemap XML
        
        Args:
            content: Contenuto XML della sitemap
        """
        try:
            try:
                soup = BeautifulSoup(content, 'xml')
            except:
                # Fallback to lxml-xml if xml parser not available
                soup = BeautifulSoup(content, 'lxml-xml')
            
            # Trova URL diretti
            for loc in soup.find_all('loc'):
                url = loc.text.strip()
                if self._is_valid_url(url):
                    self.sitemap_urls.add(self._normalize_url(url))
            
            # Se è un sitemap index, processa le sub-sitemap
            for sitemap in soup.find_all('sitemap'):
                loc = sitemap.find('loc')
                if loc:
                    try:
                        sub_response = self.session.get(loc.text.strip(), timeout=5)
                        if sub_response.status_code == 200:
                            self._parse_xml_sitemap(sub_response.text)
                    except:
                        continue
        except Exception as e:
            logger.warning(f"Errore parsing sitemap XML: {e}")
    
    def _parse_txt_sitemap(self, content: str) -> None:
        """
        Parse sitemap TXT
        
        Args:
            content: Contenuto TXT della sitemap
        """
        for line in content.split('\n'):
            url = line.strip()
            if url and self._is_valid_url(url):
                self.sitemap_urls.add(self._normalize_url(url))
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Estrae tutti i link validi dalla pagina
        
        Args:
            soup: BeautifulSoup object della pagina
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
        
        # Aggiungi URL dalla sitemap se nella stessa profondità
        for sitemap_url in self.sitemap_urls:
            if sitemap_url not in self.visited_urls and len(links) < 20:
                links.append(sitemap_url)
        
        return links
    
    def _extract_page_info(self, url: str, soup: BeautifulSoup, depth: int) -> Dict[str, any]:
        """
        Estrae informazioni sulla pagina
        
        Args:
            url: URL della pagina
            soup: BeautifulSoup object
            depth: Profondità nel crawling
            
        Returns:
            Dizionario con metadati della pagina
        """
        # Estrai titolo
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else 'Senza titolo'
        
        # Estrai meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        # Estrai lingua
        html_tag = soup.find('html')
        lang = html_tag.get('lang', 'it') if html_tag else 'it'
        
        # Conta elementi interattivi
        forms = len(soup.find_all('form'))
        inputs = len(soup.find_all(['input', 'textarea', 'select']))
        buttons = len(soup.find_all(['button', 'input[type="submit"]']))
        images = len(soup.find_all('img'))
        videos = len(soup.find_all(['video', 'iframe']))
        
        # Determina tipo di pagina
        page_type = self._determine_page_type(url, soup)
        
        # Calcola priorità per scansione
        priority = self._calculate_priority(url, page_type, depth)
        
        return {
            'url': url,
            'title': title,
            'description': description,
            'language': lang,
            'page_type': page_type,
            'depth': depth,
            'priority': priority,
            'elements': {
                'forms': forms,
                'inputs': inputs,
                'buttons': buttons,
                'images': images,
                'videos': videos
            },
            'discovered_at': time.time()
        }
    
    def _determine_page_type(self, url: str, soup: BeautifulSoup) -> str:
        """
        Determina il tipo di pagina
        
        Args:
            url: URL della pagina
            soup: BeautifulSoup object
            
        Returns:
            Tipo di pagina
        """
        url_lower = url.lower()
        
        # Check URL patterns
        if url == self.base_url or url == self.base_url + '/':
            return 'homepage'
        elif 'contact' in url_lower or 'contatti' in url_lower:
            return 'contact'
        elif 'about' in url_lower or 'chi-siamo' in url_lower:
            return 'about'
        elif 'login' in url_lower or 'signin' in url_lower:
            return 'authentication'
        elif 'search' in url_lower or 'ricerca' in url_lower:
            return 'search'
        elif 'cart' in url_lower or 'carrello' in url_lower:
            return 'ecommerce'
        elif 'blog' in url_lower or 'news' in url_lower:
            return 'content'
        
        # Check page content
        forms = soup.find_all('form')
        if forms:
            for form in forms:
                if form.find(['input[type="password"]', 'input[name="password"]']):
                    return 'authentication'
                elif form.find(['input[type="search"]', 'input[name="q"]']):
                    return 'search'
            return 'form'
        
        # Check for article/blog content
        if soup.find('article') or soup.find(class_=re.compile('article|post|blog')):
            return 'content'
        
        return 'general'
    
    def _calculate_priority(self, url: str, page_type: str, depth: int) -> int:
        """
        Calcola priorità della pagina per scansione
        
        Args:
            url: URL della pagina
            page_type: Tipo di pagina
            depth: Profondità nel crawling
            
        Returns:
            Score di priorità (0-100)
        """
        priority = 50  # Base
        
        # Bonus per tipo di pagina
        type_scores = {
            'homepage': 100,
            'authentication': 90,
            'contact': 85,
            'form': 80,
            'search': 75,
            'ecommerce': 70,
            'about': 60,
            'content': 50,
            'general': 40
        }
        priority = type_scores.get(page_type, 50)
        
        # Penalità per profondità
        priority -= (depth * 10)
        
        # Bonus se dalla sitemap
        if url in self.sitemap_urls:
            priority += 10
        
        return max(0, min(100, priority))
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalizza URL per confronti consistenti
        
        Args:
            url: URL da normalizzare
            
        Returns:
            URL normalizzato
        """
        parsed = urlparse(url.lower())
        
        # Rimuovi frammenti
        parsed = parsed._replace(fragment='')
        
        # Rimuovi trailing slash per non-root paths
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
        """
        Verifica se URL è valido per crawling
        
        Args:
            url: URL da verificare
            
        Returns:
            True se valido
        """
        # Verifica pattern esclusi
        for pattern in self.excluded_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Verifica dominio
        parsed = urlparse(url)
        if not self.follow_external:
            if parsed.netloc not in self.allowed_domains:
                return False
        
        # Verifica schema
        if parsed.scheme not in ['http', 'https']:
            return False
        
        return True
    
    def get_priority_pages(self, limit: int = 10) -> List[Dict[str, any]]:
        """
        Ottiene le pagine con priorità più alta
        
        Args:
            limit: Numero massimo di pagine
            
        Returns:
            Lista di pagine ordinate per priorità
        """
        sorted_pages = sorted(
            self.discovered_pages,
            key=lambda x: x['priority'],
            reverse=True
        )
        return sorted_pages[:limit]
    
    def get_pages_by_type(self, page_type: str) -> List[Dict[str, any]]:
        """
        Ottiene pagine di un tipo specifico
        
        Args:
            page_type: Tipo di pagina
            
        Returns:
            Lista di pagine del tipo specificato
        """
        return [p for p in self.discovered_pages if p['page_type'] == page_type]
    
    def export_sitemap(self, output_path: Path) -> None:
        """
        Esporta le pagine scoperte come sitemap
        
        Args:
            output_path: Path del file di output
        """
        sitemap_data = {
            'base_url': self.base_url,
            'crawl_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_pages': len(self.discovered_pages),
            'pages': self.discovered_pages
        }
        
        with open(output_path, 'w') as f:
            json.dump(sitemap_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sitemap esportata in {output_path}")