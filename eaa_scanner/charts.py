"""
Generazione grafici e visualizzazioni per report accessibilità
"""
import matplotlib
matplotlib.use('Agg')  # Backend non-interattivo per server
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import base64
from io import BytesIO
import logging
from pathlib import Path

# Configurazione stile italiano professionale
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generatore di grafici professionali per report EAA
    """
    
    # Palette colori accessibili e professionali
    COLORS = {
        'primary': '#2E5266',      # Blu scuro professionale
        'secondary': '#6E8898',    # Grigio blu
        'success': '#52B788',      # Verde successo
        'warning': '#F77F00',      # Arancione warning
        'danger': '#D62828',       # Rosso errore
        'info': '#4CC9F0',         # Azzurro info
        'light': '#F8F9FA',        # Grigio chiaro
        'dark': '#212529',         # Grigio scuro
        
        # Colori per severità
        'critical': '#D62828',
        'high': '#F77F00',
        'medium': '#FFC107',
        'low': '#52B788',
        
        # Colori per principi WCAG
        'perceivable': '#2E5266',
        'operable': '#6E8898',
        'understandable': '#52B788',
        'robust': '#4CC9F0'
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inizializza generatore grafici
        
        Args:
            output_dir: Directory output per salvare grafici
        """
        self.output_dir = output_dir or Path.cwd() / "charts"
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all_charts(self, analytics_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Genera tutti i grafici per il report
        
        Args:
            analytics_data: Dati analytics completi
            
        Returns:
            Dizionario con path/base64 dei grafici generati
        """
        charts = {}
        
        try:
            # Dashboard principale
            charts['dashboard'] = self.create_dashboard(analytics_data)
            
            # Grafici individuali
            charts['compliance_gauge'] = self.create_compliance_gauge(
                analytics_data.get('executive_summary', {})
            )
            charts['severity_donut'] = self.create_severity_donut(
                analytics_data.get('quantitative_analysis', {})
            )
            charts['wcag_principles'] = self.create_wcag_principles_radar(
                analytics_data.get('wcag_analysis', {})
            )
            charts['issues_by_category'] = self.create_category_bar_chart(
                analytics_data.get('category_analysis', {})
            )
            charts['scanner_comparison'] = self.create_scanner_comparison(
                analytics_data.get('scanner_comparison', {})
            )
            charts['remediation_timeline'] = self.create_remediation_timeline(
                analytics_data.get('effort_estimation', {})
            )
            charts['risk_matrix'] = self.create_risk_matrix(
                analytics_data.get('risk_assessment', {})
            )
            charts['benchmark_comparison'] = self.create_benchmark_chart(
                analytics_data.get('benchmarks', {})
            )
            
        except Exception as e:
            logger.error(f"Errore generazione grafici: {e}")
        
        return charts
    
    def create_dashboard(self, analytics_data: Dict[str, Any]) -> str:
        """
        Crea dashboard riepilogativa con metriche chiave
        
        Args:
            analytics_data: Dati analytics completi
            
        Returns:
            Path o base64 del grafico
        """
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle('Dashboard Accessibilità - Analisi Complessiva', fontsize=16, fontweight='bold')
        
        # Layout grid
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # 1. Score complessivo (grande)
        ax1 = fig.add_subplot(gs[0, :2])
        self._draw_score_card(ax1, analytics_data.get('executive_summary', {}))
        
        # 2. Distribuzione severità
        ax2 = fig.add_subplot(gs[0, 2:])
        self._draw_severity_distribution(ax2, analytics_data.get('quantitative_analysis', {}))
        
        # 3. Principi WCAG
        ax3 = fig.add_subplot(gs[1, :2])
        self._draw_wcag_bars(ax3, analytics_data.get('wcag_analysis', {}))
        
        # 4. Trend indicatori
        ax4 = fig.add_subplot(gs[1, 2:])
        self._draw_trend_indicators(ax4, analytics_data.get('trend_indicators', {}))
        
        # 5. Top issues
        ax5 = fig.add_subplot(gs[2, :2])
        self._draw_top_issues(ax5, analytics_data.get('wcag_analysis', {}))
        
        # 6. Effort estimation
        ax6 = fig.add_subplot(gs[2, 2:])
        self._draw_effort_summary(ax6, analytics_data.get('effort_estimation', {}))
        
        # Salva o converti in base64
        return self._save_figure(fig, 'dashboard')
    
    def create_compliance_gauge(self, executive_summary: Dict[str, Any]) -> str:
        """
        Crea gauge meter per score di conformità
        
        Args:
            executive_summary: Dati sommario esecutivo
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        score = executive_summary.get('compliance_score', 0)
        level = executive_summary.get('compliance_level', 'non_conforme')
        
        # Crea gauge semicircolare
        theta = np.linspace(np.pi, 0, 100)
        r_inner = 0.7
        r_outer = 1.0
        
        # Colori per zone
        colors = ['#D62828', '#F77F00', '#FFC107', '#52B788', '#2E5266']
        boundaries = [0, 40, 60, 75, 85, 100]
        
        # Disegna arco colorato
        for i in range(len(boundaries) - 1):
            theta_start = np.pi * (1 - boundaries[i] / 100)
            theta_end = np.pi * (1 - boundaries[i + 1] / 100)
            theta_range = np.linspace(theta_start, theta_end, 20)
            
            x_outer = r_outer * np.cos(theta_range)
            y_outer = r_outer * np.sin(theta_range)
            x_inner = r_inner * np.cos(theta_range)
            y_inner = r_inner * np.sin(theta_range)
            
            vertices = list(zip(x_outer, y_outer)) + list(zip(x_inner[::-1], y_inner[::-1]))
            poly = patches.Polygon(vertices, facecolor=colors[i], edgecolor='white', linewidth=2)
            ax.add_patch(poly)
        
        # Aggiungi indicatore
        angle = np.pi * (1 - score / 100)
        arrow_length = 0.85
        ax.arrow(0, 0, arrow_length * np.cos(angle), arrow_length * np.sin(angle),
                head_width=0.05, head_length=0.05, fc='black', ec='black', lw=2)
        
        # Centro
        circle = patches.Circle((0, 0), 0.1, facecolor='white', edgecolor='black', lw=2)
        ax.add_patch(circle)
        
        # Testo score
        ax.text(0, -0.2, f'{score}', fontsize=36, fontweight='bold', ha='center')
        ax.text(0, -0.35, 'SCORE', fontsize=12, ha='center')
        
        # Livello conformità
        level_text = level.replace('_', ' ').upper()
        ax.text(0, -0.5, level_text, fontsize=14, fontweight='bold', ha='center',
                color=self._get_level_color(level))
        
        # Labels
        ax.text(-1.1, 0, '0', fontsize=10, ha='center')
        ax.text(1.1, 0, '100', fontsize=10, ha='center')
        ax.text(0, 1.1, '50', fontsize=10, ha='center')
        
        # Legenda zone
        legend_items = [
            ('Non Conforme', colors[0]),
            ('Insufficiente', colors[1]),
            ('Sufficiente', colors[2]),
            ('Buono', colors[3]),
            ('Eccellente', colors[4])
        ]
        
        for i, (label, color) in enumerate(legend_items):
            y_pos = 0.6 - i * 0.15
            rect = Rectangle((1.3, y_pos), 0.1, 0.08, facecolor=color)
            ax.add_patch(rect)
            ax.text(1.45, y_pos + 0.04, label, fontsize=9, va='center')
        
        ax.set_xlim(-1.5, 2)
        ax.set_ylim(-0.7, 1.3)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Score di Conformità WCAG', fontsize=14, fontweight='bold', pad=20)
        
        return self._save_figure(fig, 'compliance_gauge')
    
    def create_severity_donut(self, quantitative_data: Dict[str, Any]) -> str:
        """
        Crea donut chart per distribuzione severità
        
        Args:
            quantitative_data: Dati analisi quantitativa
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        
        severity_breakdown = quantitative_data.get('severity_breakdown', {})
        
        # Prepara dati
        labels = []
        sizes = []
        colors = []
        
        for severity in ['critical', 'high', 'medium', 'low']:
            data = severity_breakdown.get(severity, {})
            count = data.get('count', 0)
            if count > 0:
                labels.append(f"{severity.capitalize()}\n({count})")
                sizes.append(count)
                colors.append(self.COLORS[severity])
        
        if not sizes:
            ax.text(0.5, 0.5, 'Nessun problema rilevato', ha='center', va='center',
                   fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return self._save_figure(fig, 'severity_donut')
        
        # Crea donut chart
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                          autopct='%1.1f%%', startangle=90,
                                          wedgeprops={'width': 0.5, 'edgecolor': 'white', 'linewidth': 2})
        
        # Stile testi
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)
        
        # Totale al centro
        total = sum(sizes)
        ax.text(0, 0, f'{total}\nProblemi\nTotali', ha='center', va='center',
               fontsize=14, fontweight='bold')
        
        ax.set_title('Distribuzione per Severità', fontsize=14, fontweight='bold', pad=20)
        
        return self._save_figure(fig, 'severity_donut')
    
    def create_wcag_principles_radar(self, wcag_data: Dict[str, Any]) -> str:
        """
        Crea radar chart per principi WCAG (POUR)
        
        Args:
            wcag_data: Dati analisi WCAG
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        principles = wcag_data.get('principle_distribution', {})
        
        # Prepara dati
        categories = ['Percepibile', 'Operabile', 'Comprensibile', 'Robusto']
        N = len(categories)
        
        # Calcola scores (inverso degli errori)
        values = []
        for key in ['perceivable', 'operable', 'understandable', 'robust']:
            data = principles.get(key, {})
            errors = data.get('errors', 0)
            warnings = data.get('warnings', 0)
            # Formula per score: max 100, penalità per errori e warning
            score = max(0, 100 - (errors * 15) - (warnings * 5))
            values.append(score)
        
        # Angoli per categorie
        angles = [n / N * 2 * np.pi for n in range(N)]
        values += values[:1]  # Chiudi il poligono
        angles += angles[:1]
        
        # Plot
        ax.plot(angles, values, 'o-', linewidth=2, color=self.COLORS['primary'])
        ax.fill(angles, values, alpha=0.25, color=self.COLORS['primary'])
        
        # Aggiungi grid circolare
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'])
        ax.grid(True)
        
        # Labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        
        # Aggiungi valori
        for angle, value, cat in zip(angles[:-1], values[:-1], categories):
            ax.text(angle, value + 5, f'{int(value)}', ha='center', va='center',
                   fontsize=10, fontweight='bold')
        
        ax.set_title('Conformità Principi WCAG (POUR)', fontsize=14, fontweight='bold', pad=20)
        
        return self._save_figure(fig, 'wcag_radar')
    
    def create_category_bar_chart(self, category_data: Dict[str, Any]) -> str:
        """
        Crea bar chart per problemi per categoria
        
        Args:
            category_data: Dati analisi per categoria
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if not category_data:
            ax.text(0.5, 0.5, 'Nessun dato disponibile', ha='center', va='center',
                   fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return self._save_figure(fig, 'category_bars')
        
        # Prepara dati
        categories = []
        critical_counts = []
        high_counts = []
        medium_counts = []
        
        for cat_name, cat_stats in category_data.items():
            categories.append(cat_name.capitalize())
            critical_counts.append(cat_stats.get('critical_count', 0))
            high_counts.append(cat_stats.get('high_count', 0))
            total = cat_stats.get('total_issues', 0)
            medium_counts.append(total - cat_stats.get('critical_count', 0) - cat_stats.get('high_count', 0))
        
        # Posizioni barre
        x = np.arange(len(categories))
        width = 0.6
        
        # Stacked bar chart
        p1 = ax.bar(x, critical_counts, width, label='Critici', color=self.COLORS['critical'])
        p2 = ax.bar(x, high_counts, width, bottom=critical_counts, label='Alti', color=self.COLORS['high'])
        p3 = ax.bar(x, medium_counts, width, bottom=np.array(critical_counts) + np.array(high_counts),
                   label='Medi/Bassi', color=self.COLORS['medium'])
        
        # Labels e styling
        ax.set_xlabel('Categoria', fontweight='bold')
        ax.set_ylabel('Numero Problemi', fontweight='bold')
        ax.set_title('Problemi per Categoria Funzionale', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3)
        
        # Aggiungi totali sopra le barre
        for i, (c, h, m) in enumerate(zip(critical_counts, high_counts, medium_counts)):
            total = c + h + m
            if total > 0:
                ax.text(i, total + 0.5, str(total), ha='center', fontweight='bold')
        
        plt.tight_layout()
        return self._save_figure(fig, 'category_bars')
    
    def create_scanner_comparison(self, scanner_data: Dict[str, Any]) -> str:
        """
        Crea grafico confronto scanner
        
        Args:
            scanner_data: Dati confronto scanner
            
        Returns:
            Path o base64 del grafico
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        scanner_performance = scanner_data.get('scanner_performance', {})
        
        if not scanner_performance:
            ax1.text(0.5, 0.5, 'Nessun dato scanner', ha='center', va='center',
                    fontsize=14, transform=ax1.transAxes)
            ax1.axis('off')
            ax2.axis('off')
            return self._save_figure(fig, 'scanner_comparison')
        
        # Grafico 1: Score per scanner
        scanners = list(scanner_performance.keys())
        scores = [data.get('score', 0) for data in scanner_performance.values()]
        
        bars1 = ax1.bar(scanners, scores, color=self.COLORS['primary'])
        ax1.set_xlabel('Scanner', fontweight='bold')
        ax1.set_ylabel('Score', fontweight='bold')
        ax1.set_title('Score per Scanner', fontsize=12, fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(axis='y', alpha=0.3)
        
        # Aggiungi valori sopra barre
        for bar, score in zip(bars1, scores):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{int(score)}', ha='center', fontweight='bold')
        
        # Grafico 2: Issues trovati per scanner
        issues_data = []
        for scanner in scanners:
            data = scanner_performance[scanner]
            issues_data.append([
                data.get('critical_found', 0),
                data.get('high_found', 0),
                data.get('total_issues', 0) - data.get('critical_found', 0) - data.get('high_found', 0)
            ])
        
        issues_data = np.array(issues_data).T
        
        x = np.arange(len(scanners))
        width = 0.25
        
        bars2_1 = ax2.bar(x - width, issues_data[0], width, label='Critici', color=self.COLORS['critical'])
        bars2_2 = ax2.bar(x, issues_data[1], width, label='Alti', color=self.COLORS['high'])
        bars2_3 = ax2.bar(x + width, issues_data[2], width, label='Altri', color=self.COLORS['medium'])
        
        ax2.set_xlabel('Scanner', fontweight='bold')
        ax2.set_ylabel('Numero Issues', fontweight='bold')
        ax2.set_title('Issues Trovati per Scanner', fontsize=12, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(scanners)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        plt.suptitle('Confronto Performance Scanner', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return self._save_figure(fig, 'scanner_comparison')
    
    def create_remediation_timeline(self, effort_data: Dict[str, Any]) -> str:
        """
        Crea timeline piano remediation
        
        Args:
            effort_data: Dati stima effort
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        priority_schedule = effort_data.get('priority_schedule', [])
        effort_breakdown = effort_data.get('effort_breakdown', {})
        
        if not priority_schedule:
            ax.text(0.5, 0.5, 'Nessun piano disponibile', ha='center', va='center',
                   fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return self._save_figure(fig, 'remediation_timeline')
        
        # Prepara dati timeline
        weeks = []
        activities = []
        colors = []
        
        color_map = {
            'Critici': self.COLORS['critical'],
            'Alta': self.COLORS['high'],
            'Media': self.COLORS['medium'],
            'Testing': self.COLORS['info']
        }
        
        for item in priority_schedule:
            weeks.append(f"Settimana {item['week']}")
            activities.append(item['focus'])
            
            # Determina colore
            for key, color in color_map.items():
                if key.lower() in item['focus'].lower():
                    colors.append(color)
                    break
            else:
                colors.append(self.COLORS['primary'])
        
        # Crea Gantt chart
        y_pos = np.arange(len(weeks))
        
        for i, (week, activity, color) in enumerate(zip(weeks, activities, colors)):
            ax.barh(i, 1, left=i, height=0.5, color=color, alpha=0.8, edgecolor='black', linewidth=1)
            ax.text(i + 0.5, i, activity, ha='center', va='center', fontweight='bold', fontsize=10)
        
        # Aggiungi milestone
        milestone_x = len(weeks)
        ax.scatter([milestone_x], [len(weeks)/2], s=200, marker='D', color=self.COLORS['success'],
                  edgecolor='black', linewidth=2, zorder=5)
        ax.text(milestone_x, len(weeks)/2 - 0.7, 'Conformità\nRaggiunta', ha='center', fontsize=10,
               fontweight='bold')
        
        # Styling
        ax.set_yticks(y_pos)
        ax.set_yticklabels(weeks)
        ax.set_xlabel('Timeline Progetto', fontweight='bold')
        ax.set_title('Piano di Remediation - Timeline', fontsize=14, fontweight='bold')
        ax.set_xlim(0, len(weeks) + 1)
        ax.grid(axis='x', alpha=0.3)
        
        # Aggiungi legenda effort
        total_hours = effort_data.get('total_hours', 0)
        estimated_weeks = effort_data.get('estimated_weeks', 0)
        
        info_text = f"Effort Totale: {int(total_hours)} ore | Durata: {estimated_weeks} settimane"
        ax.text(0.5, -0.15, info_text, transform=ax.transAxes, ha='center',
               fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        return self._save_figure(fig, 'remediation_timeline')
    
    def create_risk_matrix(self, risk_data: Dict[str, Any]) -> str:
        """
        Crea matrice di rischio
        
        Args:
            risk_data: Dati valutazione rischi
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Definisci matrice rischio
        risk_levels = ['BASSO', 'MEDIO', 'ALTO']
        impact_levels = ['Basso', 'Medio', 'Alto']
        probability_levels = ['Bassa', 'Media', 'Alta']
        
        # Colori per zone rischio
        risk_colors = [
            [self.COLORS['success'], self.COLORS['success'], self.COLORS['warning']],
            [self.COLORS['success'], self.COLORS['warning'], self.COLORS['danger']],
            [self.COLORS['warning'], self.COLORS['danger'], self.COLORS['danger']]
        ]
        
        # Disegna matrice
        for i in range(3):
            for j in range(3):
                rect = Rectangle((j, i), 1, 1, facecolor=risk_colors[i][j], 
                               edgecolor='white', linewidth=2, alpha=0.7)
                ax.add_patch(rect)
        
        # Posiziona rischi attuali
        risks = {
            'Legale': risk_data.get('legal_risk', {}).get('level', 'MEDIO'),
            'Reputazionale': risk_data.get('reputation_risk', {}).get('level', 'MEDIO')
        }
        
        positions = {
            'BASSO': (0.5, 0.5),
            'MEDIO': (1.5, 1.5),
            'MEDIO-ALTO': (2.0, 1.5),
            'ALTO': (2.5, 2.5)
        }
        
        markers = {'Legale': 'o', 'Reputazionale': 's'}
        
        for risk_type, level in risks.items():
            pos = positions.get(level, (1.5, 1.5))
            ax.scatter(pos[0], pos[1], s=500, marker=markers[risk_type],
                      color='white', edgecolor='black', linewidth=3, zorder=5,
                      label=f'Rischio {risk_type}')
            ax.text(pos[0], pos[1], risk_type[0], ha='center', va='center',
                   fontweight='bold', fontsize=12)
        
        # Labels
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 3)
        ax.set_xticks([0.5, 1.5, 2.5])
        ax.set_yticks([0.5, 1.5, 2.5])
        ax.set_xticklabels(probability_levels)
        ax.set_yticklabels(impact_levels)
        ax.set_xlabel('Probabilità', fontweight='bold', fontsize=12)
        ax.set_ylabel('Impatto', fontweight='bold', fontsize=12)
        ax.set_title('Matrice di Rischio Accessibilità', fontsize=14, fontweight='bold')
        
        # Legenda
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        
        # Grid
        ax.grid(True, linewidth=2, color='white')
        ax.set_axisbelow(False)
        
        plt.tight_layout()
        return self._save_figure(fig, 'risk_matrix')
    
    def create_benchmark_chart(self, benchmark_data: Dict[str, Any]) -> str:
        """
        Crea grafico confronto benchmark industria
        
        Args:
            benchmark_data: Dati benchmark
            
        Returns:
            Path o base64 del grafico
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        current_score = benchmark_data.get('current_score', 0)
        comparison = benchmark_data.get('comparison', {})
        
        if not comparison:
            ax.text(0.5, 0.5, 'Nessun dato benchmark', ha='center', va='center',
                   fontsize=14, transform=ax.transAxes)
            ax.axis('off')
            return self._save_figure(fig, 'benchmark')
        
        # Prepara dati
        sectors = list(comparison.keys())
        benchmarks = [data['benchmark'] for data in comparison.values()]
        
        # Bar chart orizzontale
        y_pos = np.arange(len(sectors))
        bars = ax.barh(y_pos, benchmarks, color=self.COLORS['secondary'], alpha=0.6, label='Media Settore')
        
        # Linea score attuale
        ax.axvline(x=current_score, color=self.COLORS['primary'], linewidth=3,
                  linestyle='--', label=f'Il Tuo Score ({current_score})')
        
        # Colora barre in base a performance
        for i, (sector, bar) in enumerate(zip(sectors, bars)):
            diff = comparison[sector]['difference']
            if diff > 0:
                bar.set_color(self.COLORS['success'])
                bar.set_alpha(0.7)
            elif diff < -10:
                bar.set_color(self.COLORS['danger'])
                bar.set_alpha(0.7)
        
        # Labels
        ax.set_yticks(y_pos)
        ax.set_yticklabels([s.capitalize() for s in sectors])
        ax.set_xlabel('Score Conformità', fontweight='bold')
        ax.set_title('Benchmark Industria', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.legend(loc='lower right')
        ax.grid(axis='x', alpha=0.3)
        
        # Aggiungi valori
        for i, (benchmark, sector) in enumerate(zip(benchmarks, sectors)):
            diff = comparison[sector]['difference']
            symbol = '+' if diff > 0 else ''
            ax.text(benchmark + 2, i, f'{benchmark}', va='center', fontweight='bold')
            ax.text(current_score + 2, i, f'({symbol}{diff})', va='center', fontsize=9,
                   color=self.COLORS['success'] if diff > 0 else self.COLORS['danger'])
        
        plt.tight_layout()
        return self._save_figure(fig, 'benchmark')
    
    # Metodi helper privati
    
    def _save_figure(self, fig: plt.Figure, name: str) -> str:
        """
        Salva figura come file o base64
        
        Args:
            fig: Figura matplotlib
            name: Nome del file
            
        Returns:
            Path del file o stringa base64
        """
        try:
            # Salva come file
            filepath = self.output_dir / f"{name}.png"
            fig.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            # Converti anche in base64 per embedding HTML
            buffer = BytesIO()
            fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor='white')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"Errore salvataggio grafico {name}: {e}")
            plt.close(fig)
            return ""
    
    def _get_level_color(self, level: str) -> str:
        """Ottiene colore per livello conformità"""
        if 'non' in level:
            return self.COLORS['danger']
        elif 'parzial' in level:
            return self.COLORS['warning']
        else:
            return self.COLORS['success']
    
    def _draw_score_card(self, ax: plt.Axes, summary: Dict) -> None:
        """Disegna card con score principale"""
        ax.axis('off')
        
        score = summary.get('compliance_score', 0)
        level = summary.get('compliance_level', 'non_conforme')
        status = summary.get('overall_status', '')
        
        # Background colorato
        color = self._get_level_color(level)
        rect = FancyBboxPatch((0.1, 0.2), 0.8, 0.6, boxstyle="round,pad=0.05",
                              facecolor=color, alpha=0.2, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        
        # Testi
        ax.text(0.5, 0.7, f'{score}', fontsize=48, fontweight='bold', ha='center', color=color)
        ax.text(0.5, 0.5, 'SCORE COMPLESSIVO', fontsize=12, ha='center')
        ax.text(0.5, 0.3, status, fontsize=10, ha='center', style='italic')
    
    def _draw_severity_distribution(self, ax: plt.Axes, quant_data: Dict) -> None:
        """Disegna distribuzione severità"""
        severity_breakdown = quant_data.get('severity_breakdown', {})
        
        severities = ['critical', 'high', 'medium', 'low']
        counts = [severity_breakdown.get(s, {}).get('count', 0) for s in severities]
        colors = [self.COLORS[s] for s in severities]
        
        bars = ax.bar(range(len(severities)), counts, color=colors)
        ax.set_xticks(range(len(severities)))
        ax.set_xticklabels(['Critici', 'Alti', 'Medi', 'Bassi'])
        ax.set_ylabel('Numero')
        ax.set_title('Distribuzione Severità', fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       str(count), ha='center', fontweight='bold')
    
    def _draw_wcag_bars(self, ax: plt.Axes, wcag_data: Dict) -> None:
        """Disegna barre principi WCAG"""
        principles = wcag_data.get('principle_distribution', {})
        
        categories = ['Percepibile', 'Operabile', 'Comprensibile', 'Robusto']
        errors = [principles.get(k, {}).get('errors', 0) 
                 for k in ['perceivable', 'operable', 'understandable', 'robust']]
        warnings = [principles.get(k, {}).get('warnings', 0)
                   for k in ['perceivable', 'operable', 'understandable', 'robust']]
        
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, errors, width, label='Errori', color=self.COLORS['danger'])
        bars2 = ax.bar(x + width/2, warnings, width, label='Avvisi', color=self.COLORS['warning'])
        
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=20, ha='right')
        ax.set_ylabel('Numero')
        ax.set_title('Principi WCAG (POUR)', fontsize=11, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    def _draw_trend_indicators(self, ax: plt.Axes, trend_data: Dict) -> None:
        """Disegna indicatori trend"""
        ax.axis('off')
        
        improvement = trend_data.get('improvement_potential', {})
        quick_wins = len(improvement.get('quick_wins', []))
        high_impact = len(improvement.get('high_impact_fixes', []))
        score_potential = improvement.get('estimated_score_improvement', 0)
        
        # Box per metriche
        metrics = [
            ('Quick Wins', quick_wins, self.COLORS['success']),
            ('High Impact', high_impact, self.COLORS['warning']),
            ('Score +', score_potential, self.COLORS['info'])
        ]
        
        for i, (label, value, color) in enumerate(metrics):
            y = 0.7 - i * 0.3
            rect = FancyBboxPatch((0.1, y), 0.8, 0.2, boxstyle="round,pad=0.02",
                                  facecolor=color, alpha=0.2, edgecolor=color)
            ax.add_patch(rect)
            ax.text(0.5, y + 0.1, f'{value}', fontsize=16, fontweight='bold', ha='center')
            ax.text(0.5, y + 0.03, label, fontsize=9, ha='center')
        
        ax.set_title('Potenziale Miglioramento', fontsize=11, fontweight='bold')
    
    def _draw_top_issues(self, ax: plt.Axes, wcag_data: Dict) -> None:
        """Disegna top issues"""
        most_violated = wcag_data.get('most_violated_criteria', [])[:5]
        
        if not most_violated:
            ax.text(0.5, 0.5, 'Nessun problema', ha='center', va='center')
            ax.axis('off')
            return
        
        criteria = [item['criteria'] for item in most_violated]
        violations = [item['violations'] for item in most_violated]
        
        bars = ax.barh(range(len(criteria)), violations, color=self.COLORS['danger'])
        ax.set_yticks(range(len(criteria)))
        ax.set_yticklabels([f"WCAG {c}" for c in criteria])
        ax.set_xlabel('Violazioni')
        ax.set_title('Top 5 Criteri WCAG Violati', fontsize=11, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        for i, (bar, val) in enumerate(zip(bars, violations)):
            ax.text(val + 0.1, i, str(val), va='center', fontweight='bold')
    
    def _draw_effort_summary(self, ax: plt.Axes, effort_data: Dict) -> None:
        """Disegna sommario effort"""
        ax.axis('off')
        
        total_hours = effort_data.get('total_hours', 0)
        total_days = effort_data.get('estimated_days', 0)
        total_cost = effort_data.get('estimated_cost_eur', 0)
        
        # Metriche chiave
        ax.text(0.5, 0.8, f'{int(total_hours)}', fontsize=24, fontweight='bold', ha='center',
               color=self.COLORS['primary'])
        ax.text(0.5, 0.65, 'ORE TOTALI', fontsize=10, ha='center')
        
        ax.text(0.5, 0.45, f'{total_days:.1f} giorni', fontsize=14, ha='center')
        ax.text(0.5, 0.3, f'€ {total_cost:,.0f}', fontsize=14, ha='center', 
               color=self.COLORS['warning'])
        
        ax.set_title('Stima Effort Remediation', fontsize=11, fontweight='bold')