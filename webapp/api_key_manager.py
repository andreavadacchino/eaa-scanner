"""
Sistema di gestione sicura delle API Keys per EAA Scanner.
Supporta crittografia, validazione e storage persistente.
"""

import os
import json
import base64
import logging
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Validazione API
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Gestore sicuro delle API Keys con crittografia e validazione"""
    
    def __init__(self, storage_file: str = ".api_keys.enc"):
        """
        Inizializza il gestore API Keys.
        
        Args:
            storage_file: Nome del file di storage crittografato
        """
        self.storage_path = Path(__file__).parent.parent / storage_file
        self._fernet = None
        self._keys = {}
        self._initialize_encryption()
        self.load_keys()

    def _load_env_defaults(self):
        """Carica chiavi da variabili d'ambiente come default sicuro (senza scrivere su file)."""
        env_openai = os.getenv('OPENAI_API_KEY')
        env_wave = os.getenv('WAVE_API_KEY')
        if env_openai and not self._keys.get('openai'):
            self._keys['openai'] = env_openai
        if env_wave and not self._keys.get('wave'):
            self._keys['wave'] = env_wave
    
    def _initialize_encryption(self):
        """Inizializza il sistema di crittografia con chiave derivata"""
        # Usa l'hostname e alcuni dati fissi per derivare la chiave
        salt = b'eaa_scanner_salt_v1'  # Salt fisso per la derivazione
        
        # Combina hostname e salt per una chiave specifica al sistema
        hostname = os.uname().nodename if hasattr(os, 'uname') else 'localhost'
        password = f"eaa_scanner_{hostname}_key".encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self._fernet = Fernet(key)
    
    def save_keys(self, openai_key: Optional[str] = None, wave_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Salva le API keys in modo sicuro.
        
        Args:
            openai_key: Chiave API OpenAI
            wave_key: Chiave API WAVE
            
        Returns:
            Dizionario con stato del salvataggio e validazione
        """
        try:
            # Carica le chiavi esistenti prima di aggiornarle
            self.load_keys()
            
            # Funzione helper per verificare se è un valore mascherato
            def is_masked_value(value: str) -> bool:
                if not value:
                    return False
                # Controlla pattern mascherati comuni (es. "sk-t...6789", "test...-key")
                return '...' in value or (value.count('*') > 3)
            
            # Mantieni le chiavi esistenti se non vengono fornite nuove o se sono mascherate
            if openai_key is not None and not is_masked_value(openai_key):
                self._keys['openai'] = openai_key
            if wave_key is not None and not is_masked_value(wave_key):
                self._keys['wave'] = wave_key
            
            # Cripta e salva
            data_to_encrypt = json.dumps(self._keys)
            encrypted_data = self._fernet.encrypt(data_to_encrypt.encode())
            
            self.storage_path.write_bytes(encrypted_data)
            
            # Valida le chiavi salvate
            validation_results = self._validate_all_keys()
            
            logger.info(f"API keys salvate con successo in {self.storage_path}")
            
            return {
                'success': True,
                'message': 'Chiavi API salvate con successo',
                'validation': validation_results
            }
            
        except Exception as e:
            logger.error(f"Errore durante il salvataggio delle chiavi: {e}")
            return {
                'success': False,
                'message': f'Errore durante il salvataggio: {str(e)}',
                'validation': {}
            }
    
    def load_keys(self) -> bool:
        """
        Carica le API keys dal file crittografato.
        
        Returns:
            True se il caricamento è avvenuto con successo
        """
        try:
            if not self.storage_path.exists():
                logger.info("File API keys non trovato, caricamento da variabili d'ambiente se presenti")
                self._keys = {}
                # Carica da env di default
                self._load_env_defaults()
                return False
            
            encrypted_data = self.storage_path.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            self._keys = json.loads(decrypted_data.decode())
            
            # Carica eventuali default da env se mancano
            self._load_env_defaults()
            logger.info("API keys caricate con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante il caricamento delle chiavi: {e}")
            self._keys = {}
            # Carica eventuali default da env anche in caso di errore
            self._load_env_defaults()
            return False
    
    def get_key(self, key_type: str) -> Optional[str]:
        """
        Ottieni una chiave API specifica.
        
        Args:
            key_type: Tipo di chiave ('openai' o 'wave')
            
        Returns:
            Chiave API o None se non presente
        """
        return self._keys.get(key_type)
    
    def get_keys_status(self) -> Dict[str, Any]:
        """
        Ottieni lo stato delle chiavi senza esporle.
        
        Returns:
            Dizionario con stato delle chiavi e validazione
        """
        status = {}
        
        for key_type in ['openai', 'wave']:
            key_value = self._keys.get(key_type)
            if key_value:
                # Mostra solo i primi e ultimi caratteri della chiave
                masked_key = self._mask_key(key_value)
                status[key_type] = {
                    'present': True,
                    'masked_value': masked_key,
                    'length': len(key_value)
                }
            else:
                status[key_type] = {
                    'present': False,
                    'masked_value': None,
                    'length': 0
                }
        
        # Aggiungi risultati di validazione
        validation_results = self._validate_all_keys()
        
        return {
            'keys': status,
            'validation': validation_results,
            'storage_exists': self.storage_path.exists()
        }
    
    def validate_openai(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida la chiave API OpenAI.
        
        Args:
            api_key: Chiave da validare (usa quella memorizzata se None)
            
        Returns:
            Dizionario con risultato della validazione
        """
        key_to_test = api_key or self._keys.get('openai')
        
        if not key_to_test:
            return {
                'valid': False,
                'error': 'Chiave API non presente',
                'details': 'Nessuna chiave OpenAI configurata'
            }
        
        try:
            # Test basic della connessione OpenAI
            client = OpenAI(api_key=key_to_test)
            
            # Chiamata minima per testare la validità
            models = client.models.list()
            
            return {
                'valid': True,
                'message': 'Chiave OpenAI valida',
                'details': f'Accesso verificato, {len(models.data)} modelli disponibili'
            }
            
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                return {
                    'valid': False,
                    'error': 'Chiave API non valida',
                    'details': 'La chiave OpenAI non è autorizzata'
                }
            elif "403" in error_msg or "Forbidden" in error_msg:
                return {
                    'valid': False,
                    'error': 'Accesso negato',
                    'details': 'La chiave OpenAI non ha i permessi necessari'
                }
            else:
                return {
                    'valid': False,
                    'error': 'Errore di connessione',
                    'details': f'Impossibile validare la chiave: {error_msg}'
                }
    
    def validate_wave(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Valida la chiave API WAVE.
        
        Args:
            api_key: Chiave da validare (usa quella memorizzata se None)
            
        Returns:
            Dizionario con risultato della validazione
        """
        key_to_test = api_key or self._keys.get('wave')
        
        if not key_to_test:
            return {
                'valid': False,
                'error': 'Chiave API non presente',
                'details': 'Nessuna chiave WAVE configurata'
            }
        
        try:
            # Test della connessione WAVE API
            url = "https://wave.webaim.org/api/request"
            params = {
                'key': key_to_test,
                'url': 'https://example.com',  # URL di test
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return {
                    'valid': True,
                    'message': 'Chiave WAVE valida',
                    'details': 'Connessione API verificata con successo'
                }
            elif response.status_code == 401:
                return {
                    'valid': False,
                    'error': 'Chiave API non valida',
                    'details': 'La chiave WAVE non è autorizzata'
                }
            elif response.status_code == 403:
                return {
                    'valid': False,
                    'error': 'Accesso negato',
                    'details': 'La chiave WAVE non ha i permessi necessari'
                }
            else:
                return {
                    'valid': False,
                    'error': f'Errore HTTP {response.status_code}',
                    'details': f'Risposta API non valida: {response.text[:100]}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'valid': False,
                'error': 'Timeout di connessione',
                'details': 'WAVE API non risponde entro il timeout'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': 'Errore di connessione',
                'details': f'Impossibile validare la chiave: {str(e)}'
            }
    
    def _validate_all_keys(self) -> Dict[str, Dict[str, Any]]:
        """Valida tutte le chiavi presenti"""
        results = {}
        
        if self._keys.get('openai'):
            results['openai'] = self.validate_openai()
        
        if self._keys.get('wave'):
            results['wave'] = self.validate_wave()
        
        return results
    
    def _mask_key(self, key: str) -> str:
        """
        Maschera una chiave API per la visualizzazione sicura.
        
        Args:
            key: Chiave da mascherare
            
        Returns:
            Chiave mascherata (es. "sk-abc...xyz")
        """
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}...{key[-4:]}"
    
    def delete_keys(self) -> bool:
        """
        Elimina tutte le chiavi salvate.
        
        Returns:
            True se l'eliminazione è avvenuta con successo
        """
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
            
            self._keys = {}
            logger.info("Tutte le API keys eliminate con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante l'eliminazione delle chiavi: {e}")
            return False


# Istanza globale del manager
_api_key_manager = None

def get_api_key_manager() -> APIKeyManager:
    """Ottieni l'istanza globale del manager API keys"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
