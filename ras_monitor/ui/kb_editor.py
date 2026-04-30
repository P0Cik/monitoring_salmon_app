

class EvaluationEditorDialog(QDialog):
    def __init__(self, kb_db, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Оценка")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Список оценок:"))
        layout.addWidget(self.list_widget)
        add_layout = QHBoxLayout()
        self.new_eval_edit = QLineEdit()
        self.new_eval_edit.setPlaceholderText("Введите название...")
        add_layout.addWidget(self.new_eval_edit)
        self.add_btn = QPushButton("+")
        self.add_btn.setMaximumWidth(40)
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_evaluation)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_evaluations()
    
    def load_evaluations(self):
        self.list_widget.clear()
        for ev in self.kb_db.get_evaluations():
            item = QListWidgetItem(f"✓ {ev['name']}")
            item.setData(Qt.ItemDataRole.UserRole, ev['id'])
            self.list_widget.addItem(item)
            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.clicked.connect(lambda checked, eid=ev['id']: self.delete_evaluation(eid))
            self.list_widget.setItemWidget(item, del_btn)
    
    def add_evaluation(self):
        name = self.new_eval_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название оценки")
            return
        if self.kb_db.add_evaluation(name):
            self.new_eval_edit.clear()
            self.load_evaluations()
        else:
            QMessageBox.warning(self, "Ошибка", f"Оценка '{name}' уже существует")
    
    def delete_evaluation(self, eval_id):
        reply = QMessageBox.question(self, "Подтверждение", "Удалить эту оценку?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_evaluation(eval_id)
            self.load_evaluations()


class StateEditorDialog(QDialog):
    def __init__(self, kb_db, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Состояние среды")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Список состояний (порядок важен!):"))
        layout.addWidget(self.list_widget)
        add_layout = QHBoxLayout()
        self.new_state_edit = QLineEdit()
        self.new_state_edit.setPlaceholderText("Введите название...")
        add_layout.addWidget(self.new_state_edit)
        self.add_btn = QPushButton("+")
        self.add_btn.setMaximumWidth(40)
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_state)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        order_layout = QHBoxLayout()
        self.up_btn = QPushButton("⬆️ Вверх")
        self.up_btn.clicked.connect(self.move_up)
        order_layout.addWidget(self.up_btn)
        self.down_btn = QPushButton("⬇️ Вниз")
        self.down_btn.clicked.connect(self.move_down)
        order_layout.addWidget(self.down_btn)
        order_layout.addStretch()
        layout.addLayout(order_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_states()
    
    def load_states(self):
        self.list_widget.clear()
        for st in self.kb_db.get_state_order():
            item = QListWidgetItem(f"{st['order_index']}. {st['name']}")
            item.setData(Qt.ItemDataRole.UserRole, st['id'])
            self.list_widget.addItem(item)
    
    def add_state(self):
        name = self.new_state_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название состояния")
            return
        if self.kb_db.add_state(name):
            cur = self.kb_db.conn.cursor()
            cur.execute("SELECT id FROM kb_states WHERE name=?", (name,))
            new_id = cur.fetchone()[0]
            max_order = self.kb_db.conn.cursor().execute("SELECT COALESCE(MAX(order_index), 0) FROM kb_state_order").fetchone()[0]
            self.kb_db.update_state_order(new_id, max_order + 1)
            self.new_state_edit.clear()
            self.load_states()
        else:
            QMessageBox.warning(self, "Ошибка", f"Состояние '{name}' уже существует")
    
    def move_up(self):
        row = self.list_widget.currentRow()
        if row <= 0: return
        self._swap_rows(row, row - 1)
    
    def move_down(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= self.list_widget.count() - 1: return
        self._swap_rows(row, row + 1)
    
    def _swap_rows(self, row1, row2):
        item1, item2 = self.list_widget.item(row1), self.list_widget.item(row2)
        id1, id2 = item1.data(Qt.ItemDataRole.UserRole), item2.data(Qt.ItemDataRole.UserRole)
        cur = self.kb_db.conn.cursor()
        cur.execute("SELECT order_index FROM kb_state_order WHERE state_id=?", (id1,)); order1 = cur.fetchone()[0]
        cur.execute("SELECT order_index FROM kb_state_order WHERE state_id=?", (id2,)); order2 = cur.fetchone()[0]
        self.kb_db.update_state_order(id1, order2)
        self.kb_db.update_state_order(id2, order1)
        self.load_states()
        self.list_widget.setCurrentRow(row2)


class ParameterEditorDialog(QDialog):
    def __init__(self, kb_db, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Редактирование: Показатели среды")
        self.setMinimumWidth(500)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        layout.addWidget(QLabel("Список показателей:"))
        layout.addWidget(self.list_widget)
        add_layout = QHBoxLayout()
        self.new_param_edit = QLineEdit()
        self.new_param_edit.setPlaceholderText("Название...")
        add_layout.addWidget(self.new_param_edit)
        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("Ед. изм.")
        self.unit_edit.setMaximumWidth(80)
        add_layout.addWidget(self.unit_edit)
        self.add_btn = QPushButton("+")
        self.add_btn.setMaximumWidth(40)
        self.add_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_parameter)
        add_layout.addWidget(self.add_btn)
        layout.addLayout(add_layout)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_parameters()
    
    def load_parameters(self):
        self.list_widget.clear()
        for p in self.kb_db.get_parameters():
            unit_str = f" ({p['unit']})" if p['unit'] else ""
            range_str = f"[{p['min_possible']}; {p['max_possible']}]"
            item = QListWidgetItem(f"✓ {p['name']}{unit_str} {range_str}")
            item.setData(Qt.ItemDataRole.UserRole, p['id'])
            self.list_widget.addItem(item)
            del_btn = QToolButton()
            del_btn.setText("🗑️")
            del_btn.setStyleSheet("color: red; border: none;")
            del_btn.clicked.connect(lambda checked, pid=p['id']: self.delete_parameter(pid))
            self.list_widget.setItemWidget(item, del_btn)
    
    def add_parameter(self):
        name = self.new_param_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название показателя")
            return
        unit = self.unit_edit.text().strip()
        default_ranges = {'температура': (5.0, 32.0), 'pH': (0.0, 14.0), 'O₂': (0.0, 100.0), 'аммиак': (0.0, 2.0), 'нитриты': (0.0, 5.0), 'солёность': (0.0, 35.0)}
        min_p, max_p = default_ranges.get(name, (0.0, 100.0))
        if self.kb_db.add_parameter(name, unit, min_p, max_p):
            self.new_param_edit.clear()
            self.unit_edit.clear()
            self.load_parameters()
        else:
            QMessageBox.warning(self, "Ошибка", f"Показатель '{name}' уже существует")
    
    def delete_parameter(self, param_id):
        reply = QMessageBox.question(self, "Подтверждение", "Удалить этот показатель? Это также удалит связанные диапазоны.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.delete_parameter(param_id)
            self.load_parameters()


class ClinicalPictureDialog(QDialog):
    def __init__(self, kb_db, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Клиническая картина")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.eval_combo = QComboBox()
        for ev in self.kb_db.get_evaluations():
            self.eval_combo.addItem(ev['name'], ev['id'])
        self.eval_combo.currentIndexChanged.connect(self.load_parameters)
        form_layout.addRow("Оценка:", self.eval_combo)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Показатели, входящие в клиническую картину:"))
        self.params_scroll = QScrollArea()
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout()
        self.params_widget.setLayout(self.params_layout)
        self.params_scroll.setWidget(self.params_widget)
        self.params_scroll.setWidgetResizable(True)
        layout.addWidget(self.params_scroll)
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.apply_btn)
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_parameters()
    
    def load_parameters(self):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        selected_eval_id = self.eval_combo.currentData()
        selected_params = self.kb_db.get_clinical_picture(selected_eval_id)
        for p in self.kb_db.get_parameters():
            cb = QCheckBox(p['name'])
            cb.setProperty('param_id', p['id'])
            cb.setChecked(p['id'] in selected_params)
            self.params_layout.addWidget(cb)
    
    def save(self):
        selected_eval_id = self.eval_combo.currentData()
        selected_params = [self.params_layout.itemAt(i).widget().property('param_id') for i in range(self.params_layout.count()) if isinstance(self.params_layout.itemAt(i).widget(), QCheckBox) and self.params_layout.itemAt(i).widget().isChecked()]
        self.kb_db.save_clinical_picture(selected_eval_id, selected_params)
        QMessageBox.information(self, "Успех", "Клиническая картина сохранена")


class StateClinicalPictureDialog(QDialog):
    def __init__(self, kb_db, parent=None):
        super().__init__(parent)
        self.kb_db = kb_db
        self.setWindowTitle("Клиническая картина по состоянию")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.state_combo = QComboBox()
        for st in self.kb_db.get_states():
            self.state_combo.addItem(st['name'], st['id'])
        self.state_combo.currentIndexChanged.connect(self.load_parameters)
        form_layout.addRow("Состояние среды:", self.state_combo)
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Показатели, определяющие состояние:"))
        self.params_scroll = QScrollArea()
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout()
        self.params_widget.setLayout(self.params_layout)
        self.params_scroll.setWidget(self.params_widget)
        self.params_scroll.setWidgetResizable(True)
        layout.addWidget(self.params_scroll)
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        self.apply_btn.clicked.connect(self.save)
        btn_layout.addWidget(self.apply_btn)
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.load_parameters()
    
    def load_parameters(self):
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        selected_state_id = self.state_combo.currentData()
        selected_params = self.kb_db.get_state_clinical_picture(selected_state_id)
        for p in self.kb_db.get_parameters():
            cb = QCheckBox(p['name'])
            cb.setProperty('param_id', p['id'])
            cb.setChecked(p['id'] in selected_params)
            self.params_layout.addWidget(cb)
    
    def save(self):
        selected_state_id = self.state_combo.currentData()
        selected_params = [self.params_layout.itemAt(i).widget().property('param_id') for i in range(self.params_layout.count()) if isinstance(self.params_layout.itemAt(i).widget(), QCheckBox) and self.params_layout.itemAt(i).widget().isChecked()]
        self.kb_db.save_state_clinical_picture(selected_state_id, selected_params)
        QMessageBox.information(self, "Успех", "Клиническая картина сохранена")


class KBEditorMainWindow(QMainWindow):
    def __init__(self, db_path="ras_monitor.db", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор базы знаний УЗВ")
        self.setGeometry(100, 100, 1000, 700)
        self.kb_db = KBDatabase(db_path)
        self.setup_ui()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Термины:"))
        self.term_list = QListWidget()
        terms = ["Оценка", "Состояние среды", "Показатели среды", "Клиническая картина", "Клиническая картина по состоянию", "Нормальные значения", "Степень тяжести значений", "Значения для пригодности", "Возможные значения", "Порядок состояний"]
        self.term_list.addItems(terms)
        self.term_list.currentRowChanged.connect(self.open_editor)
        left_layout.addWidget(self.term_list)
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(250)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel("Действия:"))
        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)
        action_layout = QVBoxLayout()
        self.check_btn = QPushButton("✓ Проверка полноты знаний")
        self.check_btn.clicked.connect(self.check_completeness)
        action_layout.addWidget(self.check_btn)
        self.save_db_btn = QPushButton("💾 Сохранить в БД")
        self.save_db_btn.clicked.connect(self.save_to_db)
        action_layout.addWidget(self.save_db_btn)
        self.load_db_btn = QPushButton("📂 Загрузить из БД")
        self.load_db_btn.clicked.connect(self.load_from_db)
        action_layout.addWidget(self.load_db_btn)
        self.reset_btn = QPushButton("🔄 Сбросить к значениям по умолчанию")
        self.reset_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        self.reset_btn.clicked.connect(self.reset_defaults)
        action_layout.addWidget(self.reset_btn)
        action_layout.addStretch()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.close)
        action_layout.addWidget(self.close_btn)
        right_layout.addLayout(action_layout)
        right_panel.setLayout(right_layout)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        central_widget.setLayout(main_layout)
    
    def open_editor(self, index):
        term = self.term_list.item(index).text()
        editors = {
            "Оценка": lambda: EvaluationEditorDialog(self.kb_db, self).exec(),
            "Состояние среды": lambda: StateEditorDialog(self.kb_db, self).exec(),
            "Показатели среды": lambda: ParameterEditorDialog(self.kb_db, self).exec(),
            "Клиническая картина": lambda: ClinicalPictureDialog(self.kb_db, self).exec(),
            "Клиническая картина по состоянию": lambda: StateClinicalPictureDialog(self.kb_db, self).exec(),
            "Нормальные значения": lambda: NormalRangesDialog(self.kb_db, self).exec(),
            "Степень тяжести значений": lambda: SeverityMappingDialog(self.kb_db, self).exec(),
            "Значения для пригодности": lambda: SuitabilityValuesDialog(self.kb_db, self).exec(),
            "Возможные значения": lambda: PossibleRangesDialog(self.kb_db, self).exec(),
            "Порядок состояний": lambda: StateOrderDialog(self.kb_db, self).exec(),
        }
        if term in editors:
            editors[term]()
    
    def check_completeness(self):
        issues = []
        if len(self.kb_db.get_evaluations()) < 2:
            issues.append("• Должно быть минимум 2 оценки (пригодна/непригодна)")
        states = self.kb_db.get_states()
        if len(states) < 4:
            issues.append("• Рекомендуется минимум 4 состояния среды")
        params = self.kb_db.get_parameters()
        if len(params) < 6:
            issues.append("• Рекомендуется минимум 6 показателей")
        normal = self.kb_db.get_normal_ranges()
        missing_normal = [p['name'] for p in params if not any(n['id'] == p['id'] for n in normal)]
        if missing_normal:
            issues.append(f"• Нет нормальных диапазонов для: {', '.join(missing_normal)}")
        possible = self.kb_db.get_possible_ranges()
        missing_possible = [p['name'] for p in params if not any(po['id'] == p['id'] for po in possible)]
        if missing_possible:
            issues.append(f"• Нет возможных диапазонов для: {', '.join(missing_possible)}")
        severity = self.kb_db.get_severity_mapping()
        if len(severity) == 0:
            issues.append("• Нет маппинга степеней тяжести")
        if issues:
            msg = "Обнаружены проблемы:\n\n" + "\n".join(issues)
            QMessageBox.warning(self, "Проверка полноты", msg)
        else:
            QMessageBox.information(self, "Проверка полноты", "База знаний заполнена полностью!")
    
    def save_to_db(self):
        QMessageBox.information(self, "Сохранение", "Все изменения сохраняются автоматически при редактировании.")
    
    def load_from_db(self):
        QMessageBox.information(self, "Загрузка", "Данные загружаются автоматически при запуске редактора.")
    
    def reset_defaults(self):
        reply = QMessageBox.question(self, "Подтверждение", "Вы уверены? Все изменения будут потеряны.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.kb_db.reset_to_defaults()
            QMessageBox.information(self, "Успех", "База знаний сброшена к значениям по умолчанию")
    
    def closeEvent(self, event):
        self.kb_db.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = KBEditorMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
