import sys
import json # Import json for saving/loading
import os   # Import os for path manipulation (basename)
import copy # <<< ADDED: Import copy module
import time # Import time for timestamp recording
# <<< ADDED Imports for Backup >>>
import shutil 
import datetime
# -----------------------------
from typing import Dict, Any, Optional, List, Tuple # Import Dict, Any, and Optional for type hinting
# Import QIcon and QStyle for standard icons
# Import QInputDialog for task type selection
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                               QToolBar, QStyle, QInputDialog, QFileDialog, QMessageBox, QLineEdit,
                               QDialog, QFormLayout, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QDialogButtonBox,
                               QHBoxLayout, QSizePolicy, QGroupBox, QToolButton, QMenu, QListWidget,
                               QListWidgetItem, QCheckBox, QRadioButton, QButtonGroup, QTextEdit, QPlainTextEdit) # Added QDoubleSpinBox, QTextEdit, QPlainTextEdit
import ctypes
from ctypes import wintypes
from PySide6.QtGui import QIcon, QAction, QPainterPath, QPainter, QColor, QBrush, QPen, QCloseEvent # Add QPainter, QColor, QBrush, QPen, QCloseEvent
from PySide6.QtCore import Qt, QSize, QPointF, QEvent, QThread, Signal, QObject, QTimer # Import QEvent, QThread, Signal, QObject, QTimer

# Imports needed for pywin32 functionalities (window listing, binding, resizing)
import time
# --- ADDED: Import re for message checking ---
import re
try:
    import win32api
    import win32con
    import win32gui
    PYWIN32_AVAILABLE = True
except ImportError:
    win32api = None
    win32con = None
    win32gui = None
    PYWIN32_AVAILABLE = False
    # Use logging configured in main.py if available, otherwise print
    log_func = logging.warning if logging.getLogger().hasHandlers() else print
    log_func("警告: pywin32 库未安装。部分窗口相关功能将不可用。请运行 'pip install pywin32'")

# Remove separate flags, use PYWIN32_AVAILABLE instead
# WIN32_AVAILABLE_FOR_BIND = PYWIN32_AVAILABLE
# WIN32_AVAILABLE_FOR_LIST = PYWIN32_AVAILABLE

from .workflow_view import WorkflowView, ConnectionLine # <<< Added ConnectionLine
from .task_card import TaskCard # <<< ADDED TaskCard import
from .custom_title_bar import CustomTitleBar # Import the new title bar
from .parameter_panel import ParameterPanel # <<< ADDED: Import parameter panel

# Import the executor
from task_workflow.executor import WorkflowExecutor

# 导入通用窗口管理器
from utils.universal_window_manager import get_universal_window_manager
import pyautogui # Import pyautogui for window selection
import logging # <-- 确保 logging 已导入
logger = logging.getLogger(__name__) # <<< ADDED: Get logger instance

# <<< ADDED: Import os for path checks >>>
import os 
# --------------------------------------

# Imports needed for window listing
import time
try:
    import win32gui
    import win32con # Might not be needed for listing, but keep for consistency
    import win32api # Might not be needed for listing, but keep for consistency
    WIN32_AVAILABLE_FOR_LIST = True
except ImportError:
    WIN32_AVAILABLE_FOR_LIST = False
    # Use logging configured in main.py if available, otherwise print
    log_func = logging.warning if logging.getLogger().hasHandlers() else print
    log_func("警告: pywin32 未安装，无法使用窗口列表选择功能。")

# --- 执行模式标准化函数 ---
def normalize_execution_mode(mode: str) -> str:
    """
    将新的7种执行模式标准化为基础的 'foreground' 或 'background' 或 'emulator'
    用于兼容现有的判断逻辑

    Args:
        mode: 执行模式标识

    Returns:
        'foreground', 'background', 或 'emulator'
    """
    if mode.startswith('foreground'):
        return 'foreground'
    elif mode.startswith('background'):
        return 'background'
    elif mode.startswith('emulator_'):
        return 'emulator'
    else:
        # 兼容旧的模式标识
        return mode

# --- Global Settings Dialog ---
class GlobalSettingsDialog(QDialog):
    """A dialog for editing global application settings with modern styling."""
    MODE_DISPLAY_MAP = {
        'foreground_driver': "前台模式一",
        'foreground_pyautogui': "前台模式二",
        'background_sendmessage': "后台模式一",
        'background_postmessage': "后台模式二",
        'emulator_mumu': "MuMu模拟器",
        'emulator_ldplayer': "雷电模拟器"
    }
    MODE_INTERNAL_MAP = {v: k for k, v in MODE_DISPLAY_MAP.items()}

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("全局设置")
        # 不设置固定大小，让Qt自动调整
        self.setMinimumWidth(500)
        self.setMaximumWidth(700)
        self.current_config = current_config
        self.bound_windows = current_config.get('bound_windows', [])  # 绑定的窗口列表
        self.window_binding_mode = current_config.get('window_binding_mode', 'single')  # 'single' 或 'multiple'

        # 🔧 调试：记录初始化时的绑定窗口信息
        logger.info(f"GlobalSettingsDialog初始化: 加载了 {len(self.bound_windows)} 个绑定窗口")
        for i, window in enumerate(self.bound_windows):
            title = window.get('title', 'Unknown')
            hwnd = window.get('hwnd', 'N/A')
            logger.info(f"  {i+1}. {title} (HWND: {hwnd})")

        # 自动清理已禁用，因为无法准确检测雷电模拟器窗口关闭状态

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)  # 进一步减少间距
        main_layout.setContentsMargins(20, 15, 20, 15)  # 合理的边距

        # 删除模式选择，统一使用窗口绑定界面

        # --- Window Settings Group ---
        self.window_settings_group = QGroupBox("窗口设置")
        window_layout = QVBoxLayout(self.window_settings_group)
        window_layout.setSpacing(8)
        window_layout.setContentsMargins(15, 10, 15, 10)

        # 添加说明文字
        info_label = QLabel("绑定单个窗口可选择执行模式，绑定多个窗口将自动使用后台模式")
        window_layout.addWidget(info_label)
        window_layout.addSpacing(5)

        # 窗口选择下拉框
        window_select_layout = QHBoxLayout()
        window_select_label = QLabel("选择窗口:")
        window_select_label.setFixedWidth(80)  # 设置固定宽度确保对齐
        self.window_select_combo = QComboBox()
        # 设置统一的宽度
        self.window_select_combo.setMinimumWidth(200)
        self.window_select_combo.setMaximumWidth(500)  # 增加最大宽度，避免长窗口标题被截断
        self.window_select_combo.setToolTip("选择要绑定的窗口")

        # 🔧 一键绑定同类型窗口按钮
        self.batch_add_button = QPushButton("一键绑定")
        self.batch_add_button.setFixedWidth(100)
        self.batch_add_button.setToolTip("一键绑定所有同类型窗口（MuMu/雷电/PC窗口）")

        window_select_layout.addWidget(window_select_label)
        window_select_layout.addWidget(self.window_select_combo, 1)
        window_select_layout.addWidget(self.batch_add_button)
        window_layout.addLayout(window_select_layout)

        # 已绑定窗口下拉框
        bound_windows_layout = QHBoxLayout()
        bound_label = QLabel("已绑定窗口:")
        bound_label.setFixedWidth(80)  # 设置与上面标签相同的固定宽度
        self.bound_windows_combo = QComboBox()
        # 设置与选择窗口下拉框一致的宽度
        self.bound_windows_combo.setMinimumWidth(200)
        self.bound_windows_combo.setMaximumWidth(500)
        self.bound_windows_combo.setToolTip("已绑定的窗口列表")

        self.remove_window_button = QPushButton("移除选中")
        self.remove_window_button.setFixedWidth(100)  # 统一按钮宽度

        bound_windows_layout.addWidget(bound_label)
        bound_windows_layout.addWidget(self.bound_windows_combo, 1)
        bound_windows_layout.addWidget(self.remove_window_button)
        window_layout.addLayout(bound_windows_layout)

        main_layout.addWidget(self.window_settings_group)

        # --- Execution Mode Group ---
        self.exec_mode_group = QGroupBox("执行模式设置")
        exec_mode_layout = QVBoxLayout(self.exec_mode_group)
        exec_mode_layout.setSpacing(8)
        exec_mode_layout.setContentsMargins(15, 10, 15, 10)

        # 模式选择下拉框
        mode_select_layout = QHBoxLayout()
        mode_label = QLabel("执行模式:")
        mode_label.setFixedWidth(80)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(list(self.MODE_DISPLAY_MAP.values()))
        internal_mode = current_config.get('execution_mode', 'foreground_driver')
        display_mode = self.MODE_DISPLAY_MAP.get(internal_mode, "前台模式一")
        self.mode_combo.setCurrentText(display_mode)
        mode_select_layout.addWidget(mode_label)
        mode_select_layout.addWidget(self.mode_combo)
        exec_mode_layout.addLayout(mode_select_layout)

        # 多窗口启动延迟固定为500ms（不显示设置）
        self.multi_window_delay = 500

        main_layout.addWidget(self.exec_mode_group)

        # --- Hotkey Settings Group ---
        self.hotkey_group = QGroupBox("快捷键设置")
        hotkey_main_layout = QVBoxLayout(self.hotkey_group)
        hotkey_main_layout.setSpacing(5)
        hotkey_main_layout.setContentsMargins(15, 10, 15, 10)

        # 创建水平布局放置三个快捷键
        hotkey_row_layout = QHBoxLayout()
        hotkey_row_layout.setSpacing(20)

        # 启动任务快捷键
        start_task_container = QVBoxLayout()
        start_task_label = QLabel("启动任务")
        start_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_task_hotkey = QLineEdit()
        self.start_task_hotkey.setText(current_config.get('start_task_hotkey', 'F9'))
        self.start_task_hotkey.setPlaceholderText("F9")
        self.start_task_hotkey.setToolTip("设置启动任务的快捷键")
        self.start_task_hotkey.setFixedWidth(60)
        self.start_task_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        start_task_container.addWidget(start_task_label)
        start_task_container.addWidget(self.start_task_hotkey)

        # 停止任务快捷键
        stop_task_container = QVBoxLayout()
        stop_task_label = QLabel("停止任务")
        stop_task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stop_task_hotkey = QLineEdit()
        self.stop_task_hotkey.setText(current_config.get('stop_task_hotkey', 'F10'))
        self.stop_task_hotkey.setPlaceholderText("F10")
        self.stop_task_hotkey.setToolTip("设置停止任务的快捷键")
        self.stop_task_hotkey.setFixedWidth(60)
        self.stop_task_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stop_task_container.addWidget(stop_task_label)
        stop_task_container.addWidget(self.stop_task_hotkey)

        # 录制控制快捷键
        record_container = QVBoxLayout()
        record_label = QLabel("录制控制")
        record_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.record_hotkey = QLineEdit()
        self.record_hotkey.setText(current_config.get('record_hotkey', 'F12'))
        self.record_hotkey.setPlaceholderText("F12")
        self.record_hotkey.setToolTip("按一次启动录制，再按一次停止录制")
        self.record_hotkey.setFixedWidth(60)
        self.record_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        record_container.addWidget(record_label)
        record_container.addWidget(self.record_hotkey)

        # 添加到水平布局
        hotkey_row_layout.addLayout(start_task_container)
        hotkey_row_layout.addLayout(stop_task_container)
        hotkey_row_layout.addLayout(record_container)
        hotkey_row_layout.addStretch()  # 添加弹性空间，让控件靠左对齐

        hotkey_main_layout.addLayout(hotkey_row_layout)
        main_layout.addWidget(self.hotkey_group)

        # --- Theme Settings Group ---
        self.theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(self.theme_group)
        theme_layout.setSpacing(8)
        theme_layout.setContentsMargins(15, 10, 15, 10)

        # 主题选择下拉框
        theme_select_layout = QHBoxLayout()
        theme_label = QLabel("应用主题:")
        theme_label.setFixedWidth(80)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["明亮模式", "暗色模式"])

        # 从配置中加载当前主题
        theme_config = current_config.get('theme', 'dark')
        if theme_config == 'light':
            self.theme_combo.setCurrentText("明亮模式")
        else:
            self.theme_combo.setCurrentText("暗色模式")

        theme_select_layout.addWidget(theme_label)
        theme_select_layout.addWidget(self.theme_combo)
        theme_layout.addLayout(theme_select_layout)

        # 添加说明
        theme_info_label = QLabel("主题设置会自动切换明暗模式")
        theme_layout.addWidget(theme_info_label)

        main_layout.addWidget(self.theme_group)

        # --- Custom Resolution Group ---
        resolution_group = QGroupBox("自定义分辨率 (0 = 禁用)")
        resolution_layout = QFormLayout(resolution_group)
        resolution_layout.setSpacing(8)
        resolution_layout.setContentsMargins(15, 10, 15, 10)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(0, 9999)
        # 🔧 修复：允许保存和显示0值（禁用状态）
        default_width = current_config.get('custom_width', 0)
        self.width_spinbox.setValue(default_width)

        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(0, 9999)
        # 🔧 修复：允许保存和显示0值（禁用状态）
        default_height = current_config.get('custom_height', 0)
        self.height_spinbox.setValue(default_height)
        resolution_layout.addRow("宽度:", self.width_spinbox)
        resolution_layout.addRow("高度:", self.height_spinbox)
        main_layout.addWidget(resolution_group)

        # --- Dialog Buttons ---
        button_box = QDialogButtonBox()
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        ok_button = button_box.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = button_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        button_layout.addWidget(button_box)
        main_layout.addLayout(button_layout)

        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        # 设置按钮对象名称（使用主题样式的 primaryButton 选择器）
        ok_button.setObjectName("primaryButton")
        cancel_button.setObjectName("")

        # --- Connect signals ---

        # 删除单窗口模式相关信号连接

        # 多个窗口模式信号
        self.batch_add_button.clicked.connect(self._batch_add_same_type_windows)  # 🔧 一键绑定
        self.remove_window_button.clicked.connect(self._remove_selected_window)

        # 初始化窗口选择下拉框
        self._refresh_window_select_combo()

        # 初始化界面状态
        self._load_bound_windows()
        # 在初始化时检查窗口状态
        self._check_and_cleanup_closed_windows()
        self._update_execution_mode_visibility()

        # --- Apply Theme-Aware Stylesheet ---
        # 注意：不再设置硬编码的白色样式表，而是使用全局主题样式表
        # 只有特定的按钮样式需要保留
        pass  # 全局样式表已经通过 app.setStyleSheet() 应用到整个应用程序

        # 初始化完成后自动调整大小
        self._adjust_dialog_size()

    def _update_execution_mode_visibility(self):
        """更新执行模式设置的可见性（现在始终显示，由用户手动选择）"""
        # 执行模式设置始终可见，不再根据窗口数量自动隐藏
        if hasattr(self, 'exec_mode_group'):
            self.exec_mode_group.setVisible(True)

        # 自动调整对话框大小
        self._adjust_dialog_size()

    def _adjust_dialog_size(self):
        """自动调整对话框大小以适应内容"""
        # 强制更新布局
        self.layout().activate()

        # 让Qt计算最佳大小
        self.adjustSize()

        # 确保最小宽度
        if self.width() < 500:
            self.resize(500, self.height())

        # 确保不会太高
        if self.height() > 600:
            self.resize(self.width(), 600)

    def _load_bound_windows(self):
        """加载已绑定的窗口列表，验证窗口是否真实存在"""
        logger.info(f"开始加载绑定窗口，配置中有 {len(self.bound_windows)} 个窗口")

        # 🔧 首先清理失效的窗口
        logger.info("加载绑定窗口前先清理失效窗口")
        self._cleanup_invalid_windows()
        logger.info(f"清理后剩余 {len(self.bound_windows)} 个窗口")

        # 验证并过滤存在的窗口
        valid_windows = []

        for i, window_info in enumerate(self.bound_windows):
            window_title = window_info.get('title', '')
            hwnd = window_info.get('hwnd', 0)

            logger.info(f"验证窗口 {i+1}: {window_title} (配置中的HWND: {hwnd})")

            if window_title:
                # 如果原来有句柄，先验证原句柄是否仍然有效
                if hwnd and hwnd != 0:
                    try:
                        import win32gui
                        # 🔧 修复：更灵活的窗口验证，不要求标题完全匹配
                        if (win32gui.IsWindow(hwnd) and
                            win32gui.IsWindowVisible(hwnd)):
                            # 窗口存在且可见即可，不要求标题完全匹配
                            # 因为保存的标题可能包含额外信息（如HWND）

                            # 检查是否已经有相同句柄的窗口
                            duplicate_found = False
                            for existing_window in valid_windows:
                                existing_hwnd = existing_window.get('hwnd', 0)
                                if existing_hwnd == hwnd:
                                    logger.warning(f"发现重复句柄 {hwnd}，跳过窗口: {window_title}")
                                    duplicate_found = True
                                    break

                            if not duplicate_found:
                                # 原句柄仍然有效且窗口可见，保留
                                valid_windows.append(window_info)
                                logger.info(f"原句柄仍然有效: {window_title} (HWND: {hwnd})")
                            else:
                                logger.warning(f"原句柄重复，已跳过: {window_title} (HWND: {hwnd})")
                            continue
                        else:
                            logger.warning(f"原句柄已失效或窗口不可见: {window_title} (HWND: {hwnd})")
                    except Exception as e:
                        logger.warning(f"验证窗口句柄时出错: {e}")

                # 原句柄无效或不存在，尝试重新查找
                # 临时清空bound_windows以避免智能查找时的冲突
                temp_bound_windows = self.bound_windows
                self.bound_windows = []

                current_hwnd = self._find_window_handle(window_title)

                # 恢复bound_windows
                self.bound_windows = temp_bound_windows

                logger.info(f"重新查找结果: {current_hwnd}")

                if current_hwnd:
                    # 检查是否已经有相同句柄的窗口
                    duplicate_found = False
                    for existing_window in valid_windows:
                        existing_hwnd = existing_window.get('hwnd', 0)
                        if existing_hwnd == current_hwnd:
                            logger.warning(f"发现重复句柄 {current_hwnd}，跳过窗口: {window_title}")
                            duplicate_found = True
                            break

                    if not duplicate_found:
                        # 窗口存在且无重复，更新句柄
                        window_info['hwnd'] = current_hwnd
                        valid_windows.append(window_info)
                        logger.info(f"重新查找到窗口: {window_title} (HWND: {current_hwnd})")
                    else:
                        logger.warning(f"窗口句柄重复，已跳过: {window_title} (HWND: {current_hwnd})")
                else:
                    logger.warning(f"配置中的窗口不存在，已跳过: {window_title}")
            else:
                logger.warning(f"窗口信息无效，已跳过: {window_info}")

        logger.info(f"验证完成，有效窗口数量: {len(valid_windows)}")

        # 更新绑定窗口列表为验证后的列表
        self.bound_windows = valid_windows

        # 刷新界面显示
        self._refresh_bound_windows_combo()

        # 为已绑定的窗口预创建OCR服务
        for window_info in self.bound_windows:
            if window_info.get('hwnd'):
                self._preregister_window_ocr_service(window_info)

        # 注册窗口到句柄管理器
        self._register_windows_to_handle_manager()

    def _refresh_window_select_combo(self):
        """刷新窗口选择下拉框 - 显示PC窗口和雷电模拟器窗口"""
        if not WIN32_AVAILABLE_FOR_LIST:
            self.window_select_combo.addItem("需要安装 pywin32")
            self.window_select_combo.setEnabled(False)
            return

        try:
            # 获取PC窗口和雷电模拟器窗口
            filtered_windows = self._get_pc_and_ldplayer_windows()

            self.window_select_combo.clear()
            self.window_select_combo.addItem("-- 选择窗口 --")

            if filtered_windows:
                # filtered_windows 现在是 (display_title, original_title) 的元组列表
                for display_title, original_title in filtered_windows:
                    self.window_select_combo.addItem(display_title)
                    # 将原始标题存储为item data
                    index = self.window_select_combo.count() - 1
                    self.window_select_combo.setItemData(index, original_title)

                    # 如果是分割线，设置为不可选择
                    if display_title.startswith("─"):
                        item = self.window_select_combo.model().item(index)
                        if item:
                            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            else:
                self.window_select_combo.addItem("未找到任何窗口")

        except Exception as e:
            print(f"刷新窗口选择列表失败: {e}")
            self.window_select_combo.clear()
            self.window_select_combo.addItem("获取窗口列表失败")

    def _get_pc_and_ldplayer_windows(self):
        """获取PC窗口和雷电模拟器窗口，分类排序并用虚线分隔"""
        try:
            from utils.emulator_detector import EmulatorDetector
            detector = EmulatorDetector()

            ldplayer_windows = []  # 雷电模拟器窗口
            mumu_windows = []      # MuMu模拟器窗口
            pc_windows = []        # PC窗口

            def enum_child_windows(parent_hwnd):
                """枚举指定窗口的子窗口"""
                child_windows = []

                def enum_child_callback(hwnd, lParam):
                    try:
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            class_name = win32gui.GetClassName(hwnd)

                            # 检查是否是雷电模拟器渲染窗口
                            if class_name == "RenderWindow" or title == "TheRender":
                                original_title = title or "TheRender"
                                display_title = f"{original_title} [雷电模拟器]"
                                child_windows.append((display_title, original_title))

                            # 检查是否是MuMu模拟器渲染窗口
                            elif class_name == "nemuwin" and "nemudisplay" in title.lower():
                                # 检查窗口大小，过滤掉小的缩略图窗口
                                try:
                                    rect = win32gui.GetClientRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]

                                    # 只显示大于300x200的渲染窗口，过滤缩略图
                                    if width > 300 and height > 200:
                                        original_title = title or "nemudisplay"
                                        # 为MuMu模拟器生成更友好的显示名称
                                        if "nemudisplay" in original_title:
                                            # 提取实例编号（如果有）
                                            instance_num = ""
                                            if "-" in original_title:
                                                parts = original_title.split("-")
                                                if len(parts) > 1 and parts[1].isdigit():
                                                    instance_num = f"-{parts[1]}"
                                            display_title = f"MuMu模拟器{instance_num} [MuMu模拟器]"
                                        else:
                                            display_title = f"{original_title} [MuMu模拟器]"
                                        child_windows.append((display_title, original_title))
                                except:
                                    pass
                    except:
                        pass
                    return True

                win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, 0)
                return child_windows

            def enum_pc_and_ldplayer_windows(hwnd, lParam):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title and title != "选择子窗口":
                            class_name = win32gui.GetClassName(hwnd)

                            # 检查是否是雷电模拟器主窗口
                            if class_name == "LDPlayerMainFrame":
                                # 枚举其子窗口寻找渲染窗口
                                child_windows = enum_child_windows(hwnd)
                                ldplayer_windows.extend(child_windows)
                                return True  # 跳过主窗口本身

                            # 检查是否是MuMu模拟器主窗口
                            elif (class_name in ["Qt5156QWindowIcon", "Qt6QWindowIcon"] and
                                  "mumu" in title.lower()):
                                # 枚举其子窗口寻找渲染窗口
                                child_windows = enum_child_windows(hwnd)
                                mumu_windows.extend(child_windows)
                                return True  # 跳过主窗口本身

                            # 检测窗口类型
                            is_emulator, emulator_type, description = detector.detect_emulator_type(hwnd)

                            if is_emulator:
                                # 显示模拟器窗口
                                if emulator_type in ["ldplayer", "therender"]:
                                    display_title = f"{title} [雷电模拟器]"
                                    ldplayer_windows.append((display_title, title))
                                elif emulator_type == "mumu":
                                    # 为MuMu模拟器生成更友好的显示名称
                                    if "nemudisplay" in title:
                                        # 提取实例编号（如果有）
                                        instance_num = ""
                                        if "-" in title:
                                            parts = title.split("-")
                                            if len(parts) > 1 and parts[1].isdigit():
                                                instance_num = f"-{parts[1]}"
                                        display_title = f"MuMu模拟器{instance_num} [MuMu模拟器]"
                                    else:
                                        display_title = f"{title} [MuMu模拟器]"
                                    mumu_windows.append((display_title, title))
                            else:
                                # 🔧 只显示剑网3相关的PC窗口，但排除启动器
                                # if ("剑网3" in title and
                                if ("启动器" not in title and
                                    "系列启动器" not in title and
                                    "launcher" not in title.lower()):
                                    friendly_title = self._get_friendly_window_title(title)
                                    display_title = f"{friendly_title} [PC窗口]"
                                    pc_windows.append((display_title, title))
                except:
                    pass
                return True

            win32gui.EnumWindows(enum_pc_and_ldplayer_windows, 0)

            # 分类排序并组合
            result = []

            # 先添加雷电模拟器窗口
            if ldplayer_windows:
                ldplayer_windows.sort(key=lambda x: x[0])  # 按显示标题排序
                result.extend(ldplayer_windows)

            # 添加MuMu模拟器窗口
            if mumu_windows:
                # 如果有雷电模拟器窗口，添加分隔线
                if ldplayer_windows:
                    result.append(("─────────────────────", ""))
                mumu_windows.sort(key=lambda x: x[0])  # 按显示标题排序
                result.extend(mumu_windows)

            # 添加分隔线
            if (ldplayer_windows or mumu_windows) and pc_windows:
                result.append(("─────────────────────", ""))

            # 再添加PC窗口
            if pc_windows:
                pc_windows.sort(key=lambda x: x[0])  # 按显示标题排序
                result.extend(pc_windows)

            return result

        except ImportError:
            # 如果模拟器检测器不可用，回退到显示所有窗口
            window_titles = []
            win32gui.EnumWindows(self._enum_windows_callback, window_titles)
            return [title for title in window_titles if title and title != "选择子窗口"]
        except Exception as e:
            print(f"获取窗口列表时出错: {e}")
            return []

    def _get_friendly_window_title(self, title):
        """获取友好的窗口标题显示"""
        if not title:
            return "未知窗口"

        # 如果标题包含路径，提取文件名
        if '\\' in title:
            # 尝试提取路径中的可执行文件名
            import os
            parts = title.split(' ')
            for part in parts:
                if '\\' in part and ('.exe' in part.lower() or '.py' in part.lower()):
                    # 提取文件名（不包含扩展名）
                    filename = os.path.basename(part)
                    name_without_ext = os.path.splitext(filename)[0]
                    # 如果还有其他部分，组合显示
                    remaining = title.replace(part, '').strip()
                    if remaining:
                        return f"{name_without_ext} - {remaining}"
                    else:
                        return name_without_ext

        # 如果标题太长，截断显示
        if len(title) > 50:
            return title[:47] + "..."

        return title

    def _refresh_bound_windows_combo(self):
        """刷新已绑定窗口下拉框"""
        self.bound_windows_combo.clear()

        if not self.bound_windows:
            self.bound_windows_combo.addItem("-- 无绑定窗口 --")
            self.bound_windows_combo.setEnabled(False)
            self.remove_window_button.setEnabled(False)
            return

        self.bound_windows_combo.setEnabled(True)
        self.remove_window_button.setEnabled(True)

        for i, window_info in enumerate(self.bound_windows):
            title = window_info['title']
            hwnd = window_info.get('hwnd', 0)

            # 构建显示文本
            if hwnd and hwnd != 0:
                display_text = f"✓ {title} (句柄: {hwnd})"
            else:
                display_text = f"✓ {title}"

            self.bound_windows_combo.addItem(display_text)
            # 保存窗口信息到item data
            self.bound_windows_combo.setItemData(i, window_info)

    def _smart_add_window(self):
        """智能添加窗口 - 自动检测雷电模拟器窗口"""
        if not WIN32_AVAILABLE_FOR_LIST:
            QMessageBox.warning(self, "错误", "需要安装 pywin32 才能使用此功能")
            return

        selected_text = self.window_select_combo.currentText()
        if not selected_text or selected_text == "-- 选择窗口 --":
            QMessageBox.information(self, "提示", "请先选择要添加的窗口")
            return

        # 检查是否选择了分隔线
        if selected_text.startswith("─"):
            QMessageBox.information(self, "提示", "请选择一个有效的窗口，而不是分隔线")
            return

        # 获取原始窗口标题
        current_index = self.window_select_combo.currentIndex()
        original_title = self.window_select_combo.itemData(current_index)
        if not original_title:
            original_title = selected_text  # 回退到显示文本

        # 自动检测并添加窗口
        self._auto_detect_and_add_window(original_title)

        # 重置选择
        self.window_select_combo.setCurrentIndex(0)

    def _batch_add_same_type_windows(self):
        """一键绑定所有同类型窗口"""
        if not WIN32_AVAILABLE_FOR_LIST:
            QMessageBox.warning(self, "错误", "需要安装 pywin32 才能使用此功能")
            return

        # 🔧 批量绑定前先清理失效的窗口
        logger.info("批量绑定开始：准备清理失效窗口")
        self._cleanup_invalid_windows()
        logger.info("批量绑定：失效窗口清理完成")

        selected_text = self.window_select_combo.currentText()
        if not selected_text or selected_text == "-- 无可用窗口 --":
            QMessageBox.information(self, "提示", "请先选择一个窗口作为参考")
            return

        # 获取选中窗口的原始标题
        current_index = self.window_select_combo.currentIndex()
        original_title = self.window_select_combo.itemData(current_index)
        if not original_title:
            original_title = selected_text

        try:
            # 查找选中窗口的句柄
            reference_hwnd = self._find_window_handle(original_title)
            if not reference_hwnd:
                QMessageBox.warning(self, "错误", f"无法找到参考窗口: {original_title}")
                return

            # 检测参考窗口的类型
            window_type = self._detect_window_type(reference_hwnd, original_title)

            # 根据窗口类型查找所有同类型窗口
            same_type_windows = self._find_all_same_type_windows(window_type, reference_hwnd)

            logger.info(f"🔍 查找到 {len(same_type_windows)} 个{window_type}类型的窗口")

            if not same_type_windows:
                # 🔧 修复：如果没有找到其他窗口，尝试绑定当前选择的窗口
                logger.info(f"未找到其他{window_type}类型窗口，尝试绑定当前选择的窗口")

                # 检查当前窗口是否已经绑定
                if not self._is_window_already_bound(original_title, reference_hwnd):
                    reply = QMessageBox.question(
                        self, "绑定当前窗口",
                        f"未找到其他{window_type}类型的窗口。\n\n是否绑定当前选择的窗口：\n• {original_title}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self._add_window_if_not_exists(original_title, reference_hwnd)
                        self._save_bound_windows_config()
                        QMessageBox.information(self, "绑定完成", f"成功绑定窗口：{original_title}")
                    return
                else:
                    QMessageBox.information(self, "提示", f"当前窗口已经绑定，未找到其他{window_type}类型的窗口")
                    return

            # 显示确认对话框
            window_list_items = []
            for item in same_type_windows:
                if isinstance(item, (tuple, list)) and len(item) >= 2:
                    window_list_items.append(f"• {item[0]}")
                elif isinstance(item, int):
                    # 如果是句柄，尝试获取窗口标题
                    try:
                        import win32gui
                        title = win32gui.GetWindowText(item)
                        if not title:
                            title = f"窗口_{item}"
                        window_list_items.append(f"• {title}")
                    except:
                        window_list_items.append(f"• 窗口_{item}")
                else:
                    window_list_items.append(f"• {str(item)}")

            window_list = "\n".join(window_list_items)
            reply = QMessageBox.question(
                self, "确认批量绑定",
                f"检测到 {len(same_type_windows)} 个{window_type}类型的窗口:\n\n{window_list}\n\n是否一键绑定所有这些窗口？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 批量添加窗口
                added_count = 0
                skipped_count = 0

                # 🔧 安全解包：检查数据格式
                logger.info(f"批量绑定: 准备处理 {len(same_type_windows)} 个同类型窗口")

                for i, item in enumerate(same_type_windows):
                    try:
                        # 检查item的类型和格式
                        if isinstance(item, (tuple, list)) and len(item) >= 2:
                            window_title, window_hwnd = item[0], item[1]
                        elif isinstance(item, int):
                            # 如果是单个整数（句柄），尝试获取窗口标题
                            import win32gui
                            window_hwnd = item
                            try:
                                window_title = win32gui.GetWindowText(window_hwnd)
                                if not window_title:
                                    window_title = f"窗口_{window_hwnd}"
                            except:
                                window_title = f"窗口_{window_hwnd}"
                        else:
                            logger.warning(f"跳过格式错误的项目 {i}: {type(item)} = {item}")
                            continue

                        # 检查是否已存在
                        if self._is_window_already_bound(window_title, window_hwnd):
                            skipped_count += 1
                            continue

                        # 静默添加窗口（不显示对话框）
                        try:
                            self._add_window_silently(window_title, window_hwnd)
                            added_count += 1
                        except Exception as e:
                            logger.warning(f"添加窗口失败: {window_title} - {e}")
                    except Exception as e:
                        logger.error(f"处理窗口项目失败: {e}")

                # 🔧 批量绑定完成后保存配置
                if added_count > 0:
                    self._save_bound_windows_config()
                    QMessageBox.information(
                        self, "批量绑定完成",
                        f"成功绑定 {added_count} 个{window_type}窗口\n跳过已绑定的 {skipped_count} 个窗口\n配置已保存到文件"
                    )
                else:
                    QMessageBox.information(self, "提示", "所有同类型窗口都已绑定")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"批量绑定失败: {e}")

    def _detect_window_type(self, hwnd: int, title: str) -> str:
        """检测窗口类型"""
        try:
            logger.info(f"🔍 检测窗口类型: {title} (HWND: {hwnd})")

            # 🔧 首先基于窗口标题进行快速检测
            if ("mumu" in title.lower() or "安卓设备" in title or
                "nemudisplay" in title.lower() or "android" in title.lower()):
                logger.info(f"✅ 基于标题识别为MuMu窗口: {title}")
                return "MUMU"

            # 🔧 修复：增强雷电模拟器检测逻辑，包括TheRender窗口
            if ("雷电" in title or "ldplayer" in title.lower() or
                "leidian" in title.lower() or title == "TheRender"):
                logger.info(f"✅ 基于标题识别为雷电窗口: {title}")
                return "LDPLAYER"

            # 使用模拟器检测器进行深度检测
            from utils.emulator_detector import detect_emulator_type
            is_emulator, emulator_type, description = detect_emulator_type(hwnd)

            logger.info(f"模拟器检测结果: is_emulator={is_emulator}, type={emulator_type}, desc={description}")

            if is_emulator and emulator_type != 'unknown':
                # 🔧 修复：统一处理therender类型
                if emulator_type in ['ldplayer', 'therender']:
                    logger.info(f"✅ 检测器识别为雷电模拟器: {emulator_type}")
                    return "LDPLAYER"
                else:
                    logger.info(f"✅ 检测器识别为模拟器: {emulator_type.upper()}")
                    return emulator_type.upper()  # 返回 MUMU, LDPLAYER 等
            else:
                logger.info(f"❌ 未识别为模拟器，归类为PC窗口: {title}")
                return "PC窗口"  # 普通PC应用窗口

        except Exception as e:
            logger.warning(f"检测窗口类型失败: {e}")
            return "PC窗口"

    def _find_all_same_type_windows(self, window_type: str, reference_hwnd: int) -> list:
        """查找所有同类型的窗口"""
        try:
            same_type_windows = []

            if window_type == "MUMU":
                # MuMu模拟器：查找所有MuMu窗口
                same_type_windows = self._find_all_mumu_windows()
            elif window_type == "LDPLAYER":
                # 雷电模拟器：查找所有雷电窗口
                same_type_windows = self._find_all_ldplayer_windows()
            else:
                # PC窗口：查找所有非模拟器窗口
                same_type_windows = self._find_all_pc_windows()

            return same_type_windows

        except Exception as e:
            logger.error(f"查找同类型窗口失败: {e}")
            return []

    def _find_all_mumu_windows(self) -> list:
        """查找所有MuMu模拟器窗口"""
        try:
            from utils.window_finder import WindowFinder
            import win32gui

            # 查找所有MuMu相关窗口句柄
            mumu_hwnds = WindowFinder.find_all_windows("MuMu", emulator_type="mumu")

            # 🔧 修复：查找MuMu渲染窗口而不是主窗口
            device_windows = []

            # 首先找到所有MuMu主窗口
            main_windows = []
            for hwnd in mumu_hwnds:
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if ("安卓设备" in title or "Android" in title):
                        if ("管理器" not in title and "Manager" not in title and
                            title != "MuMu模拟器"):
                            main_windows.append((title, hwnd))
                            logger.info(f"找到MuMu主窗口: {title} (HWND: {hwnd})")
                except:
                    continue

            # 为每个主窗口查找对应的渲染窗口
            for main_title, main_hwnd in main_windows:
                try:
                    # 枚举主窗口的子窗口，查找渲染窗口
                    def enum_child_callback(child_hwnd, param):
                        try:
                            child_title = win32gui.GetWindowText(child_hwnd)
                            child_class = win32gui.GetClassName(child_hwnd)

                            # 检查是否是MuMu渲染窗口
                            if (child_class == "nemuwin" and
                                "nemudisplay" in child_title.lower() and
                                win32gui.IsWindowVisible(child_hwnd)):

                                # 检查窗口大小，过滤掉小的缩略图窗口
                                try:
                                    rect = win32gui.GetClientRect(child_hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]

                                    if width > 300 and height > 200:
                                        # 使用主窗口的标题，但绑定渲染窗口的句柄
                                        param.append((main_title, child_hwnd))
                                        logger.info(f"找到MuMu渲染窗口: {main_title} -> {child_title} (HWND: {child_hwnd})")
                                except:
                                    pass
                        except:
                            pass
                        return True

                    win32gui.EnumChildWindows(main_hwnd, enum_child_callback, device_windows)

                except Exception as e:
                    logger.warning(f"查找 {main_title} 的渲染窗口失败: {e}")
                    # 如果找不到渲染窗口，回退到主窗口
                    device_windows.append((main_title, main_hwnd))
                    logger.info(f"回退到主窗口: {main_title} (HWND: {main_hwnd})")

            logger.info(f"总共找到 {len(device_windows)} 个MuMu渲染窗口")
            return device_windows

        except Exception as e:
            logger.error(f"查找MuMu窗口失败: {e}")
            return []

    def _find_all_ldplayer_windows(self) -> list:
        """查找所有雷电模拟器窗口"""
        try:
            from utils.window_finder import WindowFinder
            from utils.emulator_detector import EmulatorDetector
            import win32gui

            logger.info("🔍 开始查找所有雷电模拟器窗口...")

            device_windows = []
            detector = EmulatorDetector()

            # 方法1：查找TheRender窗口（雷电模拟器渲染窗口）
            therender_hwnds = WindowFinder.find_all_windows("TheRender", emulator_type="ldplayer")
            logger.info(f"找到 {len(therender_hwnds)} 个TheRender窗口")

            for hwnd in therender_hwnds:
                try:
                    title = win32gui.GetWindowText(hwnd) or "TheRender"
                    # 验证是否确实是雷电模拟器窗口
                    is_emulator, emulator_type, _ = detector.detect_emulator_type(hwnd)
                    if is_emulator and emulator_type in ['ldplayer', 'therender']:
                        device_windows.append((title, hwnd))
                        logger.info(f"✅ 找到雷电渲染窗口: {title} (HWND: {hwnd})")
                except Exception as e:
                    logger.debug(f"检查TheRender窗口失败: {e}")
                    continue

            # 方法2：查找传统的雷电模拟器主窗口
            ldplayer_hwnds = WindowFinder.find_all_windows("雷电", emulator_type="ldplayer")
            logger.info(f"找到 {len(ldplayer_hwnds)} 个传统雷电窗口")

            for hwnd in ldplayer_hwnds:
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if "雷电模拟器" in title and "多开器" not in title:
                        # 避免重复添加
                        if not any(existing_hwnd == hwnd for _, existing_hwnd in device_windows):
                            device_windows.append((title, hwnd))
                            logger.info(f"✅ 找到雷电主窗口: {title} (HWND: {hwnd})")
                except Exception as e:
                    logger.debug(f"检查雷电主窗口失败: {e}")
                    continue

            logger.info(f"🎯 总共找到 {len(device_windows)} 个雷电模拟器窗口")
            return device_windows

        except Exception as e:
            logger.error(f"查找雷电窗口失败: {e}")
            return []

    def _find_all_pc_windows(self) -> list:
        """查找所有剑网3相关的PC应用窗口"""
        try:
            import win32gui
            from utils.emulator_detector import detect_emulator_type

            pc_windows = []

            def enum_windows_callback(hwnd, _):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if title and len(title.strip()) > 0:
                            # 检查是否为模拟器
                            is_emulator, _, _ = detect_emulator_type(hwnd)
                            if not is_emulator:
                                # 🔧 只添加包含"剑网3"的窗口，但排除启动器
                                if ("剑网3" in title and
                                    "启动器" not in title and
                                    "系列启动器" not in title and
                                    "launcher" not in title.lower()):
                                    pc_windows.append((title, hwnd))
                except:
                    pass
                return True

            win32gui.EnumWindows(enum_windows_callback, None)

            logger.info(f"找到 {len(pc_windows)} 个剑网3窗口")
            return pc_windows

        except Exception as e:
            logger.error(f"查找剑网3窗口失败: {e}")
            return []

    def _is_window_already_bound(self, title: str, hwnd: int) -> bool:
        """检查窗口是否已经绑定"""
        for window_info in self.bound_windows:
            existing_hwnd = window_info.get('hwnd', 0)

            # 🔧 修复：只检查句柄是否相同，不检查标题
            # 因为多个窗口可能有相同标题（如MuMu的nemudisplay）
            if hwnd and hwnd != 0 and existing_hwnd == hwnd:
                return True
        return False

    def _save_bound_windows_config(self):
        """保存绑定窗口配置到文件"""
        try:
            # 更新当前配置中的所有相关信息
            self.current_config['bound_windows'] = self.bound_windows
            self.current_config['window_binding_mode'] = self.window_binding_mode

            # 确保自定义分辨率也被保存
            if hasattr(self, 'width_spinbox') and hasattr(self, 'height_spinbox'):
                self.current_config['custom_width'] = self.width_spinbox.value()
                self.current_config['custom_height'] = self.height_spinbox.value()

            # 通过父窗口保存配置
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, 'save_config_func'):
                parent_window.save_config_func(self.current_config)
                logger.info(f"✅ 已通过父窗口保存配置，共 {len(self.bound_windows)} 个窗口")
            else:
                # 备用方案：直接调用main模块的save_config
                from main import save_config
                save_config(self.current_config)
                logger.info(f"✅ 已直接保存配置，共 {len(self.bound_windows)} 个窗口")

        except Exception as e:
            logger.error(f"保存配置失败: {e}")

    def _cleanup_invalid_windows(self):
        """清理失效的窗口（句柄无效或窗口不可见）"""
        try:
            import win32gui

            logger.info(f"开始清理失效窗口，当前绑定窗口数量: {len(self.bound_windows)}")

            valid_windows = []
            removed_count = 0

            for window_info in self.bound_windows:
                window_title = window_info.get('title', '')
                hwnd = window_info.get('hwnd', 0)

                # 检查窗口是否仍然有效
                is_valid = False
                try:
                    if hwnd and hwnd != 0:
                        # 🔧 更严格的窗口验证
                        window_exists = win32gui.IsWindow(hwnd)
                        window_visible = win32gui.IsWindowVisible(hwnd) if window_exists else False

                        # 尝试获取窗口标题来进一步验证
                        current_title = ""
                        if window_exists:
                            try:
                                current_title = win32gui.GetWindowText(hwnd)
                            except:
                                pass

                        if window_exists and window_visible and current_title:
                            # 🔧 检查窗口类型：现在我们只保留渲染窗口
                            window_class = ""
                            try:
                                window_class = win32gui.GetClassName(hwnd)
                            except:
                                pass

                            if "nemudisplay" in current_title.lower() and window_class == "nemuwin":
                                # 这是MuMu渲染窗口，应该保留
                                is_valid = True
                                logger.debug(f"窗口有效(渲染窗口): {window_title} (HWND: {hwnd}, 当前标题: {current_title}, 类名: {window_class})")
                            elif ("安卓设备" in current_title or "Android" in current_title):
                                # 这是MuMu主窗口，应该清理掉（因为我们现在绑定渲染窗口）
                                logger.info(f"清理主窗口: {window_title} (HWND: {hwnd}) - 现在使用渲染窗口 (当前标题: {current_title}, 类名: {window_class})")
                                is_valid = False
                            else:
                                # 其他类型的窗口，保持原有逻辑
                                is_valid = True
                                logger.debug(f"窗口有效(其他类型): {window_title} (HWND: {hwnd}, 当前标题: {current_title})")
                        else:
                            logger.info(f"窗口失效: {window_title} (HWND: {hwnd}) - 存在:{window_exists}, 可见:{window_visible}, 标题:'{current_title}'")
                    else:
                        logger.info(f"窗口失效: {window_title} - 无有效句柄")
                except Exception as e:
                    logger.warning(f"检查窗口失败: {window_title} (HWND: {hwnd}) - {e}")
                    # 检查失败也认为是失效窗口
                    is_valid = False

                if is_valid:
                    valid_windows.append(window_info)
                else:
                    removed_count += 1
                    logger.info(f"移除失效窗口: {window_title} (HWND: {hwnd})")

            # 更新绑定窗口列表
            self.bound_windows = valid_windows

            logger.info(f"清理完成: 移除 {removed_count} 个失效窗口，剩余 {len(valid_windows)} 个有效窗口")

            # 如果有窗口被移除，刷新界面并保存配置
            if removed_count > 0:
                self._refresh_bound_windows_combo()
                self._save_bound_windows_config()
                logger.info(f"已保存清理后的配置")

        except Exception as e:
            logger.error(f"清理失效窗口失败: {e}")

    def _on_accept(self):
        """处理确定按钮点击事件，确保配置被正确保存"""
        try:
            # 🔧 确保绑定窗口配置被保存
            logger.info(f"全局设置对话框确定：准备保存配置，当前绑定窗口数量: {len(self.bound_windows)}")
            logger.info(f"  当前 bound_windows 内容: {[w.get('title') for w in self.bound_windows]}")

            # 🔧 关键修复：确保 current_config 的引用被更新
            # 不仅更新字典中的值，还要确保列表引用被更新
            self.current_config['bound_windows'] = self.bound_windows[:]  # 创建副本以避免引用问题
            self.current_config['window_binding_mode'] = self.window_binding_mode

            # 🔧 关键修复：保存自定义分辨率配置
            self.current_config['custom_width'] = self.width_spinbox.value()
            self.current_config['custom_height'] = self.height_spinbox.value()

            # 🔧 新增：保存主题设置并同步到系统托盘菜单
            theme_text = self.theme_combo.currentText()
            if theme_text == "明亮模式":
                theme_mode = 'light'
            else:
                theme_mode = 'dark'
            self.current_config['theme'] = theme_mode
            
            # 🔧 关键修复：立即应用主题
            app = QApplication.instance()
            if app and hasattr(app, 'theme_manager'):
                app.theme_manager.set_theme(theme_mode)
                logger.info(f"已应用主题：{theme_mode}")
            
            # 同步更新系统托盘菜单的选中状态
            app = QApplication.instance()
            if app and hasattr(app, 'main_window') and hasattr(app.main_window, 'light_action'):
                if theme_mode == 'light':
                    app.main_window.light_action.setChecked(True)
                    app.main_window.dark_action.setChecked(False)
                else:
                    app.main_window.dark_action.setChecked(True)
                    app.main_window.light_action.setChecked(False)

            logger.info(f"  已更新 current_config['bound_windows']: {len(self.current_config['bound_windows'])} 个窗口")
            logger.info(f"  已更新 current_config['custom_width']: {self.current_config['custom_width']}")
            logger.info(f"  已更新 current_config['custom_height']: {self.current_config['custom_height']}")

            # 保存配置（这会更新文件）
            self._save_bound_windows_config()

            # 调用默认的accept方法
            self.accept()

        except Exception as e:
            logger.error(f"处理确定按钮失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 即使出错也要关闭对话框
            self.accept()

    def _add_window_silently(self, window_title: str, hwnd: int = 0):
        """静默添加窗口（不显示对话框）"""
        # 检查是否已存在相同的窗口
        for window_info in self.bound_windows:
            existing_title = window_info.get('title', '')
            existing_hwnd = window_info.get('hwnd', 0)

            # 如果句柄相同且都不为0，则认为是重复窗口
            if hwnd and hwnd != 0 and existing_hwnd and existing_hwnd != 0 and existing_hwnd == hwnd:
                logger.info(f"跳过重复窗口（句柄相同）: {window_title} (HWND: {hwnd})")
                return

            # 如果标题和句柄都相同，则认为是重复窗口
            if existing_title == window_title and existing_hwnd == hwnd:
                logger.info(f"跳过重复窗口（标题和句柄相同）: {window_title}")
                return

        # 添加新窗口到列表
        new_window = {
            'title': window_title,
            'enabled': True
        }
        if hwnd and hwnd != 0:
            new_window['hwnd'] = hwnd
            # 保存窗口DPI信息
            try:
                new_window['dpi_info'] = self._get_window_dpi_info(hwnd)
            except:
                pass

        self.bound_windows.append(new_window)
        logger.info(f"✅ 成功添加窗口: {window_title} (HWND: {hwnd})")

        # 为新窗口预创建OCR服务
        try:
            self._preregister_window_ocr_service(new_window)
        except:
            pass

        # 检测模拟器类型并验证VM索引
        if hwnd:
            try:
                emulator_type = self._detect_emulator_type(hwnd)
                if emulator_type == "mumu":
                    self._verify_mumu_vm_index(hwnd, window_title)
            except:
                pass

        # 自动调整新添加窗口的分辨率
        try:
            self._auto_resize_single_window(new_window)
        except:
            pass

        # 刷新界面
        self._refresh_bound_windows_combo()
        self._update_execution_mode_visibility()

    def _add_selected_window_direct(self, selected_text):
        """直接添加选中的窗口（原有逻辑）"""
        # 查找窗口句柄
        hwnd = self._find_window_handle(selected_text)

        # 如果没有找到句柄（比如所有TheRender窗口都已绑定），给出提示
        if selected_text == "TheRender" and hwnd is None:
            QMessageBox.information(self, "提示", "所有TheRender窗口都已绑定")
            return

        self._add_window_if_not_exists(selected_text, hwnd)

    def _auto_detect_and_add_window(self, selected_text):
        """自动检测窗口类型并添加"""
        try:
            # 导入模拟器检测器
            from utils.emulator_detector import EmulatorDetector
            detector = EmulatorDetector()

            # 查找窗口句柄
            hwnd = self._find_window_handle(selected_text)
            if hwnd == "ALL_BOUND":
                QMessageBox.information(self, "提示", f"所有 {selected_text} 窗口都已被绑定")
                return
            elif not hwnd:
                QMessageBox.warning(self, "错误", f"未找到窗口: {selected_text}")
                return

            # 检测窗口类型
            is_emulator, emulator_type, description = detector.detect_emulator_type(hwnd)

            if is_emulator:
                QMessageBox.information(self, "检测结果",
                    f"检测到{description}窗口\n将使用模拟器模式添加")
            else:
                QMessageBox.information(self, "检测结果",
                    f"检测到普通窗口\n将使用标准模式添加")

            self._add_window_if_not_exists(selected_text, hwnd)

        except ImportError:
            QMessageBox.warning(self, "错误", "模拟器检测器不可用，使用标准模式添加")
            self._add_selected_window_direct(selected_text)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"自动检测失败: {e}")

    def _add_simulator_window(self):
        """添加模拟器窗口"""
        try:
            child_windows = self._enumerate_child_windows()

            if not child_windows:
                QMessageBox.information(self, "提示", "未找到雷电模拟器渲染窗口")
                return

            # 获取已绑定的窗口句柄，用于过滤
            bound_hwnds = set()
            for window_info in self.bound_windows:
                hwnd = window_info.get('hwnd')
                if hwnd and hwnd != 0:
                    bound_hwnds.add(hwnd)

            # 准备选择列表和映射，过滤已绑定的窗口
            dialog_items = []
            window_mapping = {}  # 映射显示文本到窗口信息
            available_windows = []

            for hwnd, title, class_name in child_windows:
                if hwnd not in bound_hwnds:  # 只显示未绑定的窗口
                    display_text = f"{title} (类名: {class_name}, 句柄: {hwnd})"
                    dialog_items.append(display_text)
                    window_mapping[display_text] = (hwnd, title, class_name)
                    available_windows.append((hwnd, title, class_name))

            if not available_windows:
                QMessageBox.information(self, "提示", "所有雷电模拟器渲染窗口都已绑定")
                return

            selected_item, ok = QInputDialog.getItem(
                self, "选择模拟器窗口", "请选择要添加的雷电模拟器渲染窗口:",
                dialog_items, 0, False
            )

            if ok and selected_item:
                hwnd, title, class_name = window_mapping[selected_item]
                self._add_window_if_not_exists(title, hwnd)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取模拟器窗口失败:\n{e}")

    def _auto_resize_single_window(self, window_info: dict):
        """自动调整单个窗口的分辨率（使用通用窗口管理器）"""
        try:
            logger.debug(f"开始自动调整窗口分辨率: {window_info}")

            target_client_width = self.get_custom_width()
            target_client_height = self.get_custom_height()

            # 检查是否配置了自定义分辨率
            if target_client_width <= 0 or target_client_height <= 0:
                logger.debug("未配置自定义分辨率，跳过窗口调整")
                return

            window_title = window_info.get('title', '')
            window_hwnd = window_info.get('hwnd')

            if not window_hwnd:
                logging.warning(f"窗口 {window_title} 没有有效的句柄")
                return

            # 工具 修复：添加窗口有效性检查
            try:
                import win32gui
                if not win32gui.IsWindow(window_hwnd):
                    logging.warning(f"窗口句柄无效: {window_title} (HWND: {window_hwnd})")
                    return
            except Exception as check_error:
                logging.warning(f"检查窗口有效性失败: {check_error}")
                return

            # 检测是否为MuMu模拟器，如果是则跳过绑定时的分辨率调整
            try:
                from utils.emulator_detector import EmulatorDetector
                detector = EmulatorDetector()
                is_emulator, emulator_type, _ = detector.detect_emulator_type(window_hwnd)

                if is_emulator and emulator_type == "mumu":
                    logger.info(f"检测到MuMu模拟器窗口，跳过绑定时的分辨率调整: {window_title}")
                    logger.info("MuMu模拟器分辨率将在全局设置确定时统一调整")
                    return

            except Exception as detect_error:
                logger.warning(f"检测模拟器类型失败: {detect_error}")

            try:
                # 使用通用窗口管理器调整分辨率
                from utils.universal_window_manager import get_universal_window_manager
                window_manager = get_universal_window_manager()

                # 使用异步模式避免界面卡死
                result = window_manager.adjust_single_window(window_hwnd, target_client_width, target_client_height, async_mode=True)

                if result.success:
                    logging.info(f"窗口分辨率调整成功: {result.title} "
                               f"({result.before_size[0]}x{result.before_size[1]} -> {result.after_size[0]}x{result.after_size[1]})")
                else:
                    logging.error(f"窗口分辨率调整失败: {result.title} - {result.message}")

            except ImportError as import_error:
                logging.error(f"导入窗口管理器失败: {import_error}")
                # 回退到原有方法
                self._auto_resize_single_window_legacy(window_info, target_client_width, target_client_height)
            except Exception as resize_error:
                logging.error(f"调整窗口分辨率时发生错误: {resize_error}", exc_info=True)
                # 回退到原有方法
                self._auto_resize_single_window_legacy(window_info, target_client_width, target_client_height)

        except Exception as e:
            logging.error(f"自动调整窗口分辨率过程异常: {e}", exc_info=True)

    def _auto_resize_single_window_legacy(self, window_info: dict, target_client_width: int, target_client_height: int):
        """原有的窗口分辨率调整方法（作为备用）"""
        # 检查pywin32是否可用
        if not PYWIN32_AVAILABLE or win32gui is None:
            return

        window_title = window_info.get('title', '')
        window_hwnd = window_info.get('hwnd')

        try:
            # 优先使用保存的句柄
            if window_hwnd:
                if win32gui.IsWindow(window_hwnd):
                    logging.info(f"自动调整窗口分辨率: {window_title} (HWND: {window_hwnd}) -> {target_client_width}x{target_client_height}")

                    # 检查是否为子窗口
                    parent_hwnd = win32gui.GetParent(window_hwnd)
                    is_child_window = parent_hwnd != 0

                    if is_child_window:
                        self._resize_parent_and_child_window(
                            parent_hwnd, window_hwnd, window_title,
                            target_client_width, target_client_height
                        )
                    else:
                        self._resize_single_window(
                            window_hwnd, window_title,
                            target_client_width, target_client_height
                        )

                    logging.info(f"成功 窗口 {window_title} 分辨率自动调整成功")
                else:
                    logging.warning(f"窗口句柄无效: {window_title} (HWND: {window_hwnd})")
            else:
                # 没有句柄，尝试查找
                hwnd, is_child_window, parent_hwnd = self._find_window_with_parent_info(window_title)
                if hwnd:
                    # 更新句柄
                    window_info['hwnd'] = hwnd

                    logging.info(f"自动调整窗口分辨率: {window_title} (HWND: {hwnd}) -> {target_client_width}x{target_client_height}")

                    if is_child_window and parent_hwnd:
                        self._resize_parent_and_child_window(
                            parent_hwnd, hwnd, window_title,
                            target_client_width, target_client_height
                        )
                    else:
                        self._resize_single_window(
                            hwnd, window_title,
                            target_client_width, target_client_height
                        )

                    logging.info(f"成功 窗口 {window_title} 分辨率自动调整成功")
                else:
                    logging.warning(f"无法找到窗口进行分辨率调整: {window_title}")

        except Exception as e:
            logging.error(f"自动调整窗口 {window_title} 分辨率时发生错误: {e}")

    def _add_window_if_not_exists(self, window_title: str, hwnd: int = 0):
        """如果窗口不存在则添加"""
        # 检查是否已存在相同的窗口
        for window_info in self.bound_windows:
            existing_title = window_info.get('title', '')
            existing_hwnd = window_info.get('hwnd', 0)

            # 如果句柄相同且都不为0，则认为是重复窗口（优先检查句柄）
            if hwnd and hwnd != 0 and existing_hwnd and existing_hwnd != 0 and existing_hwnd == hwnd:
                QMessageBox.information(self, "提示", f"窗口句柄 {hwnd} 已被绑定到 '{existing_title}'")
                return

            # 如果标题和句柄都相同，则认为是重复窗口
            if existing_title == window_title and existing_hwnd == hwnd:
                if hwnd and hwnd != 0:
                    QMessageBox.information(self, "提示", f"窗口 '{window_title}' (句柄: {hwnd}) 已存在")
                else:
                    QMessageBox.information(self, "提示", f"窗口 '{window_title}' 已存在")
                return

        # 添加新窗口到列表
        new_window = {
            'title': window_title,
            'enabled': True
        }
        if hwnd and hwnd != 0:
            new_window['hwnd'] = hwnd
            # 工具 新增：保存窗口DPI信息
            new_window['dpi_info'] = self._get_window_dpi_info(hwnd)

        self.bound_windows.append(new_window)
        self._refresh_bound_windows_combo()

        # 为新窗口预创建OCR服务
        self._preregister_window_ocr_service(new_window)

        # 检测模拟器类型并验证VM索引
        if hwnd:
            emulator_type = self._detect_emulator_type(hwnd)
            if emulator_type == "mumu":
                self._verify_mumu_vm_index(hwnd, window_title)

        # 自动调整新添加窗口的分辨率（MuMu模拟器会跳过）
        self._auto_resize_single_window(new_window)

        # 更新执行模式可见性
        self._update_execution_mode_visibility()

        # 工具 修复：绑定窗口时不自动激活窗口，避免干扰用户操作
        # 注释掉自动激活逻辑，只在实际执行任务时才激活窗口
        # if hwnd and hwnd != 0:
        #     # 注意：这里需要调用父窗口（MainWindow）的激活方法
        #     if hasattr(self.parent(), '_activate_window_if_needed'):
        #         self.parent()._activate_window_if_needed(hwnd, window_title)

        logger.info(f"靶心 绑定窗口完成，未激活窗口: {window_title} (HWND: {hwnd})")

    def _add_window_silently(self, window_title: str, hwnd: int = 0):
        """静默添加窗口（不显示对话框）"""
        # 检查是否已存在相同的窗口
        for window_info in self.bound_windows:
            existing_title = window_info.get('title', '')
            existing_hwnd = window_info.get('hwnd', 0)

            # 如果句柄相同且都不为0，则认为是重复窗口
            if hwnd and hwnd != 0 and existing_hwnd and existing_hwnd != 0 and existing_hwnd == hwnd:
                logger.info(f"跳过重复窗口（句柄相同）: {window_title} (HWND: {hwnd})")
                return

            # 如果标题和句柄都相同，则认为是重复窗口
            if existing_title == window_title and existing_hwnd == hwnd:
                logger.info(f"跳过重复窗口（标题和句柄相同）: {window_title}")
                return

        # 🔧 直接使用原始标题，不进行复杂的唯一化处理
        # 因为重复检测已经通过HWND进行，不需要修改标题

        # 添加新窗口到列表
        new_window = {
            'title': window_title,
            'enabled': True
        }
        if hwnd and hwnd != 0:
            new_window['hwnd'] = hwnd
            # 保存窗口DPI信息
            try:
                new_window['dpi_info'] = self._get_window_dpi_info(hwnd)
            except:
                pass

        self.bound_windows.append(new_window)
        logger.info(f"✅ 成功添加窗口: {window_title} (HWND: {hwnd})")

        # 为新窗口预创建OCR服务
        try:
            self._preregister_window_ocr_service(new_window)
        except:
            pass

        # 检测模拟器类型并验证VM索引（静默模式，不显示弹窗）
        if hwnd:
            try:
                emulator_type = self._detect_emulator_type(hwnd)
                if emulator_type == "mumu":
                    self._verify_mumu_vm_index_silently(hwnd, window_title)
            except:
                pass

        # 自动调整新添加窗口的分辨率
        try:
            self._auto_resize_single_window(new_window)
        except:
            pass

        # 刷新界面
        self._refresh_bound_windows_combo()
        self._update_execution_mode_visibility()

    def _generate_unique_window_title(self, original_title: str, hwnd: int) -> str:
        """为窗口生成唯一的显示标题"""
        try:
            # 如果是MuMu模拟器的nemudisplay窗口，尝试获取VM信息
            if original_title == "nemudisplay":
                from utils.mumu_manager import get_mumu_manager

                mumu_manager = get_mumu_manager()
                if mumu_manager.is_available():
                    vm_info = mumu_manager.get_all_vm_info()

                    # 查找对应的VM
                    for vm_index, vm_data in vm_info.items():
                        vm_hwnd = vm_data.get('hwnd')
                        if vm_hwnd == hwnd:
                            vm_title = vm_data.get('title', f'VM{vm_index}')
                            return f"{vm_title} (nemudisplay)"

                    # 如果没找到对应VM，使用句柄作为标识
                    return f"MuMu设备 (HWND: {hwnd})"

            # 检查是否有相同标题的窗口
            same_title_count = 0
            for window_info in self.bound_windows:
                existing_title = window_info.get('title', '')
                if original_title in existing_title:
                    same_title_count += 1

            # 如果有相同标题的窗口，添加编号
            if same_title_count > 0:
                return f"{original_title} #{same_title_count + 1} (HWND: {hwnd})"
            else:
                return f"{original_title} (HWND: {hwnd})"

        except Exception as e:
            logger.warning(f"生成唯一窗口标题失败: {e}")
            return f"{original_title} (HWND: {hwnd})"

    def _detect_emulator_type(self, hwnd: int) -> str:
        """检测模拟器类型"""
        try:
            from utils.emulator_detector import EmulatorDetector
            detector = EmulatorDetector()
            is_emulator, emulator_type, _ = detector.detect_emulator_type(hwnd)
            if is_emulator:
                logger.debug(f"检测到模拟器类型: {emulator_type} (HWND: {hwnd})")
                return emulator_type
            else:
                logger.debug(f"未检测到模拟器类型 (HWND: {hwnd})")
                return "unknown"
        except Exception as e:
            logger.warning(f"检测模拟器类型失败: {e}")
            return "unknown"

    def _verify_mumu_vm_index(self, hwnd: int, window_title: str):
        """验证MuMu模拟器的VM索引"""
        try:
            logger.info(f"验证MuMu窗口VM索引: {window_title} (HWND: {hwnd})")

            # 清理MuMu输入模拟器的缓存
            try:
                from utils.mumu_input_simulator import get_mumu_input_simulator
                mumu_simulator = get_mumu_input_simulator()
                mumu_simulator.clear_cache()
                logger.info("已清理MuMu输入模拟器缓存")
            except Exception as e:
                logger.warning(f"清理MuMu输入模拟器缓存失败: {e}")

            # 验证VM索引
            try:
                from utils.mumu_input_simulator import get_mumu_input_simulator
                mumu_simulator = get_mumu_input_simulator()
                vm_index = mumu_simulator.get_vm_index_from_hwnd(hwnd)

                if vm_index is not None:
                    logger.info(f"✅ MuMu窗口VM索引验证成功: {window_title} -> VM{vm_index}")
                else:
                    logger.warning(f"❌ MuMu窗口VM索引验证失败: {window_title}")

            except Exception as e:
                logger.error(f"验证MuMu窗口VM索引时出错: {e}")

        except Exception as e:
            logger.error(f"验证MuMu VM索引失败: {e}")

        # 检测模拟器类型并提示用户
        try:
            from utils.emulator_detector import EmulatorDetector
            detector = EmulatorDetector()
            is_emulator, emulator_type, _ = detector.detect_emulator_type(hwnd)

            if is_emulator and emulator_type == "mumu":
                logger.info(f"检测到MuMu模拟器，分辨率调整将在全局设置确定时进行")
        except:
            pass

        if hwnd and hwnd != 0:
            QMessageBox.information(self, "成功", f"已添加窗口: {window_title} (句柄: {hwnd})")
        else:
            QMessageBox.information(self, "成功", f"已添加窗口: {window_title}")

    def _verify_mumu_vm_index_silently(self, hwnd: int, window_title: str):
        """静默验证MuMu模拟器的VM索引（不显示弹窗）"""
        try:
            logger.info(f"静默验证MuMu窗口VM索引: {window_title} (HWND: {hwnd})")

            # 清理MuMu输入模拟器的缓存
            try:
                from utils.mumu_input_simulator import get_mumu_input_simulator
                mumu_simulator = get_mumu_input_simulator()
                mumu_simulator.clear_cache()
                logger.info("已清理MuMu输入模拟器缓存")
            except Exception as e:
                logger.warning(f"清理MuMu输入模拟器缓存失败: {e}")

            # 验证VM索引
            try:
                from utils.mumu_input_simulator import get_mumu_input_simulator
                mumu_simulator = get_mumu_input_simulator()
                vm_index = mumu_simulator.get_vm_index_from_hwnd(hwnd)

                if vm_index is not None:
                    logger.info(f"✅ MuMu窗口VM索引验证成功: {window_title} -> VM{vm_index}")
                else:
                    logger.warning(f"❌ MuMu窗口VM索引验证失败: {window_title}")

            except Exception as e:
                logger.error(f"验证MuMu窗口VM索引时出错: {e}")

        except Exception as e:
            logger.error(f"静默验证MuMu VM索引失败: {e}")

        # 检测模拟器类型（不显示弹窗）
        try:
            from utils.emulator_detector import EmulatorDetector
            detector = EmulatorDetector()
            is_emulator, emulator_type, _ = detector.detect_emulator_type(hwnd)

            if is_emulator and emulator_type == "mumu":
                logger.info(f"检测到MuMu模拟器，分辨率调整将在全局设置确定时进行")
        except:
            pass

        # 🔧 静默模式：不显示成功弹窗
        logger.info(f"✅ 静默添加窗口完成: {window_title} (HWND: {hwnd})")

    def _preregister_window_ocr_service(self, window_info):
        """为窗口预注册OCR服务"""
        try:
            logger.debug(f"开始为窗口预注册OCR服务: {window_info}")

            from services.multi_ocr_pool import get_multi_ocr_pool

            window_title = window_info['title']
            window_hwnd = window_info.get('hwnd')

            if window_hwnd:
                logger.debug(f"获取多OCR池实例...")
                multi_ocr_pool = get_multi_ocr_pool()

                logger.debug(f"调用预注册方法: {window_title} (HWND: {window_hwnd})")
                success = multi_ocr_pool.preregister_window(window_title, window_hwnd)

                if success:
                    logger.info(f"成功 为窗口预创建OCR服务成功: {window_title} (HWND: {window_hwnd})")
                else:
                    logger.warning(f"警告 为窗口预创建OCR服务失败: {window_title} (HWND: {window_hwnd})")
            else:
                logger.warning(f"窗口无有效句柄，跳过OCR服务预创建: {window_title}")

        except ImportError as e:
            logger.error(f"导入OCR服务模块失败: {e}")
        except Exception as e:
            logger.error(f"预注册OCR服务异常: {e}", exc_info=True)

    def _register_windows_to_handle_manager(self):
        """将绑定的窗口注册到句柄管理器"""
        try:
            from utils.window_handle_manager import get_window_handle_manager
            from utils.emulator_detector import EmulatorDetector

            handle_manager = get_window_handle_manager()
            detector = EmulatorDetector()

            # 启用自动监控，检测窗口句柄变化（如模拟器重启）
            handle_manager.start_monitoring(interval=10.0)  # 每10秒检查一次，避免过于频繁

            # 添加用户通知回调
            handle_manager.add_user_notification_callback(self._handle_window_invalid_notification)

            logger.info("窗口句柄管理器已注册并启动自动监控（间隔10秒）")

            for i, window_info in enumerate(self.bound_windows):
                hwnd = window_info.get('hwnd')
                title = window_info.get('title', '')

                if hwnd and title:
                    # 检测模拟器类型
                    is_emulator, emulator_type, _ = detector.detect_emulator_type(hwnd)
                    vm_index = None

                    # 如果是MuMu模拟器，获取VM索引
                    if is_emulator and emulator_type == "mumu":
                        try:
                            from utils.mumu_resolution_manager import get_mumu_resolution_manager
                            mumu_manager = get_mumu_resolution_manager()
                            vm_index = mumu_manager.get_vm_index_from_hwnd(hwnd)
                        except:
                            pass

                    # 注册窗口
                    key = f"bound_window_{i}"
                    handle_manager.register_window(
                        key=key,
                        hwnd=hwnd,
                        title=title,
                        vm_index=vm_index,
                        emulator_type=emulator_type if is_emulator else None
                    )

                    # 添加更新回调
                    handle_manager.add_update_callback(
                        key,
                        lambda old_hwnd, new_hwnd, idx=i: self._handle_window_hwnd_update(idx, old_hwnd, new_hwnd)
                    )

                    logger.info(f"注册窗口到句柄管理器: {title} (HWND: {hwnd})")

        except Exception as e:
            logger.error(f"注册窗口到句柄管理器失败: {e}")

    def _handle_window_hwnd_update(self, window_index: int, old_hwnd: int, new_hwnd: int):
        """处理窗口句柄更新 - 使用Qt信号确保线程安全"""
        try:
            # 使用QTimer.singleShot确保在主线程中执行UI更新
            from PySide6.QtCore import QTimer

            def update_in_main_thread():
                try:
                    if window_index < len(self.bound_windows):
                        window_info = self.bound_windows[window_index]
                        old_title = window_info.get('title', '')

                        # 更新句柄
                        window_info['hwnd'] = new_hwnd

                        logger.info(f"窗口句柄已更新: {old_title} -> {old_hwnd} => {new_hwnd}")

                        # 刷新界面显示 - 在主线程中安全执行
                        if hasattr(self, '_refresh_bound_windows_combo'):
                            self._refresh_bound_windows_combo()

                        # 使用状态栏通知，避免阻塞
                        if hasattr(self, 'status_bar') and self.status_bar:
                            self.status_bar.showMessage(f"窗口句柄已更新: {old_title}", 3000)

                        logger.info(f"窗口句柄更新完成: {old_title} ({old_hwnd} => {new_hwnd})")

                except Exception as e:
                    logger.error(f"主线程中处理窗口句柄更新失败: {e}")

            # 使用QTimer.singleShot在主线程中执行更新
            QTimer.singleShot(0, update_in_main_thread)

        except Exception as e:
            logger.error(f"处理窗口句柄更新失败: {e}")

    def _handle_window_invalid_notification(self, key: str, window_info):
        """处理窗口句柄失效通知"""
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QMessageBox

            def show_notification_in_main_thread():
                try:
                    window_title = window_info.title if hasattr(window_info, 'title') else '未知窗口'

                    # 显示状态栏消息
                    if hasattr(self, 'status_bar') and self.status_bar:
                        self.status_bar.showMessage(f"⚠️ 窗口句柄失效: {window_title}，请重新绑定", 10000)

                    # 显示弹窗通知（可选，避免过于打扰用户）
                    # reply = QMessageBox.warning(
                    #     self,
                    #     "窗口句柄失效",
                    #     f"检测到窗口 '{window_title}' 的句柄已失效。\n\n"
                    #     f"这通常是因为模拟器重启或窗口关闭导致的。\n"
                    #     f"请重新绑定窗口以继续使用工作流功能。",
                    #     QMessageBox.StandardButton.Ok
                    # )

                    logger.warning(f"🔔 用户通知: 窗口 '{window_title}' 句柄失效，需要重新绑定")

                except Exception as e:
                    logger.error(f"显示窗口失效通知失败: {e}")

            # 使用QTimer.singleShot确保在主线程中执行UI更新
            QTimer.singleShot(0, show_notification_in_main_thread)

        except Exception as e:
            logger.error(f"处理窗口失效通知失败: {e}")

    def _check_and_update_window_handles(self):
        """手动检查并更新窗口句柄 - 在任务执行前调用"""
        try:
            from utils.window_handle_manager import get_window_handle_manager
            handle_manager = get_window_handle_manager()

            # 手动检查所有注册的窗口
            for i, window_info in enumerate(self.bound_windows):
                key = f"bound_window_{i}"
                old_hwnd = window_info.get('hwnd')

                if old_hwnd:
                    # 检查窗口是否仍然有效
                    new_hwnd = handle_manager.get_current_hwnd(key)
                    if new_hwnd and new_hwnd != old_hwnd:
                        logger.info(f"检测到窗口句柄变化: {window_info.get('title')} -> {old_hwnd} => {new_hwnd}")
                        # 直接更新，不触发回调避免UI阻塞
                        window_info['hwnd'] = new_hwnd

        except Exception as e:
            logger.error(f"手动检查窗口句柄失败: {e}")

        # 🔧 新增：检查绑定的模拟器窗口是否完全初始化
        self._check_emulator_initialization()

    def _check_emulator_initialization(self):
        """检查绑定的模拟器窗口是否完全初始化，如果未初始化则等待"""
        try:
            from utils.emulator_detector import detect_emulator_type
            from utils.mumu_manager import get_mumu_manager
            from utils.ldplayer_manager import get_ldplayer_manager
            import time

            logger.info("🔍 检查绑定窗口的模拟器初始化状态...")

            # 检查所有启用的窗口
            enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]

            for window_info in enabled_windows:
                window_title = window_info.get('title', '')
                window_hwnd = window_info.get('hwnd')

                if not window_hwnd:
                    continue

                # 检测窗口是否为模拟器
                is_emulator, emulator_type, description = detect_emulator_type(window_hwnd)

                if not is_emulator or emulator_type == 'unknown':
                    logger.debug(f"窗口 '{window_title}' 不是已知的模拟器，跳过初始化检查")
                    continue

                logger.info(f"🎯 检测到{emulator_type}模拟器窗口: {window_title} ({description})")

                # 根据模拟器类型检查初始化状态
                if emulator_type == 'mumu':
                    self._wait_for_mumu_initialization(window_title, window_hwnd)
                elif emulator_type == 'ldplayer':
                    self._wait_for_ldplayer_initialization(window_title, window_hwnd)

        except Exception as e:
            logger.error(f"检查模拟器初始化状态失败: {e}")
            # 不阻止任务执行，只记录错误

    def _wait_for_mumu_initialization(self, window_title: str, window_hwnd: int):
        """等待MuMu模拟器完全初始化"""
        try:
            from utils.mumu_manager import get_mumu_manager
            import time

            logger.info(f"⏳ 等待MuMu模拟器初始化完成: {window_title}")

            mumu_manager = get_mumu_manager()
            if not mumu_manager.is_available():
                logger.warning("MuMu管理器不可用，跳过初始化检查")
                return

            # 获取所有VM信息
            vm_info = mumu_manager.get_all_vm_info()
            if not vm_info:
                logger.warning("无法获取MuMu VM信息，跳过初始化检查")
                return

            # 查找对应的VM
            target_vm = None
            for vm_index, vm_data in vm_info.items():
                vm_title = vm_data.get('title', '')
                if window_title in vm_title or vm_title in window_title:
                    target_vm = vm_data
                    break

            if not target_vm:
                logger.warning(f"未找到对应的MuMu VM: {window_title}")
                return

            # 检查初始化状态
            max_wait_time = 60  # 最大等待60秒
            check_interval = 2  # 每2秒检查一次
            waited_time = 0

            while waited_time < max_wait_time:
                # 重新获取VM状态
                current_vm_info = mumu_manager.get_all_vm_info()
                if current_vm_info:
                    for vm_index, vm_data in current_vm_info.items():
                        vm_title = vm_data.get('title', '')
                        if window_title in vm_title or vm_title in window_title:
                            player_state = vm_data.get('player_state', 'unknown')
                            is_android_started = vm_data.get('is_android_started', False)

                            logger.info(f"📊 MuMu状态检查: {window_title} -> 状态={player_state}, Android启动={is_android_started}")

                            if player_state == 'start_finished' and is_android_started:
                                logger.info(f"✅ MuMu模拟器初始化完成: {window_title}")
                                return
                            break

                # 显示等待进度
                logger.info(f"⏳ 等待MuMu初始化... ({waited_time}/{max_wait_time}秒)")
                time.sleep(check_interval)
                waited_time += check_interval

            logger.warning(f"⚠️ MuMu模拟器初始化等待超时: {window_title}")

        except Exception as e:
            logger.error(f"等待MuMu初始化失败: {e}")

    def _wait_for_ldplayer_initialization(self, window_title: str, window_hwnd: int):
        """等待雷电模拟器完全初始化"""
        try:
            from utils.ldplayer_manager import get_ldplayer_manager
            import time

            logger.info(f"⏳ 等待雷电模拟器初始化完成: {window_title}")

            ldplayer_manager = get_ldplayer_manager()
            if not ldplayer_manager.is_available():
                logger.warning("雷电管理器不可用，跳过初始化检查")
                return

            # 检查初始化状态
            max_wait_time = 60  # 最大等待60秒
            check_interval = 2  # 每2秒检查一次
            waited_time = 0

            while waited_time < max_wait_time:
                # 检查雷电模拟器状态（这里需要根据实际的雷电管理器API调整）
                # 暂时使用简单的窗口存在检查
                import win32gui

                if win32gui.IsWindow(window_hwnd) and win32gui.IsWindowVisible(window_hwnd):
                    logger.info(f"✅ 雷电模拟器窗口可见: {window_title}")
                    # 额外等待几秒确保Android系统完全启动
                    time.sleep(5)
                    logger.info(f"✅ 雷电模拟器初始化完成: {window_title}")
                    return

                # 显示等待进度
                logger.info(f"⏳ 等待雷电初始化... ({waited_time}/{max_wait_time}秒)")
                time.sleep(check_interval)
                waited_time += check_interval

            logger.warning(f"⚠️ 雷电模拟器初始化等待超时: {window_title}")

        except Exception as e:
            logger.error(f"等待雷电初始化失败: {e}")

    def _unregister_window_ocr_service(self, window_info):
        """注销窗口的OCR服务"""
        try:
            from services.multi_ocr_pool import get_multi_ocr_pool

            window_title = window_info['title']
            window_hwnd = window_info.get('hwnd')

            if window_hwnd:
                multi_ocr_pool = get_multi_ocr_pool()
                success = multi_ocr_pool.unregister_window(window_hwnd)

                if success:
                    logger.info(f"成功 注销窗口OCR服务成功: {window_title} (HWND: {window_hwnd})")
                else:
                    logger.debug(f"窗口无对应OCR服务: {window_title} (HWND: {window_hwnd})")
            else:
                logger.warning(f"窗口无有效句柄，跳过OCR服务注销: {window_title}")

        except Exception as e:
            logger.error(f"注销OCR服务异常: {e}")

    def _remove_selected_window(self):
        """移除选中的窗口"""
        current_index = self.bound_windows_combo.currentIndex()
        if current_index < 0 or current_index >= len(self.bound_windows):
            QMessageBox.information(self, "提示", "请先选择要移除的窗口")
            return

        window_info = self.bound_windows[current_index]
        window_title = window_info['title']
        hwnd = window_info.get('hwnd', 0)

        reply = QMessageBox.question(
            self, "确认移除",
            f"确定要移除窗口 '{window_title}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 注销窗口的OCR服务
            self._unregister_window_ocr_service(window_info)

            self.bound_windows.pop(current_index)
            self._refresh_bound_windows_combo()
            # 更新执行模式可见性
            self._update_execution_mode_visibility()
            QMessageBox.information(self, "成功", f"已移除窗口: {window_title}")

    # 添加兼容方法，对应open_global_settings调用
    def get_target_window_title(self):
        """获取目标窗口标题"""
        if self.window_binding_mode == 'single':
            return self.title_edit.text() or None
        else:
            # 多窗口模式返回None，使用get_bound_windows获取窗口列表
            return None

    def get_execution_mode(self):
        """获取执行模式"""
        selected_display_mode = self.mode_combo.currentText()
        return self.MODE_INTERNAL_MAP.get(selected_display_mode, 'foreground')

    def get_custom_width(self):
        """获取自定义宽度"""
        return self.width_spinbox.value()

    def get_custom_height(self):
        """获取自定义高度"""
        return self.height_spinbox.value()

    def get_window_binding_mode(self):
        """获取窗口绑定模式"""
        return self.window_binding_mode

    def get_bound_windows(self):
        """获取绑定的窗口列表"""
        return self.bound_windows.copy()

    def get_multi_window_delay(self):
        """获取多窗口启动延迟"""
        return self.multi_window_delay

    def _check_and_cleanup_closed_windows(self):
        """检查并清理已关闭的窗口（已禁用自动检测）"""
        # 自动检测已禁用，因为雷电模拟器的窗口关闭机制特殊
        # 所有常规检测方法都无法准确判断窗口是否真正关闭
        logger.debug("自动窗口检测已禁用，需要手动清理无效窗口")

    def _enum_windows_callback(self, hwnd, results_list: list):
        """Callback function for EnumWindows - 过滤掉模拟器主窗口"""
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                # 过滤掉模拟器主窗口
                try:
                    from utils.emulator_detector import EmulatorDetector
                    detector = EmulatorDetector()
                    if not detector.is_main_window(hwnd):
                        results_list.append(title)
                except:
                    # 如果检测失败，仍然添加窗口
                    results_list.append(title)
        return True # Continue enumeration

    # 删除不再需要的单窗口相关方法

    # 删除不再需要的_get_child_windows方法

    def _enumerate_child_windows(self):
        """枚举雷电模拟器渲染窗口"""
        child_windows = []

        def enum_windows_proc(hwnd, lParam):
            try:
                # 获取窗口标题
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                else:
                    title = ""

                # 获取窗口类名
                class_buffer = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, class_buffer, 256)
                class_name = class_buffer.value

                # 检查窗口是否可见
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    # 只显示雷电模拟器的渲染窗口
                    if class_name == "RenderWindow":
                        display_title = title or "TheRender"
                        child_windows.append((hwnd, display_title, class_name))

                    # 同时枚举这个窗口的子窗口，查找渲染窗口
                    self._enum_child_windows_recursive(hwnd, child_windows)

            except Exception as e:
                print(f"枚举窗口时出错: {e}")

            return True  # 继续枚举

        # 定义回调函数类型
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        enum_callback = EnumWindowsProc(enum_windows_proc)

        # 枚举所有顶级窗口
        ctypes.windll.user32.EnumWindows(enum_callback, 0)

        return child_windows

    def _enum_child_windows_recursive(self, parent_hwnd, child_windows):
        """递归枚举指定窗口的子窗口，只查找雷电模拟器渲染窗口"""
        def enum_child_proc(hwnd, lParam):
            try:
                # 获取窗口标题
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value
                else:
                    title = ""

                # 获取窗口类名
                class_buffer = ctypes.create_unicode_buffer(256)
                ctypes.windll.user32.GetClassNameW(hwnd, class_buffer, 256)
                class_name = class_buffer.value

                # 检查窗口是否可见，并且只添加雷电模拟器渲染窗口
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    if class_name == "RenderWindow":
                        display_title = title or "TheRender"
                        child_windows.append((hwnd, display_title, class_name))

            except Exception as e:
                print(f"枚举子窗口时出错: {e}")

            return True  # 继续枚举

        # 定义回调函数类型
        EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        enum_child_callback = EnumChildProc(enum_child_proc)

        # 枚举指定窗口的子窗口
        ctypes.windll.user32.EnumChildWindows(parent_hwnd, enum_child_callback, 0)

    def get_settings(self) -> dict:
        """Returns the edited settings as a dictionary."""
        # 获取用户选择的执行模式（保留完整的模式标识）
        selected_display_mode = self.mode_combo.currentText()
        internal_mode = self.MODE_INTERNAL_MAP.get(selected_display_mode, 'foreground_driver')

        # 根据绑定窗口数量决定窗口绑定模式
        window_count = len(self.bound_windows)
        window_binding_mode = 'multiple' if window_count > 1 else 'single'

        # 获取主题设置
        theme_text = self.theme_combo.currentText()
        if theme_text == "明亮模式":
            theme_mode = 'light'
        else:
            theme_mode = 'dark'

        settings = {
            'execution_mode': internal_mode,
            'operation_mode': 'auto',  # 默认使用自动检测
            'custom_width': self.width_spinbox.value(),
            'custom_height': self.height_spinbox.value(),
            'window_binding_mode': window_binding_mode,
            'bound_windows': self.get_bound_windows(),
            'multi_window_delay': self.multi_window_delay,
            # 快捷键设置
            'start_task_hotkey': self.start_task_hotkey.text().strip() or 'F9',
            'stop_task_hotkey': self.stop_task_hotkey.text().strip() or 'F10',
            'record_hotkey': self.record_hotkey.text().strip() or 'F12',
            # 主题设置
            'theme': theme_mode
        }

        # 根据窗口数量设置target_window_title
        if window_count == 1:
            # 单窗口：使用第一个绑定窗口的标题
            settings['target_window_title'] = self.bound_windows[0]['title']
        else:
            # 多窗口或无窗口：不设置target_window_title
            settings['target_window_title'] = None

        return settings

    def _find_window_handle(self, window_title: str):
        """查找窗口句柄（智能处理多个相同标题的窗口）"""
        try:
            from utils.window_finder import WindowFinder

            # 处理带有类型标注的窗口标题（如 "窗口名 [雷电模拟器]"）
            clean_title = window_title
            if '[' in window_title and ']' in window_title:
                # 提取原始窗口标题
                clean_title = window_title.split('[')[0].strip()

            # 检测模拟器类型
            emulator_type = None
            if clean_title == "TheRender" or "雷电" in window_title or "LDPlayer" in window_title:
                emulator_type = "ldplayer"
            elif clean_title == "nemudisplay" or "MuMu" in window_title:
                emulator_type = "mumu"

            # 如果是TheRender，需要智能选择未绑定的窗口
            if clean_title == "TheRender":
                logger.info("开始智能查找TheRender窗口...")

                # 获取所有TheRender窗口
                all_windows = WindowFinder.find_all_windows(clean_title, emulator_type)
                logger.info(f"找到 {len(all_windows)} 个TheRender窗口: {all_windows}")

                if not all_windows:
                    logger.warning("未找到任何TheRender窗口")
                    return None

                # 获取已绑定的窗口句柄
                bound_hwnds = set()
                for window_info in self.bound_windows:
                    hwnd = window_info.get('hwnd')
                    if hwnd and hwnd != 0:  # 确保句柄有效
                        bound_hwnds.add(hwnd)
                        logger.info(f"已绑定窗口句柄: {hwnd}")

                logger.info(f"已绑定的句柄集合: {bound_hwnds}")

                # 查找第一个未绑定的窗口
                for hwnd in all_windows:
                    if hwnd not in bound_hwnds:
                        logger.info(f"找到未绑定的TheRender窗口: {hwnd}")
                        return hwnd

                # 如果所有窗口都已绑定，返回特殊值表示已全部绑定
                logger.warning("所有TheRender窗口都已绑定")
                return "ALL_BOUND"

            # 如果是nemudisplay，需要智能选择未绑定的MuMu窗口
            elif clean_title == "nemudisplay":
                logger.info("开始智能查找nemudisplay窗口...")

                # 使用特殊的MuMu窗口查找逻辑
                all_windows = self._find_all_mumu_windows()
                logger.info(f"找到 {len(all_windows)} 个nemudisplay窗口: {all_windows}")

                if not all_windows:
                    logger.warning("未找到任何nemudisplay窗口")
                    return None

                # 获取已绑定的窗口句柄
                bound_hwnds = set()
                for window_info in self.bound_windows:
                    hwnd = window_info.get('hwnd')
                    if hwnd and hwnd != 0:  # 确保句柄有效
                        bound_hwnds.add(hwnd)
                        logger.info(f"已绑定窗口句柄: {hwnd}")

                logger.info(f"已绑定的句柄集合: {bound_hwnds}")

                # 查找第一个未绑定的窗口
                for hwnd in all_windows:
                    if hwnd not in bound_hwnds:
                        logger.info(f"找到未绑定的nemudisplay窗口: {hwnd}")
                        return hwnd

                # 如果所有窗口都已绑定，返回特殊值表示已全部绑定
                logger.warning("所有nemudisplay窗口都已绑定")
                return "ALL_BOUND"
            else:
                # 对于其他窗口，使用原有逻辑，使用清理后的标题
                return WindowFinder.find_window(clean_title, emulator_type)

        except ImportError:
            logger.warning("无法导入窗口查找工具")
            return None
        except Exception as e:
            logger.error(f"查找窗口句柄失败: {e}")
            return None

    def _get_window_dpi_info(self, hwnd: int) -> dict:
        """获取窗口DPI信息并保存到配置"""
        try:
            from utils.unified_dpi_handler import get_unified_dpi_handler
            dpi_handler = get_unified_dpi_handler()
            dpi_info = dpi_handler.get_window_dpi_info(hwnd, check_changes=False)

            # 只保存必要的DPI信息到配置文件
            saved_dpi_info = {
                'dpi': dpi_info.get('dpi', 96),
                'scale_factor': dpi_info.get('scale_factor', 1.0),
                'method': dpi_info.get('method', 'Default'),
                'recorded_at': time.time()  # 记录时间戳
            }

            return saved_dpi_info

        except Exception as e:
            # 返回默认DPI信息
            return {
                'dpi': 96,
                'scale_factor': 1.0,
                'method': 'Default',
                'recorded_at': time.time()
            }

class MainWindow(QMainWindow):
    """Main application window with custom title bar and custom-painted rounded corners."""

    # 自定义信号：用于从 keyboard 回调线程安全地触发任务操作
    hotkey_start_signal = Signal()
    hotkey_stop_signal = Signal()

    # Accept task_modules, initial_config, save_config_func, images_dir, and state managers in constructor
    def __init__(self, task_modules: Dict[str, Any], initial_config: dict, save_config_func, images_dir: str, task_state_manager=None):
        super().__init__()

        # 确保背景色正确应用（支持主题系统）
        self.setAutoFillBackground(True)

        self.task_modules = task_modules # Store the task modules
        self.save_config_func = save_config_func # Store the save function

        self.images_dir = images_dir # <<< RE-ADDED: Store images directory
        self.current_save_path = None # Store path for potential future "Save" without dialog
        # --- MOVED: Initialize unsaved_changes early --- 
        self.unsaved_changes = False 
        # ---------------------------------------------
        self.executor_thread: Optional[QThread] = None # Thread for execution
        self.executor: Optional[WorkflowExecutor] = None # Executor instance
        self.config = copy.deepcopy(initial_config) # Store initial config
        self.current_target_window_title = self.config.get('target_window_title') # Load from config
        self.current_execution_mode = self.config.get('execution_mode', 'foreground') # Load from config
        # Store custom resolution from config
        self.custom_width = self.config.get('custom_width', 0)
        self.custom_height = self.config.get('custom_height', 0)

        # 新增的窗口绑定配置
        self.window_binding_mode = self.config.get('window_binding_mode', 'single')
        self.bound_windows = self.config.get('bound_windows', [])
        self.multi_window_delay = self.config.get('multi_window_delay', 500)

        # 操作模式配置 - 默认使用自动检测
        self.operation_mode = 'auto'

        # 应用操作模式设置到全局输入模拟器管理器
        try:
            from utils.backend_modes import backend_manager
            backend_manager.set_global_operation_mode(self.operation_mode)
            backend_manager.set_global_execution_mode(self.current_execution_mode)
        except ImportError:
            logging.warning("无法导入backend_manager，操作模式设置未应用")

        # 快捷键配置
        self.start_task_hotkey = self.config.get('start_task_hotkey', 'F9')
        self.stop_task_hotkey = self.config.get('stop_task_hotkey', 'F10')
        self.record_hotkey = self.config.get('record_hotkey', 'F12')
        
        # --- ADDED: Store state management systems ---
        self.task_state_manager = task_state_manager
        # 安全操作管理器已移除
        # ---------------------------------------------
        
        # --- ADDED: Store failed paths during execution ---
        self.failed_paths: List[Tuple[int, str]] = []
        # --------------------------------------------------

        # --- ADDED: Initialize stop task related state variables ---
        self._stop_request_in_progress = False  # 防止重复停止请求
        self._execution_finished_processed = False  # 防止重复处理执行完成事件
        self._execution_started_flag = False  # 标记任务是否已启动
        # ----------------------------------------------------------

        # --- ADDED: Parameter panel state ---
        self._parameter_panel_visible = False
        
        # --- Initial Window Setup ---
        self.setGeometry(100, 100, 1000, 700) # Slightly larger window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 确保主窗口能够接收键盘事件（特别是 F10）
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
                
        # 使用全局主题管理器（已在 main.py 中初始化）
        self.theme_manager = QApplication.instance().theme_manager
                
        # 从配置加载主题并应用
        saved_theme = self.config.get('theme', 'system')
        self.theme_manager.set_theme(saved_theme)
        logging.info(f"MainWindow 应用主题：{saved_theme}")
                
        self.setAttribute(Qt.WidgetAttribute.WA_KeyCompression, False)  # 禁用按键压缩，确保所有按键事件都被处理

        # 🔧 多任务系统初始化 ---
        from .workflow_task_manager import WorkflowTaskManager
        from .workflow_tab_widget import WorkflowTabWidget
        from .task_execution_panel import TaskExecutionPanel

        # 创建任务管理器
        self.task_manager = WorkflowTaskManager(
            task_modules=self.task_modules,
            images_dir=self.images_dir,
            config=self.config,
            parent=self
        )

        # 🔧 连接任务管理器信号，用于更新工具栏按钮状态
        self.task_manager.task_status_changed.connect(self._on_task_status_changed)
        self.task_manager.all_tasks_completed.connect(self._on_all_tasks_completed)

        # 创建标签页控件（替代原来的单个workflow_view）
        self.workflow_tab_widget = WorkflowTabWidget(
            task_manager=self.task_manager,
            task_modules=self.task_modules,
            images_dir=self.images_dir,
            parent=self
        )

        # 兼容性：保留workflow_view引用（指向当前选中的WorkflowView）
        self.workflow_view = None  # 将在标签页切换时更新

        # 创建任务执行控制面板
        self.execution_panel = TaskExecutionPanel(
            task_manager=self.task_manager,
            parent=self
        )
        # 🔧 初始状态：没有任务时隐藏执行面板
        self.execution_panel.setVisible(False)
        # 🔧 多任务系统初始化完成 ---

        # --- ADDED: Initialize parameter panel ---
        self.parameter_panel = ParameterPanel(parent=self)
        self.parameter_panel.parameters_changed.connect(self._on_parameter_changed)
        self.parameter_panel.panel_closed.connect(self._on_parameter_panel_closed)

        # --- MOVED: Create actions AFTER workflow_view exists ---
        self._create_actions()
        # ------------------------------------------------------

        # 🔧 连接标签页切换信号，更新workflow_view引用
        self.workflow_tab_widget.current_workflow_changed.connect(self._on_current_workflow_changed)

        # 🔧 连接任务管理器信号，控制UI显示/隐藏
        self.task_manager.task_added.connect(self._on_task_count_changed)
        self.task_manager.task_removed.connect(self._on_task_count_changed)
        self.task_manager.task_added.connect(self._on_task_added_for_jump)  # 连接任务的跳转信号

        # 🔧 连接执行控制面板信号
        self.execution_panel.start_current_requested.connect(self._start_current_task)
        self.execution_panel.stop_current_requested.connect(self._stop_current_task)
        self.execution_panel.start_all_requested.connect(self._start_all_tasks)
        self.execution_panel.stop_all_requested.connect(self._stop_all_tasks)
        self.execution_panel.execution_mode_changed.connect(self._on_execution_mode_changed)

        # Central Widget setup 
        self.central_container = QWidget(self) 
        self.main_layout = QVBoxLayout(self.central_container) 
        self.main_layout.setContentsMargins(0, 0, 0, 0) 
        self.main_layout.setSpacing(0)
        
        # --- Custom Title Bar ---
        # Create the list of actions AFTER _create_actions has run
        title_bar_actions = [self.toggle_action, self.save_action, self.load_action, self.new_workflow_action, self.run_action, self.debug_run_action, self.global_settings_action]
        self.title_bar = CustomTitleBar(self, actions=title_bar_actions)
        self.main_layout.addWidget(self.title_bar)
        self.title_bar.set_file_actions_visible(self.file_actions_visible)
        
        # 初始化工具栏（注释代码已移除）

        # --- Add DPI Notification Widget ---
        from .dpi_notification_widget import DPINotificationWidget, get_dpi_detector
        self.dpi_notification = DPINotificationWidget(self)
        self.dpi_notification.hide()  # 初始隐藏
        self.dpi_notification.recalibrate_requested.connect(self._handle_dpi_recalibration)
        self.dpi_notification.dismiss_requested.connect(self._handle_dpi_dismiss)
        self.dpi_notification.auto_adjust_requested.connect(self._handle_dpi_auto_adjust)
        self.main_layout.addWidget(self.dpi_notification)

        # 设置统一DPI处理器和变化检测
        self._setup_dpi_monitoring()

        # 🔧 添加标签页控件（替代原来的单个workflow_view）
        self.main_layout.addWidget(self.workflow_tab_widget)

        # <<< ADDED: Prevent child widgets from filling background over rounded corners >>>
        self.central_container.setAutoFillBackground(False)
        self.workflow_tab_widget.setAutoFillBackground(False)
        # -----------------------------------------------------------------------------

        # 🔧 添加任务执行控制面板
        self.main_layout.addWidget(self.execution_panel)

        # --- ADDED: Step Detail Label --- 
        self.step_detail_label = QLabel("等待执行...")
        self.step_detail_label.setObjectName("stepDetailLabel")
        self.step_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Set maximum height to prevent it from becoming too large
        self.step_detail_label.setMaximumHeight(50) 
        # Apply basic styling (can be enhanced in global stylesheet)
        self.step_detail_label.setStyleSheet("""
            #stepDetailLabel {
                background-color: rgba(180, 180, 180, 180); /* Medium-light gray, semi-transparent */
                color: white;
                padding: 8px;
                border-radius: 5px; /* Rounded corners */
                font-size: 9pt;
                border: none; /* Ensure no border */
            }
        """)
        # Hide initially or set placeholder text
        # self.step_detail_label.setVisible(False) 
        self.main_layout.addWidget(self.step_detail_label)
        # --- END ADDED --- 

        self.setCentralWidget(self.central_container) # Set the container as central widget

        # --- ADDED: Connect task card parameter editing to parameter panel ---
        self._connect_parameter_panel_signals()

        # Set initial window title including target
        self._update_main_window_title()
        
        # --- Apply Initial Window Resize (if configured) ---
        self._apply_initial_window_resize()
        # -----------------------------------------------------

        # --- Start DPI Monitoring ---
        self.start_dpi_monitoring()
        # ----------------------------

        # --- 连接快捷键信号到槽函数 ---
        # keyboard 回调通过发射信号，确保在主线程执行
        self.hotkey_start_signal.connect(self.safe_start_tasks)
        self.hotkey_stop_signal.connect(self.safe_stop_tasks)
        logger.info("快捷键信号已连接到安全执行方法")
        # ----------------------------

        # --- 设置全局快捷键 ---
        self._update_hotkeys()
        # ---------------------

        # 🔧 检查是否需要等待ADB初始化
        # 使用QTimer延迟执行，确保窗口完全初始化后再检查
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self.check_emulator_windows_and_enable_button)

        # 🔧 首次启动提示：显示多任务系统使用提示
        QTimer.singleShot(500, self._show_welcome_hint)

    def _update_main_window_title(self):
        """Updates the main window title to include the target window and unsaved status."""
        base_title = "自动化工作流"

        # 根据窗口绑定模式显示不同的目标信息
        if hasattr(self, 'window_binding_mode') and self.window_binding_mode == 'multiple':
            # 多窗口模式
            if hasattr(self, 'bound_windows') and self.bound_windows:
                enabled_count = sum(1 for w in self.bound_windows if w.get('enabled', True))
                total_count = len(self.bound_windows)
                target_info = f" [多窗口: {enabled_count}/{total_count}]"
            else:
                target_info = " [多窗口: 未绑定]"
        else:
            # 单窗口模式
            target_info = f" [目标: {self.current_target_window_title}]" if self.current_target_window_title else " [未绑定窗口]"

        file_info = f" - {os.path.basename(self.current_save_path)}" if self.current_save_path else ""
        # --- ADDED: Unsaved changes indicator ---
        unsaved_indicator = " (*)" if self.unsaved_changes and self.current_save_path else ""
        # ----------------------------------------
        full_title = base_title + target_info + file_info + unsaved_indicator # Add indicator

        # 使用统一的setWindowTitle方法，会自动处理长度限制
        self.setWindowTitle(full_title)

    def _create_actions(self):
        """Creates all QAction instances."""
        self.file_actions_visible = True # Initial state for toggled actions
        style = self.style() # Get style to access standard icons

        # --- Toggle Action (Icon + Text) --- 
        # Use the original '>>' icon again, or another like SP_FileDialogDetailedView
        toggle_icon = style.standardIcon(QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton) 
        self.toggle_action = QAction(toggle_icon, "选项", self) # Add icon back
        self.toggle_action.setToolTip("显示/隐藏功能按钮") 
        self.toggle_action.triggered.connect(self.toggle_file_actions_visibility) 
        
        # --- Save Action (Icon + Text) --- 
        save_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.save_action = QAction(save_icon, "保存配置", self) 
        self.save_action.setToolTip("保存当前工作流配置 (Ctrl+S)") # Added shortcut hint
        self.save_action.setShortcut("Ctrl+S") # Added shortcut
        self.save_action.triggered.connect(self._handle_save_action) # <<< CORRECTED connection to handler
        self.save_action.setVisible(self.file_actions_visible) 

        # --- Load Action (Icon + Text) ---
        load_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        self.load_action = QAction(load_icon, "加载配置", self)
        self.load_action.setToolTip("从文件加载工作流配置")
        self.load_action.triggered.connect(self.load_workflow)
        self.load_action.setVisible(self.file_actions_visible)

        # --- New Blank Workflow Action (Icon + Text) ---
        new_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        self.new_workflow_action = QAction(new_icon, "新建工作流", self)
        self.new_workflow_action.setToolTip("创建空白工作流 (Ctrl+N)")
        self.new_workflow_action.setShortcut("Ctrl+N")
        self.new_workflow_action.triggered.connect(self.create_blank_workflow)
        self.new_workflow_action.setVisible(self.file_actions_visible)

        # --- Run Workflow Action (Icon + Text) ---
        run_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay) # Play icon
        self.run_action = QAction(run_icon, "检查中...", self)
        self.run_action.setToolTip("正在检查是否需要初始化ADB连接池...")
        self.run_action.triggered.connect(lambda: self.run_workflow())
        # 🔧 初始化时禁用运行按钮，等待检查完成
        self.run_action.setEnabled(False)
        self.run_action.setVisible(True)

        # 初始化状态标志
        self._adb_initialization_completed = False
        self._needs_adb_initialization = True  # 默认需要检查
        # --- Debug Run Action (Icon + Text) ---
        debug_icon = style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon) # Computer icon for control center
        self.debug_run_action = QAction(debug_icon, "调试运行", self)
        self.debug_run_action.setToolTip("启动中控软件进行调试运行")
        self.debug_run_action.triggered.connect(self.open_control_center)
        self.debug_run_action.setVisible(True)

        # --- Global Settings Action ---
        settings_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
        self.global_settings_action = QAction(settings_icon, "全局设置", self)
        self.global_settings_action.setToolTip("配置目标窗口、执行模式和自定义分辨率等全局选项")
        self.global_settings_action.triggered.connect(self.open_global_settings)

        # --- MODIFIED: Connect clear action to a confirmation method ---
        self.clear_action = QAction(QIcon.fromTheme("document-new", self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)), "清空工作流", self)
        self.clear_action.setToolTip("清空当前所有步骤和连接")
        # self.clear_action.triggered.connect(self.workflow_view.clear_scene) # OLD direct connection
        self.clear_action.triggered.connect(self.confirm_and_clear_workflow) # NEW connection
        # --- END MODIFICATION ---

        self.copy_action = QAction(QIcon.fromTheme("edit-copy"), "复制卡片", self)
        self.copy_action.setToolTip("复制选中的卡片")
        # 🔧 动态连接：通过lambda调用当前workflow_view的方法
        self.copy_action.triggered.connect(lambda: self.workflow_view.copy_selected_card() if self.workflow_view else None)

    def toggle_file_actions_visibility(self):
        """Toggles the visibility of Add, Save and Load actions container in the custom title bar."""
        self.file_actions_visible = not self.file_actions_visible

        # Update visibility of QActions themselves (good practice)
        if self.save_action:
            self.save_action.setVisible(self.file_actions_visible)
        if self.load_action:
            self.load_action.setVisible(self.file_actions_visible)
        if hasattr(self, 'new_workflow_action') and self.new_workflow_action:
            self.new_workflow_action.setVisible(self.file_actions_visible)
        # Run action visibility is handled separately (always visible for now)
        # if self.run_action:
        #     self.run_action.setVisible(self.file_actions_visible)

        # Update visibility of the container in the title bar
        if hasattr(self, 'title_bar') and self.title_bar:
             self.title_bar.set_file_actions_visible(self.file_actions_visible)

        print(f"功能按钮可见性设置为: {self.file_actions_visible}")
        # Note: If actions are added as widgets directly, need to show/hide widgets instead.
        # The current CustomTitleBar implementation adds widgets based on actions,
        # so just toggling QAction visibility might not hide the widgets.
        # We may need to adjust CustomTitleBar or this method later.
        # Let's test the current state first.

    # --- ADDED: Handler for Save Action (Moved Earlier) --- 
    def _handle_save_action(self):
        """Handles the save action, deciding whether to save directly or trigger Save As."""
        if self.current_save_path:
            logger.info(f"Save action triggered. Using existing path: {self.current_save_path}")
            self.perform_save(self.current_save_path)
        else:
            logger.info("Save action triggered. No current path, triggering Save As...")
            self.save_workflow_as()
    # --- END ADDED --- 

    def add_new_task_card(self):
        """Prompts the user to select a task type and adds a new card for it."""
        # 🔧 检查是否有当前工作流
        if not self.workflow_view:
            QMessageBox.warning(self, "无法添加", "请先导入或创建一个工作流任务")
            return

        # Import the function to get primary task types for UI display
        from tasks import get_available_tasks
        task_types = get_available_tasks()
        if not task_types:
            QMessageBox.warning(self, "错误", "没有可用的任务类型！")
            return

        task_type, ok = QInputDialog.getItem(self, "选择任务类型",
                                             "请选择要添加的任务类型:", task_types, 0, False)

        if ok and task_type:
            # Add near top-left, let workflow_view generate ID
            center_view = self.workflow_view.mapToScene(self.workflow_view.viewport().rect().center())
            self.workflow_view.add_task_card(center_view.x(), center_view.y(), task_type=task_type)

    def save_workflow_as(self):
        """Saves the current workflow to a new file chosen by the user."""
        default_filename = "workflow.json"
        filepath, filetype = QFileDialog.getSaveFileName(
            self,
            "保存工作流",
            self.current_save_path or default_filename, # Start in last dir or default
            "JSON 文件 (*.json);;所有文件 (*)"
        )

        if not filepath:
            return # User cancelled

        # 保存为普通工作流文件
        self.current_save_path = filepath # Remember path for next time
        self.perform_save(filepath)

    def perform_save(self, filepath: str):
        """Gathers data and writes it to the specified file path."""
        # 🔧 检查是否有当前工作流
        if not self.workflow_view:
            QMessageBox.warning(self, "无法保存", "没有打开的工作流")
            return False

        logger.info(f"Gathering workflow data for saving to {filepath}...")
        try:
            workflow_data = self.workflow_view.serialize_workflow()
        except Exception as e:
            logger.error(f"Error serializing workflow: {e}", exc_info=True)
            self._show_error_message("保存失败", f"序列化工作流时发生错误: {e}")
            return False

        # --- ADDED: Log the data JUST BEFORE writing ---
        logger.debug(f"[SAVE_DEBUG] Data to be written to JSON: {workflow_data}")
        # --- END ADDED ---

        # Write to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(workflow_data, f, indent=4, ensure_ascii=False)
        logger.info(f"工作流已保存到: {filepath}")
        self.setWindowTitle(f"自动化工作流 - {os.path.basename(filepath)}") # Update title
        filename_only = os.path.basename(filepath)
        self._update_step_details(f"任务配置文件 '{filename_only}' 保存成功。")
        self.current_save_path = filepath # Update current save path
        self.unsaved_changes = False
        self._update_main_window_title()

        # --- ADDED: Automatic Backup Logic --- 
        try:
            # --- MODIFIED: Determine backup directory --- 
            # Assume app root is parent of images_dir
            app_root = os.path.dirname(self.images_dir) 
            backup_dir = os.path.join(app_root, "backups")
            os.makedirs(backup_dir, exist_ok=True) # Ensure backup directory exists
            
            # Keep original file info
            original_dir, original_filename = os.path.split(filepath)
            base, ext = os.path.splitext(original_filename)
            # --- END MODIFICATION ---
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # --- MODIFIED: Construct backup path in backup_dir --- 
            # backup_filepath = f"{base}_backup_{timestamp}{ext}" # Old logic
            backup_filename = f"{base}_backup_{timestamp}{ext}"
            backup_filepath = os.path.join(backup_dir, backup_filename)
            # --- END MODIFICATION ---
            
            logger.info(f"尝试创建备份文件: {backup_filepath}")
            with open(backup_filepath, 'w', encoding='utf-8') as backup_f:
                json.dump(workflow_data, backup_f, indent=4, ensure_ascii=False)
        except Exception as backup_e:
            logger.error(f"创建备份文件时发生错误: {backup_e}", exc_info=True)
            # Optionally show a warning to the user?
            # self._show_error_message(\"备份警告\", f\"创建备份文件时出错: {backup_e}\")
        # --- END ADDED ---

        return True

    def load_workflow(self):
        """加载工作流（导入到标签页）"""
        # 使用标签页控件的导入功能
        task_id = self.workflow_tab_widget.import_workflow()

        if task_id is not None:
            logger.info(f"工作流导入成功，任务ID: {task_id}")
            # 不需要设置 unsaved_changes，因为新导入的任务不算未保存
        else:
            logger.info("工作流导入已取消或失败")

    def create_blank_workflow(self):
        """创建新的空白工作流"""
        # 使用标签页控件的创建功能
        task_id = self.workflow_tab_widget.create_blank_workflow()

        if task_id is not None:
            logger.info(f"空白工作流创建成功，任务ID: {task_id}")
            # 空白工作流标记为未保存（已由task_manager处理）
        else:
            logger.info("空白工作流创建失败")

    def open_control_center(self):
        """打开中控软件窗口"""
        try:
            # 导入中控窗口类
            from ui.control_center import ControlCenterWindow

            # 创建中控窗口
            self.control_center = ControlCenterWindow(
                bound_windows=self.bound_windows,
                task_modules=self.task_modules,
                parent=self
            )

            # 显示中控窗口
            self.control_center.show()

            logging.info("中控软件已启动")

        except Exception as e:
            logging.error(f"启动中控软件失败: {e}")
            QMessageBox.warning(self, "错误", f"启动中控软件失败: {e}")

    def open_global_settings(self):
        """打开全局设置对话框"""
        try:
            logger.info(f"打开全局设置前，MainWindow.config 中的 bound_windows: {len(self.config.get('bound_windows', []))} 个")

            dialog = GlobalSettingsDialog(self.config, self)
            if dialog.exec():
                # 获取所有设置
                settings = dialog.get_settings()

                logger.info(f"GlobalSettingsDialog 返回的 bound_windows: {len(settings.get('bound_windows', []))} 个")
                logger.info(f"  窗口列表: {[w.get('title') for w in settings.get('bound_windows', [])]}")

                # 更新本地设置
                self.current_target_window_title = settings.get('target_window_title')
                self.current_execution_mode = settings.get('execution_mode', 'foreground')
                self.operation_mode = 'auto'  # 默认使用自动检测
                self.custom_width = settings.get('custom_width', 1280)
                self.custom_height = settings.get('custom_height', 720)

                # 新增的配置项
                self.window_binding_mode = settings.get('window_binding_mode', 'single')
                self.bound_windows = settings.get('bound_windows', [])
                self.multi_window_delay = settings.get('multi_window_delay', 500)

                logger.info(f"更新后 MainWindow.bound_windows: {len(self.bound_windows)} 个")

                # 快捷键设置
                self.start_task_hotkey = settings.get('start_task_hotkey', 'F9')
                self.stop_task_hotkey = settings.get('stop_task_hotkey', 'F10')
                self.record_hotkey = settings.get('record_hotkey', 'F12')

                # 更新配置字典
                self.config.update(settings)

                logger.info(f"更新配置字典后，self.config['bound_windows']: {len(self.config.get('bound_windows', []))} 个")

                # 应用主题设置
                try:
                    theme_mode_str = settings.get('theme', 'system')
                    from ui.theme_manager import ThemeManager, ThemeMode

                    # 将字符串转换为 ThemeMode 枚举
                    theme_map = {
                        'light': ThemeMode.LIGHT,
                        'dark': ThemeMode.DARK,
                        'system': ThemeMode.SYSTEM
                    }
                    theme_mode = theme_map.get(theme_mode_str, ThemeMode.SYSTEM)

                    theme_manager = QApplication.instance().theme_manager
                    theme_manager.set_theme(theme_mode)
                    logger.info(f"主题已切换为: {theme_mode_str}")
                except Exception as e:
                    logger.warning(f"应用主题设置失败: {e}")

                # 应用操作模式设置到全局输入模拟器管理器
                try:
                    from utils.backend_modes import backend_manager
                    backend_manager.set_global_operation_mode(self.operation_mode)
                    backend_manager.set_global_execution_mode(self.current_execution_mode)
                    print(f"  操作模式: {self.operation_mode}")
                except ImportError:
                    logging.warning("无法导入backend_manager，操作模式设置未应用")

                # 更新快捷键
                self._update_hotkeys()

                print(f"全局设置已更新:")
                print(f"  窗口绑定模式: {self.window_binding_mode}")
                if self.window_binding_mode == 'single':
                    print(f"  目标窗口: {self.current_target_window_title or '未设置'}")
                else:
                    print(f"  绑定窗口数量: {len(self.bound_windows)}")
                    enabled_count = sum(1 for w in self.bound_windows if w.get('enabled', True))
                    print(f"  启用窗口数量: {enabled_count}")
                print(f"  执行模式: {self.current_execution_mode}")
                print(f"  自定义分辨率: {self.custom_width}x{self.custom_height}")
                if self.window_binding_mode == 'multiple':
                    print(f"  多窗口启动延迟: {self.multi_window_delay}ms")

                # 工具 修复：安全地应用自定义分辨率（如果适用）
                try:
                    logger.debug("开始应用自定义分辨率设置")
                    if self.window_binding_mode == 'multiple':
                        logger.debug("使用多窗口分辨率调整")
                        self._apply_multi_window_resize()
                    else:
                        logger.debug("使用单窗口分辨率调整")
                        self._apply_initial_window_resize()
                    logger.debug("分辨率设置应用完成")
                except Exception as resize_error:
                    logger.error(f"应用分辨率设置时发生错误: {resize_error}", exc_info=True)
                    # 不中断程序，继续执行后续操作

                # 检查是否需要激活窗口（根据执行模式和窗口状态）
                self._check_window_activation_after_settings_update()

                # 更新窗口标题以显示目标窗口
                self._update_main_window_title()

                # 保存更新后的配置到文件
                try:
                    from main import save_config
                    save_config(self.config)
                    print("配置已保存到文件")
                except ImportError:
                    logging.warning("警告: 无法导入 save_config, 全局设置未自动保存到文件。")
                except Exception as e:
                    logging.error(f"错误: 保存全局设置时出错: {e}")
                    logging.error(f"错误详细信息: {e}", exc_info=True)
                    print(f"工具 DEBUG: 保存配置时出错: {e}")
                    try:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(self, "保存设置错误", f"保存全局设置时出错: {e}")
                    except Exception as msg_error:
                        logging.error(f"显示消息框失败: {msg_error}")
                        print(f"工具 DEBUG: 显示错误消息框失败: {msg_error}")
        except Exception as e:
            logging.error(f"打开全局设置对话框时出错: {e}")
            try:
                from ui.custom_dialogs import ErrorWrapper
                ErrorWrapper.show_exception(
                    parent=self,
                    error=e,
                    title="设置错误",
                    context="打开全局设置"
                )
            except Exception as dialog_error:
                logging.error(f"显示错误对话框失败: {dialog_error}")
                # 回退到标准消息框
                QMessageBox.critical(self, "设置错误", f"打开全局设置对话框时出错: {e}")

    def _update_hotkeys(self):
        """更新全局快捷键 - 统一的快捷键管理系统"""
        try:
            import keyboard
            import time

            # 清除所有现有快捷键
            try:
                keyboard.unhook_all()
                logger.info("已清除所有现有快捷键")
                time.sleep(0.1)  # 短暂等待确保清理完成
            except Exception as e:
                logger.warning(f"清除快捷键失败: {e}，继续设置新快捷键")

            # 设置启动任务快捷键（强制抢夺使用权）
            start_key = self.start_task_hotkey.lower()
            if start_key:
                try:
                    # 使用 suppress=True 强制抢夺快捷键，trigger_on_release=False 提高响应速度
                    keyboard.add_hotkey(
                        start_key,
                        self._on_start_task_hotkey,
                        trigger_on_release=False,
                        suppress=True
                    )
                    logger.info(f"启动任务快捷键已设置: {start_key.upper()} (强制模式)")
                except Exception as e:
                    logger.error(f"设置启动任务快捷键失败: {e}")

            # 设置停止任务快捷键（强制抢夺使用权）
            stop_key = self.stop_task_hotkey.lower()
            if stop_key:
                try:
                    # 使用 suppress=True 强制抢夺快捷键，trigger_on_release=False 提高响应速度
                    keyboard.add_hotkey(
                        stop_key,
                        self._on_stop_task_hotkey,
                        trigger_on_release=False,
                        suppress=True
                    )
                    logger.info(f"停止任务快捷键已设置: {stop_key.upper()} (强制模式)")
                except Exception as e:
                    logger.error(f"设置停止任务快捷键失败: {e}")

            # 录制功能已被移除，跳过录制快捷键更新

            logger.info(f"✓ 快捷键系统已更新 - 启动: {start_key.upper()}, 停止: {stop_key.upper()}")

        except ImportError:
            logger.warning("keyboard库不可用，无法设置全局快捷键")
        except Exception as e:
            logger.error(f"更新快捷键失败: {e}")
            # 添加更详细的错误信息
            import traceback
            logger.debug(f"快捷键更新错误详情: {traceback.format_exc()}")

    def _update_record_hotkey(self):
        """更新录制器的录制控制快捷键（已禁用）"""
        # 录制功能已被移除，此方法保留以避免调用错误
        logger.debug("录制功能已被移除，跳过快捷键更新")

    def _on_start_task_hotkey(self):
        """启动任务快捷键回调 - 通过信号确保线程安全"""
        try:
            # 防抖：检查是否在短时间内重复触发
            import time
            current_time = time.time()
            if hasattr(self, '_last_start_hotkey_time'):
                if current_time - self._last_start_hotkey_time < 0.5:  # 500ms 防抖
                    logger.debug(f"快捷键防抖：忽略重复触发（距上次 {current_time - self._last_start_hotkey_time:.3f}s）")
                    return
            self._last_start_hotkey_time = current_time

            logger.info(f"检测到启动任务快捷键: {self.start_task_hotkey}")

            # 通过信号发射，Qt 会自动在主线程的事件循环中执行连接的槽函数
            self.hotkey_start_signal.emit()
            logger.info("快捷键回调：已发射 hotkey_start_signal 信号")

        except Exception as e:
            logger.error(f"启动任务快捷键处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _on_stop_task_hotkey(self):
        """停止任务快捷键回调 - 通过信号确保线程安全"""
        try:
            # 防抖：检查是否在短时间内重复触发
            import time
            current_time = time.time()
            if hasattr(self, '_last_stop_hotkey_time'):
                if current_time - self._last_stop_hotkey_time < 0.5:  # 500ms 防抖
                    logger.debug(f"快捷键防抖：忽略重复触发（距上次 {current_time - self._last_stop_hotkey_time:.3f}s）")
                    return
            self._last_stop_hotkey_time = current_time

            logger.info(f"检测到停止任务快捷键: {self.stop_task_hotkey}")

            # 通过信号发射
            self.hotkey_stop_signal.emit()
            logger.info("快捷键回调：已发射 hotkey_stop_signal 信号")

        except Exception as e:
            logger.error(f"停止任务快捷键处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _safe_start_from_hotkey(self):
        """在主线程中安全启动任务（供快捷键调用）"""
        try:
            logger.info("快捷键触发：在主线程中启动任务")
            self.safe_start_tasks()
        except Exception as e:
            logger.error(f"快捷键启动任务失败: {e}")

    def _safe_stop_from_hotkey(self):
        """在主线程中安全停止任务（供快捷键调用）"""
        try:
            logger.info("快捷键触发：在主线程中停止任务")
            self.safe_stop_tasks()
        except Exception as e:
            logger.error(f"快捷键停止任务失败: {e}")

    def run_workflow(self, *args, **kwargs):
        """Initiates the workflow execution in a separate thread."""
        logger.warning("🚨 run_workflow 被调用！")

        # 🔧 首先检查是否有当前工作流
        if not self._ensure_current_workflow(show_warning=True):
            return

        # 🔧 检查ADB初始化是否完成（仅在需要时检查）
        if (hasattr(self, '_needs_adb_initialization') and self._needs_adb_initialization and
            (not hasattr(self, '_adb_initialization_completed') or not self._adb_initialization_completed)):
            logger.warning("run_workflow: ADB初始化尚未完成，无法执行任务")
            QMessageBox.information(
                self,
                "初始化中",
                "检测到模拟器窗口，ADB连接池和ADBKeyboard正在初始化中，请稍候...\n\n初始化完成后运行按钮将自动启用。"
            )
            return

        log_func = logging.info if logging.getLogger().hasHandlers() else print

        # 在任务执行前检查并更新窗口句柄
        try:
            self._check_and_update_window_handles()
        except Exception as e:
            logger.error(f"检查窗口句柄时出错: {e}")

        # 工具 关键修复：动态检查窗口绑定模式，根据启用窗口数量决定执行方式
        enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]
        enabled_count = len(enabled_windows)

        logger.info(f"搜索 运行时检查: 总绑定窗口={len(self.bound_windows)}, 启用窗口={enabled_count}")

        if enabled_count > 1:
            # 多个启用窗口：强制使用多窗口模式
            logger.info(f"靶心 检测到{enabled_count}个启用窗口，使用多窗口模式")
            self._run_multi_window_workflow()
            return
        elif enabled_count == 1:
            # 单个启用窗口：使用单窗口模式，但使用启用的那个窗口
            enabled_window = enabled_windows[0]
            logger.info(f"靶心 检测到1个启用窗口，使用单窗口模式: {enabled_window['title']} (HWND: {enabled_window.get('hwnd')})")
            # 工具 关键修复：直接保存启用窗口的句柄，避免通过标题查找导致的混乱
            self._forced_target_hwnd = enabled_window.get('hwnd')
            self._forced_target_title = enabled_window['title']
            logger.info(f"工具 强制使用启用窗口句柄: {self._forced_target_hwnd}")
        else:
            # 没有启用的窗口
            logger.warning("警告 没有启用的窗口，无法执行")
            QMessageBox.warning(self, "无法执行", "没有启用的窗口。请在全局设置中启用至少一个窗口。")
            return

        # 单窗口模式（原有逻辑）
        # --- MODIFIED: Always Save/Backup or Prompt Save As before running ---
        save_successful = False

        # 🔧 多任务模式：检查当前任务的保存状态
        task_id = self.workflow_tab_widget.get_current_task_id()
        if task_id is not None:
            task = self.task_manager.get_task(task_id)
            if task:
                # 使用任务的filepath作为保存路径
                task_save_path = task.filepath
                logger.info(f"多任务模式：检查任务 {task.name} 的保存状态，路径: {task_save_path}")

                if task_save_path:
                    # 任务已有保存路径，直接使用（导入的任务默认已保存）
                    logger.info(f"任务已有保存路径，无需再次保存: {task_save_path}")
                    save_successful = True
                else:
                    # 任务没有保存路径，提示用户保存
                    logger.info("任务未保存，提示用户另存为...")
                    reply = QMessageBox.question(self, "需要保存",
                                                 f"工作流 '{task.name}' 尚未保存。是否先保存再运行？",
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                                 QMessageBox.StandardButton.Yes)
                    if reply == QMessageBox.StandardButton.Yes:
                        # 调用标签页的保存方法
                        from PySide6.QtWidgets import QFileDialog
                        filepath, _ = QFileDialog.getSaveFileName(
                            self,
                            "保存工作流",
                            f"./{task.name}",
                            "JSON文件 (*.json);;所有文件 (*)"
                        )
                        if filepath:
                            # 保存任务
                            workflow_data = self.workflow_view.serialize_workflow()
                            import json
                            try:
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                                task.filepath = filepath
                                task.modified = False
                                save_successful = True
                                logger.info(f"任务保存成功: {filepath}")
                            except Exception as e:
                                logger.error(f"保存任务失败: {e}")
                                QMessageBox.warning(self, "保存失败", f"保存失败: {e}")
                                return
                        else:
                            logger.info("用户取消了保存操作，中止执行。")
                            return
                    else:
                        logger.info("用户选择不保存，中止执行。")
                        return
            else:
                logger.error(f"无法找到任务: task_id={task_id}")
                return
        else:
            # 兼容旧的单任务模式
            if self.current_save_path:
                logger.info("运行前尝试保存和备份工作流...")
                save_successful = self.perform_save(self.current_save_path)
                if not save_successful:
                    logger.warning("运行前保存/备份失败，中止执行。")
                    QMessageBox.warning(self, "保存失败", "运行前保存或备份工作流失败，请检查日志或手动保存后再试。")
                    return # Stop execution if save/backup failed
            else:
                logger.info("运行前未找到保存路径，提示用户另存为...")
                reply = QMessageBox.question(self, "需要保存",
                                             "工作流尚未保存。是否先保存工作流再运行？",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                             QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    self.save_workflow_as() # This calls perform_save internally
                    if self.current_save_path: # Check if save_workflow_as was successful
                        save_successful = True
                    else:
                        logger.info("用户取消了另存为操作，中止执行。")
                        return # Stop execution if user cancelled save as
                else:
                    logger.info("用户选择不保存，中止执行。")
                    return # Stop execution if user chooses not to save

        # --- Proceed only if save was successful (or handled by Save As) ---
        if not save_successful:
            logger.error("保存步骤未成功完成，无法继续执行。") # Should technically be caught above
            return
        # --- END MODIFIED Save/Backup Logic ---

        # --- Backup Logic (Now happens inside perform_save) ---
        # ... (Keep this commented out) ...

        # --- Auto-save before running (Now redundant) ---
        # ... (Keep this commented out) ...

        # --- Check for existing thread BEFORE getting data ---
        if self.executor_thread is not None:
             logging.warning("run_workflow: 检测到现有工作流线程引用，表示清理尚未完成。")
             QMessageBox.warning(self, "操作冲突", "先前的工作流正在清理中，请稍后再试。")
             return 
        # --- End Check ---

        logging.info("run_workflow: 准备运行工作流...")
        
        try: # --- Add outer try block ---
            # 1. Gather data 
            logging.debug("run_workflow: Gathering data using serialize_workflow...")
            # --- Use serialize_workflow() for structured data --- 
            workflow_data = self.workflow_view.serialize_workflow() # <-- Use serialized data
            if not workflow_data or not workflow_data.get("cards"):
                logger.warning("工作流为空或无法序列化，无法执行。") # <-- Updated message
                QMessageBox.warning(self, "提示", "工作流为空或无法序列化，请添加步骤或检查配置。") # <-- Updated message
                self._reset_run_button() # Reset button if workflow is empty/invalid
                return
            # --------------------------------------------------

            # --- Get direct references for Executor (might still be needed) ---
            # Note: Executor might be refactored later to only use serialized data
            cards_dict = self.workflow_view.cards.copy()
            connections_objects = [item for item in self.workflow_view.scene.items() if isinstance(item, ConnectionLine)]
            # 转换 ConnectionLine 对象为字典格式
            connections_list = []
            for conn in connections_objects:
                connections_list.append({
                    'start_card_id': conn.start_item.card_id,
                    'end_card_id': conn.end_item.card_id,
                    'type': conn.line_type
                })
            logging.debug(f"run_workflow: Found {len(cards_dict)} cards, {len(connections_list)} connections for executor.")
            # Redundant check, already checked serialized data
            # if not cards_dict:
            #     QMessageBox.information(self, "提示", "工作流为空，无法执行。")
            #     logging.warning("run_workflow: 工作流为空，中止执行。")
            #     self._reset_run_button() # Ensure button is reset
            # ----------------------------------------------------------------

            # Visually update button, but keep signal connected to run_workflow for now
            logging.debug("run_workflow: Updating UI button state (Appearance only).")
            self.run_action.setEnabled(False) # Disable temporarily until thread starts
            self.run_action.setText("准备中...") # Indicate preparation
            # self.run_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)) # Don't set icon yet
            self.run_action.setToolTip("正在准备执行工作流")
            # --- DO NOT DISCONNECT/RECONNECT SIGNAL HERE --- 
            # self.run_action.triggered.disconnect()
            # self.run_action.triggered.connect(self.request_stop_workflow) 
            # -----------------------------------------------
            
            # 2. Create Thread and Executor
            logging.debug("run_workflow: Creating QThread...")
            self.executor_thread = QThread()
            logging.debug("run_workflow: Creating WorkflowExecutor...")
            # --- Add inner try block for Executor creation ---
            try:
                # --- MODIFIED: Find the starting card (must be type '起点') ---
                start_card_id = None
                start_card_obj = None
                start_card_count = 0
                for card in self.workflow_view.cards.values():
                    if card.task_type == "起点":
                        start_card_id = card.card_id
                        start_card_obj = card
                        start_card_count += 1
                        # Don't break immediately, count all start cards

                # Validate the start card
                if start_card_count == 0:
                    logging.error("未能找到起点卡片 (类型: 起点)。执行中止。")
                    QMessageBox.critical(self, "错误", "无法开始执行：工作流中必须包含一个类型为 '起点' 的卡片。")
                    self._reset_run_button()
                    # --- ADDED: Explicit cleanup on start card error ---
                    self.executor = None
                    self.executor_thread = None
                    # -------------------------------------------------
                    return
                elif start_card_count > 1:
                    logging.error(f"找到 {start_card_count} 个起点卡片。执行中止。")
                    QMessageBox.critical(self, "错误", f"无法开始执行：工作流中只能包含一个类型为 '起点' 的卡片，当前找到 {start_card_count} 个。")
                    self._reset_run_button()
                    # --- ADDED: Explicit cleanup on start card error ---
                    self.executor = None
                    self.executor_thread = None
                    # -------------------------------------------------
                    return
                else:
                     logging.info(f"找到唯一的起点卡片: Card ID={start_card_id}, Type={start_card_obj.task_type}")
                # --- END MODIFICATION ---

                # 工具 关键修复：优先使用强制指定的窗口句柄（单个启用窗口模式）
                target_hwnd = None

                # 第一优先级：强制指定的窗口句柄（来自启用窗口检查）
                if hasattr(self, '_forced_target_hwnd') and self._forced_target_hwnd:
                    target_hwnd = self._forced_target_hwnd
                    logger.info(f"靶心 使用强制指定的启用窗口句柄: {target_hwnd} ('{self._forced_target_title}')")
                # 第二优先级：从绑定窗口中查找保存的句柄
                elif self.current_target_window_title:
                    # 首先尝试从绑定窗口列表中获取保存的句柄
                    for window_info in self.bound_windows:
                        if window_info['title'] == self.current_target_window_title:
                            saved_hwnd = window_info.get('hwnd')
                            if saved_hwnd:
                                # 验证保存的句柄是否仍然有效
                                try:
                                    import win32gui
                                    if win32gui.IsWindow(saved_hwnd):
                                        target_hwnd = saved_hwnd
                                        logger.info(f"靶心 单窗口模式: 使用保存的窗口句柄 '{self.current_target_window_title}' (HWND: {target_hwnd})")

                                        # 工具 应用保存的DPI信息
                                        self._apply_saved_dpi_info(window_info, target_hwnd)
                                        break
                                    else:
                                        logger.warning(f"警告 保存的窗口句柄已失效: {saved_hwnd}")
                                except Exception as e:
                                    logger.warning(f"警告 验证保存的窗口句柄时出错: {e}")

                    # 如果没有找到有效的保存句柄，才重新查找（但这可能导致窗口混乱）
                    if not target_hwnd:
                        logger.warning(f"警告 未找到保存的窗口句柄，重新查找可能导致窗口混乱: '{self.current_target_window_title}'")
                        target_hwnd = self._find_window_by_title(self.current_target_window_title)
                        if target_hwnd:
                            logger.warning(f"警告 重新查找到窗口，但可能不是用户绑定的特定窗口: {target_hwnd}")
                        else:
                            logger.error(f"错误 完全找不到目标窗口: '{self.current_target_window_title}'")

                # 工具 关键修复：在创建WorkflowExecutor之前应用强制窗口句柄
                if hasattr(self, '_forced_target_hwnd') and self._forced_target_hwnd:
                    logger.info(f"工具 应用强制窗口句柄: {target_hwnd} -> {self._forced_target_hwnd}")
                    target_hwnd = self._forced_target_hwnd

                logger.info(f"靶心 单窗口模式: 最终目标窗口句柄 = {target_hwnd}")

                # --- Create and start the executor ---
                self.executor = WorkflowExecutor(
                    cards_data=cards_dict,          # 使用卡片字典
                    connections_data=connections_list, # 使用连接列表
                    task_modules=self.task_modules,
                    target_window_title=self.current_target_window_title,
                    execution_mode=self.current_execution_mode, # <<< 确保参数名是 execution_mode
                    start_card_id=start_card_id, # <<< 将找到的 start_card_id 传递进去
                    images_dir=self.images_dir,   # <<< ADDED: Pass images_dir
                    target_hwnd=target_hwnd       # 工具 修复：传递目标窗口句柄
                )
                logging.debug("run_workflow: WorkflowExecutor created successfully.")
            except Exception as exec_init_e:
                logging.error(f"run_workflow: 创建 WorkflowExecutor 时出错: {exec_init_e}", exc_info=True)
                QMessageBox.critical(self, "错误", f"无法初始化执行器: {exec_init_e}")
                self._reset_run_button() # Reset button on error
                # --- ADDED: Explicit cleanup on executor init error ---
                self.executor = None # Ensure executor ref is cleared
                # We might not have assigned executor_thread yet, but check just in case
                if self.executor_thread:
                     self.executor_thread.deleteLater() # Request deletion if it exists
                     self.executor_thread = None
                # ----------------------------------------------------
                return
            # --- End inner try block ---

            # Print parameters of the starting card for debugging
            if cards_dict:
                start_card_id = min(cards_dict.keys())
                start_card = cards_dict.get(start_card_id)
                if start_card:
                    logging.debug(f"run_workflow: Parameters for starting card ({start_card_id}) before execution: {start_card.parameters}") 
            
            # 检查WorkflowExecutor是否为真正的QObject（支持线程）
            is_qobject_executor = hasattr(self.executor, 'moveToThread') and hasattr(self.executor, 'execution_started')

            if is_qobject_executor:
                logging.debug("run_workflow: Moving executor to thread...")
                self.executor.moveToThread(self.executor_thread)

                # 3. Connect signals/slots
                logging.debug("run_workflow: Connecting signals and slots...")
                self.executor.execution_started.connect(self._handle_execution_started)
                self.executor.card_executing.connect(self._handle_card_executing)
                self.executor.card_finished.connect(self._handle_card_finished)
                self.executor.error_occurred.connect(self._handle_error_occurred)
                self.executor.execution_finished.connect(self._handle_execution_finished)
                # --- ADDED: Connect new signals ---
                self.executor.path_updated.connect(self._handle_path_updated)
                self.executor.path_resolution_failed.connect(self._handle_path_resolution_failed)
                # --- ADDED: Connect step_details signal ---
                self.executor.step_details.connect(self._update_step_details)
                # ------------------------------------------

                self.executor_thread.started.connect(self.executor.run)
                self.executor.execution_finished.connect(self.executor_thread.quit)
                self.executor.execution_finished.connect(self.executor.deleteLater)
                self.executor_thread.finished.connect(self.executor_thread.deleteLater)
                # --- ADDED connection for explicit reference cleanup ---
                self.executor_thread.finished.connect(self._cleanup_references)
                # -------------------------------------------------------
                logging.debug("run_workflow: Signals connected.")
            else:
                # 处理stub版本的WorkflowExecutor（打包版本）
                logging.warning("run_workflow: 检测到stub版本的WorkflowExecutor，工作流功能在打包版本中被禁用")
                QMessageBox.information(self, "功能限制",
                                      "工作流执行功能在当前版本中不可用。\n"
                                      "这是为了防止源代码泄露而设计的限制。")
                self._reset_run_button()
                # 清理资源
                self.executor = None
                if self.executor_thread:
                    self.executor_thread.deleteLater()
                    self.executor_thread = None
                return

            # 4. Start Thread
            logging.info("run_workflow: Starting thread...")
            # --- Add try block for thread start ---
            try:
                self.executor_thread.start()
                logging.info("run_workflow: 工作流执行线程已启动 (调用 thread.start() 成功)")
            except Exception as start_e:
                 logging.error(f"run_workflow: 启动线程时出错: {start_e}", exc_info=True)
                 QMessageBox.critical(self, "错误", f"无法启动执行线程: {start_e}")
                 self._reset_run_button()
                 # Clean up potentially half-created objects?
                 if self.executor:
                     # 只有QObject才能调用deleteLater
                     if hasattr(self.executor, 'deleteLater'):
                         self.executor.deleteLater()
                     self.executor = None
                 # --- MODIFIED: Ensure thread reference is cleared on start error --- 
                 if self.executor_thread:
                      # Don't try to quit/wait if start failed
                      self.executor_thread.deleteLater() 
                      self.executor_thread = None
                 # ---------------------------------------------------------------
                 return
            # --- End try block for thread start ---

            # --- ADDED: Reset unsaved changes if running a saved workflow ---
            if self.current_save_path:
                logging.debug(f"run_workflow: 工作流已保存 ({self.current_save_path})，运行后重置未保存状态。")
                self.unsaved_changes = False
                self._update_main_window_title()
            # -----------------------------------------------------------

        except Exception as e: # --- Catch errors in the outer block ---
            logging.error(f"run_workflow: 设置执行时发生意外错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"准备执行工作流时出错: {e}")
            self._reset_run_button() # Ensure button is reset
            # Clean up any potentially created thread/executor objects
            if self.executor:
                # 只有QObject才能调用deleteLater
                if hasattr(self.executor, 'deleteLater'):
                    self.executor.deleteLater()
                self.executor = None
            if self.executor_thread:
                if self.executor_thread.isRunning():
                    self.executor_thread.quit()
                    self.executor_thread.wait()
                self.executor_thread.deleteLater()
                self.executor_thread = None
            logging.warning("run_workflow: 在主 try 块中捕获到错误，确保 executor 和 thread 已清理。") # ADDED Log

    def request_stop_workflow(self):
        """Requests the running workflow to stop."""
        # 🔧 新增：优先检查任务管理器中的运行任务
        if hasattr(self, 'task_manager') and self.task_manager:
            running_tasks = [t for t in self.task_manager.get_all_tasks() if t.status == 'running']
            if running_tasks:
                logging.info(f"request_stop_workflow: 发现 {len(running_tasks)} 个运行中的任务，发送停止请求...")
                for task in running_tasks:
                    logging.info(f"  停止任务: {task.name} (ID: {task.task_id})")
                    self.task_manager.stop_task(task.task_id)
                return

        # 检查多窗口执行器
        if hasattr(self, 'multi_executor') and self.multi_executor and self.multi_executor.is_running:
            logging.info("request_stop_workflow: 向多窗口执行器发送停止请求...")
            self.multi_executor.stop_all()
            return

        # 工具 新增：检查多窗口执行器是否存在但已完成（用于手动重置状态）
        if hasattr(self, 'multi_executor') and self.multi_executor and not self.multi_executor.is_running:
            logging.info("request_stop_workflow: 多窗口执行器已完成，手动重置状态...")
            # 手动重置卡片状态和停止闪烁
            self.workflow_view.reset_card_states()
            try:
                for card_id, card in self.workflow_view.cards.items():
                    if card and hasattr(card, 'stop_flash'):
                        card.stop_flash()
                logging.info("手动重置：已停止所有卡片的闪烁效果")
            except Exception as e:
                logging.warning(f"手动重置闪烁效果失败: {e}")
            # 手动触发完成处理逻辑
            self._on_multi_window_completed(True, "手动重置状态")
            return

        # 检查单窗口执行器
        if self.executor:
            logging.info("request_stop_workflow: 向单窗口执行器发送停止请求...")
            # 检查是否为真正的WorkflowExecutor（有request_stop方法）
            if hasattr(self.executor, 'request_stop'):
                self.executor.request_stop()
                # 设置超时机制，如果5秒内没有收到停止确认，强制确认停止
                from PySide6.QtCore import QTimer
                if not hasattr(self, '_stop_timeout_timer'):
                    self._stop_timeout_timer = QTimer()
                    self._stop_timeout_timer.setSingleShot(True)
                    self._stop_timeout_timer.timeout.connect(self._force_confirm_stop)
                self._stop_timeout_timer.start(5000)  # 5秒超时
            else:
                logging.warning("request_stop_workflow: 当前执行器不支持停止操作（stub版本）")
                QMessageBox.information(self, "无法停止", "当前版本不支持停止工作流操作。")
                # 重置卡片状态和按钮状态
                self.workflow_view.reset_card_states()
                self._reset_run_button()
                # 立即确认停止状态
                if self.task_state_manager:
                    self.task_state_manager.confirm_stopped()
            # --- REMOVE Button Appearance Changes Here ---
            # Button state will be reset by _handle_execution_finished -> _reset_run_button
        else:
            logging.warning("request_stop_workflow: 没有正在运行的执行器或任务可停止。")
            if self.executor_thread is None:
                 logging.info("request_stop_workflow: 执行器和线程引用均已为 None，调用 _reset_run_button 以确保状态正确。")
                 # 重置卡片状态和按钮状态
                 self.workflow_view.reset_card_states()
                 self._reset_run_button()
                 # 立即确认停止状态
                 if self.task_state_manager:
                     self.task_state_manager.confirm_stopped() # Safe to call reset here if both are None

    def _reset_run_button(self):
        """Resets the run button to its initial 'Run' state and connects its signal."""
        # --- MODIFIED: Check button text and ensure signal is correct ---
        logging.debug("_reset_run_button: Attempting to reset button to 'Run' state.")

        # Set button appearance
        # 🔧 根据是否需要ADB初始化来决定按钮状态
        if (not hasattr(self, '_needs_adb_initialization') or not self._needs_adb_initialization or
            (hasattr(self, '_adb_initialization_completed') and self._adb_initialization_completed)):
            self.run_action.setEnabled(True)
            self.run_action.setText("运行工作流")
            self.run_action.setToolTip("开始执行当前工作流 (F9)")
        else:
            self.run_action.setEnabled(False)
            self.run_action.setText("初始化中...")
            self.run_action.setToolTip("正在初始化ADB连接池和ADBKeyboard，请稍候...")

        self.run_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        # Ensure correct signal connection
        try:
            self.run_action.triggered.disconnect() # Disconnect all first
            logging.debug("_reset_run_button: Disconnected existing signals.")
        except (TypeError, RuntimeError): # Handle case where no signals are connected or object deleted
            logging.debug("_reset_run_button: No signals to disconnect or error disconnecting.")
            pass
        try:
            # Original connection from _create_actions
            # Use a direct method reference if the lambda isn't strictly needed
            self.run_action.triggered.connect(self.run_workflow)
            logging.info("_reset_run_button: Reconnected triggered signal to self.run_workflow.")
        except Exception as e:
            logging.error(f"_reset_run_button: Error connecting signal: {e}")
        # --------------------------------------------

    def _set_toolbar_to_stop_state(self):
        """设置顶部工具栏按钮为停止状态（用于任务管理器模式）"""
        logging.info("_set_toolbar_to_stop_state: 设置工具栏按钮为停止状态")

        self.run_action.setEnabled(True)
        self.run_action.setText("停止")
        self.run_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.run_action.setToolTip("停止当前任务执行 (F10)")

        # 连接到停止方法
        try:
            self.run_action.triggered.disconnect()
        except (TypeError, RuntimeError):
            pass
        try:
            self.run_action.triggered.connect(self.request_stop_workflow)
            logging.info("_set_toolbar_to_stop_state: 已连接到 request_stop_workflow")
        except Exception as e:
            logging.error(f"_set_toolbar_to_stop_state: 连接信号失败: {e}")

    def _on_task_status_changed(self, task_id: int, status: str):
        """任务状态变化处理（用于更新工具栏按钮）"""
        logging.debug(f"_on_task_status_changed: 任务 {task_id} 状态变为 {status}")

        # 检查是否还有运行中的任务
        running_tasks = [t for t in self.task_manager.get_all_tasks() if t.status == 'running']

        if not running_tasks:
            # 没有运行中的任务，重置按钮
            logging.info("_on_task_status_changed: 没有运行中的任务，重置工具栏按钮")
            self._reset_run_button()

    def _on_all_tasks_completed(self, success: bool):
        """所有任务完成处理（用于更新工具栏按钮）"""
        logging.info(f"_on_all_tasks_completed: 所有任务已完成，成功={success}")
        self._reset_run_button()

    # --- New Slot for final cleanup after thread finishes ---
    def _cleanup_references(self):
        """Slot connected to QThread.finished signal to clear references."""
        logging.info("_cleanup_references: QThread finished signal received. Clearing executor and thread references.")
        # It's possible the executor was already deleted by deleteLater, handle gracefully
        # Also check if the attribute exists before accessing it
        if hasattr(self, 'executor') and self.executor is not None:
             logging.debug("_cleanup_references: Executor reference was not None, setting to None now.")
        self.executor = None
        # Clear the thread reference *after* it signals finished
        # Check if the attribute exists before accessing it
        if hasattr(self, 'executor_thread') and self.executor_thread is not None:
             self.executor_thread = None
             logging.info("_cleanup_references: References cleaned (executor and thread set to None).")
             # --- ADDED: Reset the run button AFTER cleanup --- 
             logging.info("_cleanup_references: 调用 _reset_run_button...")
             self._reset_run_button()
             # -------------------------------------------------
             # --- ADDED: Reset step detail label on cleanup ---
             self.step_detail_label.setText("等待执行...")
             # -----------------------------------------------
        else:
             logging.warning("_cleanup_references: Called but executor_thread reference was already None?")

    # --- Slots to handle signals from WorkflowExecutor --- 
    def _handle_execution_started(self):
        print("UI: 收到 execution_started 信号")
        
        # --- ADDED: 重置重复处理标志 ---
        self._execution_finished_processed = False
        self._execution_started_flag = True  # 标记任务已启动
        # ----------------------------
        
        # --- ADDED: Change button to 'Stop' state and connect signal --- 
        logging.info("_handle_execution_started: Setting button to 'Stop' state.")
        self.run_action.setEnabled(True) # Enable the stop button
        self.run_action.setText("停止")
        self.run_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.run_action.setToolTip("停止当前工作流执行 (F10)") # Add F10 hint
        # Ensure correct signal connection for stopping
        try:
            self.run_action.triggered.disconnect() # Disconnect previous (should be run_workflow)
        except (TypeError, RuntimeError):
            pass
        try:
            self.run_action.triggered.connect(self.request_stop_workflow)
            logging.info("_handle_execution_started: Reconnected triggered signal to self.request_stop_workflow.")
        except Exception as e:
            logging.error(f"_handle_execution_started: Error connecting signal to request_stop_workflow: {e}")
        # --------------------------------------------------------------
        self.workflow_view.reset_card_states() 

    def _handle_card_executing(self, card_id: int):
        print(f"UI: 收到 card_executing 信号 for ID {card_id}")
        self.workflow_view.set_card_state(card_id, 'executing')

        # 工具 添加闪烁效果提示正在执行的卡片
        try:
            card = self.workflow_view.cards.get(card_id)
            if card and hasattr(card, 'flash'):
                card.flash()  # 启动闪烁效果
                logger.debug(f" 启动卡片 {card_id} 闪烁效果")
            else:
                logger.debug(f"警告 卡片 {card_id} 不存在或不支持闪烁效果")
        except Exception as e:
            logger.warning(f"错误 启动卡片 {card_id} 闪烁效果失败: {e}")

    def _handle_card_finished(self, card_id: int, success: bool):
        print(f"UI: 收到 card_finished 信号 for ID {card_id}, Success: {success}")
        state = 'success' if success else 'failure'
        self.workflow_view.set_card_state(card_id, state)

        # 工具 停止闪烁效果
        try:
            card = self.workflow_view.cards.get(card_id)
            if card and hasattr(card, 'stop_flash'):
                card.stop_flash()  # 停止闪烁效果
                logger.debug(f"停止 停止卡片 {card_id} 闪烁效果")
        except Exception as e:
            logger.warning(f"错误 停止卡片 {card_id} 闪烁效果失败: {e}")

    def _handle_error_occurred(self, card_id: int, error_message: str):
        print(f"UI: 收到 error_occurred 信号 for ID {card_id}: {error_message}")
        self.workflow_view.set_card_state(card_id, 'failure') # Mark card as failed on error

        # 工具 停止闪烁效果
        try:
            card = self.workflow_view.cards.get(card_id)
            if card and hasattr(card, 'stop_flash'):
                card.stop_flash()  # 停止闪烁效果
                logger.debug(f"停止 错误时停止卡片 {card_id} 闪烁效果")
        except Exception as e:
            logger.warning(f"错误 错误时停止卡片 {card_id} 闪烁效果失败: {e}")

        # Display error message to user
        QMessageBox.warning(self, "工作流错误", f"执行卡片 {card_id} 时出错:\n{error_message}")

    def _handle_execution_finished(self, status_message: str):
        """Handles the execution_finished signal from the executor."""
        logger.info(f"_handle_execution_finished: Received status '{status_message}'")

        # 工具 关键修复：清理强制指定的窗口句柄
        if hasattr(self, '_forced_target_hwnd'):
            logger.info(f"刷新 清理强制指定的窗口句柄: {self._forced_target_hwnd}")
            delattr(self, '_forced_target_hwnd')
        if hasattr(self, '_forced_target_title'):
            delattr(self, '_forced_target_title')

        # --- ADDED: 防止重复处理 ---
        if hasattr(self, '_execution_finished_processed') and self._execution_finished_processed:
            logger.warning("_handle_execution_finished: Already processed, ignoring duplicate call")
            return
        self._execution_finished_processed = True
        # -------------------------

        # --- ADDED: 重置所有卡片状态为idle ---
        logger.info("工作流执行完成，重置所有卡片状态为idle")
        self.workflow_view.reset_card_states()

        # 工具 停止所有卡片的闪烁效果 - 增强版本
        try:
            for card_id, card in self.workflow_view.cards.items():
                if card and hasattr(card, 'stop_flash'):
                    card.stop_flash()
                    logger.debug(f"停止卡片 {card_id} 的闪烁效果")
            logger.info("已停止所有卡片的闪烁效果")
        except Exception as e:
            logger.warning(f"错误 停止所有卡片闪烁效果失败: {e}")
        # ----------------------------------

        # --- 确保执行器和线程存在 ---
        if not self.executor or not self.executor_thread:
            logger.warning("_handle_execution_finished: Executor or thread is None, cannot clean up properly.")
            self._reset_run_button() # Still try to reset UI
            self._execution_finished_processed = False  # 重置标志
            return
        # --------------------------
        # --- ADDED: Disconnect signals to prevent duplicates if run again quickly? ---
        try:
            self.executor.execution_started.disconnect(self._handle_execution_started)
            self.executor.card_executing.disconnect(self._handle_card_executing)
            self.executor.card_finished.disconnect(self._handle_card_finished)
            self.executor.error_occurred.disconnect(self._handle_error_occurred)
            self.executor.execution_finished.disconnect(self._handle_execution_finished)
            self.executor.path_updated.disconnect(self._handle_path_updated)
            self.executor.path_resolution_failed.disconnect(self._handle_path_resolution_failed)
            self.executor.step_details.disconnect(self._update_step_details)
            logger.debug("_handle_execution_finished: Disconnected executor signals.")
        except RuntimeError as e:
             # This can happen if signals were already disconnected or never connected
             logger.warning(f"_handle_execution_finished: Error disconnecting signals: {e}. May have been disconnected already.")
        except Exception as e:
             # Catch other potential errors during disconnect
             logger.error(f"_handle_execution_finished: Unexpected error during signal disconnection: {e}", exc_info=True)
        # ---------------------------------------------------------------------
        
        # --- ADDED: Check for failed paths and offer to fix ---
        if self.failed_paths:
            num_failed = len(self.failed_paths)
            reply = QMessageBox.question(self,
                                         "图片路径问题",
                                         f"工作流执行期间有 {num_failed} 个图片文件无法找到。\n\n" 
                                         f"是否现在选择一个包含这些图片的文件夹来尝试自动修复路径？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                selected_directory = QFileDialog.getExistingDirectory(self, "选择包含缺失图片的文件夹", self.images_dir) # Start in default images dir
                if selected_directory:
                    self._try_update_failed_paths(selected_directory)
        # -----------------------------------------------------

        # Always reset the UI and clean up regardless of path failures
        self._reset_run_button()
        
        # --- ADDED: 确认任务停止状态 ---
        if self.task_state_manager:
            self.task_state_manager.confirm_stopped()
            logger.info("任务状态管理器已确认停止")
        # ----------------------------
        
        # 工具 修复：将内部状态消息转换为用户友好的消息
        user_friendly_message = self._convert_status_message_to_user_friendly(status_message)
        QMessageBox.information(self, "执行完成", user_friendly_message)
        self._cleanup_references() # Clean up references
        
        # Clear the list AFTER potential fix attempt
        self.failed_paths.clear()
        
        # --- ADDED: 重置重复处理标志 ---
        self._execution_finished_processed = False
        self._execution_started_flag = False  # 重置任务启动标志
        # ----------------------------

        # 停止超时定时器（如果存在）
        if hasattr(self, '_stop_timeout_timer') and self._stop_timeout_timer.isActive():
            self._stop_timeout_timer.stop()

        logger.debug("_handle_execution_finished: Processed.")

    def _convert_status_message_to_user_friendly(self, status_message: str) -> str:
        """将内部状态消息转换为用户友好的消息"""
        try:
            # 处理包含内部标识符的消息
            if "STOP_WORKFLOW" in status_message:
                return "工作流执行已停止"
            elif "被用户停止" in status_message:
                return "工作流被用户停止"
            elif "成功停止" in status_message:
                return "工作流执行成功完成"
            elif "执行完成" in status_message:
                return "工作流执行完成"
            elif "执行成功" in status_message:
                return "工作流执行成功"
            elif "执行失败" in status_message:
                return "工作流执行失败"
            elif "错误" in status_message or "异常" in status_message:
                return f"工作流执行出错：{status_message}"
            else:
                # 如果消息已经是用户友好的，直接返回
                return status_message
        except Exception as e:
            logger.warning(f"转换状态消息时出错: {e}")
            return "工作流执行完成"

    def _force_confirm_stop(self):
        """强制确认停止状态（超时机制）"""
        logger.warning("停止操作超时，强制确认停止状态")
        if self.task_state_manager:
            self.task_state_manager.confirm_stopped()
            logger.info("已强制确认停止状态")

    # --- ADDED: New slots and helper method for path handling ---
    def _handle_path_updated(self, card_id: int, param_name: str, new_path: str):
        """Updates the path parameter of a card when resolved to the default dir."""
        logger.info(f"UI: Received path_updated for Card {card_id}, Param '{param_name}', New Path: '{new_path}'")
        card = self.workflow_view.cards.get(card_id)
        if card:
            if param_name in card.parameters:
                card.parameters[param_name] = new_path
                logger.debug(f"  Card {card_id} parameter '{param_name}' updated in UI model.")
                self.unsaved_changes = True # Mark changes as unsaved
                self._update_main_window_title() # Update title to show unsaved state
            else:
                logger.warning(f"  Parameter '{param_name}' not found in Card {card_id}. Cannot update.")
        else:
            logger.warning(f"  Card with ID {card_id} not found in UI. Cannot update path.")

    def _handle_path_resolution_failed(self, card_id: int, original_path: str):
        """Stores information about paths that failed resolution."""
        logger.warning(f"UI: Received path_resolution_failed for Card {card_id}, Original Path: '{original_path}'")
        self.failed_paths.append((card_id, original_path))
        # Optionally update status bar here?
        # self.statusBar().showMessage(f"警告: 卡片 {card_id} 图片 '{os.path.basename(original_path)}' 查找失败", 5000)

    def _try_update_failed_paths(self, selected_directory: str):
        """Attempts to find missing files in the selected directory and update card parameters."""
        logger.info(f"Attempting to update failed paths using directory: {selected_directory}")
        updated_count = 0
        still_failed = []

        for card_id, original_path in self.failed_paths:
            card = self.workflow_view.cards.get(card_id)
            if not card:
                logger.warning(f"  Skipping update for Card {card_id} (not found in UI). Original path: {original_path}")
                still_failed.append((card_id, original_path))
                continue

            base_filename = os.path.basename(original_path)
            potential_new_path = os.path.normpath(os.path.join(selected_directory, base_filename))

            logger.debug(f"  Checking for '{base_filename}' in '{selected_directory}' -> '{potential_new_path}'")

            if os.path.exists(potential_new_path):
                logger.info(f"    Found! Updating Card {card_id} path to: {potential_new_path}")
                # Find the parameter key that holds the original_path
                # This is slightly tricky as we only stored the value. Iterate through params.
                param_key_to_update = None
                for key, value in card.parameters.items():
                    # Check if the current value matches the failed path (or just its basename?)
                    # Let's assume for now the stored original_path is what was in the param.
                    if value == original_path:
                         param_key_to_update = key
                         break 
                    # Fallback: Check if basename matches if full path doesn't
                    elif isinstance(value, str) and os.path.basename(value) == base_filename:
                         param_key_to_update = key
                         # Don't break here, maybe a more exact match exists
                
                if param_key_to_update:
                    card.parameters[param_key_to_update] = potential_new_path
                    updated_count += 1
                    self.unsaved_changes = True # Mark changes
                else:
                     logger.warning(f"    Could not find parameter key in Card {card_id} matching original path '{original_path}' or basename '{base_filename}'. Cannot update.")
                     still_failed.append((card_id, original_path)) # Treat as still failed
            else:
                logger.warning(f"    File '{base_filename}' not found in selected directory.")
                still_failed.append((card_id, original_path))

        self._update_main_window_title() # Update title if changes were made

        if updated_count > 0:
            QMessageBox.information(self, "路径更新完成", f"成功更新了 {updated_count} 个图片路径。")
        
        if still_failed:
            QMessageBox.warning(self, "部分路径未更新", 
                                f"仍有 {len(still_failed)} 个图片路径未能找到或更新。请手动检查这些卡片的参数。")
        # ------------------------------------------------------

    def _update_step_details(self, step_details: str):
        """Updates the step_details label with the received step details and sets color based on status."""
        self.step_detail_label.setText(step_details)

        # Determine text color based on content
        text_color = "black" # Default color changed to black
        if "执行成功" in step_details:
            text_color = "#2196F3" # Blue for success
        elif "执行失败" in step_details:
            text_color = "red"  # Red for failure
        # elif "等待执行" in step_details: # Keep initial black
        #     text_color = "black"

        # Update stylesheet dynamically
        # Preserve existing style, only change color
        current_stylesheet = self.step_detail_label.styleSheet()
        # Basic string manipulation to replace color (could use regex for robustness)
        new_stylesheet = current_stylesheet.replace("color: white;", f"color: {text_color};") \
                                         .replace("color: lime;", f"color: {text_color};") \
                                         .replace("color: red;", f"color: {text_color};") \
                                         .replace("color: #2196F3;", f"color: {text_color};") \
                                         .replace("color: black;", f"color: {text_color};") # Add replacement for black
        # Ensure color property exists if it wasn't there before
        if f"color: {text_color};" not in new_stylesheet:
             # Find the closing brace of the #stepDetailLabel block and insert before it
             insert_pos = new_stylesheet.find('}')
             if insert_pos != -1:
                 new_stylesheet = new_stylesheet[:insert_pos] + f"    color: {text_color};\n" + new_stylesheet[insert_pos:]
             else: # Fallback if structure is unexpected
                 new_stylesheet += f" #stepDetailLabel {{ color: {text_color}; }}"
                 
        self.step_detail_label.setStyleSheet(new_stylesheet)

        # Mark unsaved changes (optional, maybe only on functional changes?)
        # self.unsaved_changes = True 
        # self._update_main_window_title()

    def keyPressEvent(self, event: QEvent) -> None:
        """Handle key presses for shortcuts like Ctrl+S, Ctrl+O, etc."""
        # 注意：F9/F10 等功能键由 keyboard 库的全局快捷键系统处理
        # 这里只处理 Ctrl 组合键等非全局快捷键

        # --- 已禁用：F9/F10 硬编码处理（现由 keyboard 库统一管理）---
        # 原因：keyboard 库使用 suppress=True 全局拦截快捷键
        #      在 keyPressEvent 中处理会导致重复执行和冲突
        # if event.key() == Qt.Key.Key_F10:
        #     self.safe_stop_tasks()
        # elif event.key() == Qt.Key.Key_F9:
        #     self.run_workflow()
        # ---------------------------------------------------------------

        # 处理其他快捷键（例如 Ctrl+S, Ctrl+O 等）
        super().keyPressEvent(event) # Pass all keys to the base class

    # Override changeEvent to detect window state changes
    def changeEvent(self, event: QEvent) -> None:
        # Keep changeEvent for maximize icon updates
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            current_state = self.windowState()
            if hasattr(self, 'title_bar') and self.title_bar and hasattr(self.title_bar, '_update_maximize_icon'):
                # 使用定时器延迟更新，确保状态变化完全完成
                from PySide6.QtCore import QTimer
                QTimer.singleShot(10, lambda: self.title_bar._update_maximize_icon(self.windowState()))
                
    # Restore setWindowTitle override for custom title bar
    def setWindowTitle(self, title: str) -> None:
        # 限制标题长度，防止遮挡顶部按钮
        max_length = 50  # 最大字符数
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."  # 截断并添加省略号

        if hasattr(self, 'title_bar') and self.title_bar:
            self.title_bar.setWindowTitle(title)
        else:
            super().setWindowTitle(title) 
            
    # --- Restore Custom Painting for Rounded Corners --- 
    def paintEvent(self, event):
        """Override paint event to draw rounded background and clip contents."""
        painter = QPainter(self)
        # 启用抗锯齿渲染（使用兼容的 API）
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        path = QPainterPath()
        rect = self.rect() 
        corner_radius = 10.0 
        path.addRoundedRect(rect.toRectF(), corner_radius, corner_radius)
        
        # 先填充背景，再设置裁剪
        background_color = QColor(Qt.GlobalColor.white)
        painter.fillPath(path, QBrush(background_color))
        
        # 设置裁剪路径，确保内容不会超出圆角区域
        painter.setClipPath(path)
        
        # 不调用父类的 paintEvent，避免额外的绘制

    def _apply_multi_window_resize(self):
        """应用多窗口分辨率调整（使用通用窗口管理器）"""
        try:
            logger.debug("开始多窗口分辨率调整")

            target_client_width = self.custom_width
            target_client_height = self.custom_height

            if target_client_width <= 0 or target_client_height <= 0:
                logging.info("未配置自定义分辨率，跳过多窗口大小调整。")
                return

            # 工具 修复：安全检查绑定窗口
            if not hasattr(self, 'bound_windows') or not self.bound_windows:
                logging.warning("没有绑定窗口，跳过多窗口大小调整。")
                return

            # 获取所有启用的绑定窗口
            enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]
            if not enabled_windows:
                logging.warning("没有启用的绑定窗口，跳过多窗口大小调整。")
                return

            logger.debug(f"准备调整 {len(enabled_windows)} 个窗口的分辨率")

        except Exception as init_error:
            logger.error(f"多窗口分辨率调整初始化失败: {init_error}", exc_info=True)
            return

        try:
            # 工具 修复：安全导入和初始化通用分辨率适配器
            logger.debug("导入通用分辨率适配器")
            from utils.universal_resolution_adapter import get_universal_adapter

            logger.debug("获取适配器实例")
            adapter = get_universal_adapter()

            # 调试：打印窗口信息和检查句柄重复
            logging.info("调试：多窗口调整前的窗口状态:")

            # 检查句柄重复
            hwnd_count = {}
            for i, window_info in enumerate(enabled_windows):
                hwnd = window_info.get('hwnd')
                title = window_info.get('title', '未知窗口')

                if hwnd:
                    hwnd_count[hwnd] = hwnd_count.get(hwnd, 0) + 1

                    debug_info = adapter.debug_window_info(hwnd)
                    logging.info(f"  窗口 {i+1}: {title}")
                    logging.info(f"    HWND: {hwnd}")
                    logging.info(f"    类名: {debug_info.get('class_name', 'N/A')}")
                    logging.info(f"    客户区尺寸: {debug_info.get('client_size', 'N/A')}")
                    logging.info(f"    窗口尺寸: {debug_info.get('window_size', 'N/A')}")
                    logging.info(f"    可见: {debug_info.get('is_visible', 'N/A')}")
                    logging.info(f"    启用: {debug_info.get('is_enabled', 'N/A')}")
                else:
                    logging.warning(f"  窗口 {i+1}: {title} - 无有效句柄")

            # 报告句柄重复情况
            duplicate_hwnds = [hwnd for hwnd, count in hwnd_count.items() if count > 1]
            if duplicate_hwnds:
                logging.error(f"发现重复的窗口句柄: {duplicate_hwnds}")
                for hwnd in duplicate_hwnds:
                    logging.error(f"  句柄 {hwnd} 被 {hwnd_count[hwnd]} 个窗口使用")
            else:
                logging.info("所有窗口句柄都是唯一的")

            # 使用通用窗口管理器批量调整窗口（异步模式）
            from utils.universal_window_manager import get_universal_window_manager
            window_manager = get_universal_window_manager()
            results = []
            for window_info in enabled_windows:
                hwnd = window_info.get('hwnd')
                if hwnd:
                    # 每个窗口使用异步调整
                    result = window_manager.adjust_single_window(
                        hwnd, target_client_width, target_client_height, async_mode=True
                    )
                    results.append(result)

            # 生成调整报告
            report = window_manager.create_adjustment_report(results)

            logging.info(f"多窗口分辨率调整完成:")
            logging.info(f"  总窗口数: {report['summary']['total_windows']}")
            logging.info(f"  成功: {report['summary']['successful']}")
            logging.info(f"  失败: {report['summary']['failed']}")
            logging.info(f"  成功率: {report['summary']['success_rate']}")

            # 记录失败的窗口
            for failed_window in report['failed_windows']:
                logging.error(f"  失败窗口: {failed_window['title']} - {failed_window['reason']}")

            # 调试：打印调整后的窗口状态
            logging.info("调试：多窗口调整后的窗口状态:")
            for i, window_info in enumerate(enabled_windows):
                hwnd = window_info.get('hwnd')
                title = window_info.get('title', '未知窗口')

                if hwnd:
                    debug_info = adapter.debug_window_info(hwnd)
                    logging.info(f"  窗口 {i+1}: {title}")
                    logging.info(f"    调整后客户区尺寸: {debug_info.get('client_size', 'N/A')}")

        except Exception as e:
            logging.error(f"使用通用窗口管理器调整失败，回退到原有方法: {e}")
            self._apply_multi_window_resize_legacy(target_client_width, target_client_height, enabled_windows)

    def _apply_multi_window_resize_legacy(self, target_client_width: int, target_client_height: int, enabled_windows: list):
        """原有的多窗口分辨率调整方法（作为备用）"""
        # Check if pywin32 is available AND win32gui is successfully imported
        if not PYWIN32_AVAILABLE or win32gui is None:
            logging.warning("无法应用多窗口大小调整：需要 pywin32 且 win32gui 模块可用。")
            return

        logging.info(f"使用原有方法调整 {len(enabled_windows)} 个绑定窗口的分辨率到 {target_client_width}x{target_client_height}")

        success_count = 0
        failed_windows = []

        for window_info in enabled_windows:
            window_title = window_info.get('title', '')
            window_hwnd = window_info.get('hwnd')

            try:
                # 优先使用保存的句柄
                if window_hwnd:
                    # 验证句柄是否仍然有效
                    if win32gui.IsWindow(window_hwnd):
                        logging.info(f"调整窗口: {window_title} (HWND: {window_hwnd})")

                        # 检查是否为子窗口
                        parent_hwnd = win32gui.GetParent(window_hwnd)
                        is_child_window = parent_hwnd != 0

                        if is_child_window:
                            self._resize_parent_and_child_window(
                                parent_hwnd, window_hwnd, window_title,
                                target_client_width, target_client_height
                            )
                        else:
                            self._resize_single_window(
                                window_hwnd, window_title,
                                target_client_width, target_client_height
                            )

                        success_count += 1
                        logging.info(f"成功 窗口 {window_title} 分辨率调整成功")
                    else:
                        logging.warning(f"窗口句柄无效，尝试重新查找: {window_title}")
                        # 句柄无效，尝试重新查找
                        hwnd, is_child_window, parent_hwnd = self._find_window_with_parent_info(window_title)
                        if hwnd:
                            # 更新句柄
                            window_info['hwnd'] = hwnd

                            if is_child_window and parent_hwnd:
                                self._resize_parent_and_child_window(
                                    parent_hwnd, hwnd, window_title,
                                    target_client_width, target_client_height
                                )
                            else:
                                self._resize_single_window(
                                    hwnd, window_title,
                                    target_client_width, target_client_height
                                )

                            success_count += 1
                            logging.info(f"成功 窗口 {window_title} 分辨率调整成功（重新查找）")
                        else:
                            failed_windows.append(window_title)
                            logging.error(f"错误 无法找到窗口: {window_title}")
                else:
                    # 没有保存的句柄，尝试查找
                    logging.info(f"查找窗口: {window_title}")
                    hwnd, is_child_window, parent_hwnd = self._find_window_with_parent_info(window_title)
                    if hwnd:
                        # 保存句柄
                        window_info['hwnd'] = hwnd

                        if is_child_window and parent_hwnd:
                            self._resize_parent_and_child_window(
                                parent_hwnd, hwnd, window_title,
                                target_client_width, target_client_height
                            )
                        else:
                            self._resize_single_window(
                                hwnd, window_title,
                                target_client_width, target_client_height
                            )

                        success_count += 1
                        logging.info(f"成功 窗口 {window_title} 分辨率调整成功")
                    else:
                        failed_windows.append(window_title)
                        logging.error(f"错误 无法找到窗口: {window_title}")

            except Exception as e:
                failed_windows.append(window_title)
                logging.error(f"错误 调整窗口 {window_title} 分辨率时发生错误: {e}")

        # 输出调整结果
        logging.info(f"多窗口分辨率调整完成: 成功 {success_count} 个，失败 {len(failed_windows)} 个")
        if failed_windows:
            logging.warning(f"调整失败的窗口: {', '.join(failed_windows)}")

        # 静默调整，只记录日志，不显示弹窗
        if success_count > 0:
            if failed_windows:
                logging.info(f"分辨率调整完成：成功 {success_count} 个，失败 {len(failed_windows)} 个")
                logging.warning(f"调整失败的窗口: {', '.join(failed_windows)}")
            else:
                logging.info(f"成功调整所有 {success_count} 个窗口的分辨率到 {target_client_width}x{target_client_height}")

            # 清理DPI缓存，确保后续操作使用最新的窗口信息
            self._clear_dpi_cache_for_adjusted_windows(enabled_windows)
        else:
            logging.warning("无法调整任何窗口的分辨率，请检查窗口是否存在且可访问")

    def _clear_dpi_cache_for_adjusted_windows(self, adjusted_windows):
        """清理已调整窗口的DPI缓存，确保后续操作使用最新信息"""
        try:
            if hasattr(self, 'unified_dpi_handler'):
                for window_info in adjusted_windows:
                    hwnd = window_info.get('hwnd')
                    if hwnd:
                        self.unified_dpi_handler.clear_cache(hwnd)
                        logging.debug(f"已清理窗口 {hwnd} 的DPI缓存")

                logging.info(f"已清理 {len(adjusted_windows)} 个窗口的DPI缓存")
            else:
                logging.warning("DPI处理器未初始化，无法清理缓存")
        except Exception as e:
            logging.error(f"清理DPI缓存时出错: {e}")

    def _check_window_activation_after_settings_update(self):
        """在全局设置更新后检查是否需要激活窗口"""
        # 工具 修复：禁用设置更新后的自动窗口激活，避免干扰用户操作
        logger.info("靶心 全局设置更新完成，跳过自动窗口激活以避免干扰用户")
        return

        # 以下代码已禁用，只在实际执行任务时才激活窗口
        try:
            if self.window_binding_mode == 'single':
                # 单窗口模式：检查目标窗口
                if self.current_target_window_title:
                    hwnd = self._find_window_by_title(self.current_target_window_title)
                    if hwnd:
                        logger.info(f"全局设置更新后检查窗口激活: {self.current_target_window_title}")
                        self._activate_window_if_needed(hwnd, self.current_target_window_title)
            elif self.window_binding_mode == 'multiple':
                # 多窗口模式：检查所有绑定的窗口
                for window_info in self.bound_windows:
                    if window_info.get('enabled', True):
                        hwnd = window_info.get('hwnd')
                        window_title = window_info.get('title', '')
                        if hwnd and window_title:
                            logger.info(f"全局设置更新后检查窗口激活: {window_title}")
                            self._activate_window_if_needed(hwnd, window_title)
        except Exception as e:
            logger.error(f"检查窗口激活时出错: {e}")

    def _activate_window_if_needed(self, hwnd: int, window_title: str):
        """根据执行模式和窗口状态决定是否激活窗口"""
        try:
            import win32gui
            import win32con
            import traceback
            import time

            # 记录调用栈以便调试
            logger.info(f"_activate_window_if_needed 被调用，窗口: {window_title}")
            logger.info("调用栈:")
            for line in traceback.format_stack()[-5:-1]:  # 显示最近的4层调用栈
                logger.info(f"  {line.strip()}")

            # 获取当前执行模式
            execution_mode = self.current_execution_mode

            # 检查是否为子窗口，如果是则检查父窗口的状态
            parent_hwnd = win32gui.GetParent(hwnd)
            target_hwnd = parent_hwnd if parent_hwnd else hwnd

            logger.info(f"检测窗口状态 - 目标窗口HWND: {hwnd}, 父窗口HWND: {parent_hwnd}, 检测状态的窗口: {target_hwnd}")

            # 检查窗口是否最小化（检查父窗口或顶级窗口）
            placement = win32gui.GetWindowPlacement(target_hwnd)
            is_minimized = placement[1] == win32con.SW_SHOWMINIMIZED

            # 检查窗口是否可见
            is_visible = win32gui.IsWindowVisible(target_hwnd)

            # 获取窗口状态的详细信息
            window_state = placement[1]
            state_names = {
                win32con.SW_HIDE: "隐藏",
                win32con.SW_SHOWNORMAL: "正常显示",
                win32con.SW_SHOWMINIMIZED: "最小化",
                win32con.SW_SHOWMAXIMIZED: "最大化",
                win32con.SW_SHOWNOACTIVATE: "显示但不激活",
                win32con.SW_SHOW: "显示",
                win32con.SW_MINIMIZE: "最小化",
                win32con.SW_SHOWMINNOACTIVE: "最小化但不激活",
                win32con.SW_SHOWNA: "显示但不激活",
                win32con.SW_RESTORE: "恢复"
            }
            state_name = state_names.get(window_state, f"未知状态({window_state})")

            logger.info(f"窗口状态检查 - {window_title}:")
            logger.info(f"  执行模式: {execution_mode}")
            logger.info(f"  窗口状态: {state_name}")
            logger.info(f"  是否最小化: {is_minimized}")
            logger.info(f"  是否可见: {is_visible}")

            should_activate = False
            reason = ""

            # 标准化执行模式
            normalized_mode = normalize_execution_mode(execution_mode)

            if normalized_mode == 'foreground':
                # 前台模式总是激活窗口
                should_activate = True
                reason = "前台模式需要激活窗口"
            elif normalized_mode == 'background':
                if is_minimized:
                    # 后台模式下，如果窗口最小化则需要激活
                    should_activate = True
                    reason = "窗口处于最小化状态，需要激活"
                else:
                    # 后台模式下，窗口正常显示则不激活
                    should_activate = False
                    reason = "后台模式且窗口正常显示，不需要激活"
            else:
                logger.warning(f"未识别的执行模式: {execution_mode}")
                should_activate = False
                reason = f"未识别的执行模式: {execution_mode}"

            logger.info(f"激活决策: {should_activate} - {reason}")

            if should_activate:
                logger.info(f"开始激活窗口: {window_title}")

                # 如果窗口最小化，先恢复窗口（恢复父窗口或顶级窗口）
                if is_minimized:
                    logger.info(f"窗口已最小化，正在恢复...")
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                    logger.info(f"已发送恢复命令到窗口: {target_hwnd}")
                    # 等待窗口恢复
                    time.sleep(0.2)

                    # 验证窗口是否已恢复
                    new_placement = win32gui.GetWindowPlacement(target_hwnd)
                    new_state = new_placement[1]
                    new_state_name = state_names.get(new_state, f'未知({new_state})')
                    logger.info(f"恢复后窗口状态: {new_state_name}")

                # 激活窗口（激活父窗口或顶级窗口）
                logger.info(f"正在激活窗口: {target_hwnd}...")
                try:
                    win32gui.SetForegroundWindow(target_hwnd)
                    logger.info(f"窗口激活命令已发送: {window_title} (HWND: {target_hwnd})")
                except Exception as activate_error:
                    logger.error(f"激活窗口失败: {activate_error}")
                    # 尝试备用方法
                    try:
                        win32gui.BringWindowToTop(target_hwnd)
                        logger.info(f"使用备用方法将窗口置顶: {window_title} (HWND: {target_hwnd})")
                    except Exception as backup_error:
                        logger.error(f"备用激活方法也失败: {backup_error}")
            else:
                logger.info(f"不激活窗口: {window_title} - {reason}")

        except Exception as e:
            logger.error(f"激活窗口时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _apply_initial_window_resize(self):
        """Attempts to resize the target window's client area based on global settings on startup."""
        # Check if pywin32 is available AND win32gui is successfully imported
        if not PYWIN32_AVAILABLE or win32gui is None:
            logging.warning("无法应用初始窗口大小调整：需要 pywin32 且 win32gui 模块可用。")
            return

        title = self.current_target_window_title
        target_client_width = self.custom_width
        target_client_height = self.custom_height

        # 检查是否配置了自定义分辨率
        has_custom_resolution = target_client_width > 0 and target_client_height > 0

        # 在多窗口模式下，即使没有单一目标窗口标题，也可以应用自定义分辨率
        if self.window_binding_mode == 'multiple':
            if has_custom_resolution and self.bound_windows:
                logging.info(f"多窗口模式：尝试将绑定的窗口调整到 {target_client_width}x{target_client_height}...")
                self._apply_multi_window_resize()
            else:
                if not has_custom_resolution:
                    logging.info("多窗口模式：未配置自定义分辨率，跳过窗口大小调整。")
                else:
                    logging.info("多窗口模式：未绑定窗口，跳过窗口大小调整。")
        elif title and has_custom_resolution:
            logging.info(f"尝试将窗口 '{title}' 的客户区调整到 {target_client_width}x{target_client_height}...")

            # 优先尝试使用通用窗口管理器（支持MuMu专用方法）
            try:
                from utils.universal_window_manager import get_universal_window_manager

                # 查找窗口句柄
                hwnd, is_child_window, parent_hwnd = self._find_window_with_parent_info(title)
                if hwnd:
                    logging.info(f"找到窗口 HWND: {hwnd}，是否为子窗口: {is_child_window}")

                    # 使用通用窗口管理器调整分辨率（自动检测MuMu并使用专用方法）
                    window_manager = get_universal_window_manager()
                    result = window_manager.adjust_single_window(
                        hwnd, target_client_width, target_client_height, async_mode=True
                    )

                    if result.success:
                        logging.info(f"通用窗口管理器调整成功: {result.message}")
                        return
                    else:
                        logging.warning(f"通用窗口管理器调整失败: {result.message}，回退到传统方法")
                else:
                    logging.warning(f"未找到窗口 '{title}'，回退到传统方法")

            except ImportError:
                logging.warning("无法导入通用窗口管理器，使用传统方法")
            except Exception as e:
                logging.error(f"通用窗口管理器调整异常: {e}，回退到传统方法")

            # 回退到传统方法
            if PYWIN32_AVAILABLE and win32gui is not None:
                try:
                    # 工具 修复：支持子窗口的查找和父子窗口同时调整
                    hwnd, is_child_window, parent_hwnd = self._find_window_with_parent_info(title)
                    if hwnd:
                        logging.info(f"传统方法找到窗口 HWND: {hwnd}，是否为子窗口: {is_child_window}")
                        if is_child_window and parent_hwnd:
                            logging.info(f"父窗口 HWND: {parent_hwnd}")

                        # 工具 如果是子窗口，需要同时调整父窗口和子窗口
                        if is_child_window and parent_hwnd:
                            self._resize_parent_and_child_window(
                                parent_hwnd, hwnd, title,
                                target_client_width, target_client_height
                            )
                        else:
                            # 普通窗口调整
                            self._resize_single_window(
                                hwnd, title,
                                target_client_width, target_client_height
                            )
                    else:
                        logging.warning(f"启动时未找到标题为 '{title}' 的窗口，无法调整大小。")
                except Exception as e:
                    logging.error(f"调整窗口 '{title}' 大小时发生错误: {e}", exc_info=True)
            else:
                 # This else should ideally not be reached if the initial check passes,
                 # but as a fallback for extreme cases or future code changes:
                 logging.error(" رغم توفر الإعدادات، لم يتمكن من الوصول إلى win32gui لتغيير حجم النافذة.") # Arabic for: Despite settings being available, could not access win32gui for window resizing.
        else:
            logging.info("单窗口模式：未配置目标窗口标题或自定义分辨率，跳过初始大小调整。")

    def _find_window_by_title(self, title):
        """查找窗口，支持顶级窗口和子窗口"""
        if not PYWIN32_AVAILABLE or win32gui is None:
            return None

        # 首先尝试查找顶级窗口
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            logging.info(f"找到顶级窗口: {title} (HWND: {hwnd})")
            return hwnd

        # 如果没找到顶级窗口，枚举所有窗口查找子窗口
        logging.info(f"未找到顶级窗口 '{title}'，开始搜索子窗口...")
        found_hwnd = None

        def enum_windows_proc(hwnd, lParam):
            nonlocal found_hwnd
            try:
                # 获取窗口标题
                window_title = win32gui.GetWindowText(hwnd)
                if window_title == title:
                    found_hwnd = hwnd
                    logging.info(f"找到匹配的顶级窗口: {title} (HWND: {hwnd})")
                    return False  # 停止枚举

                # 枚举子窗口
                def enum_child_proc(child_hwnd, child_lParam):
                    nonlocal found_hwnd
                    try:
                        child_title = win32gui.GetWindowText(child_hwnd)
                        if child_title == title:
                            found_hwnd = child_hwnd
                            logging.info(f"找到匹配的子窗口: {title} (HWND: {child_hwnd})")
                            return False  # 停止枚举
                    except Exception as e:
                        pass  # 忽略子窗口枚举错误
                    return True  # 继续枚举

                # 枚举当前窗口的子窗口
                try:
                    win32gui.EnumChildWindows(hwnd, enum_child_proc, 0)
                except Exception as e:
                    pass  # 忽略子窗口枚举错误

            except Exception as e:
                pass  # 忽略窗口枚举错误

            return found_hwnd is None  # 如果找到了就停止枚举

        try:
            win32gui.EnumWindows(enum_windows_proc, 0)
        except Exception as e:
            logging.error(f"枚举窗口时出错: {e}")

        if found_hwnd:
            logging.info(f"通过枚举找到窗口: {title} (HWND: {found_hwnd})")
        else:
            logging.warning(f"未找到标题为 '{title}' 的窗口（包括子窗口）")

        return found_hwnd

    def _find_window_with_parent_info(self, title):
        """查找窗口并返回父窗口信息"""
        if not PYWIN32_AVAILABLE or win32gui is None:
            return None, False, None

        # 处理带有类型标注的窗口标题（如 "窗口名 [雷电模拟器]"）
        clean_title = title
        if '[' in title and ']' in title:
            # 提取原始窗口标题
            clean_title = title.split('[')[0].strip()
            logging.info(f"清理窗口标题: '{title}' -> '{clean_title}'")

        # 首先尝试查找顶级窗口
        hwnd = win32gui.FindWindow(None, clean_title)
        if hwnd:
            logging.info(f"找到顶级窗口: {clean_title} (HWND: {hwnd})")
            return hwnd, False, None

        # 如果没找到顶级窗口，枚举所有窗口查找子窗口
        logging.info(f"未找到顶级窗口 '{clean_title}'，开始搜索子窗口...")
        found_hwnd = None
        parent_hwnd = None

        def enum_windows_proc(hwnd, lParam):
            nonlocal found_hwnd, parent_hwnd
            try:
                # 获取窗口标题
                window_title = win32gui.GetWindowText(hwnd)
                if window_title == clean_title:
                    found_hwnd = hwnd
                    parent_hwnd = None  # 这是顶级窗口
                    logging.info(f"找到匹配的顶级窗口: {clean_title} (HWND: {hwnd})")
                    return False  # 停止枚举

                # 枚举子窗口
                def enum_child_proc(child_hwnd, child_lParam):
                    nonlocal found_hwnd, parent_hwnd
                    try:
                        child_title = win32gui.GetWindowText(child_hwnd)
                        if child_title == clean_title:
                            found_hwnd = child_hwnd
                            parent_hwnd = hwnd  # 记录父窗口
                            logging.info(f"找到匹配的子窗口: {clean_title} (HWND: {child_hwnd}, 父窗口: {hwnd})")
                            return False  # 停止枚举
                    except Exception as e:
                        pass  # 忽略子窗口枚举错误
                    return True  # 继续枚举

                # 枚举当前窗口的子窗口
                try:
                    win32gui.EnumChildWindows(hwnd, enum_child_proc, 0)
                except Exception as e:
                    pass  # 忽略子窗口枚举错误

            except Exception as e:
                pass  # 忽略窗口枚举错误

            return found_hwnd is None  # 如果找到了就停止枚举

        try:
            win32gui.EnumWindows(enum_windows_proc, 0)
        except Exception as e:
            logging.error(f"枚举窗口时出错: {e}")

        if found_hwnd:
            is_child = parent_hwnd is not None
            logging.info(f"通过枚举找到窗口: {clean_title} (HWND: {found_hwnd}, 是否为子窗口: {is_child})")
            return found_hwnd, is_child, parent_hwnd
        else:
            logging.warning(f"未找到标题为 '{clean_title}' 的窗口（包括子窗口）")
            return None, False, None

    def _resize_single_window(self, hwnd, title, target_client_width, target_client_height):
        """调整单个窗口的大小，直接使用设置的分辨率"""
        try:
            logging.info(f"调整窗口 '{title}' 到目标分辨率: {target_client_width}x{target_client_height}")

            # Get current window and client rectangles
            window_rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)

            # Calculate border/title bar dimensions
            current_window_width = window_rect[2] - window_rect[0]
            current_window_height = window_rect[3] - window_rect[1]
            current_client_width = client_rect[2] - client_rect[0]
            current_client_height = client_rect[3] - client_rect[1]

            border_width = current_window_width - current_client_width
            border_height = current_window_height - current_client_height
            logging.info(f"计算得到非客户区尺寸 - 宽度: {border_width}, 高度: {border_height}")

            # Calculate the target total window size using original dimensions
            target_window_width = target_client_width + border_width
            target_window_height = target_client_height + border_height

            # Get current position to keep it the same
            left, top = window_rect[0], window_rect[1]
            logging.info(f"当前位置: ({left}, {top})。将设置窗口总大小为 {target_window_width}x{target_window_height}...")

            # SetWindowPos flags: NOZORDER (keep Z order), NOACTIVATE (don't activate)
            # 不使用SWP_NOMOVE，因为我们需要保持当前位置
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, left, top,
                                  target_window_width, target_window_height,
                                  win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)

            logging.info(f"窗口 '{title}' 大小设置成功，目标客户区为 {target_client_width}x{target_client_height}")

        except Exception as e:
            logging.error(f"调整单个窗口 '{title}' 大小时发生错误: {e}", exc_info=True)

    def _resize_parent_and_child_window(self, parent_hwnd, child_hwnd, child_title, target_client_width, target_client_height):
        """调整父窗口和子窗口的大小（适用于模拟器等场景），直接使用设置的分辨率"""
        try:
            logging.info(f"工具 开始调整父子窗口大小 - 子窗口: {child_title}")
            logging.info(f"目标分辨率: {target_client_width}x{target_client_height}")

            # 获取父窗口信息
            parent_title = win32gui.GetWindowText(parent_hwnd)
            parent_window_rect = win32gui.GetWindowRect(parent_hwnd)
            parent_client_rect = win32gui.GetClientRect(parent_hwnd)

            # 获取子窗口信息
            child_window_rect = win32gui.GetWindowRect(child_hwnd)
            child_client_rect = win32gui.GetClientRect(child_hwnd)

            logging.info(f"父窗口: {parent_title} (HWND: {parent_hwnd})")
            logging.info(f"子窗口: {child_title} (HWND: {child_hwnd})")

            # 计算当前尺寸
            current_parent_width = parent_window_rect[2] - parent_window_rect[0]
            current_parent_height = parent_window_rect[3] - parent_window_rect[1]
            current_child_client_width = child_client_rect[2] - child_client_rect[0]
            current_child_client_height = child_client_rect[3] - child_client_rect[1]

            logging.info(f"当前父窗口大小: {current_parent_width}x{current_parent_height}")
            logging.info(f"当前子窗口客户区: {current_child_client_width}x{current_child_client_height}")

            # 计算需要调整的差值（使用原始目标尺寸）
            width_diff = target_client_width - current_child_client_width
            height_diff = target_client_height - current_child_client_height

            logging.info(f"需要调整的差值: 宽度{width_diff}, 高度{height_diff}")

            # 计算新的父窗口大小
            new_parent_width = current_parent_width + width_diff
            new_parent_height = current_parent_height + height_diff

            logging.info(f"新的父窗口大小: {new_parent_width}x{new_parent_height}")

            # 调整父窗口大小（添加SWP_NOACTIVATE防止激活窗口）
            parent_left, parent_top = parent_window_rect[0], parent_window_rect[1]
            win32gui.SetWindowPos(parent_hwnd, win32con.HWND_TOP, parent_left, parent_top,
                                  new_parent_width, new_parent_height,
                                  win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)

            logging.info(f"成功 父窗口 '{parent_title}' 大小调整完成")

            # 等待一小段时间让窗口调整完成
            import time
            time.sleep(0.1)

            # 验证子窗口的客户区是否达到目标大小
            new_child_client_rect = win32gui.GetClientRect(child_hwnd)
            new_child_client_width = new_child_client_rect[2] - new_child_client_rect[0]
            new_child_client_height = new_child_client_rect[3] - new_child_client_rect[1]

            logging.info(f"调整后子窗口客户区: {new_child_client_width}x{new_child_client_height}")

            if new_child_client_width == target_client_width and new_child_client_height == target_client_height:
                logging.info(f"完成 子窗口 '{child_title}' 分辨率调整成功！")
            else:
                logging.warning(f"警告 子窗口分辨率调整可能不完全准确")
                logging.warning(f"期望: {target_client_width}x{target_client_height}")
                logging.warning(f"实际: {new_child_client_width}x{new_child_client_height}")

                # 如果差距较大，尝试微调
                if abs(new_child_client_width - target_client_width) > 5 or abs(new_child_client_height - target_client_height) > 5:
                    logging.info("工具 尝试微调父窗口大小...")
                    fine_tune_width = target_client_width - new_child_client_width
                    fine_tune_height = target_client_height - new_child_client_height

                    final_parent_width = new_parent_width + fine_tune_width
                    final_parent_height = new_parent_height + fine_tune_height

                    win32gui.SetWindowPos(parent_hwnd, win32con.HWND_TOP, parent_left, parent_top,
                                          final_parent_width, final_parent_height,
                                          win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)

                    logging.info(f"微调后父窗口大小: {final_parent_width}x{final_parent_height}")

        except Exception as e:
            logging.error(f"调整父子窗口大小时发生错误: {e}", exc_info=True)

    # --- ADDED: Enhanced Safe Methods for State Management ---
    # 🔧 ========== 多任务执行方法 ==========

    def _ensure_current_workflow(self, show_warning: bool = True) -> bool:
        """
        确保有当前工作流，如果没有则提示用户

        Args:
            show_warning: 是否显示警告对话框

        Returns:
            是否有可用的工作流
        """
        if self.workflow_view and hasattr(self.workflow_view, 'cards'):
            return True

        if show_warning:
            QMessageBox.information(
                self,
                "提示",
                "请先导入工作流任务\n\n点击标签栏的 '+' 按钮或使用菜单'加载配置'"
            )

        return False

    def _show_welcome_hint(self):
        """显示首次使用提示"""
        # 检查是否已经有任务
        if self.task_manager.get_task_count() == 0:
            # 显示友好提示
            hint_text = """
            <h3>🎉 欢迎使用多任务工作流系统！</h3>
            <p>现在您可以同时管理多个工作流任务。</p>
            <p><b>快速开始：</b></p>
            <ul>
                <li>点击标签栏的 <b>"+"</b> 按钮导入工作流</li>
                <li>或使用菜单 <b>"加载配置"</b> 导入任务</li>
            </ul>
            <p>详细说明请查看 <i>docs/多任务系统使用说明.md</i></p>
            """

            # 🔧 多任务模式：不再显示提示文字，保持界面简洁
            self.step_detail_label.setText("")

    def _on_current_workflow_changed(self, task_id: int):
        """当前工作流标签页变化"""
        logger.info(f"🔄 切换到工作流标签页: task_id={task_id}")

        # 更新 workflow_view 引用
        old_view = self.workflow_view
        self.workflow_view = self.workflow_tab_widget.get_current_workflow_view()

        logger.info(f"   旧WorkflowView: {old_view}")
        logger.info(f"   新WorkflowView: {self.workflow_view}")

        # 连接信号（如果需要）
        if self.workflow_view:
            # 确保WorkflowView可见并激活
            self.workflow_view.setEnabled(True)
            self.workflow_view.setVisible(True)

            # 🔧 关键修复：强制恢复画布拖拽模式
            from PySide6.QtWidgets import QGraphicsView
            current_drag_mode = self.workflow_view.dragMode()
            logger.info(f"   当前拖拽模式: {current_drag_mode}")

            # 确保设置为ScrollHandDrag（画布可拖拽）
            self.workflow_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            logger.info(f"   已强制设置拖拽模式为: ScrollHandDrag")

            # 🔍 诊断信息：场景大小和视口大小
            scene_rect = self.workflow_view.sceneRect()
            viewport_rect = self.workflow_view.viewport().rect()
            cards_count = len(self.workflow_view.cards)

            logger.info(f"   场景大小: {scene_rect.width()}x{scene_rect.height()}")
            logger.info(f"   视口大小: {viewport_rect.width()}x{viewport_rect.height()}")
            logger.info(f"   卡片数量: {cards_count}")
            logger.info(f"   横向滚动条可见: {self.workflow_view.horizontalScrollBar().isVisible()}")
            logger.info(f"   纵向滚动条可见: {self.workflow_view.verticalScrollBar().isVisible()}")

            # 🔧 关键修复：强制重新计算场景大小
            if self.workflow_view.scene.items():
                items_rect = self.workflow_view.scene.itemsBoundingRect()
                # 添加padding确保有足够的拖动空间
                padding = 500
                padded_rect = items_rect.adjusted(-padding, -padding, padding, padding)
                self.workflow_view.scene.setSceneRect(padded_rect)
                logger.info(f"   🔧 已重新设置场景大小: {padded_rect.width()}x{padded_rect.height()}")

                # 强制更新滚动条
                self.workflow_view.viewport().update()
                new_hbar = self.workflow_view.horizontalScrollBar().isVisible()
                new_vbar = self.workflow_view.verticalScrollBar().isVisible()
                logger.info(f"   更新后滚动条: 横向={new_hbar}, 纵向={new_vbar}")
            else:
                logger.warning(f"   ⚠️ 场景中没有items，无法调整场景大小")

            # 连接场景选择变化信号
            try:
                # 🔧 先断开旧的连接，避免重复连接
                if old_view and old_view != self.workflow_view:
                    try:
                        old_view.scene.selectionChanged.disconnect(self.update_status_bar_for_selection)
                        logger.debug("已断开旧WorkflowView的信号连接")
                    except:
                        pass

                self.workflow_view.scene.selectionChanged.connect(self.update_status_bar_for_selection)
                logger.debug("场景选择变化信号已连接")
            except Exception as e:
                logger.error(f"连接场景选择变化信号失败: {e}")

            # 更新参数面板
            self._connect_parameter_panel_signals()

            # 🔧 修复：连接card_added信号，以便新增卡片能自动连接参数面板信号
            try:
                # 先断开旧的连接，避免重复连接
                if old_view and old_view != self.workflow_view:
                    try:
                        old_view.card_added.disconnect(self._on_card_added)
                        logger.debug("已断开旧WorkflowView的card_added信号")
                    except:
                        pass

                self.workflow_view.card_added.connect(self._on_card_added)
                logger.debug("card_added信号已连接到_on_card_added")
            except Exception as e:
                logger.error(f"连接card_added信号失败: {e}")

            logger.info(f"✅ WorkflowView切换完成，可拖动: {self.workflow_view.isEnabled()}")

        logger.debug(f"当前工作流已切换到任务ID: {task_id}")

    def _on_task_count_changed(self, task_id: int = None):
        """任务数量变化时，更新UI元素的显示/隐藏"""
        task_count = len(self.task_manager.get_all_tasks())
        logger.info(f"📊 任务数量变化: 当前任务数={task_count}")

        # 根据任务数量控制执行面板的显示/隐藏
        if task_count > 0:
            if not self.execution_panel.isVisible():
                logger.info("   显示执行面板")
                self.execution_panel.setVisible(True)
        else:
            if self.execution_panel.isVisible():
                logger.info("   隐藏执行面板")
                self.execution_panel.setVisible(False)

    def _on_task_added_for_jump(self, task_id: int):
        """任务添加后，连接其execution_finished信号以处理跳转"""
        task = self.task_manager.get_task(task_id)
        if task:
            # 连接任务的execution_finished信号
            task.execution_finished.connect(lambda success, message, stop_reason: self._on_task_execution_finished(task_id, success, message, stop_reason))
            logger.debug(f"已连接任务 {task.name} 的跳转信号")

    def _on_task_execution_finished(self, task_id: int, success: bool, message: str, stop_reason: str):
        """
        任务执行完成后的跳转处理

        Args:
            task_id: 完成的任务ID
            success: 是否成功
            message: 执行结果消息
            stop_reason: 停止原因 ('success', 'failed', 'no_next')
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            return

        logger.info(f"🎯 任务 '{task.name}' 执行完成，停止原因: {stop_reason}")

        # 检查是否启用跳转
        if not self.task_manager.jump_enabled or not task.jump_enabled:
            logger.info("跳转功能未启用，跳过")
            return

        # 检查跳转深度（如果max_jump_count不为0）
        max_jumps = getattr(task, 'max_jump_count', 10)
        if max_jumps > 0 and self.task_manager._current_jump_depth >= max_jumps:
            logger.warning(f"达到最大跳转次数 ({max_jumps})，停止跳转")
            self.task_manager._current_jump_depth = 0
            return

        # 查找跳转目标
        target_task_id = self.task_manager.find_jump_target(task)
        if target_task_id is None:
            logger.info("没有找到跳转目标，流程结束")
            self.task_manager._current_jump_depth = 0
            return

        # 执行跳转
        self.task_manager._current_jump_depth += 1
        logger.info(f"🚀 开始跳转: {task.name} -> task_id={target_task_id} (深度: {self.task_manager._current_jump_depth}/{max_jumps if max_jumps > 0 else '无限'})")

        # 切换到目标标签页
        from PySide6.QtCore import QTimer
        def perform_jump():
            try:
                # 切换标签页
                tab_index = self.workflow_tab_widget.task_to_tab.get(target_task_id)
                if tab_index is not None:
                    logger.info(f"切换到标签页: index={tab_index}")
                    self.workflow_tab_widget.setCurrentIndex(tab_index)

                    # 如果配置了自动执行，启动目标任务
                    if task.auto_execute_after_jump:
                        logger.info("自动执行目标任务")
                        # 再延迟一下确保标签页切换完成
                        QTimer.singleShot(300, lambda: self._execute_jump_target(target_task_id))
                    else:
                        # 不自动执行，重置跳转深度
                        self.task_manager._current_jump_depth = 0
                else:
                    logger.error(f"无法找到目标任务的标签页: task_id={target_task_id}")
                    self.task_manager._current_jump_depth = 0
            except Exception as e:
                logger.error(f"跳转执行失败: {e}", exc_info=True)
                self.task_manager._current_jump_depth = 0

        # 延迟执行跳转，确保当前任务完全结束
        QTimer.singleShot(500, perform_jump)

    def _execute_jump_target(self, task_id: int):
        """执行跳转目标任务"""
        try:
            task = self.task_manager.get_task(task_id)
            if task and task.can_execute():
                logger.info(f"执行跳转目标任务: {task.name}")
                # 更新任务的窗口绑定
                self._update_task_window_binding(task)
                # 异步执行
                task.execute_async()
            else:
                logger.warning(f"目标任务无法执行: task_id={task_id}")
                self.task_manager._current_jump_depth = 0
        except Exception as e:
            logger.error(f"执行跳转目标任务失败: {e}", exc_info=True)
            self.task_manager._current_jump_depth = 0

    def _start_current_task(self):
        """开始执行当前任务"""
        task_id = self.workflow_tab_widget.get_current_task_id()

        if task_id is None:
            QMessageBox.warning(self, "无法执行", "没有选中的任务")
            return

        # 🔧 关键修复：检查任务是否已在运行（参考run_workflow）
        task = self.task_manager.get_task(task_id)
        if task and hasattr(task, 'executor_thread') and task.executor_thread is not None:
            logger.warning(f"_start_current_task: 任务 {task_id} 的线程引用仍存在，表示清理尚未完成。")
            QMessageBox.warning(self, "操作冲突", "任务正在清理中，请稍后再试。")
            return

        # 🔧 新增：执行前自动保存并备份当前任务
        if task:
            # 先从画布获取最新工作流数据
            workflow_view = self.workflow_tab_widget.get_current_workflow_view()
            if workflow_view:
                logger.info(f"从画布获取最新工作流数据: {task.name}")
                latest_workflow_data = workflow_view.serialize_workflow()
                task.update_workflow_data(latest_workflow_data)
            else:
                logger.warning(f"无法获取任务 '{task.name}' 的 WorkflowView，使用现有数据")

            logger.info(f"执行前自动保存和备份任务: {task.name}")
            if not task.save_and_backup():
                logger.warning(f"任务 '{task.name}' 保存或备份失败，但继续执行")

        # 🔧 检查窗口绑定
        if not self._check_window_binding():
            return

        # 🔧 在任务执行前检查并更新窗口句柄（包含模拟器初始化等待）
        try:
            self._check_and_update_window_handles()
        except Exception as e:
            logger.error(f"检查窗口句柄时出错: {e}")

        # 🔧 更新任务的窗口句柄信息
        if task:
            self._update_task_window_binding(task)

        # 🔧 关键修复：清除可能的旧状态（参考run_workflow）
        try:
            # 清空输入模拟器缓存
            from utils.input_simulation import global_input_simulator_manager
            global_input_simulator_manager.clear_cache()
            logger.debug(f"_start_current_task: 已清空输入模拟器缓存")

            # 重置前台输入管理器的初始化状态（不调用close）
            from utils.foreground_input_manager import get_foreground_input_manager
            foreground_input = get_foreground_input_manager()
            foreground_input._initialization_attempted = False
            logger.debug(f"_start_current_task: 已重置前台输入管理器状态")
        except Exception as e:
            logger.warning(f"_start_current_task: 清除旧状态时出错: {e}")

        logger.info(f"开始执行当前任务: ID={task_id}")
        self.task_manager.execute_task(task_id)

        # 🔧 新增：更新顶部工具栏按钮状态为"停止"
        self._set_toolbar_to_stop_state()

    def _stop_current_task(self):
        """停止当前任务"""
        task_id = self.workflow_tab_widget.get_current_task_id()

        if task_id is None:
            return

        # 🔧 关键修复：检查任务是否真的在运行（参考request_stop_workflow）
        task = self.task_manager.get_task(task_id)
        if task:
            if hasattr(task, 'executor') and task.executor:
                logger.info(f"停止当前任务: ID={task_id}")
                self.task_manager.stop_task(task_id)
            else:
                logger.warning(f"_stop_current_task: 任务 {task_id} 没有正在运行的执行器")
                # 🔧 确保状态被重置
                if hasattr(task, 'executor_thread') and task.executor_thread is None:
                    logger.info(f"_stop_current_task: 任务 {task_id} 已完成，重置状态")
                    # 可以在这里添加状态重置逻辑
        else:
            logger.warning(f"_stop_current_task: 找不到任务 {task_id}")

    def _on_execution_mode_changed(self, mode: str):
        """执行模式变化回调 - 保存配置到文件"""
        logger.info(f"执行模式已变更为: {mode}, 保存配置...")

        # 配置已经在task_execution_panel中更新到config字典
        # 这里只需要调用保存函数
        try:
            if self.save_config_func:
                self.save_config_func(self.config)
            else:
                from main import save_config
                save_config(self.config)
            logger.info("执行模式配置已保存到文件")
        except Exception as e:
            logger.error(f"保存执行模式配置失败: {e}")

    def _start_all_tasks(self):
        """开始执行所有任务"""
        executable_count = len(self.task_manager.get_executable_tasks())

        if executable_count == 0:
            QMessageBox.information(self, "无可执行任务", "没有可以执行的任务")
            return

        # 🔧 关键修复：检查是否有任务正在运行（参考run_workflow）
        for task in self.task_manager.get_executable_tasks():
            if hasattr(task, 'executor_thread') and task.executor_thread is not None:
                logger.warning(f"_start_all_tasks: 任务 {task.task_id} 的线程引用仍存在，表示清理尚未完成。")
                QMessageBox.warning(self, "操作冲突", "有任务正在清理中，请稍后再试。")
                return

        # 🔧 新增：执行前自动保存并备份所有可执行任务
        logger.info(f"执行前自动保存和备份 {executable_count} 个任务")
        saved_count = 0
        backup_failed_tasks = []
        for task in self.task_manager.get_executable_tasks():
            # 先从画布获取最新工作流数据
            workflow_view = self.workflow_tab_widget.task_views.get(task.task_id)
            if workflow_view:
                logger.info(f"从画布获取最新工作流数据: {task.name}")
                latest_workflow_data = workflow_view.serialize_workflow()
                task.update_workflow_data(latest_workflow_data)
            else:
                logger.warning(f"无法获取任务 '{task.name}' 的 WorkflowView，使用现有数据")

            if task.save_and_backup():
                saved_count += 1
            else:
                backup_failed_tasks.append(task.name)
                logger.warning(f"任务 '{task.name}' 保存或备份失败")

        logger.info(f"成功保存和备份 {saved_count}/{executable_count} 个任务")
        if backup_failed_tasks:
            logger.warning(f"以下任务保存或备份失败: {', '.join(backup_failed_tasks)}，但将继续执行")

        # 🔧 检查窗口绑定
        if not self._check_window_binding():
            return

        # 🔧 在任务执行前检查并更新窗口句柄（包含模拟器初始化等待）
        try:
            self._check_and_update_window_handles()
        except Exception as e:
            logger.error(f"检查窗口句柄时出错: {e}")

        # 🔧 更新所有可执行任务的窗口绑定
        for task in self.task_manager.get_executable_tasks():
            self._update_task_window_binding(task)

        # 🔧 关键修复：清除可能的旧状态（参考run_workflow）
        try:
            # 清空输入模拟器缓存
            from utils.input_simulation import global_input_simulator_manager
            global_input_simulator_manager.clear_cache()
            logger.debug(f"_start_all_tasks: 已清空输入模拟器缓存")

            # 重置前台输入管理器的初始化状态（不调用close）
            from utils.foreground_input_manager import get_foreground_input_manager
            foreground_input = get_foreground_input_manager()
            foreground_input._initialization_attempted = False
            logger.debug(f"_start_all_tasks: 已重置前台输入管理器状态")
        except Exception as e:
            logger.warning(f"_start_all_tasks: 清除旧状态时出错: {e}")

        # 确认执行
        mode_text = "同步（串行）" if self.task_manager.execution_mode == 'sync' else "异步（并行）"
        reply = QMessageBox.question(
            self,
            "确认执行",
            f"将以 {mode_text} 模式执行 {executable_count} 个任务，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        logger.info(f"开始执行所有任务，模式: {mode_text}")
        self.task_manager.execute_all()

        # 🔧 新增：更新顶部工具栏按钮状态为"停止"
        self._set_toolbar_to_stop_state()

    def _stop_all_tasks(self):
        """停止所有任务"""
        running_count = self.task_manager.get_running_count()

        if running_count == 0:
            QMessageBox.information(self, "提示", "没有正在运行的任务")
            return

        # 🔧 确认停止
        reply = QMessageBox.question(
            self,
            "确认停止",
            f"确定要停止 {running_count} 个正在运行的任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        logger.info("停止所有任务")
        self.task_manager.stop_all()

    def _update_task_window_binding(self, task):
        """
        更新任务的窗口绑定信息

        Args:
            task: WorkflowTask对象
        """
        # 获取启用的窗口列表
        enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]

        if not enabled_windows:
            logger.warning("没有启用的窗口，无法更新任务窗口绑定")
            return

        # 使用第一个启用的窗口（多窗口模式下，执行器会自己处理）
        target_window = enabled_windows[0]

        # 更新任务的窗口信息
        task.target_hwnd = target_window.get('hwnd')
        task.target_window_title = target_window.get('title', '')
        task.execution_mode = self.config.get('execution_mode', 'background')

        logger.info(f"任务 '{task.name}' 窗口绑定已更新: hwnd={task.target_hwnd}, title='{task.target_window_title}', mode='{task.execution_mode}'")

    def _check_window_binding(self) -> bool:
        """
        检查窗口绑定是否有效

        Returns:
            是否有有效的窗口绑定
        """
        # 检查是否有绑定窗口
        if not hasattr(self, 'bound_windows') or not self.bound_windows:
            QMessageBox.warning(
                self,
                "未绑定窗口",
                "还没有绑定任何窗口！\n\n请先在 '全局设置' 中绑定目标窗口。"
            )
            return False

        # 检查是否有启用的窗口
        enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]

        if not enabled_windows:
            QMessageBox.warning(
                self,
                "没有启用的窗口",
                "所有窗口都已禁用！\n\n请在 '全局设置' 中至少启用一个窗口。"
            )
            return False

        return True

    # 🔧 ========== 多任务执行方法结束 ==========

    def safe_start_tasks(self):
        """安全启动任务，带状态检查和防重复调用保护"""
        logger.warning("🚨 safe_start_tasks 被调用！调用堆栈:")
        import traceback
        logger.warning("".join(traceback.format_stack()))
        logger.warning(" 接收到安全启动请求 (来自热键或UI按钮)...")

        # 🔧 多任务系统：快捷键触发"开始当前任务"
        try:
            task_id = self.workflow_tab_widget.get_current_task_id()

            if task_id is None:
                logger.warning("快捷键启动：没有选中的任务")
                QMessageBox.warning(self, "无法执行", "没有选中的任务，请先导入工作流")
                return

            # 检查窗口绑定
            if not self._check_window_binding():
                return

            # 启动当前任务
            logger.info(f"快捷键启动当前任务: task_id={task_id}")
            self._start_current_task()

        except Exception as e:
            logger.error(f"快捷键启动任务失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(self, "启动失败", f"启动任务时发生错误:\n{str(e)}")

    def safe_stop_tasks(self):
        """安全停止任务，带状态检查和防重复调用保护"""
        logger.info(" 接收到安全停止请求 (来自热键或UI按钮)...")

        # --- ADDED: 额外的防重复检查 ---
        if hasattr(self, '_stop_request_in_progress') and self._stop_request_in_progress:
            logger.warning("safe_stop_tasks: 停止请求正在处理中，忽略重复请求")
            return
        self._stop_request_in_progress = True
        # -------------------------------

        try:
            # 🔧 多任务系统：快捷键触发"停止当前任务"
            task_id = self.workflow_tab_widget.get_current_task_id()

            if task_id is None:
                logger.warning("快捷键停止：没有选中的任务")
                # 尝试停止所有任务
                running_count = self.task_manager.get_running_count()
                if running_count > 0:
                    logger.info(f"快捷键停止所有任务: 共 {running_count} 个")
                    self.task_manager.stop_all()
                else:
                    logger.info("快捷键停止：没有正在运行的任务")
            else:
                # 停止当前任务
                logger.info(f"快捷键停止当前任务: task_id={task_id}")
                self._stop_current_task()

        except Exception as e:
            logger.error(f"快捷键停止任务失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self._stop_request_in_progress = False

    def handle_task_state_change(self, new_state: str):
        """处理任务状态变化的槽函数"""
        logger.info(f"任务状态变化: {new_state}")
        
        # 更新UI状态
        if hasattr(self, 'run_action'):
            if new_state in ["starting", "running"]:
                self.run_action.setEnabled(False)
                self.run_action.setText("运行中...")
            elif new_state == "stopping":
                self.run_action.setEnabled(False)
                self.run_action.setText("停止中...")
            else:  # stopped
                self.run_action.setEnabled(True)
                self.run_action.setText("运行工作流")
        
        # 更新状态显示
        if hasattr(self, 'step_detail_label'):
            status_map = {
                "starting": "正在启动任务...",
                "running": "任务执行中...",
                "stopping": "正在停止任务...",
                "stopped": "等待执行..."
            }
            if new_state in status_map:
                self.step_detail_label.setText(status_map[new_state])

    def safe_delete_card(self, card_id=None):
        """删除卡片（安全检查已移除）"""
        logger.info(f"删除卡片 {card_id}")
        return True
        
    # --- ADDED: Legacy Methods for Hotkey Connections (with enhanced safety) ---
    def start_tasks(self):
        """传统启动方法，现在调用安全启动"""
        logger.info("接收到启动热键信号，调用安全启动方法...")
        self.safe_start_tasks()

    def stop_tasks(self):
        """传统停止方法，现在调用安全停止"""
        logger.info("接收到停止热键信号，调用安全停止方法...")
        self.safe_stop_tasks()
    # --- END ADDED --- 

    def _handle_dpi_recalibration(self):
        """处理DPI重新校准请求"""
        try:
            logger.info("用户请求DPI重新校准")

            # 重新校准所有绑定窗口的DPI
            if hasattr(self, 'bound_windows') and self.bound_windows:
                for window_info in self.bound_windows:
                    if window_info.get('enabled', True):
                        hwnd = window_info.get('hwnd')
                        title = window_info.get('title', '')

                        if hwnd:
                            # 清除DPI缓存，强制重新检测
                            if hasattr(self, 'unified_dpi_handler'):
                                self.unified_dpi_handler.clear_cache(hwnd)

                            logger.info(f"重新校准窗口DPI: {title} (HWND: {hwnd})")

                QMessageBox.information(self, "DPI校准", "DPI重新校准完成")
            else:
                QMessageBox.information(self, "DPI校准", "没有绑定的窗口需要校准")

        except Exception as e:
            logger.error(f"DPI重新校准失败: {e}")
            QMessageBox.warning(self, "错误", f"DPI重新校准失败:\n{str(e)}")

    def _handle_dpi_dismiss(self):
        """处理DPI通知关闭请求"""
        try:
            logger.info("用户关闭DPI变化通知")
            if hasattr(self, 'dpi_notification'):
                self.dpi_notification.hide()
        except Exception as e:
            logger.error(f"关闭DPI通知失败: {e}")

    def _handle_dpi_auto_adjust(self):
        """处理DPI自动调整请求"""
        try:
            logger.info("用户请求DPI自动调整")

            # 触发多窗口分辨率调整
            if hasattr(self, 'bound_windows') and self.bound_windows:
                enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]
                if enabled_windows:
                    logger.info(f"开始自动调整 {len(enabled_windows)} 个窗口")
                    self._apply_multi_window_resize()
                else:
                    logger.info("没有启用的窗口需要调整")
            else:
                logger.info("没有绑定的窗口需要调整")

        except Exception as e:
            logger.error(f"DPI自动调整失败: {e}")

    def _setup_dpi_monitoring(self):
        """设置DPI监控"""
        try:
            # 初始化统一DPI处理器
            from utils.unified_dpi_handler import get_unified_dpi_handler
            self.unified_dpi_handler = get_unified_dpi_handler()

            # 设置DPI变化回调
            def on_dpi_change(hwnd, old_dpi_info, new_dpi_info, window_title=""):
                old_dpi = old_dpi_info.get('dpi', 96)
                new_dpi = new_dpi_info.get('dpi', 96)
                old_scale = old_dpi_info.get('scale_factor', 1.0)
                new_scale = new_dpi_info.get('scale_factor', 1.0)

                logger.info(f"检测到DPI变化: {old_dpi} DPI ({old_scale:.2f}x) -> {new_dpi} DPI ({new_scale:.2f}x) (窗口: {window_title})")

                # 显示DPI变化通知
                if hasattr(self, 'dpi_notification'):
                    self.dpi_notification.show_notification(old_dpi, new_dpi)

                # 更新状态栏信息
                self._update_step_details(f"检测到DPI变化: {old_scale:.0%} -> {new_scale:.0%}，请重新选择OCR区域以确保准确性")

                # 如果有OCR区域选择器正在运行，提醒用户重新选择
                try:
                    from PySide6.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        self,
                        "DPI变化检测",
                        f"检测到系统DPI从 {old_scale:.0%} 变更为 {new_scale:.0%}。\n\n"
                        f"为确保OCR区域选择和识别的准确性，建议重新选择OCR区域。\n\n"
                        f"是否现在重新调整所有绑定窗口？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        # 重新调整所有绑定窗口
                        self._readjust_all_bound_windows()

                except Exception as e:
                    logger.error(f"显示DPI变化对话框失败: {e}")

            self.unified_dpi_handler.add_dpi_change_callback(on_dpi_change)

            # 启用DPI监控
            self.unified_dpi_handler.enable_monitoring()

            logger.info("DPI监控已设置")

        except Exception as e:
            logger.error(f"设置DPI监控失败: {e}")

    def _readjust_all_bound_windows(self):
        """重新调整所有绑定窗口"""
        try:
            logger.info("开始重新调整所有绑定窗口...")

            # 获取所有绑定的窗口
            bound_windows = []
            if hasattr(self, 'window_selector') and self.window_selector:
                bound_windows = self.window_selector.get_bound_windows()

            if not bound_windows:
                logger.info("没有绑定的窗口需要调整")
                self._update_step_details("没有绑定的窗口需要调整")
                return

            success_count = 0
            total_count = len(bound_windows)

            for window_info in bound_windows:
                try:
                    hwnd = window_info.get('hwnd')
                    title = window_info.get('title', '未知窗口')

                    if hwnd:
                        # 强制刷新窗口DPI信息
                        if hasattr(self, 'unified_dpi_handler'):
                            self.unified_dpi_handler.force_refresh_dpi(hwnd)

                        # 重新调整窗口分辨率
                        from utils.window_resolution_adjuster import WindowResolutionAdjuster
                        adjuster = WindowResolutionAdjuster()

                        # 获取目标分辨率（从配置或默认1280x720）
                        target_width = 1280
                        target_height = 720

                        success = adjuster.adjust_window_resolution(hwnd, target_width, target_height)

                        if success:
                            success_count += 1
                            logger.info(f"成功调整窗口: {title} (HWND: {hwnd})")
                        else:
                            logger.warning(f"调整窗口失败: {title} (HWND: {hwnd})")

                except Exception as e:
                    logger.error(f"调整窗口失败: {e}")

            # 更新状态信息
            if success_count == total_count:
                message = f"成功重新调整所有 {total_count} 个绑定窗口"
                logger.info(message)
                self._update_step_details(message)
            else:
                message = f"重新调整窗口完成: {success_count}/{total_count} 个成功"
                logger.warning(message)
                self._update_step_details(message)

        except Exception as e:
            error_msg = f"重新调整绑定窗口失败: {e}"
            logger.error(error_msg)
            self._update_step_details(error_msg)

    def _get_window_dpi_info(self, hwnd: int) -> dict:
        """获取窗口DPI信息并保存到配置"""
        try:
            if hasattr(self, 'unified_dpi_handler'):
                dpi_info = self.unified_dpi_handler.get_window_dpi_info(hwnd, check_changes=False)
            else:
                # 如果DPI处理器未初始化，创建临时实例
                from utils.unified_dpi_handler import get_unified_dpi_handler
                dpi_handler = get_unified_dpi_handler()
                dpi_info = dpi_handler.get_window_dpi_info(hwnd, check_changes=False)

            # 只保存必要的DPI信息到配置文件
            saved_dpi_info = {
                'dpi': dpi_info.get('dpi', 96),
                'scale_factor': dpi_info.get('scale_factor', 1.0),
                'method': dpi_info.get('method', 'Default'),
                'recorded_at': time.time()  # 记录时间戳
            }

            logger.info(f"保存窗口DPI信息: HWND={hwnd}, DPI={saved_dpi_info['dpi']}, 缩放={saved_dpi_info['scale_factor']:.2f}")
            return saved_dpi_info

        except Exception as e:
            logger.warning(f"获取窗口DPI信息失败 (HWND: {hwnd}): {e}")
            # 返回默认DPI信息
            return {
                'dpi': 96,
                'scale_factor': 1.0,
                'method': 'Default',
                'recorded_at': time.time()
            }

    def _apply_saved_dpi_info(self, window_info: dict, hwnd: int):
        """应用保存的DPI信息"""
        try:
            saved_dpi_info = window_info.get('dpi_info')
            if not saved_dpi_info:
                logger.debug(f"窗口没有保存的DPI信息: HWND={hwnd}")
                return

            # 获取当前DPI信息
            current_dpi_info = self._get_window_dpi_info(hwnd)

            saved_dpi = saved_dpi_info.get('dpi', 96)
            current_dpi = current_dpi_info.get('dpi', 96)

            # 检查DPI是否发生变化
            if abs(saved_dpi - current_dpi) > 1:
                logger.warning(f"检测到DPI变化: 保存时={saved_dpi}, 当前={current_dpi} (HWND: {hwnd})")

                # 显示DPI变化通知
                if hasattr(self, 'dpi_notification'):
                    self.dpi_notification.show_notification(saved_dpi, current_dpi)

                # 更新保存的DPI信息
                window_info['dpi_info'] = current_dpi_info

                # 保存更新后的配置
                self._save_config_with_updated_dpi()
            else:
                logger.debug(f"DPI无变化: {current_dpi} (HWND: {hwnd})")

        except Exception as e:
            logger.error(f"应用DPI信息失败 (HWND: {hwnd}): {e}")

    def _force_refresh_dpi_info(self, window_info: dict, hwnd: int):
        """强制刷新DPI信息，不使用缓存的旧信息"""
        try:
            logger.info(f"强制刷新窗口DPI信息 (HWND: {hwnd})")

            # 清除DPI缓存
            if hasattr(self, 'unified_dpi_handler'):
                self.unified_dpi_handler.clear_cache(hwnd)
                logger.debug(f"已清除窗口 {hwnd} 的DPI缓存")

            # 重新检测当前DPI信息
            current_dpi_info = self._get_window_dpi_info(hwnd)

            # 更新窗口信息中的DPI数据
            old_dpi_info = window_info.get('dpi_info', {})
            window_info['dpi_info'] = current_dpi_info

            # 记录DPI变化
            old_dpi = old_dpi_info.get('dpi', 96)
            current_dpi = current_dpi_info.get('dpi', 96)

            if abs(old_dpi - current_dpi) > 1:
                logger.info(f"检测到DPI变化: {old_dpi} -> {current_dpi} (HWND: {hwnd})")
                # 保存更新后的配置
                self._save_config_with_updated_dpi()
            else:
                logger.debug(f"DPI无变化: {current_dpi} (HWND: {hwnd})")

        except Exception as e:
            logger.error(f"强制刷新DPI信息失败 (HWND: {hwnd}): {e}")

    def _save_config_with_updated_dpi(self):
        """保存更新后的DPI配置"""
        try:
            # 更新配置字典
            self.config['bound_windows'] = self.bound_windows

            # 保存到文件
            from main import save_config
            save_config(self.config)
            logger.info("已更新配置文件中的DPI信息")

        except Exception as e:
            logger.error(f"保存DPI配置失败: {e}")

    def _save_bound_windows_config(self):
        """保存绑定窗口配置到文件"""
        try:
            # 更新配置字典中的绑定窗口信息
            self.config['bound_windows'] = self.bound_windows

            # 保存到文件
            from main import save_config
            save_config(self.config)
            logger.info(f"✅ 已保存绑定窗口配置到文件，共 {len(self.bound_windows)} 个窗口")

        except Exception as e:
            logger.error(f"保存绑定窗口配置失败: {e}")

    def start_dpi_monitoring(self):
        """启动DPI监控"""
        try:
            if hasattr(self, 'unified_dpi_handler'):
                self.unified_dpi_handler.enable_monitoring(True)
                logger.info("DPI监控已启动")
            else:
                logger.warning("统一DPI处理器未初始化，无法启动监控")
        except Exception as e:
            logger.error(f"启动DPI监控失败: {e}")

    def stop_dpi_monitoring(self):
        """停止DPI监控"""
        try:
            if hasattr(self, 'unified_dpi_handler'):
                self.unified_dpi_handler.disable_monitoring()
                logger.info("DPI监控已停止")
        except Exception as e:
            logger.error(f"停止DPI监控失败: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """处理窗口关闭事件"""
        logger.warning("🚨 MainWindow closeEvent triggered!")

        # 停止DPI监控
        self.stop_dpi_monitoring()

        # 🔧 检查是否有未保存的任务
        if hasattr(self, 'workflow_tab_widget') and self.workflow_tab_widget.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "有任务包含未保存的更改。是否保存所有更改？",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Save:
                # 保存所有已修改的任务
                saved_count = self.task_manager.save_all_modified()
                logger.info(f"已保存 {saved_count} 个任务")
            elif reply == QMessageBox.StandardButton.Cancel:
                logger.info("用户取消退出操作")
                event.ignore()
                return
            # Discard 则继续关闭

        # 🔧 停止所有正在运行的任务
        running_count = self.task_manager.get_running_count()
        if running_count > 0:
            logger.info(f"检测到 {running_count} 个正在运行的任务，发送停止请求...")
            self.task_manager.stop_all()

        logger.info("closeEvent: 接受关闭事件，准备退出应用程序...")
        event.accept()

        # 显式调用 QApplication.quit()
        QApplication.instance().quit()

    # --- ADDED: Confirmation method for clearing workflow ---
    def confirm_and_clear_workflow(self):
        """Shows a confirmation dialog before clearing the workflow scene."""
        # 首先检查是否有任务正在运行
        if (self.executor is not None and 
            self.executor_thread is not None and 
            self.executor_thread.isRunning()):
            
            logger.warning("尝试在任务运行期间清空工作流")
            reply = QMessageBox.question(
                self, 
                "任务正在运行", 
                "检测到工作流正在执行中。\n\n继续清空会导致正在运行的任务失去界面显示，可能造成状态混乱。\n\n是否要先停止任务再清空？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 用户选择先停止任务
                logger.info("用户选择先停止任务再清空工作流")
                self.request_stop_workflow()
                QMessageBox.information(
                    self, 
                    "操作说明", 
                    "已发送停止请求。请等待任务停止后再次尝试清空工作流。"
                )
                return
            elif reply == QMessageBox.StandardButton.No:
                # 用户选择强制清空，继续询问确认
                logger.warning("用户选择在任务运行期间强制清空工作流")
                pass  # 继续下面的确认对话框
            else:
                # 用户取消操作
                logger.info("用户取消了清空工作流操作")
                return
        
        # 正常的清空确认对话框
        reply = QMessageBox.question(self, 
                                     "确认清空", 
                                     "您确定要清空当前工作流吗？\n所有未保存的更改将丢失，此操作无法撤销。",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No) # Default to No

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("用户确认清空工作流。")
            self.workflow_view.clear_workflow()
            # Optionally reset save path and unsaved changes flag after clearing
            self.current_save_path = None
            self.unsaved_changes = False # A new scene is not 'unsaved' initially
            self._update_main_window_title()
        else:
            logger.info("用户取消了清空工作流操作。") 

    # --- ADDED: Slot to mark changes as unsaved --- 
    def _mark_unsaved_changes(self, *args):
        """Sets the unsaved changes flag and updates the window title."""
        # <<< ADDED: Debugging log >>>
        # Try to get the sender object name if available
        sender_info = "Unknown Source"
        sender = self.sender() # Get the object that emitted the signal
        if sender:
            sender_info = f"Sender: {type(sender).__name__} {getattr(sender, 'objectName', lambda: '')()}"
            
        print(f"--- DEBUG: _mark_unsaved_changes called ({sender_info}, Args: {args}) ---")
        # <<< END ADDED >>>
        if not self.unsaved_changes:
            logger.debug("_mark_unsaved_changes: Marking changes as unsaved.")
            self.unsaved_changes = True
            self._update_main_window_title()
        # else: # Optional: log if already marked
        #    logger.debug("_mark_unsaved_changes: Changes already marked as unsaved.") 

    # <<< REVISED AGAIN: Show only selected card title in status bar >>>
    def update_status_bar_for_selection(self):
        """Updates the bottom status label to show only the selected card's title."""
        selected_items = self.workflow_view.scene.selectedItems()
        
        if len(selected_items) == 1 and isinstance(selected_items[0], TaskCard):
            card = selected_items[0]
            final_text = f"选中: {card.title}"
            self.step_detail_label.setText(final_text)
            self.step_detail_label.setToolTip("") # Clear tooltip from status bar
        else:
            # Resetting logic remains the same
            current_text = self.step_detail_label.text()
            if "执行成功" not in current_text and "执行失败" not in current_text and "错误" not in current_text:
                 self.step_detail_label.setText("等待执行...")

    def _run_multi_window_workflow(self):
        """执行多窗口工作流"""
        logger.info("开始多窗口工作流执行")

        # 检查是否有启用的窗口
        enabled_windows = [w for w in self.bound_windows if w.get('enabled', True)]
        if not enabled_windows:
            QMessageBox.warning(self, "提示", "没有启用的窗口，请在全局设置中添加并启用窗口")
            return

        # 检查工作流是否为空
        workflow_data = self.workflow_view.serialize_workflow()
        if not workflow_data or not workflow_data.get("cards"):
            QMessageBox.warning(self, "提示", "工作流为空，请添加任务卡片")
            return

        # 调试：检查工作流数据
        cards_data = workflow_data.get("cards", [])
        logger.info(f"多窗口执行: 工作流包含 {len(cards_data)} 个卡片")

        # 检查是否有起点卡片
        start_cards = [card for card in cards_data if card.get('task_type') == '起点']
        logger.info(f"多窗口执行: 找到 {len(start_cards)} 个起点卡片")

        if len(start_cards) == 0:
            logger.error("多窗口执行: 未找到起点卡片")
            logger.debug(f"多窗口执行: 所有卡片类型: {[(card.get('id'), card.get('task_type')) for card in cards_data]}")
            QMessageBox.warning(self, "提示", "工作流中必须包含一个'起点'卡片才能执行")
            return
        elif len(start_cards) > 1:
            logger.error(f"多窗口执行: 找到多个起点卡片 ({len(start_cards)} 个)")
            QMessageBox.warning(self, "提示", f"工作流中只能包含一个'起点'卡片，当前有 {len(start_cards)} 个")
            return
        else:
            logger.info(f"多窗口执行: 起点卡片验证通过，ID: {start_cards[0].get('id')}")

        # 保存工作流（如果需要）
        if not self._save_before_execution():
            return

        # 多窗口模式强制使用后台模式
        if self.current_execution_mode != 'background':
            reply = QMessageBox.question(
                self, "执行模式确认",
                "多窗口模式需要使用后台执行模式，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 工具 关键修复：先清理旧的多窗口执行器
        if hasattr(self, 'multi_executor') and self.multi_executor:
            logger.info("扫帚 清理旧的多窗口执行器...")
            try:
                # 断开旧的信号连接
                self.multi_executor.execution_progress.disconnect()
                self.multi_executor.execution_completed.disconnect()
                if hasattr(self.multi_executor, 'card_executing'):
                    self.multi_executor.card_executing.disconnect()
                if hasattr(self.multi_executor, 'card_finished'):
                    self.multi_executor.card_finished.disconnect()
                if hasattr(self.multi_executor, 'error_occurred'):
                    self.multi_executor.error_occurred.disconnect()

                # 清理执行器资源
                if hasattr(self.multi_executor, 'cleanup'):
                    self.multi_executor.cleanup()

                logger.info("成功 旧的多窗口执行器已清理")
            except Exception as e:
                logger.warning(f"清理旧执行器时出错: {e}")

        # 创建统一多窗口执行器
        try:
            from .unified_multi_window_executor import UnifiedMultiWindowExecutor
            logger.info("启动 创建新的多窗口执行器...")
            self.multi_executor = UnifiedMultiWindowExecutor(self)

            # 工具 关键修复：添加所有窗口（包括禁用的），正确传递enabled状态
            successfully_added = 0
            failed_windows = []

            # 遍历所有绑定的窗口，而不仅仅是启用的窗口
            logger.info(f"搜索 检查绑定窗口状态，总数: {len(self.bound_windows)}")
            for i, window_info in enumerate(self.bound_windows):
                window_title = window_info['title']
                window_enabled = window_info.get('enabled', True)
                logger.info(f"  窗口{i+1}: {window_title}, enabled={window_enabled}, hwnd={window_info.get('hwnd')}")

                # 优先使用绑定窗口中保存的句柄
                hwnd = window_info.get('hwnd')
                if hwnd:
                    # 验证句柄是否仍然有效
                    try:
                        import win32gui
                        if win32gui.IsWindow(hwnd):
                            logger.info(f"使用保存的窗口句柄: {window_title} (HWND: {hwnd}), 启用: {window_enabled}")

                            # 工具 强制重新检测DPI信息，不使用保存的旧信息
                            self._force_refresh_dpi_info(window_info, hwnd)
                        else:
                            logger.warning(f"保存的句柄无效，重新查找: {window_title} (HWND: {hwnd})")
                            hwnd = None
                    except:
                        logger.warning(f"无法验证句柄，重新查找: {window_title}")
                        hwnd = None

                # 工具 关键修复：多窗口模式下不重新查找窗口，避免窗口混乱
                if not hwnd:
                    logger.error(f"错误 多窗口模式下窗口句柄无效且无法恢复: {window_title}")
                    logger.error(f"   建议：重新绑定该窗口以获取正确的句柄")
                    failed_windows.append(window_title)
                    continue

                if hwnd:
                    # 工具 关键修复：传递正确的enabled状态
                    self.multi_executor.add_window(window_title, hwnd, window_enabled)
                    if window_enabled:
                        successfully_added += 1
                    logger.info(f"添加窗口到多窗口执行器: {window_title} (HWND: {hwnd}), 启用: {window_enabled}")
                else:
                    failed_windows.append(window_title)
                    logger.warning(f"未找到窗口: {window_title}")

            # 检查是否有成功添加的窗口
            if successfully_added == 0:
                error_msg = f"无法找到任何绑定的窗口！\n\n"
                error_msg += f"图表 状态统计:\n"
                error_msg += f"   启用的窗口数量: {len(enabled_windows)}\n"
                error_msg += f"   成功找到: 0 个\n"
                error_msg += f"   未找到: {len(failed_windows)} 个\n\n"
                error_msg += f"错误 未找到的窗口:\n"
                for i, window in enumerate(failed_windows, 1):
                    error_msg += f"   {i}. {window}\n"
                error_msg += f"\n灯泡 建议解决方案:\n"
                error_msg += f"   1. 检查目标窗口是否已打开\n"
                error_msg += f"   2. 在全局设置中重新绑定窗口\n"
                error_msg += f"   3. 确认窗口标题是否正确\n"
                error_msg += f"   4. 尝试使用'添加模拟器'功能重新添加"

                # 创建自定义消息框，包含打开设置的按钮
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("多窗口执行失败")
                msg_box.setText(error_msg)
                msg_box.setIcon(QMessageBox.Icon.Warning)

                # 添加按钮
                settings_button = msg_box.addButton("打开全局设置", QMessageBox.ButtonRole.ActionRole)
                close_button = msg_box.addButton("关闭", QMessageBox.ButtonRole.RejectRole)

                msg_box.exec()

                # 如果用户点击了设置按钮，打开全局设置
                if msg_box.clickedButton() == settings_button:
                    self.open_global_settings()

                return

            # 如果部分窗口未找到，给出警告
            if failed_windows:
                warning_msg = f"部分窗口未找到，是否继续执行？\n\n"
                warning_msg += f"图表 执行状态:\n"
                warning_msg += f"   成功 可执行窗口: {successfully_added} 个\n"
                warning_msg += f"   错误 未找到窗口: {len(failed_windows)} 个\n\n"
                warning_msg += f"错误 未找到的窗口:\n"
                for i, window in enumerate(failed_windows, 1):
                    warning_msg += f"   {i}. {window}\n"
                warning_msg += f"\n警告 将仅在 {successfully_added} 个可用窗口中执行任务。\n"
                warning_msg += f"是否继续执行？"

                reply = QMessageBox.question(
                    self, "部分窗口未找到", warning_msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # 连接信号
            logger.info("🔗 连接多窗口执行器信号...")
            self.multi_executor.execution_progress.connect(self._on_multi_window_progress)
            self.multi_executor.execution_completed.connect(self._on_multi_window_completed)
            logger.info("成功 已连接多窗口执行器的主要信号 (progress, completed)")

            # 工具 连接卡片状态信号以支持闪烁效果
            if hasattr(self.multi_executor, 'card_executing'):
                self.multi_executor.card_executing.connect(self._handle_card_executing)
                self.multi_executor.card_finished.connect(self._handle_card_finished)
                self.multi_executor.error_occurred.connect(self._handle_error_occurred)
                logger.info("成功 已连接多窗口执行器的卡片状态信号")
            else:
                logger.warning("警告 多窗口执行器没有卡片状态信号")

            # 开始执行
            delay_ms = self.multi_window_delay

            # 工具 关键修复：强制使用并行模式和后台执行
            from .unified_multi_window_executor import ExecutionMode
            execution_mode = ExecutionMode.PARALLEL  # 强制并行模式

            logger.info(f"靶心 多窗口执行配置: 模式={execution_mode.value}, 延迟={delay_ms}ms, 窗口数={successfully_added}")

            # 工具 异步执行优化：优先使用异步执行，回退到同步执行
            execution_success = False

            # 检查是否支持异步执行
            logger.warning(f"🔍 检查异步模式: hasattr={hasattr(self.multi_executor, '_async_mode')}")
            if hasattr(self.multi_executor, '_async_mode'):
                logger.warning(f"🔍 异步模式状态: {self.multi_executor._async_mode}")

            if hasattr(self.multi_executor, '_async_mode') and self.multi_executor._async_mode:
                logger.warning("🚀 使用异步执行模式启动多窗口任务")
                try:
                    # 使用 QTimer 来在事件循环中执行异步任务
                    import asyncio
                    from PySide6.QtCore import QTimer

                    # 创建异步执行任务
                    async def async_execution():
                        return await self.multi_executor.start_execution_async(
                            workflow_data, delay_ms, execution_mode, self.bound_windows
                        )

                    # 在Qt事件循环中执行异步任务
                    if hasattr(asyncio, 'get_event_loop'):
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 如果事件循环正在运行，创建任务
                                task = asyncio.create_task(async_execution())
                                # 使用QTimer来检查任务完成状态
                                self._async_execution_task = task
                                self._check_async_execution_timer = QTimer()
                                self._check_async_execution_timer.timeout.connect(self._check_async_execution_status)
                                self._check_async_execution_timer.start(100)  # 每100ms检查一次
                                execution_success = True
                                logger.info("异步执行任务已创建")
                            else:
                                # 🎯 关键修复：不使用run_until_complete，改用QTimer异步执行
                                logger.warning("🔧 事件循环未运行，改用QTimer异步执行避免干扰Qt事件循环")
                                task = asyncio.create_task(async_execution())
                                self._async_execution_task = task
                                self._check_async_execution_timer = QTimer()
                                self._check_async_execution_timer.timeout.connect(self._check_async_execution_status)
                                self._check_async_execution_timer.start(100)  # 每100ms检查一次
                                execution_success = True
                                logger.warning("🔧 已创建异步任务和检查定时器")

                                # 立即启动异步任务检查
                                self._check_async_execution_status()
                        except Exception as e:
                            logger.warning(f"异步执行失败，回退到同步模式: {e}")
                            execution_success = False
                    else:
                        logger.warning("asyncio不可用，回退到同步模式")
                        execution_success = False

                except Exception as e:
                    logger.warning(f"异步执行初始化失败，回退到同步模式: {e}")
                    execution_success = False

            # 如果异步执行失败或不可用，使用同步执行
            if not execution_success:
                logger.warning("⚠️ 异步执行失败，回退到同步执行模式启动多窗口任务")
                execution_success = self.multi_executor.start_execution(
                    workflow_data, delay_ms, execution_mode, self.bound_windows
                )

            if execution_success:
                logger.info(f"多窗口执行已启动，共 {successfully_added} 个窗口，延迟 {delay_ms}ms")

                # 正确设置执行状态和停止按钮
                self._setup_multi_window_stop_button()

                # 工具 删除弹窗：直接在日志中记录启动信息，不显示弹窗
                # QMessageBox.information(self, "执行开始", f"已在 {successfully_added} 个窗口开始执行任务")
            else:
                logger.error("多窗口执行启动失败")
                QMessageBox.warning(self, "执行失败", "多窗口执行启动失败，请检查窗口状态")
                self._reset_run_button()

        except ImportError:
            logger.error("无法导入多窗口执行器")
            QMessageBox.critical(self, "功能不可用", "多窗口执行功能不可用，请检查相关模块")
        except Exception as e:
            logger.error(f"多窗口执行启动失败: {e}")
            QMessageBox.critical(self, "执行失败", f"多窗口执行启动失败:\n{e}")
            self._reset_run_button()

    def _check_async_execution_status(self):
        """检查异步执行状态"""
        logger.warning("🔍 _check_async_execution_status 被调用")

        if hasattr(self, '_async_execution_task'):
            task = self._async_execution_task
            logger.warning(f"🔍 异步任务状态: done={task.done()}")

            if task.done():
                logger.warning("🔍 异步任务已完成，开始清理...")

                # 任务完成，停止定时器
                if hasattr(self, '_check_async_execution_timer'):
                    logger.warning("🔍 停止并删除定时器...")
                    self._check_async_execution_timer.stop()
                    self._check_async_execution_timer.deleteLater()
                    delattr(self, '_check_async_execution_timer')
                    logger.warning("🔍 定时器已清理")

                try:
                    logger.warning("🔍 获取异步任务结果...")
                    result = task.result()
                    logger.warning(f"🔍 异步任务结果: {result}")

                    if result:
                        logger.warning("🔍 异步多窗口执行成功，设置停止按钮...")
                        # 正确设置执行状态和停止按钮
                        self._setup_multi_window_stop_button()
                        logger.warning("🔍 停止按钮设置完成")
                    else:
                        logger.error("异步多窗口执行失败")
                        QMessageBox.warning(self, "执行失败", "异步多窗口执行失败，请检查窗口状态")
                        self._reset_run_button()

                except Exception as e:
                    logger.error(f"异步多窗口执行异常: {e}")
                    QMessageBox.warning(self, "执行异常", f"异步多窗口执行异常:\n{e}")
                    self._reset_run_button()

                # 清理任务引用
                logger.warning("🔍 清理异步任务引用...")
                delattr(self, '_async_execution_task')
                logger.warning("🔍 异步任务清理完成")
        else:
            logger.warning("🔍 没有异步任务需要检查")

    def _save_before_execution(self):
        """执行前保存工作流"""
        save_successful = False
        if self.current_save_path:
            logger.info("运行前尝试保存和备份工作流...")
            save_successful = self.perform_save(self.current_save_path)
            if not save_successful:
                logger.warning("运行前保存/备份失败，中止执行。")
                QMessageBox.warning(self, "保存失败", "运行前保存或备份工作流失败，请检查日志或手动保存后再试。")
                return False
        else:
            logger.info("运行前未找到保存路径，提示用户另存为...")
            reply = QMessageBox.question(self, "需要保存",
                                         "工作流尚未保存。是否先保存工作流再运行？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                         QMessageBox.StandardButton.Yes)
            if reply == QMessageBox.StandardButton.Yes:
                self.save_workflow_as()
                if self.current_save_path:
                    save_successful = True
                else:
                    logger.info("用户取消了另存为操作，中止执行。")
                    return False
            else:
                logger.info("用户选择不保存，中止执行。")
                return False

        return save_successful

    def _on_multi_window_progress(self, window_title: str, status: str):
        """处理多窗口执行进度"""
        logger.info(f"多窗口进度 - {window_title}: {status}")
        self.step_detail_label.setText(f"多窗口执行: {window_title} - {status}")

    def _setup_multi_window_stop_button(self):
        """设置多窗口执行时的停止按钮"""
        logger.warning("🔧 开始设置多窗口停止按钮...")

        # 断开之前的信号连接
        try:
            logger.warning("🔧 断开之前的信号连接...")
            self.run_action.triggered.disconnect()
            logger.warning("🔧 信号连接已断开")
        except (TypeError, RuntimeError) as e:
            logger.warning(f"🔧 断开信号连接时出现异常（正常）: {e}")

        # 设置按钮为停止状态
        logger.warning("🔧 设置按钮状态...")
        self.run_action.setEnabled(True)
        self.run_action.setText("停止多窗口执行")
        self.run_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.run_action.setToolTip("停止所有窗口的执行 (F10)")
        logger.warning("🔧 按钮状态设置完成")

        # 连接到停止方法
        logger.warning("🔧 连接停止方法...")
        self.run_action.triggered.connect(self.request_stop_workflow)
        logger.warning("🔧 停止方法连接完成")

        logger.warning("🔧 多窗口停止按钮已设置完成")

    def _on_multi_window_completed(self, success: bool, message: str):
        """处理多窗口执行完成 - 增强版本"""
        logger.warning(f"🎯 _on_multi_window_completed 被调用: 成功={success}, 消息={message}")
        logger.warning("🎯 调用堆栈:")
        import traceback
        logger.warning("".join(traceback.format_stack()))

        try:
            # 工具 关键修复：确保停止管理器正确清理
            if hasattr(self, 'multi_executor') and hasattr(self.multi_executor, 'stop_integration'):
                logger.info("清理增强停止管理器...")
                self.multi_executor.stop_integration.cleanup()

            # --- ADDED: 确认任务停止状态 ---
            if self.task_state_manager:
                self.task_state_manager.confirm_stopped()
                logger.info("多窗口任务完成，状态管理器已确认停止")
            # ----------------------------

            # 任务完成后自动调用停止按钮逻辑来初始化状态
            logger.info("任务完成，自动重置状态...")
            self._auto_reset_after_completion(success, message)

        except Exception as e:
            logger.error(f"多窗口完成处理失败: {e}", exc_info=True)
            # 确保UI状态重置
            self._reset_run_button()
            # 确保状态管理器重置
            if self.task_state_manager:
                self.task_state_manager.reset_state()

    def _auto_reset_after_completion(self, success: bool, message: str):
        """任务完成后自动重置状态"""
        # 防重复调用机制
        if hasattr(self, '_auto_reset_in_progress') and self._auto_reset_in_progress:
            logger.debug("自动重置已在进行中，跳过重复调用")
            return

        self._auto_reset_in_progress = True
        try:
            logger.info(f"自动重置状态: 成功={success}, 消息={message}")

            # 重置所有卡片状态和停止闪烁效果
            logger.info("重置所有卡片状态和停止闪烁效果")
            self.workflow_view.reset_card_states()

            # 额外确保停止所有闪烁效果
            try:
                for card_id, card in self.workflow_view.cards.items():
                    if card and hasattr(card, 'stop_flash'):
                        card.stop_flash()
                logger.debug("已确保停止所有卡片的闪烁效果")
            except Exception as e:
                logger.warning(f"停止卡片闪烁效果失败: {e}")

            # 重置运行按钮
            self._reset_run_button()

            # --- ADDED: 确认任务停止状态 ---
            if self.task_state_manager:
                self.task_state_manager.confirm_stopped()
                logger.info("任务状态管理器已确认停止（多窗口完成）")
            # ----------------------------

            # 清理多窗口执行器
            if hasattr(self, 'multi_executor') and self.multi_executor:
                try:
                    # 如果有增强停止管理器，清理它
                    if hasattr(self.multi_executor, 'stop_integration'):
                        self.multi_executor.stop_integration.cleanup()

                    # 重置执行器状态
                    self.multi_executor.is_running = False
                    logger.debug("多窗口执行器状态已重置")

                except Exception as e:
                    logger.error(f"清理多窗口执行器失败: {e}")

            # 显示完成通知
            if success:
                logger.info(f"成功 任务执行完成: {message}")
            else:
                logger.warning(f"警告 任务执行失败: {message}")

        except Exception as e:
            logger.error(f"自动重置状态失败: {e}")
        finally:
            # 重置防重复调用标志
            self._auto_reset_in_progress = False

    # --- ADDED: Parameter panel methods ---
    def _connect_parameter_panel_signals(self):
        """连接参数面板相关信号"""
        # 🔧 检查是否有当前工作流
        if not self.workflow_view or not hasattr(self.workflow_view, 'cards'):
            return

        # 连接工作流视图中卡片的参数编辑请求
        for card in self.workflow_view.cards.values():
            self._connect_card_parameter_signals(card)

    def _on_card_added(self, card):
        """处理新卡片添加事件"""
        logger.info(f"新卡片添加: {card.card_id}")
        self._connect_card_parameter_signals(card)

    def _on_card_deleted(self, card_id: int):
        """处理卡片删除事件 - 清理相关资源防止崩溃"""
        logger.info(f"处理卡片删除: {card_id}")

        try:
            # 1. 清理工作流上下文中的卡片数据
            from task_workflow.workflow_context import clear_card_ocr_data, get_workflow_context

            # 清理默认工作流上下文
            clear_card_ocr_data(card_id)

            # 也清理可能存在的其他工作流上下文
            try:
                from task_workflow.workflow_context import _context_manager
                for workflow_id in list(_context_manager.contexts.keys()):
                    clear_card_ocr_data(card_id, workflow_id)
            except Exception as multi_e:
                logger.debug(f"清理多工作流上下文时出错: {multi_e}")

            logger.debug(f"已清理卡片 {card_id} 的工作流上下文数据")

            # 2. 清理OCR服务池中的相关数据
            try:
                from services.multi_ocr_pool import get_multi_ocr_pool
                ocr_pool = get_multi_ocr_pool()
                if ocr_pool and hasattr(ocr_pool, 'cleanup_card_data'):
                    ocr_pool.cleanup_card_data(card_id)
                    logger.debug(f"已清理卡片 {card_id} 的OCR服务池数据")
            except Exception as ocr_e:
                logger.debug(f"清理OCR服务池数据时出错: {ocr_e}")

            # 3. 清理执行器中的持久化计数器
            if hasattr(self, 'executor') and self.executor:
                try:
                    if hasattr(self.executor, '_persistent_counters'):
                        # 清理与该卡片相关的计数器
                        keys_to_remove = []
                        for key in self.executor._persistent_counters.keys():
                            if str(card_id) in str(key):
                                keys_to_remove.append(key)

                        for key in keys_to_remove:
                            del self.executor._persistent_counters[key]
                            logger.debug(f"已清理执行器计数器: {key}")

                except Exception as exec_e:
                    logger.debug(f"清理执行器数据时出错: {exec_e}")

            # 4. 强制垃圾回收，清理可能的循环引用
            import gc
            gc.collect()

            logger.info(f"卡片 {card_id} 删除后清理完成")

        except Exception as e:
            logger.error(f"处理卡片 {card_id} 删除时发生错误: {e}", exc_info=True)
            # 即使清理失败也不应该阻止删除操作

    def _connect_card_parameter_signals(self, card):
        """连接单个卡片的参数编辑信号"""
        # 断开可能存在的旧连接
        try:
            card.edit_settings_requested.disconnect()
        except:
            pass

        # 连接到参数面板显示
        card.edit_settings_requested.connect(self._show_parameter_panel)

    def _show_parameter_panel(self, card_id: int):
        """显示参数面板"""
        logger.info(f"显示卡片 {card_id} 的参数面板")

        # 获取卡片信息
        card = self.workflow_view.cards.get(card_id)
        if not card:
            logger.warning(f"未找到卡片 {card_id}")
            return

        # 获取工作流卡片信息
        workflow_info = {}
        for seq_id, card_obj in enumerate(self.workflow_view.cards.values()):
            workflow_info[seq_id] = (card_obj.task_type, card_obj.card_id)

        # 获取目标窗口句柄
        target_window_hwnd = None
        if hasattr(self, 'config') and self.config:
            # 多窗口模式：从绑定窗口获取句柄
            bound_windows = self.config.get('bound_windows', [])
            if bound_windows:
                # 获取第一个启用的窗口句柄
                for window_info in bound_windows:
                    if window_info.get('enabled', True):
                        target_window_hwnd = window_info.get('hwnd')
                        if target_window_hwnd:
                            logger.info(f"从多窗口配置获取第一个启用窗口句柄: {target_window_hwnd}")
                            break

                # 如果没有启用的窗口，使用第一个窗口
                if not target_window_hwnd and bound_windows:
                    target_window_hwnd = bound_windows[0].get('hwnd')
                    if target_window_hwnd:
                        logger.info(f"从多窗口配置获取第一个窗口句柄: {target_window_hwnd}")

            # 单窗口模式：通过窗口标题查找句柄
            if not target_window_hwnd:
                target_window_title = self.config.get('target_window_title')
                if target_window_title:
                    from utils.window_finder import WindowFinder
                    target_window_hwnd = WindowFinder.find_window(target_window_title, "ldplayer")
                    if target_window_hwnd:
                        logger.info(f"单窗口模式通过标题找到句柄: {target_window_hwnd}")

        elif hasattr(self, 'runner') and self.runner:
            target_window_hwnd = getattr(self.runner, 'target_hwnd', None)

        # 显示参数面板
        self.parameter_panel.show_parameters(
            card_id=card_id,
            task_type=card.task_type,
            param_definitions=card.param_definitions,
            current_parameters=card.parameters,
            workflow_cards_info=workflow_info,
            images_dir=self.images_dir,
            target_window_hwnd=target_window_hwnd
        )

        # 标记参数面板为可见状态
        self._parameter_panel_visible = True

    def _on_parameter_changed(self, card_id: int, new_parameters: Dict[str, Any]):
        """处理参数更改"""
        logger.info(f"接收到参数更改信号: 卡片 {card_id}, 参数: {new_parameters}")

        # 调试延迟模式相关参数
        if 'delay_mode' in new_parameters:
            print(f"调试主窗口参数更新: 卡片 {card_id}, delay_mode={new_parameters['delay_mode']}")

        card = self.workflow_view.cards.get(card_id)
        if card:
            logger.info(f"找到卡片 {card_id}，当前参数: {card.parameters}")

            # 调试延迟模式参数更新前后的状态
            if 'delay_mode' in new_parameters:
                old_delay_mode = card.parameters.get('delay_mode', '未设置')
                print(f"调试TaskCard参数更新: delay_mode 从 '{old_delay_mode}' 更新为 '{new_parameters['delay_mode']}'")

            card.parameters.update(new_parameters)
            logger.info(f"更新后参数: {card.parameters}")

            # 调试更新后的状态
            if 'delay_mode' in new_parameters:
                print(f"调试TaskCard参数更新完成: delay_mode={card.parameters.get('delay_mode')}")

            # 清除工具提示缓存，强制重新生成
            if hasattr(card, '_tooltip_needs_update'):
                card._tooltip_needs_update = True
            if hasattr(card, '_cached_tooltip'):
                delattr(card, '_cached_tooltip')

            # 检查是否有影响连线的参数更改
            connection_affecting_params = ['next_step_card_id', 'success_jump_target_id', 'failure_jump_target_id', 'on_success', 'on_failure']
            needs_connection_update = any(param in new_parameters for param in connection_affecting_params)

            if needs_connection_update:
                logger.info(f"检测到影响连线的参数更改，触发连线更新: {[p for p in connection_affecting_params if p in new_parameters]}")
                # 触发工作流视图的连线更新
                self.workflow_view.update_card_sequence_display()

            # 标记为未保存
            self._mark_unsaved_changes()
            logger.info(f"卡片 {card_id} 参数已成功更新并标记为未保存")
        else:
            logger.error(f"未找到卡片 {card_id}，可用卡片: {list(self.workflow_view.cards.keys())}")

    def _on_parameter_panel_closed(self):
        """处理参数面板关闭"""
        logger.info("参数面板已关闭")
        self._parameter_panel_visible = False

    def moveEvent(self, event):
        """主窗口移动时，重新定位参数面板"""
        super().moveEvent(event)
        if self._parameter_panel_visible and hasattr(self, 'parameter_panel'):
            # 检查参数面板是否正在被拖拽，如果是则跳过重新定位
            if hasattr(self.parameter_panel, '_is_dragging') and self.parameter_panel._is_dragging:
                return
            # 延迟重新定位，避免移动过程中频繁更新
            QTimer.singleShot(50, self.parameter_panel._position_panel)

    def resizeEvent(self, event):
        """主窗口大小改变时，重新定位参数面板"""
        super().resizeEvent(event)
        if self._parameter_panel_visible and hasattr(self, 'parameter_panel'):
            # 延迟重新定位，避免调整大小过程中频繁更新
            QTimer.singleShot(50, self.parameter_panel._position_panel)

    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            # 同步参数面板的窗口状态
            if hasattr(self, 'parameter_panel'):
                self.parameter_panel.sync_window_state(self.windowState())
        elif event.type() == QEvent.Type.ActivationChange:
            # 智能激活同步：保护参数面板输入框焦点
            if hasattr(self, 'parameter_panel'):
                self._smart_sync_parameter_panel_activation()

    def _smart_sync_parameter_panel_activation(self):
        """智能同步参数面板激活状态，保护输入框焦点"""
        if not self.isActiveWindow() or not self.parameter_panel.isVisible():
            return

        # 检查参数面板中是否有输入控件获得焦点
        focus_widget = QApplication.focusWidget()
        if focus_widget and isinstance(focus_widget, (QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit)):
            # 检查焦点控件是否属于参数面板
            widget_parent = focus_widget
            while widget_parent:
                if widget_parent == self.parameter_panel:
                    logger.debug(f"参数面板输入控件 {focus_widget} 获得焦点，跳过激活同步")
                    return
                widget_parent = widget_parent.parent()

        # 如果参数面板已经激活，不需要重复激活
        if self.parameter_panel.isActiveWindow():
            return

        # 保存当前焦点控件
        saved_focus = QApplication.focusWidget()

        # 重新定位参数面板
        self.parameter_panel._position_panel()

        # 使用raise()代替activateWindow()，减少对焦点的影响
        self.parameter_panel.raise_()

        # 如果之前有焦点控件且仍然可用，尝试恢复焦点
        if saved_focus and saved_focus.isVisible() and saved_focus.isEnabled():
            # 使用定时器延迟恢复焦点
            QTimer.singleShot(50, lambda: self._restore_focus_to_widget(saved_focus))

        logger.debug("主窗口激活，智能同步参数面板（保护焦点）")

    def _restore_focus_to_widget(self, widget):
        """恢复焦点到指定控件"""
        try:
            if widget and widget.isVisible() and widget.isEnabled():
                widget.setFocus()
                logger.debug(f"恢复焦点到控件: {widget}")
        except Exception as e:
            logger.debug(f"恢复焦点失败: {e}")

    def check_emulator_windows_and_enable_button(self):
        """检查是否有模拟器窗口，如果没有则直接启用按钮"""
        try:
            import win32gui
            from utils.emulator_detector import detect_emulator_type

            logger.info("🔍 检查模拟器窗口状态...")

            emulator_count = 0

            def enum_windows_callback(hwnd, _):
                nonlocal emulator_count

                if not win32gui.IsWindowVisible(hwnd):
                    return True

                try:
                    # 使用统一的模拟器检测器
                    is_emulator, emulator_type, description = detect_emulator_type(hwnd)

                    if is_emulator:
                        title = win32gui.GetWindowText(hwnd)
                        logger.debug(f"检测到模拟器窗口: {description} - {title}")
                        emulator_count += 1

                except Exception as e:
                    logger.debug(f"检测窗口时出错: {e}")

                return True

            win32gui.EnumWindows(enum_windows_callback, None)
            has_emulator = emulator_count > 0

            if has_emulator:
                logger.info(f"✅ 检测到 {emulator_count} 个模拟器窗口，需要等待ADB初始化完成")
                self._needs_adb_initialization = True
                if hasattr(self, 'run_action'):
                    self.run_action.setText("初始化中...")
                    self.run_action.setToolTip("正在初始化ADB连接池和ADBKeyboard，请稍候...")
                # 🔧 禁用执行面板按钮
                if hasattr(self, 'execution_panel'):
                    self.execution_panel.set_initialization_in_progress(True)
            else:
                logger.info("❌ 未检测到模拟器窗口，直接启用运行按钮")
                self._needs_adb_initialization = False
                self._adb_initialization_completed = True
                if hasattr(self, 'run_action'):
                    self.run_action.setEnabled(True)
                    self.run_action.setText("运行工作流")
                    self.run_action.setToolTip("开始执行当前工作流 (F9)")
                    logger.info("✅ 运行按钮已启用（无需ADB初始化）")
                # 🔧 启用执行面板按钮
                if hasattr(self, 'execution_panel'):
                    self.execution_panel.set_initialization_in_progress(False)

        except Exception as e:
            logger.error(f"检查模拟器窗口时出错: {e}")
            # 出错时默认启用按钮
            self._needs_adb_initialization = False
            self._adb_initialization_completed = True
            if hasattr(self, 'run_action'):
                self.run_action.setEnabled(True)
                self.run_action.setText("运行工作流")
                self.run_action.setToolTip("开始执行当前工作流 (F9)")

    def on_adb_initialization_completed(self, device_count: int = 0):
        """ADB初始化完成后的回调函数"""
        try:
            logger.info(f"ADB初始化完成，处理了 {device_count} 个设备")
            self._adb_initialization_completed = True

            # 只有在需要ADB初始化时才启用按钮
            if self._needs_adb_initialization:
                # 启用顶部运行按钮
                if hasattr(self, 'run_action'):
                    self.run_action.setEnabled(True)
                    self.run_action.setText("运行工作流")
                    self.run_action.setToolTip("开始执行当前工作流 (F9)")
                    logger.info("运行按钮已启用，可以开始执行任务")

                # 🔧 启用执行面板的按钮
                if hasattr(self, 'execution_panel'):
                    self.execution_panel.set_initialization_in_progress(False)
                    logger.info("执行面板按钮已启用")

        except Exception as e:
            logger.error(f"处理ADB初始化完成回调时出错: {e}")