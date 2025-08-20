#!/usr/bin/env python3
"""
Avvia il server WebSocket per il dashboard real-time
"""

import sys
from pathlib import Path
import asyncio
import logging

# Aggiungi directory al path
sys.path.insert(0, str(Path(__file__).parent))

from eaa_scanner.page_sampler.realtime_progress import RealtimeProgress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Avvia server WebSocket standalone"""
    logger.info("Avvio server WebSocket per dashboard real-time...")
    
    # Crea server
    progress_server = RealtimeProgress(port=8765, host='localhost')
    
    # Avvia server
    await progress_server.start_server()

if __name__ == "__main__":
    try:
        print("🚀 WebSocket Server in ascolto su ws://localhost:8765")
        print("   Apri http://localhost:8000/smart-dashboard per il dashboard")
        print("   Premi Ctrl+C per fermare il server")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Server WebSocket fermato")