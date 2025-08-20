from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List
import os
import json
from ..utils import first_available, run_command


@dataclass
class Pa11yResult:
    ok: bool
    json: Dict[str, Any]


class Pa11yScanner:
    def __init__(self, timeout_ms: int = 60000, simulate: bool = False):
        self.timeout_ms = timeout_ms
        self.simulate = simulate

    def scan(self, url: str) -> Pa11yResult:
        # Emit operation event if hooks available
        from ..scan_events import get_current_hooks
        hooks = get_current_hooks()
        
        if self.simulate:
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Esecuzione simulata", 50)
            return self._simulate(url)
        # Attempt to run pa11y via configured command or best effort
        try:
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Ricerca eseguibile Pa11y", 20)
                
            custom = os.getenv("PA11Y_CMD")
            choices: List[List[str]] = []
            if custom:
                choices.append(custom.split())
            choices.extend([
                ["pa11y"],
                ["npx", "pa11y"],
                ["pnpm", "dlx", "pa11y"],
            ])
            base, err = first_available(choices)
            if not base:
                if hooks:
                    hooks.emit_scanner_operation("Pa11y", "Pa11y non trovato, uso simulazione", 100)
                return self._simulate(url)
                
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Esecuzione analisi accessibilità", 50)
                
            cmd = base + ["--reporter", "json", url]
            completed = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
            if completed.returncode != 0:
                # Prova a parsare stdout anche in caso di errore, potrebbe contenere risultati validi
                try:
                    stdout_data = json.loads(completed.stdout or "[]")
                    # Se stdout contiene un array valido di issues, usalo
                    if isinstance(stdout_data, list):
                        return Pa11yResult(ok=True, json={"issues": stdout_data})
                    return Pa11yResult(ok=False, json={"error": completed.stderr, "stdout": completed.stdout})
                except:
                    return Pa11yResult(ok=False, json={"error": completed.stderr, "stdout": completed.stdout})
            data = json.loads(completed.stdout or "{}")
            # Normalizza il formato: se è una lista, wrappala in un oggetto con "issues"
            if isinstance(data, list):
                data = {"issues": data}
            return Pa11yResult(ok=True, json=data)
        except Exception as e:
            return Pa11yResult(ok=False, json={"error": str(e)})

    def _simulate(self, url: str) -> Pa11yResult:
        data = {
            "documentTitle": "Simulated",
            "pageUrl": url,
            "issues": [
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "message": "Insufficient contrast",
                    "context": "<p>Low contrast</p>",
                    "selector": "body > p:nth-child(3)",
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                    "type": "error",
                    "message": "Img element missing alt",
                    "context": "<img src=\"x.jpg\">",
                    "selector": "img",
                },
                {
                    "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.A.NoContent",
                    "type": "warning",
                    "message": "Link without content",
                    "context": "<a href=\"#\"></a>",
                    "selector": "a[href='#']",
                },
            ],
        }
        return Pa11yResult(ok=True, json=data)
