#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流任务类
用于管理单个工作流任务的数据、状态和执行
"""

import logging
import os
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QThread

from task_workflow.executor import WorkflowExecutor

logger = logging.getLogger(__name__)

class WorkflowTask(QObject):
    """单个工作流任务"""

    # 信号定义
    status_changed = Signal(str)  # status: 'idle', 'running', 'completed', 'failed', 'stopped'
    progress_updated = Signal(str)  # progress_message
    execution_finished = Signal(bool, str, str)  # success, message, stop_reason ('success', 'failed', 'no_next')

    def __init__(self, task_id: int, name: str, filepath: str, workflow_data: dict,
                 task_modules: Dict[str, Any], images_dir: str, config: dict,
                 parent=None):
        """
        初始化工作流任务

        Args:
            task_id: 任务ID
            name: 任务名称（显示名）
            filepath: 任务文件路径
            workflow_data: 工作流数据（cards + connections）
            task_modules: 任务模块字典
            images_dir: 图片目录
            config: 全局配置
            parent: 父对象
        """
        super().__init__(parent)

        self.task_id = task_id
        self.name = name
        self.filepath = filepath
        self.workflow_data = workflow_data
        self.task_modules = task_modules
        self.images_dir = images_dir
        self.config = config

        # 任务状态
        self._status = 'idle'  # 'idle', 'running', 'completed', 'failed', 'stopped'
        self.enabled = True  # 是否启用
        self.modified = False  # 是否已修改

        # 执行器相关
        self.executor: Optional[WorkflowExecutor] = None
        self.executor_thread: Optional[QThread] = None

        # 执行配置（继承全局配置）
        self.execution_mode = config.get('execution_mode', 'foreground')
        self.target_hwnd = None
        self.target_window_title = config.get('target_window_title', '')

        # 🔧 跳转配置（基于工作流停止类型的自动跳转）
        self.stop_reason = None  # 'success', 'failed', 'no_next' 停止原因
        self.jump_enabled = True  # 是否启用跳转
        self.auto_execute_after_jump = True  # 跳转后是否自动执行
        self.jump_rules = {}  # 跳转规则 {'success': target_task_id, 'failed': target_task_id, 'no_next': target_task_id}
        self.max_jump_count = 10  # 最大跳转次数，0表示无限循环

        logger.info(f"创建任务: ID={task_id}, 名称='{name}'")

    @property
    def status(self) -> str:
        """获取任务状态"""
        return self._status

    @status.setter
    def status(self, value: str):
        """设置任务状态并发送信号"""
        if self._status != value:
            old_status = self._status
            self._status = value
            logger.info(f"任务 '{self.name}' 状态变更: {old_status} -> {value}")
            self.status_changed.emit(value)

    def can_execute(self) -> bool:
        """检查是否可以执行"""
        return self.enabled and self.status in ['idle', 'completed', 'failed', 'stopped']

    def can_stop(self) -> bool:
        """检查是否可以停止"""
        return self.status == 'running'

    def execute_sync(self) -> bool:
        """
        同步执行任务（阻塞直到完成）

        Returns:
            是否执行成功
        """
        if not self.can_execute():
            logger.warning(f"任务 '{self.name}' 当前状态 '{self.status}' 不允许执行")
            return False

        logger.info(f"开始同步执行任务: {self.name}")
        self.status = 'running'

        try:
            # 创建执行器
            self._create_executor()

            # 🔧 使用QEventLoop来在同步执行时保持GUI响应
            from PySide6.QtCore import QEventLoop
            event_loop = QEventLoop()

            # 创建线程执行（避免阻塞GUI）
            self.executor_thread = QThread()
            self.executor.moveToThread(self.executor_thread)

            # 连接信号
            self.executor_thread.started.connect(self.executor.run)
            self.executor.execution_finished.connect(event_loop.quit)
            self.executor.step_details.connect(self._on_step_details)

            # 记录执行结果
            execution_success = [False]  # 使用列表包装以便在闭包中修改
            execution_message = [""]

            def on_finished(message: str):
                execution_message[0] = message
                execution_success[0] = '成功' in message or '完成' in message
                logger.info(f"同步执行完成: {message}")

            self.executor.execution_finished.connect(on_finished)

            # 启动线程
            self.executor_thread.start()
            logger.info(f"任务 '{self.name}' 开始在后台线程执行（同步等待）")

            # 运行事件循环，等待执行完成
            event_loop.exec()

            # 等待线程结束
            if self.executor_thread.isRunning():
                self.executor_thread.quit()
                self.executor_thread.wait(5000)

            # 🔧 检测停止原因
            stop_reason = self._detect_stop_reason(execution_success[0], execution_message[0])
            self.stop_reason = stop_reason
            logger.info(f"任务 '{self.name}' 停止原因: {stop_reason}")

            # 更新状态
            if execution_success[0]:
                self.status = 'completed'
                self.execution_finished.emit(True, execution_message[0], stop_reason)
                logger.info(f"任务 '{self.name}' 同步执行成功")
                return True
            else:
                self.status = 'failed'
                self.execution_finished.emit(False, execution_message[0], stop_reason)
                logger.error(f"任务 '{self.name}' 同步执行失败")
                return False

        except Exception as e:
            logger.error(f"任务 '{self.name}' 执行失败: {e}", exc_info=True)
            self.status = 'failed'
            self.stop_reason = 'failed'
            self.execution_finished.emit(False, f"任务 '{self.name}' 执行失败: {e}", 'failed')
            return False
        finally:
            self._cleanup_executor()

    def _detect_stop_reason(self, success: bool, message: str) -> str:
        """
        检测工作流停止的原因

        Args:
            success: 是否成功
            message: 执行结果消息

        Returns:
            stop_reason: 'success' (成功停止), 'failed' (失败停止), 'no_next' (无后续卡片)
        """
        if success:
            # 检查是否是因为没有后续卡片而停止
            if '没有后续' in message or '无后续' in message or '流程结束' in message:
                return 'no_next'
            else:
                return 'success'
        else:
            return 'failed'

    def execute_async(self) -> QThread:
        """
        异步执行任务（立即返回，后台运行）

        Returns:
            执行线程对象
        """
        if not self.can_execute():
            logger.warning(f"任务 '{self.name}' 当前状态 '{self.status}' 不允许执行")
            return None

        logger.info(f"开始异步执行任务: {self.name}")
        self.status = 'running'

        try:
            # 创建执行器
            self._create_executor()

            # 创建线程
            self.executor_thread = QThread()
            self.executor.moveToThread(self.executor_thread)

            # 连接信号
            self.executor_thread.started.connect(self.executor.run)
            self.executor.execution_finished.connect(self._on_async_execution_finished)
            self.executor.step_details.connect(self._on_step_details)

            # 🔧 关键修复：连接线程的finished信号来清理引用
            self.executor.execution_finished.connect(self.executor_thread.quit)
            self.executor_thread.finished.connect(self._cleanup_executor_thread)

            # 启动线程
            self.executor_thread.start()
            logger.info(f"任务 '{self.name}' 异步执行已启动")

            return self.executor_thread

        except Exception as e:
            logger.error(f"任务 '{self.name}' 启动失败: {e}", exc_info=True)
            self.status = 'failed'
            self.stop_reason = 'failed'
            self.execution_finished.emit(False, f"任务 '{self.name}' 启动失败: {e}", 'failed')
            self._cleanup_executor()
            return None

    def stop(self):
        """停止任务执行"""
        if not self.can_stop():
            logger.warning(f"任务 '{self.name}' 当前状态 '{self.status}' 无法停止")
            return

        logger.info(f"请求停止任务: {self.name}")

        if self.executor:
            self.executor.request_stop()

        self.status = 'stopped'
        self.stop_reason = 'stopped'  # 用户手动停止

    def _create_executor(self):
        """创建工作流执行器"""
        # 转换数据格式
        cards_dict = {}
        for card in self.workflow_data.get('cards', []):
            card_id = card['id']
            cards_dict[card_id] = card
            cards_dict[str(card_id)] = card

        connections_list = self.workflow_data.get('connections', [])

        # 🔍 调试：打印连接数据以排查为什么不能跳转到下一个卡片
        logger.info(f"📊 任务 '{self.name}' 加载了 {len(connections_list)} 个连接")
        if connections_list:
            for conn in connections_list:
                logger.info(f"  连接: {conn.get('start_card_id')} -> {conn.get('end_card_id')} (类型: {conn.get('type')})")
        else:
            logger.warning(f"⚠️ 任务 '{self.name}' 没有任何连接数据！这会导致只执行第一个卡片就停止")

        # 查找起始卡片
        start_card_id = None
        for card in self.workflow_data.get('cards', []):
            if card.get('task_type') == '起点':
                start_card_id = card.get('id')
                break

        if start_card_id is None and self.workflow_data.get('cards'):
            start_card_id = self.workflow_data['cards'][0].get('id')

        if start_card_id is None:
            raise ValueError(f"任务 '{self.name}' 找不到起始卡片")

        # 创建执行器
        self.executor = WorkflowExecutor(
            cards_data=cards_dict,
            connections_data=connections_list,
            task_modules=self.task_modules,
            target_window_title=self.target_window_title,
            target_hwnd=self.target_hwnd,
            execution_mode=self.execution_mode,
            start_card_id=start_card_id,
            images_dir=self.images_dir,
            parent=None  # 🔧 修复：不设置parent，避免moveToThread错误
        )

        logger.debug(f"任务 '{self.name}' 执行器创建成功")

    def _cleanup_executor(self):
        """清理执行器资源"""
        if self.executor_thread and self.executor_thread.isRunning():
            self.executor_thread.quit()
            self.executor_thread.wait(3000)  # 等待最多3秒

        self.executor = None
        self.executor_thread = None

    def _cleanup_executor_thread(self):
        """清理执行器线程引用（从线程的finished信号调用）"""
        logger.info(f"任务 '{self.name}' 线程已结束，清理线程引用")
        self.executor = None
        self.executor_thread = None

    def _on_async_execution_finished(self, message: str):
        """异步执行完成回调"""
        # 判断是否成功（简单判断）
        success = '成功' in message or '完成' in message

        # 🔧 检测停止原因
        stop_reason = self._detect_stop_reason(success, message)
        self.stop_reason = stop_reason

        if success:
            self.status = 'completed'
            logger.info(f"任务 '{self.name}' 异步执行完成，停止原因: {stop_reason}")
        else:
            self.status = 'failed'
            logger.error(f"任务 '{self.name}' 异步执行失败: {message}")

        self.execution_finished.emit(success, message, stop_reason)
        # 🔧 不在这里调用 _cleanup_executor()，让线程的finished信号处理清理

    def _on_step_details(self, details: str):
        """步骤详情回调"""
        self.progress_updated.emit(details)

    def update_workflow_data(self, workflow_data: dict):
        """更新工作流数据（编辑后）"""
        self.workflow_data = workflow_data
        self.modified = True
        logger.debug(f"任务 '{self.name}' 工作流数据已更新")

    def save(self) -> bool:
        """保存任务到文件"""
        # 如果没有文件路径（新建的空白工作流），返回False
        if not self.filepath:
            logger.warning(f"任务 '{self.name}' 没有保存路径，需要先另存为")
            return False

        try:
            import json
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_data, f, ensure_ascii=False, indent=2)

            self.modified = False
            logger.info(f"任务 '{self.name}' 已保存到: {self.filepath}")
            return True

        except Exception as e:
            logger.error(f"保存任务 '{self.name}' 失败: {e}")
            return False

    def backup(self) -> bool:
        """
        备份任务到 backups 目录

        Returns:
            是否备份成功
        """
        try:
            import json
            import shutil
            from datetime import datetime

            # 创建 backups 目录（如果不存在）
            base_dir = os.path.dirname(self.filepath)
            backups_dir = os.path.join(base_dir, 'backups')
            os.makedirs(backups_dir, exist_ok=True)

            # 生成备份文件名：原文件名_backup_时间戳.json
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.basename(self.filepath)
            name_without_ext = os.path.splitext(filename)[0]
            backup_filename = f"{name_without_ext}_backup_{timestamp}.json"
            backup_filepath = os.path.join(backups_dir, backup_filename)

            # 复制文件到备份目录
            shutil.copy2(self.filepath, backup_filepath)

            logger.info(f"任务 '{self.name}' 已备份到: {backup_filepath}")
            return True

        except Exception as e:
            logger.error(f"备份任务 '{self.name}' 失败: {e}")
            return False

    def save_and_backup(self) -> bool:
        """
        保存并备份任务

        Returns:
            是否全部成功
        """
        save_success = self.save()
        backup_success = self.backup()

        if save_success and backup_success:
            logger.info(f"任务 '{self.name}' 保存和备份成功")
            return True
        else:
            if not save_success:
                logger.error(f"任务 '{self.name}' 保存失败")
            if not backup_success:
                logger.warning(f"任务 '{self.name}' 备份失败")
            return False

    def __repr__(self):
        return f"<WorkflowTask id={self.task_id} name='{self.name}' status='{self.status}'>"
