from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple
import json

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .config import Config

logger = logging.getLogger(__name__)


class LLMIntegration:
    """Integrazione LLM per generazione contenuti avanzati nei report di accessibilità"""
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.llm_enabled and bool(config.openai_api_key) and OPENAI_AVAILABLE
        self.client: Optional[OpenAI] = None
        
        if self.enabled:
            try:
                self.client = OpenAI(api_key=config.openai_api_key)
                logger.info(f"LLM integration abilitata con modello primario: {config.llm_model_primary}")
            except Exception as e:
                logger.warning(f"Errore inizializzazione client OpenAI: {e}")
                self.enabled = False
        else:
            logger.info("LLM integration disabilitata o non disponibile")
    
    def is_enabled(self) -> bool:
        """Verifica se l'integrazione LLM è attiva"""
        return self.enabled
    
    def generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Genera un executive summary basato sui dati di scansione"""
        if not self.enabled:
            return self._fallback_executive_summary(data)
        
        try:
            compliance = data.get("compliance", {})
            issues_count = {
                "errors": len(data.get("detailed_results", {}).get("errors", [])),
                "warnings": len(data.get("detailed_results", {}).get("warnings", []))
            }
            
            prompt = self._build_executive_summary_prompt(data, compliance, issues_count)
            
            response = self._call_llm(prompt, max_tokens=500)
            if response:
                logger.debug("Executive summary generato via LLM")
                return response
            else:
                logger.warning("LLM ha restituito risposta vuota, uso fallback")
                return self._fallback_executive_summary(data)
                
        except Exception as e:
            logger.error(f"Errore generazione executive summary: {e}")
            return self._fallback_executive_summary(data)
    
    def generate_technical_recommendations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Genera raccomandazioni tecniche specifiche per i problemi rilevati"""
        if not self.enabled:
            return self._fallback_technical_recommendations(data)
        
        try:
            errors = data.get("detailed_results", {}).get("errors", [])[:10]  # Limita ai primi 10 errori
            if not errors:
                return []
            
            prompt = self._build_recommendations_prompt(data, errors)
            
            response = self._call_llm(prompt, max_tokens=800, temperature=0.7)
            if response:
                try:
                    # Tenta di parsare la risposta JSON
                    recommendations = json.loads(response)
                    if isinstance(recommendations, list):
                        logger.debug(f"Generate {len(recommendations)} raccomandazioni tecniche via LLM")
                        return recommendations
                except json.JSONDecodeError:
                    logger.warning("Risposta LLM non è JSON valido, uso parsing testuale")
                    return self._parse_text_recommendations(response)
            
            return self._fallback_technical_recommendations(data)
            
        except Exception as e:
            logger.error(f"Errore generazione raccomandazioni tecniche: {e}")
            return self._fallback_technical_recommendations(data)
    
    def generate_remediation_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un piano di remediation strutturato"""
        if not self.enabled:
            return self._fallback_remediation_plan(data)
        
        try:
            compliance = data.get("compliance", {})
            errors = data.get("detailed_results", {}).get("errors", [])
            
            # Raggruppa errori per severità e criterio WCAG
            error_analysis = self._analyze_errors_for_plan(errors)
            
            prompt = self._build_remediation_plan_prompt(data, compliance, error_analysis)
            
            response = self._call_llm(prompt, max_tokens=1000, temperature=0.8)
            if response:
                try:
                    plan = json.loads(response)
                    if isinstance(plan, dict):
                        logger.debug("Piano di remediation generato via LLM")
                        return plan
                except json.JSONDecodeError:
                    logger.warning("Piano LLM non è JSON valido, uso fallback")
            
            return self._fallback_remediation_plan(data)
            
        except Exception as e:
            logger.error(f"Errore generazione piano remediation: {e}")
            return self._fallback_remediation_plan(data)
    
    def _call_llm(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> Optional[str]:
        """Chiamata al modello LLM con gestione fallback"""
        if not self.client:
            return None
        
        models = [self.config.llm_model_primary, self.config.llm_model_fallback]
        
        for model in models:
            try:
                logger.debug(f"Chiamata LLM con modello: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Sei un esperto di accessibilità web che aiuta a creare report professionali in italiano. Rispondi sempre in italiano."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                content = response.choices[0].message.content
                if content:
                    return content.strip()
                    
            except Exception as e:
                logger.warning(f"Errore con modello {model}: {e}")
                continue
        
        return None
    
    def _build_executive_summary_prompt(self, data: Dict[str, Any], compliance: Dict[str, Any], issues_count: Dict[str, int]) -> str:
        """Costruisce il prompt per l'executive summary"""
        company = data.get("company_name", "il sito web")
        url = data.get("url", "")
        score = compliance.get("overall_score", 0)
        compliance_level = compliance.get("compliance_level", "non_conforme")
        
        return f"""
Genera un executive summary professionale per un report di accessibilità EAA.

CONTESTO:
- Azienda: {company}
- URL: {url}
- Score complessivo: {score}/100
- Livello conformità: {compliance_level.replace('_', ' ')}
- Errori critici: {issues_count['errors']}
- Avvisi: {issues_count['warnings']}

Scrivi un paragrafo di 3-4 frasi che riassuma:
1. Lo stato generale dell'accessibilità
2. I punti critici principali
3. L'impatto sulla conformità EAA
4. Un accenno alle prossime azioni

Mantieni un tono professionale ma comprensibile. Scrivi in italiano.
"""

    def _build_recommendations_prompt(self, data: Dict[str, Any], errors: List[Dict[str, Any]]) -> str:
        """Costruisce il prompt per le raccomandazioni tecniche"""
        error_summary = "\n".join([
            f"- {error.get('description', 'N/A')} (WCAG: {error.get('wcag_criteria', 'N/A')}, Severità: {error.get('severity', 'medium')})"
            for error in errors[:5]
        ])
        
        return f"""
Genera raccomandazioni tecniche specifiche per questi errori di accessibilità:

ERRORI RILEVATI:
{error_summary}

Crea un JSON array con massimo 5 raccomandazioni. Ogni raccomandazione deve avere:
- "title": titolo breve e specifico
- "priority": "alta", "media" o "bassa"
- "description": spiegazione del problema (max 2 frasi)
- "actions": array di 2-4 azioni concrete da implementare
- "wcag_criteria": criteri WCAG coinvolti
- "estimated_effort": "basso", "medio" o "alto"

Rispondi SOLO con il JSON valido, senza altre spiegazioni.
"""

    def _build_remediation_plan_prompt(self, data: Dict[str, Any], compliance: Dict[str, Any], error_analysis: Dict[str, Any]) -> str:
        """Costruisce il prompt per il piano di remediation"""
        score = compliance.get("overall_score", 0)
        critical_count = error_analysis.get("critical_count", 0)
        high_count = error_analysis.get("high_count", 0)
        
        return f"""
Crea un piano di remediation strutturato per migliorare l'accessibilità.

SITUAZIONE ATTUALE:
- Score: {score}/100
- Errori critici: {critical_count}
- Errori alta priorità: {high_count}
- Criteri WCAG più problematici: {', '.join(error_analysis.get('top_wcag_issues', []))}

Genera un JSON con questa struttura:
{{
  "fasi": [
    {{
      "nome": "Fase 1: Correzioni critiche",
      "durata_stimata": "1-2 settimane",
      "priorita": "critica",
      "obiettivi": ["obiettivo 1", "obiettivo 2"],
      "attivita": ["attività 1", "attività 2"]
    }}
  ],
  "milestone": [
    {{
      "settimana": 2,
      "obiettivo": "Risoluzione errori critici",
      "metriche": ["Score > 70", "Zero errori critical"]
    }}
  ],
  "risorse_necessarie": ["risorsa 1", "risorsa 2"],
  "rischi": ["rischio 1", "rischio 2"]
}}

Prevedi 3-4 fasi con timeline realistiche. Rispondi SOLO con JSON valido.
"""

    def _analyze_errors_for_plan(self, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analizza gli errori per il piano di remediation"""
        analysis = {
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "wcag_counts": {},
            "top_wcag_issues": []
        }
        
        for error in errors:
            severity = error.get("severity", "medium").lower()
            if severity == "critical":
                analysis["critical_count"] += 1
            elif severity == "high":
                analysis["high_count"] += 1
            elif severity == "medium":
                analysis["medium_count"] += 1
            else:
                analysis["low_count"] += 1
            
            wcag = error.get("wcag_criteria", "")
            if wcag:
                analysis["wcag_counts"][wcag] = analysis["wcag_counts"].get(wcag, 0) + 1
        
        # Top 3 criteri WCAG più problematici
        sorted_wcag = sorted(analysis["wcag_counts"].items(), key=lambda x: x[1], reverse=True)
        analysis["top_wcag_issues"] = [wcag for wcag, count in sorted_wcag[:3]]
        
        return analysis
    
    def _parse_text_recommendations(self, text: str) -> List[Dict[str, Any]]:
        """Parse raccomandazioni da testo libero se JSON parsing fallisce"""
        # Implementazione semplificata per parsing testuale
        return [{
            "title": "Raccomandazioni generate via LLM",
            "priority": "media",
            "description": text[:200] + "..." if len(text) > 200 else text,
            "actions": ["Revisiona le raccomandazioni generate", "Implementa le correzioni suggerite"],
            "wcag_criteria": "",
            "estimated_effort": "medio"
        }]
    
    # Metodi fallback che restituiscono contenuto statico quando LLM non è disponibile
    
    def _fallback_executive_summary(self, data: Dict[str, Any]) -> str:
        """Executive summary di fallback senza LLM"""
        compliance = data.get("compliance", {})
        score = compliance.get("overall_score", 0)
        errors_count = len(data.get("detailed_results", {}).get("errors", []))
        company = data.get("company_name", "il sito web")
        
        if score >= 85:
            status = "presenta un buon livello di accessibilità"
        elif score >= 60:
            status = "presenta alcune criticità di accessibilità che richiedono attenzione"
        else:
            status = "presenta significative barriere all'accessibilità che devono essere risolte"
        
        return f"""L'analisi di accessibilità di {company} {status}. 
Con un punteggio di {score}/100 e {errors_count} errori rilevati, sono necessarie azioni correttive per 
garantire la conformità agli standard WCAG 2.1 AA e alla normativa EAA. 
L'implementazione delle raccomandazioni contenute in questo report permetterà di migliorare 
significativamente l'esperienza utente e la conformità normativa."""
    
    def _fallback_technical_recommendations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Raccomandazioni tecniche di fallback senza LLM"""
        errors = data.get("detailed_results", {}).get("errors", [])
        
        recommendations = []
        
        # Analizza i tipi di errori più comuni per generare raccomandazioni base
        error_types = {}
        for error in errors[:10]:
            desc = error.get("description", "").lower()
            if "alt" in desc or "immagine" in desc:
                error_types["images"] = error_types.get("images", 0) + 1
            elif "contrasto" in desc or "colore" in desc:
                error_types["contrast"] = error_types.get("contrast", 0) + 1
            elif "form" in desc or "label" in desc:
                error_types["forms"] = error_types.get("forms", 0) + 1
            elif "heading" in desc or "titolo" in desc:
                error_types["headings"] = error_types.get("headings", 0) + 1
        
        if error_types.get("images", 0) > 0:
            recommendations.append({
                "title": "Ottimizzazione testi alternativi",
                "priority": "alta",
                "description": "Sono stati rilevati problemi con i testi alternativi delle immagini che compromettono l'accessibilità per utenti con screen reader.",
                "actions": [
                    "Aggiungere attributi alt descrittivi a tutte le immagini informative",
                    "Utilizzare alt=\"\" per immagini puramente decorative",
                    "Verificare che le immagini complesse abbiano descrizioni dettagliate",
                    "Testare con screen reader la comprensibilità dei contenuti"
                ],
                "wcag_criteria": "WCAG 2.1 - 1.1.1",
                "estimated_effort": "medio"
            })
        
        if error_types.get("contrast", 0) > 0:
            recommendations.append({
                "title": "Correzione contrasto colori",
                "priority": "alta", 
                "description": "I rapporti di contrasto tra testo e sfondo non soddisfano i requisiti minimi per la leggibilità.",
                "actions": [
                    "Verificare tutti i rapporti di contrasto con strumenti automatici",
                    "Modificare i colori per raggiungere almeno 4.5:1 per il testo normale",
                    "Garantire 3:1 per testi grandi e elementi grafici",
                    "Testare la leggibilità in diverse condizioni di illuminazione"
                ],
                "wcag_criteria": "WCAG 2.1 - 1.4.3",
                "estimated_effort": "alto"
            })
        
        if error_types.get("forms", 0) > 0:
            recommendations.append({
                "title": "Miglioramento accessibilità form",
                "priority": "media",
                "description": "I moduli presentano problemi di etichettatura e struttura che possono impedire la compilazione agli utenti con disabilità.",
                "actions": [
                    "Associare correttamente tutte le etichette ai campi input",
                    "Aggiungere istruzioni chiare per campi obbligatori",
                    "Implementare messaggi di errore descrittivi e accessibili",
                    "Garantire navigazione da tastiera completa"
                ],
                "wcag_criteria": "WCAG 2.1 - 3.3.2",
                "estimated_effort": "medio"
            })
        
        if not recommendations:
            # Raccomandazione generica se non si rilevano pattern specifici
            recommendations.append({
                "title": "Revisione generale accessibilità",
                "priority": "media",
                "description": "Sono stati rilevati diversi problemi di accessibilità che richiedono un'analisi e correzione sistematica.",
                "actions": [
                    "Condurre audit manuale approfondito",
                    "Implementare test automatici nel processo di sviluppo", 
                    "Formare il team sui principi di accessibilità",
                    "Testare con utenti reali e tecnologie assistive"
                ],
                "wcag_criteria": "WCAG 2.1 - Generale",
                "estimated_effort": "alto"
            })
        
        return recommendations[:5]  # Limita a 5 raccomandazioni
    
    def _fallback_remediation_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Piano di remediation di fallback senza LLM"""
        compliance = data.get("compliance", {})
        score = compliance.get("overall_score", 0)
        errors_count = len(data.get("detailed_results", {}).get("errors", []))
        
        # Piano base adattato al punteggio
        if score < 50:
            # Situazione critica
            plan = {
                "fasi": [
                    {
                        "nome": "Fase 1: Correzioni critiche immediate",
                        "durata_stimata": "2-3 settimane",
                        "priorita": "critica",
                        "obiettivi": [
                            "Risolvere tutti gli errori critici",
                            "Migliorare accessibilità base"
                        ],
                        "attivita": [
                            "Audit dettagliato di tutti gli errori critici",
                            "Correzione problemi di contrasto colori",
                            "Implementazione testi alternativi",
                            "Fix navigazione da tastiera"
                        ]
                    },
                    {
                        "nome": "Fase 2: Miglioramenti strutturali",
                        "durata_stimata": "3-4 settimane",
                        "priorita": "alta",
                        "obiettivi": [
                            "Sistemare struttura semantica",
                            "Migliorare form e controlli"
                        ],
                        "attivita": [
                            "Ottimizzare gerarchia dei titoli",
                            "Migliorare etichettatura form",
                            "Implementare ARIA dove necessario",
                            "Test con screen reader"
                        ]
                    },
                    {
                        "nome": "Fase 3: Validazione e conformità",
                        "durata_stimata": "1-2 settimane",
                        "priorita": "media",
                        "obiettivi": [
                            "Raggiungere conformità WCAG AA",
                            "Documentare accessibilità"
                        ],
                        "attivita": [
                            "Test di validazione finale",
                            "Creazione documentazione accessibilità",
                            "Training team interno",
                            "Processo di mantenimento"
                        ]
                    }
                ]
            }
        else:
            # Situazione migliorabile
            plan = {
                "fasi": [
                    {
                        "nome": "Fase 1: Correzioni prioritarie",
                        "durata_stimata": "1-2 settimane", 
                        "priorita": "alta",
                        "obiettivi": [
                            "Risolvere errori ad alta priorità",
                            "Migliorare score accessibilità"
                        ],
                        "attivita": [
                            "Correzione errori alta priorità",
                            "Ottimizzazione contenuti esistenti",
                            "Test di regressione"
                        ]
                    },
                    {
                        "nome": "Fase 2: Ottimizzazioni finali",
                        "durata_stimata": "1-2 settimane",
                        "priorita": "media", 
                        "obiettivi": [
                            "Raggiungere piena conformità",
                            "Implementare best practices"
                        ],
                        "attivita": [
                            "Risoluzione avvisi rimanenti",
                            "Miglioramento esperienza utente",
                            "Documentazione finale"
                        ]
                    }
                ]
            }
        
        # Aggiungi milestone e dettagli comuni
        plan.update({
            "milestone": [
                {
                    "settimana": 2,
                    "obiettivo": "Completamento correzioni critiche",
                    "metriche": [f"Score > {min(score + 20, 85)}", "Zero errori critical"]
                },
                {
                    "settimana": 4,
                    "obiettivo": "Raggiungimento conformità base",
                    "metriche": ["Score > 85", "Conformità WCAG AA"]
                }
            ],
            "risorse_necessarie": [
                "Sviluppatore frontend con competenze accessibility",
                "Designer per revisioni UI/UX", 
                "Tester con tecnologie assistive",
                "Tool di testing automatico"
            ],
            "rischi": [
                "Impatto su design esistente",
                "Tempi di sviluppo sottostimati",
                "Necessità di modifiche backend",
                "Test utente insufficienti"
            ]
        })
        
        return plan