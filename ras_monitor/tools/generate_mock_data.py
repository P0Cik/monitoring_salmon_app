# [FILE: ras_monitor/tools/generate_mock_data.py]
"""
Mock data generator for RAS monitoring system.
Generates 7 days (168 hours) of realistic measurement data with various scenarios.

Scenarios:
- 0-48h: Normal conditions (all parameters in ideal ranges)
- 48-96h: Gradual degradation (temp rises, O2 drops, ammonia increases)
- 96-120h: Critical peak → state 4
- 120-168h: Recovery after intervention
"""

import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import Database
from core.solver import Solver, MeasurementData


class MockDataGenerator:
    """Generate realistic mock measurement data for testing."""
    
    # Normal ranges (ideal values within normal bounds)
    NORMAL_RANGES = {
        'temp': (12.5, 13.5),      # Within [12.0; 14.0]
        'ph': (7.5, 7.7),          # Within [7.4; 7.8]
        'o2': (93, 98),            # Within [90; 100]
        'ammonia': (0.1, 0.3),     # Within [0; 0.5)
        'nitrite': (0.02, 0.06),   # Within [0; 0.1)
        'salinity': (0, 0),        # Exactly 0
    }
    
    def __init__(self, db_path: str = "ras_monitor.db"):
        self.db = Database(db_path)
        self.solver = Solver()
        self.noise_factor = 0.03  # ±3% noise
    
    def _add_noise(self, value: float) -> float:
        """Add ±3% noise to a value."""
        if value == 0:
            return 0
        noise = value * self.noise_factor * random.uniform(-1, 1)
        return round(value + noise, 3)
    
    def generate_normal_values(self) -> dict:
        """Generate values within normal ranges."""
        values = {}
        for param, (min_v, max_v) in self.NORMAL_RANGES.items():
            if min_v == max_v:
                values[param] = min_v
            else:
                values[param] = random.uniform(min_v, max_v)
        
        return {k: self._add_noise(v) for k, v in values.items()}
    
    def generate_degrading_values(self, progress: float, prev_values: dict) -> dict:
        """
        Generate values that gradually degrade from normal.
        
        Args:
            progress: 0.0 to 1.0 indicating degradation progress
            prev_values: Previous hour's values for smooth transition
        """
        # Start from normal and progressively move toward dangerous levels
        values = {}
        
        # Temperature: rises from ~13 to ~18 (crosses into severity 3-4)
        temp_target = 18.0
        temp_start = 13.0
        values['temp'] = prev_values.get('temp', temp_start) + (temp_target - temp_start) * progress * 0.1
        
        # pH: drops slightly then recovers
        ph_target = 7.0
        ph_start = 7.6
        values['ph'] = prev_values.get('ph', ph_start) + (ph_target - ph_start) * progress * 0.05
        
        # O2: drops from ~95 to ~55 (severity 4)
        o2_target = 55.0
        o2_start = 95.0
        values['o2'] = prev_values.get('o2', o2_start) + (o2_target - o2_start) * progress * 0.15
        
        # Ammonia: rises from ~0.2 to ~2.0 (severity 4)
        nh3_target = 2.0
        nh3_start = 0.2
        values['ammonia'] = prev_values.get('ammonia', nh3_start) + (nh3_target - nh3_start) * progress * 0.2
        
        # Nitrite: rises from ~0.04 to ~0.35 (severity 4)
        no2_target = 0.35
        no2_start = 0.04
        values['nitrite'] = prev_values.get('nitrite', no2_start) + (no2_target - no2_start) * progress * 0.15
        
        # Salinity: stays at 0
        values['salinity'] = 0
        
        return {k: self._add_noise(max(0, v)) for k, v in values.items()}
    
    def generate_critical_values(self, prev_values: dict) -> dict:
        """Generate values at critical levels (state 4)."""
        values = {
            'temp': random.uniform(19, 21),      # Severity 3-4
            'ph': random.uniform(6.7, 7.0),      # Severity 3
            'o2': random.uniform(50, 60),        # Severity 3-4
            'ammonia': random.uniform(1.6, 2.2), # Severity 4
            'nitrite': random.uniform(0.28, 0.4),# Severity 4
            'salinity': random.uniform(0, 0.15), # Severity 1-2
        }
        return {k: self._add_noise(v) for k, v in values.items()}
    
    def generate_recovery_values(self, progress: float, prev_values: dict) -> dict:
        """
        Generate values that recover toward normal.
        
        Args:
            progress: 0.0 to 1.0 indicating recovery progress
            prev_values: Previous hour's values
        """
        values = {}
        
        # Move each parameter back toward normal range
        for param, (norm_min, norm_max) in self.NORMAL_RANGES.items():
            norm_mid = (norm_min + norm_max) / 2
            current = prev_values.get(param, norm_mid)
            
            # Smooth interpolation toward normal
            if param == 'salinity':
                values[param] = current * (1 - progress * 0.3)
            else:
                target = norm_mid
                values[param] = current + (target - current) * progress * 0.4
        
        return {k: self._add_noise(max(0, v)) for k, v in values.items()}
    
    def generate_7_days(self, start_date: datetime = None) -> int:
        """
        Generate 7 days (168 hours) of mock data.
        
        Args:
            start_date: Starting timestamp (default: 7 days ago)
            
        Returns:
            Number of records inserted
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        
        # Clear existing data for clean test
        cursor = self.db.conn.cursor()
        cursor.execute("DELETE FROM history")
        cursor.execute("DELETE FROM measurements")
        self.db.conn.commit()
        
        records = []
        current_values = self.generate_normal_values()
        previous_state = 0
        
        total_hours = 168  # 7 days * 24 hours
        
        for hour in range(total_hours):
            timestamp = start_date + timedelta(hours=hour)
            
            # Determine scenario based on hour
            if hour < 48:
                # Phase 1: Normal (0-48h)
                current_values = self.generate_normal_values()
                
            elif hour < 96:
                # Phase 2: Gradual degradation (48-96h)
                progress = (hour - 48) / 48  # 0 to 1
                current_values = self.generate_degrading_values(progress, current_values)
                
            elif hour < 120:
                # Phase 3: Critical peak (96-120h)
                current_values = self.generate_critical_values(current_values)
                
            else:
                # Phase 4: Recovery (120-168h)
                progress = (hour - 120) / 48  # 0 to 1
                current_values = self.generate_recovery_values(progress, current_values)
            
            # Create measurement data
            data = MeasurementData(
                temp=round(current_values['temp'], 2),
                ph=round(current_values['ph'], 2),
                o2=round(current_values['o2'], 1),
                ammonia=round(current_values['ammonia'], 3),
                nitrite=round(current_values['nitrite'], 3),
                salinity=round(current_values['salinity'], 2),
            )
            
            # Evaluate with solver to get state
            result = self.solver.evaluate(data, previous_state)
            
            # Save measurement
            measurement_id = self.db.add_measurement(
                temp=data.temp,
                ph=data.ph,
                o2=data.o2,
                ammonia=data.ammonia,
                nitrite=data.nitrite,
                salinity=data.salinity,
                timestamp=timestamp.isoformat(),
            )
            
            # Save history (simplified forecast for mock data)
            forecast_dynamics = "Стабильно" if result.current_state == 0 else (
                "Ухудшение" if result.past_dynamics == "Ухудшение" else "Улучшение"
            )
            forecast_confidence = random.uniform(0.6, 0.95) if hour > 6 else None
            
            self.db.add_history(
                measurement_id=measurement_id,
                current_state=result.current_state,
                suitability=result.suitability,
                past_dynamics=result.past_dynamics,
                forecast_dynamics=forecast_dynamics if hour > 6 else None,
                forecast_confidence=forecast_confidence,
            )
            
            previous_state = result.current_state
            records.append((timestamp, result.current_state))
        
        return len(records)
    
    def close(self):
        """Close database connection."""
        self.db.close()


def main():
    """Main entry point for mock data generation."""
    print("=" * 60)
    print("🧪 Генератор тестовых данных УЗВ")
    print("=" * 60)
    
    # Create generator
    generator = MockDataGenerator("ras_monitor.db")
    
    # Set start date to 7 days ago
    start_date = datetime.now() - timedelta(days=7)
    
    print(f"\n📅 Генерация данных начиная с: {start_date.strftime('%Y-%m-%d %H:%M')}")
    print("📊 Сценарий на 7 суток (168 записей):")
    print("   • 0-48ч: Норма (все параметры в идеальных диапазонах)")
    print("   • 48-96ч: Плавное ухудшение (температура растёт, O2 падает, аммиак растёт)")
    print("   • 96-120ч: Критический пик → переход в состояние 4")
    print("   • 120-168ч: Восстановление после вмешательства")
    print()
    
    try:
        # Generate data
        count = generator.generate_7_days(start_date)
        
        # Get date range
        measurements = generator.db.get_measurements(limit=1, order="ASC")
        first_date = measurements[0]['timestamp'] if measurements else "N/A"
        
        measurements = generator.db.get_measurements(limit=1, order="DESC")
        last_date = measurements[0]['timestamp'] if measurements else "N/A"
        
        print(f"\n✅ Загружено {count} записей.")
        print(f"📅 Диапазон: {first_date[:10]} ... {last_date[:10]}")
        print("\n📈 Статистика состояний:")
        
        # Show state distribution
        history = generator.db.get_history_with_measurements(limit=200)
        state_counts = {}
        for record in history:
            state = record['current_state']
            state_counts[state] = state_counts.get(state, 0) + 1
        
        solver = Solver()
        for state in sorted(state_counts.keys()):
            desc = solver.get_state_description(state)
            print(f"   Состояние {state} ({desc}): {state_counts[state]} записей")
        
        print("\n" + "=" * 60)
        print("Генерация завершена успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка генерации: {e}")
        raise
    
    finally:
        generator.close()


if __name__ == "__main__":
    main()
