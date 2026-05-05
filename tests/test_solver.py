"""
Тестирование модуля core/solver.py
"""
import sys
sys.path.insert(0, 'ras_monitor')

from ras_monitor.core.solver import Solver, MeasurementData

def test_solver():
    """Тестирование жёсткого решателя"""
    solver = Solver()
    results = []

    # Тест 1: Все параметры в норме
    print("Тест 1: Все параметры в норме")
    data = MeasurementData(temp=13.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 1,
        'function': 'Оценка состояния воды',
        'input': 'Температура=13.0, pH=7.6, O2=95, NH3=0.2, NO2=0.05, Соленость=0',
        'expected': 'Пригодна, состояние=0',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: пригодна, состояние=0")
    status = 'PASS' if result.suitability == 'пригодна' and result.current_state == 0 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 2: Температура - уровень 1
    print("Тест 2: Температура отклонение уровень 1")
    data = MeasurementData(temp=11.5, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 2,
        'function': 'Оценка состояния воды',
        'input': 'Температура=11.5 (отклонение уровень 1), остальные в норме',
        'expected': 'Непригодна, состояние=1',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=1")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 1 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 3: pH - уровень 2
    print("Тест 3: pH отклонение уровень 2")
    data = MeasurementData(temp=13.0, ph=7.1, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 3,
        'function': 'Оценка состояния воды',
        'input': 'pH=7.1 (отклонение уровень 2), остальные в норме',
        'expected': 'Непригодна, состояние=2',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=2")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 2 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 4: O2 - уровень 3
    print("Тест 4: Кислород отклонение уровень 3")
    data = MeasurementData(temp=13.0, ph=7.6, o2=65, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 4,
        'function': 'Оценка состояния воды',
        'input': 'O2=65 (отклонение уровень 3), остальные в норме',
        'expected': 'Непригодна, состояние=3',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=3")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 3 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 5: Аммиак - уровень 4
    print("Тест 5: Аммиак критический уровень 4")
    data = MeasurementData(temp=13.0, ph=7.6, o2=95, ammonia=1.6, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 5,
        'function': 'Оценка состояния воды',
        'input': 'NH3=1.6 (критический уровень 4), остальные в норме',
        'expected': 'Непригодна, состояние=4',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=4")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 4 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 6: Несколько параметров отклонены - максимальный уровень
    print("Тест 6: Несколько параметров отклонены")
    data = MeasurementData(temp=10.5, ph=7.3, o2=87, ammonia=0.55, nitrite=0.12, salinity=0.05)
    result = solver.evaluate(data)
    results.append({
        'test_num': 6,
        'function': 'Оценка состояния воды',
        'input': 'Температура=10.5(ур.2), pH=7.3(ур.1), O2=87(ур.1), NH3=0.55(ур.1), NO2=0.12(ур.1), Соленость=0.05(ур.1)',
        'expected': 'Непригодна, состояние=2 (максимальный уровень)',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=2")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 2 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 7: Динамика - стабильно
    print("Тест 7: Динамика - стабильно")
    data = MeasurementData(temp=13.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data, previous_state=0)
    results.append({
        'test_num': 7,
        'function': 'Расчет динамики',
        'input': 'Текущее состояние=0, предыдущее=0',
        'expected': 'Стабильно',
        'actual': result.past_dynamics
    })
    print(f"  Результат: {result.past_dynamics}")
    print(f"  Ожидалось: Стабильно")
    status = 'PASS' if result.past_dynamics == 'Стабильно' else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 8: Динамика - ухудшение
    print("Тест 8: Динамика - ухудшение")
    data = MeasurementData(temp=10.5, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data, previous_state=0)
    results.append({
        'test_num': 8,
        'function': 'Расчет динамики',
        'input': 'Текущее состояние=2, предыдущее=0',
        'expected': 'Ухудшение',
        'actual': result.past_dynamics
    })
    print(f"  Результат: {result.past_dynamics}")
    print(f"  Ожидалось: Ухудшение")
    status = 'PASS' if result.past_dynamics == 'Ухудшение' else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 9: Динамика - улучшение
    print("Тест 9: Динамика - улучшение")
    data = MeasurementData(temp=13.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data, previous_state=2)
    results.append({
        'test_num': 9,
        'function': 'Расчет динамики',
        'input': 'Текущее состояние=0, предыдущее=2',
        'expected': 'Улучшение',
        'actual': result.past_dynamics
    })
    print(f"  Результат: {result.past_dynamics}")
    print(f"  Ожидалось: Улучшение")
    status = 'PASS' if result.past_dynamics == 'Улучшение' else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 10: Граничные значения - аммиак 0.5 (граница нормы)
    print("Тест 10: Граничное значение аммиака 0.5")
    data = MeasurementData(temp=13.0, ph=7.6, o2=95, ammonia=0.5, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 10,
        'function': 'Оценка состояния воды',
        'input': 'NH3=0.5 (граница нормы [0; 0.5))',
        'expected': 'Непригодна, состояние=1',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=1")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 1 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 11: Температура критическая низкая
    print("Тест 11: Температура критическая низкая")
    data = MeasurementData(temp=4.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 11,
        'function': 'Оценка состояния воды',
        'input': 'Температура=4.0 (критический уровень 4)',
        'expected': 'Непригодна, состояние=4',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=4")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 4 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 12: Температура критическая высокая
    print("Тест 12: Температура критическая высокая")
    data = MeasurementData(temp=22.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0)
    result = solver.evaluate(data)
    results.append({
        'test_num': 12,
        'function': 'Оценка состояния воды',
        'input': 'Температура=22.0 (критический уровень 4)',
        'expected': 'Непригодна, состояние=4',
        'actual': f'{result.suitability}, состояние={result.current_state}'
    })
    print(f"  Результат: {result.suitability}, состояние={result.current_state}")
    print(f"  Ожидалось: непригодна, состояние=4")
    status = 'PASS' if result.suitability == 'непригодна' and result.current_state == 4 else 'FAIL'
    print(f"  Статус: {status}\n")

    return results

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ SOLVER (Жёсткий решатель)")
    print("=" * 80)
    print()

    results = test_solver()

    print("=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Всего тестов: {len(results)}")
    print()
