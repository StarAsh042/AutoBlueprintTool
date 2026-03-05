#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR区域选择工具
使用截图方式在绑定窗口客户区域内框选OCR识别区域
"""

import logging
import sys
import os
import time
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, QMessageBox, QRubberBand
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QImage, QCursor

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.window_finder import WindowFinder

# 导入通用坐标系统
from utils.universal_coordinate_system import (
    get_universal_coordinate_system, create_region_from_ocr_selector,
    CoordinateSource
)
from utils.universal_resolution_adapter import get_universal_adapter

# Windows API 相关导入
try:
    import win32gui
    import win32api
    import ctypes
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRRegionSelectorOverlay(QWidget):
    """OCR区域选择覆盖层"""

    region_selected = Signal(int, int, int, int)  # x, y, width, height
    overlay_closed = Signal()  # 覆盖层关闭信号

    def __init__(self, target_window_title: str = None, target_window_hwnd: int = None, parent=None):
        # 重要：不设置parent，让覆盖层完全独立
        super().__init__(None)  # 传入None作为parent
        self.target_window_title = target_window_title
        self.target_hwnd = target_window_hwnd  # 直接使用传入的窗口句柄
        self.window_info = None

        # 选择状态
        self.selecting = False
        self.start_pos = QPoint()
        self.end_pos = QPoint()

        # 设置窗口属性 - 完全独立的窗口，不受任何模态对话框影响
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint |  # 绕过窗口管理器
            Qt.WindowType.WindowSystemMenuHint |     # 系统菜单
            Qt.WindowType.WindowDoesNotAcceptFocus   # 不接受焦点，避免与模态对话框冲突
        )

        # 强制设置为非模态，完全独立运行
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 设置为应用程序级别的窗口，不依赖父窗口
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # 设置窗口透明但确保能接收鼠标事件
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # 不设置样式表，让Qt自动处理透明背景

        # 设置鼠标追踪和焦点
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 确保窗口可见
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)

        logger.info("创建OCR区域选择覆盖层")

        # 初始化
        self.setup_target_window()

        # 显示提示信息
        logger.info("OCR区域选择器已启动")
        logger.info("使用说明:")
        logger.info("在绿色边框的目标窗口内拖拽鼠标进行选择")
        logger.info("右键点击或按ESC键取消选择")
        logger.info("选择完成后会自动填充坐标参数")
        
    def setup_target_window(self):
        """设置目标窗口并进行截图"""
        if not PYWIN32_AVAILABLE:
            QMessageBox.critical(self, "错误", "需要安装pywin32库")
            return False

        # 优先使用传入的窗口句柄，否则通过标题查找
        if self.target_hwnd:
            logger.info(f"使用传入的窗口句柄: {self.target_hwnd}")
            # 获取窗口标题用于显示
            try:
                import win32gui
                self.target_window_title = win32gui.GetWindowText(self.target_hwnd)
                logger.info(f"窗口句柄 {self.target_hwnd} 对应标题: {self.target_window_title}")
            except Exception as e:
                logger.warning(f"获取窗口标题失败: {e}")
                self.target_window_title = f"窗口{self.target_hwnd}"
        else:
            # 查找目标窗口
            self.target_hwnd = self._find_window_by_title(self.target_window_title)
            if not self.target_hwnd:
                QMessageBox.warning(self, "警告", f"未找到窗口: {self.target_window_title}")
                return False

        # 激活并置顶目标窗口
        self._activate_target_window(self.target_hwnd)

        # 获取窗口信息
        self.window_info = self._get_window_info(self.target_hwnd)
        if not self.window_info:
            QMessageBox.warning(self, "警告", "无法获取窗口信息")
            return False

        # 进行全屏截图
        if not self._take_screenshot():
            QMessageBox.warning(self, "警告", "无法进行截图")
            return False

        # 设置全屏覆盖
        self._setup_fullscreen_overlay()

        # 验证窗口位置是否正确（通过检查绿色边框是否在正确位置）
        self._verify_window_position()

        return True
        
    def _find_window_by_title(self, title: str) -> Optional[int]:
        """根据标题查找窗口（使用统一的窗口查找工具）"""
        if not title:
            return None

        logger.info(f" [窗口查找] 开始查找窗口: '{title}'")

        # 尝试检测模拟器类型
        emulator_type = None
        if title == "TheRender" or "雷电" in title or "LDPlayer" in title:
            emulator_type = "ldplayer"

        logger.info(f" [窗口查找] 检测到模拟器类型: {emulator_type}")

        # 使用统一的窗口查找工具
        hwnd = WindowFinder.find_window(title, emulator_type)
        if hwnd:
            # 验证找到的窗口
            found_title = win32gui.GetWindowText(hwnd)
            found_class = win32gui.GetClassName(hwnd)
            window_rect = win32gui.GetWindowRect(hwnd)
            client_rect = win32gui.GetClientRect(hwnd)

            logger.info(f" [窗口查找] 统一工具找到窗口:")
            logger.info(f" [窗口查找]   句柄: {hwnd}")
            logger.info(f" [窗口查找]   标题: '{found_title}'")
            logger.info(f" [窗口查找]   类名: '{found_class}'")
            logger.info(f" [窗口查找]   窗口矩形: {window_rect}")
            logger.info(f" [窗口查找]   客户区矩形: {client_rect}")

            return hwnd

        # 如果统一工具没找到，回退到原始方法
        logger.warning(f" [窗口查找] 统一窗口查找工具未找到窗口，尝试原始方法: {title}")
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    windows.append(hwnd)
                    logger.info(f" [窗口查找] 原始方法找到候选窗口: '{window_title}' (句柄: {hwnd})")
            return True

        windows = []
        win32gui.EnumWindows(enum_callback, windows)

        if windows:
            selected_hwnd = windows[0]
            selected_title = win32gui.GetWindowText(selected_hwnd)
            logger.info(f" [窗口查找] 原始方法选择窗口: '{selected_title}' (句柄: {selected_hwnd})")
            return selected_hwnd
        else:
            logger.error(f" [窗口查找] 未找到任何匹配的窗口: '{title}'")
            return None

    def _activate_target_window(self, hwnd: int):
        """激活并置顶目标窗口（如果是渲染窗口则置顶主窗口）"""
        try:
            # 获取需要置顶的窗口句柄（可能是主窗口）
            target_hwnd = self._get_window_to_activate(hwnd)

            user32 = ctypes.windll.user32

            # 检查窗口是否最小化，如果是则恢复
            if user32.IsIconic(target_hwnd):
                logger.info("目标窗口已最小化，正在恢复...")
                user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
                import time
                time.sleep(0.2)  # 等待窗口恢复

            # 将窗口置于前台
            user32.SetForegroundWindow(target_hwnd)

            # 激活窗口
            user32.SetActiveWindow(target_hwnd)

            # 确保窗口在最顶层
            user32.BringWindowToTop(target_hwnd)

            if target_hwnd != hwnd:
                logger.info(f"成功 已激活并置顶主窗口: {target_hwnd} (原绑定窗口: {hwnd})")
            else:
                logger.info(f"成功 已激活并置顶目标窗口: {self.target_window_title}")

        except Exception as e:
            logger.warning(f"激活目标窗口失败: {e}")
            # 即使激活失败也继续执行，不影响框选功能

    def _get_window_to_activate(self, hwnd: int) -> int:
        """获取需要激活的窗口句柄（如果是渲染窗口则返回主窗口）"""
        try:
            # 检测是否是MuMu渲染窗口
            from utils.emulator_detector import detect_emulator_type
            is_emulator, emulator_type, description = detect_emulator_type(hwnd)

            if is_emulator and emulator_type == "mumu":
                # 如果是MuMu渲染窗口，查找对应的主窗口
                from utils.input_simulation.emulator_window import EmulatorWindowInputSimulator
                emulator_window = EmulatorWindowInputSimulator(hwnd, "mumu", "background")
                main_hwnd = emulator_window._get_mumu_parent_window()
                if main_hwnd:
                    logger.debug(f"从渲染窗口 {hwnd} 找到主窗口 {main_hwnd} 用于置顶")
                    return main_hwnd

            # 如果不是渲染窗口或找不到主窗口，返回原窗口
            return hwnd

        except Exception as e:
            logger.debug(f"获取激活窗口失败: {e}")
            return hwnd

    def _get_window_info(self, hwnd: int) -> Optional[dict]:
        """获取窗口详细信息"""
        try:
            # 获取窗口类名和标题用于调试
            window_title = win32gui.GetWindowText(hwnd)
            window_class = win32gui.GetClassName(hwnd)

            logger.info(f" [窗口调试] 目标窗口: '{window_title}' (类名: {window_class}, 句柄: {hwnd})")

            # 检查是否为雷电模拟器的TheRender窗口
            if window_class == "RenderWindow" and window_title == "TheRender":
                logger.info(" [窗口调试] 检测到雷电模拟器TheRender窗口，查找父窗口...")

                # 获取父窗口（主窗口）
                parent_hwnd = win32gui.GetParent(hwnd)
                if parent_hwnd:
                    parent_title = win32gui.GetWindowText(parent_hwnd)
                    parent_class = win32gui.GetClassName(parent_hwnd)
                    logger.info(f" [窗口调试] 父窗口: '{parent_title}' (类名: {parent_class}, 句柄: {parent_hwnd})")

                    # 如果父窗口是LDPlayerMainFrame，使用混合策略
                    if parent_class == "LDPlayerMainFrame":
                        logger.info(" [窗口调试] 使用混合策略：父窗口用于截图，TheRender用于坐标")

                        # 使用TheRender的坐标信息（这是我们需要的游戏区域）
                        window_rect = win32gui.GetWindowRect(hwnd)  # TheRender的窗口矩形
                        client_rect = win32gui.GetClientRect(hwnd)  # TheRender的客户区
                        client_screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))  # TheRender的屏幕位置

                        # 获取Qt的DPI信息（移到这里避免变量未定义错误）
                        from PySide6.QtWidgets import QApplication
                        screen = QApplication.primaryScreen()
                        qt_dpi = screen.logicalDotsPerInch()
                        qt_device_pixel_ratio = screen.devicePixelRatio()
                        actual_dpi = int(qt_dpi * qt_device_pixel_ratio)

                        # 但是保存父窗口句柄用于截图
                        window_info = {
                            'hwnd': hwnd,  # 保持TheRender句柄用于坐标计算
                            'parent_hwnd': parent_hwnd,  # 父窗口句柄用于截图
                            'window_rect': window_rect,
                            'client_rect': client_rect,
                            'client_screen_pos': client_screen_pos,
                            'client_width': client_rect[2] - client_rect[0],
                            'client_height': client_rect[3] - client_rect[1],
                            'qt_dpi': qt_dpi,
                            'qt_device_pixel_ratio': qt_device_pixel_ratio,
                            'actual_dpi': actual_dpi,
                            'scale_factor': qt_device_pixel_ratio,
                            'is_ldplayer': True  # 标记为雷电模拟器
                        }

                        logger.info(f" [窗口调试] 混合策略设置完成")
                        logger.info(f" [窗口调试] TheRender窗口矩形: {window_rect}")
                        logger.info(f" [窗口调试] TheRender客户区矩形: {client_rect}")
                        logger.info(f" [窗口调试] TheRender客户区屏幕位置: {client_screen_pos}")
                        logger.info(f" [关键验证] 物理客户区位置: {client_screen_pos}")
                        qt_client_x = int(client_screen_pos[0] / qt_device_pixel_ratio)
                        qt_client_y = int(client_screen_pos[1] / qt_device_pixel_ratio)
                        logger.info(f" [关键验证] Qt逻辑客户区位置: ({qt_client_x}, {qt_client_y})")
                        logger.info(f" [关键验证] 这个位置应该对应阴阳师窗口的左上角！")

                        return window_info
                    else:
                        # 使用原始窗口信息
                        window_rect = win32gui.GetWindowRect(hwnd)
                        client_rect = win32gui.GetClientRect(hwnd)
                        client_screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))
                else:
                    # 没有父窗口，使用原始窗口信息
                    window_rect = win32gui.GetWindowRect(hwnd)
                    client_rect = win32gui.GetClientRect(hwnd)
                    client_screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))
            else:
                # 非雷电模拟器窗口，使用标准方法
                window_rect = win32gui.GetWindowRect(hwnd)
                client_rect = win32gui.GetClientRect(hwnd)
                client_screen_pos = win32gui.ClientToScreen(hwnd, (0, 0))

            # 使用Qt的DPI检测
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            qt_dpi = screen.logicalDotsPerInch()
            qt_device_pixel_ratio = screen.devicePixelRatio()

            # 基于Qt计算实际DPI
            actual_dpi = int(qt_dpi * qt_device_pixel_ratio)

            window_info = {
                'hwnd': hwnd,
                'window_rect': window_rect,
                'client_rect': client_rect,
                'client_screen_pos': client_screen_pos,
                'client_width': client_rect[2] - client_rect[0],
                'client_height': client_rect[3] - client_rect[1],
                'qt_dpi': qt_dpi,
                'qt_device_pixel_ratio': qt_device_pixel_ratio,
                'actual_dpi': actual_dpi,
                'scale_factor': qt_device_pixel_ratio
            }

            logger.info(f" [窗口调试] 最终窗口矩形: {window_rect}")
            logger.info(f" [窗口调试] 最终客户区矩形: {client_rect}")
            logger.info(f" [窗口调试] 最终客户区屏幕位置: {client_screen_pos}")
            logger.info(f"窗口信息: 客户区位置({client_screen_pos}), "
                       f"尺寸({window_info['client_width']}x{window_info['client_height']})")
            logger.info(f"DPI信息: Qt逻辑DPI={qt_dpi:.1f}, 设备像素比={qt_device_pixel_ratio:.2f}, 实际DPI={actual_dpi}")
            logger.info(f"缩放百分比: {qt_device_pixel_ratio*100:.0f}%")

            # 添加关键调试信息：验证窗口位置是否正确
            qt_client_x = int(client_screen_pos[0] / qt_device_pixel_ratio)
            qt_client_y = int(client_screen_pos[1] / qt_device_pixel_ratio)
            logger.info(f" [关键验证] 物理客户区位置: {client_screen_pos}")
            logger.info(f" [关键验证] Qt逻辑客户区位置: ({qt_client_x}, {qt_client_y})")
            logger.info(f" [关键验证] 这个位置应该对应阴阳师窗口的左上角！")

            return window_info

        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")
            return None
            
    def _take_screenshot(self) -> bool:
        """进行全屏截图"""
        try:
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QScreen

            # 获取主屏幕
            screen = QApplication.primaryScreen()
            if not screen:
                logger.error("无法获取主屏幕")
                return False

            # 进行全屏截图
            self.screenshot = screen.grabWindow(0)
            if self.screenshot.isNull():
                logger.error("截图失败")
                return False

            logger.info(f"截图成功: {self.screenshot.width()}x{self.screenshot.height()}")
            return True

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return False

    def _setup_fullscreen_overlay(self):
        """设置全屏覆盖层"""
        from PySide6.QtWidgets import QApplication

        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        device_pixel_ratio = screen.devicePixelRatio()

        # 设置为全屏
        self.setGeometry(screen_geometry)

        logger.info(f"全屏覆盖层设置: {screen_geometry}")
        logger.info(f"屏幕设备像素比率: {device_pixel_ratio}")

    def _verify_window_position(self):
        """验证窗口位置是否正确"""
        if not self.window_info:
            return

        try:
            # 获取覆盖层的实际几何信息
            overlay_geometry = self.geometry()
            client_screen_pos = self.window_info['client_screen_pos']
            qt_device_pixel_ratio = self.window_info['qt_device_pixel_ratio']

            # 计算绿色边框应该显示的位置
            qt_x = int(client_screen_pos[0] / qt_device_pixel_ratio)
            qt_y = int(client_screen_pos[1] / qt_device_pixel_ratio)

            logger.info(f" [位置验证] 覆盖层几何: {overlay_geometry}")
            logger.info(f" [位置验证] 窗口位置: {client_screen_pos}")
            logger.info(f" [位置验证] 绿色边框位置: ({qt_x}, {qt_y})")

            # 检查绿色边框是否在覆盖层范围内
            if (qt_x < overlay_geometry.x() or qt_x > overlay_geometry.right() or
                qt_y < overlay_geometry.y() or qt_y > overlay_geometry.bottom()):
                logger.warning(f" [位置异常] 绿色边框位置({qt_x}, {qt_y})超出覆盖层范围{overlay_geometry}")
                logger.warning(f" 这说明窗口位置信息可能不准确")
            else:
                logger.info(f" [位置验证] 窗口位置正常")

        except Exception as e:
            logger.error(f"窗口位置验证失败: {e}")

    def _get_relative_coordinates(self, overlay_pos: QPoint) -> QPoint:
        """将覆盖层坐标转换为窗口客户区相对坐标（修复版本）"""
        if not self.window_info:
            return overlay_pos

        try:
            # 获取窗口信息
            client_screen_pos = self.window_info.get('client_screen_pos', (0, 0))  # 物理坐标
            qt_device_pixel_ratio = self.window_info.get('qt_device_pixel_ratio', 1.0)
            hwnd = self.window_info.get('hwnd')

            logger.info(f" [坐标转换] 窗口信息: client_screen_pos={client_screen_pos}, qt_device_pixel_ratio={qt_device_pixel_ratio}")
            logger.info(f" [坐标转换] 输入覆盖层坐标(Qt逻辑): ({overlay_pos.x()}, {overlay_pos.y()})")

            # 正确的坐标转换方法：
            # 1. overlay_pos是Qt逻辑坐标（屏幕坐标）
            # 2. client_screen_pos是物理坐标（屏幕坐标）
            # 3. 需要将overlay_pos转换为物理坐标，然后计算相对位置

            # 将覆盖层Qt逻辑坐标转换为物理坐标
            overlay_physical_x = int(overlay_pos.x() * qt_device_pixel_ratio)
            overlay_physical_y = int(overlay_pos.y() * qt_device_pixel_ratio)

            # 计算相对于窗口客户区的物理坐标
            relative_physical_x = overlay_physical_x - client_screen_pos[0]
            relative_physical_y = overlay_physical_y - client_screen_pos[1]

            logger.info(f" [坐标转换详细] 覆盖层Qt逻辑: ({overlay_pos.x()}, {overlay_pos.y()})")
            logger.info(f" [坐标转换详细] 覆盖层物理坐标: ({overlay_physical_x}, {overlay_physical_y})")
            logger.info(f" [坐标转换详细] 窗口客户区物理位置: {client_screen_pos}")
            logger.info(f" [坐标转换详细] 最终相对物理坐标: ({relative_physical_x}, {relative_physical_y})")

            # 验证坐标合理性
            client_width = self.window_info.get('client_width', 0)
            client_height = self.window_info.get('client_height', 0)

            if relative_physical_x < 0 or relative_physical_y < 0 or relative_physical_x >= client_width or relative_physical_y >= client_height:
                logger.warning(f" [坐标验证] 转换后的坐标({relative_physical_x}, {relative_physical_y})超出窗口范围({client_width}x{client_height})")
                logger.warning(f" [坐标验证] 这可能表示坐标转换存在问题")
            else:
                logger.info(f" [坐标验证] 转换后的坐标在有效范围内")

            return QPoint(relative_physical_x, relative_physical_y)

        except Exception as e:
            logger.error(f"OCR坐标转换失败: {e}")
            return overlay_pos

    def _convert_rect_to_relative_coordinates(self, overlay_rect: QRect) -> QRect:
        """将覆盖层矩形转换为窗口客户区相对坐标矩形（修复版本）"""
        if not self.window_info:
            return overlay_rect

        try:
            # 获取窗口信息
            client_screen_pos = self.window_info.get('client_screen_pos', (0, 0))  # 物理坐标
            qt_device_pixel_ratio = self.window_info.get('qt_device_pixel_ratio', 1.0)

            logger.info(f" [矩形转换] 输入覆盖层矩形(Qt逻辑): ({overlay_rect.x()}, {overlay_rect.y()}) {overlay_rect.width()}x{overlay_rect.height()}")
            logger.info(f" [矩形转换] 窗口客户区屏幕位置(物理): {client_screen_pos}")
            logger.info(f" [矩形转换] Qt设备像素比率: {qt_device_pixel_ratio}")

            # overlay_rect是Qt逻辑坐标（屏幕坐标）
            # client_screen_pos是物理坐标（屏幕坐标）
            # 需要统一到同一坐标系统进行计算

            # 方法1：将overlay_rect转换为物理坐标，然后计算相对位置
            overlay_physical_x = int(overlay_rect.x() * qt_device_pixel_ratio)
            overlay_physical_y = int(overlay_rect.y() * qt_device_pixel_ratio)
            overlay_physical_width = int(overlay_rect.width() * qt_device_pixel_ratio)
            overlay_physical_height = int(overlay_rect.height() * qt_device_pixel_ratio)

            # 计算相对于窗口客户区的物理坐标
            relative_physical_x = overlay_physical_x - client_screen_pos[0]
            relative_physical_y = overlay_physical_y - client_screen_pos[1]

            logger.info(f" [矩形转换详细] 覆盖层物理坐标: ({overlay_physical_x}, {overlay_physical_y}) {overlay_physical_width}x{overlay_physical_height}")
            logger.info(f" [矩形转换详细] 窗口客户区物理位置: {client_screen_pos}")
            logger.info(f" [矩形转换详细] 最终相对物理坐标: ({relative_physical_x}, {relative_physical_y}) {overlay_physical_width}x{overlay_physical_height}")

            # 验证坐标合理性
            client_width = self.window_info.get('client_width', 0)
            client_height = self.window_info.get('client_height', 0)

            if (relative_physical_x < 0 or relative_physical_y < 0 or
                relative_physical_x + overlay_physical_width > client_width or
                relative_physical_y + overlay_physical_height > client_height):
                logger.warning(f" [矩形验证] 转换后的矩形({relative_physical_x}, {relative_physical_y}) {overlay_physical_width}x{overlay_physical_height}超出窗口范围({client_width}x{client_height})")
                logger.warning(f" [矩形验证] 这可能表示坐标转换存在问题")
            else:
                logger.info(f" [矩形验证] 转换后的矩形在有效范围内")

            return QRect(relative_physical_x, relative_physical_y, overlay_physical_width, overlay_physical_height)

        except Exception as e:
            logger.error(f"OCR矩形转换失败: {e}")
            return overlay_rect

    def _save_selection_debug_image(self, x: int, y: int, width: int, height: int):
        """调试图像保存功能已禁用"""
        pass

    def _is_point_in_target_window(self, qt_screen_pos: QPoint) -> bool:
        """检查点是否在目标窗口客户区内（使用Qt逻辑坐标）"""
        if not self.window_info:
            return False

        # 使用Qt设备像素比进行坐标转换
        client_screen_pos = self.window_info['client_screen_pos']
        client_width = self.window_info['client_width']
        client_height = self.window_info['client_height']
        qt_device_pixel_ratio = self.window_info['qt_device_pixel_ratio']

        # Win32坐标转换为Qt逻辑坐标（用于正确的范围检查）
        qt_client_x = int(client_screen_pos[0] / qt_device_pixel_ratio)
        qt_client_y = int(client_screen_pos[1] / qt_device_pixel_ratio)
        qt_client_width = int(client_width / qt_device_pixel_ratio)
        qt_client_height = int(client_height / qt_device_pixel_ratio)

        return (qt_client_x <= qt_screen_pos.x() <= qt_client_x + qt_client_width and
                qt_client_y <= qt_screen_pos.y() <= qt_client_y + qt_client_height)
        
    def paintEvent(self, event):
        """绘制事件 - 透明背景，只绘制边框和选择框"""
        painter = QPainter(self)

        # 设置抗锯齿
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制一个几乎透明的背景，确保能接收鼠标事件
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))  # 几乎透明但不是完全透明

        # 不绘制提示文字，保持界面简洁

        # 绘制目标窗口边框（如果有）
        if hasattr(self, 'target_window_rect') and self.target_window_rect:
            pen = QPen(QColor(0, 255, 0), 3)  # 绿色边框
            painter.setPen(pen)
            painter.drawRect(self.target_window_rect)

        # 第一个选择框绘制逻辑已移除，避免重复绘制

        # 绘制目标窗口区域标识
        if self.window_info:
            client_screen_pos = self.window_info['client_screen_pos']
            client_width = self.window_info['client_width']
            client_height = self.window_info['client_height']
            qt_device_pixel_ratio = self.window_info['qt_device_pixel_ratio']

            # 正确的坐标转换：Win32物理坐标转换为Qt逻辑坐标
            # client_screen_pos是物理坐标，需要除以DPI比率得到Qt逻辑坐标
            qt_x = int(client_screen_pos[0] / qt_device_pixel_ratio)
            qt_y = int(client_screen_pos[1] / qt_device_pixel_ratio)
            qt_width = int(client_width / qt_device_pixel_ratio)
            qt_height = int(client_height / qt_device_pixel_ratio)

            target_rect = QRect(qt_x, qt_y, qt_width, qt_height)

            # 绘制目标窗口边框（绿色，较粗便于观察）
            pen = QPen(QColor(0, 255, 0), 4)
            painter.setPen(pen)
            painter.drawRect(target_rect)

            # 不绘制目标窗口内的提示文字

        # 绘制选择框
        if self.selecting and self.start_pos != self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            # 绘制选择框（红色边框）
            pen = QPen(QColor(255, 0, 0), 3)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 填充选择区域（半透明红色）
            painter.fillRect(rect, QColor(255, 0, 0, 50))

            # 显示坐标信息
            if self.window_info:
                relative_start = self._get_relative_coordinates(self.start_pos)
                relative_end = self._get_relative_coordinates(self.end_pos)
                relative_rect = QRect(relative_start, relative_end).normalized()

                info_text = f"({relative_rect.x()}, {relative_rect.y()}) {relative_rect.width()}x{relative_rect.height()}"
            else:
                info_text = f"({rect.x()}, {rect.y()}) {rect.width()}x{rect.height()}"

            # 绘制坐标文字
            painter.setPen(QPen(QColor(255, 255, 255)))
            text_pos = rect.topLeft() + QPoint(5, -10)
            painter.fillRect(text_pos.x() - 2, text_pos.y() - 15, 200, 20, QColor(0, 0, 0, 150))
            painter.drawText(text_pos, info_text)

        # 绘制全局提示
        painter.setPen(QPen(QColor(255, 255, 255)))
        painter.drawText(50, 50, "拖拽鼠标选择区域 | 右键或ESC取消")
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        logger.info(f"🖱 [鼠标按下] 按钮={event.button()}, 位置={event.pos()}")
        logger.info(f"🖱 [鼠标按下] 全局位置={event.globalPos()}")
        logger.info(f"🖱 [鼠标按下] 覆盖层几何信息: {self.geometry()}")
        logger.info(f"🖱 [鼠标按下] 覆盖层可见性: {self.isVisible()}")

        # 添加屏幕和DPI信息
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        logger.info(f"🖱 [鼠标按下] 屏幕几何: {screen.geometry()}")
        logger.info(f"🖱 [鼠标按下] 屏幕DPI比率: {screen.devicePixelRatio()}")

        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
            self.selecting = True

            # 详细的鼠标坐标调试
            global_pos = event.globalPos()
            screen_pos = event.screenPos()
            overlay_geometry = self.geometry()

            logger.info(f"🖱 [鼠标按下] 覆盖层坐标: {event.pos()}")
            logger.info(f"🖱 [鼠标按下] 全局坐标: {global_pos}")
            logger.info(f"🖱 [鼠标按下] 屏幕坐标: {screen_pos}")
            logger.info(f"🖱 [鼠标按下] 覆盖层几何: {overlay_geometry}")

            # 计算预期的覆盖层坐标（如果覆盖层真的是全屏的话）
            expected_overlay_x = global_pos.x() - overlay_geometry.x()
            expected_overlay_y = global_pos.y() - overlay_geometry.y()
            logger.info(f"🖱 [坐标验证] 预期覆盖层坐标: ({expected_overlay_x}, {expected_overlay_y})")
            logger.info(f"🖱 [坐标验证] 实际覆盖层坐标: ({event.pos().x()}, {event.pos().y()})")

            # 检查坐标一致性
            coord_diff_x = abs(event.pos().x() - expected_overlay_x)
            coord_diff_y = abs(event.pos().y() - expected_overlay_y)
            if coord_diff_x > 5 or coord_diff_y > 5:
                logger.error(f" [坐标系统错误] 覆盖层坐标系统不正确！")
                logger.error(f" 坐标差异: X={coord_diff_x}, Y={coord_diff_y}")
                logger.error(f" 这说明覆盖层的位置或坐标转换有问题")

            # 立即转换为窗口相对坐标进行调试
            if self.window_info:
                relative_pos = self._get_relative_coordinates(event.pos())
                logger.info(f"🖱 [鼠标按下] 转换为窗口坐标: {relative_pos}")

            self.setCursor(Qt.CursorShape.CrossCursor)
            self.update()
            # 接受事件，防止传递给其他窗口
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键取消
            logger.info("鼠标 右键点击，关闭选择器")
            self.close()
            event.accept()
        else:
            logger.info(f"鼠标 其他鼠标按钮: {event.button()}")
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.selecting:
            self.end_pos = event.pos()
            logger.debug(f"🖱 [鼠标] 拖拽: {self.start_pos} -> {self.end_pos}, selecting={self.selecting}")
            self.update()
            event.accept()
        else:
            # 设置鼠标样式
            if self.window_info and self._is_point_in_target_window(event.pos()):
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.selecting:
            self.selecting = False

            # 计算选择区域
            rect = QRect(self.start_pos, event.pos()).normalized()
            logger.info(f"🖱 [鼠标释放] 覆盖层坐标: 开始={self.start_pos}, 结束={event.pos()}")
            logger.info(f"🖱 [鼠标释放] 覆盖层矩形: {rect}")

            if rect.width() > 10 and rect.height() > 10:
                # 检查选择区域是否在目标窗口内
                if self.window_info:
                    # 检查开始和结束位置是否都在目标窗口客户区内
                    start_in_window = self._is_point_in_target_window(self.start_pos)
                    end_in_window = self._is_point_in_target_window(event.pos())

                    if not start_in_window or not end_in_window:
                        logger.warning("选择区域超出目标窗口客户区，请在绿色边框内进行选择")
                        # 显示提示信息，但不关闭覆盖层，允许用户重新选择
                        self.setCursor(Qt.CursorShape.ArrowCursor)
                        self.update()
                        return

                    # 保存原始框选区域（Qt屏幕坐标）用于调试对比
                    self.last_selection_rect = rect

                    # 使用统一的区域转换方法，避免分别转换起始和结束点导致的误差
                    relative_rect = self._convert_rect_to_relative_coordinates(rect)

                    # 发射选择信号（使用相对坐标）
                    logger.info(f"区域选择完成: ({relative_rect.x()}, {relative_rect.y()}, {relative_rect.width()}, {relative_rect.height()})")

                    # 直接发射信号，让父组件处理坐标转换
                    self.region_selected.emit(relative_rect.x(), relative_rect.y(),
                                            relative_rect.width(), relative_rect.height())
                else:
                    # 没有窗口信息，使用屏幕坐标（这种情况下不进行边界检查）
                    logger.warning("没有窗口信息，使用屏幕坐标")
                    logger.info(f"区域选择完成(屏幕坐标): ({rect.x()}, {rect.y()}, {rect.width()}, {rect.height()})")
                    # 直接发射信号，让父组件处理坐标转换
                    self.region_selected.emit(rect.x(), rect.y(), rect.width(), rect.height())

                self.close()
            else:
                logger.warning(f"选择区域太小: {rect.width()}x{rect.height()}")
                # 重置选择状态，允许用户重新选择
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()

            event.accept()
                
    def keyPressEvent(self, event):
        """键盘事件"""
        logger.info(f"键盘 键盘事件: {event.key()}")
        if event.key() == Qt.Key.Key_Escape:
            logger.info("键盘 ESC键取消选择")
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击事件 - 关闭覆盖层"""
        logger.info("鼠标 双击关闭覆盖层")
        self.close()
        event.accept()

    def showEvent(self, event):
        """显示事件"""
        from PySide6.QtWidgets import QApplication
        logger.info("👁 OCR区域选择器显示事件触发")
        logger.info(f"手机 窗口几何信息: {self.geometry()}")
        logger.info(f"台式机 屏幕几何信息: {QApplication.primaryScreen().geometry()}")
        super().showEvent(event)

        # 强制窗口在最顶层，即使有模态对话框打开
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # 设置窗口模态性，确保能接收事件
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 使用Windows API强制置顶并确保能接收事件（如果在Windows上）
        if PYWIN32_AVAILABLE:
            try:
                import ctypes
                hwnd = int(self.winId())

                # 设置窗口为最顶层
                ctypes.windll.user32.SetWindowPos(
                    hwnd, -1,  # HWND_TOPMOST
                    0, 0, 0, 0,
                    0x0001 | 0x0002  # SWP_NOSIZE | SWP_NOMOVE (移除SWP_NOACTIVATE)
                )

                # 强制激活窗口，确保能接收鼠标事件
                ctypes.windll.user32.SetActiveWindow(hwnd)
                ctypes.windll.user32.SetForegroundWindow(hwnd)

                # 确保窗口可以接收输入
                ctypes.windll.user32.EnableWindow(hwnd, True)

                logger.info("成功 使用Windows API强制置顶并激活成功")
            except Exception as e:
                logger.warning(f"Windows API置顶失败: {e}")

        # 设置键盘焦点策略
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 确保鼠标追踪开启
        self.setMouseTracking(True)

        # 强制刷新窗口状态
        self.repaint()

        # 使用定时器延迟确保窗口完全显示后再次获得焦点
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, self._ensure_focus)

        logger.info(f"鼠标 鼠标追踪状态: {self.hasMouseTracking()}")
        logger.info(f"鼠标 窗口标志: {self.windowFlags()}")

    def _ensure_focus(self):
        """确保窗口获得焦点"""
        self.raise_()
        self.activateWindow()
        self.setFocus()
        logger.info("靶心 延迟焦点设置完成")

    def closeEvent(self, event):
        """关闭事件"""
        logger.info(" OCR区域选择器关闭，发出关闭信号")
        self.overlay_closed.emit()
        super().closeEvent(event)

class OCRRegionSelectorWidget(QWidget):
    """OCR区域选择器控件"""

    region_selected = Signal(int, int, int, int)  # x, y, width, height
    selection_started = Signal()  # 选择开始信号
    selection_finished = Signal()  # 选择结束信号（无论成功还是取消）
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_window_title = None
        self.target_window_hwnd = None  # 添加窗口句柄属性
        self.current_region = (0, 0, 0, 0)

        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # 选择按钮
        self.select_button = QPushButton("框选识别指定区域")
        self.select_button.clicked.connect(self.start_selection)
        layout.addWidget(self.select_button)

        # 不再显示区域信息，避免与参数界面的显示重复
        # 区域信息将通过 region_coordinates 参数显示
        
    def set_target_window(self, window_title: str):
        """设置目标窗口"""
        self.target_window_title = window_title
        if window_title:
            self.select_button.setText(f"框选区域 (目标: {window_title})")
            self.select_button.setToolTip(f"在窗口 '{window_title}' 中框选OCR识别区域")
        else:
            self.select_button.setText("框选识别指定区域")
            self.select_button.setToolTip("请先绑定目标窗口")

    def set_target_window_hwnd(self, window_hwnd: int):
        """设置目标窗口句柄"""
        self.target_window_hwnd = window_hwnd
        if window_hwnd:
            # 获取窗口标题用于显示
            try:
                import win32gui
                window_title = win32gui.GetWindowText(window_hwnd)
                self.target_window_title = window_title
                self.select_button.setText(f"框选区域 (目标: {window_title})")
                self.select_button.setToolTip(f"在窗口 '{window_title}' (HWND: {window_hwnd}) 中框选OCR识别区域")
                logger.info(f"设置目标窗口句柄: {window_hwnd}, 标题: {window_title}")
            except Exception as e:
                logger.warning(f"获取窗口标题失败: {e}")
                self.target_window_title = f"窗口{window_hwnd}"
                self.select_button.setText(f"框选区域 (目标: 窗口{window_hwnd})")
                self.select_button.setToolTip(f"在窗口 {window_hwnd} 中框选OCR识别区域")
        else:
            self.select_button.setText("框选识别指定区域")
            self.select_button.setToolTip("请先绑定目标窗口")

    def _get_bound_window_from_editor(self) -> Optional[str]:
        """从编辑器获取已绑定的窗口标题（支持多窗口模式）"""
        try:
            # 方法1: 从配置文件获取
            import json
            import os
            config_file = "config.json"
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        target_window_title = config.get('target_window_title')
                        if target_window_title:
                            logger.info(f"从配置文件获取目标窗口: {target_window_title}")
                            return target_window_title
                except Exception as e:
                    logger.warning(f"读取配置文件失败: {e}")

            # 方法2: 从父窗口获取绑定的窗口列表（支持多窗口）
            current_widget = self.parent()
            level = 0
            while current_widget and level < 10:  # 最多查找10层
                # 检查是否有bound_windows属性（多窗口模式）
                if hasattr(current_widget, 'bound_windows'):
                    bound_windows = current_widget.bound_windows
                    if bound_windows and len(bound_windows) > 0:
                        # 获取第一个启用的窗口
                        for window_info in bound_windows:
                            if window_info.get('enabled', True):
                                window_title = window_info.get('title')
                                if window_title:
                                    logger.info(f"从多窗口绑定列表获取第一个启用窗口: {window_title}")
                                    return window_title

                        # 如果没有启用的窗口，使用第一个窗口
                        first_window = bound_windows[0]
                        window_title = first_window.get('title')
                        if window_title:
                            logger.info(f"从多窗口绑定列表获取第一个窗口: {window_title}")
                            return window_title

                # 检查是否有runner属性（单窗口模式）
                if hasattr(current_widget, 'runner'):
                    runner = current_widget.runner
                    if hasattr(runner, 'target_window_title'):
                        target_window_title = runner.target_window_title
                        if target_window_title:
                            logger.info(f"从第{level}层窗口runner获取目标窗口: {target_window_title}")
                            return target_window_title

                # 检查是否有直接的target_window_title属性
                if hasattr(current_widget, 'target_window_title'):
                    target_window_title = current_widget.target_window_title
                    if target_window_title:
                        logger.info(f"从第{level}层窗口属性获取目标窗口: {target_window_title}")
                        return target_window_title

                # 向上查找父窗口
                current_widget = current_widget.parent()
                level += 1

            logger.warning("未找到编辑器绑定的目标窗口")
            return None

        except Exception as e:
            logger.error(f"获取编辑器绑定窗口时出错: {e}")
            return None
            
    def start_selection(self):
        """开始区域选择"""
        # 清理之前的覆盖层（如果存在）
        self._cleanup_previous_overlay()

        # 发出选择开始信号
        logger.info("靶心 发出OCR区域选择开始信号")
        self.selection_started.emit()

        # 优先使用窗口句柄，否则使用窗口标题
        if self.target_window_hwnd:
            # 使用窗口句柄创建覆盖层
            logger.info(f"工具 开始创建覆盖层，使用窗口句柄: {self.target_window_hwnd}")
            overlay = OCRRegionSelectorOverlay(target_window_hwnd=self.target_window_hwnd)
        elif self.target_window_title:
            # 使用窗口标题创建覆盖层
            logger.info(f"工具 开始创建覆盖层，使用窗口标题: {self.target_window_title}")
            overlay = OCRRegionSelectorOverlay(self.target_window_title)
        else:
            # 如果没有设置目标窗口，尝试自动获取编辑器绑定的窗口
            self.target_window_title = self._get_bound_window_from_editor()
            if self.target_window_title:
                # 更新按钮文本显示自动获取的窗口
                self.select_button.setText(f"框选区域 (已绑定: {self.target_window_title})")
                logger.info(f"靶心 自动获取编辑器绑定的窗口: {self.target_window_title}")
                overlay = OCRRegionSelectorOverlay(self.target_window_title)
            else:
                QMessageBox.warning(self, "警告", "未找到编辑器绑定的窗口，请先在编辑器中绑定目标窗口")
                return

        # 创建选择覆盖层并保持引用
        logger.info(f"工具 覆盖层对象创建完成: {overlay}")

        if overlay is None:
            logger.error("错误 覆盖层对象为 None")
            QMessageBox.critical(self, "错误", "覆盖层对象创建失败")
            return

        logger.info(f"工具 开始连接信号...")
        overlay.region_selected.connect(self._on_region_selected)

        # 连接覆盖层关闭信号
        overlay.overlay_closed.connect(self._on_overlay_closed)
        logger.info("成功 信号连接成功")

        # 直接使用局部变量，不依赖实例属性
        # 将overlay保存到一个不会被干扰的地方
        self.__dict__['_current_overlay'] = overlay
        logger.info("成功 覆盖层保存成功")

        # 当覆盖层销毁时清理引用（不发出信号）
        def on_overlay_destroyed():
            logger.info("靶心 OCR覆盖层销毁，清理引用")
            if '_current_overlay' in self.__dict__:
                del self.__dict__['_current_overlay']
        overlay.destroyed.connect(on_overlay_destroyed)

        if overlay.setup_target_window():
            logger.info("启动 显示OCR区域选择覆盖层")

            # 强制显示在最顶层，即使有对话框
            overlay.show()
            overlay.raise_()
            overlay.activateWindow()

            # 使用定时器多次尝试获得焦点，确保能覆盖模态对话框
            from PySide6.QtCore import QTimer
            def force_top():
                overlay.raise_()
                overlay.activateWindow()
                overlay.setFocus()

                # 额外的Windows API调用确保置顶
                if PYWIN32_AVAILABLE:
                    try:
                        import ctypes
                        hwnd = int(overlay.winId())
                        ctypes.windll.user32.SetWindowPos(
                            hwnd, -1,  # HWND_TOPMOST
                            0, 0, 0, 0,
                            0x0001 | 0x0002 | 0x0010  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
                        )
                        # 强制获得焦点
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                    except Exception as e:
                        logger.warning(f"强制置顶失败: {e}")

            # 多次尝试确保窗口在最顶层，覆盖模态对话框
            QTimer.singleShot(50, force_top)
            QTimer.singleShot(150, force_top)
            QTimer.singleShot(300, force_top)
            QTimer.singleShot(500, force_top)  # 额外的尝试

            logger.info(f"手机 覆盖层几何信息: {overlay.geometry()}")
            logger.info(f"👁 覆盖层可见性: {overlay.isVisible()}")
        else:
            logger.error("错误 设置目标窗口失败")
            overlay.deleteLater()
            if '_current_overlay' in self.__dict__:
                del self.__dict__['_current_overlay']
            
    def _on_region_selected(self, x: int, y: int, width: int, height: int):
        """处理区域选择完成（直接使用原始坐标，不进行DPI转换）"""
        logger.info(f"OCR区域选择完成: ({x}, {y}, {width}, {height})")

        try:
            # 获取当前绑定的窗口句柄（用于日志记录）
            bound_hwnd = self._get_bound_window_hwnd()

            if bound_hwnd:
                logger.info(f"OCR区域基于窗口 HWND:{bound_hwnd}: ({x}, {y}, {width}, {height})")
            else:
                logger.warning(f"OCR区域（无窗口句柄）: ({x}, {y}, {width}, {height})")

            # 直接使用原始坐标，不进行任何DPI转换
            # 这样可以避免重复缩放导致的坐标偏移问题
            self.current_region = (x, y, width, height)
            self.region_selected.emit(x, y, width, height)

            logger.info(f"OCR区域选择处理完成，使用原始坐标: ({x}, {y}, {width}, {height})")

        except Exception as e:
            logger.error(f"处理OCR区域选择失败: {e}")
            # 回退到原始处理方式
            self.current_region = (x, y, width, height)
            self.region_selected.emit(x, y, width, height)

    def _get_bound_window_hwnd(self) -> Optional[int]:
        """获取当前绑定的窗口句柄"""
        try:
            # 向上查找主窗口，获取绑定的窗口信息
            current_widget = self.parent()
            level = 0
            max_levels = 10

            while current_widget and level < max_levels:
                # 检查是否有config属性（主窗口）
                if hasattr(current_widget, 'config'):
                    config = current_widget.config

                    # 单窗口模式
                    if hasattr(config, 'target_window_title') and config.target_window_title:
                        return self._find_window_by_title(config.target_window_title)

                    # 多窗口模式
                    if hasattr(config, 'bound_windows') and config.bound_windows:
                        enabled_windows = [w for w in config.bound_windows if w.get('enabled', True)]
                        if enabled_windows:
                            return enabled_windows[0].get('hwnd')

                # 检查是否有runner属性
                if hasattr(current_widget, 'runner') and hasattr(current_widget.runner, 'config'):
                    config = current_widget.runner.config

                    if hasattr(config, 'target_window_title') and config.target_window_title:
                        return self._find_window_by_title(config.target_window_title)

                    if hasattr(config, 'bound_windows') and config.bound_windows:
                        enabled_windows = [w for w in config.bound_windows if w.get('enabled', True)]
                        if enabled_windows:
                            return enabled_windows[0].get('hwnd')

                current_widget = current_widget.parent()
                level += 1

            return None

        except Exception as e:
            logger.error(f"获取绑定窗口句柄失败: {e}")
            return None

    def _find_window_by_title(self, title: str) -> Optional[int]:
        """通过标题查找窗口句柄"""
        try:
            if not PYWIN32_AVAILABLE:
                return None

            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if title in window_title:
                        windows.append(hwnd)
                return True

            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)

            return windows[0] if windows else None

        except Exception as e:
            logger.error(f"查找窗口失败: {e}")
            return None

    def _save_region_record(self, original_region, normalized_region, hwnd: int):
        """保存区域记录用于DPI适配"""
        try:
            # 获取通用分辨率适配器
            adapter = get_universal_adapter()
            window_state = adapter.get_window_state(hwnd)

            if window_state:
                # 创建区域记录
                record = {
                    'window_title': window_state.title,
                    'original_region': {
                        'x': original_region.x, 'y': original_region.y,
                        'width': original_region.width, 'height': original_region.height
                    },
                    'normalized_region': {
                        'x': normalized_region.x, 'y': normalized_region.y,
                        'width': normalized_region.width, 'height': normalized_region.height
                    },
                    'window_state': {
                        'width': window_state.width, 'height': window_state.height,
                        'dpi': window_state.dpi, 'scale_factor': window_state.scale_factor
                    },
                    'timestamp': time.time()
                }

                logger.debug(f"保存OCR区域记录: {record}")

        except Exception as e:
            logger.error(f"保存区域记录失败: {e}")

    def _save_region_dpi_info(self, x: int, y: int, width: int, height: int):
        """保存区域选择时的DPI信息"""
        try:
            from utils.unified_dpi_handler import get_unified_dpi_handler

            # 获取当前DPI信息
            dpi_info = self._get_current_dpi_info()
            if not dpi_info:
                logger.warning("警告 [DPI记录] 无法获取DPI信息，跳过保存")
                return

            # 使用DPI管理器保存记录
            dpi_handler = get_unified_dpi_handler()
            success = dpi_handler.save_region_dpi_record(
                self.window_title, x, y, width, height, dpi_info
            )

            if success:
                logger.info(f"成功 [DPI记录] 区域DPI信息保存成功")
            else:
                logger.warning(f"警告 [DPI记录] 区域DPI信息保存失败")

        except Exception as e:
            logger.error(f"错误 [DPI记录] 保存DPI信息失败: {e}")

    def _get_current_dpi_info(self) -> dict:
        """获取当前DPI信息"""
        try:
            if not self.window_info:
                return None

            # 从窗口信息中获取DPI数据
            hwnd = self.window_info.get('hwnd', 0)

            # 使用DPI管理器获取DPI信息
            from utils.unified_dpi_handler import get_unified_dpi_handler
            dpi_handler = get_unified_dpi_handler()
            return dpi_handler.get_current_window_dpi_info(hwnd)

        except Exception as e:
            logger.error(f"获取DPI信息失败: {e}")
            return None

    def _cleanup_previous_overlay(self):
        """清理之前的覆盖层"""
        if '_current_overlay' in self.__dict__:
            overlay = self.__dict__['_current_overlay']
            if overlay:
                logger.info("扫帚 清理之前的覆盖层")
                # 断开所有信号连接，避免触发不必要的信号
                try:
                    overlay.overlay_closed.disconnect()
                    overlay.region_selected.disconnect()
                    overlay.destroyed.disconnect()  # 断开destroyed信号
                    logger.info("成功 已断开所有覆盖层信号连接")
                except Exception as e:
                    logger.warning(f"断开信号连接失败: {e}")

                # 先清理引用，避免destroyed信号触发时找到引用
                del self.__dict__['_current_overlay']

                # 直接删除覆盖层，不调用close()避免触发closeEvent
                overlay.hide()  # 先隐藏
                overlay.deleteLater()  # 直接删除
                logger.info("成功 覆盖层已隐藏并标记删除")

    def _on_overlay_closed(self):
        """覆盖层关闭时的处理"""
        logger.info("靶心 OCR覆盖层关闭，发出选择结束信号")
        self.selection_finished.emit()

    def get_region(self) -> Tuple[int, int, int, int]:
        """获取当前选择的区域"""
        return self.current_region
        
    def set_region(self, x: int, y: int, width: int, height: int):
        """设置区域"""
        self.current_region = (x, y, width, height)
        # 不再更新UI显示，区域信息将通过参数界面的 region_coordinates 显示
