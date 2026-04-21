"""
Selenium自动化管理模块
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from typing import Optional, Dict, Any
from pathlib import Path
import time

from config.config import Config
from utils.logger import Logger
from utils.exceptions import SeleniumException


class SeleniumManager:
    """Selenium管理器"""
    
    def __init__(self):
        self.logger = Logger.get_logger("SeleniumManager")
        self.driver: Optional[webdriver.Chrome] = None
        self.wait_timeout = Config.SELENIUM_CONFIG["wait_timeout"]
    
    def _find_driver_in_tools_dir(self) -> Optional[Path]:
        """在tools目录中查找Chrome驱动"""
        tools_dir = Config.TOOLS_DIR
        if not tools_dir.exists():
            return None
        
        # 可能的驱动文件名（Windows、Linux、Mac）
        driver_names = [
            "chromedriver.exe",  # Windows
            "chromedriver",      # Linux/Mac
            "chromedriver_win32.exe",
            "chromedriver_linux64",
            "chromedriver_mac64",
        ]
        
        for name in driver_names:
            driver_path = tools_dir / name
            if driver_path.exists() and driver_path.is_file():
                # 检查文件是否可执行（在Windows上，.exe文件总是可执行的）
                return driver_path
        
        return None
    
    def init_driver(self, headless: bool = None) -> webdriver.Chrome:
        """初始化浏览器驱动"""
        try:
            chrome_options = Options()
            
            if headless is None:
                headless = Config.SELENIUM_CONFIG["headless"]
            
            if headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            # DOM 就绪即返回，不等待全部资源（避免 SPA/百家号等页面一直不触发 load 导致 get() 卡住）
            chrome_options.page_load_strategy = 'eager'
            
            # 设置窗口大小
            window_size = Config.SELENIUM_CONFIG["window_size"]
            chrome_options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
            
            # 查找Chrome驱动（仅使用tools目录或指定路径）
            driver_path = Config.SELENIUM_CONFIG.get("chrome_driver_path")
            
            # 如果指定了驱动路径，直接使用
            if driver_path:
                driver_path = Path(driver_path)
                if not driver_path.exists():
                    raise SeleniumException(
                        f"指定的Chrome驱动路径不存在: {driver_path}\n"
                        f"请确保驱动文件存在，或将其放置在 tools 目录下"
                    )
                self.logger.info(f"使用指定的Chrome驱动路径: {driver_path}")
                service = Service(str(driver_path))
            else:
                # 从tools目录查找驱动
                tools_driver = self._find_driver_in_tools_dir()
                if tools_driver:
                    self.logger.info(f"在tools目录找到Chrome驱动: {tools_driver}")
                    service = Service(str(tools_driver))
                else:
                    # 找不到驱动，抛出错误提示
                    tools_dir = Config.TOOLS_DIR
                    raise SeleniumException(
                        f"未找到Chrome驱动！\n"
                        f"请将 chromedriver.exe (Windows) 或 chromedriver (Linux/Mac) 放置在以下目录：\n"
                        f"{tools_dir}\n"
                        f"或者通过在配置中设置 chrome_driver_path 来指定驱动路径"
                    )
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # 页面加载最长等待，避免 get(url) 无限卡住
            self.driver.set_page_load_timeout(60)
            # 设置隐式等待
            self.driver.implicitly_wait(Config.SELENIUM_CONFIG["implicit_wait"])
            
            # 执行反检测脚本
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            # 加载 stealth.min.js 增强反检测能力
            self._load_stealth_script()
            
            self.logger.info("浏览器驱动初始化成功")
            return self.driver
            
        except Exception as e:
            self.logger.error("浏览器驱动初始化失败: %s", str(e))
            msg = str(e)
            hint = (
                "\n\n【常见原因】\n"
                "1. Chrome 浏览器与 tools 目录下的 chromedriver.exe 主版本号必须一致。\n"
                "   在 Chrome 地址栏打开 chrome://version 查看版本；到\n"
                "   https://googlechromelabs.github.io/chrome-for-testing/\n"
                "   下载对应版本的 chromedriver，替换项目 tools\\chromedriver.exe。\n"
                "2. 若本机未安装 Google Chrome，请先安装或与 chromedriver 匹配的 Chromium。\n"
                "3. 可在「设置」中指定 chrome_driver_path 指向正确驱动路径。"
            )
            if "session not created" in msg.lower() or "chrome instance exited" in msg.lower():
                msg = msg + hint
            raise SeleniumException(f"驱动初始化失败: {msg}")
    
    def get_driver(self) -> webdriver.Chrome:
        """获取浏览器驱动，如果不存在则创建"""
        if self.driver is None:
            self.init_driver()
        return self.driver
    
    def wait_for_element(self, by: By, value: str, timeout: int = None) -> Any:
        """等待元素出现"""
        if timeout is None:
            timeout = self.wait_timeout
        
        try:
            wait = WebDriverWait(self.get_driver(), timeout)
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            self.logger.warning(f"元素定位超时: {by}={value}")
            raise SeleniumException(f"元素定位超时: {by}={value}")
    
    def wait_for_clickable(self, by: By, value: str, timeout: int = None) -> Any:
        """等待元素可点击"""
        if timeout is None:
            timeout = self.wait_timeout
        
        try:
            wait = WebDriverWait(self.get_driver(), timeout)
            return wait.until(EC.element_to_be_clickable((by, value)))
        except TimeoutException:
            self.logger.warning(f"元素不可点击: {by}={value}")
            raise SeleniumException(f"元素不可点击: {by}={value}")
    
    def safe_click(self, by: By, value: str, timeout: int = None):
        """安全点击元素"""
        element = self.wait_for_clickable(by, value, timeout)
        try:
            element.click()
            return True
        except Exception as e:
            self.logger.error(f"点击元素失败: {str(e)}")
            return False
    
    def safe_input(self, by: By, value: str, text: str, clear: bool = True):
        """安全输入文本"""
        element = self.wait_for_element(by, value)
        try:
            if clear:
                element.clear()
            element.send_keys(text)
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败: {str(e)}")
            return False
    
    def get_page_source(self) -> str:
        """获取页面源码"""
        return self.get_driver().page_source
    
    def get_current_url(self) -> str:
        """获取当前URL"""
        return self.get_driver().current_url
    
    def navigate_to(self, url: str):
        """导航到指定URL（page_load_strategy=eager，DOM 就绪即继续）"""
        try:
            self.logger.info("正在打开: %s", url)
            self.get_driver().get(url)
            self.logger.info("页面已打开，当前 URL: %s", self.get_driver().current_url or url)
        except Exception as e:
            self.logger.error("导航失败: %s", str(e))
            raise SeleniumException(f"导航失败: {str(e)}")
    
    def _load_stealth_script(self):
        """加载 stealth.min.js 反检测脚本"""
        try:
            stealth_js_path = Config.TOOLS_DIR / "stealth.min.js"
            if stealth_js_path.exists():
                with open(stealth_js_path, 'r', encoding='utf-8') as f:
                    stealth_js = f.read()
                
                # 注入到每个新文档中
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': stealth_js
                })
                self.logger.info("stealth.min.js 反检测脚本加载成功")
            else:
                self.logger.warning(f"未找到 stealth.min.js: {stealth_js_path}，使用基础反检测")
        except Exception as e:
            self.logger.error(f"加载 stealth.min.js 失败: {str(e)}，继续使用基础反检测")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger.info("浏览器已关闭")
            except Exception as e:
                self.logger.error(f"关闭浏览器失败: {str(e)}")
    
    def __del__(self):
        """析构函数"""
        self.close()

