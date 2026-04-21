"""
数据库管理模块
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from config.config import Config
from utils.logger import Logger


class Database:
    """数据库管理类"""
    
    def __init__(self):
        self.logger = Logger.get_logger("Database")
        self.db_path = Path(Config.DATABASE_CONFIG["path"])
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"数据库操作失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库表结构"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 账号表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    username TEXT NOT NULL,
                    nickname TEXT,
                    cookie TEXT,
                    status TEXT DEFAULT 'invalid',
                    last_refresh_time DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, username)
                )
            """)
            
            # 上传记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'uploading',
                    total_chunks INTEGER DEFAULT 1,
                    uploaded_chunks INTEGER DEFAULT 0
                )
            """)
            
            # 资源包表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    upload_record_id INTEGER,
                    base_path TEXT NOT NULL,
                    directory_count INTEGER DEFAULT 0,
                    content_generated INTEGER DEFAULT 0,
                    content_published INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (upload_record_id) REFERENCES upload_records(id)
                )
            """)
            
            # 内容表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_package_id INTEGER NOT NULL,
                    template_id INTEGER,
                    title TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'pending',
                    published_at DATETIME,
                    platform TEXT,
                    account_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (resource_package_id) REFERENCES resource_packages(id),
                    FOREIGN KEY (template_id) REFERENCES templates(id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
            """)
            
            # 话术模板表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    platform TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 系统用户表（登录 / 注册）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_platform ON accounts(platform)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contents_status ON contents(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_contents_resource_package ON contents(resource_package_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_packages_upload_record ON resource_packages(upload_record_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            
            cursor.execute("SELECT COUNT(*) AS c FROM users")
            if cursor.fetchone()[0] == 0:
                from models.models import User
                User.create_user(self, "admin", "admin123", "admin")
                User.create_user(self, "operator", "operator123", "operator")
                self.logger.info("已创建默认用户 admin / operator")
            
            self.logger.info("数据库初始化完成")
    
    def execute(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """执行查询"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def execute_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """执行查询，返回单条记录"""
        results = self.execute(sql, params)
        return results[0] if results else None
    
    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """执行更新，返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.rowcount

