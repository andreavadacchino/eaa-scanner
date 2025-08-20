"""
Template Detector per identificare e raggruppare pagine simili
Usa analisi DOM e clustering per identificare template comuni
"""

import hashlib
import logging
from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict
import re

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import DBSCAN
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None
    print("Attenzione: scikit-learn non installato. Installa con: pip install scikit-learn numpy")

logger = logging.getLogger(__name__)


class TemplateDetector:
    """
    Identifica template comuni tra le pagine analizzando struttura DOM
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Inizializza il detector
        
        Args:
            similarity_threshold: Soglia di similarità per considerare stesso template
        """
        self.similarity_threshold = similarity_threshold
        self.templates: Dict[str, List[Dict]] = defaultdict(list)
        self.template_signatures: Dict[str, str] = {}
        
    def detect_templates(self, pages: List[Dict]) -> Dict[str, Dict]:
        """
        Identifica template tra le pagine
        
        Args:
            pages: Lista di PageInfo come dizionari
            
        Returns:
            Dizionario con template identificati
        """
        if len(pages) < 2:
            return self._single_page_template(pages)
        
        # Estrai fingerprints DOM
        fingerprints = []
        for page in pages:
            fp = page.get('dom_structure', '')
            if not fp:
                fp = self._generate_simple_fingerprint(page)
            fingerprints.append(fp)
        
        # Calcola matrice di similarità
        similarity_matrix = self._calculate_similarity_matrix(fingerprints)
        
        # Clustering delle pagine
        clusters = self._cluster_pages(similarity_matrix)
        
        # Crea template dai cluster
        templates = self._create_templates_from_clusters(pages, clusters)
        
        return templates
    
    def _generate_simple_fingerprint(self, page: Dict) -> str:
        """
        Genera fingerprint semplice se DOM structure non disponibile
        
        Args:
            page: Dizionario PageInfo
            
        Returns:
            Fingerprint string
        """
        # Usa caratteristiche della pagina come fallback
        features = [
            f"type:{page.get('page_type', 'unknown')}",
            f"forms:{page.get('forms_count', 0)}",
            f"inputs:{page.get('inputs_count', 0)}",
            f"buttons:{page.get('buttons_count', 0)}",
            f"images:{page.get('images_count', 0)}",
            f"videos:{page.get('videos_count', 0)}",
            f"h1:{page.get('has_h1', False)}",
            f"nav:{page.get('has_nav', False)}",
            f"main:{page.get('has_main', False)}",
            f"footer:{page.get('has_footer', False)}"
        ]
        return "|".join(features)
    
    def _calculate_similarity_matrix(self, fingerprints: List[str]) -> Any:
        """
        Calcola matrice di similarità tra fingerprints
        
        Args:
            fingerprints: Lista di fingerprint DOM
            
        Returns:
            Matrice di similarità
        """
        if not SKLEARN_AVAILABLE:
            # Fallback semplice senza sklearn
            n = len(fingerprints)
            matrix = [[0.0] * n for _ in range(n)]
            
            # Calcola similarità semplice basata su features comuni
            for i in range(n):
                for j in range(n):
                    if i == j:
                        matrix[i][j] = 1.0
                    else:
                        # Similarità basata su features comuni
                        features_i = set(fingerprints[i].split('|'))
                        features_j = set(fingerprints[j].split('|'))
                        if features_i and features_j:
                            common = len(features_i & features_j)
                            total = len(features_i | features_j)
                            matrix[i][j] = common / total if total > 0 else 0.0
            
            return matrix
        
        try:
            # Usa TF-IDF per vettorizzare fingerprints
            vectorizer = TfidfVectorizer(
                tokenizer=lambda x: x.split('|'),
                token_pattern=None,
                lowercase=False
            )
            
            # Trasforma in vettori
            vectors = vectorizer.fit_transform(fingerprints)
            
            # Calcola similarità coseno
            similarity_matrix = cosine_similarity(vectors)
            
            return similarity_matrix
            
        except Exception as e:
            logger.warning(f"Errore calcolo similarità: {e}")
            # Fallback: matrice identità
            n = len(fingerprints)
            if SKLEARN_AVAILABLE and np:
                return np.eye(n)
            else:
                # Matrice identità senza numpy
                matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
                return matrix
    
    def _cluster_pages(self, similarity_matrix: Any) -> List[int]:
        """
        Clusterizza pagine basandosi su similarità
        
        Args:
            similarity_matrix: Matrice di similarità
            
        Returns:
            Lista di cluster IDs per ogni pagina
        """
        if not SKLEARN_AVAILABLE:
            # Fallback: clustering semplice basato su threshold
            n = len(similarity_matrix) if isinstance(similarity_matrix, list) else similarity_matrix.shape[0]
            clusters = list(range(n))  # Inizialmente ogni pagina è un cluster
            
            # Raggruppa pagine simili
            for i in range(n):
                for j in range(i + 1, n):
                    sim = similarity_matrix[i][j] if isinstance(similarity_matrix, list) else similarity_matrix[i, j]
                    if sim >= self.similarity_threshold:
                        # Assegna stesso cluster
                        clusters[j] = clusters[i]
            
            return clusters
        
        try:
            # Converti similarità in distanza
            distance_matrix = 1 - similarity_matrix
            
            # DBSCAN clustering
            clustering = DBSCAN(
                eps=1 - self.similarity_threshold,
                min_samples=1,
                metric='precomputed'
            )
            
            clusters = clustering.fit_predict(distance_matrix)
            
            return clusters.tolist()
            
        except Exception as e:
            logger.warning(f"Errore clustering: {e}")
            # Fallback: ogni pagina è un template
            n = len(similarity_matrix) if isinstance(similarity_matrix, list) else similarity_matrix.shape[0]
            return list(range(n))
    
    def _create_templates_from_clusters(self, pages: List[Dict], 
                                       clusters: List[int]) -> Dict[str, Dict]:
        """
        Crea template dai cluster identificati
        
        Args:
            pages: Lista di pagine
            clusters: Lista di cluster IDs
            
        Returns:
            Dizionario con template
        """
        templates = {}
        cluster_pages = defaultdict(list)
        
        # Raggruppa pagine per cluster
        for page, cluster_id in zip(pages, clusters):
            cluster_pages[cluster_id].append(page)
        
        # Crea template per ogni cluster
        for cluster_id, cluster_page_list in cluster_pages.items():
            template_id = f"template_{cluster_id + 1}"
            
            # Determina nome template
            template_name = self._determine_template_name(cluster_page_list)
            
            # Trova pagina rappresentativa
            representative = self._find_representative_page(cluster_page_list)
            
            # Calcola statistiche template
            template_info = {
                'id': template_id,
                'name': template_name,
                'page_count': len(cluster_page_list),
                'pages': cluster_page_list,
                'representative_url': representative['url'],
                'representative_title': representative.get('title', ''),
                'common_elements': self._extract_common_elements(cluster_page_list),
                'average_priority': sum([p.get('priority', 50) for p in cluster_page_list]) / len(cluster_page_list) if cluster_page_list else 50,
                'page_types': list(set(p.get('page_type', 'general') for p in cluster_page_list))
            }
            
            templates[template_id] = template_info
        
        return templates
    
    def _determine_template_name(self, pages: List[Dict]) -> str:
        """
        Determina nome descrittivo per template
        
        Args:
            pages: Pagine del template
            
        Returns:
            Nome template
        """
        # Conta tipi di pagina più comuni
        type_counts = defaultdict(int)
        for page in pages:
            page_type = page.get('page_type', 'general')
            type_counts[page_type] += 1
        
        # Tipo più comune
        if type_counts:
            most_common_type = max(type_counts, key=type_counts.get)
            
            # Nomi user-friendly
            type_names = {
                'homepage': 'Homepage',
                'product': 'Pagine Prodotto',
                'article': 'Articoli/Blog',
                'form': 'Moduli',
                'checkout': 'Checkout',
                'authentication': 'Autenticazione',
                'contact': 'Contatti',
                'search': 'Ricerca',
                'about': 'Chi Siamo',
                'legal': 'Pagine Legali',
                'general': 'Pagine Generiche'
            }
            
            base_name = type_names.get(most_common_type, 'Template')
            
            # Aggiungi conteggio se più di una pagina
            if len(pages) > 1:
                return f"{base_name} ({len(pages)} pagine)"
            else:
                return base_name
        
        return f"Template ({len(pages)} pagine)"
    
    def _find_representative_page(self, pages: List[Dict]) -> Dict:
        """
        Trova la pagina più rappresentativa del template
        
        Args:
            pages: Pagine del template
            
        Returns:
            Pagina rappresentativa
        """
        if not pages:
            return {}
        
        # Criteri per scegliere rappresentativa:
        # 1. Priorità più alta
        # 2. Profondità minore
        # 3. Più elementi interattivi
        
        def score_page(page):
            score = 0
            score += page.get('priority', 0) * 2  # Peso doppio per priorità
            score -= page.get('depth', 0) * 10    # Penalità per profondità
            score += page.get('forms_count', 0) * 5
            score += page.get('inputs_count', 0) * 2
            score += page.get('buttons_count', 0) * 2
            return score
        
        # Trova pagina con score massimo
        representative = max(pages, key=score_page)
        return representative
    
    def _extract_common_elements(self, pages: List[Dict]) -> Dict[str, any]:
        """
        Estrae elementi comuni tra le pagine del template
        
        Args:
            pages: Pagine del template
            
        Returns:
            Dizionario con elementi comuni
        """
        if not pages:
            return {}
        
        common = {
            'all_have_forms': all(p.get('forms_count', 0) > 0 for p in pages),
            'all_have_h1': all(p.get('has_h1', False) for p in pages),
            'all_have_nav': all(p.get('has_nav', False) for p in pages),
            'all_have_main': all(p.get('has_main', False) for p in pages),
            'all_have_footer': all(p.get('has_footer', False) for p in pages),
            'avg_forms': sum([p.get('forms_count', 0) for p in pages]) / len(pages) if pages else 0,
            'avg_inputs': sum([p.get('inputs_count', 0) for p in pages]) / len(pages) if pages else 0,
            'avg_images': sum([p.get('images_count', 0) for p in pages]) / len(pages) if pages else 0,
            'common_lang': self._most_common([p.get('lang', 'it') for p in pages])
        }
        
        return common
    
    def _most_common(self, items: List) -> any:
        """Trova elemento più comune in lista"""
        if not items:
            return None
        
        counts = defaultdict(int)
        for item in items:
            counts[item] += 1
        
        return max(counts, key=counts.get)
    
    def _single_page_template(self, pages: List[Dict]) -> Dict[str, Dict]:
        """
        Gestisce caso con singola pagina
        
        Args:
            pages: Lista con una pagina
            
        Returns:
            Template per singola pagina
        """
        if not pages:
            return {}
        
        page = pages[0]
        return {
            'template_1': {
                'id': 'template_1',
                'name': f"{page.get('page_type', 'Homepage').title()}",
                'page_count': 1,
                'pages': [page],
                'representative_url': page.get('url', ''),
                'representative_title': page.get('title', ''),
                'common_elements': self._extract_common_elements([page]),
                'average_priority': page.get('priority', 100),
                'page_types': [page.get('page_type', 'homepage')]
            }
        }
    
    def get_template_summary(self, templates: Dict[str, Dict]) -> Dict:
        """
        Genera sommario dei template identificati
        
        Args:
            templates: Template identificati
            
        Returns:
            Sommario
        """
        total_pages = sum(t['page_count'] for t in templates.values())
        
        summary = {
            'total_templates': len(templates),
            'total_pages': total_pages,
            'templates': []
        }
        
        for template_id, template_info in templates.items():
            summary['templates'].append({
                'id': template_id,
                'name': template_info['name'],
                'page_count': template_info['page_count'],
                'representative_url': template_info['representative_url'],
                'priority': template_info['average_priority'],
                'has_forms': template_info['common_elements'].get('all_have_forms', False)
            })
        
        # Ordina per priorità
        summary['templates'].sort(key=lambda x: x['priority'], reverse=True)
        
        return summary
    
    def suggest_sampling(self, templates: Dict[str, Dict], 
                        max_pages: int = 10) -> List[Dict]:
        """
        Suggerisce campionamento WCAG-EM compliant
        
        Args:
            templates: Template identificati
            max_pages: Numero massimo di pagine da campionare
            
        Returns:
            Lista di pagine suggerite per scansione
        """
        selected_pages = []
        
        # 1. Sempre includi homepage
        for template in templates.values():
            for page in template['pages']:
                if page.get('page_type') == 'homepage':
                    selected_pages.append(page)
                    break
        
        # 2. Una pagina rappresentativa per template (max 2 per template)
        for template in sorted(templates.values(), 
                              key=lambda x: x['average_priority'], 
                              reverse=True):
            
            # Salta se già selezionate troppe pagine
            if len(selected_pages) >= max_pages:
                break
            
            # Prendi 1-2 pagine per template basate su priorità
            template_pages = sorted(template['pages'], 
                                   key=lambda x: x.get('priority', 0),
                                   reverse=True)
            
            pages_to_add = 1 if template['page_count'] <= 5 else 2
            
            for page in template_pages[:pages_to_add]:
                if page not in selected_pages:
                    selected_pages.append(page)
                    if len(selected_pages) >= max_pages:
                        break
        
        # 3. Assicura presenza di pagine critiche
        critical_types = ['checkout', 'authentication', 'contact', 'form']
        for c_type in critical_types:
            if len(selected_pages) >= max_pages:
                break
            
            # Cerca pagina di questo tipo non ancora selezionata
            for template in templates.values():
                for page in template['pages']:
                    if page.get('page_type') == c_type and page not in selected_pages:
                        selected_pages.append(page)
                        break
        
        return selected_pages[:max_pages]