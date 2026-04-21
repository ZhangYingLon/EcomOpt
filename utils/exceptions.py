"""
自定义异常类
"""


class EcomOptException(Exception):
    """基础异常类"""
    pass


class PlatformException(EcomOptException):
    """平台相关异常"""
    pass


class SeleniumException(EcomOptException):
    """Selenium自动化异常"""
    pass


class AIException(EcomOptException):
    """AI服务异常"""
    pass


class ConfigException(EcomOptException):
    """配置异常"""
    pass

