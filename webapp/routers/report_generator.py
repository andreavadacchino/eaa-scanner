"""FastAPI Router for AI-powered Report Generation

Integra il sistema multi-agent per generazione report professionali.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator

# Import EAA Scanner multi-agent system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from eaa_scanner.agents.orchestrator import AIReportOrchestrator
from eaa_scanner.models import AggregatedResults

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/api/report",
    tags=["report-generation"],
    responses={404: {"description": "Not found"}}
)

# Initialize orchestrator (singleton)
orchestrator = AIReportOrchestrator()


# ==================== REQUEST/RESPONSE MODELS ====================

class ReportGenerationRequest(BaseModel):
    """Request model for report generation"""
    
    scan_id: str = Field(..., description="ID della scansione completata")
    company_name: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl = Field(..., description="URL del sito analizzato")
    email: Optional[EmailStr] = Field(None, description="Email di contatto")
    country: str = Field(default="Italia", description="Paese per normativa")
    
    # Report preferences
    target_audience: str = Field(
        default="mixed",
        pattern="^(executive|technical|mixed)$",
        description="Target audience del report"
    )
    language: str = Field(default="it", pattern="^(it|en)$")
    include_technical_details: bool = Field(default=True)
    include_remediation_plan: bool = Field(default=True)
    include_cost_estimates: bool = Field(default=False)
    
    # Format options
    format: str = Field(default="html", pattern="^(html|pdf|json)$")
    style: str = Field(
        default="professional",
        pattern="^(professional|executive|technical)$"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "scan_id": "abc123",
                "company_name": "Principia SRL",
                "url": "https://www.principiadv.com",
                "email": "info@principiadv.com",
                "country": "Italia",
                "target_audience": "executive",
                "include_cost_estimates": True
            }
        }
    }


class ReportGenerationResponse(BaseModel):
    """Response model for report generation"""
    
    success: bool
    report_id: str
    status: str
    generation_time: float
    quality_score: float
    html_report: Optional[str] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any]
    agent_metrics: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None
    warnings: Optional[list] = None


class ReportStatusResponse(BaseModel):
    """Response model for report status check"""
    
    report_id: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    message: str
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    quality_score: Optional[float] = None


# ==================== STORAGE ====================

# In-memory storage for demo (use Redis/DB in production)
report_storage = {}
scan_data_cache = {}


# ==================== HELPER FUNCTIONS ====================

async def get_scan_data(scan_id: str) -> Dict[str, Any]:
    """Recupera i dati della scansione
    
    In produzione, questo dovrebbe leggere da database/storage.
    """
    
    # Check cache first
    if scan_id in scan_data_cache:
        return scan_data_cache[scan_id]
    
    # In produzione: query database
    # Per ora simuliamo con dati di esempio strutturati
    
    # Prova a caricare da file se esiste
    scan_file = Path(f"output/scan_{scan_id}/summary.json")
    if scan_file.exists():
        with open(scan_file, 'r') as f:
            scan_data = json.load(f)
            scan_data_cache[scan_id] = scan_data
            return scan_data
    
    # Altrimenti restituisce struttura vuota (per test)
    logger.warning(f"Scan data not found for {scan_id}, using empty structure")
    return {
        'all_violations': [],
        'compliance': {
            'overall_score': 0,
            'compliance_level': 'unknown'
        }
    }


async def save_report(report_id: str, html_content: str, metadata: Dict[str, Any]):
    """Salva il report generato
    
    In produzione: salvare su storage persistente (S3, DB, etc.)
    """
    
    # Create output directory
    output_dir = Path(f"output/reports/{report_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save HTML report
    html_path = output_dir / "report.html"
    async with aiofiles.open(html_path, 'w', encoding='utf-8') as f:
        await f.write(html_content)
    
    # Save metadata
    meta_path = output_dir / "metadata.json"
    async with aiofiles.open(meta_path, 'w') as f:
        await f.write(json.dumps(metadata, indent=2, default=str))
    
    # Update storage
    report_storage[report_id] = {
        'html_path': str(html_path),
        'metadata': metadata,
        'created_at': datetime.now()
    }
    
    return str(html_path)


# ==================== API ENDPOINTS ====================

@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
) -> ReportGenerationResponse:
    """Genera report professionale utilizzando sistema multi-agent
    
    Endpoint principale per generazione report AI-powered.
    """
    
    logger.info(f"Starting report generation for {request.company_name}")
    
    try:
        # 1. Recupera dati scansione
        scan_data = await get_scan_data(request.scan_id)
        
        if not scan_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scan data not found for ID: {request.scan_id}"
            )
        
        # 2. Prepara info azienda
        company_info = {
            'company_name': request.company_name,
            'url': str(request.url),
            'email': request.email,
            'country': request.country
        }
        
        # 3. Prepara requisiti report
        requirements = {
            'target_audience': request.target_audience,
            'language': request.language,
            'include_technical_details': request.include_technical_details,
            'include_remediation_plan': request.include_remediation_plan,
            'include_cost_estimates': request.include_cost_estimates,
            'format': request.format,
            'style': request.style
        }
        
        # 4. Genera report con orchestrator
        start_time = datetime.now()
        
        result = await orchestrator.generate_report(
            scan_data=scan_data,
            company_info=company_info,
            requirements=requirements
        )
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        # 5. Gestisci risultato
        if result['status'] == 'success':
            # Genera report ID
            report_id = f"report_{request.scan_id}_{int(datetime.now().timestamp())}"
            
            # Salva report
            await save_report(
                report_id,
                result['html_report'],
                result['metadata']
            )
            
            # Prepara response
            response = ReportGenerationResponse(
                success=True,
                report_id=report_id,
                status="completed",
                generation_time=generation_time,
                quality_score=result['quality_score'],
                html_report=result['html_report'] if request.format == 'html' else None,
                download_url=f"/api/report/download/{report_id}",
                metadata=result['metadata'],
                agent_metrics=result.get('agent_metrics'),
                errors=None,
                warnings=None
            )
            
            logger.info(f"Report generated successfully: {report_id} (quality: {result['quality_score']:.2f})")
            
        else:
            # Gestisci fallback
            report_id = f"fallback_{request.scan_id}_{int(datetime.now().timestamp())}"
            
            response = ReportGenerationResponse(
                success=False,
                report_id=report_id,
                status="fallback",
                generation_time=generation_time,
                quality_score=result.get('quality_score', 0.3),
                html_report=result.get('html_report'),
                download_url=None,
                metadata=result.get('metadata', {}),
                agent_metrics=None,
                errors=[result.get('error', 'Report generation failed')],
                warnings=["Using fallback report"]
            )
            
            logger.warning(f"Report generation failed, using fallback: {report_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/status/{report_id}", response_model=ReportStatusResponse)
async def get_report_status(report_id: str) -> ReportStatusResponse:
    """Controlla lo stato di generazione del report
    
    Utile per operazioni asincrone lunghe.
    """
    
    if report_id not in report_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    
    report_info = report_storage[report_id]
    
    return ReportStatusResponse(
        report_id=report_id,
        status="completed",
        progress=100,
        message="Report generato con successo",
        completed_at=report_info['created_at'],
        download_url=f"/api/report/download/{report_id}",
        quality_score=report_info['metadata'].get('quality_score', 0)
    )


@router.get("/download/{report_id}")
async def download_report(report_id: str, format: str = "html"):
    """Scarica il report generato
    
    Supporta diversi formati di output.
    """
    
    if report_id not in report_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    
    report_info = report_storage[report_id]
    html_path = report_info['html_path']
    
    if format == "html":
        # Return HTML file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=html_path,
            media_type="text/html",
            filename=f"{report_id}.html"
        )
    
    elif format == "json":
        # Return metadata as JSON
        return JSONResponse(
            content=report_info['metadata'],
            media_type="application/json"
        )
    
    elif format == "pdf":
        # TODO: Implement PDF generation
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF format not yet implemented"
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}"
        )


@router.get("/orchestrator/stats")
async def get_orchestrator_stats() -> Dict[str, Any]:
    """Ottiene statistiche dell'orchestratore
    
    Utile per monitoring e debugging.
    """
    
    stats = orchestrator.get_orchestrator_stats()
    stats['cache_size'] = len(scan_data_cache)
    stats['reports_generated'] = len(report_storage)
    
    return stats


@router.delete("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """Pulisce la cache (solo per admin/debug)"""
    
    scan_data_cache.clear()
    # Non pulire report_storage per non perdere report generati
    
    return {"status": "Cache cleared successfully"}


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check per il servizio di generazione report"""
    
    try:
        # Verifica che orchestrator sia attivo
        stats = orchestrator.get_orchestrator_stats()
        
        return {
            "status": "healthy",
            "service": "report-generator",
            "orchestrator_active": True,
            "total_reports": stats.get('total_reports', 0),
            "success_rate": stats.get('successful_reports', 0) / max(stats.get('total_reports', 1), 1),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "report-generator",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }