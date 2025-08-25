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
        class ProgressMonitor:
            def __init__(self, scan_id, scan_manager, ws_manager, scan_status):
                self.scan_id = scan_id
                self.scan_manager = scan_manager
                self.ws_manager = ws_manager
                self.scan_status = scan_status
            
            async def on_progress(self, scanner_name: str, progress: int, message: str):
                await self.scan_manager.update_scan(self.scan_id, progress=progress, message=message)
                if self.scan_status:
                    self.scan_status.update(progress=progress, message=message)
                await self.ws_manager.broadcast(self.scan_id, {
                    "type": "progress",
                    "progress": progress,
                    "message": message
                })
        
        monitor = ProgressMonitor(scan_id, scan_manager, ws_manager, scan_status)
        
        # Execute enterprise scan using the correct method
        result_dict = adapter.run_enterprise_scan_for_api(
            url=str(request.url),
            company_name=request.company_name,
            email=request.email,
            wave_api_key=get_effective_wave_key(),
            simulate=bool(simulate_flag),
            event_monitor=monitor
        )
        
        # Update final status
        await scan_manager.update_scan(
            scan_id, 
            status="completed", 
            progress=100, 
            results=result_dict,
            message="Scansione enterprise completata"
        )
        
        if scan_status:
            scan_status.update(
                status="completed", 
                progress=100, 
                message="Scansione enterprise completata",
                results=result_dict
            )
        
        await ws_manager.broadcast(scan_id, {
            "type": "complete",
            "status": "completed",
            "progress": 100,
            "results": result_dict
        })
        
        logger.info(f"========== ENTERPRISE SCAN {scan_id} COMPLETED ==========")
        logger.info(f"Results summary: {len(result_dict.get('individual_results', []))} scanners, {result_dict.get('compliance_metrics', {}).get('total_violations', 0)} violations")
        
    except Exception as e:
        error_msg = f"Enterprise scan failed: {str(e)}"
        logger.error(f"Enterprise scan error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        await scan_manager.update_scan(scan_id, status="error", message=error_msg)
        if scan_status:
            scan_status.update(status="error", message=error_msg)
        
        await ws_manager.broadcast(scan_id, {
            "type": "error",
            "status": "error",
            "message": error_msg
        })