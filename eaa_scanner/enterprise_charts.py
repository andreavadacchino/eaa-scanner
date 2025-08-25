"""
Enterprise Chart Generator con defensive programming e null safety
Gestisce robustamente dati mancanti e operazioni matematiche sicure
"""

import matplotlib
matplotlib.use('Agg')  # Backend non-interattivo
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
import base64
from io import BytesIO
import logging
from pathlib import Path
from decimal import Decimal, InvalidOperation
import traceback

logger = logging.getLogger(__name__)


class EnterpriseChartGenerator:
    """
    Chart generator enterprise con defensive programming
    
    Features:
    - Null-safe mathematical operations
    - Fallback graceful per errori matplotlib
    - Validazione dati input robusta
    - Error reporting dettagliato
    - Memory management ottimizzato
    """
    
    # Palette colori accessibili WCAG AA
    COLORS = {
        'primary': '#1f4e79',      # Blu scuro (contrast 7.8:1)
        'secondary': '#4a90a4',    # Blu medio (contrast 4.9:1)
        'success': '#2d5016',      # Verde scuro (contrast 8.2:1) 
        'warning': '#bf6900',      # Arancione (contrast 5.1:1)
        'danger': '#a50e0e',       # Rosso scuro (contrast 9.1:1)
        'info': '#0f3460',         # Blu info (contrast 11.2:1)
        'light': '#f8f9fa',        # Grigio chiaro
        'dark': '#212529',         # Grigio scuro
        
        # Severity mapping sicuro
        'critical': '#a50e0e',
        'high': '#bf6900', 
        'medium': '#8a6914',
        'low': '#2d5016'
    }
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Setup matplotlib sicuro
        self._setup_matplotlib_safe()
        
        # Statistics per monitoring
        self.generation_stats = {
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "fallback": 0
        }
    
    def _setup_matplotlib_safe(self):
        """Setup matplotlib con configurazione sicura"""
        try:
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
            plt.rcParams['font.size'] = 10
            plt.rcParams['figure.dpi'] = 100
            plt.rcParams['savefig.dpi'] = 150
            plt.rcParams['axes.spines.top'] = False
            plt.rcParams['axes.spines.right'] = False
            
        except Exception as e:
            logger.warning(f"Matplotlib setup warning: {e}")
    
    def generate_all_charts_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera tutti i charts con gestione robusta errori
        
        Args:
            data: Dati normalizzati (può contenere null values)
            
        Returns:
            Dizionario con charts generati e fallback info
        """
        
        logger.info("🎨 Avvio generazione charts enterprise")
        
        # Valida dati input
        validated_data = self._validate_and_clean_data(data)
        
        charts_data = {
            "generation_mode": "enterprise",
            "validation_passed": validated_data is not None,
            "charts": {},
            "fallbacks": {},
            "errors": []
        }
        
        if not validated_data:
            logger.error("❌ Validazione dati fallita - usando fallback completo")
            return self._generate_fallback_charts(data, charts_data)
        
        # Lista chart da generare con priority
        chart_generators = [
            ("overview_score", self._generate_overview_chart_safe, 1),
            ("severity_breakdown", self._generate_severity_chart_safe, 2),
            ("scanner_comparison", self._generate_scanner_chart_safe, 3),
            ("wcag_categories", self._generate_wcag_chart_safe, 4),
            ("compliance_gauge", self._generate_compliance_gauge_safe, 5)
        ]
        
        # Genera charts con error handling individuale
        for chart_name, generator_func, priority in chart_generators:
            self.generation_stats["attempted"] += 1
            
            try:
                logger.info(f"📊 Generando {chart_name}...")
                
                chart_result = generator_func(validated_data)
                
                if chart_result and chart_result.get("success"):
                    charts_data["charts"][chart_name] = chart_result
                    self.generation_stats["successful"] += 1
                    logger.info(f"✅ {chart_name} generato con successo")
                else:
                    # Fallback per questo chart
                    fallback = self._generate_chart_fallback(chart_name, validated_data)
                    charts_data["fallbacks"][chart_name] = fallback
                    self.generation_stats["fallback"] += 1
                    logger.warning(f"⚠️ {chart_name} usa fallback")
                    
            except Exception as e:
                error_msg = f"Error generating {chart_name}: {e}"
                logger.error(error_msg)
                
                charts_data["errors"].append(error_msg)
                
                # Fallback per questo chart
                fallback = self._generate_chart_fallback(chart_name, validated_data, error_msg)
                charts_data["fallbacks"][chart_name] = fallback
                self.generation_stats["failed"] += 1
        
        # Aggiungi statistiche generazione
        charts_data["generation_stats"] = self.generation_stats.copy()
        
        logger.info(f"🎨 Generazione completata: {self.generation_stats['successful']} successi, "
                   f"{self.generation_stats['fallback']} fallback, {self.generation_stats['failed']} errori")
        
        return charts_data
    
    def _validate_and_clean_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Valida e pulisce dati input per prevenire errori matematici
        
        Returns:
            Dati validati o None se validazione fallisce
        """
        try:
            if not data or not isinstance(data, dict):
                logger.error("Dati input non validi")
                return None
            
            # Estrai compliance info con fallback sicuri
            compliance = data.get("compliance", {})
            if not isinstance(compliance, dict):
                compliance = {}
            
            # Valida overall_score con handling robusto
            overall_score = compliance.get("overall_score", 0)
            overall_score = self._safe_numeric_conversion(overall_score, 0)
            overall_score = max(0, min(100, overall_score))  # Clamp 0-100
            
            # Estrai detailed_results con fallback
            detailed = data.get("detailed_results", {})
            if not isinstance(detailed, dict):
                detailed = {}
            
            errors = detailed.get("errors", [])
            warnings = detailed.get("warnings", [])
            scanner_scores = detailed.get("scanner_scores", {})
            
            if not isinstance(errors, list):
                errors = []
            if not isinstance(warnings, list):
                warnings = []
            if not isinstance(scanner_scores, dict):
                scanner_scores = {}
                
            # Pulisci scanner scores
            cleaned_scores = {}
            for scanner, score in scanner_scores.items():
                clean_score = self._safe_numeric_conversion(score, 0)
                clean_score = max(0, min(100, clean_score))
                cleaned_scores[str(scanner)] = clean_score
            
            # Costruisci dati validati
            validated_data = {
                "compliance": {
                    "overall_score": overall_score,
                    "compliance_level": str(compliance.get("compliance_level", "non_conforme"))
                },
                "detailed_results": {
                    "errors": errors,
                    "warnings": warnings,
                    "scanner_scores": cleaned_scores
                },
                "severity_counts": self._calculate_safe_severity_counts(errors, warnings),
                "wcag_categories": self._calculate_safe_wcag_categories(errors, warnings)
            }
            
            logger.info("✅ Validazione dati completata")
            return validated_data
            
        except Exception as e:
            logger.error(f"❌ Validazione dati fallita: {e}")
            return None
    
    def _safe_numeric_conversion(
        self, 
        value: Any, 
        default: Union[int, float] = 0
    ) -> Union[int, float]:
        """Conversione numerica sicura con fallback"""
        
        if value is None:
            return default
        
        # Se è già un numero
        if isinstance(value, (int, float)):
            if np.isnan(value) or np.isinf(value):
                return default
            return value
            
        # Se è Decimal
        if isinstance(value, Decimal):
            try:
                return float(value)
            except (ValueError, InvalidOperation):
                return default
        
        # Se è stringa
        if isinstance(value, str):
            try:
                # Prova int prima
                if '.' not in value:
                    return int(value)
                else:
                    return float(value)
            except (ValueError, TypeError):
                return default
        
        # Fallback finale
        return default
    
    def _calculate_safe_severity_counts(
        self, 
        errors: List[Dict], 
        warnings: List[Dict]
    ) -> Dict[str, int]:
        """Calcola conteggi severità in modo sicuro"""
        
        counts = {
            "critical": 0,
            "high": 0, 
            "medium": 0,
            "low": 0
        }
        
        # Conta errori
        for error in errors:
            if not isinstance(error, dict):
                continue
            severity = str(error.get("severity", "medium")).lower()
            count = self._safe_numeric_conversion(error.get("count", 1), 1)
            count = max(0, int(count))  # Assicura positivo
            
            if severity in counts:
                counts[severity] += count
                
        # Conta warnings
        for warning in warnings:
            if not isinstance(warning, dict):
                continue
            severity = str(warning.get("severity", "low")).lower()
            count = self._safe_numeric_conversion(warning.get("count", 1), 1)
            count = max(0, int(count))
            
            if severity in counts:
                counts[severity] += count
        
        return counts
    
    def _calculate_safe_wcag_categories(
        self,
        errors: List[Dict],
        warnings: List[Dict]
    ) -> Dict[str, int]:
        """Calcola categorie WCAG in modo sicuro"""
        
        categories = {
            "perceivable": 0,
            "operable": 0,
            "understandable": 0,
            "robust": 0
        }
        
        def get_wcag_category(wcag_criteria: str) -> str:
            """Mappa criterio WCAG a categoria POUR"""
            if not wcag_criteria or not isinstance(wcag_criteria, str):
                return "robust"
            
            first_char = wcag_criteria.strip()[0] if wcag_criteria.strip() else "4"
            mapping = {"1": "perceivable", "2": "operable", "3": "understandable", "4": "robust"}
            return mapping.get(first_char, "robust")
        
        # Processa errors + warnings
        all_issues = errors + warnings
        
        for issue in all_issues:
            if not isinstance(issue, dict):
                continue
                
            wcag_criteria = issue.get("wcag_criteria", "")
            category = get_wcag_category(wcag_criteria)
            count = self._safe_numeric_conversion(issue.get("count", 1), 1)
            count = max(0, int(count))
            
            categories[category] += count
            
        return categories
    
    def _generate_overview_chart_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera overview chart con gestione errori"""
        
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Estrai score
            score = data["compliance"]["overall_score"]
            compliance_level = data["compliance"]["compliance_level"]
            
            # Determina colore basato su compliance
            color_map = {
                "conforme": self.COLORS["success"],
                "parzialmente_conforme": self.COLORS["warning"],
                "non_conforme": self.COLORS["danger"]
            }
            color = color_map.get(compliance_level, self.COLORS["warning"])
            
            # Crea gauge chart
            theta = np.linspace(0, np.pi, 100)
            r_outer = 1.0
            r_inner = 0.7
            
            # Background arc
            ax.fill_between(theta, r_inner, r_outer, color='#e9ecef', alpha=0.3)
            
            # Score arc
            score_angle = (score / 100) * np.pi
            score_theta = np.linspace(0, score_angle, int(score))
            ax.fill_between(score_theta, r_inner, r_outer, color=color, alpha=0.8)
            
            # Testo centrale
            ax.text(0, 0.4, f"{score:.1f}", fontsize=32, weight='bold', 
                   ha='center', va='center', color=color)
            ax.text(0, 0.15, "Punteggio", fontsize=14, ha='center', va='center')
            ax.text(0, -0.05, "Accessibilità", fontsize=14, ha='center', va='center')
            
            # Etichette scale
            for angle, label in [(0, '0'), (np.pi/2, '50'), (np.pi, '100')]:
                x = r_outer * 1.1 * np.cos(angle)
                y = r_outer * 1.1 * np.sin(angle)
                ax.text(x, y, label, fontsize=10, ha='center', va='center')
            
            ax.set_xlim(-1.3, 1.3)
            ax.set_ylim(-0.3, 1.3)
            ax.set_aspect('equal')
            ax.axis('off')
            
            plt.title(f"Score Accessibilità - {compliance_level.replace('_', ' ').title()}", 
                     fontsize=16, weight='bold', pad=20)
            
            # Salva e converti
            image_data = self._save_chart_safe(fig, "overview_score")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": {
                    "score": score,
                    "compliance_level": compliance_level
                }
            }
            
        except Exception as e:
            logger.error(f"Overview chart error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_severity_chart_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera severity breakdown chart con null safety"""
        
        try:
            severity_counts = data["severity_counts"]
            
            # Filtra solo severità con count > 0
            filtered_counts = {k: v for k, v in severity_counts.items() if v > 0}
            
            if not filtered_counts:
                # Fallback per nessuna violazione
                return self._generate_no_violations_chart()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            labels = list(filtered_counts.keys())
            values = list(filtered_counts.values())
            colors = [self.COLORS.get(label, self.COLORS["info"]) for label in labels]
            
            # Bar chart orizzontale
            bars = ax.barh(labels, values, color=colors, alpha=0.8)
            
            # Aggiungi valori sulle barre
            for i, bar in enumerate(bars):
                width = bar.get_width()
                if width > 0:
                    ax.text(width + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                           f'{int(width)}', ha='left', va='center', fontweight='bold')
            
            ax.set_xlabel('Numero Violazioni', fontsize=12)
            ax.set_title('Distribuzione Violazioni per Severità', fontsize=14, weight='bold')
            
            # Styling
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            
            image_data = self._save_chart_safe(fig, "severity_breakdown")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": severity_counts
            }
            
        except Exception as e:
            logger.error(f"Severity chart error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_scanner_chart_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera confronto scanner con handling null scores"""
        
        try:
            scanner_scores = data["detailed_results"]["scanner_scores"]
            
            if not scanner_scores:
                return self._generate_no_scanners_chart()
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            scanners = list(scanner_scores.keys())
            scores = [self._safe_numeric_conversion(score, 0) for score in scanner_scores.values()]
            
            # Colori basati su score
            colors = []
            for score in scores:
                if score >= 80:
                    colors.append(self.COLORS["success"])
                elif score >= 60:
                    colors.append(self.COLORS["warning"])
                else:
                    colors.append(self.COLORS["danger"])
            
            bars = ax.bar(scanners, scores, color=colors, alpha=0.8)
            
            # Aggiungi valori sopra le barre
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{score:.0f}', ha='center', va='bottom', fontweight='bold')
            
            ax.set_ylabel('Score Accessibilità', fontsize=12)
            ax.set_ylim(0, 105)
            ax.set_title('Confronto Score per Scanner', fontsize=14, weight='bold')
            
            # Linee di riferimento
            ax.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='Soglia Buona (80)')
            ax.axhline(y=60, color='orange', linestyle='--', alpha=0.5, label='Soglia Minima (60)')
            
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            image_data = self._save_chart_safe(fig, "scanner_comparison")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": scanner_scores
            }
            
        except Exception as e:
            logger.error(f"Scanner chart error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_wcag_chart_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera chart categorie WCAG con null handling"""
        
        try:
            wcag_categories = data["wcag_categories"]
            
            # Filtra categorie con violazioni
            filtered_categories = {k: v for k, v in wcag_categories.items() if v > 0}
            
            if not filtered_categories:
                return self._generate_no_wcag_violations_chart()
            
            fig, ax = plt.subplots(figsize=(8, 8))
            
            labels = list(filtered_categories.keys())
            values = list(filtered_categories.values())
            
            # Pie chart con colori accessibili
            colors = [self.COLORS["primary"], self.COLORS["secondary"], 
                     self.COLORS["warning"], self.COLORS["info"]]
            
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                            colors=colors[:len(labels)], startangle=90,
                                            textprops={'fontsize': 12})
            
            # Migliora leggibilità
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title('Violazioni per Principio WCAG', fontsize=14, weight='bold')
            
            plt.tight_layout()
            
            image_data = self._save_chart_safe(fig, "wcag_categories")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": wcag_categories
            }
            
        except Exception as e:
            logger.error(f"WCAG chart error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_compliance_gauge_safe(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera gauge compliance con styling sicuro"""
        
        try:
            score = data["compliance"]["overall_score"]
            compliance_level = data["compliance"]["compliance_level"]
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Gauge semicircolare
            theta = np.linspace(0, np.pi, 180)
            
            # Background
            ax.fill_between(theta, 0.8, 1.0, color='#e9ecef', alpha=0.3)
            
            # Sezioni colorate
            sections = [
                (0, 0.6, self.COLORS["danger"]),      # 0-60 rosso
                (0.6, 0.8, self.COLORS["warning"]),   # 60-80 arancione  
                (0.8, 1.0, self.COLORS["success"])    # 80-100 verde
            ]
            
            for start, end, color in sections:
                start_angle = start * np.pi
                end_angle = end * np.pi
                section_theta = np.linspace(start_angle, end_angle, 50)
                ax.fill_between(section_theta, 0.8, 1.0, color=color, alpha=0.6)
            
            # Indicatore score
            score_angle = (score / 100) * np.pi
            ax.arrow(0, 0, 0.9 * np.cos(score_angle), 0.9 * np.sin(score_angle),
                    head_width=0.05, head_length=0.05, fc='black', ec='black', lw=3)
            
            # Testo centrale
            ax.text(0, 0.3, f"{score:.1f}", fontsize=28, weight='bold', ha='center', va='center')
            ax.text(0, 0.15, compliance_level.replace('_', ' ').title(), 
                   fontsize=12, ha='center', va='center')
            
            # Etichette
            ax.text(-0.9, -0.1, '0', fontsize=10, ha='center')
            ax.text(0, 1.1, '50', fontsize=10, ha='center')
            ax.text(0.9, -0.1, '100', fontsize=10, ha='center')
            
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-0.2, 1.3)
            ax.set_aspect('equal')
            ax.axis('off')
            
            plt.title('Gauge Conformità EAA', fontsize=16, weight='bold', pad=20)
            
            image_data = self._save_chart_safe(fig, "compliance_gauge")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": {
                    "score": score,
                    "compliance_level": compliance_level
                }
            }
            
        except Exception as e:
            logger.error(f"Compliance gauge error: {e}")
            return {"success": False, "error": str(e)}
    
    def _save_chart_safe(self, fig, filename: str) -> Optional[str]:
        """Salva chart come base64 con error handling"""
        
        try:
            # Salva su file
            file_path = self.output_dir / f"{filename}.png"
            fig.savefig(file_path, dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            
            # Converti a base64
            buffer = BytesIO()
            fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            buffer.close()
            
            return image_base64
            
        except Exception as e:
            logger.error(f"Chart save error for {filename}: {e}")
            return None
    
    def _generate_chart_fallback(
        self, 
        chart_name: str, 
        data: Dict[str, Any], 
        error_msg: str = ""
    ) -> Dict[str, Any]:
        """Genera fallback testuale per chart fallito"""
        
        fallback = {
            "type": "text_fallback",
            "chart_name": chart_name,
            "error": error_msg,
            "summary": {}
        }
        
        try:
            # Estrai metriche basic per fallback
            if "compliance" in data:
                fallback["summary"]["overall_score"] = data["compliance"].get("overall_score", 0)
                fallback["summary"]["compliance_level"] = data["compliance"].get("compliance_level", "non_conforme")
            
            if "severity_counts" in data:
                fallback["summary"]["violations"] = data["severity_counts"]
                
            if "detailed_results" in data and "scanner_scores" in data["detailed_results"]:
                fallback["summary"]["scanner_scores"] = data["detailed_results"]["scanner_scores"]
                
        except Exception as e:
            logger.error(f"Fallback generation error: {e}")
            
        return fallback
    
    def _generate_fallback_charts(self, original_data: Dict, charts_data: Dict) -> Dict[str, Any]:
        """Genera set completo di fallback quando validazione fallisce"""
        
        charts_data["fallback_mode"] = True
        charts_data["fallbacks"] = {
            "overview_score": {
                "type": "validation_failed",
                "message": "Impossibile validare dati per overview chart"
            },
            "severity_breakdown": {
                "type": "validation_failed", 
                "message": "Impossibile determinare breakdown severità"
            },
            "scanner_comparison": {
                "type": "validation_failed",
                "message": "Impossibile confrontare scanner"
            }
        }
        
        return charts_data
    
    def _generate_no_violations_chart(self) -> Dict[str, Any]:
        """Genera chart per caso nessuna violazione"""
        
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            ax.text(0.5, 0.5, '🎉\nNessuna Violazione\nRilevata!', 
                   fontsize=24, ha='center', va='center', 
                   transform=ax.transAxes, weight='bold',
                   color=self.COLORS["success"])
            
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            
            plt.title('Severità Violazioni', fontsize=14, weight='bold')
            
            image_data = self._save_chart_safe(fig, "no_violations")
            plt.close(fig)
            
            return {
                "success": True,
                "image_base64": image_data,
                "metrics": {"message": "no_violations_detected"}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_no_scanners_chart(self) -> Dict[str, Any]:
        """Genera chart per caso nessuno scanner"""
        
        return {
            "success": False,
            "error": "Nessuno scanner ha prodotto risultati validi",
            "fallback_type": "no_scanners"
        }
    
    def _generate_no_wcag_violations_chart(self) -> Dict[str, Any]:
        """Genera chart per caso nessuna violazione WCAG"""
        
        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            
            ax.text(0.5, 0.5, '✅\nNessuna Violazione\nWCAG Rilevata', 
                   fontsize=20, ha='center', va='center',
                   transform=ax.transAxes, color=self.COLORS["success"])
            
            ax.axis('off')
            plt.title('Principi WCAG', fontsize=14, weight='bold')
            
            image_data = self._save_chart_safe(fig, "no_wcag_violations")
            plt.close(fig)
            
            return {
                "success": True, 
                "image_base64": image_data,
                "metrics": {"message": "no_wcag_violations"}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Factory function
def create_enterprise_chart_generator(output_dir: str) -> EnterpriseChartGenerator:
    """Factory per creare chart generator enterprise"""
    return EnterpriseChartGenerator(output_dir)