"""
账号管理组件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QGroupBox,
                             QMessageBox, QLineEdit, QComboBox, QHeaderView,
                             QDialog, QFormLayout, QDialogButtonBox, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from typing import Optional

from models import Account
from models.database import Database
from services.account_service import AccountService
from config.config import Config
from utils.logger import Logger


class GetCookieDialog(QDialog):
    """获取Cookie对话框"""
    
    def __init__(self, parent=None, platform: str = ""):
        super().__init__(parent)
        self.platform = platform
        self.setWindowTitle(f"获取 {platform} Cookie")
        self.setModal(True)
        self.cookie = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        form = QFormLayout()
        
        info_label = QLabel(f"""
请按照以下步骤操作：
1. 点击"打开浏览器"按钮，程序将打开登录页面
2. 手动完成登录操作
3. 登录成功后，点击"获取Cookie"按钮
4. Cookie将自动填入下方文本框
        """)
        form.addRow(info_label)
        
        self.open_browser_btn = QPushButton("打开浏览器")
        form.addRow(self.open_browser_btn)
        
        self.get_cookie_btn = QPushButton("获取Cookie")
        self.get_cookie_btn.setEnabled(False)
        form.addRow(self.get_cookie_btn)
        
        form.addRow(QLabel("Cookie:"))
        self.cookie_input = QTextEdit()
        self.cookie_input.setMaximumHeight(150)
        form.addRow(self.cookie_input)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("确定")
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.open_browser_btn.clicked.connect(self.on_open_browser)
        self.get_cookie_btn.clicked.connect(self.on_get_cookie)
    
    def on_open_browser(self):
        """打开浏览器"""
        self.open_browser_btn.setEnabled(False)
        self.get_cookie_btn.setEnabled(True)
        # 触发父窗口打开浏览器
        if self.parent():
            self.parent().open_browser_for_cookie(self.platform)
    
    def on_get_cookie(self):
        """获取Cookie"""
        if self.parent():
            cookie = self.parent().get_cookie_from_browser()
            if cookie:
                self.cookie_input.setPlainText(cookie)
                self.cookie = cookie
    
    def get_cookie(self):
        """获取输入的Cookie"""
        return self.cookie_input.toPlainText().strip()


class LoginAndSaveDialog(QDialog):
    """登录后获取Cookie并保存到当前账号的对话框"""
    
    def __init__(self, parent, account_id: int, platform_name: str):
        super().__init__(parent)
        self.account_id = account_id
        self.platform_name = platform_name
        self.setWindowTitle(f"登录 - {platform_name}")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel("请在浏览器中完成登录，登录成功后点击下方按钮保存 Cookie 到本账号。"))
        self.save_btn = QPushButton("获取Cookie并保存")
        self.save_btn.clicked.connect(self.on_save)
        layout.addWidget(self.save_btn)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_save(self):
        if not self.parent():
            return
        cookie = self.parent().account_service.get_current_cookies()
        if not cookie or not cookie.strip():
            QMessageBox.warning(self, "提示", "未获取到 Cookie，请确保已在浏览器中登录成功后再点击。")
            return
        try:
            self.parent().account_service.update_account_cookie(self.account_id, cookie)
            self.parent().refresh_account_list()
            QMessageBox.information(self, "成功", "Cookie 已保存，账号将参与定时刷新。")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


class AccountWidget(QWidget):
    """账号管理组件"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger.get_logger("AccountWidget")
        self.db = Database()
        self.account_service = AccountService(self.db)
        self.account_service.account_status_changed.connect(self.on_account_status_changed)
        self.current_platform_for_cookie = None
        self.init_ui()
        self.refresh_account_list()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 操作按钮区域
        btn_layout = QHBoxLayout()
        
        self.add_account_btn = QPushButton("添加账号")
        self.add_account_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(self.add_account_btn)
        
        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self.refresh_all_status)
        btn_layout.addWidget(self.refresh_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_account)
        btn_layout.addWidget(self.delete_btn)
        
        btn_layout.addStretch()
        
        platform_label = QLabel("平台筛选:")
        btn_layout.addWidget(platform_label)
        
        self.platform_filter = QComboBox()
        self.platform_filter.addItems(["全部", "百家号", "小红书"])
        self.platform_filter.currentTextChanged.connect(self.refresh_account_list)
        btn_layout.addWidget(self.platform_filter)
        
        layout.addLayout(btn_layout)
        
        # 账号列表表格
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(7)
        self.account_table.setHorizontalHeaderLabels([
            "ID", "平台", "账号", "昵称", "状态", "最后刷新", "操作"
        ])
        self.account_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.verticalHeader().setDefaultSectionSize(44)
        self.account_table.doubleClicked.connect(self.edit_account)
        layout.addWidget(self.account_table)
        
        # 底部操作按钮
        bottom_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.edit_account)
        bottom_layout.addWidget(self.edit_btn)
        
        self.get_cookie_btn = QPushButton("获取Cookie")
        self.get_cookie_btn.clicked.connect(self.get_cookie_for_account)
        bottom_layout.addWidget(self.get_cookie_btn)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
    
    def _format_refresh_time(self, value):
        """格式化为 年-月-日 时:分:秒，去掉秒的小数部分"""
        if value is None or value == '' or value == '未刷新':
            return '未刷新'
        s = str(value).strip()
        if not s or s == '未刷新':
            return '未刷新'
        if '.' in s:
            s = s.split('.')[0]
        return s
    
    def refresh_account_list(self):
        """刷新账号列表"""
        platform_filter = self.platform_filter.currentText()
        if platform_filter == "全部":
            accounts = self.account_service.get_all_accounts()
        else:
            platform_map = {"百家号": "baijiahao", "小红书": "xiaohongshu"}
            platform = platform_map.get(platform_filter, "")
            accounts = self.account_service.get_all_accounts(platform)
        
        self.account_table.setRowCount(len(accounts))
        align_center = Qt.AlignCenter

        for row, account in enumerate(accounts):
            def make_item(text, align=True):
                item = QTableWidgetItem(str(text) if text is not None else '')
                if align:
                    item.setTextAlignment(align_center)
                return item

            self.account_table.setItem(row, 0, make_item(account['id']))
            self.account_table.setItem(row, 1, make_item(account['platform']))
            self.account_table.setItem(row, 2, make_item(account['username']))
            self.account_table.setItem(row, 3, make_item(account.get('nickname', '') or ''))
            
            status_raw = account.get('status') or 'invalid'
            if status_raw not in ('valid', 'invalid'):
                status_raw = 'invalid'
            status_display = '有效' if status_raw == 'valid' else '无效'
            status_item = make_item(status_display)
            if status_raw == 'valid':
                status_item.setForeground(Qt.darkGreen)
            else:
                status_item.setForeground(Qt.red)
            self.account_table.setItem(row, 4, status_item)
            
            refresh_time = account.get('last_refresh_time', '') or '未刷新'
            refresh_display = self._format_refresh_time(refresh_time)
            self.account_table.setItem(row, 5, make_item(refresh_display))
            
            # 操作列：登录按钮
            login_btn = QPushButton("登录")
            login_btn.setMinimumHeight(28)
            account_id = account['id']
            platform_key = account.get('platform') or ''
            platform_name = Config.PLATFORMS.get(platform_key, {}).get("name", platform_key)
            login_btn.clicked.connect(lambda checked=False, aid=account_id, plat=platform_key: self.login_account(aid, plat))
            login_btn.setEnabled(bool(platform_key))
            cell_widget = QWidget()
            cell_layout = QHBoxLayout()
            cell_layout.setContentsMargins(4, 2, 4, 2)
            cell_layout.addWidget(login_btn)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_widget.setLayout(cell_layout)
            self.account_table.setCellWidget(row, 6, cell_widget)
            self.account_table.setRowHeight(row, 44)
    
    def add_account(self):
        """添加账号"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加账号")
        layout = QFormLayout()
        dialog.setLayout(layout)
        
        platform_combo = QComboBox()
        platform_combo.addItems(["百家号", "小红书"])
        layout.addRow("平台:", platform_combo)
        
        username_input = QLineEdit()
        layout.addRow("账号:", username_input)
        
        nickname_input = QLineEdit()
        layout.addRow("昵称:", nickname_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("确定")
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            platform_map = {"百家号": "baijiahao", "小红书": "xiaohongshu"}
            platform = platform_map.get(platform_combo.currentText(), "")
            username = username_input.text().strip()
            nickname = nickname_input.text().strip()
            
            if not username:
                QMessageBox.warning(self, "警告", "请输入账号")
                return
            
            try:
                self.account_service.add_account(platform, username, nickname)
                self.refresh_account_list()
                QMessageBox.information(self, "成功", "账号添加成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")
    
    def edit_account(self):
        """编辑账号"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要编辑的账号")
            return
        
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        account_dict = Account.get_by_id(self.account_service.db, account_id)
        if not account_dict:
            return
        # 转换为可访问的格式
        class AccountObj:
            def __init__(self, d):
                self.__dict__ = d
        account = AccountObj(account_dict)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑账号")
        layout = QFormLayout()
        dialog.setLayout(layout)
        
        nickname_input = QLineEdit(account['nickname'] or '')
        layout.addRow("昵称:", nickname_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        if ok_btn:
            ok_btn.setText("确定")
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setText("取消")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # 更新昵称
            from models.models import Account as AccountModel
            sql = "UPDATE accounts SET nickname = ? WHERE id = ?"
            self.account_service.db.execute_update(sql, (nickname_input.text().strip(), account_id))
            self.refresh_account_list()
    
    def get_cookie_for_account(self):
        """获取账号Cookie"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要获取Cookie的账号")
            return
        
        row = selected_rows[0].row()
        account_id = int(self.account_table.item(row, 0).text())
        platform = self.account_table.item(row, 1).text()
        
        platform_map = {"百家号": "baijiahao", "小红书": "xiaohongshu"}
        platform_key = platform_map.get(platform, platform)
        
        dialog = GetCookieDialog(self, platform)
        dialog.setParent(self)
        self.current_platform_for_cookie = platform_key
        
        if dialog.exec_() == QDialog.Accepted:
            cookie = dialog.get_cookie()
            if cookie:
                try:
                    self.account_service.update_account_cookie(account_id, cookie)
                    self.refresh_account_list()
                    QMessageBox.information(self, "成功", "Cookie更新成功")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")
    
    def open_browser_for_cookie(self, platform: str):
        """打开浏览器获取Cookie"""
        if self.current_platform_for_cookie:
            cookie = self.account_service.get_cookie_from_browser(self.current_platform_for_cookie)
            return cookie
        return None
    
    def get_cookie_from_browser(self):
        """从浏览器获取Cookie"""
        if self.current_platform_for_cookie:
            return self.account_service.get_cookie_from_browser(self.current_platform_for_cookie)
        return None
    
    def login_account(self, account_id: int, platform_key: str):
        """打开登录页，手动登录后获取 Cookie 并保存到该账号（并参与定时刷新）"""
        if not platform_key:
            QMessageBox.warning(self, "提示", "未知平台")
            return
        try:
            self.account_service.open_browser_to_login(platform_key)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开登录页失败: {str(e)}")
            return
        platform_name = Config.PLATFORMS.get(platform_key, {}).get("name", platform_key)
        dialog = LoginAndSaveDialog(self, account_id, platform_name)
        dialog.exec_()
    
    def delete_account(self):
        """删除账号"""
        selected_rows = self.account_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要删除的账号")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除选中的账号吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            row = selected_rows[0].row()
            account_id = int(self.account_table.item(row, 0).text())
            try:
                self.account_service.delete_account(account_id)
                self.refresh_account_list()
                QMessageBox.information(self, "成功", "账号删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def refresh_all_status(self):
        """刷新所有账号状态"""
        self.account_service.refresh_all_accounts()
        self.refresh_account_list()
        QMessageBox.information(self, "成功", "账号状态刷新完成")
    
    def on_account_status_changed(self, account_id: int, status: str):
        """账号状态变化回调"""
        self.refresh_account_list()
    
    def cleanup(self):
        """清理资源"""
        if hasattr(self.account_service, 'selenium_manager'):
            try:
                self.account_service.selenium_manager.close()
            except:
                pass

