from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from .config import Config
from .core import run_scan


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="EAA Multi-Scanner (Python)")
    p.add_argument("--url", help="Target URL")
    p.add_argument("--company_name", help="Company name")
    p.add_argument("--email", help="Contact email")
    p.add_argument("--wave_api_key", help="WAVE API key", default="")
    
    # LLM Integration arguments
    p.add_argument("--openai_api_key", help="OpenAI API key for LLM features", default="")
    p.add_argument("--llm_model_primary", help="Primary LLM model", default="gpt-4o")
    p.add_argument("--llm_model_fallback", help="Fallback LLM model", default="gpt-3.5-turbo")
    p.add_argument("--llm_enabled", help="Enable/disable LLM features", type=lambda x: x.lower() in ('true', '1', 'yes'), default=True)
    
    # PDF Generation arguments
    p.add_argument("--pdf_engine", help="PDF engine (auto, weasyprint, chrome, wkhtmltopdf)", default="auto")
    p.add_argument("--pdf_format", help="PDF page format (A4, Letter, etc)", default="A4")
    p.add_argument("--pdf_margins", help="PDF margins in inches (top,right,bottom,left)", default=None)
    
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--simulate", action="store_true", help="Run in simulate (offline) mode")
    mode.add_argument("--real", action="store_true", help="Run real scanners (requires tools/network)")
    p.add_argument("--output-dir", default="output", help="Output directory")
    p.add_argument("--config", help="JSON config file with fields matching CLI arguments")
    return p.parse_args()


def load_config(ns: argparse.Namespace) -> Config:
    args: Dict[str, Any] = {}
    if ns.config:
        path = Path(ns.config)
        args.update(json.loads(path.read_text(encoding="utf-8")))
    for k, v in vars(ns).items():
        if v is not None and k != "config":
            args[k] = v
    if ns.real:
        args["simulate"] = False
    cfg = Config.from_env_or_args(args)
    cfg.validate()
    return cfg


def main() -> int:
    ns = parse_args()
    cfg = load_config(ns)
    result = run_scan(cfg, output_root=Path(ns.output_dir or "output"))
    scan_id = result["scan_id"]
    base_out = Path(result["base_out"]) 
    aggregated = result["aggregated"]
    report_path = Path(result["report_html_path"])

    # API-like response (mimic n8n final-response node)
    api_response = {
        "status": "success",
        "message": "Report accessibilità EAA completato con successo (simulato)" if cfg.simulate else "Report accessibilità EAA completato con successo",
        "scan_info": {
            "scan_id": scan_id,
            "timestamp": aggregated.get("timestamp"),
            "url": cfg.url,
            "company_name": cfg.company_name,
        },
        "compliance_results": {
            "wcag_version": aggregated.get("compliance", {}).get("wcag_version"),
            "wcag_level": aggregated.get("compliance", {}).get("wcag_level"),
            "compliance_level": aggregated.get("compliance", {}).get("compliance_level"),
            "eaa_compliance": aggregated.get("compliance", {}).get("eaa_compliance"),
            "overall_score": aggregated.get("compliance", {}).get("overall_score"),
            "total_errors": aggregated.get("compliance", {}).get("total_unique_errors"),
            "total_warnings": aggregated.get("compliance", {}).get("total_unique_warnings"),
            "total_issues": aggregated.get("compliance", {}).get("total_issues"),
        },
        "scanner_results": {
            "wave_score": aggregated.get("detailed_results", {}).get("scanner_scores", {}).get("wave"),
            "pa11y_score": aggregated.get("detailed_results", {}).get("scanner_scores", {}).get("pa11y"),
            "axe_core_score": aggregated.get("detailed_results", {}).get("scanner_scores", {}).get("axe_core"),
            "lighthouse_score": aggregated.get("detailed_results", {}).get("scanner_scores", {}).get("lighthouse"),
            "scanners_used": aggregated.get("scan_metadata", {}).get("scanners_used", []),
        },
        "report_info": {
            "html_report_generated": True,
            "report_filename": report_path.name,
            "report_size_bytes": report_path.stat().st_size if report_path.exists() else 0,
            "pdf_report_generated": result.get("pdf_status") == "success",
            "pdf_filename": Path(result["report_pdf_path"]).name if result.get("report_pdf_path") else None,
            "pdf_size_bytes": Path(result["report_pdf_path"]).stat().st_size if result.get("report_pdf_path") and Path(result["report_pdf_path"]).exists() else 0,
            "pdf_engine_used": cfg.pdf_engine,
            "pdf_status": result.get("pdf_status"),
            "ai_synthesis_generated": False,
        },
        "notifications": {
            "email_sent": False,
            "telegram_sent": False,
            "recipient": cfg.email,
        },
        "recommendations_summary": aggregated.get("recommendations", [])[:3] if aggregated.get("recommendations") else [],
        "next_steps": [
            "Rivedere il report HTML generato",
            f"Prioritizzare correzione errori critici ({aggregated.get('compliance',{}).get('total_unique_errors',0)} trovati)",
            "Implementare raccomandazioni ad alta priorità",
            "Pianificare controllo accessibilità periodico",
            "Considerare formazione team su WCAG 2.1 AA",
        ],
        "technical_details": {
            "processing_time": "variable (simulated)",
            "workflow_version": "python-0.1",
            "standards_compliance": ["WCAG 2.1 AA", "European Accessibility Act (EAA)"],
        },
    }
    (base_out / "api_response.json").write_text(json.dumps(api_response, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Generated:")
    for f in ["wave.json", "pa11y.json", "axe.json", "lighthouse.json", "summary.json", "api_response.json"]:
        p = base_out / f
        if p.exists():
            print(" -", p)
    print(" -", report_path)
    
    # Informazioni PDF
    if result.get("pdf_status") == "success" and result.get("report_pdf_path"):
        pdf_path = Path(result["report_pdf_path"])
        pdf_size_kb = pdf_path.stat().st_size / 1024
        print(f" - {pdf_path} ({pdf_size_kb:.1f} KB, engine: {cfg.pdf_engine})")
    elif result.get("pdf_status"):
        print(f" - PDF generation: {result['pdf_status']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
