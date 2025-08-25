"""Prompt Manager - Gestione centralizzata prompt e template"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptManager:
    """Manager centralizzato per prompt e template"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        """Carica template prompt"""
        
        # In produzione questi andrebbero in file separati
        return {
            'executive': self._get_executive_prompt_template(),
            'technical': self._get_technical_prompt_template(),
            'compliance': self._get_compliance_prompt_template(),
            'remediation': self._get_remediation_prompt_template(),
            'recommendations': self._get_recommendations_prompt_template()
        }
    
    def get_prompt(self, 
                   agent_type: str,
                   context: Dict[str, Any],
                   requirements: Dict[str, Any]) -> str:
        """Genera prompt personalizzato per agent
        
        Args:
            agent_type: Tipo di agent
            context: Contesto con dati
            requirements: Requisiti specifici
            
        Returns:
            Prompt personalizzato
        """
        
        template = self.templates.get(agent_type, '')
        
        if not template:
            self.logger.warning(f"No template found for agent type: {agent_type}")
            return self._get_default_prompt()
        
        # Personalizza template con contesto
        prompt = template.format(
            company_name=context.get('company_name', 'N/A'),
            url=context.get('url', 'N/A'),
            total_violations=context.get('total_violations', 0),
            critical_count=context.get('critical_count', 0),
            overall_score=context.get('overall_score', 0),
            target_audience=requirements.get('target_audience', 'mixed'),
            language=requirements.get('language', 'it'),
            include_costs=requirements.get('include_cost_estimates', False)
        )
        
        return prompt
    
    def _get_executive_prompt_template(self) -> str:
        """Template prompt per Executive Summary"""
        return """
Genera un Executive Summary professionale per il report di accessibilità.

Dati azienda:
- Nome: {company_name}
- Sito: {url}
- Score: {overall_score}/100
- Problemi critici: {critical_count}
- Problemi totali: {total_violations}

Target audience: {target_audience}
Lingua: {language}

Focalizzati su:
1. Impatto business e rischi legali
2. Metriche chiave e KPI
3. Raccomandazioni strategiche con ROI
4. Timeline e priorità
5. Costi e benefici se richiesto: {include_costs}

Usa un linguaggio professionale adatto a C-level executives.
Evita tecnicismi non necessari.
Sii conciso ma completo.
        """
    
    def _get_technical_prompt_template(self) -> str:
        """Template prompt per Technical Analysis"""
        return """
Genera un'analisi tecnica dettagliata dei problemi di accessibilità.

Dati tecnici:
- Violazioni totali: {total_violations}
- Critiche: {critical_count}
- Score WCAG: {overall_score}/100

Richiesto:
1. Categorizzazione per area tecnica
2. Pattern e problemi ricorrenti
3. Analisi WCAG dettagliata
4. Stima debito tecnico
5. Root cause analysis

Target: Team tecnico
Dettaglio: Comprehensive
Includere esempi di codice dove appropriato.
        """
    
    def _get_compliance_prompt_template(self) -> str:
        """Template prompt per Compliance Assessment"""
        return """
Valuta la conformità agli standard di accessibilità.

Standard da valutare:
- WCAG 2.1 Livello AA
- European Accessibility Act (EAA)  
- EN 301 549
- Linee Guida AgID (per Italia)

Dati conformità:
- Score: {overall_score}/100
- Violazioni critiche: {critical_count}

Fornisci:
1. Stato conformità per ogni standard
2. Gap analysis dettagliata
3. Rischi di non conformità
4. Requisiti per conformità
5. Timeline compliance

Linguaggio: Legale/Compliance
Precisione: Alta
        """
    
    def _get_remediation_prompt_template(self) -> str:
        """Template prompt per Remediation Plan"""
        return """
Crea un piano di remediation dettagliato e prioritizzato.

Problemi da risolvere:
- Totali: {total_violations}
- Critici: {critical_count}
- Budget disponibile: Da determinare

Piano deve includere:
1. Prioritizzazione per impatto e effort
2. Timeline con milestone  
3. Stima risorse (ore/persone)
4. Quick wins identificati
5. Dipendenze tra correzioni
6. Test e validazione

Costi: {include_costs}
Approccio: Pragmatico e incrementale
        """
    
    def _get_recommendations_prompt_template(self) -> str:
        """Template prompt per Recommendations"""
        return """
Genera raccomandazioni strategiche per migliorare l'accessibilità.

Contesto:
- Azienda: {company_name}
- Score attuale: {overall_score}/100
- Problemi: {total_violations}

Raccomandazioni richieste:
1. Azioni immediate (entro 30gg)
2. Strategie medio termine (90gg)
3. Visione lungo termine
4. Best practice da implementare
5. Strumenti e tecnologie
6. Formazione e cultura aziendale

Focus: ROI e sostenibilità
Tono: Costruttivo e motivante
        """
    
    def _get_default_prompt(self) -> str:
        """Prompt di default generico"""
        return """
Genera una sezione di report professionale basata sui dati forniti.
Sii accurato, professionale e basati solo su dati verificabili.
Non inventare informazioni.
Usa un linguaggio appropriato al contesto.
        """
    
    def enhance_prompt_with_examples(self, 
                                    base_prompt: str,
                                    examples: List[Dict[str, str]]) -> str:
        """Arricchisce prompt con esempi
        
        Args:
            base_prompt: Prompt base
            examples: Lista di esempi input/output
            
        Returns:
            Prompt arricchito
        """
        
        if not examples:
            return base_prompt
        
        examples_text = "\n\nEsempi di output desiderato:\n"
        
        for i, example in enumerate(examples[:3], 1):  # Max 3 esempi
            examples_text += f"\nEsempio {i}:\n"
            examples_text += f"Input: {example.get('input', '')}\n"
            examples_text += f"Output: {example.get('output', '')}\n"
        
        return base_prompt + examples_text
    
    def get_validation_prompt(self, content: str) -> str:
        """Genera prompt per validazione contenuto
        
        Args:
            content: Contenuto da validare
            
        Returns:
            Prompt di validazione
        """
        
        return f"""
Valida il seguente contenuto per qualità e accuratezza:

{content[:500]}...

Verifica:
1. Accuratezza dei dati numerici
2. Consistenza delle informazioni
3. Completezza delle sezioni
4. Professionalità del linguaggio
5. Assenza di errori o contraddizioni

Fornisci un punteggio 0-100 e lista di problemi trovati.
        """
    
    def save_prompt_history(self, 
                           agent_type: str,
                           prompt: str,
                           response: str,
                           quality_score: float):
        """Salva storia prompt per learning
        
        Args:
            agent_type: Tipo agent
            prompt: Prompt usato
            response: Risposta ottenuta
            quality_score: Score qualità
        """
        
        # In produzione salvare su DB per ML/fine-tuning
        history_entry = {
            'agent_type': agent_type,
            'prompt_length': len(prompt),
            'response_length': len(response),
            'quality_score': quality_score,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Prompt history: {history_entry}")