#!/usr/bin/env python3
"""
EAA Scanner - CLI per scansioni batch di accessibilità
"""
import sys
from pathlib import Path
import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import logging

# Aggiungi path parent per import
sys.path.append(str(Path(__file__).parent.parent))

from eaa_scanner.config import Config
from eaa_scanner.core import run_scan
from src.utils.io import read_input_file, validate_url
from eaa_scanner.notifiers.telegram import send_telegram_notification, format_telegram_message

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="EAA Accessibility Scanner - Audit multi-scanner per WCAG 2.1/2.2 AA")
console = Console()


@app.command()
def scan(
    url: Optional[str] = typer.Option(None, "--url", help="URL singolo da scansionare"),
    input_file: Optional[Path] = typer.Option(None, "--input", help="File con lista URL (txt/csv/json)"),
    company_name: str = typer.Option("", "--company", help="Nome azienda"),
    email: str = typer.Option("", "--email", help="Email di contatto"),
    out_dir: Path = typer.Option("output", "--out-dir", help="Directory output"),
    wave_api_key: Optional[str] = typer.Option(None, "--wave-key", envvar="WAVE_API_KEY", help="WAVE API key"),
    simulate: bool = typer.Option(True, "--simulate/--real", help="Modalità simulata (offline) o reale"),
    send_email: Optional[str] = typer.Option(None, "--email-to", help="Invia report via email"),
    send_telegram: bool = typer.Option(False, "--telegram", help="Invia notifica Telegram"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Output dettagliato"),
):
    """
    Esegue scansione di accessibilità su uno o più URL
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validazione input
    if not url and not input_file:
        console.print("[red]Errore: Specificare --url o --input[/red]")
        raise typer.Exit(1)
    
    # Prepara lista URL
    urls_to_scan = []
    
    if url:
        if not validate_url(url):
            console.print(f"[red]URL non valido: {url}[/red]")
            raise typer.Exit(1)
        urls_to_scan.append({
            'url': url,
            'company_name': company_name,
            'email': email
        })
    
    if input_file:
        try:
            file_urls = read_input_file(input_file)
            # Override con valori CLI se forniti
            for item in file_urls:
                if company_name:
                    item['company_name'] = company_name
                if email:
                    item['email'] = email
            urls_to_scan.extend(file_urls)
        except Exception as e:
            console.print(f"[red]Errore lettura file: {e}[/red]")
            raise typer.Exit(1)
    
    if not urls_to_scan:
        console.print("[yellow]Nessun URL valido trovato[/yellow]")
        raise typer.Exit(0)
    
    console.print(f"[green]Scansione di {len(urls_to_scan)} URL...[/green]")
    
    # Tabella risultati
    results_table = Table(title="Risultati Scansione Accessibilità")
    results_table.add_column("URL", style="cyan")
    results_table.add_column("Azienda", style="white")
    results_table.add_column("Score", style="green")
    results_table.add_column("Conformità", style="yellow")
    results_table.add_column("Report", style="blue")
    
    successful_scans = []
    failed_scans = []
    
    # Esegui scansioni
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        for idx, scan_item in enumerate(urls_to_scan, 1):
            task_desc = f"[{idx}/{len(urls_to_scan)}] Scansione {scan_item['url']}"
            task = progress.add_task(task_desc, total=1)
            
            try:
                # Configura scansione
                config_args = {
                    'url': scan_item['url'],
                    'company_name': scan_item.get('company_name', ''),
                    'email': scan_item.get('email', ''),
                    'simulate': simulate,
                    'wave_api_key': wave_api_key or '',
                }
                
                cfg = Config.from_env_or_args(config_args)
                
                # Esegui scansione
                result = run_scan(cfg, output_root=out_dir)
                
                # Estrai dati per tabella
                aggregated = result['aggregated']
                compliance = aggregated.get('compliance', {})
                score = compliance.get('overall_score', 0)
                level = compliance.get('compliance_level', 'non_conforme')
                report_path = Path(result['report_html_path'])
                
                results_table.add_row(
                    scan_item['url'],
                    scan_item.get('company_name', '-'),
                    f"{score}/100",
                    level.replace('_', ' ').title(),
                    report_path.name
                )
                
                successful_scans.append({
                    'scan_item': scan_item,
                    'result': result,
                    'aggregated': aggregated
                })
                
                # Notifiche
                if send_email and scan_item.get('email'):
                    # TODO: Implementare invio email con PDF
                    logger.info(f"Email da inviare a {scan_item['email']}")
                
                if send_telegram:
                    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                    chat_id = os.getenv('TELEGRAM_CHAT_ID')
                    if bot_token and chat_id:
                        message = format_telegram_message(aggregated)
                        send_telegram_notification(message, bot_token, chat_id)
                
            except Exception as e:
                logger.error(f"Errore scansione {scan_item['url']}: {e}")
                failed_scans.append({
                    'scan_item': scan_item,
                    'error': str(e)
                })
                results_table.add_row(
                    scan_item['url'],
                    scan_item.get('company_name', '-'),
                    "ERRORE",
                    "-",
                    "-"
                )
            
            progress.update(task, completed=1)
    
    # Mostra risultati
    console.print("\n")
    console.print(results_table)
    
    # Riepilogo
    console.print("\n[bold]Riepilogo:[/bold]")
    console.print(f"✅ Scansioni completate: {len(successful_scans)}")
    if failed_scans:
        console.print(f"❌ Scansioni fallite: {len(failed_scans)}")
        for fail in failed_scans:
            console.print(f"   - {fail['scan_item']['url']}: {fail['error']}")
    
    # Score medio
    if successful_scans:
        avg_score = sum(s['aggregated']['compliance']['overall_score'] for s in successful_scans) / len(successful_scans)
        console.print(f"📊 Score medio: {avg_score:.1f}/100")
    
    console.print(f"\n[green]Report salvati in: {out_dir}/[/green]")


@app.command()
def version():
    """Mostra versione del programma"""
    console.print("[bold]EAA Accessibility Scanner[/bold]")
    console.print("Versione: 1.0.0")
    console.print("Python: 3.11+")
    console.print("WCAG: 2.1/2.2 AA")


if __name__ == "__main__":
    import os
    # Carica .env se presente
    from dotenv import load_dotenv
    load_dotenv()
    
    app()