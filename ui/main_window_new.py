"""
主窗口模块 - 支持双角色（运营人员 / 管理员）
"""
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QStatusBar, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from ui.widgets.account_widget import AccountWidget
from ui.widgets.upload_widget import UploadWidget
from ui.widgets.resource_widget import ResourceWidget
from ui.widgets.content_widget import ContentWidget
from ui.widgets.template_widget import TemplateWidget
from ui.widgets.settings_widget_new import SettingsWidget
from ui.widgets.admin_widgets import PlatformManageWidget, FileServiceWidget, LogExceptionWidget
from ui.login_window import ROLE_OPERATOR, ROLE_ADMIN
from utils.logger import Logger


class MainWindow(QMainWindow):
    """主窗口类：根据角色显示运营人员或管理员功能。"""

    def __init__(self, role: str = ROLE_OPERATOR):
        super().__init__()
        self.role = role if role in (ROLE_OPERATOR, ROLE_ADMIN) else ROLE_OPERATOR
        self.logger = Logger.get_logger("MainWindow")
        self.init_ui()
        self.logger.info("主窗口初始化完成（角色: %s）", "管理员" if self.role == ROLE_ADMIN else "运营人员")
    
    def init_ui(self):
        """初始化UI"""
        title_suffix = " - 管理员" if self.role == ROLE_ADMIN else " - 运营人员"
        self.setWindowTitle("电商运营平台" + title_suffix)
        self.setGeometry(100, 100, 1600, 1000)
        
        # 设置窗口图标
        self.set_window_icon()
        
        # 窗口居中
        self.center_window()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 · " + ("管理员" if self.role == ROLE_ADMIN else "运营人员"))
        
        # 创建主内容区域
        self.create_central_widget()
    
    def set_window_icon(self):
        """设置窗口图标"""
        from pathlib import Path
        from config.config import Config
        
        # 尝试使用ICO文件（Windows）
        icon_path = Config.BASE_DIR / "imgs" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            # 如果ICO不存在，使用PNG
            icon_path = Config.BASE_DIR / "imgs" / "app.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
    
    def center_window(self):
        """窗口居中"""
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def create_central_widget(self):
        """根据角色创建不同选项卡。运营人员：账号/上传/资源/内容/话术/设置；管理员：平台发布/文件服务/配置/日志与异常。"""
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        if self.role == ROLE_OPERATOR:
            self.account_widget = AccountWidget()
            self.tab_widget.addTab(self.account_widget, "账号管理")
            self.upload_widget = UploadWidget()
            self.tab_widget.addTab(self.upload_widget, "上传管理")
            self.resource_widget = ResourceWidget()
            self.tab_widget.addTab(self.resource_widget, "资源管理")
            self.content_widget = ContentWidget()
            self.tab_widget.addTab(self.content_widget, "内容管理")
            self.template_widget = TemplateWidget()
            self.tab_widget.addTab(self.template_widget, "话术模板管理")
            self.settings_widget = SettingsWidget()
            self.tab_widget.addTab(self.settings_widget, "设置")
        else:
            # 管理员：平台发布管理、文件服务管理、配置管理、日志与异常管理
            self.tab_widget.addTab(PlatformManageWidget(), "平台发布管理")
            self.tab_widget.addTab(FileServiceWidget(), "文件服务管理")
            self.tab_widget.addTab(SettingsWidget(), "配置管理")
            self.tab_widget.addTab(LogExceptionWidget(), "日志与异常管理")
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.role == ROLE_OPERATOR:
                    if hasattr(self, 'account_widget'):
                        self.account_widget.cleanup()
                    if hasattr(self, 'content_widget'):
                        self.content_widget.cleanup()
            except Exception as e:
                self.logger.error("清理资源失败: %s", str(e))
            event.accept()
        else:
            event.ignore()

