from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class WaveResult:
    ok: bool
    json: Dict[str, Any]


class WaveScanner:
    def __init__(self, api_key: str, timeout_ms: int = 60000, simulate: bool = False):
        self.api_key = api_key
        self.timeout_ms = timeout_ms
        self.simulate = simulate

    def scan(self, url: str) -> WaveResult:
        # Emit operation event if hooks available
        from ..scan_events import get_current_hooks
        hooks = get_current_hooks()
        
        if self.simulate or not self.api_key:
            if hooks:
                hooks.emit_scanner_operation("WAVE", "Esecuzione simulata", 50)
            return self._simulate(url)
        try:
            # Lazy import to avoid dependency when offline
            import urllib.parse
            import urllib.request

            if hooks:
                hooks.emit_scanner_operation("WAVE", "Invio richiesta API", 30)
                
            params = urllib.parse.urlencode(
                {
                    "key": self.api_key,
                    "url": url,
                    "format": "json",
                    "reporttype": "4",
                }
            )
            req_url = f"https://wave.webaim.org/api/request?{params}"
            
            if hooks:
                hooks.emit_scanner_operation("WAVE", "Attesa risposta API", 60)
                
            with urllib.request.urlopen(req_url, timeout=self.timeout_ms / 1000.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                
            if hooks:
                hooks.emit_scanner_operation("WAVE", "Analisi risultati", 90)
                
            ok = bool(data.get("status", {}).get("success", False))
            return WaveResult(ok=ok, json=data)
        except Exception as e:
            return WaveResult(ok=False, json={"status": {"success": False, "error": str(e)}})

    def _simulate(self, url: str) -> WaveResult:
        data = {
            "status": {"success": True},
            "statistics": {
                "waveurl": url,
                "pagetitle": "Simulated page",
                "time": 1234,
            },
            "categories": {
                "error": {
                    "items": {
                        "alt_missing": {
                            "description": "Image elements missing alt attribute",
                            "count": 2,
                            "impact": "high",
                            "wcag": ["1.1.1"],
                        }
                    }
                },
                "contrast": {
                    "items": {
                        "contrast": {
                            "description": "Insufficient color contrast",
                            "count": 3,
                            "impact": "high",
                            "wcag": ["1.4.3", "1.4.11"],
                        }
                    }
                },
                "alert": {
                    "items": {
                        "link_suspicious": {
                            "description": "Anchor without text",
                            "count": 1,
                            "impact": "medium",
                            "wcag": ["2.4.4"],
                        }
                    }
                },
                "feature": {"items": {}}
            },
        }
        return WaveResult(ok=True, json=data)

