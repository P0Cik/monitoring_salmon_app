# [FILE: ras_monitor/core/report_export.py]
"""
Report export module for RAS monitoring system.
Generates PDF reports with charts and tables for specified date ranges.
"""

import io
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.db import Database
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
import base64


class ReportExporter:
    """Export measurement history to PDF reports with charts and tables."""
    
    def __init__(self, db_path: str = "ras_monitor.db"):
        self.db = Database(db_path)
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Unified color scheme
        self.colors = {
            'primary': '#2A2A35',
            'secondary': '#3A3A45',
            'accent': '#4CAF50',
            'temp': '#E74C3C',
            'ph': '#3498DB',
            'o2': '#2ECC71',
            'ammonia': '#F39C12',
            'nitrite': '#9B59B6',
            'salinity': '#1ABC9C',
        }
    
    def get_data_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get all measurements and history for a given period.
        
        Args:
            start_date: Start of period (inclusive)
            end_date: End of period (inclusive)
            
        Returns:
            List of combined measurement and history records
        """
        cursor = self.db.conn.cursor()
        
        # Query joined data with timestamp filtering
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        cursor.execute("""
            SELECT 
                m.timestamp, m.temp, m.ph, m.o2, m.ammonia, m.nitrite, m.salinity,
                h.current_state as state, h.suitability, h.past_dynamics as dynamics,
                h.forecast_dynamics as forecast_state, h.forecast_confidence
            FROM measurements m
            JOIN history h ON m.id = h.measurement_id
            WHERE m.timestamp >= ? AND m.timestamp <= ?
            ORDER BY m.timestamp ASC
        """, (start_str, end_str))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            results.append(record)
        
        return results
    
    def _create_chart_image(self, data: List[Dict], param: str, color: str, title: str) -> bytes:
        """Create a matplotlib chart and return as PNG bytes."""
        fig = Figure(figsize=(10, 4), dpi=100, facecolor='#2A2A35')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#2A2A35')
        
        # Extract data
        timestamps = []
        values = []
        for record in data:
            ts = record.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    timestamps.append(dt)
                except:
                    timestamps.append(ts[:16])
            values.append(record.get(param, 0))
        
        if not values:
            ax.text(0.5, 0.5, "Нет данных", transform=ax.transAxes,
                    ha='center', va='center', fontsize=14, color='#888888')
        else:
            x_range = range(len(values))
            ax.plot(x_range, values, color=color, linewidth=2, marker='o', markersize=4)
            ax.fill_between(x_range, values, alpha=0.3, color=color)
            
            ax.set_title(title, fontsize=12, weight='bold', color='#E0E0E0')
            ax.grid(True, alpha=0.2, linestyle='--', color='#3A3A45')
            ax.tick_params(colors='#AAAAAA', labelsize=9)
            
            for spine in ax.spines.values():
                spine.set_color('#3A3A45')
        
        # Save to bytes buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)
        plt = None
        return buf.getvalue()
    
    def _chart_to_image(self, chart_bytes: bytes) -> Image:
        """Convert chart bytes to ReportLab Image."""
        from reportlab.platypus import Image as RLImage
        buf = io.BytesIO(chart_bytes)
        img = RLImage(buf, width=9*inch, height=3.5*inch)
        return img
    
    def export_to_pdf(
        self,
        start_date: datetime,
        end_date: datetime,
        filename: Optional[str] = None
    ) -> str:
        """
        Export data for period to PDF file with charts and table.
        
        Args:
            start_date: Start of period
            end_date: End of period
            filename: Optional custom filename (default: auto-generated)
            
        Returns:
            Path to generated PDF file
            
        Raises:
            ValueError: If no data found for period
        """
        data = self.get_data_for_period(start_date, end_date)
        
        if not data:
            raise ValueError(f"No data found for period {start_date} to {end_date}")
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"report_{timestamp}.pdf"
        
        filepath = self.reports_dir / filename
        
        # Create PDF document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=landscape(A4),
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor(self.colors['primary']),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        # Title
        elements.append(Paragraph("Отчёт мониторинга водной среды УЗВ", title_style))
        period_text = f"Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        elements.append(Paragraph(period_text, subtitle_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Charts section
        chart_configs = [
            ('temp', self.colors['temp'], 'Температура (°C)'),
            ('ph', self.colors['ph'], 'pH'),
            ('o2', self.colors['o2'], 'Кислород (O₂, %)'),
            ('ammonia', self.colors['ammonia'], 'Аммиак (NH₃, мг/л)'),
            ('nitrite', self.colors['nitrite'], 'Нитриты (NO₂, мг/л)'),
            ('salinity', self.colors['salinity'], 'Солёность (‰)'),
        ]
        
        elements.append(Paragraph("Графики параметров", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        for param, color, title in chart_configs:
            chart_bytes = self._create_chart_image(data, param, color, title)
            chart_img = self._chart_to_image(chart_bytes)
            elements.append(chart_img)
            elements.append(Spacer(1, 0.3*inch))
        
        # Data table
        elements.append(Paragraph("Таблица замеров", styles['Heading2']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Table headers
        table_data = [['Время', 'Temp', 'pH', 'O₂', 'NH₃', 'NO₂', 'Sal', 'Состояние', 'Пригодность']]
        
        for record in data:
            ts = record.get('timestamp', '')[:16].replace('T', ' ') if record.get('timestamp') else ''
            row = [
                ts,
                f"{record.get('temp', 0):.2f}",
                f"{record.get('ph', 0):.2f}",
                f"{record.get('o2', 0):.1f}",
                f"{record.get('ammonia', 0):.3f}",
                f"{record.get('nitrite', 0):.3f}",
                f"{record.get('salinity', 0):.2f}",
                str(record.get('state', 0)),
                record.get('suitability', '')
            ]
            table_data.append(row)
        
        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.colors['primary'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Row styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5F5')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        
        return str(filepath)
    
    def close(self):
        """Close database connection."""
        self.db.close()
