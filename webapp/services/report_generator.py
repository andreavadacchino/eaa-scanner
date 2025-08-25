"""
Report generator service for creating accessibility reports
Handles HTML, PDF, JSON, and Markdown generation with AI enhancement
"""

import os
import json
import asyncio
import aiofiles
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import markdown
import pdfkit

from ..models.scan import ReportGenerationRequest

class ReportGenerator:
    """Service for generating accessibility reports"""
    
    def __init__(self):
        self.output_path = Path(os.getenv("REPORT_OUTPUT_PATH", "./output/reports"))
        self.output_path.mkdir(exist_ok=True, parents=True)
        
        # Setup Jinja2 template environment
        template_path = Path(__file__).parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        self.reports_in_progress = {}
        
    async def generate_async(
        self,
        report_id: str,
        scan_data: Dict,
        request: ReportGenerationRequest,
        api_keys
    ):
        """
        Generate report asynchronously
        
        Args:
            report_id: Unique report identifier
            scan_data: Scan results data
            request: Report generation request
            api_keys: API key manager
        """
        try:
            self.reports_in_progress[report_id] = {
                "status": "processing",
                "progress": 0,
                "started_at": datetime.now().isoformat()
            }
            
            # Generate AI-enhanced content if API key provided
            enhanced_content = {}
            if request.api_key:
                enhanced_content = await self._generate_ai_content(
                    scan_data,
                    request,
                    api_keys
                )
                self.reports_in_progress[report_id]["progress"] = 50
            
            # Generate report in requested format
            if request.output_format == "html":
                output_path = await self._generate_html_report(
                    report_id,
                    scan_data,
                    enhanced_content,
                    request
                )
            elif request.output_format == "pdf":
                html_path = await self._generate_html_report(
                    report_id,
                    scan_data,
                    enhanced_content,
                    request
                )
                output_path = await self._convert_html_to_pdf(html_path)
            elif request.output_format == "json":
                output_path = await self._generate_json_report(
                    report_id,
                    scan_data,
                    enhanced_content
                )
            elif request.output_format == "markdown":
                output_path = await self._generate_markdown_report(
                    report_id,
                    scan_data,
                    enhanced_content,
                    request
                )
            else:
                raise ValueError(f"Unsupported format: {request.output_format}")
            
            self.reports_in_progress[report_id] = {
                "status": "completed",
                "progress": 100,
                "completed_at": datetime.now().isoformat(),
                "output_path": str(output_path)
            }
            
        except Exception as e:
            self.reports_in_progress[report_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
    
    async def _generate_ai_content(
        self,
        scan_data: Dict,
        request: ReportGenerationRequest,
        api_keys
    ) -> Dict:
        """Generate AI-enhanced content using OpenAI"""
        enhanced = {}
        
        # Prepare context for AI
        issues_summary = self._summarize_issues(scan_data.get("results", {}))
        
        # Generate content for each requested section
        for section in request.sections:
            if not section.enabled:
                continue
            
            prompt = self._create_section_prompt(
                section.name,
                issues_summary,
                section.language
            )
            
            content = await self._call_openai_api(
                prompt,
                request.model,
                request.api_key
            )
            
            enhanced[section.name] = content
        
        return enhanced
    
    async def _call_openai_api(
        self,
        prompt: str,
        model: str,
        api_key: str
    ) -> str:
        """Call OpenAI API for content generation"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Sei un esperto di accessibilità web e conformità EAA. Genera contenuti professionali e dettagliati in italiano."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            ) as response:
                if response.status != 200:
                    raise Exception(f"OpenAI API error: {response.status}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    def _create_section_prompt(
        self,
        section_name: str,
        issues_summary: Dict,
        language: str
    ) -> str:
        """Create prompt for AI section generation"""
        prompts = {
            "summary": f"""
                Genera un sommario esecutivo per un report di accessibilità web.
                Problemi trovati: {json.dumps(issues_summary, ensure_ascii=False)}
                Il sommario deve includere:
                1. Stato generale di conformità
                2. Principali criticità identificate
                3. Impatto sugli utenti
                4. Raccomandazioni prioritarie
                Lingua: {language}
            """,
            "recommendations": f"""
                Genera raccomandazioni dettagliate per risolvere i problemi di accessibilità.
                Problemi: {json.dumps(issues_summary, ensure_ascii=False)}
                Organizza per priorità (critica, alta, media, bassa).
                Includi tempistiche stimate e best practice.
                Lingua: {language}
            """,
            "technical_details": f"""
                Genera dettagli tecnici per sviluppatori sui problemi di accessibilità.
                Problemi: {json.dumps(issues_summary, ensure_ascii=False)}
                Includi esempi di codice corretto e riferimenti WCAG.
                Lingua: {language}
            """,
            "wcag_compliance": f"""
                Analizza la conformità WCAG 2.2 basata sui problemi trovati.
                Problemi: {json.dumps(issues_summary, ensure_ascii=False)}
                Dettaglia conformità per ogni principio WCAG.
                Lingua: {language}
            """,
            "remediation_plan": f"""
                Crea un piano di remediation dettagliato.
                Problemi: {json.dumps(issues_summary, ensure_ascii=False)}
                Includi fasi, responsabilità, tempistiche e costi stimati.
                Lingua: {language}
            """
        }
        
        return prompts.get(section_name, f"Genera contenuto per {section_name}")
    
    def _summarize_issues(self, results: Dict) -> Dict:
        """Summarize issues for AI context"""
        all_issues = results.get("all_issues", [])
        
        summary = {
            "total": len(all_issues),
            "by_severity": {},
            "by_wcag": {},
            "top_issues": []
        }
        
        # Count by severity
        for issue in all_issues:
            severity = issue.get("severity", "unknown")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            wcag = issue.get("wcag_criterion", "unknown")
            summary["by_wcag"][wcag] = summary["by_wcag"].get(wcag, 0) + 1
        
        # Get top 5 issues
        summary["top_issues"] = [
            {
                "message": issue.get("message"),
                "severity": issue.get("severity"),
                "wcag": issue.get("wcag_criterion")
            }
            for issue in all_issues[:5]
        ]
        
        return summary
    
    async def _generate_html_report(
        self,
        report_id: str,
        scan_data: Dict,
        enhanced_content: Dict,
        request: ReportGenerationRequest
    ) -> Path:
        """Generate HTML report"""
        template = self.jinja_env.get_template("report_template.html")
        
        # Prepare template context
        context = {
            "scan": scan_data,
            "results": scan_data.get("results", {}),
            "enhanced": enhanced_content,
            "generation_date": datetime.now().isoformat(),
            "report_id": report_id,
            "include_technical": request.include_technical_details,
            "include_costs": request.include_remediation_costs
        }
        
        # Render HTML
        html_content = template.render(**context)
        
        # Save to file
        output_file = self.output_path / f"{report_id}.html"
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(html_content)
        
        return output_file
    
    async def _convert_html_to_pdf(self, html_path: Path) -> Path:
        """Convert HTML report to PDF"""
        pdf_path = html_path.with_suffix('.pdf')
        
        # Try Chrome/Chromium first
        chrome_commands = [
            os.getenv("CHROME_CMD", ""),
            "google-chrome",
            "chromium",
            "chromium-browser"
        ]
        
        for cmd in filter(None, chrome_commands):
            try:
                process = await asyncio.create_subprocess_exec(
                    cmd,
                    "--headless",
                    "--disable-gpu",
                    "--print-to-pdf=" + str(pdf_path),
                    str(html_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                
                if pdf_path.exists():
                    return pdf_path
            except FileNotFoundError:
                continue
        
        # Fallback to wkhtmltopdf
        try:
            pdfkit.from_file(str(html_path), str(pdf_path))
            return pdf_path
        except Exception as e:
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    async def _generate_json_report(
        self,
        report_id: str,
        scan_data: Dict,
        enhanced_content: Dict
    ) -> Path:
        """Generate JSON report"""
        report_data = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "scan_data": scan_data,
            "enhanced_content": enhanced_content
        }
        
        output_file = self.output_path / f"{report_id}.json"
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(report_data, indent=2, ensure_ascii=False))
        
        return output_file
    
    async def _generate_markdown_report(
        self,
        report_id: str,
        scan_data: Dict,
        enhanced_content: Dict,
        request: ReportGenerationRequest
    ) -> Path:
        """Generate Markdown report"""
        md_content = f"""# Report Accessibilità - {scan_data.get('company_name')}

## Informazioni Scansione
- **URL**: {scan_data.get('url')}
- **Data**: {scan_data.get('scan_date')}
- **ID Report**: {report_id}

## Metriche di Conformità
"""
        
        metrics = scan_data.get("results", {}).get("metrics", {})
        md_content += f"""
- **Punteggio Conformità**: {metrics.get('compliance_score', 0):.1f}/100
- **Livello**: {metrics.get('compliance_level', 'unknown')}
- **Problemi Totali**: {metrics.get('total_issues', 0)}
  - Critici: {metrics.get('critical_issues', 0)}
  - Alti: {metrics.get('high_issues', 0)}
  - Medi: {metrics.get('medium_issues', 0)}
  - Bassi: {metrics.get('low_issues', 0)}
"""
        
        # Add enhanced sections
        for section_name, content in enhanced_content.items():
            section_title = section_name.replace('_', ' ').title()
            md_content += f"\n## {section_title}\n{content}\n"
        
        # Add issues table
        if request.include_technical_details:
            md_content += "\n## Dettagli Problemi\n\n"
            md_content += "| Severità | Codice | Messaggio | WCAG |\n"
            md_content += "|----------|--------|-----------|------|\n"
            
            for issue in scan_data.get("results", {}).get("all_issues", [])[:20]:
                md_content += f"| {issue.get('severity')} | {issue.get('code')} | {issue.get('message')[:50]}... | {issue.get('wcag_criterion')} |\n"
        
        output_file = self.output_path / f"{report_id}.md"
        async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        return output_file
    
    async def generate_basic_html(self, scan_data: Dict) -> str:
        """Generate basic HTML report without AI enhancement"""
        template = self.jinja_env.get_template("basic_report.html")
        
        context = {
            "scan": scan_data,
            "results": scan_data.get("results", {}),
            "generation_date": datetime.now().isoformat()
        }
        
        return template.render(**context)
    
    async def get_status(self, report_id: str) -> Optional[Dict]:
        """Get report generation status"""
        return self.reports_in_progress.get(report_id)
    
    async def get_report_path(self, report_id: str, format: str) -> Optional[Path]:
        """Get path to generated report file"""
        report_file = self.output_path / f"{report_id}.{format}"
        
        if report_file.exists():
            return report_file
        
        return None
    
    async def send_email(
        self,
        scan_data: Dict,
        recipient: str,
        include_pdf: bool
    ):
        """Send report via email"""
        # Implementation would use SMTP or email service
        # Placeholder for email functionality
        pass
    
    async def generate_remediation_plan(
        self,
        plan_id: str,
        scan_data: Dict,
        priority: str,
        timeline_days: int,
        api_key: Optional[str]
    ):
        """Generate AI-powered remediation plan"""
        # Implementation for remediation plan generation
        pass
    
    async def list_templates(self) -> List[Dict]:
        """List available report templates"""
        templates_dir = Path(__file__).parent.parent / "templates"
        templates = []
        
        for template_file in templates_dir.glob("*.html"):
            templates.append({
                "name": template_file.stem,
                "path": str(template_file),
                "type": "html"
            })
        
        return templates
    
    async def validate_template(self, template_content: str) -> bool:
        """Validate Jinja2 template"""
        try:
            self.jinja_env.from_string(template_content)
            return True
        except Exception:
            return False
    
    async def save_template(
        self,
        name: str,
        content: str,
        user_id: str
    ) -> str:
        """Save custom template"""
        template_id = f"custom_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        template_path = Path(__file__).parent.parent / "templates" / "custom" / f"{template_id}.html"
        
        template_path.parent.mkdir(exist_ok=True, parents=True)
        
        async with aiofiles.open(template_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        return template_id