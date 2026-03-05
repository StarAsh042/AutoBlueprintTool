# -*- coding: utf-8 -*-
"""
Qt 原生样式主题管理器
提供明暗两种主题切换功能
"""

from enum import Enum
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette, QColor
import logging

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """主题模式枚举（兼容旧的 Fluent Design API）"""
    LIGHT = 'light'
    DARK = 'dark'

class ThemeManager(QObject):
    """Qt 原生样式主题管理器"""
    
    theme_changed = Signal(str)  # 主题变化信号：light 或 dark
    
    # 明亮主题颜色
    LIGHT_PALETTE = {
        'window': QColor(210, 210, 210),              # 窗口背景（浅中灰）
        'window_text': QColor(0, 0, 0),
        'base': QColor(230, 230, 230),                # 基础背景（浅灰）
        'alternate_base': QColor(220, 220, 220),
        'text': QColor(0, 0, 0),
        'button': QColor(200, 200, 200),
        'button_text': QColor(0, 0, 0),
        'bright_text': QColor(255, 255, 255),
        'highlight': QColor(0, 120, 212),
        'highlighted_text': QColor(255, 255, 255),
        'link': QColor(0, 120, 212),
        'link_visited': QColor(150, 50, 150),
        
        # UI 组件专用颜色
        'card_background': QColor(240, 240, 240),      # 卡片背景（浅灰，稍白）
        'surface': QColor(225, 225, 225),              # 表面
        'text_primary': QColor(0, 0, 0),               # 主要文字
        'text_disabled': QColor(130, 130, 130),        # 禁用文字
        'text_on_primary': QColor(255, 255, 255),      # 主色调上的文字
        'divider': QColor(190, 190, 190),              # 分隔线
        'workflow_background': QColor(220, 220, 220),  # 工作流背景（浅灰）
        'border': QColor(160, 160, 160),               # 边框（适中）
        'primary': QColor(0, 120, 212),                # 主色调
        'success': QColor(76, 175, 80),                # 成功（绿色）
        'error': QColor(244, 67, 54),                  # 错误（红色）
        'port_sequential': QColor(33, 150, 243),       # 顺序端口（蓝色）
        'port_success': QColor(76, 175, 80),           # 成功端口（绿色）
        'port_failure': QColor(244, 67, 54),           # 失败端口（红色）
    }
    
    # 黑暗主题颜色
    DARK_PALETTE = {
        'window': QColor(30, 30, 30),
        'window_text': QColor(255, 255, 255),
        'base': QColor(37, 37, 37),
        'alternate_base': QColor(40, 40, 40),
        'text': QColor(255, 255, 255),
        'button': QColor(45, 45, 45),
        'button_text': QColor(255, 255, 255),
        'bright_text': QColor(255, 255, 255),
        'highlight': QColor(0, 120, 212),
        'highlighted_text': QColor(255, 255, 255),
        'link': QColor(0, 120, 212),
        'link_visited': QColor(180, 80, 180),
        
        # UI 组件专用颜色
        'card_background': QColor(45, 45, 45),         # 卡片背景（深色）
        'surface': QColor(40, 40, 40),                 # 表面（深灰色）
        'text_primary': QColor(255, 255, 255),         # 主要文字
        'text_disabled': QColor(120, 120, 120),        # 禁用文字（暗色）
        'text_on_primary': QColor(255, 255, 255),      # 主色调上的文字
        'divider': QColor(60, 60, 60),                 # 分隔线（暗色）
        'workflow_background': QColor(30, 30, 30),     # 工作流背景（暗色）
        'border': QColor(70, 70, 70),                  # 边框
        'primary': QColor(0, 120, 212),                # 主色调
        'success': QColor(76, 175, 80),                # 成功（绿色）
        'error': QColor(244, 67, 54),                  # 错误（红色）
        'port_sequential': QColor(33, 150, 243),       # 顺序端口（蓝色）
        'port_success': QColor(76, 175, 80),           # 成功端口（绿色）
        'port_failure': QColor(244, 67, 54),           # 失败端口（红色）
    }
    
    # 明亮主题 QSS
    LIGHT_QSS = """
    QMainWindow, QDialog {
        background-color: #e6e6e6;
        color: #000000;
    }
    
    QWidget {
        background-color: #f5f5f5;
        color: #000000;
    }
    
    /* 卡片和容器使用浅灰色背景，带边框 */
    QFrame#task_card, QFrame#workflow_view, QFrame#parameter_panel, QGroupBox {
        background-color: #fafafa;
        border: 1px solid #b4b4b4;
        border-radius: 4px;
    }
    
    /* 画布区域使用浅灰色 */
    QScrollArea, QGraphicsView {
        background-color: #f0f0f0;
        border: 1px solid #d0d0d0;
    }
    
    /* 任务选择按钮样式 - 使用通配符匹配所有 */
    QPushButton[objectName^="taskButton_"] {
        background-color: #fafafa;
        border: 1px solid #c0c0c0;
        border-radius: 8px;
        font-size: 13px;
        color: #000000;
        padding: 10px;
    }
    
    QPushButton[objectName^="taskButton_"]:hover {
        background-color: #e0e0e0;
        border-color: #0078d4;
    }
    
    QPushButton[objectName^="taskButton_"]:pressed {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    /* 对话框样式 */
    QDialog {
        background-color: #f5f5f5;
        border: 1px solid #c0c0c0;
    }
    
    /* 确定/取消按钮样式 */
    QPushButton#okButton {
        background-color: #0078d4;
        border: 1px solid #005a9e;
        border-radius: 8px;
        font-size: 14px;
        color: #ffffff;
        padding: 8px 20px;
    }
    QPushButton#okButton:hover {
        background-color: #1084d8;
    }
    QPushButton#okButton:pressed {
        background-color: #006cbe;
    }
    
    QPushButton#cancelButton {
        background-color: #d43636;
        border: 1px solid #a82b2b;
        border-radius: 8px;
        font-size: 14px;
        color: #ffffff;
        padding: 8px 20px;
    }
    QPushButton#cancelButton:hover {
        background-color: #e04444;
    }
    QPushButton#cancelButton:pressed {
        background-color: #c03030;
    }
    
    QPushButton {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 6px 12px;
        color: #000000;
    }
    
    QPushButton:hover {
        background-color: rgba(0, 0, 0, 0.05);
        border-color: #cccccc;
    }
    
    QPushButton:pressed {
        background-color: rgba(0, 0, 0, 0.1);
    }
    
    QPushButton:checked {
        background-color: #0078d4;
        color: #ffffff;
        border-color: #0078d4;
    }
    
    /* 连接线和边框使用淡色 */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px;
        color: #000000;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #0078d4;
    }
    
    QComboBox {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px 8px;
        color: #000000;
    }
    
    QComboBox:hover {
        border-color: #0078d4;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    
    QSpinBox, QDoubleSpinBox {
        background-color: #ffffff;
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        padding: 4px;
        color: #000000;
    }
    
    QSpinBox:hover, QDoubleSpinBox:hover {
        border-color: #0078d4;
    }
    
    QCheckBox, QRadioButton {
        color: #000000;
        spacing: 8px;
    }
    
    QSlider::groove:horizontal {
        background-color: #e0e0e0;
        height: 4px;
        border-radius: 2px;
    }
    
    QSlider::handle:horizontal {
        background-color: #0078d4;
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }
    
    QSlider::handle:horizontal:hover {
        background-color: #1084d8;
    }
    
    QProgressBar {
        background-color: #e0e0e0;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 2px;
        text-align: center;
        color: #000000;
    }
    
    QProgressBar::chunk {
        background-color: #0078d4;
        border-radius: 2px;
    }
    
    QTabWidget::pane {
        border: 1px solid #cccccc;
        border-radius: 4px;
        background-color: #f5f5f5;
    }
    
    QTabBar::tab {
        background-color: #e8e8e8;
        border: 1px solid #d0d0d0;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 6px 12px;
        color: #000000;
        margin-right: 2px;
    }
    
    QTabBar::tab:selected {
        background-color: #f5f5f5;
        border-bottom: 1px solid #f5f5f5;
    }
    
    QTabBar::tab:hover {
        background-color: #d0d0d0;
    }
    
    QTableWidget, QTreeWidget, QListWidget {
        background-color: #ffffff;
        alternate-background-color: #f0f0f0;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
        gridline-color: #d0d0d0;
    }
    
    QTableWidget::item, QTreeWidget::item, QListWidget::item {
        padding: 4px;
        border: none;
    }
    
    QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {
        background-color: #e0e0e0;
    }
    
    QHeaderView::section {
        background-color: #e0e0e0;
        border: 1px solid #cccccc;
        padding: 4px;
        color: #000000;
        font-weight: bold;
    }
    
    QScrollBar:vertical {
        background-color: #f5f5f5;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #c0c0c0;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        background-color: #f5f5f5;
        height: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #c0c0c0;
        border-radius: 6px;
        min-width: 20px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #a0a0a0;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    QMenu {
        background-color: #ffffff;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 4px;
    }
    
    QMenu::item {
        padding: 6px 24px 6px 12px;
        color: #000000;
    }
    
    QMenu::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #e0e0e0;
        margin: 4px 0;
    }
    
    QToolTip {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 4px;
    }
    
    QMessageBox, QFileDialog, QInputDialog {
        background-color: #f5f5f5;
    }
    """
    
    # 黑暗主题 QSS
    DARK_QSS = """
    QMainWindow, QDialog {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    
    QWidget {
        background-color: #252525;
        color: #ffffff;
    }
    
    /* 卡片和容器使用深色背景，带边框 */
    QFrame#task_card, QFrame#workflow_view, QFrame#parameter_panel, QGroupBox {
        background-color: #2d2d2d;
        border: 1px solid #3e3e3e;
        border-radius: 4px;
    }
    
    /* 画布区域使用稍浅的深色 */
    QScrollArea, QGraphicsView {
        background-color: #2a2a2a;
        border: 1px solid #353535;
    }
    
    /* 任务选择按钮样式 - 使用通配符匹配所有 */
    QPushButton[objectName^="taskButton_"] {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        font-size: 13px;
        color: #ffffff;
        padding: 10px;
    }
    
    QPushButton[objectName^="taskButton_"]:hover {
        background-color: #3d3d3d;
        border-color: #0078d4;
    }
    
    QPushButton[objectName^="taskButton_"]:pressed {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    /* 对话框样式 */
    QDialog {
        background-color: #252525;
        border: 1px solid #3d3d3d;
    }
    
    /* 确定/取消按钮样式 */
    QPushButton#okButton {
        background-color: #0078d4;
        border: 1px solid #005a9e;
        border-radius: 8px;
        font-size: 14px;
        color: #ffffff;
        padding: 8px 20px;
    }
    QPushButton#okButton:hover {
        background-color: #1084d8;
    }
    QPushButton#okButton:pressed {
        background-color: #006cbe;
    }
    
    QPushButton#cancelButton {
        background-color: #d43636;
        border: 1px solid #a82b2b;
        border-radius: 8px;
        font-size: 14px;
        color: #ffffff;
        padding: 8px 20px;
    }
    QPushButton#cancelButton:hover {
        background-color: #e04444;
    }
    QPushButton#cancelButton:pressed {
        background-color: #c03030;
    }
    
    QPushButton {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 6px 12px;
        color: #ffffff;
    }
    
    QPushButton:hover {
        background-color: rgba(255, 255, 255, 0.05);
        border-color: #555555;
    }
    
    QPushButton:pressed {
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    QPushButton:checked {
        background-color: #0078d4;
        color: #ffffff;
        border-color: #0078d4;
    }
    
    /* 连接线和边框使用淡色 */
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #2d2d2d;
        border: 1px solid #404040;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #0078d4;
    }
    
    QComboBox {
        background-color: #2d2d2d;
        border: 1px solid #404040;
        border-radius: 4px;
        padding: 4px 8px;
        color: #ffffff;
    }
    
    QComboBox:hover {
        border-color: #0078d4;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        border: 1px solid #555555;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
    }
    
    QSpinBox, QDoubleSpinBox {
        background-color: #2d2d2d;
        border: 1px solid #404040;
        border-radius: 4px;
        padding: 4px;
        color: #ffffff;
    }
    
    QSpinBox:hover, QDoubleSpinBox:hover {
        border-color: #0078d4;
    }
    
    QCheckBox, QRadioButton {
        color: #ffffff;
        spacing: 8px;
    }
    
    QSlider::groove:horizontal {
        background-color: #3c3c3c;
        height: 4px;
        border-radius: 2px;
    }
    
    QSlider::handle:horizontal {
        background-color: #0078d4;
        width: 12px;
        margin: -4px 0;
        border-radius: 6px;
    }
    
    QSlider::handle:horizontal:hover {
        background-color: #1084d8;
    }
    
    QProgressBar {
        background-color: #3c3c3c;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 2px;
        text-align: center;
        color: #ffffff;
    }
    
    QProgressBar::chunk {
        background-color: #0078d4;
        border-radius: 2px;
    }
    
    QTabWidget::pane {
        border: 1px solid #555555;
        border-radius: 4px;
        background-color: #202020;
    }
    
    QTabBar::tab {
        background-color: #3a3a3a;
        border: 1px solid #404040;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 6px 12px;
        color: #ffffff;
        margin-right: 2px;
    }
    
    QTabBar::tab:selected {
        background-color: #202020;
        border-bottom: 1px solid #202020;
    }
    
    QTabBar::tab:hover {
        background-color: #4c4c4c;
    }
    
    QTableWidget, QTreeWidget, QListWidget {
        background-color: #2d2d2d;
        alternate-background-color: #282828;
        border: 1px solid #404040;
        border-radius: 4px;
        selection-background-color: #0078d4;
        selection-color: #ffffff;
        gridline-color: #353535;
    }
    
    QTableWidget::item, QTreeWidget::item, QListWidget::item {
        padding: 4px;
        border: none;
    }
    
    QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {
        background-color: #3c3c3c;
    }
    
    QHeaderView::section {
        background-color: #353535;
        border: 1px solid #404040;
        padding: 4px;
        color: #ffffff;
        font-weight: bold;
    }
    
    QScrollBar:vertical {
        background-color: #202020;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #555555;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #666666;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    
    QScrollBar:horizontal {
        background-color: #202020;
        height: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #555555;
        border-radius: 6px;
        min-width: 20px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #666666;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }
    
    QMenu {
        background-color: #2d2d2d;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px;
    }
    
    QMenu::item {
        padding: 6px 24px 6px 12px;
        color: #ffffff;
    }
    
    QMenu::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #3c3c3c;
        margin: 4px 0;
    }
    
    QToolTip {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px;
    }
    
    QMessageBox, QFileDialog, QInputDialog {
        background-color: #202020;
    }
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = 'dark'  # 默认暗色主题
        
        # 监听系统主题变化
        try:
            from PySide6.QtCore import QSysInfo
            self._dark_mode = QSysInfo.productType() in ['osx', 'android']  # 默认值
        except:
            self._dark_mode = False
    
    def set_theme(self, theme_name: str):
        """设置主题并发送信号
        
        Args:
            theme_name: 主题名称 ('light' 或 'dark')
        """
        # 兼容处理：如果是枚举类型，转换为字符串
        if hasattr(theme_name, 'value'):
            theme_name = theme_name.value
        
        if theme_name not in ['light', 'dark']:
            logger.warning(f"不支持的主题：{theme_name}")
            theme_name = 'dark'  # 默认为暗色
        
        self._current_theme = theme_name
        
        # 应用主题并发送信号
        self._apply_theme_without_signal(theme_name)
        self.theme_changed.emit(theme_name)
    
    def follow_system_theme(self):
        """跟随系统主题（已废弃，直接使用 set_theme）"""
        # 这个方法已经不再使用，因为移除了 system 选项
        pass
    
    def apply_theme(self, theme_name: str):
        """应用主题并发送信号
        
        Args:
            theme_name: 主题名称 ('light', 'dark' 或 'system')
        """
        self.set_theme(theme_name)
        self.theme_changed.emit(self._current_theme)
    
    def _apply_theme_without_signal(self, theme_name: str):
        """应用主题但不发送信号（内部使用）"""
        if theme_name not in ['light', 'dark']:
            logger.warning(f"不支持的主题：{theme_name}")
            return
        
        self._current_theme = theme_name
        app = QApplication.instance()
        if not app:
            return
        
        # 设置调色板
        palette = QPalette()
        colors = self.LIGHT_PALETTE if theme_name == 'light' else self.DARK_PALETTE
        
        palette.setColor(QPalette.Window, colors['window'])
        palette.setColor(QPalette.WindowText, colors['window_text'])
        palette.setColor(QPalette.Base, colors['base'])
        palette.setColor(QPalette.AlternateBase, colors['alternate_base'])
        palette.setColor(QPalette.Text, colors['text'])
        palette.setColor(QPalette.Button, colors['button'])
        palette.setColor(QPalette.ButtonText, colors['button_text'])
        palette.setColor(QPalette.BrightText, colors['bright_text'])
        palette.setColor(QPalette.Highlight, colors['highlight'])
        palette.setColor(QPalette.HighlightedText, colors['highlighted_text'])
        palette.setColor(QPalette.Link, colors['link'])
        palette.setColor(QPalette.LinkVisited, colors['link_visited'])
        
        app.setPalette(palette)
        
        # 应用 QSS 样式表
        qss = self.LIGHT_QSS if theme_name == 'light' else self.DARK_QSS
        app.setStyleSheet(qss)
        
        # 强制刷新所有已打开的窗口样式
        for widget in app.topLevelWidgets():
            widget.setStyleSheet(qss)
            widget.update()
            # 递归刷新子控件
            self._refresh_widget_styles(widget, qss)
        
        logger.info(f"已应用{theme_name}主题")
    
    def _refresh_widget_styles(self, parent, qss: str):
        """递归刷新控件及其子控件的样式"""
        for child in parent.findChildren(QWidget):
            child.setStyleSheet(qss)
            child.update()
    
    def toggle_theme(self):
        """切换主题（明暗互换）"""
        new_theme = 'light' if self._current_theme == 'dark' else 'dark'
        self.apply_theme(new_theme)
        return new_theme
    
    def get_current_theme(self) -> str:
        """获取当前主题名称"""
        return self._current_theme
    
    def is_dark_mode(self) -> bool:
        """判断当前是否是黑暗模式
        
        Returns:
            bool: True 如果是黑暗模式，否则 False
        """
        return self._current_theme == 'dark'
    
    def get_colors(self) -> dict:
        """获取当前主题的配色方案
        
        Returns:
            dict: 配色字典
        """
        is_dark = (self._current_theme == 'dark')
        
        return self.LIGHT_PALETTE if not is_dark else self.DARK_PALETTE
    
    def get_palette(self) -> dict:
        """获取当前主题的配色方案（兼容旧 API）
        
        Returns:
            dict: 配色字典
        """
        return self.get_colors()
