"""
Notifiche Telegram per EAA Scanner
"""
from typing import Optional, Tuple
import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


def send_telegram_notification(
    message: str,
    bot_token: str,
    chat_id: str,
    pdf_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Invia notifica Telegram con opzionale allegato PDF
    
    Args:
        message: Messaggio da inviare
        bot_token: Token del bot Telegram
        chat_id: ID della chat/canale
        pdf_path: Path al PDF da allegare (opzionale)
        
    Returns:
        Tuple di (successo, messaggio)
    """
    if not bot_token or not chat_id:
        logger.warning("Token bot o chat ID mancante")
        return False, "Configurazione Telegram incompleta"
    
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    try:
        # Invia messaggio di testo
        text_url = f"{base_url}/sendMessage"
        text_data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(text_url, json=text_data, timeout=10)
        response.raise_for_status()
        
        # Se c'è un PDF, invialo come documento
        if pdf_path and pdf_path.exists():
            doc_url = f"{base_url}/sendDocument"
            with open(pdf_path, 'rb') as f:
                files = {'document': (pdf_path.name, f, 'application/pdf')}
                doc_data = {
                    'chat_id': chat_id,
                    'caption': 'Report Accessibilità EAA'
                }
                doc_response = requests.post(doc_url, data=doc_data, files=files, timeout=30)
                doc_response.raise_for_status()
        
        logger.info(f"Notifica Telegram inviata a chat {chat_id}")
        return True, "Notifica inviata con successo"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Errore invio Telegram: {e}")
        return False, f"Errore invio Telegram: {str(e)}"
    except Exception as e:
        logger.error(f"Errore generico Telegram: {e}")
        return False, f"Errore: {str(e)}"


def format_telegram_message(scan_data: dict) -> str:
    """
    Formatta i dati della scansione per Telegram
    
    Args:
        scan_data: Dati normalizzati della scansione
        
    Returns:
        Messaggio formattato per Telegram
    """
    compliance = scan_data.get("compliance", {})
    score = compliance.get("overall_score", 0)
    level = compliance.get("compliance_level", "non_conforme")
    
    # Emoji basate su score
    if score >= 85:
        emoji = "✅"
    elif score >= 60:
        emoji = "⚠️"
    else:
        emoji = "❌"
    
    # Formatta messaggio
    message = f"""
<b>{emoji} Report Accessibilità Completato</b>

<b>Azienda:</b> {scan_data.get("company_name", "N/A")}
<b>URL:</b> {scan_data.get("url", "N/A")}
<b>Score:</b> {score}/100
<b>Conformità:</b> {level.replace("_", " ").title()}

<b>Riepilogo:</b>
• Errori: {len(scan_data.get("detailed_results", {}).get("errors", []))}
• Avvisi: {len(scan_data.get("detailed_results", {}).get("warnings", []))}

<i>Scansione completata il {scan_data.get("scan_metadata", {}).get("scan_date", "N/A")}</i>
"""
    
    return message.strip()