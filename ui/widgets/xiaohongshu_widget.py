"""
小红书功能组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextEdit, QLineEdit, QLabel, QGroupBox, QFormLayout,
                             QMessageBox, QProgressBar, QListWidget, QSplitter,
                             QFileDialog, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from typing import Optional, List
from pathlib import Path

from platforms.xiaohongshu_platform import XiaohongshuPlatform
from core.ai_service import AIService
from utils.logger import Logger


class LoginThread(QThread):
    """登录线程"""
    login_finished = pyqtSignal(bool, str)
    
    def __init__(self, platform: XiaohongshuPlatform, username: str, password: str):
        super().__init__()
        self.platform = platform
        self.username = username
        self.password = password
    
    def run(self):
        try:
            success = self.platform.login(self.username, self.password)
            message = "登录成功" if success else "登录失败，请检查账号密码"
            self.login_finished.emit(success, message)
        except Exception as e:
            self.login_finished.emit(False, f"登录异常: {str(e)}")


class PublishThread(QThread):
    """发布线程"""
    publish_finished = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, platform: XiaohongshuPlatform, title: str, content: str, **kwargs):
        super().__init__()
        self.platform = platform
        self.title = title
        self.content = content
        self.kwargs = kwargs
    
    def run(self):
        try:
            self.progress_updated.emit(20, "开始发布...")
            success = self.platform.publish_article(self.title, self.content, **self.kwargs)
            message = "发布成功" if success else "发布失败"
            self.progress_updated.emit(100, message)
            self.publish_finished.emit(success, message)
        except Exception as e:
            self.publish_finished.emit(False, f"发布异常: {str(e)}")


class XiaohongshuWidget(QWidget):
    """小红书功能组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("XiaohongshuWidget")
        self.platform: Optional[XiaohongshuPlatform] = None
        self.ai_service = AIService()
        self.login_thread: Optional[LoginThread] = None
        self.publish_thread: Optional[PublishThread] = None
        self.image_paths: List[str] = []
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # 左侧：登录和笔记列表
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 登录区域
        login_group = QGroupBox("账号登录")
        login_layout = QFormLayout()
        login_group.setLayout(login_layout)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入手机号/账号")
        login_layout.addRow("账号:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入密码")
        login_layout.addRow("密码:", self.password_input)
        
        self.login_btn = QPushButton("登录")
        self.login_btn.clicked.connect(self.handle_login)
        login_layout.addRow(self.login_btn)
        
        self.login_status_label = QLabel("未登录")
        self.login_status_label.setStyleSheet("color: red;")
        login_layout.addRow("状态:", self.login_status_label)
        
        left_layout.addWidget(login_group)
        
        # 笔记列表区域
        list_group = QGroupBox("笔记列表")
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        
        self.note_list = QListWidget()
        list_layout.addWidget(self.note_list)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_note_list)
        list_layout.addWidget(refresh_btn)
        
        left_layout.addWidget(list_group)
        left_layout.addStretch()
        
        splitter.addWidget(left_widget)
        
        # 右侧：笔记编辑和发布
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 笔记编辑区域
        edit_group = QGroupBox("笔记编辑")
        edit_layout = QVBoxLayout()
        edit_group.setLayout(edit_layout)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("请输入笔记标题（建议包含表情符号）")
        edit_layout.addWidget(QLabel("标题:"))
        edit_layout.addWidget(self.title_input)
        
        edit_layout.addWidget(QLabel("内容:"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("请输入笔记内容...")
        edit_layout.addWidget(self.content_input)
        
        # 图片选择区域
        image_group = QGroupBox("图片选择")
        image_layout = QVBoxLayout()
        image_group.setLayout(image_layout)
        
        image_btn_layout = QHBoxLayout()
        add_image_btn = QPushButton("添加图片")
        add_image_btn.clicked.connect(self.add_images)
        image_btn_layout.addWidget(add_image_btn)
        
        clear_image_btn = QPushButton("清空图片")
        clear_image_btn.clicked.connect(self.clear_images)
        image_btn_layout.addWidget(clear_image_btn)
        image_layout.addLayout(image_btn_layout)
        
        self.image_list = QListWidget()
        self.image_list.setMaximumHeight(100)
        image_layout.addWidget(self.image_list)
        
        edit_layout.addWidget(image_group)
        
        # AI辅助按钮
        ai_btn_layout = QHBoxLayout()
        ai_generate_btn = QPushButton("AI生成标题")
        ai_generate_btn.clicked.connect(self.ai_generate_title)
        ai_btn_layout.addWidget(ai_generate_btn)
        
        ai_optimize_btn = QPushButton("AI优化内容")
        ai_optimize_btn.clicked.connect(self.ai_optimize_content)
        ai_btn_layout.addWidget(ai_optimize_btn)
        
        ai_tags_btn = QPushButton("AI生成标签")
        ai_tags_btn.clicked.connect(self.ai_generate_tags)
        ai_btn_layout.addWidget(ai_tags_btn)
        edit_layout.addLayout(ai_btn_layout)
        
        right_layout.addWidget(edit_group)
        
        # 发布区域
        publish_group = QGroupBox("发布设置")
        publish_layout = QVBoxLayout()
        publish_group.setLayout(publish_layout)
        
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("标签（用逗号分隔，或以#开头）")
        publish_layout.addWidget(QLabel("标签:"))
        publish_layout.addWidget(self.tags_input)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        publish_layout.addWidget(self.progress_bar)
        
        publish_btn = QPushButton("发布笔记")
        publish_btn.clicked.connect(self.handle_publish)
        publish_layout.addWidget(publish_btn)
        
        right_layout.addWidget(publish_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
    
    def handle_login(self):
        """处理登录"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "警告", "请输入账号和密码")
            return
        
        self.login_btn.setEnabled(False)
        self.login_status_label.setText("登录中...")
        self.login_status_label.setStyleSheet("color: orange;")
        
        if not self.platform:
            self.platform = XiaohongshuPlatform()
        
        self.login_thread = LoginThread(self.platform, username, password)
        self.login_thread.login_finished.connect(self.on_login_finished)
        self.login_thread.start()
    
    def on_login_finished(self, success: bool, message: str):
        """登录完成回调"""
        self.login_btn.setEnabled(True)
        
        if success:
            self.login_status_label.setText("已登录")
            self.login_status_label.setStyleSheet("color: green;")
            QMessageBox.information(self, "成功", message)
        else:
            self.login_status_label.setText("登录失败")
            self.login_status_label.setStyleSheet("color: red;")
            QMessageBox.warning(self, "失败", message)
    
    def handle_publish(self):
        """处理发布"""
        if not self.platform or not self.platform.check_login_status():
            QMessageBox.warning(self, "警告", "请先登录")
            return
        
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        
        if not title or not content:
            QMessageBox.warning(self, "警告", "请输入标题和内容")
            return
        
        # 获取标签
        tags = []
        tags_text = self.tags_input.text().strip()
        if tags_text:
            tags = [tag.strip().lstrip('#') for tag in tags_text.split(',')]
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.publish_thread = PublishThread(
            self.platform, 
            title, 
            content, 
            tags=tags,
            images=self.image_paths if self.image_paths else None
        )
        self.publish_thread.publish_finished.connect(self.on_publish_finished)
        self.publish_thread.progress_updated.connect(self.on_progress_updated)
        self.publish_thread.start()
    
    def on_publish_finished(self, success: bool, message: str):
        """发布完成回调"""
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            # 清空输入
            self.title_input.clear()
            self.content_input.clear()
            self.tags_input.clear()
            self.clear_images()
        else:
            QMessageBox.warning(self, "失败", message)
    
    def on_progress_updated(self, value: int, message: str):
        """进度更新回调"""
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"{message} - {value}%")
    
    def add_images(self):
        """添加图片"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("图片文件 (*.png *.jpg *.jpeg *.gif *.bmp)")
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            for file_path in selected_files:
                if file_path not in self.image_paths:
                    self.image_paths.append(file_path)
                    item = QListWidgetItem(Path(file_path).name)
                    self.image_list.addItem(item)
    
    def clear_images(self):
        """清空图片"""
        self.image_paths.clear()
        self.image_list.clear()
    
    def ai_generate_title(self):
        """AI生成标题"""
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请先输入内容")
            return
        
        try:
            title = self.ai_service.generate_title(content, platform="xiaohongshu")
            if title:
                self.title_input.setText(title.strip())
                QMessageBox.information(self, "成功", "标题生成成功")
            else:
                QMessageBox.warning(self, "失败", "标题生成失败，请检查AI配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"AI生成失败: {str(e)}")
    
    def ai_optimize_content(self):
        """AI优化内容"""
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请先输入内容")
            return
        
        try:
            optimized = self.ai_service.optimize_content(content, platform="xiaohongshu")
            if optimized:
                self.content_input.setPlainText(optimized.strip())
                QMessageBox.information(self, "成功", "内容优化成功")
            else:
                QMessageBox.warning(self, "失败", "内容优化失败，请检查AI配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"AI优化失败: {str(e)}")
    
    def ai_generate_tags(self):
        """AI生成标签"""
        content = self.content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请先输入内容")
            return
        
        try:
            tags = self.ai_service.generate_tags(content, platform="xiaohongshu", count=5)
            if tags:
                tags_text = ", ".join(tags)
                self.tags_input.setText(tags_text)
                QMessageBox.information(self, "成功", "标签生成成功")
            else:
                QMessageBox.warning(self, "失败", "标签生成失败，请检查AI配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"AI生成标签失败: {str(e)}")
    
    def refresh_note_list(self):
        """刷新笔记列表"""
        if not self.platform or not self.platform.check_login_status():
            QMessageBox.warning(self, "警告", "请先登录")
            return
        
        try:
            notes = self.platform.get_article_list()
            self.note_list.clear()
            for note in notes:
                self.note_list.addItem(note.get("title", "未知标题"))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取笔记列表失败: {str(e)}")
    
    def cleanup(self):
        """清理资源"""
        if self.platform:
            try:
                self.platform.close()
            except:
                pass

