"""AI Report Orchestrator - Coordina gli agent per generazione report enterprise"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from .base_agent import AgentContext, AgentResult, AgentStatus, AgentPriority
from .executive_agent import ExecutiveSummaryAgent
from .technical_agent import TechnicalAnalysisAgent
from .compliance_agent import ComplianceAssessmentAgent
from .remediation_agent import RemediationPlannerAgent
from .recommendations_agent import RecommendationsAgent
from .quality_controller import QualityControlAgent
from .context_manager import ContextManager
from .prompt_manager import PromptManager
from .fallback_manager import IntelligentFallbackManager

logger = logging.getLogger(__name__)


class AIReportOrchestrator:
    """Orchestratore principale per generazione report multi-agent"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)
        
        # Inizializza componenti core
        self.context_manager = ContextManager()
        self.prompt_manager = PromptManager()
        self.quality_controller = QualityControlAgent()
        self.fallback_manager = IntelligentFallbackManager()
        
        # Inizializza agent specializzati
        self.specialist_agents = self._initialize_agents()
        
        # Metriche di esecuzione
        self.execution_metrics = {
            'total_reports': 0,
            'successful_reports': 0,
            'failed_reports': 0,
            'avg_generation_time': 0.0,
            'avg_quality_score': 0.0
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configurazione di default"""
        return {
            'parallel_execution': True,
            'max_parallel_agents': 5,
            'quality_threshold': 0.7,
            'enable_caching': True,
            'cache_ttl': 3600,
            'fallback_strategy': 'intelligent',
            'cross_validation': True,
            'language': 'it',
            'report_style': 'professional'
        }
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Inizializza gli agent specializzati"""
        return {
            'executive': ExecutiveSummaryAgent(
                priority=AgentPriority.CRITICAL
            ),
            'technical': TechnicalAnalysisAgent(
                priority=AgentPriority.HIGH
            ),
            'compliance': ComplianceAssessmentAgent(
                priority=AgentPriority.HIGH
            ),
            'remediation': RemediationPlannerAgent(
                priority=AgentPriority.NORMAL
            ),
            'recommendations': RecommendationsAgent(
                priority=AgentPriority.NORMAL
            )
        }
    
    async def generate_report(self,
                             scan_data: Dict[str, Any],
                             company_info: Dict[str, Any],
                             requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Genera report completo utilizzando sistema multi-agent
        
        Args:
            scan_data: Dati della scansione di accessibilità
            company_info: Informazioni azienda (name, url, email, country)
            requirements: Requisiti specifici del report
            
        Returns:
            Dizionario con report HTML e metadati
        """
        start_time = datetime.now()
        self.logger.info(f"Starting report generation for {company_info.get('company_name')}")
        
        try:
            # 1. Prepara contesto condiviso
            context = await self.context_manager.prepare_context(
                scan_data, 
                company_info, 
                requirements or self._get_default_requirements()
            )
            
            # 2. Esegui agent in modalità parallela o sequenziale
            if self.config['parallel_execution']:
                agent_results = await self._execute_agents_parallel(context)
            else:
                agent_results = await self._execute_agents_sequential(context)
            
            # 3. Validazione e cross-referencing
            validated_results = await self.quality_controller.validate_and_cross_reference(
                agent_results, context
            )
            
            # 4. Gestisci fallimenti con fallback intelligenti
            enhanced_results = await self._handle_failures(validated_results, context)
            
            # 5. Componi report finale
            final_report = await self._compose_final_report(enhanced_results, context)
            
            # 6. Valuta qualità complessiva
            quality_score = await self.quality_controller.assess_overall_quality(
                final_report, context
            )
            
            # 7. Aggiorna metriche
            self._update_metrics(True, datetime.now() - start_time, quality_score)
            
            self.logger.info(f"Report generated successfully with quality score: {quality_score:.2f}")
            
            return {
                'status': 'success',
                'html_report': final_report,
                'quality_score': quality_score,
                'generation_time': (datetime.now() - start_time).total_seconds(),
                'agent_metrics': self._get_agent_metrics(agent_results),
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'company': company_info.get('company_name'),
                    'url': company_info.get('url'),
                    'orchestrator_version': '2.0.0'
                }
            }
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            self._update_metrics(False, datetime.now() - start_time, 0.0)
            
            # Genera report di fallback completo
            fallback_report = await self.fallback_manager.generate_complete_fallback(
                scan_data, company_info, str(e)
            )
            
            return {
                'status': 'fallback',
                'html_report': fallback_report,
                'quality_score': 0.3,
                'generation_time': (datetime.now() - start_time).total_seconds(),
                'error': str(e),
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'company': company_info.get('company_name'),
                    'fallback_reason': 'orchestrator_failure'
                }
            }
    
    async def _execute_agents_parallel(self, context: AgentContext) -> List[AgentResult]:
        """Esegue gli agent in parallelo con controllo concorrenza"""
        # Ordina agent per priorità
        sorted_agents = sorted(
            self.specialist_agents.items(),
            key=lambda x: x[1].priority.value
        )
        
        # Crea task per esecuzione parallela
        tasks = []
        for agent_name, agent in sorted_agents:
            task = asyncio.create_task(
                agent.execute(context),
                name=agent_name
            )
            tasks.append(task)
        
        # Esegui con limite di concorrenza
        semaphore = asyncio.Semaphore(self.config['max_parallel_agents'])
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Gestisci eccezioni
        agent_results = []
        for i, result in enumerate(results):
            agent_name = sorted_agents[i][0]
            if isinstance(result, Exception):
                self.logger.error(f"Agent {agent_name} failed with exception: {result}")
                # Crea risultato di fallimento
                agent_results.append(AgentResult(
                    agent_name=agent_name,
                    section_content="",
                    metadata={},
                    quality_score=0.0,
                    status=AgentStatus.FAILED,
                    execution_time=0.0,
                    errors=[str(result)]
                ))
            else:
                agent_results.append(result)
        
        return agent_results
    
    async def _execute_agents_sequential(self, context: AgentContext) -> List[AgentResult]:
        """Esegue gli agent in sequenza basandosi sulla priorità"""
        results = []
        
        # Ordina per priorità
        sorted_agents = sorted(
            self.specialist_agents.items(),
            key=lambda x: x[1].priority.value
        )
        
        for agent_name, agent in sorted_agents:
            try:
                result = await agent.execute(context)
                results.append(result)
                
                # Aggiorna contesto con risultati intermedi per agent successivi
                context.shared_metrics[agent_name] = result.metadata
                
            except Exception as e:
                self.logger.error(f"Agent {agent_name} failed: {e}")
                results.append(AgentResult(
                    agent_name=agent_name,
                    section_content="",
                    metadata={},
                    quality_score=0.0,
                    status=AgentStatus.FAILED,
                    execution_time=0.0,
                    errors=[str(e)]
                ))
        
        return results
    
    async def _handle_failures(self, 
                              results: List[AgentResult], 
                              context: AgentContext) -> List[AgentResult]:
        """Gestisce fallimenti con fallback intelligenti"""
        enhanced_results = []
        
        for result in results:
            if result.status == AgentStatus.FAILED or result.quality_score < self.config['quality_threshold']:
                self.logger.warning(f"Handling failure for agent {result.agent_name}")
                
                # Genera fallback intelligente
                fallback_content = await self.fallback_manager.generate_intelligent_fallback(
                    result.agent_name,
                    context,
                    result
                )
                
                # Crea nuovo risultato con fallback
                enhanced_result = AgentResult(
                    agent_name=result.agent_name,
                    section_content=fallback_content,
                    metadata=result.metadata,
                    quality_score=max(0.5, result.quality_score),
                    status=AgentStatus.FALLBACK,
                    execution_time=result.execution_time,
                    errors=result.errors,
                    warnings=result.warnings + ["Using intelligent fallback"]
                )
                enhanced_results.append(enhanced_result)
            else:
                enhanced_results.append(result)
        
        return enhanced_results
    
    async def _compose_final_report(self, 
                                   results: List[AgentResult],
                                   context: AgentContext) -> str:
        """Compone il report finale dalle sezioni generate"""
        
        # Ordina risultati per presentazione logica
        section_order = [
            'executive',
            'compliance', 
            'technical',
            'remediation',
            'recommendations'
        ]
        
        # Mappa risultati per nome agent
        results_map = {r.agent_name: r for r in results}
        
        # Componi sezioni in ordine
        sections = []
        
        # Header
        sections.append(self._generate_report_header(context))
        
        # Sezioni principali
        for section_name in section_order:
            if section_name in results_map:
                result = results_map[section_name]
                if result.section_content:
                    sections.append(result.section_content)
        
        # Footer
        sections.append(self._generate_report_footer(context))
        
        # Unisci tutto
        return '\n'.join(sections)
    
    def _generate_report_header(self, context: AgentContext) -> str:
        """Genera header del report"""
        company_name = context.company_info.get('company_name', 'N/A')
        url = context.company_info.get('url', 'N/A')
        date = context.generation_timestamp.strftime('%d/%m/%Y')
        
        return f"""
        <header class="report-header">
            <h1>Report di Conformità Accessibilità Enterprise</h1>
            <div class="header-info">
                <p><strong>Azienda:</strong> {company_name}</p>
                <p><strong>Sito Web:</strong> {url}</p>
                <p><strong>Data Analisi:</strong> {date}</p>
                <p><strong>Standard:</strong> WCAG 2.1 AA, EN 301 549, EAA</p>
            </div>
        </header>
        """
    
    def _generate_report_footer(self, context: AgentContext) -> str:
        """Genera footer del report"""
        return f"""
        <footer class="report-footer">
            <section>
                <h2>Note Finali</h2>
                <p>Questo report è stato generato automaticamente utilizzando un sistema 
                multi-agent avanzato che analizza molteplici aspetti dell'accessibilità web.</p>
                
                <p><strong>Disclaimer:</strong> La valutazione automatizzata copre circa il 30-40% 
                dei criteri WCAG. Si raccomanda una verifica manuale completa con test di 
                usabilità e tecnologie assistive.</p>
                
                <p>Per assistenza nell'implementazione delle correzioni o per una valutazione 
                manuale completa, contattare: {context.company_info.get('email', 'N/A')}</p>
            </section>
            
            <div class="generation-info">
                <p><small>Report generato il {context.generation_timestamp.strftime('%d/%m/%Y alle %H:%M')}</small></p>
                <p><small>Versione Orchestrator: 2.0.0 | Quality Score: [QS]</small></p>
            </div>
        </footer>
        """
    
    def _get_default_requirements(self) -> Dict[str, Any]:
        """Requisiti di default per il report"""
        return {
            'target_audience': 'mixed',  # executive, technical, mixed
            'detail_level': 'comprehensive',
            'include_technical_details': True,
            'include_remediation_plan': True,
            'include_cost_estimates': False,
            'language': 'it',
            'format': 'html',
            'style': 'professional'
        }
    
    def _get_agent_metrics(self, results: List[AgentResult]) -> Dict[str, Any]:
        """Estrae metriche di esecuzione degli agent"""
        return {
            'total_agents': len(results),
            'successful': sum(1 for r in results if r.status == AgentStatus.COMPLETED),
            'failed': sum(1 for r in results if r.status == AgentStatus.FAILED),
            'fallback': sum(1 for r in results if r.status == AgentStatus.FALLBACK),
            'avg_quality': sum(r.quality_score for r in results) / len(results) if results else 0,
            'total_execution_time': sum(r.execution_time for r in results),
            'agent_details': [
                {
                    'name': r.agent_name,
                    'status': r.status.value,
                    'quality': r.quality_score,
                    'time': r.execution_time,
                    'errors': len(r.errors),
                    'warnings': len(r.warnings)
                }
                for r in results
            ]
        }
    
    def _update_metrics(self, success: bool, duration, quality_score: float):
        """Aggiorna metriche di esecuzione"""
        self.execution_metrics['total_reports'] += 1
        
        if success:
            self.execution_metrics['successful_reports'] += 1
        else:
            self.execution_metrics['failed_reports'] += 1
        
        # Aggiorna medie
        total = self.execution_metrics['total_reports']
        prev_avg_time = self.execution_metrics['avg_generation_time']
        prev_avg_quality = self.execution_metrics['avg_quality_score']
        
        self.execution_metrics['avg_generation_time'] = \
            (prev_avg_time * (total - 1) + duration.total_seconds()) / total
        
        if success:
            successful = self.execution_metrics['successful_reports']
            self.execution_metrics['avg_quality_score'] = \
                (prev_avg_quality * (successful - 1) + quality_score) / successful
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche dell'orchestratore"""
        stats = self.execution_metrics.copy()
        
        # Aggiungi statistiche per agent
        stats['agent_stats'] = {}
        for name, agent in self.specialist_agents.items():
            stats['agent_stats'][name] = agent.get_execution_stats()
        
        return stats