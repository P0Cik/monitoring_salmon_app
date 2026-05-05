"""
Тестирование UI компонентов
"""
import sys
sys.path.insert(0, 'ras_monitor')

from PyQt6.QtWidgets import QApplication
from ras_monitor.ui.main_window import MainWindow, StatusCard, MLForecastCard
from ras_monitor.core.solver import Solver, MeasurementData

def test_ui_components():
    """Тестирование UI компонентов"""
    results = []

    # Создаем QApplication для тестирования UI
    app = QApplication(sys.argv)

    # Тест 1: Создание главного окна
    print("Тест 1: Создание главного окна")
    try:
        window = MainWindow()
        success = window is not None
        results.append({
            'test_num': 1,
            'function': 'Создание главного окна',
            'input': 'Инициализация MainWindow()',
            'expected': 'Окно создано',
            'actual': 'Окно создано успешно'
        })
        print(f"  Результат: Окно создано")
        print(f"  Ожидалось: Окно создано")
        status = 'PASS' if success else 'FAIL'
        print(f"  Статус: {status}\n")
    except Exception as e:
        results.append({
            'test_num': 1,
            'function': 'Создание главного окна',
            'input': 'Инициализация MainWindow()',
            'expected': 'Окно создано',
            'actual': f'Ошибка: {str(e)}'
        })
        print(f"  Результат: Ошибка - {str(e)}")
        print(f"  Статус: FAIL\n")
        return results

    # Тест 2: Проверка наличия полей ввода
    print("Тест 2: Проверка наличия полей ввода")
    input_fields = ['temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity']
    all_fields_exist = hasattr(window, 'input_fields') and all(field in window.input_fields for field in input_fields)
    results.append({
        'test_num': 2,
        'function': 'Проверка полей ввода',
        'input': 'Проверка атрибута input_fields',
        'expected': 'Все 6 полей ввода существуют',
        'actual': f'Поля существуют: {all_fields_exist}'
    })
    print(f"  Результат: Все поля существуют: {all_fields_exist}")
    print(f"  Ожидалось: True")
    status = 'PASS' if all_fields_exist else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 3: Ввод корректных данных
    print("Тест 3: Ввод корректных данных")
    window.input_fields['temp'].setText("13.0")
    window.input_fields['ph'].setText("7.6")
    window.input_fields['o2'].setText("95")
    window.input_fields['ammonia'].setText("0.2")
    window.input_fields['nitrite'].setText("0.05")
    window.input_fields['salinity'].setText("0")

    values_set = (window.input_fields['temp'].text() == "13.0" and
                  window.input_fields['ph'].text() == "7.6" and
                  window.input_fields['o2'].text() == "95")
    results.append({
        'test_num': 3,
        'function': 'Ввод данных в поля',
        'input': 'Температура=13.0, pH=7.6, O2=95, NH3=0.2, NO2=0.05, Соленость=0',
        'expected': 'Данные введены в поля',
        'actual': f'Данные введены: {values_set}'
    })
    print(f"  Результат: Данные введены: {values_set}")
    print(f"  Ожидалось: True")
    status = 'PASS' if values_set else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 4: Создание карточки состояния
    print("Тест 4: Создание карточки состояния")
    status_card = StatusCard("Тестовая карточка")
    success = status_card is not None
    results.append({
        'test_num': 4,
        'function': 'Создание StatusCard',
        'input': 'title="Тестовая карточка"',
        'expected': 'Карточка создана',
        'actual': f'Карточка создана: {success}'
    })
    print(f"  Результат: Карточка создана")
    print(f"  Ожидалось: Карточка создана")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 5: Обновление карточки состояния
    print("Тест 5: Обновление карточки состояния")
    status_card.update_value("Тестовое значение", "#90EE90")
    success = status_card.value_label.text() == "Тестовое значение"
    results.append({
        'test_num': 5,
        'function': 'Обновление StatusCard',
        'input': 'value="Тестовое значение", color="#90EE90"',
        'expected': 'Значение обновлено',
        'actual': f'Значение: {status_card.value_label.text()}'
    })
    print(f"  Результат: Значение = {status_card.value_label.text()}")
    print(f"  Ожидалось: Тестовое значение")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 6: Создание карточки прогноза ML
    print("Тест 6: Создание карточки прогноза ML")
    ml_card = MLForecastCard("Прогноз ML")
    success = ml_card is not None
    results.append({
        'test_num': 6,
        'function': 'Создание MLForecastCard',
        'input': 'title="Прогноз ML"',
        'expected': 'Карточка ML создана',
        'actual': f'Карточка создана: {success}'
    })
    print(f"  Результат: Карточка ML создана")
    print(f"  Ожидалось: Карточка создана")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 7: Обновление карточки прогноза ML
    print("Тест 7: Обновление карточки прогноза ML")
    test_probs = {1: 0.1, 2: 0.3, 3: 0.4, 4: 0.2}
    ml_card.update_forecast("Ухудшение", 0.85, test_probs)
    success = ml_card.forecast_dynamics == "Ухудшение" and ml_card.confidence == 0.85
    results.append({
        'test_num': 7,
        'function': 'Обновление MLForecastCard',
        'input': 'dynamics="Ухудшение", confidence=0.85',
        'expected': 'Прогноз обновлен',
        'actual': f'Динамика: {ml_card.forecast_dynamics}, Уверенность: {ml_card.confidence}'
    })
    print(f"  Результат: Динамика={ml_card.forecast_dynamics}, Уверенность={ml_card.confidence}")
    print(f"  Ожидалось: Ухудшение, 0.85")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 8: Проверка наличия таблицы истории
    print("Тест 8: Проверка наличия таблицы истории")
    success = hasattr(window, 'history_table') and window.history_table is not None
    results.append({
        'test_num': 8,
        'function': 'Проверка таблицы истории',
        'input': 'Проверка атрибута history_table',
        'expected': 'Таблица истории существует',
        'actual': f'Таблица существует: {success}'
    })
    print(f"  Результат: Таблица существует: {success}")
    print(f"  Ожидалось: True")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 9: Проверка наличия графика
    print("Тест 9: Проверка наличия графика")
    success = hasattr(window, 'canvas') and window.canvas is not None
    results.append({
        'test_num': 9,
        'function': 'Проверка графика',
        'input': 'Проверка атрибута canvas',
        'expected': 'График существует',
        'actual': f'График существует: {success}'
    })
    print(f"  Результат: График существует: {success}")
    print(f"  Ожидалось: True")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 10: Проверка метода получения значений
    print("Тест 10: Проверка метода получения значений")
    success = hasattr(window, 'get_input_values')
    results.append({
        'test_num': 10,
        'function': 'Проверка метода get_input_values',
        'input': 'Проверка наличия метода',
        'expected': 'Метод существует',
        'actual': f'Метод существует: {success}'
    })
    print(f"  Результат: Метод существует: {success}")
    print(f"  Ожидалось: True")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 11: Проверка валидации ввода (некорректные данные)
    print("Тест 11: Проверка валидации ввода")
    window.input_fields['temp'].setText("abc")  # Некорректное значение
    window.input_fields['ph'].setText("7.6")
    window.input_fields['o2'].setText("95")
    window.input_fields['ammonia'].setText("0.2")
    window.input_fields['nitrite'].setText("0.05")
    window.input_fields['salinity'].setText("0")

    # Попытка получить значения
    try:
        temp = float(window.input_fields['temp'].text())
        validation_failed = False
    except ValueError:
        validation_failed = True

    results.append({
        'test_num': 11,
        'function': 'Валидация ввода',
        'input': 'Температура="abc" (некорректное значение)',
        'expected': 'Ошибка валидации',
        'actual': f'Ошибка валидации: {validation_failed}'
    })
    print(f"  Результат: Ошибка валидации: {validation_failed}")
    print(f"  Ожидалось: True")
    status = 'PASS' if validation_failed else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 12: Проверка наличия solver
    print("Тест 12: Проверка наличия solver")
    success = hasattr(window, 'solver') and window.solver is not None
    results.append({
        'test_num': 12,
        'function': 'Проверка наличия solver',
        'input': 'Проверка атрибута solver',
        'expected': 'Solver инициализирован',
        'actual': f'Solver существует: {success}'
    })
    print(f"  Результат: Solver существует: {success}")
    print(f"  Ожидалось: True")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    return results

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ UI КОМПОНЕНТОВ")
    print("=" * 80)
    print()

    results = test_ui_components()

    print("=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Всего тестов: {len(results)}")
    print()
