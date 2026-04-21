"""
设置功能组件 - 新版（支持国内大模型）
"""
from pathlib import Path

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QGroupBox, QFormLayout,
                             QMessageBox, QComboBox, QSpinBox, QCheckBox,
                             QTabWidget, QListWidget, QTextEdit, QSplitter,
                             QPlainTextEdit)
from PyQt5.QtCore import Qt

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
        
        # AI设置
        ai_tab = QWidget()
        ai_layout = QVBoxLayout()
        ai_tab.setLayout(ai_layout)
        
        ai_group = QGroupBox("AI服务设置")
        ai_form = QFormLayout()
        ai_group.setLayout(ai_form)
        
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["dashscope", "qianfan"])
        self.ai_provider_combo.currentTextChanged.connect(self.on_provider_changed)
        ai_form.addRow("AI提供商:", self.ai_provider_combo)
        
        # 阿里通义千问设置
        self.ali_api_key_input = QLineEdit()
        self.ali_api_key_input.setEchoMode(QLineEdit.Password)
        self.ali_api_key_input.setPlaceholderText("请输入阿里通义千问API Key")
        ai_form.addRow("阿里API Key:", self.ali_api_key_input)
        
        self.ali_model_input = QLineEdit()
        self.ali_model_input.setPlaceholderText("例如: qwen-turbo")
        ai_form.addRow("阿里模型名称:", self.ali_model_input)
        
        # 百度千帆设置（OpenAI 兼容接口，仅需 api_key）
        self.baidu_api_key_input = QLineEdit()
        self.baidu_api_key_input.setEchoMode(QLineEdit.Password)
        self.baidu_api_key_input.setPlaceholderText("获取地址: https://console.bce.baidu.com/qianfan/ais/console/apiKey")
        ai_form.addRow("百度 API Key:", self.baidu_api_key_input)
        
        self.baidu_model_input = QLineEdit()
        self.baidu_model_input.setPlaceholderText("例如: ernie-4.5-turbo-128k")
        ai_form.addRow("百度模型名称:", self.baidu_model_input)
        
        self.ai_max_tokens_spin = QSpinBox()
        self.ai_max_tokens_spin.setRange(500, 8000)
        self.ai_max_tokens_spin.setSuffix(" tokens")
        ai_form.addRow("最大Token:", self.ai_max_tokens_spin)
        
        ai_layout.addWidget(ai_group)
        ai_layout.addStretch()
        
        tab_widget.addTab(ai_tab, "AI设置")
        
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
        
        selenium_layout.addWidget(selenium_group)
        selenium_layout.addStretch()
        
        tab_widget.addTab(selenium_tab, "Selenium设置")
        
        # 账号设置
        account_tab = QWidget()
        account_layout = QVBoxLayout()
        account_tab.setLayout(account_layout)
        
        account_group = QGroupBox("账号刷新设置")
        account_form = QFormLayout()
        account_group.setLayout(account_form)
        
        self.auto_refresh_check = QCheckBox()
        self.auto_refresh_check.setText("自动刷新账号状态")
        account_form.addRow("自动刷新:", self.auto_refresh_check)
        
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(300, 86400)
        self.refresh_interval_spin.setSuffix(" 秒")
        account_form.addRow("刷新间隔:", self.refresh_interval_spin)
        
        account_layout.addWidget(account_group)
        account_layout.addStretch()
        
        tab_widget.addTab(account_tab, "账号设置")
        
        # 日志与异常管理：查看系统日志
        log_tab = QWidget()
        log_layout = QVBoxLayout()
        log_tab.setLayout(log_layout)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("日志文件:"))
        self.log_refresh_btn = QPushButton("刷新")
        self.log_refresh_btn.clicked.connect(self.refresh_log_list)
        log_header.addWidget(self.log_refresh_btn)
        log_header.addStretch()
        log_layout.addLayout(log_header)
        self.log_list = QListWidget()
        self.log_list.currentTextChanged.connect(self.on_log_file_selected)
        log_layout.addWidget(self.log_list)
        log_layout.addWidget(QLabel("日志内容:"))
        self.log_content = QPlainTextEdit()
        self.log_content.setReadOnly(True)
        self.log_content.setPlaceholderText("选择上方日志文件查看内容，便于定位错误与异常。")
        log_layout.addWidget(self.log_content)
        self.refresh_log_list()
        tab_widget.addTab(log_tab, "日志查看")
        
        # 平台与文件服务管理
        platform_tab = QWidget()
        platform_layout = QVBoxLayout()
        platform_tab.setLayout(platform_layout)
        
        platform_group = QGroupBox("平台发布管理（登录地址）")
        platform_form = QFormLayout()
        platform_group.setLayout(platform_form)
        self.baijiahao_url_input = QLineEdit()
        self.baijiahao_url_input.setPlaceholderText("https://baijiahao.baidu.com/")
        platform_form.addRow("百家号登录URL:", self.baijiahao_url_input)
        self.xiaohongshu_url_input = QLineEdit()
        self.xiaohongshu_url_input.setPlaceholderText("https://creator.xiaohongshu.com/")
        platform_form.addRow("小红书登录URL:", self.xiaohongshu_url_input)
        platform_layout.addWidget(platform_group)
        
        file_group = QGroupBox("文件服务管理（目录路径）")
        file_form = QFormLayout()
        file_group.setLayout(file_form)
        self.uploads_dir_label = QLabel(str(Config.UPLOADS_DIR))
        self.uploads_dir_label.setWordWrap(True)
        file_form.addRow("上传目录:", self.uploads_dir_label)
        self.extracted_dir_label = QLabel(str(Config.EXTRACTED_DIR))
        self.extracted_dir_label.setWordWrap(True)
        file_form.addRow("解压目录:", self.extracted_dir_label)
        self.logs_dir_label = QLabel(str(Config.LOGS_DIR))
        self.logs_dir_label.setWordWrap(True)
        file_form.addRow("日志目录:", self.logs_dir_label)
        platform_layout.addWidget(file_group)
        platform_layout.addStretch()
        tab_widget.addTab(platform_tab, "平台与文件")
        
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
    
    def on_provider_changed(self):
        """提供商改变时的处理"""
        pass
    
    def refresh_log_list(self):
        """刷新日志文件列表"""
        if not hasattr(self, 'log_list'):
            return
        self.log_list.clear()
        logs_dir = Path(Config.LOGS_DIR)
        if not logs_dir.exists():
            return
        files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files:
            self.log_list.addItem(f.name)
    
    def on_log_file_selected(self, name):
        """选择日志文件时显示内容"""
        if not name or not hasattr(self, 'log_content'):
            return
        path = Path(Config.LOGS_DIR) / name
        if not path.exists():
            self.log_content.setPlainText("")
            return
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
            self.log_content.setPlainText(text)
            self.log_content.moveCursor(self.log_content.textCursor().End)
        except Exception as e:
            self.log_content.setPlainText(f"读取失败: {e}")
    
    def load_settings(self):
        """加载设置（优先从已保存的 settings.json 读取，重启后才能显示已保存的 API Key）"""
        try:
            saved = Config.load_config("settings.json")
            
            # 加载AI设置：优先使用已保存文件，并同步到内存供其他模块使用
            ai_config = saved.get("ai", Config.AI_CONFIG)
            if "ai" in saved:
                Config.AI_CONFIG.update(saved["ai"])
            provider = ai_config.get("provider", "dashscope")
            index = self.ai_provider_combo.findText(provider)
            if index >= 0:
                self.ai_provider_combo.setCurrentIndex(index)
            
            dashscope_config = ai_config.get("dashscope", {})
            self.ali_api_key_input.setText(dashscope_config.get("api_key", ""))
            self.ali_model_input.setText(dashscope_config.get("model", "qwen-turbo"))
            
            qianfan_config = ai_config.get("qianfan", {})
            self.baidu_api_key_input.setText(qianfan_config.get("api_key", ""))
            self.baidu_model_input.setText(qianfan_config.get("model", "ernie-4.5-turbo-128k"))
            
            self.ai_max_tokens_spin.setValue(ai_config.get("max_tokens", 2000))
            
            # 加载Selenium设置：优先使用已保存
            selenium_config = saved.get("selenium", Config.SELENIUM_CONFIG)
            if "selenium" in saved:
                Config.SELENIUM_CONFIG.update(saved["selenium"])
            self.headless_check.setChecked(selenium_config.get("headless", False))
            self.wait_timeout_spin.setValue(selenium_config.get("wait_timeout", 10))
            self.implicit_wait_spin.setValue(selenium_config.get("implicit_wait", 5))
            
            # 加载账号设置：优先使用已保存
            account_config = saved.get("account", Config.ACCOUNT_CONFIG)
            if "account" in saved:
                Config.ACCOUNT_CONFIG.update(saved["account"])
            self.auto_refresh_check.setChecked(account_config.get("auto_refresh", True))
            self.refresh_interval_spin.setValue(account_config.get("refresh_interval", 3600))
            
            # 加载平台与文件（从已保存设置或默认）
            platforms = saved.get("platforms", Config.PLATFORMS)
            if hasattr(self, 'baijiahao_url_input'):
                self.baijiahao_url_input.setText(platforms.get("baijiahao", {}).get("login_url", "") or Config.PLATFORMS.get("baijiahao", {}).get("login_url", ""))
            if hasattr(self, 'xiaohongshu_url_input'):
                self.xiaohongshu_url_input.setText(platforms.get("xiaohongshu", {}).get("login_url", "") or Config.PLATFORMS.get("xiaohongshu", {}).get("login_url", ""))
            if "platforms" in saved:
                for k, v in saved["platforms"].items():
                    if k in Config.PLATFORMS and isinstance(v, dict):
                        Config.PLATFORMS[k].update(v)
            
            self.logger.info("设置加载成功")
        except Exception as e:
            self.logger.error(f"加载设置失败: {str(e)}")
            QMessageBox.warning(self, "警告", f"加载设置失败: {str(e)}")
    
    def save_settings(self):
        """保存设置"""
        try:
            settings = {}
            
            # 保存AI设置
            settings["ai"] = {
                "provider": self.ai_provider_combo.currentText(),
                "max_tokens": self.ai_max_tokens_spin.value(),
                "dashscope": {
                    "api_key": self.ali_api_key_input.text(),
                    "model": self.ali_model_input.text()
                },
                "qianfan": {
                    "api_key": self.baidu_api_key_input.text(),
                    "model": self.baidu_model_input.text()
                }
            }
            
            # 保存Selenium设置
            settings["selenium"] = {
                "headless": self.headless_check.isChecked(),
                "wait_timeout": self.wait_timeout_spin.value(),
                "implicit_wait": self.implicit_wait_spin.value()
            }
            
            # 保存账号设置
            settings["account"] = {
                "auto_refresh": self.auto_refresh_check.isChecked(),
                "refresh_interval": self.refresh_interval_spin.value()
            }
            
            # 保存平台登录 URL
            if hasattr(self, 'baijiahao_url_input') and hasattr(self, 'xiaohongshu_url_input'):
                settings["platforms"] = {
                    "baijiahao": {"login_url": self.baijiahao_url_input.text().strip() or "https://baijiahao.baidu.com/"},
                    "xiaohongshu": {"login_url": self.xiaohongshu_url_input.text().strip() or "https://creator.xiaohongshu.com/"}
                }
            
            # 保存到文件
            Config.save_config(settings, "settings.json")
            
            # 更新内存中的配置
            Config.AI_CONFIG.update(settings["ai"])
            Config.SELENIUM_CONFIG.update(settings["selenium"])
            Config.ACCOUNT_CONFIG.update(settings["account"])
            if "platforms" in settings:
                for k, v in settings["platforms"].items():
                    if k in Config.PLATFORMS and isinstance(v, dict):
                        Config.PLATFORMS[k].update(v)
            
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
            self.ai_provider_combo.setCurrentIndex(0)
            self.ali_api_key_input.clear()
            self.ali_model_input.setText("qwen-turbo")
            self.baidu_api_key_input.clear()
            self.baidu_model_input.setText("ernie-4.5-turbo-128k")
            self.ai_max_tokens_spin.setValue(2000)
            
            self.headless_check.setChecked(False)
            self.wait_timeout_spin.setValue(10)
            self.implicit_wait_spin.setValue(5)
            
            self.auto_refresh_check.setChecked(True)
            self.refresh_interval_spin.setValue(3600)
            
            if hasattr(self, 'baijiahao_url_input'):
                self.baijiahao_url_input.setText("https://baijiahao.baidu.com/")
            if hasattr(self, 'xiaohongshu_url_input'):
                self.xiaohongshu_url_input.setText("https://creator.xiaohongshu.com/")
            
            QMessageBox.information(self, "成功", "设置已重置为默认值")

