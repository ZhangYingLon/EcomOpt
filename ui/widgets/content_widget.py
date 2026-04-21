"""
内容管理组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
                             QMessageBox, QHeaderView, QComboBox, QListWidget,
                             QSplitter, QTextEdit, QLineEdit, QDialog,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from typing import Optional, List

from models.database import Database
from models.models import ResourcePackage, Content, Template, Account
from services.content_service import ContentService
from services.ai_service import AIService
from services.file_service import FileService
from utils.logger import Logger


class ContentEditDialog(QDialog):
    """内容编辑与AI优化对话框"""
    
    def __init__(self, parent, content: dict, ai_service: AIService):
        super().__init__(parent)
        self.content = content
        self.ai_service = ai_service
        self.setWindowTitle("编辑内容")
        self.setMinimumSize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_edit.setText(self.content.get('title') or '')
        self.title_edit.setPlaceholderText("标题")
        form.addRow("标题:", self.title_edit)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.content.get('content') or '')
        self.content_edit.setPlaceholderText("正文内容")
        form.addRow("内容:", self.content_edit)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        self.optimize_btn = QPushButton("AI 优化")
        self.optimize_btn.clicked.connect(self.on_ai_optimize)
        btn_layout.addWidget(self.optimize_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Save)
        if ok_btn:
            ok_btn.setText("确定")
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.accepted.connect(self.save_and_close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_ai_optimize(self):
        text = self.content_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先输入要优化的内容")
            return
        self.optimize_btn.setEnabled(False)
        try:
            optimized = self.ai_service.optimize_content(text, platform="xiaohongshu")
            if optimized:
                self.content_edit.setPlainText(optimized)
                QMessageBox.information(self, "成功", "AI 优化完成")
            else:
                QMessageBox.warning(self, "提示", "AI 优化未返回结果，请检查 API 配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"AI 优化失败: {str(e)}")
        finally:
            self.optimize_btn.setEnabled(True)
    
    def save_and_close(self):
        title = self.title_edit.text().strip()
        content_text = self.content_edit.toPlainText()
        Content.update(self.parent().db, self.content['id'], title=title or None, content=content_text or None)
        self.parent().refresh_content_list()
        self.accept()


class GenerateContentThread(QThread):
    """生成内容线程"""
    generate_progress = pyqtSignal(int, str)
    generate_finished = pyqtSignal(bool, str)
    
    def __init__(self, content_service: ContentService, 
                 resource_package_ids: List[int], template_id: int):
        super().__init__()
        self.content_service = content_service
        self.resource_package_ids = resource_package_ids
        self.template_id = template_id
    
    def run(self):
        try:
            total = len(self.resource_package_ids)
            for idx, package_id in enumerate(self.resource_package_ids):
                self.generate_progress.emit(
                    int((idx / total) * 100), 
                    f"正在生成资源包 {package_id} 的内容..."
                )
                self.content_service.generate_content_from_resource(package_id, self.template_id)
            
            self.generate_progress.emit(100, "生成完成")
            self.generate_finished.emit(True, f"成功生成 {total} 条内容")
        except Exception as e:
            self.generate_finished.emit(False, f"生成失败: {str(e)}")


class PublishThread(QThread):
    """发布线程"""
    publish_progress = pyqtSignal(int, str)  # 进度, 消息
    publish_finished = pyqtSignal(bool, str, list)  # 成功, 消息, 已发布ID列表
    
    def __init__(self, content_service, content_ids, account_ids, platform):
        super().__init__()
        self.content_service = content_service
        self.content_ids = content_ids
        self.account_ids = account_ids
        self.platform = platform
    
    def run(self):
        try:
            total = len(self.content_ids) * len(self.account_ids)
            current = 0
            published_count = 0
            
            for content_id in self.content_ids:
                for account_id in self.account_ids:
                    current += 1
                    progress = int((current / total) * 100)
                    self.publish_progress.emit(progress, f"正在发布 {current}/{total}...")
                    
                    try:
                        self.content_service.publish_content(
                            content_id, account_id, self.platform
                        )
                        published_count += 1
                    except Exception as e:
                        self.publish_progress.emit(progress, f"内容 {content_id} 发布失败: {str(e)}")
            
            self.publish_finished.emit(True, f"{published_count} 条作品已发布", self.content_ids)
        except Exception as e:
            self.publish_finished.emit(False, f"发布异常: {str(e)}", [])


class ContentWidget(QWidget):
    """内容管理组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("ContentWidget")
        self.db = Database()
        ai_service = AIService()
        file_service = FileService(self.db)
        self.content_service = ContentService(self.db, ai_service, file_service)
        self.generate_thread: Optional[GenerateContentThread] = None
        self.init_ui()
        self.refresh_content_list()
        self.refresh_resource_list()
        self.refresh_template_list()
        self.refresh_account_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：生成区域
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 资源包选择
        resource_group = QGroupBox("选择资源包")
        resource_layout = QVBoxLayout()
        resource_group.setLayout(resource_layout)
        
        resource_header = QHBoxLayout()
        resource_header.addWidget(QLabel("资源包"))
        resource_refresh_btn = QPushButton("刷新")
        resource_refresh_btn.clicked.connect(self.refresh_resource_list)
        resource_header.addWidget(resource_refresh_btn)
        resource_header.addStretch()
        resource_layout.addLayout(resource_header)
        
        self.resource_list = QListWidget()
        self.resource_list.setSelectionMode(QListWidget.MultiSelection)
        resource_layout.addWidget(self.resource_list)
        
        left_layout.addWidget(resource_group)
        
        # 模板选择
        template_group = QGroupBox("选择话术模板")
        template_layout = QVBoxLayout()
        template_group.setLayout(template_layout)
        
        template_header = QHBoxLayout()
        template_header.addWidget(QLabel("话术模板"))
        template_refresh_btn = QPushButton("刷新")
        template_refresh_btn.clicked.connect(self.refresh_template_list)
        template_header.addWidget(template_refresh_btn)
        template_header.addStretch()
        template_layout.addLayout(template_header)
        
        self.template_combo = QComboBox()
        template_layout.addWidget(self.template_combo)
        
        left_layout.addWidget(template_group)
        
        # 生成时使用的 AI 模型
        ai_group = QGroupBox("生成使用模型")
        ai_layout = QVBoxLayout()
        ai_group.setLayout(ai_layout)
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["通义千问", "百度千帆"])
        ai_layout.addWidget(self.ai_provider_combo)
        left_layout.addWidget(ai_group)
        
        # 生成按钮
        self.generate_btn = QPushButton("批量生成内容")
        self.generate_btn.clicked.connect(self.batch_generate_content)
        left_layout.addWidget(self.generate_btn)
        
        left_layout.addStretch()
        splitter.addWidget(left_widget)
        
        # 右侧：内容列表和发布
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 内容列表
        content_header = QHBoxLayout()
        content_header.addWidget(QLabel("内容列表:"))
        content_refresh_btn = QPushButton("刷新")
        content_refresh_btn.clicked.connect(self.refresh_content_list)
        content_header.addWidget(content_refresh_btn)
        edit_content_btn = QPushButton("编辑/优化")
        edit_content_btn.clicked.connect(self.view_content_detail)
        content_header.addWidget(edit_content_btn)
        delete_content_btn = QPushButton("删除")
        delete_content_btn.clicked.connect(self.delete_selected_content)
        content_header.addWidget(delete_content_btn)
        content_header.addStretch()
        right_layout.addLayout(content_header)
        
        self.content_table = QTableWidget()
        self.content_table.setColumnCount(6)
        self.content_table.setHorizontalHeaderLabels([
            "ID", "资源包", "标题", "状态", "账号", "创建时间"
        ])
        self.content_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.content_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.content_table.doubleClicked.connect(self.view_content_detail)
        right_layout.addWidget(self.content_table)
        
        # 发布区域
        publish_group = QGroupBox("批量发布")
        publish_layout = QVBoxLayout()
        publish_group.setLayout(publish_layout)
        
        account_header = QHBoxLayout()
        account_header.addWidget(QLabel("选择账号:"))
        account_refresh_btn = QPushButton("刷新")
        account_refresh_btn.clicked.connect(self.refresh_account_list)
        account_header.addWidget(account_refresh_btn)
        account_header.addStretch()
        publish_layout.addLayout(account_header)
        
        self.account_list = QListWidget()
        self.account_list.setSelectionMode(QListWidget.MultiSelection)
        publish_layout.addWidget(self.account_list)
        
        platform_label = QLabel("平台:")
        publish_layout.addWidget(platform_label)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["百家号", "小红书"])
        publish_layout.addWidget(self.platform_combo)
        
        self.publish_btn = QPushButton("批量发布")
        self.publish_btn.clicked.connect(self.batch_publish_content)
        publish_layout.addWidget(self.publish_btn)
        
        right_layout.addWidget(publish_group)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
    
    def refresh_resource_list(self):
        """刷新资源包列表"""
        self.resource_list.clear()
        resources = ResourcePackage.get_all(self.db)
        for resource in resources:
            self.resource_list.addItem(f"{resource['id']} - {resource['name']}")
    
    def refresh_template_list(self):
        """刷新模板列表"""
        self.template_combo.clear()
        templates = Template.get_all(self.db)
        for template in templates:
            self.template_combo.addItem(template['name'], template['id'])
    
    def refresh_account_list(self):
        """刷新账号列表"""
        self.account_list.clear()
        accounts = Account.get_all(self.db)
        for account in accounts:
            if account['status'] == 'valid':
                self.account_list.addItem(f"{account['id']} - {account['platform']} - {account['username']}")
    
    def _make_center_item(self, text):
        item = QTableWidgetItem(str(text) if text is not None else '')
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def refresh_content_list(self):
        """刷新内容列表"""
        contents = Content.get_all(self.db)
        
        self.content_table.setRowCount(len(contents))
        
        for row, content in enumerate(contents):
            self.content_table.setItem(row, 0, self._make_center_item(content['id']))
            self.content_table.setItem(row, 1, self._make_center_item(content.get('resource_name', '')))
            self.content_table.setItem(row, 2, self._make_center_item(content.get('title', '')[:50]))
            
            status_raw = content.get('status', 'pending')
            status_display = '已发布' if status_raw == 'published' else '待发布'
            status_item = self._make_center_item(status_display)
            if status_raw == 'published':
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.darkYellow)
            self.content_table.setItem(row, 3, status_item)
            
            self.content_table.setItem(row, 4, self._make_center_item(content.get('account_nickname', '')))
            self.content_table.setItem(row, 5, self._make_center_item(content.get('created_at', '')))
    
    def batch_generate_content(self):
        """批量生成内容"""
        selected_items = self.resource_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择资源包")
            return
        
        template_id = self.template_combo.currentData()
        if not template_id:
            QMessageBox.warning(self, "警告", "请选择话术模板")
            return
        
        resource_package_ids = []
        for item in selected_items:
            package_id = int(item.text().split(' - ')[0])
            resource_package_ids.append(package_id)
        
        provider_map = {"通义千问": "dashscope", "百度千帆": "qianfan"}
        provider = provider_map.get(self.ai_provider_combo.currentText(), "dashscope")
        ai_service = AIService(provider=provider)
        file_service = FileService(self.db)
        content_service_for_generate = ContentService(self.db, ai_service, file_service)
        
        self.generate_btn.setEnabled(False)
        self.generate_thread = GenerateContentThread(
            content_service_for_generate, resource_package_ids, template_id
        )
        self.generate_thread.generate_finished.connect(self.on_generate_finished)
        self.generate_thread.start()
    
    def on_generate_finished(self, success: bool, message: str):
        """生成完成回调"""
        self.generate_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "成功", message)
            self.refresh_content_list()
            self.refresh_resource_list()
        else:
            QMessageBox.warning(self, "失败", message)
    
    def batch_publish_content(self):
        """批量发布内容（异步）"""
        selected_rows = self.content_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要发布的内容")
            return
        
        selected_accounts = self.account_list.selectedItems()
        if not selected_accounts:
            QMessageBox.warning(self, "警告", "请选择账号")
            return
        
        platform_map = {"百家号": "baijiahao", "小红书": "xiaohongshu"}
        platform = platform_map.get(self.platform_combo.currentText(), "")
        
        content_ids = []
        for row_index in selected_rows:
            content_id = int(self.content_table.item(row_index.row(), 0).text())
            content_ids.append(content_id)
        
        account_ids = []
        for item in selected_accounts:
            account_id = int(item.text().split(' - ')[0])
            account_ids.append(account_id)
        
        # 禁用按钮，显示进度
        self.publish_btn.setEnabled(False)
        self.publish_btn.setText("发布中...")
        
        # 创建并发布线程
        self.publish_thread = PublishThread(
            self.content_service, content_ids, account_ids, platform
        )
        self.publish_thread.publish_progress.connect(self.on_publish_progress)
        self.publish_thread.publish_finished.connect(self.on_publish_finished)
        self.publish_thread.start()
    
    def on_publish_progress(self, progress: int, message: str):
        """发布进度回调"""
        self.publish_btn.setText(f"{message} ({progress}%)")
    
    def on_publish_finished(self, success: bool, message: str, published_ids: list):
        """发布完成回调"""
        self.publish_btn.setEnabled(True)
        self.publish_btn.setText("批量发布")
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.refresh_content_list()
        else:
            QMessageBox.critical(self, "错误", message)
    
    def delete_selected_content(self):
        """删除选中的内容"""
        selected_rows = self.content_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要删除的内容")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 条内容吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            for row_index in selected_rows:
                content_id = int(self.content_table.item(row_index.row(), 0).text())
                self.content_service.delete_content(content_id)
            self.refresh_content_list()
            QMessageBox.information(self, "成功", "删除成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def view_content_detail(self):
        """查看/编辑内容详情（可编辑、AI 优化并保存）"""
        selected_rows = self.content_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择一条内容")
            return
        row = selected_rows[0].row()
        content_id = int(self.content_table.item(row, 0).text())
        contents = Content.get_all(self.db)
        content = next((c for c in contents if c['id'] == content_id), None)
        if not content:
            QMessageBox.warning(self, "提示", "内容不存在")
            return
        ai_service = AIService()
        dialog = ContentEditDialog(self, content, ai_service)
        dialog.exec_()
    
    def cleanup(self):
        """清理资源"""
        pass

