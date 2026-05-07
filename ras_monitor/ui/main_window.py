# [FILE: ras_monitor/ui/main_window.py]
"""
Main window UI for RAS monitoring system.
Built with PyQt6, includes input form, charts, status cards, and history table.
"""

import sys
import os
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QScrollArea, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.solver import Solver, MeasurementData, SolverResult
from core.db import Database
from ml.predictor import Predictor


class MLForecastCard(QFrame):
    """Enhanced card widget for ML forecast with probability visualization."""

    def __init__(self, title: str = "Прогноз ML"):
        super().__init__()
        self.title = title
        self.probabilities = {}
        self.confidence = 0.0
        self.forecast_dynamics = "—"

        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the enhanced forecast card UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2A2A35;
                border-radius: 8px;
                border: 1px solid #3A3A45;
                padding: 8px;
                color: #E0E0E0;
            }
            QFrame:hover {
                border: 1px solid #5A5A65;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #AAAAAA;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Forecast dynamics
        self.dynamics_label = QLabel("—")
        self.dynamics_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.dynamics_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dynamics_label.setStyleSheet("color: #E0E0E0;")
        self.dynamics_label.setWordWrap(True)
        layout.addWidget(self.dynamics_label)

        # Confidence indicator
        conf_layout = QHBoxLayout()
        conf_layout.setSpacing(4)
        conf_label = QLabel("Уверенность:")
        conf_label.setStyleSheet("font-size: 8pt; color: #AAAAAA;")
        conf_label.setWordWrap(False)
        conf_label.setMinimumWidth(80)
        conf_layout.addWidget(conf_label)
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setTextVisible(True)
        self.confidence_bar.setMaximumHeight(16)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3A3A45;
                border-radius: 3px;
                text-align: center;
                background-color: #1E1E24;
                color: #E0E0E0;
                font-size: 8pt;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        conf_layout.addWidget(self.confidence_bar)
        layout.addLayout(conf_layout)

        # Probabilities section
        prob_label = QLabel("Вероятности состояний:")
        prob_label.setFont(QFont("Arial", 8))
        prob_label.setStyleSheet("color: #AAAAAA;")
        prob_label.setWordWrap(True)
        layout.addWidget(prob_label)

        # Create progress bars for each state
        self.state_bars = {}
        state_names = {
            1: "Отходящее",
            2: "Неустойчивое",
            3: "Угроза",
            4: "Критическое"
        }

        for state_id, state_name in state_names.items():
            state_layout = QHBoxLayout()
            state_layout.setSpacing(4)

            # State label with number and name
            label = QLabel(f"{state_id}.")
            label.setStyleSheet("color: #AAAAAA; font-size: 8pt;")
            label.setWordWrap(False)
            label.setFixedWidth(15)
            state_layout.addWidget(label)

            name_label = QLabel(state_name)
            name_label.setStyleSheet("color: #AAAAAA; font-size: 8pt;")
            name_label.setWordWrap(False)
            name_label.setMinimumWidth(80)
            state_layout.addWidget(name_label)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(True)
            bar.setMaximumHeight(14)
            bar.setMinimumWidth(50)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid #3A3A45;
                    border-radius: 2px;
                    text-align: center;
                    background-color: #1E1E24;
                    color: #E0E0E0;
                    font-size: 7pt;
                }}
                QProgressBar::chunk {{
                    background-color: {self._get_state_color(state_id)};
                }}
            """)
            state_layout.addWidget(bar, 1)

            layout.addLayout(state_layout)
            self.state_bars[state_id] = bar

        self.setLayout(layout)

    def _get_state_color(self, state_id: int) -> str:
        """Get color for state."""
        colors = {
            1: "#FFC107",  # Yellow
            2: "#FF9800",  # Orange
            3: "#FF5722",  # Deep Orange
            4: "#F44336",  # Red
        }
        return colors.get(state_id, "#4CAF50")

    def update_forecast(
        self,
        dynamics: str,
        confidence: float,
        probabilities: Dict[int, float]
    ) -> None:
        """Update the forecast card with new ML predictions."""
        self.forecast_dynamics = dynamics
        self.confidence = confidence
        self.probabilities = probabilities

        # Update dynamics label
        self.dynamics_label.setText(dynamics)

        # Update confidence bar
        conf_percent = int(confidence * 100)
        self.confidence_bar.setValue(conf_percent)

        # Update confidence bar color based on value
        if confidence > 0.7:
            chunk_color = "#4CAF50"  # Green
        elif confidence > 0.5:
            chunk_color = "#FFC107"  # Yellow
        else:
            chunk_color = "#F44336"  # Red

        self.confidence_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #3A3A45;
                border-radius: 3px;
                text-align: center;
                background-color: #1E1E24;
                color: #E0E0E0;
            }}
            QProgressBar::chunk {{
                background-color: {chunk_color};
            }}
        """)

        # Update state probability bars
        for state_id, bar in self.state_bars.items():
            prob = probabilities.get(state_id, 0.0)
            prob_percent = int(prob * 100)
            bar.setValue(prob_percent)
            bar.setFormat(f"{prob_percent}%")

    def clear_forecast(self) -> None:
        """Clear forecast display."""
        self.dynamics_label.setText("Недостаточно данных")
        self.confidence_bar.setValue(0)
        for bar in self.state_bars.values():
            bar.setValue(0)
            bar.setFormat("0%")


class StatusCard(QFrame):
    """Styled card widget for displaying status information."""
    
    def __init__(self, title: str, value: str = "", color: str = "#2A2A35"):
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
                border: 1px solid #3A3A45;
                padding: 12px;
                color: #E0E0E0;
            }}
            QFrame:hover {{
                border: 1px solid #5A5A65;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Title label
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #AAAAAA;")
        layout.addWidget(self.title_label)
        
        # Value label
        self.value_label = QLabel(self.value)
        self.value_label.setFont(QFont("Arial", 14))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(True)
        self.value_label.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(self.value_label)
        
        self.setLayout(layout)
    
    def update_value(self, value: str, color: Optional[str] = None, tooltip: Optional[str] = None) -> None:
        """Update the card value and optionally color and tooltip."""
        self.value = value
        self.value_label.setText(value)

        # Set tooltip if provided
        if tooltip:
            self.setToolTip(tooltip)
            self.value_label.setToolTip(tooltip)

        if color:
            self.color = color
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 8px;
                    border: 1px solid #3A3A45;
                    padding: 12px;
                    color: #FFFFFF;
                }}
                QFrame:hover {{
                    border: 1px solid #5A5A65;
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
        self.setMinimumHeight(150)


class MainWindow(QMainWindow):
    """
    Main application window for RAS monitoring.
    
    Layout:
    - Left: Input form for 6 parameters + Add button
    - Center: Matplotlib chart with time series
    - Right: Status cards (current state, dynamics, forecast, suitability)
    - Bottom: History table
    """
    
    # Color mapping for states - semantic colors as per requirements
    STATE_COLORS = {
        0: "#2A2A35",  # Dark gray - normal (default card color)
        1: "#4CAF50",  # Green - отходящее от нормы
        2: "#FFC107",  # Yellow - неустойчивое
        3: "#FF9800",  # Orange - угроза
        4: "#F44336",  # Red - критическое
    }
    
    DYNAMICS_COLORS = {
        "Стабильно": "#4CAF50",
        "Улучшение": "#2196F3",
        "Ухудшение": "#F44336",
    }
    
    SUITABILITY_COLORS = {
        "пригодна": "#4CAF50",
        "непригодна": "#F44336",
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
        self.setWindowTitle("Система мониторинга водной среды УЗВ")
        self.setGeometry(100, 100, 1400, 900)
        
        self.create_menu_bar()
        self.setup_ui()
        self.load_history()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_chart)
    
    def create_menu_bar(self):
        """Create menu bar with additional features."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2A2A35;
                color: #E0E0E0;
                border-bottom: 1px solid #3A3A45;
            }
            QMenuBar::item:selected {
                background-color: #3A3A45;
            }
            QMenu {
                background-color: #2A2A35;
                color: #E0E0E0;
                border: 1px solid #3A3A45;
            }
            QMenu::item:selected {
                background-color: #3A3A45;
            }
        """)
        
        # Tools menu
        tools_menu = menubar.addMenu("Инструменты")
        
        # KB Editor action
        kb_action = tools_menu.addAction("Редактор БЗ")
        kb_action.setShortcut("Ctrl+K")
        kb_action.triggered.connect(self.open_kb_editor)
        
        # Report export action
        report_action = tools_menu.addAction("Экспорт отчёта")
        report_action.setShortcut("Ctrl+E")
        report_action.triggered.connect(self.open_report_dialog)
        
        # Separator
        tools_menu.addSeparator()
        
        # Mock data generator action
        mock_action = tools_menu.addAction("Генератор тестовых данных")
        mock_action.triggered.connect(self.generate_mock_data)
    
    def setup_ui(self) -> None:
        """Set up the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Apply main window dark theme stylesheet
        central_widget.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E24;
            }
            QWidget {
                background-color: #1E1E24;
                color: #E0E0E0;
            }
            QGroupBox {
                background-color: #2A2A35;
                border: 1px solid #3A3A45;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #E0E0E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #AAAAAA;
            }
            QTableWidget {
                background-color: #2A2A35;
                alternate-background-color: #32323D;
                color: #E0E0E0;
                gridline-color: #3A3A45;
                border: 1px solid #3A3A45;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3A3A45;
                color: #E0E0E0;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #3A3A45;
                border: 1px solid #4A4A55;
                border-radius: 4px;
                padding: 6px;
                color: #E0E0E0;
            }
            QLineEdit:focus {
                border: 1px solid #5A5A65;
            }
            QLabel {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

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
        """Create the matplotlib chart section with separate charts for each parameter."""
        group = QGroupBox("Графики параметров")
        layout = QVBoxLayout()
        
        # Create a scroll area for multiple charts
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container widget for charts
        charts_container = QWidget()
        charts_layout = QVBoxLayout()
        charts_layout.setSpacing(15)
        
        # Define parameters and their colors (unified color scheme)
        self.param_configs = {
            'temp': {'label': 'Температура', 'unit': '°C', 'color': '#E74C3C'},
            'ph': {'label': 'pH', 'unit': '', 'color': '#3498DB'},
            'o2': {'label': 'Кислород (O₂)', 'unit': '%', 'color': '#2ECC71'},
            'ammonia': {'label': 'Аммиак (NH₃)', 'unit': 'мг/л', 'color': '#F39C12'},
            'nitrite': {'label': 'Нитриты (NO₂)', 'unit': 'мг/л', 'color': '#9B59B6'},
            'salinity': {'label': 'Солёность', 'unit': '‰', 'color': '#1ABC9C'},
        }
        
        # Create separate canvas for each parameter
        self.param_canvases = {}
        for param, config in self.param_configs.items():
            canvas = MplCanvas(self, width=6, height=1.5, dpi=80)
            self.param_canvases[param] = canvas
            charts_layout.addWidget(canvas)
        
        charts_container.setLayout(charts_layout)
        scroll_area.setWidget(charts_container)
        layout.addWidget(scroll_area)
        
        # Initial plots
        self.plot_data()
        
        group.setLayout(layout)
        return group
    
    def create_status_cards(self) -> QGroupBox:
        """Create the status information cards."""
        group = QGroupBox("Состояние системы")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Current state card
        self.card_current_state = StatusCard("Текущее состояние", "—", "#1E1E24")
        layout.addWidget(self.card_current_state)

        # Suitability card
        self.card_suitability = StatusCard("Пригодность", "—", "#1E1E24")
        layout.addWidget(self.card_suitability)

        # Past dynamics card
        self.card_past_dynamics = StatusCard("Динамика (факт)", "—", "#1E1E24")
        layout.addWidget(self.card_past_dynamics)

        # ML Forecast card (enhanced with probabilities)
        self.card_ml_forecast = MLForecastCard("Прогноз ML (t+1)")
        if not self.ml_available:
            self.card_ml_forecast.dynamics_label.setText("ML не доступен")
            self.card_ml_forecast.dynamics_label.setStyleSheet("color: #F44336;")
        layout.addWidget(self.card_ml_forecast)

        # Spacer
        layout.addStretch()

        group.setLayout(layout)
        return group
    
    def create_history_table(self) -> QGroupBox:
        """Create the history data table."""
        group = QGroupBox("История замеров")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Время", "С", "pH", "O₂", "NH₃", "NO₂", "Sal", "Состояние", "Прогноз"
        ])
        
        # Configure table - increased size
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setMinimumHeight(250)  # Increased minimum height
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #2A2A35;
                alternate-background-color: #32323D;
                color: #E0E0E0;
                gridline-color: #3A3A45;
                border: 1px solid #3A3A45;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3A3A45;
                color: #E0E0E0;
                padding: 10px;
                border: none;
                font-weight: bold;
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
        forecast_probs = None

        if self.ml_available:
            recent = self.db.get_recent_measurements_for_ml(window_size=6)
            if recent is not None:
                probs = self.predictor.predict(recent)
                if probs:
                    forecast_probs = probs
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
        self.update_status_cards(result, forecast_dynamics, forecast_confidence, forecast_probs)
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
        forecast_confidence: Optional[float],
        forecast_probs: Optional[Dict[int, float]] = None
    ) -> None:
        """Update the status cards with new data."""
        # Current state with tooltip
        state_desc = self.solver.get_state_description(result.current_state)
        state_color = self.STATE_COLORS.get(result.current_state, "#f0f0f0")

        # Build state tooltip
        state_tooltip = self._build_state_tooltip(result)
        self.card_current_state.update_value(state_desc, state_color, state_tooltip)

        # Suitability with tooltip
        suit_color = self.SUITABILITY_COLORS.get(result.suitability, "#f0f0f0")
        suit_tooltip = self._build_suitability_tooltip(result)
        self.card_suitability.update_value(result.suitability, suit_color, suit_tooltip)

        # Past dynamics
        dyn_color = self.DYNAMICS_COLORS.get(result.past_dynamics, "#f0f0f0")
        self.card_past_dynamics.update_value(result.past_dynamics, dyn_color)

        # ML Forecast card
        if forecast_dynamics and forecast_dynamics != "—" and forecast_confidence is not None and forecast_probs:
            self.card_ml_forecast.update_forecast(
                dynamics=forecast_dynamics,
                confidence=forecast_confidence,
                probabilities=forecast_probs
            )
        else:
            self.card_ml_forecast.clear_forecast()

    def _build_state_tooltip(self, result: SolverResult) -> str:
        """Build tooltip explaining why this state was determined."""
        lines = [f"Состояние: {self.solver.get_state_description(result.current_state)}"]
        lines.append("")
        lines.append("Причины:")

        param_names = {
            'temp': 'Температура',
            'ph': 'pH',
            'o2': 'Кислород',
            'ammonia': 'Аммиак',
            'nitrite': 'Нитриты',
            'salinity': 'Солёность'
        }

        # Show parameters that are out of normal range
        abnormal_params = []
        for param, severity in result.parameter_states.items():
            if severity > 0:
                abnormal_params.append(f"• {param_names.get(param, param)}: уровень тяжести {severity}")

        if abnormal_params:
            lines.extend(abnormal_params)
        else:
            lines.append("• Все параметры в норме")

        return "\n".join(lines)

    def _build_suitability_tooltip(self, result: SolverResult) -> str:
        """Build tooltip explaining why this suitability was determined."""
        lines = [f"Пригодность: {result.suitability}"]
        lines.append("")

        if result.suitability == "пригодна":
            lines.append("Все параметры находятся в пределах нормы:")
            lines.append("• Температура: [12.0; 14.0] °C")
            lines.append("• pH: [7.4; 7.8]")
            lines.append("• O₂: [90; 100] %")
            lines.append("• Аммиак: [0; 0.5) мг/л")
            lines.append("• Нитриты: [0; 0.1) мг/л")
            lines.append("• Солёность: 0 ‰")
        else:
            lines.append("Один или несколько параметров вышли за пределы нормы.")
            lines.append("")
            lines.append("Параметры с отклонениями:")

            param_names = {
                'temp': 'Температура',
                'ph': 'pH',
                'o2': 'Кислород',
                'ammonia': 'Аммиак',
                'nitrite': 'Нитриты',
                'salinity': 'Солёность'
            }

            for param, severity in result.parameter_states.items():
                if severity > 0:
                    lines.append(f"• {param_names.get(param, param)}: тяжесть {severity}")

        return "\n".join(lines)
    
    def plot_data(self) -> None:
        """Plot measurement data on separate charts for each parameter."""
        if not self.measurements_history:
            # Clear all canvases and show "no data" message
            for param, canvas in self.param_canvases.items():
                canvas.axes.clear()
                canvas.axes.text(0.5, 0.5, "Нет данных", 
                                 transform=canvas.axes.transAxes,
                                 ha='center', va='center', fontsize=12, color='#888888')
                canvas.axes.set_facecolor('#1E1E24')
                canvas.draw()
            return
        
        # Prepare data for plotting (last 50 measurements)
        params_data = {
            'temp': [],
            'ph': [], 
            'o2': [],
            'ammonia': [],
            'nitrite': [],
            'salinity': []
        }
        
        for m in self.measurements_history[-50:]:
            params_data['temp'].append(m.get('temp', 0))
            params_data['ph'].append(m.get('ph', 0))
            params_data['o2'].append(m.get('o2', 0))
            params_data['ammonia'].append(m.get('ammonia', 0))
            params_data['nitrite'].append(m.get('nitrite', 0))
            params_data['salinity'].append(m.get('salinity', 0))
        
        # Plot each parameter on its own chart with unified colors
        for param, values in params_data.items():
            config = self.param_configs[param]
            canvas = self.param_canvases[param]
            canvas.axes.clear()
            
            # Plot the line with unified color scheme
            canvas.axes.plot(
                range(len(values)), values,
                color=config['color'],
                linewidth=2,
                marker='o',
                markersize=4,
                markerfacecolor=config['color'],
                markeredgecolor='#1E1E24',
                markeredgewidth=1
            )
            
            # Fill area under the line
            canvas.axes.fill_between(
                range(len(values)), values, 
                alpha=0.3, color=config['color']
            )
            
            # Styling with unified dark theme
            canvas.axes.set_title(f"{config['label']}", fontsize=11, weight='bold', color='#E0E0E0')
            canvas.axes.set_ylabel(config['unit'], fontsize=9, color='#AAAAAA')
            canvas.axes.grid(True, alpha=0.2, linestyle='--', color='#3A3A45')
            
            # Set background colors to match theme
            canvas.axes.set_facecolor('#2A2A35')
            canvas.fig.patch.set_facecolor('#2A2A35')
            
            # Style tick labels
            canvas.axes.tick_params(colors='#AAAAAA', labelsize=9)
            
            # Set spine colors
            for spine in canvas.axes.spines.values():
                spine.set_color('#3A3A45')
            
            canvas.draw()
    
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
    
    def open_kb_editor(self):
        """Open Knowledge Base Editor window."""
        from ui.kb_editor import KBEditorMainWindow
        self.kb_editor = KBEditorMainWindow(self.db.db_path, self)
        self.kb_editor.show()

    def open_report_dialog(self):
        """Open Report Export dialog."""
        from ui.report_dialog import ReportDialog
        dialog = ReportDialog(self.db.db_path, self)
        dialog.exec()

    def generate_mock_data(self):
        """Generate mock test data."""
        from tools.generate_mock_data import MockDataGenerator
        from datetime import datetime, timedelta
        
        reply = QMessageBox.question(
            self, "Генерация тестовых данных",
            "Сгенерировать 7 суток тестовых данных?\n\n"
            "⚠️ Внимание: Все текущие данные будут удалены!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            start_date = datetime.now() - timedelta(days=7)
            generator = MockDataGenerator(self.db.db_path)
            count = generator.generate_7_days(start_date)
            generator.close()
            
            # Refresh UI
            self.load_history()
            self.refresh_chart()
            
            QMessageBox.information(
                self, "Успех",
                f"Сгенерировано {count} записей тестовых данных."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка генерации данных:\n{e}"
            )
