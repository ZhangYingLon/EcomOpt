"""
数据模型类
"""
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from models.database import Database


class User:
    """系统登录用户（与平台账号 Account 区分）"""

    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def create_user(db: Database, username: str, password: str, role: str) -> Tuple[bool, str]:
        """注册用户。成功返回 (True, '')，失败返回 (False, 原因)。"""
        username = (username or "").strip()
        if not username or not password:
            return False, "用户名和密码不能为空"
        if role not in ("admin", "operator"):
            return False, "无效角色"
        sql = """
            INSERT INTO users (username, password_hash, role, updated_at)
            VALUES (?, ?, ?, ?)
        """
        try:
            db.execute_update(
                sql,
                (username, User.hash_password(password), role, datetime.now()),
            )
            return True, ""
        except sqlite3.IntegrityError:
            return False, "用户名已存在"

    @staticmethod
    def authenticate(db: Database, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证登录。成功返回 {id, username, role}，否则 None。"""
        username = (username or "").strip()
        if not username or not password:
            return None
        row = db.execute_one(
            "SELECT id, username, password_hash, role FROM users WHERE username = ?",
            (username,),
        )
        if not row:
            return None
        if row["password_hash"] != User.hash_password(password):
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
        }


class Account:
    """账号模型"""
    
    def __init__(self, db: Database):
        self.db = db
    
    @staticmethod
    def create(db: Database, platform: str, username: str, nickname: str = None, 
               cookie: str = None, status: str = 'invalid') -> int:
        """创建账号"""
        sql = """
            INSERT INTO accounts (platform, username, nickname, cookie, status, last_refresh_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (platform, username, nickname, cookie, status, datetime.now())
        db.execute_update(sql, params)
        return db.execute_one("SELECT last_insert_rowid() as id")['id']
    
    @staticmethod
    def get_all(db: Database, platform: str = None) -> List[Dict[str, Any]]:
        """获取所有账号"""
        if platform:
            sql = "SELECT * FROM accounts WHERE platform = ? ORDER BY created_at DESC"
            rows = db.execute(sql, (platform,))
        else:
            sql = "SELECT * FROM accounts ORDER BY created_at DESC"
            rows = db.execute(sql)
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(db: Database, account_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取账号"""
        sql = "SELECT * FROM accounts WHERE id = ?"
        row = db.execute_one(sql, (account_id,))
        return dict(row) if row else None
    
    @staticmethod
    def update_cookie(db: Database, account_id: int, cookie: str, status: str = 'valid'):
        """更新Cookie和状态"""
        sql = """
            UPDATE accounts 
            SET cookie = ?, status = ?, last_refresh_time = ?, updated_at = ?
            WHERE id = ?
        """
        db.execute_update(sql, (cookie, status, datetime.now(), datetime.now(), account_id))
    
    @staticmethod
    def update_status(db: Database, account_id: int, status: str, update_refresh_time: bool = False):
        """更新状态，可选同时更新最后刷新时间"""
        if update_refresh_time:
            sql = "UPDATE accounts SET status = ?, last_refresh_time = ?, updated_at = ? WHERE id = ?"
            db.execute_update(sql, (status, datetime.now(), datetime.now(), account_id))
        else:
            sql = "UPDATE accounts SET status = ?, updated_at = ? WHERE id = ?"
            db.execute_update(sql, (status, datetime.now(), account_id))


class UploadRecord:
    """上传记录模型"""
    
    @staticmethod
    def create(db: Database, filename: str, file_path: str, file_size: int,
               total_chunks: int = 1, status: str = 'completed') -> int:
        """创建上传记录"""
        sql = """
            INSERT INTO upload_records (filename, file_path, file_size, total_chunks, uploaded_chunks, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (filename, file_path, file_size, total_chunks, 0, status)
        db.execute_update(sql, params)
        return db.execute_one("SELECT last_insert_rowid() as id")['id']
    
    @staticmethod
    def get_all(db: Database) -> List[Dict[str, Any]]:
        """获取所有上传记录"""
        sql = "SELECT * FROM upload_records ORDER BY upload_time DESC"
        rows = db.execute(sql)
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_status(db: Database, record_id: int, status: str, uploaded_chunks: int = None):
        """更新上传状态"""
        if uploaded_chunks is not None:
            sql = "UPDATE upload_records SET status = ?, uploaded_chunks = ? WHERE id = ?"
            db.execute_update(sql, (status, uploaded_chunks, record_id))
        else:
            sql = "UPDATE upload_records SET status = ? WHERE id = ?"
            db.execute_update(sql, (status, record_id))


class ResourcePackage:
    """资源包模型"""
    
    @staticmethod
    def create(db: Database, name: str, base_path: str, upload_record_id: int = None,
               directory_count: int = 0) -> int:
        """创建资源包"""
        sql = """
            INSERT INTO resource_packages (name, base_path, upload_record_id, directory_count)
            VALUES (?, ?, ?, ?)
        """
        params = (name, base_path, upload_record_id, directory_count)
        db.execute_update(sql, params)
        return db.execute_one("SELECT last_insert_rowid() as id")['id']
    
    @staticmethod
    def get_all(db: Database) -> List[Dict[str, Any]]:
        """获取所有资源包"""
        sql = """
            SELECT rp.*, ur.filename as upload_filename, ur.upload_time
            FROM resource_packages rp
            LEFT JOIN upload_records ur ON rp.upload_record_id = ur.id
            ORDER BY rp.created_at DESC
        """
        rows = db.execute(sql)
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(db: Database, package_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取资源包"""
        sql = "SELECT * FROM resource_packages WHERE id = ?"
        row = db.execute_one(sql, (package_id,))
        return dict(row) if row else None
    
    @staticmethod
    def update_stats(db: Database, package_id: int, content_generated: int = None,
                     content_published: int = None):
        """更新统计信息"""
        updates = []
        params = []
        if content_generated is not None:
            updates.append("content_generated = ?")
            params.append(content_generated)
        if content_published is not None:
            updates.append("content_published = ?")
            params.append(content_published)
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(package_id)
            sql = f"UPDATE resource_packages SET {', '.join(updates)} WHERE id = ?"
            db.execute_update(sql, tuple(params))


class Content:
    """内容模型"""
    
    @staticmethod
    def create(db: Database, resource_package_id: int, template_id: int = None,
               title: str = None, content: str = None) -> int:
        """创建内容"""
        sql = """
            INSERT INTO contents (resource_package_id, template_id, title, content, status)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (resource_package_id, template_id, title, content, 'pending')
        db.execute_update(sql, params)
        return db.execute_one("SELECT last_insert_rowid() as id")['id']
    
    @staticmethod
    def get_all(db: Database, resource_package_id: int = None, status: str = None) -> List[Dict[str, Any]]:
        """获取所有内容"""
        conditions = []
        params = []
        if resource_package_id:
            conditions.append("c.resource_package_id = ?")
            params.append(resource_package_id)
        if status:
            conditions.append("c.status = ?")
            params.append(status)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT c.*, rp.name as resource_name, t.name as template_name, a.nickname as account_nickname
            FROM contents c
            LEFT JOIN resource_packages rp ON c.resource_package_id = rp.id
            LEFT JOIN templates t ON c.template_id = t.id
            LEFT JOIN accounts a ON c.account_id = a.id
            {where_clause}
            ORDER BY c.created_at DESC
        """
        rows = db.execute(sql, tuple(params))
        return [dict(row) for row in rows]
    
    @staticmethod
    def update(db: Database, content_id: int, title: str = None, content: str = None,
               status: str = None, account_id: int = None, platform: str = None):
        """更新内容"""
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            if status == 'published':
                updates.append("published_at = ?")
                params.append(datetime.now())
        if account_id is not None:
            updates.append("account_id = ?")
            params.append(account_id)
        if platform is not None:
            updates.append("platform = ?")
            params.append(platform)
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(content_id)
            sql = f"UPDATE contents SET {', '.join(updates)} WHERE id = ?"
            db.execute_update(sql, tuple(params))


class Template:
    """话术模板模型"""
    
    @staticmethod
    def create(db: Database, name: str, content: str, description: str = None,
               platform: str = None) -> int:
        """创建话术模板"""
        sql = """
            INSERT INTO templates (name, description, content, platform)
            VALUES (?, ?, ?, ?)
        """
        params = (name, description, content, platform)
        db.execute_update(sql, params)
        return db.execute_one("SELECT last_insert_rowid() as id")['id']
    
    @staticmethod
    def get_all(db: Database, platform: str = None) -> List[Dict[str, Any]]:
        """获取所有模板"""
        if platform:
            sql = "SELECT * FROM templates WHERE platform = ? OR platform IS NULL ORDER BY created_at DESC"
            rows = db.execute(sql, (platform,))
        else:
            sql = "SELECT * FROM templates ORDER BY created_at DESC"
            rows = db.execute(sql)
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(db: Database, template_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取模板"""
        sql = "SELECT * FROM templates WHERE id = ?"
        row = db.execute_one(sql, (template_id,))
        return dict(row) if row else None
    
    @staticmethod
    def update(db: Database, template_id: int, name: str = None, content: str = None,
               description: str = None, platform: str = None):
        """更新模板"""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if platform is not None:
            updates.append("platform = ?")
            params.append(platform)
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now())
            params.append(template_id)
            sql = f"UPDATE templates SET {', '.join(updates)} WHERE id = ?"
            db.execute_update(sql, tuple(params))
    
    @staticmethod
    def delete(db: Database, template_id: int):
        """删除模板"""
        sql = "DELETE FROM templates WHERE id = ?"
        db.execute_update(sql, (template_id,))

