"""
文件处理服务
"""
import os
import zipfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from models.database import Database
from models.models import UploadRecord, ResourcePackage
from config.config import Config
from utils.logger import Logger


class FileService:
    """文件处理服务"""
    
    def __init__(self, db: Database):
        self.db = db
        self.logger = Logger.get_logger("FileService")
        self.uploads_dir = Config.UPLOADS_DIR
        self.extracted_dir = Config.EXTRACTED_DIR
    
    def save_upload_file(self, file_path: str, filename: str = None) -> str:
        """
        保存上传的文件
        Returns: 保存的文件路径
        """
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if filename is None:
            filename = source_path.name
        
        # 生成唯一文件名（添加时间戳）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = Path(filename).stem, Path(filename).suffix
        unique_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        
        dest_path = self.uploads_dir / unique_filename
        shutil.copy2(source_path, dest_path)
        
        self.logger.info(f"文件保存成功: {dest_path}")
        return str(dest_path)
    
    def create_upload_record(self, filename: str, file_path: str, 
                            file_size: int, total_chunks: int = 1, status: str = 'completed') -> int:
        """创建上传记录"""
        return UploadRecord.create(self.db, filename, file_path, file_size, total_chunks, status)

    def update_upload_record_status(self, record_id: int, status: str) -> None:
        """更新上传记录状态（如上传完成后设为 completed）"""
        UploadRecord.update_status(self.db, record_id, status)

    def delete_upload_record(self, record_id: int, delete_file: bool = True) -> None:
        """
        删除上传记录，可选同时删除磁盘上的文件。
        若有关联资源包会一并删除。
        """
        row = self.db.execute_one("SELECT * FROM upload_records WHERE id = ?", (record_id,))
        if not row:
            raise ValueError(f"上传记录不存在: {record_id}")
        rec = dict(row)
        file_path = Path(rec.get("file_path") or "")
        self.db.execute_update("DELETE FROM resource_packages WHERE upload_record_id = ?", (record_id,))
        self.db.execute_update("DELETE FROM upload_records WHERE id = ?", (record_id,))
        if delete_file and file_path.exists():
            try:
                file_path.unlink()
                self.logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                self.logger.warning(f"删除文件失败 {file_path}: {e}")
    
    def extract_zip(self, zip_path: str, extract_to: Path = None) -> Path:
        """
        解压ZIP文件，自动处理超长路径
        Returns: 解压后的目录路径
        """
        zip_file = Path(zip_path)
        if not zip_file.exists():
            raise FileNotFoundError(f"ZIP文件不存在: {zip_path}")
        
        if extract_to is None:
            extract_to = self.extracted_dir / zip_file.stem
        
        extract_to.mkdir(parents=True, exist_ok=True)
        
        # 使用 \\?\ 前缀绕过 Windows 260 字符限制
        long_extract_to = Path("\\\\?\\" + str(extract_to.absolute()))
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(long_extract_to)
        
        # 解压完成后，重命名超长路径
        self._rename_long_paths(extract_to)
        
        self.logger.info(f"ZIP文件解压成功: {extract_to}")
        return extract_to
    
    def _rename_long_paths(self, base_path: Path) -> None:
        """重命名超长路径文件夹（从内到外），保留原标题前缀"""
        try:
            # 从最深的目录开始处理
            for root, dirs, files in os.walk(str(base_path), topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    path_len = len(str(dir_path))
                    
                    if path_len > 200:
                        # 计算安全长度：预留余量后，截取原标题
                        max_name_len = 200 - len(str(dir_path.parent)) - 1  # -1 为分隔符
                        if max_name_len < 10:
                            max_name_len = 30  # 最少保留30字符
                        
                        # 截取原标题（保持可读性）
                        safe_name = dir_name[:max_name_len].rstrip()
                        
                        new_path = dir_path.parent / safe_name
                        try:
                            dir_path.rename(new_path)
                            self.logger.info("截断超长目录: %s -> %s", dir_name[:40], safe_name)
                        except Exception as e:
                            self.logger.warning("重命名失败: %s", e)
        except Exception as e:
            self.logger.debug("重命名超长路径失败: %s", e)
    
    def _fix_long_paths(self, base_path: Path) -> None:
        """递归重命名超长路径，避免 WinError 3"""
        try:
            # 使用 \\?\ 前缀绕过 Windows 路径限制
            import ctypes
            ctypes.windll.kernel32.SetConsoleCP(65001)
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            
            long_path = "\\\\?\\" + str(base_path.absolute())
            for item in Path(long_path).iterdir():
                if item.is_dir():
                    # 递归处理子目录
                    real_sub = str(item).replace("\\\\?\\", "")
                    self._fix_long_paths(Path(real_sub))
                    
                    # 检查路径长度
                    if len(real_sub) > 200:
                        new_name = f"dir_{hash(Path(real_sub).name) % 10000:04d}_{Path(real_sub).name[:20]}"
                        new_path = Path(real_sub).parent / new_name
                        try:
                            Path(real_sub).rename(new_path)
                            self.logger.info("重命名超长路径: %s -> %s", Path(real_sub).name[:30], new_name)
                        except Exception as e:
                            self.logger.warning("重命名失败: %s", e)
        except Exception as e:
            self.logger.debug("扫描目录时跳过: %s", e)
    
    def find_leaf_directories(self, base_path: Path) -> List[Path]:
        """
        查找所有叶子目录（没有子目录的目录）
        """
        leaf_dirs = []
        
        # 使用 \\?\ 前缀支持长路径
        scan_path = "\\\\?\\" + str(base_path.absolute())
        
        def _scan_dir(path_str: str):
            try:
                has_subdirs = False
                for item in Path(path_str).iterdir():
                    if item.is_dir():
                        has_subdirs = True
                        _scan_dir(str(item))
                
                if not has_subdirs:
                    real_path = path_str.replace("\\\\?\\", "")
                    leaf_dirs.append(Path(real_path))
            except Exception as e:
                self.logger.debug("扫描目录失败: %s", e)
        
        _scan_dir(scan_path)
        return leaf_dirs
    
    def count_directory_items(self, directory: Path) -> int:
        """统计目录下的文件数量"""
        count = 0
        for item in directory.rglob('*'):
            if item.is_file():
                count += 1
        return count
    
    def process_resource_package(self, upload_record_id: int, zip_path: str) -> List[int]:
        """
        处理资源包：解压、识别叶子目录、创建资源包记录
        Returns: 创建的资源包ID列表
        """
        # 解压ZIP文件
        extracted_path = self.extract_zip(zip_path)
        
        # 查找所有叶子目录
        leaf_dirs = self.find_leaf_directories(extracted_path)
        
        if not leaf_dirs:
            self.logger.warning("未找到叶子目录，可能ZIP文件结构不正确")
            return []
        
        resource_package_ids = []
        
        for idx, leaf_dir in enumerate(leaf_dirs, 1):
            # 使用目录名作为资源包名称
            original_name = leaf_dir.name
            
            # Windows 路径限制 260 字符，自动缩短超长文件夹名
            safe_name = original_name
            if len(str(leaf_dir)) > 200:  # 预留 60 字符余量
                safe_name = f"作品{idx}_{original_name[:30]}" if len(original_name) > 30 else f"作品{idx}"
                try:
                    new_path = leaf_dir.parent / safe_name
                    leaf_dir.rename(new_path)
                    leaf_dir = new_path
                    self.logger.info("文件夹名过长，已自动重命名: %s -> %s", original_name[:50], safe_name)
                except Exception as e:
                    self.logger.warning("重命名文件夹失败: %s", e)
            
            # 统计目录数量（从根目录到叶子目录的层级）
            dir_count = len(leaf_dir.relative_to(extracted_path).parts)
            
            # 创建资源包记录，保存原始名称
            package_id = ResourcePackage.create(
                self.db,
                name=original_name,  # 保存原始完整名称
                base_path=str(leaf_dir),  # 使用安全路径
                upload_record_id=upload_record_id,
                directory_count=dir_count
            )
            
            resource_package_ids.append(package_id)
            self.logger.info(f"创建资源包: {original_name[:50]}... (ID: {package_id})")
        
        return resource_package_ids
    
    def get_resource_files(self, resource_package_id: int) -> List[Path]:
        """获取资源包下的所有文件"""
        package = ResourcePackage.get_by_id(self.db, resource_package_id)
        if not package:
            return []
        
        base_path = Path(package['base_path'])
        if not base_path.exists():
            return []
        
        files = []
        for item in base_path.rglob('*'):
            if item.is_file():
                files.append(item)
        
        return files

    # 发布用图片扩展名（与小红书选图逻辑一致）
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def get_package_image_paths(self, resource_package_id: int, max_count: int = 18) -> List[str]:
        """获取资源包下的图片文件路径（绝对路径），按文件名排序，最多 max_count 张，供发布使用。"""
        files = self.get_resource_files(resource_package_id)
        image_paths = []
        for p in sorted(files, key=lambda x: x.name):
            if p.suffix.lower() in self.IMAGE_EXTENSIONS:
                image_paths.append(str(p.resolve()))
                if len(image_paths) >= max_count:
                    break
        return image_paths
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

