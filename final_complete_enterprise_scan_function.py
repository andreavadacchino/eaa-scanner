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
        
        # Complete Progress Monitor with ALL required methods
        class ProgressMonitor:
            """Complete monitor implementation for enterprise scan events"""
            
            def __init__(self, scan_id, scan_manager, ws_manager, scan_status):
                self.scan_id = scan_id
                self.scan_manager = scan_manager
                self.ws_manager = ws_manager
                self.scan_status = scan_status
                self.last_progress = 10  # Start from 10 after init
            
            def emit_scanner_start(self, scan_id: str, scanner_name: str, url: str = None, estimated_duration: int = None):
                """Scanner started"""
                message = f"Avvio scanner {scanner_name}..."
                self.last_progress = min(90, self.last_progress + 5)
                asyncio.create_task(self._update_progress(self.last_progress, message))
                
            def emit_scanner_operation(self, scan_id: str, scanner_name: str, operation: str, progress: int = None, details: str = None):
                """Scanner operation"""
                message = f"{scanner_name}: {operation}"
                if details:
                    message += f" - {details}"
                if progress:
                    self.last_progress = max(self.last_progress, progress)
                else:
                    self.last_progress = min(85, self.last_progress + 2)
                asyncio.create_task(self._update_progress(self.last_progress, message))
                
            def emit_scanner_complete(self, scan_id: str, scanner_name: str, results_summary: str = None):
                """Scanner completed"""
                message = f"Scanner {scanner_name} completato"
                if results_summary:
                    message += f" - {results_summary}"
                self.last_progress = min(80, self.last_progress + 15)
                asyncio.create_task(self._update_progress(self.last_progress, message))
                
            def emit_scanner_error(self, scan_id: str, scanner_name: str, error_message: str, is_critical: bool = False):
                """Scanner error"""
                message = f"Scanner {scanner_name}: {error_message[:100]}"
                # Don't update progress on errors, keep current
                asyncio.create_task(self._update_progress(self.last_progress, message))
                
            def emit_processing_step(self, scan_id: str, step_name: str, progress: int = None):
                """Processing step"""
                if progress:
                    self.last_progress = max(self.last_progress, progress)
                else:
                    self.last_progress = min(85, self.last_progress + 3)
                asyncio.create_task(self._update_progress(self.last_progress, step_name))
                
            def emit_page_progress(self, scan_id: str, current_page: int, total_pages: int, current_url: str):
                """Page progress"""
                message = f"Pagina {current_page}/{total_pages}"
                page_progress = int((current_page / total_pages) * 10) + self.last_progress
                self.last_progress = min(85, page_progress)
                asyncio.create_task(self._update_progress(self.last_progress, message))
                
            def emit_report_generation(self, scan_id: str, stage: str, progress: int = None):
                """Report generation"""
                message = f"Generazione report: {stage}"
                report_progress = progress if progress else min(95, self.last_progress + 5)
                self.last_progress = report_progress
                asyncio.create_task(self._update_progress(self.last_progress, message))
            
            async def _update_progress(self, progress: int, message: str):
                """Internal progress update"""
                try:
                    progress = max(0, min(99, progress))  # Clamp between 0-99
                    await self.scan_manager.update_scan(self.scan_id, progress=progress, message=message)
                    if self.scan_status:
                        self.scan_status.update(progress=progress, message=message)
                    await self.ws_manager.broadcast(self.scan_id, {
                        "type": "progress",
                        "progress": progress,
                        "message": message
                    })
                except Exception as e:
                    logger.error(f"Progress update error: {e}")
        
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
        
        # Update final status (scan_status.update() doesn't accept 'results')
        await scan_manager.update_scan(
            scan_id, 
            status="completed", 
            progress=100, 
            results=result_dict,
            message="Scansione enterprise completata"
        )
        
        if scan_status:
            # Don't pass results to scan_status.update()
            scan_status.update(
                status="completed", 
                progress=100, 
                message="Scansione enterprise completata"
            )
        
        await ws_manager.broadcast(scan_id, {
            "type": "complete",
            "status": "completed",
            "progress": 100,
            "results": result_dict
        })
        
        logger.info(f"========== ENTERPRISE SCAN {scan_id} COMPLETED ==========")
        
        # Log risultati per debug
        if result_dict and "compliance_metrics" in result_dict:
            metrics = result_dict["compliance_metrics"]
            logger.info(f"✅ Risultati enterprise: {metrics.get('total_violations', 0)} violazioni, score {metrics.get('overall_score', 0)}")
            logger.info(f"✅ Scanner completati: {len(result_dict.get('individual_results', []))}")
            logger.info(f"✅ Sistema enterprise funzionante con DATI REALI!")
        
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