"""
Sistema di notifiche per EAA Scanner
"""
from .telegram import send_telegram_notification

__all__ = ['send_telegram_notification']