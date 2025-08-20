"""
Utility per lettura input da file (TXT, CSV, JSON)
"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    Valida che una stringa sia un URL valido
    
    Args:
        url: URL da validare
        
    Returns:
        True se l'URL è valido
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def read_input_file(file_path: Path) -> List[Dict[str, str]]:
    """
    Legge un file di input e restituisce lista di record
    
    Supporta:
    - TXT: una URL per riga
    - CSV: colonne url, company_name (opz), email (opz)
    - JSON: array di oggetti con campi url, company_name, email
    
    Args:
        file_path: Path al file di input
        
    Returns:
        Lista di dizionari con url, company_name, email
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File non trovato: {file_path}")
    
    results = []
    suffix = file_path.suffix.lower()
    
    if suffix == '.txt':
        # File TXT: una URL per riga
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if validate_url(line):
                        results.append({
                            'url': line,
                            'company_name': '',
                            'email': ''
                        })
    
    elif suffix == '.csv':
        # File CSV con header
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('url', '').strip()
                if url and validate_url(url):
                    results.append({
                        'url': url,
                        'company_name': row.get('company_name', '').strip(),
                        'email': row.get('email', '').strip()
                    })
    
    elif suffix == '.json':
        # File JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        url = item.get('url', '').strip()
                        if url and validate_url(url):
                            results.append({
                                'url': url,
                                'company_name': item.get('company_name', '').strip(),
                                'email': item.get('email', '').strip()
                            })
    
    else:
        raise ValueError(f"Formato file non supportato: {suffix}")
    
    # Deduplica per URL
    seen_urls = set()
    deduplicated = []
    for item in results:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            deduplicated.append(item)
    
    return deduplicated


def write_output_file(file_path: Path, data: Any, format: str = 'json') -> None:
    """
    Scrive dati su file in formato specificato
    
    Args:
        file_path: Path del file di output
        data: Dati da scrivere
        format: Formato output (json, html, txt)
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif format == 'html' or format == 'txt':
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(data))
    else:
        raise ValueError(f"Formato non supportato: {format}")