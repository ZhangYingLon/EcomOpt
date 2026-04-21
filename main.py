"""
电商运营平台主程序入口
EcomOpt - 融合Selenium和AI技术的电商运营平台
支持平台：百家号、小红书
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from ui.login_window import LoginWindow, ROLE_OPERATOR
from ui.main_window_new import MainWindow
from utils.logger import Logger
from config.config import Config


def main():
    """主函数"""
    # 初始化日志
    logger = Logger.get_logger("Main")
    logger.info("=" * 60)
    logger.info("电商运营平台启动")
    logger.info("=" * 60)
    
    # 初始化目录结构
    Config.init_directories()
    logger.info("目录结构初始化完成")
    
    # 启动时加载已保存的设置，使 API Key 等重启后生效
    saved = Config.load_config("settings.json")
    if saved:
        if "ai" in saved:
            Config.AI_CONFIG.update(saved["ai"])
        if "selenium" in saved:
            Config.SELENIUM_CONFIG.update(saved["selenium"])
        if "account" in saved:
            Config.ACCOUNT_CONFIG.update(saved["account"])
        if "platforms" in saved:
            for k, v in saved["platforms"].items():
                if k in Config.PLATFORMS and isinstance(v, dict):
                    Config.PLATFORMS[k].update(v)
    
    # 创建应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("EcomOpt")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("EcomOpt")
    
    # 设置应用程序图标
    icon_path = Config.BASE_DIR / "imgs" / "app.ico"
    if not icon_path.exists():
        icon_path = Config.BASE_DIR / "imgs" / "app.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # 界面美观：加载全局样式表
    app.setStyle('Fusion')
    style_file = Config.RESOURCES_DIR / "style.qss"
    if style_file.exists():
        with open(style_file, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    # 先显示登录/角色选择界面
    login = LoginWindow()
    if login.exec_() != QDialog.Accepted:
        logger.info("用户取消登录，退出")
        sys.exit(0)
    role = login.get_role()
    if not role:
        role = ROLE_OPERATOR
    uname = login.get_username()
    logger.info(
        "登录成功: 用户=%s, 角色=%s",
        uname or "(未知)",
        "管理员" if role == "admin" else "运营人员",
    )

    # 根据角色创建并显示主窗口
    try:
        main_window = MainWindow(role=role)
        main_window.show()
        logger.info("主窗口显示成功")
    except Exception as e:
        logger.error("启动主窗口失败: %s", str(e))
        sys.exit(1)

    exit_code = app.exec_()
    logger.info("应用程序退出")
    logger.info("=" * 60)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

