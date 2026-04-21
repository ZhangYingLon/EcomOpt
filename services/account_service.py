"""
账号管理服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from selenium.webdriver.common.by import By

from models.database import Database
from models.models import Account
from core.selenium_manager import SeleniumManager
from config.config import Config
from utils.logger import Logger


class AccountService(QObject):
    """账号管理服务"""
    
    account_status_changed = pyqtSignal(int, str)  # 账号ID, 状态
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.logger = Logger.get_logger("AccountService")
        self.selenium_manager = SeleniumManager()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_all_accounts)
        self._init_refresh_timer()
    
    def _init_refresh_timer(self):
        """初始化刷新定时器"""
        if Config.ACCOUNT_CONFIG.get("auto_refresh", True):
            interval = Config.ACCOUNT_CONFIG.get("refresh_interval", 3600) * 1000  # 转换为毫秒
            self.refresh_timer.start(interval)
            self.logger.info(f"账号自动刷新定时器已启动，间隔: {interval/1000}秒")
    
    def add_account(self, platform: str, username: str, nickname: str = None) -> int:
        """添加账号"""
        try:
            account_id = Account.create(self.db, platform, username, nickname)
            self.logger.info(f"添加账号成功: {platform} - {username}")
            return account_id
        except Exception as e:
            self.logger.error(f"添加账号失败: {str(e)}")
            raise
    
    def get_all_accounts(self, platform: str = None) -> List[Dict[str, Any]]:
        """获取所有账号"""
        return Account.get_all(self.db, platform)
    
    def open_browser_to_login(self, platform: str) -> None:
        """仅打开平台登录页，供用户手动登录（不获取 Cookie）"""
        config = Config.PLATFORMS.get(platform)
        if not config:
            raise ValueError(f"不支持的平台: {platform}")
        login_url = config["login_url"]
        driver = self.selenium_manager.get_driver()
        driver.get(login_url)
        self.logger.info(f"已打开 {platform} 登录页，请手动登录后点击「获取Cookie并保存」")

    def get_current_cookies(self) -> Optional[str]:
        """从当前浏览器页面获取 Cookie（不跳转页面，用于登录完成后保存）"""
        try:
            driver = self.selenium_manager.get_driver()
            cookies = driver.get_cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            return cookie_str
        except Exception as e:
            self.logger.error(f"获取Cookie失败: {str(e)}")
            return None

    def get_cookie_from_browser(self, platform: str) -> Optional[str]:
        """
        从浏览器获取Cookie（会先打开登录页）
        用户需要手动登录，程序自动获取Cookie
        """
        try:
            self.open_browser_to_login(platform)
            return self.get_current_cookies()
        except Exception as e:
            self.logger.error(f"获取Cookie失败: {str(e)}")
            return None
    
    def update_account_cookie(self, account_id: int, cookie: str, check_valid: bool = True):
        """更新账号Cookie"""
        try:
            status = 'valid'
            if check_valid:
                account = Account.get_by_id(self.db, account_id)
                platform = account.get('platform', '') if account else ''
                status = self.check_cookie_validity(cookie, platform)
            
            Account.update_cookie(self.db, account_id, cookie, status)
            self.account_status_changed.emit(account_id, status)
            self.logger.info(f"更新账号Cookie成功: {account_id}")
        except Exception as e:
            self.logger.error(f"更新账号Cookie失败: {str(e)}")
            raise
    
    def _inject_cookies_and_check_xiaohongshu(self, cookie_str: str) -> str:
        """
        注入 Cookie 并检查小红书创作者后台是否仍处于登录状态。
        返回 'valid' 或 'invalid'
        """
        try:
            driver = self.selenium_manager.get_driver()
            login_url = Config.PLATFORMS.get("xiaohongshu", {}).get("login_url", "https://creator.xiaohongshu.com/")
            driver.get(login_url)
            self.selenium_manager.get_driver().implicitly_wait(3)
            driver.delete_all_cookies()
            for part in cookie_str.split(";"):
                part = part.strip()
                if not part or "=" not in part:
                    continue
                name, _, value = part.partition("=")
                name, value = name.strip(), value.strip()
                if not name:
                    continue
                try:
                    driver.add_cookie({"name": name, "value": value, "domain": ".xiaohongshu.com"})
                except Exception:
                    try:
                        driver.add_cookie({"name": name, "value": value})
                    except Exception:
                        pass
            driver.refresh()
            time.sleep(2)
            current_url = driver.current_url
            if "login" in current_url.lower() or "passport" in current_url.lower():
                self.logger.info("小红书刷新状态: Cookie 已失效，显示 invalid")
                return "invalid"
            if "creator.xiaohongshu.com" in current_url and "login" not in current_url.lower():
                self.logger.info("小红书刷新状态: Cookie 有效，显示 valid")
                return "valid"
            self.logger.info("小红书刷新状态: 无法确认登录态，显示 invalid")
            return "invalid"
        except Exception as e:
            error_msg = str(e)
            if "invalid session id" in error_msg:
                self.logger.warning("检测到浏览器会话失效，正在重置驱动...")
                self.selenium_manager.driver = None
                return self._inject_cookies_and_check_xiaohongshu(cookie_str)
            self.logger.warning(f"小红书 Cookie 校验异常: {e}，显示 invalid")
            return "invalid"
    
    def check_cookie_validity(self, cookie: str, platform: str = None) -> str:
        """
        检查 Cookie 有效性，按平台实现。
        返回 'valid' 或 'invalid'
        """
        if not cookie or not cookie.strip():
            return "invalid"
        if platform == "xiaohongshu":
            return self._inject_cookies_and_check_xiaohongshu(cookie.strip())
        return "valid"
    
    def check_account_status(self, account_id: int) -> str:
        """检查账号状态"""
        account = Account.get_by_id(self.db, account_id)
        if not account:
            return 'not_found'
        
        if not account.get('cookie'):
            Account.update_status(self.db, account_id, 'invalid', update_refresh_time=True)
            self.account_status_changed.emit(account_id, 'invalid')
            return 'invalid'
        
        platform = account.get('platform', '')
        status = self.check_cookie_validity(account['cookie'], platform)
        if status != account.get('status'):
            Account.update_status(self.db, account_id, status, update_refresh_time=True)
            self.account_status_changed.emit(account_id, status)
        else:
            Account.update_status(self.db, account_id, status, update_refresh_time=True)
        
        return status
    
    def refresh_account(self, account_id: int):
        """刷新单个账号状态"""
        status = self.check_account_status(account_id)
        self.logger.info(f"账号 {account_id} 状态: {status}")
        return status
    
    def refresh_all_accounts(self):
        """刷新所有账号状态"""
        self.logger.info("开始刷新所有账号状态...")
        accounts = self.get_all_accounts()
        for account in accounts:
            try:
                self.refresh_account(account['id'])
            except Exception as e:
                self.logger.error(f"刷新账号 {account['id']} 失败: {str(e)}")
    
    def delete_account(self, account_id: int):
        """删除账号"""
        sql = "DELETE FROM accounts WHERE id = ?"
        self.db.execute_update(sql, (account_id,))
        self.logger.info(f"删除账号: {account_id}")

