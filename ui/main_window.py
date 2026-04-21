"""
主窗口模块
"""
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QMenuBar, QMenu, QAction, QStatusBar,
                             QMessageBox, QToolBar)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QIcon

from ui.widgets.baijiahao_widget import BaijiahaoWidget
from ui.widgets.xiaohongshu_widget import XiaohongshuWidget
from ui.widgets.ai_widget import AIWidget
from ui.widgets.settings_widget import SettingsWidget
from utils.logger import Logger


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("MainWindow")
        self.init_ui()
        self.logger.info("主窗口初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("电商运营平台 - EcomOpt")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建主内容区域
        self.create_central_widget()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        settings_action = QAction("设置(&S)", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        
        # 可以在这里添加工具栏按钮
        # settings_action = QAction("设置", self)
        # settings_action.triggered.connect(self.show_settings)
        # toolbar.addAction(settings_action)
    
    def create_central_widget(self):
        """创建中心内容区域"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 百家号选项卡
        self.baijiahao_widget = BaijiahaoWidget()
        self.tab_widget.addTab(self.baijiahao_widget, "百家号")
        
        # 小红书选项卡
        self.xiaohongshu_widget = XiaohongshuWidget()
        self.tab_widget.addTab(self.xiaohongshu_widget, "小红书")
        
        # AI工具选项卡
        self.ai_widget = AIWidget()
        self.tab_widget.addTab(self.ai_widget, "AI工具")
        
        # 设置选项卡
        self.settings_widget = SettingsWidget()
        self.tab_widget.addTab(self.settings_widget, "设置")
    
    def show_settings(self):
        """显示设置页面"""
        self.tab_widget.setCurrentWidget(self.settings_widget)
        self.status_bar.showMessage("打开设置页面")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """
            <h2>电商运营平台 EcomOpt</h2>
            <p>版本: 1.0.0</p>
            <p>融合Selenium和AI技术的电商运营平台</p>
            <p>支持平台：百家号、小红书</p>
            <p>开发语言：Python 3.8 + PyQt5</p>
            """
        )
    
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
            # 清理资源
            try:
                if hasattr(self, 'baijiahao_widget'):
                    self.baijiahao_widget.cleanup()
                if hasattr(self, 'xiaohongshu_widget'):
                    self.xiaohongshu_widget.cleanup()
            except Exception as e:
                self.logger.error(f"清理资源失败: {str(e)}")
            
            event.accept()
        else:
            event.ignore()

