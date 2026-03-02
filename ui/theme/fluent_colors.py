# -*- coding: utf-8 -*-
"""
Windows 11 Fluent Design System 配色定义
参考 Microsoft Fluent Design System 官方规范
"""

from enum import Enum
from typing import Dict, Any
from PySide6.QtGui import QColor


class ThemeMode(Enum):
    """主题模式枚举"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"  # 跟随系统


class FluentColors:
    """
    Windows 11 Fluent Design 配色方案
    提供明亮和暗色两种模式的完整配色定义
    """
    
    # ==================== 明亮模式配色 ====================
    LIGHT = {
        # 主色调
        "primary": "#0078D4",
        "primary_hover": "#106EBE", 
        "primary_pressed": "#005A9E",
        "primary_light": "#E5F1FB",
        
        # 背景色
        "background": "#F3F3F3",
        "background_secondary": "#FAFAFA",
        "surface": "#FFFFFF",
        "surface_hover": "#F7F7F7",
        "surface_pressed": "#F0F0F0",
        
        # 卡片/面板
        "card_background": "#FFFFFF",
        "card_border": "#E0E0E0",
        "card_shadow": "#000000",
        
        # 文字色
        "text_primary": "#1A1A1A",
        "text_secondary": "#5F5F5F", 
        "text_disabled": "#A0A0A0",
        "text_on_primary": "#FFFFFF",
        
        # 边框和分割线
        "border": "#E0E0E0",
        "border_strong": "#D0D0D0",
        "divider": "#E8E8E8",
        
        # 控件状态
        "control_background": "#FFFFFF",
        "control_border": "#D0D0D0",
        "control_hover": "#F5F5F5",
        "control_pressed": "#E8E8E8",
        "control_focus": "#0078D4",
        
        # 状态色
        "success": "#0F7B0F",
        "success_light": "#DFF6DD",
        "warning": "#9C5F00",
        "warning_light": "#FFF4CE",
        "error": "#C42B1C",
        "error_light": "#FDE7E9",
        "info": "#0078D4",
        "info_light": "#E5F1FB",
        
        # 标题栏
        "titlebar_background": "#F9F9F9",
        "titlebar_text": "#1A1A1A",
        "titlebar_button_hover": "#E5E5E5",
        "titlebar_button_pressed": "#D0D0D0",
        "titlebar_close_hover": "#E81123",
        "titlebar_close_pressed": "#B00000",
        
        # 工作流视图
        "workflow_background": "#F0F0F0",
        "workflow_grid": "#E0E0E0",
        "connection_line": "#9E9E9E",
        "connection_line_selected": "#0078D4",
        
        # 任务卡片端口色
        "port_sequential": "#0078D4",
        "port_success": "#0F7B0F", 
        "port_failure": "#C42B1C",
        "port_hover_boost": 40,
        
        # 滚动条
        "scrollbar_track": "#F0F0F0",
        "scrollbar_thumb": "#C0C0C0",
        "scrollbar_thumb_hover": "#A0A0A0",
    }
    
    # ==================== 暗色模式配色 ====================
    DARK = {
        # 主色调
        "primary": "#4CC2FF",
        "primary_hover": "#47B1E8",
        "primary_pressed": "#3AA0D6",
        "primary_light": "#1E3A4C",
        
        # 背景色
        "background": "#202020",
        "background_secondary": "#1E1E1E",
        "surface": "#2D2D2D",
        "surface_hover": "#353535",
        "surface_pressed": "#3D3D3D",
        
        # 卡片/面板
        "card_background": "#2D2D2D",
        "card_border": "#3A3A3A",
        "card_shadow": "#000000",
        
        # 文字色
        "text_primary": "#FFFFFF",
        "text_secondary": "#AAAAAA",
        "text_disabled": "#666666",
        "text_on_primary": "#000000",
        
        # 边框和分割线
        "border": "#3A3A3A",
        "border_strong": "#4A4A4A",
        "divider": "#333333",
        
        # 控件状态
        "control_background": "#2D2D2D",
        "control_border": "#4A4A4A",
        "control_hover": "#383838",
        "control_pressed": "#454545",
        "control_focus": "#4CC2FF",
        
        # 状态色
        "success": "#54B054",
        "success_light": "#1E3A1E",
        "warning": "#F2A900",
        "warning_light": "#3A3000",
        "error": "#FF99A4",
        "error_light": "#3A1E20",
        "info": "#4CC2FF",
        "info_light": "#1E3A4C",
        
        # 标题栏
        "titlebar_background": "#202020",
        "titlebar_text": "#FFFFFF",
        "titlebar_button_hover": "#383838",
        "titlebar_button_pressed": "#4A4A4A",
        "titlebar_close_hover": "#E81123",
        "titlebar_close_pressed": "#B00000",
        
        # 工作流视图
        "workflow_background": "#1E1E1E",
        "workflow_grid": "#333333",
        "connection_line": "#666666",
        "connection_line_selected": "#4CC2FF",
        
        # 任务卡片端口色
        "port_sequential": "#4CC2FF",
        "port_success": "#54B054",
        "port_failure": "#FF99A4",
        "port_hover_boost": 40,
        
        # 滚动条
        "scrollbar_track": "#2D2D2D",
        "scrollbar_thumb": "#5A5A5A",
        "scrollbar_thumb_hover": "#707070",
    }
    
    @classmethod
    def get_palette(cls, mode: ThemeMode) -> Dict[str, str]:
        """
        获取指定主题的配色方案
        
        Args:
            mode: 主题模式
            
        Returns:
            配色字典
        """
        if mode == ThemeMode.DARK:
            return cls.DARK.copy()
        else:
            return cls.LIGHT.copy()
    
    @classmethod
    def get_color(cls, mode: ThemeMode, color_name: str) -> str:
        """
        获取指定主题下的特定颜色
        
        Args:
            mode: 主题模式
            color_name: 颜色名称
            
        Returns:
            颜色值（十六进制字符串）
        """
        palette = cls.get_palette(mode)
        return palette.get(color_name, "#000000")
    
    @classmethod
    def get_qcolor(cls, mode: ThemeMode, color_name: str) -> QColor:
        """
        获取指定主题下的特定颜色（QColor对象）
        
        Args:
            mode: 主题模式
            color_name: 颜色名称
            
        Returns:
            QColor对象
        """
        color_str = cls.get_color(mode, color_name)
        return QColor(color_str)
    
    @classmethod
    def detect_system_theme(cls) -> ThemeMode:
        """
        检测当前系统主题
        
        Returns:
            系统主题模式（LIGHT 或 DARK）
        """
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtCore import Qt
            
            app = QApplication.instance()
            if app:
                # 使用 Qt6 的 ColorScheme API
                color_scheme = app.styleHints().colorScheme()
                if color_scheme == Qt.ColorScheme.Dark:
                    return ThemeMode.DARK
                elif color_scheme == Qt.ColorScheme.Light:
                    return ThemeMode.LIGHT
                else:
                    # 回退到调色板检测
                    palette = app.palette()
                    window_color = palette.window().color()
                    # 计算亮度 (YIQ 公式)
                    brightness = (window_color.red() * 299 + window_color.green() * 587 + window_color.blue() * 114) / 1000
                    return ThemeMode.DARK if brightness < 128 else ThemeMode.LIGHT
        except Exception:
            pass
        
        # 默认返回明亮模式
        return ThemeMode.LIGHT
