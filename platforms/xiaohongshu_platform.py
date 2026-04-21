"""
小红书平台模块
参考 AI-social-xhs_ai_publisher 流程：首页 -> 点击发布笔记 -> 上传图文 tab -> 上传图片 -> 填标题/正文 -> 点击发布
"""
from typing import Dict, Any, Optional, List, Tuple

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import random

from platforms.base_platform import BasePlatform
from config.config import Config
from utils.exceptions import PlatformException

# 发布用占位图路径（至少选一张图才能进入编辑页）
PLACEHOLDER_IMAGE = str(Config.RESOURCES_DIR / "placeholder_publish.png")
# 小红书标题最大字数（超出无法填入且会阻塞后续正文输入）
XHS_TITLE_MAX_LEN = 20


class XiaohongshuPlatform(BasePlatform):
    """小红书平台类"""
    
    def __init__(self):
        super().__init__("xiaohongshu")
        self.config = Config.PLATFORMS["xiaohongshu"]
        self.login_url = self.config["login_url"]
    
    def login(self, username: str, password: str) -> bool:
        """登录小红书"""
        try:
            self.logger.info("开始登录小红书...")
            driver = self.selenium_manager.get_driver()
            self.selenium_manager.navigate_to(self.login_url)
            
            # 等待页面加载
            time.sleep(2)
            
            # 查找登录按钮或输入框
            # 注意：实际使用时需要根据网页结构调整选择器
            try:
                # 等待登录入口出现
                login_btn = self.selenium_manager.wait_for_clickable(
                    By.CSS_SELECTOR, 
                    ".login-btn, .sign-in, [class*='login'], button:contains('登录')", 
                    timeout=5
                )
                login_btn.click()
                time.sleep(1)
            except:
                self.logger.warning("未找到登录入口，可能已经显示登录表单")
            
            # 输入用户名和密码
            # 注意：需要根据实际页面调整选择器
            try:
                username_input = self.selenium_manager.wait_for_element(
                    By.CSS_SELECTOR,
                    "input[name='username'], input[type='text'], input[placeholder*='手机号'], input[placeholder*='账号']",
                    timeout=5
                )
                username_input.clear()
                username_input.send_keys(username)
                
                password_input = self.selenium_manager.wait_for_element(
                    By.CSS_SELECTOR,
                    "input[name='password'], input[type='password']",
                    timeout=5
                )
                password_input.clear()
                password_input.send_keys(password)
                
                # 点击登录按钮
                submit_btn = self.selenium_manager.wait_for_clickable(
                    By.CSS_SELECTOR,
                    "button[type='submit'], .submit-btn, button[class*='login']",
                    timeout=5
                )
                submit_btn.click()
                
                # 等待登录完成
                time.sleep(3)
                
                # 检查登录是否成功（通过URL或页面元素判断）
                current_url = driver.current_url
                if "creator.xiaohongshu.com" in current_url and "login" not in current_url.lower():
                    self.is_logged_in = True
                    self.logger.info("小红书登录成功")
                    return True
                else:
                    self.logger.error("小红书登录失败，请检查账号密码")
                    return False
                    
            except Exception as e:
                self.logger.error(f"登录过程中出错: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"小红书登录异常: {str(e)}")
            raise PlatformException(f"登录失败: {str(e)}")
    
    def _try_click(self, driver, selectors: List[Tuple[By, str]], timeout: int = 10) -> bool:
        """依次尝试选择器，找到可点击元素并点击。"""
        wait = WebDriverWait(driver, timeout)
        for by, value in selectors:
            try:
                el = wait.until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                el.click()
                return True
            except Exception:
                continue
        return False

    def _try_fill(self, driver, selectors: List[Tuple[By, str]], text: str, clear_first: bool = True, timeout: int = 8):
        """依次尝试选择器，找到元素并填入文本。返回是否成功。"""
        wait = WebDriverWait(driver, timeout)
        for by, value in selectors:
            try:
                el = wait.until(EC.presence_of_element_located((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                el.click()
                time.sleep(0.2)
                if clear_first:
                    try:
                        el.clear()
                    except Exception:
                        try:
                            el.send_keys(Keys.CONTROL + "a")
                            el.send_keys(Keys.BACKSPACE)
                        except Exception:
                            pass
                if text:
                    el.send_keys(text)
                return True
            except Exception:
                continue
        return False

    def _fill_contenteditable(self, driver, content: str, timeout: int = 10) -> bool:
        """填充正文框。流程已定位到内容框且处于焦点时，优先对当前焦点元素(active_element)直接 send_keys。"""
        if not (content or "").strip():
            return True
        
        # 过滤掉非 BMP 字符（emoji 等），避免 ChromeDriver 报错
        def filter_non_bmp(text):
            return ''.join(char for char in text if ord(char) <= 0xFFFF)
        
        safe_content = filter_non_bmp(content)
        if len(safe_content) < len(content):
            self.logger.warning("正文中包含 %d 个非 BMP 字符（如 emoji），已自动过滤", 
                              len(content) - len(safe_content))
        
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        def try_active_element_send_keys(extra_tabs: int = 0) -> bool:
            if extra_tabs:
                for _ in range(extra_tabs):
                    ActionChains(driver).send_keys(Keys.TAB).perform()
                    time.sleep(0.15)
            time.sleep(0.25)
            active = driver.switch_to.active_element
            try:
                active.send_keys(Keys.CONTROL + "a")
                active.send_keys(Keys.BACKSPACE)
            except Exception:
                pass
            active.send_keys(safe_content)
            return True

        # 1）优先：当前焦点已是内容框时，直接对 active_element 输入（流程已定位且处于焦点）
        try:
            try_active_element_send_keys(extra_tabs=0)
            self.logger.info("正文已通过对当前焦点元素(active_element)填入")
            return True
        except Exception as e:
            self.logger.debug("当前焦点输入失败，尝试 Tab 后再输入: %s", e)
        # 2）Tab 1～2 次后再对 active_element 输入
        try:
            try_active_element_send_keys(extra_tabs=2)
            self.logger.info("正文已通过 Tab 后对 active_element 填入")
            return True
        except Exception as e:
            self.logger.warning("Tab+active_element 填入正文失败: %s", e)

        # 3）按选择器找到 contenteditable，点击后对该元素 send_keys
        content_selectors = [
            (By.CSS_SELECTOR, "div[data-placeholder*='正文'] div[contenteditable='true']"),
            (By.CSS_SELECTOR, "div[data-placeholder*='请输入正文'] div[contenteditable='true']"),
            (By.CSS_SELECTOR, "div.ProseMirror[contenteditable='true']"),
            (By.CSS_SELECTOR, "[contenteditable='true'][role='textbox']"),
            (By.CSS_SELECTOR, "div.tiptap div.ProseMirror"),
            (By.XPATH, "//*[@contenteditable='true' and (contains(@data-placeholder,'正文') or contains(@data-placeholder,'描述') or contains(@placeholder,'正文'))]"),
        ]
        wait = WebDriverWait(driver, timeout)
        for by, value in content_selectors:
            try:
                el = wait.until(EC.presence_of_element_located((by, value)))
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.2)
                el.click()
                time.sleep(0.3)
                try:
                    el.send_keys(Keys.CONTROL + "a")
                    el.send_keys(Keys.BACKSPACE)
                except Exception:
                    pass
                el.send_keys(safe_content)
                self.logger.info("正文已通过 contenteditable 元素填入")
                return True
            except Exception:
                continue
        # 4）兜底：execCommand insertText（天然支持 Unicode）
        try:
            for by, value in content_selectors:
                try:
                    el = driver.find_element(by, value)
                    if not el.is_displayed():
                        continue
                    driver.execute_script("arguments[0].focus();", el)
                    time.sleep(0.2)
                    driver.execute_script(
                        "var el = arguments[0]; el.focus(); document.execCommand('insertText', false, arguments[1]);",
                        el, safe_content
                    )
                    self.logger.info("正文已通过 execCommand insertText 填入")
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def publish_article(self, title: str, content: str, **kwargs) -> bool:
        """发布小红书笔记。参考 AI-social-xhs_ai_publisher：首页 -> 发布笔记 -> 上传图文 -> 传图 -> 填标题/正文 -> 发布。"""
        if not self.check_login_status():
            raise PlatformException("请先登录小红书")
        images = [str(p) for p in (kwargs.get("images") or []) if p]
        if not images and not os.path.isfile(PLACEHOLDER_IMAGE):
            raise PlatformException("未提供发布图片且占位图不存在: " + PLACEHOLDER_IMAGE)
        use_paths = images if images else [PLACEHOLDER_IMAGE]
        file_value = "\n".join(use_paths) if len(use_paths) > 1 else use_paths[0]
        # 标题最多20字，超出会无法填入并导致正文也填不进去
        title_raw = (title or "").strip()
        if len(title_raw) > XHS_TITLE_MAX_LEN:
            self.logger.warning("小红书标题最多 %d 字，已截断: %d -> %d", XHS_TITLE_MAX_LEN, len(title_raw), XHS_TITLE_MAX_LEN)
        title_fill = title_raw[:XHS_TITLE_MAX_LEN] if title_raw else ""

        try:
            self.logger.info("开始发布笔记（参考 xhs_ai_publisher 流程）")
            driver = self.selenium_manager.get_driver()
            wait_long = WebDriverWait(driver, max(25, self.selenium_manager.wait_timeout))

            # ---------- 1. 进入创作者首页 ----------
            self.selenium_manager.navigate_to("https://creator.xiaohongshu.com/new/home")
            time.sleep(3)
            if "login" in (driver.current_url or ""):
                raise PlatformException("未登录或已登出，请先在账号管理中登录并保存 Cookie")

            # ---------- 2. 点击「发布笔记」 ----------
            publish_btn_selectors = [
                (By.CSS_SELECTOR, ".publish-video .btn"),
                (By.XPATH, "//button[contains(.,'发布笔记')]"),
                (By.XPATH, "//div[contains(@class,'btn')][contains(.,'发布笔记')]"),
            ]
            if not self._try_click(driver, publish_btn_selectors, timeout=12):
                raise PlatformException("未找到「发布笔记」按钮")
            time.sleep(3)

            # ---------- 3. 切换到「上传图文」选项卡（第二个 .creator-tab） ----------
            try:
                wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".creator-tab")))
                driver.execute_script("""
                    var tabs = document.querySelectorAll('.creator-tab');
                    if (tabs.length > 1) { tabs[1].click(); return true; }
                    return false;
                """)
                self.logger.info("已切换到上传图文选项卡")
            except Exception as e:
                self.logger.warning("切换上传图文选项卡异常: %s", e)
            time.sleep(3)

            # ---------- 4. 等待上传区域并注入图片（不弹系统选择框） ----------
            try:
                wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".upload-button")))
            except Exception:
                try:
                    wait_long.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".upload-input")))
                except Exception:
                    pass
            time.sleep(1.5)
            upload_ok = False
            for sel in [".upload-input", "input[type='file'][accept*='image']", "input[type='file']"]:
                try:
                    inp = driver.find_element(By.CSS_SELECTOR, sel)
                    inp.send_keys(file_value)
                    upload_ok = True
                    self.logger.info("已向上传输入框填入 %d 张图片", len(use_paths))
                    break
                except Exception:
                    continue
            if not upload_ok:
                self.logger.warning("未能通过 input 注入图片，请确认页面上传区域已加载")

            # ---------- 5. 等待编辑区出现（标题输入框或预览图） ----------
            title_ready_selectors = [
                "input.d-text[placeholder*='填写标题']",
                "input[placeholder*='填写标题']",
                "input.d-text",
                "[data-placeholder*='标题']",
            ]
            deadline = time.time() + 60
            while time.time() < deadline:
                if "login" in (driver.current_url or ""):
                    raise PlatformException("发布过程中跳转登录页，请重新登录")
                for sel in title_ready_selectors:
                    try:
                        el = driver.find_element(By.CSS_SELECTOR, sel)
                        if el.is_displayed():
                            break
                    except Exception:
                        continue
                else:
                    time.sleep(0.5)
                    continue
                break
            time.sleep(5)

            # ---------- 6. 输入标题（可为空，最多20字） ----------
            title_selectors = [
                (By.CSS_SELECTOR, "input.d-text[placeholder*='填写标题']"),
                (By.CSS_SELECTOR, "input[placeholder*='填写标题会有更多赞哦']"),
                (By.CSS_SELECTOR, "input.d-text"),
                (By.XPATH, "//input[contains(@placeholder,'标题')]"),
            ]
            self._try_fill(driver, title_selectors, title_fill, clear_first=True, timeout=10)
            # 等待标题被页面提交后再动焦点，否则过早切到正文会导致标题丢失（2～10 秒随机）
            time.sleep(random.uniform(2, 10))
            
            # 确保焦点离开标题框，切换到正文区域
            try:
                ActionChains(driver).send_keys(Keys.TAB).perform()
                time.sleep(0.5)
                self.logger.info("已通过 Tab 键将焦点从标题切换到正文区域")
            except Exception as e:
                self.logger.warning("切换焦点失败: %s", e)

            # ---------- 7. 输入正文（contenteditable：先点击聚焦再向该元素 send_keys） ----------
            if not self._fill_contenteditable(driver, content or "", timeout=12):
                self.logger.warning("正文填入未成功，请检查页面正文输入框是否可用")
            
            # 关闭正文输入后弹出的模板话题蒙版（会遮挡发布按钮）
            try:
                time.sleep(1.5)
                self.logger.info("尝试关闭模板话题蒙版...")
                
                # 方案1：按 ESC 键关闭蒙版（最简单有效）
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.8)
                
                # 方案2：点击页面主体空白区域触发失焦
                driver.execute_script("""
                    // 查找并隐藏常见的蒙版层
                    var masks = document.querySelectorAll('.mask, .overlay, .modal, [class*="mask"], [class*="overlay"], [role="dialog"]');
                    masks.forEach(function(m) { 
                        if (m.offsetParent !== null) { // 只处理可见的
                            m.style.display = 'none'; 
                        }
                    });
                    // 点击 body 空白处触发失焦
                    document.body.click();
                """)
                time.sleep(0.8)
                
                # 方案3：如果还有蒙版，强制移除（不使用 :visible 伪类）
                driver.execute_script("""
                    var allElements = document.querySelectorAll('[class*="mask"], [class*="overlay"]');
                    allElements.forEach(function(el) {
                        // 检查元素是否可见
                        if (el.offsetParent !== null && el.offsetWidth > 0 && el.offsetHeight > 0) {
                            el.remove();
                        }
                    });
                """)
                time.sleep(0.5)
                
                self.logger.info("模板话题蒙版清理完成")
            except Exception as e:
                self.logger.warning("关闭模板话题蒙版异常: %s", e)

            if kwargs.get("tags"):
                try:
                    tags_str = " " + " ".join([f"#{t}" for t in kwargs["tags"]])
                    driver.switch_to.default_content()
                    ActionChains(driver).send_keys(tags_str).perform()
                except Exception:
                    pass

            # ---------- 8. 滚动到底部并点击「发布」 ----------
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                for _ in range(4):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.2)
            except Exception:
                pass
            final_publish_selectors = [
                (By.XPATH, "//button[contains(.,'确认发布')]"),
                (By.XPATH, "//button[contains(.,'立即发布')]"),
                (By.XPATH, "//button[contains(.,'发布') and not(contains(.,'暂存'))]"),
                (By.CSS_SELECTOR, "button.publishBtn"),
                (By.CSS_SELECTOR, ".publish-btn"),
                (By.XPATH, "//span[text()='发布']/ancestor::button"),
            ]
            publish_clicked = self._try_click(driver, final_publish_selectors, timeout=12)
            if not publish_clicked:
                raise PlatformException("未找到最终「发布」按钮")
            time.sleep(2)
            # 二次确认弹窗
            confirm_selectors = [
                (By.XPATH, "//div[@role='dialog']//button[contains(.,'确认发布')]"),
                (By.XPATH, "//div[@role='dialog']//button[contains(.,'确认')]"),
                (By.XPATH, "//div[@role='dialog']//button[contains(.,'确定')]"),
                (By.XPATH, "//button[contains(.,'确认发布')]"),
            ]
            self._try_click(driver, confirm_selectors, timeout=5)
            time.sleep(2)
            self.logger.info("笔记发布流程已完成")
            return True
        except PlatformException:
            raise
        except Exception as e:
            self.logger.error("发布笔记异常: %s", str(e))
            raise PlatformException("发布失败: " + str(e))
    
    def get_article_list(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        if not self.check_login_status():
            raise PlatformException("请先登录小红书")
        
        try:
            self.logger.info(f"获取笔记列表，页码: {page}")
            
            # 导航到笔记管理页面
            article_list_url = "https://creator.xiaohongshu.com/publish/publish?tab=published"
            self.selenium_manager.navigate_to(article_list_url)
            time.sleep(2)
            
            articles = []
            
            # 获取笔记元素列表
            try:
                article_elements = self.selenium_manager.get_driver().find_elements(
                    By.CSS_SELECTOR,
                    ".note-item, .article-item, .publish-item, [class*='note-card']"
                )
                
                for element in article_elements[:page_size]:
                    try:
                        title_elem = element.find_element(By.CSS_SELECTOR, ".title, .note-title, .article-title")
                        title = title_elem.text
                        
                        articles.append({
                            "title": title,
                            "platform": "xiaohongshu",
                        })
                    except:
                        continue
                        
            except Exception as e:
                self.logger.warning(f"解析笔记列表失败: {str(e)}")
            
            self.logger.info(f"获取到 {len(articles)} 篇笔记")
            return articles
            
        except Exception as e:
            self.logger.error(f"获取笔记列表异常: {str(e)}")
            raise PlatformException(f"获取笔记列表失败: {str(e)}")

