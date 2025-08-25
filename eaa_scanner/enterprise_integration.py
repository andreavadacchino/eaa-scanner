"""
Enterprise Integration per FastAPI
Bridge tra sistema enterprise e FastAPI esistente
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from .config import Config
from .enterprise_core import EnterpriseScanOrchestrator
from .models.scanner_results import AggregatedResults

logger = logging.getLogger(__name__)


class FastAPIEnterpriseAdapter:
    """
    Adapter per integrare sistema enterprise con FastAPI esistente
    Mantiene backward compatibility con API esistenti
    """
    
    def __init__(self):
        self.orchestrator = EnterpriseScanOrchestrator(enable_parallel=False)
        self.active_scans = {}  # Track scan status per WebSocket support
    
    def run_enterprise_scan_for_api(
        self,
        url: str,
        company_name: str,
        email: str,
        wave_api_key: Optional[str] = None,
        simulate: bool = False,
        event_monitor=None,
        scan_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Entry point per API FastAPI con enterprise system
        
        Returns:
            API-compatible response con paths e metadata
        """
        
        try:
            # Crea configurazione dal request
            cfg = Config(
                url=url,
                company_name=company_name,
                email=email,
                wave_api_key=wave_api_key,
                simulate=simulate
            )
            
            # Log configurazione per debugging
            logger.info(f"🏢 Enterprise scan request: {company_name} - {url}")
            logger.info(f"Simulate: {simulate}, Wave API: {wave_api_key is not None}")
            
            # Esegui scansione enterprise
            enterprise_result = self.orchestrator.run_enterprise_scan(
                cfg=cfg,
                output_root=Path("output"),
                event_monitor=event_monitor,
                scan_id=scan_id,
                enable_pdf=True,
                max_retries=2
            )
            
            # Converti risultato per API compatibility
            api_response = self._convert_enterprise_to_api_format(enterprise_result)
            
            logger.info(f"✅ Enterprise scan completed: {api_response['scan_id']}")
            return api_response
            
        except Exception as e:
            logger.error(f"❌ Enterprise scan failed: {e}")
            
            # Return error in API format
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "enterprise_mode": True
            }
    
    def _convert_enterprise_to_api_format(self, enterprise_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converte risultato enterprise in formato API compatibile
        Mantiene struttura per frontend esistente
        """
        
        # Base response structure
        api_response = {
            "status": "success",
            "scan_id": enterprise_result["scan_id"],
            "timestamp": enterprise_result["timestamp"],
            "enterprise_mode": True,
            
            # Paths per frontend
            "base_out": enterprise_result["paths"]["base_output"],
            "summary_path": enterprise_result["paths"]["enterprise_summary"],
            "report_html_path": enterprise_result["paths"]["html_report"],
            "report_pdf_path": enterprise_result["paths"]["pdf_report"],
            
            # Compliance data per frontend
            "compliance_summary": {
                "overall_score": enterprise_result["compliance"]["overall_score"],
                "compliance_level": enterprise_result["compliance"]["compliance_level"],
                "total_violations": enterprise_result["compliance"]["total_violations"],
                "confidence": enterprise_result["compliance"]["confidence"]
            },
            
            # Execution info
            "execution_info": {
                "successful_scanners": enterprise_result["execution"]["successful_scanners"],
                "failed_scanners": enterprise_result["execution"]["failed_scanners"],
                "success_rate": enterprise_result["execution"]["success_rate"]
            },
            
            # Enterprise-specific data
            "enterprise_data": {
                "processing_stats_path": enterprise_result["paths"]["processing_stats"],
                "charts_path": enterprise_result["paths"]["charts_data"],
                "validation_passed": True
            }
        }
        
        return api_response
    
    def get_scan_status(self, scan_id: str) -> Dict[str, Any]:
        """
        Ottiene status scansione per WebSocket updates
        """
        
        if scan_id not in self.active_scans:
            return {
                "status": "unknown",
                "scan_id": scan_id,
                "message": "Scan ID not found"
            }
        
        return self.active_scans[scan_id]
    
    def register_scan_monitor(self, scan_id: str, monitor):
        """
        Registra monitor per tracking real-time
        """
        self.active_scans[scan_id] = {
            "status": "running",
            "monitor": monitor,
            "started_at": datetime.utcnow().isoformat()
        }
    
    def cleanup_completed_scan(self, scan_id: str):
        """
        Cleanup dopo completamento scansione
        """
        if scan_id in self.active_scans:
            del self.active_scans[scan_id]


class EnterpriseWebSocketMonitor:
    """
    Monitor per WebSocket events durante scansione enterprise
    Compatible con sistema eventi esistente
    """
    
    def __init__(self, websocket, scan_id: str):
        self.websocket = websocket
        self.scan_id = scan_id
        self.events = []
    
    async def emit_scanner_operation(self, scanner: str, operation: str, progress: int):
        """Emette evento scanner operation"""
        
        event = {
            "type": "scanner_operation",
            "scanner": scanner,
            "operation": operation,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.events.append(event)
        
        try:
            await self.websocket.send_json({
                "scan_id": self.scan_id,
                "event": event
            })
        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
    
    async def emit_processing_step(self, step: str, progress: int):
        """Emette evento processing step"""
        
        event = {
            "type": "processing_step",
            "step": step,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.events.append(event)
        
        try:
            await self.websocket.send_json({
                "scan_id": self.scan_id,
                "event": event
            })
        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
    
    async def emit_report_generation(self, stage: str, progress: int):
        """Emette evento report generation"""
        
        event = {
            "type": "report_generation",
            "stage": stage,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.events.append(event)
        
        try:
            await self.websocket.send_json({
                "scan_id": self.scan_id,
                "event": event
            })
        except Exception as e:
            logger.error(f"WebSocket send failed: {e}")
    
    def get_events_history(self) -> list:
        """Restituisce storico eventi"""
        return self.events.copy()


# Global adapter instance
enterprise_adapter = FastAPIEnterpriseAdapter()


def get_enterprise_adapter() -> FastAPIEnterpriseAdapter:
    """Dependency per ottenere adapter enterprise"""
    return enterprise_adapter


# Export per utilizzo esterno
__all__ = [
    "FastAPIEnterpriseAdapter",
    "EnterpriseWebSocketMonitor", 
    "enterprise_adapter",
    "get_enterprise_adapter"
]