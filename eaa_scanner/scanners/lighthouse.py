from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import os
import json
from ..utils import first_available, run_command


@dataclass
class LighthouseResult:
    ok: bool
    json: Dict[str, Any]


class LighthouseScanner:
    def __init__(self, timeout_ms: int = 60000, simulate: bool = False):
        self.timeout_ms = timeout_ms
        self.simulate = simulate

    def scan(self, url: str) -> LighthouseResult:
        # Emit operation event if hooks available
        from ..scan_events import get_current_hooks
        hooks = get_current_hooks()
        
        # Modalità simulata
        if self.simulate:
            if hooks:
                hooks.emit_scanner_operation("Lighthouse", "Simulazione audit Lighthouse", 60)
            return self._simulate(url)
        try:
            if hooks:
                hooks.emit_scanner_operation("Lighthouse", "Ricerca eseguibile Lighthouse", 20)
                
            custom = os.getenv("LIGHTHOUSE_CMD")
            choices: List[List[str]] = []
            if custom:
                choices.append(custom.split())
            choices.extend([
                ["lighthouse"],
                ["npx", "lighthouse"],
            ])
            base, err = first_available(choices)
            if not base:
                if hooks:
                    hooks.emit_scanner_operation("Lighthouse", "Lighthouse non trovato", 100)
                raise Exception(f"Lighthouse not found. Tried: {choices}")
                
            if hooks:
                hooks.emit_scanner_operation("Lighthouse", "Avvio browser headless", 40)
                
            # Configurazione browser per container Docker
            # Lighthouse richiede flags Chrome estesi per funzionare come root in Docker
            chrome_flags = "--headless --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --disable-gpu --disable-extensions --no-first-run --disable-features=TranslateUI --disable-default-apps"
            
            # Specifica il path di chromium se nel container
            chromium_path = "/usr/bin/chromium" if os.path.exists("/usr/bin/chromium") else None
            
            cmd = base + [
                url,
                "--only-categories=accessibility",
                "--quiet",
                "--output=json",
                "--output-path=stdout",
            ]
            
            # Aggiungi chrome-executable solo se chromium è disponibile
            if chromium_path:
                cmd.extend([
                    f"--chrome-executable={chromium_path}",
                ])
            
            cmd.append(f"--chrome-flags={chrome_flags}")
            
            if hooks:
                hooks.emit_scanner_operation("Lighthouse", "Audit accessibilità in corso", 70)
                
            cp = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
            if cp.returncode != 0:
                return LighthouseResult(ok=False, json={"error": cp.stderr, "stdout": cp.stdout})
            data = json.loads(cp.stdout or "{}")
            # Return raw data for proper processing by normalize.py
            # Keep all audit details needed by the processor
            return LighthouseResult(
                ok=True,
                json={
                    "scanner": "lighthouse",
                    "url": url,
                    "audits": data.get("audits", {}),  # Full audit data with details
                    "categories": data.get("categories", {}),  # Complete categories
                    "lighthouse_version": data.get("lighthouseVersion"),
                    "raw_data": data  # Keep raw data for reference
                },
            )
        except Exception as e:
            return LighthouseResult(ok=False, json={"error": str(e)})

    def _simulate(self, url: str) -> LighthouseResult:
        data = {
            "scanner": "lighthouse",
            "url": url,
            "accessibility_score": 78,
            "audits": {
                "bypass": {"score": 1, "title": "Page has a logical tab order"},
                "color-contrast": {
                    "score": 0.85,
                    "title": "Background and foreground colors have sufficient contrast ratio",
                    "details": "3 elements fail",
                },
                "heading-order": {
                    "score": 0.5,
                    "title": "Headings are in a logical order",
                    "details": "1 heading out of order",
                },
                "image-alt": {"score": 1, "title": "Image elements have [alt] attributes"},
                "link-name": {"score": 0.9, "title": "Links have a discernible name", "details": "1 link without name"},
                "meta-viewport": {"score": 1, "title": "Has a meta name=\"viewport\" tag"},
            },
            "performance_score": 82,
            "seo_score": 91,
            "best_practices_score": 88,
            "categories": {
                "accessibility": {"score": 0.78, "title": "Accessibility"},
                "performance": {"score": 0.82, "title": "Performance"},
                "seo": {"score": 0.91, "title": "SEO"},
                "best-practices": {"score": 0.88, "title": "Best Practices"}
            },
        }
        return LighthouseResult(ok=True, json=data)
