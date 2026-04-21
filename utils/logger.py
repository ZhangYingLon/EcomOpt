"""
日志工具模块
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from config.config import Config


class Logger:
    """日志管理类"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str = "EcomOpt") -> logging.Logger:
        """获取日志记录器"""
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            
            # 避免重复添加处理器
            if logger.handlers:
                return logger
            
            # 创建格式器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器
            log_file = Config.LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            cls._loggers[name] = logger
        
        return cls._loggers[name]


# 创建默认日志记录器
default_logger = Logger.get_logger()

