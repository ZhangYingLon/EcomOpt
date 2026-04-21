"""
资源管理组件
"""
import os
import sys
import subprocess
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel,
                             QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from typing import Optional

from models.database import Database
from models.models import ResourcePackage
from utils.logger import Logger


class ResourceWidget(QWidget):
    """资源管理组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("ResourceWidget")
        self.db = Database()
        self.init_ui()
        self.refresh_resource_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_resource_list)
        btn_layout.addWidget(self.refresh_btn)
        
        self.open_dir_btn = QPushButton("打开资源包目录")
        self.open_dir_btn.clicked.connect(self.open_selected_resource_dir)
        btn_layout.addWidget(self.open_dir_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_selected_resource)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 资源包列表
        self.resource_table = QTableWidget()
        self.resource_table.setColumnCount(7)
        self.resource_table.setHorizontalHeaderLabels([
            "ID", "资源名称", "上传文件", "目录数", "已生成", "已发布", "创建时间"
        ])
        self.resource_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resource_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.resource_table)
    
    def _make_item(self, text, align_center=True):
        item = QTableWidgetItem(str(text) if text is not None else '')
        if align_center:
            item.setTextAlignment(Qt.AlignCenter)
        return item
    
    def refresh_resource_list(self):
        """刷新资源列表"""
        resources = ResourcePackage.get_all(self.db)
        self.resource_table.setRowCount(len(resources))
        
        for row, resource in enumerate(resources):
            self.resource_table.setItem(row, 0, self._make_item(resource['id']))
            self.resource_table.setItem(row, 1, self._make_item(resource['name']))
            self.resource_table.setItem(row, 2, self._make_item(resource.get('upload_filename', '')))
            self.resource_table.setItem(row, 3, self._make_item(resource['directory_count']))
            self.resource_table.setItem(row, 4, self._make_item(resource['content_generated']))
            self.resource_table.setItem(row, 5, self._make_item(resource['content_published']))
            self.resource_table.setItem(row, 6, self._make_item(resource.get('created_at', '')))
    
    def _open_directory(self, path: str) -> bool:
        """用系统默认方式打开目录"""
        p = Path(path)
        if not p.exists() or not p.is_dir():
            return False
        path_str = str(p.resolve())
        try:
            if sys.platform == 'win32':
                os.startfile(path_str)
            elif sys.platform == 'darwin':
                subprocess.run(['open', path_str], check=False)
            else:
                subprocess.run(['xdg-open', path_str], check=False)
            return True
        except Exception as e:
            self.logger.warning(f"打开目录失败: {e}")
            return False
    
    def open_selected_resource_dir(self):
        """打开选中资源包的目录"""
        selected = self.resource_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要打开的资源包")
            return
        row = selected[0].row()
        package_id = int(self.resource_table.item(row, 0).text())
        package = ResourcePackage.get_by_id(self.db, package_id)
        if not package:
            QMessageBox.warning(self, "警告", "资源包不存在")
            return
        base_path = package.get('base_path') or ''
        if not base_path:
            QMessageBox.warning(self, "警告", "该资源包没有目录路径")
            return
        if self._open_directory(base_path):
            QMessageBox.information(self, "提示", "已打开资源包目录")
        else:
            QMessageBox.warning(self, "警告", "目录不存在或无法打开")
    
    def delete_selected_resource(self):
        """删除选中的资源包（同时删除关联的内容记录）"""
        selected = self.resource_table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的资源包")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除选中的资源包吗？\n关联的内容记录将一并删除，磁盘文件不会删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        row = selected[0].row()
        package_id = int(self.resource_table.item(row, 0).text())
        try:
            self.db.execute_update("DELETE FROM contents WHERE resource_package_id = ?", (package_id,))
            self.db.execute_update("DELETE FROM resource_packages WHERE id = ?", (package_id,))
            self.refresh_resource_list()
            QMessageBox.information(self, "成功", "删除成功")
        except Exception as e:
            self.logger.error(f"删除资源包失败: {e}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

