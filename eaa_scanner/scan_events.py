"""
Integrazione eventi di monitoraggio per il sistema di scansione
Fornisce hook per emettere eventi durante l'esecuzione dei scanner
"""

from typing import Optional, Dict, Any
import threading
import time

class ScanEventHooks:
    """
    Sistema di hook per eventi di scansione
    Permette di emettere eventi durante l'esecuzione dei scanner
    """
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.monitor = None
        self.start_time = time.time()
        
    def set_monitor(self, monitor):
        """Imposta il monitor per emettere eventi"""
        self.monitor = monitor
        
    def emit_scanner_start(self, scanner_name: str, url: str, estimated_duration: Optional[int] = None):
        """Hook per inizio scanner"""
        if self.monitor:
            self.monitor.emit_scanner_start(self.scan_id, scanner_name, url, estimated_duration)
    
    def emit_scanner_operation(self, scanner_name: str, operation: str, 
                             progress: Optional[int] = None, details: Optional[Dict] = None):
        """Hook per operazione scanner"""
        if self.monitor:
            self.monitor.emit_scanner_operation(self.scan_id, scanner_name, operation, progress, details)
    
    def emit_scanner_complete(self, scanner_name: str, results_summary: Dict[str, Any]):
        """Hook per completamento scanner"""
        if self.monitor:
            self.monitor.emit_scanner_complete(self.scan_id, scanner_name, results_summary)
    
    def emit_scanner_error(self, scanner_name: str, error_message: str, is_critical: bool = False):
        """Hook per errore scanner"""
        if self.monitor:
            self.monitor.emit_scanner_error(self.scan_id, scanner_name, error_message, is_critical)
    
    def emit_page_progress(self, current_page: int, total_pages: int, current_url: str):
        """Hook per progresso multi-pagina"""
        if self.monitor:
            self.monitor.emit_page_progress(self.scan_id, current_page, total_pages, current_url)
    
    def emit_processing_step(self, step_name: str, progress: Optional[int] = None):
        """Hook per step di processing"""
        if self.monitor:
            self.monitor.emit_processing_step(self.scan_id, step_name, progress)
    
    def emit_report_generation(self, stage: str, progress: Optional[int] = None):
        """Hook per generazione report"""
        if self.monitor:
            self.monitor.emit_report_generation(self.scan_id, stage, progress)


# Thread-local storage per gli hook attuali
_local = threading.local()

def set_current_hooks(hooks: ScanEventHooks):
    """Imposta gli hook per il thread corrente"""
    _local.hooks = hooks

def get_current_hooks() -> Optional[ScanEventHooks]:
    """Ottiene gli hook per il thread corrente"""
    return getattr(_local, 'hooks', None)

def emit_scanner_event(event_type: str, scanner_name: str, **kwargs):
    """Utility per emettere eventi dai scanner"""
    hooks = get_current_hooks()
    if not hooks:
        return
        
    if event_type == 'start':
        hooks.emit_scanner_start(scanner_name, **kwargs)
    elif event_type == 'operation':
        hooks.emit_scanner_operation(scanner_name, **kwargs)
    elif event_type == 'complete':
        hooks.emit_scanner_complete(scanner_name, **kwargs)
    elif event_type == 'error':
        hooks.emit_scanner_error(scanner_name, **kwargs)
    elif event_type == 'progress':
        hooks.emit_processing_step(**kwargs)
    elif event_type == 'report':
        hooks.emit_report_generation(**kwargs)


class MonitoredScanner:
    """
    Wrapper per scanner che emette eventi di monitoraggio
    """
    
    def __init__(self, scanner_instance, scanner_name: str):
        self.scanner = scanner_instance
        self.scanner_name = scanner_name
        
    def scan(self, url: str):
        """Esegue scan con monitoring"""
        hooks = get_current_hooks()
        
        try:
            # Emit start event
            if hooks:
                hooks.emit_scanner_start(self.scanner_name, url)
                
            # Emit initial operation event
            if hooks:
                hooks.emit_scanner_operation(self.scanner_name, f"Inizializzazione {self.scanner_name}", progress=25)
            
            # Emit progress during scan
            if hooks:
                hooks.emit_scanner_operation(self.scanner_name, f"Scansione in corso per {url}", progress=50)
                
            # Execute scanner
            result = self.scanner.scan(url)
            
            # Emit progress after scan
            if hooks:
                hooks.emit_scanner_operation(self.scanner_name, "Elaborazione risultati", progress=90)
            
            # Emit complete event with summary
            if hooks and hasattr(result, 'json') and result.json:
                summary = self._extract_summary(result.json)
                hooks.emit_scanner_complete(self.scanner_name, summary)
            
            return result
            
        except Exception as e:
            # Emit error event
            if hooks:
                hooks.emit_scanner_error(self.scanner_name, str(e), is_critical=True)
            raise
    
    def _extract_summary(self, result_json: dict) -> Dict[str, Any]:
        """Estrae summary dai risultati del scanner"""
        summary = {
            "scanner": self.scanner_name,
            "timestamp": time.time()
        }
        
        # Estrazione specifica per tipo scanner
        if self.scanner_name.lower() == "wave":
            if 'categories' in result_json:
                cats = result_json['categories']
                summary.update({
                    "errors": cats.get('error', {}).get('count', 0),
                    "warnings": cats.get('alert', {}).get('count', 0),
                    "features": cats.get('feature', {}).get('count', 0),
                    "structure": cats.get('structure', {}).get('count', 0)
                })
                
        elif self.scanner_name.lower() == "pa11y":
            issues = None
            if isinstance(result_json, list):
                issues = result_json
            elif isinstance(result_json, dict):
                issues = result_json.get('issues', [])
            if issues is not None:
                errors = [r for r in issues if r.get('type') == 'error']
                warnings = [r for r in issues if r.get('type') == 'warning']
                summary.update({
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "total_issues": len(issues)
                })
                
        elif self.scanner_name.lower() == "axe":
            if 'violations' in result_json:
                violations = result_json['violations']
                passes = result_json.get('passes', [])
                summary.update({
                    "violations": len(violations),
                    "passes": len(passes),
                    "critical_issues": len([v for v in violations if v.get('impact') == 'critical']),
                    "serious_issues": len([v for v in violations if v.get('impact') == 'serious'])
                })
                
        elif self.scanner_name.lower() == "lighthouse":
            if 'audits' in result_json:
                audits = result_json['audits']
                accessibility_audits = {k: v for k, v in audits.items() 
                                     if k.startswith('accessibility') or 'a11y' in k}
                failed = len([a for a in accessibility_audits.values() 
                            if a.get('score') == 0])
                passed = len([a for a in accessibility_audits.values() 
                            if a.get('score') == 1])
                # Safe extraction per evitare AttributeError su types non-dict
                categories = result_json.get('categories', {})
                accessibility_score = 0
                if isinstance(categories, dict):
                    accessibility_data = categories.get('accessibility', {})
                    if isinstance(accessibility_data, dict):
                        accessibility_score = accessibility_data.get('score', 0)
                
                summary.update({
                    "accessibility_score": accessibility_score,
                    "failed_audits": failed,
                    "passed_audits": passed,
                    "total_audits": len(accessibility_audits)
                })
        
        return summary
