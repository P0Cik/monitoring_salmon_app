"""
Тестирование модуля ml/predictor.py
"""
import sys
import os
sys.path.insert(0, 'ras_monitor')

from ras_monitor.ml.predictor import Predictor, LSTMModel
import torch

def test_predictor():
    """Тестирование модуля прогнозирования"""
    results = []

    # Тест 1: Создание экземпляра предиктора
    print("Тест 1: Создание экземпляра предиктора")
    predictor = Predictor()
    success = predictor is not None
    results.append({
        'test_num': 1,
        'function': 'Создание экземпляра Predictor',
        'input': 'Инициализация Predictor()',
        'expected': 'Объект создан',
        'actual': f'Объект создан: {success}'
    })
    print(f"  Результат: Объект создан")
    print(f"  Ожидалось: Объект создан")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 2: Проверка архитектуры модели
    print("Тест 2: Проверка архитектуры модели LSTM")
    model = LSTMModel(input_size=6, hidden_size=32, num_layers=1, output_size=4)
    success = (model.hidden_size == 32 and
               model.num_layers == 1)
    results.append({
        'test_num': 2,
        'function': 'Создание модели LSTM',
        'input': 'input_size=6, hidden_size=32, output_size=4',
        'expected': 'Модель создана с правильными параметрами',
        'actual': f'hidden_size={model.hidden_size}, num_layers={model.num_layers}'
    })
    print(f"  Результат: hidden_size={model.hidden_size}, num_layers={model.num_layers}")
    print(f"  Ожидалось: hidden_size=32, num_layers=1")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 3: Forward pass модели
    print("Тест 3: Forward pass модели")
    test_input = torch.randn(1, 6, 6)  # batch=1, seq_len=6, features=6
    output = model(test_input)
    success = output.shape == torch.Size([1, 4])
    results.append({
        'test_num': 3,
        'function': 'Forward pass модели',
        'input': 'Тензор размера (1, 6, 6)',
        'expected': 'Выход размера (1, 4)',
        'actual': f'Выход размера {output.shape}'
    })
    print(f"  Результат: Выход размера {output.shape}")
    print(f"  Ожидалось: torch.Size([1, 4])")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 4: Проверка softmax (сумма вероятностей = 1)
    print("Тест 4: Проверка softmax")
    prob_sum = output.sum().item()
    success = abs(prob_sum - 1.0) < 0.01
    results.append({
        'test_num': 4,
        'function': 'Проверка softmax',
        'input': 'Выход модели',
        'expected': 'Сумма вероятностей = 1.0',
        'actual': f'Сумма вероятностей = {prob_sum:.4f}'
    })
    print(f"  Результат: Сумма вероятностей = {prob_sum:.4f}")
    print(f"  Ожидалось: 1.0")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 5: Загрузка модели (если файлы существуют)
    print("Тест 5: Загрузка модели")
    model_path = "ras_monitor/ml/model.pth"
    scaler_path = "ras_monitor/ml/scaler.pkl"

    if os.path.exists(model_path) and os.path.exists(scaler_path):
        predictor2 = Predictor(model_path=model_path, scaler_path=scaler_path)
        load_success = predictor2.load_model()
        results.append({
            'test_num': 5,
            'function': 'Загрузка обученной модели',
            'input': 'model.pth и scaler.pkl',
            'expected': 'Модель загружена успешно',
            'actual': f'Загрузка: {load_success}'
        })
        print(f"  Результат: Модель загружена: {load_success}")
        print(f"  Ожидалось: True")
        status = 'PASS' if load_success else 'FAIL'
        print(f"  Статус: {status}\n")
    else:
        results.append({
            'test_num': 5,
            'function': 'Загрузка обученной модели',
            'input': 'model.pth и scaler.pkl',
            'expected': 'Файлы модели не найдены',
            'actual': 'Файлы модели отсутствуют (требуется обучение)'
        })
        print(f"  Результат: Файлы модели не найдены")
        print(f"  Ожидалось: Требуется обучение модели")
        print(f"  Статус: SKIP\n")

    # Тест 6: Прогнозирование (если модель загружена)
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        print("Тест 6: Прогнозирование состояния")
        # Создаем тестовые данные (6 замеров)
        test_measurements = [
            [13.0, 7.6, 95, 0.2, 0.05, 0],
            [13.1, 7.6, 94, 0.21, 0.05, 0],
            [13.2, 7.6, 93, 0.22, 0.06, 0],
            [13.3, 7.6, 92, 0.23, 0.06, 0],
            [13.4, 7.6, 91, 0.24, 0.07, 0],
            [13.5, 7.6, 90, 0.25, 0.07, 0],
        ]

        probs = predictor2.predict(test_measurements)
        success = probs is not None and len(probs) == 4
        results.append({
            'test_num': 6,
            'function': 'Прогнозирование состояния',
            'input': '6 замеров с постепенным ухудшением',
            'expected': 'Возвращены вероятности для 4 состояний',
            'actual': f'Получено {len(probs) if probs else 0} вероятностей'
        })
        print(f"  Результат: {probs}")
        print(f"  Ожидалось: Словарь с 4 вероятностями")
        status = 'PASS' if success else 'FAIL'
        print(f"  Статус: {status}\n")

        # Тест 7: Получение предсказанного состояния
        if probs:
            print("Тест 7: Получение предсказанного состояния")
            predicted_state = predictor2.get_predicted_state(probs)
            success = 1 <= predicted_state <= 4
            results.append({
                'test_num': 7,
                'function': 'Получение предсказанного состояния',
                'input': f'Вероятности: {probs}',
                'expected': 'Состояние от 1 до 4',
                'actual': f'Предсказанное состояние: {predicted_state}'
            })
            print(f"  Результат: Состояние = {predicted_state}")
            print(f"  Ожидалось: 1-4")
            status = 'PASS' if success else 'FAIL'
            print(f"  Статус: {status}\n")

            # Тест 8: Расчет динамики прогноза
            print("Тест 8: Расчет динамики прогноза")
            current_state = 0
            forecast_dynamics = predictor2.get_forecast_dynamics(current_state, probs)
            success = forecast_dynamics in ["Стабильно", "Ухудшение", "Улучшение"]
            results.append({
                'test_num': 8,
                'function': 'Расчет динамики прогноза',
                'input': f'current_state={current_state}, predicted={predicted_state}',
                'expected': 'Динамика: Стабильно/Ухудшение/Улучшение',
                'actual': f'Динамика: {forecast_dynamics}'
            })
            print(f"  Результат: {forecast_dynamics}")
            print(f"  Ожидалось: Ухудшение (т.к. predicted > current)")
            status = 'PASS' if success else 'FAIL'
            print(f"  Статус: {status}\n")

            # Тест 9: Получение уверенности прогноза
            print("Тест 9: Получение уверенности прогноза")
            confidence = predictor2.get_confidence(probs)
            success = 0 <= confidence <= 1
            results.append({
                'test_num': 9,
                'function': 'Получение уверенности прогноза',
                'input': f'Вероятности: {probs}',
                'expected': 'Уверенность от 0 до 1',
                'actual': f'Уверенность: {confidence:.4f}'
            })
            print(f"  Результат: Уверенность = {confidence:.4f}")
            print(f"  Ожидалось: 0.0 - 1.0")
            status = 'PASS' if success else 'FAIL'
            print(f"  Статус: {status}\n")

    # Тест 10: Проверка размера окна
    print("Тест 10: Проверка размера окна")
    success = Predictor.WINDOW_SIZE == 6
    results.append({
        'test_num': 10,
        'function': 'Проверка размера окна',
        'input': 'Константа WINDOW_SIZE',
        'expected': 'WINDOW_SIZE = 6',
        'actual': f'WINDOW_SIZE = {Predictor.WINDOW_SIZE}'
    })
    print(f"  Результат: WINDOW_SIZE = {Predictor.WINDOW_SIZE}")
    print(f"  Ожидалось: 6")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    # Тест 11: Проверка списка признаков
    print("Тест 11: Проверка списка признаков")
    expected_features = ['temp', 'ph', 'o2', 'ammonia', 'nitrite', 'salinity']
    success = Predictor.FEATURES == expected_features
    results.append({
        'test_num': 11,
        'function': 'Проверка списка признаков',
        'input': 'Константа FEATURES',
        'expected': 'temp, ph, o2, ammonia, nitrite, salinity',
        'actual': f'{", ".join(Predictor.FEATURES)}'
    })
    print(f"  Результат: {', '.join(Predictor.FEATURES)}")
    print(f"  Ожидалось: temp, ph, o2, ammonia, nitrite, salinity")
    status = 'PASS' if success else 'FAIL'
    print(f"  Статус: {status}\n")

    return results

if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ МОДУЛЯ PREDICTOR (Нейросеть LSTM)")
    print("=" * 80)
    print()

    results = test_predictor()

    print("=" * 80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)
    print(f"Всего тестов: {len(results)}")
    print()
