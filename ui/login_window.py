"""
登录 / 角色选择窗口
根据 修改.txt 划分：运营人员、管理员 两种角色，选择后登录进入对应功能界面。
"""
import random
import re
from typing import Tuple

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QWidget, QLineEdit, QTabWidget, QMessageBox,
                             QFormLayout, QSizePolicy, QAction)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter, QPen, QFont

from models.database import Database
from models.models import User

# 角色常量
ROLE_OPERATOR = "operator"   # 运营人员
ROLE_ADMIN = "admin"        # 管理员

# 输入校验（与界面提示一致）
USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 32
PASSWORD_MIN_LEN = 6
PASSWORD_MAX_LEN = 128
# 用户名：字母、数字、下划线、中文（不含空格）
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fff]+$")

# 图形验证码字符集（排除易混淆的 0/O、1/l/I）
_CAPTCHA_CHARSET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"


class LoginDialog(QDialog):
    """登录 / 注册对话框：按所选入口校验角色一致。"""

    _LINE_STYLE = (
        "QLineEdit {"
        "  border: 1px solid #cbd5e1; border-radius: 6px;"
        "  padding: 8px 12px; min-height: 20px; font-size: 13px;"
        "}"
        "QLineEdit:focus { border-color: #1a73e8; }"
    )

    def __init__(self, db: Database, expected_role: str, parent=None):
        super().__init__(parent)
        self.db = db
        self.expected_role = expected_role if expected_role in (ROLE_OPERATOR, ROLE_ADMIN) else ROLE_OPERATOR
        self._authenticated_role = None
        self._authenticated_username = None
        self.setWindowTitle("登录" if self.expected_role == ROLE_OPERATOR else "管理员登录")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self._set_icon()
        self._setup_ui()
        self.setMinimumSize(460, 560)
        self.resize(480, 600)
        self._center()

    def _set_icon(self):
        try:
            from pathlib import Path
            from config.config import Config
            icon_path = Config.BASE_DIR / "imgs" / "app.ico"
            if not icon_path.exists():
                icon_path = Config.BASE_DIR / "imgs" / "app.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass

    def _center(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    @staticmethod
    def _validate_username_raw(username: str) -> Tuple[bool, str]:
        s = username.strip()
        if not s:
            return False, "请输入用户名"
        if len(s) < USERNAME_MIN_LEN:
            return False, f"用户名至少 {USERNAME_MIN_LEN} 个字符"
        if len(s) > USERNAME_MAX_LEN:
            return False, f"用户名不超过 {USERNAME_MAX_LEN} 个字符"
        if not _USERNAME_RE.match(s):
            return False, "用户名仅支持字母、数字、下划线与中文"
        return True, s

    @staticmethod
    def _validate_password_raw(password: str, confirm: str = None) -> Tuple[bool, str]:
        if not password:
            return False, "请输入密码"
        if len(password) < PASSWORD_MIN_LEN:
            return False, f"密码至少 {PASSWORD_MIN_LEN} 位"
        if len(password) > PASSWORD_MAX_LEN:
            return False, f"密码不超过 {PASSWORD_MAX_LEN} 位"
        if confirm is not None and password != confirm:
            return False, "两次输入的密码不一致"
        return True, ""

    def _style_line_edit(self, edit: QLineEdit):
        edit.setStyleSheet(self._LINE_STYLE)
        edit.setMinimumHeight(40)
        edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    @staticmethod
    def _password_eye_icon(visible_plaintext: bool) -> QIcon:
        pix = QPixmap(22, 22)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor("#5f6368"))
        pen.setWidthF(1.25)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(2, 7, 18, 10)
        p.drawPoint(11, 12)
        if visible_plaintext:
            p.drawLine(4, 4, 18, 18)
        p.end()
        return QIcon(pix)

    def _attach_password_visibility_action(self, edit: QLineEdit):
        """行尾图标显示/隐藏密码，输入框与用户名等宽。"""
        act = QAction(self._password_eye_icon(False), "", edit)
        act.setCheckable(True)
        act.setToolTip("显示密码")

        def on_toggled(checked):
            edit.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
            act.setIcon(self._password_eye_icon(checked))
            act.setToolTip("隐藏密码" if checked else "显示密码")

        act.toggled.connect(on_toggled)
        trailing = getattr(QLineEdit, "TrailingPosition", 1)
        edit.addAction(act, trailing)

    @staticmethod
    def _generate_captcha() -> Tuple[QPixmap, str]:
        length = 4
        code = "".join(random.choice(_CAPTCHA_CHARSET) for _ in range(length))
        w, h = 118, 42
        pm = QPixmap(w, h)
        pm.fill(QColor(255, 255, 255))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing, True)
        for _ in range(5):
            painter.setPen(
                QPen(
                    QColor(
                        random.randint(200, 230),
                        random.randint(200, 230),
                        random.randint(210, 235),
                    ),
                    1,
                )
            )
            painter.drawLine(
                random.randint(0, w),
                random.randint(0, h),
                random.randint(0, w),
                random.randint(0, h),
            )
        font = QFont("Consolas", 20, QFont.Bold)
        if not font.exactMatch():
            font = QFont("Courier New", 18, QFont.Bold)
        painter.setFont(font)
        for i, ch in enumerate(code):
            painter.setPen(
                QColor(
                    random.randint(45, 110),
                    random.randint(45, 110),
                    random.randint(80, 160),
                )
            )
            x = 14 + i * 24 + random.randint(-2, 2)
            y = 30 + random.randint(-3, 3)
            painter.drawText(x, y, ch)
        for _ in range(40):
            painter.setPen(QColor(200, 200, 210, 120))
            painter.drawPoint(random.randint(0, w - 1), random.randint(0, h - 1))
        painter.end()
        return pm, code

    def _refresh_captcha(self):
        pix, text = self._generate_captcha()
        self._captcha_answer = text
        self.captcha_label.setPixmap(pix)
        self.captcha_input.clear()

    def _make_error_label(self) -> QLabel:
        lab = QLabel("")
        lab.setWordWrap(True)
        lab.setStyleSheet("color: #dc2626; font-size: 12px; min-height: 18px;")
        lab.hide()
        return lab

    def _show_error(self, label: QLabel, message: str):
        label.setText(message)
        label.show()

    def _clear_error(self, label: QLabel):
        label.clear()
        label.hide()

    def _setup_ui(self):
        self._captcha_answer = ""

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(22, 18, 22, 16)

        role_label = "运营人员" if self.expected_role == ROLE_OPERATOR else "管理员"
        title = QLabel(f"{role_label} · 登录或注册")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #0f172a; padding: 0 0 4px 0;"
        )
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(320)
        self.tabs.setStyleSheet(
            "QTabWidget::pane {"
            "  border: 1px solid #e5e7eb; border-radius: 10px;"
            "  padding: 20px 20px 20px 20px; background: #ffffff;"
            "}"
            "QTabBar::tab {"
            "  background: transparent; padding: 10px 22px; margin-right: 4px;"
            "  font-size: 13px; color: #64748b;"
            "}"
            "QTabBar::tab:selected {"
            "  color: #1d4ed8; font-weight: 600;"
            "  border-bottom: 2px solid #2563eb; margin-bottom: -1px;"
            "}"
            "QTabBar::tab:hover { color: #334155; }"
        )

        # —— 登录 ——
        login_page = QWidget()
        login_page.setMinimumHeight(220)
        login_outer = QVBoxLayout(login_page)
        login_outer.setContentsMargins(0, 0, 0, 0)
        login_outer.setSpacing(16)

        form_login = QFormLayout()
        form_login.setSpacing(16)
        form_login.setHorizontalSpacing(14)
        form_login.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_login.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_login.setVerticalSpacing(4)

        self.login_user = QLineEdit()
        self.login_user.setPlaceholderText(f"{USERNAME_MIN_LEN}–{USERNAME_MAX_LEN} 位，字母数字下划线或中文")
        self._style_line_edit(self.login_user)

        self.login_pass = QLineEdit()
        self.login_pass.setPlaceholderText(f"至少 {PASSWORD_MIN_LEN} 位")
        self.login_pass.setEchoMode(QLineEdit.Password)
        self._style_line_edit(self.login_pass)
        self._attach_password_visibility_action(self.login_pass)

        form_login.addRow("用户名", self.login_user)
        form_login.addRow("密码", self.login_pass)

        login_outer.addLayout(form_login)

        self.login_error = self._make_error_label()
        login_outer.addWidget(self.login_error)

        login_outer.addStretch(1)

        login_btn = QPushButton("登 录")
        login_btn.setDefault(True)
        login_btn.setMinimumHeight(44)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:pressed { background-color: #1e40af; }"
        )
        login_btn.clicked.connect(self._do_login)
        login_outer.addWidget(login_btn)

        self.tabs.addTab(login_page, "登录")

        # —— 注册 ——
        reg_page = QWidget()
        reg_page.setMinimumHeight(380)
        reg_outer = QVBoxLayout(reg_page)
        reg_outer.setContentsMargins(0, 0, 0, 0)
        reg_outer.setSpacing(14)

        reg_info = QLabel(
            f"在本入口注册的账号角色为「{role_label}」，与另一入口账号互不通用。"
        )
        reg_info.setWordWrap(True)
        reg_info.setStyleSheet(
            "font-size: 12px; color: #475569; background: #f8fafc;"
            "border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px;"
        )
        reg_outer.addWidget(reg_info)

        form_reg = QFormLayout()
        form_reg.setSpacing(16)
        form_reg.setHorizontalSpacing(14)
        form_reg.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_reg.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_reg.setVerticalSpacing(4)

        self.reg_user = QLineEdit()
        self.reg_user.setPlaceholderText("设置登录用户名")
        self._style_line_edit(self.reg_user)

        self.reg_pass = QLineEdit()
        self.reg_pass.setPlaceholderText(f"至少 {PASSWORD_MIN_LEN} 位")
        self.reg_pass.setEchoMode(QLineEdit.Password)
        self._style_line_edit(self.reg_pass)
        self._attach_password_visibility_action(self.reg_pass)

        self.reg_pass2 = QLineEdit()
        self.reg_pass2.setPlaceholderText("再次输入密码")
        self.reg_pass2.setEchoMode(QLineEdit.Password)
        self._style_line_edit(self.reg_pass2)
        self._attach_password_visibility_action(self.reg_pass2)

        form_reg.addRow("用户名", self.reg_user)
        form_reg.addRow("密码", self.reg_pass)
        form_reg.addRow("确认密码", self.reg_pass2)

        captcha_row = QWidget()
        captcha_h = QHBoxLayout(captcha_row)
        captcha_h.setContentsMargins(0, 0, 0, 0)
        captcha_h.setSpacing(10)

        self.captcha_label = QLabel()
        self.captcha_label.setFixedSize(118, 42)
        self.captcha_label.setAlignment(Qt.AlignCenter)
        self.captcha_label.setStyleSheet(
            "QLabel { background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; }"
        )

        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText("右侧图形中的字符，不区分大小写")
        self.captcha_input.setMaxLength(8)
        self._style_line_edit(self.captcha_input)

        captcha_refresh = QPushButton("换一张")
        captcha_refresh.setFixedHeight(40)
        captcha_refresh.setMinimumWidth(72)
        captcha_refresh.setCursor(Qt.PointingHandCursor)
        captcha_refresh.setStyleSheet(
            "QPushButton { border: 1px solid #cbd5e1; border-radius: 6px; "
            "background: #f8fafc; font-size: 12px; color: #334155; }"
            "QPushButton:hover { background: #f1f5f9; border-color: #94a3b8; }"
        )
        captcha_refresh.clicked.connect(self._refresh_captcha)

        captcha_h.addWidget(self.captcha_label, 0, Qt.AlignVCenter)
        captcha_h.addWidget(self.captcha_input, 1)
        captcha_h.addWidget(captcha_refresh, 0, Qt.AlignVCenter)

        form_reg.addRow("验证码", captcha_row)

        reg_outer.addLayout(form_reg)

        self.reg_error = self._make_error_label()
        reg_outer.addWidget(self.reg_error)

        reg_outer.addStretch(1)

        reg_btn = QPushButton("注 册")
        reg_btn.setMinimumHeight(44)
        reg_btn.setCursor(Qt.PointingHandCursor)
        reg_btn.setStyleSheet(
            "QPushButton { background-color: #0d9488; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0f766e; }"
            "QPushButton:pressed { background-color: #115e59; }"
        )
        reg_btn.clicked.connect(self._do_register)
        reg_outer.addWidget(reg_btn)

        self.tabs.addTab(reg_page, "注册")

        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("取消")
        cancel.setMinimumHeight(36)
        cancel.setMinimumWidth(88)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(
            "QPushButton { border: 1px solid #cbd5e1; border-radius: 8px; padding: 6px 16px; "
            "font-size: 13px; background: #ffffff; color: #475569; }"
            "QPushButton:hover { background: #f8fafc; border-color: #94a3b8; }"
        )
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        layout.addLayout(footer)

        self.setStyleSheet("QDialog { background-color: #eef2f6; }")

        self.login_user.textChanged.connect(lambda _: self._clear_error(self.login_error))
        self.login_pass.textChanged.connect(lambda _: self._clear_error(self.login_error))
        self.reg_user.textChanged.connect(lambda _: self._clear_error(self.reg_error))
        self.reg_pass.textChanged.connect(lambda _: self._clear_error(self.reg_error))
        self.reg_pass2.textChanged.connect(lambda _: self._clear_error(self.reg_error))
        self.captcha_input.textChanged.connect(lambda _: self._clear_error(self.reg_error))

        self.login_user.returnPressed.connect(self.login_pass.setFocus)
        self.login_pass.returnPressed.connect(self._do_login)
        self.reg_user.returnPressed.connect(self.reg_pass.setFocus)
        self.reg_pass.returnPressed.connect(self.reg_pass2.setFocus)
        self.reg_pass2.returnPressed.connect(self.captcha_input.setFocus)
        self.captcha_input.returnPressed.connect(self._do_register)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.login_user.setFocus()

    def _on_tab_changed(self, index: int):
        if index == 0:
            self._clear_error(self.login_error)
        else:
            self._clear_error(self.reg_error)
            self._refresh_captcha()

    def _do_login(self):
        self._clear_error(self.login_error)
        ok, uname_or_err = self._validate_username_raw(self.login_user.text())
        if not ok:
            self._show_error(self.login_error, uname_or_err)
            self.login_user.setFocus()
            return
        ok, pwd_err = self._validate_password_raw(self.login_pass.text())
        if not ok:
            self._show_error(self.login_error, pwd_err)
            self.login_pass.setFocus()
            return

        user = User.authenticate(self.db, uname_or_err, self.login_pass.text())
        if not user:
            self._show_error(self.login_error, "用户名或密码错误，请重试。")
            self.login_pass.selectAll()
            self.login_pass.setFocus()
            return
        if user["role"] != self.expected_role:
            QMessageBox.warning(
                self,
                "角色不符",
                "该账号不能使用当前入口登录，请返回选择正确的身份。",
            )
            return
        self._authenticated_role = user["role"]
        self._authenticated_username = user["username"]
        self.accept()

    def _do_register(self):
        self._clear_error(self.reg_error)
        ok, uname_or_err = self._validate_username_raw(self.reg_user.text())
        if not ok:
            self._show_error(self.reg_error, uname_or_err)
            self.reg_user.setFocus()
            return
        p1 = self.reg_pass.text()
        p2 = self.reg_pass2.text()
        ok, pwd_err = self._validate_password_raw(p1)
        if not ok:
            self._show_error(self.reg_error, pwd_err)
            self.reg_pass.setFocus()
            return
        ok, match_err = self._validate_password_raw(p1, p2)
        if not ok:
            self._show_error(self.reg_error, match_err)
            self.reg_pass2.setFocus()
            return

        cap = self.captcha_input.text().strip()
        if not cap:
            self._show_error(self.reg_error, "请输入图形验证码。")
            self.captcha_input.setFocus()
            return
        if cap.lower() != (self._captcha_answer or "").lower():
            self._show_error(self.reg_error, "验证码错误，请重新输入或点击「换一张」。")
            self._refresh_captcha()
            self.captcha_input.setFocus()
            return

        ok, err = User.create_user(self.db, uname_or_err, p1, self.expected_role)
        if not ok:
            self._show_error(self.reg_error, err)
            self._refresh_captcha()
            return
        QMessageBox.information(self, "注册成功", "请切换到「登录」页签，使用新账号登录。")
        self.tabs.setCurrentIndex(0)
        self.login_user.setText(uname_or_err)
        self.login_pass.clear()
        self.reg_user.clear()
        self.reg_pass.clear()
        self.reg_pass2.clear()
        self._clear_error(self.reg_error)
        self._refresh_captcha()
        self.login_user.setFocus()

    def get_role(self):
        return self._authenticated_role

    def get_username(self):
        return self._authenticated_username


class LoginWindow(QDialog):
    """登录界面：选择角色（运营人员 / 管理员）后弹出登录对话框。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_role = None
        self._last_username = None
        self.db = Database()
        self.setWindowTitle("EcomOpt - 请选择身份")
        self.setFixedSize(560, 420)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self._set_icon()
        self._setup_ui()
        self._center()

    def _set_icon(self):
        try:
            from pathlib import Path
            from config.config import Config
            icon_path = Config.BASE_DIR / "imgs" / "app.ico"
            if not icon_path.exists():
                icon_path = Config.BASE_DIR / "imgs" / "app.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass

    def _center(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 36, 40, 36)

        title = QLabel("电商运营平台")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #1a1a2e;
            padding: 8px 0;
        """)
        layout.addWidget(title)

        tip = QLabel("请选择身份，登录后进入系统")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("font-size: 13px; color: #6b7280; padding-bottom: 16px;")
        layout.addWidget(tip)

        cards = QHBoxLayout()
        cards.setSpacing(24)

        op_card = self._make_role_card(
            "运营人员",
            "账号管理 · 内容管理 · 资源包 · 话术模板",
            ROLE_OPERATOR,
        )
        admin_card = self._make_role_card(
            "管理员",
            "平台发布 · 文件服务 · 配置 · 日志与异常",
            ROLE_ADMIN,
        )
        cards.addWidget(op_card)
        cards.addWidget(admin_card)
        layout.addLayout(cards)

        layout.addStretch()
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #f8fafc, stop:1 #e2e8f0);
            }
        """)

    def _make_role_card(self, role_name: str, desc: str, role_id: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("RoleCard")
        frame.setCursor(Qt.PointingHandCursor)
        frame.setFixedHeight(180)
        frame.setStyleSheet("""
            QFrame#RoleCard {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }
            QFrame#RoleCard:hover {
                background-color: #f1f5f9;
                border-color: #1a73e8;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 26))
        frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        name = QLabel(role_name)
        name.setStyleSheet("font-size: 18px; font-weight: bold; color: #1a1a2e;")
        layout.addWidget(name)

        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 12px; color: #64748b; line-height: 1.4;")
        layout.addWidget(desc_label)
        layout.addStretch()

        btn = QPushButton("进入")
        btn.setFixedHeight(36)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1765cc; }
            QPushButton:pressed { background-color: #1557b0; }
        """)
        btn.clicked.connect(lambda: self._on_role_selected(role_id))
        layout.addWidget(btn)

        def on_frame_release(event):
            if event.button() == Qt.LeftButton:
                child = frame.childAt(event.pos())
                if not isinstance(child, QPushButton):
                    self._on_role_selected(role_id)
                    return
            QFrame.mouseReleaseEvent(frame, event)

        frame.mouseReleaseEvent = on_frame_release
        return frame

    def _on_role_selected(self, role_id: str):
        dlg = LoginDialog(self.db, role_id, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.selected_role = dlg.get_role()
        self._last_username = dlg.get_username()
        if self.selected_role:
            self.accept()

    def get_role(self):
        return self.selected_role

    def get_username(self):
        return self._last_username
