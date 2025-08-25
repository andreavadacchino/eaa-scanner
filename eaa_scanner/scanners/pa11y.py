from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List
import os
import tempfile
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
        
        # Modalità simulata
        if self.simulate:
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Simulazione analisi Pa11y", 60)
            return self._simulate(url)
            
        # Usa il runner Node.js per Pa11y
        try:
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Avvio analisi Pa11y", 20)
            
            # FORZA USO CLI INVECE DEL RUNNER
            # Il runner ha problemi con i moduli nel container Docker
            # Vai direttamente alla CLI che funziona meglio
            return self._scan_with_cli(url, hooks)
            
            if hooks:
                hooks.emit_scanner_operation("Pa11y", "Esecuzione analisi accessibilità", 50)
            
            # Esegui il runner Node.js
            cmd = ["node", runner_path, url, "WCAG2AA", str(self.timeout_ms)]
            completed = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
            
            if completed.returncode != 0:
                # Prova a parsare stdout anche in caso di errore
                try:
                    error_data = json.loads(completed.stdout or completed.stderr or "{}")
                    return Pa11yResult(ok=False, json=error_data)
                except:
                    return Pa11yResult(ok=False, json={"error": completed.stderr or "Pa11y scan failed"})
            
            # Parsa i risultati
            data = json.loads(completed.stdout or "{}")
            
            if hooks:
                issues_count = len(data.get("issues", []))
                hooks.emit_scanner_operation("Pa11y", f"Trovati {issues_count} problemi", 100)
            
            return Pa11yResult(ok=True, json=data)
            
        except Exception as e:
            return Pa11yResult(ok=False, json={"error": str(e)})
    
    def _scan_with_cli(self, url: str, hooks) -> Pa11yResult:
        """Fallback al CLI standard di Pa11y"""
        try:
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
                    hooks.emit_scanner_operation("Pa11y", "Pa11y non trovato", 100)
                raise Exception(f"Pa11y not found. Tried: {choices}")
            
            # Configurazione browser per container Docker
            config_data = {
                "chromeLaunchConfig": {
                    "executablePath": "/usr/bin/chromium",
                    "args": [
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--headless"
                    ]
                },
                "timeout": 30000
            }
            
            # Crea un file di configurazione temporaneo
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
                json.dump(config_data, config_file)
                config_path = config_file.name
            
            try:
                cmd = base + [
                    "--reporter", "json",
                    "--config", config_path,
                    url
                ]
                completed = run_command(cmd, timeout_sec=self.timeout_ms / 1000.0)
                if completed.returncode != 0:
                    return Pa11yResult(ok=False, json={"error": completed.stderr})
                data = json.loads(completed.stdout or "{}")
                if isinstance(data, list):
                    data = {"issues": data}
                return Pa11yResult(ok=True, json=data)
            finally:
                try:
                    os.unlink(config_path)
                except:
                    pass
        except Exception as e:
            return Pa11yResult(ok=False, json={"error": str(e)})

    def _simulate(self, url: str) -> Pa11yResult:
        # Dati realistici basati su scan reale di Principia.it
        data = {
            "documentTitle": "Principia – Navis browse data of your plant",
            "pageUrl": url,
            "issues": [
                # CRITICAL ISSUES (2)
                {
                    "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.InputText.Name",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This textinput element does not have a name available to an accessibility API. Valid names are: label element, title undefined, aria-label undefined, aria-labelledby undefined.",
                    "context": "<input type=\"text\" name=\"s\" value=\"\" class=\"s\" placeholder=\"Search...\">",
                    "selector": "#top-header > div > div:nth-child(2) > div:nth-child(3) > form > input"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_3.1_3_1.F68",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This form field should be labelled in some way. Use the label element (either with a \"for\" attribute or wrapped around the form field), or \"title\", \"aria-label\" or \"aria-labelledby\" attributes as appropriate.",
                    "context": "<input type=\"text\" name=\"s\" value=\"\" class=\"s\" placeholder=\"Search...\">",
                    "selector": "#top-header > div > div:nth-child(2) > div:nth-child(3) > form > input"
                },
                # HIGH ISSUES (15)
                {
                    "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.Button.Name",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This button element does not have a name available to an accessibility API. Valid names are: title undefined, element content, aria-label undefined, aria-labelledby undefined.",
                    "context": "<button type=\"submit\" name=\"submit\" class=\"searchsubmit\"><i class=\"fa fa-search\"></i></button>",
                    "selector": "#top-header > div > div:nth-child(2) > div:nth-child(3) > form > button"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"https://www.principia.it/\">Home</a>",
                    "selector": "#menu-item-51 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"#\">Company</a>",
                    "selector": "#menu-item-321 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"#\">Products</a>",
                    "selector": "#menu-item-322 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"#\">Applications</a>",
                    "selector": "#menu-item-323 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"https://www.principia.it/en/support/\">Support</a>",
                    "selector": "#menu-item-194 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"https://www.principia.it/en/download/\">Download</a>",
                    "selector": "#menu-item-195 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<span style=\"margin-left:0.3em;\">Italiano</span>",
                    "selector": "#menu-item-61-it > a > span"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 4.25:1.",
                    "context": "<span style=\"margin-left:0.3em;\">English</span>",
                    "selector": "#menu-item-61-en > a > span"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H37",
                    "type": "error",
                    "typeCode": 1,
                    "message": "Img element missing an alt attribute. Use the alt attribute to specify a short text alternative.",
                    "context": "<img src=\"https://www.principia.it/wp-content/uploads/2020/02/slider1.jpg\">",
                    "selector": "#masthead > div:nth-child(3) > div > div > div > div:nth-child(1) > ul > li:nth-child(1) > img"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 1.18:1.",
                    "context": "<a href=\"\" data-slide-index=\"0\" class=\"bx-pager-link active\">1</a>",
                    "selector": "#masthead > div:nth-child(3) > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(1) > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"\" data-slide-index=\"1\" class=\"bx-pager-link\">2</a>",
                    "selector": "#masthead > div:nth-child(3) > div > div > div > div:nth-child(2) > div:nth-child(2) > div:nth-child(2) > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G145.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 3:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<h4>Navis browse data of your plant...</h4>",
                    "selector": "#call-to-action > div > h4"
                },
                {
                    "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.A.EmptyNoId",
                    "type": "error",
                    "typeCode": 1,
                    "message": "Anchor element found with no link content and no name and/or ID attribute.",
                    "context": "<a class=\"action-btn\" href=\"\"></a>",
                    "selector": "#call-to-action > div > a"
                },
                # MEDIUM ISSUES (5)
                {
                    "code": "WCAG2AA.Principle1.Guideline1_3.1_3_1.H42.2",
                    "type": "error",
                    "typeCode": 1,
                    "message": "Heading tag found with no content. Text that is not intended as a heading should not be marked up with heading tags.",
                    "context": "<h2><a href=\"https://www.principia...</h2>",
                    "selector": "#welcome-text > h2"
                },
                {
                    "code": "WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.A.NoContent",
                    "type": "error",
                    "typeCode": 1,
                    "message": "Anchor element found with a valid href attribute, but no link content has been supplied.",
                    "context": "<a href=\"https://www.principia.it/en/2017/03/17/welcome/\"></a>",
                    "selector": "#welcome-text > h2 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_1.1_1_1.H30.2",
                    "type": "error",
                    "typeCode": 1,
                    "message": "Img element is the only content of the link, but is missing alt text. The alt text should describe the purpose of the link.",
                    "context": "<a href=\"https://www.principia.it/en/2017/03/17/welcome/\">\\n\\t\\t\\t\\t\\t\\t<img src=\"https://www.pr...</a>",
                    "selector": "#welcome-text > figure > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"https://www.principia.it/en/2017/04/07/new-data-aware-components/\">New Data Aware Components</a>",
                    "selector": "#latest-events > div:nth-child(2) > div > h4 > a"
                },
                {
                    "code": "WCAG2AA.Principle1.Guideline1_4.1_4_3.G18.Fail",
                    "type": "error",
                    "typeCode": 1,
                    "message": "This element has insufficient contrast at this conformance level. Expected a contrast ratio of at least 4.5:1, but text in this element has a contrast ratio of 2.81:1.",
                    "context": "<a href=\"https://www.principia.it/en/2017/04/07/trends-converter/\">Trends Converter</a>",
                    "selector": "#latest-events > div:nth-child(3) > div > h4 > a"
                }
            ]
        }
        return Pa11yResult(ok=True, json=data)
