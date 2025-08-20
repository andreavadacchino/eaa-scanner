from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import os
import json
from ..utils import first_available, run_command


@dataclass
class AxeResult:
    ok: bool
    json: Dict[str, Any]


class AxeScanner:
    def __init__(self, timeout_ms: int = 60000, simulate: bool = True):
        self.timeout_ms = timeout_ms
        self.simulate = simulate

    def scan(self, url: str) -> AxeResult:
        # Emit operation event if hooks available
        from ..scan_events import get_current_hooks
        hooks = get_current_hooks()
        
        if self.simulate:
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Esecuzione simulata", 50)
            return self._simulate(url)
        # Try @axe-core/cli via npx or pnpm dlx
        try:
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Ricerca eseguibile Axe", 20)
                
            custom = os.getenv("AXE_CMD")
            choices: List[List[str]] = []
            if custom:
                parts = custom.split()
                choices.append(parts)
            choices.extend([
                ["npx", "@axe-core/cli"],
                ["pnpm", "dlx", "@axe-core/cli"],
                ["axe"],
            ])
            base, err = first_available(choices)
            if not base:
                if hooks:
                    hooks.emit_scanner_operation("Axe-core", "Axe non trovato, uso simulazione", 100)
                return self._simulate(url)
                
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Analisi WCAG in corso", 50)
                
            cmd = base + ["--stdout", url]
            cp = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
            if cp.returncode != 0:
                return AxeResult(ok=False, json={"error": cp.stderr, "stdout": cp.stdout})
            data = json.loads(cp.stdout or "{}")
            # Axe ritorna una lista con un singolo oggetto, estraiamolo
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            return AxeResult(ok=True, json=data)
        except Exception as e:
            return AxeResult(ok=False, json={"error": str(e)})

    def _simulate(self, url: str) -> AxeResult:
        data = {
            "scanner": "axe-core",
            "url": url,
            "violations": [
                {
                    "id": "color-contrast",
                    "impact": "serious",
                    "description": "Elements must have sufficient color contrast",
                    "nodes": 2,
                    "wcag": ["1.4.3"],
                },
                {
                    "id": "heading-order",
                    "impact": "moderate",
                    "description": "Heading levels should only increase by one",
                    "nodes": 1,
                    "wcag": ["1.3.1"],
                },
            ],
            "passes": [{"id": "image-alt", "description": "Images must have alternate text", "nodes": 15}],
            "inapplicable": [],
            "incomplete": [],
            "total_violations": 2,
            "total_nodes_tested": 87,
            "compliance_score": 85,
        }
        return AxeResult(ok=True, json=data)
