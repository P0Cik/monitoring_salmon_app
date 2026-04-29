# [FILE: ras_monitor/core/solver.py]
"""
Solver module implementing the rule-based decision system for RAS monitoring.
Strictly follows Algorithm 3.c.i from the report.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MeasurementData:
    """Container for measurement parameters."""
    temp: float
    ph: float
    o2: float
    ammonia: float
    nitrite: float
    salinity: float


@dataclass
class SolverResult:
    """Result of the solver evaluation."""
    suitability: str  # "пригодна" or "непригодна"
    current_state: int  # 0-4 (0 = normal, 1-4 severity levels)
    past_dynamics: str  # "Стабильно", "Ухудшение", "Улучшение"
    parameter_states: dict  # Individual parameter severity levels


class Solver:
    """
    Rule-based solver for water quality assessment in RAS systems.
    
    Normal ranges (hypothesis "пригодна"):
    - Temp: [12.0; 14.0]
    - pH: [7.4; 7.8]
    - O2: [90; 100]
    - NH3: [0; 0.5)
    - NO2: [0; 0.1)
    - Sal: [0; 0]
    """
    
    # Normal ranges
    NORMAL_RANGES = {
        'temp': (12.0, 14.0),
        'ph': (7.4, 7.8),
        'o2': (90, 100),
        'ammonia': (0, 0.5),  # [0; 0.5)
        'nitrite': (0, 0.1),  # [0; 0.1)
        'salinity': (0, 0),   # [0; 0]
    }
    
    # Severity thresholds for each parameter
    # Format: list of (min, max, severity) tuples
    THRESHOLDS = {
        'temp': [
            (11, 12, 1), (14, 15, 1),
            (9, 11, 2), (15, 17, 2),
            (5, 9, 3), (17, 21, 3),
            (float('-inf'), 5, 4), (21, float('inf'), 4),
        ],
        'ph': [
            (7.2, 7.4, 1), (7.8, 8.0, 1),
            (7.0, 7.2, 2), (8.0, 8.2, 2),
            (6.6, 7.0, 3), (8.2, 8.6, 3),
            (float('-inf'), 6.6, 4), (8.6, float('inf'), 4),
        ],
        'o2': [
            (85, 90, 1),
            (70, 85, 2),
            (60, 70, 3),
            (float('-inf'), 60, 4),
        ],
        'ammonia': [
            (0.5, 0.6, 1),
            (0.6, 1.0, 2),
            (1.0, 1.5, 3),
            (1.5, float('inf'), 4),
        ],
        'nitrite': [
            (0.1, 0.15, 1),
            (0.15, 0.2, 2),
            (0.2, 0.25, 3),
            (0.25, float('inf'), 4),
        ],
        'salinity': [
            (0, 0.1, 1),
            (0.1, 0.5, 2),
            (0.5, 1.0, 3),
            (1.0, float('inf'), 4),
        ],
    }
    
    def __init__(self):
        """Initialize the solver."""
        pass
    
    def _is_in_normal_range(self, param: str, value: float) -> bool:
        """Check if a parameter value is within normal range."""
        min_val, max_val = self.NORMAL_RANGES[param]
        
        # Special case for salinity: exactly 0
        if param == 'salinity':
            return value == 0
        
        # For ranges like [0; 0.5) - inclusive lower, exclusive upper
        if param in ('ammonia', 'nitrite'):
            return min_val <= value < max_val
        
        # For closed intervals [a; b]
        return min_val <= value <= max_val
    
    def _get_severity_level(self, param: str, value: float) -> int:
        """
        Determine severity level (1-4) for a parameter value outside normal range.
        
        Args:
            param: Parameter name
            value: Parameter value
            
        Returns:
            Severity level (1-4), or 0 if in normal range
        """
        # First check if in normal range
        if self._is_in_normal_range(param, value):
            return 0
        
        # Find severity level from thresholds
        for min_val, max_val, severity in self.THRESHOLDS[param]:
            if min_val <= value < max_val:
                return severity
        
        # Default fallback (should not reach here with proper thresholds)
        return 4
    
    def evaluate(
        self, 
        data: MeasurementData, 
        previous_state: Optional[int] = None
    ) -> SolverResult:
        """
        Evaluate water quality based on measurement data.
        
        Algorithm 3.c.i:
        1. If ALL parameters in normal ranges → suitability="пригодна", state=0
        2. Otherwise → find severity for each parameter, state=MAX(severities), suitability="непригодна"
        3. Dynamics: compare with previous state
        
        Args:
            data: Measurement data
            previous_state: Previous state from database (for dynamics calculation)
            
        Returns:
            SolverResult with evaluation results
        """
        # Get all parameter values
        params = {
            'temp': data.temp,
            'ph': data.ph,
            'o2': data.o2,
            'ammonia': data.ammonia,
            'nitrite': data.nitrite,
            'salinity': data.salinity,
        }
        
        # Check each parameter and get severity levels
        parameter_states = {}
        all_normal = True
        
        for param, value in params.items():
            severity = self._get_severity_level(param, value)
            parameter_states[param] = severity
            if severity > 0:
                all_normal = False
        
        # Determine overall state and suitability
        if all_normal:
            suitability = "пригодна"
            current_state = 0
        else:
            suitability = "непригодна"
            current_state = max(parameter_states.values())
        
        # Calculate retrospective dynamics
        past_dynamics = self._calculate_dynamics(current_state, previous_state)
        
        return SolverResult(
            suitability=suitability,
            current_state=current_state,
            past_dynamics=past_dynamics,
            parameter_states=parameter_states,
        )
    
    def _calculate_dynamics(
        self, 
        current_state: int, 
        previous_state: Optional[int]
    ) -> str:
        """
        Calculate retrospective dynamics by comparing states.
        
        Args:
            current_state: Current state (0-4)
            previous_state: Previous state from history (0-4) or None
            
        Returns:
            Dynamics string: "Стабильно", "Ухудшение", or "Улучшение"
        """
        if previous_state is None:
            return "Стабильно"
        
        if current_state == previous_state:
            return "Стабильно"
        elif current_state > previous_state:
            return "Ухудшение"
        else:
            return "Улучшение"
    
    def get_state_description(self, state: int) -> str:
        """
        Get human-readable description for a state level.
        
        Args:
            state: State level (0-4)
            
        Returns:
            Description string
        """
        descriptions = {
            0: "Нормальное состояние",
            1: "Отходящее от нормы",
            2: "Неустойчивое равновесие",
            3: "Угроза нарушения биобаланса",
            4: "Критическое состояние",
        }
        return descriptions.get(state, "Неизвестное состояние")
