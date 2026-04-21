"""
AI工具功能组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTextEdit, QLineEdit, QLabel, QGroupBox, QFormLayout,
                             QMessageBox, QComboBox, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from typing import Optional

from core.ai_service import AIService
from utils.logger import Logger


class AIGenerateThread(QThread):
    """AI生成线程"""
    generate_finished = pyqtSignal(bool, str)
    
    def __init__(self, ai_service: AIService, prompt: str, max_tokens: int = 2000):
        super().__init__()
        self.ai_service = ai_service
        self.prompt = prompt
        self.max_tokens = max_tokens
    
    def run(self):
        try:
            result = self.ai_service.generate_content(self.prompt, self.max_tokens)
            if result:
                self.generate_finished.emit(True, result)
            else:
                self.generate_finished.emit(False, "生成失败，请检查AI配置")
        except Exception as e:
            self.generate_finished.emit(False, f"生成异常: {str(e)}")


class AIWidget(QWidget):
    """AI工具功能组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("AIWidget")
        self.ai_service = AIService()
        self.generate_thread: Optional[AIGenerateThread] = None
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # AI内容生成区域
        generate_group = QGroupBox("AI内容生成")
        generate_layout = QVBoxLayout()
        generate_group.setLayout(generate_layout)
        
        # 提示词输入
        generate_layout.addWidget(QLabel("提示词:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("请输入您的需求，AI将为您生成内容...")
        self.prompt_input.setMaximumHeight(150)
        generate_layout.addWidget(self.prompt_input)
        
        # 生成选项
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("平台:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["通用", "百家号", "小红书"])
        options_layout.addWidget(self.platform_combo)
        
        options_layout.addWidget(QLabel("最大Token:"))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setValue(2000)
        options_layout.addWidget(self.max_tokens_spin)
        
        options_layout.addStretch()
        generate_layout.addLayout(options_layout)
        
        # 生成按钮
        generate_btn = QPushButton("生成内容")
        generate_btn.clicked.connect(self.handle_generate)
        generate_layout.addWidget(generate_btn)
        
        # 生成结果
        generate_layout.addWidget(QLabel("生成结果:"))
        self.result_output = QTextEdit()
        self.result_output.setPlaceholderText("生成的内容将显示在这里...")
        generate_layout.addWidget(self.result_output)
        
        # 操作按钮
        result_btn_layout = QHBoxLayout()
        
        copy_btn = QPushButton("复制结果")
        copy_btn.clicked.connect(self.copy_result)
        result_btn_layout.addWidget(copy_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_result)
        result_btn_layout.addWidget(clear_btn)
        
        result_btn_layout.addStretch()
        generate_layout.addLayout(result_btn_layout)
        
        layout.addWidget(generate_group)
        
        # AI内容优化区域
        optimize_group = QGroupBox("AI内容优化")
        optimize_layout = QVBoxLayout()
        optimize_group.setLayout(optimize_layout)
        
        optimize_layout.addWidget(QLabel("待优化内容:"))
        self.optimize_input = QTextEdit()
        self.optimize_input.setPlaceholderText("请输入需要优化的内容...")
        self.optimize_input.setMaximumHeight(150)
        optimize_layout.addWidget(self.optimize_input)
        
        # 优化选项
        optimize_options_layout = QHBoxLayout()
        optimize_options_layout.addWidget(QLabel("平台:"))
        self.optimize_platform_combo = QComboBox()
        self.optimize_platform_combo.addItems(["通用", "百家号", "小红书"])
        optimize_options_layout.addWidget(self.optimize_platform_combo)
        optimize_options_layout.addStretch()
        optimize_layout.addLayout(optimize_options_layout)
        
        optimize_btn = QPushButton("优化内容")
        optimize_btn.clicked.connect(self.handle_optimize)
        optimize_layout.addWidget(optimize_btn)
        
        optimize_layout.addWidget(QLabel("优化结果:"))
        self.optimize_output = QTextEdit()
        self.optimize_output.setPlaceholderText("优化后的内容将显示在这里...")
        optimize_layout.addWidget(self.optimize_output)
        
        layout.addWidget(optimize_group)
        
        # AI标题生成区域
        title_group = QGroupBox("AI标题生成")
        title_layout = QVBoxLayout()
        title_group.setLayout(title_layout)
        
        title_layout.addWidget(QLabel("内容摘要:"))
        self.title_content_input = QTextEdit()
        self.title_content_input.setPlaceholderText("请输入内容摘要，AI将为您生成标题...")
        self.title_content_input.setMaximumHeight(100)
        title_layout.addWidget(self.title_content_input)
        
        title_options_layout = QHBoxLayout()
        title_options_layout.addWidget(QLabel("平台:"))
        self.title_platform_combo = QComboBox()
        self.title_platform_combo.addItems(["通用", "百家号", "小红书"])
        title_options_layout.addWidget(self.title_platform_combo)
        title_options_layout.addStretch()
        title_layout.addLayout(title_options_layout)
        
        title_btn = QPushButton("生成标题")
        title_btn.clicked.connect(self.handle_generate_title)
        title_layout.addWidget(title_btn)
        
        title_layout.addWidget(QLabel("生成的标题:"))
        self.title_output = QLineEdit()
        self.title_output.setReadOnly(True)
        title_layout.addWidget(self.title_output)
        
        layout.addWidget(title_group)
        
        layout.addStretch()
    
    def handle_generate(self):
        """处理内容生成"""
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "警告", "请输入提示词")
            return
        
        platform_map = {
            "通用": "general",
            "百家号": "baijiahao",
            "小红书": "xiaohongshu"
        }
        platform = platform_map.get(self.platform_combo.currentText(), "general")
        
        # 添加平台特定的提示
        platform_prompts = {
            "baijiahao": "请为百家号撰写以下内容：\n\n",
            "xiaohongshu": "请为小红书撰写以下内容（要求活泼有趣，符合小红书风格）：\n\n",
            "general": ""
        }
        
        full_prompt = platform_prompts.get(platform, "") + prompt
        
        max_tokens = self.max_tokens_spin.value()
        
        self.result_output.clear()
        self.result_output.setPlainText("正在生成，请稍候...")
        
        self.generate_thread = AIGenerateThread(self.ai_service, full_prompt, max_tokens)
        self.generate_thread.generate_finished.connect(self.on_generate_finished)
        self.generate_thread.start()
    
    def on_generate_finished(self, success: bool, result: str):
        """生成完成回调"""
        if success:
            self.result_output.setPlainText(result)
            QMessageBox.information(self, "成功", "内容生成成功")
        else:
            self.result_output.clear()
            QMessageBox.warning(self, "失败", result)
    
    def handle_optimize(self):
        """处理内容优化"""
        content = self.optimize_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入待优化内容")
            return
        
        platform_map = {
            "通用": "general",
            "百家号": "baijiahao",
            "小红书": "xiaohongshu"
        }
        platform = platform_map.get(self.optimize_platform_combo.currentText(), "general")
        
        try:
            self.optimize_output.setPlainText("正在优化，请稍候...")
            optimized = self.ai_service.optimize_content(content, platform=platform)
            if optimized:
                self.optimize_output.setPlainText(optimized)
                QMessageBox.information(self, "成功", "内容优化成功")
            else:
                self.optimize_output.clear()
                QMessageBox.warning(self, "失败", "内容优化失败，请检查AI配置")
        except Exception as e:
            self.optimize_output.clear()
            QMessageBox.critical(self, "错误", f"优化失败: {str(e)}")
    
    def handle_generate_title(self):
        """处理标题生成"""
        content = self.title_content_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入内容摘要")
            return
        
        platform_map = {
            "通用": "general",
            "百家号": "baijiahao",
            "小红书": "xiaohongshu"
        }
        platform = platform_map.get(self.title_platform_combo.currentText(), "general")
        
        try:
            self.title_output.clear()
            title = self.ai_service.generate_title(content, platform=platform)
            if title:
                self.title_output.setText(title.strip())
                QMessageBox.information(self, "成功", "标题生成成功")
            else:
                QMessageBox.warning(self, "失败", "标题生成失败，请检查AI配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"标题生成失败: {str(e)}")
    
    def copy_result(self):
        """复制结果"""
        text = self.result_output.toPlainText()
        if text:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "成功", "内容已复制到剪贴板")
        else:
            QMessageBox.warning(self, "警告", "没有可复制的内容")
    
    def clear_result(self):
        """清空结果"""
        self.result_output.clear()

