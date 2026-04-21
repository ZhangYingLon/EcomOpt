"""
百家号平台模块
"""
from typing import Dict, Any, Optional, List, Tuple, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

from platforms.base_platform import BasePlatform
from config.config import Config
from utils.exceptions import PlatformException


# 百家号标题字数限制（页面提示 2-64 字）
BJH_TITLE_MAX_LEN = 64

# ---------------------------------------------------------------------------
# 图文发布 XPath：请按你本地页面填写；也可在 publish_article(..., kwargs) 中覆盖同名参数。
# body_image_trigger_xpaths：工具栏「插入图片」等，点击后弹出「本地图片 / 本地上传」弹窗。
# cover_trigger_xpaths：基础信息区「选择封面」，需先滚动到页面下方才能点击。
# modal_confirm_xpaths（kwargs）或 BJH_MODAL_CONFIRM_XPATHS：弹窗底部「确定/确认」优先 XPath。
# ---------------------------------------------------------------------------
BJH_BODY_IMAGE_TRIGGER_XPATHS: List[str] = [
    '//*[@id="edui29_body"]',
]
BJH_COVER_TRIGGER_XPATHS: List[str] = [
    '//*[@id="bjhNewsCover"]/div/div/div[2]/div/div/div[2]/div/div/div/div/div[1]',
]
# 可选：插图弹窗「确认」、封面弹窗「确定」等；留空则使用 _wait_and_click_modal_confirm 内的通用兜底
BJH_MODAL_CONFIRM_XPATHS: List[str] = ['/html/body/div[6]/div/div[2]/div/div[1]/div/div[2]/button[2]/span',
                                       '//*[@id="rc-tabs-3-panel-local_main"]/div/div[2]/button[2]/span',]



class BaijiahaoPlatform(BasePlatform):
    """百家号平台类"""
    
    def __init__(self):
        super().__init__("baijiahao")
        self.config = Config.PLATFORMS["baijiahao"]
        self.login_url = self.config["login_url"]
    
    def login(self, username: str, password: str) -> bool:
        """登录百家号"""
        try:
            self.logger.info("开始登录百家号...")
            driver = self.selenium_manager.get_driver()
            self.selenium_manager.navigate_to(self.login_url)
            
            # 等待页面加载
            time.sleep(2)
            
            # 这里需要根据实际的百家号登录页面来定位元素
            # 以下是示例代码，需要根据实际情况调整
            
            # 查找登录按钮或输入框
            # 注意：实际使用时需要根据网页结构调整选择器
            try:
                # 等待登录入口出现
                login_btn = self.selenium_manager.wait_for_clickable(
                    By.CSS_SELECTOR, 
                    ".login-btn, .sign-in, [class*='login']", 
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
                    "input[name='username'], input[type='text'], input[placeholder*='账号']",
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
                if "baijiahao.baidu.com" in current_url and "login" not in current_url.lower():
                    self.is_logged_in = True
                    self.logger.info("百家号登录成功")
                    return True
                else:
                    self.logger.error("百家号登录失败，请检查账号密码")
                    return False
                    
            except Exception as e:
                self.logger.error(f"登录过程中出错: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"百家号登录异常: {str(e)}")
            raise PlatformException(f"登录失败: {str(e)}")
    
    def _try_wait_and_fill(self, driver, selectors: List[Tuple[By, str]], text: str, timeout: int = 20) -> bool:
        """依次尝试多组选择器，等待出现后清空并填入文本。支持 input/textarea 与 contenteditable。"""
        # 过滤掉非 BMP 字符（emoji 等），避免 ChromeDriver 报错
        def filter_non_bmp(t):
            return ''.join(char for char in t if ord(char) <= 0xFFFF)
        
        safe_text = filter_non_bmp(text or "")
        if len(safe_text) < len(text or ""):
            self.logger.warning("文本中包含 %d 个非 BMP 字符（如 emoji），已自动过滤", 
                              len(text or "") - len(safe_text))
        
        for by, value in selectors:
            try:
                el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.2)
                el.click()
                time.sleep(0.15)
                try:
                    el.clear()
                except Exception:
                    try:
                        el.send_keys(Keys.CONTROL + "a")
                        el.send_keys(Keys.BACKSPACE)
                    except Exception:
                        pass
                if safe_text:
                    el.send_keys(safe_text)
                return True
            except Exception:
                continue
        return False

    def _try_wait_and_click(self, driver, selectors: List[Tuple[By, str]], timeout: int = 15) -> bool:
        """依次尝试多组选择器，等待可点击后点击。"""
        for by, value in selectors:
            try:
                el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                el.click()
                return True
            except Exception:
                continue
        return False

    @staticmethod
    def _merge_xpath_lists(default_list: List[str], override: Union[None, str, List[str]]) -> List[str]:
        out = [x.strip() for x in (default_list or []) if x and str(x).strip()]
        if override is None:
            return out
        if isinstance(override, str) and override.strip():
            return out + [override.strip()]
        if isinstance(override, (list, tuple)):
            out.extend([str(x).strip() for x in override if x and str(x).strip()])
        return out

    def _scroll_page_to_bottom(self, driver, rounds: int = 5) -> None:
        """发布页较长，多次滚到底部以便露出「基础信息 / 选择封面」等区域。"""
        try:
            for _ in range(rounds):
                driver.execute_script(
                    "window.scrollTo(0, Math.max(document.body.scrollHeight,"
                    "document.documentElement.scrollHeight));"
                )
                time.sleep(0.25)
        except Exception as e:
            self.logger.debug("滚动页面到底部时忽略: %s", e)

    def _try_send_keys_to_file_inputs(self, driver, file_path: str) -> bool:
        """参考小红书：向页面（含弹窗内）的 file input 注入路径，从后往前优先匹配顶层弹窗。"""
        if not file_path or not os.path.isfile(file_path):
            self.logger.warning("图片路径无效或文件不存在: %s", file_path)
            return False
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for inp in reversed(inputs):
            try:
                inp.send_keys(file_path)
                return True
            except Exception:
                continue
        return False

    def _click_element_hard(self, driver, el) -> None:
        """Ant Design 等场景下常规 click 易失败，优先滚入视口后 JS 点击。"""
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.1)
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)

    def _visible_modal_roots(self, driver) -> List[Any]:
        """取当前页上可见的弹窗内容根节点（从后往前一般为最顶层）。"""
        roots = []
        for xp in (
            "//div[contains(@class,'ant-modal-content')]",
            "//div[contains(@class,'Modal') and contains(@class,'content')]",
            "//div[@role='dialog']",
        ):
            try:
                for el in driver.find_elements(By.XPATH, xp):
                    try:
                        if el.is_displayed():
                            roots.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return roots

    def _wait_and_click_modal_confirm(
        self, driver, extra_xpaths: Optional[List[str]] = None, timeout: int = 20
    ) -> bool:
        """
        插图/封面弹窗点「确认」「确定」。优化版：快速定位，减少冗余查找。
        """
        time.sleep(1.0)  # 等待弹窗出现
        deadline = time.time() + timeout
        
        # # 优先使用配置的 XPath
        # merged = self._merge_xpath_lists(BJH_MODAL_CONFIRM_XPATHS, extra_xpaths)
        # xpath_selectors: List[Tuple[By, str]] = [(By.XPATH, xp) for xp in merged]

        while time.time() < deadline:
            # # 1）尝试配置的 XPath
            # for by, loc in xpath_selectors:
            #     try:
            #         for el in driver.find_elements(by, loc):
            #             try:
            #                 if el.is_displayed() and el.size.get("width", 0) > 5:
            #                     self._click_element_hard(driver, el)
            #                     time.sleep(0.3)
            #                     return True
            #             except Exception:
            #                 continue
            #     except Exception:
            #         continue

            # 2）弹窗内找「确认」或「确定」按钮（仅查找可见弹窗）
            roots = self._visible_modal_roots(driver)
            if roots:
                root = roots[-1]  # 最顶层弹窗
                try:
                    # 优先查找明确包含"确认/确定"的按钮
                    for btn in root.find_elements(By.TAG_NAME, "button"):
                        text = (btn.text or "").strip()
                        if ("确认" in text or "确定" in text) and "取消" not in text:
                            if btn.is_displayed():
                                self._click_element_hard(driver, btn)
                                time.sleep(0.3)
                                return True
                except Exception:
                    pass
                
                # 兜底：找弹窗页脚的最后一个按钮
                try:
                    foot_btns = root.find_elements(
                        By.XPATH, ".//div[contains(@class,'modal-footer')]//button | .//div[contains(@class,'footer')]//button"
                    )
                    if foot_btns:
                        btn = foot_btns[-1]  # 最后一个按钮通常是确认
                        text = (btn.text or "").strip()
                        if "取消" not in text and btn.is_displayed():
                            self._click_element_hard(driver, btn)
                            time.sleep(0.3)
                            return True
                except Exception:
                    pass

            time.sleep(0.3)  # 缩短轮询间隔
        return False

    def _upload_via_toolbar_modal(
        self,
        driver,
        trigger_xpaths: List[str],
        image_paths: List[str],
        confirm_xpaths: Optional[List[str]] = None,
    ) -> bool:
        """点击工具栏触发按钮 -> 弹窗内批量 send_keys 多张图片 -> 点确认/确定。"""
        driver.switch_to.default_content()
        if not trigger_xpaths:
            self.logger.warning("未配置正文插图触发 XPath，跳过批量上传")
            return False
        if not image_paths:
            self.logger.warning("图片路径列表为空")
            return False
            
        selectors = [(By.XPATH, xp) for xp in trigger_xpaths]
        if not self._try_wait_and_click(driver, selectors, timeout=12):
            self.logger.error("点击正文插图入口失败，请检查 BJH_BODY_IMAGE_TRIGGER_XPATHS 或 body_image_trigger_xpaths")
            return False
        time.sleep(0.3)  # 缩短等待
        
        # 批量发送所有图片路径到 file input
        for idx, img_path in enumerate(image_paths):
            if not os.path.isfile(img_path):
                self.logger.warning("跳过不存在的图片 (%d): %s", idx + 1, img_path)
                continue
            
            try:
                # 每次发送前重新查找 file input（避免 stale element）
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                if not inputs:
                    self.logger.error("第 %d 张图片：未找到 file input", idx + 1)
                    return False
                
                # 使用最后一个（通常是顶层弹窗的）input
                file_input = inputs[-1]
                file_input.send_keys(img_path)
                self.logger.info("已添加第 %d/%d 张图片: %s", idx + 1, len(image_paths), os.path.basename(img_path))
                time.sleep(0.2)  # 缩短等待时间
            except Exception as e:
                self.logger.error("发送第 %d 张图片路径失败: %s", idx + 1, str(e))
                return False
        
        # 点击确认
        if not self._wait_and_click_modal_confirm(driver, extra_xpaths=confirm_xpaths, timeout=20):
            self.logger.warning("正文插图后未点到「确认/确定」，请检查弹窗")
            return False
        time.sleep(0.5)  # 缩短等待
        return True

    def _upload_cover_flow(
        self, driver, cover_path: str, trigger_xpaths: List[str], modal_confirm_xpaths: Optional[List[str]] = None
    ) -> bool:
        """先滚到底再点「选择封面」，弹窗内本地上传后点确定。"""
        driver.switch_to.default_content()
        self._scroll_page_to_bottom(driver)
        time.sleep(0.5)
        if not trigger_xpaths:
            self.logger.warning("未配置封面区域 XPath，跳过封面上传")
            return False
        if not self._try_wait_and_click(driver, [(By.XPATH, xp) for xp in trigger_xpaths], timeout=15):
            self.logger.error("点击「选择封面」失败，请检查 BJH_COVER_TRIGGER_XPATHS 或 cover_trigger_xpaths")
            return False
        time.sleep(1.0)
        if not self._try_send_keys_to_file_inputs(driver, cover_path):
            self.logger.error("封面弹窗内未找到 file input")
            return False
        if not self._wait_and_click_modal_confirm(
            driver, extra_xpaths=modal_confirm_xpaths, timeout=60
        ):
            self.logger.warning("封面未点到「确定/确认」，请检查 BJH_MODAL_CONFIRM_XPATHS 或 modal_confirm_xpaths")
            return False
        return True

    def _dismiss_baijiahao_overlays(self, driver) -> None:
        """关闭发布页蒙版弹窗：优先点击叉叉关闭，再点「我知道了」，最后处理 AI 引导。"""
        try:
            # 2）「新增风险检测」弹窗 -> 点击「我知道了」
            ok_selectors = [
                (By.XPATH, "//button[contains(.,'我知道了')]"),
                (By.XPATH, "//*[contains(text(),'我知道了')]/ancestor::button"),
                (By.XPATH, "//span[text()='我知道了']/ancestor::button"),
            ]
            for by, value in ok_selectors:
                try:
                    el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((by, value)))
                    el.click()
                    self.logger.info("已点击「我知道了」关闭风险检测弹窗")
                    time.sleep(0.8)
                    break
                except Exception:
                    continue

            # 3）「AI工具收起」引导蒙版 -> 点击关闭
            ai_close_selectors = [
                (By.XPATH, "//*[contains(.,'让AI工具收起')]"),
                (By.XPATH, "//button[contains(.,'让AI工具收起')]"),
                (By.XPATH, "//div[contains(.,'AI工具收起')]//*[contains(@class,'close')]"),
                (By.CSS_SELECTOR, "[aria-label='close'], .ant-modal-close"),
            ]
            for by, value in ai_close_selectors:
                try:
                    el = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((by, value)))
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    el.click()
                    self.logger.info("已关闭 AI 工具引导蒙版")
                    time.sleep(0.8)
                    break
                except Exception:
                    continue
            else:
                # 若无关闭按钮，尝试多次点击「下一步」走完引导
                for _ in range(4):
                    try:
                        next_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'下一步')]"))
                        )
                        next_btn.click()
                        time.sleep(0.5)
                    except Exception:
                        break
        except Exception as e:
            self.logger.debug("关闭蒙版时忽略: %s", e)

    def publish_article(self, title: str, content: str, **kwargs) -> bool:
        """
        发布百家号图文。
        kwargs:
            images: 正文中插入的本地图片路径列表（逐张点击插图入口并走本地上传弹窗）。
            cover_image: 封面图路径；若不传且 images 非空，默认用 images[0] 作为封面。
            body_image_trigger_xpaths / cover_trigger_xpaths / modal_confirm_xpaths:
                与模块顶部 BJH_* 合并，便于在调用处临时覆盖（XPath 字符串或列表）。
        """
        if not self.check_login_status():
            raise PlatformException("请先登录百家号")
        try:
            self.logger.info("开始发布文章: %s", title[:20] if title else "")
            driver = self.selenium_manager.get_driver()
            publish_url = "https://baijiahao.baidu.com/builder/rc/edit?type=news"
            self.selenium_manager.navigate_to(publish_url)
            self.logger.info("发布页已跳转，等待数秒后开始定位...")
            # 页面为 SPA，短暂等待后即开始定位，避免长时间无操作
            time.sleep(3)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: "edit" in (d.current_url or "") and "baijiahao" in (d.current_url or "")
                )
            except Exception:
                pass
            time.sleep(2)
            self.logger.info("尝试关闭蒙版弹窗（我知道了 / AI工具收起）...")
            self._dismiss_baijiahao_overlays(driver)
            time.sleep(1)
            self.logger.info("已进入发布页，正在定位标题输入框（每个选择器最多等 6 秒）...")

            # 标题：页面为 contenteditable，占位「请输入标题（2 - 64字）」、data-testid="news-title-input"
            title_raw = (title or "").strip()
            if len(title_raw) > BJH_TITLE_MAX_LEN:
                self.logger.warning("百家号标题最多 %d 字，已截断", BJH_TITLE_MAX_LEN)
            title_fill = title_raw[:BJH_TITLE_MAX_LEN] if title_raw else ""
            title_selectors = [
                (By.XPATH, "//div[contains(@class,'placeholder') and contains(.,'请输入标题')]/following-sibling::div[@contenteditable='true']"),
                (By.XPATH, "//div[@data-testid='news-title-input']//div[@contenteditable='true']"),
                (By.CSS_SELECTOR, "div[data-testid='news-title-input'] [contenteditable='true']"),
                (By.CSS_SELECTOR, "#bjhNewsTitle [contenteditable='true']"),
                (By.CSS_SELECTOR, "#newsTextArea [contenteditable='true']"),
                (By.CSS_SELECTOR, "input[placeholder*='标题']"),
                (By.CSS_SELECTOR, "input[placeholder*='请输入标题']"),
                (By.CSS_SELECTOR, "input[name='title']"),
            ]
            title_ok = self._try_wait_and_fill(driver, title_selectors, title_fill, timeout=6)
            if not title_ok:
                self.logger.info("主文档未找到标题框，尝试在 iframe 中查找...")
                try:
                    for frame in driver.find_elements(By.TAG_NAME, "iframe"):
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame(frame)
                            title_ok = self._try_wait_and_fill(driver, title_selectors, title_fill, timeout=5)
                            if title_ok:
                                break
                        except Exception:
                            continue
                    if not title_ok:
                        driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
            if not title_ok:
                self.logger.error("输入标题失败: 所有选择器均未找到标题输入框")
                return False

            # 正文：在 iframe#ueditor_0 内，占位「请输入正文」；UEditor 编辑区在 iframe body
            driver.switch_to.default_content()
            content_ok = False
            self.logger.info("正在定位正文编辑区（iframe#ueditor_0）...")
            
            # 过滤掉非 BMP 字符
            def filter_non_bmp(t):
                return ''.join(char for char in t if ord(char) <= 0xFFFF)
            
            safe_content = filter_non_bmp(content or "")
            if len(safe_content) < len(content or ""):
                self.logger.warning("正文中包含 %d 个非 BMP 字符（如 emoji），已自动过滤", 
                                  len(content or "") - len(safe_content))
            
            try:
                frame = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "iframe#ueditor_0"))
                )
                driver.switch_to.frame(frame)
                body = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                body.click()
                time.sleep(0.2)
                try:
                    body.send_keys(Keys.CONTROL + "a")
                    body.send_keys(Keys.BACKSPACE)
                except Exception:
                    pass
                body.send_keys(safe_content)
                content_ok = True
                self.logger.info("正文已填入 ueditor_0 iframe body")
            except Exception:
                pass
            driver.switch_to.default_content()
            if not content_ok:
                content_selectors = [
                    (By.CSS_SELECTOR, ".editor-content"),
                    (By.CSS_SELECTOR, "textarea[name='content']"),
                    (By.CSS_SELECTOR, "[contenteditable='true']"),
                    (By.XPATH, "//*[contains(@class,'holderText') and contains(.,'请输入正文')]/ancestor::*//*[@contenteditable='true']"),
                ]
                self.logger.info("正文 iframe 未就绪，尝试主文档选择器...")
                content_ok = self._try_wait_and_fill(driver, content_selectors, safe_content, timeout=6)
            if not content_ok:
                try:
                    for frame_el in driver.find_elements(By.TAG_NAME, "iframe"):
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame(frame_el)
                            body = driver.find_element(By.TAG_NAME, "body")
                            body.click()
                            body.send_keys(Keys.CONTROL + "a")
                            body.send_keys(Keys.BACKSPACE)
                            body.send_keys(safe_content)
                            content_ok = True
                            break
                        except Exception:
                            continue
                    if not content_ok:
                        driver.switch_to.default_content()
                except Exception:
                    driver.switch_to.default_content()
            if not content_ok:
                self.logger.error("输入内容失败: 未找到正文输入区域")
                return False

            driver.switch_to.default_content()
            image_paths = [str(p) for p in (kwargs.get("images") or []) if p]
            body_triggers = self._merge_xpath_lists(
                BJH_BODY_IMAGE_TRIGGER_XPATHS, kwargs.get("body_image_trigger_xpaths")
            )
            cover_triggers = self._merge_xpath_lists(
                BJH_COVER_TRIGGER_XPATHS, kwargs.get("cover_trigger_xpaths")
            )
            confirm_kw = self._merge_xpath_lists([], kwargs.get("modal_confirm_xpaths"))

            if image_paths:
                if not body_triggers:
                    self.logger.warning(
                        "有 %d 张配图但未配置正文插图 XPath（BJH_BODY_IMAGE_TRIGGER_XPATHS），跳过正文批量插图",
                        len(image_paths),
                    )
                else:
                    self.logger.info("开始批量插入正文配图，共 %d 张", len(image_paths))
                    # 一次性打开弹窗，批量发送所有图片
                    if not self._upload_via_toolbar_modal(
                        driver, body_triggers, image_paths, confirm_xpaths=confirm_kw
                    ):
                        self.logger.error("正文批量插图失败")
                        return False
                    time.sleep(1.5)
            elif body_triggers:
                self.logger.debug("已配置正文插图 XPath 但未提供 images，跳过插图")

            if kwargs.get("tags"):
                driver.switch_to.default_content()
                tags_selectors = [
                    (By.CSS_SELECTOR, "input[placeholder*='标签']"),
                    (By.CSS_SELECTOR, "input[name='tags']"),
                ]
                self._try_wait_and_fill(driver, tags_selectors, ",".join(kwargs["tags"]), timeout=5)

            driver.switch_to.default_content()
            time.sleep(0.5)

            cover_path = kwargs.get("cover_image")
            if cover_path is None and image_paths:
                cover_path = image_paths[0]
            if cover_path:
                cover_path = str(cover_path).strip()
            if cover_path and os.path.isfile(cover_path):
                if not cover_triggers:
                    self.logger.warning(
                        "已准备封面文件但未配置封面 XPath（BJH_COVER_TRIGGER_XPATHS），跳过封面上传；"
                        "若平台强制封面，发布可能失败"
                    )
                else:
                    self.logger.info("开始上传封面（页面需下滑至「设置封面」区域）")
                    if not self._upload_cover_flow(
                        driver, cover_path, cover_triggers, modal_confirm_xpaths=confirm_kw
                    ):
                        self.logger.error("封面上传未完成，发布可能被平台拦截")
                        return False
            elif cover_path:
                self.logger.warning("封面路径无效，跳过: %s", cover_path)
            elif cover_triggers:
                self.logger.warning("已配置封面 XPath 但未提供 cover_image / images，跳过封面")

            self._scroll_page_to_bottom(driver)
            time.sleep(0.5)
            self.logger.info("正在定位发布按钮...")
            # 发布按钮：data-testid="publish-btn"，文案「发布」
            publish_selectors = [
                (By.CSS_SELECTOR, "button[data-testid='publish-btn']"),
                (By.CSS_SELECTOR, "[data-testid='publish-btn']"),
                (By.XPATH, "//button[.//span[text()='发布']]"),
                (By.XPATH, "//button[contains(.,'发布')]"),
                (By.CSS_SELECTOR, "button.cheetah-btn-primary span"),
            ]
            if not self._try_wait_and_click(driver, publish_selectors, timeout=8):
                self.logger.error("未找到发布按钮")
                return False
            time.sleep(2)
            self.logger.info("文章发布请求已提交")
            return True
        except Exception as e:
            self.logger.error("发布文章异常: %s", str(e))
            raise PlatformException("发布失败: " + str(e))

    def get_article_list(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """获取文章列表"""
        if not self.check_login_status():
            raise PlatformException("请先登录百家号")
        
        try:
            self.logger.info(f"获取文章列表，页码: {page}")
            
            # 导航到文章管理页面
            # 注意：需要根据实际URL调整
            article_list_url = "https://baijiahao.baidu.com/builder/rc/article/list"
            self.selenium_manager.navigate_to(article_list_url)
            time.sleep(2)
            
            articles = []
            
            # 这里需要根据实际的列表页面结构来解析文章
            # 以下是示例代码，需要根据实际情况调整
            
            # 获取文章元素列表
            try:
                article_elements = self.selenium_manager.get_driver().find_elements(
                    By.CSS_SELECTOR,
                    ".article-item, .article-list-item, [class*='article-card']"
                )
                
                for element in article_elements[:page_size]:
                    try:
                        title_elem = element.find_element(By.CSS_SELECTOR, ".title, .article-title")
                        title = title_elem.text
                        
                        # 获取其他信息（时间、阅读量等）
                        # 这里需要根据实际页面结构调整
                        
                        articles.append({
                            "title": title,
                            "platform": "baijiahao",
                            # 可以添加更多字段
                        })
                    except:
                        continue
                        
            except Exception as e:
                self.logger.warning(f"解析文章列表失败: {str(e)}")
            
            self.logger.info(f"获取到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            self.logger.error(f"获取文章列表异常: {str(e)}")
            raise PlatformException(f"获取文章列表失败: {str(e)}")

