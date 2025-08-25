async def run_scan_task_enterprise(scan_id: str, request: ScanRequest):
    """Enhanced background task using enterprise orchestrator"""
    scan_status = None
    try:
        logger.info(f"========== STARTING ENTERPRISE SCAN {scan_id} for {request.url} ==========")
        
        # Get scan status
        scan_status = scan_status_store.get(scan_id)
        
        # Update status
        await scan_manager.update_scan(scan_id, status="running", progress=5)
        if scan_status:
            scan_status.update(status="running", progress=5, message="Avvio scansione enterprise...")
        
        await ws_manager.broadcast(scan_id, {
            "type": "status_update",
            "status": "running", 
            "progress": 5
        })
        
        # Configure enterprise scan
        simulate_flag = getattr(request, 'simulate', None)
        if simulate_flag is None:
            simulate_env = os.getenv("SIMULATE_MODE", "false").lower()
            simulate_flag = simulate_env in ("1", "true", "yes", "on")
            
        # Create FastAPI adapter
        adapter = FastAPIEnterpriseAdapter()
        
        # Progress callback for enterprise scan
        async def progress_callback(progress: int, message: str):
            await scan_manager.update_scan(scan_id, progress=progress, message=message)
            if scan_status:
                scan_status.update(progress=progress, message=message)
            await ws_manager.broadcast(scan_id, {
                "type": "progress",
                "progress": progress,
                "message": message
            })
        
        # Execute enterprise scan
        result = await adapter.execute_scan_async(
            url=str(request.url),
            company_name=request.company_name,
            email=request.email,
            scan_id=scan_id,
            simulate=bool(simulate_flag),
            wave_api_key=get_effective_wave_key(),
            progress_callback=progress_callback,
            scanner_config=request.scannerConfig if request.scannerConfig else None
        )
        
        # Update final status
        await scan_manager.update_scan(
            scan_id, 
            status="completed", 
            progress=100, 
            results=result.model_dump(),
            message="Scansione completata"
        )
        
        if scan_status:
            scan_status.update(
                status="completed", 
                progress=100, 
                message="Scansione completata",
                results=result.model_dump()
            )
        
        await ws_manager.broadcast(scan_id, {
            "type": "complete",
            "status": "completed",
            "progress": 100,
            "results": result.model_dump()
        })
        
        logger.info(f"========== ENTERPRISE SCAN {scan_id} COMPLETED ==========")
        
    except Exception as e:
        error_msg = f"Enterprise scan failed: {str(e)}"
        logger.error(f"Enterprise scan error: {e}")
        
        await scan_manager.update_scan(scan_id, status="error", message=error_msg)
        if scan_status:
            scan_status.update(status="error", message=error_msg)
        
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "error",
            "message": error_msg
        })