"""
配置文件管理模块
"""
import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    """配置管理类"""
    
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / "config"
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"
    RESOURCES_DIR = BASE_DIR / "resources"
    UPLOADS_DIR = BASE_DIR / "uploads"
    EXTRACTED_DIR = BASE_DIR / "extracted"
    TOOLS_DIR = BASE_DIR / "tools"
    
    # 平台配置
    PLATFORMS = {
        "baijiahao": {
            "name": "百家号",
            "enabled": True,
            "login_url": "https://baijiahao.baidu.com/",
        },
        "xiaohongshu": {
            "name": "小红书",
            "enabled": True,
            "login_url": "https://creator.xiaohongshu.com/",
        }
    }
    
    # Selenium配置
    SELENIUM_CONFIG = {
        "headless": False,
        "wait_timeout": 10,
        "implicit_wait": 5,
        "window_size": (1920, 1080),
        "chrome_driver_path": None,  # 如果指定路径，则使用指定的驱动；None则从tools目录查找
    }
    
    # AI配置 - 支持国内大模型
    AI_CONFIG = {
        "provider": "dashscope",  # dashscope(阿里), qianfan(百度), etc.
        "api_key": "",
        "model": "qwen-turbo",  # 阿里通义千问
        "max_tokens": 2000,
        # 百度千帆配置（OpenAI 兼容接口，仅需 api_key）
        "qianfan": {
            "api_key": "",
            "model": "ernie-4.5-turbo-128k",
            "vision_model": "ernie-4.5-turbo-vl",  # 视觉模型
        },
        # 阿里通义千问配置
        "dashscope": {
            "api_key": "",
            "model": "qwen-turbo",
            "vision_model": "qwen-vl-plus",  # 视觉模型：qwen-vl-plus 或 qwen-vl-max
        }
    }
    
    # 数据库配置（如果需要）
    DATABASE_CONFIG = {
        "type": "sqlite",
        "path": str(DATA_DIR / "ecom.db"),
    }
    
    # 账号刷新配置
    ACCOUNT_CONFIG = {
        "refresh_interval": 3600,  # 刷新间隔（秒），默认1小时
        "auto_refresh": True,  # 是否自动刷新
    }
    
    @classmethod
    def init_directories(cls):
        """初始化必要的目录"""
        directories = [
            cls.CONFIG_DIR, cls.DATA_DIR, cls.LOGS_DIR, 
            cls.RESOURCES_DIR, cls.UPLOADS_DIR, cls.EXTRACTED_DIR,
            cls.TOOLS_DIR
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_config(cls, config_file: str = "settings.json") -> Dict[str, Any]:
        """从文件加载配置"""
        config_path = cls.CONFIG_DIR / config_file
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @classmethod
    def save_config(cls, config: Dict[str, Any], config_file: str = "settings.json"):
        """保存配置到文件"""
        config_path = cls.CONFIG_DIR / config_file
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)


# 初始化目录
Config.init_directories()

