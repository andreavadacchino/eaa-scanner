"""Base Agent class for specialized report generation agents"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AgentPriority(Enum):
    """Priorità di esecuzione degli agent"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class AgentStatus(Enum):
    """Stati possibili di un agent"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FALLBACK = "fallback"


@dataclass
class AgentContext:
    """Contesto condiviso tra gli agent"""
    scan_data: Dict[str, Any]
    company_info: Dict[str, Any]
    requirements: Dict[str, Any]
    shared_metrics: Dict[str, Any]
    generation_timestamp: datetime
    target_audience: str = "technical"  # technical, executive, compliance
    language: str = "it"
    format_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.format_preferences is None:
            self.format_preferences = {
                'style': 'professional',
                'detail_level': 'comprehensive',
                'include_technical': True
            }


@dataclass
class AgentResult:
    """Risultato prodotto da un agent"""
    agent_name: str
    section_content: str
    metadata: Dict[str, Any]
    quality_score: float
    status: AgentStatus
    execution_time: float
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class BaseAgent(ABC):
    """Classe base per tutti gli agent specializzati"""
    
    def __init__(self, 
                 name: str,
                 priority: AgentPriority = AgentPriority.NORMAL,
                 timeout: int = 30):
        self.name = name
        self.priority = priority
        self.timeout = timeout
        self.status = AgentStatus.IDLE
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self._execution_history: List[AgentResult] = []
    
    @abstractmethod
    async def generate_section(self, 
                              context: AgentContext) -> str:
        """Genera la sezione specifica del report
        
        Args:
            context: Contesto condiviso con dati e requisiti
            
        Returns:
            Contenuto HTML della sezione generata
        """
        pass
    
    @abstractmethod
    def validate_input(self, context: AgentContext) -> bool:
        """Valida che il contesto contenga i dati necessari
        
        Args:
            context: Contesto da validare
            
        Returns:
            True se il contesto è valido, False altrimenti
        """
        pass
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Esegue l'agent con gestione errori e timeout
        
        Args:
            context: Contesto di esecuzione
            
        Returns:
            Risultato dell'esecuzione con metadati
        """
        start_time = asyncio.get_event_loop().time()
        self.status = AgentStatus.PROCESSING
        errors = []
        warnings = []
        
        try:
            # Valida input
            if not self.validate_input(context):
                raise ValueError(f"Invalid context for agent {self.name}")
            
            # Esegui con timeout
            section_content = await asyncio.wait_for(
                self.generate_section(context),
                timeout=self.timeout
            )
            
            # Valida output
            quality_score = self._assess_quality(section_content, context)
            
            if quality_score < 0.5:
                warnings.append(f"Low quality score: {quality_score:.2f}")
            
            self.status = AgentStatus.COMPLETED
            
            result = AgentResult(
                agent_name=self.name,
                section_content=section_content,
                metadata=self._extract_metadata(section_content),
                quality_score=quality_score,
                status=self.status,
                execution_time=asyncio.get_event_loop().time() - start_time,
                errors=errors,
                warnings=warnings
            )
            
        except asyncio.TimeoutError:
            self.logger.error(f"Agent {self.name} timeout after {self.timeout}s")
            self.status = AgentStatus.FAILED
            errors.append(f"Timeout after {self.timeout} seconds")
            
            # Genera fallback
            section_content = await self._generate_fallback(context)
            
            result = AgentResult(
                agent_name=self.name,
                section_content=section_content,
                metadata={},
                quality_score=0.3,
                status=AgentStatus.FALLBACK,
                execution_time=asyncio.get_event_loop().time() - start_time,
                errors=errors,
                warnings=["Using fallback content"]
            )
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {str(e)}")
            self.status = AgentStatus.FAILED
            errors.append(str(e))
            
            # Genera fallback
            section_content = await self._generate_fallback(context)
            
            result = AgentResult(
                agent_name=self.name,
                section_content=section_content,
                metadata={},
                quality_score=0.2,
                status=AgentStatus.FAILED,
                execution_time=asyncio.get_event_loop().time() - start_time,
                errors=errors,
                warnings=["Agent failed, using minimal fallback"]
            )
        
        # Salva nella storia
        self._execution_history.append(result)
        
        return result
    
    def _assess_quality(self, content: str, context: AgentContext) -> float:
        """Valuta la qualità del contenuto generato
        
        Args:
            content: Contenuto da valutare
            context: Contesto per valutazione contestuale
            
        Returns:
            Score di qualità tra 0 e 1
        """
        if not content:
            return 0.0
        
        score = 1.0
        
        # Penalizza contenuto troppo corto
        if len(content) < 100:
            score -= 0.3
        
        # Penalizza mancanza di struttura HTML
        if '<h' not in content.lower():
            score -= 0.2
        
        # Penalizza mancanza di dati specifici
        if context.company_info.get('company_name') not in content:
            score -= 0.2
        
        # Bonus per contenuto strutturato
        if '<table>' in content:
            score += 0.1
        
        if '<ul>' in content or '<ol>' in content:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Estrae metadati dal contenuto generato
        
        Args:
            content: Contenuto da analizzare
            
        Returns:
            Dizionario con metadati estratti
        """
        metadata = {
            'content_length': len(content),
            'has_tables': '<table>' in content,
            'has_lists': '<ul>' in content or '<ol>' in content,
            'has_headings': '<h2>' in content or '<h3>' in content,
            'section_count': content.count('<section>'),
            'paragraph_count': content.count('<p>')
        }
        
        # Conta errori e warning menzionati
        metadata['error_mentions'] = content.lower().count('error') + content.lower().count('errore')
        metadata['warning_mentions'] = content.lower().count('warning') + content.lower().count('avviso')
        
        return metadata
    
    async def _generate_fallback(self, context: AgentContext) -> str:
        """Genera contenuto di fallback minimale
        
        Args:
            context: Contesto per generazione fallback
            
        Returns:
            Contenuto HTML di fallback
        """
        return f"""
        <section>
            <h2>{self.name.replace('_', ' ').title()}</h2>
            <p>Sezione temporaneamente non disponibile. 
            I dati sono in elaborazione.</p>
            <p><em>Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}</em></p>
        </section>
        """
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Ottiene statistiche di esecuzione dell'agent
        
        Returns:
            Dizionario con statistiche aggregate
        """
        if not self._execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_quality': 0.0,
                'avg_execution_time': 0.0
            }
        
        total = len(self._execution_history)
        successful = sum(1 for r in self._execution_history 
                        if r.status == AgentStatus.COMPLETED)
        
        avg_quality = sum(r.quality_score for r in self._execution_history) / total
        avg_time = sum(r.execution_time for r in self._execution_history) / total
        
        return {
            'total_executions': total,
            'success_rate': successful / total,
            'avg_quality': avg_quality,
            'avg_execution_time': avg_time,
            'failure_count': sum(1 for r in self._execution_history 
                                if r.status == AgentStatus.FAILED),
            'fallback_count': sum(1 for r in self._execution_history 
                                 if r.status == AgentStatus.FALLBACK)
        }