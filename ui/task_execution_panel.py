#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务执行控制面板
提供任务执行的控制界面（开始、停止、执行模式选择等）
"""

import logging
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel,
                               QComboBox, QProgressBar, QVBoxLayout, QFrame, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon

from .workflow_task_manager import WorkflowTaskManager

logger = logging.getLogger(__name__)

class TaskExecutionPanel(QWidget):
    """
    任务执行控制面板

    功能：
    1. 开始/停止当前任务
    2. 开始/停止所有任务
    3. 选择执行模式（同步/异步）
    4. 显示执行进度
    """

    # 信号定义
    start_current_requested = Signal()
    stop_current_requested = Signal()
    start_all_requested = Signal()
    stop_all_requested = Signal()
    execution_mode_changed = Signal(str)  # 'sync' or 'async'

    def __init__(self, task_manager: WorkflowTaskManager, parent=None):
        """
        初始化执行控制面板

        Args:
            task_manager: 任务管理器
            parent: 父控件
        """
        super().__init__(parent)

        self.task_manager = task_manager
        self._initialization_in_progress = False  # 🔧 添加：标记初始化状态
        self._init_ui()
        self._connect_signals()

        # 从task_manager读取当前执行模式并设置UI
        current_mode = self.task_manager.execution_mode
        if current_mode == 'async':
            self.mode_combo.setCurrentIndex(1)  # 异步执行
        else:
            self.mode_combo.setCurrentIndex(0)  # 同步执行

    def _init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 3, 5, 3)
        main_layout.setSpacing(5)

        # 设置面板背景为轻微灰色，与主窗口风格一致
        self.setStyleSheet("""
            TaskExecutionPanel {
                background-color: #f5f5f5;
                border-top: 1px solid #d0d0d0;
            }
        """)

        # === 当前任务控制 ===
        self.start_current_button = QPushButton("开始当前")
        self.start_current_button.setMinimumHeight(26)
        self.start_current_button.setMinimumWidth(80)

        self.stop_current_button = QPushButton("停止当前")
        self.stop_current_button.setMinimumHeight(26)
        self.stop_current_button.setMinimumWidth(80)
        self.stop_current_button.setEnabled(False)

        main_layout.addWidget(self.start_current_button)
        main_layout.addWidget(self.stop_current_button)

        # 空白间隔（不用分隔线）
        main_layout.addSpacing(10)

        # === 全部任务控制 ===
        self.start_all_button = QPushButton("开始全部")
        self.start_all_button.setMinimumHeight(26)
        self.start_all_button.setMinimumWidth(80)

        self.stop_all_button = QPushButton("停止全部")
        self.stop_all_button.setMinimumHeight(26)
        self.stop_all_button.setMinimumWidth(80)
        self.stop_all_button.setEnabled(False)

        main_layout.addWidget(self.start_all_button)
        main_layout.addWidget(self.stop_all_button)

        # 空白间隔（不用分隔线）
        main_layout.addSpacing(10)

        # === 执行模式选择 ===
        mode_label = QLabel("模式:")
        mode_label.setStyleSheet("color: #666666; font-size: 12px;")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("同步执行", "sync")
        self.mode_combo.addItem("异步执行", "async")
        self.mode_combo.setMinimumHeight(24)
        self.mode_combo.setMinimumWidth(100)

        main_layout.addWidget(mode_label)
        main_layout.addWidget(self.mode_combo)

        # 空白间隔
        main_layout.addSpacing(10)

        # === 跳转规则按钮 ===
        self.jump_rules_button = QPushButton("跳转规则")
        self.jump_rules_button.setMinimumHeight(26)
        self.jump_rules_button.setMinimumWidth(80)
        self.jump_rules_button.setToolTip("配置任务间的跳转规则")
        main_layout.addWidget(self.jump_rules_button)

        # 弹性空间
        main_layout.addStretch()

        # === 状态显示 ===
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666666; font-size: 12px;")

        self.task_count_label = QLabel("任务: 0")
        self.task_count_label.setStyleSheet("color: #666666; font-size: 12px;")

        main_layout.addWidget(self.status_label)
        main_layout.addSpacing(8)
        main_layout.addWidget(self.task_count_label)

    def _connect_signals(self):
        """连接信号"""
        # 按钮信号
        self.start_current_button.clicked.connect(self.start_current_requested.emit)
        self.stop_current_button.clicked.connect(self.stop_current_requested.emit)
        self.start_all_button.clicked.connect(self.start_all_requested.emit)
        self.stop_all_button.clicked.connect(self.stop_all_requested.emit)

        # 执行模式变化
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # 跳转规则按钮
        self.jump_rules_button.clicked.connect(self._on_jump_rules_clicked)

        # 任务管理器信号
        self.task_manager.task_added.connect(self._update_ui_state)
        self.task_manager.task_removed.connect(self._update_ui_state)
        self.task_manager.task_status_changed.connect(self._update_ui_state)
        self.task_manager.all_tasks_completed.connect(self._on_all_tasks_completed)

    def _on_mode_changed(self, index):
        """执行模式变化"""
        mode = self.mode_combo.currentData()
        self.task_manager.set_execution_mode(mode)

        # 保存到配置文件
        self.task_manager.config['task_execution_mode'] = mode

        self.execution_mode_changed.emit(mode)

        logger.info(f"执行模式已切换为: {self.mode_combo.currentText()}")

    def _on_jump_rules_clicked(self):
        """打开跳转规则配置对话框"""
        from .jump_rules_dialog import JumpRulesDialog

        dialog = JumpRulesDialog(self.task_manager, self)
        dialog.exec()

    def _update_ui_state(self, *args):
        """更新UI状态"""
        # 获取任务统计
        total_count = self.task_manager.get_task_count()
        running_count = self.task_manager.get_running_count()
        executable_count = len(self.task_manager.get_executable_tasks())

        # 更新任务计数
        self.task_count_label.setText(f"任务: {total_count} | 运行中: {running_count}")

        # 🔧 修改：初始化期间禁用所有开始按钮
        if self._initialization_in_progress:
            self.start_current_button.setEnabled(False)
            self.start_all_button.setEnabled(False)
            self.stop_current_button.setEnabled(False)
            self.stop_all_button.setEnabled(False)
            return

        # 更新按钮状态
        has_tasks = total_count > 0
        has_executable = executable_count > 0
        is_running = running_count > 0

        self.start_current_button.setEnabled(has_tasks and not is_running)
        self.stop_current_button.setEnabled(is_running)
        self.start_all_button.setEnabled(has_executable and not is_running)
        self.stop_all_button.setEnabled(is_running)

        # 更新状态文本
        if is_running:
            if self.task_manager.execution_mode == 'sync':
                self.status_label.setText("执行中(同步)")
            else:
                self.status_label.setText("执行中(异步)")
            self.status_label.setStyleSheet("color: #2196F3; font-size: 12px; font-weight: bold;")
        else:
            self.status_label.setText("就绪")
            self.status_label.setStyleSheet("color: #666666; font-size: 12px;")

    def _on_all_tasks_completed(self, success: bool):
        """所有任务执行完成"""
        if success:
            self.status_label.setText("全部完成")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        else:
            self.status_label.setText("执行失败")
            self.status_label.setStyleSheet("color: #f44336; font-size: 12px; font-weight: bold;")

        # 3秒后恢复状态
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._update_ui_state())

    def set_status_message(self, message: str, color: str = "#666666"):
        """
        设置状态消息

        Args:
            message: 消息文本
            color: 文本颜色
        """
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    def set_initialization_in_progress(self, in_progress: bool):
        """
        设置初始化进行中状态

        Args:
            in_progress: 是否正在初始化
        """
        self._initialization_in_progress = in_progress
        if in_progress:
            self.set_status_message("初始化中...", "#FF9800")
        self._update_ui_state()
