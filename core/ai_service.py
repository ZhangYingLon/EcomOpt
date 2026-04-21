"""
AI服务模块 - 用于内容生成、优化等功能
"""
from typing import Optional, List, Dict, Any
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from config.config import Config
from utils.logger import Logger
from utils.exceptions import AIException


class AIService:
    """AI服务类"""
    
    def __init__(self):
        self.logger = Logger.get_logger("AIService")
        self.config = Config.AI_CONFIG
        self.client = None
        self.client_initialized = False
        self._init_client()
    
    def _init_client(self):
        """初始化AI客户端"""
        try:
            if OpenAI is None:
                self.logger.warning("OpenAI库未安装，AI功能将不可用")
                return
            
            api_key = self.config.get("api_key", "")
            if not api_key:
                self.logger.warning("AI API Key未配置，部分功能可能无法使用")
                return
            
            self.client = OpenAI(api_key=api_key)
            self.client_initialized = True
            self.logger.info("AI服务初始化成功")
        except Exception as e:
            self.logger.error(f"AI服务初始化失败: {str(e)}")
            self.client_initialized = False
    
    def generate_content(self, prompt: str, max_tokens: int = None) -> Optional[str]:
        """
        生成内容
        
        Args:
            prompt: 提示词
            max_tokens: 最大token数
        
        Returns:
            生成的内容
        """
        if not self.client_initialized or self.client is None:
            raise AIException("AI服务未初始化，请检查API Key配置")
        
        try:
            max_tokens = max_tokens or self.config.get("max_tokens", 2000)
            model = self.config.get("model", "gpt-3.5-turbo")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的电商运营助手，擅长撰写吸引人的营销文案。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            self.logger.info(f"内容生成成功，长度: {len(content)}")
            return content
            
        except Exception as e:
            self.logger.error(f"内容生成失败: {str(e)}")
            raise AIException(f"内容生成失败: {str(e)}")
    
    def optimize_content(self, content: str, platform: str = "general") -> Optional[str]:
        """
        优化内容
        
        Args:
            content: 原始内容
            platform: 平台类型 (baijiahao, xiaohongshu, general)
        
        Returns:
            优化后的内容
        """
        platform_prompts = {
            "baijiahao": "请优化以下百家号文章内容，使其更具吸引力和可读性：\n\n",
            "xiaohongshu": "请优化以下小红书笔记内容，使其更符合小红书用户的阅读习惯，增加互动性：\n\n",
            "general": "请优化以下内容，使其更具吸引力和可读性：\n\n"
        }
        
        prompt = platform_prompts.get(platform, platform_prompts["general"]) + content
        return self.generate_content(prompt)
    
    def generate_title(self, content: str, platform: str = "general") -> Optional[str]:
        """
        生成标题
        
        Args:
            content: 内容
            platform: 平台类型
        
        Returns:
            生成的标题
        """
        platform_prompts = {
            "baijiahao": "根据以下内容，生成一个吸引人的百家号文章标题：\n\n",
            "xiaohongshu": "根据以下内容，生成一个吸引人的小红书笔记标题（建议包含表情符号）：\n\n",
            "general": "根据以下内容，生成一个吸引人的标题：\n\n"
        }
        
        prompt = platform_prompts.get(platform, platform_prompts["general"]) + content[:500]
        return self.generate_content(prompt, max_tokens=100)
    
    def generate_tags(self, content: str, platform: str = "general", count: int = 5) -> Optional[List[str]]:
        """
        生成标签
        
        Args:
            content: 内容
            platform: 平台类型
            count: 标签数量
        
        Returns:
            标签列表
        """
        prompt = f"根据以下内容，生成{count}个相关的标签或关键词（用逗号分隔）：\n\n{content[:500]}"
        
        try:
            result = self.generate_content(prompt, max_tokens=100)
            if result:
                tags = [tag.strip() for tag in result.split(',')]
                return tags[:count]
        except Exception as e:
            self.logger.error(f"生成标签失败: {str(e)}")
        
        return None

