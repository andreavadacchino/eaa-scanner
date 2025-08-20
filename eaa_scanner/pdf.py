from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def html_to_pdf(html_path: Path, pdf_path: Path, engine: str = "auto", **kwargs) -> bool:
    """Converte HTML in PDF usando vari engine con fallback chain.
    
    Args:
        html_path: Path al file HTML
        pdf_path: Path di output PDF
        engine: Engine da usare ('weasyprint', 'chrome', 'wkhtmltopdf', 'auto')
        **kwargs: Opzioni aggiuntive per l'engine
    
    Returns:
        bool: True se conversione riuscita
    """
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Determina engine da usare
    engines_to_try = _determine_engines(engine)
    
    for engine_name in engines_to_try:
        logger.debug(f"Tentativo conversione PDF con {engine_name}")
        
        success = False
        if engine_name == "weasyprint":
            success = _try_weasyprint(html_path, pdf_path, **kwargs)
        elif engine_name == "chrome":
            success = _try_chrome(html_path, pdf_path, **kwargs)
        elif engine_name == "wkhtmltopdf":
            success = _try_wkhtmltopdf(html_path, pdf_path, **kwargs)
            
        if success:
            logger.info(f"PDF generato con successo usando {engine_name}: {pdf_path}")
            return True
        else:
            logger.debug(f"Engine {engine_name} fallito o non disponibile")
    
    logger.error(f"Fallita generazione PDF: nessun engine disponibile")
    return False


def _determine_engines(engine: str) -> list[str]:
    """Determina ordine di prova degli engine PDF"""
    if engine == "weasyprint":
        return ["weasyprint"]
    elif engine == "chrome":
        return ["chrome"]
    elif engine == "wkhtmltopdf":
        return ["wkhtmltopdf"]
    else:  # auto
        return ["weasyprint", "chrome", "wkhtmltopdf"]


def _try_weasyprint(html_path: Path, pdf_path: Path, **kwargs) -> bool:
    """Prova conversione con WeasyPrint"""
    try:
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        
        # Configurazione font per supporto caratteri internazionali
        font_config = FontConfiguration()
        
        # CSS aggiuntivo per stampa se fornito
        css_extra = kwargs.get('css_extra')
        stylesheets = []
        if css_extra:
            if isinstance(css_extra, str):
                stylesheets.append(CSS(string=css_extra, font_config=font_config))
            elif isinstance(css_extra, Path) and css_extra.exists():
                stylesheets.append(CSS(filename=str(css_extra), font_config=font_config))
        
        # Aggiunge CSS print-friendly di default
        default_print_css = _get_default_print_css()
        stylesheets.append(CSS(string=default_print_css, font_config=font_config))
        
        # Configurazione PDF
        html_doc = HTML(filename=str(html_path))
        
        # Opzioni WeasyPrint
        pdf_options = {
            'stylesheets': stylesheets,
            'font_config': font_config,
            'presentational_hints': True,
            'optimize_size': ('fonts', 'images'),
        }
        
        # Override con opzioni utente
        pdf_options.update(kwargs.get('weasyprint_options', {}))
        
        # Genera PDF
        html_doc.write_pdf(str(pdf_path), **pdf_options)
        
        # Verifica file generato
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True
            
    except ImportError:
        logger.debug("WeasyPrint non installato")
    except Exception as e:
        logger.debug(f"Errore WeasyPrint: {e}")
    
    return False


def _try_chrome(html_path: Path, pdf_path: Path, **kwargs) -> bool:
    """Prova conversione con Chrome/Chromium headless"""
    chrome_cmd = os.getenv("CHROME_CMD")
    chrome_candidates = []
    if chrome_cmd:
        chrome_candidates.append(chrome_cmd)
    chrome_candidates += [
        "google-chrome", "chrome", "chromium", "chromium-browser", "brave"
    ]

    for bin_name in chrome_candidates:
        bin_path = shutil.which(bin_name)
        if not bin_path:
            continue
        try:
            # Parametri Chrome di base
            cmd = [
                bin_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                f"--print-to-pdf={str(pdf_path)}",
                f"file://{str(html_path)}",
            ]
            
            # Opzioni aggiuntive per Chrome
            chrome_opts = kwargs.get('chrome_options', {})
            
            # Formato pagina
            if 'page_format' in chrome_opts:
                cmd.append(f"--print-to-pdf-no-header")
            
            # Margini
            if 'margins' in chrome_opts:
                margins = chrome_opts['margins']
                if isinstance(margins, dict):
                    # Margini personalizzati (unità: pollici)
                    cmd.extend([
                        f"--print-to-pdf-margin-top={margins.get('top', 1)}",
                        f"--print-to-pdf-margin-bottom={margins.get('bottom', 1)}",
                        f"--print-to-pdf-margin-left={margins.get('left', 1)}",
                        f"--print-to-pdf-margin-right={margins.get('right', 1)}",
                    ])
            
            timeout = kwargs.get('timeout', 120)
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            if cp.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
                return True
                
        except Exception as e:
            logger.debug(f"Errore Chrome {bin_name}: {e}")
            continue
    
    return False


def _try_wkhtmltopdf(html_path: Path, pdf_path: Path, **kwargs) -> bool:
    """Prova conversione con wkhtmltopdf"""
    wkhtml = shutil.which("wkhtmltopdf")
    if not wkhtml:
        return False
        
    try:
        # Parametri base wkhtmltopdf
        cmd = [
            wkhtml,
            "--page-size", "A4",
            "--margin-top", "0.75in",
            "--margin-right", "0.75in",
            "--margin-bottom", "0.75in",
            "--margin-left", "0.75in",
            "--encoding", "utf-8",
            "--print-media-type",
        ]
        
        # Opzioni aggiuntive wkhtmltopdf
        wkhtml_opts = kwargs.get('wkhtmltopdf_options', {})
        
        # Formato pagina personalizzato
        if 'page_size' in wkhtml_opts:
            cmd[cmd.index("A4")] = wkhtml_opts['page_size']
        
        # Qualità
        if wkhtml_opts.get('low_quality', False):
            cmd.append("--lowquality")
        
        # Disabilita JavaScript se richiesto
        if wkhtml_opts.get('disable_javascript', True):
            cmd.append("--disable-javascript")
        
        cmd.extend([str(html_path), str(pdf_path)])
        
        timeout = kwargs.get('timeout', 120)
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if cp.returncode == 0 and pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True
            
    except Exception as e:
        logger.debug(f"Errore wkhtmltopdf: {e}")
    
    return False


def _get_default_print_css() -> str:
    """CSS ottimizzato per stampa PDF con WeasyPrint"""
    return """
    @page {
        size: A4;
        margin: 2cm 1.5cm;
        @top-center {
            content: "Report Accessibilità EAA";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Pagina " counter(page) " di " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
    
    /* Reset e base */
    * {
        box-sizing: border-box;
    }
    
    body {
        font-family: "Arial", "Helvetica", sans-serif;
        font-size: 11pt;
        line-height: 1.4;
        color: #222;
        background: white;
        margin: 0;
        padding: 0;
    }
    
    .container {
        max-width: none;
        margin: 0;
        padding: 0;
    }
    
    /* Header ottimizzato per stampa */
    .header {
        background: #2c3e50 !important;
        color: white !important;
        padding: 20pt;
        margin-bottom: 15pt;
        border-radius: 6pt;
        page-break-inside: avoid;
    }
    
    .header h1 {
        font-size: 18pt;
        margin: 0 0 8pt 0;
        font-weight: bold;
    }
    
    .header .company {
        font-size: 14pt;
        font-weight: 500;
        margin-bottom: 8pt;
    }
    
    .metadata {
        font-size: 10pt;
        opacity: 0.9;
    }
    
    .metadata span {
        margin-right: 15pt;
        display: inline-block;
    }
    
    /* Score cards ottimizzate */
    .score-section {
        display: flex;
        flex-wrap: wrap;
        gap: 10pt;
        margin: 15pt 0;
        page-break-inside: avoid;
    }
    
    .score-card {
        flex: 1;
        min-width: 120pt;
        background: #f8f9fa;
        border: 1pt solid #dee2e6;
        border-radius: 4pt;
        padding: 12pt;
        text-align: center;
    }
    
    .score-card h3 {
        margin: 0 0 6pt 0;
        font-size: 9pt;
        color: #666;
        text-transform: uppercase;
        font-weight: 600;
    }
    
    .score-card .value {
        font-size: 20pt;
        font-weight: bold;
        color: #2c3e50;
        margin: 0;
    }
    
    /* Sezioni */
    .section {
        background: white;
        border: 1pt solid #e9ecef;
        border-radius: 4pt;
        padding: 15pt;
        margin-bottom: 15pt;
        page-break-inside: avoid;
    }
    
    .section h2 {
        font-size: 14pt;
        margin: 0 0 12pt 0;
        color: #2c3e50;
        font-weight: 600;
        border-bottom: 1pt solid #e9ecef;
        padding-bottom: 6pt;
    }
    
    /* Compliance badges */
    .compliance-badge {
        display: inline-block;
        padding: 6pt 10pt;
        border-radius: 12pt;
        font-weight: bold;
        font-size: 9pt;
        text-transform: uppercase;
    }
    
    .compliance-badge.conforme {
        background: #d4edda;
        color: #155724;
        border: 1pt solid #c3e6cb;
    }
    
    .compliance-badge.parzialmente_conforme {
        background: #fff3cd;
        color: #856404;
        border: 1pt solid #ffeaa7;
    }
    
    .compliance-badge.non_conforme {
        background: #f8d7da;
        color: #721c24;
        border: 1pt solid #f5c6cb;
    }
    
    /* Issues styling */
    .issues-section {
        border: 1pt solid #e9ecef;
        border-radius: 4pt;
        padding: 15pt;
        margin-bottom: 15pt;
        background: white;
    }
    
    .issue-item {
        border: 1pt solid #e9ecef;
        border-radius: 4pt;
        margin-bottom: 10pt;
        page-break-inside: avoid;
        break-inside: avoid;
    }
    
    .issue-header {
        background: #f8f9fa;
        padding: 8pt 12pt;
        border-bottom: 1pt solid #e9ecef;
        font-weight: 600;
        font-size: 10pt;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .issue-item.high .issue-header {
        background: #f8d7da;
        color: #721c24;
        border-bottom-color: #f5c6cb;
    }
    
    .issue-item.medium .issue-header {
        background: #fff3cd;
        color: #856404;
        border-bottom-color: #ffeaa7;
    }
    
    .issue-item.low .issue-header {
        background: #d1ecf1;
        color: #0c5460;
        border-bottom-color: #bee5eb;
    }
    
    .issue-content {
        padding: 10pt 12pt;
        font-size: 10pt;
        line-height: 1.3;
    }
    
    .issue-meta {
        font-size: 9pt;
        color: #666;
        margin-top: 6pt;
        padding-top: 6pt;
        border-top: 1pt solid #e9ecef;
    }
    
    .issue-meta span {
        margin-right: 12pt;
        display: inline-block;
    }
    
    /* Raccomandazioni */
    .recommendation-item {
        border: 1pt solid #e9ecef;
        border-radius: 4pt;
        margin-bottom: 12pt;
        padding: 12pt;
        page-break-inside: avoid;
    }
    
    .recommendation-item.priority-alta {
        border-left: 3pt solid #dc3545;
        background: #fff5f5;
    }
    
    .recommendation-item.priority-media {
        border-left: 3pt solid #ffc107;
        background: #fffef5;
    }
    
    .recommendation-item.priority-bassa {
        border-left: 3pt solid #28a745;
        background: #f8fff8;
    }
    
    .rec-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8pt;
    }
    
    .rec-header h3 {
        font-size: 12pt;
        margin: 0;
        color: #2c3e50;
        font-weight: 600;
        flex: 1;
    }
    
    .rec-badges {
        display: flex;
        gap: 6pt;
        flex-shrink: 0;
        margin-left: 12pt;
    }
    
    .priority-badge, .effort-badge {
        padding: 3pt 8pt;
        border-radius: 10pt;
        font-size: 8pt;
        font-weight: bold;
        text-transform: uppercase;
        border: 1pt solid transparent;
    }
    
    .priority-badge.alta {
        background: #f8d7da;
        color: #721c24;
        border-color: #f5c6cb;
    }
    
    .priority-badge.media {
        background: #fff3cd;
        color: #856404;
        border-color: #ffeaa7;
    }
    
    .priority-badge.bassa {
        background: #d4edda;
        color: #155724;
        border-color: #c3e6cb;
    }
    
    .effort-badge {
        background: #d1ecf1;
        color: #0c5460;
        border-color: #bee5eb;
    }
    
    .rec-description {
        font-size: 10pt;
        margin: 8pt 0;
        line-height: 1.3;
    }
    
    .wcag-ref {
        font-size: 9pt;
        color: #666;
        margin-top: 8pt;
        font-weight: 500;
    }
    
    /* Piano remediation */
    .remediation-plan .phase-item {
        border: 1pt solid #e9ecef;
        border-radius: 4pt;
        margin-bottom: 12pt;
        padding: 12pt;
        border-left: 3pt solid #6c757d;
        background: #f8f9fa;
        page-break-inside: avoid;
    }
    
    .phase-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8pt;
    }
    
    .phase-header h4 {
        font-size: 11pt;
        margin: 0;
        font-weight: 600;
        color: #2c3e50;
    }
    
    .phase-duration {
        background: white;
        padding: 3pt 8pt;
        border-radius: 10pt;
        font-size: 9pt;
        border: 1pt solid #dee2e6;
        color: #495057;
    }
    
    .phase-priority {
        font-size: 9pt;
        padding: 3pt 8pt;
        border-radius: 10pt;
        margin: 6pt 0;
        display: inline-block;
    }
    
    .phase-priority.priority-critica {
        background: #f8d7da;
        color: #721c24;
    }
    
    .phase-priority.priority-alta {
        background: #fff3cd;
        color: #856404;
    }
    
    .phase-priority.priority-media {
        background: #fff3cd;
        color: #856404;
    }
    
    .phase-objectives {
        font-size: 10pt;
        margin: 8pt 0;
        line-height: 1.3;
    }
    
    /* Liste */
    ul, ol {
        margin: 6pt 0;
        padding-left: 15pt;
    }
    
    li {
        margin-bottom: 3pt;
        font-size: 10pt;
        line-height: 1.3;
    }
    
    /* Executive summary */
    .executive-summary {
        background: #e7f3ff;
        border: 1pt solid #b3d9ff;
        border-radius: 4pt;
        padding: 12pt;
        margin: 12pt 0;
        font-size: 10pt;
        line-height: 1.4;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        font-size: 9pt;
        color: #666;
        margin-top: 20pt;
        padding: 12pt 0;
        border-top: 1pt solid #e9ecef;
    }
    
    /* Utilità di stampa */
    .page-break {
        page-break-before: always;
    }
    
    .no-break {
        page-break-inside: avoid;
        break-inside: avoid;
    }
    
    /* LLM notes */
    .llm-note {
        background: #e8f5e8;
        color: #2e7d32;
        padding: 6pt 10pt;
        border-radius: 4pt;
        font-size: 9pt;
        margin-top: 8pt;
        text-align: center;
        border: 1pt solid #c8e6c9;
    }
    
    /* Nasconde elementi non necessari per stampa */
    @media print {
        .no-print {
            display: none;
        }
        
        /* Forza colori per stampa */
        body {
            -webkit-print-color-adjust: exact;
            color-adjust: exact;
        }
    }
    """


def get_pdf_engines_status() -> Dict[str, Dict[str, Any]]:
    """Ritorna lo status degli engine PDF disponibili"""
    status = {}
    
    # WeasyPrint
    try:
        import weasyprint
        status['weasyprint'] = {
            'available': True,
            'version': weasyprint.__version__,
            'description': 'Engine PDF nativo Python con supporto CSS avanzato'
        }
    except ImportError:
        status['weasyprint'] = {
            'available': False,
            'version': None,
            'description': 'Non installato (pip install weasyprint)',
            'install_cmd': 'pip install weasyprint'
        }
    
    # Chrome/Chromium
    chrome_found = False
    chrome_path = None
    for cmd in ["google-chrome", "chrome", "chromium", "chromium-browser", "brave"]:
        path = shutil.which(cmd)
        if path:
            chrome_found = True
            chrome_path = path
            break
    
    status['chrome'] = {
        'available': chrome_found,
        'path': chrome_path,
        'description': 'Engine basato su Chromium con supporto JavaScript'
    }
    
    # wkhtmltopdf
    wkhtml_path = shutil.which("wkhtmltopdf")
    status['wkhtmltopdf'] = {
        'available': bool(wkhtml_path),
        'path': wkhtml_path,
        'description': 'Engine tradizionale con supporto CSS limitato'
    }
    
    return status


def create_pdf_with_options(html_path: Path, pdf_path: Path, 
                           engine: str = "auto",
                           page_format: str = "A4",
                           margins: Dict[str, float] = None,
                           css_extra: Optional[str] = None,
                           timeout: int = 120) -> bool:
    """Interfaccia avanzata per generazione PDF con opzioni"""
    
    if margins is None:
        margins = {'top': 1, 'bottom': 1, 'left': 0.75, 'right': 0.75}  # pollici
    
    # Opzioni specifiche per engine
    options = {
        'css_extra': css_extra,
        'timeout': timeout,
        'chrome_options': {
            'page_format': page_format,
            'margins': margins
        },
        'wkhtmltopdf_options': {
            'page_size': page_format,
            'disable_javascript': True
        },
        'weasyprint_options': {
            'optimize_size': ('fonts', 'images')
        }
    }
    
    return html_to_pdf(html_path, pdf_path, engine=engine, **options)