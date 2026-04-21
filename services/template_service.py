"""
话术模板管理服务
"""
from typing import List, Dict, Any, Optional

from models.database import Database
from models.models import Template
from utils.logger import Logger


class TemplateService:
    """话术模板管理服务"""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = Logger.get_logger("TemplateService")
    
    def create_template(self, name: str, content: str, description: str = None,
                       platform: str = None) -> int:
        """创建话术模板"""
        try:
            template_id = Template.create(self.db, name, content, description, platform)
            self.logger.info(f"创建话术模板成功: {name} (ID: {template_id})")
            return template_id
        except Exception as e:
            self.logger.error(f"创建话术模板失败: {str(e)}")
            raise
    
    def get_all_templates(self, platform: str = None) -> List[Dict[str, Any]]:
        """获取所有模板"""
        return Template.get_all(self.db, platform)
    
    def get_template_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取模板"""
        return Template.get_by_id(self.db, template_id)
    
    def update_template(self, template_id: int, name: str = None, content: str = None,
                       description: str = None, platform: str = None):
        """更新模板"""
        try:
            Template.update(self.db, template_id, name, content, description, platform)
            self.logger.info(f"更新话术模板成功: {template_id}")
        except Exception as e:
            self.logger.error(f"更新话术模板失败: {str(e)}")
            raise
    
    def delete_template(self, template_id: int):
        """删除模板"""
        try:
            Template.delete(self.db, template_id)
            self.logger.info(f"删除话术模板成功: {template_id}")
        except Exception as e:
            self.logger.error(f"删除话术模板失败: {str(e)}")
            raise

