"""
EAA Scanner Web Application Package
Backend Flask con supporto LLM avanzato
"""

__version__ = "2.0.0"
__author__ = "EAA Scanner Team"

# Configura logging per package
import logging

# Crea logger specifico per webapp
logger = logging.getLogger('webapp')

# Evita propagazione doppia
logger.propagate = False

# Setup base se non già configurato
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)