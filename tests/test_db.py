"""
Тестирование модуля core/db.py
"""
import sys
import os
sys.path.insert(0, 'ras_monitor')

from ras_monitor.core.db import Database

def test_database():
    """Тестирование работы с базой данных"""
    results = []

    # Создаем тестовую базу данных
    test_db_path = "test_db_temp.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    db = Database(test_db_path)

    # Тест 1: Создание таблиц
    print("Тест 1: Создание таблиц")
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    expected_tables = ['measurements', 'history']
    success = all(table in tables for table in expected_tables)
    results.append({
        'test_num': 1,
        'function': 'Создание таблиц БД',
        'input': 'Инициализация базы данных',
        'expected': 'Таблицы measurements и history созданы',
        'actual': f'Созданы таблицы: {", ".join(tables)}'
    })
    print(f"  Результат: Таблицы созданы: {', '.join(tables)}")
    print(f"  Ожидалось: measurements, history")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 2: Добавление замера
    print("Тест 2: Добавление замера")
    measurement_id = db.add_measurement(
        temp=13.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0
    )
    results.append({
        'test_num': 2,
        'function': 'Добавление замера',
        'input': 'temp=13.0, ph=7.6, o2=95, ammonia=0.2, nitrite=0.05, salinity=0',
        'expected': 'Замер добавлен, возвращен ID',
        'actual': f'ID замера: {measurement_id}'
    })
    print(f"  Результат: ID замера = {measurement_id}")
    print(f"  Ожидалось: ID > 0")
    status = 'PASS' if measurement_id > 0 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 3: Получение последнего замера
    print("Тест 3: Получение последнего замера")
    last_measurement = db.get_last_measurement()
    success = (last_measurement is not None and
               last_measurement['temp'] == 13.0 and
               last_measurement['ph'] == 7.6)
    results.append({
        'test_num': 3,
        'function': 'Получение последнего замера',
        'input': 'Запрос последнего замера',
        'expected': 'Возвращен замер с temp=13.0, ph=7.6',
        'actual': f'temp={last_measurement["temp"]}, ph={last_measurement["ph"]}' if last_measurement else 'None'
    })
    print(f"  Результат: {last_measurement}")
    print(f"  Ожидалось: temp=13.0, ph=7.6")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 4: Добавление истории
    print("Тест 4: Добавление истории")
    history_id = db.add_history(
        measurement_id=measurement_id,
        current_state=0,
        suitability="пригодна",
        past_dynamics="Стабильно"
    )
    results.append({
        'test_num': 4,
        'function': 'Добавление записи истории',
        'input': 'measurement_id, state=0, suitability="пригодна"',
        'expected': 'История добавлена, возвращен ID',
        'actual': f'ID истории: {history_id}'
    })
    print(f"  Результат: ID истории = {history_id}")
    print(f"  Ожидалось: ID > 0")
    status = 'PASS' if history_id > 0 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 5: Получение последнего состояния
    print("Тест 5: Получение последнего состояния")
    last_state = db.get_last_state()
    results.append({
        'test_num': 5,
        'function': 'Получение последнего состояния',
        'input': 'Запрос последнего состояния',
        'expected': 'Возвращено состояние 0',
        'actual': f'Состояние: {last_state}'
    })
    print(f"  Результат: Состояние = {last_state}")
    print(f"  Ожидалось: 0")
    status = 'PASS' if last_state == 0 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 6: Добавление нескольких замеров
    print("Тест 6: Добавление нескольких замеров")
    for i in range(5):
        db.add_measurement(
            temp=13.0 + i * 0.5, ph=7.6, o2=95 - i,
            ammonia=0.2, nitrite=0.05, salinity=0
        )
    measurements = db.get_measurements(limit=10)
    results.append({
        'test_num': 6,
        'function': 'Добавление нескольких замеров',
        'input': 'Добавлено 5 замеров',
        'expected': 'Всего 6 замеров в БД',
        'actual': f'Количество замеров: {len(measurements)}'
    })
    print(f"  Результат: Количество замеров = {len(measurements)}")
    print(f"  Ожидалось: 6")
    status = 'PASS' if len(measurements) == 6 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 7: Получение замеров для ML (окно 6)
    print("Тест 7: Получение замеров для ML")
    ml_data = db.get_recent_measurements_for_ml(window_size=6)
    success = ml_data is not None and len(ml_data) == 6
    results.append({
        'test_num': 7,
        'function': 'Получение замеров для ML',
        'input': 'window_size=6',
        'expected': 'Возвращено 6 замеров в формате списка',
        'actual': f'Получено {len(ml_data) if ml_data else 0} замеров'
    })
    print(f"  Результат: Получено {len(ml_data) if ml_data else 0} замеров")
    print(f"  Ожидалось: 6 замеров")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 8: Получение истории с замерами (JOIN)
    print("Тест 8: Получение истории с замерами")
    history_with_measurements = db.get_history_with_measurements(limit=5)
    success = len(history_with_measurements) > 0 and 'temp' in history_with_measurements[0]
    results.append({
        'test_num': 8,
        'function': 'Получение истории с замерами (JOIN)',
        'input': 'limit=5',
        'expected': 'Возвращены записи с полями истории и замеров',
        'actual': f'Получено {len(history_with_measurements)} записей'
    })
    print(f"  Результат: Получено {len(history_with_measurements)} записей")
    print(f"  Ожидалось: > 0 записей с полем temp")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 9: Добавление истории с прогнозом
    print("Тест 9: Добавление истории с прогнозом")
    measurement_id2 = db.add_measurement(
        temp=14.5, ph=7.7, o2=92, ammonia=0.3, nitrite=0.06, salinity=0
    )
    history_id2 = db.add_history(
        measurement_id=measurement_id2,
        current_state=1,
        suitability="непригодна",
        past_dynamics="Ухудшение",
        forecast_dynamics="Стабильно",
        forecast_confidence=0.85
    )
    cursor.execute("SELECT forecast_dynamics, forecast_confidence FROM history WHERE id=?", (history_id2,))
    row = cursor.fetchone()
    success = row[0] == "Стабильно" and abs(row[1] - 0.85) < 0.01
    results.append({
        'test_num': 9,
        'function': 'Добавление истории с прогнозом',
        'input': 'forecast_dynamics="Стабильно", forecast_confidence=0.85',
        'expected': 'История с прогнозом добавлена',
        'actual': f'forecast_dynamics={row[0]}, confidence={row[1]}'
    })
    print(f"  Результат: forecast_dynamics={row[0]}, confidence={row[1]}")
    print(f"  Ожидалось: Стабильно, 0.85")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 10: Получение всех замеров для обучения
    print("Тест 10: Получение всех замеров для обучения")
    all_measurements = db.get_all_measurements_for_training()
    results.append({
        'test_num': 10,
        'function': 'Получение всех замеров для обучения',
        'input': 'Запрос всех замеров',
        'expected': 'Возвращены все замеры в хронологическом порядке',
        'actual': f'Получено {len(all_measurements)} замеров'
    })
    print(f"  Результат: Получено {len(all_measurements)} замеров")
    print(f"  Ожидалось: 7 замеров")
    status = 'PASS' if len(all_measurements) == 7 else 'FAIL'
    print(f"  Статус: {status}\n")

    # Закрываем соединение и удаляем тестовую БД
    db.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    return results

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ DATABASE (База данных)")
    print("=" * 80)
    print()

    results = test_database()

    print("=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Всего тестов: {len(results)}")
    print()
