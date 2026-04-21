"""
话术模板管理组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel,
                             QMessageBox, QHeaderView, QDialog, QFormLayout,
                             QDialogButtonBox, QTextEdit, QLineEdit, QComboBox)
from PyQt5.QtCore import Qt
from typing import Optional

from models.database import Database
from services.template_service import TemplateService
from utils.logger import Logger


class TemplateDialog(QDialog):
    """话术模板编辑对话框"""
    
    def __init__(self, parent=None, template_data=None):
        super().__init__(parent)
        self.template_data = template_data
        self.setWindowTitle("编辑话术模板" if template_data else "新建话术模板")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        self.setLayout(layout)
        
        self.name_input = QLineEdit()
        if self.template_data:
            self.name_input.setText(self.template_data.get('name', ''))
        layout.addRow("模板名称:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        if self.template_data:
            self.description_input.setPlainText(self.template_data.get('description', ''))
        layout.addRow("描述:", self.description_input)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["通用", "百家号", "小红书"])
        if self.template_data and self.template_data.get('platform'):
            platform_map = {"baijiahao": "百家号", "xiaohongshu": "小红书"}
            platform_text = platform_map.get(self.template_data['platform'], "通用")
            index = self.platform_combo.findText(platform_text)
            if index >= 0:
                self.platform_combo.setCurrentIndex(index)
        layout.addRow("适用平台:", self.platform_combo)
        
        self.content_input = QTextEdit()
        self.content_input.setMinimumHeight(200)
        if self.template_data:
            self.content_input.setPlainText(self.template_data.get('content', ''))
        layout.addRow("模板内容:", self.content_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("确定")
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_data(self):
        """获取表单数据"""
        platform_map = {"通用": None, "百家号": "baijiahao", "小红书": "xiaohongshu"}
        return {
            'name': self.name_input.text().strip(),
            'description': self.description_input.toPlainText().strip(),
            'content': self.content_input.toPlainText().strip(),
            'platform': platform_map.get(self.platform_combo.currentText())
        }


class TemplateWidget(QWidget):
    """话术模板管理组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("TemplateWidget")
        self.db = Database()
        self.template_service = TemplateService(self.db)
        self.init_ui()
        self.refresh_template_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("新建模板")
        self.add_btn.clicked.connect(self.add_template)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_template)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        platform_label = QLabel("平台筛选:")
        btn_layout.addWidget(platform_label)
        
        self.platform_filter = QComboBox()
        self.platform_filter.addItems(["全部", "通用", "百家号", "小红书"])
        self.platform_filter.currentTextChanged.connect(self.refresh_template_list)
        btn_layout.addWidget(self.platform_filter)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_template_list)
        btn_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(btn_layout)
        
        # 模板列表
        self.template_table = QTableWidget()
        self.template_table.setColumnCount(5)
        self.template_table.setHorizontalHeaderLabels([
            "ID", "模板名称", "描述", "平台", "创建时间"
        ])
        self.template_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.template_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.template_table.doubleClicked.connect(self.edit_template)
        layout.addWidget(self.template_table)
    
    def refresh_template_list(self):
        """刷新模板列表"""
        platform_filter = self.platform_filter.currentText()
        if platform_filter == "全部":
            templates = self.template_service.get_all_templates()
        elif platform_filter == "通用":
            templates = [t for t in self.template_service.get_all_templates() if not t.get('platform')]
        else:
            platform_map = {"百家号": "baijiahao", "小红书": "xiaohongshu"}
            platform = platform_map.get(platform_filter)
            templates = self.template_service.get_all_templates(platform)
        
        self.template_table.setRowCount(len(templates))
        
        def make_center_item(text):
            item = QTableWidgetItem(str(text) if text is not None else '')
            item.setTextAlignment(Qt.AlignCenter)
            return item

        for row, template in enumerate(templates):
            self.template_table.setItem(row, 0, make_center_item(template['id']))
            self.template_table.setItem(row, 1, make_center_item(template['name']))
            self.template_table.setItem(row, 2, make_center_item(template.get('description', '')[:50]))
            
            platform_text = template.get('platform', '') or '通用'
            platform_map = {"baijiahao": "百家号", "xiaohongshu": "小红书"}
            platform_text = platform_map.get(platform_text, platform_text)
            self.template_table.setItem(row, 3, make_center_item(platform_text))
            
            self.template_table.setItem(row, 4, make_center_item(template.get('created_at', '')))
    
    def add_template(self):
        """添加模板"""
        dialog = TemplateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name'] or not data['content']:
                QMessageBox.warning(self, "警告", "请填写模板名称和内容")
                return
            
            try:
                self.template_service.create_template(
                    data['name'], data['content'], 
                    data['description'], data['platform']
                )
                QMessageBox.information(self, "成功", "模板创建成功")
                self.refresh_template_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")
    
    def edit_template(self):
        """编辑模板"""
        selected_rows = self.template_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要编辑的模板")
            return
        
        row = selected_rows[0].row()
        template_id = int(self.template_table.item(row, 0).text())
        
        template = self.template_service.get_template_by_id(template_id)
        if not template:
            return
        
        dialog = TemplateDialog(self, template)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['name'] or not data['content']:
                QMessageBox.warning(self, "警告", "请填写模板名称和内容")
                return
            
            try:
                self.template_service.update_template(
                    template_id, data['name'], data['content'],
                    data['description'], data['platform']
                )
                QMessageBox.information(self, "成功", "模板更新成功")
                self.refresh_template_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")
    
    def delete_template(self):
        """删除模板"""
        selected_rows = self.template_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要删除的模板")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除选中的模板吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            row = selected_rows[0].row()
            template_id = int(self.template_table.item(row, 0).text())
            try:
                self.template_service.delete_template(template_id)
                QMessageBox.information(self, "成功", "模板删除成功")
                self.refresh_template_list()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

