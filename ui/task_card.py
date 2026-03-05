import sys
import logging
logger = logging.getLogger(__name__)
from typing import Optional, Dict, Any, List, Tuple # For type hints

# 调试开关 - 设置为 False 可以禁用所有调试输出
DEBUG_ENABLED = False

def debug_print(*args, **kwargs):
    """条件调试打印函数"""
    if DEBUG_ENABLED:
        print(*args, **kwargs)
from PySide6.QtWidgets import (QApplication, QMenu,
                               QGraphicsSceneContextMenuEvent, QGraphicsSceneMouseEvent, 
                               QStyleOptionGraphicsItem, QGraphicsDropShadowEffect,
                               QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGraphicsProxyWidget,
                               QSpacerItem, QSizePolicy, QFrame, QPushButton, QCheckBox, QFileDialog, QDialog,
                               QGraphicsSceneHoverEvent, QGraphicsObject, QGraphicsItem)
from PySide6.QtCore import Qt, QRectF, QPointF, QSizeF, Signal, QTimer # <-- ADD Signal & QTimer
from PySide6.QtGui import QBrush, QPen, QColor, QPainter, QFont, QPainterPath, QAction # <-- ADD QAction
from ui.parameter_dialog import ParameterDialog # <<< UNCOMMENTED Import

# Import theme system
try:
    from ui.theme_manager import ThemeManager, ThemeMode
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False
    logger.warning("主题系统不可用，TaskCard将使用默认颜色")

# Removed direct import of TASK_MODULES to break circular dependency
# from tasks import TASK_MODULES 

# Forward declare WorkflowView for type hinting
class WorkflowView: pass 

# --- REMOVED Signals moved outside class --- 
# delete_requested = Signal(int)
# copy_requested = Signal(int, dict) # Emit card_id and parameters
# paste_requested = Signal(QPointF) # Emit scene position for paste
# edit_settings_requested = Signal(int)
# ----------------------------------------

# Define port types - Keep for now, might be needed later
PORT_TYPE_SEQUENTIAL = 'sequential'
PORT_TYPE_SUCCESS = 'success'
PORT_TYPE_FAILURE = 'failure'
PORT_TYPES = [PORT_TYPE_SEQUENTIAL, PORT_TYPE_SUCCESS, PORT_TYPE_FAILURE]

# --- CHANGED Inheritance from QGraphicsRectItem to QGraphicsObject --- 
class TaskCard(QGraphicsObject):
# ------------------------------------------------------------------
    """Represents a task step (SIMPLIFIED)."""
    # --- Signals moved back INSIDE the class --- 
    delete_requested = Signal(int)
    copy_requested = Signal(int, dict) # Emit card_id and parameters
    edit_settings_requested = Signal(int)
    # --- ADDED Signal for jump target change ---
    jump_target_parameter_changed = Signal(str, int, int) # param_name, old_target_id, new_target_id
    # --- ADDED Signal for card click --- 
    card_clicked = Signal(int) # Emit card_id
    # -------------------------------------------
    
    def __init__(self, view: 'WorkflowView', x: float, y: float, task_type: str, card_id: int, task_module: Any, width: int = 180): 
        debug_print(f"--- [DEBUG] TaskCard __init__ START (Inherits QGraphicsObject) - ID: {card_id}, Type: '{task_type}' ---") # Updated log
        # --- MODIFIED: 卡片大小适配网格 (20px 网格) ---
        # 宽度：180px = 9 个网格单位
        # 高度：60px = 3 个网格单位
        self.initial_height = 60  # 3 个网格单位
        
        # --- ADDED: 检测是否是容器卡片 ---
        self.is_container = task_type == "多卡片节点"
        if self.is_container:
            # 容器卡片使用不同的尺寸
            self._width = 400  # 容器更宽
            self._height = 120  # 容器初始高度
        else:
            self._width = width
            self._height = self.initial_height
        # --------------------------------------
        
        # --- ADJUSTED super().__init__() call for QGraphicsObject --- 
        # QGraphicsObject init doesn't take rect args directly like QGraphicsRectItem
        # We might need to set a parent QGraphicsItem if needed, but for now None is okay.
        super().__init__(None) # Call QGraphicsObject's init 
        # -------------------------------------------------------------
        self.setPos(x, y) 
        
        self.view = view
        self.task_type = task_type
        self.card_id = card_id
        self.sequence_id: Optional[int] = None # <<< ADDED: Dynamic sequence ID, initially None
        self.display_id = card_id # Initialize display_id (maybe remove later?)
        self.custom_name: Optional[str] = None # 用户自定义的备注名称
        self.title = f"{task_type} (ID: {self.card_id})" # Use card_id directly
        self.task_module = task_module # Keep reference
        self.parameters: Dict[str, Any] = {} 
        self.param_definitions: Dict[str, Dict[str, Any]] = {} 
        self.connections = [] # Keep connections list
        self.child_cards: Dict[int, 'TaskCard'] = {}  # 存储子卡片 {card_id: TaskCard 对象}
        self.parent_card: Optional['TaskCard'] = None  # 父容器卡片引用
        self.container_margin = 20  # 容器内边距
        self.child_card_spacing = 10  # 子卡片间距
        
        # --- ADDED: Flag for restricted output ports ---
        self.restricted_outputs = self._calculate_restricted_outputs()
        # --------------------------------------------
        
        # Basic Item Flags (QGraphicsObject inherits QGraphicsItem flags)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges) # Needed for connections
        # self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True) # Might not be needed or available
        self.setAcceptHoverEvents(True)
        
        # --- MODIFIED: ComfyUI风格端口设置 --- 
        self.border_radius = 6  # 圆角稍小
        self.port_radius = 3.5  # 缩小端口圆点
        self.port_border_width = 1.0
        self.port_hit_radius = 10.0  # 保持点击区域
        self.text_padding = 8 # Padding around the content area
        self.param_padding = 5 # Internal padding within the content layout
        self.default_pen = QPen(Qt.PenStyle.NoPen)
        self.title_font = QFont("Segoe UI", 9)
        self.title_font.setBold(True) 
        self.param_font = QFont("Segoe UI", 8) 
        self.port_hover_color_boost = 40 # How much brighter/lighter on hover
        # --- END MODIFIED ---

        # 初始化主题颜色（从主题系统获取或默认值）
        self._init_theme_colors()
        
        # 连接主题变化信号
        if THEME_AVAILABLE:
            self._connect_theme_signals()

        # Shadow Effect - 平面化设计，轻微阴影
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(6)
        self.shadow.setColor(QColor(0, 0, 0, 25))
        self.shadow.setOffset(1, 1)
        self.setGraphicsEffect(self.shadow)
        self.shadow.setEnabled(True)
        # 选中状态使用发光边框而非阴影放大
        self.selection_glow_color = QColor(100, 160, 220)  # 柔和蓝光
        self.selection_border_width = 2
        self.default_shadow_blur = self.shadow.blurRadius()
        self.default_shadow_offset = self.shadow.offset().x()
        self.default_shadow_color = self.shadow.color() 

        # Placeholder for execution state needed by paint logic
        self.execution_state = 'idle' 
        # 状态颜色将在 _init_theme_colors 中设置
        # --- ADDED: Store current border pen for flash --- 
        self._current_border_pen = self.default_pen # Start with default
        self._original_border_pen_before_flash = self.default_pen
        # --- MODIFIED: Timer for continuous toggle, not single shot --- 
        self._is_flashing = False # Flag for persistent flashing
        self.flash_toggle_timer = QTimer(self) # Timer for toggling flash border
        self.flash_toggle_timer.timeout.connect(self._toggle_flash_border)
        self.flash_interval_ms = 300 # Interval for toggling flash visual state
        self.flash_border_pen = QPen(QColor(255, 165, 0), 3) # Orange, thick border for flash
        self._flash_border_on = False # Internal state for toggling appearance
        # --------------------------------------------------------

        # --- REMOVED setBrush and setPen (QGraphicsObject doesn't have them directly) --- 
        # We draw everything in paint()
        # self.setBrush(QBrush(self.card_color))
        # self.setPen(self.default_pen)
        # -----------------------------------------------------------------------------

        # Hover state for ports
        self.hovered_port_side: Optional[str] = None
        self.hovered_port_type: Optional[str] = None
        
        # --- Load parameters --- 
        self.load_and_create_parameters() 
        # ------------------------
        
        # --- ADDED: Enable ToolTips for hover events ---
        self.setAcceptHoverEvents(True) # Ensure hover events are enabled
        self.setToolTip("") # Initialize tooltip, hoverEnterEvent will populate it
        # --- END ADDED ---

        # --- ADDED: Tooltip caching for performance optimization ---
        self._cached_tooltip = ""
        self._tooltip_needs_update = True
        self._hover_timer = None  # 用于延迟显示工具提示
        # --- END ADDED ---

        debug_print(f"--- [DEBUG] TaskCard __init__ END (Inherits QGraphicsObject) - ID: {card_id} ---") # Updated log

    # --- ADDED boundingRect method (Required by QGraphicsObject) --- 
    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the item."""
        # Use stored width/height
        return QRectF(0, 0, self._width, self._height) 
    # -------------------------------------------------------------

    def _init_theme_colors(self):
        """初始化主题颜色，从主题系统获取或设置默认值"""
        if THEME_AVAILABLE:
            try:
                theme_manager = QApplication.instance().theme_manager
                colors = theme_manager.get_palette()
                is_dark = theme_manager.is_dark_mode()
                logger.debug(f"TaskCard 初始化主题：is_dark={is_dark}, current_theme={theme_manager.get_current_theme()}")
            except Exception as e:
                logger.warning(f"获取主题颜色失败，使用默认值：{e}")
                colors = None
                is_dark = False
        else:
            colors = None
            is_dark = False
        
        if colors:
            # 从主题系统获取颜色
            self.card_color = QColor(colors["card_background"])
            self.title_area_color = QColor(colors["surface"])
            self.title_color = QColor(colors["text_primary"])
            self.port_idle_color = QColor(colors["border"])
            self.selection_shadow_color = QColor(colors["primary"])
            
            # 端口颜色
            self.port_colors = {
                PORT_TYPE_SEQUENTIAL: QColor(colors["port_sequential"]),
                PORT_TYPE_SUCCESS: QColor(colors["port_success"]),
                PORT_TYPE_FAILURE: QColor(colors["port_failure"])
            }
            
            # 状态颜色 - 根据明暗模式调整
            if is_dark:
                self.state_colors = {
                    'idle': self.card_color,
                    'executing': QColor(30, 60, 90),  # 深蓝
                    'success': QColor(30, 70, 30),    # 深绿
                    'failure': QColor(80, 30, 30)     # 深红
                }
            else:
                self.state_colors = {
                    'idle': self.card_color,
                    'executing': QColor(200, 220, 255), # 浅蓝
                    'success': QColor(200, 255, 200),   # 浅绿
                    'failure': QColor(255, 200, 200)    # 浅红
                }
            
            # 状态边框 - 使用更淡的颜色
            primary_color = QColor(colors.get('highlight', QColor(0, 120, 212)))
            success_color = QColor(76, 175, 80)  # Material Green 500
            error_color = QColor(244, 67, 54)    # Material Red 500
            
            self.state_border_pens = {
                'idle': self.default_pen,
                'executing': QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 140), 2),  # Alpha 140/255
                'success': QPen(QColor(success_color.red(), success_color.green(), success_color.blue(), 140), 2),   # Alpha 140/255
                'failure': QPen(QColor(error_color.red(), error_color.green(), error_color.blue(), 140), 2)          # Alpha 140/255
            }
        else:
            # 使用默认颜色
            self.card_color = QColor(255, 255, 255)
            self.title_area_color = QColor(240, 240, 240)
            self.title_color = QColor(20, 20, 20)
            self.port_idle_color = QColor(180, 180, 180)
            self.selection_shadow_color = QColor(0, 120, 215, 100)
            
            self.port_colors = {
                PORT_TYPE_SEQUENTIAL: QColor(0, 120, 215),
                PORT_TYPE_SUCCESS: QColor(16, 124, 16),
                PORT_TYPE_FAILURE: QColor(196, 43, 43)
            }
            
            self.state_colors = {
                'idle': self.card_color,
                'executing': QColor(200, 220, 255),
                'success': QColor(200, 255, 200),
                'failure': QColor(255, 200, 200)
            }
            
            self.state_border_pens = {
                'idle': self.default_pen,
                'executing': QPen(QColor(33, 150, 243, 140), 2),   # Material Blue 500 with Alpha 140
                'success': QPen(QColor(76, 175, 80, 140), 2),      # Material Green 500 with Alpha 140
                'failure': QPen(QColor(244, 67, 54, 140), 2)       # Material Red 500 with Alpha 140
            }
    
    def _connect_theme_signals(self):
        """连接主题变化信号"""
        try:
            theme_manager = QApplication.instance().theme_manager
            theme_manager.theme_changed.connect(self._on_theme_changed)
        except Exception as e:
            logger.warning(f"连接主题信号失败: {e}")
    
    def _on_theme_changed(self, mode: ThemeMode):
        """
        主题变化回调 - 更新颜色并重绘
        
        Args:
            mode: 新主题模式
        """
        # 重新初始化颜色
        self._init_theme_colors()
        # 触发重绘
        self.update()

        # 兼容处理：mode 可能是 ThemeMode 枚举或字符串
        mode_str = mode.value if hasattr(mode, 'value') else str(mode)
        logger.debug(f"TaskCard {self.card_id} 主题更新为: {mode_str}")

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        """Custom painting for rounded corners, title, ports, and state highlight."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) 
        
        # --- CHANGED: Use boundingRect() instead of self.rect() --- 
        rect = self.boundingRect()
        # --------------------------------------------------------
        path = QPainterPath()
        path.addRoundedRect(rect, self.border_radius, self.border_radius) 
        
        # Draw Background
        painter.setPen(Qt.PenStyle.NoPen)
        
        # 如果是子卡片，使用半透明背景
        if self.parent_card:
            # 子卡片背景稍暗一些，透明度降低
            base_color = self.state_colors.get(self.execution_state, self.card_color)
            bg_color = QColor(base_color)
            bg_color.setAlpha(200)  # 降低透明度
            painter.fillPath(path, QBrush(bg_color))
        else:
            bg_color = self.state_colors.get(self.execution_state, self.card_color) 
            painter.fillPath(path, QBrush(bg_color))
        
        # --- MODIFIED: 绘制选中状态发光边框 ---
        effective_border_pen = self.default_pen
        if self._is_flashing:
            effective_border_pen = self._current_border_pen
        else:
            effective_border_pen = self.state_border_pens.get(self.execution_state, self.default_pen)

        # 绘制选中状态发光边框
        if self.isSelected():
            # 外发光层 - 柔和渐变
            for i in range(3, 0, -1):
                glow_alpha = 40 - i * 10
                glow_pen = QPen(QColor(self.selection_glow_color.red(),
                                       self.selection_glow_color.green(),
                                       self.selection_glow_color.blue(),
                                       glow_alpha), self.selection_border_width + i * 2)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)

            # 主边框 - 清晰锐利
            main_border_pen = QPen(self.selection_glow_color, self.selection_border_width)
            painter.setPen(main_border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        elif effective_border_pen != QPen(Qt.PenStyle.NoPen):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(effective_border_pen)
            painter.drawPath(path)
        # --- END MODIFIED ---
            
        # 如果是容器卡片，绘制容器标识（内边框）- 使用更淡的颜色
        if self.is_container:
            container_pen = QPen(QColor(100, 160, 220, 120), 2)  # 蓝色边框，Alpha 120/255
            container_pen.setStyle(Qt.PenStyle.DashLine)  # 虚线
            inner_rect = rect.adjusted(10, 10, -10, -10)
            inner_path = QPainterPath()
            inner_path.addRoundedRect(inner_rect, self.border_radius - 2, self.border_radius - 2)
            painter.setPen(container_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(inner_path)
        
        # --- Restore default pen for text --- 
        painter.setPen(QPen(self.title_color))
        # ------------------------------------

        # Draw Title Text 
        painter.setFont(self.title_font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.title)
        
        # --- MODIFIED: ComfyUI风格端口绘制（实心圆点）---
        for side in ['left', 'right']:
            for port_type in PORT_TYPES:
                # 跳过受限的输出端口
                if side == 'right' and self.restricted_outputs and port_type != PORT_TYPE_SEQUENTIAL:
                    continue
                
                base_color = self.port_colors.get(port_type, Qt.GlobalColor.gray)
                is_hovered = (self.hovered_port_side == ('input' if side == 'left' else 'output') and 
                              self.hovered_port_type == port_type)
                
                # ComfyUI风格：实心圆点，悬停时放大并发光
                if is_hovered:
                    hover_color = base_color.lighter(120)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(hover_color))
                    radius = self.port_radius + 2
                    
                    # 悬停发光效果
                    glow_color = QColor(hover_color.red(), hover_color.green(), hover_color.blue(), 80)
                    painter.setBrush(QBrush(glow_color))
                    port_center = self.get_port_pos(side, port_type)
                    painter.drawEllipse(port_center, radius + 3, radius + 3)
                    painter.setBrush(QBrush(hover_color))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(base_color))
                    radius = self.port_radius
                
                port_center = self.get_port_pos(side, port_type)
                painter.drawEllipse(port_center, radius, radius)
                # 去掉高光，简洁风格
        # --- END MODIFIED ---
    # ------------------------------

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        """Handle clicks for port dragging and card selection/movement."""
        debug_print(f"--- [DEBUG] TaskCard {self.card_id} ({self.task_type}): mousePressEvent START - Button: {event.button()} ---") # DEBUG

        # Port Dragging Logic
        if event.button() == Qt.MouseButton.LeftButton:
            port_info = self.get_port_at(event.pos()) # Requires get_port_at
            if port_info and port_info['side'] == 'output':
                # --- REMOVED: Check preventing dragging from success/failure ports ---
                # if port_info['type'] == PORT_TYPE_SUCCESS or port_info['type'] == PORT_TYPE_FAILURE:
                #    debug_print(f"  [DRAG_DEBUG] Clicked on non-draggable output port: {port_info['type']} for card {self.card_id}. Ignoring.")
                #    event.ignore() # Explicitly ignore the event for this port
                #    return # Do not start drag
                # --- END REMOVED ---

                debug_print(f"  [DRAG_DEBUG] Detected click on output port: {port_info['type']} for card {self.card_id}")
                debug_print(f"开始拖动: 从 {self.title} 的 {port_info['type']} 输出端口")
                self.view.start_drag_line(self, port_info['type']) # Requires view reference and start_drag_line
                event.accept()
                return # Port dragging handled

        # Context Menu Trigger (Right Click)
        # 🔧 修复：不要ignore右键事件，让Qt自动处理并调用contextMenuEvent
        if event.button() == Qt.MouseButton.RightButton:
            debug_print("  [DEBUG] TaskCard: Right mouse button pressed, accepting event for context menu.")
            event.accept()  # 接受事件，让contextMenuEvent被调用
            return

        # --- Emit card_clicked signal on Left Click Press ---
        if event.button() == Qt.MouseButton.LeftButton:
             port_info = self.get_port_at(event.pos())
             # Only emit click if not starting a line drag
             if not (port_info and port_info['side'] == 'output'):
                 debug_print(f"  [CLICK_DEBUG] Emitting card_clicked for ID: {self.card_id}")
                 self.card_clicked.emit(self.card_id)
        # --- END Click Signal ---

        # Standard Card Selection/Dragging
        debug_print("Handling standard card selection/dragging.")
        scene = self.scene()
        if scene:
            selected_items = scene.selectedItems()
            is_already_only_selected = self.isSelected() and len(selected_items) == 1
            if not is_already_only_selected:
                modifiers = QApplication.keyboardModifiers()
                if not (modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                    scene.clearSelection()
                self.setSelected(True)

        super().mousePressEvent(event) 

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        """Handle double-click to open parameter settings dialog."""
        debug_print(f"--- [DEBUG] TaskCard {self.card_id}: mouseDoubleClickEvent triggered ---")
        
        # 双击左键打开参数设置
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在端口上，如果是则不打开参数对话框
            port_info = self.get_port_at(event.pos())
            if not port_info:
                debug_print(f"  [DBLCLICK_DEBUG] Opening parameter dialog for card {self.card_id}")
                self.open_parameter_dialog()
                event.accept()
                return
        
        # 其他情况调用父类方法
        super().mouseDoubleClickEvent(event)

    def get_port_pos(self, side: str, port_type: str = PORT_TYPE_SEQUENTIAL) -> QPointF:
        rect = self.boundingRect()
        center_y = rect.center().y()
        
        # --- MODIFIED: Calculate offset based on specific port type --- 
        spacing = 15 # Vertical distance between ports
        y_offset = 0 # Default to center (for sequential)
        if port_type == PORT_TYPE_SUCCESS:
            y_offset = -spacing # Success port above center
        elif port_type == PORT_TYPE_FAILURE:
            y_offset = spacing # Failure port below center
        # ----------------------------------------------------------
        
        # --- MODIFIED: Move ports inside the card ---
        port_offset_x = 6  # 端口距离边缘的内边距
        if side == 'left':
            x = rect.left() + port_offset_x
        else:  # right
            x = rect.right() - port_offset_x
        # -------------------------------------------
        
        final_y = center_y + y_offset
        return QPointF(x, final_y)

    def shape(self) -> QPainterPath:
        """Define the precise shape for collision detection and painting."""
        path = QPainterPath()
        # Use the bounding rectangle which already includes potential padding
        path.addRoundedRect(self.boundingRect(), self.border_radius, self.border_radius)
        return path

    def itemChange(self, change, value):
        """Override to update connections when the card moves."""
        # debug_print(f"--- [ITEM_CHANGE_ENTRY] Card ID: {self.card_id}, Change: {change}, Value: {value} ---") # <-- Add this line # <<< MODIFIED: Commented out
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update connections attached to this card
            pass # <<< ADDED: Placeholder to fix indentation error

        # Keep basic connection update logic
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # --- ADDED: Grid snapping ---
            original_pos = value # QPointF representing the proposed new top-left position
            new_pos = original_pos
            
            # Apply grid snapping if enabled
            if self.view and hasattr(self.view, '_grid_snap_enabled') and self.view._grid_snap_enabled:
                grid_size = self.view._grid_snap_size if hasattr(self.view, '_grid_snap_size') else 20
                snapped_x = round(original_pos.x() / grid_size) * grid_size
                snapped_y = round(original_pos.y() / grid_size) * grid_size
                new_pos = QPointF(snapped_x, snapped_y)
                # debug_print(f"  [GRID_SNAP] Card {self.card_id}: ({original_pos.x():.1f}, {original_pos.y():.1f}) -> ({snapped_x:.1f}, {snapped_y:.1f})")
            # --- END GRID SNAPPING ---
            
            # Calculate the card's bounding rect at the new position
            card_rect_at_new_pos = self.boundingRect().translated(new_pos)

            current_scene_rect = self.scene().sceneRect()
            # --- ADDED: More detailed logging BEFORE the check ---
            debug_print(f"--- [ITEM_CHANGE_DEBUG] Card ID: {self.card_id} ---")
            debug_print(f"    Original Pos (value): {original_pos}")
            debug_print(f"    Snapped Pos: {new_pos}")
            debug_print(f"    Card Rect @ New Pos: L={card_rect_at_new_pos.left():.2f}, T={card_rect_at_new_pos.top():.2f}, R={card_rect_at_new_pos.right():.2f}, B={card_rect_at_new_pos.bottom():.2f}")
            debug_print(f"    Current Scene Rect:  L={current_scene_rect.left():.2f}, T={current_scene_rect.top():.2f}, R={current_scene_rect.right():.2f}, B={current_scene_rect.bottom():.2f}")
            # --- END ADDED ---
            # Define a margin/padding around the edges
            margin = 50.0 # Expand scene if item comes within 50 pixels of the edge

            new_scene_rect = QRectF(current_scene_rect) # Start with current rect
            expanded = False

            # Check and expand left boundary
            if card_rect_at_new_pos.left() < current_scene_rect.left() + margin:
                new_scene_rect.setLeft(card_rect_at_new_pos.left() - margin)
                expanded = True

            # Check and expand top boundary
            if card_rect_at_new_pos.top() < current_scene_rect.top() + margin:
                new_scene_rect.setTop(card_rect_at_new_pos.top() - margin)
                expanded = True

            # Check and expand right boundary
            if card_rect_at_new_pos.right() > current_scene_rect.right() - margin:
                new_scene_rect.setRight(card_rect_at_new_pos.right() + margin)
                expanded = True

            # Check and expand bottom boundary
            if card_rect_at_new_pos.bottom() > current_scene_rect.bottom() - margin:
                new_scene_rect.setBottom(card_rect_at_new_pos.bottom() + margin)
                expanded = True

            if expanded:
                # --- ADDED Debug Logging ---
                debug_print(f"--- [SCENE EXPAND] Card ID: {self.card_id} triggered expansion. ---")
                debug_print(f"    Card BRect @ new_pos: {card_rect_at_new_pos}")
                debug_print(f"    Current Scene Rect: {current_scene_rect}")
                debug_print(f"    Calculated New Scene Rect: {new_scene_rect}")
                # --- END Debug Logging ---
                # debug_print(f"Expanding sceneRect to: {new_scene_rect}") # Optional Debug
                self.scene().setSceneRect(new_scene_rect)
                # --- ADDED Log after set ---
                debug_print(f"    Scene Rect AFTER setSceneRect: {self.scene().sceneRect()}")
                # --- END Log after set ---
            # --- END ADDED ---

            # Update connections after position change is approved
            # Ensure connections are updated AFTER the superclass call handles the position change
            # We'll rely on the signal emitted by the superclass change or handle it slightly differently
            pass # Let superclass handle position update first

        # Handle selection change for shadow effect
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            selected = value # value is True if selected, False otherwise
            self.update_selection_effect(selected)
            # Allow the default behavior to proceed
            
        # --- MODIFIED: Call super with snapped position ---
        # Use new_pos if we calculated it, otherwise use original value
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            if self.view and hasattr(self.view, '_grid_snap_enabled') and self.view._grid_snap_enabled:
                grid_size = self.view._grid_snap_size if hasattr(self.view, '_grid_snap_size') else 20
                snapped_x = round(value.x() / grid_size) * grid_size
                snapped_y = round(value.y() / grid_size) * grid_size
                result = super().itemChange(change, QPointF(snapped_x, snapped_y))
            else:
                result = super().itemChange(change, value)
        else:
            result = super().itemChange(change, value)
        # --------------------------------------------------------------

        # --- MOVED Connection Update AFTER super().itemChange ---
        # Now that the item's position *has* changed, update connections
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
             # debug_print(f"Card {self.card_id} moved, updating {len(self.connections)} connections.") # Optional Debug
             for conn in self.connections:
                 conn.update_path() # Update path based on new card position
        # --- END MOVED ---

        return result # Return the result from the superclass call

    def _calculate_restricted_outputs(self) -> bool:
        """计算是否应该限制输出端口（动态计算）"""
        # 基础限制类型（这些任务类型永远只有sequential端口）
        base_restricted_types = ['延迟', '鼠标滚轮操作', '模拟键盘操作', '起点']
        if self.task_type in base_restricted_types:
            return True

        # 条件控制卡片永远不限制端口（它的核心功能就是分支）
        if self.task_type == '条件控制':
            return False

        # 动态限制类型（根据参数决定是否显示成功/失败端口）
        dynamic_types = ['查找图片并点击', 'OCR区域识别', '模拟键盘操作', '查找颜色']
        if self.task_type not in dynamic_types:
            return False

        # 检查参数以确定是否应该显示成功/失败端口
        # 如果任何失败处理参数不是"执行下一步"，则需要显示对应端口
        on_failure = self.parameters.get('on_failure', '执行下一步')
        on_success = self.parameters.get('on_success', '执行下一步')

        # 对于某些任务，检查特定的参数名称
        if self.task_type == '查找图片并点击':
            on_image_found = self.parameters.get('on_image_found', '继续执行本步骤')
            on_image_not_found = self.parameters.get('on_image_not_found', '执行下一步')
            # 如果有任何非默认的处理方式，就不限制端口
            if (on_image_found != '继续执行本步骤' or
                on_image_not_found != '执行下一步'):
                return False
        elif self.task_type == '查找颜色':
            on_image_found = self.parameters.get('on_image_found', '继续执行本步骤')
            on_image_not_found = self.parameters.get('on_image_not_found', '执行下一步')
            if (on_image_found != '继续执行本步骤' or
                on_image_not_found != '执行下一步'):
                return False

        # 通用检查：如果有成功/失败处理且不是默认的"执行下一步"，则不限制
        if (on_failure != '执行下一步' or on_success != '执行下一步'):
            return False

        # 默认情况下，如果所有处理都是"执行下一步"，则限制端口（只显示sequential）
        return True

    def update_port_restrictions(self):
        """更新端口限制状态并刷新显示"""
        old_restricted = self.restricted_outputs
        new_restricted = self._calculate_restricted_outputs()

        if old_restricted != new_restricted:
            debug_print(f"[PORT_UPDATE] Card {self.card_id} port restrictions changed: {old_restricted} -> {new_restricted}")
            self.restricted_outputs = new_restricted

            # 如果端口限制发生变化，需要清理不再有效的连接
            if new_restricted and not old_restricted:
                # 从不限制变为限制：需要移除成功/失败连接
                self._cleanup_invalid_connections(['success', 'failure'])
            elif not new_restricted and old_restricted:
                # 从限制变为不限制：不需要清理，但需要刷新显示
                pass

            # 刷新卡片显示
            self.update()

            # 更新所有连接的路径（因为端口位置可能改变）
            for conn in self.connections:
                if hasattr(conn, 'update_path'):
                    conn.update_path()

    def _cleanup_invalid_connections(self, invalid_port_types: list):
        """清理无效的连接"""
        connections_to_remove = []

        for conn in self.connections[:]:  # 使用切片创建副本以避免修改时的问题
            if hasattr(conn, 'line_type') and conn.line_type in invalid_port_types:
                # 检查这个连接是否从当前卡片的输出端口开始
                if hasattr(conn, 'start_item') and conn.start_item == self:
                    connections_to_remove.append(conn)
                    debug_print(f"[PORT_CLEANUP] Marking connection for removal: {self.card_id} -> {conn.end_item.card_id if hasattr(conn, 'end_item') and conn.end_item else 'None'} ({conn.line_type})")

        # 通知视图移除这些连接
        if connections_to_remove and self.view:
            for conn in connections_to_remove:
                if hasattr(self.view, 'remove_connection'):
                    self.view.remove_connection(conn)

    def update_selection_effect(self, selected: bool):
        """Updates the visual effect based on selection state - 使用发光边框替代阴影"""
        # 选中状态使用发光边框（在paint中绘制），阴影保持平面化
        if selected:
            # 选中时轻微提升阴影
            self.shadow.setBlurRadius(8)
            self.shadow.setOffset(2, 2)
        else:
            # 未选中时恢复平面阴影
            self.shadow.setBlurRadius(self.default_shadow_blur)
            self.shadow.setOffset(self.default_shadow_offset, self.default_shadow_offset)
        self.shadow.setEnabled(True)

    def set_display_id(self, sequence_id: Optional[int]): # Keep this uncommented
        """Sets the display ID shown on the card title."""
        self.sequence_id = sequence_id # Store the logical sequence ID
        if sequence_id is not None:
            self.display_id = sequence_id # Use sequence ID for display if available
        else:
            self.display_id = self.card_id # Fallback to original card ID
        
        # Update the title text immediately
        # --- MODIFIED: Change title format to support custom names ---
        if hasattr(self, 'task_type') and self.task_type:
            if self.custom_name:
                self.title = f"{self.custom_name} (ID: {self.card_id})"
            else:
                self.title = f"{self.task_type} (ID: {self.card_id})" # Use card_id directly
        else:
            # Fallback title if task_type isn't set yet (shouldn't happen in normal flow)
            self.title = f"Task (ID: {self.card_id})"
        # --- END MODIFICATION ---

        self.update() # Request a repaint to show the new title

    def set_custom_name(self, custom_name: Optional[str]):
        """设置卡片的自定义备注名称"""
        self.custom_name = custom_name
        # 更新标题显示
        if custom_name:
            self.title = f"{custom_name} (ID: {self.card_id})"
        else:
            self.title = f"{self.task_type} (ID: {self.card_id})"
        self.update() # 重新绘制卡片

    def get_port_at(self, pos: QPointF) -> Optional[Dict[str, Any]]:
        """Checks if a point (in item coordinates) hits a port using an enlarged hit radius."""
        hit_radius_sq = self.port_hit_radius ** 2
        for port_type in PORT_TYPES:
            in_center = self.get_port_pos('left', port_type)
            delta_in = pos - in_center
            if delta_in.x()**2 + delta_in.y()**2 <= hit_radius_sq:
                return {'side': 'input', 'type': port_type}
            out_center = self.get_port_pos('right', port_type)
            delta_out = pos - out_center
            if delta_out.x()**2 + delta_out.y()**2 <= hit_radius_sq:
                # --- ADDED: Check for restricted output ports --- 
                if self.restricted_outputs and port_type != PORT_TYPE_SEQUENTIAL:
                    pass # Ignore click on restricted success/failure output ports
                else:
                    return {'side': 'output', 'type': port_type}
                # -----------------------------------------------
        return None

    def set_execution_state(self, state: str):
        """Sets the execution state and triggers a repaint."""
        if state in self.state_colors:
            self.execution_state = state
            self.update() 
        else:
            debug_print(f"警告: 尝试为卡片 {self.card_id} 设置无效状态 '{state}'")

    def open_parameter_dialog(self):
        """Opens the parameter editing dialog - MODIFIED to use parameter panel."""
        print(f"搜索 TaskCard.open_parameter_dialog() 被调用！Card ID: {self.card_id}")

        # 检查是否正在运行，如果是则阻止打开参数设置
        if self._is_workflow_running():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "操作被禁止",
                "工作流正在执行中，暂时无法进行参数设置操作。\n\n请等待任务执行完成或停止任务后再试。"
            )
            return

        # 🔧 修复：发送信号给main_window的参数面板处理
        print(f"搜索 发送参数编辑请求信号: {self.card_id}")
        self.edit_settings_requested.emit(self.card_id)

    def set_parent_card(self, parent: Optional['TaskCard']):
        """设置父容器卡片"""
        old_parent = self.parent_card
        
        # 从旧容器中移除
        if old_parent and self.card_id in old_parent.child_cards:
            del old_parent.child_cards[self.card_id]
            old_parent.update_container_size()
        
        # 设置新父容器
        self.parent_card = parent
        
        # 添加到新容器的子卡片列表
        if parent:
            parent.child_cards[self.card_id] = self
            parent.update_container_size()
            
            # 设置子卡片的父级标志
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
            
            # 将子卡片移动到容器内部
            self._reposition_in_container()
    
    def _reposition_in_container(self):
        """在容器内重新定位子卡片"""
        if not self.parent_card:
            return
        
        # 计算在容器内的位置
        index = list(self.parent_card.child_cards.keys()).index(self.card_id)
        container_rect = self.parent_card.boundingRect()
        
        # 计算 Y 位置（从上到下排列）
        y_pos = self.parent_card.container_margin + index * (self.initial_height + self.parent_card.child_card_spacing)
        x_pos = self.parent_card.container_margin
        
        # 平滑移动动画（可选）
        self.setPos(x_pos, y_pos)
    
    def update_container_size(self):
        """根据子卡片数量更新容器大小"""
        if not self.is_container:
            return
        
        child_count = len(self.child_cards)
        if child_count == 0:
            # 没有子卡片，使用最小高度
            new_height = 120  # 容器最小高度
        else:
            # 计算需要的高度
            total_height = (
                self.container_margin * 2 +  # 上下边距
                child_count * self.initial_height +  # 所有子卡片高度
                (child_count - 1) * self.child_card_spacing  # 子卡片间距
            )
            new_height = max(120, total_height)  # 至少 120px
        
        # 更新高度
        if new_height != self._height:
            self._height = new_height
            self.update()  # 重绘
            
            # 通知 view 更新连接
            if hasattr(self, 'view') and self.view:
                for conn in self.connections:
                    conn.update_line()
    
    def add_connection(self, connection): # Keep connection logic
        if connection not in self.connections:
            self.connections.append(connection)

    def remove_connection(self, connection): # Keep connection logic
        try:
            self.connections.remove(connection)
        except ValueError:
            debug_print(f"警告: 尝试移除卡片 '{self.title}' 上不存在的连接。")

    def get_input_port_scene_pos(self, port_type: str = PORT_TYPE_SEQUENTIAL) -> QPointF:
        """Gets the scene coordinates of the specified input port type (left side)."""
        return self.mapToScene(self.get_port_pos('left', port_type))
    def get_output_port_scene_pos(self, port_type: str = PORT_TYPE_SEQUENTIAL) -> QPointF:
        """Gets the scene coordinates of the specified output port type (right side)."""
        return self.mapToScene(self.get_port_pos('right', port_type))

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent): 
        """Handle mouse hovering over the card to highlight ports."""
        pos = event.pos()
        hovered_port_info = self.get_port_at(pos)
        new_hovered_side = None
        new_hovered_type = None
        if hovered_port_info:
            new_hovered_side = hovered_port_info.get('side')
            new_hovered_type = hovered_port_info.get('type')
        if new_hovered_side != self.hovered_port_side or new_hovered_type != self.hovered_port_type:
            self.hovered_port_side = new_hovered_side
            self.hovered_port_type = new_hovered_type
            self.update() 
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        """Handle mouse leaving the card area."""
        if self.hovered_port_side is not None or self.hovered_port_type is not None:
            self.hovered_port_side = None
            self.hovered_port_type = None
            self.update()

        # --- ADDED: Call super for other potential hover leave handling ---
        super().hoverLeaveEvent(event)

        # --- ADDED: Clear tooltip when mouse leaves the card ---
        self.setToolTip("")

        # 立即隐藏QToolTip
        from PySide6.QtWidgets import QToolTip
        QToolTip.hideText()
        # --- END ADDED ---

    def load_and_create_parameters(self):
        """Loads parameter definitions and initializes the parameters dictionary."""
        debug_print(f"--- [DEBUG] TaskCard {self.card_id}: load_and_create_parameters START ---") # DEBUG
        
        if not self.task_module or not hasattr(self.task_module, 'get_params_definition'):
            debug_print(f"    [DEBUG] TaskCard {self.card_id}: Task module missing or no get_params_definition.") # DEBUG
            debug_print(f"    警告: 任务类型 '{self.task_type}' 的模块无效或缺少 get_params_definition。 Module: {self.task_module}")
            self.param_definitions = {} 
            debug_print(f"--- [DEBUG] TaskCard {self.card_id}: load_and_create_parameters END (Module Invalid/Missing Def) ---") # DEBUG
            return

        try:
            debug_print(f"    [DEBUG] TaskCard {self.card_id}: Calling {self.task_type}.get_params_definition()...") # DEBUG
            self.param_definitions = self.task_module.get_params_definition()
            debug_print(f"    [DEBUG] TaskCard {self.card_id}: Received param_definitions type: {type(self.param_definitions)}") # DEBUG
        except Exception as e:
             debug_print(f"    [DEBUG] TaskCard {self.card_id}: ERROR calling get_params_definition: {e}") # DEBUG
             self.param_definitions = {}
             debug_print(f"--- [DEBUG] TaskCard {self.card_id}: load_and_create_parameters END (Exception in get_params_definition) ---") # DEBUG
             return
             
        if isinstance(self.param_definitions, list):
            debug_print(f"    [DEBUG] TaskCard {self.card_id}: Converting list of param definitions to dict...") # DEBUG
            try:
                definitions_dict = {item['name']: item for item in self.param_definitions if isinstance(item, dict) and 'name' in item}
                self.param_definitions = definitions_dict
                debug_print(f"    [DEBUG] TaskCard {self.card_id}: Conversion successful. New type: {type(self.param_definitions)}") # DEBUG
            except (TypeError, KeyError) as e:
                debug_print(f"    [DEBUG] TaskCard {self.card_id}: ERROR converting list to dict: {e}. Invalid list format.") # DEBUG
                self.param_definitions = {} 
        elif not isinstance(self.param_definitions, dict):
             debug_print(f"    [DEBUG] TaskCard {self.card_id}: ERROR - get_params_definition returned unexpected type: {type(self.param_definitions)}") # DEBUG
             self.param_definitions = {} 

        debug_print(f"  [DEBUG] TaskCard {self.card_id}: Initializing parameters with defaults...") # DEBUG
        # 工具 修复：只为缺失的参数设置默认值，不覆盖已有参数
        for name, param_def in self.param_definitions.items():
            if param_def.get('type') == 'separator':
                continue
            # 只有当参数不存在时才设置默认值，避免覆盖用户设置的参数
            if name not in self.parameters:
                default_value = param_def.get('default')
                self.parameters[name] = default_value
                debug_print(f"    [DEBUG] 设置默认参数 {name} = {default_value}")
            else:
                debug_print(f"    [DEBUG] 保留现有参数 {name} = {self.parameters[name]}")
        
        debug_print(f"卡片 {self.card_id} ('{self.task_type}') 参数定义已加载，初始参数: {self.parameters}")
        debug_print(f"--- [DEBUG] TaskCard {self.card_id}: load_and_create_parameters END (Success) ---") # DEBUG

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        """Creates and shows the right-click context menu."""
        # 检查工作流是否正在运行
        is_running = self._is_workflow_running()
        
        menu = QMenu()
        # --- 使用主题系统设置菜单样式 ---
        try:
            from ui.theme_manager import ThemeManager
            theme_mode = QApplication.instance().theme_manager.get_current_theme()
            QApplication.instance().theme_manager.get_colors()
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {colors["surface"]};
                    border: 1px solid {colors["border"]};
                    border-radius: 8px;
                    padding: 8px;
                    color: {colors["text_primary"]};
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
            """)
        except Exception as e:
            print(f"[WARN] Failed to apply theme to context menu: {e}")
        
        copy_action = QAction("复制卡片", menu)
        copy_action.triggered.connect(self.copy_card) # Connects to method
        copy_action.setEnabled(not is_running)
        if is_running:
            copy_action.setToolTip("工作流运行期间无法复制卡片")
        menu.addAction(copy_action)

        menu.addSeparator()
        
        settings_action = QAction("参数设置", menu)
        settings_action.triggered.connect(self.open_parameter_dialog) # Connects to method
        settings_action.setEnabled(not is_running)
        if is_running:
            settings_action.setToolTip("工作流运行期间无法修改参数")
        menu.addAction(settings_action)

        menu.addSeparator()

        delete_action = QAction("删除卡片", menu)
        delete_action.triggered.connect(
            lambda: (debug_print(f"--- [CONTEXT_MENU_DEBUG] Delete Action triggered for Card {self.card_id}. Emitting delete_requested... ---"), self.delete_requested.emit(self.card_id))
        )
        delete_action.setEnabled(not is_running)
        if is_running:
            delete_action.setToolTip("工作流运行期间无法删除卡片")
        menu.addAction(delete_action)

        debug_print(f"  [CONTEXT_DEBUG] Context menu created for card {self.card_id} at scene pos {event.scenePos()}")
        # Show the menu at the event position
        # --- CHANGED: Execute using mapToGlobal for correct screen positioning --- 
        selected_action = menu.exec(event.screenPos())
        # -----------------------------------------------------------------------
        
        # Handle selected action (optional, can be handled by WorkflowView via signals)
        if selected_action:
            debug_print(f"  [CONTEXT_DEBUG] Selected action: {selected_action.text()}")
            # Example: emit signal based on action
            if selected_action.text() == "编辑设置":
                self.edit_settings_requested.emit(self.card_id)
            elif selected_action.text() == "删除卡片":
                self.delete_requested.emit(self.card_id)
            elif selected_action.text() == "复制卡片":
                self.copy_card() # Call the method WorkflowView expects
                
        debug_print("--- [DEBUG] TaskCard contextMenuEvent END ---")
        
    # --- ADDED: Method to emit copy request --- 
    def copy_card(self):
        """Emits the signal that this card should be copied."""
        # 检查是否正在运行，如果是则阻止复制
        if self._is_workflow_running():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, 
                "操作被禁止", 
                "工作流正在执行中，暂时无法进行复制卡片操作。\n\n请等待任务执行完成或停止任务后再试。"
            )
            return
            
        debug_print(f"--- [DEBUG] TaskCard {self.card_id}: copy_card() method called, emitting copy_requested signal. ---")
        self.copy_requested.emit(self.card_id, self.parameters.copy())
        
    def _is_workflow_running(self) -> bool:
        """检查工作流是否正在运行"""
        try:
            # 通过view获取主窗口
            if self.view and hasattr(self.view, '_is_workflow_running'):
                return self.view._is_workflow_running()
            
            # 备用方法：直接从QApplication查找
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    if (hasattr(widget, 'executor') and hasattr(widget, 'executor_thread') and
                        widget.executor is not None and widget.executor_thread is not None and
                        widget.executor_thread.isRunning()):
                        return True
        except Exception as e:
            import logging
            logging.error(f"TaskCard检查任务运行状态时发生错误: {e}")
            
        return False

    # --- ADDED: Helper method to format tooltip values ---
    def _format_tooltip_value(self, value: Any) -> str:
        if value is None:
            return "None"
        if isinstance(value, bool):
            return "是" if value else "否"

        # 转换为字符串
        str_value = str(value)

        # 特殊处理多行文本（如路径点坐标）
        if isinstance(value, str) and '\n' in str_value:
            lines = str_value.strip().split('\n')

            # 如果是路径点坐标格式（每行都是 x,y 格式）
            if len(lines) > 3 and all(',' in line.strip() for line in lines[:3] if line.strip()):
                # 显示前3个点和总数
                preview_lines = lines[:3]
                total_count = len([line for line in lines if line.strip()])
                preview_text = '\n    '.join(preview_lines)
                return f"{preview_text}\n    ... (共{total_count}个坐标点)"

            # 其他多行文本，限制显示行数
            elif len(lines) > 5:
                preview_lines = lines[:5]
                preview_text = '\n    '.join(preview_lines)
                return f"{preview_text}\n    ... (共{len(lines)}行)"
            else:
                # 少于5行，直接显示，但添加缩进
                return '\n    '.join(lines)

        # 单行文本，限制长度
        elif isinstance(value, str) and len(str_value) > 50:
            return f"{str_value[:47]}..."

        # For other types (int, float, etc.), use standard string conversion
        return str_value
    # --- END ADDED ---

    # --- ADDED: Handle hover events to show parameter tooltip --- 
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """Formats and sets the tooltip when the mouse enters the card."""
        # 优化：使用缓存的工具提示，避免每次重新计算
        if not hasattr(self, '_cached_tooltip') or self._tooltip_needs_update:
            self._cached_tooltip = self._generate_tooltip_text()
            self._tooltip_needs_update = False

        # 先调用父类方法
        super().hoverEnterEvent(event)

        # 立即设置工具提示，不等待Qt的默认延迟
        self.setToolTip(self._cached_tooltip)

        # 使用QToolTip立即显示工具提示
        from PySide6.QtWidgets import QToolTip
        if self._cached_tooltip and hasattr(self, 'scene') and self.scene():
            # 获取鼠标在屏幕上的位置
            scene_pos = event.scenePos()
            if self.scene().views():
                view = self.scene().views()[0]
                view_pos = view.mapFromScene(scene_pos)
                global_pos = view.mapToGlobal(view_pos)
                # 立即显示工具提示
                QToolTip.showText(global_pos, self._cached_tooltip)

    def _generate_tooltip_text(self) -> str:
        """生成工具提示文本（优化版本）"""
        # 快速检查：如果没有参数，直接返回简单文本
        if not hasattr(self, 'parameters') or not self.parameters:
            return "详细参数:\n  (无参数)"

        param_lines = ["详细参数:"]

        # 优化：如果没有参数定义，直接显示原始参数
        if not hasattr(self, 'param_definitions') or not self.param_definitions:
            param_lines.append("  (参数定义缺失，显示原始键值)")
            # 限制显示的参数数量，避免工具提示过长
            count = 0
            for key, value in self.parameters.items():
                if count >= 10:  # 最多显示10个参数
                    param_lines.append("  ...")
                    break
                param_lines.append(f"    {key}: {repr(value)}")
                count += 1
            return "\n".join(param_lines)

        # 优化：预先计算需要显示的参数，避免重复检查
        visible_params = []
        for name, param_def in self.param_definitions.items():
            # 快速跳过不需要的参数类型
            param_type = param_def.get('type')
            if param_type == 'separator':
                continue

            # 跳过所有隐藏参数
            if param_type == 'hidden':
                continue

            # 检查条件显示（优化：只在有条件时才检查）
            if 'condition' in param_def:
                condition_def = param_def['condition']

                # 处理多条件和单条件
                condition_met = True
                try:
                    if isinstance(condition_def, list):
                        # 多条件：所有条件都必须满足（AND逻辑）
                        for single_condition in condition_def:
                            if isinstance(single_condition, dict):
                                controlling_param_name = single_condition.get('param')
                                expected_value = single_condition.get('value')
                                current_value = self.parameters.get(controlling_param_name)

                                if isinstance(expected_value, list):
                                    if current_value not in expected_value:
                                        condition_met = False
                                        break
                                else:
                                    if current_value != expected_value:
                                        condition_met = False
                                        break
                    else:
                        # 单条件
                        if isinstance(condition_def, dict):
                            controlling_param_name = condition_def.get('param')
                            expected_value = condition_def.get('value')
                            current_value = self.parameters.get(controlling_param_name)

                            # 调试信息
                            if name in ['min_delay', 'max_delay', 'fixed_delay']:
                                print(f"调试工具提示条件: 参数={name}, 控制参数={controlling_param_name}, 期望值={expected_value}, 当前值={current_value}")
                                print(f"调试工具提示条件: 所有参数={dict(self.parameters)}")

                            # 检查条件是否满足
                            if isinstance(expected_value, list):
                                condition_met = current_value in expected_value
                            else:
                                condition_met = current_value == expected_value
                except Exception as e:
                    # 如果条件检查出错，默认显示参数
                    debug_print(f"TaskCard条件检查出错: {e}")
                    condition_met = True

                if not condition_met:
                    continue

            # 添加到可见参数列表
            visible_params.append((name, param_def))

        # 生成工具提示文本
        for name, param_def in visible_params:
            label = param_def.get('label', name)
            raw_value = self.parameters.get(name)
            formatted_value = self._format_tooltip_value(raw_value)
            param_lines.append(f"  {label}: {formatted_value}")

        return "\n".join(param_lines)
        
    # hoverLeaveEvent is modified above to clear the tooltip
    # --- END ADDED --- 

    # --- ADDED Flash methods --- 
    def flash(self, duration_ms: int = 500):
        """ Starts persistently flashing the card border. """
        if self._is_flashing: # Already flashing
            return
        debug_print(f"  [FLASH_DEBUG] Starting flash for Card {self.card_id}")
        self._is_flashing = True
        # Store the non-flashing border based on current execution state
        self._original_border_pen_before_flash = self.state_border_pens.get(self.execution_state, self.default_pen)
        self._flash_border_on = True # Start with flash border visible
        self._current_border_pen = self.flash_border_pen # Set initial flash state
        self.flash_toggle_timer.start(self.flash_interval_ms) # Start repeating timer
        self.update() # Trigger repaint

    def stop_flash(self):
        """ Stops the persistent flashing and restores the border. """
        if not self._is_flashing: # Not flashing
            return
        debug_print(f"  [FLASH_DEBUG] Stopping flash for Card {self.card_id}")
        self._is_flashing = False
        self.flash_toggle_timer.stop()
        self._current_border_pen = self._original_border_pen_before_flash
        self.update() # Trigger repaint

    def _toggle_flash_border(self):
        """ Called by the timer to toggle the visual state of the flash. """
        if not self._is_flashing: # Safety check
            self.flash_toggle_timer.stop()
            return
        self._flash_border_on = not self._flash_border_on
        if self._flash_border_on:
            self._current_border_pen = self.flash_border_pen
        else:
            # Show the original border during the "off" cycle of the flash
            self._current_border_pen = self._original_border_pen_before_flash
        self.update()
    # --- END Flash methods --- 