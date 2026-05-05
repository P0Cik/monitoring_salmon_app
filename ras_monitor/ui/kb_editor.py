# [FILE: ras_monitor/ui/kb_editor.py]
"""
Knowledge Base Editor module for RAS monitoring system.
Full implementation according to section 3.5.3 of the report.
Contains 10 editor dialogs for all KB terms.
"""

import sys
from typing import Dict, List, Any, Optional, Tuple
from PyQt6.QtWidgets import (
    QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QTabWidget,
    QWidget, QFileDialog, QApplication, QListWidget, QListWidgetItem,
    QCheckBox, QToolButton, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

import sqlite3
import json


# ============================================================================
# DATABASE HANDLER
# ============================================================================

class KBDatabase:
    """Handler for Knowledge Base SQLite tables according to section 3.5.3."""

    def __init__(self, db_path: str = "ras_monitor.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._init_defaults()

    def _create_tables(self):
        """Create all KB tables if they don't exist."""
        cursor = self.conn.cursor()

        # kb_evaluations - possible suitability evaluations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # kb_states - environment states
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # kb_parameters - water quality parameters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                unit TEXT,
                min_possible REAL,
                max_possible REAL
            )
        """)

        # kb_clinical_picture - evaluation to parameters mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_clinical_picture (
                evaluation_id INTEGER REFERENCES kb_evaluations(id),
                parameter_id INTEGER REFERENCES kb_parameters(id),
                PRIMARY KEY (evaluation_id, parameter_id)
            )
        """)

        # kb_state_clinical_picture - state to parameters mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_state_clinical_picture (
                state_id INTEGER REFERENCES kb_states(id),
                parameter_id INTEGER REFERENCES kb_parameters(id),
                PRIMARY KEY (state_id, parameter_id)
            )
        """)

        # kb_normal_ranges - normal value ranges for parameters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_normal_ranges (
                parameter_id INTEGER PRIMARY KEY REFERENCES kb_parameters(id),
                min_value REAL NOT NULL,
                max_value REAL NOT NULL,
                interval_type TEXT DEFAULT '[)'
            )
        """)

        # kb_possible_ranges - physically possible ranges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_possible_ranges (
                parameter_id INTEGER PRIMARY KEY REFERENCES kb_parameters(id),
                min_value REAL NOT NULL,
                max_value REAL NOT NULL
            )
        """)

        # kb_severity_mapping - parameter intervals to state mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_severity_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parameter_id INTEGER REFERENCES kb_parameters(id),
                min1 REAL,
                max1 REAL,
                min2 REAL,
                max2 REAL,
                state_id INTEGER REFERENCES kb_states(id),
                interval_type1 TEXT DEFAULT '[)',
                interval_type2 TEXT DEFAULT '[)'
            )
        """)

        # kb_suitability_ranges - ranges leading to "unsuitable" evaluation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_suitability_ranges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parameter_id INTEGER REFERENCES kb_parameters(id),
                min1 REAL,
                max1 REAL,
                min2 REAL,
                max2 REAL,
                interval_type1 TEXT DEFAULT '[)',
                interval_type2 TEXT DEFAULT '[)'
            )
        """)

        # kb_state_order - ordering of states
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_state_order (
                state_id INTEGER PRIMARY KEY REFERENCES kb_states(id),
                order_index INTEGER UNIQUE NOT NULL
            )
        """)

        self.conn.commit()

    def _init_defaults(self):
        """Initialize default knowledge base data if empty."""
        cursor = self.conn.cursor()

        # Initialize evaluations
        cursor.execute("SELECT COUNT(*) FROM kb_evaluations")
        if cursor.fetchone()[0] == 0:
            evaluations = [("пригодна",), ("непригодна",)]
            cursor.executemany("INSERT INTO kb_evaluations (name) VALUES (?)", evaluations)

        # Initialize states
        cursor.execute("SELECT COUNT(*) FROM kb_states")
        if cursor.fetchone()[0] == 0:
            states = [
                ("отходящее от нормы",),
                ("неустойчивое равновесие",),
                ("угроза нарушения биобаланса",),
                ("критическое состояние среды",)
            ]
            cursor.executemany("INSERT INTO kb_states (name) VALUES (?)", states)

        # Initialize parameters
        cursor.execute("SELECT COUNT(*) FROM kb_parameters")
        if cursor.fetchone()[0] == 0:
            params = [
                ("температура", "°C", 5.0, 32.0),
                ("pH", "", 0.0, 14.0),
                ("O₂", "%", 0.0, 100.0),
                ("аммиак", "мг/л", 0.0, 2.0),
                ("нитриты", "мг/л", 0.0, 5.0),
                ("солёность", "‰", 0.0, 35.0)
            ]
            cursor.executemany(
                "INSERT INTO kb_parameters (name, unit, min_possible, max_possible) VALUES (?, ?, ?, ?)",
                params
            )

        # Initialize clinical picture for evaluations
        cursor.execute("SELECT COUNT(*) FROM kb_clinical_picture")
        if cursor.fetchone()[0] == 0:
            # For "непригодна" - all parameters
            eval_unsuitable = cursor.execute("SELECT id FROM kb_evaluations WHERE name='непригодна'").fetchone()
            if eval_unsuitable:
                cursor.execute("SELECT id FROM kb_parameters")
                param_ids = cursor.fetchall()
                for pid in param_ids:
                    cursor.execute(
                        "INSERT INTO kb_clinical_picture (evaluation_id, parameter_id) VALUES (?, ?)",
                        (eval_unsuitable[0], pid[0])
                    )

        # Initialize state clinical picture
        cursor.execute("SELECT COUNT(*) FROM kb_state_clinical_picture")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id FROM kb_states")
            state_ids = cursor.fetchall()
            cursor.execute("SELECT id FROM kb_parameters")
            param_ids = cursor.fetchall()
            for sid in state_ids:
                for pid in param_ids:
                    cursor.execute(
                        "INSERT INTO kb_state_clinical_picture (state_id, parameter_id) VALUES (?, ?)",
                        (sid[0], pid[0])
                    )

        # Initialize normal ranges
        cursor.execute("SELECT COUNT(*) FROM kb_normal_ranges")
        if cursor.fetchone()[0] == 0:
            normal_ranges = [
                (1, 12.0, 14.0, '[)'),   # температура
                (2, 7.4, 7.8, '[)'),     # pH
                (3, 90.0, 100.0, '[)'),  # O₂
                (4, 0.0, 0.5, '(]'),     # аммиак
                (5, 0.0, 0.1, '(]'),     # нитриты
                (6, 0.0, 0.0, '[)'),     # солёность
            ]
            cursor.executemany(
                "INSERT INTO kb_normal_ranges (parameter_id, min_value, max_value, interval_type) VALUES (?, ?, ?, ?)",
                normal_ranges
            )

        # Initialize possible ranges
        cursor.execute("SELECT COUNT(*) FROM kb_possible_ranges")
        if cursor.fetchone()[0] == 0:
            possible_ranges = [
                (1, 5.0, 32.0),    # температура
                (2, 0.0, 14.0),    # pH
                (3, 0.0, 100.0),   # O₂
                (4, 0.0, 2.0),     # аммиак
                (5, 0.0, 5.0),     # нитриты
                (6, 0.0, 35.0),    # солёность
            ]
            cursor.executemany(
                "INSERT INTO kb_possible_ranges (parameter_id, min_value, max_value) VALUES (?, ?, ?)",
                possible_ranges
            )

        # Initialize severity mapping
        cursor.execute("SELECT COUNT(*) FROM kb_severity_mapping")
        if cursor.fetchone()[0] == 0:
            self._init_severity_defaults(cursor)

        # Initialize suitability ranges
        cursor.execute("SELECT COUNT(*) FROM kb_suitability_ranges")
        if cursor.fetchone()[0] == 0:
            suitability_ranges = [
                (1, 5.0, 12.0, 14.0, 32.0, '[)', '(]'),   # температура
                (2, 0.0, 7.4, 7.8, 14.0, '[)', '(]'),     # pH
                (3, 0.0, 90.0, None, None, '[)', None),   # O₂
                (4, 0.5, 2.0, None, None, '(]', None),    # аммиак
                (5, 0.1, 5.0, None, None, '(]', None),    # нитриты
                (6, 0.1, 35.0, None, None, '(]', None),   # солёность
            ]
            cursor.executemany(
                "INSERT INTO kb_suitability_ranges (parameter_id, min1, max1, min2, max2, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?)",
                suitability_ranges
            )

        # Initialize state order
        cursor.execute("SELECT COUNT(*) FROM kb_state_order")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id FROM kb_states ORDER BY id")
            state_ids = cursor.fetchall()
            for idx, (sid,) in enumerate(state_ids, 1):
                cursor.execute(
                    "INSERT INTO kb_state_order (state_id, order_index) VALUES (?, ?)",
                    (sid, idx)
                )

        self.conn.commit()

    def _init_severity_defaults(self, cursor):
        """Initialize default severity mappings."""
        # Temperature severity (param_id=1)
        temp_sev = [
            (1, 11.0, 12.0, None, None, 1, '[)', None),
            (1, 14.0, 15.0, None, None, 1, '[)', None),
            (1, 9.0, 11.0, None, None, 2, '[)', None),
            (1, 15.0, 17.0, None, None, 2, '[)', None),
            (1, 5.0, 9.0, None, None, 3, '[)', None),
            (1, 17.0, 21.0, None, None, 3, '[)', None),
            (1, -100.0, 5.0, None, None, 4, '[)', None),
            (1, 21.0, 100.0, None, None, 4, '[)', None),
        ]
        for row in temp_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

        # pH severity (param_id=2)
        ph_sev = [
            (2, 7.2, 7.4, None, None, 1, '[)', None),
            (2, 7.8, 8.0, None, None, 1, '[)', None),
            (2, 7.0, 7.2, None, None, 2, '[)', None),
            (2, 8.0, 8.2, None, None, 2, '[)', None),
            (2, 6.6, 7.0, None, None, 3, '[)', None),
            (2, 8.2, 8.6, None, None, 3, '[)', None),
            (2, -100.0, 6.6, None, None, 4, '[)', None),
            (2, 8.6, 100.0, None, None, 4, '[)', None),
        ]
        for row in ph_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

        # O2 severity (param_id=3)
        o2_sev = [
            (3, 85.0, 90.0, None, None, 1, '[)', None),
            (3, 70.0, 85.0, None, None, 2, '[)', None),
            (3, 60.0, 70.0, None, None, 3, '[)', None),
            (3, -100.0, 60.0, None, None, 4, '[)', None),
        ]
        for row in o2_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

        # Ammonia severity (param_id=4)
        nh3_sev = [
            (4, 0.5, 0.6, None, None, 1, '(]', None),
            (4, 0.6, 1.0, None, None, 2, '(]', None),
            (4, 1.0, 1.5, None, None, 3, '(]', None),
            (4, 1.5, 100.0, None, None, 4, '(]', None),
        ]
        for row in nh3_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

        # Nitrite severity (param_id=5)
        no2_sev = [
            (5, 0.1, 0.15, None, None, 1, '(]', None),
            (5, 0.15, 0.2, None, None, 2, '(]', None),
            (5, 0.2, 0.25, None, None, 3, '(]', None),
            (5, 0.25, 100.0, None, None, 4, '(]', None),
        ]
        for row in no2_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

        # Salinity severity (param_id=6)
        sal_sev = [
            (6, 0.0, 0.1, None, None, 1, '[)', None),
            (6, 0.1, 0.5, None, None, 2, '[)', None),
            (6, 0.5, 1.0, None, None, 3, '[)', None),
            (6, 1.0, 100.0, None, None, 4, '[)', None),
        ]
        for row in sal_sev:
            cursor.execute(
                "INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row
            )

    # ==================== Evaluation methods ====================

    def get_evaluations(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_evaluations ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def add_evaluation(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO kb_evaluations (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_evaluation(self, eval_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_evaluations WHERE id=?", (eval_id,))
        self.conn.commit()

    # ==================== State methods ====================

    def get_states(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_states ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def get_states_ordered(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.id, s.name, o.order_index
            FROM kb_states s
            LEFT JOIN kb_state_order o ON s.id = o.state_id
            ORDER BY o.order_index
        """)
        return [dict(row) for row in cursor.fetchall()]

    def add_state(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO kb_states (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_state(self, state_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_states WHERE id=?", (state_id,))
        self.conn.commit()

    def update_state_order(self, state_id: int, order_index: int):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO kb_state_order (state_id, order_index) VALUES (?, ?)
        """, (state_id, order_index))
        self.conn.commit()

    # ==================== Parameter methods ====================

    def get_parameters(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_parameters ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]

    def add_parameter(self, name: str, unit: str = "", min_possible: float = 0.0, max_possible: float = 100.0):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO kb_parameters (name, unit, min_possible, max_possible) VALUES (?, ?, ?, ?)",
            (name, unit, min_possible, max_possible)
        )
        self.conn.commit()

    def delete_parameter(self, param_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_parameters WHERE id=?", (param_id,))
        self.conn.commit()

    # ==================== Clinical Picture methods ====================

    def get_clinical_picture(self, evaluation_id: int) -> List[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT parameter_id FROM kb_clinical_picture WHERE evaluation_id=?", (evaluation_id,))
        return [row[0] for row in cursor.fetchall()]

    def save_clinical_picture(self, evaluation_id: int, parameter_ids: List[int]):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_clinical_picture WHERE evaluation_id=?", (evaluation_id,))
        for pid in parameter_ids:
            cursor.execute(
                "INSERT INTO kb_clinical_picture (evaluation_id, parameter_id) VALUES (?, ?)",
                (evaluation_id, pid)
            )
        self.conn.commit()

    # ==================== State Clinical Picture methods ====================

    def get_state_clinical_picture(self, state_id: int) -> List[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT parameter_id FROM kb_state_clinical_picture WHERE state_id=?", (state_id,))
        return [row[0] for row in cursor.fetchall()]

    def save_state_clinical_picture(self, state_id: int, parameter_ids: List[int]):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_state_clinical_picture WHERE state_id=?", (state_id,))
        for pid in parameter_ids:
            cursor.execute(
                "INSERT INTO kb_state_clinical_picture (state_id, parameter_id) VALUES (?, ?)",
                (state_id, pid)
            )
        self.conn.commit()

    # ==================== Normal Ranges methods ====================

    def get_normal_ranges(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.name, r.min_value, r.max_value, r.interval_type
            FROM kb_normal_ranges r
            JOIN kb_parameters p ON r.parameter_id = p.id
            ORDER BY p.id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def save_normal_range(self, parameter_id: int, min_value: float, max_value: float, interval_type: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO kb_normal_ranges (parameter_id, min_value, max_value, interval_type)
            VALUES (?, ?, ?, ?)
        """, (parameter_id, min_value, max_value, interval_type))
        self.conn.commit()

    # ==================== Possible Ranges methods ====================

    def get_possible_ranges(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, r.min_value, r.max_value
            FROM kb_possible_ranges r
            JOIN kb_parameters p ON r.parameter_id = p.id
            ORDER BY p.id
        """)
        return [dict(row) for row in cursor.fetchall()]

    def save_possible_range(self, parameter_id: int, min_value: float, max_value: float):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO kb_possible_ranges (parameter_id, min_value, max_value)
            VALUES (?, ?, ?)
        """, (parameter_id, min_value, max_value))
        self.conn.commit()

    # ==================== Severity Mapping methods ====================

    def get_severity_mapping(self, parameter_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM kb_severity_mapping WHERE parameter_id=? ORDER BY min1
        """, (parameter_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_severity_mapping(self, parameter_id: int, min1: float, max1: float,
                             min2: Optional[float], max2: Optional[float],
                             state_id: int, interval_type1: str = '[)', interval_type2: str = '[)'):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO kb_severity_mapping (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (parameter_id, min1, max1, min2, max2, state_id, interval_type1, interval_type2))
        self.conn.commit()

    def delete_severity_mapping(self, mapping_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_severity_mapping WHERE id=?", (mapping_id,))
        self.conn.commit()

    # ==================== Suitability Ranges methods ====================

    def get_suitability_ranges(self, parameter_id: int) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM kb_suitability_ranges WHERE parameter_id=? ORDER BY id
        """, (parameter_id,))
        return [dict(row) for row in cursor.fetchall()]

    def add_suitability_range(self, parameter_id: int, min1: float, max1: float,
                              min2: Optional[float], max2: Optional[float],
                              interval_type1: str = '[)', interval_type2: str = '[)'):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO kb_suitability_ranges (parameter_id, min1, max1, min2, max2, interval_type1, interval_type2)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (parameter_id, min1, max1, min2, max2, interval_type1, interval_type2))
        self.conn.commit()

    def delete_suitability_range(self, range_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_suitability_ranges WHERE id=?", (range_id,))
        self.conn.commit()

    # ==================== Export/Import/Reset ====================

    def export_kb(self, filepath: str):
        """Export entire KB to JSON."""
        data = {
            'evaluations': self.get_evaluations(),
            'states': self.get_states(),
            'parameters': self.get_parameters(),
            'normal_ranges': self.get_normal_ranges(),
            'possible_ranges': self.get_possible_ranges(),
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def reset_to_defaults(self):
        """Drop and recreate all tables with defaults."""
        cursor = self.conn.cursor()
        tables = [
            'kb_state_order', 'kb_suitability_ranges', 'kb_severity_mapping',
            'kb_possible_ranges', 'kb_normal_ranges', 'kb_state_clinical_picture',
            'kb_clinical_picture', 'kb_parameters', 'kb_states', 'kb_evaluations'
        ]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.commit()
        self._create_tables()
        self._init_defaults()

    def close(self):
        if self.conn:
            self.conn.close()


# ============================================================================
# DIALOG CLASSES FOR EDITING KB TERMS (Section 3.5.3)
# ============================================================================

class EvaluationEditorDialog(QDialog):
    """Dialog for editing evaluations (Оценка)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Оценка")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_evaluations()

    def setup_ui(self):
        layout = QVBoxLayout()

        # List widget
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Список оценок:"))
        layout.addWidget(self.list_widget)

        # Add new evaluation
        add_layout = QHBoxLayout()
        self.new_eval_edit = QLineEdit()
        self.new_eval_edit.setPlaceholderText("Введите название...")
        add_layout.addWidget(self.new_eval_edit)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_evaluation)
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_evaluations(self):
        self.list_widget.clear()
        for eval_item in self.kb_db.get_evaluations():
            item = QListWidgetItem(f"✓ {eval_item['name']}")
            item.setData(Qt.ItemDataRole.UserRole, eval_item['id'])

            # Add delete button as widget
            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.setToolTip("Удалить оценку")
            del_btn.clicked.connect(lambda checked, eid=eval_item['id']: self.delete_evaluation(eid))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, del_btn)

    def add_evaluation(self):
        name = self.new_eval_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название оценки")
            return

        try:
            self.kb_db.add_evaluation(name)
            self.new_eval_edit.clear()
            self.load_evaluations()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", f"Оценка '{name}' уже существует")

    def delete_evaluation(self, eval_id: int):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить эту оценку?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_evaluation(eval_id)
            self.load_evaluations()


class StateEditorDialog(QDialog):
    """Dialog for editing environment states (Состояние среды)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Состояние среды")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_states()

    def setup_ui(self):
        layout = QVBoxLayout()

        # List widget with order controls
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Список состояний (порядок важен!):"))
        layout.addWidget(self.list_widget)

        # Order buttons
        order_layout = QHBoxLayout()
        self.up_btn = QPushButton("⬆️ Вверх")
        self.up_btn.clicked.connect(self.move_up)
        order_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("⬇️ Вниз")
        self.down_btn.clicked.connect(self.move_down)
        order_layout.addWidget(self.down_btn)
        order_layout.addStretch()
        layout.addLayout(order_layout)

        # Add new state
        add_layout = QHBoxLayout()
        self.new_state_edit = QLineEdit()
        self.new_state_edit.setPlaceholderText("Введите название...")
        add_layout.addWidget(self.new_state_edit)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_state)
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_states(self):
        self.list_widget.clear()
        for state in self.kb_db.get_states_ordered():
            item = QListWidgetItem(f"{state.get('order_index', '?')}. {state['name']}")
            item.setData(Qt.ItemDataRole.UserRole, state['id'])
            self.list_widget.addItem(item)

    def add_state(self):
        name = self.new_state_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название состояния")
            return

        try:
            self.kb_db.add_state(name)
            self.new_state_edit.clear()
            self.load_states()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", f"Состояние '{name}' уже существует")

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self.swap_items(row, row - 1)

    def move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            self.swap_items(row, row + 1)

    def swap_items(self, row1: int, row2: int):
        item1 = self.list_widget.item(row1)
        item2 = self.list_widget.item(row2)
        id1 = item1.data(Qt.ItemDataRole.UserRole)
        id2 = item2.data(Qt.ItemDataRole.UserRole)

        # Swap in UI
        text1, text2 = item1.text(), item2.text()
        item1.setText(text2)
        item2.setText(text1)
        self.list_widget.setCurrentRow(row2)

        # Update order in DB
        for i, idx in enumerate([row2, row1], 1):
            if idx == row2:
                self.kb_db.update_state_order(id2, i)
            else:
                self.kb_db.update_state_order(id1, i)

        self.load_states()


class ParameterEditorDialog(QDialog):
    """Dialog for editing parameters (Показатели среды)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Показатели среды")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_parameters()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Ед. изм.", "Мин", "Макс"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Add parameter form
        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Добавить параметр:"), 0, 0, 1, 4)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название")
        form_layout.addWidget(self.name_edit, 1, 0)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("Ед. изм.")
        form_layout.addWidget(self.unit_edit, 1, 1)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000, 1000)
        self.min_spin.setValue(0.0)
        self.min_spin.setDecimals(2)
        form_layout.addWidget(self.min_spin, 1, 2)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000, 1000)
        self.max_spin.setValue(100.0)
        self.max_spin.setDecimals(2)
        form_layout.addWidget(self.max_spin, 1, 3)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_parameter)
        form_layout.addWidget(self.add_btn, 1, 4)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_parameters(self):
        params = self.kb_db.get_parameters()
        self.table.setRowCount(len(params))
        for row, p in enumerate(params):
            self.table.setItem(row, 0, QTableWidgetItem(str(p['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.table.setItem(row, 2, QTableWidgetItem(p.get('unit') or ''))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.get('min_possible', 0):.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{p.get('max_possible', 0):.2f}"))

    def add_parameter(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название параметра")
            return

        unit = self.unit_edit.text().strip()
        min_val = self.min_spin.value()
        max_val = self.max_spin.value()

        try:
            self.kb_db.add_parameter(name, unit, min_val, max_val)
            self.name_edit.clear()
            self.unit_edit.clear()
            self.load_parameters()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", f"Параметр '{name}' уже существует")


class ClinicalPictureDialog(QDialog):
    """Dialog for editing clinical picture by evaluation (Клиническая картина)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Клиническая картина")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Evaluation selector
        eval_layout = QHBoxLayout()
        eval_layout.addWidget(QLabel("Оценка:"))
        self.eval_combo = QComboBox()
        self.eval_combo.currentIndexChanged.connect(self.load_parameters)
        eval_layout.addWidget(self.eval_combo)
        eval_layout.addStretch()
        layout.addLayout(eval_layout)

        # Parameters checkboxes
        layout.addWidget(QLabel("Показатели, входящие в клиническую картину:"))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.checks_widget = QWidget()
        self.checks_layout = QVBoxLayout()
        self.checks_widget.setLayout(self.checks_layout)
        self.scroll.setWidget(self.checks_widget)
        layout.addWidget(self.scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.save_clinical_picture)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_evaluations()

    def load_evaluations(self):
        self.eval_combo.clear()
        for e in self.kb_db.get_evaluations():
            self.eval_combo.addItem(e['name'], e['id'])
        self.load_parameters()

    def load_parameters(self):
        # Clear existing checkboxes
        while self.checks_layout.count():
            item = self.checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add checkboxes for each parameter
        self.param_checks = {}
        for p in self.kb_db.get_parameters():
            cb = QCheckBox(p['name'])
            cb.(p['id'])
            self.checks_layout.addWidget(cb)
            self.param_checks[p['id']] = cb

        # Load current selection
        eval_id = self.eval_combo.currentData()
        selected_params = self.kb_db.get_clinical_picture(eval_id)
        for pid, cb in self.param_checks.items():
            cb.setChecked(pid in selected_params)

    def save_clinical_picture(self):
        eval_id = self.eval_combo.currentData()
        selected = [pid for pid, cb in self.param_checks.items() if cb.isChecked()]
        self.kb_db.save_clinical_picture(eval_id, selected)
        QMessageBox.information(self, "Успех", "Клиническая картина сохранена")


class StateClinicalPictureDialog(QDialog):
    """Dialog for editing clinical picture by state (Клиническая картина по состоянию)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Клиническая картина по состоянию")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # State selector
        state_layout = QHBoxLayout()
        state_layout.addWidget(QLabel("Состояние:"))
        self.state_combo = QComboBox()
        self.state_combo.currentIndexChanged.connect(self.load_parameters)
        state_layout.addWidget(self.state_combo)
        state_layout.addStretch()
        layout.addLayout(state_layout)

        # Parameters checkboxes
        layout.addWidget(QLabel("Показатели для этого состояния:"))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.checks_widget = QWidget()
        self.checks_layout = QVBoxLayout()
        self.checks_widget.setLayout(self.checks_layout)
        self.scroll.setWidget(self.checks_widget)
        layout.addWidget(self.scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.save_clinical_picture)
        btn_layout.addWidget(self.apply_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_states()

    def load_states(self):
        self.state_combo.clear()
        for s in self.kb_db.get_states():
            self.state_combo.addItem(s['name'], s['id'])
        self.load_parameters()

    def load_parameters(self):
        while self.checks_layout.count():
            item = self.checks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.param_checks = {}
        for p in self.kb_db.get_parameters():
            cb = QCheckBox(p['name'])
            cb.setData(p['id'])
            self.checks_layout.addWidget(cb)
            self.param_checks[p['id']] = cb

        state_id = self.state_combo.currentData()
        selected_params = self.kb_db.get_state_clinical_picture(state_id)
        for pid, cb in self.param_checks.items():
            cb.setChecked(pid in selected_params)

    def save_clinical_picture(self):
        state_id = self.state_combo.currentData()
        selected = [pid for pid, cb in self.param_checks.items() if cb.isChecked()]
        self.kb_db.save_state_clinical_picture(state_id, selected)
        QMessageBox.information(self, "Успех", "Клиническая картина сохранена")


class NormalRangesDialog(QDialog):
    """Dialog for editing normal ranges (Нормальные значения)."""

    INTERVAL_TYPES = ["[ ] закрытый", "[ ) полуоткрытый", "( ] полуоткрытый", "( ) открытый"]
    INTERVAL_MAP = {"[ ]": "[]", "[ )": "[)", "( ]": "(]", "( )": "()"}

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Нормальные значения")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.load_ranges()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Показатель", "Минимум", "Максимум", "Тип интервала", ""])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_ranges)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_ranges(self):
        params = self.kb_db.get_parameters()
        ranges = {r['name']: r for r in self.kb_db.get_normal_ranges()}

        self.table.setRowCount(len(params))
        for row, p in enumerate(params):
            self.table.setItem(row, 0, QTableWidgetItem(p['name']))

            r = ranges.get(p['name'], {'min_value': 0, 'max_value': 0, 'interval_type': '[)'})

            min_spin = QDoubleSpinBox()
            min_spin.setRange(-1000, 1000)
            min_spin.setValue(r['min_value'])
            min_spin.setDecimals(2)
            self.table.setCellWidget(row, 1, min_spin)

            max_spin = QDoubleSpinBox()
            max_spin.setRange(-1000, 1000)
            max_spin.setValue(r['max_value'])
            max_spin.setDecimals(2)
            self.table.setCellWidget(row, 2, max_spin)

            interval_combo = QComboBox()
            interval_combo.addItems(self.INTERVAL_TYPES)
            inv_map = {v: k for k, v in self.INTERVAL_MAP.items()}
            idx = list(inv_map.keys()).index(inv_map.get(r['interval_type'], '[)'))
            interval_combo.setCurrentIndex(idx)
            self.table.setCellWidget(row, 3, interval_combo)

    def save_ranges(self):
        params = self.kb_db.get_parameters()
        inv_map = {v: k for k, v in self.INTERVAL_MAP.items()}

        for row, p in enumerate(params):
            min_w = self.table.cellWidget(row, 1)
            max_w = self.table.cellWidget(row, 2)
            interval_w = self.table.cellWidget(row, 3)

            min_val = min_w.value()
            max_val = max_w.value()
            interval_type = inv_map[self.INTERVAL_TYPES[interval_w.currentIndex()]]

            if min_val >= max_val:
                QMessageBox.warning(self, "Ошибка", f"Для {p['name']}: минимум должен быть меньше максимума")
                return

            self.kb_db.save_normal_range(p['id'], min_val, max_val, interval_type)

        QMessageBox.information(self, "Успех", "Нормальные значения сохранены")


class SeverityMappingDialog(QDialog):
    """Dialog for editing severity mapping (Степень тяжести значений)."""

    INTERVAL_TYPES = ["[ ] закрытый", "[ ) полуоткрытый", "( ] полуоткрытый", "( ) открытый"]
    INTERVAL_MAP = {"[ ]": "[]", "[ )": "[)", "( ]": "(]", "( )": "()"}

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Степень тяжести значений")
        self.setMinimumWidth(600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Parameter selector
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Показатель:"))
        self.param_combo = QComboBox()
        self.param_combo.currentIndexChanged.connect(self.load_mappings)
        param_layout.addWidget(self.param_combo)
        param_layout.addStretch()
        layout.addLayout(param_layout)

        # Mappings table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Интервал значений", "Состояние", "", ""])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Add interval form
        form_group = QGroupBox("Добавить интервал:")
        form_layout = QGridLayout()

        form_layout.addWidget(QLabel("Мин:"), 0, 0)
        self.min1_spin = QDoubleSpinBox()
        self.min1_spin.setRange(-1000, 1000)
        self.min1_spin.setValue(0.0)
        self.min1_spin.setDecimals(2)
        form_layout.addWidget(self.min1_spin, 0, 1)

        form_layout.addWidget(QLabel("Макс:"), 0, 2)
        self.max1_spin = QDoubleSpinBox()
        self.max1_spin.setRange(-1000, 1000)
        self.max1_spin.setValue(0.0)
        self.max1_spin.setDecimals(2)
        form_layout.addWidget(self.max1_spin, 0, 3)

        form_layout.addWidget(QLabel("Состояние:"), 0, 4)
        self.state_combo = QComboBox()
        for s in self.kb_db.get_states():
            self.state_combo.addItem(s['name'], s['id'])
        form_layout.addWidget(self.state_combo, 0, 5)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_mapping)
        form_layout.addWidget(self.add_btn, 0, 6)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_parameters()

    def load_parameters(self):
        self.param_combo.clear()
        for p in self.kb_db.get_parameters():
            self.param_combo.addItem(p['name'], p['id'])
        self.load_mappings()

    def load_mappings(self):
        self.table.setRowCount(0)
        param_id = self.param_combo.currentData()
        if not param_id:
            return

        mappings = self.kb_db.get_severity_mapping(param_id)
        states = {s['id']: s['name'] for s in self.kb_db.get_states()}
        inv_map = {v: k for k, v in self.INTERVAL_MAP.items()}

        for m in mappings:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Build interval string
            interval_str = f"[{m['min1']:.1f}; {m['max1']:.1f})"
            if m['min2'] is not None:
                interval_str += f" ∪ [{m['min2']:.1f}; {m['max2']:.1f})"

            self.table.setItem(row, 0, QTableWidgetItem(interval_str))
            self.table.setItem(row, 1, QTableWidgetItem(states.get(m['state_id'], '?')))

            # Delete button
            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.clicked.connect(lambda checked, mid=m['id']: self.delete_mapping(mid))
            self.table.setCellWidget(row, 2, del_btn)

    def add_mapping(self):
        param_id = self.param_combo.currentData()
        state_id = self.state_combo.currentData()
        min1 = self.min1_spin.value()
        max1 = self.max1_spin.value()

        if min1 >= max1:
            QMessageBox.warning(self, "Ошибка", "Минимум должен быть меньше максимума")
            return

        self.kb_db.add_severity_mapping(param_id, min1, max1, None, None, state_id)
        self.load_mappings()

    def delete_mapping(self, mapping_id: int):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить этот интервал?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_severity_mapping(mapping_id)
            self.load_mappings()


class SuitabilityValuesDialog(QDialog):
    """Dialog for editing suitability ranges (Значения для пригодности)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Значения для пригодности")
        self.setMinimumWidth(600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Parameter selector
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Показатель:"))
        self.param_combo = QComboBox()
        self.param_combo.currentIndexChanged.connect(self.load_ranges)
        param_layout.addWidget(self.param_combo)
        param_layout.addStretch()
        layout.addLayout(param_layout)

        # Ranges table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Интервал значений", "", ""])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Add range form
        form_group = QGroupBox("Добавить интервал:")
        form_layout = QHBoxLayout()

        form_layout.addWidget(QLabel("Мин:"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-1000, 1000)
        self.min_spin.setValue(0.0)
        self.min_spin.setDecimals(2)
        form_layout.addWidget(self.min_spin)

        form_layout.addWidget(QLabel("Макс:"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-1000, 1000)
        self.max_spin.setValue(0.0)
        self.max_spin.setDecimals(2)
        form_layout.addWidget(self.max_spin)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_range)
        form_layout.addWidget(self.add_btn)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_parameters()

    def load_parameters(self):
        self.param_combo.clear()
        for p in self.kb_db.get_parameters():
            self.param_combo.addItem(p['name'], p['id'])
        self.load_ranges()

    def load_ranges(self):
        self.table.setRowCount(0)
        param_id = self.param_combo.currentData()
        if not param_id:
            return

        ranges = self.kb_db.get_suitability_ranges(param_id)

        for r in ranges:
            row = self.table.rowCount()
            self.table.insertRow(row)

            interval_str = f"[{r['min1']:.1f}; {r['max1']:.1f})"
            if r['min2'] is not None:
                interval_str += f" ∪ [{r['min2']:.1f}; {r['max2']:.1f})"

            self.table.setItem(row, 0, QTableWidgetItem(interval_str))

            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.clicked.connect(lambda checked, rid=r['id']: self.delete_range(rid))
            self.table.setCellWidget(row, 1, del_btn)

    def add_range(self):
        param_id = self.param_combo.currentData()
        min1 = self.min_spin.value()
        max1 = self.max_spin.value()

        if min1 >= max1:
            QMessageBox.warning(self, "Ошибка", "Минимум должен быть меньше максимума")
            return

        self.kb_db.add_suitability_range(param_id, min1, max1, None, None)
        self.load_ranges()

    def delete_range(self, range_id: int):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить этот интервал?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_suitability_range(range_id)
            self.load_ranges()


class PossibleRangesDialog(QDialog):
    """Dialog for editing possible ranges (Возможные значения)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Возможные значения")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_ranges()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Показатель", "Минимум", "Максимум"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_ranges)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_ranges(self):
        params = self.kb_db.get_parameters()
        ranges_data = self.kb_db.get_possible_ranges()
        ranges = {r['id']: r for r in ranges_data}

        self.table.setRowCount(len(params))
        for row, p in enumerate(params):
            self.table.setItem(row, 0, QTableWidgetItem(p['name']))

            r = ranges.get(p['id'], {'min_value': p.get('min_possible', 0), 'max_value': p.get('max_possible', 100)})

            min_spin = QDoubleSpinBox()
            min_spin.setRange(-1000, 1000)
            min_spin.setValue(r['min_value'])
            min_spin.setDecimals(2)
            self.table.setCellWidget(row, 1, min_spin)

            max_spin = QDoubleSpinBox()
            max_spin.setRange(-1000, 1000)
            max_spin.setValue(r['max_value'])
            max_spin.setDecimals(2)
            self.table.setCellWidget(row, 2, max_spin)

    def save_ranges(self):
        params = self.kb_db.get_parameters()

        for row, p in enumerate(params):
            min_w = self.table.cellWidget(row, 1)
            max_w = self.table.cellWidget(row, 2)

            min_val = min_w.value()
            max_val = max_w.value()

            if min_val > max_val:
                QMessageBox.warning(self, "Ошибка", f"Для {p['name']}: минимум не может быть больше максимума")
                return

            self.kb_db.save_possible_range(p['id'], min_val, max_val)

        QMessageBox.information(self, "Успех", "Возможные значения сохранены")


class StateOrderDialog(QDialog):
    """Dialog for editing state order (Порядок состояний)."""

    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Порядок состояний")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_states()

    def setup_ui(self):
        layout = QVBoxLayout()

        # List widget with order controls
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Порядок состояний (от меньшего к большему):"))
        layout.addWidget(self.list_widget)

        # Order buttons
        order_layout = QHBoxLayout()
        self.up_btn = QPushButton("⬆️ Вверх")
        self.up_btn.clicked.connect(self.move_up)
        order_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("⬇️ Вниз")
        self.down_btn.clicked.connect(self.move_down)
        order_layout.addWidget(self.down_btn)
        order_layout.addStretch()
        layout.addLayout(order_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить порядок")
        self.save_btn.clicked.connect(self.save_order)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_states(self):
        self.list_widget.clear()
        for i, state in enumerate(self.kb_db.get_states_ordered(), 1):
            item = QListWidgetItem(f"{i}. {state['name']}")
            item.setData(Qt.ItemDataRole.UserRole, state['id'])
            self.list_widget.addItem(item)

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def save_order(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            state_id = item.data(Qt.ItemDataRole.UserRole)
            self.kb_db.update_state_order(state_id, i + 1)
        QMessageBox.information(self, "Успех", "Порядок состояний сохранён")


# ============================================================================
# MAIN WINDOW
# ============================================================================

class KBEditorMainWindow(QMainWindow):
    """Main Knowledge Base Editor window according to section 3.5.3."""

    TERM_NAMES = [
        "Оценка",
        "Состояние среды",
        "Показатели среды",
        "Клиническая картина",
        "Клиническая картина по состоянию",
        "Нормальные значения",
        "Степень тяжести значений",
        "Значения для пригодности",
        "Возможные значения",
        "Порядок состояний"
    ]

    def __init__(self, db_path: str = "ras_monitor.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор базы знаний УЗВ")
        self.setGeometry(100, 100, 900, 700)

        self.kb_db = KBDatabase(db_path)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Left side - terms list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Термины:"))
        self.terms_list = QListWidget()
        self.terms_list.addItems(self.TERM_NAMES)
        self.terms_list.itemDoubleClicked.connect(self.open_term_editor)
        left_layout.addWidget(self.terms_list)

        left_widget.setLayout(left_layout)
        main_layout.addWidget(left_widget, 1)

        # Right side - action buttons
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Info label
        info_label = QLabel("Выберите термин для редактирования\nили используйте кнопки ниже:")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-style: italic; padding: 20px;")
        right_layout.addWidget(info_label)

        # Action buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        self.completeness_btn = QPushButton("📋 Проверка полноты знаний")
        self.completeness_btn.clicked.connect(self.check_completeness)
        btn_layout.addWidget(self.completeness_btn)

        self.save_db_btn = QPushButton("💾 Сохранить в БД")
        self.save_db_btn.clicked.connect(self.save_to_db)
        btn_layout.addWidget(self.save_db_btn)

        self.load_db_btn = QPushButton("📂 Загрузить из БД")
        self.load_db_btn.clicked.connect(self.load_from_db)
        btn_layout.addWidget(self.load_db_btn)

        self.reset_btn = QPushButton("🔄 Сбросить к значениям по умолчанию")
        self.reset_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.reset_btn.clicked.connect(self.reset_kb)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        right_layout.addLayout(btn_layout)
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 1)

        central_widget.setLayout(main_layout)

    def open_term_editor(self, item: QListWidgetItem):
        term_name = item.text()

        editors = {
            "Оценка": lambda: EvaluationEditorDialog(self.kb_db, self).exec(),
            "Состояние среды": lambda: StateEditorDialog(self.kb_db, self).exec(),
            "Показатели среды": lambda: ParameterEditorDialog(self.kb_db, self).exec(),
            "Клиническая картина": lambda: ClinicalPictureDialog(self.kb_db, self).exec(),
            "Клиническая картина по состоянию": lambda: StateClinicalPictureDialog(self.kb_db, self).exec(),
            "Нормальные значения": lambda: NormalRangesDialog(self.kb_db, self).exec(),
            "Степень тяжести значений": lambda: SeverityMappingDialog(self.kb_db, self).exec(),
            "Значения для пригодности": lambda: SuitabilityValuesDialog(self.kb_db, self).exec(),
            "Возможные значения": lambda: PossibleRangesDialog(self.kb_db, self).exec(),
            "Порядок состояний": lambda: StateOrderDialog(self.kb_db, self).exec(),
        }

        if term_name in editors:
            editors[term_name]()

    def check_completeness(self):
        """Check completeness of knowledge base."""
        issues = []

        # Check evaluations
        evals = self.kb_db.get_evaluations()
        if len(evals) < 2:
            issues.append("Недостаточно оценок (минимум 2: пригодна, непригодна)")

        # Check states
        states = self.kb_db.get_states()
        if len(states) < 4:
            issues.append("Недостаточно состояний среды (минимум 4)")

        # Check parameters
        params = self.kb_db.get_parameters()
        if len(params) < 6:
            issues.append("Недостаточно показателей (минимум 6)")

        # Check normal ranges
        normal_ranges = self.kb_db.get_normal_ranges()
        if len(normal_ranges) < len(params):
            issues.append(f"Не для всех показателей заданы нормальные диапазоны ({len(normal_ranges)}/{len(params)})")

        # Check possible ranges
        possible_ranges = self.kb_db.get_possible_ranges()
        if len(possible_ranges) < len(params):
            issues.append(f"Не для всех показателей заданы возможные диапазоны ({len(possible_ranges)}/{len(params)})")

        if issues:
            msg = "Обнаружены проблемы с полнотой знаний:\n\n" + "\n".join(f"• {i}" for i in issues)
            QMessageBox.warning(self, "Проверка полноты", msg)
        else:
            QMessageBox.information(self, "Проверка полноты", "База знаний заполнена полностью!")

    def save_to_db(self):
        """Save KB to database (auto-saved on edits)."""
        QMessageBox.information(self, "Сохранение", "Изменения сохраняются автоматически при редактировании.")

    def load_from_db(self):
        """Reload KB from database."""
        reply = QMessageBox.question(
            self, "Загрузка",
            "Перезагрузить данные из БД? Несохранённые изменения будут потеряны.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Reinitialize database connection
            self.kb_db.close()
            self.kb_db = KBDatabase(self.kb_db.db_path)
            QMessageBox.information(self, "Загрузка", "Данные загружены из БД")

    def reset_kb(self):
        """Reset KB to defaults."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены? Все изменения будут потеряны.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.reset_to_defaults()
            QMessageBox.information(self, "Сброс", "База знаний сброшена к значениям по умолчанию")

    def closeEvent(self, event):
        self.kb_db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = KBEditorMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
