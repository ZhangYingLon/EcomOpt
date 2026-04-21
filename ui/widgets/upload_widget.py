"""
上传管理组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
                             QMessageBox, QFileDialog, QHeaderView, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from pathlib import Path
from typing import Optional

from models.database import Database
from services.file_service import FileService
from utils.logger import Logger


class UploadThread(QThread):
    """上传线程"""
    upload_progress = pyqtSignal(int, str)
    upload_finished = pyqtSignal(bool, str, int)
    
    def __init__(self, file_service: FileService, file_path: str):
        super().__init__()
        self.file_service = file_service
        self.file_path = file_path
    
    def run(self):
        try:
            self.upload_progress.emit(10, "开始上传...")
            
            # 保存文件
            saved_path = self.file_service.save_upload_file(self.file_path)
            
            self.upload_progress.emit(50, "创建上传记录...")
            
            # 创建上传记录
            file_size = Path(saved_path).stat().st_size
            filename = Path(saved_path).name
            record_id = self.file_service.create_upload_record(
                filename, saved_path, file_size, status='completed'
            )
            
            self.upload_progress.emit(100, "上传完成")
            self.upload_finished.emit(True, "上传成功", record_id)
        except Exception as e:
            self.upload_finished.emit(False, f"上传失败: {str(e)}", 0)


class UploadWidget(QWidget):
    """上传管理组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("UploadWidget")
        self.db = Database()
        self.file_service = FileService(self.db)
        self.upload_thread: Optional[UploadThread] = None
        self.init_ui()
        self.refresh_upload_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 上传区域
        upload_group = QGroupBox("文件上传")
        upload_layout = QVBoxLayout()
        upload_group.setLayout(upload_layout)
        
        btn_layout = QHBoxLayout()
        self.upload_btn = QPushButton("选择文件上传")
        self.upload_btn.clicked.connect(self.select_and_upload_file)
        btn_layout.addWidget(self.upload_btn)
        
        self.process_btn = QPushButton("解压上传文件")
        self.process_btn.clicked.connect(self.process_selected_upload)
        btn_layout.addWidget(self.process_btn)
        
        btn_layout.addStretch()
        upload_layout.addLayout(btn_layout)
        
        self.upload_progress = QProgressBar()
        self.upload_progress.setVisible(False)
        upload_layout.addWidget(self.upload_progress)
        
        layout.addWidget(upload_group)
        
        # 上传记录区域：标题行 + 操作按钮
        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("上传记录:"))
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_upload_list)
        list_header.addWidget(self.refresh_btn)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_selected_upload)
        list_header.addWidget(self.delete_btn)
        list_header.addStretch()
        layout.addLayout(list_header)
        
        self.upload_table = QTableWidget()
        self.upload_table.setColumnCount(6)
        self.upload_table.setHorizontalHeaderLabels([
            "ID", "文件名", "文件大小", "上传时间", "状态", "文件路径"
        ])
        self.upload_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.upload_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.upload_table.horizontalHeader().setMinimumSectionSize(200)
        self.upload_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.upload_table)
    
    def select_and_upload_file(self):
        """选择并上传文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "ZIP文件 (*.zip);;所有文件 (*.*)"
        )
        
        if file_path:
            self.upload_file(file_path)
    
    def upload_file(self, file_path: str):
        """上传文件"""
        self.upload_btn.setEnabled(False)
        self.upload_progress.setVisible(True)
        self.upload_progress.setValue(0)
        
        self.upload_thread = UploadThread(self.file_service, file_path)
        self.upload_thread.upload_progress.connect(self.on_upload_progress)
        self.upload_thread.upload_finished.connect(self.on_upload_finished)
        self.upload_thread.start()
    
    def on_upload_progress(self, value: int, message: str):
        """上传进度回调"""
        self.upload_progress.setValue(value)
        self.upload_progress.setFormat(f"{message} - {value}%")
    
    def on_upload_finished(self, success: bool, message: str, record_id: int):
        """上传完成回调"""
        self.upload_btn.setEnabled(True)
        self.upload_progress.setVisible(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.refresh_upload_list()
        else:
            QMessageBox.warning(self, "失败", message)
    
    def _format_upload_time(self, value):
        """上传时间去掉秒的小数部分"""
        if value is None or value == '':
            return ''
        s = str(value).strip()
        if '.' in s:
            s = s.split('.')[0]
        return s

    def refresh_upload_list(self):
        """刷新上传列表"""
        records = self.file_service.db.execute(
            "SELECT * FROM upload_records ORDER BY upload_time DESC", ()
        )
        
        self.upload_table.setRowCount(len(records))
        align_center = Qt.AlignCenter

        for row, record in enumerate(records):
            record_dict = dict(record)

            def make_item(text, center=True):
                item = QTableWidgetItem(str(text) if text is not None else '')
                if center:
                    item.setTextAlignment(align_center)
                return item

            self.upload_table.setItem(row, 0, make_item(record_dict['id']))
            self.upload_table.setItem(row, 1, make_item(record_dict['filename']))
            
            # 格式化文件大小
            size = record_dict['file_size']
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.2f} MB"
            self.upload_table.setItem(row, 2, make_item(size_str))
            
            upload_time = self._format_upload_time(record_dict.get('upload_time'))
            self.upload_table.setItem(row, 3, make_item(upload_time))
            self.upload_table.setItem(row, 4, make_item(record_dict['status']))

            file_path = record_dict.get('file_path') or ''
            path_item = make_item(file_path)
            path_item.setToolTip(file_path)
            self.upload_table.setItem(row, 5, path_item)
    
    def process_selected_upload(self):
        """处理选中的上传记录"""
        selected_rows = self.upload_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要处理的上传记录")
            return
        
        row = selected_rows[0].row()
        record_id = int(self.upload_table.item(row, 0).text())
        file_path = self.upload_table.item(row, 5).text()
        
        try:
            # 处理资源包
            package_ids = self.file_service.process_resource_package(record_id, file_path)
            
            # 更新上传记录状态
            self.file_service.db.execute_update(
                "UPDATE upload_records SET status = ? WHERE id = ?",
                ("processed", record_id)
            )
            
            QMessageBox.information(
                self, "成功", 
                f"处理完成，共创建 {len(package_ids)} 个资源包"
            )
            self.refresh_upload_list()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理失败: {str(e)}")

    def delete_selected_upload(self):
        """删除选中的上传记录及其文件"""
        selected_rows = self.upload_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要删除的上传记录")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除选中的上传记录吗？\n若存在，磁盘上的文件也将被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        row = selected_rows[0].row()
        record_id = int(self.upload_table.item(row, 0).text())
        try:
            self.file_service.delete_upload_record(record_id, delete_file=True)
            self.refresh_upload_list()
            QMessageBox.information(self, "成功", "删除成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

