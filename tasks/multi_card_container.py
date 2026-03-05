# -*- coding: utf-8 -*-
"""
多卡片节点容器任务模块

允许在一个容器节点内放置多个子节点，容器会自动扩展大小以适应子节点。
容器内的节点按顺序执行，可共享上下文信息。
"""

from typing import Dict, Any, Optional, Tuple, List
from PySide6.QtWidgets import QGraphicsObject, QGraphicsRectItem
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtCore import QRectF, Qt, QPointF
import logging
import time
import random

logger = logging.getLogger(__name__)


def get_params_definition() -> Dict[str, Dict[str, Any]]:
    """
    定义多卡片节点的参数
    
    Returns:
        参数定义字典
    """
    return {
        # 容器基本信息
        "container_id": {
            "label": "容器 ID",
            "type": "string",
            "default": "",
            "readonly": True,
            "tooltip": "容器的唯一标识符（自动生成）"
        },
        "container_name": {
            "label": "容器名称",
            "type": "string",
            "default": "多卡片节点",
            "tooltip": "容器的显示名称"
        },
        
        # 容器内部工作流数据
        "internal_workflow": {
            "label": "内部工作流",
            "type": "json",
            "default": {},
            "hidden": True,
            "tooltip": "容器内部的工作流数据（卡片和连接）"
        },
        
        # 执行控制参数
        "execution_mode": {
            "label": "执行模式",
            "type": "select",
            "options": ["顺序执行", "并行执行"],
            "default": "并行执行",
            "tooltip": "顺序执行：按添加顺序依次执行子节点；并行执行：同时执行所有子节点"
        },
        
        # 错误处理
        "on_error": {
            "label": "错误处理",
            "type": "select",
            "options": ["停止容器", "继续执行", "停止工作流"],
            "default": "停止容器",
            "tooltip": "当子节点执行失败时的处理方式"
        },
        
        # --- 下一步延迟执行设置 ---
        "enable_delay": {
            "label": "启用下一步延迟执行",
            "type": "bool",
            "default": False,
            "tooltip": "启用后，在执行下一步前会延迟指定时间"
        },
        "delay_mode": {
            "label": "延迟模式",
            "type": "select",
            "options": {
                "fixed": "固定延迟",
                "random": "随机延迟"
            },
            "default": "fixed",
            "condition": {
                "param": "enable_delay",
                "value": True
            },
            "tooltip": "固定延迟：每次使用固定时间；随机延迟：在最小和最大时间之间随机选择"
        },
        "fixed_delay": {
            "label": "固定延迟 (秒)",
            "type": "float",
            "default": 1.0,
            "min": 0.0,
            "max": 60.0,
            "decimals": 1,
            "condition": [
                {
                    "param": "enable_delay",
                    "value": True
                },
                {
                    "param": "delay_mode",
                    "value": "fixed"
                }
            ],
            "tooltip": "执行下一步前的固定延迟时间（秒）"
        },
        "min_delay": {
            "label": "最小延迟 (秒)",
            "type": "float",
            "default": 0.5,
            "min": 0.0,
            "max": 60.0,
            "decimals": 1,
            "condition": [
                {
                    "param": "enable_delay",
                    "value": True
                },
                {
                    "param": "delay_mode",
                    "value": "random"
                }
            ],
            "tooltip": "随机延迟的最小时间（秒）"
        },
        "max_delay": {
            "label": "最大延迟 (秒)",
            "type": "float",
            "default": 2.0,
            "min": 0.0,
            "max": 60.0,
            "decimals": 1,
            "condition": [
                {
                    "param": "enable_delay",
                    "value": True
                },
                {
                    "param": "delay_mode",
                    "value": "random"
                }
            ],
            "tooltip": "随机延迟的最大时间（秒）"
        },
        
        # --- 执行后操作 ---
        "---execution_after---": {
            "label": "执行后操作",
            "type": "separator"
        },
        "on_success": {
            "label": "成功后操作",
            "type": "select",
            "options": {
                "continue_current": "继续执行本步骤",
                "next_step": "执行下一步",
                "jump_to_step": "跳转到步骤",
                "stop_workflow": "停止工作流"
            },
            "default": "next_step",
            "tooltip": "当前步骤执行成功后的操作"
        },
        "on_failure": {
            "label": "失败后操作",
            "type": "select",
            "options": {
                "continue_current": "继续执行本步骤",
                "next_step": "执行下一步",
                "jump_to_step": "跳转到步骤",
                "stop_workflow": "停止工作流"
            },
            "default": "next_step",
            "tooltip": "当前步骤执行失败后的操作"
        },
        "jump_target_after_success": {
            "label": "成功后跳转目标",
            "type": "select",
            "default": None,
            "widget_hint": "jump_target_selector",
            "condition": {
                "param": "on_success",
                "value": "jump_to_step"
            },
            "tooltip": "执行成功后要跳转到的步骤卡片 ID"
        },
        "jump_target_after_failure": {
            "label": "失败后跳转目标",
            "type": "select",
            "default": None,
            "widget_hint": "jump_target_selector",
            "condition": {
                "param": "on_failure",
                "value": "jump_to_step"
            },
            "tooltip": "执行失败后要跳转到的步骤卡片 ID"
        },
        
        # 容器外观
        "container_color": {
            "label": "容器背景色",
            "type": "color",
            "default": "#2d2d2d",
            "tooltip": "容器的背景颜色"
        },
        "show_sub_cards": {
            "label": "显示子卡片",
            "type": "bool",
            "default": True,
            "tooltip": "是否在容器内显示子卡片的简化视图"
        }
    }


class MultiCardContainer:
    """
    多卡片节点容器类
    
    管理容器内部的子卡片和连接，提供执行逻辑
    """
    
    def __init__(self, container_id: int, container_params: Dict[str, Any]):
        """
        初始化容器
        
        Args:
            container_id: 容器 ID
            container_params: 容器参数
        """
        self.container_id = container_id
        self.params = container_params
        
        # 内部工作流数据
        self.internal_cards: Dict[int, Dict] = {}  # 子卡片数据 {card_id: card_data}
        self.internal_connections: List[Dict] = []  # 内部连接数据
        self.start_card_id: Optional[int] = None  # 内部起始卡片 ID
        
        # 执行状态
        self.execution_results: Dict[int, Tuple[bool, str]] = {}  # {card_id: (success, message)}
        
        # 从参数加载内部工作流
        self._load_internal_workflow()
    
    def _load_internal_workflow(self):
        """从参数加载内部工作流数据"""
        internal_wf = self.params.get('internal_workflow', {})
        if internal_wf:
            self.internal_cards = internal_wf.get('cards', {})
            self.internal_connections = internal_wf.get('connections', [])
            self.start_card_id = internal_wf.get('start_card_id')
    
    def add_sub_card(self, card_data: Dict) -> int:
        """
        添加子卡片到容器
        
        Args:
            card_data: 卡片数据
            
        Returns:
            新卡片的 ID
        """
        card_id = card_data.get('card_id')
        if card_id is None:
            card_id = max(self.internal_cards.keys(), default=0) + 1
            card_data['card_id'] = card_id
        
        self.internal_cards[card_id] = card_data
        logger.info(f"容器 {self.container_id} 添加子卡片：{card_id} ({card_data.get('task_type')})")
        return card_id
    
    def remove_sub_card(self, card_id: int):
        """
        从容器移除子卡片
        
        Args:
            card_id: 要移除的卡片 ID
        """
        if card_id in self.internal_cards:
            del self.internal_cards[card_id]
            # 清理相关连接
            self.internal_connections = [
                conn for conn in self.internal_connections
                if conn.get('start_card_id') != card_id and conn.get('end_card_id') != card_id
            ]
            logger.info(f"容器 {self.container_id} 移除子卡片：{card_id}")
    
    def add_internal_connection(self, connection_data: Dict):
        """
        添加内部连接
        
        Args:
            connection_data: 连接数据
        """
        self.internal_connections.append(connection_data)
        logger.info(f"容器 {self.container_id} 添加内部连接：{connection_data}")
    
    def get_next_card_id(self, current_card_id: int, success: bool) -> Optional[int]:
        """
        获取下一个要执行的卡片 ID
        
        Args:
            current_card_id: 当前卡片 ID
            success: 当前卡片是否执行成功
            
        Returns:
            下一个卡片 ID，如果没有则返回 None
        """
        # 查找从当前卡片出发的连接
        for conn in self.internal_connections:
            if conn.get('start_card_id') == current_card_id:
                line_type = conn.get('line_type', 'sequential')
                if line_type == 'sequential':
                    return conn.get('end_card_id')
                elif line_type == 'success' and success:
                    return conn.get('end_card_id')
                elif line_type == 'failure' and not success:
                    return conn.get('end_card_id')
        
        return None
    
    def execute(self, execution_context: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        执行容器内的所有子卡片
        
        Args:
            execution_context: 执行上下文，包含：
                - target_hwnd: 目标窗口句柄
                - counters: 计数器
                - execution_mode: 执行模式
                - shared_data: 共享数据
                
        Returns:
            (是否成功，动作消息，跳转目标 ID)
        """
        logger.info(f"开始执行容器 {self.container_id}，包含 {len(self.internal_cards)} 个子卡片")
        
        execution_mode = self.params.get('execution_mode', '顺序执行')
        on_error = self.params.get('on_error', '停止容器')
        
        if execution_mode == '并行执行':
            # TODO: 实现并行执行
            return self._execute_parallel(execution_context)
        else:
            return self._execute_sequential(execution_context, on_error)
    
    def _execute_sequential(self, execution_context: Dict, on_error: str) -> Tuple[bool, str, Optional[int]]:
        """
        顺序执行容器内的所有子卡片
        
        Args:
            execution_context: 执行上下文
            on_error: 错误处理策略
            
        Returns:
            (是否成功，动作消息，跳转目标 ID)
        """
        from tasks import TASK_MODULES_DICT
        
        # 如果没有内部卡片，直接成功
        if not self.internal_cards:
            return True, "容器内无子卡片", None
        
        # 如果没有指定起始卡片，使用第一个卡片
        if self.start_card_id is None:
            self.start_card_id = min(self.internal_cards.keys())
        
        current_card_id = self.start_card_id
        visited_cards = set()  # 防止无限循环
        max_iterations = len(self.internal_cards) * 2  # 安全限制
        
        iteration_count = 0
        while current_card_id is not None and iteration_count < max_iterations:
            iteration_count += 1
            
            # 检查是否循环
            if current_card_id in visited_cards:
                logger.warning(f"容器 {self.container_id} 检测到循环执行，在卡片 {current_card_id}")
                break
            
            visited_cards.add(current_card_id)
            
            # 获取卡片数据
            card_data = self.internal_cards.get(current_card_id)
            if not card_data:
                error_msg = f"容器 {self.container_id} 找不到卡片 {current_card_id}"
                logger.error(error_msg)
                if on_error == '停止工作流':
                    return False, error_msg, None
                elif on_error == '停止容器':
                    return False, error_msg, None
                else:  # 继续执行
                    current_card_id = self.get_next_card_id(current_card_id, False)
                    continue
            
            task_type = card_data.get('task_type')
            card_params = card_data.get('parameters', {})
            
            logger.info(f"容器 {self.container_id} 执行子卡片 {current_card_id}: {task_type}")
            
            try:
                # 获取任务模块
                task_module = TASK_MODULES_DICT.get(task_type)
                if not task_module:
                    error_msg = f"未找到任务模块：{task_type}"
                    logger.error(error_msg)
                    return False, error_msg, None
                
                # 执行任务
                if hasattr(task_module, 'execute_task'):
                    success, message, jump_target = task_module.execute_task(
                        params=card_params,
                        counters=execution_context.get('counters', {}),
                        execution_mode=execution_context.get('execution_mode', '前台'),
                        **execution_context
                    )
                elif hasattr(task_module, 'execute'):
                    # 旧版本接口
                    result = task_module.execute(
                        card_params=card_params,
                        counters=execution_context.get('counters', {}),
                        execution_mode=execution_context.get('execution_mode', '前台'),
                        **execution_context
                    )
                    if isinstance(result, tuple) and len(result) == 3:
                        success, message, jump_target = result
                    else:
                        success, message = result
                        jump_target = None
                else:
                    error_msg = f"任务模块 {task_type} 没有 execute_task 或 execute 方法"
                    logger.error(error_msg)
                    return False, error_msg, None
                
                # 记录执行结果
                self.execution_results[current_card_id] = (success, message)
                
                # 处理跳转
                if jump_target is not None:
                    logger.info(f"容器 {self.container_id} 卡片 {current_card_id} 跳转到：{jump_target}")
                    # 如果是容器内的卡片 ID，继续执行
                    if jump_target in self.internal_cards:
                        current_card_id = jump_target
                        continue
                    else:
                        # 跳出容器
                        return success, f"容器执行完成，跳转到 {jump_target}", jump_target
                
                # 处理动作消息
                if message == '停止工作流':
                    return success, '停止工作流', None
                elif message == '停止容器':
                    return success, '容器执行停止', None
                
                # 获取下一个卡片
                if success:
                    current_card_id = self.get_next_card_id(current_card_id, True)
                else:
                    # 执行失败
                    logger.error(f"容器 {self.container_id} 卡片 {current_card_id} 执行失败：{message}")
                    
                    if on_error == '停止工作流':
                        return False, f"子卡片执行失败：{message}", None
                    elif on_error == '停止容器':
                        return False, f"子卡片执行失败：{message}", None
                    else:  # 继续执行
                        current_card_id = self.get_next_card_id(current_card_id, False)
                        
            except Exception as e:
                error_msg = f"容器 {self.container_id} 执行卡片 {current_card_id} 时发生异常：{e}"
                logger.error(error_msg, exc_info=True)
                
                if on_error == '停止工作流':
                    return False, error_msg, None
                elif on_error == '停止容器':
                    return False, error_msg, None
                else:  # 继续执行
                    current_card_id = self.get_next_card_id(current_card_id, False)
        
        # 所有卡片执行完成
        all_success = all(result[0] for result in self.execution_results.values())
        return all_success, "容器内所有子卡片执行完成", None
    
    def _execute_parallel(self, execution_context: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        并行执行容器内的所有子卡片（同时执行所有节点）
        
        Args:
            execution_context: 执行上下文
            
        Returns:
            (是否成功，动作消息，跳转目标 ID)
        """
        from tasks import TASK_MODULES_DICT
        
        logger.info(f"开始并行执行容器 {self.container_id}，包含 {len(self.internal_cards)} 个子卡片")
        
        if not self.internal_cards:
            return True, "容器内无子卡片", None
        
        all_results = []
        errors = []
        
        # 遍历所有子卡片，依次执行（注意：真正的并行需要多线程，这里简化为快速连续执行）
        for card_id, card_data in self.internal_cards.items():
            task_type = card_data.get('task_type')
            card_params = card_data.get('parameters', {})
            
            logger.info(f"容器 {self.container_id} 并行执行子卡片 {card_id}: {task_type}")
            
            try:
                # 获取任务模块
                task_module = TASK_MODULES_DICT.get(task_type)
                if not task_module:
                    error_msg = f"未找到任务模块：{task_type}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    all_results.append(False)
                    continue
                
                # 执行任务
                if hasattr(task_module, 'execute_task'):
                    success, message, jump_target = task_module.execute_task(
                        params=card_params,
                        counters=execution_context.get('counters', {}),
                        execution_mode=execution_context.get('execution_mode', '前台'),
                        **execution_context
                    )
                elif hasattr(task_module, 'execute'):
                    # 旧版本接口
                    result = task_module.execute(
                        card_params=card_params,
                        counters=execution_context.get('counters', {}),
                        execution_mode=execution_context.get('execution_mode', '前台'),
                        **execution_context
                    )
                    if isinstance(result, tuple) and len(result) == 3:
                        success, message, jump_target = result
                    else:
                        success, message = result
                        jump_target = None
                else:
                    error_msg = f"任务模块 {task_type} 没有 execute_task 或 execute 方法"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    all_results.append(False)
                    continue
                
                # 记录执行结果
                self.execution_results[card_id] = (success, message)
                all_results.append(success)
                
                # 处理跳转（并行模式下不支持跳转）
                if jump_target is not None:
                    logger.warning(f"并行执行模式下卡片 {card_id} 的跳转被忽略")
                
                # 处理停止信号
                if message == '停止工作流':
                    return False, '停止工作流', None
                elif message == '停止容器':
                    return False, '容器执行停止', None
                    
            except Exception as e:
                error_msg = f"容器 {self.container_id} 执行卡片 {card_id} 时发生异常：{e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                all_results.append(False)
        
        # 所有卡片执行完成
        all_success = all(all_results)
        if errors:
            error_summary = f"并行执行完成，{len(errors)} 个错误"
            return all_success, error_summary, None
        else:
            return all_success, "容器内所有子卡片并行执行完成", None
    
    def get_container_size(self) -> Tuple[int, int]:
        """
        根据内部卡片数量计算容器尺寸
        
        Returns:
            (宽度，高度)
        """
        base_width = 400  # 容器基础宽度
        base_height = 120  # 容器基础高度
        
        card_count = len(self.internal_cards)
        if card_count == 0:
            return base_width, base_height
        
        # 每个子卡片需要约 80px 高度（包括间距）
        cards_height = card_count * 80 + 40  # 40px 为上下边距
        
        total_height = max(base_height, cards_height)
        
        return base_width, total_height


def execute_task(params: Dict, counters: Dict, execution_mode: str, **kwargs) -> Tuple[bool, str, Optional[int]]:
    """
    执行多卡片节点容器
    
    Args:
        params: 容器参数
        counters: 计数器
        execution_mode: 执行模式
        **kwargs: 其他参数
        
    Returns:
        (是否成功，动作消息，跳转目标 ID)
    """
    container_id = params.get('container_id', 'unknown')
    logger.info(f"执行多卡片节点容器：{container_id}")
    
    try:
        # 创建容器实例
        container = MultiCardContainer(container_id, params)
        
        # 准备执行上下文
        execution_context = {
            'counters': counters,
            'execution_mode': execution_mode,
            'target_hwnd': kwargs.get('target_hwnd'),
            'shared_data': kwargs.get('shared_data', {})
        }
        
        # 执行容器
        success, message, jump_target = container.execute(execution_context)
        
        # 处理延迟执行
        enable_delay = params.get('enable_delay', False)
        if enable_delay:
            delay_mode = params.get('delay_mode', 'fixed')
            if delay_mode == 'fixed':
                # 固定延迟模式
                fixed_delay = params.get('fixed_delay', 1.0)
                if fixed_delay > 0:
                    logger.info(f"执行固定延迟：{fixed_delay}秒")
                    time.sleep(fixed_delay)
            else:
                # 随机延迟模式
                min_delay = params.get('min_delay', 0.5)
                max_delay = params.get('max_delay', 2.0)
                if min_delay < max_delay:
                    delay_time = random.uniform(min_delay, max_delay)
                else:
                    delay_time = min_delay
                if delay_time > 0:
                    logger.info(f"执行随机延迟：{delay_time:.2f}秒 (范围：{min_delay}-{max_delay}秒)")
                    time.sleep(delay_time)
        
        # 处理成功后/失败后操作
        on_success = params.get('on_success', 'next_step')
        on_failure = params.get('on_failure', 'next_step')
        
        # 根据执行结果和设置的操作类型，决定返回值
        if success:
            if on_success == 'stop_workflow':
                return True, '停止工作流', None
            elif on_success == 'continue_current':
                # 继续执行本步骤：返回当前卡片 ID，让执行器重新执行
                logger.info("成功后继续执行本步骤")
                # 这里返回一个特殊的跳转目标，让执行器知道要继续当前步骤
                return True, message, container_id  # 跳转到自己，实现继续执行
            elif on_success == 'jump_to_step':
                # 跳转到步骤：需要额外的参数指定跳转目标
                jump_target_id = params.get('jump_target_after_success')
                if jump_target_id is not None:
                    logger.info(f"成功后跳转到步骤：{jump_target_id}")
                    return True, message, jump_target_id
        else:
            if on_failure == 'stop_workflow':
                return False, '停止工作流', None
            elif on_failure == 'continue_current':
                # 失败后继续执行本步骤
                logger.info("失败后继续执行本步骤")
                return False, message, container_id  # 跳转到自己，实现继续执行
            elif on_failure == 'jump_to_step':
                # 跳转到步骤：需要额外的参数指定跳转目标
                jump_target_id = params.get('jump_target_after_failure')
                if jump_target_id is not None:
                    logger.info(f"失败后跳转到步骤：{jump_target_id}")
                    return False, message, jump_target_id
        
        logger.info(f"多卡片节点容器 {container_id} 执行完成：success={success}, message={message}")
        return success, message, jump_target
        
    except Exception as e:
        error_msg = f"执行多卡片节点容器时发生异常：{e}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None
