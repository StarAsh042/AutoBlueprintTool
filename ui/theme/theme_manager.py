# -*- coding: utf-8 -*-
"""
主题管理器 - 管理应用程序主题状态
支持自动跟随系统主题，提供主题切换信号
"""

import logging
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from .fluent_colors import FluentColors, ThemeMode

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """
    主题管理器单例类
    管理应用程序的主题状态，支持明亮/暗色/跟随系统三种模式
    """
    
    # 主题切换信号
    theme_changed = Signal(ThemeMode)  # 参数：新主题模式
    colors_changed = Signal(dict)       # 参数：新配色字典
    
    # 单例实例
    _instance: Optional['ThemeManager'] = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, parent=None):
        if ThemeManager._initialized:
            return
            
        super().__init__(parent)
        ThemeManager._initialized = True
        
        # 当前主题模式（默认跟随系统）
        self._current_mode = ThemeMode.SYSTEM
        self._actual_mode = ThemeMode.LIGHT  # 实际应用的模式（LIGHT 或 DARK）
        
        # 当前配色方案
        self._current_palette = FluentColors.get_palette(ThemeMode.LIGHT)
        
        # 监听器列表
        self._listeners: list[Callable] = []
        
        # 是否已设置系统监听
        self._system_listener_setup = False
        
        logger.info("主题管理器初始化完成")
    
    @classmethod
    def instance(cls) -> 'ThemeManager':
        """获取主题管理器单例实例"""
        if cls._instance is None:
            cls._instance = ThemeManager()
        return cls._instance
    
    def setup_system_listener(self):
        """设置系统主题变化监听"""
        if self._system_listener_setup:
            return
            
        try:
            app = QApplication.instance()
            if app:
                # 连接 Qt6 的系统主题变化信号
                app.styleHints().colorSchemeChanged.connect(self._on_system_theme_changed)
                self._system_listener_setup = True
                logger.info("系统主题监听器已设置")
        except Exception as e:
            logger.warning(f"设置系统主题监听器失败: {e}")
    
    def _on_system_theme_changed(self, color_scheme: Qt.ColorScheme):
        """
        系统主题变化回调
        
        Args:
            color_scheme: Qt.ColorScheme 枚举值
        """
        if self._current_mode != ThemeMode.SYSTEM:
            # 用户手动设置了主题，不响应系统变化
            return
            
        new_mode = ThemeMode.DARK if color_scheme == Qt.ColorScheme.Dark else ThemeMode.LIGHT
        if new_mode != self._actual_mode:
            logger.info(f"系统主题变化: {self._actual_mode.value} -> {new_mode.value}")
            self._apply_theme(new_mode)
    
    def initialize(self, config_mode: str = "system"):
        """
        初始化主题管理器
        
        Args:
            config_mode: 配置中的主题设置 ("light", "dark", "system")
        """
        # 解析配置
        mode_map = {
            "light": ThemeMode.LIGHT,
            "dark": ThemeMode.DARK,
            "system": ThemeMode.SYSTEM
        }
        self._current_mode = mode_map.get(config_mode.lower(), ThemeMode.SYSTEM)
        
        # 设置系统监听
        self.setup_system_listener()
        
        # 确定实际应用的主题
        if self._current_mode == ThemeMode.SYSTEM:
            self._actual_mode = FluentColors.detect_system_theme()
        else:
            self._actual_mode = self._current_mode
            
        # 应用主题
        self._apply_theme(self._actual_mode, emit_signal=False)
        
        logger.info(f"主题管理器初始化: 配置={config_mode}, 实际={self._actual_mode.value}")
    
    def set_theme(self, mode: ThemeMode):
        """
        手动设置主题模式
        
        Args:
            mode: 目标主题模式
        """
        if mode == self._current_mode and mode != ThemeMode.SYSTEM:
            return
            
        self._current_mode = mode
        
        # 确定实际要应用的主题
        if mode == ThemeMode.SYSTEM:
            new_mode = FluentColors.detect_system_theme()
        else:
            new_mode = mode
            
        if new_mode != self._actual_mode:
            self._apply_theme(new_mode)
        else:
            # 更新配置但颜色未变，仍然发射信号以确保UI更新
            self._actual_mode = new_mode
            self._current_palette = FluentColors.get_palette(new_mode)
            self.theme_changed.emit(new_mode)
            self.colors_changed.emit(self._current_palette)
    
    def _apply_theme(self, mode: ThemeMode, emit_signal: bool = True):
        """
        应用指定主题
        
        Args:
            mode: 主题模式
            emit_signal: 是否发射主题变化信号
        """
        self._actual_mode = mode
        self._current_palette = FluentColors.get_palette(mode)
        
        # 更新应用程序调色板
        self._update_application_palette()
        
        if emit_signal:
            self.theme_changed.emit(mode)
            self.colors_changed.emit(self._current_palette)
            
        logger.info(f"主题已应用: {mode.value}")
    
    def _update_application_palette(self):
        """更新应用程序调色板"""
        try:
            app = QApplication.instance()
            if not app:
                return
                
            palette = QPalette()
            colors = self._current_palette
            
            # 设置调色板颜色
            palette.setColor(QPalette.ColorRole.Window, QColor(colors["background"]))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(colors["text_primary"]))
            palette.setColor(QPalette.ColorRole.Base, QColor(colors["surface"]))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors["background_secondary"]))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors["surface"]))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors["text_primary"]))
            palette.setColor(QPalette.ColorRole.Text, QColor(colors["text_primary"]))
            palette.setColor(QPalette.ColorRole.Button, QColor(colors["control_background"]))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors["text_primary"]))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(colors["error"]))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(colors["primary"]))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors["text_on_primary"]))
            
            app.setPalette(palette)
            
        except Exception as e:
            logger.error(f"更新应用程序调色板失败: {e}")
    
    def get_current_mode(self) -> ThemeMode:
        """获取当前实际应用的主题模式"""
        return self._actual_mode
    
    def get_configured_mode(self) -> ThemeMode:
        """获取用户配置的主题模式"""
        return self._current_mode
    
    def get_palette(self) -> dict:
        """获取当前配色方案"""
        return self._current_palette.copy()
    
    def get_color(self, color_name: str) -> str:
        """
        获取指定颜色值
        
        Args:
            color_name: 颜色名称
            
        Returns:
            颜色值（十六进制字符串）
        """
        return self._current_palette.get(color_name, "#000000")
    
    def get_qcolor(self, color_name: str) -> QColor:
        """
        获取指定颜色值（QColor对象）
        
        Args:
            color_name: 颜色名称
            
        Returns:
            QColor对象
        """
        return QColor(self.get_color(color_name))
    
    def is_dark_mode(self) -> bool:
        """检查当前是否为暗色模式"""
        return self._actual_mode == ThemeMode.DARK
    
    def is_light_mode(self) -> bool:
        """检查当前是否为明亮模式"""
        return self._actual_mode == ThemeMode.LIGHT
    
    def add_listener(self, callback: Callable):
        """
        添加主题变化监听器
        
        Args:
            callback: 回调函数，接收 ThemeMode 参数
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
            # 立即用当前主题调用一次
            try:
                callback(self._actual_mode)
            except Exception as e:
                logger.error(f"主题监听器初始化调用失败: {e}")
    
    def remove_listener(self, callback: Callable):
        """
        移除主题变化监听器
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self._listeners:
            self._listeners.remove(callback)


# 便捷函数
def get_theme_manager() -> ThemeManager:
    """获取主题管理器实例的便捷函数"""
    return ThemeManager.instance()
