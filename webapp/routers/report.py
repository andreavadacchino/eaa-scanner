"""
Report generation router for FastAPI
Handles AI-enhanced report generation and delivery
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
import json
import os
from pathlib import Path
from datetime import datetime

from ..models.scan import ReportGenerationRequest
from ..dependencies import (
    get_rate_limit, 
    get_current_user, 
    get_api_key_manager,
    APIKeyManager
)
from ..services.scan_service import ScanService
from ..services.report_generator import ReportGenerator

router = APIRouter(
    prefix="/api/v2/report",
    tags=["report"],
    dependencies=[Depends(get_rate_limit)]
)

# Service instances
scan_service = ScanService()
report_generator = ReportGenerator()

@router.post("/generate")
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    user: Optional[Dict] = Depends(get_current_user),
    api_keys: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Generate AI-enhanced accessibility report
    
    - **scan_id**: ID of completed scan
    - **model**: AI model to use for enhancement
    - **api_key**: OpenAI API key
    - **sections**: Report sections to include
    - **output_format**: Output format (html, pdf, json, markdown)
    """
    # Get scan data
    scan = await scan_service.get_scan(request.scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Scan is {scan['status']}, not completed"
        )
    
    # Validate API key
    if not api_keys.validate_key("openai", request.api_key):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format"
        )
    
    # Check user permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to generate report for this scan"
            )
    
    # Generate report in background
    report_id = f"report_{request.scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    background_tasks.add_task(
        report_generator.generate_async,
        report_id,
        scan,
        request,
        api_keys
    )
    
    return {
        "report_id": report_id,
        "status": "generating",
        "message": "Report generation started",
        "estimated_time": 30  # seconds
    }

@router.get("/{scan_id}/preview")
async def preview_report(
    scan_id: str,
    user: Optional[Dict] = Depends(get_current_user)
):
    """
    Preview HTML report without AI enhancement
    
    Returns basic HTML report from scan results
    """
    scan = await scan_service.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Scan is {scan['status']}, not completed"
        )
    
    # Check permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this report"
            )
    
    # Generate basic HTML report
    html_content = await report_generator.generate_basic_html(scan)
    
    return HTMLResponse(content=html_content)

@router.get("/{report_id}/status")
async def get_report_status(report_id: str):
    """Get status of report generation"""
    status = await report_generator.get_status(report_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return status

@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = "html",
    user: Optional[Dict] = Depends(get_current_user)
):
    """
    Download generated report
    
    - **format**: Output format (html, pdf, json, markdown)
    """
    # Validate format
    valid_formats = ["html", "pdf", "json", "markdown"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {valid_formats}"
        )
    
    # Get report file path
    report_path = await report_generator.get_report_path(report_id, format)
    
    if not report_path or not report_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    
    # Set appropriate content type
    content_types = {
        "html": "text/html",
        "pdf": "application/pdf",
        "json": "application/json",
        "markdown": "text/markdown"
    }
    
    return FileResponse(
        path=report_path,
        media_type=content_types[format],
        filename=f"accessibility_report_{report_id}.{format}"
    )

@router.post("/{scan_id}/email")
async def email_report(
    scan_id: str,
    email: str,
    include_pdf: bool = True,
    background_tasks: BackgroundTasks,
    user: Optional[Dict] = Depends(get_current_user)
):
    """
    Email report to specified address
    
    - **email**: Recipient email address
    - **include_pdf**: Include PDF attachment
    """
    scan = await scan_service.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to email this report"
            )
    
    # Send email in background
    background_tasks.add_task(
        report_generator.send_email,
        scan,
        email,
        include_pdf
    )
    
    return {
        "status": "queued",
        "message": f"Report will be sent to {email}"
    }

@router.get("/{scan_id}/issues")
async def get_scan_issues(
    scan_id: str,
    severity: Optional[str] = None,
    wcag_level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: Optional[Dict] = Depends(get_current_user)
):
    """
    Get detailed issue list from scan
    
    - **severity**: Filter by severity (critical, high, medium, low)
    - **wcag_level**: Filter by WCAG level (A, AA, AAA)
    - **limit**: Maximum results
    - **offset**: Pagination offset
    """
    scan = await scan_service.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if not scan.get("results"):
        raise HTTPException(status_code=404, detail="No results available")
    
    # Check permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view these issues"
            )
    
    # Extract and filter issues
    all_issues = scan["results"].get("all_issues", [])
    
    # Apply filters
    filtered_issues = all_issues
    
    if severity:
        filtered_issues = [
            issue for issue in filtered_issues
            if issue.get("severity") == severity
        ]
    
    if wcag_level:
        filtered_issues = [
            issue for issue in filtered_issues
            if wcag_level in issue.get("wcag_criterion", "")
        ]
    
    # Apply pagination
    paginated_issues = filtered_issues[offset:offset + limit]
    
    return {
        "total": len(filtered_issues),
        "limit": limit,
        "offset": offset,
        "issues": paginated_issues
    }

@router.get("/{scan_id}/metrics")
async def get_scan_metrics(
    scan_id: str,
    user: Optional[Dict] = Depends(get_current_user)
):
    """Get compliance metrics from scan"""
    scan = await scan_service.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if not scan.get("results"):
        raise HTTPException(status_code=404, detail="No results available")
    
    # Check permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view these metrics"
            )
    
    metrics = scan["results"].get("metrics", {})
    
    return {
        "scan_id": scan_id,
        "url": scan["url"],
        "company_name": scan["company_name"],
        "scan_date": scan.get("completed_at"),
        "metrics": metrics
    }

@router.post("/{scan_id}/remediation")
async def generate_remediation_plan(
    scan_id: str,
    priority: str = "high",
    timeline_days: int = 30,
    api_key: str = None,
    background_tasks: BackgroundTasks,
    user: Optional[Dict] = Depends(get_current_user),
    api_keys: APIKeyManager = Depends(get_api_key_manager)
):
    """
    Generate AI-powered remediation plan
    
    - **priority**: Issue priority threshold (critical, high, medium, low)
    - **timeline_days**: Suggested timeline for fixes
    - **api_key**: OpenAI API key for AI generation
    """
    scan = await scan_service.get_scan(scan_id)
    
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if not scan.get("results"):
        raise HTTPException(status_code=404, detail="No results available")
    
    # Check permissions
    if user and scan.get("user_id") != user.get("id"):
        if not user.get("is_admin"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to generate remediation plan"
            )
    
    # Validate API key if provided
    if api_key and not api_keys.validate_key("openai", api_key):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format"
        )
    
    # Generate remediation plan in background
    plan_id = f"remediation_{scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    background_tasks.add_task(
        report_generator.generate_remediation_plan,
        plan_id,
        scan,
        priority,
        timeline_days,
        api_key or api_keys.get_key("openai")
    )
    
    return {
        "plan_id": plan_id,
        "status": "generating",
        "message": "Remediation plan generation started"
    }

@router.get("/templates")
async def list_report_templates():
    """List available report templates"""
    templates = await report_generator.list_templates()
    
    return {
        "templates": templates,
        "default": "standard",
        "custom_allowed": True
    }

@router.post("/templates/custom")
async def upload_custom_template(
    name: str,
    template_content: str,
    user: Dict = Depends(get_current_user)
):
    """
    Upload custom report template
    
    Requires authentication
    """
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to upload templates"
        )
    
    # Validate template
    is_valid = await report_generator.validate_template(template_content)
    
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid template format"
        )
    
    # Save template
    template_id = await report_generator.save_template(
        name,
        template_content,
        user["id"]
    )
    
    return {
        "template_id": template_id,
        "name": name,
        "status": "saved"
    }