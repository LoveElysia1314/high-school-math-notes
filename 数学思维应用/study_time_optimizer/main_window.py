from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .config_manager import ConfigManager
from .constants import (
    CORE_SUBJECTS,
    CURVE_STRENGTH,
    DEFAULT_ELECTIVES,
    GROUP_A,
    GROUP_B,
    PANEL_STATE_FILE,
    SPECTRUM_ELECTIVES,
    SUBJECT_ADVANCED_DEFAULTS,
    SUBJECT_AXIS,
    SUBJECT_FULL_MARKS,
    SUBJECT_SCORE_DEFAULTS,
)
from .dialogs import PresetManagementDialog, SubjectSelectionDialog
from .model import StudyTimeModel


class StudyOptimizerApp(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("学习时间优化器（重构版）")
        self._suspend_auto_calc = False
        self._syncing_param_widgets = False
        self.selected_electives = list(DEFAULT_ELECTIVES)
        self.config_mgr = ConfigManager()

        self._calc_timer = QTimer(self)
        self._calc_timer.setSingleShot(True)
        self._calc_timer.timeout.connect(lambda: self.calculate(show_input_error=False))

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_panel_state)

        self._param_generate_timer = QTimer(self)
        self._param_generate_timer.setSingleShot(True)
        self._param_generate_timer.timeout.connect(self.generate_scores_from_params)

        self._setup_ui()
        self._connect_signals()
        self.refresh_preset_combo()
        if not self._load_panel_state():
            self.reset_default()

        self._finalize_window_size()

    def _setup_ui(self) -> None:
        self.root_layout = QGridLayout(self)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setHorizontalSpacing(10)
        self.root_layout.setVerticalSpacing(10)

        self.ctrl_panel = QGroupBox("控制面板")
        self.ctrl_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ctrl_main_layout = QVBoxLayout(self.ctrl_panel)
        ctrl_main_layout.setContentsMargins(8, 8, 8, 8)
        ctrl_main_layout.setSpacing(6)

        basic_group = QGroupBox("学习时间与计算")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setHorizontalSpacing(8)
        basic_layout.setVerticalSpacing(6)

        basic_layout.addWidget(QLabel("额外学习时间 T (小时/周)"), 0, 0)
        self.total_time_spin = QDoubleSpinBox()
        self.total_time_spin.setRange(1, 100)
        self.total_time_spin.setSingleStep(1)
        self.total_time_spin.setDecimals(0)
        self.total_time_spin.setValue(30)
        self.total_time_spin.setMinimumWidth(90)
        basic_layout.addWidget(self.total_time_spin, 0, 1)

        self.auto_calc_check = QCheckBox("自动计算")
        self.auto_calc_check.setChecked(True)
        basic_layout.addWidget(self.auto_calc_check, 0, 2)

        self.btn_calc = QPushButton("开始计算")
        self.btn_calc.setMinimumWidth(90)
        basic_layout.addWidget(self.btn_calc, 0, 3)

        self.warning_label = QLabel("结果状态：等待计算。")
        self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.warning_label.setWordWrap(False)
        basic_layout.addWidget(self.warning_label, 1, 0, 1, 4, Qt.AlignBottom)
        basic_layout.setColumnStretch(0, 0)
        basic_layout.setColumnStretch(1, 1)
        basic_layout.setColumnStretch(2, 0)
        basic_layout.setColumnStretch(3, 0)
        ctrl_main_layout.addWidget(basic_group)

        preset_group = QGroupBox("预设工作流")
        preset_layout = QGridLayout(preset_group)
        preset_layout.setHorizontalSpacing(8)
        preset_layout.setVerticalSpacing(6)

        preset_layout.addWidget(QLabel("快速预设"), 0, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(150)
        preset_layout.addWidget(self.preset_combo, 0, 1)

        self.preset_auto_apply_check = QCheckBox("切换即应用")
        self.preset_auto_apply_check.setChecked(True)
        preset_layout.addWidget(self.preset_auto_apply_check, 0, 2)

        self.btn_apply_selected_preset = QPushButton("应用选中预设")
        self.btn_apply_selected_preset.setMinimumWidth(90)
        preset_layout.addWidget(self.btn_apply_selected_preset, 0, 3)

        self.btn_save_as_preset = QPushButton("另存为预设")
        self.btn_save_as_preset.setMinimumWidth(90)
        preset_layout.addWidget(self.btn_save_as_preset, 1, 0)

        self.btn_override_current_preset = QPushButton("覆盖当前预设")
        self.btn_override_current_preset.setMinimumWidth(90)
        preset_layout.addWidget(self.btn_override_current_preset, 1, 1)

        self.btn_preset_manage = QPushButton("管理预设")
        self.btn_preset_manage.setMinimumWidth(90)
        preset_layout.addWidget(self.btn_preset_manage, 1, 2)

        self.btn_reset = QPushButton("恢复默认")
        self.btn_reset.setMinimumWidth(90)
        preset_layout.addWidget(self.btn_reset, 1, 3)
        preset_layout.setColumnStretch(0, 0)
        preset_layout.setColumnStretch(1, 1)
        preset_layout.setColumnStretch(2, 0)
        preset_layout.setColumnStretch(3, 0)
        ctrl_main_layout.addWidget(preset_group)

        param_group = QGroupBox("参数化生成")
        param_layout = QGridLayout(param_group)
        param_layout.setHorizontalSpacing(8)
        param_layout.setVerticalSpacing(6)

        param_layout.addWidget(QLabel("整体得分率"), 0, 0)
        self.overall_rate_slider = QSlider(Qt.Horizontal)
        self.overall_rate_slider.setRange(0, 100)
        self.overall_rate_slider.setValue(80)
        param_layout.addWidget(self.overall_rate_slider, 0, 1)
        self.overall_rate_spin = QDoubleSpinBox()
        self.overall_rate_spin.setRange(0.0, 1.0)
        self.overall_rate_spin.setSingleStep(0.01)
        self.overall_rate_spin.setDecimals(2)
        self.overall_rate_spin.setValue(0.80)
        param_layout.addWidget(self.overall_rate_spin, 0, 2)

        param_layout.addWidget(QLabel("学生偏科光谱[-1,1]"), 1, 0)
        self.spectrum_slider = QSlider(Qt.Horizontal)
        self.spectrum_slider.setRange(-100, 100)
        self.spectrum_slider.setValue(0)
        param_layout.addWidget(self.spectrum_slider, 1, 1)
        self.spectrum_spin = QDoubleSpinBox()
        self.spectrum_spin.setRange(-1.0, 1.0)
        self.spectrum_spin.setSingleStep(0.01)
        self.spectrum_spin.setDecimals(2)
        self.spectrum_spin.setValue(0.00)
        param_layout.addWidget(self.spectrum_spin, 1, 2)

        param_layout.addWidget(QLabel("基准-当前间隔"), 2, 0)
        self.delta_base_spin = QDoubleSpinBox()
        self.delta_base_spin.setRange(0.01, 0.50)
        self.delta_base_spin.setSingleStep(0.01)
        self.delta_base_spin.setDecimals(2)
        self.delta_base_spin.setValue(0.12)
        param_layout.addWidget(self.delta_base_spin, 2, 1)

        param_layout.addWidget(QLabel("当前-上限间隔"), 2, 2)
        self.delta_cap_spin = QDoubleSpinBox()
        self.delta_cap_spin.setRange(0.01, 0.50)
        self.delta_cap_spin.setSingleStep(0.01)
        self.delta_cap_spin.setDecimals(2)
        self.delta_cap_spin.setValue(0.12)
        param_layout.addWidget(self.delta_cap_spin, 2, 3)

        self.param_auto_generate_check = QCheckBox("参数变化自动生成")
        self.param_auto_generate_check.setChecked(False)
        param_layout.addWidget(self.param_auto_generate_check, 3, 0)

        self.btn_generate_by_params = QPushButton("按参数生成")
        self.btn_generate_by_params.setMinimumWidth(90)
        param_layout.addWidget(self.btn_generate_by_params, 3, 3)
        param_layout.setColumnStretch(0, 0)
        param_layout.setColumnStretch(1, 1)
        param_layout.setColumnStretch(2, 0)
        param_layout.setColumnStretch(3, 0)
        ctrl_main_layout.addWidget(param_group)

        tool_group = QGroupBox("工具与说明")
        tool_layout = QGridLayout(tool_group)
        tool_layout.setHorizontalSpacing(8)
        tool_layout.setVerticalSpacing(6)

        self.btn_subjects = QPushButton("科目选择")
        self.btn_subjects.setMinimumWidth(90)
        tool_layout.addWidget(self.btn_subjects, 0, 0)

        self.btn_explanation = QPushButton("程序说明")
        self.btn_explanation.setMinimumWidth(90)
        tool_layout.addWidget(self.btn_explanation, 0, 1)

        self.remember_state_check = QCheckBox("记忆当前状态")
        self.remember_state_check.setChecked(False)
        tool_layout.addWidget(self.remember_state_check, 0, 2)

        self.advanced_tip = QLabel("当前使用默认高级参数。")
        self.advanced_tip.setStyleSheet("color: #333333;")
        self.advanced_tip.setWordWrap(False)
        tool_layout.addWidget(self.advanced_tip, 1, 0, 1, 3, Qt.AlignBottom)
        tool_layout.setColumnStretch(0, 0)
        tool_layout.setColumnStretch(1, 1)
        tool_layout.setColumnStretch(2, 0)
        ctrl_main_layout.addWidget(tool_group)

        self.status_panel = QGroupBox("状态自评")
        status_layout = QVBoxLayout(self.status_panel)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(6)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "科目",
                "当前分 S_cur",
                "长期上限 M",
                "基础分 S0",
                "学习效率 eta",
                "衰退强度 theta",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        status_layout.addWidget(self.table)

        self.result_panel = QGroupBox("优化结果")
        res_layout = QVBoxLayout(self.result_panel)
        res_layout.setContentsMargins(8, 8, 8, 8)
        res_layout.setSpacing(6)
        self.result_table = QTableWidget(0, 6)
        self.result_table.setHorizontalHeaderLabels(
            [
                "科目",
                "保底时间 t_min",
                "全局最优分配",
                "单科突破时提分",
                "保底稳态分",
                "全局稳态分",
            ]
        )
        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.result_table.horizontalHeader().setStretchLastSection(False)
        self.result_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        res_layout.addWidget(self.result_table)

        self.root_layout.addWidget(self.ctrl_panel, 0, 0, 2, 1)
        self.root_layout.addWidget(self.status_panel, 0, 1)
        self.root_layout.addWidget(self.result_panel, 1, 1)

        self.root_layout.setColumnStretch(0, 1)
        self.root_layout.setColumnStretch(1, 1)
        self.root_layout.setRowStretch(0, 0)
        self.root_layout.setRowStretch(1, 1)

    def _connect_signals(self) -> None:
        self.table.itemChanged.connect(self.on_input_changed)
        self.total_time_spin.valueChanged.connect(self.on_input_changed)
        self.auto_calc_check.stateChanged.connect(self.on_input_changed)
        self.btn_calc.clicked.connect(lambda: self.calculate(show_input_error=True))
        self.btn_subjects.clicked.connect(self.select_subjects)
        self.preset_combo.currentTextChanged.connect(self.on_preset_combo_changed)
        self.btn_apply_selected_preset.clicked.connect(
            self.apply_selected_preset_from_panel
        )
        self.btn_preset_manage.clicked.connect(self.open_preset_management)
        self.btn_save_as_preset.clicked.connect(self.save_as_preset_from_panel)
        self.btn_override_current_preset.clicked.connect(
            self.override_current_preset_from_panel
        )
        self.btn_reset.clicked.connect(self.reset_default)
        self.btn_explanation.clicked.connect(self.show_explanation)
        self.remember_state_check.stateChanged.connect(self.on_remember_state_changed)
        self.btn_generate_by_params.clicked.connect(self.generate_scores_from_params)
        self.overall_rate_slider.valueChanged.connect(self.on_overall_slider_changed)
        self.overall_rate_spin.valueChanged.connect(self.on_overall_spin_changed)
        self.spectrum_slider.valueChanged.connect(self.on_spectrum_slider_changed)
        self.spectrum_spin.valueChanged.connect(self.on_spectrum_spin_changed)
        self.delta_base_spin.valueChanged.connect(self.on_param_widget_changed)
        self.delta_cap_spin.valueChanged.connect(self.on_param_widget_changed)

    def on_input_changed(self, *_args) -> None:
        if self._suspend_auto_calc:
            return
        self.update_param_tip()
        if self.auto_calc_check.isChecked():
            self._calc_timer.start(500)
        self._schedule_panel_state_save()

    def refresh_preset_combo(self) -> None:
        current = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(self.config_mgr.get_preset_names())
        self.preset_combo.setCurrentText(
            current if current in self.config_mgr.get_preset_names() else "学霸-偏理"
        )
        self.preset_combo.blockSignals(False)

    def on_preset_combo_changed(self, preset_name: str) -> None:
        if preset_name and self.preset_auto_apply_check.isChecked():
            self.apply_preset(preset_name)
            self.config_mgr.set_last_preset(preset_name)
            self._schedule_panel_state_save()

    def apply_selected_preset_from_panel(self) -> None:
        preset_name = self.preset_combo.currentText().strip()
        if not preset_name:
            QMessageBox.information(self, "提示", "请先选择一个预设。")
            return
        self.apply_preset(preset_name)
        self.config_mgr.set_last_preset(preset_name)
        self._schedule_panel_state_save()

    def on_remember_state_changed(self, _state: int) -> None:
        self._save_panel_state()

    def on_overall_slider_changed(self, value: int) -> None:
        if self._syncing_param_widgets:
            return
        self._syncing_param_widgets = True
        self.overall_rate_spin.setValue(value / 100.0)
        self._syncing_param_widgets = False
        self.on_param_widget_changed()

    def on_overall_spin_changed(self, value: float) -> None:
        if self._syncing_param_widgets:
            return
        self._syncing_param_widgets = True
        self.overall_rate_slider.setValue(int(round(value * 100)))
        self._syncing_param_widgets = False
        self.on_param_widget_changed()

    def on_spectrum_slider_changed(self, value: int) -> None:
        if self._syncing_param_widgets:
            return
        self._syncing_param_widgets = True
        self.spectrum_spin.setValue(value / 100.0)
        self._syncing_param_widgets = False
        self.on_param_widget_changed()

    def on_spectrum_spin_changed(self, value: float) -> None:
        if self._syncing_param_widgets:
            return
        self._syncing_param_widgets = True
        self.spectrum_slider.setValue(int(round(value * 100)))
        self._syncing_param_widgets = False
        self.on_param_widget_changed()

    def on_param_widget_changed(self, *_args) -> None:
        if self._syncing_param_widgets:
            return
        if self.param_auto_generate_check.isChecked():
            self._param_generate_timer.start(400)
        self._schedule_panel_state_save()

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    def _power_curve(self, x: float, p: float) -> float:
        x = self._clamp(x, 0.0, 1.0)
        p = max(0.05, p)
        return x**p

    def _subject_exponent(self, axis: float, student_spectrum: float) -> float:
        p = 1.0 - CURVE_STRENGTH * student_spectrum * axis
        return self._clamp(p, 0.2, 2.5)

    def _difficulty_index(self, eta: float, theta: float) -> float:
        """基于学习效率与衰退强度自动计算难度系数：d = theta / (eta + theta)。"""
        denom = eta + theta
        if denom <= 1e-12:
            return 0.5
        return self._clamp(theta / denom, 0.0, 1.0)

    def _solve_gamma_for_target_avg(
        self,
        overall_rate: float,
        raw_exponents: List[float],
        full_marks: List[float],
    ) -> float:
        x = self._clamp(overall_rate, 0.0, 1.0)
        if (
            x <= 1e-12
            or x >= 1.0 - 1e-12
            or not raw_exponents
            or not full_marks
            or len(raw_exponents) != len(full_marks)
        ):
            return 0.0

        total_full = sum(max(0.0, float(m)) for m in full_marks)
        if total_full <= 1e-12:
            return 0.0

        def avg_rate(gamma: float) -> float:
            weighted_sum = 0.0
            for p, mark in zip(raw_exponents, full_marks):
                weighted_sum += self._power_curve(x, p + gamma) * max(0.0, float(mark))
            return weighted_sum / total_full

        lo, hi = -2.0, 2.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if avg_rate(mid) > x:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    def _to_score(self, rate: float, full_mark: int) -> float:
        return round(self._clamp(rate, 0.0, 1.0) * full_mark, 1)

    def _get_param_config(self) -> Dict:
        return {
            "overall_rate": float(self.overall_rate_spin.value()),
            "student_spectrum": float(self.spectrum_spin.value()),
            "delta_base_exp": float(self.delta_base_spin.value()),
            "delta_cap_exp": float(self.delta_cap_spin.value()),
        }

    def _set_param_config(self, params: Dict) -> None:
        self._syncing_param_widgets = True
        self.overall_rate_spin.setValue(float(params.get("overall_rate", 0.8)))
        self.overall_rate_slider.setValue(
            int(round(self.overall_rate_spin.value() * 100))
        )
        self.spectrum_spin.setValue(float(params.get("student_spectrum", 0.0)))
        self.spectrum_slider.setValue(int(round(self.spectrum_spin.value() * 100)))
        self.delta_base_spin.setValue(float(params.get("delta_base_exp", 0.12)))
        self.delta_cap_spin.setValue(float(params.get("delta_cap_exp", 0.12)))
        self._syncing_param_widgets = False

    def _generate_score_triplets(
        self,
        names: List[str],
        params: Dict,
        subject_adv: Dict[str, tuple[float, float]],
    ) -> Dict[str, List[float]]:
        overall_rate = self._clamp(float(params.get("overall_rate", 0.8)), 0.0, 1.0)
        student_spectrum = self._clamp(
            float(params.get("student_spectrum", 0.0)), -1.0, 1.0
        )
        delta_base_exp = float(params.get("delta_base_exp", 0.12))
        delta_cap_exp = float(params.get("delta_cap_exp", 0.12))

        difficulties = {
            name: self._difficulty_index(*subject_adv.get(name, (0.03, 0.10)))
            for name in names
        }
        difficulty_mean = (
            sum(difficulties.values()) / len(difficulties) if difficulties else 0.5
        )

        raw_exponents = [
            self._subject_exponent(SUBJECT_AXIS.get(name, 0.0), student_spectrum)
            + (difficulties.get(name, difficulty_mean) - difficulty_mean)
            for name in names
        ]
        full_marks = [float(SUBJECT_FULL_MARKS.get(name, 100)) for name in names]
        gamma = self._solve_gamma_for_target_avg(
            overall_rate, raw_exponents, full_marks
        )

        scores = {}
        for name in names:
            axis = SUBJECT_AXIS.get(name, 0.0)
            full_mark = SUBJECT_FULL_MARKS.get(name, 100)
            p_cur = (
                self._subject_exponent(axis, student_spectrum)
                + (difficulties.get(name, difficulty_mean) - difficulty_mean)
                + gamma
            )
            p_base = p_cur + delta_base_exp
            p_cap = max(0.05, p_cur - delta_cap_exp)

            cur_rate = self._power_curve(overall_rate, p_cur)
            base_rate = self._power_curve(overall_rate, p_base)
            cap_rate = self._power_curve(overall_rate, p_cap)

            if 1e-9 < overall_rate < 1.0 - 1e-9:
                if base_rate >= cur_rate:
                    base_rate = max(0.0, cur_rate - 0.005)
                if cap_rate <= cur_rate:
                    cap_rate = min(1.0, cur_rate + 0.005)

            cur = self._to_score(cur_rate, full_mark)
            s0 = self._to_score(base_rate, full_mark)
            m = self._to_score(cap_rate, full_mark)

            if s0 >= cur:
                s0 = max(0.0, cur - 1.0)
            if m <= cur:
                m = min(float(full_mark), cur + 1.0)
            if m <= s0:
                m = min(float(full_mark), s0 + 2.0)

            scores[name] = [cur, m, s0]

        return scores

    def generate_scores_from_params(self) -> None:
        snapshot = self._get_table_snapshot()
        names = self._build_subject_names()
        params = self._get_param_config()
        subject_adv: Dict[str, tuple[float, float]] = {}
        for name in names:
            vals = snapshot.get(name, [])
            if len(vals) == 5:
                try:
                    eta = float(vals[3])
                    theta = float(vals[4])
                    subject_adv[name] = (eta, theta)
                    continue
                except ValueError:
                    pass
            defaults = SUBJECT_ADVANCED_DEFAULTS.get(name, [0.03, 0.10])
            subject_adv[name] = (float(defaults[0]), float(defaults[1]))

        generated = self._generate_score_triplets(names, params, subject_adv)

        merged_snapshot = {}
        for name in names:
            adv_defaults = SUBJECT_ADVANCED_DEFAULTS.get(name, [0.03, 0.10])
            old_vals = snapshot.get(name, [])
            if len(old_vals) == 5:
                adv_vals = [old_vals[3], old_vals[4]]
            else:
                adv_vals = [str(adv_defaults[0]), str(adv_defaults[1])]

            cur, m, s0 = generated.get(
                name, SUBJECT_SCORE_DEFAULTS.get(name, [70, 85, 60])
            )
            merged_snapshot[name] = [
                str(cur),
                str(m),
                str(s0),
                adv_vals[0],
                adv_vals[1],
            ]

        self._populate_subject_table(merged_snapshot)
        self._schedule_panel_state_save()

    def _electives_from_spectrum(self, spectrum: float) -> List[str]:
        if spectrum > 0.15:
            return list(SPECTRUM_ELECTIVES["偏理"])
        if spectrum < -0.15:
            return list(SPECTRUM_ELECTIVES["偏文"])
        return list(SPECTRUM_ELECTIVES["均衡"])

    def open_preset_management(self) -> None:
        dialog = PresetManagementDialog(self.config_mgr, self._get_current_config, self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_preset_combo()

    def save_as_preset_from_panel(self) -> None:
        name, ok = QInputDialog.getText(self, "另存为预设", "预设名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.config_mgr.get_preset_names():
            QMessageBox.warning(self, "保存失败", f"预设 '{name}' 已存在。")
            return

        if self.config_mgr.create_preset(name, self._get_current_config()):
            self.refresh_preset_combo()
            self.preset_combo.setCurrentText(name)
            self.config_mgr.set_last_preset(name)
            QMessageBox.information(self, "保存成功", f"已保存为预设 '{name}'。")

    def override_current_preset_from_panel(self) -> None:
        name = self.preset_combo.currentText().strip()
        if not name:
            QMessageBox.information(self, "提示", "请先选择要覆盖的预设。")
            return

        if (
            QMessageBox.question(self, "确认覆盖", f"确定要覆盖当前预设 '{name}' 吗？")
            != QMessageBox.Yes
        ):
            return

        self.config_mgr.override_preset(name, self._get_current_config())
        self.refresh_preset_combo()
        self.preset_combo.setCurrentText(name)
        self.config_mgr.set_last_preset(name)
        QMessageBox.information(self, "覆盖成功", f"预设 '{name}' 已更新。")

    def apply_preset(self, preset_name: str) -> None:
        preset = self.config_mgr.get_preset(preset_name)
        if not preset:
            return

        params = preset.get("params") if isinstance(preset, dict) else None
        if isinstance(params, dict):
            self._set_param_config(params)

        default_electives = self._electives_from_spectrum(self.spectrum_spin.value())
        self.selected_electives = list(preset.get("electives", default_electives))

        if preset.get("mode") == "parametric":
            self.generate_scores_from_params()
            return

        snapshot = {}
        for name, vals in preset.get("subjects", {}).items():
            if not isinstance(vals, list) or len(vals) != 5:
                continue
            snapshot[name] = [str(v) for v in vals]
        self._populate_subject_table(snapshot)

    def _get_current_config(self) -> Dict:
        snapshot = self._get_table_snapshot()
        config = {
            "mode": "custom",
            "params": self._get_param_config(),
            "electives": list(self.selected_electives),
            "subjects": {},
        }
        for name, values in snapshot.items():
            try:
                config["subjects"][name] = [
                    float(values[0]),
                    float(values[1]),
                    float(values[2]),
                    float(values[3]),
                    float(values[4]),
                ]
            except ValueError:
                pass
        return config

    def _get_table_snapshot(self) -> Dict[str, List[str]]:
        snapshot = {}
        for i in range(self.table.rowCount()):
            name_item = self.table.item(i, 0)
            if not name_item:
                continue
            name = name_item.text().strip()
            vals = [
                self.table.item(i, j).text().strip() if self.table.item(i, j) else " "
                for j in range(1, 6)
            ]
            snapshot[name] = vals
        return snapshot

    def _build_subject_names(self) -> List[str]:
        return CORE_SUBJECTS + list(self.selected_electives)

    def _populate_subject_table(
        self, snapshot: Optional[Dict[str, List[str]]] = None
    ) -> None:
        snapshot = snapshot or {}
        self._suspend_auto_calc = True
        names = self._build_subject_names()
        self.table.blockSignals(True)
        self.table.setRowCount(len(names))
        self.result_table.setRowCount(len(names) + 1)

        for i, name in enumerate(names):
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)

            score_defaults = SUBJECT_SCORE_DEFAULTS.get(name, [70, 85, 60])
            adv_defaults = SUBJECT_ADVANCED_DEFAULTS.get(name, [0.03, 0.10])
            defaults = score_defaults + adv_defaults
            raw_values = snapshot.get(name)
            if isinstance(raw_values, list) and len(raw_values) == 5:
                values = [str(x) for x in raw_values]
            else:
                values = [str(x) for x in defaults]
            for j in range(1, 6):
                val = values[j - 1] if j - 1 < len(values) else " "
                self.table.setItem(i, j, QTableWidgetItem(val))

        self.table.blockSignals(False)
        self._suspend_auto_calc = False
        self.update_param_tip()
        self.calculate(show_input_error=False)
        self._auto_adjust_table_columns(self.table)
        self._adjust_table_height(self.table)
        self._finalize_window_size()

    def select_subjects(self) -> None:
        dialog = SubjectSelectionDialog(self.selected_electives, self)
        if dialog.exec() != QDialog.Accepted:
            return
        selected = dialog.selected_subjects()
        a_count = sum(1 for s in selected if s in GROUP_A)
        b_count = sum(1 for s in selected if s in GROUP_B)
        if not (a_count == 1 and b_count == 2):
            QMessageBox.warning(
                self, "选科错误", "需满足：物理/历史 1 科 + 生化政地 2 科。"
            )
            return
        snapshot = self._get_table_snapshot()
        self.selected_electives = selected
        self._populate_subject_table(snapshot)
        self._schedule_panel_state_save()

    def update_param_tip(self) -> None:
        customized = False
        try:
            for i in range(self.table.rowCount()):
                name = self.table.item(i, 0).text().strip()
                adv_defaults = SUBJECT_ADVANCED_DEFAULTS.get(name)
                if not adv_defaults:
                    continue
                eta = float(self.table.item(i, 4).text().strip())
                theta = float(self.table.item(i, 5).text().strip())
                if (
                    abs(eta - adv_defaults[0]) > 1e-9
                    or abs(theta - adv_defaults[1]) > 1e-9
                ):
                    customized = True
                    break
        except Exception:
            customized = True

        if customized:
            self.advanced_tip.setText(
                "⚠ 检测到高级参数已修改。若结果异常，请点击“恢复默认”。"
            )
            self.advanced_tip.setStyleSheet("color: #9a4f00;")
        else:
            self.advanced_tip.setText("ℹ 当前使用默认高级参数。")
            self.advanced_tip.setStyleSheet("color: #666666;")

    def reset_default(self) -> None:
        last_preset = self.config_mgr.get_last_preset()
        default_preset = last_preset if last_preset else "学霸-偏理"
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentText(default_preset)
        self.preset_combo.blockSignals(False)
        self.apply_preset(default_preset)
        self.config_mgr.set_last_preset(default_preset)
        self._schedule_panel_state_save()

    def _schedule_panel_state_save(self) -> None:
        if self.remember_state_check.isChecked() and not self._suspend_auto_calc:
            self._save_timer.start(600)

    def _read_panel_config(self) -> Dict:
        path = Path(PANEL_STATE_FILE)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_panel_config(self, data: Dict) -> None:
        try:
            with open(PANEL_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _build_panel_state(self) -> Dict:
        return {
            "preset_name": self.preset_combo.currentText(),
            "total_time": float(self.total_time_spin.value()),
            "auto_calc": self.auto_calc_check.isChecked(),
            "params": self._get_param_config(),
            "electives": list(self.selected_electives),
            "subjects": self._get_table_snapshot(),
        }

    def _load_panel_state(self) -> bool:
        config = self._read_panel_config()
        remember_state = bool(config.get("remember_state", False))

        self.remember_state_check.blockSignals(True)
        self.remember_state_check.setChecked(remember_state)
        self.remember_state_check.blockSignals(False)

        if not remember_state:
            return False

        state = config.get("panel_state")
        if not isinstance(state, dict):
            return False

        try:
            self._suspend_auto_calc = True

            self.total_time_spin.setValue(float(state.get("total_time", 30)))
            self.auto_calc_check.setChecked(bool(state.get("auto_calc", True)))
            params = state.get("params", {})
            if isinstance(params, dict):
                self._set_param_config(params)

            electives = state.get("electives", list(DEFAULT_ELECTIVES))
            all_electives = set(GROUP_A + GROUP_B)
            if isinstance(electives, list):
                restored = [s for s in electives if s in all_electives]
            else:
                restored = list(DEFAULT_ELECTIVES)

            a_count = sum(1 for s in restored if s in GROUP_A)
            b_count = sum(1 for s in restored if s in GROUP_B)
            self.selected_electives = (
                restored if (a_count == 1 and b_count == 2) else list(DEFAULT_ELECTIVES)
            )

            preset_name = state.get("preset_name", "")
            if (
                isinstance(preset_name, str)
                and preset_name in self.config_mgr.get_preset_names()
            ):
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentText(preset_name)
                self.preset_combo.blockSignals(False)

            snapshot = state.get("subjects", {})
            if not isinstance(snapshot, dict):
                return False
            self._populate_subject_table(snapshot)

            return True
        except Exception:
            return False
        finally:
            self._suspend_auto_calc = False

    def _save_panel_state(self) -> None:
        config = self._read_panel_config()
        config["remember_state"] = self.remember_state_check.isChecked()
        if config["remember_state"]:
            config["panel_state"] = self._build_panel_state()
        else:
            config.pop("panel_state", None)
        self._write_panel_config(config)

    def parse_subjects(self) -> List[Dict]:
        subjects = []
        for i in range(self.table.rowCount()):
            row = [
                self.table.item(i, j).text().strip()
                for j in range(6)
                if self.table.item(i, j)
            ]
            if len(row) < 6:
                raise ValueError(f"第 {i + 1} 行数据不完整。")
            subjects.append(
                {
                    "name": row[0],
                    "cur": float(row[1]),
                    "M": float(row[2]),
                    "S0": float(row[3]),
                    "eta": float(row[4]),
                    "theta": float(row[5]),
                }
            )
        return subjects

    def calculate(self, show_input_error: bool = True) -> None:
        try:
            subjects = self.parse_subjects()
            err = StudyTimeModel.validate_subjects(subjects)
            if err:
                raise ValueError(err)
        except Exception as exc:
            if show_input_error:
                QMessageBox.warning(self, "输入错误", str(exc))
            else:
                self.warning_label.setText(f"结果状态：输入检查未通过（{exc}）")
                self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
            return

        T = float(self.total_time_spin.value())
        tmins = {
            s["name"]: StudyTimeModel.t_min(
                s["cur"], s["eta"], s["theta"], s["M"], s["S0"]
            )
            for s in subjects
        }
        Tmin = sum(tmins.values())
        deltaT = T - Tmin

        alloc = StudyTimeModel.calc_global_opt(subjects, T)

        self.render_result_table(subjects, tmins, alloc, deltaT)

        if Tmin > T:
            self.warning_label.setText(
                "⚠ 结果状态：保底总时长已超过总时长，当前配置不可行。建议上调部分学科长期上限 M 或基础分 S0。"
            )
            self.warning_label.setStyleSheet("color: #b00020; font-weight: bold;")
        else:
            self.warning_label.setText(
                f"✓ 结果状态：配置可行（保底总时长 {Tmin:.1f}h，空余突破时长 {deltaT:.1f}h）。"
            )
            self.warning_label.setStyleSheet("color: #2e7d32; font-weight: bold;")

    def render_result_table(
        self, subjects: List[Dict], tmins: Dict, alloc: Dict, deltaT: float
    ) -> None:
        self.result_table.blockSignals(True)
        totals = [0.0] * 5
        single_break_gains = []
        for i, s in enumerate(subjects):
            name = s["name"]
            t_keep = tmins[name]
            t_all_in = t_keep + max(0.0, deltaT)
            t_opt = alloc[name]
            single_all_in_score = StudyTimeModel.s_star(
                t_all_in, s["eta"], s["theta"], s["M"], s["S0"]
            )
            single_break_gain = single_all_in_score - s["cur"]
            single_break_gains.append(single_break_gain)
            vals = [
                name,
                f"{t_keep:.1f}",
                f"{t_opt:.1f}",
                f"{single_break_gain:.1f}",
                f"{StudyTimeModel.s_star(t_keep, s['eta'], s['theta'], s['M'], s['S0']):.1f}",
                f"{StudyTimeModel.s_star(t_opt, s['eta'], s['theta'], s['M'], s['S0']):.1f}",
            ]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(v)
                self.result_table.setItem(i, j, item)
                if j > 0:
                    totals[j - 1] += float(v.replace("  ", " "))

        if single_break_gains:
            max_gain = max(single_break_gains)
            for i, gain in enumerate(single_break_gains):
                if abs(gain - max_gain) <= 1e-9:
                    gain_item = self.result_table.item(i, 3)
                    if gain_item:
                        gain_item.setForeground(QBrush(QColor("#b00020")))
                        gain_item.setBackground(QBrush(QColor("#ffe5e5")))

        totals_row = ["总计"] + [f"{x:.1f}" for x in totals]
        for j, v in enumerate(totals_row):
            total_item = QTableWidgetItem(v)
            self.result_table.setItem(len(subjects), j, total_item)

        total_tmin_item = self.result_table.item(len(subjects), 1)
        if total_tmin_item:
            feasible = totals[0] <= float(self.total_time_spin.value())
            if feasible:
                total_tmin_item.setForeground(QBrush(QColor("#2e7d32")))
                total_tmin_item.setBackground(QBrush(QColor("#e9f7ef")))
            else:
                total_tmin_item.setForeground(QBrush(QColor("#b00020")))
                total_tmin_item.setBackground(QBrush(QColor("#ffe5e5")))

        total_global_item = self.result_table.item(len(subjects), 5)
        if total_global_item:
            total_global_item.setForeground(QBrush(QColor("#b00020")))
            total_global_item.setBackground(QBrush(QColor("#ffe5e5")))

        self.result_table.blockSignals(False)
        self._auto_adjust_table_columns(self.result_table)
        self._adjust_table_height(self.result_table)
        self._finalize_window_size()

    def _adjust_table_height(self, table: QTableWidget) -> None:
        table.resizeRowsToContents()
        height = table.horizontalHeader().height()
        for i in range(table.rowCount()):
            height += table.rowHeight(i)
        height += 25
        table.setMaximumHeight(height)

    def _auto_adjust_table_columns(self, table: QTableWidget) -> None:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.resizeColumnsToContents()
        auto_widths = [table.columnWidth(i) for i in range(table.columnCount())]
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        for i, width in enumerate(auto_widths):
            table.setColumnWidth(i, width)

    def _table_required_size(self, table: QTableWidget) -> tuple[int, int]:
        width = table.verticalHeader().width() + table.frameWidth() * 2 + 2
        for col in range(table.columnCount()):
            width += table.columnWidth(col)

        height = table.horizontalHeader().height() + table.frameWidth() * 2 + 2
        for row in range(table.rowCount()):
            height += table.rowHeight(row)

        return width, height

    def _widget_required_size(self, widget: QWidget) -> tuple[int, int]:
        hint = widget.sizeHint()
        min_hint = widget.minimumSizeHint()
        return max(hint.width(), min_hint.width()), max(
            hint.height(), min_hint.height()
        )

    def _finalize_window_size(self) -> None:
        left_w, left_h = self._widget_required_size(self.ctrl_panel)

        status_w, status_h = self._widget_required_size(self.status_panel)
        result_w_panel, result_h_panel = self._widget_required_size(self.result_panel)

        table_w, table_h = self._table_required_size(self.table)
        result_w, result_h = self._table_required_size(self.result_table)

        status_w = max(status_w, table_w + 32)
        status_h = max(status_h, table_h + 32)
        result_w_panel = max(result_w_panel, result_w + 32)
        result_h_panel = max(result_h_panel, result_h + 32)

        left_col_min = left_w
        right_col_min = max(status_w, result_w_panel)

        row0_h = status_h
        row1_h = result_h_panel

        self.root_layout.setColumnMinimumWidth(0, left_col_min)
        self.root_layout.setColumnMinimumWidth(1, right_col_min)
        self.root_layout.setRowMinimumHeight(0, row0_h)
        self.root_layout.setRowMinimumHeight(1, row1_h)

        margins = self.root_layout.contentsMargins()
        min_width = (
            left_col_min
            + right_col_min
            + self.root_layout.horizontalSpacing()
            + margins.left()
            + margins.right()
        )
        min_height = (
            row0_h
            + row1_h
            + self.root_layout.verticalSpacing()
            + margins.top()
            + margins.bottom()
        )
        min_height = max(min_height, left_h + margins.top() + margins.bottom())

        self.setMinimumSize(min_width, min_height)
        self.resize(min_width + 20, min_height + 20)

    def closeEvent(self, event) -> None:
        self._save_panel_state()
        super().closeEvent(event)

    def show_explanation(self) -> None:
        QMessageBox.information(
            self,
            "程序说明",
            "情景说明\n- 学生每周有固定自主学习时间 T，需要在当前选定科目之间分配。\n"
            "- 学习会带来进步，但长期不用会衰退，且不同学科参数不同。\n\n"
            "模型建立\n- 稳态分数模型：S*(t) = (eta*t*M + theta*S0) / (eta*t + theta)。\n"
            "- 保底时间：t_min = theta*(S_cur - S0) / (eta*(M - S_cur))，用于守住当前水平。\n"
            "- 全局最优：通过二分法求解拉格朗日乘子，严格满足 KKT 条件分配时间。\n\n"
            "交互优化\n- 自动计算已添加 500ms 防抖，输入中途不会卡顿。\n- 布局支持窗口拖拽自适应，表格高度由 Qt 自动管理。",
        )
