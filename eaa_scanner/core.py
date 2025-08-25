from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import Config, new_scan_id
from .scanners import WaveScanner, Pa11yScanner, AxeScanner, LighthouseScanner
from .processors import process_wave, process_pa11y, normalize_all
from .report import generate_html_report, write_report
from .pdf import create_pdf_with_options, get_pdf_engines_status
from .crawler import WebCrawler
from .page_sampler import (
    SmartPageSamplerCoordinator, 
    SamplerConfig, 
    SelectionStrategy,
    AnalysisDepth
)
from .methodology import TestMethodology, MetadataManager
from .analytics import AccessibilityAnalytics
from .charts import ChartGenerator
from .remediation import RemediationPlanManager
from .accessibility_statement import generate_statement_from_scan
from .scan_events import ScanEventHooks, set_current_hooks, MonitoredScanner


def run_scan(cfg: Config, output_root: Path | None = None, 
            enable_crawling: bool = False,
            crawler_config: Optional[Dict[str, Any]] = None,
            methodology_config: Optional[Dict[str, Any]] = None,
            report_type: str = "standard",
            event_monitor=None,
            scan_id: Optional[str] = None) -> Dict[str, Any]:
    
    # DEBUG: Log parametri ricevuti
    print(f"🔍 DEBUG run_scan - cfg.url: {repr(cfg.url)}")
    print(f"🔍 DEBUG run_scan - cfg.company_name: {repr(cfg.company_name)}")
    import logging
    logging.getLogger(__name__).info(f"EAA CORE: Received URL = {cfg.url}")
    
    output_root = output_root or Path("output")
    # Usa scan_id fornito o genera nuovo
    if not scan_id:
        scan_id = new_scan_id()
    base_out = output_root / scan_id
    base_out.mkdir(parents=True, exist_ok=True)
    
    # Configura hooks per eventi se monitor è fornito
    hooks = None
    if event_monitor:
        hooks = ScanEventHooks(scan_id)
        hooks.set_monitor(event_monitor)
        set_current_hooks(hooks)
    
    # Configurazione crawler per scansione multi-pagina
    urls_to_scan = [cfg.url]
    if enable_crawling and crawler_config:
        try:
            crawler = WebCrawler(
                base_url=cfg.url,
                max_pages=crawler_config.get('max_pages', 10),
                max_depth=crawler_config.get('max_depth', 2),
                follow_external=crawler_config.get('follow_external', False),
                allowed_domains=crawler_config.get('allowed_domains'),
                excluded_patterns=crawler_config.get('excluded_patterns')
            )
            discovered_urls = crawler.crawl()
            
            # Se il crawler trova URL, usale; altrimenti mantieni l'URL originale
            if discovered_urls:
                urls_to_scan = discovered_urls[:crawler_config.get('max_pages', 10)]
            else:
                print(f"Avviso: Il crawler non ha trovato pagine aggiuntive, procedo con URL base: {cfg.url}")
                urls_to_scan = [cfg.url]
            
            # Salva risultati crawler
            crawler_results = {
                "discovered_urls": discovered_urls,
                "total_discovered": len(discovered_urls),
                "scanned_urls": urls_to_scan,
                "crawler_config": crawler_config
            }
            (base_out / "crawler_results.json").write_text(
                json.dumps(crawler_results, indent=2, ensure_ascii=False), 
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Errore durante il crawling: {e}. Procedo con URL singolo.")
            urls_to_scan = [cfg.url]
    
    # Inizializza metodologia di test
    methodology = TestMethodology()
    if methodology_config:
        for key, value in methodology_config.items():
            if hasattr(methodology, key):
                setattr(methodology, key, value)
    
    # Aggiorna sample_pages con URLs scoperte
    methodology.sample_pages = urls_to_scan
    methodology_dict = methodology.to_dict()
    (base_out / "methodology.json").write_text(
        json.dumps(methodology_dict, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    # Run scanners su tutte le URL
    all_results = []
    
    for i, url in enumerate(urls_to_scan):
        # Emetti evento progresso pagine
        if hooks:
            hooks.emit_page_progress(i + 1, len(urls_to_scan), url)
            
        wave_res = None
        pa11y_res = None
        axe_res = None
        lighthouse_res = None
        
        url_dir = base_out / f"page_{i+1}"
        url_dir.mkdir(exist_ok=True)
        
        if cfg.scanners_enabled.wave:
            try:
                wave = MonitoredScanner(
                    WaveScanner(
                        api_key=cfg.wave_api_key,
                        timeout_ms=min(cfg.scanner_timeout_ms, 30000),
                        simulate=cfg.simulate,
                    ),
                    "WAVE",
                )
                r = wave.scan(url)
                wave_res = process_wave(r.json)
                (url_dir / "wave.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"WAVE scanner error: {e}")
                # Segnala errore invece di simulare
                wave_res = None
                print(f"⚠️ WAVE scan failed for {url}: {e}")

        if cfg.scanners_enabled.pa11y:
            try:
                pz = MonitoredScanner(
                    Pa11yScanner(
                        timeout_ms=min(cfg.scanner_timeout_ms, 30000),
                        simulate=cfg.simulate,
                    ),
                    "Pa11y",
                )
                r = pz.scan(url)
                pa11y_res = process_pa11y(r.json)
                (url_dir / "pa11y.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"Pa11y scanner error: {e}")
                # Segnala errore invece di simulare
                pa11y_res = None
                print(f"⚠️ Pa11y scan failed for {url}: {e}")

        if cfg.scanners_enabled.axe_core:
            try:
                axe = MonitoredScanner(
                    AxeScanner(
                        timeout_ms=min(cfg.scanner_timeout_ms, 30000),
                        simulate=cfg.simulate,
                    ),
                    "Axe-core",
                )
                r = axe.scan(url)
                axe_res = r.json
                (url_dir / "axe.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"Axe scanner error: {e}")
                # Segnala errore invece di simulare
                axe_res = None
                print(f"⚠️ Axe scan failed for {url}: {e}")

        if cfg.scanners_enabled.lighthouse:
            try:
                lh = MonitoredScanner(
                    LighthouseScanner(
                        timeout_ms=min(cfg.scanner_timeout_ms, 30000),
                        simulate=cfg.simulate,
                    ),
                    "Lighthouse",
                )
                r = lh.scan(url)
                lighthouse_res = r.json
                (url_dir / "lighthouse.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"Lighthouse scanner error: {e}")
                # Segnala errore invece di simulare
                lighthouse_res = None
                print(f"⚠️ Lighthouse scan failed for {url}: {e}")
        
        # Normalizza risultati per questa URL
        url_results = normalize_all(
            url=url,
            company_name=cfg.company_name,
            wave=wave_res,
            pa11y=pa11y_res,
            axe=axe_res,
            lighthouse=lighthouse_res,
        )
        url_results["page_index"] = i + 1
        all_results.append(url_results)
        
        # Salva risultati per singola pagina
        (url_dir / "summary.json").write_text(
            json.dumps(url_results, indent=2, ensure_ascii=False), 
            encoding="utf-8"
        )
    
    # Aggrega risultati di tutte le pagine
    if len(all_results) == 0:
        # Nessun risultato disponibile - errore critico
        raise ValueError("Nessuna pagina scansionata con successo. Verifica l'URL e la connessione.")
    elif len(all_results) > 1:
        aggregated = _aggregate_multi_page_results(all_results, cfg.url, cfg.company_name)
    else:
        aggregated = all_results[0]

    aggregated.update(
        {
            "scan_id": scan_id,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "methodology": methodology_dict,
            "pages_scanned": len(urls_to_scan),
            "multi_page_scan": len(urls_to_scan) > 1
        }
    )

    (base_out / "summary.json").write_text(json.dumps(aggregated, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Genera analytics avanzate
    if hooks:
        hooks.emit_processing_step("Generazione analytics", 70)
    analytics = AccessibilityAnalytics(aggregated)
    analytics_data = analytics.generate_complete_analytics()
    (base_out / "analytics.json").write_text(
        json.dumps(analytics_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera grafici e visualizzazioni
    if hooks:
        hooks.emit_processing_step("Generazione grafici", 80)
    chart_generator = ChartGenerator(output_dir=base_out)
    charts_data = chart_generator.generate_all_charts(analytics_data)
    (base_out / "charts.json").write_text(
        json.dumps(charts_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera piano di remediation
    remediation = RemediationPlanManager(aggregated, cfg.company_name)
    remediation_plan = remediation.generate_comprehensive_plan()
    (base_out / "remediation_plan.json").write_text(
        json.dumps(remediation_plan, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera dichiarazione di accessibilità
    org_data = {
        "name": cfg.company_name,
        "type": "privato",
        "website_name": cfg.company_name,
        "email": cfg.email
    }
    accessibility_statement = generate_statement_from_scan(aggregated, org_data).to_dict()
    (base_out / "accessibility_statement.json").write_text(
        json.dumps(accessibility_statement, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Arricchisci i dati aggregati con nuove informazioni
    aggregated.update({
        "analytics": analytics_data,
        "charts": charts_data,
        "remediation_plan": remediation_plan,
        "accessibility_statement": accessibility_statement
    })

    # Generate HTML report (standard o professionale)
    if hooks:
        hooks.emit_report_generation("Generazione report HTML", 90)
    if report_type == "professional":
        html_report = _generate_professional_report(aggregated, cfg)
    else:
        html_report = generate_html_report(aggregated, cfg)
    
    report_path = write_report(base_out / f"report_{cfg.company_name.replace(' ', '_')}.html", html_report)
    
    # Genera PDF se richiesto
    pdf_path = None
    pdf_status = None
    try:
        pdf_filename = f"report_{cfg.company_name.replace(' ', '_')}.pdf"
        pdf_path = base_out / pdf_filename
        
        # Configura opzioni PDF dalla configurazione
        margins = cfg.get_pdf_margins_dict()
        
        pdf_success = create_pdf_with_options(
            html_path=report_path,
            pdf_path=pdf_path,
            engine=cfg.pdf_engine,
            page_format=cfg.pdf_page_format,
            margins=margins,
            timeout=120
        )
        
        if pdf_success:
            pdf_status = "success"
        else:
            pdf_status = "failed"
            pdf_path = None
            
    except Exception as e:
        pdf_status = f"error: {str(e)}"
        pdf_path = None
    
    # API-like response metadata
    api_response = {
        "status": "success",
        "message": "Report generato",
        "scan_info": {
            "scan_id": scan_id,
            "timestamp": aggregated.get("timestamp"),
            "url": cfg.url,
            "company_name": cfg.company_name,
        },
    }
    (base_out / "api_response.json").write_text(json.dumps(api_response, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "scan_id": scan_id,
        "base_out": str(base_out),
        "summary_path": str(base_out / "summary.json"),
        "report_html_path": str(report_path),
        "report_pdf_path": str(pdf_path) if pdf_path else None,
        "pdf_status": pdf_status,
        "aggregated": aggregated,
        "analytics_path": str(base_out / "analytics.json"),
        "charts_path": str(base_out / "charts.json"),
        "remediation_path": str(base_out / "remediation_plan.json"),
        "statement_path": str(base_out / "accessibility_statement.json"),
        "pages_scanned": len(urls_to_scan),
        "report_type": report_type
    }


def _aggregate_multi_page_results(results: List[Dict], base_url: str, company_name: str) -> Dict[str, Any]:
    """
    Aggrega risultati di scansione multi-pagina
    
    Args:
        results: Lista risultati per pagina
        base_url: URL base del sito
        company_name: Nome azienda
        
    Returns:
        Risultati aggregati
    """
    if not results:
        return {}
    
    # Usa il primo risultato come base
    aggregated = results[0].copy()
    
    # Assicura che detailed_results esista e abbia le chiavi necessarie
    if "detailed_results" not in aggregated:
        aggregated["detailed_results"] = {}
    
    # Assicura che le chiavi errors, warnings, notices esistano
    if "errors" not in aggregated["detailed_results"]:
        aggregated["detailed_results"]["errors"] = []
    if "warnings" not in aggregated["detailed_results"]:
        aggregated["detailed_results"]["warnings"] = []
    if "notices" not in aggregated["detailed_results"]:
        aggregated["detailed_results"]["notices"] = []
    
    # Aggrega errori e warning da tutte le pagine
    all_errors = []
    all_warnings = []
    all_notices = []
    
    for result in results:
        if "detailed_results" in result:
            details = result["detailed_results"]
            all_errors.extend(details.get("errors", []))
            all_warnings.extend(details.get("warnings", []))
            all_notices.extend(details.get("notices", []))
    
    # Deduplica per codice + criterio WCAG
    seen_errors = set()
    unique_errors = []
    for error in all_errors:
        key = (error.get("code"), error.get("wcag_criteria"))
        if key not in seen_errors:
            seen_errors.add(key)
            unique_errors.append(error)
    
    seen_warnings = set()
    unique_warnings = []
    for warning in all_warnings:
        key = (warning.get("code"), warning.get("wcag_criteria"))
        if key not in seen_warnings:
            seen_warnings.add(key)
            unique_warnings.append(warning)
    
    # Aggiorna risultati aggregati
    aggregated["detailed_results"]["errors"] = unique_errors
    aggregated["detailed_results"]["warnings"] = unique_warnings
    aggregated["detailed_results"]["notices"] = all_notices[:100]  # Limita notices
    
    # Ricalcola score complessivo
    total_issues = len(unique_errors) + len(unique_warnings)
    critical_count = sum(1 for e in unique_errors if e.get("severity") == "critical")
    high_count = sum(1 for e in unique_errors if e.get("severity") == "high")
    
    # Formula per score aggregato
    if total_issues == 0:
        score = 100
    else:
        penalty = (critical_count * 10) + (high_count * 5) + (len(unique_errors) * 2) + len(unique_warnings)
        score = max(0, 100 - penalty)
    
    aggregated["compliance"]["overall_score"] = score
    
    # Determina livello conformità
    if score >= 90:
        aggregated["compliance"]["compliance_level"] = "conforme"
    elif score >= 70:
        aggregated["compliance"]["compliance_level"] = "parzialmente_conforme"
    else:
        aggregated["compliance"]["compliance_level"] = "non_conforme"
    
    # Aggiungi metadati multi-pagina
    aggregated["multi_page_summary"] = {
        "total_pages_scanned": len(results),
        "base_url": base_url,
        "unique_errors": len(unique_errors),
        "unique_warnings": len(unique_warnings),
        "pages_with_errors": sum(1 for r in results if r.get("detailed_results", {}).get("errors")),
        "aggregation_method": "deduplicated_by_code_and_wcag"
    }
    
    return aggregated


def _generate_professional_report(data: Dict[str, Any], config: Config = None) -> str:
    """
    Genera report HTML professionale con supporto LLM
    
    Args:
        data: Dati completi scansione
        config: Configurazione con impostazioni LLM
        
    Returns:
        HTML del report
    """
    # Arricchisci i dati con LLM se disponibile
    if config:
        from .report import enhance_data_with_llm
        data = enhance_data_with_llm(data, config)
    from jinja2 import Environment, FileSystemLoader
    import os
    
    # Configura Jinja2
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    
    # Carica template professionale
    template = env.get_template("report_professionale.html")
    
    # Prepara dati per template
    context = {
        "scan_data": data,
        "company_name": data.get("company_name", "N/A"),
        "url": data.get("url", "N/A"),
        "scan_date": data.get("timestamp", "N/A"),
        "compliance": data.get("compliance", {}),
        "analytics": data.get("analytics", {}),
        "charts": data.get("charts", {}),
        "remediation": data.get("remediation_plan", {}),
        "statement": data.get("accessibility_statement", {}),
        "methodology": data.get("methodology", {}),
        "detailed_results": data.get("detailed_results", {}),
        "multi_page": data.get("multi_page_scan", False),
        "pages_scanned": data.get("pages_scanned", 1)
    }
    
    # Renderizza template
    return template.render(**context)


def run_smart_scan(cfg: Config, output_root: Path | None = None,
                  sampler_config: Optional[Dict[str, Any]] = None,
                  report_type: str = "standard",
                  scan_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Esegue scansione utilizzando Smart Page Sampler per selezione intelligente pagine
    
    Args:
        cfg: Configurazione base scanner
        output_root: Directory output
        sampler_config: Configurazione per Smart Page Sampler
        report_type: Tipo di report (standard/professional)
        scan_id: ID scan da usare (opzionale, se non fornito viene generato)
        
    Returns:
        Dizionario con risultati scansione
    """
    output_root = output_root or Path("output")
    # Usa scan_id fornito o genera nuovo
    if not scan_id:
        scan_id = new_scan_id()
    base_out = output_root / scan_id
    base_out.mkdir(parents=True, exist_ok=True)
    
    # FASE 1: Smart Page Sampling
    print("\n🚀 Avvio Smart Page Sampling...")
    
    # Configura sampler
    sampler_cfg = SamplerConfig()
    if sampler_config:
        # Aggiorna configurazione con parametri forniti
        for key, value in sampler_config.items():
            if hasattr(sampler_cfg, key):
                setattr(sampler_cfg, key, value)
    
    # Override output directory per sampler
    sampler_cfg.output_dir = str(base_out / "page_sampler")
    
    # Inizializza e esegui sampler
    sampler = SmartPageSamplerCoordinator(sampler_cfg)
    sampler_result = sampler.execute(cfg.url)
    
    # Salva risultati sampler
    sampler_data = sampler_result.to_dict()
    (base_out / "sampler_result.json").write_text(
        json.dumps(sampler_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Verifica errori critici
    if sampler_result.errors and not sampler_result.selected_pages:
        raise ValueError(f"Smart sampling fallito: {'; '.join(sampler_result.errors)}")
    
    # Ottieni configurazione per scanner
    try:
        scan_config = sampler.get_scan_configuration()
        urls_to_scan = scan_config['urls']
    except Exception as e:
        print(f"⚠️ Errore ottenendo configurazione scanner: {e}")
        # Fallback: usa URL base
        urls_to_scan = [cfg.url]
        scan_config = {'urls': urls_to_scan}
    
    print(f"✅ Smart sampling completato: {len(urls_to_scan)} pagine selezionate")
    print(f"   - Template identificati: {len(sampler_result.templates)}")
    print(f"   - Strategia: {sampler_result.selection_strategy}")
    print(f"   - Tempo stimato: {sampler_result.estimated_scan_time.get('total_hours', 0):.1f} ore")
    
    # FASE 2: Metodologia di test aggiornata
    methodology = TestMethodology()
    methodology.sample_pages = urls_to_scan
    methodology.sampling_method = sampler_result.selection_strategy
    methodology.templates_covered = len(sampler_result.templates)
    methodology.wcag_em_compliant = sampler_result.selection_strategy == "wcag_em"
    
    methodology_dict = methodology.to_dict()
    methodology_dict.update({
        'smart_sampling': {
            'pages_discovered': sampler_result.total_discovered,
            'templates_identified': len(sampler_result.templates),
            'selection_reasons': sampler_result.selection_reasons,
            'depth_configurations': sampler_result.depth_summary
        }
    })
    
    (base_out / "methodology.json").write_text(
        json.dumps(methodology_dict, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # FASE 3: Scansione con profondità configurata
    print("\n🔍 Inizio scansione accessibilità...")
    all_results = []
    
    # Mappa URL -> configurazione profondità
    depth_configs = {}
    for page, depth_config in sampler_result.depth_configs:
        depth_configs[page['url']] = depth_config
    
    for i, url in enumerate(urls_to_scan):
        print(f"\n📄 Scansione pagina {i+1}/{len(urls_to_scan)}: {url}")
        
        # Ottieni configurazione profondità per questa pagina
        page_depth = depth_configs.get(url)
        if page_depth:
            print(f"   Profondità: {page_depth.level.value} ({page_depth.estimated_time_minutes} min)")
        
        wave_res = None
        pa11y_res = None
        axe_res = None
        lighthouse_res = None
        
        url_dir = base_out / f"page_{i+1}"
        url_dir.mkdir(exist_ok=True)
        
        # Esegui scanner in base a configurazione profondità
        scanners_to_use = cfg.scanners_enabled
        if page_depth:
            # Usa scanner configurati per questa profondità
            scan_params = sampler.depth_manager.get_scan_configuration(page_depth)
            scanners_enabled = scan_params['scanners_enabled']
            
            # Override timeout se necessario
            scanner_timeout = scan_params.get('timeout_per_scanner', cfg.scanner_timeout_ms)
        else:
            scanners_enabled = {
                'wave': cfg.scanners_enabled.wave,
                'axe': cfg.scanners_enabled.axe_core,
                'pa11y': cfg.scanners_enabled.pa11y,
                'lighthouse': cfg.scanners_enabled.lighthouse
            }
            scanner_timeout = cfg.scanner_timeout_ms
        
        # Esegui scanner abilitati
        if scanners_enabled.get('wave') and cfg.scanners_enabled.wave:
            wave = WaveScanner(api_key=cfg.wave_api_key, timeout_ms=scanner_timeout, simulate=cfg.simulate)
            r = wave.scan(url)
            wave_res = process_wave(r.json)
            (url_dir / "wave.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
        
        if scanners_enabled.get('pa11y') and cfg.scanners_enabled.pa11y:
            pz = Pa11yScanner(timeout_ms=scanner_timeout, simulate=cfg.simulate)
            r = pz.scan(url)
            pa11y_res = process_pa11y(r.json)
            (url_dir / "pa11y.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
        
        if scanners_enabled.get('axe') and cfg.scanners_enabled.axe_core:
            axe = AxeScanner(timeout_ms=scanner_timeout, simulate=cfg.simulate)
            r = axe.scan(url)
            axe_res = r.json
            (url_dir / "axe.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
        
        if scanners_enabled.get('lighthouse') and cfg.scanners_enabled.lighthouse:
            lh = LighthouseScanner(timeout_ms=scanner_timeout, simulate=cfg.simulate)
            r = lh.scan(url)
            lighthouse_res = r.json
            (url_dir / "lighthouse.json").write_text(json.dumps(r.json, indent=2), encoding="utf-8")
        
        # Normalizza risultati
        url_results = normalize_all(
            url=url,
            company_name=cfg.company_name,
            wave=wave_res,
            pa11y=pa11y_res,
            axe=axe_res,
            lighthouse=lighthouse_res,
        )
        url_results["page_index"] = i + 1
        url_results["page_category"] = sampler_result.selection_reasons.get(url, "general")
        url_results["depth_config"] = page_depth.level.value if page_depth else "standard"
        
        all_results.append(url_results)
        
        # Salva risultati per singola pagina
        (url_dir / "summary.json").write_text(
            json.dumps(url_results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    # Aggrega risultati
    if len(all_results) == 0:
        raise ValueError("Nessuna pagina scansionata con successo")
    elif len(all_results) > 1:
        aggregated = _aggregate_multi_page_results(all_results, cfg.url, cfg.company_name)
    else:
        aggregated = all_results[0]
    
    # Aggiungi metadati smart sampling
    aggregated.update({
        "scan_id": scan_id,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "methodology": methodology_dict,
        "pages_scanned": len(urls_to_scan),
        "multi_page_scan": len(urls_to_scan) > 1,
        "smart_sampling": sampler_data
    })
    
    (base_out / "summary.json").write_text(
        json.dumps(aggregated, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # FASE 4: Analytics e report (come in run_scan)
    print("\n📊 Generazione analytics e report...")
    
    # Genera analytics
    analytics = AccessibilityAnalytics(aggregated)
    analytics_data = analytics.generate_complete_analytics()
    (base_out / "analytics.json").write_text(
        json.dumps(analytics_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera grafici
    chart_generator = ChartGenerator(output_dir=base_out)
    charts_data = chart_generator.generate_all_charts(analytics_data)
    (base_out / "charts.json").write_text(
        json.dumps(charts_data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera piano di remediation
    remediation = RemediationPlanManager(aggregated, cfg.company_name)
    remediation_plan = remediation.generate_comprehensive_plan()
    (base_out / "remediation_plan.json").write_text(
        json.dumps(remediation_plan, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Genera dichiarazione accessibilità
    org_data = {
        "name": cfg.company_name,
        "type": "privato",
        "website_name": cfg.company_name,
        "email": cfg.email
    }
    accessibility_statement = generate_statement_from_scan(aggregated, org_data).to_dict()
    (base_out / "accessibility_statement.json").write_text(
        json.dumps(accessibility_statement, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    # Arricchisci dati aggregati
    aggregated.update({
        "analytics": analytics_data,
        "charts": charts_data,
        "remediation_plan": remediation_plan,
        "accessibility_statement": accessibility_statement
    })
    
    # Genera report HTML
    if report_type == "professional":
        html_report = _generate_professional_report(aggregated, cfg)
    else:
        html_report = generate_html_report(aggregated, cfg)
    
    report_path = write_report(
        base_out / f"report_{cfg.company_name.replace(' ', '_')}.html",
        html_report
    )
    
    # API response
    api_response = {
        "status": "success",
        "message": "Smart scan completato",
        "scan_info": {
            "scan_id": scan_id,
            "timestamp": aggregated.get("timestamp"),
            "url": cfg.url,
            "company_name": cfg.company_name,
            "pages_scanned": len(urls_to_scan),
            "templates_found": len(sampler_result.templates),
            "selection_strategy": sampler_result.selection_strategy
        }
    }
    (base_out / "api_response.json").write_text(
        json.dumps(api_response, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"\n✅ Scansione completata! Report salvato in: {report_path}")
    
    return {
        "scan_id": scan_id,
        "base_out": str(base_out),
        "summary_path": str(base_out / "summary.json"),
        "report_html_path": str(report_path),
        "aggregated": aggregated,
        "analytics_path": str(base_out / "analytics.json"),
        "charts_path": str(base_out / "charts.json"),
        "remediation_path": str(base_out / "remediation_plan.json"),
        "statement_path": str(base_out / "accessibility_statement.json"),
        "sampler_path": str(base_out / "sampler_result.json"),
        "pages_scanned": len(urls_to_scan),
        "report_type": report_type,
        "smart_sampling": True
    }
