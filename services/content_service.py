"""
内容管理服务
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import time

from config.config import Config
from models.database import Database
from models.models import Content, ResourcePackage, Template, Account
from services.ai_service import AIService
from services.file_service import FileService
from utils.logger import Logger
from utils.exceptions import PlatformException
from platforms.baijiahao_platform import BaijiahaoPlatform
from platforms.xiaohongshu_platform import XiaohongshuPlatform


class ContentService:
    """内容管理服务"""
    
    def __init__(self, db: Database, ai_service: AIService, file_service: FileService):
        self.db = db
        self.ai_service = ai_service
        self.file_service = file_service
        self.logger = Logger.get_logger("ContentService")
    
    def generate_content_from_resource(self, resource_package_id: int, template_id: int) -> int:
        """
        根据资源包和话术模板生成内容
        Returns: 生成的内容ID
        """
        # 获取资源包信息
        package = ResourcePackage.get_by_id(self.db, resource_package_id)
        if not package:
            raise ValueError(f"资源包不存在: {resource_package_id}")
        
        # 获取模板
        template = Template.get_by_id(self.db, template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        # 获取资源文件列表
        resource_files = self.file_service.get_resource_files(resource_package_id)
        image_paths = self.file_service.get_package_image_paths(resource_package_id, max_count=5)
        
        # 构建提示词（分析文件夹名称和图片内容）
        prompt = self._build_generation_prompt(template['content'], package['name'], resource_files, image_paths)
        
        # 使用AI生成内容
        try:
            generated_text = self.ai_service.generate_content(prompt)
            
            # 解析生成的内容（假设返回标题和内容，用特殊分隔符分开）
            # 实际格式可能需要根据AI返回调整
            title, content = self._parse_generated_content(generated_text)
            
            # 创建内容记录
            content_id = Content.create(
                self.db,
                resource_package_id=resource_package_id,
                template_id=template_id,
                title=title,
                content=content
            )
            
            # 更新资源包统计
            ResourcePackage.update_stats(self.db, resource_package_id, content_generated=1)
            
            self.logger.info(f"内容生成成功: {content_id}")
            return content_id
            
        except Exception as e:
            self.logger.error(f"内容生成失败: {str(e)}")
            raise
    
    def batch_generate_content(self, resource_package_ids: List[int], template_id: int) -> List[int]:
        """批量生成内容"""
        content_ids = []
        for package_id in resource_package_ids:
            try:
                content_id = self.generate_content_from_resource(package_id, template_id)
                content_ids.append(content_id)
            except Exception as e:
                self.logger.error(f"批量生成失败 (资源包 {package_id}): {str(e)}")
        return content_ids
    
    def _build_generation_prompt(self, template: str, resource_name: str, 
                                resource_files: List[Path], image_paths: List[Path] = None) -> str:
        """构建生成提示词，结合文件夹信息和图片内容"""
        # 1. 从文件夹名称提取关键信息
        folder_info = self._extract_folder_info(resource_name)
        
        # 2. 分析图片内容（如果有图片）
        image_descriptions = []
        if image_paths and len(image_paths) > 0:
            try:
                self.logger.info(f"开始分析 {len(image_paths)} 张图片...")
                # 分析前3张图片作为参考
                for i, img_path in enumerate(image_paths[:3]):
                    try:
                        desc = self.ai_service.analyze_image(
                            str(img_path),
                            prompt="请详细描述这张图片的内容，包括产品特征、颜色、场景、文字信息等"
                        )
                        if desc:
                            image_descriptions.append(f"图片{i+1}: {desc}")
                            self.logger.info(f"图片{i+1}分析完成")
                    except Exception as e:
                        self.logger.warning(f"图片{i+1}分析失败: {e}")
                        continue
            except Exception as e:
                self.logger.warning(f"图片分析整体失败: {e}")
        
        # 3. 构建完整的提示词
        file_info = f"资源包包含 {len(resource_files)} 个文件"
        if resource_files:
            file_info += f"\n主要文件示例: {resource_files[0].name}"
        
        image_info = ""
        if image_descriptions:
            image_info = "\n\n图片内容分析:\n" + "\n\n".join(image_descriptions)
        
        prompt = f"""
请根据以下信息生成小红书/百家号风格的营销文案：

=== 产品信息 ===
资源包名称: {resource_name}
{folder_info}
{file_info}

=== 话术模板参考 ===
{template}

=== 图片内容参考 ===
{image_info}

=== 生成要求 ===
1. 标题要求：
   - 吸引眼球，符合平台风格
   - 突出产品卖点和优势
   - 长度适中（15-30字）
   - 可包含数字、表情符号

2. 内容要求：
   - 结合图片中的产品特征
   - 突出文件夹名称中的关键信息（品牌、价位、卖点）
   - 语言生动有趣，符合目标用户群体
   - 结构清晰，分段合理
   - 包含互动引导

3. 输出格式：
   直接输出标题（不要加"标题："前缀）
   ###
   正文内容

请生成标题和内容（标题和内容之间用 ### 分隔，标题不要加任何前缀）：
"""
        return prompt
    
    def _extract_folder_info(self, folder_name: str) -> str:
        """从文件夹名称中提取关键信息"""
        info_parts = []
        
        # 提取品类（如：洗碗机、电竞椅等）
        # 通常文件夹名格式："品类 描述_时间"
        parts = folder_name.split()
        if parts:
            category = parts[0]
            info_parts.append(f"产品品类: {category}")
        
        # 提取描述信息（如：整理、盲选、安利等）
        if len(parts) > 1:
            description = parts[1] if len(parts) > 1 else ""
            if description:
                info_parts.append(f"内容类型: {description}")
        
        # 尝试从完整名称中提取更多信息
        # 例如："6k价位段各品牌洗碗机天花板"
        if "价位" in folder_name or "k" in folder_name.lower():
            info_parts.append("价格区间: 文件夹名称中包含价格信息，请在文案中突出性价比")
        
        if "品牌" in folder_name:
            info_parts.append("多品牌对比: 文件夹涉及多个品牌，可以进行横向对比")
        
        if any(keyword in folder_name for keyword in ["天花板", "必备", "必看", "踩坑"]):
            info_parts.append("营销亮点: 文件夹名称包含强吸引力词汇，建议在标题中使用")
        
        return "\n".join(info_parts) if info_parts else ""
    
    def _parse_generated_content(self, generated_text: str) -> tuple:
        """解析生成的内容，提取标题和正文"""
        # 尝试用 ### 分隔符提取
        if "###" in generated_text:
            parts = generated_text.split("###", 1)
            title = parts[0].strip()
            content = parts[1].strip()
                
            # 清理标题前缀（如"标题："、"Title:"等）
            title = self._clean_title_prefix(title)
                
            return title, content
            
        # 如果没有分隔符，尝试从文本中提取
        lines = generated_text.strip().split('\n')
            
        # 过滤掉AI的对话性文字（如"当然可以"、"以下是"等）
        filtered_lines = []
        skip_patterns = ['当然可以', '以下是', '优化后的版本', '这个版本', '需要其他风格']
            
        for line in lines:
            # 跳过包含对话性文字的段落
            if any(pattern in line for pattern in skip_patterns):
                continue
            filtered_lines.append(line)
            
        # 重新组合
        cleaned_text = '\n'.join(filtered_lines).strip()
            
        # 尝试提取第一行作为标题
        if cleaned_text:
            clean_lines = cleaned_text.split('\n', 1)
            title = clean_lines[0].strip()
            content = clean_lines[1].strip() if len(clean_lines) > 1 else ""
                
            # 清理标题前缀
            title = self._clean_title_prefix(title)
                
            # 如果标题太长，尝试找更合适的标题
            if len(title) > 50:
                # 查找可能的标题模式（包含#或较短的行）
                for line in clean_lines[0:10]:  # 在前10行查找
                    line = line.strip()
                    if line and (line.startswith('#') or (len(line) < 30 and len(line) > 5)):
                        title = line
                        # 找到标题后，内容是标题之后的部分
                        title_idx = cleaned_text.find(line)
                        if title_idx != -1:
                            content = cleaned_text[title_idx + len(line):].strip()
                        break
                
            return title, content
            
        # 最后的兜底方案
        return generated_text[:50], generated_text[50:]
        
    def _clean_title_prefix(self, title: str) -> str:
        """清理标题前缀（兜底方案）"""
        import re
        # 只处理最常见的前缀
        title = re.sub(r'^标题[:：\s]*', '', title)
        return title.strip()
    
    def get_all_contents(self, resource_package_id: int = None, 
                        status: str = None) -> List[Dict[str, Any]]:
        """获取所有内容"""
        return Content.get_all(self.db, resource_package_id, status)
    
    def _get_content_by_id(self, content_id: int) -> Optional[Dict[str, Any]]:
        row = self.db.execute_one("SELECT * FROM contents WHERE id = ?", (content_id,))
        return dict(row) if row else None
    
    def _get_account_by_id(self, account_id: int) -> Optional[Dict[str, Any]]:
        return Account.get_by_id(self.db, account_id)
    
    def _inject_cookie_and_login(self, platform_client, cookie_str: str, login_url: str, domain_hint: str) -> bool:
        """
        使用 cookie_str 注入浏览器 cookie 并判断是否登录成功。
        这里采用“打开登录页 -> 清 cookie -> 注入 -> refresh -> 通过 URL 判断”的简化策略。
        """
        if not cookie_str or not cookie_str.strip():
            return False
        
        driver = platform_client.selenium_manager.get_driver()
        driver.get(login_url)
        time.sleep(1)
        
        try:
            driver.delete_all_cookies()
        except Exception:
            pass
        
        for part in cookie_str.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, _, value = part.partition("=")
            name, value = name.strip(), value.strip()
            if not name:
                continue
            # 优先带 domain 注入；失败则降级不带 domain
            try:
                driver.add_cookie({"name": name, "value": value, "domain": domain_hint})
            except Exception:
                try:
                    driver.add_cookie({"name": name, "value": value})
                except Exception:
                    continue
        
        driver.refresh()
        time.sleep(2)
        current_url = (driver.current_url or "").lower()
        # 简单判断：被跳到 login/passport 则认为未登录
        if "login" in current_url or "passport" in current_url:
            return False
        return True
    
    def publish_content(self, content_id: int, account_id: int, platform: str) -> bool:
        """
        发布内容到平台
        通过 Selenium + 账号 Cookie 调用平台发布接口
        """
        content = self._get_content_by_id(content_id)
        if not content:
            raise ValueError(f"内容不存在: {content_id}")
        
        account = self._get_account_by_id(account_id)
        if not account:
            raise ValueError(f"账号不存在: {account_id}")
        if account.get("platform") != platform:
            raise ValueError(f"账号平台不匹配：账号={account.get('platform')}，发布平台={platform}")
        cookie_str = account.get("cookie") or ""
        if not cookie_str.strip():
            raise PlatformException("账号未设置 Cookie，请先在账号管理中登录并保存 Cookie")
        
        title = content.get("title") or ""
        body = content.get("content") or ""
        if not (title.strip() and body.strip()):
            raise ValueError("内容标题或正文为空，无法发布")
        
        if platform == "xiaohongshu":
            client = XiaohongshuPlatform()
            login_url = client.login_url
            logged_in = self._inject_cookie_and_login(client, cookie_str, login_url, ".xiaohongshu.com")
            client.is_logged_in = bool(logged_in)
            if not client.check_login_status():
                raise PlatformException("小红书 Cookie 可能已失效，请重新登录获取 Cookie")
            # 使用内容所属资源包中的图片（最多18张），直接用于发布，无需手选
            images = []
            rp_id = content.get("resource_package_id")
            if rp_id:
                images = self.file_service.get_package_image_paths(rp_id, max_count=18)
            ok = client.publish_article(title, body, images=images)
        elif platform == "baijiahao":
            client = BaijiahaoPlatform()
            login_url = client.login_url
            logged_in = self._inject_cookie_and_login(client, cookie_str, login_url, ".baidu.com")
            client.is_logged_in = bool(logged_in)
            if not client.check_login_status():
                raise PlatformException("百家号 Cookie 可能已失效，请重新登录获取 Cookie")
            images: List[str] = []
            rp_id = content.get("resource_package_id")
            if rp_id:
                images = [str(p) for p in self.file_service.get_package_image_paths(rp_id, max_count=20)]
            placeholder = str(Config.RESOURCES_DIR / "placeholder_publish.png")
            cover_image: Optional[str] = None
            if images:
                cover_image = images[0]
            elif os.path.isfile(placeholder):
                cover_image = placeholder
            ok = client.publish_article(title, body, images=images, cover_image=cover_image)
        else:
            raise ValueError(f"不支持的平台: {platform}")
        
        try:
            client.close()
        except Exception:
            pass
        
        if not ok:
            raise PlatformException("平台发布失败，请查看日志定位原因")
        
        # 发布成功才更新内容状态
        Content.update(self.db, content_id, status="published", account_id=account_id, platform=platform)
        ResourcePackage.update_stats(self.db, content["resource_package_id"], content_published=1)
        self.logger.info(f"内容发布成功: {content_id} -> {platform}")
        return True
    
    def batch_publish_content(self, content_ids: List[int], account_ids: List[int], 
                            platform: str) -> List[int]:
        """批量发布内容"""
        published_ids = []
        for content_id in content_ids:
            for account_id in account_ids:
                try:
                    if self.publish_content(content_id, account_id, platform):
                        published_ids.append(content_id)
                        break  # 一个内容只需要发布一次
                except Exception as e:
                    self.logger.error(f"发布失败 (内容 {content_id}): {str(e)}")
        return published_ids
    
    def delete_content(self, content_id: int):
        """删除内容"""
        sql = "DELETE FROM contents WHERE id = ?"
        self.db.execute_update(sql, (content_id,))
        self.logger.info(f"删除内容: {content_id}")

