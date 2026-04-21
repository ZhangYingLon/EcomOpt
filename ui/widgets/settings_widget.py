"""
设置功能组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QGroupBox, QFormLayout,
                             QMessageBox, QComboBox, QSpinBox, QCheckBox,
                             QFileDialog, QTabWidget)
from PyQt5.QtCore import Qt
import json

from config.config import Config
from utils.logger import Logger


class SettingsWidget(QWidget):
    """设置功能组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("SettingsWidget")
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Selenium设置
        selenium_tab = QWidget()
        selenium_layout = QVBoxLayout()
        selenium_tab.setLayout(selenium_layout)
        
        selenium_group = QGroupBox("Selenium自动化设置")
        selenium_form = QFormLayout()
        selenium_group.setLayout(selenium_form)
        
        self.headless_check = QCheckBox()
        self.headless_check.setText("无头模式（后台运行）")
        selenium_form.addRow("无头模式:", self.headless_check)
        
        self.wait_timeout_spin = QSpinBox()
        self.wait_timeout_spin.setRange(5, 60)
        self.wait_timeout_spin.setSuffix(" 秒")
        selenium_form.addRow("等待超时:", self.wait_timeout_spin)
        
        self.implicit_wait_spin = QSpinBox()
        self.implicit_wait_spin.setRange(1, 30)
        self.implicit_wait_spin.setSuffix(" 秒")
        selenium_form.addRow("隐式等待:", self.implicit_wait_spin)
        
        window_size_layout = QHBoxLayout()
        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(800, 3840)
        self.window_width_spin.setValue(1920)
        window_size_layout.addWidget(self.window_width_spin)
        
        window_size_layout.addWidget(QLabel(" x "))
        
        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(600, 2160)
        self.window_height_spin.setValue(1080)
        window_size_layout.addWidget(self.window_height_spin)
        
        selenium_form.addRow("窗口大小:", window_size_layout)
        
        selenium_layout.addWidget(selenium_group)
        selenium_layout.addStretch()
        
        tab_widget.addTab(selenium_tab, "Selenium设置")
        
        # AI设置
        ai_tab = QWidget()
        ai_layout = QVBoxLayout()
        ai_tab.setLayout(ai_layout)
        
        ai_group = QGroupBox("AI服务设置")
        ai_form = QFormLayout()
        ai_group.setLayout(ai_form)
        
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["openai", "baidu", "custom"])
        ai_form.addRow("AI提供商:", self.ai_provider_combo)
        
        self.ai_api_key_input = QLineEdit()
        self.ai_api_key_input.setEchoMode(QLineEdit.Password)
        self.ai_api_key_input.setPlaceholderText("请输入API Key")
        ai_form.addRow("API Key:", self.ai_api_key_input)
        
        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("例如: gpt-3.5-turbo")
        ai_form.addRow("模型名称:", self.ai_model_input)
        
        self.ai_max_tokens_spin = QSpinBox()
        self.ai_max_tokens_spin.setRange(500, 8000)
        self.ai_max_tokens_spin.setSuffix(" tokens")
        ai_form.addRow("最大Token:", self.ai_max_tokens_spin)
        
        ai_layout.addWidget(ai_group)
        ai_layout.addStretch()
        
        tab_widget.addTab(ai_tab, "AI设置")
        
        # 平台设置
        platform_tab = QWidget()
        platform_layout = QVBoxLayout()
        platform_tab.setLayout(platform_layout)
        
        platform_group = QGroupBox("平台配置")
        platform_form = QFormLayout()
        platform_group.setLayout(platform_form)
        
        self.baijiahao_url_input = QLineEdit()
        self.baijiahao_url_input.setPlaceholderText("https://baijiahao.baidu.com/")
        platform_form.addRow("百家号登录URL:", self.baijiahao_url_input)
        
        self.xiaohongshu_url_input = QLineEdit()
        self.xiaohongshu_url_input.setPlaceholderText("https://creator.xiaohongshu.com/")
        platform_form.addRow("小红书登录URL:", self.xiaohongshu_url_input)
        
        platform_layout.addWidget(platform_group)
        platform_layout.addStretch()
        
        tab_widget.addTab(platform_tab, "平台设置")
        
        # 保存和重置按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("重置为默认")
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """加载设置"""
        try:
            # 加载Selenium设置
            selenium_config = Config.SELENIUM_CONFIG
            self.headless_check.setChecked(selenium_config.get("headless", False))
            self.wait_timeout_spin.setValue(selenium_config.get("wait_timeout", 10))
            self.implicit_wait_spin.setValue(selenium_config.get("implicit_wait", 5))
            window_size = selenium_config.get("window_size", (1920, 1080))
            self.window_width_spin.setValue(window_size[0])
            self.window_height_spin.setValue(window_size[1])
            
            # 加载AI设置
            ai_config = Config.AI_CONFIG
            provider = ai_config.get("provider", "openai")
            index = self.ai_provider_combo.findText(provider)
            if index >= 0:
                self.ai_provider_combo.setCurrentIndex(index)
            self.ai_api_key_input.setText(ai_config.get("api_key", ""))
            self.ai_model_input.setText(ai_config.get("model", "gpt-3.5-turbo"))
            self.ai_max_tokens_spin.setValue(ai_config.get("max_tokens", 2000))
            
            # 加载平台设置
            platforms_config = Config.PLATFORMS
            self.baijiahao_url_input.setText(platforms_config.get("baijiahao", {}).get("login_url", ""))
            self.xiaohongshu_url_input.setText(platforms_config.get("xiaohongshu", {}).get("login_url", ""))
            
            self.logger.info("设置加载成功")
        except Exception as e:
            self.logger.error(f"加载设置失败: {str(e)}")
            QMessageBox.warning(self, "警告", f"加载设置失败: {str(e)}")
    
    def save_settings(self):
        """保存设置"""
        try:
            settings = {}
            
            # 保存Selenium设置
            settings["selenium"] = {
                "headless": self.headless_check.isChecked(),
                "wait_timeout": self.wait_timeout_spin.value(),
                "implicit_wait": self.implicit_wait_spin.value(),
                "window_size": [self.window_width_spin.value(), self.window_height_spin.value()]
            }
            
            # 保存AI设置
            settings["ai"] = {
                "provider": self.ai_provider_combo.currentText(),
                "api_key": self.ai_api_key_input.text(),
                "model": self.ai_model_input.text(),
                "max_tokens": self.ai_max_tokens_spin.value()
            }
            
            # 保存平台设置
            settings["platforms"] = {
                "baijiahao": {
                    "login_url": self.baijiahao_url_input.text()
                },
                "xiaohongshu": {
                    "login_url": self.xiaohongshu_url_input.text()
                }
            }
            
            # 保存到文件
            Config.save_config(settings, "settings.json")
            
            # 更新内存中的配置
            Config.SELENIUM_CONFIG.update(settings["selenium"])
            Config.AI_CONFIG.update(settings["ai"])
            Config.PLATFORMS["baijiahao"].update(settings["platforms"]["baijiahao"])
            Config.PLATFORMS["xiaohongshu"].update(settings["platforms"]["xiaohongshu"])
            
            QMessageBox.information(self, "成功", "设置保存成功！部分设置需要重启程序才能生效。")
            self.logger.info("设置保存成功")
        except Exception as e:
            self.logger.error(f"保存设置失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
    
    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 重置为默认值
            self.headless_check.setChecked(False)
            self.wait_timeout_spin.setValue(10)
            self.implicit_wait_spin.setValue(5)
            self.window_width_spin.setValue(1920)
            self.window_height_spin.setValue(1080)
            
            self.ai_provider_combo.setCurrentIndex(0)
            self.ai_api_key_input.clear()
            self.ai_model_input.setText("gpt-3.5-turbo")
            self.ai_max_tokens_spin.setValue(2000)
            
            self.baijiahao_url_input.setText("https://baijiahao.baidu.com/")
            self.xiaohongshu_url_input.setText("https://creator.xiaohongshu.com/")
            
            QMessageBox.information(self, "成功", "设置已重置为默认值")

