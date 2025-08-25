"""Multi-Agent System for Enterprise Report Generation

Provides specialized agents for professional accessibility report generation.
Each agent handles a specific aspect of report creation with cross-validation.
"""

from .base_agent import BaseAgent, AgentContext, AgentResult
from .orchestrator import AIReportOrchestrator
from .executive_agent import ExecutiveSummaryAgent
from .technical_agent import TechnicalAnalysisAgent
from .compliance_agent import ComplianceAssessmentAgent
from .remediation_agent import RemediationPlannerAgent
from .recommendations_agent import RecommendationsAgent
from .quality_controller import QualityControlAgent
from .context_manager import ContextManager
from .prompt_manager import PromptManager
from .fallback_manager import IntelligentFallbackManager

__all__ = [
    'BaseAgent',
    'AgentContext', 
    'AgentResult',
    'AIReportOrchestrator',
    'ExecutiveSummaryAgent',
    'TechnicalAnalysisAgent',
    'ComplianceAssessmentAgent',
    'RemediationPlannerAgent',
    'RecommendationsAgent',
    'QualityControlAgent',
    'ContextManager',
    'PromptManager',
    'IntelligentFallbackManager'
]