# -*- coding: utf-8 -*-
"""
样式表构建器 - 动态生成QSS样式表
根据当前主题生成符合Fluent Design规范的样式
"""

import logging
from typing import Optional
from .fluent_colors import FluentColors, ThemeMode
from .theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class StylesheetBuilder:
    """
    样式表构建器
    根据当前主题动态生成QSS样式表
    """
    
    def __init__(self):
        self._cached_stylesheet: Optional[str] = None
        self._cached_mode: Optional[ThemeMode] = None
    
    def get_stylesheet(self, mode: Optional[ThemeMode] = None) -> str:
        """
        获取当前主题的完整样式表
        
        Args:
            mode: 主题模式，None则使用当前主题
            
        Returns:
            QSS样式表字符串
        """
        if mode is None:
            mode = ThemeManager.instance().get_current_mode()
            
        # 检查缓存
        if self._cached_stylesheet and self._cached_mode == mode:
            return self._cached_stylesheet
            
        # 生成新样式表
        colors = FluentColors.get_palette(mode)
        stylesheet = self._build_stylesheet(colors)
        
        # 更新缓存
        self._cached_stylesheet = stylesheet
        self._cached_mode = mode
        
        return stylesheet
    
    def clear_cache(self):
        """清除样式表缓存"""
        self._cached_stylesheet = None
        self._cached_mode = None
    
    def _build_stylesheet(self, colors: dict) -> str:
        """
        构建完整样式表
        
        Args:
            colors: 配色字典
            
        Returns:
            QSS样式表字符串
        """
        return f"""
        /* ============================================
           Windows 11 Fluent Design 样式表
           自动生成，请勿手动修改
           ============================================ */
        
        /* 基础样式 */
        QWidget {{
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            color: {colors["text_primary"]};
            background-color: {colors["background"]};
        }}

        /* 主窗口 - 使用更强的选择器 */
        QMainWindow, QMainWindow > QWidget, QMainWindow > QWidget > QWidget {{
            background-color: {colors["background"]} !important;
        }}

        /* 对话框 */
        QDialog, QDialog > QWidget {{
            background-color: {colors["background"]} !important;
            border-radius: 8px;
        }}
        
        QMessageBox {{
            background-color: {colors["background"]};
        }}
        
        /* 分组框 */
        QGroupBox {{
            font-weight: 600;
            font-size: 13px;
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            margin-top: 12px;
            padding: 16px 12px 12px 12px;
            background-color: {colors["surface"]};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 12px;
            color: {colors["text_secondary"]};
            background-color: {colors["surface"]};
        }}
        
        /* 按钮样式 - Fluent Design */
        QPushButton {{
            background-color: {colors["control_background"]};
            border: 1px solid {colors["border"]};
            padding: 8px 20px;
            border-radius: 4px;
            color: {colors["text_primary"]};
            font-weight: 500;
            min-height: 24px;
            outline: none;
        }}
        
        QPushButton:hover {{
            background-color: {colors["control_hover"]};
            border-color: {colors["border_strong"]};
        }}
        
        QPushButton:pressed {{
            background-color: {colors["control_pressed"]};
        }}
        
        QPushButton:disabled {{
            background-color: {colors["background_secondary"]};
            color: {colors["text_disabled"]};
            border-color: {colors["border"]};
        }}
        
        /* 主要按钮 */
        QPushButton#primaryButton,
        QDialogButtonBox QPushButton[StandardButton="2048"],
        QMessageBox QPushButton[StandardButton="16384"] {{
            background-color: {colors["primary"]};
            color: {colors["text_on_primary"]};
            border: none;
        }}
        
        QPushButton#primaryButton:hover,
        QDialogButtonBox QPushButton[StandardButton="2048"]:hover,
        QMessageBox QPushButton[StandardButton="16384"]:hover {{
            background-color: {colors["primary_hover"]};
        }}
        
        QPushButton#primaryButton:pressed,
        QDialogButtonBox QPushButton[StandardButton="2048"]:pressed,
        QMessageBox QPushButton[StandardButton="16384"]:pressed {{
            background-color: {colors["primary_pressed"]};
        }}
        
        /* 工具按钮 */
        QToolButton {{
            background-color: transparent;
            border: none;
            padding: 6px;
            border-radius: 4px;
            color: {colors["text_primary"]};
        }}
        
        QToolButton:hover {{
            background-color: {colors["control_hover"]};
        }}
        
        QToolButton:pressed {{
            background-color: {colors["control_pressed"]};
        }}
        
        QToolButton:disabled {{
            color: {colors["text_disabled"]};
        }}
        
        /* 输入框 */
        QLineEdit {{
            padding: 8px 12px;
            border: 1px solid {colors["control_border"]};
            border-radius: 4px;
            background-color: {colors["control_background"]};
            color: {colors["text_primary"]};
            min-height: 20px;
        }}
        
        QLineEdit:focus {{
            border-color: {colors["primary"]};
            outline: none;
        }}
        
        QLineEdit:disabled {{
            background-color: {colors["background_secondary"]};
            color: {colors["text_disabled"]};
        }}
        
        /* 下拉框 */
        QComboBox {{
            padding: 8px 12px;
            border: 1px solid {colors["control_border"]};
            border-radius: 4px;
            background-color: {colors["control_background"]};
            color: {colors["text_primary"]};
            min-height: 20px;
        }}
        
        QComboBox:hover {{
            border-color: {colors["border_strong"]};
        }}
        
        QComboBox:focus {{
            border-color: {colors["primary"]};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {colors["text_secondary"]};
            width: 0;
            height: 0;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors["surface"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            selection-background-color: {colors["primary"]};
            selection-color: {colors["text_on_primary"]};
            padding: 4px;
        }}
        
        /* 数字输入框 */
        QSpinBox, QDoubleSpinBox {{
            padding: 8px 12px;
            border: 1px solid {colors["control_border"]};
            border-radius: 4px;
            background-color: {colors["control_background"]};
            color: {colors["text_primary"]};
            min-height: 20px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {colors["primary"]};
        }}
        
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            background-color: transparent;
            border: none;
            width: 20px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {colors["control_hover"]};
        }}
        
        /* 复选框 */
        QCheckBox {{
            spacing: 8px;
            color: {colors["text_primary"]};
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors["control_border"]};
            border-radius: 3px;
            background-color: {colors["control_background"]};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors["primary"]};
            border-color: {colors["primary"]};
            image: url(:/qt-project.org/styles/commonstyle/images/check.png);
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {colors["border_strong"]};
        }}
        
        /* 单选按钮 */
        QRadioButton {{
            spacing: 8px;
            color: {colors["text_primary"]};
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors["control_border"]};
            border-radius: 8px;
            background-color: {colors["control_background"]};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {colors["primary"]};
            border-color: {colors["primary"]};
        }}
        
        /* 标签 */
        QLabel {{
            color: {colors["text_primary"]};
            background-color: transparent;
        }}
        
        QLabel#subtitle {{
            color: {colors["text_secondary"]};
            font-size: 12px;
        }}
        
        /* 滑块 */
        QSlider::groove:horizontal {{
            height: 4px;
            background-color: {colors["border"]};
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            width: 16px;
            height: 16px;
            background-color: {colors["primary"]};
            border-radius: 8px;
            margin: -6px 0;
        }}
        
        QSlider::sub-page:horizontal {{
            background-color: {colors["primary"]};
            border-radius: 2px;
        }}
        
        /* 进度条 */
        QProgressBar {{
            border: none;
            border-radius: 4px;
            background-color: {colors["border"]};
            text-align: center;
            color: {colors["text_primary"]};
            height: 8px;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors["primary"]};
            border-radius: 4px;
        }}
        
        /* 滚动条 */
        QScrollBar:vertical {{
            background-color: {colors["scrollbar_track"]};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors["scrollbar_thumb"]};
            min-height: 40px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors["scrollbar_thumb_hover"]};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors["scrollbar_track"]};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors["scrollbar_thumb"]};
            min-width: 40px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors["scrollbar_thumb_hover"]};
        }}
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* 菜单 */
        QMenu {{
            background-color: {colors["surface"]};
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            padding: 8px;
        }}
        
        QMenu::item {{
            padding: 8px 24px;
            background-color: transparent;
            border-radius: 4px;
            color: {colors["text_primary"]};
        }}
        
        QMenu::item:selected {{
            background-color: {colors["primary"]};
            color: {colors["text_on_primary"]};
        }}
        
        QMenu::item:disabled {{
            color: {colors["text_disabled"]};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors["divider"]};
            margin: 8px 12px;
        }}
        
        /* 工具提示 */
        QToolTip {{
            background-color: {colors["surface"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        
        /* Tab 控件 */
        QTabWidget::pane {{
            border: 1px solid {colors["border"]};
            border-radius: 8px;
            background-color: {colors["surface"]};
            top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: transparent;
            border: none;
            padding: 10px 20px;
            color: {colors["text_secondary"]};
            font-weight: 500;
        }}
        
        QTabBar::tab:selected {{
            color: {colors["primary"]};
            border-bottom: 2px solid {colors["primary"]};
        }}
        
        QTabBar::tab:hover:!selected {{
            color: {colors["text_primary"]};
        }}
        
        /* 列表视图 */
        QListView {{
            background-color: {colors["surface"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            outline: none;
            padding: 4px;
        }}
        
        QListView::item {{
            padding: 8px 12px;
            border-radius: 4px;
        }}
        
        QListView::item:selected {{
            background-color: {colors["primary"]};
            color: {colors["text_on_primary"]};
        }}
        
        QListView::item:hover:!selected {{
            background-color: {colors["control_hover"]};
        }}
        
        /* 树形视图 */
        QTreeView {{
            background-color: {colors["surface"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
            outline: none;
        }}
        
        QTreeView::item {{
            padding: 6px 8px;
        }}
        
        QTreeView::item:selected {{
            background-color: {colors["primary"]};
            color: {colors["text_on_primary"]};
        }}
        
        /* 文本编辑区 */
        QTextEdit, QPlainTextEdit {{
            background-color: {colors["control_background"]};
            color: {colors["text_primary"]};
            border: 1px solid {colors["control_border"]};
            border-radius: 4px;
            padding: 8px;
        }}
        
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {colors["primary"]};
        }}
        
        /* 分隔线 */
        QFrame[frameShape="4"],  /* HLine */
        QFrame[frameShape="5"]   /* VLine */ {{
            color: {colors["divider"]};
        }}
        
        /* ============================================
           自定义组件样式
           ============================================ */
        
        /* 自定义标题栏 */
        #CustomTitleBar {{
            background-color: {colors["titlebar_background"]};
            border-bottom: 1px solid {colors["border"]};
        }}
        
        #CustomTitleBar QLabel {{
            color: {colors["titlebar_text"]};
            font-size: 12px;
            font-weight: 500;
        }}
        
        #CustomTitleBar QPushButton#windowButton {{
            background-color: transparent;
            border: none;
            color: {colors["titlebar_text"]};
            font-size: 10px;
            padding: 4px 12px;
            border-radius: 4px;
        }}
        
        #CustomTitleBar QPushButton#windowButton:hover {{
            background-color: {colors["titlebar_button_hover"]};
        }}
        
        #CustomTitleBar QPushButton#closeButton:hover {{
            background-color: {colors["titlebar_close_hover"]};
            color: white;
        }}
        
        /* 任务卡片相关 */
        #TaskCard {{
            background-color: {colors["card_background"]};
            border: 1px solid {colors["card_border"]};
            border-radius: 8px;
        }}
        
        /* 中央框架 */
        #CentralFrame {{
            background-color: {colors["background"]};
            border-radius: 8px;
        }}
        
        /* 工作流视图 */
        #WorkflowView {{
            background-color: {colors["workflow_background"]};
            border: none;
        }}
        
        /* 参数面板 */
        #ParameterPanel {{
            background-color: {colors["surface"]};
            border-left: 1px solid {colors["border"]};
        }}

        /* 表格样式 */
        QTableWidget {{
            gridline-color: {colors["border"]};
            background-color: {colors["surface"]};
            alternate-background-color: {colors["background_secondary"]};
            selection-background-color: {colors["primary"]};
            selection-color: {colors["text_on_primary"]};
            border: 1px solid {colors["border"]};
            border-radius: 4px;
        }}

        QTableWidget::item {{
            padding: 8px;
            border: none;
            color: {colors["text_primary"]};
        }}

        QTableWidget::item:selected {{
            background-color: {colors["primary"]};
            color: {colors["text_on_primary"]};
        }}

        QTableWidget::item:focus {{
            border: none;
            outline: none;
        }}

        QTableWidget:focus {{
            border: none;
            outline: none;
        }}

        QTableWidget::horizontalHeader {{
            background-color: {colors["surface"]};
            color: {colors["text_secondary"]};
            border: none;
            border-bottom: 1px solid {colors["border"]};
            padding: 8px;
            font-weight: 600;
        }}

        QTableWidget::verticalHeader {{
            background-color: {colors["surface"]};
            color: {colors["text_secondary"]};
            border: none;
            border-right: 1px solid {colors["border"]};
            padding: 8px;
        }}

        /* 状态标签样式 */
        .success {{ color: {colors["success"]}; }}
        .warning {{ color: {colors["warning"]}; }}
        .error {{ color: {colors["error"]}; }}
        .info {{ color: {colors["info"]}; }}
        """


# 全局样式表构建器实例
_stylesheet_builder: Optional[StylesheetBuilder] = None


def get_stylesheet_builder() -> StylesheetBuilder:
    """获取样式表构建器单例"""
    global _stylesheet_builder
    if _stylesheet_builder is None:
        _stylesheet_builder = StylesheetBuilder()
    return _stylesheet_builder


def get_current_stylesheet() -> str:
    """获取当前主题的样式表（便捷函数）"""
    return get_stylesheet_builder().get_stylesheet()
