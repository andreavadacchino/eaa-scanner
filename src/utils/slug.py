"""
Utility per generazione slug da stringhe
"""
import re
from typing import Optional


def slugify(text: str, max_length: Optional[int] = 50) -> str:
    """
    Converte una stringa in slug sicuro per filesystem
    
    Args:
        text: Stringa da convertire
        max_length: Lunghezza massima dello slug
        
    Returns:
        Stringa slug-ificata
    """
    if not text:
        return "unnamed"
    
    # Rimuovi caratteri non-ASCII
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # Sostituisci spazi e caratteri speciali con trattino
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text)
    
    # Rimuovi trattini iniziali/finali
    text = text.strip('-')
    
    # Tronca se necessario
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit('-', 1)[0]
    
    return text or "unnamed"