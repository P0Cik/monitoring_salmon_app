# [FILE: ras_monitor/ui/kb_editor.py]
"""
Knowledge Base Editor module for RAS monitoring system.
Allows editing terms, ranges, severity mappings as per section 3.5 of the report.
"""

import sys
from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QTabWidget,
    QWidget, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import sqlite3
import json


class KBDatabase:
    """Handler for Knowledge Base SQLite tables."""
    
    def __init__(self, db_path: str = "ras_monitor.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._init_defaults()
    
    def _create_tables(self):
        """Create KB tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Terms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        """)
        
        # Ranges table for normal values
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_ranges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                param_name TEXT NOT NULL,
                min_val REAL NOT NULL,
                max_val REAL NOT NULL,
                is_exclusive_upper INTEGER DEFAULT 0
            )
        """)
        
        # Severity mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_severity_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                param_name TEXT NOT NULL,
                min_val REAL NOT NULL,
                max_val REAL NOT NULL,
                severity INTEGER NOT NULL
            )
        """)
        
        self.conn.commit()
    
    def _init_defaults(self):
        """Initialize default knowledge base data if empty."""
        cursor = self.conn.cursor()
        
        # Check if terms exist
        cursor.execute("SELECT COUNT(*) FROM kb_terms")
        if cursor.fetchone()[0] == 0:
            # Insert default terms from section 3.5
            terms = [
                ("Оценка", "Оценка пригодности водной среды"),
                ("Состояние среды", "Уровень состояния системы (0-4)"),
                ("Показатели", "Параметры водной среды: temp, ph, o2, ammonia, nitrite, salinity"),
                ("Нормальные значения", "Диапазоны значений параметров в норме"),
                ("Степень тяжести значений", "Уровни severity 1-4 для отклонений"),
                ("Возможные значения", "Все допустимые значения параметров"),
                ("Порядок состояний", "Иерархия состояний: 0 < 1 < 2 < 3 < 4"),
            ]
            cursor.executemany(
                "INSERT INTO kb_terms (term_name, description) VALUES (?, ?)",
                terms
            )
        
        # Check if ranges exist
        cursor.execute("SELECT COUNT(*) FROM kb_ranges")
        if cursor.fetchone()[0] == 0:
            # Default normal ranges from solver.py
            ranges = [
                ('temp', 12.0, 14.0, 0),
                ('ph', 7.4, 7.8, 0),
                ('o2', 90, 100, 0),
                ('ammonia', 0, 0.5, 1),  # exclusive upper
                ('nitrite', 0, 0.1, 1),
                ('salinity', 0, 0, 0),
            ]
            cursor.executemany(
                "INSERT INTO kb_ranges (param_name, min_val, max_val, is_exclusive_upper) VALUES (?, ?, ?, ?)",
                ranges
            )
        
        # Check if severity map exists
        cursor.execute("SELECT COUNT(*) FROM kb_severity_map")
        if cursor.fetchone()[0] == 0:
            # Default severity thresholds
            severity_data = []
            
            # Temperature severity
            temp_sev = [
                (11, 12, 1), (14, 15, 1),
                (9, 11, 2), (15, 17, 2),
                (5, 9, 3), (17, 21, 3),
                (-100, 5, 4), (21, 100, 4),
            ]
            for min_v, max_v, sev in temp_sev:
                severity_data.append(('temp', min_v, max_v, sev))
            
            # pH severity
            ph_sev = [
                (7.2, 7.4, 1), (7.8, 8.0, 1),
                (7.0, 7.2, 2), (8.0, 8.2, 2),
                (6.6, 7.0, 3), (8.2, 8.6, 3),
                (-100, 6.6, 4), (8.6, 100, 4),
            ]
            for min_v, max_v, sev in ph_sev:
                severity_data.append(('ph', min_v, max_v, sev))
            
            # O2 severity
            o2_sev = [
                (85, 90, 1),
                (70, 85, 2),
                (60, 70, 3),
                (-100, 60, 4),
            ]
            for min_v, max_v, sev in o2_sev:
                severity_data.append(('o2', min_v, max_v, sev))
            
            # Ammonia severity
            nh3_sev = [
                (0.5, 0.6, 1),
                (0.6, 1.0, 2),
                (1.0, 1.5, 3),
                (1.5, 100, 4),
            ]
            for min_v, max_v, sev in nh3_sev:
                severity_data.append(('ammonia', min_v, max_v, sev))
            
            # Nitrite severity
            no2_sev = [
                (0.1, 0.15, 1),
                (0.15, 0.2, 2),
                (0.2, 0.25, 3),
                (0.25, 100, 4),
            ]
            for min_v, max_v, sev in no2_sev:
                severity_data.append(('nitrite', min_v, max_v, sev))
            
            # Salinity severity
            sal_sev = [
                (0, 0.1, 1),
                (0.1, 0.5, 2),
                (0.5, 1.0, 3),
                (1.0, 100, 4),
            ]
            for min_v, max_v, sev in sal_sev:
                severity_data.append(('salinity', min_v, max_v, sev))
            
            cursor.executemany(
                "INSERT INTO kb_severity_map (param_name, min_val, max_val, severity) VALUES (?, ?, ?, ?)",
                severity_data
            )
        
        self.conn.commit()
    
    def get_terms(self) -> List[Dict]:
        """Get all terms."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_terms")
        return [dict(row) for row in cursor.fetchall()]
    
    def save_term(self, term_name: str, description: str, term_id: Optional[int] = None):
        """Save or update a term."""
        cursor = self.conn.cursor()
        if term_id:
            cursor.execute(
                "UPDATE kb_terms SET term_name=?, description=? WHERE id=?",
                (term_name, description, term_id)
            )
        else:
            try:
                cursor.execute(
                    "INSERT INTO kb_terms (term_name, description) VALUES (?, ?)",
                    (term_name, description)
                )
            except sqlite3.IntegrityError:
                raise ValueError(f"Term '{term_name}' already exists")
        self.conn.commit()
    
    def delete_term(self, term_id: int):
        """Delete a term."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_terms WHERE id=?", (term_id,))
        self.conn.commit()
    
    def get_ranges(self) -> List[Dict]:
        """Get all normal ranges."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_ranges")
        return [dict(row) for row in cursor.fetchall()]
    
    def save_range(self, param_name: str, min_val: float, max_val: float, 
                   is_exclusive: bool, range_id: Optional[int] = None):
        """Save or update a range."""
        cursor = self.conn.cursor()
        excl = 1 if is_exclusive else 0
        if range_id:
            cursor.execute(
                "UPDATE kb_ranges SET param_name=?, min_val=?, max_val=?, is_exclusive_upper=? WHERE id=?",
                (param_name, min_val, max_val, excl, range_id)
            )
        else:
            cursor.execute(
                "INSERT INTO kb_ranges (param_name, min_val, max_val, is_exclusive_upper) VALUES (?, ?, ?, ?)",
                (param_name, min_val, max_val, excl)
            )
        self.conn.commit()
    
    def delete_range(self, range_id: int):
        """Delete a range."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_ranges WHERE id=?", (range_id,))
        self.conn.commit()
    
    def get_severity_map(self) -> List[Dict]:
        """Get all severity mappings."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM kb_severity_map ORDER BY param_name, min_val")
        return [dict(row) for row in cursor.fetchall()]
    
    def save_severity(self, param_name: str, min_val: float, max_val: float, 
                      severity: int, sev_id: Optional[int] = None):
        """Save or update a severity mapping."""
        cursor = self.conn.cursor()
        if sev_id:
            cursor.execute(
                "UPDATE kb_severity_map SET param_name=?, min_val=?, max_val=?, severity=? WHERE id=?",
                (param_name, min_val, max_val, severity, sev_id)
            )
        else:
            cursor.execute(
                "INSERT INTO kb_severity_map (param_name, min_val, max_val, severity) VALUES (?, ?, ?, ?)",
                (param_name, min_val, max_val, severity)
            )
        self.conn.commit()
    
    def delete_severity(self, sev_id: int):
        """Delete a severity mapping."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM kb_severity_map WHERE id=?", (sev_id,))
        self.conn.commit()
    
    def export_kb(self, filepath: str):
        """Export KB to JSON file."""
        data = {
            'terms': self.get_terms(),
            'ranges': self.get_ranges(),
            'severity_map': self.get_severity_map(),
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_kb(self, filepath: str):
        """Import KB from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM kb_terms")
        cursor.execute("DELETE FROM kb_ranges")
        cursor.execute("DELETE FROM kb_severity_map")
        
        # Import terms
        for term in data.get('terms', []):
            cursor.execute(
                "INSERT INTO kb_terms (term_name, description) VALUES (?, ?)",
                (term['term_name'], term['description'])
            )
        
        # Import ranges
        for rng in data.get('ranges', []):
            cursor.execute(
                "INSERT INTO kb_ranges (param_name, min_val, max_val, is_exclusive_upper) VALUES (?, ?, ?, ?)",
                (rng['param_name'], rng['min_val'], rng['max_val'], rng['is_exclusive_upper'])
            )
        
        # Import severity map
        for sev in data.get('severity_map', []):
            cursor.execute(
                "INSERT INTO kb_severity_map (param_name, min_val, max_val, severity) VALUES (?, ?, ?, ?)",
                (sev['param_name'], sev['min_val'], sev['max_val'], sev['severity'])
            )
        
        self.conn.commit()
    
    def reset_to_defaults(self):
        """Reset KB to default values."""
        cursor = self.conn.cursor()
        cursor.execute("DROP TABLE kb_terms")
        cursor.execute("DROP TABLE kb_ranges")
        cursor.execute("DROP TABLE kb_severity_map")
        self._create_tables()
        self._init_defaults()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


class TermsEditorDialog(QWidget):
    """Widget for editing KB terms."""
    
    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setup_ui()
        self.load_terms()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Термин", "Описание"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_term)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self.edit_term)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_term)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_terms(self):
        terms = self.kb_db.get_terms()
        self.table.setRowCount(len(terms))
        for row, term in enumerate(terms):
            self.table.setItem(row, 0, QTableWidgetItem(str(term['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(term['term_name']))
            self.table.setItem(row, 2, QTableWidgetItem(term['description']))
    
    def add_term(self):
        dialog = TermEditDialog(self.kb_db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_terms()
    
    def edit_term(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите термин для редактирования")
            return
        
        term_id = int(self.table.item(row, 0).text())
        term_name = self.table.item(row, 1).text()
        description = self.table.item(row, 2).text()
        
        dialog = TermEditDialog(self.kb_db, self, term_id, term_name, description)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_terms()
    
    def delete_term(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите термин для удаления")
            return
        
        term_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить термин?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_term(term_id)
            self.load_terms()


class TermEditDialog(QDialog):
    """Dialog for editing a single term."""
    
    def __init__(self, kb_db: KBDatabase, parent=None, term_id: Optional[int] = None,
                 term_name: str = "", description: str = ""):
        super().__init__(parent)
        self.kb_db = kb_db
        self.term_id = term_id
        self.setWindowTitle("Добавление термина" if not term_id else "Редактирование термина")
        self.setup_ui(term_name, description)
    
    def setup_ui(self, term_name: str, description: str):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit(term_name)
        layout.addRow("Термин:", self.name_edit)
        
        self.desc_edit = QLineEdit(description)
        layout.addRow("Описание:", self.desc_edit)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def save(self):
        name = self.name_edit.text().strip()
        desc = self.desc_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название термина")
            return
        
        try:
            self.kb_db.save_term(name, desc, self.term_id)
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))


class RangesEditorDialog(QWidget):
    """Widget for editing normal ranges."""
    
    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setup_ui()
        self.load_ranges()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Параметр", "Мин", "Макс", "Искл. верх"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_range)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self.edit_range)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_range)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_ranges(self):
        ranges = self.kb_db.get_ranges()
        self.table.setRowCount(len(ranges))
        for row, rng in enumerate(ranges):
            self.table.setItem(row, 0, QTableWidgetItem(str(rng['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(rng['param_name']))
            self.table.setItem(row, 2, QTableWidgetItem(f"{rng['min_val']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{rng['max_val']:.2f}"))
            excl = "Да" if rng['is_exclusive_upper'] else "Нет"
            self.table.setItem(row, 4, QTableWidgetItem(excl))
    
    def add_range(self):
        dialog = RangeEditDialog(self.kb_db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_ranges()
    
    def edit_range(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите диапазон")
            return
        
        rng_id = int(self.table.item(row, 0).text())
        param = self.table.item(row, 1).text()
        min_v = float(self.table.item(row, 2).text())
        max_v = float(self.table.item(row, 3).text())
        excl = self.table.item(row, 4).text() == "Да"
        
        dialog = RangeEditDialog(self.kb_db, self, rng_id, param, min_v, max_v, excl)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_ranges()
    
    def delete_range(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите диапазон")
            return
        
        rng_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить диапазон?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_range(rng_id)
            self.load_ranges()


class RangeEditDialog(QDialog):
    """Dialog for editing a single range."""
    
    def __init__(self, kb_db: KBDatabase, parent=None, range_id: Optional[int] = None,
                 param: str = "", min_v: float = 0, max_v: float = 0, excl: bool = False):
        super().__init__(parent)
        self.kb_db = kb_db
        self.range_id = range_id
        self.setWindowTitle("Добавление диапазона" if not range_id else "Редактирование диапазона")
        self.setup_ui(param, min_v, max_v, excl)
    
    def setup_ui(self, param: str, min_v: float, max_v: float, excl: bool):
        layout = QFormLayout()
        
        self.param_combo = QComboBox()
        self.param_combo.addItems(['temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity'])
        if param:
            self.param_combo.setCurrentText(param)
        layout.addRow("Параметр:", self.param_combo)
        
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-100, 100)
        self.min_spin.setValue(min_v)
        self.min_spin.setDecimals(2)
        layout.addRow("Минимум:", self.min_spin)
        
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-100, 100)
        self.max_spin.setValue(max_v)
        self.max_spin.setDecimals(2)
        layout.addRow("Максимум:", self.max_spin)
        
        self.excl_check = QComboBox()
        self.excl_check.addItems(["Включительно", "Исключительно (верх)"])
        self.excl_check.setCurrentIndex(1 if excl else 0)
        layout.addRow("Верхняя граница:", self.excl_check)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def save(self):
        param = self.param_combo.currentText()
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        excl = self.excl_check.currentIndex() == 1
        
        if min_v >= max_v:
            QMessageBox.warning(self, "Ошибка", "Минимум должен быть меньше максимума")
            return
        
        self.kb_db.save_range(param, min_v, max_v, excl, self.range_id)
        self.accept()


class SeverityEditorDialog(QWidget):
    """Widget for editing severity mappings."""
    
    def __init__(self, kb_db: KBDatabase, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setup_ui()
        self.load_severity()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Параметр", "Мин", "Макс", "Severity"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_severity)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Изменить")
        self.edit_btn.clicked.connect(self.edit_severity)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_severity)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def load_severity(self):
        severity_map = self.kb_db.get_severity_map()
        self.table.setRowCount(len(severity_map))
        for row, sev in enumerate(severity_map):
            self.table.setItem(row, 0, QTableWidgetItem(str(sev['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(sev['param_name']))
            self.table.setItem(row, 2, QTableWidgetItem(f"{sev['min_val']:.2f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{sev['max_val']:.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(str(sev['severity'])))
    
    def add_severity(self):
        dialog = SeverityEditDialog(self.kb_db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_severity()
    
    def edit_severity(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return
        
        sev_id = int(self.table.item(row, 0).text())
        param = self.table.item(row, 1).text()
        min_v = float(self.table.item(row, 2).text())
        max_v = float(self.table.item(row, 3).text())
        severity = int(self.table.item(row, 4).text())
        
        dialog = SeverityEditDialog(self.kb_db, self, sev_id, param, min_v, max_v, severity)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_severity()
    
    def delete_severity(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите запись")
            return
        
        sev_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить запись?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_severity(sev_id)
            self.load_severity()


class SeverityEditDialog(QDialog):
    """Dialog for editing a single severity mapping."""
    
    def __init__(self, kb_db: KBDatabase, parent=None, sev_id: Optional[int] = None,
                 param: str = "", min_v: float = 0, max_v: float = 0, severity: int = 1):
        super().__init__(parent)
        self.kb_db = kb_db
        self.sev_id = sev_id
        self.setWindowTitle("Добавление severity" if not sev_id else "Редактирование severity")
        self.setup_ui(param, min_v, max_v, severity)
    
    def setup_ui(self, param: str, min_v: float, max_v: float, severity: int):
        layout = QFormLayout()
        
        self.param_combo = QComboBox()
        self.param_combo.addItems(['temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity'])
        if param:
            self.param_combo.setCurrentText(param)
        layout.addRow("Параметр:", self.param_combo)
        
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(-100, 100)
        self.min_spin.setValue(min_v)
        self.min_spin.setDecimals(3)
        layout.addRow("Минимум:", self.min_spin)
        
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(-100, 100)
        self.max_spin.setValue(max_v)
        self.max_spin.setDecimals(3)
        layout.addRow("Максимум:", self.max_spin)
        
        self.sev_spin = QSpinBox()
        self.sev_spin.setRange(1, 4)
        self.sev_spin.setValue(severity)
        layout.addRow("Severity (1-4):", self.sev_spin)
        
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def save(self):
        param = self.param_combo.currentText()
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        severity = self.sev_spin.value()
        
        if min_v >= max_v:
            QMessageBox.warning(self, "Ошибка", "Минимум должен быть меньше максимума")
            return
        
        self.kb_db.save_severity(param, min_v, max_v, severity, self.sev_id)
        self.accept()


class KBEditorWindow(QMainWindow):
    """Main Knowledge Base Editor window."""
    
    def __init__(self, db_path: str = "ras_monitor.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор базы знаний УЗВ")
        self.setGeometry(100, 100, 900, 600)
        
        self.kb_db = KBDatabase(db_path)
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab widget for different editors - open editors directly in tabs
        tabs = QTabWidget()
        
        # Terms tab - embed editor directly
        terms_widget = QWidget()
        terms_layout = QVBoxLayout()
        terms_layout.setContentsMargins(0, 0, 0, 0)
        self.terms_editor = TermsEditorDialog(self.kb_db)
        self.terms_editor.table.setMaximumHeight(300)
        # Remove close button from embedded dialog
        terms_layout.addWidget(self.terms_editor)
        terms_widget.setLayout(terms_layout)
        tabs.addTab(terms_widget, "Термины")
        
        # Ranges tab - embed editor directly
        ranges_widget = QWidget()
        ranges_layout = QVBoxLayout()
        ranges_layout.setContentsMargins(0, 0, 0, 0)
        self.ranges_editor = RangesEditorDialog(self.kb_db)
        self.ranges_editor.table.setMaximumHeight(300)
        ranges_layout.addWidget(self.ranges_editor)
        ranges_widget.setLayout(ranges_layout)
        tabs.addTab(ranges_widget, "Диапазоны")
        
        # Severity tab - embed editor directly
        severity_widget = QWidget()
        severity_layout = QVBoxLayout()
        severity_layout.setContentsMargins(0, 0, 0, 0)
        self.severity_editor = SeverityEditorDialog(self.kb_db)
        self.severity_editor.table.setMaximumHeight(300)
        severity_layout.addWidget(self.severity_editor)
        severity_widget.setLayout(severity_layout)
        tabs.addTab(severity_widget, "Степени тяжести")
        
        layout.addWidget(tabs)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Сохранить БЗ в файл")
        self.save_btn.clicked.connect(self.export_kb)
        btn_layout.addWidget(self.save_btn)
        
        self.load_btn = QPushButton("Загрузить БЗ из файла")
        self.load_btn.clicked.connect(self.import_kb)
        btn_layout.addWidget(self.load_btn)
        
        self.reset_btn = QPushButton("Сбросить к значениям по умолчанию")
        self.reset_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.reset_btn.clicked.connect(self.reset_kb)
        btn_layout.addWidget(self.reset_btn)
        
        btn_layout.addStretch()
        
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        layout.addLayout(btn_layout)
        central_widget.setLayout(layout)
    
    def export_kb(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Экспорт базы знаний", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                self.kb_db.export_kb(filepath)
                QMessageBox.information(self, "Успех", f"База знаний экспортирована в {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")
    
    def import_kb(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Импорт базы знаний", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                self.kb_db.import_kb(filepath)
                QMessageBox.information(self, "Успех", "База знаний импортирована")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка импорта: {e}")
    
    def reset_kb(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены? Все изменения будут потеряны.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.reset_to_defaults()
            QMessageBox.information(self, "Успех", "База знаний сброшена к значениям по умолчанию")
    
    def closeEvent(self, event):
        self.kb_db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = KBEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
