# [FILE: ras_monitor/core/report_export.py]
"""
Report export module for RAS monitoring system.
Generates CSV reports for specified date ranges.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.db import Database


class ReportExporter:
    """Export measurement history to CSV reports."""
    
    def __init__(self, db_path: str = "ras_monitor.db"):
        self.db = Database(db_path)
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
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
    
    def export_to_csv(
        self,
        start_date: datetime,
        end_date: datetime,
        filename: Optional[str] = None
    ) -> str:
        """
        Export data for period to CSV file.
        
        Args:
            start_date: Start of period
            end_date: End of period
            filename: Optional custom filename (default: auto-generated)
            
        Returns:
            Path to generated CSV file
            
        Raises:
            ValueError: If no data found for period
        """
        data = self.get_data_for_period(start_date, end_date)
        
        if not data:
            raise ValueError(f"No data found for period {start_date} to {end_date}")
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"report_{timestamp}.csv"
        
        filepath = self.reports_dir / filename
        
        # Define CSV columns as per requirements
        fieldnames = [
            'timestamp', 'temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity',
            'state', 'suitability', 'dynamics', 'forecast_state', 'forecast_confidence'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for row in data:
                # Format numeric values
                formatted_row = {
                    'timestamp': row.get('timestamp', ''),
                    'temp': f"{row.get('temp', 0):.2f}",
                    'ph': f"{row.get('ph', 0):.2f}",
                    'o2': f"{row.get('o2', 0):.1f}",
                    'ammonia': f"{row.get('ammonia', 0):.3f}",
                    'nitrite': f"{row.get('nitrite', 0):.3f}",
                    'salinity': f"{row.get('salinity', 0):.2f}",
                    'state': row.get('state', 0),
                    'suitability': row.get('suitability', ''),
                    'dynamics': row.get('dynamics', ''),
                    'forecast_state': row.get('forecast_state') or '',
                    'forecast_confidence': f"{row.get('forecast_confidence', 0):.2f}" if row.get('forecast_confidence') else ''
                }
                writer.writerow(formatted_row)
        
        return str(filepath)
    
    def close(self):
        """Close database connection."""
        self.db.close()
