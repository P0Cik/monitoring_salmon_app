# [FILE: ras_monitor/core/db.py]
"""
Database module for RAS monitoring system.
Handles SQLite CRUD operations for measurements, history, and configuration.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """
    SQLite database handler for RAS monitoring data.
    
    Tables:
    - measurements: id, timestamp, temp, ph, o2, ammonia, nitrite, salinity
    - history: id, measurement_id, current_state, suitability, past_dynamics, 
               forecast_dynamics, forecast_confidence
    """
    
    def __init__(self, db_path: str = "ras_monitor.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()
    
    def _connect(self) -> None:
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
    
    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Measurements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temp REAL NOT NULL,
                ph REAL NOT NULL,
                o2 REAL NOT NULL,
                ammonia REAL NOT NULL,
                nitrite REAL NOT NULL,
                salinity REAL NOT NULL
            )
        """)
        
        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER NOT NULL,
                current_state INTEGER NOT NULL,
                suitability TEXT NOT NULL,
                past_dynamics TEXT NOT NULL,
                forecast_dynamics TEXT,
                forecast_confidence REAL,
                FOREIGN KEY (measurement_id) REFERENCES measurements(id)
            )
        """)
        
        self.conn.commit()
    
    def add_measurement(
        self,
        temp: float,
        ph: float,
        o2: float,
        ammonia: float,
        nitrite: float,
        salinity: float,
        timestamp: Optional[str] = None
    ) -> int:
        """
        Add a new measurement to the database.
        
        Args:
            temp: Temperature (°C)
            ph: pH level
            o2: Dissolved oxygen (%)
            ammonia: Ammonia concentration (mg/L)
            nitrite: Nitrite concentration (mg/L)
            salinity: Salinity (‰)
            timestamp: ISO format timestamp (default: current time)
            
        Returns:
            ID of the inserted measurement
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO measurements (timestamp, temp, ph, o2, ammonia, nitrite, salinity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, temp, ph, o2, ammonia, nitrite, salinity))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def add_history(
        self,
        measurement_id: int,
        current_state: int,
        suitability: str,
        past_dynamics: str,
        forecast_dynamics: Optional[str] = None,
        forecast_confidence: Optional[float] = None
    ) -> int:
        """
        Add history record for a measurement.
        
        Args:
            measurement_id: Reference to measurements.id
            current_state: Current state (0-4)
            suitability: "пригодна" or "непригодна"
            past_dynamics: "Стабильно", "Ухудшение", or "Улучшение"
            forecast_dynamics: Predicted dynamics
            forecast_confidence: Confidence score for forecast
            
        Returns:
            ID of the inserted history record
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO history (measurement_id, current_state, suitability, 
                                past_dynamics, forecast_dynamics, forecast_confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (measurement_id, current_state, suitability, past_dynamics,
              forecast_dynamics, forecast_confidence))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_last_measurement(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent measurement.
        
        Returns:
            Dictionary with measurement data or None if no measurements exist
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return dict(row)
    
    def get_last_state(self) -> Optional[int]:
        """
        Get the state from the most recent history record.
        
        Returns:
            Current state (0-4) or None if no history exists
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT current_state FROM history ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return row['current_state']
    
    def get_measurements(
        self, 
        limit: int = 100,
        order: str = "ASC"
    ) -> List[Dict[str, Any]]:
        """
        Get measurements with optional limit and ordering.
        
        Args:
            limit: Maximum number of records to return
            order: "ASC" or "DESC" for timestamp ordering
            
        Returns:
            List of measurement dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT * FROM measurements ORDER BY timestamp {order} LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_history_with_measurements(
        self, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get history records joined with measurements.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of combined history and measurement dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT h.*, m.timestamp, m.temp, m.ph, m.o2, m.ammonia, m.nitrite, m.salinity
            FROM history h
            JOIN measurements m ON h.measurement_id = m.id
            ORDER BY h.id DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_measurements_for_ml(self, window_size: int = 6) -> Optional[List[List[float]]]:
        """
        Get recent measurements formatted for ML prediction.
        
        Args:
            window_size: Number of recent measurements to retrieve
            
        Returns:
            List of [temp, ph, o2, ammonia, nitrite, salinity] lists,
            or None if not enough data
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT temp, ph, o2, ammonia, nitrite, salinity
            FROM measurements
            ORDER BY timestamp DESC
            LIMIT ?
        """, (window_size,))
        
        rows = cursor.fetchall()
        
        if len(rows) < window_size:
            return None
        
        # Reverse to get chronological order (oldest first)
        rows = list(reversed(rows))
        return [[float(val) for val in row] for row in rows]
    
    def get_all_measurements_for_training(self) -> List[Dict[str, Any]]:
        """
        Get all measurements for ML training.
        
        Returns:
            List of all measurement dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM measurements ORDER BY timestamp ASC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
