# [FILE: ras_monitor/ui/report_dialog.py]
"""
Report export dialog for RAS monitoring system.
Allows user to select date range and export data to CSV.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QDateEdit, QComboBox, QMessageBox,
    QGroupBox
)
from PyQt6.QtCore import QDate
from PyQt6.QtGui import QFont

from core.report_export import ReportExporter


class ReportDialog(QDialog):
    """Dialog for exporting reports for a specified period."""
    
    def __init__(self, db_path: str = "ras_monitor.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт отчёта за период")
        self.setGeometry(100, 100, 450, 300)
        self.setModal(True)
        
        self.report_exporter = ReportExporter(db_path)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Date range group
        date_group = QGroupBox("Период отчёта")
        date_layout = QFormLayout()
        date_layout.setSpacing(10)
        
        # Start date
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        self.start_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.start_date_edit.setFont(QFont("Arial", 11))
        date_layout.addRow("Дата начала:", self.start_date_edit)
        
        # End date
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.end_date_edit.setFont(QFont("Arial", 11))
        date_layout.addRow("Дата окончания:", self.end_date_edit)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        # Format selection
        format_group = QGroupBox("Формат экспорта")
        format_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF"])
        self.format_combo.setEnabled(False)  # Only PDF for now
        format_layout.addWidget(QLabel("Формат:"))
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.export_btn = QPushButton("📄 Экспорт в PDF")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(self.export_btn)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def export_report(self):
        """Export report for selected period."""
        # Get dates
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        
        # Set time to include full days
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Validate date range
        if start_datetime > end_datetime:
            QMessageBox.warning(
                self, "Ошибка",
                "Дата начала должна быть раньше даты окончания"
            )
            return
        
        try:
            # Export to PDF
            filepath = self.report_exporter.export_to_pdf(start_datetime, end_datetime)
            
            QMessageBox.information(
                self, "Успех",
                f"Отчёт успешно экспортирован:\n{filepath}"
            )
            self.accept()
            
        except ValueError as e:
            QMessageBox.warning(
                self, "Нет данных",
                str(e)
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка экспорта",
                f"Произошла ошибка при экспорте:\n{e}"
            )
    
    def closeEvent(self, event):
        self.report_exporter.close()
        event.accept()
