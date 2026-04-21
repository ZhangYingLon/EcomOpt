"""
AI服务 - 支持国内大模型（阿里通义千问、百度千帆等）
百度千帆使用 OpenAI 兼容接口，仅需 api_key：https://qianfan.baidubce.com/v2
"""
from typing import Optional, List
import requests
import json
import base64
from pathlib import Path

from config.config import Config
from utils.logger import Logger
from utils.exceptions import AIException


class AIService:
    """AI服务类 - 支持国内大模型"""
    
    def __init__(self, provider: Optional[str] = None):
        self.logger = Logger.get_logger("AIService")
        self.config = Config.AI_CONFIG
        self.provider = provider if provider else self.config.get("provider", "dashscope")
        self._init_client()
    
    def _init_client(self):
        """初始化AI客户端"""
        try:
            if self.provider == "dashscope":
                # 阿里通义千问
                api_key = self.config.get("dashscope", {}).get("api_key") or self.config.get("api_key", "")
                if not api_key:
                    self.logger.warning("阿里通义千问API Key未配置")
                    self.client_initialized = False
                    return
                self.model = self.config.get("dashscope", {}).get("model", "qwen-turbo")
                self.vision_model = self.config.get("dashscope", {}).get("vision_model", "qwen-vl-plus")
                
            elif self.provider == "qianfan":
                # 百度千帆（OpenAI 兼容接口，仅需 api_key）
                api_key = self.config.get("qianfan", {}).get("api_key", "")
                if not api_key:
                    self.logger.warning("百度千帆 API Key 未配置")
                    self.client_initialized = False
                    return
                self.model = self.config.get("qianfan", {}).get("model", "ernie-4.5-turbo-128k")
                self.vision_model = self.config.get("qianfan", {}).get("vision_model", "ernie-4.5-turbo-vl")
                
            else:
                self.logger.warning(f"不支持的AI提供商: {self.provider}")
                self.client_initialized = False
                return
            
            self.client_initialized = True
            self.logger.info(f"AI服务初始化成功，提供商: {self.provider}, 文本模型: {self.model}, 视觉模型: {self.vision_model}")
            
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
        if not self.client_initialized:
            raise AIException("AI服务未初始化，请检查API Key配置")
        
        max_tokens = max_tokens or self.config.get("max_tokens", 2000)
        
        try:
            if self.provider == "dashscope":
                return self._generate_dashscope(prompt, max_tokens)
            elif self.provider == "qianfan":
                return self._generate_qianfan(prompt, max_tokens)
            else:
                raise AIException(f"不支持的AI提供商: {self.provider}")
        except Exception as e:
            self.logger.error(f"内容生成失败: {str(e)}")
            raise AIException(f"内容生成失败: {str(e)}")
    
    def _generate_dashscope(self, prompt: str, max_tokens: int) -> str:
        """使用阿里通义千问生成内容"""
        api_key = self.config.get("dashscope", {}).get("api_key") or self.config.get("api_key", "")
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的电商运营助手，擅长撰写吸引人的营销文案。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        output = result.get("output", {})
        content = None
        if "text" in output:
            content = output["text"]
        elif "choices" in output and output["choices"]:
            content = output["choices"][0].get("message", {}).get("content")
        if content:
            self.logger.info(f"内容生成成功，长度: {len(content)}")
            return content
        raise AIException(f"API返回格式异常: {result}")
    
    def _generate_qianfan(self, prompt: str, max_tokens: int) -> str:
        """使用百度千帆生成内容（OpenAI 兼容接口，仅需 api_key，用 requests 直连避免 proxies 兼容问题）"""
        api_key = self.config.get("qianfan", {}).get("api_key", "")
        if not api_key:
            raise AIException("百度千帆 API Key 未配置")
        
        url = "https://qianfan.baidubce.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的电商运营助手，擅长撰写吸引人的营销文案。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content")
            if content:
                self.logger.info(f"内容生成成功，长度: {len(content)}")
                return content
        raise AIException("API 未返回有效内容")
    
    def optimize_content(self, content: str, platform: str = "general") -> Optional[str]:
        """
        优化内容（使用百度千帆模型）
        
        Args:
            content: 原始内容
            platform: 平台类型 (baijiahao, xiaohongshu, general)
        
        Returns:
            优化后的内容
        """
        import random
        # 保存原始提供商和模型
        original_provider = self.provider
        original_model = self.model
        
        try:
            # 临时切换到百度千帆
            self.provider = "qianfan"
            self.model = self.config.get("qianfan", {}).get("model", "ernie-4.5-turbo-128k")
            
            # 添加随机因子避免API缓存
            cache_buster = f"\n\n[优化版本v{random.randint(1000,9999)}]"
            
            platform_prompts = {
                "baijiahao": "请对以下内容进行优化改写，使其更具吸引力和可读性。要求：\n1. 保持原意不变\n2. 优化语言表达，使其更流畅\n3. 增加一些生动的描述\n4. 每次生成不同的表达方式\n5. 只返回优化后的正文，不要添加任何说明\n\n待优化内容：\n\n",
                "xiaohongshu": "请对以下内容进行小红书风格优化改写。要求：\n1. 保持原意不变\n2. 增加表情符号和互动性语言\n3. 使用更活泼、亲切的表达方式\n4. 分段清晰，易于阅读\n5. 每次生成不同的表达方式\n6. 只返回优化后的正文，不要添加任何说明\n\n待优化内容：\n\n",
                "general": "请对以下内容进行优化改写，使其更具吸引力。要求：\n1. 保持原意不变\n2. 优化语言表达\n3. 每次生成不同的表达方式\n4. 只返回优化后的正文，不要添加任何说明\n\n待优化内容：\n\n"
            }
            
            prompt = platform_prompts.get(platform, platform_prompts["general"]) + content + cache_buster
            result = self.generate_content(prompt, max_tokens=2000)
            return result
        finally:
            # 恢复原始提供商和模型
            self.provider = original_provider
            self.model = original_model
    
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
    
    def analyze_image(self, image_path: str, prompt: str = "请描述这张图片的内容") -> Optional[str]:
        """
        分析图片内容
        
        Args:
            image_path: 图片文件路径
            prompt: 分析提示词
        
        Returns:
            AI对图片的分析结果
        """
        if not self.client_initialized:
            raise AIException("AI服务未初始化，请检查API Key配置")
        
        try:
            # 读取图片并转换为Base64
            image_path = Path(image_path)
            if not image_path.exists():
                raise AIException(f"图片文件不存在: {image_path}")
            
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 获取图片格式
            image_format = image_path.suffix.lower().lstrip('.')
            if image_format in ['jpg', 'jpeg']:
                image_format = 'jpeg'
            elif image_format == 'png':
                image_format = 'png'
            else:
                raise AIException(f"不支持的图片格式: {image_format}")
            
            if self.provider == "dashscope":
                return self._analyze_image_dashscope(image_data, image_format, prompt)
            elif self.provider == "qianfan":
                return self._analyze_image_qianfan(image_data, image_format, prompt)
            else:
                raise AIException(f"不支持的AI提供商: {self.provider}")
                
        except AIException:
            raise
        except Exception as e:
            self.logger.error(f"图片分析失败: {str(e)}")
            raise AIException(f"图片分析失败: {str(e)}")
    
    def _analyze_image_dashscope(self, image_base64: str, image_format: str, prompt: str) -> str:
        """使用阿里通义千问VL模型分析图片"""
        api_key = self.config.get("dashscope", {}).get("api_key") or self.config.get("api_key", "")
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建多模态消息，使用视觉模型
        data = {
            "model": self.vision_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": f"data:image/{image_format};base64,{image_base64}"
                            },
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            },
            "parameters": {
                "max_tokens": 2000,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        output = result.get("output", {})
        
        # 解析返回结果
        choices = output.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", [])
            # 查找文本内容
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    self.logger.info(f"图片分析成功，长度: {len(text)}")
                    return text
        
        raise AIException(f"API返回格式异常: {result}")
    
    def _analyze_image_qianfan(self, image_base64: str, image_format: str, prompt: str) -> str:
        """使用百度千帆视觉模型分析图片"""
        api_key = self.config.get("qianfan", {}).get("api_key", "")
        if not api_key:
            raise AIException("百度千帆 API Key 未配置")
        
        url = "https://qianfan.baidubce.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建多模态消息，使用视觉模型
        data = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        # 检查响应状态
        if response.status_code == 401:
            error_detail = response.json() if response.content else {}
            self.logger.error(f"认证失败: {error_detail}")
            raise AIException(f"API Key 认证失败，请检查:\n1. API Key 是否正确\n2. 是否开通了视觉模型服务\n3. 账户余额是否充足\n详细信息: {error_detail}")
        elif response.status_code == 400:
            error_detail = response.json() if response.content else {}
            self.logger.error(f"请求格式错误: {error_detail}")
            raise AIException(f"请求格式错误: {error_detail}")
        
        response.raise_for_status()
        result = response.json()
        
        choices = result.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content")
            if content:
                self.logger.info(f"图片分析成功，长度: {len(content)}")
                return content
        
        raise AIException("API 未返回有效内容")
    
    def analyze_images_batch(self, image_paths: List[str], prompt: str = "请描述这些图片的内容") -> Optional[str]:
        """
        批量分析多张图片
        
        Args:
            image_paths: 图片文件路径列表
            prompt: 分析提示词
        
        Returns:
            AI对多张图片的分析结果
        """
        if not self.client_initialized:
            raise AIException("AI服务未初始化，请检查API Key配置")
        
        if not image_paths:
            raise AIException("图片路径列表不能为空")
        
        try:
            # 读取所有图片并转换为Base64
            images_data = []
            for image_path in image_paths:
                path = Path(image_path)
                if not path.exists():
                    self.logger.warning(f"图片文件不存在，跳过: {image_path}")
                    continue
                
                with open(path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                image_format = path.suffix.lower().lstrip('.')
                if image_format in ['jpg', 'jpeg']:
                    image_format = 'jpeg'
                
                images_data.append((image_data, image_format))
            
            if not images_data:
                raise AIException("没有有效的图片可以分析")
            
            if self.provider == "dashscope":
                return self._analyze_images_batch_dashscope(images_data, prompt)
            elif self.provider == "qianfan":
                return self._analyze_images_batch_qianfan(images_data, prompt)
            else:
                raise AIException(f"不支持的AI提供商: {self.provider}")
                
        except AIException:
            raise
        except Exception as e:
            self.logger.error(f"批量图片分析失败: {str(e)}")
            raise AIException(f"批量图片分析失败: {str(e)}")
    
    def _analyze_images_batch_dashscope(self, images_data: list, prompt: str) -> str:
        """使用阿里通义千问VL模型批量分析图片"""
        api_key = self.config.get("dashscope", {}).get("api_key") or self.config.get("api_key", "")
        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建多模态消息，包含所有图片，使用视觉模型
        content_list = []
        for image_base64, image_format in images_data:
            content_list.append({
                "image": f"data:image/{image_format};base64,{image_base64}"
            })
        content_list.append({"text": prompt})
        
        data = {
            "model": self.vision_model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content_list
                    }
                ]
            },
            "parameters": {
                "max_tokens": 2000,
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        output = result.get("output", {})
        
        choices = output.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", [])
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    self.logger.info(f"批量图片分析成功，长度: {len(text)}")
                    return text
        
        raise AIException(f"API返回格式异常: {result}")
    
    def _analyze_images_batch_qianfan(self, images_data: list, prompt: str) -> str:
        """使用百度千帆视觉模型批量分析图片"""
        api_key = self.config.get("qianfan", {}).get("api_key", "")
        if not api_key:
            raise AIException("百度千帆 API Key 未配置")
        
        url = "https://qianfan.baidubce.com/v2/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建多模态消息，包含所有图片，使用视觉模型
        content_list = []
        for image_base64, image_format in images_data:
            content_list.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{image_base64}"
                }
            })
        content_list.append({
            "type": "text",
            "text": prompt
        })
        
        data = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.8
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        choices = result.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content")
            if content:
                self.logger.info(f"批量图片分析成功，长度: {len(content)}")
                return content
        
        raise AIException("API 未返回有效内容")

