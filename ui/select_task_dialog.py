# -*- coding: utf-8 -*-
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt

class SelectTaskDialog(QDialog):
    """A custom dialog for selecting a task type with modern styling."""
    def __init__(self, task_types: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择任务类型")
        self.setMinimumWidth(350)

        self._selected_task_type: Optional[str] = None

        # --- Layouts --- 
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # --- Widgets --- 
        self.info_label = QLabel("请选择要添加的任务类型:")
        self.info_label.setObjectName("infoLabel")

        self.combo_box = QComboBox()
        self.combo_box.setObjectName("taskComboBox")
        self.combo_box.addItems(task_types)
        self.combo_box.setMinimumHeight(30)

        self.ok_button = QPushButton("确定") # Use Chinese
        self.ok_button.setObjectName("okButton")
        self.ok_button.setDefault(True)
        self.ok_button.setMinimumHeight(30)

        self.cancel_button = QPushButton("取消") # Use Chinese
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setMinimumHeight(30)

        # --- Assemble Layout --- 
        self.main_layout.addWidget(self.info_label)
        self.main_layout.addWidget(self.combo_box)
        self.main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch(1)
        self.main_layout.addLayout(button_layout)

        # --- Styling --- 
        # 样式现在由全局主题系统管理

        # --- Connections --- 
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def selected_task_type(self) -> Optional[str]:
        """Returns the currently selected task type in the combo box."""
        return self.combo_box.currentText()