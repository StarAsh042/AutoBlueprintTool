# -*- coding: utf-8 -*-
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QSpacerItem, QSizePolicy,
    QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt

class SelectTaskDialog(QDialog):
    """A custom dialog for selecting a task type with modern styling."""
    def __init__(self, task_types: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择任务类型")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._selected_task_type: Optional[str] = None

        # --- Layouts --- 
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # --- Info Label --- 
        self.info_label = QLabel("请选择要添加的任务类型:")
        self.info_label.setObjectName("infoLabel")
        # 移除内联样式，使用全局 QSS
        self.main_layout.addWidget(self.info_label)

        # --- Scroll Area for Buttons --- 
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setObjectName("taskScrollArea")
        
        # Container widget for the grid layout
        self.container_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.container_widget.setLayout(self.grid_layout)
        
        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area, 1)  # Stretch factor 1

        # --- Create Buttons in Grid --- 
        self.task_buttons = []
        columns = 2  # 2 columns
        
        for i, task_type in enumerate(task_types):
            row = i // columns
            col = i % columns
            
            button = QPushButton(task_type)
            button.setObjectName(f"taskButton_{i}")
            button.setMinimumHeight(50)
            # 使用全局 QSS 样式，不再内联设置
            button.clicked.connect(lambda checked, t=task_type: self.select_task(t))
            
            self.grid_layout.addWidget(button, row, col)
            self.task_buttons.append(button)
        
        # Add stretch to fill remaining space
        if len(task_types) % columns != 0:
            # Add empty widgets to fill the last row
            for _ in range(columns - (len(task_types) % columns)):
                self.grid_layout.addWidget(QWidget(), len(task_types) // columns, len(task_types) % columns)

        # --- Buttons Layout --- 
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.ok_button = QPushButton("确定")
        self.ok_button.setObjectName("okButton")
        self.ok_button.setDefault(True)
        self.ok_button.setMinimumHeight(35)
        self.ok_button.setMinimumWidth(100)
        # 使用全局 QSS 样式

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setMinimumWidth(100)
        # 使用全局 QSS 样式

        button_layout.addStretch(1)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch(1)
        self.main_layout.addLayout(button_layout)

        # --- Connections --- 
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def select_task(self, task_type: str):
        """Handle task selection from button click."""
        self._selected_task_type = task_type
        # Auto-accept when a task is selected
        self.accept()

    def selected_task_type(self) -> Optional[str]:
        """Returns the currently selected task type."""
        return self._selected_task_type