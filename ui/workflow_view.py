import sys, math, time
from typing import Optional, Any, Dict, List # Import Dict for type hinting

# 调试开关 - 设置为 False 可以禁用所有调试输出
DEBUG_ENABLED = False

def debug_print(*args, **kwargs):
    """条件调试打印函数"""
    if DEBUG_ENABLED:
        print(*args, **kwargs)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QApplication, QPushButton, QVBoxLayout, QWidget, QGraphicsLineItem, QMenu, QInputDialog, QMessageBox, QDialog, QFileDialog, QGraphicsEllipseItem # Removed QResizeEvent, QShowEvent
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QLineF, QTimer # <<< ADDED QTimer
from PySide6.QtGui import QPainter, QWheelEvent, QColor, QBrush, QMouseEvent, QPen, QAction, QTransform, QResizeEvent, QShowEvent # <<< ADDED QResizeEvent, QShowEvent HERE
import os
# Import json module
import json
import logging # <-- Import logging
import collections # <-- Added for BFS traversal
import copy # Added for deep copy
import re # <<< ADDED: Import re for regex parsing
from datetime import datetime # <<< ADDED: Import datetime for metadata
import os # <<< ADDED: Import os for file operations

logger = logging.getLogger(__name__) # <<< ADDED: Define module-level logger

# Import theme system
try:
    from ui.theme import ThemeManager, ThemeMode
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False
    logger.warning("主题系统不可用，WorkflowView将使用默认颜色")

# --- MOVED TaskCard import earlier for Signal definition ---
from .task_card import TaskCard, PORT_TYPES # Import TaskCard and PORT_TYPES
# ----------------------------------------------------------
from .connection_line import ConnectionLine, ConnectionType # Import ConnectionLine and ConnectionType
# Removed direct import of TASK_MODULES
# from tasks import TASK_MODULES 
# Import the new dialog
from .select_task_dialog import SelectTaskDialog

# Define padding for fitInView
FIT_VIEW_PADDING = 50
# Define snapping distance for connection lines
SNAP_DISTANCE = 15

class WorkflowView(QGraphicsView):
    """The main view widget displaying the workflow scene with task cards."""
    # Accept task_modules in constructor
    card_moved = Signal(int, QPointF) # Existing signal
    request_paste_card = Signal(QPointF) # Signal to request paste from main window/editor
    card_added = Signal(TaskCard) # <<< ADDED: Signal when a card is added
    connection_added = Signal(object, object, str) # start_card, end_card, type
    connection_deleted = Signal(object)
    card_deleted = Signal(int) # card_id

    def __init__(self, task_modules: Dict[str, Any], images_dir: str, parent=None):
        super().__init__(parent)
        self.task_modules = task_modules # <-- Store task modules correctly
        self.images_dir = images_dir # <<< ADDED: Store images_dir

        # Scene setup
        self.scene = QGraphicsScene(self)
        # --- MODIFIED: Start with a smaller initial scene rect --- 
        self.scene.setSceneRect(-500, -300, 1000, 600) # Reasonable starting size
        # -----------------------------------------------------
        self.setScene(self.scene)
        
        # --- MODIFIED: Change Scroll Bar Policy ---
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # ---------------------------------------

        # Render hints
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Set default drag mode to ScrollHandDrag for panning
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setInteractive(True)

        # 设置焦点策略，确保能接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 确保视图可以接收键盘事件
        self.setFocus()

        # Context menu setup
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)  # 恢复此连接

        # Set window title
        self.setWindowTitle("工作流视图")
        
        # Enable drag and drop
        self.setAcceptDrops(True)

        self.zoom_factor_base = 1.15

        # Line Dragging State
        self.connections: List[ConnectionLine] = []
        self.is_dragging_line = False
        self.drag_start_card: Optional[TaskCard] = None
        self.drag_start_port_type: Optional[str] = None
        self.temp_line: Optional[QGraphicsLineItem] = None
        
        # 初始化主题颜色
        self._init_theme_colors()
        if THEME_AVAILABLE:
            self._connect_theme_signals()
        
        # Snapping state
        self.is_snapped = False
        self.snapped_target_card: Optional[TaskCard] = None

        # Store cards for easy access
        self.cards: Dict[int, TaskCard] = {}
        self._next_card_id = 0
        self._max_loaded_id = -1 # Track max ID during loading
        self._dragging_item = None
        self._line_start_item: Optional[TaskCard] = None
        self._connection_type_to_draw: ConnectionType = ConnectionType.SUCCESS

        # --- Log initialization --- 
        log_func = logging.info if logging.getLogger().hasHandlers() else print
        log_func("WorkflowView Initialized.")

        # --- Demo Setup Removed --- 
        # The user will add cards manually now

        # Restore state variables for right-click handling in the view
        self._original_drag_mode = self.dragMode()
        self._right_mouse_pressed = False
        self._last_right_click_global_pos: Optional[QPointF] = None # Keep for potential future use, but not used now
        self._last_right_click_view_pos_f: Optional[QPointF] = None # <-- ADDED: Store precise view pos (float)
        self.copied_card_data: Optional[Dict[str, Any]] = None # <-- ADDED to store copied data

        # 撤销系统
        self.undo_stack: List[Dict[str, Any]] = []  # 撤销历史栈
        self.max_undo_steps = 50  # 最大撤销步数
        self._deleting_card = False  # 标志：正在删除卡片，防止连线删除触发额外撤销
        self._loading_workflow = False  # 标志：正在加载工作流，防止连线删除触发撤销保存
        self._updating_sequence = False  # 标志：正在更新序列显示，防止连线重建触发撤销保存
        self._undoing_operation = False  # 标志：正在执行撤销操作，防止撤销过程中的操作触发新的撤销保存
        
        # --- ADDED: Connect scroll bar signals for dynamic scene expansion ---
        # --- RE-ENABLED: Uncommented to restore dynamic scene expansion --- 
        self.horizontalScrollBar().valueChanged.connect(self._handle_scroll_change)
        self.verticalScrollBar().valueChanged.connect(self._handle_scroll_change)
        # --------------------------------------------------------------------
        # --- END ADDED ---

        # <<< ADDED: Track flashing cards >>>
        self.flashing_card_ids = set()
        # <<< END ADDED >>>

    def _is_workflow_running(self) -> bool:
        """检查工作流是否正在运行"""
        try:
            main_window = None
            # 从父级查找MainWindow
            try:
                parent = self.parent()
                # 添加循环计数器防止无限循环
                loop_count = 0
                max_loops = 50  # 最多向上查找50层
                while parent and not hasattr(parent, 'executor') and loop_count < max_loops:
                    parent = parent.parent()
                    loop_count += 1
                if loop_count >= max_loops:
                    logger.warning("查找MainWindow时达到最大循环次数限制")
                    parent = None
                main_window = parent
            except Exception as e:
                logger.debug(f"从父级查找MainWindow失败: {e}")
            
            # 如果没找到，从QApplication查找
            if not main_window:
                try:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for widget in app.allWidgets():
                            if hasattr(widget, 'executor') and hasattr(widget, 'executor_thread'):
                                main_window = widget
                                break
                except Exception as e:
                    logger.debug(f"从QApplication查找MainWindow失败: {e}")
            
            # 检查是否有任务正在运行
            if main_window and hasattr(main_window, 'executor') and hasattr(main_window, 'executor_thread'):
                if (main_window.executor is not None and 
                    main_window.executor_thread is not None and 
                    main_window.executor_thread.isRunning()):
                    return True
                
        except Exception as e:
            logger.error(f"检查任务运行状态时发生错误: {e}")
            
        return False

    def _block_edit_if_running(self, operation_name: str) -> bool:
        """如果工作流正在运行，阻止编辑操作并显示提示 - 增强版本

        Args:
            operation_name: 操作名称，用于错误提示

        Returns:
            bool: True如果操作被阻止，False如果可以继续
        """
        try:
            # 基础运行状态检查
            if self._is_workflow_running():
                logger.warning(f"尝试在任务运行期间执行{operation_name}操作")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "操作被禁止",
                    f"工作流正在执行中，暂时无法进行{operation_name}操作。\n\n请等待任务执行完成或停止任务后再试。"
                )
                return True

            # 增强检查：任务状态管理器状态
            if hasattr(self, 'main_window') and self.main_window:
                if hasattr(self.main_window, 'task_state_manager'):
                    current_state = self.main_window.task_state_manager.get_current_state()
                    if current_state in ["starting", "running", "stopping"]:
                        logger.warning(f"任务状态为 {current_state}，阻止 {operation_name} 操作")
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "操作被阻止",
                                          f"任务正在{current_state}，请等待任务完全停止后再进行{operation_name}操作")
                        return True

                    # 检查状态是否正在改变
                    if self.main_window.task_state_manager.is_state_changing():
                        logger.warning(f"任务状态正在改变，阻止 {operation_name} 操作")
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(self, "操作被阻止",
                                          f"任务状态正在改变，请稍候再试{operation_name}操作")
                        return True

            # 检查是否有卡片处于执行状态
            executing_cards = []
            for card_id, card in self.cards.items():
                if hasattr(card, 'execution_state') and card.execution_state in ['running', 'executing']:
                    executing_cards.append(card_id)

            if executing_cards:
                logger.warning(f"发现执行中的卡片 {executing_cards}，阻止 {operation_name} 操作")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "操作被阻止",
                                  f"发现正在执行的卡片，请等待完成后再进行{operation_name}操作")
                return True

            return False

        except Exception as e:
            logger.error(f"检查运行状态时发生错误: {e}")
            # 出错时采用保守策略，阻止操作
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "安全检查失败",
                              f"无法确定当前状态，为安全起见阻止{operation_name}操作")
            return True

    def add_task_card(self, x: float, y: float, task_type: str = "未知", card_id: Optional[int] = None, parameters: Optional[dict] = None) -> Optional[TaskCard]:
        """Adds a new task card to the scene."""
        # 检查是否正在运行，如果是则阻止添加（除非是在加载工作流期间）
        if card_id is None and self._block_edit_if_running("添加卡片"):
            return None

        # --- ADDED: 检查起点卡片限制 ---
        if task_type == "起点" and card_id is None:  # 只在新建卡片时检查，加载时不检查
            # 检查是否已存在起点卡片
            existing_start_cards = [card for card in self.cards.values() if card.task_type == "起点"]
            if existing_start_cards:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(None, "添加卡片失败",
                                  f"工作流中只能有一个起点卡片！\n\n"
                                  f"当前已存在起点卡片 (ID: {existing_start_cards[0].card_id})。\n"
                                  f"请先删除现有起点卡片，或者选择其他类型的卡片。")
                debug_print(f"阻止添加起点卡片：已存在起点卡片 ID {existing_start_cards[0].card_id}")
                return None
        # --- END ADDED ---

        # --- ADDED: Debugging ---
        logger.debug(f"DEBUG [add_task_card]: Received task_type='{task_type}', card_id={card_id}")
        logger.debug(f"DEBUG [add_task_card]: Available task module keys: {list(self.task_modules.keys())}")
        # --- END ADDED ---

        # <<< MODIFIED: Lookup Task Class from task_modules >>>
        task_info = self.task_modules.get(task_type)
        if task_info is None:
            debug_print(f"错误：未知的任务类型或模块 '{task_type}'")
            return None

        # Determine the card ID
        if card_id is None: # Generating new card ID
            # Ensure the generated ID is higher than any loaded ID
            current_id = max(self._next_card_id, self._max_loaded_id + 1)
            self._next_card_id = current_id + 1
        else: # Using provided card ID during loading
            current_id = card_id
            # Update the maximum loaded ID seen so far
            self._max_loaded_id = max(self._max_loaded_id, current_id)
            # Ensure next generated ID starts after the max loaded ID
            self._next_card_id = max(self._next_card_id, self._max_loaded_id + 1)

        # Check for ID collision (should not happen with proper loading logic)
        if current_id in self.cards:
             debug_print(f"警告：尝试添加已存在的卡片 ID {current_id}。跳过。")
             # Potentially update _next_card_id again if collision occurred due to manual generation
             if card_id is None:
                  self._next_card_id = max(self._next_card_id, current_id + 1)
             return self.cards[current_id] # Return existing card

        # Create and add the card
        card = TaskCard(self, x, y, task_type=task_type, card_id=current_id, task_module=task_info) 
        card.set_display_id(None) # Set the display ID
        debug_print(f"--- [DEBUG] TaskCard __init__ END (SIMPLIFIED) - ID: {current_id} ---")

        # --- ADD ITEM BACK HERE --- 
        self.scene.addItem(card)
        # --------------------------
        self.cards[current_id] = card 
        debug_print(f"添加卡片实例到场景: 类型='{task_type}', ID={current_id} at ({x}, {y})") # Updated log message
        
        # --- REMOVED: Instance-level signal check --- 
        # debug_print(f"DEBUG [WorkflowView]: Inspecting card {current_id} before connect:")
        # ... (removed debug prints) ...
        # debug_print(f"  - hasattr(card.delete_requested, 'connect'): {hasattr(card.delete_requested, 'connect')}")
        # -------------------------------------------
        
        # --- Restore Signal Connections/Emit --- 
        # Note: Connection should still work via instance -> class -> module lookup
        debug_print(f"DEBUG [WorkflowView]: Attempting to connect delete_requested for card {current_id}")
        card.delete_requested.connect(self.delete_card) 
        debug_print(f"DEBUG [WorkflowView]: Attempting to connect copy_requested for card {current_id}")
        card.copy_requested.connect(self.handle_copy_card)
        # 🔧 修复：不再连接edit_settings_requested到workflow_view，由main_window处理
        # debug_print(f"DEBUG [WorkflowView]: Attempting to connect edit_settings_requested for card {current_id}")
        # card.edit_settings_requested.connect(self.edit_card_settings)

        debug_print(f"DEBUG [WorkflowView]: Attempting to emit card_added for card {current_id}")
        self.card_added.emit(card) # <<< RESTORED
        # ------------------------------------------------------
        debug_print(f"--- [DEBUG] WorkflowView: Finished signal connections/emit for card {current_id}. Current cards: {list(self.cards.keys())} ---") # RESTORED final print

        # --- ADDED: Connect to the new jump target signal ---
        card.jump_target_parameter_changed.connect(self._handle_jump_target_change)
        # --- ADDED: Connect to the card click signal ---
        card.card_clicked.connect(self._handle_card_clicked)
        # ---------------------------------------------

        # 应用传入的参数（用于撤销恢复等场景）
        if parameters:
            debug_print(f"  [DEBUG] Applying provided parameters to card {current_id}: {parameters}")
            debug_print(f"  [DEBUG] Card {current_id} parameters before update: {card.parameters}")
            card.parameters.update(parameters)
            debug_print(f"  [DEBUG] Card {current_id} parameters after update: {card.parameters}")

            # 验证参数是否正确应用
            for key, value in parameters.items():
                if key in card.parameters and card.parameters[key] == value:
                    debug_print(f"    ✓ Parameter {key} correctly applied: {value}")
                else:
                    debug_print(f"    ✗ Parameter {key} failed to apply: expected {value}, got {card.parameters.get(key)}")
        else:
            debug_print(f"  [DEBUG] No parameters provided for card {current_id}")

        # 保存添加卡片状态用于撤销（除非正在加载工作流、执行撤销操作或粘贴卡片）
        if (not self._loading_workflow and not self._undoing_operation and card_id is None and
            not getattr(self, '_pasting_card', False)):
            # 只有手动添加的卡片才保存撤销状态（card_id为None表示是新建的）
            self._save_add_card_state_for_undo(current_id, task_type, x, y, parameters)
        else:
            if self._loading_workflow:
                debug_print(f"  [UNDO] Skipping add card undo save (loading workflow)")
            if self._undoing_operation:
                debug_print(f"  [UNDO] Skipping add card undo save (undoing operation)")
            if card_id is not None:
                debug_print(f"  [UNDO] Skipping add card undo save (loading existing card)")

        # --- REMOVED: Update sequence display after adding a card (moved to load_workflow end) ---
        # self.update_card_sequence_display()  # <<< REMOVED THIS LINE
        # -------------------------------------------------------------------------------------
        return card

    def add_connection(self, start_card: TaskCard, end_card: TaskCard, line_type: str):
        """Adds a connection line between two cards."""
        # 检查是否正在运行，如果是则阻止添加连接
        if self._block_edit_if_running("添加连接"):
            return None
            
        # <<< ENHANCED: 增强连接有效性验证 >>>
        debug_print(f"    [ADD_CONN_DEBUG] Validating connection: Start={start_card.card_id if start_card else 'None'}, End={end_card.card_id if end_card else 'None'}, Type='{line_type}'")
        
        # 验证卡片对象有效性
        if not start_card or not end_card:
            debug_print("错误：无法连接无效的卡片对象")
            return None
        
        # 验证卡片是否在字典中
        if start_card.card_id not in self.cards:
            debug_print(f"错误：起始卡片 ID {start_card.card_id} 不在当前工作流中")
            return None
        
        if end_card.card_id not in self.cards:
            debug_print(f"错误：目标卡片 ID {end_card.card_id} 不在当前工作流中")
            return None
        
        # 验证卡片是否在场景中
        if start_card.scene() != self.scene:
            debug_print(f"错误：起始卡片 ID {start_card.card_id} 不在当前场景中")
            return None
            
        if end_card.scene() != self.scene:
            debug_print(f"错误：目标卡片 ID {end_card.card_id} 不在当前场景中")
            return None
        
        # 验证起始卡片的输出端口是否可用
        if (hasattr(start_card, 'restricted_outputs') and start_card.restricted_outputs and
            line_type in ['success', 'failure']):
            debug_print(f"错误：起始卡片 ID {start_card.card_id} 的 {line_type} 输出端口被限制")
            return None

        # --- ADDED: Check for connections in card connection lists ---
        debug_print(f"  [CONN_DEBUG] Checking for existing connections in card lists...")

        # Check start card's connections
        if hasattr(start_card, 'connections'):
            for card_conn in start_card.connections:
                if (hasattr(card_conn, 'start_item') and hasattr(card_conn, 'end_item') and hasattr(card_conn, 'line_type') and
                    card_conn.start_item == start_card and card_conn.end_item == end_card and card_conn.line_type == line_type):
                    debug_print(f"  [CONN_DEBUG] Found connection in start card's list: {start_card.card_id} -> {end_card.card_id} ({line_type})")
                    debug_print(f"  [CONN_DEBUG] Connection in view list: {card_conn in self.connections}")
                    if card_conn not in self.connections:
                        debug_print(f"  [CONN_DEBUG] Connection not in view list, adding it for proper handling")
                        self.connections.append(card_conn)

        # Check end card's connections
        if hasattr(end_card, 'connections'):
            for card_conn in end_card.connections:
                if (hasattr(card_conn, 'start_item') and hasattr(card_conn, 'end_item') and hasattr(card_conn, 'line_type') and
                    card_conn.start_item == start_card and card_conn.end_item == end_card and card_conn.line_type == line_type):
                    debug_print(f"  [CONN_DEBUG] Found connection in end card's list: {start_card.card_id} -> {end_card.card_id} ({line_type})")
                    debug_print(f"  [CONN_DEBUG] Connection in view list: {card_conn in self.connections}")
                    if card_conn not in self.connections:
                        debug_print(f"  [CONN_DEBUG] Connection not in view list, adding it for proper handling")
                        self.connections.append(card_conn)
        # --- END ADDED ---

        # 首先检查起始端口是否已有连接（一个端口只能有一个输出连接）
        debug_print(f"  [PORT_CHECK] Checking if start port {line_type} on card {start_card.card_id} already has a connection...")
        existing_output_connection = None
        for existing_conn in self.connections:
            if (isinstance(existing_conn, ConnectionLine) and
                existing_conn.start_item == start_card and
                existing_conn.line_type == line_type):
                existing_output_connection = existing_conn
                debug_print(f"    Found existing output connection: {start_card.card_id} -> {existing_conn.end_item.card_id if existing_conn.end_item else 'None'} ({line_type})")
                break

        # 如果起始端口已有连接，先移除旧连接
        old_connection_for_modify = None
        if existing_output_connection:
            debug_print(f"  [MODIFY_CONN_DEBUG] Detected existing connection, this is a MODIFY operation")
            debug_print(f"  [MODIFY_CONN_DEBUG] Old connection: {existing_output_connection.start_item.card_id if existing_output_connection.start_item else 'None'} -> {existing_output_connection.end_item.card_id if existing_output_connection.end_item else 'None'} ({existing_output_connection.line_type if hasattr(existing_output_connection, 'line_type') else 'unknown'})")
            debug_print(f"  [MODIFY_CONN_DEBUG] New connection will be: {start_card.card_id} -> {end_card.card_id} ({line_type})")
            # 保存旧连接信息用于修改连接的撤销
            old_connection_for_modify = existing_output_connection
            # 设置修改连线标志，防止删除和添加连接时保存撤销状态
            self._modifying_connection = True
            debug_print(f"  [MODIFY_CONN_DEBUG] Set _modifying_connection = True")
            self.remove_connection(existing_output_connection)
            debug_print(f"  [MODIFY_CONN_DEBUG] Old connection removed")
            # 注意：不在这里重置 _modifying_connection，要等到新连接添加完成后

        # 验证是否已存在相同连接
        debug_print(f"  [DUPLICATE_CHECK] Checking {len(self.connections)} connections in view list...")
        for i, existing_conn in enumerate(self.connections):
            debug_print(f"    Connection {i+1}: {existing_conn.start_item.card_id if hasattr(existing_conn, 'start_item') and existing_conn.start_item else 'N/A'} -> {existing_conn.end_item.card_id if hasattr(existing_conn, 'end_item') and existing_conn.end_item else 'N/A'} ({existing_conn.line_type if hasattr(existing_conn, 'line_type') else 'N/A'})")

            if (isinstance(existing_conn, ConnectionLine) and
                existing_conn.start_item == start_card and
                existing_conn.end_item == end_card and
                existing_conn.line_type == line_type):
                # --- ADDED: Enhanced duplicate connection debugging and validation ---
                in_scene = existing_conn.scene() == self.scene
                path_empty = existing_conn.path().isEmpty() if hasattr(existing_conn, 'path') else True
                debug_print(f"警告：相同类型的连接已存在 ({start_card.card_id} -> {end_card.card_id}, {line_type})")
                debug_print(f"  现有连接状态: 在场景中={in_scene}, 路径为空={path_empty}")
                debug_print(f"  连接对象: {existing_conn}")

                # --- ADDED: Enhanced connection validity check ---
                # 检查连接是否真的可见（除了路径检查，还要检查端口限制）
                start_restricted = (hasattr(existing_conn.start_item, 'restricted_outputs') and
                                  existing_conn.start_item.restricted_outputs and
                                  existing_conn.line_type in ['success', 'failure'])

                debug_print(f"  连接有效性检查: 在场景中={in_scene}, 路径为空={path_empty}, 起始端口限制={start_restricted}")

                # 如果现有连接无效，则移除它并创建新连接
                if not in_scene or path_empty or start_restricted:
                    debug_print(f"  现有连接无效，移除并创建新连接")
                    self._force_remove_connection(existing_conn)
                    # --- ADDED: Also clean up any other connections of the same type between these cards ---
                    self._cleanup_duplicate_connections(start_card, end_card, line_type)
                    # --- END ADDED ---
                    break  # 跳出循环，继续创建新连接
                else:
                    debug_print(f"  现有连接有效，但强制更新路径")
                    # 即使连接有效，也强制更新路径以确保可见性
                    existing_conn.update_path()
                    return existing_conn
                # --- END ADDED ---
                # --- END ADDED ---

        debug_print(f"    [ADD_CONN_DEBUG] Validation passed. Creating ConnectionLine...")
        # <<< END ENHANCED >>>

        # --- ADDED: Force cleanup any remaining duplicate connections before creating new one ---
        debug_print(f"    [ADD_CONN_DEBUG] Force cleaning up any remaining duplicate connections...")
        self._cleanup_duplicate_connections(start_card, end_card, line_type)
        # --- END ADDED ---

        # --- ADDED: Detailed logging for connection creation ---
        debug_print(f"    [ADD_CONN_DEBUG] Attempting to create ConnectionLine: Start={start_card.card_id}, End={end_card.card_id}, Type='{line_type}'")
        try:
            connection = ConnectionLine(start_card, end_card, line_type)
            debug_print(f"      [ADD_CONN_DEBUG] ConnectionLine object created: {connection}")
        except Exception as e:
            debug_print(f"      [ADD_CONN_ERROR] Failed to create ConnectionLine object: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        debug_print(f"      [ADD_CONN_DEBUG] Attempting self.scene.addItem({connection})")
        try:
            self.scene.addItem(connection)
            # Verify if item is in scene
            is_in_scene = connection.scene() == self.scene
            debug_print(f"      [ADD_CONN_DEBUG] self.scene.addItem finished. Item in scene? {is_in_scene}")
            if not is_in_scene:
                 debug_print(f"      [ADD_CONN_WARN] Item {connection} was NOT added to the scene successfully!")
                 # <<< ENHANCED: 创建失败时的清理 >>>
                 if hasattr(connection, 'start_item'):
                     connection.start_item = None
                 if hasattr(connection, 'end_item'):
                     connection.end_item = None
                 # ConnectionLine继承自QGraphicsPathItem，不是QObject，所以没有deleteLater()
                 # 直接删除引用即可，Qt会在适当时候回收内存
                 del connection
                 return None
                 # <<< END ENHANCED >>>
        except Exception as e:
            debug_print(f"      [ADD_CONN_ERROR] Failed during self.scene.addItem: {e}")
            import traceback
            traceback.print_exc()
            # Attempt cleanup if possible
            if connection in self.connections: 
                self.connections.remove(connection)
            # <<< ENHANCED: 更彻底的清理 >>>
            if hasattr(connection, 'start_item'):
                connection.start_item = None
            if hasattr(connection, 'end_item'):
                connection.end_item = None
            # ConnectionLine继承自QGraphicsPathItem，不是QObject，所以没有deleteLater()
            # 直接删除引用即可，Qt会在适当时候回收内存
            del connection
            # <<< END ENHANCED >>>
            return None
        # --------------------------------------------------------

        # Register the connection with both cards (assuming add_connection still exists)
        if hasattr(start_card, 'add_connection'):
            start_card.add_connection(connection)
            debug_print(f"      [ADD_CONN_DEBUG] Added to start card connections list. Count: {len(start_card.connections)}")
        if hasattr(end_card, 'add_connection'):
            end_card.add_connection(connection)
            debug_print(f"      [ADD_CONN_DEBUG] Added to end card connections list. Count: {len(end_card.connections)}")
        
        # --- ADDED: Add connection to view's tracking list --- 
        self.connections.append(connection)
        debug_print(f"      [ADD_CONN_DEBUG] Added to view connections list. Total count: {len(self.connections)}")
        # -----------------------------------------------------
        
        # <<< ENHANCED: 发出连接添加信号 >>>
        self.connection_added.emit(start_card, end_card, line_type)
        debug_print(f"      [ADD_CONN_DEBUG] Connection added signal emitted")
        # <<< END ENHANCED >>>
        
        # --- REMOVED: No longer update sequence or path here. Done by final update in load/other actions ---
        # if line_type == 'sequential':
        #     debug_print("  [CONN_DEBUG] Sequential connection added, triggering sequence update.")
        #     self.update_card_sequence_display() # <<< REMOVED
        # else:
        #     # For jump lines, just ensure they are visually updated if needed (already handled by update_card_sequence_display called elsewhere)
        #     connection.update_path() # Was: connection.update_positions() # <<< REMOVED
        # --- END REMOVAL ---

        # --- ADDED: Update card parameters when connection is created ---
        self._update_card_parameters_on_connection_create(start_card, end_card, line_type)
        # --- END ADDED ---

        # 保存连接状态用于撤销（除非正在加载工作流、更新序列显示、执行撤销操作或修改连线）
        debug_print(f"  [UNDO_SAVE_DEBUG] Checking undo save conditions:")
        debug_print(f"    _loading_workflow: {self._loading_workflow}")
        debug_print(f"    _updating_sequence: {self._updating_sequence}")
        debug_print(f"    _undoing_operation: {self._undoing_operation}")
        debug_print(f"    _modifying_connection: {getattr(self, '_modifying_connection', False)}")
        debug_print(f"    old_connection_for_modify: {old_connection_for_modify is not None}")

        if (not self._loading_workflow and not self._updating_sequence and not self._undoing_operation and
            not getattr(self, '_modifying_connection', False)):
            # 这是纯添加新连接操作，保存添加连接的撤销状态
            debug_print(f"  [UNDO_SAVE_DEBUG] PURE ADD: Saving add_connection undo state")
            self._save_add_connection_state_for_undo(start_card, end_card, line_type)
        elif old_connection_for_modify and not self._loading_workflow and not self._updating_sequence and not self._undoing_operation:
            # 这是修改连接操作，保存修改连接的撤销状态
            debug_print(f"  [UNDO_SAVE_DEBUG] MODIFY: Saving modify_connection undo state")
            self._save_modify_connection_state_for_undo(old_connection_for_modify, start_card, end_card, line_type)
            # 重置修改连线标志
            self._modifying_connection = False
            debug_print(f"  [UNDO_SAVE_DEBUG] MODIFY: Reset _modifying_connection flag")
        else:
            debug_print(f"  [UNDO_SAVE_DEBUG] SKIPPING undo save due to conditions:")
            if self._loading_workflow:
                debug_print(f"    - loading workflow")
            if self._updating_sequence:
                debug_print(f"    - updating sequence")
            if self._undoing_operation:
                debug_print(f"    - undoing operation")
            if getattr(self, '_modifying_connection', False):
                debug_print(f"    - modifying connection")
                # 如果是修改连线但在其他条件下跳过，也要重置标志
                if old_connection_for_modify:
                    self._modifying_connection = False
                    debug_print(f"    - reset _modifying_connection flag")

        debug_print(f"      [ADD_CONN_DEBUG] Connection creation completed successfully")
        return connection

    def remove_connection(self, connection):
        """Removes a connection from the scene and internal tracking - 增强安全版本"""
        try:
            # 直接使用传统删除方法
            logger.info(f"删除连接")

            # 检查是否正在运行，如果是则阻止删除连接
            if self._block_edit_if_running("删除连接"):
                return

            # 验证连接对象的有效性
            if not connection:
                logger.warning("尝试删除空连接对象")
                return

            # 检查连接是否仍然有效
            if not hasattr(connection, 'start_item') or not hasattr(connection, 'end_item'):
                logger.warning("连接对象缺少必要属性，可能已损坏")
                return

            # 检查连接是否还在连接列表中
            if connection not in self.connections:
                logger.debug("连接已不在连接列表中，可能已被删除")
                return

            # 保存连接状态用于撤销（除非正在删除卡片、加载工作流、更新序列显示、执行撤销操作或修改连线）
            if (not self._deleting_card and not self._loading_workflow and not self._updating_sequence and
                not self._undoing_operation and not getattr(self, '_modifying_connection', False)):
                try:
                    self._save_connection_state_for_undo(connection)
                except Exception as e:
                    logger.warning(f"保存连接撤销状态失败: {e}")
            else:
                if self._deleting_card:
                    debug_print(f"  [UNDO] Skipping connection undo save (deleting card)")
                if self._loading_workflow:
                    debug_print(f"  [UNDO] Skipping connection undo save (loading workflow)")
                if self._updating_sequence:
                    debug_print(f"  [UNDO] Skipping connection undo save (updating sequence)")
                if self._undoing_operation:
                    debug_print(f"  [UNDO] Skipping connection undo save (undoing operation)")
                if getattr(self, '_modifying_connection', False):
                    debug_print(f"  [UNDO] Skipping connection undo save (modifying connection)")

            logger.info(f"--- [DEBUG] WorkflowView: Attempting to remove connection: {connection} ---")
            was_sequential = False

        except Exception as e:
            logger.error(f"删除连接预处理失败: {e}", exc_info=True)
            return
        
        if isinstance(connection, ConnectionLine) and hasattr(connection, 'line_type') and connection.line_type == 'sequential':
             was_sequential = True

        # --- MODIFIED: Clear jump parameters on connection deletion ---
        if isinstance(connection, ConnectionLine) and \
           hasattr(connection, 'start_item') and isinstance(connection.start_item, TaskCard) and \
           hasattr(connection.start_item, 'parameters'):
            
            start_card: TaskCard = connection.start_item # Type hint for clarity
            line_type = connection.line_type
            param_to_clear = None
            # action_param_name = None # e.g., 'on_success' or 'on_failure' # Kept for future reference if action reset is needed

            if line_type == ConnectionType.SUCCESS.value:
                param_to_clear = 'success_jump_target_id'
                # action_param_name = 'on_success'
            elif line_type == ConnectionType.FAILURE.value:
                param_to_clear = 'failure_jump_target_id'
                # action_param_name = 'on_failure'

            parameter_actually_changed = False
            if param_to_clear and param_to_clear in start_card.parameters:
                if start_card.parameters[param_to_clear] is not None: # Only change if it was set
                    logger.info(f"  [SYNC] Clearing parameter '{param_to_clear}' for card {start_card.card_id} due to '{line_type}' connection removal.")
                    start_card.parameters[param_to_clear] = None
                    parameter_actually_changed = True

                    # 同时重置相关的动作参数
                    if line_type == ConnectionType.SUCCESS.value and start_card.parameters.get('on_success') == '跳转到步骤':
                        start_card.parameters['on_success'] = '执行下一步'
                        logger.info(f"  [SYNC] Reset on_success action to '执行下一步' for card {start_card.card_id}")
                    elif line_type == ConnectionType.FAILURE.value and start_card.parameters.get('on_failure') == '跳转到步骤':
                        start_card.parameters['on_failure'] = '执行下一步'
                        logger.info(f"  [SYNC] Reset on_failure action to '执行下一步' for card {start_card.card_id}")

            if parameter_actually_changed:
                start_card.update()
                logger.info(f"卡片 {start_card.card_id} 的参数因连接线删除而更新。")
        # --- END MODIFICATION ---

        try:
            # Remove from card connection lists - 增强安全处理
            if hasattr(connection, 'start_item') and connection.start_item:
                try:
                    if hasattr(connection.start_item, 'remove_connection'):
                        connection.start_item.remove_connection(connection)
                        logger.debug(f"  [DEBUG] Removed connection from start item: {connection.start_item.title if hasattr(connection.start_item, 'title') else 'Unknown'}")
                except Exception as e:
                    logger.warning(f"从起始卡片移除连接失败: {e}")

            if hasattr(connection, 'end_item') and connection.end_item:
                try:
                    if hasattr(connection.end_item, 'remove_connection'):
                        connection.end_item.remove_connection(connection)
                        logger.debug(f"  [DEBUG] Removed connection from end item: {connection.end_item.title if hasattr(connection.end_item, 'title') else 'Unknown'}")
                except Exception as e:
                    logger.warning(f"从目标卡片移除连接失败: {e}")

            # Remove from view's connection list
            try:
                if connection in self.connections:
                    self.connections.remove(connection)
                    logger.debug(f"  [DEBUG] Removed connection from view's list.")
            except Exception as e:
                logger.warning(f"从视图连接列表移除连接失败: {e}")

            # Remove from scene
            try:
                if hasattr(connection, 'scene') and connection.scene() == self.scene:
                    self.scene.removeItem(connection)
                    logger.debug(f"  [DEBUG] Removed connection from scene.")
                else:
                    logger.debug(f"  [DEBUG] Connection was not in the scene or already removed.")
            except Exception as e:
                logger.warning(f"从场景移除连接失败: {e}")

            # 清理连接对象引用，防止内存泄漏
            try:
                if hasattr(connection, 'start_item'):
                    connection.start_item = None
                if hasattr(connection, 'end_item'):
                    connection.end_item = None
                logger.debug(f"  [DEBUG] Cleared connection object references.")
            except Exception as e:
                logger.warning(f"清理连接对象引用失败: {e}")

            logger.info(f"--- [DEBUG] WorkflowView: Connection removal finished for: {connection} ---")

            # 更新序列显示（如果是顺序连接）
            if was_sequential:
                try:
                    logger.info("  [CONN_DEBUG] Manual sequential connection removed, triggering sequence update.")
                    self.update_card_sequence_display()
                    logger.debug(f"  Direct sequence update called after sequential connection removal.")
                except Exception as e:
                    logger.error(f"更新序列显示失败: {e}")

        except Exception as e:
            logger.error(f"连接删除过程中发生严重错误: {e}", exc_info=True)
            # 即使出错也要尝试基本清理
            try:
                if connection in self.connections:
                    self.connections.remove(connection)
                if hasattr(connection, 'scene') and connection.scene():
                    connection.scene().removeItem(connection)
            except:
                pass

    def _init_theme_colors(self):
        """初始化主题颜色"""
        if THEME_AVAILABLE:
            try:
                theme_manager = ThemeManager.instance()
                colors = theme_manager.get_palette()
            except Exception as e:
                logger.warning(f"获取主题颜色失败: {e}")
                colors = None
        else:
            colors = None
        
        if colors:
            # 设置临时连线颜色
            self.temp_line_pen = QPen(QColor(colors["text_disabled"]), 1.5, Qt.PenStyle.DashLine)
            self.temp_line_snap_pen = QPen(QColor(colors["primary"]), 2.0, Qt.PenStyle.DashLine)
            # 设置背景色
            self.setBackgroundBrush(QBrush(QColor(colors["workflow_background"])))
        else:
            # 使用默认颜色
            self.temp_line_pen = QPen(Qt.GlobalColor.black, 1.5, Qt.PenStyle.DashLine)
            self.temp_line_snap_pen = QPen(QColor(0, 120, 215), 2.0, Qt.PenStyle.DashLine)
    
    def _connect_theme_signals(self):
        """连接主题变化信号"""
        try:
            theme_manager = ThemeManager.instance()
            theme_manager.theme_changed.connect(self._on_theme_changed)
        except Exception as e:
            logger.warning(f"连接主题信号失败: {e}")
    
    def _on_theme_changed(self, mode: ThemeMode):
        """主题变化回调"""
        self._init_theme_colors()
        # 重绘所有连接线
        for connection in self.connections:
            if hasattr(connection, 'set_line_color'):
                connection.set_line_color()
        self.scene.update()

        # 兼容处理：mode 可能是 ThemeMode 枚举或字符串
        mode_str = mode.value if hasattr(mode, 'value') else str(mode)
        logger.debug(f"WorkflowView 主题更新为: {mode_str}")

    def wheelEvent(self, event: QWheelEvent):
        """Handles mouse wheel events for zooming."""
        # Check if Ctrl key is pressed (optional: zoom only with Ctrl)
        # if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
        
        delta = event.angleDelta().y()

        if delta > 0:
            # Zoom in
            scale_factor = self.zoom_factor_base
        elif delta < 0:
            # Zoom out
            scale_factor = 1.0 / self.zoom_factor_base
        else:
            # No vertical scroll
            super().wheelEvent(event) # Pass to base class if no zoom
            return

        # Apply scaling
        self.scale(scale_factor, scale_factor)
        event.accept() # Indicate the event has been handled
        # else:
        #     # If Ctrl is not pressed, pass the event to the base class for scrolling
        #     super().wheelEvent(event) 

    # --- Line Dragging Methods --- 
    def start_drag_line(self, start_card: TaskCard, port_type: str):
        """Called by TaskCard when a drag starts from an output port."""
        # 检查是否正在运行，如果是则阻止拖拽连接
        if self._block_edit_if_running("拖拽连接"):
            return
            
        debug_print(f"  [DRAG_DEBUG] WorkflowView.start_drag_line called. Card: {start_card.card_id}, Port: {port_type}") # <-- ADD LOG
        
        # <<< ENHANCED: 拖拽前验证连接状态 >>>
        logger.debug("验证连接状态（拖拽开始前）...")
        invalid_count = self.validate_connections()
        if invalid_count > 0:
            logger.info(f"拖拽开始前清理了 {invalid_count} 个无效连接")
        # <<< END ENHANCED >>>
        
        self.is_dragging_line = True
        self.drag_start_card = start_card
        self.drag_start_port_type = port_type
        
        # Get the starting position in scene coordinates
        start_pos = start_card.get_output_port_scene_pos(port_type)
        
        # Create and add the temporary line
        self.temp_line = QGraphicsLineItem(start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y())
        self.temp_line.setPen(self.temp_line_pen)
        self.scene.addItem(self.temp_line)
        debug_print(f"  [DRAG_DEBUG] Temp line created and added to scene.") # <-- ADD LOG
        
        # Temporarily disable scene panning while dragging line
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def update_drag_line(self, end_pos_scene: QPointF):
        """Updates the end position of the temporary drag line, implementing snapping."""
        if not self.temp_line or not self.is_dragging_line or not self.drag_start_card or not self.drag_start_port_type:
            return

        target_pos = end_pos_scene # Default to mouse position
        snapped = False
        snap_distance_sq = SNAP_DISTANCE ** 2
        self.snapped_target_card = None # Reset snapped card initially

        # Check for snapping candidates
        for card in self.cards.values():
            if card == self.drag_start_card: # Don't snap to the starting card
                continue
                
            # Get the potential target input port position in scene coordinates
            potential_snap_target = card.get_input_port_scene_pos(self.drag_start_port_type)
            
            # Calculate distance squared for efficiency
            delta = end_pos_scene - potential_snap_target
            dist_sq = delta.x()**2 + delta.y()**2
            
            if dist_sq <= snap_distance_sq:
                target_pos = potential_snap_target # Snap to the port center
                snapped = True
                self.snapped_target_card = card # Store the card we snapped to
                break # Snap to the first valid port found

        self.is_snapped = snapped # Update overall snapping status

        # Update line end position
        line = self.temp_line.line()
        line.setP2(target_pos)
        self.temp_line.setLine(line)
        
        # Update line style based on snapping state
        if snapped:
            self.temp_line.setPen(self.temp_line_snap_pen)
        else:
            self.temp_line.setPen(self.temp_line_pen)

    def end_drag_line(self, end_pos: QPointF):
        """Finalizes line dragging: creates connection if valid, removes temp line."""
        logger.debug(f"  [DRAG_DEBUG] WorkflowView.end_drag_line called. End pos (scene): {end_pos}")
        self.is_dragging_line = False

        if self.temp_line:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None
            logger.debug(f"  [DRAG_DEBUG] Temp line removed from scene.")

        needs_update = False
        if self.is_snapped and self.snapped_target_card and self.drag_start_card:
            start_card = self.drag_start_card
            end_card = self.snapped_target_card
            port_type = self.drag_start_port_type

            # <<< ENHANCED: 连接创建前的全面验证 >>>
            logger.debug(f"  [DRAG_VALIDATION] Validating connection before creation...")
            
            # 验证起始卡片仍然有效
            if start_card.card_id not in self.cards:
                logger.warning(f"  [DRAG_VALIDATION] Start card {start_card.card_id} no longer exists in workflow. Aborting connection.")
                self._cleanup_drag_state()
                return
            
            # 验证目标卡片仍然有效
            if end_card.card_id not in self.cards:
                logger.warning(f"  [DRAG_VALIDATION] End card {end_card.card_id} no longer exists in workflow. Aborting connection.")
                self._cleanup_drag_state()
                return
            
            # 验证卡片仍在场景中
            if start_card.scene() != self.scene:
                logger.warning(f"  [DRAG_VALIDATION] Start card {start_card.card_id} is no longer in scene. Aborting connection.")
                self._cleanup_drag_state()
                return
                
            if end_card.scene() != self.scene:
                logger.warning(f"  [DRAG_VALIDATION] End card {end_card.card_id} is no longer in scene. Aborting connection.")
                self._cleanup_drag_state()
                return
            
            logger.debug(f"  [DRAG_VALIDATION] All validations passed. Proceeding with connection creation.")
            # <<< END ENHANCED >>>

            if start_card == end_card:
                logger.debug("  [DRAG_DEBUG] Drag ended on self. Connection not created.")
            elif any(conn for conn in start_card.connections
                     if isinstance(conn, ConnectionLine) and conn.end_item == end_card and conn.line_type == port_type):
                logger.debug(f"  [DRAG_DEBUG] Duplicate connection detected ({start_card.card_id} -> {end_card.card_id}, type: {port_type}). Not created.")
                # --- ADDED: Force cleanup when duplicate detected during manual connection ---
                logger.debug(f"  [DRAG_DEBUG] Force cleaning up duplicate connection during manual drag...")
                self._cleanup_duplicate_connections(start_card, end_card, port_type)
                # Try to create connection again after cleanup
                logger.debug(f"  [DRAG_DEBUG] Attempting to create connection after cleanup...")
                connection = self.add_connection(start_card, end_card, port_type)
                if connection:
                    logger.debug(f"  [DRAG_DEBUG] Successfully created connection after cleanup: {connection}")
                else:
                    logger.debug(f"  [DRAG_DEBUG] Failed to create connection even after cleanup")
                # --- END ADDED ---
            elif (port_type == ConnectionType.SUCCESS.value or port_type == ConnectionType.FAILURE.value) and start_card == end_card:
                logger.debug(f"  [DRAG_DEBUG] Self-loop connection ignored for Success/Failure port type on card {start_card.card_id}.")
            else:
                logger.debug(f"  [SYNC_DEBUG] Checking for existing output connection from card {start_card.card_id}, port type '{port_type}'.")
                existing_connection_to_remove = None
                for conn in list(start_card.connections):
                    if isinstance(conn, ConnectionLine) and conn.start_item == start_card and conn.line_type == port_type:
                        existing_connection_to_remove = conn
                        break
                if existing_connection_to_remove:
                    logger.debug(f"  [SYNC_DEBUG] Removing existing connection from port '{port_type}' of card {start_card.card_id} before adding new one.")
                    self.remove_connection(existing_connection_to_remove) # This might trigger an update

                if port_type == ConnectionType.SUCCESS.value or port_type == ConnectionType.FAILURE.value:
                    param_name = 'success_jump_target_id' if port_type == ConnectionType.SUCCESS.value else 'failure_jump_target_id'
                    action_param = 'on_success' if port_type == ConnectionType.SUCCESS.value else 'on_failure'
                    
                    logger.debug(f"  [DRAG_DEBUG] Jump connection ({port_type}). Updating parameters for card {start_card.card_id}.")
                    if action_param in start_card.parameters and start_card.parameters[action_param] != '跳转到步骤':
                        logger.info(f"  Updating card {start_card.card_id} parameter '{action_param}' to '跳转到步骤' due to new connection drag.")
                        start_card.parameters[action_param] = '跳转到步骤'
                    
                    if param_name in start_card.parameters:
                        logger.info(f"  Updating card {start_card.card_id} parameter '{param_name}' to {end_card.card_id}")
                        start_card.parameters[param_name] = end_card.card_id
                    else:
                        logger.warning(f"  Skipping parameter update: Card {start_card.card_id} ({start_card.task_type}) does not have parameter '{param_name}'.")
                    
                    # <<< ENHANCED: 创建跳转连接时使用增强的add_connection >>>
                    logger.debug(f"  [DRAG_DEBUG] Creating jump connection via add_connection...")
                    connection = self.add_connection(start_card, end_card, port_type)
                    if connection:
                        logger.debug(f"  [DRAG_DEBUG] Jump connection created successfully: {connection}")
                    else:
                        logger.warning(f"  [DRAG_DEBUG] Failed to create jump connection")
                    # <<< END ENHANCED >>>
                    needs_update = True # Parameter change means an update is needed
                
                elif port_type == "sequential": # Check against the actual string value
                    logger.debug(f"  [DRAG_DEBUG] Sequential connection. Creating connection {start_card.card_id} -> {end_card.card_id}...")
                    connection = self.add_connection(start_card, end_card, port_type)
                    if connection:
                        logger.debug(f"  [DRAG_DEBUG] Sequential connection created: {connection}")
                        if start_card.task_type == "起点" and 'next_step_card_id' in start_card.parameters:
                            logger.info(f"  Updating '起点' card {start_card.card_id} parameter 'next_step_card_id' to {end_card.card_id}")
                            start_card.parameters['next_step_card_id'] = end_card.card_id
                    else:
                        logger.warning(f"  [DRAG_DEBUG] Failed to create sequential connection")
                    needs_update = True

                if needs_update:
                    logger.debug(f"  [DRAG_DEBUG] Triggering sequence/jump update after drag operation for port type '{port_type}'.")
                    self.update_card_sequence_display()
        else:
            logger.debug(f"  [DRAG_DEBUG] Drag ended without snapping to a valid target.")

        # <<< ENHANCED: 使用清理方法统一清理状态 >>>
        self._cleanup_drag_state()
        # <<< END ENHANCED >>>

    # <<< ENHANCED: 新增拖拽状态清理方法 >>>
    def _cleanup_drag_state(self):
        """Clean up drag state and restore view mode."""
        logger.debug(f"  [DRAG_CLEANUP] Cleaning up drag state...")
        
        self.drag_start_card = None
        self.drag_start_port_type = None
        self.is_snapped = False
        self.snapped_target_card = None
        
        # 确保临时线已被移除
        if self.temp_line and self.temp_line.scene() == self.scene:
            self.scene.removeItem(self.temp_line)
            self.temp_line = None

        restore_mode = self._original_drag_mode if self._original_drag_mode is not None else QGraphicsView.DragMode.ScrollHandDrag
        self.setDragMode(restore_mode)
        logger.debug(f"  [DRAG_CLEANUP] Restored drag mode to {restore_mode} after line drag.")
    # <<< END ENHANCED >>>

    # --- Override Mouse Events --- 
    def mousePressEvent(self, event: QMouseEvent):
        """Override mouse press to handle multi-selection, background clicks, and drag operations."""
        item_at_pos = self.itemAt(event.pos())
        modifiers = event.modifiers()

        # Handle Ctrl+Left click for multi-selection
        if (event.button() == Qt.MouseButton.LeftButton and
            modifiers == Qt.KeyboardModifier.ControlModifier):

            if isinstance(item_at_pos, TaskCard):
                # Ctrl+点击卡片：切换选择状态
                if item_at_pos.isSelected():
                    item_at_pos.setSelected(False)
                    debug_print(f"  [MULTI_SELECT] Ctrl+Click: Deselected card {item_at_pos.card_id}")
                else:
                    item_at_pos.setSelected(True)
                    debug_print(f"  [MULTI_SELECT] Ctrl+Click: Selected card {item_at_pos.card_id}")
                event.accept()
                return
            elif item_at_pos is None:
                # Ctrl+拖拽背景：启用框选模式
                debug_print("  [MULTI_SELECT] Ctrl+Drag: Enabling rubber band selection")
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                super().mousePressEvent(event)
                return

        # If clicking background (or non-card item) with left button, stop flashing
        if event.button() == Qt.MouseButton.LeftButton and item_at_pos is None:
             debug_print("  [DEBUG] WorkflowView: Background left-clicked. Stopping all flashing.")
             self._stop_all_flashing()

             # 确保视图获得焦点，以便接收键盘事件
             if not self.hasFocus():
                 self.setFocus()
                 debug_print("  [FOCUS] Set focus to WorkflowView on background click")

             # 如果不是Ctrl+拖拽，则清除所有选择并允许平移
             if modifiers != Qt.KeyboardModifier.ControlModifier:
                 self.scene.clearSelection()
                 # Allow panning to start
                 super().mousePressEvent(event)
             return

        # Handle right-click for context menu (ignores press)
        if event.button() == Qt.MouseButton.RightButton:
            self._last_right_click_view_pos_f = event.position()
            debug_print("  [DEBUG] WorkflowView: Right mouse button pressed. Storing pos. NOT calling super() initially.")
            event.accept()
            return

        # Handle left-click on a card (will emit card_clicked handled by _handle_card_clicked)
        # or port drag (handled by TaskCard.mousePressEvent)
        # Let the normal event propagation happen for items/drag
        debug_print("  [DEBUG] WorkflowView: Left/Other mouse button pressed on item or starting drag. Calling super().")

        # 确保视图获得焦点，以便接收键盘事件
        if not self.hasFocus():
            self.setFocus()
            debug_print("  [FOCUS] Set focus to WorkflowView on item click")

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events for line dragging and view panning."""
        if self.is_dragging_line:
            scene_pos = self.mapToScene(event.pos())
            self.update_drag_line(scene_pos)
        else:
            super().mouseMoveEvent(event)  # Handle panning or item dragging

    def mouseReleaseEvent(self, event: QMouseEvent):
        # --- SIMPLIFIED: Remove specific right-click handling and drag mode restore --- 
        # if self._right_mouse_pressed and event.button() == Qt.MouseButton.RightButton:
        #     debug_print("  [DEBUG] WorkflowView: Right mouse button released.") # DEBUG
        #     # --- MODIFIED: Ensure restoring to ScrollHandDrag as a fallback ---
        #     restore_mode = self._original_drag_mode if self._original_drag_mode is not None else QGraphicsView.DragMode.ScrollHandDrag
        #     self.setDragMode(restore_mode)
        #     debug_print(f"  [DEBUG] WorkflowView: Restored drag mode to {restore_mode}.") # DEBUG
        #     # ----------------------------------------------------------------
        #     self._right_mouse_pressed = False
        #     # Call super() to ensure base class release logic runs
        #     super().mouseReleaseEvent(event)
        #     debug_print("  [DEBUG] WorkflowView: Called super().mouseReleaseEvent for right-click.") # DEBUG
        if self.is_dragging_line:
            scene_pos = self.mapToScene(event.pos())
            self.end_drag_line(scene_pos)
        else:
            # Handle normal release (e.g., end panning or rubber band selection)
            super().mouseReleaseEvent(event)

            # 如果当前是框选模式，释放后恢复到平移模式
            if self.dragMode() == QGraphicsView.DragMode.RubberBandDrag:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                debug_print("  [MULTI_SELECT] Restored drag mode to ScrollHandDrag after rubber band selection")
        # ----------------------------------------------------------------------------
            
    def clear_workflow(self):
        """Removes all cards and connections from the scene using scene.clear()."""
        # --- 任务运行安全检查 ---
        try:
            main_window = None
            # 从父级查找MainWindow
            try:
                parent = self.parent()
                # 工具 用户要求：删除无限循环限制，但保留合理的查找限制防止真正的死循环
                loop_count = 0
                max_loops = 100  # 增加查找层数限制，从50增加到100
                while parent and not hasattr(parent, 'executor') and loop_count < max_loops:
                    parent = parent.parent()
                    loop_count += 1
                if loop_count >= max_loops:
                    logger.warning("查找MainWindow时达到最大循环次数限制")
                    parent = None
                main_window = parent
            except Exception as e:
                logger.debug(f"从父级查找MainWindow失败: {e}")
            
            # 如果没找到，从QApplication查找
            if not main_window:
                try:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        for widget in app.allWidgets():
                            if hasattr(widget, 'executor') and hasattr(widget, 'executor_thread'):
                                main_window = widget
                                break
                except Exception as e:
                    logger.debug(f"从QApplication查找MainWindow失败: {e}")
            
            # 检查是否有任务正在运行
            if main_window and hasattr(main_window, 'executor') and hasattr(main_window, 'executor_thread'):
                if (main_window.executor is not None and 
                    main_window.executor_thread is not None and 
                    main_window.executor_thread.isRunning()):
                    
                    logger.warning("尝试在任务运行期间清空工作流")
                    from PySide6.QtWidgets import QMessageBox
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
                        if hasattr(main_window, 'request_stop_workflow'):
                            main_window.request_stop_workflow()
                        QMessageBox.information(
                            self, 
                            "操作说明", 
                            "已发送停止请求。请等待任务停止后再次尝试清空工作流。"
                        )
                        return
                    elif reply == QMessageBox.StandardButton.No:
                        # 用户选择强制清空
                        logger.warning("用户选择在任务运行期间强制清空工作流")
                        pass  # 继续执行清空操作
                    else:
                        # 用户取消操作
                        logger.info("用户取消了清空工作流操作")
                        return
                        
        except Exception as e:
            logger.error(f"检查任务运行状态时发生错误: {e}")
            # 出错时允许继续，但记录警告
            logger.warning("由于检查失败，按传统方式执行清空操作")
        # --- 结束任务运行安全检查 ---
        
        # <<< ENHANCED: 清理前验证连接状态 >>>
        logger.debug("清理工作流前验证连接状态...")
        self.validate_connections()
        self.cleanup_orphaned_connections()
        # <<< END ENHANCED >>>
        
        # Use scene.clear() for a more robust way to remove all items
        self.scene.clear() 
        
        # Reset internal state
        self.cards.clear()
        self.connections.clear()
        self._next_card_id = 0
        self._max_loaded_id = -1

        # 清空撤销栈
        old_undo_size = len(self.undo_stack)
        self.undo_stack.clear()
        if old_undo_size > 0:
            debug_print(f"  [UNDO] Cleared undo stack during workflow clear (had {old_undo_size} operations)")
            logger.info(f"  [UNDO] Cleared undo stack during workflow clear (had {old_undo_size} operations)")

        # 只在非加载状态下重置加载工作流标志
        # 如果正在加载工作流，保持标志状态，让加载完成后再重置
        if not self._loading_workflow:
            debug_print(f"  [UNDO] Not loading workflow, keeping flag as False")
            logger.info(f"  [UNDO] Not loading workflow, keeping flag as False")
        else:
            debug_print(f"  [UNDO] Loading workflow in progress, keeping flag as True")
            logger.info(f"  [UNDO] Loading workflow in progress, keeping flag as True")

        logger.info("Workflow cleared.")
        # --- MODIFIED: Only update if needed (clearing usually means no cards left) ---
        # self.update_card_sequence_display() # <<< REMOVED (No cards to update)
        # ---------------------------------------------------------------------------
        # Remove automatic fit view after clearing
        # self.fit_view_to_items()

    def show_context_menu(self, pos: QPointF):
        """Shows a context menu at the given view position provided by the signal."""
        # --- CORRECTED: Use the signal's QPoint 'pos' directly --- 
        scene_pos = self.mapToScene(pos) # mapToScene accepts QPoint
        # ----------------------------------------------------------

        # --- REMOVED: No longer rely on manually stored _last_right_click_view_pos_f ---
        # ... (removed commented out block) ...
        # -----------------------------------------------------------------------------

        item = self.itemAt(pos) # itemAt uses QPoint
        debug_print(f"\n--- [DEBUG] WorkflowView.show_context_menu --- ") # DEBUG
        debug_print(f"  [DEBUG] Signal click position (view): {pos}") # DEBUG
        debug_print(f"  [DEBUG] Calculated click position (scene): {scene_pos}") # DEBUG
        debug_print(f"  [DEBUG] Item at position: {type(item).__name__}") # DEBUG
        if item:
             # Try accessing attributes common to QGraphicsItem or specific ones
             if isinstance(item, TaskCard):
                  debug_print(f"  [DEBUG] Item is TaskCard with ID: {item.card_id}, Type: {item.task_type}") # DEBUG
             elif isinstance(item, ConnectionLine):
                  debug_print(f"  [DEBUG] Item is ConnectionLine") # DEBUG
             else:
                  debug_print(f"  [DEBUG] Item exists but is not TaskCard or ConnectionLine.") # DEBUG

        menu = QMenu(self)

        # --- 使用主题系统设置菜单样式 --- 
        try:
            from ui.theme import ThemeManager
            theme_mode = ThemeManager.instance().get_current_mode()
            from ui.theme.fluent_colors import FluentColors
            colors = FluentColors.get_palette(theme_mode)
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
        # -------------------------------------------------------------------------------

        # --- Restore logic to handle clicks on items OR background --- 
        if isinstance(item, TaskCard):
            # --- Card Context Menu ---
            debug_print(f"  [DEBUG] Creating context menu for TaskCard {item.card_id}.") # DEBUG
            
            # 检查任务是否正在运行，如果是则禁用编辑选项
            is_running = self._is_workflow_running()
            
            settings_action = menu.addAction("参数设置")
            settings_action.setEnabled(not is_running)
            if is_running:
                settings_action.setToolTip("工作流运行期间无法修改参数")
            
            menu.addSeparator()

            # 添加备注名称选项
            rename_action = menu.addAction("备注卡片名称")
            rename_action.setEnabled(not is_running)
            if is_running:
                rename_action.setToolTip("工作流运行期间无法修改备注")

            # 添加修改ID选项
            change_id_action = menu.addAction("修改卡片ID")
            change_id_action.setEnabled(not is_running)
            if is_running:
                change_id_action.setToolTip("工作流运行期间无法修改ID")

            menu.addSeparator()

            copy_action = menu.addAction("复制卡片")
            copy_action.setEnabled(not is_running)
            if is_running:
                copy_action.setToolTip("工作流运行期间无法复制卡片")

            delete_action = menu.addAction("删除卡片")
            delete_action.setEnabled(not is_running)
            if is_running:
                delete_action.setToolTip("工作流运行期间无法删除卡片")
            
            debug_print(f"  [DEBUG] Executing card menu...") # DEBUG
            action = menu.exec(self.mapToGlobal(pos))
            debug_print(f"  [DEBUG] Card menu finished. Selected action: {action.text() if action else 'None'}") # DEBUG

            if action == settings_action:
                debug_print(f"  [DEBUG] '参数设置' action selected for card {item.card_id}.") # DEBUG
                if hasattr(item, 'open_parameter_dialog') and callable(item.open_parameter_dialog):
                    debug_print(f"  [DEBUG] Calling item.open_parameter_dialog()...") # DEBUG
                    item.open_parameter_dialog()
                    debug_print(f"  [DEBUG] Returned from item.open_parameter_dialog().") # DEBUG
                else:
                    debug_print(f"  [DEBUG] ERROR: item {item.card_id} does not have a callable open_parameter_dialog method!") # DEBUG
                    QMessageBox.warning(self, "错误", f"任务卡片 '{item.title}' 缺少参数设置功能。")
            elif action == rename_action:
                debug_print(f"  [DEBUG] '备注卡片名称' action selected for card {item.card_id}.") # DEBUG
                self.handle_rename_card(item)
            elif action == change_id_action:
                debug_print(f"  [DEBUG] '修改卡片ID' action selected for card {item.card_id}.") # DEBUG
                self.handle_change_card_id(item)
            elif action == copy_action:
                debug_print(f"  [DEBUG] '复制卡片' action selected.") # DEBUG
                item.copy_card()
            elif action == delete_action:
                # <<< MODIFIED: Call the central delete_card method >>>
                debug_print(f"  [DEBUG] '删除卡片' action selected for card {item.card_id}. Calling self.delete_card...")
                self.delete_card(item.card_id)
                # --- REMOVED manual cleanup code --- 
                # card_to_delete = item
                # debug_print(f"  [DEBUG] '删除卡片' action selected for card {card_to_delete.card_id}.") # DEBUG
                # # --- ADDED: Also check connections during card deletion ---
                # for conn in list(card_to_delete.connections): # Iterate over a copy
                #     self.remove_connection(conn) # Use the modified remove_connection logic
                #     # --- REMOVED redundant logic now handled by remove_connection ---
                #     # self.scene.removeItem(conn)
                #     # other_card = conn.start_item if conn.end_item == card_to_delete else conn.end_item
                #     # if other_card and hasattr(other_card, 'remove_connection'):
                #     #     other_card.remove_connection(conn)
                #     # ----------------------------------------------------------
                # self.scene.removeItem(card_to_delete)
                # if card_to_delete.card_id in self.cards:
                #     del self.cards[card_to_delete.card_id]
                # debug_print(f"卡片 {card_to_delete.card_id} 已删除")
                # --- END REMOVED manual cleanup code ---

        elif isinstance(item, ConnectionLine):
             # --- Connection Context Menu --- 
            debug_print(f"  [DEBUG] Creating context menu for ConnectionLine.") # DEBUG
            delete_conn_action = menu.addAction("删除连接")
            action = menu.exec(self.mapToGlobal(pos))
            if action == delete_conn_action:
                conn_to_delete = item # Keep reference
                debug_print(f"  [DEBUG] '删除连接' (context menu) action selected for {conn_to_delete}. Calling self.remove_connection...") # DEBUG (Fixed string escaping)
                # remove_connection will trigger update_card_sequence_display if needed
                self.remove_connection(conn_to_delete) # <-- Use the centralized method
                debug_print("连接已通过 remove_connection 删除。") # DEBUG

        elif item is None: # Explicitly check for None for background
            # --- View Context Menu --- 
            debug_print("  [DEBUG] Clicked on background. Showing view context menu.") # DEBUG
            
            # 检查任务是否正在运行，如果是则禁用编辑选项
            is_running = self._is_workflow_running()
            
            add_card_action = menu.addAction("添加步骤")
            add_card_action.setEnabled(not is_running)
            if is_running:
                add_card_action.setToolTip("工作流运行期间无法添加步骤")
            
            # --- Corrected Paste Action --- 
            paste_action = menu.addAction("粘贴卡片")
            # Use lambda to pass the correct scene_pos where the menu was requested
            paste_action.triggered.connect(lambda: self.handle_paste_card(scene_pos)) 
            # --- ADDED: Set enabled state based on clipboard and running status --- 
            can_paste = self.is_paste_available() and not is_running
            paste_action.setEnabled(can_paste)
            if is_running:
                paste_action.setToolTip("工作流运行期间无法粘贴卡片")
            elif not self.is_paste_available():
                paste_action.setToolTip("剪贴板中没有可粘贴的卡片数据")

            # 添加撤销选项
            undo_action = menu.addAction("撤销 (Ctrl+Z)")
            can_undo = self.can_undo()
            undo_action.setEnabled(can_undo)
            if is_running:
                undo_action.setToolTip("工作流运行期间无法撤销")
            elif not can_undo:
                undo_action.setToolTip("没有可撤销的操作")
            # ---------------------------------------------------
            menu.addSeparator()

            save_action = menu.addAction("保存工作流")

            menu.addSeparator()
            fit_view_action = menu.addAction("适应视图")

            # --- REMOVED: Auto Arrange Action ---
            # (Code was already removed in previous step)
            # -------------------------------------

            action = menu.exec(self.mapToGlobal(pos))

            if action == add_card_action:
                self.prompt_and_add_card_at(scene_pos) # <-- RESTORED: Call original function
            elif action == save_action:
                # Need access to main window or a way to trigger save from there
                logger.warning("保存工作流功能应由主窗口处理。")
            elif action == undo_action:
                self.undo_last_operation()
            elif action == fit_view_action:
                 self.fit_view_to_items()
        else: # Should not be reached if item is not None, Card, or Line
            debug_print(f"  [DEBUG] Clicked on unhandled item type ({type(item).__name__}), no menu shown.") # DEBUG

    def prompt_and_add_card_at(self, scene_pos: QPointF):
        """Opens the custom task selection dialog and adds the selected card."""
        # Import the function to get primary task types for UI display
        from tasks import get_available_tasks
        task_types = get_available_tasks()
        if not task_types:
            QMessageBox.warning(self, "错误", "没有可用的任务类型！")
            return

        # Use the custom dialog instead of QInputDialog
        dialog = SelectTaskDialog(task_types, self) # Pass self as parent
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            task_type = dialog.selected_task_type()
            if task_type:
                # Add the card (won't trigger update by itself)
                new_card = self.add_task_card(scene_pos.x(), scene_pos.y(), task_type=task_type)
                # Manually trigger update after adding card via context menu
                if new_card:
                    debug_print("  [CONTEXT_ADD_DEBUG] Card added via context menu, triggering sequence update.")
                    # self.update_card_sequence_display() # <<< REMOVED Direct Call
                    # QTimer.singleShot(0, self.update_card_sequence_display) # <<< REMOVED Deferred Call
                    self.update_card_sequence_display() # <<< RESTORED Direct Call
                    debug_print(f"  Direct sequence update called after adding card via context menu.")
            else:
                 debug_print("警告：选择的任务类型为空。") # Should not happen if list is populated
        # else: User cancelled (Rejected)

    def serialize_workflow(self) -> Dict[str, Any]:
        """Serializes the current workflow (cards, connections, view state) into a dictionary."""
        workflow_data = {
            "cards": [],
            "connections": [],
            "view_transform": [],
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "engine_version": "1.0.0",  # 当前引擎版本
                "module_versions": {}       # 记录使用的模块版本
            }
        }

        # Serialize cards
        for card_id, card in self.cards.items():
            debug_print(f"--- [DEBUG] Saving Card ID: {card_id}, Type: {card.task_type} ---") # DEBUG
            # --- ADDED: Specific log for Start Card (ID 0) --- 
            if card_id == 0:
                debug_print(f"    [SAVE_DEBUG] Parameters for Start Card (ID 0) before saving: {card.parameters}")
            # --- END ADDED ---
            debug_print(f"  Parameters to be saved: {card.parameters}") # <<< ADDED DEBUG PRINT
            card_data = {
                "id": card_id,
                "task_type": card.task_type, # <<< CHANGED FROM 'type' TO 'task_type'
                # --- UNIFIED: Save using 'pos_x' and 'pos_y' ---
                "pos_x": card.x(), # <<< CHANGED FROM 'x' TO 'pos_x'
                "pos_y": card.y(), # <<< CHANGED FROM 'y' TO 'pos_y'
                # --- END UNIFICATION ---
                "parameters": card.parameters.copy(), # Assuming parameters are serializable
                "custom_name": card.custom_name # 保存自定义名称
            }

            workflow_data["cards"].append(card_data)

        # Serialize connections
        # --- MODIFIED: Only save SEQUENTIAL connections --- 
        debug_print(f"  [SAVE_DEBUG] Serializing connections...")
        for item in self.scene.items():
            if isinstance(item, ConnectionLine) and item.line_type == 'sequential':
                # Ensure start/end items are valid TaskCards before accessing card_id
                if isinstance(item.start_item, TaskCard) and isinstance(item.end_item, TaskCard):
                    conn_data = {
                        "start_card_id": item.start_item.card_id, # Still use internal card_id for identifying endpoints
                        "end_card_id": item.end_item.card_id,
                        "type": item.line_type # <<< CHANGED KEY from 'line_type' to 'type'
                    }
                    workflow_data["connections"].append(conn_data)
                    debug_print(f"    [SAVE_DEBUG] Saved sequential connection: {item.start_item.card_id} -> {item.end_item.card_id} (using key 'type')") # Updated log
                else:
                    debug_print(f"    [SAVE_DEBUG] WARNING: Skipping invalid sequential connection during save: {item}")
            elif isinstance(item, ConnectionLine):
                 debug_print(f"    [SAVE_DEBUG] Skipping non-sequential connection (Type: {item.line_type}) during save.")
        debug_print(f"  [SAVE_DEBUG] Finished serializing connections. Saved {len(workflow_data['connections'])} sequential lines.")
        # --- END MODIFICATION ---
                
        # Serialize view transform
        transform = self.transform()
        workflow_data["view_transform"] = [
            transform.m11(), transform.m12(), transform.m13(), # m13 usually 0
            transform.m21(), transform.m22(), transform.m23(), # m23 usually 0
            transform.m31(), transform.m32(), transform.m33()  # m31=dx, m32=dy, m33 usually 1
        ]
        # --- ADDED: Debug log for saved transform data ---
        debug_print(f"  [SAVE_DEBUG] Serialized view_transform: {workflow_data['view_transform']}")
        # --- END ADDED ---

        # --- ADDED: Serialize view center point ---
        viewport_center_view = self.viewport().rect().center()
        scene_center_point = self.mapToScene(viewport_center_view)
        workflow_data["view_center"] = [scene_center_point.x(), scene_center_point.y()]
        debug_print(f"  [SAVE_DEBUG] Serialized view_center: {workflow_data['view_center']}")
        # --- END ADDED ---

        logger.info(f"序列化完成：找到 {len(workflow_data['cards'])} 个卡片，{len(workflow_data['connections'])} 个连接。")
        return workflow_data

    def save_workflow(self, filepath: str):
        """DEPRECATED: Logic moved to MainWindow. Use serialize_workflow instead."""
        # This method is likely no longer needed here as MainWindow handles saving.
        # Keep it stubbed or remove it if confirmed unused.
        logger.warning("WorkflowView.save_workflow is deprecated and should not be called.")
        pass
        # workflow_data = self.serialize_workflow()
        # try:
        #     with open(filepath, 'w', encoding='utf-8') as f:
        #         json.dump(workflow_data, f, indent=4, ensure_ascii=False)
        #     debug_print(f"工作流已保存到: {filepath}")
        # except Exception as e:
        #     QMessageBox.critical(self, "保存失败", f"无法保存工作流到 '{filepath}':\n{e}")
        #     debug_print(f"错误: 保存工作流失败 - {e}")

    # <<< MODIFIED: Changed signature to accept data dictionary >>>
    def load_workflow(self, workflow_data: Dict[str, Any]):
        """Loads a workflow from the provided data dictionary."""
        # <<< REMOVED: Ensure all file reading logic is gone >>>
        # (Removed the commented-out try/except block that contained `open(filepath,...)`)
        # -------------------------------------

        logger.info(f"WorkflowView: 开始从数据字典加载工作流...")

        # 设置加载工作流标志，防止连接删除时保存撤销状态
        self._loading_workflow = True

        # Clear existing workflow
        self.clear_workflow()

        # 检查是否为模块文件格式
        if 'workflow' in workflow_data and 'cards' not in workflow_data:
            # 这是模块文件格式，提取workflow部分
            actual_workflow = workflow_data['workflow']
            module_info = workflow_data.get('module_info', {})
            logger.info(f"检测到模块文件格式，提取workflow数据: {module_info.get('name', '未知模块')}")
        else:
            # 这是标准工作流格式
            actual_workflow = workflow_data

        # 验证workflow数据完整性
        if not isinstance(actual_workflow, dict):
            logger.error("工作流数据格式错误：不是字典类型")
            return

        if 'cards' not in actual_workflow:
            logger.error("工作流数据缺少cards字段")
            actual_workflow['cards'] = []

        if 'connections' not in actual_workflow:
            logger.warning("工作流数据缺少connections字段，使用空列表")
            actual_workflow['connections'] = []

        # Load Cards from the extracted list
        for card_data in actual_workflow['cards']:
            logger.debug(f"DEBUG [load_workflow]: LOOP START for card data: {card_data}") # Keep this debug log
            try:
                # Call add_task_card
                # --- RE-APPLYING CORRECTION: Use correct keys 'x', 'y', and USE 'task_type' --- 
                card_type_from_json = card_data.get('task_type', '未知') # <<< CHANGED FROM 'type' TO 'task_type'
                logger.debug(f"DEBUG [load_workflow]: Extracted task_type='{card_type_from_json}' (using key 'task_type')") # Updated log
                card = self.add_task_card(
                    # --- FINAL CORRECTION: Read 'pos_x' and 'pos_y' based on JSON analysis --- 
                    x=card_data.get('pos_x', 0), # <<< Use 'pos_x'
                    y=card_data.get('pos_y', 0), # <<< Use 'pos_y'
                    # --- END CORRECTION ---
                    task_type=card_type_from_json, # Pass the extracted type
                    card_id=card_data.get('id')
                )
                # --- END CORRECTION ---
                logger.debug(f"DEBUG [load_workflow]: Returned from add_task_card. Card object: {card}") # Keep this debug log

                # --- Parameter Merging (Now directly after card creation) ---
                debug_print(f"DEBUG [load_workflow]: Processing card data for merge: {card_data}")
                if card and "parameters" in card_data and card_data["parameters"] is not None:
                    debug_print(f"DEBUG [load_workflow]: Starting parameter merge for card {card.card_id}")
                    loaded_params = card_data["parameters"]
                    debug_print(f"  [LOAD_DEBUG] Loaded params from JSON: {loaded_params}")
                    current_params = card.parameters.copy()
                    debug_print(f"  [LOAD_DEBUG] Default params from card before merge: {current_params}")
                    # --- REVISED Merge Loop: Handle card_selector parsing --- 
                    for key, loaded_value in loaded_params.items():
                        # Get parameter definition to check for hints
                        param_def_for_key = card.param_definitions.get(key, {}) 
                        widget_hint = param_def_for_key.get('widget_hint')

                        if widget_hint == 'card_selector':
                            # Attempt to parse Card ID from string like "Task Type (ID: 123)"
                            parsed_id = None
                            if isinstance(loaded_value, str):
                                match = re.search(r'\(ID:\s*(\d+)\)', loaded_value)
                                if match:
                                    try:
                                        parsed_id = int(match.group(1))
                                        debug_print(f"    [LOAD_DEBUG] Parsed Card ID {parsed_id} from '{loaded_value}' for key '{key}'.")
                                    except ValueError:
                                        debug_print(f"    [LOAD_DEBUG] WARNING: Could not convert parsed ID '{match.group(1)}' to int for key '{key}'. Setting to None.")
                                elif loaded_value.strip().lower() == 'none' or loaded_value.strip() == "默认 (蓝色连线)": # Handle explicit None/Default strings
                                    debug_print(f"    [LOAD_DEBUG] Loaded value for '{key}' indicates None/Default ('{loaded_value}'). Setting target ID to None.")
                                    parsed_id = None
                                else:
                                    debug_print(f"    [LOAD_DEBUG] WARNING: Could not parse Card ID from string '{loaded_value}' for key '{key}'. Setting to None.")
                            elif isinstance(loaded_value, int):
                                parsed_id = loaded_value
                                debug_print(f"    [LOAD_DEBUG] Loaded value for '{key}' is already an integer: {parsed_id}.")
                            elif loaded_value is None:
                                debug_print(f"    [LOAD_DEBUG] Loaded value for '{key}' is None.")
                                parsed_id = None
                            else:
                                debug_print(f"    [LOAD_DEBUG] WARNING: Unexpected type {type(loaded_value)} ('{loaded_value}') for card selector '{key}'. Setting to None.")
                            
                            # Store the parsed ID (or None)
                            current_params[key] = parsed_id
                            debug_print(f"    [LOAD_DEBUG] Merging PARSED ID: '{key}' = {current_params[key]}")

                        elif loaded_value is not None: # Keep original logic for non-card selectors
                            debug_print(f"    [LOAD_DEBUG] Merging STANDARD value: '{key}' = {loaded_value} (Type: {type(loaded_value)}) -> Overwriting default: {current_params.get(key)}")
                            current_params[key] = loaded_value
                        else: # loaded_value is None for non-card selectors
                            debug_print(f"    [LOAD_DEBUG] Skipping merge for key '{key}' because loaded value is None (standard param).")
                    # --- END REVISED Merge Loop ---
                    card.parameters = current_params
                    debug_print(f"  [LOAD_DEBUG] Final card parameters after merge: {card.parameters}")

                # --- 恢复自定义名称 ---
                if card and "custom_name" in card_data:
                    custom_name = card_data["custom_name"]
                    if custom_name:
                        card.set_custom_name(custom_name)
                        debug_print(f"  [LOAD_DEBUG] 恢复卡片 {card.card_id} 的自定义名称: '{custom_name}'")
                    else:
                        debug_print(f"  [LOAD_DEBUG] 卡片 {card.card_id} 无自定义名称")

                debug_print(f"DEBUG [load_workflow]: Reached end of try block for card {card.card_id if card else 'N/A'}")

            except Exception as e:
                debug_print(f"--- ERROR DURING CARD LOAD LOOP (Card Data: {card_data}) ---")
                # --- ADDED: More detailed exception info --- 
                debug_print(f"  Exception Type: {type(e)}")
                debug_print(f"  Exception Repr: {repr(e)}")
                # --- END ADDED ---
                import traceback
                debug_print("  Traceback:")
                traceback.print_exc() # Ensure traceback is printed
                # --- MODIFIED: Explicitly convert exception to string --- 
                error_message = str(e)
                debug_print(f"警告：加载卡片时发生错误: {error_message}")
                # --- MODIFIED: Create QMessageBox instance and style directly ---
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("加载警告")
                msg_box.setText(f"加载卡片时发生错误: {error_message}\n请查看控制台日志获取详细信息。")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                
                # 设置按钮中文文本
                ok_button = msg_box.button(QMessageBox.StandardButton.Ok)
                if ok_button: ok_button.setText("确定")
                
                # Apply the modern stylesheet
                msg_box.setStyleSheet("""
                    QMessageBox { background-color: #ffffff; border: none; border-radius: 8px; padding: 15px; }
                    QLabel#qt_msgbox_label { color: #333333; background-color: transparent; font-size: 11pt; }
                    QLabel#qt_msgboxex_icon_label { padding-right: 10px; }
                    QPushButton { background-color: #0078d7; border: none; padding: 8px 20px; border-radius: 4px; min-width: 70px; color: white; font-size: 10pt; }
                    QPushButton:hover { background-color: #0056b3; }
                    QPushButton:pressed { background-color: #004085; }
                """)
                msg_box.exec()
                # -----------------------------------------------------------------
                # --- END MODIFICATION ---

        debug_print(f"DEBUG [load_workflow]: Card creation loop finished.")

        # --- Restore Connection Loading (using extracted list) ---
        debug_print(f"DEBUG [load_workflow]: Starting connection loading ({len(actual_workflow['connections'])} connections).")
        if actual_workflow['connections']:
            for conn_data in actual_workflow['connections']:
                try:
                    start_card_id = conn_data.get('start_card_id') # <-- Get IDs first
                    end_card_id = conn_data.get('end_card_id')
                    start_card = self.cards.get(start_card_id)
                    end_card = self.cards.get(end_card_id)
                    # --- CORRECTED: Key is 'type' in JSON, not 'line_type' ---
                    line_type = conn_data.get('type') # <<< CORRECTED KEY
                    # ---------------------------------------------------------

                    # Check if cards exist and line_type is valid before proceeding
                    if start_card and end_card and line_type: # <<< Now line_type should be correct
                        # --- CORRECTED: ONLY load SEQUENTIAL here. Jump lines are rebuilt later. ---
                        should_add_connection = True
                        if line_type != 'sequential': # <<< Now this comparison works
                             debug_print(f"[LOAD_INFO] Skipping non-sequential line type '{line_type}' from JSON (ID: {start_card_id} -> {end_card_id}). Will be rebuilt by update_card_sequence_display.")
                             should_add_connection = False
                        # --------------------------------------------------------------------------

                        if should_add_connection: # <<< Should now be true for sequential lines
                             debug_print(f"  [LOAD_DEBUG] Adding SEQUENTIAL connection: {start_card_id} -> {end_card_id}, Type: {line_type}")
                             # Call add_connection (which now does NOT trigger update)
                             self.add_connection(start_card, end_card, line_type) 
                        # No else needed, already printed skip message
                    else:
                        # More specific warning
                        warning_reason = []
                        if not start_card: warning_reason.append(f"start_card_id {start_card_id} not found")
                        if not end_card: warning_reason.append(f"end_card_id {end_card_id} not found")
                        if not line_type: warning_reason.append("line_type missing") # Should no longer happen if 'type' exists
                        debug_print(f"警告：恢复连接时跳过无效数据 ({conn_data}): {', '.join(warning_reason)}")
                except Exception as e:
                    debug_print(f"警告：恢复连接时发生错误 ({conn_data}): {e}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.warning(self, "加载警告", f"恢复连接时发生错误: {e}")

        # --- 验证和清理无效的跳转参数 ---
        debug_print(f"DEBUG [load_workflow]: Validating jump target parameters...")
        self._validate_and_cleanup_jump_targets()

        # --- Call final update AFTER processing cards and SEQUENTIAL connections from JSON ---
        # This will calculate sequence IDs AND rebuild JUMP connections based on parameters.
        debug_print(f"DEBUG [load_workflow]: Finished loading cards and sequential connections from JSON. Calling final update_card_sequence_display...") # <<< LOG BEFORE
        self.update_card_sequence_display() # <<< RESTORED Direct Call
        debug_print(f"  Direct final sequence update called after loading workflow.")

        # --- Final Update (REBUILDS JUMP CONNECTIONS and Numbers) ---
        # This needs to happen AFTER cards are loaded and sequential connections potentially added
        # But BEFORE view is potentially centered/zoomed based on saved state.
        debug_print(f"DEBUG [load_workflow]: Calling final update_card_sequence_display...")
        self.update_card_sequence_display() 
        debug_print(f"DEBUG [load_workflow]: Finished final update_card_sequence_display.")

        # --- ADDED: Explicitly set sceneRect before restoring view --- 
        try:
            if self.scene.items():
                items_rect = self.scene.itemsBoundingRect()
                # Add generous padding to ensure center target is well within bounds
                padded_rect = items_rect.adjusted(-FIT_VIEW_PADDING * 2, -FIT_VIEW_PADDING * 2,
                                                FIT_VIEW_PADDING * 2, FIT_VIEW_PADDING * 2)
                debug_print(f"  [LOAD_DEBUG] Calculated items bounding rect (padded): {padded_rect}")
                self.scene.setSceneRect(padded_rect)
                debug_print(f"  [LOAD_DEBUG] Set sceneRect to encompass all items before view restore.")
            else:
                debug_print("  [LOAD_DEBUG] No items found, skipping sceneRect adjustment before view restore.")
        except Exception as e_sr:
            debug_print(f"  [LOAD_DEBUG] Error calculating/setting sceneRect before view restore: {e_sr}")
        # --- END ADDED ---

        # --- View restoration block (already moved to the end) ---
        debug_print(f"DEBUG [load_workflow]: Attempting to restore view transform and center (at the end)...")
        try:
            view_transform_data = workflow_data.get('view_transform') 
            debug_print(f"  [LOAD_DEBUG] Raw view_transform data from file: {view_transform_data}")
            data_exists = bool(view_transform_data)
            is_list = isinstance(view_transform_data, list)
            correct_length = len(view_transform_data) == 9 if is_list else False
            debug_print(f"  [LOAD_DEBUG] Condition checks: Exists={data_exists}, IsList={is_list}, LengthIs9={correct_length}")
            transform_restored = False
            if data_exists and is_list and correct_length:
                saved_transform = QTransform(
                    view_transform_data[0], view_transform_data[1], 0,
                    view_transform_data[3], view_transform_data[4], 0,
                    view_transform_data[6], view_transform_data[7], 1
                )
                self.setTransform(saved_transform)
                transform_restored = True
                debug_print("视图变换 (缩放/平移基点) 已恢复。")

                view_center_data = workflow_data.get('view_center')
                debug_print(f"  [LOAD_DEBUG] Raw view_center data from file: {view_center_data}")
                if isinstance(view_center_data, list) and len(view_center_data) == 2:
                    try:
                        saved_center_point = QPointF(view_center_data[0], view_center_data[1])
                        QTimer.singleShot(100, lambda p=saved_center_point: self._deferred_center_view(p))
                        debug_print(f"  [LOAD_DEBUG] Scheduling deferred centering on {saved_center_point}.")
                    except ValueError as center_val_e:
                        logger.warning(f"无法创建中心点 QPointF: {center_val_e}")
                    except Exception as center_e:
                        logger.warning(f"加载视图中心时出错: {center_e}")
                else:
                     logger.warning(f"无法恢复视图中心，数据无效: {view_center_data}")
            else:
                logger.info("未从文件恢复视图变换。") # No valid transform data found

  
        except Exception as e:
            debug_print(f"警告: 恢复视图变换或中心时出错: {e}")
            # --- END ADDED Block ---

        # <<< CORRECTED INDENTATION: Moved INSIDE the main try block >>>
        logger.info(f"工作流已从数据字典加载完成。卡片数: {len(self.cards)}, 连接数: {len(self.connections)}")

        # <<< ENHANCED: 加载完成后验证连接完整性 >>>
        logger.info("验证加载后的连接完整性...")
        invalid_count = self.validate_connections()
        orphaned_count = self.cleanup_orphaned_connections()

        if invalid_count > 0 or orphaned_count > 0:
            logger.info(f"加载后连接清理完成：无效连接 {invalid_count} 个，孤立连接 {orphaned_count} 个")
        else:
            logger.info("加载后连接验证通过，所有连接完整有效")
        # <<< END ENHANCED >>>

        # 无论是否有异常，都要确保清除加载工作流标志
        # 清除加载工作流标志
        self._loading_workflow = False
        debug_print(f"  [UNDO] Cleared loading workflow flag")
        logger.info(f"  [UNDO] Cleared loading workflow flag")


    def fit_view_to_items(self):
        """Adjusts the view to fit all items in the scene with padding."""
        if self.scene.items(): # Only fit if there are items
            items_rect = self.scene.itemsBoundingRect()
            # Add padding
            padded_rect = items_rect.adjusted(-FIT_VIEW_PADDING, -FIT_VIEW_PADDING, 
                                                FIT_VIEW_PADDING, FIT_VIEW_PADDING)
            self.fitInView(padded_rect, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            # Optional: Reset view if scene is empty?
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio) # Fit to initial rect or default
            pass

    # --- ADDED: Method to center view deferred ---
    def _deferred_center_view(self, center_point: QPointF):
        """Deferred function to center the view."""
        debug_print(f"  [LOAD_DEBUG] Entering DEFERRED center function. Target: {center_point}.") # Log entry
        # --- Log BEFORE centerOn --- 
        try:
            pre_center_vp_center = self.viewport().rect().center()
            pre_center_scene_center = self.mapToScene(pre_center_vp_center)
            debug_print(f"  [LOAD_DEBUG] Center BEFORE centerOn call: {pre_center_scene_center}")
        except Exception as pre_e:
            debug_print(f"  [LOAD_DEBUG] Error getting center BEFORE call: {pre_e}")
        # --- END Log BEFORE ---

        try:
            # --- ADDED: Force scene update before centering ---
            debug_print(f"  [LOAD_DEBUG] Calling self.scene.update() before centerOn.")
            self.scene.update()
            QApplication.processEvents() # Also process events after update, before centerOn
            debug_print(f"  [LOAD_DEBUG] Finished scene update and processEvents.")
            # --- END ADDED ---

            self.centerOn(center_point)
            # --- Log IMMEDIATELY AFTER centerOn (BEFORE processEvents) ---
            try:
                post_center_vp_center = self.viewport().rect().center()
                post_center_scene_center = self.mapToScene(post_center_vp_center)
                debug_print(f"  [LOAD_DEBUG] Center IMMEDIATELY AFTER centerOn call: {post_center_scene_center}")
            except Exception as post_e:
                debug_print(f"  [LOAD_DEBUG] Error getting center IMMEDIATELY AFTER call: {post_e}")
            # --- END Log AFTER ---

            # --- Verify actual center point AFTER deferred centerOn AND processEvents --- 
            debug_print(f"  [LOAD_DEBUG] Calling processEvents...")
            QApplication.processEvents() # Try processing pending events again
            debug_print(f"  [LOAD_DEBUG] Finished processEvents.")
            current_viewport_center_view = self.viewport().rect().center()
            actual_scene_center = self.mapToScene(current_viewport_center_view)
            debug_print(f"  [LOAD_DEBUG] VERIFY (Deferred - AFTER processEvents): Actual scene center: {actual_scene_center}")
        except Exception as deferred_center_e:
             logger.error(f"Error during deferred centerOn or verification: {deferred_center_e}", exc_info=True)
    # --- END ADDED --- 

    # --- ADDED: Logging for resizeEvent ---
    def resizeEvent(self, event: QResizeEvent):
        """Logs the view center when the view is resized."""
        super().resizeEvent(event) # Call base implementation first
        try:
            center_point = self.mapToScene(self.viewport().rect().center())
            debug_print(f"  [VIEW_DEBUG] resizeEvent: Current scene center = {center_point}")
        except Exception as e:
            debug_print(f"  [VIEW_DEBUG] resizeEvent: Error getting center point: {e}")
    # --- END ADDED ---

    # --- ADDED: Logging for showEvent ---
    def showEvent(self, event: QShowEvent):
        """Logs the view center when the view is shown."""
        super().showEvent(event) # Call base implementation first
        try:
            center_point = self.mapToScene(self.viewport().rect().center())
            debug_print(f"  [VIEW_DEBUG] showEvent: Current scene center = {center_point}")
        except Exception as e:
            debug_print(f"  [VIEW_DEBUG] showEvent: Error getting center point: {e}")
    # --- END ADDED ---

    # --- UI Update Methods for Execution --- 
    def set_card_state(self, card_id: int, state: str):
        """Sets the visual state of a card (e.g., 'idle', 'executing', 'success', 'failure')."""
        try:
            card = self.cards.get(card_id)
            if card and hasattr(card, 'set_execution_state'): # Check if method exists on TaskCard
                try:
                    # 检查卡片是否仍在场景中
                    if card.scene() != self.scene:
                        logger.debug(f"卡片 {card_id} 不在场景中，跳过状态设置")
                        return
                    
                    card.set_execution_state(state)
                    logger.debug(f"成功设置卡片 {card_id} 状态为 {state}")
                except RuntimeError as re:
                    # 处理Qt对象已删除的情况
                    logger.debug(f"卡片 {card_id} 对象已删除，无法设置状态: {re}")
                    # 从cards字典中移除已删除的卡片引用
                    if card_id in self.cards:
                        del self.cards[card_id]
                except Exception as e:
                    logger.warning(f"设置卡片 {card_id} 状态时发生错误: {e}")
            else:
                # 改为debug级别，避免在控制台产生过多警告信息
                logger.debug(f"尝试设置状态时找不到卡片 {card_id} 或卡片缺少 set_execution_state 方法。")
                # 如果工作流被清空但执行器还在运行，这是正常情况
        except Exception as e:
            logger.error(f"设置卡片 {card_id} 状态时发生严重错误: {e}")
            # 确保不会因为状态设置错误导致程序崩溃

    def reset_card_states(self):
        """Resets all cards to their idle visual state."""
        debug_print("重置所有卡片状态为 idle")
        for card_id in self.cards:
             self.set_card_state(card_id, 'idle')

        # 工具 停止所有卡片的闪烁效果
        try:
            for card_id, card in self.cards.items():
                if card and hasattr(card, 'stop_flash'):
                    card.stop_flash()
            debug_print("停止 已停止所有卡片的闪烁效果")
        except Exception as e:
            debug_print(f"错误 停止所有卡片闪烁效果失败: {e}")

    # --- Renumbering Logic - Kept but unused? --- 
    def renumber_cards_display_by_sequence(self):
        """Placeholder or potentially deprecated renumbering logic."""
        logger.warning("renumber_cards_display_by_sequence called - likely deprecated. Use update_card_sequence_display.")
        # If this is truly needed, it should call update_card_sequence_display
        self.update_card_sequence_display()

    # --- Restore Copy/Paste/Delete/Edit Slots --- 
    def handle_copy_card(self, card_id: int, parameters: dict):
        """Stores the data of the card requested to be copied (单卡片复制，保持向后兼容)."""
        card = self.cards.get(card_id)
        if card:
            self.copied_card_data = {
                'single_card': True,  # 标记为单卡片复制
                'task_type': card.task_type,
                'parameters': parameters,
                'custom_name': card.custom_name  # 包含卡片备注
            }
            logger.info(f"已复制卡片 {card_id} ({card.task_type}) 的数据，包含备注: {card.custom_name}")
        else:
            logger.warning(f"尝试复制不存在的卡片 ID: {card_id}")

    def handle_copy_selected_cards(self):
        """复制当前选中的所有卡片"""
        if self._block_edit_if_running("复制选中卡片"):
            return

        selected_items = self.scene.selectedItems()
        selected_cards = [item for item in selected_items if isinstance(item, TaskCard)]

        if not selected_cards:
            logger.warning("没有选中的卡片可以复制")
            return

        # 准备批量复制数据
        cards_data = []
        for card in selected_cards:
            card_data = {
                'task_type': card.task_type,
                'parameters': card.parameters.copy(),
                'custom_name': card.custom_name,
                'original_pos': (card.pos().x(), card.pos().y())  # 保存原始位置用于相对定位
            }
            cards_data.append(card_data)

        self.copied_card_data = {
            'single_card': False,  # 标记为批量复制
            'cards': cards_data
        }

        logger.info(f"已复制 {len(selected_cards)} 个卡片到剪贴板")

        # 可选：显示提示信息
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "复制成功", f"已复制 {len(selected_cards)} 个卡片到剪贴板\n\n使用 Ctrl+V 或右键菜单粘贴")

    def is_paste_available(self) -> bool:
        """Checks if there is card data in the clipboard to paste."""
        return self.copied_card_data is not None

    def handle_paste_card(self, scene_pos: QPointF):
        """Handles pasting card(s) from the internal clipboard at the given scene position."""
        # 检查是否正在运行，如果是则阻止粘贴
        if self._block_edit_if_running("粘贴卡片"):
            return

        debug_print(f"--- [DEBUG] WorkflowView: handle_paste_card START - Scene Pos: {scene_pos} ---")
        if not self.copied_card_data:
            debug_print("  [DEBUG] Paste failed: No card data in clipboard.")
            QMessageBox.warning(self, "粘贴失败", "剪贴板中没有可粘贴的卡片数据。")
            debug_print(f"--- [DEBUG] WorkflowView: handle_paste_card END (No data) ---")
            return

        # 检查是单卡片复制还是批量复制
        is_single_card = self.copied_card_data.get('single_card', True)

        if is_single_card:
            # 单卡片粘贴（保持原有逻辑）
            self._paste_single_card(scene_pos)
        else:
            # 批量卡片粘贴
            self._paste_multiple_cards(scene_pos)

        debug_print(f"--- [DEBUG] WorkflowView: handle_paste_card END ---")

    def _paste_single_card(self, scene_pos: QPointF):
        """粘贴单个卡片"""
        # Extract data from clipboard
        task_type = self.copied_card_data.get('task_type')
        parameters_to_paste = self.copied_card_data.get('parameters', {})

        if not task_type or not self.task_modules.get(task_type):
            debug_print(f"  [DEBUG] Paste failed: Invalid task type '{task_type}' in clipboard data.")
            QMessageBox.critical(self, "粘贴失败", f"剪贴板中的卡片类型 '{task_type}' 无效。")
            self.copied_card_data = None # Clear invalid data
            return

        debug_print(f"  [DEBUG] Pasting single card: Type='{task_type}', Params={parameters_to_paste}")

        # 设置粘贴标志，防止add_task_card保存撤销状态
        self._pasting_card = True
        # Add the new card at the specified position
        new_card = self.add_task_card(scene_pos.x(), scene_pos.y(), task_type, card_id=None)
        # 重置粘贴标志
        self._pasting_card = False

        if new_card:
            debug_print(f"  [DEBUG] New card created with ID: {new_card.card_id}")
            # Apply the copied parameters to the new card
            new_card.parameters.update(parameters_to_paste.copy())
            debug_print(f"  [DEBUG] Copied parameters applied to new card {new_card.card_id}: {new_card.parameters}")

            # Apply the copied custom name (备注)
            custom_name = self.copied_card_data.get('custom_name')
            if custom_name:
                new_card.set_custom_name(custom_name)
                debug_print(f"  [DEBUG] Copied custom name applied to new card {new_card.card_id}: '{custom_name}'")

            # 保存撤销状态
            self._save_undo_state('paste_cards', {
                'pasted_card_ids': [new_card.card_id],
                'paste_type': 'single'
            })

            # Trigger update after pasting
            self.update_card_sequence_display()
            debug_print(f"  Single card pasted successfully.")
        else:
            debug_print("  [DEBUG] Paste failed: add_task_card returned None.")
            QMessageBox.critical(self, "粘贴失败", "创建新卡片时发生错误。")

    def _paste_multiple_cards(self, scene_pos: QPointF):
        """粘贴多个卡片"""
        cards_data = self.copied_card_data.get('cards', [])
        if not cards_data:
            QMessageBox.warning(self, "粘贴失败", "剪贴板中没有有效的卡片数据。")
            return

        debug_print(f"  [DEBUG] Pasting {len(cards_data)} cards...")

        # 计算原始卡片的边界框，用于相对定位
        if len(cards_data) > 1:
            min_x = min(card_data['original_pos'][0] for card_data in cards_data)
            min_y = min(card_data['original_pos'][1] for card_data in cards_data)
        else:
            min_x = min_y = 0

        new_cards = []
        failed_count = 0

        # 设置粘贴标志，防止add_task_card保存撤销状态
        self._pasting_card = True

        for i, card_data in enumerate(cards_data):
            task_type = card_data.get('task_type')
            parameters = card_data.get('parameters', {})
            custom_name = card_data.get('custom_name')
            original_pos = card_data.get('original_pos', (0, 0))

            if not task_type or not self.task_modules.get(task_type):
                debug_print(f"  [DEBUG] Skipping invalid task type: {task_type}")
                failed_count += 1
                continue

            # 计算新位置（相对于点击位置）
            offset_x = original_pos[0] - min_x
            offset_y = original_pos[1] - min_y
            new_x = scene_pos.x() + offset_x
            new_y = scene_pos.y() + offset_y

            # 创建新卡片
            new_card = self.add_task_card(new_x, new_y, task_type, card_id=None)

            if new_card:
                # 应用参数
                new_card.parameters.update(parameters.copy())

                # 应用备注
                if custom_name:
                    new_card.set_custom_name(custom_name)

                new_cards.append(new_card)
                debug_print(f"  [DEBUG] Created card {i+1}/{len(cards_data)}: ID {new_card.card_id} ({task_type})")
            else:
                failed_count += 1
                debug_print(f"  [DEBUG] Failed to create card {i+1}/{len(cards_data)}: {task_type}")

        # 重置粘贴标志
        self._pasting_card = False

        # 保存撤销状态（只有成功粘贴的卡片）
        if new_cards:
            pasted_card_ids = [card.card_id for card in new_cards]
            self._save_undo_state('paste_cards', {
                'pasted_card_ids': pasted_card_ids,
                'paste_type': 'multiple'
            })

            # 触发更新
            self.update_card_sequence_display()

        # 显示结果
        success_count = len(new_cards)
        if success_count > 0:
            if failed_count > 0:
                QMessageBox.information(self, "粘贴完成", f"成功粘贴 {success_count} 个卡片\n失败 {failed_count} 个卡片")
            else:
                QMessageBox.information(self, "粘贴成功", f"成功粘贴 {success_count} 个卡片")
        else:
            QMessageBox.critical(self, "粘贴失败", "所有卡片粘贴都失败了")

        debug_print(f"  [DEBUG] Multiple cards paste completed: {success_count} success, {failed_count} failed")

    def _save_undo_state(self, operation_type: str, operation_data: Dict[str, Any]):
        """保存撤销状态到历史栈"""
        if self._block_edit_if_running("保存撤销状态"):
            return

        # 加载工作流期间或撤销操作期间不保存任何撤销状态
        if self._loading_workflow:
            debug_print(f"  [UNDO] Skipping undo save during workflow loading: {operation_type}")
            return

        if self._undoing_operation:
            debug_print(f"  [UNDO] Skipping undo save during undo operation: {operation_type}")
            logger.info(f"  [UNDO] Skipping undo save during undo operation: {operation_type}")
            return

        undo_state = {
            'operation_type': operation_type,
            'operation_data': operation_data,
            'timestamp': time.time()
        }

        self.undo_stack.append(undo_state)

        # 限制撤销历史的大小
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

        debug_print(f"  [UNDO] Saved undo state: {operation_type}, stack size: {len(self.undo_stack)}")

    def _save_card_state_for_undo(self, card: TaskCard):
        """保存卡片的完整状态用于撤销删除操作"""
        debug_print(f"  [UNDO] _save_card_state_for_undo called for card {card.card_id}")
        try:
            # 收集卡片的所有连接信息
            connections_data = []
            debug_print(f"  [UNDO] Card {card.card_id} has {len(card.connections)} connections")
            for conn in card.connections:
                if isinstance(conn, ConnectionLine):
                    conn_data = {
                        'start_card_id': conn.start_item.card_id if conn.start_item else None,
                        'end_card_id': conn.end_item.card_id if conn.end_item else None,
                        'line_type': conn.line_type,
                        'is_outgoing': conn.start_item == card  # 是否是从该卡片发出的连接
                    }
                    connections_data.append(conn_data)

            # 保存卡片的完整状态
            card_state = {
                'card_id': card.card_id,
                'task_type': card.task_type,
                'parameters': card.parameters.copy(),
                'custom_name': card.custom_name,
                'position': (card.pos().x(), card.pos().y()),
                'connections': connections_data
            }

            # 保存到撤销栈
            self._save_undo_state('delete_card', {
                'card_state': card_state
            })

            debug_print(f"  [UNDO] Saved card state for undo: {card.card_id} with {len(connections_data)} connections")

        except Exception as e:
            debug_print(f"  [UNDO] Error saving card state: {e}")
            logger.error(f"保存卡片状态失败: {e}", exc_info=True)

    def _save_connection_state_for_undo(self, connection):
        """保存连接状态用于撤销删除操作"""
        try:
            if isinstance(connection, ConnectionLine):
                conn_data = {
                    'start_card_id': connection.start_item.card_id if connection.start_item else None,
                    'end_card_id': connection.end_item.card_id if connection.end_item else None,
                    'line_type': connection.line_type
                }

                # 保存到撤销栈
                self._save_undo_state('delete_connection', {
                    'connection_data': conn_data
                })

                debug_print(f"  [UNDO] Saved connection state for undo: {conn_data['start_card_id']} -> {conn_data['end_card_id']} ({conn_data['line_type']})")

        except Exception as e:
            debug_print(f"  [UNDO] Error saving connection state: {e}")
            logger.error(f"保存连接状态失败: {e}", exc_info=True)

    def _save_add_connection_state_for_undo(self, start_card, end_card, line_type):
        """保存添加连接的状态用于撤销"""
        try:
            conn_data = {
                'start_card_id': start_card.card_id if start_card else None,
                'end_card_id': end_card.card_id if end_card else None,
                'line_type': line_type
            }

            # 保存到撤销栈
            self._save_undo_state('add_connection', {
                'connection_data': conn_data
            })

            debug_print(f"  [UNDO] Saved add connection state for undo: {conn_data['start_card_id']} -> {conn_data['end_card_id']} ({conn_data['line_type']})")

        except Exception as e:
            debug_print(f"  [UNDO] Error saving add connection state: {e}")
            logger.error(f"保存添加连接状态失败: {e}", exc_info=True)

    def _save_modify_connection_state_for_undo(self, old_connection, new_start_card, new_end_card, new_line_type):
        """保存修改连接的状态用于撤销（包含删除旧连接和添加新连接）"""
        try:
            # 旧连接数据
            old_conn_data = {
                'start_card_id': old_connection.start_item.card_id if old_connection.start_item else None,
                'end_card_id': old_connection.end_item.card_id if old_connection.end_item else None,
                'line_type': old_connection.line_type if hasattr(old_connection, 'line_type') else 'unknown'
            }

            # 新连接数据
            new_conn_data = {
                'start_card_id': new_start_card.card_id if new_start_card else None,
                'end_card_id': new_end_card.card_id if new_end_card else None,
                'line_type': new_line_type
            }

            # 保存复合撤销操作
            self._save_undo_state('modify_connection', {
                'old_connection_data': old_conn_data,
                'new_connection_data': new_conn_data
            })

            debug_print(f"  [UNDO] Saved modify connection state for undo:")
            debug_print(f"    Old: {old_conn_data['start_card_id']} -> {old_conn_data['end_card_id']} ({old_conn_data['line_type']})")
            debug_print(f"    New: {new_conn_data['start_card_id']} -> {new_conn_data['end_card_id']} ({new_conn_data['line_type']})")

        except Exception as e:
            debug_print(f"  [UNDO] Error saving modify connection state: {e}")
            logger.error(f"保存修改连接状态失败: {e}", exc_info=True)

    def _save_add_card_state_for_undo(self, card_id: int, task_type: str, x: float, y: float, parameters: Optional[dict]):
        """保存添加卡片的状态用于撤销"""
        try:
            card_data = {
                'card_id': card_id,
                'task_type': task_type,
                'position': (x, y),
                'parameters': parameters.copy() if parameters else {}
            }

            # 保存到撤销栈
            self._save_undo_state('add_card', {
                'card_data': card_data
            })

            debug_print(f"  [UNDO] Saved add card state for undo: ID={card_id}, type={task_type}, pos=({x}, {y})")

        except Exception as e:
            debug_print(f"  [UNDO] Error saving add card state: {e}")
            logger.error(f"保存添加卡片状态失败: {e}", exc_info=True)

    def can_undo(self) -> bool:
        """检查是否可以撤销"""
        can_undo = len(self.undo_stack) > 0 and not self._is_workflow_running()
        debug_print(f"  [UNDO] can_undo check: stack_size={len(self.undo_stack)}, is_running={self._is_workflow_running()}, result={can_undo}")
        if len(self.undo_stack) > 0:
            last_op = self.undo_stack[-1]
            debug_print(f"  [UNDO] Last operation in stack: {last_op.get('operation_type', 'unknown')}")
        return can_undo

    def undo_last_operation(self):
        """撤销最后一个操作"""
        debug_print(f"  [UNDO] undo_last_operation called")

        if not self.can_undo():
            debug_print("  [UNDO] Cannot undo: no operations in stack or workflow is running")
            return

        if self._block_edit_if_running("撤销操作"):
            return

        # 设置撤销操作标志，防止撤销过程中的操作触发新的撤销保存
        self._undoing_operation = True
        debug_print(f"  [UNDO] Set undoing operation flag to True")
        logger.info(f"  [UNDO] Set undoing operation flag to True")

        last_operation = self.undo_stack.pop()
        operation_type = last_operation['operation_type']
        operation_data = last_operation['operation_data']

        debug_print(f"  [UNDO] Undoing operation: {operation_type}")
        debug_print(f"  [UNDO] Operation data: {operation_data}")

        try:
            if operation_type == 'paste_cards':
                self._undo_paste_cards(operation_data)
            elif operation_type == 'delete_card':
                self._undo_delete_card(operation_data)
            elif operation_type == 'delete_connection':
                self._undo_delete_connection(operation_data)
            elif operation_type == 'add_connection':
                self._undo_add_connection(operation_data)
            elif operation_type == 'modify_connection':
                self._undo_modify_connection(operation_data)
            elif operation_type == 'add_card':
                self._undo_add_card(operation_data)
            else:
                debug_print(f"  [UNDO] Unknown operation type: {operation_type}")
                return

            # 更新显示
            self.update_card_sequence_display()
            debug_print(f"  [UNDO] Successfully undone operation: {operation_type}")

        except Exception as e:
            debug_print(f"  [UNDO] Error undoing operation {operation_type}: {e}")
            logger.error(f"撤销操作失败: {e}", exc_info=True)

        finally:
            # 无论成功还是失败，都要清除撤销操作标志
            self._undoing_operation = False
            debug_print(f"  [UNDO] Cleared undoing operation flag")

    def _undo_paste_cards(self, operation_data: Dict[str, Any]):
        """撤销粘贴卡片操作"""
        pasted_card_ids = operation_data.get('pasted_card_ids', [])

        debug_print(f"  [UNDO] Undoing paste operation, removing {len(pasted_card_ids)} cards")

        for card_id in pasted_card_ids:
            if card_id in self.cards:
                card = self.cards[card_id]
                # 移除卡片的所有连接
                for conn in list(card.connections):
                    self.remove_connection(conn)

                # 从场景和字典中移除卡片
                if card.scene() == self.scene:
                    self.scene.removeItem(card)
                del self.cards[card_id]

                debug_print(f"  [UNDO] Removed pasted card: {card_id}")

    def _undo_delete_card(self, operation_data: Dict[str, Any]):
        """撤销删除卡片操作"""
        card_state = operation_data.get('card_state')
        if not card_state:
            debug_print("  [UNDO] No card state found for undo")
            return

        card_id = card_state['card_id']
        task_type = card_state['task_type']
        parameters = card_state['parameters']
        custom_name = card_state['custom_name']
        position = card_state['position']
        connections_data = card_state['connections']

        debug_print(f"  [UNDO] Restoring deleted card: {card_id} ({task_type})")
        debug_print(f"  [UNDO] Card state to restore:")
        debug_print(f"    - Position: {position}")
        debug_print(f"    - Parameters: {parameters}")
        debug_print(f"    - Custom name: {custom_name}")
        debug_print(f"    - Connections: {len(connections_data)} connections")

        # 检查卡片ID是否已存在
        if card_id in self.cards:
            debug_print(f"  [UNDO] ERROR: Card ID {card_id} already exists! Current cards: {list(self.cards.keys())}")
            return

        # 重新创建卡片
        debug_print(f"  [UNDO] Calling add_task_card with: pos=({position[0]}, {position[1]}), type={task_type}, id={card_id}")
        restored_card = self.add_task_card(position[0], position[1], task_type, card_id, parameters)
        if not restored_card:
            debug_print(f"  [UNDO] ERROR: Failed to restore card {card_id}")
            return

        debug_print(f"  [UNDO] Card {card_id} created successfully")
        debug_print(f"  [UNDO] Restored card parameters: {restored_card.parameters}")

        # 恢复自定义名称
        if custom_name:
            debug_print(f"  [UNDO] Setting custom name: '{custom_name}'")
            restored_card.set_custom_name(custom_name)
        else:
            debug_print(f"  [UNDO] No custom name to restore")

        # 恢复连接（延迟执行，确保所有相关卡片都存在）
        debug_print(f"  [UNDO] Scheduling connection restoration for card {card_id} in 500ms")
        QTimer.singleShot(500, lambda: self._restore_card_connections(card_id, connections_data))

        debug_print(f"  [UNDO] Successfully restored card {card_id}")

    def _restore_card_connections(self, card_id: int, connections_data: List[Dict[str, Any]]):
        """恢复卡片的连接"""
        debug_print(f"  [UNDO] Starting connection restoration for card {card_id}")
        debug_print(f"  [UNDO] Current cards in workflow: {list(self.cards.keys())}")

        # 设置撤销操作标志，防止连接恢复过程中的操作触发新的撤销保存
        was_undoing = getattr(self, '_undoing_operation', False)
        self._undoing_operation = True
        debug_print(f"  [UNDO] Set undoing operation flag to True for connection restoration")

        restored_card = self.cards.get(card_id)
        if not restored_card:
            debug_print(f"  [UNDO] ERROR: Cannot restore connections: card {card_id} not found")
            debug_print(f"  [UNDO] Available cards: {list(self.cards.keys())}")
            return

        debug_print(f"  [UNDO] Restoring {len(connections_data)} connections for card {card_id}")

        successful_restorations = 0
        failed_restorations = 0

        for i, conn_data in enumerate(connections_data):
            start_card_id = conn_data['start_card_id']
            end_card_id = conn_data['end_card_id']
            line_type = conn_data['line_type']

            debug_print(f"    [CONN {i+1}/{len(connections_data)}] Restoring: {start_card_id} -> {end_card_id} ({line_type})")

            start_card = self.cards.get(start_card_id)
            end_card = self.cards.get(end_card_id)

            if not start_card:
                debug_print(f"      ERROR: Start card {start_card_id} not found")
                failed_restorations += 1
                continue

            if not end_card:
                debug_print(f"      ERROR: End card {end_card_id} not found")
                failed_restorations += 1
                continue

            # 检查连接是否已存在
            existing_conn = None
            for conn in self.connections:
                if (isinstance(conn, ConnectionLine) and
                    conn.start_item == start_card and
                    conn.end_item == end_card and
                    conn.line_type == line_type):
                    existing_conn = conn
                    break

            if existing_conn:
                debug_print(f"      Connection already exists, skipping")
                successful_restorations += 1
            else:
                new_conn = self.add_connection(start_card, end_card, line_type)
                if new_conn:
                    debug_print(f"      SUCCESS: Restored connection")
                    successful_restorations += 1
                else:
                    debug_print(f"      ERROR: Failed to create connection")
                    failed_restorations += 1

        debug_print(f"  [UNDO] Connection restoration completed: {successful_restorations} success, {failed_restorations} failed")

        # 如果有连接恢复，触发更新
        if successful_restorations > 0:
            debug_print(f"  [UNDO] Triggering sequence update after connection restoration")
            self.update_card_sequence_display()

        # 恢复撤销操作标志状态
        self._undoing_operation = was_undoing
        debug_print(f"  [UNDO] Restored undoing operation flag to {was_undoing} after connection restoration")

    def _undo_delete_connection(self, operation_data: Dict[str, Any]):
        """撤销删除连接操作"""
        conn_data = operation_data.get('connection_data')
        if not conn_data:
            debug_print("  [UNDO] No connection data found for undo")
            return

        start_card_id = conn_data['start_card_id']
        end_card_id = conn_data['end_card_id']
        line_type = conn_data['line_type']

        start_card = self.cards.get(start_card_id)
        end_card = self.cards.get(end_card_id)

        if start_card and end_card:
            new_conn = self.add_connection(start_card, end_card, line_type)
            if new_conn:
                debug_print(f"  [UNDO] Restored connection: {start_card_id} -> {end_card_id} ({line_type})")
            else:
                debug_print(f"  [UNDO] Failed to restore connection: {start_card_id} -> {end_card_id} ({line_type})")
        else:
            debug_print(f"  [UNDO] Cannot restore connection: missing cards {start_card_id} or {end_card_id}")

    def _undo_add_connection(self, operation_data: Dict[str, Any]):
        """撤销添加连接操作"""
        conn_data = operation_data.get('connection_data')
        if not conn_data:
            debug_print("  [UNDO] No connection data found for undo")
            return

        start_card_id = conn_data['start_card_id']
        end_card_id = conn_data['end_card_id']
        line_type = conn_data['line_type']

        debug_print(f"  [UNDO] Removing added connection: {start_card_id} -> {end_card_id} ({line_type})")

        # 查找并删除对应的连接
        connection_to_remove = None
        for conn in self.connections:
            if (hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and
                conn.start_item and conn.end_item and
                conn.start_item.card_id == start_card_id and
                conn.end_item.card_id == end_card_id and
                conn.line_type == line_type):
                connection_to_remove = conn
                break

        if connection_to_remove:
            self.remove_connection(connection_to_remove)
            debug_print(f"  [UNDO] Added connection removed successfully")
        else:
            debug_print(f"  [UNDO] Connection not found for removal")

    def _undo_modify_connection(self, operation_data: Dict[str, Any]):
        """撤销修改连接操作"""
        old_conn_data = operation_data.get('old_connection_data')
        new_conn_data = operation_data.get('new_connection_data')

        if not old_conn_data or not new_conn_data:
            debug_print("  [UNDO] Missing connection data for modify undo")
            return

        debug_print(f"  [UNDO] Undoing connection modification:")
        debug_print(f"    Removing new: {new_conn_data['start_card_id']} -> {new_conn_data['end_card_id']} ({new_conn_data['line_type']})")
        debug_print(f"    Restoring old: {old_conn_data['start_card_id']} -> {old_conn_data['end_card_id']} ({old_conn_data['line_type']})")

        # 1. 删除新连接
        new_connection_to_remove = None
        for conn in self.connections:
            if (hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and
                conn.start_item and conn.end_item and
                conn.start_item.card_id == new_conn_data['start_card_id'] and
                conn.end_item.card_id == new_conn_data['end_card_id'] and
                conn.line_type == new_conn_data['line_type']):
                new_connection_to_remove = conn
                break

        if new_connection_to_remove:
            self.remove_connection(new_connection_to_remove)
            debug_print(f"  [UNDO] Removed new connection")
        else:
            debug_print(f"  [UNDO] New connection not found for removal")

        # 2. 恢复旧连接
        old_start_card = self.cards.get(old_conn_data['start_card_id'])
        old_end_card = self.cards.get(old_conn_data['end_card_id'])

        if old_start_card and old_end_card:
            restored_conn = self.add_connection(old_start_card, old_end_card, old_conn_data['line_type'])
            if restored_conn:
                debug_print(f"  [UNDO] Successfully restored old connection")
            else:
                debug_print(f"  [UNDO] Failed to restore old connection")
        else:
            debug_print(f"  [UNDO] Cannot restore old connection: missing cards {old_conn_data['start_card_id']} or {old_conn_data['end_card_id']}")

    def _undo_add_card(self, operation_data: Dict[str, Any]):
        """撤销添加卡片操作"""
        card_data = operation_data.get('card_data')
        if not card_data:
            debug_print("  [UNDO] No card data found for undo")
            return

        card_id = card_data.get('card_id')
        if card_id and card_id in self.cards:
            self.delete_card(card_id)
            debug_print(f"  [UNDO] Removed added card: {card_id}")
        else:
            debug_print(f"  [UNDO] Card not found for removal: {card_id}")

    def delete_card(self, card_id: int):
        """Deletes the specified card and its connections from the view - 增强安全版本"""
        debug_print(f"--- [DELETE_CARD_DEBUG] START delete_card for ID: {card_id} ---")

        # 直接删除卡片
        logger.info(f"删除卡片: {card_id}")

        # 检查是否正在运行，如果是则阻止删除
        if self._block_edit_if_running("删除卡片"):
            return

        # 设置删除卡片标志，防止连线删除触发额外撤销
        self._deleting_card = True
        debug_print(f"  [UNDO] Set _deleting_card flag to True")

        # 安全删除检查已移除，直接执行删除

        # --- 整个删除过程的异常处理 ---
        try:
            # 添加额外的安全检查
            import gc
            gc.disable()  # 临时禁用垃圾回收，防止删除过程中的意外回收
            # 获取和验证卡片
            card_to_delete = self.cards.get(card_id)
            if not card_to_delete:
                logger.warning(f"尝试删除不存在的卡片 ID: {card_id}")
                debug_print(f"  [ERROR] Card {card_id} not found in self.cards")
                return

            debug_print(f"  Card to delete: {card_to_delete}")

            if not hasattr(card_to_delete, 'card_id'):
                logger.error(f"卡片对象缺少card_id属性: {card_to_delete}")
                debug_print(f"  [ERROR] Card object missing card_id attribute")
                return

            # 保存卡片状态用于撤销（在删除之前）
            self._save_card_state_for_undo(card_to_delete)

            # --- 使用新的安全清理方法 ---
            self.safe_cleanup_card_state(card_id)

            # --- 清理工作流上下文数据，防止崩溃 ---
            debug_print(f"  Cleaning workflow context data for card {card_id}...")
            try:
                from task_workflow.workflow_context import clear_card_ocr_data
                clear_card_ocr_data(card_id)
                debug_print(f"    Successfully cleaned workflow context for card {card_id}")
            except Exception as context_e:
                debug_print(f"    Failed to clean workflow context: {context_e}")
                logger.warning(f"清理卡片 {card_id} 工作流上下文失败: {context_e}")

            # --- 清理其他卡片中指向被删除卡片的跳转参数 ---
            debug_print(f"  Cleaning jump target parameters pointing to card {card_id}...")
            self._cleanup_jump_target_references(card_id)

            # 收集所有相关连接
            debug_print(f"  Starting ENHANCED connection cleanup...")
            connections_to_remove = []
            
            # 从卡片的连接列表收集
            try:
                if hasattr(card_to_delete, 'connections') and card_to_delete.connections:
                    for conn in list(card_to_delete.connections):
                        if conn not in connections_to_remove:
                            connections_to_remove.append(conn)
                            debug_print(f"    Found connection from card.connections: {conn}")
            except Exception as e:
                debug_print(f"    [WARNING] Error collecting connections from card: {e}")
                logger.warning(f"收集卡片连接时出错: {e}")
            
            # 从视图的连接列表收集
            try:
                for conn in list(self.connections):
                    if (isinstance(conn, ConnectionLine) and 
                        hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and
                        (conn.start_item == card_to_delete or conn.end_item == card_to_delete)):
                        if conn not in connections_to_remove:
                            connections_to_remove.append(conn)
                            debug_print(f"    Found connection from view.connections: {conn}")
            except Exception as e:
                debug_print(f"    [WARNING] Error collecting connections from view: {e}")
                logger.warning(f"收集视图连接时出错: {e}")
            
            # 从场景中收集连接对象
            try:
                scene_items = self.scene.items()
                for item in scene_items:
                    if (isinstance(item, ConnectionLine) and 
                        hasattr(item, 'start_item') and hasattr(item, 'end_item') and
                        (item.start_item == card_to_delete or item.end_item == card_to_delete)):
                        if item not in connections_to_remove:
                            connections_to_remove.append(item)
                            debug_print(f"    Found connection from scene.items(): {item}")
            except Exception as e:
                debug_print(f"    [WARNING] Error collecting connections from scene: {e}")
                logger.warning(f"收集场景连接时出错: {e}")
        
            debug_print(f"  Total connections to remove: {len(connections_to_remove)}")
            
            # 逐个彻底移除连接
            for i, connection in enumerate(connections_to_remove):
                debug_print(f"    [CONN_REMOVE {i+1}/{len(connections_to_remove)}] Processing: {connection}")
                try:
                    # 从场景移除
                    if connection.scene() == self.scene:
                        debug_print(f"      Removing from scene...")
                        self.scene.removeItem(connection)
                        debug_print(f"      Removed from scene. Scene check: {connection.scene() is None}")
                    
                    # 从视图列表移除
                    if connection in self.connections:
                        debug_print(f"      Removing from view connections list...")
                        self.connections.remove(connection)
                        debug_print(f"      Removed from view list. Current count: {len(self.connections)}")
                    
                    # 从相关卡片移除
                    if hasattr(connection, 'start_item') and connection.start_item:
                        start_card = connection.start_item
                        if hasattr(start_card, 'connections') and connection in start_card.connections:
                            debug_print(f"      Removing from start card {start_card.card_id}...")
                            start_card.connections.remove(connection)
                            debug_print(f"      Removed from start card. Card connections count: {len(start_card.connections)}")
                    
                    if hasattr(connection, 'end_item') and connection.end_item:
                        end_card = connection.end_item
                        if hasattr(end_card, 'connections') and connection in end_card.connections:
                            debug_print(f"      Removing from end card {end_card.card_id}...")
                            end_card.connections.remove(connection)
                            debug_print(f"      Removed from end card. Card connections count: {len(end_card.connections)}")
                    
                    # 清除连接对象的引用
                    if hasattr(connection, 'start_item'):
                        connection.start_item = None
                    if hasattr(connection, 'end_item'):
                        connection.end_item = None
                    
                    debug_print(f"      Connection {connection} removed and marked for garbage collection")
                    
                except Exception as e:
                    debug_print(f"    ERROR removing connection {connection}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 清空要删除卡片的连接列表
            if hasattr(card_to_delete, 'connections'):
                card_to_delete.connections.clear()
                debug_print(f"  Cleared card {card_id} connections list")
            
            # 验证连接清理结果
            debug_print(f"  Verifying connection cleanup...")
            remaining_invalid = []
            for conn in self.connections:
                if (isinstance(conn, ConnectionLine) and 
                    ((hasattr(conn, 'start_item') and conn.start_item == card_to_delete) or
                     (hasattr(conn, 'end_item') and conn.end_item == card_to_delete))):
                    remaining_invalid.append(conn)
            
            if remaining_invalid:
                debug_print(f"  WARNING: Found {len(remaining_invalid)} invalid connections still in view list!")
                for conn in remaining_invalid:
                    try:
                        self.connections.remove(conn)
                        debug_print(f"    Force removed: {conn}")
                    except ValueError:
                        pass
            else:
                debug_print(f"  Connection cleanup verification PASSED")
            
            # 从内部字典移除卡片
            debug_print(f"  Removing card {card_id} from internal dictionary...")
            if card_id in self.cards:
                self.cards.pop(card_id)
                debug_print(f"    Card removed from dictionary. Remaining cards: {len(self.cards)}")
            
            # 发出删除信号
            self.card_deleted.emit(card_id)
            
            # 从场景移除卡片
            debug_print(f"  Removing card from scene immediately...")
            if card_to_delete.scene() == self.scene:
                self.scene.removeItem(card_to_delete)
                debug_print(f"    Card removed from scene. Scene check: {card_to_delete.scene() is None}")
            
            # 确保UI更新完成
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 清理卡片对象引用
            try:
                if hasattr(card_to_delete, 'view'):
                    card_to_delete.view = None
                if hasattr(card_to_delete, 'task_module'):
                    card_to_delete.task_module = None
                if hasattr(card_to_delete, 'parameters'):
                    card_to_delete.parameters.clear()
            except Exception as ref_e:
                debug_print(f"    [REF_CLEANUP] 清理卡片引用时出错: {ref_e}")
            
            # 最后调度卡片删除
            card_to_delete.deleteLater()
            debug_print(f"    Card scheduled for final deletion")
            
            # 再次处理事件，确保删除操作被正确处理
            QApplication.processEvents()
            
            # 更新序列显示
            self.update_card_sequence_display()
            debug_print(f"  Sequence display updated")
            
        except Exception as e:
            # 如果删除过程中发生任何错误，记录并显示错误消息
            error_msg = f"删除卡片 {card_id} 时发生严重错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            debug_print(f"  [CRITICAL_ERROR] {error_msg}")

            # 显示错误对话框
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "删除失败",
                               f"删除卡片时发生错误:\n{str(e)}\n\n" +
                               "程序状态可能不一致，建议保存工作并重启程序。")
        finally:
            # 重新启用垃圾回收并强制执行一次
            try:
                import gc
                gc.enable()
                gc.collect()
                debug_print(f"  [CLEANUP] 重新启用垃圾回收并执行清理")
            except Exception as gc_e:
                debug_print(f"  [CLEANUP] 垃圾回收操作失败: {gc_e}")

            # 重置删除卡片标志
            self._deleting_card = False
            debug_print(f"  [UNDO] Reset _deleting_card flag to False")

        debug_print(f"--- [DELETE_CARD_DEBUG] END delete_card for ID: {card_id} (ENHANCED) ---")

    def edit_card_settings(self, card_id: int):
        """Opens the parameter dialog for the specified card."""
        card = self.cards.get(card_id)
        if card and hasattr(card, 'open_parameter_dialog'):
            card.open_parameter_dialog()
            
    # --- ADDED: Slot to handle jump target changes from TaskCard ---
    def _handle_jump_target_change(self, param_name: str, old_target_id: Optional[int], new_target_id: Optional[int]):
        """Handles changes in jump target parameters to update connections."""
        source_card = self.sender() 
        logger.debug(f"--- [HANDLE_JUMP_DEBUG] Received jump signal from Card ID: {source_card.card_id if source_card else 'None'} ---")
        logger.debug(f"    Param Name: {param_name}, Old Target ID: {old_target_id}, New Target ID: {new_target_id}")
        
        if not isinstance(source_card, TaskCard):
            logger.error("_handle_jump_target_change called by non-TaskCard sender.")
            return
        if param_name not in ['success_jump_target_id', 'failure_jump_target_id']:
            logger.error(f"Unknown parameter name in _handle_jump_target_change: {param_name}")
            return
            
        # Determine line type based on parameter name
        line_type = ConnectionType.SUCCESS.value if param_name == 'success_jump_target_id' else ConnectionType.FAILURE.value
        action_param_name = 'on_success' if line_type == ConnectionType.SUCCESS.value else 'on_failure'
        current_action = source_card.parameters.get(action_param_name)

        logger.debug(f"  Source Card: {source_card.card_id} ({source_card.task_type}), Line Type: {line_type}")
        logger.debug(f"  Current Action ('{action_param_name}') on Card: '{current_action}'")
        logger.debug(f"  New Target ID for '{param_name}': {new_target_id}")

        # No direct connection manipulation here anymore.
        # The parameters on the source_card are already updated by the dialog.
        # We just need to refresh the view to reflect these parameter changes.

        logger.debug(f"--- [HANDLE_JUMP_DEBUG] Parameters on card {source_card.card_id} have changed. Scheduling full view update. ---")
        
        # Optional: Explicitly call update on the source card if its visual state (not connections)
        # needs changing due to the parameter (e.g. if it displays the target ID directly).
        # source_card.update() 

        self.update_card_sequence_display()
        logger.debug(f"  [HANDLE_JUMP_DEBUG] Called update_card_sequence_display to redraw connections based on new parameters.")

    def keyPressEvent(self, event):
        """Handles key presses: Delete, Ctrl+C, Ctrl+V for selected items."""
        modifiers = event.modifiers()
        key = event.key()

        # Ctrl+C - 复制选中的卡片
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            self.handle_copy_selected_cards()
            event.accept()
            return

        # Ctrl+V - 粘贴卡片到鼠标位置或视图中心
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V:
            # 获取当前鼠标位置，如果没有则使用视图中心
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            if self.viewport().rect().contains(cursor_pos):
                scene_pos = self.mapToScene(cursor_pos)
            else:
                # 使用视图中心
                view_center = self.viewport().rect().center()
                scene_pos = self.mapToScene(view_center)

            self.handle_paste_card(scene_pos)
            event.accept()
            return

        # Ctrl+Z - 撤销最后一个操作
        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            from PySide6.QtWidgets import QMessageBox

            # 使用全局logger，不要重新定义
            logger.info(f"  [UNDO] ===== Ctrl+Z pressed =====")
            logger.info(f"  [UNDO] Stack size: {len(self.undo_stack)}")
            logger.info(f"  [UNDO] Workflow running: {self._is_workflow_running()}")

            debug_print(f"  [UNDO] ===== Ctrl+Z pressed =====")
            debug_print(f"  [UNDO] Stack size: {len(self.undo_stack)}")
            debug_print(f"  [UNDO] Workflow running: {self._is_workflow_running()}")

            # 打印撤销栈内容
            if len(self.undo_stack) > 0:
                logger.info(f"  [UNDO] Stack contents:")
                debug_print(f"  [UNDO] Stack contents:")
                for i, op in enumerate(self.undo_stack):
                    logger.info(f"    {i}: {op.get('operation_type', 'unknown')} - {op.get('timestamp', 'no_time')}")
                    debug_print(f"    {i}: {op.get('operation_type', 'unknown')} - {op.get('timestamp', 'no_time')}")
            else:
                logger.info(f"  [UNDO] Stack is empty")
                debug_print(f"  [UNDO] Stack is empty")

            # 先检查撤销栈是否为空
            if len(self.undo_stack) == 0:
                logger.info("  [UNDO] RESULT: No operations to undo - showing empty message")
                debug_print("  [UNDO] RESULT: No operations to undo - showing empty message")
                QMessageBox.information(self, "无法撤销", "没有可撤销的操作")
            elif self._is_workflow_running():
                logger.info("  [UNDO] RESULT: Cannot undo - workflow is running")
                debug_print("  [UNDO] RESULT: Cannot undo - workflow is running")
                QMessageBox.warning(self, "无法撤销", "工作流运行期间无法执行撤销操作")
            else:
                # 有可撤销操作
                # 获取要撤销的操作类型（在执行撤销之前）
                last_operation = self.undo_stack[-1]
                operation_type = last_operation.get('operation_type', '未知操作')

                logger.info(f"  [UNDO] RESULT: About to undo operation: {operation_type}")
                logger.info(f"  [UNDO] Operation data: {last_operation}")
                debug_print(f"  [UNDO] RESULT: About to undo operation: {operation_type}")
                debug_print(f"  [UNDO] Operation data: {last_operation}")

                self.undo_last_operation()

                # 显示具体的撤销提示
                operation_names = {
                    'paste_cards': '粘贴卡片',
                    'delete_card': '删除卡片',
                    'delete_connection': '删除连线',
                    'add_connection': '添加连线',
                    'modify_connection': '修改连线',
                    'add_card': '添加卡片'
                }
                operation_name = operation_names.get(operation_type, operation_type)

                logger.info(f"  [UNDO] RESULT: Showing success message: {operation_name}")
                debug_print(f"  [UNDO] RESULT: Showing success message: {operation_name}")
                QMessageBox.information(self, "撤销成功", f"已撤销：{operation_name}")

            logger.info(f"  [UNDO] ===== End Ctrl+Z =====")
            debug_print(f"  [UNDO] ===== End Ctrl+Z =====")
            event.accept()
            return

        # Delete key - 删除选中项目
        if key == Qt.Key.Key_Delete:
            logger.info("🗑️ Delete key pressed in WorkflowView!")

            # 检查是否正在运行，如果是则阻止删除操作
            if self._block_edit_if_running("删除选中项目"):
                logger.info("  ❌ Deletion blocked - workflow is running")
                event.accept()
                return

            # 获取选中的项目
            items_to_delete = self.scene.selectedItems()
            logger.info(f"  Selected items count: {len(items_to_delete)}")

            if not items_to_delete:
                logger.info("  ❌ No items selected for deletion.")
                # 确保视图有焦点
                if not self.hasFocus():
                    self.setFocus()
                    logger.info("  🎯 Set focus to WorkflowView")
                event.accept()
                return

            # 分类选中的项目
            cards_to_delete = []
            connections_to_delete = []

            for item in items_to_delete:
                if isinstance(item, TaskCard):
                    cards_to_delete.append(item)
                    logger.debug(f"    📋 Selected card: ID={item.card_id}")
                elif hasattr(item, '__class__') and 'ConnectionLine' in item.__class__.__name__:
                    connections_to_delete.append(item)
                    logger.debug(f"    🔗 Selected connection")

            # 简化确认对话框逻辑，避免卡死
            total_items = len(cards_to_delete) + len(connections_to_delete)
            logger.info(f"  准备删除: {len(cards_to_delete)} 个卡片, {len(connections_to_delete)} 个连接")

            if total_items > 3:  # 只有超过3个项目才显示确认对话框
                try:
                    from PySide6.QtWidgets import QMessageBox
                    reply = QMessageBox.question(
                        None,  # 使用None作为父窗口，避免焦点问题
                        "确认批量删除",
                        f"确定要删除 {len(cards_to_delete)} 个卡片和 {len(connections_to_delete)} 个连接吗？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )

                    if reply != QMessageBox.StandardButton.Yes:
                        logger.info("  ❌ User cancelled batch deletion")
                        event.accept()
                        return
                except Exception as e:
                    logger.warning(f"确认对话框显示失败: {e}")
                    # 继续执行删除，不因对话框失败而中断

            # 执行删除操作 - 简化逻辑避免卡死
            logger.info(f"  🗑️ Starting deletion of {total_items} items...")

            try:
                # 先删除连接（更简单，不容易出错）
                for item in connections_to_delete:
                    try:
                        self.remove_connection(item)
                        logger.debug(f"    ✅ Connection deleted")
                    except Exception as e:
                        logger.warning(f"    ❌ Failed to delete connection: {e}")

                # 再删除卡片
                for item in cards_to_delete:
                    try:
                        self.delete_card(item.card_id)
                        logger.debug(f"    ✅ Card {item.card_id} deleted")
                    except Exception as e:
                        logger.error(f"    ❌ Failed to delete card {item.card_id}: {e}")

                logger.info(f"  ✅ Deletion completed successfully")

            except Exception as e:
                logger.error(f"删除过程中发生错误: {e}")
                # 即使出错也要接受事件，避免传递给父组件

            event.accept() # We handled the delete event
        else:
            super().keyPressEvent(event) # Pass other keys to base class
    # -------------------------------------

    # --- ADDED: Method to update card display sequence numbers --- 
    def update_card_sequence_display(self):
        """Calculates the sequence order based on blue connections using BFS,
           updates card sequence IDs, and redraws jump connections based on sequence IDs.
        """
        logger.debug("--- [DEBUG] START update_card_sequence_display --- ")

        # 设置更新序列标志，防止连接重建时保存撤销状态
        self._updating_sequence = True
        debug_print(f"  [UNDO] Set updating sequence flag to True")
        
        # <<< ENHANCED: 序列更新前验证连接状态 >>>
        logger.debug("验证连接状态（序列更新前）...")
        invalid_count = self.validate_connections()
        if invalid_count > 0:
            logger.info(f"序列更新前清理了 {invalid_count} 个无效连接")
        # <<< END ENHANCED >>>
        
        if not self.cards:
            logger.debug("  [DEBUG] No cards to update.")
            # 清除更新序列标志
            self._updating_sequence = False
            debug_print(f"  [UNDO] Cleared updating sequence flag (no cards)")
            logger.debug("--- [DEBUG] END update_card_sequence_display (no cards) --- ")
            return

        # 1. 首先处理起点卡片的next_step_card_id参数，确保sequential连接正确
        self._update_sequential_connections_from_parameters()

        # 2. Reset all sequence IDs and build adjacency list for BLUE lines only
        adj: Dict[int, List[TaskCard]] = {}
        in_degree: Dict[int, int] = {}
        card_map: Dict[int, TaskCard] = self.cards.copy()

        for card_id, card in card_map.items():
            adj[card_id] = []
            in_degree[card_id] = 0
            card.set_display_id(None)

        logger.debug(f"  [SEQ_DEBUG] Building graph from {len(list(self.connections))} connections...")
        connections_copy = list(self.connections)
        for i_conn, conn in enumerate(connections_copy):
            logger.debug(f"    [SEQ_BUILD Loop {i_conn}/{len(connections_copy)-1}] Processing conn: {conn}")
            if not isinstance(conn, ConnectionLine) or not conn.start_item or not conn.end_item or conn.line_type != 'sequential':
                logger.debug(f"      Skipping (not valid sequential connection or incomplete).")
                continue

            start_id = conn.start_item.card_id
            end_id = conn.end_item.card_id
            start_card_obj = card_map.get(start_id)
            end_card_obj = card_map.get(end_id)

            if start_card_obj and end_card_obj and start_card_obj == conn.start_item and end_card_obj == conn.end_item:
                logger.debug(f"      Valid sequential connection {start_id} -> {end_id}. Updating adj and in_degree.")
                if start_id in adj:
                     adj[start_id].append(end_card_obj)
                if end_id in in_degree:
                     in_degree[end_id] += 1
            else:
                 logger.debug(f"      Skipping connection {start_id} -> {end_id} (Start valid: {bool(start_card_obj)}, End valid: {bool(end_card_obj)}, Start match: {start_card_obj == conn.start_item}, End match: {end_card_obj == conn.end_item}). Card might have been deleted.")
        logger.debug(f"  [SEQ_DEBUG] Finished building graph.")

        # 2. Find starting nodes (only Card ID 0)
        queue = collections.deque()
        start_card = card_map.get(0)
        if start_card:
            if in_degree.get(0, 0) == 0:
                queue.append(start_card)
                logger.debug("  [SEQ_DEBUG] Starting sequence numbering from Card 0.")
            else:
                logger.warning(f"  [SEQ_DEBUG] WARNING: Card 0 exists but has in_degree {in_degree.get(0)}. Sequence numbering may be incomplete.")
                queue.append(start_card)
        else:
            logger.warning("  [SEQ_DEBUG] Card 0 not found. Sequence numbering will not be performed automatically from 0.")
            
        sequence_counter = 0
        visited_in_bfs = set()

        # 3. Perform BFS to assign sequence IDs along the main blue line paths
        logger.debug(f"  [SEQ_DEBUG] Starting BFS. Initial Queue: {[c.card_id for c in queue]}")
        processed_nodes_count = 0
        # 工具 用户要求：删除无限循环限制，允许工作流真正无限循环
        # max_iterations = len(card_map) * 2  # 防止无限循环，最多处理卡片数量的2倍
        while queue:
            current_card = queue.popleft()
            processed_nodes_count += 1
            logger.debug(f"    [SEQ_DEBUG BFS Loop {processed_nodes_count}] Dequeued Card {current_card.card_id} ('{current_card.task_type}')")

            current_card_id = current_card.card_id
            if current_card_id not in card_map or card_map[current_card_id] != current_card:
                 logger.debug(f"      [SEQ_DEBUG] Card {current_card_id} no longer valid or changed in card_map. Skipping BFS step.")
                 continue

            if current_card.card_id in visited_in_bfs:
                logger.debug(f"      [SEQ_DEBUG] Card {current_card.card_id} already visited. Skipping.")
                continue
            visited_in_bfs.add(current_card.card_id)
            logger.debug(f"      [SEQ_DEBUG] Added {current_card.card_id} to visited_in_bfs: {visited_in_bfs}")

            current_card.set_display_id(sequence_counter)
            logger.debug(f"      [SEQ_DEBUG] Assigned sequence ID {sequence_counter} to card {current_card.card_id}")
            sequence_counter += 1

            if current_card_id not in adj:
                 logger.debug(f"      [SEQ_DEBUG] Card {current_card_id} not found in adjacency list (adj). Skipping successors.")
                 continue
            successors = adj[current_card_id]

            logger.debug(f"      [SEQ_DEBUG] Successors of {current_card_id}: {[c.card_id for c in successors]}")
            successors.sort(key=lambda c: c.card_id)
            for next_card in successors:
                next_card_id = next_card.card_id
                if next_card_id not in card_map or card_map[next_card_id] != next_card:
                     logger.debug(f"        [SEQ_DEBUG] Successor Card {next_card_id} no longer valid or changed. Skipping.")
                     continue
                logger.debug(f"        [SEQ_DEBUG] Processing successor Card {next_card_id}. Current in_degree: {in_degree.get(next_card_id)}")
                if next_card_id in in_degree:
                    in_degree[next_card_id] -= 1
                    logger.debug(f"          Decremented in_degree[{next_card_id}] to {in_degree[next_card_id]}")
                    if in_degree[next_card_id] == 0:
                        if next_card.card_id not in visited_in_bfs:
                            queue.append(next_card)
                            logger.debug(f"            Added Card {next_card.card_id} to queue. New queue: {[c.card_id for c in queue]}")
                        else:
                            logger.debug(f"            Card {next_card.card_id} in_degree is 0 BUT already visited. Not adding to queue.")
                    else:
                        logger.debug(f"            Card {next_card.card_id} in_degree is {in_degree[next_card_id]} (not 0). Not adding to queue.")
                else:
                     logger.warning(f"         [SEQ_DEBUG] WARNING: Successor Card {next_card.card_id} not found in in_degree map. Skipping.")

        # 工具 用户要求：删除无限循环限制检查，允许工作流真正无限循环
        # if processed_nodes_count >= max_iterations:
        #     logger.warning(f"BFS循环达到最大迭代次数限制 ({max_iterations})，可能存在循环依赖")

        logger.debug(f"  [SEQ_DEBUG] Finished assigning sequence IDs. Processed {processed_nodes_count} nodes.")

        # 4. Update all jump (green/red) connections based on parameters and current card IDs
        logger.debug("  [JUMP_CONN_DEBUG] Updating jump connections...")
        
        # --- MODIFIED: Remove old jump lines WITHOUT clearing parameters ---
        old_jump_connections_to_remove = []
        logger.debug(f"    [JUMP_CONN_DEBUG] Checking {len(list(self.connections))} connections in view for old jump lines...")

        # --- ADDED: Also check for orphaned connections in scene ---
        scene_connections = []
        for item in self.scene.items():
            if isinstance(item, ConnectionLine):
                scene_connections.append(item)
        logger.debug(f"    [JUMP_CONN_DEBUG] Found {len(scene_connections)} ConnectionLine items in scene")
        # --- END ADDED ---
        view_connections_copy = list(self.connections) # Iterate a copy
        for i_check, conn in enumerate(view_connections_copy):
             logger.debug(f"      [JUMP_CHECK Loop {i_check}/{len(view_connections_copy)-1}] Checking: {conn} (Type: {conn.line_type if hasattr(conn, 'line_type') else 'N/A'})")
             # --- ADDED: Enhanced connection details ---
             if hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and conn.start_item and conn.end_item:
                 logger.debug(f"        Connection details: {conn.start_item.card_id} -> {conn.end_item.card_id} ({conn.line_type})")
             # --- END ADDED ---
             # Check if it's a jump connection (not sequential) AND if it's a valid ConnectionLine instance
             if isinstance(conn, ConnectionLine) and conn.start_item and conn.end_item and conn.line_type != 'sequential':
                  old_jump_connections_to_remove.append(conn)
                  logger.debug(f"        -> Marked for graphical removal.")
             else:
                  logger.debug(f"        -> Keeping (sequential or invalid connection)")
        
        logger.debug(f"    [JUMP_CONN_DEBUG] Found {len(old_jump_connections_to_remove)} old jump connections to remove graphically.")

        # --- ADDED: Check for connections in scene but not in view list ---
        orphaned_connections = []
        for scene_conn in scene_connections:
            if scene_conn not in self.connections and hasattr(scene_conn, 'line_type') and scene_conn.line_type != 'sequential':
                orphaned_connections.append(scene_conn)
                logger.debug(f"    [ORPHANED_CONN] Found orphaned connection in scene: {scene_conn.start_item.card_id if scene_conn.start_item else 'N/A'} -> {scene_conn.end_item.card_id if scene_conn.end_item else 'N/A'} ({scene_conn.line_type})")

        if orphaned_connections:
            logger.debug(f"    [JUMP_CONN_DEBUG] Found {len(orphaned_connections)} orphaned connections to remove.")
            old_jump_connections_to_remove.extend(orphaned_connections)
        # --- END ADDED ---

        # Remove ONLY from scene and view list, DO NOT call self.remove_connection()
        for i_rem, conn_to_remove in enumerate(old_jump_connections_to_remove):
            logger.debug(f"      [JUMP_GRAPHICAL_REMOVE Loop {i_rem}/{len(old_jump_connections_to_remove)-1}] Removing connection: {conn_to_remove}")
            if conn_to_remove in self.connections:
                self.connections.remove(conn_to_remove) # Remove from view tracking list
                logger.debug("        Removed from view connection list.")
            if conn_to_remove.scene() == self.scene:
                self.scene.removeItem(conn_to_remove) # Remove from scene
                logger.debug("        Removed from scene.")
        # --- END MODIFICATION ---
             
        # --- Rebuild jump connections based on CARD IDs and CURRENT parameters --- 
        logger.debug(f"    [JUMP_CONN_DEBUG] Rebuilding jump connections based on card parameters and Card IDs...")
        added_jump_count = 0
        sorted_card_ids = sorted(card_map.keys())
        logger.debug(f"    [JUMP_CONN_DEBUG] Iterating through {len(sorted_card_ids)} cards for jump line rebuild...")
        for i_build, card_id in enumerate(sorted_card_ids):
            source_card = card_map.get(card_id)
            if not source_card:
                 logger.debug(f"    [JUMP_REBUILD Loop {i_build}/{len(sorted_card_ids)-1}] Skipping Card ID {card_id} (no longer in card_map).")
                 continue

            logger.debug(f"    [JUMP_REBUILD Loop {i_build}/{len(sorted_card_ids)-1}] Processing card ID: {source_card.card_id}")
            # --- Check Success Jump --- 
            on_success_action = source_card.parameters.get('on_success')
            success_target_id = source_card.parameters.get('success_jump_target_id') # Parameters were NOT cleared this time
            logger.debug(f"      Success Params: Action='{on_success_action}', Target ID={success_target_id}")

            if on_success_action == '跳转到步骤' and success_target_id is not None:
                logger.debug(f"        Condition met for SUCCESS jump to ID: {success_target_id}")
                target_card_success = card_map.get(success_target_id)
                logger.debug(f"        Target card found (Success): {target_card_success is not None} (type: {type(target_card_success)})")
                if target_card_success:
                    if source_card.card_id in self.cards and target_card_success.card_id in self.cards:
                        if source_card != target_card_success:
                             # --- ADDED: Check if source port is restricted before creating connection ---
                             source_restricted = getattr(source_card, 'restricted_outputs', False)
                             logger.debug(f"        Source card restricted_outputs: {source_restricted}")
                             if source_restricted:
                                 logger.debug(f"        SKIPPING SUCCESS connection: {source_card.card_id} -> {success_target_id} (source port restricted)")
                             else:
                                 logger.debug(f"        Attempting to add SUCCESS connection: {source_card.card_id} -> {success_target_id}")
                                 # Call add_connection which adds to scene and card lists
                                 connection_result = self.add_connection(source_card, target_card_success, ConnectionType.SUCCESS.value)
                                 logger.debug(f"        Connection result: {connection_result}")
                                 if connection_result:
                                     added_jump_count += 1
                             # --- END ADDED ---
                        else:
                             logger.debug(f"        SKIPPING SUCCESS self-loop: Card {source_card.card_id} -> Target Card ID {success_target_id}")
                    else:
                         logger.warning(f"        SKIPPING SUCCESS add: Source ({source_card.card_id} valid: {source_card.card_id in self.cards}) or Target ({target_card_success.card_id} valid: {target_card_success.card_id in self.cards}) became invalid.")
                else:
                    logger.warning(f"        WARNING: Success jump target Card ID {success_target_id} from Card {source_card.card_id} not found in self.cards.")

            # --- Check Failure Jump --- 
            on_failure_action = source_card.parameters.get('on_failure')
            failure_target_id = source_card.parameters.get('failure_jump_target_id') # Parameters were NOT cleared
            logger.debug(f"      Failure Params: Action='{on_failure_action}', Target ID={failure_target_id}")

            if on_failure_action == '跳转到步骤' and failure_target_id is not None:
                logger.debug(f"        Condition met for FAILURE jump to ID: {failure_target_id}")
                target_card_failure = card_map.get(failure_target_id)
                logger.debug(f"        Target card found (Failure): {target_card_failure is not None} (type: {type(target_card_failure)})")
                if target_card_failure:
                    if source_card.card_id in self.cards and target_card_failure.card_id in self.cards:
                        if source_card != target_card_failure:
                             # --- ADDED: Check if source port is restricted before creating connection ---
                             source_restricted = getattr(source_card, 'restricted_outputs', False)
                             logger.debug(f"        Source card restricted_outputs: {source_restricted}")
                             if source_restricted:
                                 logger.debug(f"        SKIPPING FAILURE connection: {source_card.card_id} -> {failure_target_id} (source port restricted)")
                             else:
                                 logger.debug(f"        Attempting to add FAILURE connection: {source_card.card_id} -> {failure_target_id}")
                                 # Call add_connection which adds to scene and card lists
                                 connection_result = self.add_connection(source_card, target_card_failure, ConnectionType.FAILURE.value)
                                 logger.debug(f"        Connection result: {connection_result}")
                                 if connection_result:
                                     added_jump_count += 1
                             # --- END ADDED ---
                        else:
                              logger.debug(f"        SKIPPING FAILURE self-loop: Card {source_card.card_id} -> Target Card ID {failure_target_id}")
                    else:
                         logger.warning(f"        SKIPPING FAILURE add: Source ({source_card.card_id} valid: {source_card.card_id in self.cards}) or Target ({target_card_failure.card_id} valid: {target_card_failure.card_id in self.cards}) became invalid.")
                else:
                    logger.warning(f"        WARNING: Failure jump target Card ID {failure_target_id} from Card {source_card.card_id} not found in self.cards.")

        logger.debug(f"  [JUMP_CONN_DEBUG] Finished updating jump connections. Added {added_jump_count} new jump lines.")

        # --- ADDED: Debug connection visibility ---
        logger.debug(f"  [CONN_VISIBILITY_DEBUG] Checking visibility of all {len(self.connections)} connections:")
        for i, conn in enumerate(self.connections):
            if hasattr(conn, 'line_type') and hasattr(conn, 'start_item') and hasattr(conn, 'end_item'):
                in_scene = conn.scene() == self.scene
                path_empty = conn.path().isEmpty() if hasattr(conn, 'path') else True
                logger.debug(f"    Connection {i+1}: {conn.start_item.card_id} -> {conn.end_item.card_id} ({conn.line_type}) - In Scene: {in_scene}, Path Empty: {path_empty}")
        # --- END ADDED ---

        # 最后清理所有重复的端口连接
        self.cleanup_all_duplicate_connections()

        # 清除更新序列标志
        self._updating_sequence = False
        debug_print(f"  [UNDO] Cleared updating sequence flag")

        logger.debug("--- [DEBUG] END update_card_sequence_display --- ")

    def _update_sequential_connections_from_parameters(self):
        """根据起点卡片的next_step_card_id参数更新sequential连接"""
        logger.debug("  [PARAM_CONN_DEBUG] 开始根据参数更新sequential连接...")

        # 查找起点卡片
        start_cards = [card for card in self.cards.values() if card.task_type == "起点"]

        for start_card in start_cards:
            if 'next_step_card_id' not in start_card.parameters:
                continue

            target_id = start_card.parameters.get('next_step_card_id')
            if target_id is None:
                continue

            logger.debug(f"    [PARAM_CONN_DEBUG] 处理起点卡片 {start_card.card_id}, next_step_card_id={target_id}")

            # 查找目标卡片
            target_card = self.cards.get(target_id)
            if not target_card:
                logger.warning(f"    [PARAM_CONN_DEBUG] 目标卡片 {target_id} 不存在，跳过")
                continue

            # 检查是否已经存在正确的sequential连接
            existing_connection = None
            for conn in self.connections:
                if (isinstance(conn, ConnectionLine) and
                    conn.line_type == 'sequential' and
                    conn.start_item == start_card and
                    conn.end_item == target_card):
                    existing_connection = conn
                    break

            if existing_connection:
                logger.debug(f"    [PARAM_CONN_DEBUG] 正确的连接已存在: {start_card.card_id} -> {target_id}")
                continue

            # 移除起点卡片的所有旧sequential连接
            old_connections = []
            for conn in list(self.connections):
                if (isinstance(conn, ConnectionLine) and
                    conn.line_type == 'sequential' and
                    conn.start_item == start_card):
                    old_connections.append(conn)

            for old_conn in old_connections:
                logger.debug(f"    [PARAM_CONN_DEBUG] 移除旧连接: {start_card.card_id} -> {old_conn.end_item.card_id if old_conn.end_item else 'None'}")
                self.remove_connection(old_conn)

            # 创建新的sequential连接
            logger.debug(f"    [PARAM_CONN_DEBUG] 创建新连接: {start_card.card_id} -> {target_id}")
            new_connection = self.add_connection(start_card, target_card, 'sequential')
            if new_connection:
                logger.info(f"    [PARAM_CONN_DEBUG] 成功创建sequential连接: {start_card.card_id} -> {target_id}")
            else:
                logger.error(f"    [PARAM_CONN_DEBUG] 创建sequential连接失败: {start_card.card_id} -> {target_id}")

        logger.debug("  [PARAM_CONN_DEBUG] sequential连接更新完成")

    def _remove_duplicate_port_connections(self, card: TaskCard, port_type: str):
        """移除指定卡片指定端口的所有重复连接，只保留最新的一个"""
        debug_print(f"  [PORT_CLEANUP] Cleaning duplicate connections for card {card.card_id}, port {port_type}")

        # 查找所有从该端口发出的连接
        port_connections = []
        for conn in list(self.connections):
            if (isinstance(conn, ConnectionLine) and
                conn.start_item == card and
                conn.line_type == port_type):
                port_connections.append(conn)

        # 如果有多个连接，移除除最后一个外的所有连接
        if len(port_connections) > 1:
            debug_print(f"    Found {len(port_connections)} connections from port {port_type}, removing {len(port_connections)-1}")
            for conn in port_connections[:-1]:  # 保留最后一个
                debug_print(f"    Removing duplicate connection: {card.card_id} -> {conn.end_item.card_id if conn.end_item else 'None'}")
                self.remove_connection(conn)
        else:
            debug_print(f"    No duplicate connections found for port {port_type}")

    def cleanup_all_duplicate_connections(self):
        """清理所有重复的端口连接"""
        debug_print("  [GLOBAL_CLEANUP] Starting global duplicate connection cleanup...")

        for card_id, card in self.cards.items():
            # 检查每种端口类型
            port_types = ['sequential', 'success', 'failure']
            for port_type in port_types:
                self._remove_duplicate_port_connections(card, port_type)

        debug_print("  [GLOBAL_CLEANUP] Global duplicate connection cleanup completed")







    def zoomIn(self):
        # ... existing code ...
        pass

    def zoomOut(self):
        self.scale(1 / self.zoom_factor_base, 1 / self.zoom_factor_base)

    # --- ADDED: Method to handle scroll changes and expand scene ---
    def _handle_scroll_change(self, value: int):
        """Called when scroll bars change. Checks if view is near scene edge and expands if needed."""
        # Define margin for view-based expansion
        margin = 100.0 # Expand if view edge is within 100 pixels of scene edge

        # Get visible rect in scene coordinates
        visible_rect_scene = self.mapToScene(self.viewport().rect()).boundingRect() # Use boundingRect for QRectF
        current_scene_rect = self.sceneRect()

        new_scene_rect = QRectF(current_scene_rect) # Start with current rect
        expanded = False

        # --- Logging current state --- # <<< DISABLED LOGS START
        # debug_print(f"--- [SCROLL_EXPAND_CHECK] Scroll Value Changed: {value} ---")
        # debug_print(f"    Visible Rect (Scene): L={visible_rect_scene.left():.2f}, T={visible_rect_scene.top():.2f}, R={visible_rect_scene.right():.2f}, B={visible_rect_scene.bottom():.2f}")
        # debug_print(f"    Current Scene Rect:   L={current_scene_rect.left():.2f}, T={current_scene_rect.top():.2f}, R={current_scene_rect.right():.2f}, B={current_scene_rect.bottom():.2f}")
        # ---------------------------- # <<< DISABLED LOGS END

        # Check and expand left boundary
        if visible_rect_scene.left() < current_scene_rect.left() + margin:
            new_scene_rect.setLeft(visible_rect_scene.left() - margin * 2) # Expand generously
            expanded = True
            # debug_print(f"    [SCROLL_EXPAND_INFO] Expanding LEFT edge.") # <<< DISABLED LOG

        # Check and expand top boundary
        if visible_rect_scene.top() < current_scene_rect.top() + margin:
            new_scene_rect.setTop(visible_rect_scene.top() - margin * 2) # Expand generously
            expanded = True
            # debug_print(f"    [SCROLL_EXPAND_INFO] Expanding TOP edge.") # <<< DISABLED LOG

        # Check and expand right boundary
        if visible_rect_scene.right() > current_scene_rect.right() - margin:
            new_scene_rect.setRight(visible_rect_scene.right() + margin * 2) # Expand generously
            expanded = True
            # debug_print(f"    [SCROLL_EXPAND_INFO] Expanding RIGHT edge.") # <<< DISABLED LOG

        # Check and expand bottom boundary
        if visible_rect_scene.bottom() > current_scene_rect.bottom() - margin:
            new_scene_rect.setBottom(visible_rect_scene.bottom() + margin * 2) # Expand generously
            expanded = True
            # debug_print(f"    [SCROLL_EXPAND_INFO] Expanding BOTTOM edge.") # <<< DISABLED LOG

        if expanded:
            # --- DISABLED LOGS START ---
            # debug_print(f"--- [SCROLL_EXPAND_ACTION] Expanding sceneRect ---")
            # debug_print(f"    Old Scene Rect: {current_scene_rect}")
            # debug_print(f"    New Scene Rect: {new_scene_rect}")
            # --- DISABLED LOGS END ---
            self.scene.setSceneRect(new_scene_rect)
            # debug_print(f"    Scene Rect AFTER setSceneRect: {self.sceneRect()}") # <<< DISABLED LOG
        # else:
        #     # debug_print(f"    [SCROLL_EXPAND_INFO] No expansion needed.") # <<< DISABLED LOG
    # --- END ADDED METHOD ---

    # --- ADDED: copy_selected_card method ---
    def copy_selected_card(self):
        """Copies the currently selected single card and pastes it nearby."""
        # 检查是否正在运行，如果是则阻止复制
        if self._block_edit_if_running("复制选中卡片"):
            return
            
        selected_items = self.scene.selectedItems()
        if len(selected_items) != 1:
            logger.warning(f"Copy Card: Expected 1 selected item, found {len(selected_items)}. Aborting.")
            # Optionally show a message box
            # QMessageBox.information(self, "复制卡片", "请只选中一个卡片进行复制。")
            return

        item = selected_items[0]
        if not isinstance(item, TaskCard):
            logger.warning("Copy Card: Selected item is not a TaskCard. Aborting.")
            return

        original_card: TaskCard = item
        logger.info(f"Copy Card: Requesting copy of Card ID {original_card.card_id}...")

        # Reuse the logic from handle_copy_card to store data
        self.handle_copy_card(original_card.card_id, original_card.parameters)
        if not self.copied_card_data:
             logger.error("Copy Card: Failed to store copied card data.")
             return

        # Calculate paste position (offset from original)
        paste_offset = QPointF(30, 30) # Offset down and right
        paste_scene_pos = original_card.scenePos() + paste_offset
        logger.debug(f"  Original pos: {original_card.scenePos()}, Calculated paste pos: {paste_scene_pos}")

        # Reuse the logic from handle_paste_card
        self.handle_paste_card(paste_scene_pos)

        # Clear copied data after paste to prevent accidental multiple pastes from one copy?
        # self.copied_card_data = None
    # --- END ADDED ---

    # ... (rest of WorkflowView methods like mouse events, drawing, etc.) ... 

    # <<< ADDED: Handler for card clicks >>>
    def _handle_card_clicked(self, clicked_card_id: int):
        """Handles card clicks: stops previous flashing, starts new flashing."""
        logger.debug(f"_handle_card_clicked: Received click from Card ID {clicked_card_id}")

        # 1. Stop any currently flashing cards
        self._stop_all_flashing()

        # 2. Find neighbors of the clicked card
        clicked_card = self.cards.get(clicked_card_id)
        if not clicked_card:
            logger.warning("  Clicked card not found in view.")
            return

        connected_card_ids_to_flash = set()

        # Iterate through connections in the view to find connected cards
        for conn in self.connections:
            if isinstance(conn, ConnectionLine):
                target_card_to_flash = None
                if conn.start_item == clicked_card and conn.end_item:
                    target_card_to_flash = conn.end_item
                elif conn.end_item == clicked_card and conn.start_item:
                    target_card_to_flash = conn.start_item
                
                if target_card_to_flash and target_card_to_flash.card_id != clicked_card_id:
                    connected_card_ids_to_flash.add(target_card_to_flash.card_id)

        if not connected_card_ids_to_flash:
             logger.debug(f"  Card {clicked_card_id} has no connected cards to flash.")
             return

        # 3. Start flashing neighbors and track them
        logger.info(f"  Starting flash for {len(connected_card_ids_to_flash)} cards connected to Card {clicked_card_id}: {connected_card_ids_to_flash}")
        for card_id_to_flash in connected_card_ids_to_flash:
            card_to_flash = self.cards.get(card_id_to_flash)
            if card_to_flash and hasattr(card_to_flash, 'flash'):
                card_to_flash.flash() # Call the persistent flash start
                self.flashing_card_ids.add(card_id_to_flash) # Add to tracking set
            else:
                 logger.warning(f"    Could not find card {card_id_to_flash} or it has no flash method.")
    # <<< END MODIFICATION >>>

    # <<< ADDED: Helper to stop all flashing >>>
    def _stop_all_flashing(self):
        """Stops flashing on all currently tracked flashing cards."""
        if not self.flashing_card_ids:
            return
        debug_print(f"  [FLASH_DEBUG] Stopping flash for cards: {self.flashing_card_ids}")
        ids_to_stop = list(self.flashing_card_ids) # Iterate a copy
        self.flashing_card_ids.clear() # Clear the set immediately
        for card_id in ids_to_stop:
            try:
                card = self.cards.get(card_id)
                if card and hasattr(card, 'stop_flash'):
                    card.stop_flash()
                    debug_print(f"    [FLASH_DEBUG] 成功停止卡片 {card_id} 的闪烁")
                elif card_id not in self.cards:
                    debug_print(f"    [FLASH_DEBUG] 卡片 {card_id} 已不存在，跳过停止闪烁")
                else:
                    debug_print(f"    [FLASH_DEBUG] 卡片 {card_id} 没有 stop_flash 方法")
            except Exception as e:
                debug_print(f"    [FLASH_DEBUG] 停止卡片 {card_id} 闪烁时出错: {e}")
                logger.warning(f"停止卡片 {card_id} 闪烁时出错: {e}")
    # <<< END ADDED >>>

    # <<< ENHANCED: 新增连接验证和清理方法 >>>
    def validate_connections(self):
        """验证并清理无效的连接"""
        logger.debug("开始验证连接完整性...")
        
        invalid_connections = []
        valid_card_ids = set(self.cards.keys())
        
        for conn in list(self.connections):
            is_invalid = False
            reason = ""
            
            # 检查连接对象类型
            if not isinstance(conn, ConnectionLine):
                is_invalid = True
                reason = "连接对象类型无效"
            # 检查起始卡片
            elif not hasattr(conn, 'start_item') or not conn.start_item:
                is_invalid = True
                reason = "缺少起始卡片"
            elif conn.start_item.card_id not in valid_card_ids:
                is_invalid = True
                reason = f"起始卡片 {conn.start_item.card_id} 不存在"
            elif conn.start_item.scene() != self.scene:
                is_invalid = True
                reason = f"起始卡片 {conn.start_item.card_id} 不在场景中"
            # 检查目标卡片
            elif not hasattr(conn, 'end_item') or not conn.end_item:
                is_invalid = True
                reason = "缺少目标卡片"
            elif conn.end_item.card_id not in valid_card_ids:
                is_invalid = True
                reason = f"目标卡片 {conn.end_item.card_id} 不存在"
            elif conn.end_item.scene() != self.scene:
                is_invalid = True
                reason = f"目标卡片 {conn.end_item.card_id} 不在场景中"
            # 检查连接是否在场景中
            elif conn.scene() != self.scene:
                is_invalid = True
                reason = "连接不在场景中"
            
            if is_invalid:
                invalid_connections.append((conn, reason))
                logger.warning(f"发现无效连接: {conn} - {reason}")
        
        # 清理无效连接
        if invalid_connections:
            logger.info(f"清理 {len(invalid_connections)} 个无效连接...")
            for conn, reason in invalid_connections:
                try:
                    self._force_remove_connection(conn)
                    logger.debug(f"已清理无效连接: {reason}")
                except Exception as e:
                    logger.error(f"清理连接时出错: {e}")
        
        logger.debug(f"连接验证完成。剩余有效连接: {len(self.connections)}")
        return len(invalid_connections)
    
    def _force_remove_connection(self, connection):
        """强制移除连接，不依赖连接对象的完整性"""
        logger.debug(f"强制移除连接: {connection}")
        
        # 从视图列表移除
        if connection in self.connections:
            self.connections.remove(connection)
        
        # 从场景移除（如果还在场景中）
        try:
            if connection.scene() == self.scene:
                self.scene.removeItem(connection)
        except Exception as e:
            logger.debug(f"从场景移除连接时出错: {e}")
        
        # 从卡片连接列表移除
        try:
            if hasattr(connection, 'start_item') and connection.start_item:
                start_card = connection.start_item
                if hasattr(start_card, 'connections') and connection in start_card.connections:
                    start_card.connections.remove(connection)
        except Exception as e:
            logger.debug(f"从起始卡片移除连接时出错: {e}")
        
        try:
            if hasattr(connection, 'end_item') and connection.end_item:
                end_card = connection.end_item
                if hasattr(end_card, 'connections') and connection in end_card.connections:
                    end_card.connections.remove(connection)
        except Exception as e:
            logger.debug(f"从目标卡片移除连接时出错: {e}")
        
        # 清除连接对象引用
        try:
            if hasattr(connection, 'start_item'):
                connection.start_item = None
            if hasattr(connection, 'end_item'):
                connection.end_item = None
        except Exception as e:
            logger.debug(f"清除连接引用时出错: {e}")
        
        # ConnectionLine继承自QGraphicsPathItem，不是QObject，所以没有deleteLater()
        # 连接已从场景和列表中移除，对象会被Python垃圾回收
        try:
            # 不需要调用deleteLater()，对象引用清除后会自动回收
            pass
        except Exception as e:
            logger.debug(f"清理连接时出错: {e}")

    def _cleanup_duplicate_connections(self, start_card, end_card, line_type):
        """清理指定卡片之间的所有重复连接"""
        debug_print(f"  [CLEANUP_DUPLICATES] Cleaning up duplicate connections: {start_card.card_id} -> {end_card.card_id} ({line_type})")

        # 从场景中查找所有相关连接
        connections_to_remove = []

        # 检查场景中的所有连接
        for item in self.scene.items():
            if isinstance(item, ConnectionLine):
                if (hasattr(item, 'start_item') and hasattr(item, 'end_item') and hasattr(item, 'line_type') and
                    item.start_item == start_card and item.end_item == end_card and item.line_type == line_type):
                    connections_to_remove.append(item)
                    debug_print(f"    Found duplicate connection in scene: {item}")

        # 检查卡片连接列表中的连接
        if hasattr(start_card, 'connections'):
            for conn in start_card.connections[:]:
                if (hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and hasattr(conn, 'line_type') and
                    conn.start_item == start_card and conn.end_item == end_card and conn.line_type == line_type):
                    if conn not in connections_to_remove:
                        connections_to_remove.append(conn)
                        debug_print(f"    Found duplicate connection in start card list: {conn}")

        if hasattr(end_card, 'connections'):
            for conn in end_card.connections[:]:
                if (hasattr(conn, 'start_item') and hasattr(conn, 'end_item') and hasattr(conn, 'line_type') and
                    conn.start_item == start_card and conn.end_item == end_card and conn.line_type == line_type):
                    if conn not in connections_to_remove:
                        connections_to_remove.append(conn)
                        debug_print(f"    Found duplicate connection in end card list: {conn}")

        # 强制移除所有找到的重复连接
        for conn in connections_to_remove:
            debug_print(f"    Forcefully removing duplicate connection: {conn}")
            self._force_remove_connection(conn)

        debug_print(f"  [CLEANUP_DUPLICATES] Removed {len(connections_to_remove)} duplicate connections")

    def _update_card_parameters_on_connection_create(self, start_card, end_card, line_type):
        """当创建连接时更新卡片参数"""
        debug_print(f"  [PARAM_UPDATE] ===== UPDATING PARAMETERS FOR CONNECTION CREATION =====")
        debug_print(f"  [PARAM_UPDATE] Connection: {start_card.card_id} -> {end_card.card_id} ({line_type})")
        debug_print(f"  [PARAM_UPDATE] Start card current parameters: {start_card.parameters}")

        # 只处理成功/失败连接，sequential连接不需要更新参数
        if line_type not in ['success', 'failure']:
            return

        # 确定要更新的参数名称
        if line_type == 'success':
            action_param = 'on_success'
            target_param = 'success_jump_target_id'
        else:  # failure
            action_param = 'on_failure'
            target_param = 'failure_jump_target_id'

        # 检查起始卡片是否有这些参数
        if not hasattr(start_card, 'parameters'):
            debug_print(f"    [PARAM_UPDATE] Start card {start_card.card_id} has no parameters attribute")
            return

        # 更新参数
        parameter_changed = False

        # 设置动作为"跳转到步骤"
        if start_card.parameters.get(action_param) != '跳转到步骤':
            start_card.parameters[action_param] = '跳转到步骤'
            parameter_changed = True
            debug_print(f"    [PARAM_UPDATE] Set {action_param} to '跳转到步骤' for card {start_card.card_id}")

        # 设置目标ID
        if start_card.parameters.get(target_param) != end_card.card_id:
            start_card.parameters[target_param] = end_card.card_id
            parameter_changed = True
            debug_print(f"    [PARAM_UPDATE] Set {target_param} to {end_card.card_id} for card {start_card.card_id}")

        # 更新端口限制和卡片显示（无论参数是否变化都要更新显示）
        debug_print(f"    [PARAM_UPDATE] Updating display for card {start_card.card_id} (parameter_changed: {parameter_changed})")
        start_card.update_port_restrictions()

        # --- ADDED: Always update parameter preview display ---
        # 标记工具提示需要更新
        start_card._tooltip_needs_update = True
        # 触发卡片重绘以更新显示
        start_card.update()
        # --- END ADDED ---

        if parameter_changed:
            debug_print(f"    [PARAM_UPDATE] Card {start_card.card_id} parameters changed and display updated due to connection creation")
        else:
            debug_print(f"    [PARAM_UPDATE] Card {start_card.card_id} parameters unchanged but display refreshed due to connection creation")
    
    def cleanup_orphaned_connections(self):
        """清理孤立的连接（连接到不存在卡片的连接）"""
        logger.debug("开始清理孤立连接...")
        
        # 从场景中查找所有ConnectionLine对象
        scene_connections = []
        for item in self.scene.items():
            if isinstance(item, ConnectionLine):
                scene_connections.append(item)
        
        orphaned_connections = []
        valid_card_ids = set(self.cards.keys())
        
        for conn in scene_connections:
            is_orphaned = False
            
            # 检查是否连接到已删除的卡片
            if (hasattr(conn, 'start_item') and conn.start_item and 
                conn.start_item.card_id not in valid_card_ids):
                is_orphaned = True
            elif (hasattr(conn, 'end_item') and conn.end_item and 
                  conn.end_item.card_id not in valid_card_ids):
                is_orphaned = True
            # 检查连接是否在视图列表中
            elif conn not in self.connections:
                is_orphaned = True
            
            if is_orphaned:
                orphaned_connections.append(conn)
        
        # 清理孤立连接
        if orphaned_connections:
            logger.info(f"发现 {len(orphaned_connections)} 个孤立连接，正在清理...")
            for conn in orphaned_connections:
                try:
                    self._force_remove_connection(conn)
                except Exception as e:
                    logger.error(f"清理孤立连接时出错: {e}")
        
        logger.debug(f"孤立连接清理完成")
        return len(orphaned_connections)
    
    def safe_cleanup_card_state(self, card_id: int):
        """安全地清理卡片的所有状态，防止删除时崩溃"""
        try:
            debug_print(f"  [SAFE_CLEANUP] 开始安全清理卡片 {card_id} 状态...")
            
            # 1. 从闪烁集合中移除
            if card_id in self.flashing_card_ids:
                self.flashing_card_ids.discard(card_id)
                debug_print(f"    [SAFE_CLEANUP] 从闪烁集合中移除卡片 {card_id}")
            
            # 2. 获取卡片对象
            card = self.cards.get(card_id)
            if not card:
                debug_print(f"    [SAFE_CLEANUP] 卡片 {card_id} 不存在，跳过状态清理")
                return
            
            # 3. 停止闪烁
            if hasattr(card, 'stop_flash'):
                try:
                    card.stop_flash()
                    debug_print(f"    [SAFE_CLEANUP] 成功停止卡片 {card_id} 闪烁")
                except Exception as e:
                    debug_print(f"    [SAFE_CLEANUP] 停止卡片 {card_id} 闪烁失败: {e}")
            
            # 4. 停止定时器
            if hasattr(card, 'flash_timer') and card.flash_timer:
                try:
                    card.flash_timer.stop()
                    card.flash_timer.deleteLater()
                    card.flash_timer = None
                    debug_print(f"    [SAFE_CLEANUP] 停止卡片 {card_id} 定时器")
                except Exception as e:
                    debug_print(f"    [SAFE_CLEANUP] 停止定时器失败: {e}")
            
            # 5. 重置执行状态
            if hasattr(card, 'set_execution_state'):
                try:
                    card.set_execution_state('idle')
                    debug_print(f"    [SAFE_CLEANUP] 重置卡片 {card_id} 执行状态")
                except Exception as e:
                    debug_print(f"    [SAFE_CLEANUP] 重置执行状态失败: {e}")
            
            # 6. 断开信号连接
            try:
                if hasattr(card, 'delete_requested'):
                    card.delete_requested.disconnect()
                if hasattr(card, 'copy_requested'):
                    card.copy_requested.disconnect()
                if hasattr(card, 'edit_settings_requested'):
                    card.edit_settings_requested.disconnect()
                if hasattr(card, 'jump_target_parameter_changed'):
                    card.jump_target_parameter_changed.disconnect()
                if hasattr(card, 'card_clicked'):
                    card.card_clicked.disconnect()
                debug_print(f"    [SAFE_CLEANUP] 断开卡片 {card_id} 信号连接")
            except Exception as e:
                debug_print(f"    [SAFE_CLEANUP] 断开信号连接失败: {e}")

            # 7. 清理任何可能的线程或定时器引用
            try:
                # 清理可能的QTimer引用
                for attr_name in dir(card):
                    if 'timer' in attr_name.lower():
                        attr_value = getattr(card, attr_name, None)
                        if attr_value and hasattr(attr_value, 'stop'):
                            try:
                                attr_value.stop()
                                debug_print(f"    [SAFE_CLEANUP] 停止定时器: {attr_name}")
                            except:
                                pass
                        if attr_value and hasattr(attr_value, 'deleteLater'):
                            try:
                                attr_value.deleteLater()
                                setattr(card, attr_name, None)
                                debug_print(f"    [SAFE_CLEANUP] 清理定时器引用: {attr_name}")
                            except:
                                pass
            except Exception as e:
                debug_print(f"    [SAFE_CLEANUP] 清理定时器引用失败: {e}")

            # 8. 强制处理待处理的事件，确保清理完成
            try:
                from PySide6.QtWidgets import QApplication
                QApplication.processEvents()
                debug_print(f"    [SAFE_CLEANUP] 处理待处理事件完成")
            except Exception as e:
                debug_print(f"    [SAFE_CLEANUP] 处理事件失败: {e}")

            debug_print(f"    [SAFE_CLEANUP] 卡片 {card_id} 状态清理完成")
            
        except Exception as e:
            debug_print(f"  [SAFE_CLEANUP] 安全清理卡片 {card_id} 状态时发生错误: {e}")
            logger.error(f"安全清理卡片 {card_id} 状态失败: {e}")
    # <<< END ENHANCED >>>

    def handle_rename_card(self, card: TaskCard):
        """处理卡片备注名称功能"""
        current_name = card.custom_name if card.custom_name else ""

        # 创建自定义输入对话框以支持中文按钮
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("备注卡片名称")
        dialog.setModal(True)
        dialog.resize(350, 150)

        layout = QVBoxLayout(dialog)

        # 添加说明标签
        label = QLabel(f"为卡片 '{card.task_type}' (ID: {card.card_id}) 设置备注名称：\n\n留空则使用默认名称")
        layout.addWidget(label)

        # 添加输入框
        line_edit = QLineEdit(current_name)
        layout.addWidget(line_edit)

        # 添加按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 连接信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # 设置默认按钮和焦点
        ok_button.setDefault(True)
        line_edit.setFocus()

        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = line_edit.text()
            # 如果输入为空，则清除自定义名称
            if text.strip():
                card.set_custom_name(text.strip())
                debug_print(f"卡片 {card.card_id} 备注名称已设置为: '{text.strip()}'")
            else:
                card.set_custom_name(None)
                debug_print(f"卡片 {card.card_id} 备注名称已清除，恢复默认显示")

    def handle_change_card_id(self, card: TaskCard):
        """处理修改卡片ID功能"""
        old_id = card.card_id

        # 创建自定义输入对话框以支持中文按钮
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("修改卡片ID")
        dialog.setModal(True)
        dialog.resize(350, 180)

        layout = QVBoxLayout(dialog)

        # 添加说明标签
        label = QLabel(f"当前卡片ID: {old_id}\n请输入新的ID (0-9999)：\n\n注意：ID 0 通常用于起点任务")
        layout.addWidget(label)

        # 添加数字输入框
        spin_box = QSpinBox()
        spin_box.setRange(0, 9999)
        spin_box.setValue(old_id)
        layout.addWidget(spin_box)

        # 添加按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 连接信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # 设置默认按钮和焦点
        ok_button.setDefault(True)
        spin_box.setFocus()

        # 显示对话框
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_id = spin_box.value()
            if new_id != old_id:
                # 检查新ID是否已存在
                if new_id in self.cards:
                    # ID冲突，询问是否对换
                    existing_card = self.cards[new_id]

                    # 创建自定义消息框以支持中文按钮
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("ID冲突")
                    msg_box.setText(f"ID {new_id} 已被卡片 '{existing_card.task_type}' 使用。\n\n是否要与该卡片对换ID？\n\n"
                                   f"• 卡片 '{card.task_type}' (ID: {old_id}) → ID: {new_id}\n"
                                   f"• 卡片 '{existing_card.task_type}' (ID: {new_id}) → ID: {old_id}")
                    msg_box.setIcon(QMessageBox.Icon.Question)
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                    # 设置按钮中文文本
                    yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
                    no_button = msg_box.button(QMessageBox.StandardButton.No)
                    if yes_button: yes_button.setText("是")
                    if no_button: no_button.setText("否")

                    reply = msg_box.exec()

                    if reply == QMessageBox.StandardButton.Yes:
                        # 执行ID对换
                        self._swap_card_ids(card, existing_card)
                        debug_print(f"卡片ID对换完成: {old_id} ↔ {new_id}")

                        # 更新序列显示
                        self.update_card_sequence_display()

                        # 创建自定义信息框以支持中文按钮
                        info_box = QMessageBox(self)
                        info_box.setWindowTitle("ID对换完成")
                        info_box.setText(f"卡片ID对换成功：\n\n"
                                        f"• '{card.task_type}' 的ID: {old_id} → {new_id}\n"
                                        f"• '{existing_card.task_type}' 的ID: {new_id} → {old_id}")
                        info_box.setIcon(QMessageBox.Icon.Information)
                        info_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                        # 设置按钮中文文本
                        ok_button = info_box.button(QMessageBox.StandardButton.Ok)
                        if ok_button: ok_button.setText("确定")

                        info_box.exec()
                else:
                    # 新ID不冲突，直接修改
                    self._change_card_id(card, new_id)
                    debug_print(f"卡片ID修改完成: {old_id} → {new_id}")

                    # 更新序列显示
                    self.update_card_sequence_display()

                    # 创建自定义信息框以支持中文按钮
                    info_box = QMessageBox(self)
                    info_box.setWindowTitle("ID修改完成")
                    info_box.setText(f"卡片 '{card.task_type}' 的ID已从 {old_id} 修改为 {new_id}")
                    info_box.setIcon(QMessageBox.Icon.Information)
                    info_box.setStandardButtons(QMessageBox.StandardButton.Ok)

                    # 设置按钮中文文本
                    ok_button = info_box.button(QMessageBox.StandardButton.Ok)
                    if ok_button: ok_button.setText("确定")

                    info_box.exec()

    def _swap_card_ids(self, card1: TaskCard, card2: TaskCard):
        """对换两个卡片的ID"""
        old_id1 = card1.card_id
        old_id2 = card2.card_id

        # 临时移除卡片
        del self.cards[old_id1]
        del self.cards[old_id2]

        # 更新卡片ID
        card1.card_id = old_id2
        card2.card_id = old_id1

        # 更新标题显示
        if card1.custom_name:
            card1.title = f"{card1.custom_name} (ID: {card1.card_id})"
        else:
            card1.title = f"{card1.task_type} (ID: {card1.card_id})"

        if card2.custom_name:
            card2.title = f"{card2.custom_name} (ID: {card2.card_id})"
        else:
            card2.title = f"{card2.task_type} (ID: {card2.card_id})"

        # 重新添加到字典
        self.cards[card1.card_id] = card1
        self.cards[card2.card_id] = card2

        # 更新所有引用这些ID的参数
        self._update_card_references(old_id1, card1.card_id)
        self._update_card_references(old_id2, card2.card_id)

        # 重新绘制卡片
        card1.update()
        card2.update()

    def _change_card_id(self, card: TaskCard, new_id: int):
        """修改单个卡片的ID"""
        old_id = card.card_id

        # 移除旧的映射
        del self.cards[old_id]

        # 更新卡片ID
        card.card_id = new_id

        # 更新标题显示
        if card.custom_name:
            card.title = f"{card.custom_name} (ID: {card.card_id})"
        else:
            card.title = f"{card.task_type} (ID: {card.card_id})"

        # 添加新的映射
        self.cards[new_id] = card

        # 更新所有引用这个ID的参数
        self._update_card_references(old_id, new_id)

        # 重新绘制卡片
        card.update()

    def _cleanup_jump_target_references(self, deleted_card_id: int):
        """清理所有卡片中指向被删除卡片的跳转参数"""
        debug_print(f"    [CLEANUP_JUMP] Cleaning jump target references to card {deleted_card_id}")

        cards_updated = []
        for card_id, card in self.cards.items():
            if card_id == deleted_card_id:
                continue  # 跳过被删除的卡片本身

            updated = False

            # 检查成功跳转目标
            if card.parameters.get('success_jump_target_id') == deleted_card_id:
                debug_print(f"      Clearing success_jump_target_id in card {card_id}")
                card.parameters['success_jump_target_id'] = None
                # 同时重置相关的动作参数
                if card.parameters.get('on_success') == '跳转到步骤':
                    card.parameters['on_success'] = '执行下一步'
                    debug_print(f"      Reset on_success action to '执行下一步' in card {card_id}")
                updated = True

            # 检查失败跳转目标
            if card.parameters.get('failure_jump_target_id') == deleted_card_id:
                debug_print(f"      Clearing failure_jump_target_id in card {card_id}")
                card.parameters['failure_jump_target_id'] = None
                # 同时重置相关的动作参数
                if card.parameters.get('on_failure') == '跳转到步骤':
                    card.parameters['on_failure'] = '执行下一步'
                    debug_print(f"      Reset on_failure action to '执行下一步' in card {card_id}")
                updated = True

            # 检查其他可能的跳转参数（如条件控制任务中的跳转）
            for param_name, param_value in card.parameters.items():
                if param_name.endswith('_jump_target_id') and param_value == deleted_card_id:
                    debug_print(f"      Clearing {param_name} in card {card_id}")
                    card.parameters[param_name] = None
                    updated = True

            if updated:
                cards_updated.append(card_id)
                card.update()  # 更新卡片显示
                debug_print(f"      Updated card {card_id} parameters and display")

        if cards_updated:
            debug_print(f"    [CLEANUP_JUMP] Updated {len(cards_updated)} cards: {cards_updated}")
            logger.info(f"清理了 {len(cards_updated)} 个卡片中指向已删除卡片 {deleted_card_id} 的跳转参数")
        else:
            debug_print(f"    [CLEANUP_JUMP] No cards had jump target references to card {deleted_card_id}")

    def _validate_and_cleanup_jump_targets(self):
        """验证并清理所有无效的跳转目标参数"""
        debug_print(f"    [VALIDATE_JUMP] Validating jump target parameters...")

        valid_card_ids = set(self.cards.keys())
        cards_updated = []

        for card_id, card in self.cards.items():
            updated = False

            # 检查成功跳转目标
            success_target = card.parameters.get('success_jump_target_id')
            if success_target is not None and success_target not in valid_card_ids:
                debug_print(f"      Invalid success_jump_target_id {success_target} in card {card_id}, clearing...")
                card.parameters['success_jump_target_id'] = None
                if card.parameters.get('on_success') == '跳转到步骤':
                    card.parameters['on_success'] = '执行下一步'
                    debug_print(f"      Reset on_success action to '执行下一步' in card {card_id}")
                updated = True

            # 检查失败跳转目标
            failure_target = card.parameters.get('failure_jump_target_id')
            if failure_target is not None and failure_target not in valid_card_ids:
                debug_print(f"      Invalid failure_jump_target_id {failure_target} in card {card_id}, clearing...")
                card.parameters['failure_jump_target_id'] = None
                if card.parameters.get('on_failure') == '跳转到步骤':
                    card.parameters['on_failure'] = '执行下一步'
                    debug_print(f"      Reset on_failure action to '执行下一步' in card {card_id}")
                updated = True

            # 检查其他跳转参数
            for param_name, param_value in list(card.parameters.items()):
                if param_name.endswith('_jump_target_id') and param_value is not None:
                    if param_value not in valid_card_ids:
                        debug_print(f"      Invalid {param_name} {param_value} in card {card_id}, clearing...")
                        card.parameters[param_name] = None
                        updated = True

            if updated:
                cards_updated.append(card_id)
                card.update()  # 更新卡片显示
                debug_print(f"      Updated card {card_id} parameters and display")

        if cards_updated:
            debug_print(f"    [VALIDATE_JUMP] Cleaned invalid jump targets in {len(cards_updated)} cards: {cards_updated}")
            logger.info(f"清理了 {len(cards_updated)} 个卡片中的无效跳转参数")
        else:
            debug_print(f"    [VALIDATE_JUMP] All jump target parameters are valid")

    def _update_card_references(self, old_id: int, new_id: int):
        """更新所有卡片中引用指定ID的参数"""
        for card in self.cards.values():
            updated = False
            for param_name, param_value in card.parameters.items():
                if param_value == old_id:
                    card.parameters[param_name] = new_id
                    updated = True
                    debug_print(f"更新卡片 {card.card_id} 的参数 '{param_name}': {old_id} → {new_id}")

            if updated:
                card.update()