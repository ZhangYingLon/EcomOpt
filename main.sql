-- EcomOpt 数据库结构
-- 数据库: SQLite (data/ecom.db)
-- 对应模块: models/database.py

-- ----------------------------------------
-- 上传记录表
-- ----------------------------------------
CREATE TABLE IF NOT EXISTS upload_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'uploading',
    total_chunks INTEGER DEFAULT 1,
    uploaded_chunks INTEGER DEFAULT 0
);

-- ----------------------------------------
-- 账号表
-- ----------------------------------------
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
);

-- ----------------------------------------
-- 资源包表
-- ----------------------------------------
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
);

-- ----------------------------------------
-- 话术模板表
-- ----------------------------------------
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    platform TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------
-- 内容表
-- ----------------------------------------
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
);

-- ----------------------------------------
-- 索引
-- ----------------------------------------
CREATE INDEX IF NOT EXISTS idx_accounts_platform ON accounts(platform);
CREATE INDEX IF NOT EXISTS idx_contents_status ON contents(status);
CREATE INDEX IF NOT EXISTS idx_contents_resource_package ON contents(resource_package_id);
CREATE INDEX IF NOT EXISTS idx_resource_packages_upload_record ON resource_packages(upload_record_id);
