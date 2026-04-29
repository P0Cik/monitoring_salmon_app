# [FILE: ras_monitor/ui/main_window.py]
"""
Main window UI for RAS monitoring system.
Built with PyQt6, includes input form, charts, status cards, and history table.
"""

import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import application modules
sys.path.insert(0, '..')
from core.solver import Solver, MeasurementData, SolverResult
from core.db import Database
from ml.predictor import Predictor


class StatusCard(QFrame):
    """Styled card widget for displaying status information."""
    
    def __init__(self, title: str, value: str = "", color: str = "#ffffff"):
        super().__init__()
        self.title = title
        self.value = value
        self.color = color
        
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Set up the card UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.color};
                border-radius: 8px;
                border: 1px solid #cccccc;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Title label
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Value label
        self.value_label = QLabel(self.value)
        self.value_label.setFont(QFont("Arial", 14))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)
        
        self.setLayout(layout)
    
    def update_value(self, value: str, color: Optional[str] = None) -> None:
        """Update the card value and optionally color."""
        self.value = value
        self.value_label.setText(value)
        if color:
            self.color = color
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 8px;
                    border: 1px solid #cccccc;
                    padding: 10px;
                }}
            """)


class MplCanvas(FigureCanvas):
    """Matplotlib canvas for embedding in PyQt6."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Set minimum size
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)


class MainWindow(QMainWindow):
    """
    Main application window for RAS monitoring.
    
    Layout:
    - Left: Input form for 6 parameters + Add button
    - Center: Matplotlib chart with time series
    - Right: Status cards (current state, dynamics, forecast, suitability)
    - Bottom: History table
    """
    
    # Color mapping for states
    STATE_COLORS = {
        0: "#90EE90",  # Light green - normal
        1: "#FFFF99",  # Light yellow - deviation
        2: "#FFD700",  # Gold - unstable
        3: "#FFA500",  # Orange - threat
        4: "#FF6347",  # Tomato - critical
    }
    
    DYNAMICS_COLORS = {
        "Стабильно": "#90EE90",
        "Улучшение": "#87CEEB",
        "Ухудшение": "#FFB6C1",
    }
    
    SUITABILITY_COLORS = {
        "пригодна": "#90EE90",
        "непригодна": "#FF6347",
    }
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.db = Database("ras_monitor.db")
        self.solver = Solver()
        self.predictor = Predictor()
        
        # Try to load ML model
        self.ml_available = self.predictor.load_model()
        
        # Store recent measurements for chart
        self.measurements_history: List[Dict[str, Any]] = []
        
        # Setup UI
        self.setWindowTitle("RAS Monitor - Система мониторинга водной среды УЗВ")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setup_ui()
        self.load_history()
        
        # Auto-refresh timer (optional)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_chart)
        # self.refresh_timer.start(30000)  # Refresh every 30 seconds
    
    def setup_ui(self) -> None:
        """Set up the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top section: Input form + Chart + Status cards
        top_section = QHBoxLayout()
        top_section.setSpacing(10)
        
        # Left: Input form
        input_group = self.create_input_form()
        top_section.addWidget(input_group, stretch=1)
        
        # Center: Chart
        chart_group = self.create_chart_section()
        top_section.addWidget(chart_group, stretch=2)
        
        # Right: Status cards
        cards_group = self.create_status_cards()
        top_section.addWidget(cards_group, stretch=1)
        
        main_layout.addLayout(top_section, stretch=2)
        
        # Bottom: History table
        table_group = self.create_history_table()
        main_layout.addWidget(table_group, stretch=1)
        
        central_widget.setLayout(main_layout)
    
    def create_input_form(self) -> QGroupBox:
        """Create the input form for measurement parameters."""
        group = QGroupBox("Ввод параметров")
        layout = QGridLayout()
        layout.setSpacing(8)
        
        # Parameter fields with labels and units
        params = [
            ("temp", "Температура", "°C", 13.0),
            ("ph", "pH", "", 7.6),
            ("o2", "Кислород (O₂)", "%", 95.0),
            ("ammonia", "Аммиак (NH₃)", "мг/л", 0.2),
            ("nitrite", "Нитриты (NO₂)", "мг/л", 0.05),
            ("salinity", "Солёность", "‰", 0.0),
        ]
        
        self.input_fields: Dict[str, QLineEdit] = {}
        
        for i, (key, label, unit, default) in enumerate(params):
            lbl = QLabel(f"{label}:")
            lbl.setFont(QFont("Arial", 10))
            layout.addWidget(lbl, i, 0)
            
            field = QLineEdit()
            field.setText(str(default))
            field.setPlaceholderText(f"в {unit}")
            self.input_fields[key] = field
            layout.addWidget(field, i, 1)
            
            if unit:
                unit_lbl = QLabel(unit)
                unit_lbl.setFont(QFont("Arial", 9))
                layout.addWidget(unit_lbl, i, 2)
        
        # Add button
        add_btn = QPushButton("Добавить замер")
        add_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_btn.clicked.connect(self.add_measurement)
        layout.addWidget(add_btn, len(params), 0, 1, 3)
        
        group.setLayout(layout)
        return group
    
    def create_chart_section(self) -> QGroupBox:
        """Create the matplotlib chart section."""
        group = QGroupBox("График параметров")
        layout = QVBoxLayout()
        
        # Create matplotlib canvas
        self.canvas = MplCanvas(self, width=8, height=5, dpi=80)
        layout.addWidget(self.canvas)
        
        # Initial plot
        self.plot_data()
        
        group.setLayout(layout)
        return group
    
    def create_status_cards(self) -> QGroupBox:
        """Create the status information cards."""
        group = QGroupBox("Состояние системы")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Current state card
        self.card_current_state = StatusCard("Текущее состояние", "—", "#f0f0f0")
        layout.addWidget(self.card_current_state)
        
        # Suitability card
        self.card_suitability = StatusCard("Пригодность", "—", "#f0f0f0")
        layout.addWidget(self.card_suitability)
        
        # Past dynamics card
        self.card_past_dynamics = StatusCard("Динамика (факт)", "—", "#f0f0f0")
        layout.addWidget(self.card_past_dynamics)
        
        # Forecast dynamics card
        self.card_forecast_dynamics = StatusCard("Прогноз на t+1", "—", "#f0f0f0")
        layout.addWidget(self.card_forecast_dynamics)
        
        # Forecast confidence (only shown when ML available)
        self.card_confidence = StatusCard("Достоверность прогноза", "—", "#f0f0f0")
        if not self.ml_available:
            self.card_confidence.update_value("ML не доступен", "#ffcccc")
        layout.addWidget(self.card_confidence)
        
        # Spacer
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def create_history_table(self) -> QGroupBox:
        """Create the history data table."""
        group = QGroupBox("История замеров")
        layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Время", "Temp", "pH", "O₂", "NH₃", "NO₂", "Sal", "Состояние", "Прогноз"
        ])
        
        # Configure table
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dddddd;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        
        layout.addWidget(self.history_table)
        group.setLayout(layout)
        return group
    
    def get_input_values(self) -> Optional[MeasurementData]:
        """
        Get values from input fields.
        
        Returns:
            MeasurementData if all fields are valid, None otherwise
        """
        try:
            return MeasurementData(
                temp=float(self.input_fields['temp'].text().replace(',', '.')),
                ph=float(self.input_fields['ph'].text().replace(',', '.')),
                o2=float(self.input_fields['o2'].text().replace(',', '.')),
                ammonia=float(self.input_fields['ammonia'].text().replace(',', '.')),
                nitrite=float(self.input_fields['nitrite'].text().replace(',', '.')),
                salinity=float(self.input_fields['salinity'].text().replace(',', '.')),
            )
        except ValueError as e:
            QMessageBox.warning(
                self,
                "Ошибка ввода",
                f"Проверьте корректность введённых значений.\nОшибка: {e}"
            )
            return None
    
    def add_measurement(self) -> None:
        """Add a new measurement to the database and update UI."""
        data = self.get_input_values()
        if data is None:
            return
        
        # Get previous state for dynamics calculation
        previous_state = self.db.get_last_state()
        
        # Evaluate with solver
        result = self.solver.evaluate(data, previous_state)
        
        # Save measurement to database
        measurement_id = self.db.add_measurement(
            temp=data.temp,
            ph=data.ph,
            o2=data.o2,
            ammonia=data.ammonia,
            nitrite=data.nitrite,
            salinity=data.salinity,
        )
        
        # Get forecast if ML is available
        forecast_dynamics = "—"
        forecast_confidence = None
        
        if self.ml_available:
            recent = self.db.get_recent_measurements_for_ml(window_size=6)
            if recent is not None:
                probs = self.predictor.predict(recent)
                if probs:
                    forecast_dynamics = self.predictor.get_forecast_dynamics(
                        result.current_state, probs
                    )
                    forecast_confidence = self.predictor.get_confidence(probs)
        
        # Save history record
        self.db.add_history(
            measurement_id=measurement_id,
            current_state=result.current_state,
            suitability=result.suitability,
            past_dynamics=result.past_dynamics,
            forecast_dynamics=forecast_dynamics if forecast_dynamics != "—" else None,
            forecast_confidence=forecast_confidence,
        )
        
        # Update UI
        self.update_status_cards(result, forecast_dynamics, forecast_confidence)
        self.refresh_chart()
        self.load_history()
        
        # Show success message
        QMessageBox.information(
            self,
            "Замер добавлен",
            f"Состояние: {self.solver.get_state_description(result.current_state)}\n"
            f"Пригодность: {result.suitability}\n"
            f"Динамика: {result.past_dynamics}"
        )
    
    def update_status_cards(
        self, 
        result: SolverResult,
        forecast_dynamics: str,
        forecast_confidence: Optional[float]
    ) -> None:
        """Update the status cards with new data."""
        # Current state
        state_desc = self.solver.get_state_description(result.current_state)
        state_color = self.STATE_COLORS.get(result.current_state, "#f0f0f0")
        self.card_current_state.update_value(state_desc, state_color)
        
        # Suitability
        suit_color = self.SUITABILITY_COLORS.get(result.suitability, "#f0f0f0")
        self.card_suitability.update_value(result.suitability, suit_color)
        
        # Past dynamics
        dyn_color = self.DYNAMICS_COLORS.get(result.past_dynamics, "#f0f0f0")
        self.card_past_dynamics.update_value(result.past_dynamics, dyn_color)
        
        # Forecast dynamics
        if forecast_dynamics and forecast_dynamics != "—":
            forecast_color = self.DYNAMICS_COLORS.get(forecast_dynamics, "#f0f0f0")
            self.card_forecast_dynamics.update_value(forecast_dynamics, forecast_color)
        else:
            self.card_forecast_dynamics.update_value("Недостаточно данных", "#f0f0f0")
        
        # Forecast confidence
        if forecast_confidence is not None:
            conf_text = f"{forecast_confidence * 100:.1f}%"
            if forecast_confidence > 0.7:
                conf_color = "#90EE90"
            elif forecast_confidence > 0.4:
                conf_color = "#FFD700"
            else:
                conf_color = "#FFB6C1"
            self.card_confidence.update_value(conf_text, conf_color)
    
    def plot_data(self) -> None:
        """Plot measurement data on the chart."""
        self.canvas.axes.clear()
        
        if not self.measurements_history:
            self.canvas.axes.text(0.5, 0.5, "Нет данных для отображения", 
                                 transform=self.canvas.axes.transAxes,
                                 ha='center', va='center', fontsize=14)
            self.canvas.draw()
            return
        
        # Prepare data for plotting
        timestamps = []
        params = {
            'temp': [], 'ph': [], 'o2': [],
            'ammonia': [], 'nitrite': [], 'salinity': []
        }
        
        for m in self.measurements_history[-50:]:  # Last 50 measurements
            timestamps.append(m.get('timestamp', '')[:16])  # Short timestamp
            params['temp'].append(m.get('temp', 0))
            params['ph'].append(m.get('ph', 0))
            params['o2'].append(m.get('o2', 0))
            params['ammonia'].append(m.get('ammonia', 0))
            params['nitrite'].append(m.get('nitrite', 0))
            params['salinity'].append(m.get('salinity', 0))
        
        # Plot each parameter
        colors = {
            'temp': 'red', 'ph': 'blue', 'o2': 'green',
            'ammonia': 'orange', 'nitrite': 'purple', 'salinity': 'brown'
        }
        
        for param, values in params.items():
            self.canvas.axes.plot(
                range(len(values)), values,
                label=f"{param}",
                color=colors[param],
                linewidth=1.5,
                marker='o',
                markersize=3
            )
        
        # Formatting
        self.canvas.axes.set_xlabel("Замеры")
        self.canvas.axes.set_ylabel("Значение")
        self.canvas.axes.set_title("Динамика параметров водной среды")
        self.canvas.axes.legend(loc='upper left', bbox_to_anchor=(1, 1))
        self.canvas.axes.grid(True, alpha=0.3)
        
        # Rotate x-axis labels
        self.canvas.fig.autofmt_xdate()
        
        self.canvas.draw()
    
    def refresh_chart(self) -> None:
        """Refresh the chart with latest data."""
        self.load_history()
        self.plot_data()
    
    def load_history(self) -> None:
        """Load history from database and update table and chart data."""
        history = self.db.get_history_with_measurements(limit=100)
        self.measurements_history = history
        
        # Update table
        self.history_table.setRowCount(len(history))
        
        for row, record in enumerate(reversed(history)):  # Newest first
            self.history_table.setItem(row, 0, QTableWidgetItem(str(record.get('id', ''))))
            self.history_table.setItem(row, 1, QTableWidgetItem(
                record.get('timestamp', '')[:16].replace('T', ' ')
            ))
            self.history_table.setItem(row, 2, QTableWidgetItem(f"{record.get('temp', 0):.2f}"))
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{record.get('ph', 0):.2f}"))
            self.history_table.setItem(row, 4, QTableWidgetItem(f"{record.get('o2', 0):.1f}"))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{record.get('ammonia', 0):.3f}"))
            self.history_table.setItem(row, 6, QTableWidgetItem(f"{record.get('nitrite', 0):.3f}"))
            self.history_table.setItem(row, 7, QTableWidgetItem(f"{record.get('salinity', 0):.2f}"))
            
            # State with color
            state = record.get('current_state', 0)
            state_item = QTableWidgetItem(self.solver.get_state_description(state))
            state_bg = self.STATE_COLORS.get(state, "#ffffff")
            state_item.setBackground(self._qcolor_from_hex(state_bg))
            self.history_table.setItem(row, 8, state_item)
            
            # Forecast
            forecast = record.get('forecast_dynamics') or "—"
            self.history_table.setItem(row, 9, QTableWidgetItem(forecast))
    
    def _qcolor_from_hex(self, hex_color: str) -> any:
        """Convert hex color to QColor."""
        from PyQt6.QtGui import QColor
        return QColor(hex_color)
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.db.close()
        event.accept()
