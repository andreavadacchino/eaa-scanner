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
    def __init__(self, timeout_ms: int = 60000, simulate: bool = False):
        self.timeout_ms = timeout_ms
        self.simulate = simulate

    def scan(self, url: str) -> AxeResult:
        # Emit operation event if hooks available
        from ..scan_events import get_current_hooks
        hooks = get_current_hooks()
        
        # Modalità simulata
        if self.simulate:
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Simulazione analisi Axe", 60)
            return self._simulate(url)
        
        # Prima prova il runner Node.js ottimizzato per Docker
        try:
            runner_path = os.path.join(os.path.dirname(__file__), "axe_runner.js")
            if os.path.exists(runner_path):
                if hooks:
                    hooks.emit_scanner_operation("Axe-core", "Avvio runner Node.js ottimizzato", 30)
                
                cmd = ["node", runner_path, url, "WCAG2AA", str(self.timeout_ms)]
                cp = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
                
                if cp.returncode == 0 and cp.stdout:
                    if hooks:
                        hooks.emit_scanner_operation("Axe-core", "Analisi completata con successo", 100)
                    data = json.loads(cp.stdout)
                    return AxeResult(ok=True, json=data)
                else:
                    if hooks:
                        hooks.emit_scanner_operation("Axe-core", "Runner Node.js fallito, fallback a CLI", 40)
                    # Fallback to CLI method
                    pass
        except Exception as e:
            if hooks:
                hooks.emit_scanner_operation("Axe-core", f"Runner Node.js error: {str(e)}", 50)
            # Fallback to CLI method
            pass
            
        # Fallback: Try @axe-core/cli via npx or pnpm dlx (metodo originale)
        try:
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Ricerca eseguibile Axe CLI", 60)
                
            custom = os.getenv("AXE_CMD")
            choices: List[List[str]] = []
            if custom:
                parts = custom.split()
                choices.append(parts)
            choices.extend([
                ["axe"],  # Prima prova il comando globale (per Docker)
                ["npx", "@axe-core/cli"],
                ["pnpm", "dlx", "@axe-core/cli"],
            ])
            base, err = first_available(choices)
            if not base:
                if hooks:
                    hooks.emit_scanner_operation("Axe-core", "Axe non trovato", 100)
                raise Exception(f"Axe-core not found. Tried: {choices}")
                
            if hooks:
                hooks.emit_scanner_operation("Axe-core", "Analisi WCAG con CLI in corso", 80)
                
            # Configurazione browser per container Docker
            # Axe-core CLI richiede flags Chrome specifici per funzionare come root
            chrome_options = [
                "--no-sandbox",
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--headless",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-web-security",
                "--allow-running-insecure-content"
            ]
            
            # Usa sempre chrome per compatibilità
            cmd = base + [
                "--stdout",
                "--browser", "chrome",
            ]
            
            # Aggiungi le opzioni Chrome come parametri separati
            # Axe CLI vuole le opzioni in formato diverso
            for opt in chrome_options:
                cmd.extend(["--chrome-options", opt])
            cmd.append(url)
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
