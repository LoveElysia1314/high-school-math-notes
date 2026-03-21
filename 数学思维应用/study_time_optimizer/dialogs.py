from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .constants import GROUP_A, GROUP_B
from .config_manager import ConfigManager


class SubjectSelectionDialog(QDialog):
    def __init__(self, selected: List[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选科")
        self.resize(420, 300)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请选择：物理/历史 1 科 + 生物/化学/政治/地理 2 科。"))

        self.checks: List[QCheckBox] = []
        for group_name, group_list in [
            ("组 1：物理 / 历史", GROUP_A),
            ("组 2：生物 / 化学 / 政治 / 地理", GROUP_B),
        ]:
            gb = QGroupBox(group_name)
            gb_layout = QVBoxLayout(gb)
            for name in group_list:
                cb = QCheckBox(name)
                cb.setChecked(name in selected)
                cb.stateChanged.connect(self.update_state)
                self.checks.append(cb)
                gb_layout.addWidget(cb)
            layout.addWidget(gb)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.update_state()

    def selected_subjects(self) -> List[str]:
        return [cb.text() for cb in self.checks if cb.isChecked()]

    def update_state(self) -> None:
        selected = self.selected_subjects()
        a_count = sum(1 for s in selected if s in GROUP_A)
        b_count = sum(1 for s in selected if s in GROUP_B)
        ok_btn = self.buttons.button(QDialogButtonBox.Ok)
        valid = (a_count == 1) and (b_count == 2)
        ok_btn.setEnabled(valid)
        if valid:
            self.status_label.setText("选科规则满足：物理/历史 1 科，生化政地 2 科。")
            self.status_label.setStyleSheet("color: #2e7d32;")
        else:
            self.status_label.setText(
                f"当前：物理/历史已选 {a_count} 科，生化政地已选 {b_count} 科；需满足 1+2。"
            )
            self.status_label.setStyleSheet("color: #b00020;")


class PresetManagementDialog(QDialog):
    def __init__(
        self,
        preset_manager: ConfigManager,
        get_config_callback=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("预设管理")
        self.resize(500, 400)
        self.preset_mgr = preset_manager
        self.get_config_callback = get_config_callback

        layout = QVBoxLayout(self)
        self.preset_list = QListWidget()
        self.preset_list.itemSelectionChanged.connect(self.on_preset_selected)
        layout.addWidget(QLabel("已有预设："))
        layout.addWidget(self.preset_list)

        self.mark_label = QLabel()
        self.mark_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(self.mark_label)

        btn_layout = QGridLayout()
        btn_layout.setHorizontalSpacing(8)
        btn_layout.setVerticalSpacing(6)
        actions = [
            ("保存为预设", self.save_as_preset),
            ("覆盖预设", self.override_preset),
            ("删除预设", self.delete_preset),
            ("复位到初始", self.reset_to_builtin),
            ("重命名", self.rename_preset),
            ("关闭", self.accept),
        ]
        for i, (text, slot) in enumerate(actions):
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn.setFixedWidth(100)
            row, col = divmod(i, 3)
            btn_layout.addWidget(btn, row, col)
        layout.addLayout(btn_layout)

        self.refresh_list()
        self.on_preset_selected()

    def refresh_list(self) -> None:
        self.preset_list.clear()
        for name in self.preset_mgr.get_preset_names():
            is_builtin = self.preset_mgr.is_builtin(name)
            display_name = f"{name} [内置]" if is_builtin else name
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, name)
            self.preset_list.addItem(item)

    def on_preset_selected(self) -> None:
        items = self.preset_list.selectedItems()
        if not items:
            for btn in self.findChildren(QPushButton):
                if btn.text() in ["保存为预设", "复位到初始", "关闭"]:
                    btn.setEnabled(True)
                else:
                    btn.setEnabled(False)
            self.mark_label.setText("")
            return

        name = items[0].data(Qt.UserRole)
        is_builtin = self.preset_mgr.is_builtin(name)
        for btn in self.findChildren(QPushButton):
            if btn.text() == "保存为预设":
                btn.setEnabled(True)
            elif btn.text() == "复位到初始":
                btn.setEnabled(True)
            elif btn.text() == "关闭":
                btn.setEnabled(True)
            elif btn.text() in ("删除预设", "重命名"):
                btn.setEnabled(not is_builtin)
            else:
                btn.setEnabled(True)

        if is_builtin:
            self.mark_label.setText("✓ 内置预设：可覆盖，不可删除/重命名。")
            self.mark_label.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            self.mark_label.setText("✎ 自定义预设：可覆盖、重命名、删除。")
            self.mark_label.setStyleSheet("color: #1976d2; font-size: 11px;")

    def save_as_preset(self) -> None:
        name, ok = QInputDialog.getText(self, "保存为新预设", "预设名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.preset_mgr.get_preset_names():
            QMessageBox.warning(self, "保存失败", f"预设 '{name}' 已存在。")
            return
        config = (
            self.get_config_callback()
            if self.get_config_callback
            else {"electives": [], "subjects": {}}
        )
        if self.preset_mgr.create_preset(name, config):
            QMessageBox.information(self, "保存成功", f"已保存为预设 '{name}'。")
            self.refresh_list()

    def override_preset(self) -> None:
        items = self.preset_list.selectedItems()
        if not items:
            return
        item = items[0]
        name = item.data(Qt.UserRole)
        if (
            QMessageBox.question(
                self, "确认覆盖", f"确定要用当前配置覆盖预设 '{name}' 吗？"
            )
            != QMessageBox.Yes
        ):
            return
        config = (
            self.get_config_callback()
            if self.get_config_callback
            else {"electives": [], "subjects": {}}
        )
        self.preset_mgr.override_preset(name, config)
        QMessageBox.information(self, "覆盖成功", f"预设 '{name}' 已更新。")
        self.refresh_list()

    def delete_preset(self) -> None:
        items = self.preset_list.selectedItems()
        if not items:
            return
        item = items[0]
        name = item.data(Qt.UserRole)
        if (
            QMessageBox.question(
                self, "确认删除", f"确定要删除预设 '{name}' 吗？此操作不可撤销。"
            )
            != QMessageBox.Yes
        ):
            return
        if self.preset_mgr.delete_preset(name):
            QMessageBox.information(self, "删除成功", f"预设 '{name}' 已删除。")
            self.refresh_list()

    def rename_preset(self) -> None:
        items = self.preset_list.selectedItems()
        if not items:
            return
        item = items[0]
        old_name = item.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "重命名预设", "新名称：", text=old_name
        )
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        if new_name in self.preset_mgr.get_preset_names():
            QMessageBox.warning(self, "重命名失败", f"预设 '{new_name}' 已存在。")
            return
        config = self.preset_mgr.get_preset(old_name)
        self.preset_mgr.delete_preset(old_name)
        self.preset_mgr.create_preset(new_name, config)
        QMessageBox.information(self, "重命名成功", f"预设已重命名为 '{new_name}'。")
        self.refresh_list()

    def reset_to_builtin(self) -> None:
        if (
            QMessageBox.question(
                self,
                "确认复位",
                "确定要将所有预设复位为初始状态吗？自定义预设将全部删除。",
            )
            != QMessageBox.Yes
        ):
            return
        self.preset_mgr.reset_to_builtin()
        QMessageBox.information(self, "复位成功", "已复位到初始状态。")
        self.refresh_list()
