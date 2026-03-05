import math
import logging
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsLineItem, QGraphicsPolygonItem
from PySide6.QtCore import Qt, QPointF
# QPainter, QPolygonF, QBrush are no longer needed here
from PySide6.QtGui import QPen, QColor, QPainterPath
# Import port types from TaskCard to avoid string literals here
from .task_card import PORT_TYPE_SEQUENTIAL, PORT_TYPE_SUCCESS, PORT_TYPE_FAILURE
from typing import TYPE_CHECKING, Optional
# Import Enum
from enum import Enum

logger = logging.getLogger(__name__)

# 调试开关 - 设置为 False 可以禁用所有调试输出
DEBUG_ENABLED = False

def debug_print(*args, **kwargs):
    """条件调试打印函数"""
    if DEBUG_ENABLED:
        print(*args, **kwargs)

# Import theme system
try:
    from ui.theme_manager import ThemeManager
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

# Forward reference for type hinting
if TYPE_CHECKING:
    from .task_card import TaskCard

# Define ConnectionType Enum
class ConnectionType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    # Add other types if needed

class ConnectionLine(QGraphicsPathItem):
    """Represents a connection line with refined style."""
    def __init__(self, start_item: 'TaskCard', end_item: 'TaskCard', line_type: str, parent=None):
        super().__init__(parent)
        debug_print(f"  [CONN_DEBUG] ConnectionLine __init__: Start={start_item.card_id}, End={end_item.card_id}, Type='{line_type}'")
        self.start_item = start_item
        self.end_item = end_item
        self.line_type = line_type
        
        self.pen = QPen()
        self.pen.setWidthF(1.5) # Make line slightly thinner
        self.set_line_color()
        self.setPen(self.pen)
        self.setZValue(0)  # 设置与卡片同级的 zValue，确保可以被点击到
        self.setBrush(Qt.BrushStyle.NoBrush) # Ensure the path item itself has no fill
        
        # --- ADDED: 悬停效果支持 ---
        self._is_hovered = False
        self._is_dashed = False  # 是否为虚线（用于悬停时表示可删除）
        self._original_pen = QPen(self.pen)
        self.setAcceptHoverEvents(True)  # 启用悬停事件
        self._hover_detection_width = 20.0  # 悬停检测宽度（像素）- 增加到20以改善用户体验
        # --- END ADDED ---
        
        self.update_path()

    def set_line_color(self):
        """Sets the pen color based on the line type (less saturated)."""
        debug_print(f"  [CONN_DEBUG] set_line_color called for type: '{self.line_type}'")
            
        # 尝试从主题系统获取颜色
        if THEME_AVAILABLE:
            try:
                theme_manager = QApplication.instance().theme_manager
                colors = theme_manager.get_palette()
                    
                # 根据连接类型选择颜色，并使用更淡的透明度
                if self.line_type == ConnectionType.SUCCESS.value:
                    # 绿色连接线 - 使用更淡的颜色
                    base_color = QColor(76, 175, 80)  # Material Design Green 500
                    color = QColor(base_color.red(), base_color.green(), base_color.blue(), 140)  # Alpha 140/255
                elif self.line_type == ConnectionType.FAILURE.value:
                    # 红色连接线 - 使用更淡的颜色
                    base_color = QColor(244, 67, 54)  # Material Design Red 500
                    color = QColor(base_color.red(), base_color.green(), base_color.blue(), 140)  # Alpha 140/255
                else:
                    # 顺序连接使用主要强调色，但降低饱和度和透明度
                    primary = QColor(colors.get('highlight', QColor(0, 120, 212)))
                    # 降低饱和度并增加透明度
                    h, s, l, a = primary.getHslF()
                    color = QColor.fromHslF(h, s * 0.5, l + 0.15, 140)  # Alpha 140/255
            except Exception as e:
                logger.debug(f"获取主题颜色失败，使用默认：{e}")
                color = self._get_default_color()
        else:
            color = self._get_default_color()
            
        self.pen.setColor(color)
        self.setPen(self.pen) # Apply the updated pen to the item
    
    def _get_default_color(self) -> QColor:
        """获取默认颜色（柔和、低饱和度）"""
        if self.line_type == ConnectionType.SUCCESS.value:
            # 柔和绿色 - 使用更淡的颜色
            return QColor(76, 175, 80, 140)    # Material Green 500 with Alpha 140
        elif self.line_type == ConnectionType.FAILURE.value:
            # 柔和红色 - 使用更淡的颜色
            return QColor(244, 67, 54, 140)    # Material Red 500 with Alpha 140
        else:
            # 柔和蓝色 - 使用更淡的颜色
            return QColor(33, 150, 243, 140)   # Material Blue 500 with Alpha 140

    def get_start_pos(self) -> QPointF:
        """Gets the connection point from the start item's corresponding output port."""
        if self.start_item:
            return self.start_item.get_output_port_scene_pos(self.line_type)
        return QPointF(0,0)

    def get_end_pos(self) -> QPointF:
        """Gets the connection point from the end item's corresponding input port."""
        if self.end_item:
            return self.end_item.get_input_port_scene_pos(self.line_type)
        return QPointF(0,0)

    def shape(self) -> QPainterPath:
        """扩展点击检测范围，增加悬停灵敏度"""
        try:
            # 使用路径描边创建更宽的点击区域
            from PySide6.QtGui import QPainterPathStroker
            stroker = QPainterPathStroker()
            stroker.setWidthF(self._hover_detection_width)
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            wide_shape = stroker.createStroke(self.path())
            return wide_shape
        except Exception:
            # 如果出错，返回默认形状
            return super().shape()

    def update_path(self):
        """Recalculates and sets the path as a cubic Bezier curve (no arrowhead)."""
        if not self.start_item or not self.end_item or not self.start_item.scene() or not self.end_item.scene():
            self.setPath(QPainterPath())
            return

        start_pos = self.get_start_pos()
        end_pos = self.get_end_pos()

        # --- ADDED: Log calculated positions ---
        debug_print(f"    [UPDATE_PATH_DEBUG] Connection {self.start_item.card_id if self.start_item else 'N/A'}->{self.end_item.card_id if self.end_item else 'N/A'} ({self.line_type}):")
        debug_print(f"      Start Pos: {start_pos}")
        debug_print(f"      End Pos:   {end_pos}")
        debug_print(f"      Start Restricted: {getattr(self.start_item, 'restricted_outputs', False)}")
        debug_print(f"      Start Item Scene: {self.start_item.scene() is not None}")
        debug_print(f"      End Item Scene: {self.end_item.scene() is not None}")
        # ---------------------------------------

        if start_pos == end_pos:
            # --- ADDED: Log when positions are equal ---
            debug_print(f"      [UPDATE_PATH_WARN] Start and End positions are equal! Setting empty path.")
            # -------------------------------------------
            self.setPath(QPainterPath())
            return

        # --- Create Cubic Bezier Curve --- 
        path = QPainterPath(start_pos)
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - dx * 0.5, end_pos.y())
        path.cubicTo(ctrl1, ctrl2, end_pos)

        # Update the item's path directly
        self.prepareGeometryChange() # Notify system bounding rect might change
        self.setPath(path)
        self.update() # Explicitly request an update for this item

    # --- ADDED: Override paint to support dashed hover effect ---
    def paint(self, painter, option, widget=None):
        # 如果悬停，绘制虚线效果
        if self._is_dashed:
            dashed_pen = QPen(self.pen)
            dashed_pen.setStyle(Qt.PenStyle.DashLine)
            dashed_pen.setWidthF(2.5)  # 悬停时加粗
            painter.setPen(dashed_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self.path())
        else:
            # Call the base class paint method to actually draw the path
            super().paint(painter, option, widget)
    # --------------------------------------------
    
    # --- ADDED: 悬停事件处理 ---
    def hoverEnterEvent(self, event):
        """鼠标悬停时，变为虚线"""
        self._is_hovered = True
        self._is_dashed = True
        self.update()
        event.accept()

    def hoverLeaveEvent(self, event):
        """鼠标离开时，恢复实线"""
        self._is_hovered = False
        self._is_dashed = False
        self.update()
        event.accept()
    # --- END ADDED ---

    # Rely on default QGraphicsPathItem painting for the line itself 