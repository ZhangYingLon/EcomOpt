"""
平台基类模块
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.selenium_manager import SeleniumManager
from utils.logger import Logger
from utils.exceptions import PlatformException


class BasePlatform(ABC):
    """平台基类"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = Logger.get_logger(f"Platform_{platform_name}")
        self.selenium_manager = SeleniumManager()
        self.is_logged_in = False
        self.user_info: Optional[Dict[str, Any]] = None
    
    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """
        登录平台
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            登录是否成功
        """
        pass
    
    @abstractmethod
    def publish_article(self, title: str, content: str, **kwargs) -> bool:
        """
        发布文章/笔记
        
        Args:
            title: 标题
            content: 内容
            **kwargs: 其他参数（标签、图片等）
        
        Returns:
            发布是否成功
        """
        pass
    
    @abstractmethod
    def get_article_list(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        获取文章列表
        
        Args:
            page: 页码
            page_size: 每页数量
        
        Returns:
            文章列表
        """
        pass
    
    def check_login_status(self) -> bool:
        """检查登录状态"""
        # 子类可以重写此方法来实现具体的登录状态检查
        return self.is_logged_in
    
    def logout(self) -> bool:
        """退出登录"""
        try:
            self.is_logged_in = False
            self.user_info = None
            self.logger.info("已退出登录")
            return True
        except Exception as e:
            self.logger.error(f"退出登录失败: {str(e)}")
            return False
    
    def close(self):
        """关闭平台相关资源"""
        if self.selenium_manager:
            self.selenium_manager.close()

