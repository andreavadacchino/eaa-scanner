"""
Processori per normalizzazione risultati scanner
"""
from .normalize import normalize_all
from .process_wave import process_wave
from .process_pa11y import process_pa11y

__all__ = ['normalize_all', 'process_wave', 'process_pa11y']