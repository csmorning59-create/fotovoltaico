"""
Modulo per la generazione di report PDF professionali per studi di fattibilità fotovoltaici
"""

import os
import json
import matplotlib
matplotlib.use('Agg')  # Backend non-interattivo per server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
import io
import base64
from typing import Dict, List, Optional, Tuple

class ReportGenerator:
    """Generatore di report PDF professionali per studi di fattibilità fotovoltaici"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
        # Configurazione matplotlib per grafici professionali
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")
        
        # Colori aziendali
        self.colors = {
            'primary': '#4F46E5',      # Indigo
            'secondary': '#10B981',    # Emerald
            'accent': '#F59E0B',       # Amber
            'danger': '#EF4444',       # Red
            'success': '#22C55E',      # Green
            'warning': '#F97316',      # Orange
            'info': '#3B82F6',         # Blue
            'dark': '#1F2937',         # Gray-800
            'light': '#F9FAFB'         # Gray-50
        }
    
    def setup_custom_styles(self):
        """Configura stili personalizzati per il report"""
        
        # Stile titolo principale
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1F2937'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Stile sottotitolo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#4F46E5'),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Stile sezione
        self.styles.add(ParagraphStyle(
            name='CustomSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#1F2937'),
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Stile testo normale
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.HexColor('#374151'),
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Stile KPI
        self.styles.add(ParagraphStyle(
            name='KPIValue',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#10B981'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Stile KPI Label
        self.styles.add(ParagraphStyle(
            name='KPILabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6B7280'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
    
    def create_production_chart(self, pvgis_data: Dict, save_path: str) -> str:
        """Crea grafico della produzione mensile"""
        
        # Estrai dati mensili
        monthly_data = pvgis_data.get('monthly_data', [])
        if not monthly_data:
            return None
        
        months = [item['month'] for item in monthly_data]
        production = [item['production_kwh'] for item in monthly_data]
        
        # Nomi mesi in italiano
        month_names = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                      'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        
        # Crea il grafico
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Barre con gradiente di colore
        bars = ax.bar(month_names, production, 
                     color=plt.cm.viridis(np.linspace(0.3, 0.9, 12)),
                     edgecolor='white', linewidth=1.5)
        
        # Personalizzazione
        ax.set_title('Produzione Mensile Fotovoltaico', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel('Produzione (kWh)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Mese', fontsize=12, fontweight='bold')
        
        # Aggiungi valori sopra le barre
        for bar, value in zip(bars, production):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(production)*0.01,
                   f'{value:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        # Griglia e stile
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Salva il grafico
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return save_path
    
    def create_economic_chart(self, economic_data: Dict, save_path: str) -> str:
        """Crea grafico dell'analisi economica"""
        
        pv_results = economic_data.get('pv_only_results', {})
        combined_results = economic_data.get('combined_results', {})
        
        # Dati per il grafico
        scenarios = ['FV Solo', 'FV + BESS']
        npv_values = [
            pv_results.get('npv', 0),
            combined_results.get('npv', 0) if combined_results else 0
        ]
        irr_values = [
            pv_results.get('irr', 0) * 100,
            combined_results.get('irr', 0) * 100 if combined_results else 0
        ]
        payback_values = [
            pv_results.get('payback_years', 0),
            combined_results.get('payback_years', 0) if combined_results else 0
        ]
        
        # Crea subplot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        
        # Grafico NPV
        colors_npv = ['#10B981' if v > 0 else '#EF4444' for v in npv_values]
        bars1 = ax1.bar(scenarios, npv_values, color=colors_npv, alpha=0.8)
        ax1.set_title('Valore Attuale Netto (NPV)', fontweight='bold')
        ax1.set_ylabel('NPV (€)')
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        for bar, value in zip(bars1, npv_values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + (max(npv_values)*0.05 if height > 0 else min(npv_values)*0.05),
                    f'€{value:,.0f}', ha='center', va='bottom' if height > 0 else 'top', fontweight='bold')
        
        # Grafico IRR
        bars2 = ax2.bar(scenarios, irr_values, color=['#3B82F6', '#8B5CF6'], alpha=0.8)
        ax2.set_title('Tasso Interno di Rendimento (IRR)', fontweight='bold')
        ax2.set_ylabel('IRR (%)')
        for bar, value in zip(bars2, irr_values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(irr_values)*0.02,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Grafico Payback
        bars3 = ax3.bar(scenarios, payback_values, color=['#F59E0B', '#F97316'], alpha=0.8)
        ax3.set_title('Periodo di Ritorno (Payback)', fontweight='bold')
        ax3.set_ylabel('Anni')
        for bar, value in zip(bars3, payback_values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + max(payback_values)*0.02,
                    f'{value:.1f} anni', ha='center', va='bottom', fontweight='bold')
        
        # Grafico a torta investimenti
        if combined_results:
            pv_investment = pv_results.get('total_investment', 0)
            bess_investment = combined_results.get('total_investment', 0) - pv_investment
            
            if bess_investment > 0:
                investments = [pv_investment, bess_investment]
                labels = ['Fotovoltaico', 'BESS']
                colors_pie = ['#10B981', '#F59E0B']
                
                wedges, texts, autotexts = ax4.pie(investments, labels=labels, colors=colors_pie, 
                                                  autopct='%1.1f%%', startangle=90)
                ax4.set_title('Ripartizione Investimento', fontweight='bold')
                
                # Migliora la leggibilità
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
        else:
            ax4.text(0.5, 0.5, 'Solo Fotovoltaico', ha='center', va='center', 
                    transform=ax4.transAxes, fontsize=14, fontweight='bold')
            ax4.set_xlim(0, 1)
            ax4.set_ylim(0, 1)
            ax4.axis('off')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return save_path
    
    def create_layout_diagram(self, geometry_data: Dict, save_path: str) -> str:
        """Crea diagramma del layout fotovoltaico"""
        
        # Estrai dati geometrici
        superficie_mq = geometry_data.get('superficie_lorda_mq', 2500)
        num_moduli = geometry_data.get('numero_moduli', 0)
        num_file = geometry_data.get('numero_file', 0)
        moduli_per_fila = geometry_data.get('moduli_per_fila', 0)
        
        if num_file == 0 or moduli_per_fila == 0:
            return None
        
        # Crea il diagramma
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Dimensioni approssimative (assumendo rettangolo)
        lato = np.sqrt(superficie_mq)
        
        # Disegna il perimetro del sito
        site_rect = Rectangle((0, 0), lato, lato, 
                             linewidth=3, edgecolor='black', 
                             facecolor='lightgray', alpha=0.3)
        ax.add_patch(site_rect)
        
        # Calcola dimensioni moduli (approssimate)
        modulo_width = lato / (moduli_per_fila + 1)
        modulo_height = lato / (num_file + 2)
        
        # Disegna i moduli
        for fila in range(num_file):
            for modulo in range(moduli_per_fila):
                x = (modulo + 0.5) * modulo_width
                y = (fila + 1) * modulo_height
                
                module_rect = Rectangle((x, y), modulo_width * 0.8, modulo_height * 0.6,
                                      linewidth=1, edgecolor='blue', 
                                      facecolor='darkblue', alpha=0.7)
                ax.add_patch(module_rect)
        
        # Personalizzazione
        ax.set_xlim(-lato*0.1, lato*1.1)
        ax.set_ylim(-lato*0.1, lato*1.1)
        ax.set_aspect('equal')
        ax.set_title(f'Layout Fotovoltaico - {num_moduli} Moduli ({num_file} file x {moduli_per_fila} moduli)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Aggiungi annotazioni
        ax.text(lato/2, -lato*0.05, f'Superficie: {superficie_mq:,.0f} m²', 
               ha='center', va='top', fontsize=12, fontweight='bold')
        
        # Rimuovi assi
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Aggiungi legenda
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='lightgray', alpha=0.3, label='Area disponibile'),
            Patch(facecolor='darkblue', alpha=0.7, label='Moduli fotovoltaici')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return save_path
    
    def generate_report(self, project_data: Dict, output_path: str) -> str:
        """Genera il report PDF completo"""
        
        # Crea directory per i grafici temporanei
        charts_dir = os.path.join(os.path.dirname(output_path), 'temp_charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # Genera grafici
        charts = {}
        
        # Grafico produzione mensile
        if project_data.get('pvgis_data'):
            production_chart = os.path.join(charts_dir, 'production_chart.png')
            if self.create_production_chart(project_data['pvgis_data'], production_chart):
                charts['production'] = production_chart
        
        # Grafico analisi economica
        if project_data.get('economic_data'):
            economic_chart = os.path.join(charts_dir, 'economic_chart.png')
            if self.create_economic_chart(project_data['economic_data'], economic_chart):
                charts['economic'] = economic_chart
        
        # Diagramma layout
        if project_data.get('geometry_data'):
            layout_chart = os.path.join(charts_dir, 'layout_diagram.png')
            if self.create_layout_diagram(project_data['geometry_data'], layout_chart):
                charts['layout'] = layout_chart
        
        # Crea il documento PDF
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        story = []
        
        # Titolo principale
        story.append(Paragraph("Studio di Fattibilità Impianto Fotovoltaico", 
                              self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Informazioni progetto
        story.append(Paragraph("Informazioni Generali", self.styles['CustomSubtitle']))
        
        project_info = [
            ['Nome Progetto:', project_data.get('name', 'N/A')],
            ['Indirizzo:', project_data.get('address', 'N/A')],
            ['Superficie:', f"{project_data.get('superficie_lorda_mq', 0):,.0f} m²"],
            ['Data Studio:', datetime.now().strftime('%d/%m/%Y')],
            ['Stato:', project_data.get('status', 'N/A').title()]
        ]
        
        info_table = Table(project_info, colWidths=[4*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 30))
        
        # KPI Riassuntivi
        story.append(Paragraph("Key Performance Indicators", self.styles['CustomSubtitle']))
        
        # Estrai KPI principali
        geometry_data = project_data.get('geometry_data', {})
        pvgis_data = project_data.get('pvgis_data', {})
        economic_data = project_data.get('economic_data', {})
        
        potenza_kwp = geometry_data.get('potenza_installabile_kwp', 0)
        produzione_kwh = pvgis_data.get('produzione_annuale_kwh', 0)
        produzione_specifica = pvgis_data.get('produzione_specifica_kwh_kwp', 0)
        
        pv_results = economic_data.get('pv_only_results', {})
        npv = pv_results.get('npv', 0)
        irr = pv_results.get('irr', 0) * 100
        payback = pv_results.get('payback_years', 0)
        lcoe = pv_results.get('lcoe_eur_mwh', 0)
        
        kpi_data = [
            [
                Paragraph(f"{potenza_kwp:.1f}", self.styles['KPIValue']),
                Paragraph(f"{produzione_kwh:,.0f}", self.styles['KPIValue']),
                Paragraph(f"{produzione_specifica:.0f}", self.styles['KPIValue']),
                Paragraph(f"€{npv:,.0f}", self.styles['KPIValue'])
            ],
            [
                Paragraph("kWp Installabili", self.styles['KPILabel']),
                Paragraph("kWh/anno", self.styles['KPILabel']),
                Paragraph("kWh/kWp", self.styles['KPILabel']),
                Paragraph("NPV", self.styles['KPILabel'])
            ],
            [
                Paragraph(f"{irr:.1f}%", self.styles['KPIValue']),
                Paragraph(f"{payback:.1f}", self.styles['KPIValue']),
                Paragraph(f"€{lcoe:.0f}", self.styles['KPIValue']),
                Paragraph(f"{geometry_data.get('fattore_riempimento_percent', 0):.1f}%", self.styles['KPIValue'])
            ],
            [
                Paragraph("IRR", self.styles['KPILabel']),
                Paragraph("Payback (anni)", self.styles['KPILabel']),
                Paragraph("LCOE (€/MWh)", self.styles['KPILabel']),
                Paragraph("Fattore Riempimento", self.styles['KPILabel'])
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#EFF6FF')),
            ('BACKGROUND', (0, 2), (-1, 3), colors.HexColor('#F0FDF4')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
        ]))
        
        story.append(kpi_table)
        story.append(PageBreak())
        
        # Sezione Analisi Tecnica
        story.append(Paragraph("Analisi Tecnica", self.styles['CustomSubtitle']))
        
        # Layout fotovoltaico
        if 'layout' in charts:
            story.append(Paragraph("Layout Impianto", self.styles['CustomSection']))
            story.append(Image(charts['layout'], width=15*cm, height=10*cm))
            story.append(Spacer(1, 20))
        
        # Dettagli tecnici
        if geometry_data:
            story.append(Paragraph("Specifiche Tecniche", self.styles['CustomSection']))
            
            tech_data = [
                ['Parametro', 'Valore', 'Unità'],
                ['Potenza Installabile', f"{potenza_kwp:.1f}", 'kWp'],
                ['Numero Moduli', f"{geometry_data.get('numero_moduli', 0):,}", 'pz'],
                ['Numero File', f"{geometry_data.get('numero_file', 0)}", 'pz'],
                ['Moduli per Fila', f"{geometry_data.get('moduli_per_fila', 0)}", 'pz'],
                ['Fattore di Riempimento', f"{geometry_data.get('fattore_riempimento_percent', 0):.1f}", '%'],
                ['Orientamento', geometry_data.get('orientamento', 'N/A'), ''],
                ['Inclinazione', f"{geometry_data.get('inclinazione_gradi', 0):.0f}", '°'],
                ['Azimuth', f"{geometry_data.get('azimuth_gradi', 0):.0f}", '°']
            ]
            
            tech_table = Table(tech_data, colWidths=[6*cm, 4*cm, 3*cm])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
            ]))
            
            story.append(tech_table)
            story.append(Spacer(1, 20))
        
        # Produzione energetica
        if 'production' in charts:
            story.append(Paragraph("Produzione Energetica", self.styles['CustomSection']))
            story.append(Image(charts['production'], width=16*cm, height=8*cm))
            story.append(Spacer(1, 20))
        
        # Dati PVGIS
        if pvgis_data:
            story.append(Paragraph("Dati di Irraggiamento (PVGIS)", self.styles['CustomSection']))
            
            pvgis_info = [
                ['Parametro', 'Valore'],
                ['Produzione Annuale', f"{produzione_kwh:,.0f} kWh"],
                ['Produzione Specifica', f"{produzione_specifica:.0f} kWh/kWp"],
                ['Performance Ratio', f"{pvgis_data.get('performance_ratio', 0):.1f}%"],
                ['Irraggiamento Annuale', f"{pvgis_data.get('irraggiamento_annuale_kwh_mq', 0):.0f} kWh/m²"],
                ['Coordinate', f"{pvgis_data.get('latitude', 0):.4f}°N, {pvgis_data.get('longitude', 0):.4f}°E"],
                ['Elevazione', f"{pvgis_data.get('elevation_m', 0):.0f} m s.l.m."],
                ['Database', pvgis_data.get('database', 'PVGIS-SARAH2')],
                ['Periodo Dati', pvgis_data.get('data_period', '2005-2020')]
            ]
            
            pvgis_table = Table(pvgis_info, colWidths=[8*cm, 6*cm])
            pvgis_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#FEF3C7')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#FFFBEB')])
            ]))
            
            story.append(pvgis_table)
            story.append(PageBreak())
        
        # Sezione Analisi Economica
        story.append(Paragraph("Analisi Economica", self.styles['CustomSubtitle']))
        
        if 'economic' in charts:
            story.append(Image(charts['economic'], width=16*cm, height=12*cm))
            story.append(Spacer(1, 20))
        
        # Dettagli economici
        if economic_data and pv_results:
            story.append(Paragraph("Dettagli Finanziari", self.styles['CustomSection']))
            
            economic_details = [
                ['Parametro', 'FV Solo', 'FV + BESS'],
                ['Investimento Totale', f"€{pv_results.get('total_investment', 0):,.0f}", 
                 f"€{economic_data.get('combined_results', {}).get('total_investment', 0):,.0f}" if economic_data.get('combined_results') else 'N/A'],
                ['NPV (20 anni)', f"€{npv:,.0f}", 
                 f"€{economic_data.get('combined_results', {}).get('npv', 0):,.0f}" if economic_data.get('combined_results') else 'N/A'],
                ['IRR', f"{irr:.1f}%", 
                 f"{economic_data.get('combined_results', {}).get('irr', 0)*100:.1f}%" if economic_data.get('combined_results') else 'N/A'],
                ['Payback Period', f"{payback:.1f} anni", 
                 f"{economic_data.get('combined_results', {}).get('payback_years', 0):.1f} anni" if economic_data.get('combined_results') else 'N/A'],
                ['LCOE', f"€{lcoe:.0f}/MWh", 
                 f"€{economic_data.get('combined_results', {}).get('lcoe_eur_mwh', 0):.0f}/MWh" if economic_data.get('combined_results') else 'N/A'],
                ['Risparmio Annuale', f"€{pv_results.get('annual_savings', 0):,.0f}", 
                 f"€{economic_data.get('combined_results', {}).get('annual_savings', 0):,.0f}" if economic_data.get('combined_results') else 'N/A']
            ]
            
            econ_table = Table(economic_details, colWidths=[6*cm, 4*cm, 4*cm])
            econ_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDF4')])
            ]))
            
            story.append(econ_table)
            story.append(Spacer(1, 20))
        
        # Parametri utilizzati
        story.append(Paragraph("Parametri di Calcolo", self.styles['CustomSection']))
        
        params_text = f"""
        <b>WACC (Costo del Capitale):</b> {economic_data.get('parameters', {}).get('wacc_percent', 6):.1f}%<br/>
        <b>CAPEX Fotovoltaico:</b> €{economic_data.get('parameters', {}).get('pv_capex_eur_kwp', 1200):,.0f}/kWp<br/>
        <b>OPEX Fotovoltaico:</b> €{economic_data.get('parameters', {}).get('pv_opex_eur_kwp_year', 15):,.0f}/kWp/anno<br/>
        <b>Prezzo Energia F1:</b> €{economic_data.get('parameters', {}).get('energy_price_f1_eur_kwh', 0.25):.3f}/kWh<br/>
        <b>Prezzo Energia F2:</b> €{economic_data.get('parameters', {}).get('energy_price_f2_eur_kwh', 0.20):.3f}/kWh<br/>
        <b>Prezzo Energia F3:</b> €{economic_data.get('parameters', {}).get('energy_price_f3_eur_kwh', 0.15):.3f}/kWh<br/>
        <b>Vita Utile Impianto:</b> {economic_data.get('parameters', {}).get('project_lifetime_years', 20)} anni<br/>
        <b>Degradazione Annuale:</b> {economic_data.get('parameters', {}).get('degradation_percent_year', 0.5):.1f}%/anno
        """
        
        story.append(Paragraph(params_text, self.styles['CustomNormal']))
        story.append(Spacer(1, 20))
        
        # Note e disclaimer
        story.append(Paragraph("Note e Disclaimer", self.styles['CustomSection']))
        
        disclaimer_text = """
        Questo studio di fattibilità è stato generato automaticamente utilizzando dati di irraggiamento PVGIS 
        (Photovoltaic Geographical Information System) del Joint Research Centre della Commissione Europea. 
        I calcoli economici sono basati su parametri standard di mercato e possono variare in base alle 
        condizioni specifiche del sito e agli accordi commerciali. Si raccomanda una verifica tecnica 
        dettagliata prima dell'implementazione del progetto.
        
        <b>Fonte Dati Irraggiamento:</b> PVGIS © European Union, 2001-2023<br/>
        <b>Data Generazione Report:</b> {}<br/>
        <b>Versione Software:</b> Studio di Fattibilità Fotovoltaico v1.0
        """.format(datetime.now().strftime('%d/%m/%Y %H:%M'))
        
        story.append(Paragraph(disclaimer_text, self.styles['CustomNormal']))
        
        # Genera il PDF
        doc.build(story)
        
        # Pulisci i file temporanei
        for chart_path in charts.values():
            if os.path.exists(chart_path):
                os.remove(chart_path)
        
        if os.path.exists(charts_dir):
            os.rmdir(charts_dir)
        
        return output_path


# Test del modulo
if __name__ == "__main__":
    # Dati di test
    test_data = {
        'name': 'Impianto Test - Capannone Industriale',
        'address': 'Via Roma 123, Milano, MI',
        'superficie_lorda_mq': 2500,
        'status': 'completato',
        'geometry_data': {
            'potenza_installabile_kwp': 228.7,
            'numero_moduli': 462,
            'numero_file': 11,
            'moduli_per_fila': 42,
            'fattore_riempimento_percent': 91.5,
            'orientamento': 'Sud',
            'inclinazione_gradi': 30,
            'azimuth_gradi': 180
        },
        'pvgis_data': {
            'produzione_annuale_kwh': 164830,
            'produzione_specifica_kwh_kwp': 721,
            'performance_ratio': 100.0,
            'irraggiamento_annuale_kwh_mq': 979,
            'latitude': 45.4642,
            'longitude': 9.1900,
            'elevation_m': 131,
            'database': 'PVGIS-SARAH2',
            'data_period': '2005-2020',
            'monthly_data': [
                {'month': 1, 'production_kwh': 3132},
                {'month': 2, 'production_kwh': 4101},
                {'month': 3, 'production_kwh': 9481},
                {'month': 4, 'production_kwh': 17650},
                {'month': 5, 'production_kwh': 25538},
                {'month': 6, 'production_kwh': 29065},
                {'month': 7, 'production_kwh': 29809},
                {'month': 8, 'production_kwh': 21846},
                {'month': 9, 'production_kwh': 12391},
                {'month': 10, 'production_kwh': 5654},
                {'month': 11, 'production_kwh': 3395},
                {'month': 12, 'production_kwh': 2767}
            ]
        },
        'economic_data': {
            'pv_only_results': {
                'total_investment': 274440,
                'npv': 113823,
                'irr': 0.104,
                'payback_years': 8.8,
                'lcoe_eur_mwh': 174,
                'annual_savings': 36966
            },
            'parameters': {
                'wacc_percent': 6.0,
                'pv_capex_eur_kwp': 1200,
                'pv_opex_eur_kwp_year': 15,
                'energy_price_f1_eur_kwh': 0.25,
                'energy_price_f2_eur_kwh': 0.20,
                'energy_price_f3_eur_kwh': 0.15,
                'project_lifetime_years': 20,
                'degradation_percent_year': 0.5
            }
        }
    }
    
    # Test generazione report
    generator = ReportGenerator()
    output_file = '/tmp/test_report.pdf'
    
    print("=== TEST REPORT GENERATOR ===")
    try:
        result = generator.generate_report(test_data, output_file)
        print(f"Report generato con successo: {result}")
        print(f"Dimensione file: {os.path.getsize(result) / 1024:.1f} KB")
    except Exception as e:
        print(f"Errore nella generazione: {e}")
        import traceback
        traceback.print_exc()

