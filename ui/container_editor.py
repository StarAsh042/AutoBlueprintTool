# -*- coding: utf-8 -*-
"""
多卡片节点容器编辑器对话框

用于编辑容器内部的子工作流
"""

from typing import Dict, Any, Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPen, QBrush

import logging
logger = logging.getLogger(__name__)

class ContainerWorkflowEditor(QDialog):
    """
    容器工作流编辑器
    
    提供一个简化版的画布用于编辑容器内部的子工作流
    """
    
    def __init__(self, container_id: int, container_params: Dict[str, Any], parent=None):
        super().__init__(parent)
        
        self.container_id = container_id
        self.container_params = container_params
        
        # 窗口设置
        self.setWindowTitle(f"多卡片节点编辑器 - ID: {container_id}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # 内部工作流数据
        self.internal_cards: Dict[int, Dict] = {}
        self.internal_connections: List[Dict] = []
        self.start_card_id: Optional[int] = None
        
        # 从参数加载内部工作流
        self._load_internal_workflow()
        
        # 创建 UI
        self._setup_ui()
        
        # 保存标志
        self.workflow_modified = False
    
    def _load_internal_workflow(self):
        """从参数加载内部工作流数据"""
        internal_wf = self.container_params.get('internal_workflow', {})
        if internal_wf:
            self.internal_cards = internal_wf.get('cards', {})
            self.internal_connections = internal_wf.get('connections', [])
            self.start_card_id = internal_wf.get('start_card_id')
            logger.info(f"加载容器 {self.container_id} 的内部工作流：{len(self.internal_cards)} 个卡片")
    
    def _save_internal_workflow(self):
        """保存内部工作流数据到参数"""
        self.container_params['internal_workflow'] = {
            'cards': self.internal_cards,
            'connections': self.internal_connections,
            'start_card_id': self.start_card_id
        }
        logger.info(f"保存容器 {self.container_id} 的内部工作流：{len(self.internal_cards)} 个卡片")
    
    def _setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 顶部提示
        info_label = QLabel(
            f"容器 ID: {self.container_id}\n"
            f"在下方画布中添加和管理子节点。子节点按顺序执行。"
        )
        info_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(info_label)
        
        # 画布区域
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        
        # 添加网格背景
        self._draw_grid()
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        layout.addWidget(self.view, 1)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # 添加卡片按钮
        self.add_card_btn = QPushButton("添加子节点")
        self.add_card_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbe;
            }
        """)
        self.add_card_btn.clicked.connect(self._add_sub_card)
        button_layout.addWidget(self.add_card_btn)
        
        button_layout.addStretch()
        
        # 保存按钮
        self.save_btn = QPushButton("保存并关闭")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
        """)
        self.save_btn.clicked.connect(self._save_and_close)
        button_layout.addWidget(self.save_btn)
        
        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _draw_grid(self):
        """绘制网格背景"""
        grid_size = 20
        grid_range = 2000
        
        # 绘制网格线
        pen = QPen(QColor("#333333"), 0.5)
        for x in range(-grid_range, grid_range + 1, grid_size):
            line = self.scene.addLine(x, -grid_range, x, grid_range, pen)
            line.setZValue(-1)
        for y in range(-grid_range, grid_range + 1, grid_size):
            line = self.scene.addLine(-grid_range, y, grid_range, y, pen)
            line.setZValue(-1)
        
        # 绘制坐标轴
        axis_pen = QPen(QColor("#555555"), 1)
        self.scene.addLine(-grid_range, 0, grid_range, 0, axis_pen)  # X 轴
        self.scene.addLine(0, -grid_range, 0, grid_range, axis_pen)  # Y 轴
    
    def _add_sub_card(self):
        """添加子卡片（简化版本：显示消息框）"""
        QMessageBox.information(
            self,
            "添加子节点",
            "子节点添加功能将在后续版本中实现。\n\n"
            "当前版本仅支持查看容器参数。"
        )
    
    def _save_and_close(self):
        """保存并关闭"""
        self._save_internal_workflow()
        self.accept()
    
    def get_workflow_data(self) -> Dict[str, Any]:
        """获取工作流数据"""
        return {
            'cards': self.internal_cards,
            'connections': self.internal_connections,
            'start_card_id': self.start_card_id
        }

# 导入 QPainter 用于类型检查
from PySide6.QtGui import QPainter
