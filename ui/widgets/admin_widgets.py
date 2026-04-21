"""
管理员专用功能组件（根据 修改.txt）
- 平台发布管理：维护平台适配逻辑（小红书、百家号），配置发布流程
- 文件服务管理：统一处理文件上传、解压、目录扫描与路径管理
- 配置管理：环境变量、平台参数、目录初始化等（由主窗口直接复用 SettingsWidget）
- 日志与异常管理：查看系统日志、定位错误、处理自动化与AI调用异常
"""
from pathlib import Path
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QFormLayout, QLineEdit, QPushButton,
                             QListWidget, QPlainTextEdit)
from PyQt5.QtCore import Qt
from config.config import Config
from utils.logger import Logger


class PlatformManageWidget(QWidget):
    """平台发布管理：维护平台适配逻辑，配置发布流程。"""
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("PlatformManageWidget")
        layout = QVBoxLayout(self)
        tip = QLabel("维护平台适配逻辑（如小红书、百家号），配置发布流程。可在此配置各平台登录地址等参数。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #64748b; padding: 8px 0;")
        layout.addWidget(tip)
        g = QGroupBox("平台登录地址")
        f = QFormLayout()
        self.xiaohongshu_url = QLineEdit()
        self.xiaohongshu_url.setPlaceholderText("https://creator.xiaohongshu.com/")
        f.addRow("小红书登录URL:", self.xiaohongshu_url)
        self.baijiahao_url = QLineEdit()
        self.baijiahao_url.setPlaceholderText("https://baijiahao.baidu.com/")
        f.addRow("百家号登录URL:", self.baijiahao_url)
        g.setLayout(f)
        layout.addWidget(g)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()
        self._load()

    def _load(self):
        try:
            saved = Config.load_config("settings.json")
            if not saved or "platforms" not in saved:
                return
            p = saved["platforms"]
            if "xiaohongshu" in p and "login_url" in p["xiaohongshu"]:
                self.xiaohongshu_url.setText(p["xiaohongshu"]["login_url"])
            if "baijiahao" in p and "login_url" in p["baijiahao"]:
                self.baijiahao_url.setText(p["baijiahao"]["login_url"])
        except Exception as e:
            self.logger.warning("加载平台配置失败: %s", e)

    def _save(self):
        try:
            saved = Config.load_config("settings.json") or {}
            if "platforms" not in saved:
                saved["platforms"] = {}
            saved["platforms"].setdefault("xiaohongshu", {})["login_url"] = self.xiaohongshu_url.text().strip() or "https://creator.xiaohongshu.com/"
            saved["platforms"].setdefault("baijiahao", {})["login_url"] = self.baijiahao_url.text().strip() or "https://baijiahao.baidu.com/"
            Config.save_config(saved, "settings.json")
            if hasattr(Config, "PLATFORMS"):
                for k, v in saved["platforms"].items():
                    if k in Config.PLATFORMS and isinstance(v, dict):
                        Config.PLATFORMS[k].update(v)
            self.logger.info("平台配置已保存")
        except Exception as e:
            self.logger.error("保存平台配置失败: %s", e)


class FileServiceWidget(QWidget):
    """文件服务管理：统一处理文件上传、解压、目录扫描与路径管理。"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        tip = QLabel("统一处理文件上传、解压、目录扫描与路径管理。上传与资源管理由运营人员在对应模块操作，此处展示系统目录配置。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #64748b; padding: 8px 0;")
        layout.addWidget(tip)
        g = QGroupBox("目录路径")
        f = QFormLayout()
        f.addRow("上传目录:", QLabel(str(Config.UPLOADS_DIR)))
        f.addRow("解压目录:", QLabel(str(Config.EXTRACTED_DIR)))
        f.addRow("日志目录:", QLabel(str(Config.LOGS_DIR)))
        f.addRow("配置目录:", QLabel(str(Config.CONFIG_DIR)))
        g.setLayout(f)
        layout.addWidget(g)
        layout.addStretch()


class LogExceptionWidget(QWidget):
    """日志与异常管理：查看系统日志、定位错误、处理自动化与AI调用异常。"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        tip = QLabel("查看系统日志，便于定位错误与处理自动化、AI 调用异常。")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #64748b; padding: 8px 0;")
        layout.addWidget(tip)
        row = QHBoxLayout()
        row.addWidget(QLabel("日志文件:"))
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh)
        row.addWidget(self.refresh_btn)
        row.addStretch()
        layout.addLayout(row)
        self.log_list = QListWidget()
        self.log_list.currentTextChanged.connect(self._on_select)
        layout.addWidget(self.log_list)
        layout.addWidget(QLabel("日志内容:"))
        self.log_content = QPlainTextEdit()
        self.log_content.setReadOnly(True)
        self.log_content.setPlaceholderText("选择上方日志文件查看内容。")
        layout.addWidget(self.log_content)
        self._refresh()

    def _refresh(self):
        self.log_list.clear()
        logs_dir = Path(Config.LOGS_DIR)
        if not logs_dir.exists():
            return
        for f in sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
            self.log_list.addItem(f.name)

    def _on_select(self, name):
        if not name:
            self.log_content.setPlainText("")
            return
        path = Path(Config.LOGS_DIR) / name
        if not path.exists():
            self.log_content.setPlainText("")
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            self.log_content.setPlainText(text)
            self.log_content.moveCursor(self.log_content.textCursor().End)
        except Exception as e:
            self.log_content.setPlainText(f"读取失败: {e}")
